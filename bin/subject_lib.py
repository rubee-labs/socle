#!/usr/bin/env python3
"""subject_lib.py — types et capacités des subjects (SOCLE 0.7.0).

Design 2026-10-10 (docs/superpowers/specs/2026-10-10-subject-par-en-tete-design.md) :
un subject est reconnu à son en-tête, jamais à son chemin. Ce module dit quel
type il a (en-tête > type_by_path > choix de Claude) et ce que ce type sait faire.

Python 3 stdlib uniquement.
"""

from fnmatch import fnmatch
from pathlib import Path

from forge_lib import load_forge_config, parse_frontmatter

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ALL_CAPABILITIES = ["memory", "decisions", "lifecycle", "events", "links"]
DEFAULT_CAPABILITIES = ["memory", "decisions", "lifecycle"]
_SKIP_PARTS = {".git", "node_modules", "fixtures", "venv", "__pycache__"}


def _iter_reference_files(root):
    for ref in sorted(Path(root).rglob("types/*/REFERENCE.md")):
        rel_parts = ref.relative_to(root).parts
        if any(p in _SKIP_PARTS or p.startswith(".") for p in rel_parts):
            continue
        yield ref


def load_type_index(project_dir):
    """Index type → {ref_path, capabilities, source, name_pattern}.

    Les types du plugin sont lus d'abord, ceux du dépôt ensuite : le dépôt
    surcharge. Un REFERENCE.md sans champ `capabilities` (types métier d'avant
    0.7.0) reçoit toutes les capacités : c'était leur comportement.
    """
    index = {}
    for source, root in (("plugin", PLUGIN_ROOT), ("repo", Path(project_dir))):
        for ref in _iter_reference_files(root):
            fm = parse_frontmatter(ref) or {}
            name = fm.get("type")
            if not name:
                continue
            caps = fm.get("capabilities")
            if isinstance(caps, list) and caps:
                caps = [c for c in ALL_CAPABILITIES if c in caps]
            else:
                caps = list(ALL_CAPABILITIES)
            index[str(name)] = {
                "ref_path": str(ref),
                "capabilities": caps,
                "source": source,
                "name_pattern": fm.get("name_pattern"),
            }
    return index


def type_capabilities(type_name, type_index):
    """Rend (capacités, type connu). Type inconnu ou absent : capacités par défaut."""
    entry = type_index.get(str(type_name)) if type_name else None
    if entry is None:
        return list(DEFAULT_CAPABILITIES), False
    return list(entry["capabilities"]), True


def has_capability(fm, type_index, capability):
    caps, _ = type_capabilities((fm or {}).get("type"), type_index)
    return capability in caps


def resolve_type(subject_dir, project_dir, config=None):
    """Type d'un dossier : en-tête, puis type_by_path, puis choix de Claude.

    Un type présent dans l'en-tête n'est jamais recalculé. `fnmatch` laisse `*`
    traverser les `/` : l'ordre des règles départage (cas avant skill).
    """
    subject_dir = Path(subject_dir)
    project_dir = Path(project_dir)
    fm = parse_frontmatter(subject_dir / "MEMORY.md") or {}
    if fm.get("type"):
        return {"type": str(fm["type"]), "source": "frontmatter"}
    config = config or load_forge_config(project_dir)
    try:
        rel = subject_dir.resolve().relative_to(project_dir.resolve()).as_posix()
    except ValueError:
        rel = subject_dir.as_posix()
    if "subjects" in rel.split("/"):
        # Sous subjects/, le type vient de l'en-tête ou de Claude, jamais de l'emplacement.
        return {"type": None, "source": "claude"}
    for rule in config.get("type_by_path", []):
        if fnmatch(rel, rule["pattern"]):
            return {"type": rule["type"], "source": "type_by_path"}
    return {"type": None, "source": "claude"}
