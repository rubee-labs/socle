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


_CONFIG_CACHE = {}

# Défauts historiques (arborescence claude-enterprise). Servent UNIQUEMENT de
# valeurs par défaut quand `.forge.yaml` est absent — jamais codés en dur dans la
# logique des engines.
_DEFAULT_POOL_ROOTS = ["services", "entreprise", "humains", "."]
_DEFAULT_DOMAIN_ROOTS = ["services", "humains", "entreprise"]
_DEFAULT_SKILL_VISIBILITY = "entreprise"


def load_forge_config(project_dir=None) -> dict:
    """Charge la config par-repo `.forge.yaml` (racine du pool) + défauts auto-détectés.

    Rend un dict aux clés garanties :
      output_dir       : Path absolu (où écrire SUBJECTS-INDEX.md + SUBJECT-POOL-METRICS.md)
      pool_roots       : list[str]  (dossiers sous lesquels vivent <root>/subjects/ ; "." = racine)
      types_roots      : list[str]  (idem pour <root>/types/ ; défaut = pool_roots)
      domain_roots     : list[str]  (préfixes regroupés sur 2 segments dans les metrics)
      skill_visibility : str

    Ne lève JAMAIS : fichier absent ou malformé → auto-détection complète. Ce
    contrat est critique car le scanner appelle cette fonction à l'import (un
    throw casserait le hook SessionStart).

    Auto-détection (clé absente) :
      - output_dir : <root>/entreprise si ce dossier existe, sinon <root>
        (jamais de création forcée d'un `entreprise/` fantôme).
      - pool_roots / types_roots / domain_roots / skill_visibility : défauts CE.
        Le "." dans pool_roots rend un pool plat (<root>/subjects/) découvrable
        sans config, et est inerte pour CE (pas de subjects/ à sa racine).
    """
    project_dir = Path(project_dir).resolve() if project_dir else get_project_dir()
    cache_key = str(project_dir)
    if cache_key in _CONFIG_CACHE:
        return _CONFIG_CACHE[cache_key]

    raw = {}
    cfg_path = project_dir / ".forge.yaml"
    try:
        if cfg_path.is_file():
            text = cfg_path.read_text(encoding="utf-8")
            # parse_simple_yaml ne gère pas les commentaires en fin de ligne ;
            # on retire les ` # ...` (hash précédé d'un espace, hors guillemets simples)
            # pour tolérer un .forge.yaml écrit à la main avec commentaires inline.
            cleaned = "\n".join(re.sub(r"\s+#.*$", "", ln) for ln in text.split("\n"))
            raw = parse_simple_yaml(cleaned) or {}
    except Exception:
        raw = {}

    def _resolve_dir(value):
        value = str(value).strip()
        if value in (".", ""):
            return project_dir
        return project_dir / value

    # output_dir
    if raw.get("output_dir") is not None:
        output_dir = _resolve_dir(raw["output_dir"])
    else:
        ent = project_dir / "entreprise"
        output_dir = ent if ent.is_dir() else project_dir

    def _as_list(value, default):
        if value is None:
            return list(default)
        if isinstance(value, list):
            return [str(v) for v in value]
        return [str(value)]

    pool_roots = _as_list(raw.get("pool_roots"), _DEFAULT_POOL_ROOTS)
    types_roots = _as_list(raw.get("types_roots"), pool_roots)
    domain_roots = _as_list(raw.get("domain_roots"), _DEFAULT_DOMAIN_ROOTS)
    skill_visibility = raw.get("skill_visibility") or _DEFAULT_SKILL_VISIBILITY

    config = {
        "output_dir": output_dir,
        "pool_roots": pool_roots,
        "types_roots": types_roots,
        "domain_roots": domain_roots,
        "skill_visibility": str(skill_visibility),
    }
    _CONFIG_CACHE[cache_key] = config
    return config


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
    """Parser YAML minimal — gère les cas simples du frontmatter subject.

    Une clé sans valeur inline (`last_event:`) est résolue par la ligne
    suivante : `  - item` → liste, `  sous_cle: valeur` → dict. Sans ligne
    indentée derrière, la clé vaut [] (compat historique : liste vide).
    Correctif 2026-09-06 : avant, toute clé sans valeur devenait une liste,
    et les blocs `last_event:` / `last_synthesis:` étaient lus comme [].
    """
    result = {}
    current_key = None
    current_list = None
    pending_key = None  # clé sans valeur inline, type encore indéterminé
    for line in yaml_text.split("\n"):
        if not line.strip() or line.strip().startswith("#"):
            continue

        if line.startswith("  - ") or line.startswith("    - "):
            if pending_key is not None:
                result[pending_key] = []
                current_list = result[pending_key]
                pending_key = None
            if current_list is not None:
                value = line.split("-", 1)[1].strip()
                current_list.append(parse_value(value))
            continue

        if line.startswith("  ") and ":" in line and current_key is not None:
            if pending_key is not None:
                result[pending_key] = {}
                pending_key = None
            sub_key, sub_value = line.strip().split(":", 1)
            sub_value = sub_value.strip()
            if isinstance(result.get(current_key), dict):
                result[current_key][sub_key.strip()] = parse_value(sub_value)
            continue

        if ":" in line and not line.startswith(" "):
            if pending_key is not None:
                result[pending_key] = []
                pending_key = None
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_key = key
            current_list = None
            if not value:
                result[key] = []
                pending_key = key
            elif value.startswith("["):
                result[key] = parse_inline_list(value)
            elif value.startswith("{"):
                result[key] = parse_inline_dict(value)
            else:
                result[key] = parse_value(value)
    if pending_key is not None:
        result[pending_key] = []
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
    """Parse `{key: v, key: v}` → dict réel. Pas de nesting, valeurs scalaires uniquement."""
    s = value.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return {"_inline": value}
    inner = s[1:-1].strip()
    if not inner:
        return {}
    result = {}
    for pair in inner.split(","):
        if ":" not in pair:
            continue
        k, v = pair.split(":", 1)
        result[k.strip()] = parse_value(v.strip())
    return result


