#!/usr/bin/env python3
"""
documente_lib.py — Helpers pour documente_engine.py.

Édition surgicale du frontmatter YAML. Préserve l'ordre des clés,
les commentaires, et le body markdown intact. Stdlib only.
"""

import hashlib
import re
from pathlib import Path


def split_frontmatter(content):
    """Sépare le frontmatter du body. Retourne (fm_lines, body)."""
    if not content.startswith("---"):
        return None, content
    match = re.match(r"^---\n(.*?)\n---\n?", content, re.DOTALL)
    if not match:
        return None, content
    fm_text = match.group(1)
    body = content[match.end():]
    return fm_text.split("\n"), body


def join_frontmatter(fm_lines, body):
    """Reconstruit le fichier complet."""
    fm_text = "\n".join(fm_lines)
    return f"---\n{fm_text}\n---\n{body}"


def find_key_block(fm_lines, key):
    """Trouve le bloc d'une clé top-level dans le frontmatter.

    Retourne (start_idx, end_idx_exclusive, kind) où kind est 'scalar', 'dict', 'list', 'empty_list'.
    Retourne (None, None, None) si la clé n'existe pas.
    """
    pattern = re.compile(rf"^{re.escape(key)}\s*:\s*(.*)$")
    for i, line in enumerate(fm_lines):
        m = pattern.match(line)
        if not m:
            continue
        value_part = m.group(1).strip()
        if value_part:
            # Scalar inline (ou liste/dict inline []/{}) — sur 1 ligne
            return i, i + 1, "scalar"
        # Sinon : valeur sur lignes suivantes (dict ou liste)
        j = i + 1
        kind = "empty_list"
        while j < len(fm_lines):
            nxt = fm_lines[j]
            if nxt.startswith("  - "):
                kind = "list"
                j += 1
            elif nxt.startswith("  ") and ":" in nxt:
                kind = "dict"
                j += 1
            elif nxt.strip() == "":
                # Ligne vide : on s'arrête, elle ne fait pas partie du bloc
                break
            elif nxt.startswith("    "):
                # Ligne profondément indentée (sous-bloc d'un dict) — fait partie du bloc
                j += 1
            else:
                break
        return i, j, kind
    return None, None, None


def serialize_value(value):
    """Sérialise une valeur scalaire pour YAML."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    if any(c in s for c in [":", "#"]) and not (s.startswith('"') and s.endswith('"')):
        return f'"{s}"'
    return s


def render_scalar_line(key, value):
    """Rend une ligne `key: value`."""
    return f"{key}: {serialize_value(value)}"


def render_dict_block(key, dict_value):
    """Rend un bloc `key:\\n  k1: v1\\n  k2: v2`."""
    lines = [f"{key}:"]
    for k, v in dict_value.items():
        lines.append(f"  {k}: {serialize_value(v)}")
    return lines


def render_list_block(key, list_value):
    """Rend un bloc `key:\\n  - item1\\n  - item2`."""
    if not list_value:
        return [f"{key}: []"]
    lines = [f"{key}:"]
    for item in list_value:
        lines.append(f"  - {serialize_value(item)}")
    return lines


def parse_existing_list(fm_lines, start, end):
    """Extrait les items d'un bloc liste existant."""
    items = []
    for i in range(start + 1, end):
        line = fm_lines[i]
        if line.startswith("  - "):
            items.append(line[4:].strip())
    return items


