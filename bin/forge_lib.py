#!/usr/bin/env python3
"""
forge_lib.py — Helpers communs aux scripts de la feedback-loop.

Extraits de forge_scanner.py pour être réutilisés par forge_engine.py
(couche 1 du moteur /documente). Aucune logique métier ici, uniquement :

- parsing YAML minimal du frontmatter
- résolution portable du chemin du repo (PROJECT_DIR)
- helpers de date

NE PAS dépendre de pyyaml ni d'autres packages externes — Python 3 stdlib only.
"""

import os
import re
from datetime import datetime
from pathlib import Path


def get_project_dir() -> Path:
    """Retourne le chemin absolu du repo de travail.

    claude-forge est un binaire installé globalement (plugin Claude Code) qui
    opère sur le repo dans lequel il est invoqué — pas sur son propre repo
    d'install. La résolution suit donc l'ordre suivant :

    1. Variable d'env CLAUDE_FORGE_PROJECT_DIR (override explicite)
    2. Remontée depuis cwd jusqu'à un dossier .git (repo Git racine)
    3. cwd (fallback si pas dans un repo Git)
    """
    env_dir = os.environ.get("CLAUDE_FORGE_PROJECT_DIR")
    if env_dir:
        return Path(env_dir).resolve()

    cwd = Path.cwd().resolve()
    p = cwd
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent

    return cwd


def parse_frontmatter(path):
    """Parse le frontmatter YAML d'un fichier markdown. Retourne None si absent."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    if not content.startswith("---"):
        return None

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None

    yaml_text = match.group(1)
    try:
        return parse_simple_yaml(yaml_text)
    except Exception:
        return None


def parse_simple_yaml(yaml_text):
    """Parser YAML minimal — gère les cas simples du frontmatter subject."""
    result = {}
    current_key = None
    current_list = None
    for line in yaml_text.split("\n"):
        if not line.strip() or line.strip().startswith("#"):
            continue

        if line.startswith("  - ") or line.startswith("    - "):
            if current_list is not None:
                value = line.split("-", 1)[1].strip()
                current_list.append(parse_value(value))
            continue

        if line.startswith("  ") and ":" in line and current_key is not None:
            sub_key, sub_value = line.strip().split(":", 1)
            sub_value = sub_value.strip()
            if isinstance(result.get(current_key), dict):
                result[current_key][sub_key.strip()] = parse_value(sub_value)
            continue

        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_key = key
            current_list = None
            if not value:
                result[key] = []
                current_list = result[key]
            elif value.startswith("["):
                result[key] = parse_inline_list(value)
            elif value.startswith("{"):
                result[key] = parse_inline_dict(value)
            else:
                result[key] = parse_value(value)
    return result


def parse_value(value):
    value = value.strip()
    if value.lower() == "null" or value == "":
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


def parse_inline_list(value):
    inner = value.strip()[1:-1]
    if not inner.strip():
        return []
    return [parse_value(item) for item in inner.split(",")]


def parse_inline_dict(value):
    return {"_inline": value}


def days_since(date_str):
    """Retourne le nombre de jours écoulés depuis une date ISO (YYYY-MM-DD)."""
    if not date_str:
        return None
    try:
        date = datetime.fromisoformat(str(date_str)[:10])
        return (datetime.now() - date).days
    except (ValueError, TypeError):
        return None