def parse_typed_linked_types(raw):
    """Décode `typical_linked_types` en liste normalisée de {name, type}.

    Supporte deux formats (rétrocompatibilité) :
    - Ancien : liste plate de types (`[supplier, product-line]`) → name == type
    - Nouveau : liste de paires inline (`[{name: ordered_from, type: supplier}]`)

    Retourne toujours `[{"name": str, "type": str}, ...]`. Items invalides
    silencieusement ignorés.
    """
    result = []
    if not raw or not isinstance(raw, list):
        return result
    for item in raw:
        if isinstance(item, str):
            stripped = item.strip()
            if stripped.startswith("{"):
                parsed = parse_inline_dict(stripped)
                if parsed and "name" in parsed and "type" in parsed:
                    result.append({"name": str(parsed["name"]), "type": str(parsed["type"])})
            elif stripped:
                result.append({"name": stripped, "type": stripped})
        elif isinstance(item, dict):
            if "_inline" in item:
                parsed = parse_inline_dict(item["_inline"])
                if parsed and "name" in parsed and "type" in parsed:
                    result.append({"name": str(parsed["name"]), "type": str(parsed["type"])})
            elif "name" in item and "type" in item:
                result.append({"name": str(item["name"]), "type": str(item["type"])})
    return result


def parse_subject_slug(slug, known_types=None):
    """Décode un slug `<type>:<name>` ou fallback `<type>-<name>`.

    Format canonique : `supplier:weifang` (séparateur `:`).
    Fallback historique : `supplier-weifang` (séparateur `-`, ambigu) — résolu
    seulement si `known_types` est fourni et qu'un préfixe correspond.

    Retourne `{"type": str|None, "name": str, "raw": str}`.
    """
    if not slug:
        return {"type": None, "name": "", "raw": slug or ""}
    if ":" in slug:
        t, n = slug.split(":", 1)
        return {"type": t.strip(), "name": n.strip(), "raw": slug}
    if known_types:
        for t in sorted(known_types, key=len, reverse=True):
            prefix = f"{t}-"
            if slug.startswith(prefix):
                return {"type": t, "name": slug[len(prefix):], "raw": slug}
    return {"type": None, "name": slug, "raw": slug}


def days_since(date_str):
    """Retourne le nombre de jours écoulés depuis une date ISO (YYYY-MM-DD)."""
    if not date_str:
        return None
    try:
        date = datetime.fromisoformat(str(date_str)[:10])
        return (datetime.now() - date).days
    except (ValueError, TypeError):
        return None
