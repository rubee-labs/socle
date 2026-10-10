# Subject reconnu par son en-tête — plan d'implémentation

> **Pour les agents d'exécution :** sous-skill requis : superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans, tâche par tâche. Les étapes utilisent des cases à cocher (`- [ ]`).

**But :** SOCLE 0.7.0. Tout MEMORY.md dont l'en-tête porte `forging_state` est un subject, où qu'il soit. Son type vient de l'en-tête, puis de `type_by_path`, puis du choix de Claude. `/documente` n'a plus qu'un circuit, sans question.

**Architecture :**
- Une seule fonction de découverte, `forge_lib.find_subjects`, remplace les quatre recherches par chemin.
- Un nouveau module `subject_lib.py` porte l'attribution du type et les capacités par type. Les types génériques sont livrés dans `types/` à la racine du plugin.
- Un nouveau module `convert_lib.py` convertit un MEMORY.md à l'ancien format sans rien perdre.
- `documente_engine.py` expose `prepare` (réécrit), `convert` et `migrate`.
- Le SKILL.md perd la phase F0 et le workflow folder.

**Stack :** Python 3, bibliothèque standard uniquement (pas de pyyaml) ; pytest ; bash pour le dispatcher `bin/forge`.

**Spec :** `docs/superpowers/specs/2026-10-10-subject-par-en-tete-design.md` (dépôt socle).

## Contraintes globales

- Python 3 stdlib uniquement, comme tout `bin/` (en-tête de `forge_lib.py`).
- Chaque commande `documente_engine.py` rend un JSON `{"ok": ..., "version": 1, ...}` sur stdout et sort en code 0. Les erreurs passent par `_err(message, code=...)`.
- `load_forge_config` ne lève jamais d'exception : un `.forge.yaml` absent ou malformé donne les défauts.
- Aucune question à l'utilisateur dans `/documente` pour nommer, typer ou classer.
- Une conversion ne supprime aucune ligne de contenu.
- Pas de conversion en masse : `forge migrate` n'existe qu'en `--dry-run`.
- Plafond par défaut d'un MEMORY.md : 8 Ko (`DEFAULT_MEMORY_MAX_KB`, déjà présent).
- Les 4 dépôts consommateurs (civisol-ai, equipstore-direction, equipstore-hl, equipstore-ia-entreprise) ne changent pas leur `.forge.yaml`.
- Version livrée : 0.7.0.
- Langue : français, accents corrects, dans le code (commentaires, messages) comme dans la doc.
- Lancer les tests depuis la racine de socle : `python3 -m pytest -q`. État de départ : 129 tests verts.

## Points d'attention pour la relecture

Comportements que la spec implique sans les tester explicitement, ou qui risquent de piquer :

1. **Titre `##` dans un bloc de code** pendant la conversion : il ne doit pas être pris pour une section. Test `test_titre_dans_bloc_de_code_ignore` (tâche 5).
2. **Balises `okf-links`** : la conversion doit les garder intactes et en fin de fichier. Test `test_bloc_okf_conserve_en_fin` (tâche 5).
3. **Stagnation sur un type sans `events`** : un `tool` converti, sans `last_event`, ne doit lever ni alerte ni métrique de stagnation. Test `test_pas_de_stagnation_sans_capacite_events` (tâche 3).
4. **Motif `type_by_path` à la racine** : avec `fnmatch`, `*/skills/*` ne correspond pas à `skills/x` (il faut un segment devant), mais `*` traverse les `/`. L'ordre des règles est donc ce qui départage. Tests `test_ordre_des_motifs` et `test_motif_sans_segment_initial` (tâche 2).
5. **Double conversion** : relancer `convert` sur un MEMORY déjà converti ne doit rien changer. Test `test_convert_deja_subject_noop` (tâche 5).

---

## Structure des fichiers

| Fichier | Rôle | Tâche |
|---|---|---|
| `bin/forge_lib.py` | + `iter_memory_files`, `find_subjects`, clé de config `type_by_path` | 1 |
| `bin/subject_lib.py` (nouveau) | index des types, capacités, `resolve_type`, `has_capability` | 2 |
| `types/<type>/REFERENCE.md` (nouveaux, ×6) | types génériques du plugin | 2 |
| `bin/forge_scanner.py` | découverte via `find_subjects`, alertes `duplicate_name` / `unknown_type`, stagnation filtrée, index par type | 3 |
| `bin/documente_engine.py` | `list-subjects` via `find_subjects` (tâche 3) ; `prepare` réécrit, `convert`, `migrate` (tâches 5-6) | 3, 5, 6 |
| `bin/autolink_engine.py` | `_iter_subjects` via `find_subjects` | 3 |
| `bin/forge_engine.py` | `resolve_link` par `name` puis dossier, homonymes refusés | 4 |
| `bin/convert_lib.py` (nouveau) | conversion pure texte → texte | 5 |
| `bin/forge` | sous-commande `migrate` | 6 |
| `skills/documente/SKILL.md`, `rules/subject-pool.md` | circuit unique, suppression de F0 et du folder | 7 |
| `VERSION`, `.claude-plugin/*.json`, `README.md` | 0.7.0 | 8 |
| CE : `.forge.yaml`, `entreprise/config/rules/operations.md`, `~/.claude/CLAUDE.md`, décision | adoption | 9 |

---

### Tâche 1 : découverte par en-tête et clé `type_by_path`

**Fichiers :**
- Modifier : `bin/forge_lib.py` (ajouts après `load_forge_config`, et dans `load_forge_config` avant `_CONFIG_CACHE[cache_key] = config`)
- Créer : `tests/test_find_subjects.py`
- Modifier : `tests/test_forge_config.py` (ajout de deux tests)

**Interfaces :**
- Produit :
  - `iter_memory_files(project_dir: Path) -> Iterator[Path]` ;
  - `find_subjects(project_dir: Path | None = None) -> list[tuple[Path, dict]]`, triée par chemin ;
  - `load_forge_config(...)["type_by_path"] -> list[dict]`, chaque dict de la forme `{"pattern": str, "type": str}`, et `[]` par défaut.

- [ ] **Étape 1 : écrire les tests qui échouent**

`tests/test_find_subjects.py` :

```python
"""find_subjects : un subject est reconnu à son en-tête, pas à son chemin (0.7.0)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
from forge_lib import find_subjects, iter_memory_files  # noqa: E402


def _memory(root, rel, frontmatter):
    d = root / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / "MEMORY.md").write_text(f"---\n{frontmatter}\n---\n\n## Quick\n\nx\n", encoding="utf-8")
    return d / "MEMORY.md"


def test_subject_hors_dossier_subjects_trouve(tmp_path):
    m = _memory(tmp_path, "entreprise/tools/factures", "name: factures\ntype: tool\nforging_state: actif")
    assert [p for p, _ in find_subjects(tmp_path)] == [m]


def test_ancien_format_ignore(tmp_path):
    _memory(tmp_path, "entreprise/tools/factures", "entite: factures\ntype: tool")
    assert find_subjects(tmp_path) == []
    assert len(list(iter_memory_files(tmp_path))) == 1


def test_fixtures_archive_et_caches_exclus(tmp_path):
    fm = "name: x\ntype: tool\nforging_state: actif"
    _memory(tmp_path, "tests/fixtures/x", fm)
    _memory(tmp_path, "services/_archive_2025/x", fm)
    _memory(tmp_path, ".claude/x", fm)
    _memory(tmp_path, "node_modules/x", fm)
    gardé = _memory(tmp_path, "services/achats/subjects/order-1", fm)
    assert [p for p, _ in find_subjects(tmp_path)] == [gardé]


def test_frontmatter_rendu_et_tri(tmp_path):
    b = _memory(tmp_path, "b/x", "name: b\ntype: tool\nforging_state: actif")
    a = _memory(tmp_path, "a/x", "name: a\ntype: tool\nforging_state: archived")
    res = find_subjects(tmp_path)
    assert [p for p, _ in res] == [a, b]
    assert res[0][1]["forging_state"] == "archived"
```

Ajouter à la fin de `tests/test_forge_config.py` :

```python
def test_type_by_path_absent_liste_vide(tmp_path):
    _fresh()
    assert load_forge_config(tmp_path)["type_by_path"] == []


def test_type_by_path_lu_dans_l_ordre(tmp_path):
    _fresh()
    (tmp_path / ".forge.yaml").write_text(
        "type_by_path:\n"
        '  - {pattern: "*/skills/*/cas/*", type: skill-cas}\n'
        '  - {pattern: "*/skills/*", type: skill}\n'
        "  - {pattern: incomplet}\n",
        encoding="utf-8",
    )
    assert load_forge_config(tmp_path)["type_by_path"] == [
        {"pattern": "*/skills/*/cas/*", "type": "skill-cas"},
        {"pattern": "*/skills/*", "type": "skill"},
    ]
```

- [ ] **Étape 2 : vérifier qu'ils échouent**

Lancer : `python3 -m pytest -q tests/test_find_subjects.py tests/test_forge_config.py`
Attendu : ÉCHEC, avec `ImportError: cannot import name 'find_subjects'` et `KeyError: 'type_by_path'`.

- [ ] **Étape 3 : implémenter**

Dans `bin/forge_lib.py`, dans `load_forge_config`, juste avant `config = {` :

```python
    # type_by_path (0.7.0) : règles emplacement → type, lues dans l'ordre, la
    # première qui correspond gagne. Une règle incomplète est ignorée en silence
    # (contrat : load_forge_config ne lève jamais).
    type_by_path = []
    for item in (raw.get("type_by_path") or []):
        if isinstance(item, dict) and item.get("pattern") and item.get("type"):
            type_by_path.append({"pattern": str(item["pattern"]), "type": str(item["type"])})
```

et ajouter `"type_by_path": type_by_path,` dans le dict `config`.

Après `load_forge_config`, ajouter :

