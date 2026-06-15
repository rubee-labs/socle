#!/usr/bin/env python3
"""
okf_sync_engine.py — Synchronise les markdown links inline dans les MEMORY.md.

Génère / maintient une section `## Liens` dans le body de chaque MEMORY.md,
entourée de markers HTML, qui reflète les `linked_subjects:` du frontmatter
sous forme de markdown links inline conformes à la spec OKF §5.1
(bundle-relative paths).

Pourquoi : OKF (Open Knowledge Format, Google 2026-06-12) ne parse que les
markdown links **dans le body** pour construire son graph. Forge utilise
`linked_subjects:` dans le frontmatter qui n'est pas lu par un consumer OKF
naïf. Pour atteindre la 100% compat OKF (analyse Forge-Lab #8 2026-06-15,
D9), on émet les liens dans les 2 formats en parallèle.

Sous-commandes :
- sync [--dry-run] [--root PATH]   Régénère la section `## Liens` dans tous les MEMORY.md
- check                            Liste les MEMORY.md où la section est absente ou périmée

Marquage idempotent : la section est entourée de
`<!-- okf-links:start -->` / `<!-- okf-links:end -->` HTML comments invisibles
au rendu. Tout contenu hors markers est préservé.

Format des liens : `[<slug>](/path/relative/to/repo/root/MEMORY.md)`. Les
paths sont bundle-relative (commencent par `/`) — convention OKF recommandée
qui survit au déplacement intra-bundle.

Stdlib only. Pas d'appel LLM. Réutilise `forge_lib` + `autolink_engine`.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from forge_lib import get_project_dir, parse_frontmatter, parse_subject_slug
from autolink_engine import _build_full_graph

# ----------------------------------------------------------------------------
# Constantes
# ----------------------------------------------------------------------------

EXCLUDE_DIRS = {".git", "node_modules", "venv", "__pycache__", ".claude",
                "templates", "fixtures"}

MARKER_START = "<!-- okf-links:start -->"
MARKER_END = "<!-- okf-links:end -->"


def _find_subject_memories(project_dir):
    """Itère sur tous les MEMORY.md de subjects avec frontmatter parsé."""
    for memory in project_dir.rglob("MEMORY.md"):
        if any(part in EXCLUDE_DIRS or part.startswith("_archive")
               for part in memory.parts):
            continue
        fm = parse_frontmatter(memory)
        if not fm or "forging_state" not in fm:
            continue
        yield memory, fm


def _build_slug_to_path(project_dir):
    """Construit l'index slug `<type>:<name>` → path absolu du MEMORY.md.

    Le path absolu est utilisé en interne ; il sera converti en path relatif
    au MEMORY.md émetteur dans `_resolve_target` pour respecter OKF §5.2
    (relative links). Approche plus robuste que §5.1 absolute-bundle-relative
    car elle ne dépend pas du choix de bundle root du consumer.
    """
    index = {}
    for memory, fm in _find_subject_memories(project_dir):
        name = str(fm.get("name") or memory.parent.name)
        subject_type = str(fm.get("type") or "")
        slug = f"{subject_type}:{name}" if subject_type else name
        index[slug] = str(memory.resolve())
    return index


def _resolve_target(raw_slug, slug_to_path, known_types, alias_map=None):
    """Résout un linked_subjects vers (display_slug, bundle_relative_path) ou (slug, None) si non-résolu.

    Tolère les commentaires inline YAML (`#`) et les double-spaces que certains
    subjects Rubee utilisent.
    """
    cleaned = raw_slug.split("#", 1)[0].strip()
    if "  " in cleaned:
        cleaned = cleaned.split("  ", 1)[0].strip()

    if cleaned in slug_to_path:
        return cleaned, slug_to_path[cleaned]

    info = parse_subject_slug(cleaned, known_types=known_types)
    if info["type"] and info["name"]:
        canonical = f"{info['type']}:{info['name']}"
        if canonical in slug_to_path:
            return canonical, slug_to_path[canonical]
        # Try with type-prefix added to name (Rubee convention `supplier-weifang`)
        prefixed_name = f"{info['type']}-{info['name']}"
        prefixed = f"{info['type']}:{prefixed_name}"
        if prefixed in slug_to_path:
            return prefixed, slug_to_path[prefixed]

    if alias_map and cleaned in alias_map:
        canonical = alias_map[cleaned]
        if canonical in slug_to_path:
            return canonical, slug_to_path[canonical]

    return cleaned, None


def _build_alias_map(slug_to_path):
    """Construit un alias map pour matcher les variantes courtes vs préfixées.

    Trois familles d'alias générées :
    1. `<type>:<name_without_type_prefix>` ↔ `<type>:<name_with_type_prefix>`
       (ex: `supplier:weifang` ↔ `supplier:supplier-weifang`)
    2. `<name>` (bare slug sans type) → `<type>:<name>` quand le name est
       unique dans le pool. Couvre les conventions Rubee où les
       linked_subjects utilisent juste le name (ex: `amazon-ads-DE`).
    3. `<type>-<name>` (séparateur historique `-`) → `<type>:<name>`
       (rétrocompat anciens slugs Forge).
    """
    aliases = {}
    # Pass 1 : variantes du préfixe type sur le name
    for canonical in list(slug_to_path.keys()):
        if ":" not in canonical:
            continue
        type_name, name = canonical.split(":", 1)
        prefix = f"{type_name}-"
        if name.startswith(prefix):
            short = name[len(prefix):]
            alt = f"{type_name}:{short}"
            if alt != canonical and alt not in slug_to_path:
                aliases[alt] = canonical
        else:
            alt = f"{type_name}:{prefix}{name}"
            if alt != canonical and alt not in slug_to_path:
                aliases[alt] = canonical

    # Pass 2 : bare name si unique + séparateur historique `-`
    name_to_canonicals = {}
    for canonical in slug_to_path:
        if ":" not in canonical:
            continue
        _type, name = canonical.split(":", 1)
        name_to_canonicals.setdefault(name, []).append(canonical)
    for name, canonicals in name_to_canonicals.items():
        if len(canonicals) == 1:
            canonical = canonicals[0]
            if name != canonical and name not in slug_to_path:
                aliases.setdefault(name, canonical)
            # Aussi forme `<type>-<name>` historique
            type_name = canonical.split(":", 1)[0]
            alt_hist = f"{type_name}-{name}"
            if alt_hist != canonical and alt_hist not in slug_to_path:
                aliases.setdefault(alt_hist, canonical)
    return aliases


def _render_section(targets):
    """Compose la section `## Liens` entre markers HTML.

    Inclut les liens résolus en markdown link OKF + une note pour les non-résolus.
    """
    lines = [MARKER_START, "", "## Liens", ""]
    if not targets:
        lines.append("_Aucun lien sortant._")
        lines.append("")
        lines.append(MARKER_END)
        return "\n".join(lines)

    resolved = [(slug, path) for slug, path in targets if path]
    unresolved = [slug for slug, path in targets if not path]

    for slug, path in resolved:
        lines.append(f"- [{slug}]({path})")

    if unresolved:
        lines.append("")
        lines.append("_Liens non résolus (subjects manquants ou commentaires inline)_ :")
        for slug in unresolved:
            lines.append(f"- `{slug}`")

    lines.append("")
    lines.append(MARKER_END)
    return "\n".join(lines)


def _splice_section(content, new_section):
    """Insère / remplace la section délimitée par les markers.

    Si les markers existent : remplace tout entre eux (markers compris).
    Sinon : append la section à la fin du body (avec ligne vide de séparation).
    """
    pattern = re.compile(
        r"<!-- okf-links:start -->.*?<!-- okf-links:end -->",
        re.DOTALL,
    )
    if pattern.search(content):
        return pattern.sub(new_section, content)
    # Append
    trailing_nl = "" if content.endswith("\n") else "\n"
    sep = "" if content.endswith("\n\n") else "\n"
    return f"{content}{trailing_nl}{sep}{new_section}\n"


def _process_memory(memory, fm, slug_to_path, alias_map, known_types):
    """Calcule la section à écrire pour un MEMORY.md donné.

    Retourne (changed, old_content, new_content, targets).

    Les paths sont convertis en relatifs au MEMORY.md émetteur (OKF §5.2)
    pour rester valides quel que soit le bundle root choisi par le consumer.
    """
    raw_links = fm.get("linked_subjects") or []
    if not isinstance(raw_links, list):
        raw_links = []
    source_dir = memory.parent.resolve()
    targets = []
    for raw in raw_links:
        if not isinstance(raw, str):
            continue
        slug = raw.strip()
        if not slug:
            continue
        resolved_slug, abs_path = _resolve_target(slug, slug_to_path, known_types, alias_map)
        if abs_path:
            try:
                import os
                rel_path = os.path.relpath(abs_path, start=source_dir)
                # Normalise vers POSIX-style pour les liens markdown
                rel_path = rel_path.replace("\\", "/")
                # Prefix `./` si pas déjà `../` pour rester explicitement relatif
                if not rel_path.startswith(".."):
                    rel_path = "./" + rel_path
            except (ValueError, TypeError):
                rel_path = None
            targets.append((resolved_slug, rel_path))
        else:
            targets.append((resolved_slug, None))

    new_section = _render_section(targets)
    old_content = memory.read_text(encoding="utf-8")
    new_content = _splice_section(old_content, new_section)
    changed = (new_content != old_content)
    return changed, old_content, new_content, targets


def cmd_sync(args):
    project_dir = get_project_dir() if not args.root else Path(args.root).resolve()
    slug_to_path = _build_slug_to_path(project_dir)
    alias_map = _build_alias_map(slug_to_path)
    _, _, known_types_set = _build_full_graph(project_dir)
    known_types = set(known_types_set)

    changed_files = []
    resolved_count = 0
    unresolved_count = 0
    for memory, fm in _find_subject_memories(project_dir):
        changed, _old, new_content, targets = _process_memory(
            memory, fm, slug_to_path, alias_map, known_types
        )
        for _slug, path in targets:
            if path:
                resolved_count += 1
            else:
                unresolved_count += 1
        rel = str(memory.relative_to(project_dir)) if memory.is_relative_to(project_dir) else str(memory)
        if changed:
            changed_files.append(rel)
            if not args.dry_run:
                memory.write_text(new_content, encoding="utf-8")

    result = {
        "ok": True,
        "dry_run": args.dry_run,
        "subject_count": len(slug_to_path),
        "changed_count": len(changed_files),
        "resolved_links": resolved_count,
        "unresolved_links": unresolved_count,
        "changed_files": changed_files[:20] if args.dry_run else changed_files,
    }
    if args.dry_run and len(changed_files) > 20:
        result["changed_files_truncated"] = True
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def cmd_check(args):
    project_dir = get_project_dir() if not args.root else Path(args.root).resolve()
    slug_to_path = _build_slug_to_path(project_dir)
    alias_map = _build_alias_map(slug_to_path)
    _, _, known_types_set = _build_full_graph(project_dir)
    known_types = set(known_types_set)

    missing = []
    stale = []
    for memory, fm in _find_subject_memories(project_dir):
        content = memory.read_text(encoding="utf-8")
        has_markers = MARKER_START in content and MARKER_END in content
        rel = str(memory.relative_to(project_dir)) if memory.is_relative_to(project_dir) else str(memory)
        if not has_markers:
            missing.append(rel)
            continue
        changed, _old, _new, _t = _process_memory(memory, fm, slug_to_path, alias_map, known_types)
        if changed:
            stale.append(rel)

    print(json.dumps({
        "ok": True,
        "subject_count": len(slug_to_path),
        "missing_section": missing,
        "stale_section": stale,
        "in_sync_count": len(slug_to_path) - len(missing) - len(stale),
    }, indent=2, ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="OKF v0.1 compat: maintain inline `## Liens` section in MEMORY.md bodies.")
    sub = parser.add_subparsers(dest="cmd")

    p_sync = sub.add_parser("sync", help="Regenerate the `## Liens` section in all MEMORY.md")
    p_sync.add_argument("--dry-run", action="store_true", help="Don't write, just report what would change")
    p_sync.add_argument("--root", default=None, help="Override project root (default: auto-detect via git)")

    p_check = sub.add_parser("check", help="List MEMORY.md where the section is missing or stale")
    p_check.add_argument("--root", default=None)

    args = parser.parse_args()
    if args.cmd == "sync":
        sys.exit(cmd_sync(args))
    elif args.cmd == "check":
        sys.exit(cmd_check(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
