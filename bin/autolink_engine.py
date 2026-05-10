#!/usr/bin/env python3
"""
autolink_engine.py — Extracteur de typed graph déterministe.

Lit le frontmatter d'un subject (`linked_subjects`) + le `REFERENCE.md` de son
type (`typical_linked_types` enrichi en paires {name, type}), croise pour
produire un graph typé. Zéro LLM call.

Sous-commandes :
- extract <subject-path>          → JSON des typed edges sortants du subject
- graph-query <slug> [...]        → JSON des arêtes touchant <slug>, BFS limité
- reconcile <subject-path>        → équivalent extract (idempotent par construction)

Conventions :
- Slug canonique d'un subject : `<type>:<name>` (ex: `supplier:weifang`)
- Format historique toléré : `<type>-<name>` si un type connu correspond au préfixe
- Tous les outputs sortent en JSON sur stdout (exit 0) ; warnings/erreurs sur
  stderr. Conformément au pattern forge_engine.py.

Stdlib only (Python 3.9+).
"""

import argparse
import json
import sys
from pathlib import Path

from forge_lib import (
    get_project_dir,
    parse_frontmatter,
    parse_subject_slug,
    parse_typed_linked_types,
)


def _iter_type_references(project_dir):
    """Itère sur les fichiers REFERENCE.md des types détectés dans le repo."""
    for ref in project_dir.rglob("types/*/REFERENCE.md"):
        yield ref


def _load_type_index(project_dir):
    """Construit un index `type_name -> {ref_path, typed_relations[{name, type}]}`."""
    index = {}
    for ref in _iter_type_references(project_dir):
        fm = parse_frontmatter(ref)
        if not fm:
            continue
        type_name = fm.get("type")
        if not type_name:
            continue
        index[type_name] = {
            "ref_path": str(ref),
            "typed_relations": parse_typed_linked_types(fm.get("typical_linked_types", []) or []),
        }
    return index


def _resolve_memory_path(subject_path):
    """Accepte un dossier subject ou directement un MEMORY.md, retourne le path du MEMORY.md."""
    p = Path(subject_path).resolve()
    if p.is_file():
        return p
    if p.is_dir():
        candidate = p / "MEMORY.md"
        if candidate.exists():
            return candidate
    return None


def extract_typed_edges(subject_path, type_index=None, known_types=None):
    """Extrait les typed edges sortants d'un subject.

    Args:
        subject_path: chemin vers le dossier subject ou son MEMORY.md.
        type_index: index pré-calculé des types (optionnel — recalculé sinon).
        known_types: ensemble des type_name connus (utilisé pour résoudre les slugs ambigus).

    Returns:
        dict JSON-serializable :
        - ok: bool
        - subject: nom du subject
        - type: type du subject
        - edges: liste de {name, target_slug, target_type}
        - warnings: liste de strings (slugs non résolus, etc.)
    """
    memory = _resolve_memory_path(subject_path)
    if not memory:
        return {"ok": False, "error": f"no MEMORY.md at {subject_path}"}

    fm = parse_frontmatter(memory)
    if not fm:
        return {"ok": False, "error": f"no frontmatter at {memory}"}

    subject_name = fm.get("name") or memory.parent.name
    subject_type = fm.get("type")
    linked_subjects = fm.get("linked_subjects", []) or []

    if not subject_type:
        return {"ok": False, "error": f"no `type` in frontmatter at {memory}"}

    project_dir = get_project_dir()
    if type_index is None:
        type_index = _load_type_index(project_dir)
    if known_types is None:
        known_types = set(type_index.keys())

    relations_for_type = type_index.get(subject_type, {}).get("typed_relations", [])
    relation_map = {tr["type"]: tr["name"] for tr in relations_for_type}

    edges = []
    warnings = []
    for raw_slug in linked_subjects:
        if not isinstance(raw_slug, str) or not raw_slug.strip():
            continue
        slug_info = parse_subject_slug(raw_slug.strip(), known_types=known_types)
        target_type = slug_info["type"]
        if not target_type:
            warnings.append(f"slug `{raw_slug}` non résolu (préfixe de type inconnu)")
            edge_name = "linked"
        else:
            edge_name = relation_map.get(target_type, "linked")
            if target_type not in relation_map and relations_for_type:
                warnings.append(
                    f"type cible `{target_type}` absent de typical_linked_types pour type `{subject_type}`"
                )
        edges.append({
            "name": edge_name,
            "target_slug": slug_info["raw"],
            "target_type": target_type,
            "target_name": slug_info["name"],
        })

    return {
        "ok": True,
        "version": 1,
        "subject_name": subject_name,
        "subject_type": subject_type,
        "memory_path": str(memory),
        "edges": edges,
        "warnings": warnings,
    }