```python
# Dossiers jamais parcourus pour trouver des MEMORY.md (repris de forge_scanner,
# + fixtures). Les dossiers cachés et _archive* sont exclus en plus.
_WALK_EXCLUDE_DIRS = {".git", "node_modules", "venv", "__pycache__", ".claude", "templates", "fixtures"}


def iter_memory_files(project_dir):
    """Rend tous les MEMORY.md du dépôt, convertis ou non, dans un ordre stable."""
    project_dir = Path(project_dir)
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = sorted(
            d for d in dirs
            if d not in _WALK_EXCLUDE_DIRS
            and not d.startswith(".")
            and not d.startswith("_archive")
        )
        if "MEMORY.md" in files:
            yield Path(root) / "MEMORY.md"


def find_subjects(project_dir=None):
    """Liste les subjects : tout MEMORY.md dont l'en-tête porte forging_state.

    Le chemin ne compte pas (design 2026-10-10, SOCLE 0.7.0). Un MEMORY.md à
    l'ancien format n'est pas un subject tant que /documente ne l'a pas converti.
    Rend [(chemin du MEMORY.md, frontmatter)], trié par chemin.
    """
    project_dir = Path(project_dir) if project_dir else get_project_dir()
    out = []
    for memory in iter_memory_files(project_dir):
        fm = parse_frontmatter(memory)
        if fm and "forging_state" in fm:
            out.append((memory, fm))
    return sorted(out, key=lambda x: str(x[0]))
```

- [ ] **Étape 4 : vérifier que tout passe**

Lancer : `python3 -m pytest -q`
Attendu : tout vert, soit 129 + 6 = 135 tests.

- [ ] **Étape 5 : commit**

```bash
git add bin/forge_lib.py tests/test_find_subjects.py tests/test_forge_config.py
git commit -m "feat(lib): find_subjects reconnaît un subject à son en-tête + clé type_by_path"
```

---

### Tâche 2 : types génériques, capacités et attribution du type

**Fichiers :**
- Créer : `bin/subject_lib.py`
- Créer : `types/skill/REFERENCE.md`, `types/skill-cas/REFERENCE.md`, `types/tool/REFERENCE.md`, `types/agent/REFERENCE.md`, `types/service/REFERENCE.md`, `types/projet/REFERENCE.md`
- Créer : `tests/test_subject_types.py`

**Interfaces :**
- Consomme : `forge_lib.load_forge_config`, `forge_lib.parse_frontmatter`.
- Produit :
  - `ALL_CAPABILITIES = ["memory", "decisions", "lifecycle", "events", "links"]` ;
  - `DEFAULT_CAPABILITIES = ["memory", "decisions", "lifecycle"]` ;
  - `load_type_index(project_dir) -> dict[str, dict]`, chaque entrée de la forme `{"ref_path": str, "capabilities": list[str], "source": "plugin"|"repo", "name_pattern": str|None}` ;
  - `type_capabilities(type_name: str|None, type_index: dict) -> tuple[list[str], bool]`, où le booléen dit si le type est connu ;
  - `has_capability(fm: dict, type_index: dict, capability: str) -> bool` ;
  - `resolve_type(subject_dir, project_dir, config=None) -> {"type": str|None, "source": "frontmatter"|"type_by_path"|"claude"}`.

- [ ] **Étape 1 : écrire les tests qui échouent**

`tests/test_subject_types.py` :

```python
"""Types et capacités des subjects (design 2026-10-10 §2)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
import forge_lib  # noqa: E402
from subject_lib import (  # noqa: E402
    ALL_CAPABILITIES, DEFAULT_CAPABILITIES,
    has_capability, load_type_index, resolve_type, type_capabilities,
)

CE_RULES = (
    "type_by_path:\n"
    '  - {pattern: "*/skills/*/cas/*", type: skill-cas}\n'
    '  - {pattern: "*/skills/*", type: skill}\n'
    '  - {pattern: "*/tools/*", type: tool}\n'
    '  - {pattern: "services/*", type: service}\n'
)


def _repo(tmp_path, forge_yaml=""):
    forge_lib._CONFIG_CACHE.clear()
    if forge_yaml:
        (tmp_path / ".forge.yaml").write_text(forge_yaml, encoding="utf-8")
    return tmp_path


def _dir(root, rel, frontmatter=None):
    d = root / rel
    d.mkdir(parents=True, exist_ok=True)
    if frontmatter is not None:
        (d / "MEMORY.md").write_text(f"---\n{frontmatter}\n---\n", encoding="utf-8")
    return d


def test_types_generiques_du_plugin(tmp_path):
    idx = load_type_index(_repo(tmp_path))
    for t in ("skill", "skill-cas", "tool", "agent", "service"):
        assert idx[t]["capabilities"] == DEFAULT_CAPABILITIES, t
        assert idx[t]["source"] == "plugin"
    assert idx["projet"]["capabilities"] == ALL_CAPABILITIES


def test_type_metier_sans_champ_capabilities_a_tout(tmp_path):
    root = _repo(tmp_path)
    _dir(root, "services/achats/types/supplier")
    (root / "services/achats/types/supplier/REFERENCE.md").write_text(
        "---\ntype: supplier\nhorizon: permanent\n---\n", encoding="utf-8")
    idx = load_type_index(root)
    assert idx["supplier"]["capabilities"] == ALL_CAPABILITIES
    assert idx["supplier"]["source"] == "repo"


def test_depot_surcharge_le_plugin(tmp_path):
    root = _repo(tmp_path)
    _dir(root, "types/tool")
    (root / "types/tool/REFERENCE.md").write_text(
        "---\ntype: tool\ncapabilities: [memory, decisions, lifecycle, links]\n---\n", encoding="utf-8")
    assert load_type_index(root)["tool"]["capabilities"] == ["memory", "decisions", "lifecycle", "links"]


def test_type_inconnu_capacites_par_defaut(tmp_path):
    caps, connu = type_capabilities("inexistant", load_type_index(_repo(tmp_path)))
    assert caps == DEFAULT_CAPABILITIES and connu is False


def test_has_capability(tmp_path):
    idx = load_type_index(_repo(tmp_path))
    assert has_capability({"type": "projet"}, idx, "events")
    assert not has_capability({"type": "tool"}, idx, "events")
    assert not has_capability({}, idx, "links")


def test_type_de_l_en_tete_gagne(tmp_path):
    root = _repo(tmp_path, CE_RULES)
    d = _dir(root, "entreprise/tools/x", "type: projet")
    assert resolve_type(d, root) == {"type": "projet", "source": "frontmatter"}


def test_type_by_path(tmp_path):
    root = _repo(tmp_path, CE_RULES)
    d = _dir(root, "entreprise/tools/factures", "entite: factures")
    assert resolve_type(d, root) == {"type": "tool", "source": "type_by_path"}


def test_ordre_des_motifs(tmp_path):
    root = _repo(tmp_path, CE_RULES)
    d = _dir(root, "services/achats/skills/reassort/cas/conteneur")
    assert resolve_type(d, root)["type"] == "skill-cas"
    d2 = _dir(root, "services/amazon/ads/skills/observation")
    assert resolve_type(d2, root)["type"] == "skill"


def test_motif_sans_segment_initial(tmp_path):
    root = _repo(tmp_path, CE_RULES)
    d = _dir(root, "skills/racine")
    assert resolve_type(d, root) == {"type": None, "source": "claude"}


def test_sans_regle_choix_de_claude(tmp_path):
    root = _repo(tmp_path)
    d = _dir(root, "docs/notes", "entite: notes")
    assert resolve_type(d, root) == {"type": None, "source": "claude"}
```

- [ ] **Étape 2 : vérifier qu'ils échouent**

Lancer : `python3 -m pytest -q tests/test_subject_types.py`
Attendu : ÉCHEC avec `ModuleNotFoundError: No module named 'subject_lib'`.

- [ ] **Étape 3 : créer les six types génériques**

`types/skill/REFERENCE.md` :

```markdown
---
type: skill
parent_type: entity
horizon: permanent
capabilities: [memory, decisions, lifecycle]
name_pattern: "{nom du dossier du skill}"
---

# skill — mémoire d'un skill

Type générique livré par SOCLE (0.7.0). Un skill garde une mémoire bornée, ses discussions et ses décisions, et un état `actif` / `archived`. Pas d'événements externes ni de liens typés. Un dépôt peut surcharger ce type dans son propre `types/skill/`.
```

Les cinq autres fichiers suivent exactement ce gabarit, avec les valeurs ci-dessous.

| Fichier | `type` | `capabilities` | `name_pattern` | Phrase de titre |
|---|---|---|---|---|
| `types/skill-cas/REFERENCE.md` | `skill-cas` | `[memory, decisions, lifecycle]` | `"{nom du cas}"` | `# skill-cas — mémoire d'un cas d'usage d'un skill` |
| `types/tool/REFERENCE.md` | `tool` | `[memory, decisions, lifecycle]` | `"{nom du dossier de l'outil}"` | `# tool — mémoire d'un outil` |
| `types/agent/REFERENCE.md` | `agent` | `[memory, decisions, lifecycle]` | `"{nom de l'agent}"` | `# agent — mémoire d'un agent` |
| `types/service/REFERENCE.md` | `service` | `[memory, decisions, lifecycle]` | `"{nom du service}"` | `# service — mémoire d'un service` |
| `types/projet/REFERENCE.md` | `projet` | `[memory, decisions, lifecycle, events, links]` | `"{nom court du projet, kebab-case}"` | `# projet — mémoire d'un projet` |

Pour `projet`, la phrase descriptive devient : « Un projet a un cycle complet : mémoire bornée, discussions et décisions, état, événements et liens vers d'autres subjects. »

- [ ] **Étape 4 : implémenter `bin/subject_lib.py`**

```python
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
    for rule in config.get("type_by_path", []):
        if fnmatch(rel, rule["pattern"]):
            return {"type": rule["type"], "source": "type_by_path"}
    return {"type": None, "source": "claude"}
```