def apply_patch(fm_lines, patch):
    """Applique un patch dict au frontmatter et retourne les nouvelles lignes.

    Pour chaque clé du patch :
    - liste avec items "+x" / "-x" → append/remove sur la liste existante
    - valeur scalaire / dict / liste plate → remplace ou ajoute
    """
    new_lines = list(fm_lines)
    for key, value in patch.items():
        start, end, kind = find_key_block(new_lines, key)

        # Liste avec opérations +/-
        is_list_ops = (
            isinstance(value, list)
            and value
            and all(isinstance(v, str) and (v.startswith("+") or v.startswith("-")) for v in value)
        )
        if is_list_ops:
            if start is None:
                existing = []
                start = len(new_lines)
                end = len(new_lines)
            else:
                existing = parse_existing_list(new_lines, start, end)
            for op in value:
                target = op[1:]
                if op.startswith("+") and target not in existing:
                    existing.append(target)
                elif op.startswith("-") and target in existing:
                    existing.remove(target)
            new_block = render_list_block(key, existing)
            new_lines[start:end] = new_block
            continue

        # Remplacement direct
        if isinstance(value, dict):
            new_block = render_dict_block(key, value)
        elif isinstance(value, list):
            new_block = render_list_block(key, value)
        else:
            new_block = [render_scalar_line(key, value)]

        if start is None:
            new_lines.extend(new_block)
        else:
            new_lines[start:end] = new_block

    return new_lines


def parse_nested_dict_block(path, top_key):
    """Lit le frontmatter d'un fichier et extrait un dict imbriqué sous une clé donnée.

    Contourne la limitation de forge_lib.parse_simple_yaml qui ne sait pas
    distinguer un bloc dict vide d'un bloc liste vide.
    Retourne un dict {sub_key: parsed_value} ou {} si la clé n'existe pas.
    """
    content = path.read_text(encoding="utf-8")
    fm_lines, _ = split_frontmatter(content)
    if fm_lines is None:
        return {}
    start, end, kind = find_key_block(fm_lines, top_key)
    if start is None or kind != "dict":
        return {}
    result = {}
    for i in range(start + 1, end):
        line = fm_lines[i]
        if line.startswith("  ") and ":" in line and not line.startswith("    "):
            sub_key, sub_value = line.strip().split(":", 1)
            result[sub_key.strip()] = _parse_scalar(sub_value.strip())
    return result


def _parse_scalar(value):
    """Parse un scalaire YAML simple (int, float, bool, null, string)."""
    if value == "" or value.lower() == "null":
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value


def patch_frontmatter_file(path, patch, dry_run=False, expected_hash=None):
    """Applique le patch au MEMORY.md. Retourne dict {changed, before_hash, after_hash, dry_run}.

    Si `expected_hash` est fourni (12 hex chars du sha256 attendu sur le contenu
    actuel), refuse l'écriture quand le hash réel diverge — fail explicite plutôt
    qu'overwrite stale, pattern Optimike Obsidian MCP `expectedHash` (analyse
    Forge-Lab #7 2026-05-26). Le mismatch est signalé via la clé `stale_hash`
    dans le retour : le caller (CLI ou autre agent) décide quoi faire.

    Cible : éviter le scénario incident 2026-05-26 (2 sessions Claude qui
    committent le même repo en parallèle, commits tronqués) — feedback critique
    `feedback_pas_de_sessions_git_concurrentes.md` côté CE.
    """
    content = path.read_text(encoding="utf-8")
    before_hash = hashlib.sha256(content.encode()).hexdigest()[:12]

    if expected_hash is not None and expected_hash != before_hash:
        return {
            "changed": False,
            "before_hash": before_hash,
            "after_hash": None,
            "dry_run": dry_run,
            "stale_hash": True,
            "expected_hash": expected_hash,
        }

    fm_lines, body = split_frontmatter(content)
    if fm_lines is None:
        raise ValueError(f"no frontmatter found in {path}")
    new_fm_lines = apply_patch(fm_lines, patch)
    new_content = join_frontmatter(new_fm_lines, body)
    after_hash = hashlib.sha256(new_content.encode()).hexdigest()[:12]
    changed = (before_hash != after_hash)
    if changed and not dry_run:
        path.write_text(new_content, encoding="utf-8")
    return {
        "changed": changed,
        "before_hash": before_hash,
        "after_hash": after_hash,
        "dry_run": dry_run,
        "stale_hash": False,
    }
