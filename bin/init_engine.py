#!/usr/bin/env python3
"""
init_engine.py — `forge init`

Porte d'entrée d'un nouveau repo client : écrit le `.forge.yaml` à la racine du
pool et scaffolde la structure `subjects/` + `types/`. Rend l'emplacement de
stockage EXPLICITE et propre à chaque repo — le plugin ne suppose plus
l'arborescence de claude-enterprise.

Usage :
  forge init [--output-dir X] [--pool-root Y] [--types-root Z] [--force]

Sans flags : auto-détection (output_dir = entreprise/ si présent sinon racine ;
pool_root = "."). Le `.forge.yaml` écrit reflète ces choix, éditable ensuite.

Convention : JSON sur stdout, `{"ok": true|false, "version": 1, ...}`.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge_lib import get_project_dir

VERSION = 1


def _ok(**extra):
    return {"ok": True, "version": VERSION, **extra}


def _err(message, code="generic_error", **extra):
    return {"ok": False, "version": VERSION, "error": message, "code": code, **extra}


def _render_yaml(output_dir, pool_root, types_root, skill_visibility):
    lines = [
        "# .forge.yaml — configuration socle propre à ce repo.",
        "# Écrit par `forge init`. Toutes les clés sont optionnelles (défauts auto-détectés).",
        "",
        "# Où écrire SUBJECTS-INDEX.md + SUBJECT-POOL-METRICS.md (\".\" = racine du repo)",
        f"output_dir: {output_dir}",
        "",
        "# Dossiers sous lesquels vivent <root>/subjects/",
        f'pool_roots: ["{pool_root}"]',
    ]
    if types_root != pool_root:
        lines.append("")
        lines.append("# Dossiers sous lesquels vivent <root>/types/")
        lines.append(f'types_roots: ["{types_root}"]')
    lines.append("")
    lines.append("# Valeur injectée dans le frontmatter des SKILL.md générés")
    lines.append(f"skill_visibility: {skill_visibility}")
    return "\n".join(lines) + "\n"


def cmd_init(args):
    project_dir = get_project_dir()
    cfg_path = project_dir / ".forge.yaml"

    if cfg_path.exists() and not args.force:
        return _err(
            f".forge.yaml existe déjà à {cfg_path} (utiliser --force pour écraser)",
            code="exists",
        )

    # Auto-détection des défauts si flags absents.
    if args.output_dir is not None:
        output_dir = args.output_dir
    else:
        output_dir = "entreprise" if (project_dir / "entreprise").is_dir() else "."
    pool_root = args.pool_root if args.pool_root is not None else "."
    types_root = args.types_root if args.types_root is not None else pool_root
    skill_visibility = args.skill_visibility or project_dir.name

    # Écriture config
    cfg_path.write_text(
        _render_yaml(output_dir, pool_root, types_root, skill_visibility),
        encoding="utf-8",
    )

    # Scaffold structure (idempotent)
    scaffolded = []

    def _scaffold(rel, child):
        base = project_dir if rel == "." else project_dir / rel
        d = base / child
        gk = d / ".gitkeep"
        if not d.is_dir():
            d.mkdir(parents=True, exist_ok=True)
        if not gk.exists():
            gk.write_text("", encoding="utf-8")
        scaffolded.append(str(d.relative_to(project_dir)))

    _scaffold(pool_root, "subjects")
    _scaffold(types_root, "types")

    return _ok(
        written=str(cfg_path.relative_to(project_dir)),
        output_dir=output_dir,
        pool_root=pool_root,
        types_root=types_root,
        scaffolded=scaffolded,
    )


def main():
    parser = argparse.ArgumentParser(prog="forge init")
    parser.add_argument("--output-dir", default=None, help='où écrire l\'index/metrics ("." = racine)')
    parser.add_argument("--pool-root", default=None, help='dossier des subjects/ ("." = racine)')
    parser.add_argument("--types-root", default=None, help="dossier des types/ (défaut = pool-root)")
    parser.add_argument("--skill-visibility", default=None, help="visibilité injectée dans les SKILL.md générés")
    parser.add_argument("--force", action="store_true", help="écraser un .forge.yaml existant")
    args = parser.parse_args()

    result = cmd_init(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