- [ ] **Étape 5 : vérifier que tout passe**

Lancer : `python3 -m pytest -q`
Attendu : tout vert (135 + 10 = 145).

- [ ] **Étape 6 : commit**

```bash
git add bin/subject_lib.py types/ tests/test_subject_types.py
git commit -m "feat(types): types génériques skill/tool/agent/service/projet + capacités par type"
```

---

### Tâche 3 : brancher le scanner, `list-subjects` et autolink sur `find_subjects`

**Fichiers :**
- Modifier : `bin/forge_scanner.py`
  - `find_subject_memory_files` (l. 76-98) ;
  - `detect_alerts` (l. 147-207) ;
  - `compute_metrics` (l. 209-270) ;
  - `regenerate_index` (l. 353-391) ;
  - imports (l. 35).
- Modifier : `bin/documente_engine.py` : `cmd_list_subjects` (l. 66-97) et import l. 32.
- Modifier : `bin/autolink_engine.py` : `_iter_subjects` (l. 145-148) et imports (l. 28).
- Créer : `tests/test_scanner_identite.py`

**Interfaces :**
- Consomme : `forge_lib.find_subjects`, `subject_lib.load_type_index`, `subject_lib.has_capability`.
- Produit : `forge_scanner.detect_identity_alerts(subjects, project_dir, type_index) -> list[dict]`. Chaque alerte est de la forme `{"type": "duplicate_name"|"unknown_type", "subject": str, "detail": str}`.

- [ ] **Étape 1 : écrire les tests qui échouent**

`tests/test_scanner_identite.py` :

```python
"""Scanner 0.7.0 : découverte par en-tête, homonymes, types inconnus, stagnation par capacité."""
import importlib
import json
import subprocess
import sys
from pathlib import Path

BIN = Path(__file__).resolve().parents[1] / "bin"
sys.path.insert(0, str(BIN))


def _memory(root, rel, frontmatter):
    d = root / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / "MEMORY.md").write_text(f"---\n{frontmatter}\n---\n\n## Quick\n\nx\n", encoding="utf-8")
    return d / "MEMORY.md"


def _scanner(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_FORGE_PROJECT_DIR", str(tmp_path))
    import forge_lib
    forge_lib._CONFIG_CACHE.clear()
    import forge_scanner
    return importlib.reload(forge_scanner)


def test_scanner_trouve_un_subject_hors_subjects(tmp_path, monkeypatch):
    m = _memory(tmp_path, "entreprise/tools/factures", "name: factures\ntype: tool\nforging_state: actif")
    sc = _scanner(tmp_path, monkeypatch)
    assert [p for p, _ in sc.find_subject_memory_files()] == [m]


def test_homonymes_et_type_inconnu(tmp_path, monkeypatch):
    _memory(tmp_path, "a/x", "name: dup\ntype: tool\nforging_state: actif")
    _memory(tmp_path, "b/x", "name: dup\ntype: tool\nforging_state: actif")
    _memory(tmp_path, "c/x", "name: seul\ntype: bizarre\nforging_state: actif")
    sc = _scanner(tmp_path, monkeypatch)
    from subject_lib import load_type_index
    subjects = sc.find_subject_memory_files()
    alerts = sc.detect_identity_alerts(subjects, tmp_path, load_type_index(tmp_path))
    types = sorted(a["type"] for a in alerts)
    assert types == ["duplicate_name", "unknown_type"]
    dup = next(a for a in alerts if a["type"] == "duplicate_name")
    assert dup["subject"] == "dup" and "a/x" in dup["detail"] and "b/x" in dup["detail"]


def test_pas_de_stagnation_sans_capacite_events(tmp_path, monkeypatch):
    vieux = "created_at: 2020-01-01"
    _memory(tmp_path, "t/x", f"name: t\ntype: tool\nforging_state: actif\n{vieux}")
    _memory(tmp_path, "p/x", f"name: p\ntype: projet\nforging_state: actif\n{vieux}")
    sc = _scanner(tmp_path, monkeypatch)
    subjects = sc.find_subject_memory_files()
    stagn = [a["subject"] for a in sc.detect_alerts(subjects) if a["type"] == "stagnation"]
    assert stagn == ["p/x/MEMORY.md"]
    assert sc.compute_metrics(subjects)["stagnant"] == 1


def test_index_regroupe_par_type(tmp_path, monkeypatch):
    _memory(tmp_path, "t/x", "name: t\ntype: tool\nforging_state: actif")
    _memory(tmp_path, "p/x", "name: p\ntype: projet\nforging_state: actif")
    sc = _scanner(tmp_path, monkeypatch)
    sc.regenerate_index(sc.find_subject_memory_files())
    text = (tmp_path / "SUBJECTS-INDEX.md").read_text(encoding="utf-8")
    assert "### projet (1)" in text and "### tool (1)" in text


def test_list_subjects_hors_subjects(tmp_path):
    _memory(tmp_path, "entreprise/tools/factures", "name: factures\ntype: tool\nforging_state: actif")
    out = subprocess.run(
        [sys.executable, str(BIN / "documente_engine.py"), "list-subjects"],
        capture_output=True, text=True, cwd=tmp_path,
        env={"CLAUDE_FORGE_PROJECT_DIR": str(tmp_path), "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin"},
    )
    res = json.loads(out.stdout)
    assert [s["path"] for s in res["subjects"]] == ["entreprise/tools/factures"]


def test_autolink_itere_hors_subjects(tmp_path):
    m = _memory(tmp_path, "entreprise/projets/tresorerie", "name: tresorerie\ntype: projet\nforging_state: actif")
    import autolink_engine
    assert list(autolink_engine._iter_subjects(tmp_path)) == [m]
```

Note : le chemin rendu par `detect_alerts` est relatif au MEMORY.md (`rel_path = path.relative_to(PROJECT_DIR)`, code existant). D'où `"p/x/MEMORY.md"` : on ne modifie pas ce format.

- [ ] **Étape 2 : vérifier qu'ils échouent**

Lancer : `python3 -m pytest -q tests/test_scanner_identite.py`
Attendu : ÉCHEC. Les tests « hors subjects » rendent une liste vide, `detect_identity_alerts` n'existe pas, et la stagnation compte aussi le `tool`.

- [ ] **Étape 3 : implémenter dans `bin/forge_scanner.py`**

Imports : ajouter `find_subjects` à l'import `from forge_lib import (...)`, puis :

```python
from subject_lib import has_capability, load_type_index
```

Remplacer `find_subject_memory_files` par :

```python
def find_subject_memory_files():
    """Délègue à forge_lib.find_subjects : une seule découverte pour tout SOCLE (0.7.0)."""
    return find_subjects(PROJECT_DIR)


_TYPE_INDEX = None


def _type_index():
    global _TYPE_INDEX
    if _TYPE_INDEX is None:
        _TYPE_INDEX = load_type_index(PROJECT_DIR)
    return _TYPE_INDEX


def detect_identity_alerts(subjects, project_dir, type_index):
    """Homonymes (même name : liens non résolus) et types sans REFERENCE.md."""
    alerts = []
    by_name = {}
    for path, fm in subjects:
        rel = str(path.parent.relative_to(project_dir))
        by_name.setdefault(str(fm.get("name") or path.parent.name), []).append(rel)
        t = fm.get("type")
        if not t or str(t) not in type_index:
            alerts.append({
                "type": "unknown_type",
                "subject": rel,
                "detail": f"type « {t or '—'} » sans REFERENCE.md, capacités par défaut",
            })
    for name, rels in sorted(by_name.items()):
        if len(rels) > 1:
            alerts.append({
                "type": "duplicate_name",
                "subject": name,
                "detail": ", ".join(sorted(rels)) + " : liens vers ce nom non résolus",
            })
    return alerts
```

Dans `detect_alerts`, après `alerts.extend(detect_overdue_decisions(subjects))`, ajouter :

```python
    alerts.extend(detect_identity_alerts(subjects, PROJECT_DIR, _type_index()))
```

et remplacer `if state == "actif":`, dans la boucle de stagnation, par :

```python
        if state == "actif" and has_capability(fm, _type_index(), "events"):
```

Faire le même remplacement dans `compute_metrics`, sur la ligne `# Stagnation : subject actif ...` suivie de `if state == "actif":`.

Dans `regenerate_index`, remplacer la boucle `for path, fm in sorted(items, key=lambda x: str(x[0])):` et son corps par :

```python
        by_type = {}
        for path, fm in items:
            by_type.setdefault(str(fm.get("type") or "?"), []).append((path, fm))
        for stype in sorted(by_type):
            group = by_type[stype]
            lines.append(f"### {stype} ({len(group)})")
            lines.append("")
            for path, fm in sorted(group, key=lambda x: str(x[0])):
                name = fm.get("name") or path.parent.name
                rel = path.parent.relative_to(PROJECT_DIR)
                links = fm.get("linked_subjects") or []
                link_preview = ", ".join(str(l) for l in links[:3])
                if len(links) > 3:
                    link_preview += f" (+{len(links) - 3})"
                lines.append(f"- **{name}** — `{rel}/`")
                if link_preview:
                    lines.append(f"  - liens : {link_preview}")
            lines.append("")
```

Puis supprimer l'ancien `lines.append("")` de fin de boucle d'état, désormais émis par groupe.

- [ ] **Étape 4 : brancher `list-subjects` et autolink**

`bin/documente_engine.py`, import l. 32 :

```python
from forge_lib import find_subjects, get_project_dir, load_forge_config, parse_frontmatter
```

Remplacer `cmd_list_subjects` par :