def _iter_subjects(project_dir):
    """Itère sur tous les MEMORY.md de subjects dans le repo."""
    for memory in project_dir.rglob("subjects/*/MEMORY.md"):
        yield memory


def _build_full_graph(project_dir):
    """Construit l'index complet du graph typé du repo.

    Returns:
        - by_slug: `<type>:<name>` -> {edges_out: [...], memory_path}
        - incoming: `<type>:<name>` -> [(source_slug, edge_name)]
    """
    type_index = _load_type_index(project_dir)
    known_types = set(type_index.keys())

    by_slug = {}
    incoming = {}

    for memory in _iter_subjects(project_dir):
        result = extract_typed_edges(memory, type_index=type_index, known_types=known_types)
        if not result.get("ok"):
            continue
        subject_type = result["subject_type"]
        subject_name = result["subject_name"]
        slug = f"{subject_type}:{subject_name}"
        by_slug[slug] = {
            "edges_out": result["edges"],
            "memory_path": result["memory_path"],
        }
        for edge in result["edges"]:
            target_slug_info = parse_subject_slug(edge["target_slug"], known_types=known_types)
            if target_slug_info["type"] and target_slug_info["name"]:
                canonical_target = f"{target_slug_info['type']}:{target_slug_info['name']}"
            else:
                canonical_target = edge["target_slug"]
            incoming.setdefault(canonical_target, []).append((slug, edge["name"]))

    return by_slug, incoming, known_types


def graph_query(start_slug, edge_type=None, depth=1, direction="both"):
    """Parcourt le graph depuis un slug, en suivant les typed edges.

    Args:
        start_slug: slug `<type>:<name>` (préféré) ou format historique.
        edge_type: filtre sur le nom de la relation (ex: `ordered_from`). None = tous.
        depth: profondeur max du parcours (BFS).
        direction: `outgoing`, `incoming`, ou `both`.

    Returns:
        dict JSON avec liste `matches` de typed edges visités.
    """
    project_dir = get_project_dir()
    by_slug, incoming, known_types = _build_full_graph(project_dir)

    canonical_info = parse_subject_slug(start_slug, known_types=known_types)
    if canonical_info["type"] and canonical_info["name"]:
        start_canonical = f"{canonical_info['type']}:{canonical_info['name']}"
    else:
        start_canonical = start_slug

    visited = set()
    queue = [(start_canonical, 0)]
    matches = []

    while queue:
        slug, d = queue.pop(0)
        if slug in visited or d > depth:
            continue
        visited.add(slug)
        if d >= depth:
            continue

        if direction in ("outgoing", "both"):
            for edge in by_slug.get(slug, {}).get("edges_out", []):
                if edge_type is not None and edge["name"] != edge_type:
                    continue
                target_info = parse_subject_slug(edge["target_slug"], known_types=known_types)
                if target_info["type"] and target_info["name"]:
                    canonical_target = f"{target_info['type']}:{target_info['name']}"
                else:
                    canonical_target = edge["target_slug"]
                matches.append({
                    "from": slug,
                    "to": canonical_target,
                    "name": edge["name"],
                    "direction": "outgoing",
                    "depth": d + 1,
                })
                queue.append((canonical_target, d + 1))

        if direction in ("incoming", "both"):
            for source_slug, name in incoming.get(slug, []):
                if edge_type is not None and name != edge_type:
                    continue
                matches.append({
                    "from": source_slug,
                    "to": slug,
                    "name": name,
                    "direction": "incoming",
                    "depth": d + 1,
                })
                queue.append((source_slug, d + 1))

    return {
        "ok": True,
        "version": 1,
        "start": start_canonical,
        "edge_type": edge_type,
        "depth": depth,
        "direction": direction,
        "matches": matches,
        "visited_count": len(visited),
    }


def main():
    parser = argparse.ArgumentParser(description="Forge typed-graph autolink engine")
    sub = parser.add_subparsers(dest="cmd")

    p_ext = sub.add_parser("extract", help="Extract typed edges from a subject")
    p_ext.add_argument("subject_path")

    p_q = sub.add_parser("graph-query", help="Walk typed graph from a slug")
    p_q.add_argument("slug")
    p_q.add_argument("--type", dest="edge_type", default=None,
                     help="Filter on edge name (ex: ordered_from)")
    p_q.add_argument("--depth", type=int, default=1)
    p_q.add_argument("--direction", choices=("outgoing", "incoming", "both"),
                     default="both")

    p_rec = sub.add_parser("reconcile",
                           help="Re-extract (idempotent — equivalent to extract)")
    p_rec.add_argument("subject_path")

    args = parser.parse_args()

    if args.cmd in ("extract", "reconcile"):
        result = extract_typed_edges(args.subject_path)
    elif args.cmd == "graph-query":
        result = graph_query(args.slug, args.edge_type, args.depth, args.direction)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