```python
def cmd_list_subjects(args):
    """Liste tous les subjects du dépôt : MEMORY.md avec forging_state, où qu'il soit (0.7.0)."""
    project_dir = get_project_dir()
    subjects = []
    for memory_md, fm in find_subjects(project_dir):
        last_event = fm.get("last_event")
        last_event_date = last_event.get("date") if isinstance(last_event, dict) else None
        subjects.append({
            "path": str(memory_md.parent.relative_to(project_dir)),
            "forging_state": fm.get("forging_state"),
            "type": fm.get("type"),
            "last_event_date": last_event_date,
        })
    return _ok(subjects=sorted(subjects, key=lambda s: s["path"]))
```

`bin/autolink_engine.py` : ajouter `find_subjects,` à l'import `from forge_lib import (...)`, puis remplacer `_iter_subjects` par :

```python
def _iter_subjects(project_dir):
    """Itère sur les MEMORY.md de tous les subjects, où qu'ils soient (0.7.0)."""
    for memory, _fm in find_subjects(project_dir):
        yield memory
```

- [ ] **Étape 5 : vérifier que tout passe**

Lancer : `python3 -m pytest -q`
Attendu : tout vert (145 + 6 = 151). Si `test_autolink.py` échoue parce qu'un de ses dépôts de test n'a pas de `forging_state` dans ses MEMORY.md, ajouter `forging_state: actif` aux en-têtes de ces fixtures de test. Ne pas modifier le code.

- [ ] **Étape 6 : commit**

```bash
git add bin/forge_scanner.py bin/documente_engine.py bin/autolink_engine.py tests/
git commit -m "feat(scanner): découverte unique par en-tête, alertes homonymes/type inconnu, index par type"
```

---

### Tâche 4 : `resolve_link` par `name`, puis par dossier, sans homonymes

**Fichiers :**
- Modifier : `bin/forge_engine.py` : `_candidate_subject_roots` (l. 228-245, supprimée) et `resolve_link` (l. 248-311) ; ajouter `find_subjects` à l'import `from forge_lib import (...)` (l. 43).
- Créer : `tests/test_resolve_link.py`

**Interfaces :**
- Consomme : `forge_lib.find_subjects`.
- Produit : `resolve_link(link: str, current_subject_path: Path) -> Path | None`. La signature ne change pas ; `current_subject_path` est gardé pour la compatibilité.

- [ ] **Étape 1 : écrire les tests qui échouent**

`tests/test_resolve_link.py` :

```python
"""resolve_link 0.7.0 : par name d'en-tête, puis par dossier ; homonymes = None."""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))


def _memory(root, rel, frontmatter):
    d = root / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / "MEMORY.md").write_text(f"---\n{frontmatter}\n---\n", encoding="utf-8")
    return d / "MEMORY.md"


def _engine(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_FORGE_PROJECT_DIR", str(tmp_path))
    import forge_lib
    forge_lib._CONFIG_CACHE.clear()
    import forge_engine
    return importlib.reload(forge_engine)


def test_par_name_hors_subjects(tmp_path, monkeypatch):
    cible = _memory(tmp_path, "entreprise/projets/treso", "name: tresorerie\ntype: projet\nforging_state: actif")
    src = _memory(tmp_path, "services/achats/subjects/order-1", "name: order-1\ntype: supplier-order\nforging_state: actif")
    eng = _engine(tmp_path, monkeypatch)
    assert eng.resolve_link("projet:tresorerie", src.parent) == cible
    assert eng.resolve_link("tresorerie", src.parent) == cible


def test_type_verifie_sur_le_name(tmp_path, monkeypatch):
    _memory(tmp_path, "a/weifang", "name: weifang\ntype: tool\nforging_state: actif")
    eng = _engine(tmp_path, monkeypatch)
    assert eng.resolve_link("supplier:weifang", tmp_path) is None


def test_liens_historiques_par_dossier(tmp_path, monkeypatch):
    sw = _memory(tmp_path, "services/achats/subjects/supplier-weifang", "type: supplier\nforging_state: actif")
    o = _memory(tmp_path, "services/achats/subjects/order-398", "type: supplier-order\nforging_state: actif")
    eng = _engine(tmp_path, monkeypatch)
    assert eng.resolve_link("supplier:weifang", o.parent) == sw
    assert eng.resolve_link("order-398", sw.parent) == o


def test_homonymes_refuses(tmp_path, monkeypatch):
    _memory(tmp_path, "a/x", "name: dup\ntype: tool\nforging_state: actif")
    _memory(tmp_path, "b/x", "name: dup\ntype: tool\nforging_state: actif")
    eng = _engine(tmp_path, monkeypatch)
    assert eng.resolve_link("dup", tmp_path) is None


def test_ancien_format_jamais_cible(tmp_path, monkeypatch):
    _memory(tmp_path, "a/vieux", "name: vieux\ntype: tool")
    eng = _engine(tmp_path, monkeypatch)
    assert eng.resolve_link("vieux", tmp_path) is None
```

- [ ] **Étape 2 : vérifier qu'ils échouent**

Lancer : `python3 -m pytest -q tests/test_resolve_link.py`
Attendu : ÉCHEC. `test_par_name_hors_subjects` rend `None`, et `test_homonymes_refuses` rend un des deux chemins.

- [ ] **Étape 3 : implémenter**

Supprimer `_candidate_subject_roots`. Vérifier d'abord qu'elle n'a pas d'autre appelant : `grep -n "_candidate_subject_roots" bin/*.py` ne doit plus rien rendre après la modification. Remplacer `resolve_link` par :

```python
_SUBJECTS_CACHE = None


def _all_subjects():
    """find_subjects une fois par processus : resolve_link est appelé par lien."""
    global _SUBJECTS_CACHE
    if _SUBJECTS_CACHE is None:
        _SUBJECTS_CACHE = find_subjects(PROJECT_DIR)
    return _SUBJECTS_CACHE


def _unique(paths):
    paths = list(dict.fromkeys(paths))
    return paths[0] if len(paths) == 1 else None


def resolve_link(link: str, current_subject_path: Path) -> Path | None:
    """Résout un linked_subject vers le MEMORY.md de sa cible (0.7.0).

    1. par `name:` de l'en-tête (type vérifié pour un lien `<type>:<name>`) ;
    2. sinon par nom de dossier : `<slug>`, `<type>-<name>`, ou `<name>` avec
       vérification du type (formes historiques, toujours valides).
    Deux cibles à la même étape → None : les homonymes sont signalés par le
    scanner (alerte duplicate_name), jamais résolus au hasard.
    `current_subject_path` est gardé pour la compatibilité de signature.
    """
    if not isinstance(link, str) or not link.strip():
        return None
    link = link.strip()
    type_part, name_part = None, link
    if ":" in link:
        type_part, _, name_part = link.partition(":")
        type_part, name_part = type_part.strip(), name_part.strip()
    subjects = _all_subjects()

    def type_ok(fm):
        return type_part is None or str(fm.get("type")) == type_part

    by_name = [m for m, fm in subjects if str(fm.get("name") or "") == name_part and type_ok(fm)]
    if by_name:
        return _unique(by_name)

    if type_part is None:
        by_folder = [m for m, fm in subjects if m.parent.name == link]
    else:
        by_folder = [
            m for m, fm in subjects
            if m.parent.name == f"{type_part}-{name_part}"
            or (m.parent.name == name_part and type_ok(fm))
        ]
    return _unique(by_folder) if by_folder else None
```

- [ ] **Étape 4 : vérifier que tout passe**

Lancer : `python3 -m pytest -q`
Attendu : tout vert (151 + 5 = 156).

- [ ] **Étape 5 : commit**

```bash
git add bin/forge_engine.py tests/test_resolve_link.py
git commit -m "feat(engine): resolve_link par name d'en-tête puis dossier, homonymes refusés"
```

---

### Tâche 5 : conversion d'un MEMORY.md, commande `convert`

**Fichiers :**
- Créer : `bin/convert_lib.py`
- Modifier : `bin/documente_engine.py` : `cmd_convert`, parser et `handlers`.
- Créer : `tests/test_convert.py`

**Interfaces :**
- Produit :
  - `convert_lib.CANONICAL_SECTIONS = ["Quick", "Doctrine en vigueur", "Décisions actives", "Règles apprises", "Détails", "Liens"]` ;
  - `convert_lib.convert_memory_text(text: str, *, name: str, type_name: str, today: str) -> str` ;
  - `convert_lib.new_memory_text(*, name: str, type_name: str, today: str) -> str` ;
  - la commande `forge documente convert <path> --type T [--name N] [--dry-run]`, qui rend `{"ok", "action": "created"|"converted"|"noop", "path", "type", "name", "size_kb_after"}`.

- [ ] **Étape 1 : écrire les tests qui échouent**

`tests/test_convert.py` :

````python
"""Conversion au format unique (design 2026-10-10 §3) : rien n'est perdu."""
import json
import re
import subprocess
import sys
from pathlib import Path

BIN = Path(__file__).resolve().parents[1] / "bin"
sys.path.insert(0, str(BIN))
from convert_lib import convert_memory_text, new_memory_text  # noqa: E402

ANCIEN = """---
entite: entreprise/tools/modern-sky
type: tool
derniere_maj: 2026-10-04
---

# Memory — modern-sky

## Doctrine en vigueur

### Git

- toujours yarn

## Décisions actives

1. D1 → decisions/a.yaml

## Décisions remplacées

- D0 (2026-01-01)

## Discussions ouvertes

```bash
## pas une section
```
"""


def _contenu(text):
    """Lignes non vides, sans marqueurs de titre : ce qui ne doit jamais disparaître."""
    return [re.sub(r"^#+\s*", "", l).strip() for l in text.splitlines() if l.strip() and l.strip() != "---"]


def _titres(text):
    out, fence = [], False
    for l in text.splitlines():
        if l.lstrip().startswith("```"):
            fence = not fence
        elif not fence and l.startswith("## "):
            out.append(l)
    return out


def test_rien_n_est_perdu():
    out = convert_memory_text(ANCIEN, name="modern-sky", type_name="tool", today="2026-10-11")
    for ligne in _contenu(ANCIEN):
        assert ligne in _contenu(out), ligne


def test_en_tete_complete_sans_ecraser():
    out = convert_memory_text(ANCIEN, name="modern-sky", type_name="projet", today="2026-10-11")
    fm = out.split("---")[1]
    assert "entite: entreprise/tools/modern-sky" in fm
    assert "name: modern-sky" in fm
    assert "type: tool" in fm and "type: projet" not in fm
    assert "forging_state: actif" in fm
    assert "derniere_maj: 2026-10-04" in fm


def test_sections_dans_l_ordre_canonique():
    out = convert_memory_text(ANCIEN, name="modern-sky", type_name="tool", today="2026-10-11")
    assert _titres(out) == ["## Quick", "## Doctrine en vigueur", "## Décisions actives", "## Détails"]
    details = out.split("## Détails", 1)[1]
    assert "### Décisions remplacées" in details and "### Discussions ouvertes" in details


def test_titres_internes_descendus_d_un_niveau():
    src = ANCIEN.replace("## Discussions ouvertes", "## Divers\n\n### Sous-titre")
    out = convert_memory_text(src, name="m", type_name="tool", today="2026-10-11")
    assert "#### Sous-titre" in out.split("## Détails", 1)[1]


def test_titre_dans_bloc_de_code_ignore():
    out = convert_memory_text(ANCIEN, name="m", type_name="tool", today="2026-10-11")
    assert "## pas une section" in out
    assert "## pas une section" not in _titres(out)


def test_bloc_okf_conserve_en_fin():
    src = ANCIEN + "\n<!-- okf-links:start -->\n## Liens\n\n- [[x]]\n<!-- okf-links:end -->\n"
    out = convert_memory_text(src, name="m", type_name="tool", today="2026-10-11")
    assert out.rstrip().endswith("<!-- okf-links:end -->")
    assert out.count("<!-- okf-links:start -->") == 1
    assert _titres(out)[-1] == "## Liens"


def test_derniere_maj_ajoutee_si_absente():
    src = ANCIEN.replace("derniere_maj: 2026-10-04\n", "")
    out = convert_memory_text(src, name="m", type_name="tool", today="2026-10-11")
    assert "derniere_maj: 2026-10-11" in out


def test_sans_frontmatter():
    out = convert_memory_text("# Titre\n\n## Notes\n\n- a\n", name="m", type_name="tool", today="2026-10-11")
    assert out.startswith("---\nname: m\ntype: tool\nforging_state: actif\nderniere_maj: 2026-10-11\n---\n")
    assert "### Notes" in out


def test_nouveau_memory():
    out = new_memory_text(name="treso", type_name="projet", today="2026-10-11")
    assert out == "---\nname: treso\ntype: projet\nforging_state: actif\nderniere_maj: 2026-10-11\n---\n\n# treso\n\n## Quick\n"


def _run(*args, project):
    out = subprocess.run([sys.executable, str(BIN / "documente_engine.py"), *args],
                         capture_output=True, text=True, cwd=project,
                         env={"CLAUDE_FORGE_PROJECT_DIR": str(project), "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin"})
    return json.loads(out.stdout)


def test_convert_ecrit_puis_noop(tmp_path):
    d = tmp_path / "entreprise/tools/modern-sky"
    d.mkdir(parents=True)
    (d / "MEMORY.md").write_text(ANCIEN, encoding="utf-8")
    r1 = _run("convert", "entreprise/tools/modern-sky", "--type", "tool", project=tmp_path)
    assert r1["ok"] and r1["action"] == "converted" and r1["name"] == "modern-sky"
    avant = (d / "MEMORY.md").read_text(encoding="utf-8")
    r2 = _run("convert", "entreprise/tools/modern-sky", "--type", "tool", project=tmp_path)
    assert r2["action"] == "noop"
    assert (d / "MEMORY.md").read_text(encoding="utf-8") == avant


def test_convert_deja_subject_noop(tmp_path):
    d = tmp_path / "x"
    d.mkdir()
    texte = "---\nname: x\ntype: tool\nforging_state: actif\n---\n\n## Quick\n"
    (d / "MEMORY.md").write_text(texte, encoding="utf-8")
    assert _run("convert", "x", "--type", "projet", project=tmp_path)["action"] == "noop"
    assert (d / "MEMORY.md").read_text(encoding="utf-8") == texte


def test_convert_cree_si_absent(tmp_path):
    r = _run("convert", "entreprise/projets/treso", "--type", "projet", "--name", "tresorerie", project=tmp_path)
    assert r["action"] == "created"
    assert "name: tresorerie" in (tmp_path / "entreprise/projets/treso/MEMORY.md").read_text(encoding="utf-8")


def test_convert_dry_run_n_ecrit_rien(tmp_path):
    d = tmp_path / "x"
    d.mkdir()
    (d / "MEMORY.md").write_text(ANCIEN, encoding="utf-8")
    r = _run("convert", "x", "--type", "tool", "--dry-run", project=tmp_path)
    assert r["action"] == "converted" and r["dry_run"] is True
    assert (d / "MEMORY.md").read_text(encoding="utf-8") == ANCIEN
````

- [ ] **Étape 2 : vérifier qu'ils échouent**

Lancer : `python3 -m pytest -q tests/test_convert.py`
Attendu : ÉCHEC avec `ModuleNotFoundError: No module named 'convert_lib'`.

- [ ] **Étape 3 : implémenter `bin/convert_lib.py`**

```python
#!/usr/bin/env python3
"""convert_lib.py — conversion d'un MEMORY.md au format unique (SOCLE 0.7.0).

Design 2026-10-10 §3. Fonctions pures texte → texte. Règle absolue : aucune
ligne de contenu n'est supprimée. Une section sans place dans le format unique
va dans `## Détails` sous `### <titre>`, ses titres internes descendent d'un
niveau. Le bloc okf-links est recopié tel quel, en fin de fichier.
"""

import re

CANONICAL_SECTIONS = ["Quick", "Doctrine en vigueur", "Décisions actives", "Règles apprises", "Détails", "Liens"]
OKF_START = "<!-- okf-links:start -->"
_FM_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)


def _frontmatter(text):
    m = _FM_RE.match(text)
    if not m:
        return [], text
    return m.group(1).split("\n"), text[m.end():]


def _has_key(fm_lines, key):
    return any(re.match(rf"^{re.escape(key)}\s*:", l) for l in fm_lines)


def _split_sections(body):
    """(préambule, [(titre, lignes)]). Ignore les `## ` dans les blocs de code."""
    preamble, sections, current, in_fence = [], [], None, False
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            current = (line[3:].strip(), [])
            sections.append(current)
            continue
        (current[1] if current else preamble).append(line)
    return preamble, sections


def _demote(lines):
    out, in_fence = [], False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and re.match(r"^#{1,5} ", line):
            line = "#" + line
        out.append(line)
    return out


def _trim(lines):
    while lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    return lines


def _header(fm_lines, *, name, type_name, today):
    fm = [l for l in fm_lines]
    for key, value in (("name", name), ("type", type_name), ("forging_state", "actif"), ("derniere_maj", today)):
        if not _has_key(fm, key):
            fm.append(f"{key}: {value}")
    return "---\n" + "\n".join(fm) + "\n---\n"


def new_memory_text(*, name, type_name, today):
    """MEMORY.md minimal d'un nouveau subject ; /documente rédige le Quick ensuite."""
    return _header([], name=name, type_name=type_name, today=today) + f"\n# {name}\n\n## Quick\n"


def convert_memory_text(text, *, name, type_name, today):
    fm_lines, body = _frontmatter(text)
    okf_tail = ""
    idx = body.find(OKF_START)
    if idx >= 0:
        body, okf_tail = body[:idx], body[idx:]
    preamble, sections = _split_sections(body)

    canon = {c.lower(): c for c in CANONICAL_SECTIONS}
    kept = {c: [] for c in CANONICAL_SECTIONS}
    present = set()
    extras = []
    for title, lines in sections:
        key = canon.get(title.lower())
        if key and not (key == "Liens" and okf_tail):
            present.add(key)
            kept[key].extend(_trim(lines) + [""])
        else:
            extras.extend([f"### {title}", ""] + _trim(_demote(lines)) + [""])

    out = [_header(fm_lines, name=name, type_name=type_name, today=today).rstrip("\n")]
    pre = _trim(preamble)
    if pre:
        out += [""] + pre
    for key in CANONICAL_SECTIONS:
        content = _trim(kept[key])
        if key == "Détails":
            if key in present or extras:
                details = content + ([""] if content and extras else []) + _trim(extras)
                out += ["", f"## {key}", ""] + details
        elif key == "Quick" or key in present:
            out += ["", f"## {key}"] + ([""] + content if content else [])
    text_out = "\n".join(out).rstrip("\n") + "\n"
    if okf_tail:
        text_out += "\n" + okf_tail.rstrip("\n") + "\n"
    return text_out
```

Note : `_header` n'écrit le `type` que s'il est absent. Le type d'en-tête n'est jamais remplacé, conformément au design §2.

- [ ] **Étape 4 : implémenter la commande dans `bin/documente_engine.py`**

Import, en tête de fichier après l'import de `documente_lib` :

```python
from convert_lib import convert_memory_text, new_memory_text
```

Fonction, à placer après `cmd_patch_section` :

```python
def cmd_convert(args):
    """Convertit (ou crée) le MEMORY.md d'un dossier au format unique (0.7.0).

    Déjà subject (forging_state présent) → noop, rien n'est écrit. Absent →
    MEMORY.md minimal. Ancien format → en-tête complété, sections rangées,
    rien de supprimé (convert_lib).
    """
    project_dir = get_project_dir()
    p = Path(args.path)
    if not p.is_absolute():
        p = project_dir / args.path
    md = p / "MEMORY.md"
    name = args.name or p.name
    today = _dt.date.today().isoformat()
    rel = str(p.relative_to(project_dir)) if p.is_relative_to(project_dir) else str(p)
    if md.is_file():
        old = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(md) or {}
        if "forging_state" in fm:
            return _ok(action="noop", path=rel, type=fm.get("type"), name=fm.get("name") or name)
        new = convert_memory_text(old, name=name, type_name=args.type, today=today)
        action = "converted"
        type_used = fm.get("type") or args.type
    else:
        new = new_memory_text(name=name, type_name=args.type, today=today)
        action = "created"
        type_used = args.type
    size_kb = round(len(new.encode("utf-8")) / 1024, 1)
    if args.dry_run:
        return _ok(action=action, dry_run=True, path=rel, type=type_used, name=name, size_kb_after=size_kb)
    p.mkdir(parents=True, exist_ok=True)
    md.write_text(new, encoding="utf-8")
    return _ok(action=action, dry_run=False, path=rel, type=type_used, name=name, size_kb_after=size_kb)
```

Parser, dans `main()`, avant `args = parser.parse_args()` :

```python
    p_conv = sub.add_parser("convert", help="Convertit ou crée le MEMORY.md d'un dossier au format unique (0.7.0)")
    p_conv.add_argument("path")
    p_conv.add_argument("--type", required=True, help="type si l'en-tête n'en a pas")
    p_conv.add_argument("--name", default=None, help="name si l'en-tête n'en a pas (défaut : nom du dossier)")
    p_conv.add_argument("--dry-run", action="store_true")
```

Puis ajouter `"convert": cmd_convert,` dans `handlers`.

- [ ] **Étape 5 : vérifier que tout passe**

Lancer : `python3 -m pytest -q`
Attendu : tout vert (156 + 13 = 169).

- [ ] **Étape 6 : commit**

```bash
git add bin/convert_lib.py bin/documente_engine.py tests/test_convert.py
git commit -m "feat(documente): convert — ancien MEMORY.md au format unique, sans perte"
```

---

### Tâche 6 : `prepare` sans aiguillage par chemin, et `forge migrate --dry-run`

**Fichiers :**
- Modifier : `bin/documente_engine.py` :
  - `cmd_prepare` (l. 114-178) ;
  - `_detect_service_root` (l. 101-111) : supprimée si plus aucun appelant ;
  - `cmd_migrate`, parser et `handlers`.
- Modifier : `bin/forge` : case `migrate` et ligne d'aide.
- Modifier : `tests/test_documente_engine.py` : classe `TestPrepare` (l. 426-450).
- Créer : `tests/test_prepare_migrate.py`

**Interfaces :**
- Consomme :
  - `subject_lib.resolve_type`, `subject_lib.load_type_index`, `subject_lib.type_capabilities` et `DEFAULT_CAPABILITIES` (tâche 2) ;
  - `forge_lib.iter_memory_files` (tâche 1).
- Produit :
  - `prepare` rend `{"ok", "path", "is_subject", "subject_exists", "needs_conversion", "needs_creation", "type", "type_source", "type_known", "capabilities", "known_types", "name_pattern", "default_name", "current_frontmatter"}` ;
  - `migrate --dry-run` rend `{"ok", "pending": [{"path", "type", "type_source"}], "total", "by_source"}`.

- [ ] **Étape 1 : écrire les tests qui échouent**

`tests/test_prepare_migrate.py` :

```python
"""prepare 0.7.0 (subject = en-tête) et forge migrate --dry-run."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
sys.path.insert(0, str(BIN))
from forge_lib import find_subjects, iter_memory_files  # noqa: E402

RULES = 'type_by_path:\n  - {pattern: "*/tools/*", type: tool}\n'


def _run(*args, project, via_forge=False):
    cmd = ["bash", str(BIN / "forge"), *args] if via_forge else [sys.executable, str(BIN / "documente_engine.py"), *args]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=project,
                         env={"CLAUDE_FORGE_PROJECT_DIR": str(project), "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin"})
    return json.loads(out.stdout)


def _repo(tmp_path):
    (tmp_path / ".forge.yaml").write_text(RULES, encoding="utf-8")
    for rel, fm in (("entreprise/tools/factures", "entite: factures"),
                    ("docs/notes", "entite: notes"),
                    ("services/achats/subjects/order-1", "name: order-1\ntype: projet\nforging_state: actif")):
        d = tmp_path / rel
        d.mkdir(parents=True)
        (d / "MEMORY.md").write_text(f"---\n{fm}\n---\n", encoding="utf-8")
    return tmp_path


def test_prepare_subject(tmp_path):
    r = _run("prepare", "services/achats/subjects/order-1", project=_repo(tmp_path))
    assert r["is_subject"] and not r["needs_conversion"] and not r["needs_creation"]
    assert r["type"] == "projet" and r["type_source"] == "frontmatter"
    assert r["capabilities"] == ["memory", "decisions", "lifecycle", "events", "links"]
    assert "is_subject_pool" not in r and "recommended_workflow" not in r


def test_prepare_ancien_format_hors_subjects(tmp_path):
    r = _run("prepare", "entreprise/tools/factures", project=_repo(tmp_path))
    assert not r["is_subject"] and r["needs_conversion"]
    assert r["type"] == "tool" and r["type_source"] == "type_by_path"
    assert r["capabilities"] == ["memory", "decisions", "lifecycle"]
    assert r["default_name"] == "factures"


def test_prepare_type_a_choisir(tmp_path):
    r = _run("prepare", "docs/notes", project=_repo(tmp_path))
    assert r["type"] is None and r["type_source"] == "claude"
    assert "tool" in r["known_types"] and "projet" in r["known_types"]


def test_prepare_dossier_neuf(tmp_path):
    r = _run("prepare", "entreprise/projets/neuf", project=_repo(tmp_path))
    assert r["needs_creation"] and not r["subject_exists"]


def test_migrate_exige_dry_run(tmp_path):
    r = _run("migrate", project=_repo(tmp_path), via_forge=True)
    assert not r["ok"] and r["code"] == "dry_run_required"


def test_migrate_liste_sans_ecrire(tmp_path):
    root = _repo(tmp_path)
    avant = {p: p.read_text(encoding="utf-8") for p in iter_memory_files(root)}
    r = _run("migrate", "--dry-run", project=root, via_forge=True)
    assert r["ok"] and r["total"] == 2
    assert {x["path"]: x["type"] for x in r["pending"]} == {"docs/notes": None, "entreprise/tools/factures": "tool"}
    assert r["by_source"] == {"claude": 1, "type_by_path": 1}
    assert {p: p.read_text(encoding="utf-8") for p in iter_memory_files(root)} == avant
    # cohérence : à convertir + subjects = tous les MEMORY.md
    assert r["total"] + len(find_subjects(root)) == len(avant)
```

Dans `tests/test_documente_engine.py`, remplacer la classe `TestPrepare` par :

```python
class TestPrepare(unittest.TestCase):

    def test_existing_subject(self):
        repo_root = _consumer_root()
        result = run_engine("prepare", "services/achats/subjects/order-398", cwd=str(repo_root))
        self.assertTrue(result["ok"])
        self.assertTrue(result["is_subject"])
        self.assertTrue(result["subject_exists"])
        self.assertIn("type", result)
        self.assertIn("current_frontmatter", result)
        self.assertFalse(result["needs_creation"])

    def test_nonexistent_subject(self):
        repo_root = _consumer_root()
        result = run_engine("prepare", "services/achats/subjects/order-99999", cwd=str(repo_root))
        self.assertTrue(result["ok"])
        self.assertFalse(result["is_subject"])
        self.assertTrue(result["needs_creation"])

    def test_entity_path_reports_conversion_state(self):
        repo_root = _consumer_root()
        result = run_engine("prepare", "entreprise/config", cwd=str(repo_root))
        self.assertTrue(result["ok"])
        self.assertIn("needs_conversion", result)
        self.assertIn("capabilities", result)
```

- [ ] **Étape 2 : vérifier qu'ils échouent**

Lancer : `python3 -m pytest -q tests/test_prepare_migrate.py`
Attendu : ÉCHEC. Il manque `KeyError: 'is_subject'`, et `forge: sous-commande inconnue 'migrate'` rend un JSON invalide.

- [ ] **Étape 3 : réécrire `cmd_prepare` et ajouter `cmd_migrate`**

Import en tête de `bin/documente_engine.py` :

```python
from forge_lib import find_subjects, get_project_dir, iter_memory_files, load_forge_config, parse_frontmatter
from subject_lib import DEFAULT_CAPABILITIES, load_type_index, resolve_type, type_capabilities
```

Remplacer `cmd_prepare` par :

```python
def cmd_prepare(args):
    """Phase A (0.7.0) : un dossier est un subject si son MEMORY.md porte forging_state.

    Plus d'aiguillage par chemin. Rend l'état (subject, à convertir, à créer),
    le type (en-tête > type_by_path > choix de Claude) et ses capacités, qui
    disent quelles phases de /documente s'appliquent.
    """
    project_dir = get_project_dir()
    p = Path(args.path)
    if not p.is_absolute():
        p = project_dir / args.path
    rel_path = str(p.relative_to(project_dir)) if p.is_relative_to(project_dir) else str(p)
    memory_md = p / "MEMORY.md"
    exists = memory_md.is_file()
    fm = parse_frontmatter(memory_md) if exists else None
    is_subject = bool(fm) and "forging_state" in fm
    rt = resolve_type(p, project_dir)
    type_index = load_type_index(project_dir)
    if rt["type"]:
        caps, known = type_capabilities(rt["type"], type_index)
    else:
        caps, known = list(DEFAULT_CAPABILITIES), False
    return _ok(
        path=rel_path,
        is_subject=is_subject,
        subject_exists=exists,
        needs_conversion=exists and not is_subject,
        needs_creation=not exists,
        type=rt["type"],
        type_source=rt["source"],
        type_known=known,
        capabilities=caps,
        known_types=sorted(type_index),
        name_pattern=(type_index.get(rt["type"]) or {}).get("name_pattern") if rt["type"] else None,
        default_name=p.name,
        current_frontmatter=fm,
    )


def cmd_migrate(args):
    """Liste les MEMORY.md à l'ancien format et le type que chacun recevrait.

    Lecture seule : il n'y a pas de conversion en masse (design 2026-10-10 §3),
    /documente convertit au fil de l'eau.
    """
    if not args.dry_run:
        return _err(
            "forge migrate n'écrit rien : relancer avec --dry-run. "
            "La conversion se fait au fil de l'eau par /documente.",
            code="dry_run_required",
        )
    project_dir = get_project_dir()
    config = load_forge_config(project_dir)
    pending = []
    for memory in iter_memory_files(project_dir):
        fm = parse_frontmatter(memory)
        if fm and "forging_state" in fm:
            continue
        rt = resolve_type(memory.parent, project_dir, config)
        pending.append({
            "path": str(memory.parent.relative_to(project_dir)),
            "type": rt["type"],
            "type_source": rt["source"],
        })
    by_source = {}
    for item in pending:
        by_source[item["type_source"]] = by_source.get(item["type_source"], 0) + 1
    return _ok(pending=pending, total=len(pending), by_source=by_source)
```

Supprimer `_detect_service_root`. Lancer `grep -n "_detect_service_root" bin/*.py` pour vérifier qu'il n'en reste aucune trace.

Parser :

```python
    p_mig = sub.add_parser("migrate", help="Liste les MEMORY.md à convertir (lecture seule)")
    p_mig.add_argument("--dry-run", action="store_true")
```

Puis ajouter `"migrate": cmd_migrate,` dans `handlers`.

- [ ] **Étape 4 : dispatcher `bin/forge`**

Ajouter, après le case `documente)` :

```bash
  migrate)
    shift
    exec python3 "$BIN_DIR/documente_engine.py" migrate "$@"
    ;;
```

Ajouter aussi, dans l'aide, après la ligne `documente` :

```
  migrate --dry-run               Liste les MEMORY.md à l'ancien format et leur type (n'écrit rien)
```

- [ ] **Étape 5 : vérifier que tout passe**

Lancer : `python3 -m pytest -q`
Attendu : tout vert (169 + 6 = 175 ; les tests `TestPrepare` restent en skip sans `CLAUDE_FORGE_PROJECT_DIR`).

Puis lancer : `CLAUDE_FORGE_PROJECT_DIR=/Users/bhamon/git/claude-enterprise python3 -m pytest -q tests/test_documente_engine.py -k Prepare`
Attendu : 3 tests verts.

- [ ] **Étape 6 : commit**

```bash
git add bin/documente_engine.py bin/forge tests/test_prepare_migrate.py tests/test_documente_engine.py
git commit -m "feat(documente): prepare sans aiguillage par chemin + forge migrate --dry-run"
```

---

### Tâche 7 : SKILL.md et doctrine, un seul circuit

**Fichiers :**
- Modifier : `skills/documente/SKILL.md`
- Modifier : `rules/subject-pool.md`

**Interfaces :**
- Consomme : la sortie JSON de `prepare` (tâche 6) et la commande `convert` (tâche 5).

- [ ] **Étape 1 : description et Objectif**

Dans le frontmatter, remplacer `lazy-creates the type (with user validation) and the instance (silent) if missing` par `recognizes any folder with a MEMORY.md as a subject (type from the header, then .forge.yaml type_by_path, then Claude's choice), converts legacy MEMORY.md in place, creates missing ones silently — never asks a question`. Remplacer aussi `version: 3.0` par `version: 4.0`.

Dans `## Objectif`, remplacer les items 1 et 2 par :

```markdown
1. **Tout dossier qui a un MEMORY.md est un subject** (SOCLE 0.7.0, design 2026-10-10). Le type est porté par l'en-tête, jamais par le chemin. Un MEMORY.md à l'ancien format est converti sur place au premier passage (`forge documente convert`), un dossier sans MEMORY.md reçoit le sien. **Aucune question** : `/documente` tourne en fin de cycle d'agents autonomes qui ne peuvent pas répondre.
2. **Nommage et typage automatiques** : nom = dossier existant, sinon `name_pattern` du type, sinon choix de Claude ; type = en-tête, sinon `type_by_path` du `.forge.yaml`, sinon choix de Claude parmi `known_types`.
```

- [ ] **Étape 2 : Argument et Gotchas**

Dans `## Argument`, remplacer le paragraphe « Inférence du path quand omis (v2.7) » et sa liste par :

```markdown
**Inférence du path quand omis** : le LLM choisit seul le dossier d'après la conversation, sans question. Un fichier identifiable (skill, outil, agent) donne son dossier ; un objet métier durable donne son subject existant (`forge documente list-subjects`) ou un nouveau dossier nommé selon le `name_pattern` du type. Doublon possible : même objet → enrichir l'existant, sinon créer.
```

Supprimer aussi la phrase « Une fois le path inféré, `forge documente prepare` retourne `service_root` ... ».

Dans `## Gotchas`, supprimer quatre puces : « Création paresseuse v2.1 », « Critère subject pool vs entité (v2.6) », « Structure service absente (v2.7) » et « Folder aussi instrumenté Python (v2.3) ». Remplacer la puce « Identifier le bon subject (ou dossier) » par :

```markdown
- **Aucune question pour nommer, typer ou classer** (0.7.0) : `prepare` donne le type ou `type_source: claude` ; dans ce cas Claude choisit dans `known_types` et le passe à `convert --type`. Jamais d'`AskUserQuestion`, jamais de marque `a_revoir`.
- **Capacités du type** : `prepare.capabilities` dit quelles phases s'appliquent. Sans `links` : pas de Phase F.1 autolink, H ni H.5. Sans `events` : pas de `last_event` à patcher en Phase G. Une phase sautée l'est en silence.
```

- [ ] **Étape 3 : Phases A et B**

Remplacer le corps de `### Phase A` (après le bloc bash) par :

```markdown
Parser le JSON retourné :
- `needs_creation: true` ou `needs_conversion: true` → **Phase B**.
- `is_subject: true` → **Phase C**.

Garder `capabilities` pour la suite : chaque phase marquée « (capacité X) » n'est exécutée que si X y figure.
```

Remplacer `### Phase B — Création paresseuse (interactif si type absent)` et son corps par :

````markdown
### Phase B — Création ou conversion (Python, sans question)

1. Type : `prepare.type`, sinon (`type_source: claude`) le type le plus juste parmi `prepare.known_types`, choisi par Claude d'après le contenu du dossier.
2. Nom : `prepare.default_name` pour un dossier existant ; pour un nouveau dossier, appliquer `prepare.name_pattern` (ou, à défaut, un slug kebab-case court tiré du contexte).
3. Si le type a un `TEMPLATE.md` à côté de son `REFERENCE.md` et que le dossier est neuf → `/subject-create <type> <name>` (Skill tool, silencieux). Sinon :

```bash
forge documente convert <path> --type <type> [--name <name>]
```

4. Repasser par Phase A (`is_subject: true` attendu), puis Phase C. Une conversion est committée avec le reste du bloc en Phase J.
````

- [ ] **Étape 4 : phases conditionnelles et F.2**

Ajouter les suffixes de capacité aux titres :
- `**F.1 — Extraire les typed edges (Python autolink)**` devient `**F.1 — Extraire les typed edges (Python autolink, capacité links)**` ;
- `### Phase H — Cascade horizontale` reçoit `(capacité links)` à la fin du titre ;
- `### Phase H.5` reçoit aussi `(capacité links)`.

Dans F.2, remplacer la liste des sections à rédiger, c'est-à-dire les deux puces `## Quick` et `## Détails`, par :

```markdown
- `## Quick` (<100 mots, ton synthétique factuel ; ligne **`Liens forts`** seulement avec la capacité links).
- `## Doctrine en vigueur` : une ligne par règle.
- `## Décisions actives` : au plus 10, chacune en pointeur vers son fichier `decisions/`.
- `## Règles apprises`.
- `## Détails` : contexte et paramètres en cours, **préserver les sous-sections custom** (`### Notes libres`, `### Stress tests à prévoir`, sections versées par une conversion), **sauf les sous-sections datées**, traitées en F.3.
```

Garder le paragraphe d'exemple `Liens forts` existant à l'intérieur de la puce Quick.

- [ ] **Étape 5 : supprimer le workflow folder et ajuster les évaluations**

Supprimer tout ce qui va de `## Workflow — Classique (folder, hors subject pool)` (ligne 326) jusqu'à la ligne qui précède `## Exemples` (ligne 494). Renommer `## Workflow — Subject Pool (depuis 2026-05-04, via \`forge documente\`)` en `## Workflow (unique depuis 0.7.0, via \`forge documente\`)`.

Dans F.3, remplacer « même règle que le workflow folder (F4), appliquée aux subjects » par « borne commune à tous les subjects ».

Dans `## Critères d'évaluation`, supprimer EVAL 13. Remplacer EVAL 11 par :

```
EVAL 11 : Zéro question (0.7.0)
Question: /documente a-t-il nommé, typé, converti ou créé le subject sans aucune AskUserQuestion ?
Pass: Type et nom fixés depuis prepare (en-tête, type_by_path, name_pattern) ou choisis par Claude, conversion faite et committée
Fail: Question posée à l'utilisateur, ou bloc arrêté faute de réponse
```

et remplacer, dans EVAL 9, « (pas un MEMORY.md de service) » par « (format unique : Quick, Doctrine en vigueur, Décisions actives, Règles apprises, Détails) ».

- [ ] **Étape 6 : `rules/subject-pool.md`**

Sous `### Localisation` (l. 17), remplacer le premier paragraphe par :

```markdown
**Depuis SOCLE 0.7.0 (design 2026-10-10), un subject est reconnu à son en-tête, pas à son chemin** : tout `MEMORY.md` dont le frontmatter porte `forging_state` est un subject, qu'il vive sous `subjects/` ou ailleurs (`entreprise/tools/x/`, `services/amazon/`, `entreprise/projets/y/`). Le type vient de l'en-tête, sinon de `type_by_path` dans `.forge.yaml`, sinon du choix de Claude. Les types génériques `skill`, `skill-cas`, `tool`, `agent`, `service` et `projet` sont livrés dans `types/` du plugin ; chaque type déclare ses `capabilities` (`memory`, `decisions`, `lifecycle`, `events`, `links`). Le dossier `subjects/` reste l'emplacement par défaut des objets métier, sans être une condition.
```

Remplacer `### Création paresseuse via \`/documente\` (v2.1+)` et son corps (l. 121-137) par :

```markdown
### Création et conversion via `/documente` (0.7.0)

`/documente <path>` sans `MEMORY.md` le crée ; sur un `MEMORY.md` à l'ancien format (sans `forging_state`), il le convertit sur place dans le même commit (`forge documente convert`, rien n'est supprimé). Aucune question : nom = dossier, `name_pattern` du type ou choix de Claude ; type = en-tête, `type_by_path` ou choix de Claude. `forge migrate --dry-run` liste ce qui reste à convertir.
```

Puis lancer `grep -n "entité\|folder\|F0" rules/subject-pool.md`. Pour chaque occurrence qui oppose encore « entité » et « subject », réécrire la phrase pour qu'elle dise « subject de type tool/skill/service » au lieu d'« entité ».

- [ ] **Étape 7 : vérifier**

Lancer : `grep -n "F0\|workflow folder\|is_subject_pool\|service_structure_exists\|AskUserQuestion" skills/documente/SKILL.md rules/subject-pool.md`
Attendu : aucune ligne, sauf `AskUserQuestion` dans la phrase « Jamais d'`AskUserQuestion` » et dans EVAL 11.

Lancer : `python3 -m pytest -q`
Attendu : toujours vert.

- [ ] **Étape 8 : commit**

```bash
git add skills/documente/SKILL.md rules/subject-pool.md
git commit -m "docs(documente): circuit unique — F0 et workflow folder supprimés, zéro question"
```

---

### Tâche 8 : version 0.7.0, essais réels et publication

**Fichiers :**
- Modifier : `VERSION`, `.claude-plugin/plugin.json` (l. 4), `.claude-plugin/marketplace.json` (l. 13), `README.md` (changelog, après l'entrée v0.6.1, vers la l. 117)

- [ ] **Étape 1 : versions**

Passer `0.6.1` à `0.7.0` dans les trois fichiers. Ajouter au README, après le paragraphe v0.6.1 :

```markdown
v0.7.0 — subject reconnu par son en-tête (2026-10-10) : tout `MEMORY.md` dont l'en-tête porte `forging_state` est un subject, où qu'il soit. Type = en-tête, puis `type_by_path` (`.forge.yaml`, facultatif), puis choix de Claude ; types génériques `skill`, `skill-cas`, `tool`, `agent`, `service`, `projet` livrés dans `types/`, capacités par type. `/documente` n'a plus qu'un circuit, sans question : la phase F0 et le workflow folder disparaissent, un ancien `MEMORY.md` est converti sur place au premier passage (`forge documente convert`, rien n'est supprimé). `forge migrate --dry-run` liste ce qui reste à convertir. `resolve_link` cherche par `name` d'en-tête partout et refuse les homonymes (alerte `duplicate_name`). Spec : `docs/superpowers/specs/2026-10-10-subject-par-en-tete-design.md`.
```

- [ ] **Étape 2 : suite complète**

Lancer : `python3 -m pytest -q`
Attendu : tout vert, environ 175 tests.

- [ ] **Étape 3 : essais réels en lecture seule**

Lancer :

```bash
CLAUDE_FORGE_PROJECT_DIR=/Users/bhamon/git/claude-enterprise bash bin/forge migrate --dry-run > /tmp/socle-migrate-ce.json
CLAUDE_FORGE_PROJECT_DIR=/Users/bhamon/git/equipstore-direction bash bin/forge migrate --dry-run > /tmp/socle-migrate-equipstore.json
CLAUDE_FORGE_PROJECT_DIR=/Users/bhamon/git/claude-enterprise python3 bin/documente_engine.py list-subjects | python3 -c "import json,sys; print(len(json.load(sys.stdin)['subjects']))"
git -C /Users/bhamon/git/claude-enterprise status --short
git -C /Users/bhamon/git/equipstore-direction status --short
```

Attendu :
- `ok: true` sur les deux dépôts ;
- environ 88 MEMORY.md à convertir pour CE ;
- `list-subjects` CE ≥ 42 ;
- aucun fichier modifié dans les deux dépôts.

`type_by_path` n'est pas encore en place dans CE (tâche 9), donc `by_source` y vaut surtout `claude`, sauf les MEMORY.md qui ont déjà un `type:` d'en-tête. Montrer à Benjamin un résumé : total, `by_source`, et dix lignes d'exemple pour chaque dépôt. **Attendre son accord avant l'étape 4.**

- [ ] **Étape 4 : commit, push et mise à jour locale du plugin**

```bash
git add VERSION .claude-plugin/plugin.json .claude-plugin/marketplace.json README.md
git commit -m "release: v0.7.0 — subject reconnu par son en-tête"
git push origin main
claude plugin marketplace update rubee-labs
claude plugin update socle@rubee-labs --scope user
claude plugin update socle@rubee-labs --scope project
ls ~/.claude/plugins/cache/rubee-labs/socle/
```

Attendu : un dossier `0.7.0` dans le cache.

---

### Tâche 9 : adoption dans claude-enterprise

**Fichiers :**
- Modifier : `/Users/bhamon/git/claude-enterprise/.forge.yaml`
- Modifier : `/Users/bhamon/git/claude-enterprise/entreprise/config/rules/operations.md` (paragraphe de délégation à `/documente`)
- Modifier : `/Users/bhamon/.claude/CLAUDE.md` (paragraphe « Délégation à `/documente` … si subject pool »)
- Créer : `/Users/bhamon/git/claude-enterprise/entreprise/config/decisions/2026-10-10-subject-par-en-tete-socle-0-7.yaml`

- [ ] **Étape 1 : `.forge.yaml`**

Ajouter à la fin :

```yaml
# Types par emplacement (SOCLE 0.7.0) : lus dans l'ordre, le premier qui correspond gagne.
# Un MEMORY.md dont l'en-tête a déjà un type n'est jamais recalculé.
type_by_path:
  - {pattern: "*/skills/*/cas/*", type: skill-cas}
  - {pattern: "*/skills/*", type: skill}
  - {pattern: "*/tools/*", type: tool}
  - {pattern: "*/agents/*", type: agent}
  - {pattern: "entreprise/projets/*", type: projet}
  - {pattern: "services/*", type: service}
```

Vérifier :

```bash
cd /Users/bhamon/git/claude-enterprise && forge migrate --dry-run | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['total'], r['by_source'])"
```

Attendu : la plupart des entrées sont en `type_by_path` ou `frontmatter` (en-tête déjà typé). Montrer à Benjamin, pour information, les entrées restantes en `claude` : Claude choisira leur type au premier `/documente`.

- [ ] **Étape 2 : règles**

Dans `entreprise/config/rules/operations.md` et dans `~/.claude/CLAUDE.md`, remplacer le paragraphe « **Délégation à `/documente` (plugin SOCLE, ex-claude-forge) si subject pool** : … » par :

```markdown
**Toujours `/documente` (plugin SOCLE ≥ 0.7.0)** : tout dossier qui a un `MEMORY.md` est un subject (type porté par l'en-tête, pas par le chemin). Ne PAS écrire 1+2+3 à la main → invoquer `/documente <dossier>` qui orchestre tout (capture conversation, écrit discussion + décision, convertit un ancien MEMORY.md au premier passage, réécrit le MEMORY.md borné, propage aux `linked_subjects` si le type a des liens), sans aucune question. 4+5 restent à la charge de la doctrine post-bloc.
```

Pour `~/.claude/CLAUDE.md` : c'est un fichier hors dépôt, à modifier avec Edit, sans commit.

- [ ] **Étape 3 : décision**

Écrire la décision au format de `entreprise/config/decisions/2026-10-10-hook-post-bloc-socle.yaml` :
- `sujet` : « Tout dossier qui a un MEMORY.md est un subject (SOCLE 0.7.0) ; type par l'en-tête, `type_by_path` dans `.forge.yaml` » ;
- `parameters` : `socle_version: 0.7.0`, `spec`, `plan` ;
- `options_considerees` : les trois approches du design ;
- `confirmation.preuve` : « le premier `/documente` sur un dossier hors `subjects/` le convertit sans question, et `forge migrate --dry-run` baisse d'au moins 1 » ;
- `echeance: 2026-10-24`.

Lancer `date` avant d'écrire, pour l'heure et la date.

- [ ] **Étape 4 : `/documente` sur `entreprise/config`**

Invoquer `/documente entreprise/config` : c'est le premier vrai passage, qui convertit `entreprise/config/MEMORY.md`. Vérifier :
- l'en-tête a `forging_state: actif` et `type: <choisi>` ;
- aucune ligne de contenu perdue : `git diff` ne montre que des ajouts et des déplacements ;
- `forge migrate --dry-run` a un total plus bas de 1.

- [ ] **Étape 5 : commit et push CE**

```bash
git -C /Users/bhamon/git/claude-enterprise add .forge.yaml entreprise/config/
git -C /Users/bhamon/git/claude-enterprise commit -m "config: SOCLE 0.7.0 — subject reconnu par son en-tête, type_by_path"
git -C /Users/bhamon/git/claude-enterprise push origin main
```
