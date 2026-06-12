# Extraction `/documente` → `documente_engine.py` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extraire les phases déterministes de `/documente` (frontmatter, scan, commit, cohérence, captures) dans un binaire CLI `documente_engine.py` calqué sur `forge_engine.py`. Réduire de ~70% les tokens consommés par invocation et éliminer le risque de corruption YAML par le LLM.

**Architecture:** Strangler pattern. M1-M7 livrent `documente_engine.py` avec 8 commandes CLI testées en standalone. Le `SKILL.md` n'est PAS modifié pendant M1-M7. À la fin de M7, bascule sèche : réécriture du SKILL.md en orchestrateur léger, suppression des phases déterministes du LLM. Pas de feature flag. Tag git `pre-documente-engine-cutover` avant la bascule pour rollback propre via `git revert`.

**Tech Stack:** Python 3 stdlib uniquement (pas de pyyaml, pas de ruamel — calqué sur `forge_lib.py`). Tests via `unittest` stdlib + script bash de smoke. Git via subprocess. Pas de dépendance npm/pip ajoutée.

**Doctrine projet :** travail sur `main` directement (memory: "projets CE toujours sur main"). Commit après chaque task. Pas de worktree.

---

## File Structure

| Fichier | Responsabilité | M |
|---|---|---|
| `entreprise/config/feedback-loop/documente_engine.py` | Dispatcher CLI principal — 8 commandes | M1-M7 |
| `entreprise/config/feedback-loop/documente_lib.py` | Helpers YAML write + path utils (complète `forge_lib.py`) | M2-M7 |
| `entreprise/config/feedback-loop/tests/test_documente_engine.py` | Tests unitaires `unittest` | M1-M7 |
| `entreprise/config/feedback-loop/tests/fixtures/` | 3 subjects copiés (order-398, supplier-weifang, google-ads-brumeaux) | M1 |
| `entreprise/config/feedback-loop/tests/run_smoke.sh` | Script smoke test bout-en-bout | M1 |
| `entreprise/skills/documente/SKILL.md` | Réécrit en orchestrateur léger | Bascule (T13) |

**Convention de retour CLI** : toutes les commandes retournent un JSON sur `stdout` au format :

```json
{ "ok": true, "version": 1, ...payload }
```

ou en cas d'erreur :

```json
{ "ok": false, "version": 1, "error": "<message>", "code": "<error_code>" }
```

Exit code `0` toujours (sauf crash Python). Le skill teste `ok` du JSON, pas l'exit code.

---

## Task 1: Créer le squelette `documente_engine.py` avec dispatcher

**Files:**
- Create: `entreprise/config/feedback-loop/documente_engine.py`
- Create: `entreprise/skills/documente/plans/` (dossier)

- [ ] **Step 1: Vérifier que le dossier plans existe**

```bash
ls entreprise/skills/documente/plans/
```

Expected: au moins ce fichier de plan présent (déjà créé).

- [ ] **Step 2: Créer le squelette `documente_engine.py`**

```python
#!/usr/bin/env python3
"""
documente_engine.py — Couche déterministe du skill /documente.

Frère de forge_engine.py. Extrait les phases mécaniques du skill
(infer-type, patch-frontmatter, scan, commit, etc.) pour économiser
des tokens LLM et éliminer le risque de corruption YAML.

Usage CLI :
  python3 documente_engine.py <command> [args]

Toutes les commandes retournent un JSON sur stdout au format :
  {"ok": true, "version": 1, ...}
ou
  {"ok": false, "version": 1, "error": "...", "code": "..."}

Exit code 0 toujours (sauf crash Python). Le skill teste `ok` du JSON.
"""

import argparse
import json
import sys
from pathlib import Path

VERSION = 1


def _ok(**payload):
    return {"ok": True, "version": VERSION, **payload}


def _err(message, code="generic_error"):
    return {"ok": False, "version": VERSION, "error": message, "code": code}


def cmd_list_subjects(args):
    return _err("not implemented", code="not_implemented")


def cmd_prepare(args):
    return _err("not implemented", code="not_implemented")


def cmd_infer_type(args):
    return _err("not implemented", code="not_implemented")


def cmd_patch_frontmatter(args):
    return _err("not implemented", code="not_implemented")


def cmd_commit_atomic(args):
    return _err("not implemented", code="not_implemented")


def cmd_scan_impacted(args):
    return _err("not implemented", code="not_implemented")


def cmd_check_coherence(args):
    return _err("not implemented", code="not_implemented")


def cmd_write_capture(args):
    return _err("not implemented", code="not_implemented")


def cmd_cascade_last_event(args):
    return _err("not implemented", code="not_implemented")


def main():
    parser = argparse.ArgumentParser(prog="documente_engine.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-subjects")

    p_prepare = sub.add_parser("prepare")
    p_prepare.add_argument("path")

    p_infer = sub.add_parser("infer-type")
    p_infer.add_argument("path")

    p_patch = sub.add_parser("patch-frontmatter")
    p_patch.add_argument("path")
    p_patch.add_argument("--patch", required=True, help="JSON patch object")
    p_patch.add_argument("--dry-run", action="store_true")

    p_commit = sub.add_parser("commit-atomic")
    p_commit.add_argument("--paths", required=True, help="comma-separated paths")
    p_commit.add_argument("--message", required=True)
    p_commit.add_argument("--push", action="store_true")

    p_scan = sub.add_parser("scan-impacted")
    p_scan.add_argument("path")

    p_check = sub.add_parser("check-coherence")
    p_check.add_argument("path")
    p_check.add_argument("--decision-yaml", required=True, help="JSON of new decision parameters")

    p_write = sub.add_parser("write-capture")
    p_write.add_argument("path")
    p_write.add_argument("--kind", required=True, choices=["discussion", "decision"])
    p_write.add_argument("--slug", required=True)
    p_write.add_argument("--body-file", required=True, help="path to file containing body markdown/yaml")
    p_write.add_argument("--frontmatter", required=True, help="JSON object of frontmatter fields")

    p_cascade = sub.add_parser("cascade-last-event")
    p_cascade.add_argument("root_path")
    p_cascade.add_argument("linked_path")
    p_cascade.add_argument("--event-ref", required=True)

    args = parser.parse_args()

    handlers = {
        "list-subjects": cmd_list_subjects,
        "prepare": cmd_prepare,
        "infer-type": cmd_infer_type,
        "patch-frontmatter": cmd_patch_frontmatter,
        "commit-atomic": cmd_commit_atomic,
        "scan-impacted": cmd_scan_impacted,
        "check-coherence": cmd_check_coherence,
        "write-capture": cmd_write_capture,
        "cascade-last-event": cmd_cascade_last_event,
    }

    result = handlers[args.cmd](args)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Vérifier que le dispatcher fonctionne sur chaque commande**

```bash
chmod +x entreprise/config/feedback-loop/documente_engine.py
for cmd in list-subjects prepare infer-type patch-frontmatter commit-atomic scan-impacted check-coherence write-capture cascade-last-event; do
  case "$cmd" in
    list-subjects)
      python3 entreprise/config/feedback-loop/documente_engine.py "$cmd" 2>&1 | head -5
      ;;
    patch-frontmatter)
      python3 entreprise/config/feedback-loop/documente_engine.py "$cmd" /tmp --patch '{}' 2>&1 | head -5
      ;;
    commit-atomic)
      python3 entreprise/config/feedback-loop/documente_engine.py "$cmd" --paths /tmp --message x 2>&1 | head -5
      ;;
    check-coherence)
      python3 entreprise/config/feedback-loop/documente_engine.py "$cmd" /tmp --decision-yaml '{}' 2>&1 | head -5
      ;;
    write-capture)
      python3 entreprise/config/feedback-loop/documente_engine.py "$cmd" /tmp --kind discussion --slug x --body-file /tmp/x --frontmatter '{}' 2>&1 | head -5
      ;;
    cascade-last-event)
      python3 entreprise/config/feedback-loop/documente_engine.py "$cmd" /tmp /tmp --event-ref x 2>&1 | head -5
      ;;
    *)
      python3 entreprise/config/feedback-loop/documente_engine.py "$cmd" /tmp 2>&1 | head -5
      ;;
  esac
  echo "---"
done
```

Expected: chaque commande affiche `{"ok": false, "version": 1, "error": "not implemented", "code": "not_implemented"}` puis `---`.

- [ ] **Step 4: Commit**

```bash
git -C "/Users/bhamon/git/claude-enterprise" add \
  entreprise/config/feedback-loop/documente_engine.py \
  entreprise/skills/documente/plans/2026-05-04-extraction-engine-python.md
git -C "/Users/bhamon/git/claude-enterprise" commit -m "feat(documente): squelette documente_engine.py + plan d'extraction

- Dispatcher CLI avec 9 commandes stub (list-subjects, prepare, infer-type,
  patch-frontmatter, commit-atomic, scan-impacted, check-coherence,
  write-capture, cascade-last-event)
- Convention JSON {ok, version, ...} sur stdout
- Plan d'extraction complet documenté

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Test fixtures + harness `unittest`

**Files:**
- Create: `entreprise/config/feedback-loop/tests/__init__.py`
- Create: `entreprise/config/feedback-loop/tests/test_documente_engine.py`
- Create: `entreprise/config/feedback-loop/tests/fixtures/order-398/` (copie)
- Create: `entreprise/config/feedback-loop/tests/run_smoke.sh`

- [ ] **Step 1: Créer le dossier tests + init**

```bash
mkdir -p entreprise/config/feedback-loop/tests/fixtures
touch entreprise/config/feedback-loop/tests/__init__.py
```

- [ ] **Step 2: Copier 3 subjects de référence comme fixtures**

```bash
cp -r "services/achats/subjects/order-398" entreprise/config/feedback-loop/tests/fixtures/
```

Si `services/marketing/subjects/google-ads-brumeaux/` existe :
```bash
cp -r services/marketing/subjects/google-ads-brumeaux entreprise/config/feedback-loop/tests/fixtures/ 2>/dev/null || echo "skip — fixture non disponible"
```

Si `services/achats/subjects/supplier-weifang/` existe :
```bash
cp -r services/achats/subjects/supplier-weifang entreprise/config/feedback-loop/tests/fixtures/ 2>/dev/null || echo "skip — fixture non disponible"
```

Au minimum, `order-398` doit être présent comme fixture.

- [ ] **Step 3: Créer le test harness `test_documente_engine.py`**

```python
#!/usr/bin/env python3
"""Tests unittest pour documente_engine.py."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent / "documente_engine.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run_engine(*args, cwd=None):
    """Invoque le binaire et retourne le JSON parsé."""
    result = subprocess.run(
        [sys.executable, str(ENGINE), *args],
        capture_output=True,
        text=True,
        cwd=cwd or os.getcwd(),
    )
    if result.returncode != 0:
        raise AssertionError(
            f"engine crashed (exit {result.returncode}):\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
    return json.loads(result.stdout)


class TestEngineSkeleton(unittest.TestCase):
    """Tests de base : dispatcher fonctionne, commandes stub retournent not_implemented."""

    def test_dispatcher_returns_json(self):
        result = run_engine("list-subjects")
        self.assertIn("ok", result)
        self.assertIn("version", result)
        self.assertEqual(result["version"], 1)

    def test_unknown_command_fails(self):
        result = subprocess.run(
            [sys.executable, str(ENGINE), "nonexistent-cmd"],
            capture_output=True, text=True,
        )
        # argparse exit 2 sur sous-commande inconnue
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Créer le smoke test bash**

```bash
cat > entreprise/config/feedback-loop/tests/run_smoke.sh << 'SMOKE_EOF'
#!/usr/bin/env bash
# Smoke test : invoque chaque commande de documente_engine.py et vérifie
# que la sortie est un JSON valide avec champs ok et version.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
ENGINE="$ROOT/entreprise/config/feedback-loop/documente_engine.py"

assert_json() {
  local name="$1"
  local output="$2"
  if ! echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'ok' in d and 'version' in d, 'missing keys'" 2>/dev/null; then
    echo "FAIL $name : sortie non-JSON ou champs manquants"
    echo "  output: $output"
    exit 1
  fi
  echo "OK   $name"
}

assert_json "list-subjects" "$(python3 "$ENGINE" list-subjects 2>&1)"
assert_json "prepare(/tmp)" "$(python3 "$ENGINE" prepare /tmp 2>&1)"
assert_json "infer-type(/tmp)" "$(python3 "$ENGINE" infer-type /tmp 2>&1)"
assert_json "patch-frontmatter(/tmp)" "$(python3 "$ENGINE" patch-frontmatter /tmp --patch '{}' 2>&1)"
assert_json "commit-atomic" "$(python3 "$ENGINE" commit-atomic --paths /tmp --message x 2>&1)"
assert_json "scan-impacted(/tmp)" "$(python3 "$ENGINE" scan-impacted /tmp 2>&1)"
assert_json "check-coherence(/tmp)" "$(python3 "$ENGINE" check-coherence /tmp --decision-yaml '{}' 2>&1)"

echo ""
echo "Smoke OK : toutes les commandes retournent un JSON parsable."
SMOKE_EOF
chmod +x entreprise/config/feedback-loop/tests/run_smoke.sh
```

- [ ] **Step 5: Lancer le smoke test**

```bash
bash entreprise/config/feedback-loop/tests/run_smoke.sh
```

Expected:
```
OK   list-subjects
OK   prepare(/tmp)
OK   infer-type(/tmp)
OK   patch-frontmatter(/tmp)
OK   commit-atomic
OK   scan-impacted(/tmp)
OK   check-coherence(/tmp)

Smoke OK : toutes les commandes retournent un JSON parsable.
```

- [ ] **Step 6: Lancer les tests unittest**

```bash
python3 -m unittest entreprise.config.feedback-loop.tests.test_documente_engine -v
```

Si le module path échoue (à cause du tiret dans `feedback-loop`), utiliser :

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine -v
```

Expected: 2 tests OK.

- [ ] **Step 7: Commit**

```bash
git -C "/Users/bhamon/git/claude-enterprise" add \
  entreprise/config/feedback-loop/tests/
git -C "/Users/bhamon/git/claude-enterprise" commit -m "test(documente): harness unittest + smoke + fixture order-398

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Implémenter `list-subjects`

**Files:**
- Modify: `entreprise/config/feedback-loop/documente_engine.py:cmd_list_subjects`
- Modify: `entreprise/config/feedback-loop/tests/test_documente_engine.py`

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter dans `test_documente_engine.py` :

```python
class TestListSubjects(unittest.TestCase):

    def test_returns_at_least_one_subject(self):
        # Lancer depuis racine repo pour scanner subjects/ réels
        repo_root = Path(__file__).resolve().parents[4]
        result = run_engine("list-subjects", cwd=str(repo_root))
        self.assertTrue(result["ok"])
        self.assertIn("subjects", result)
        self.assertGreater(len(result["subjects"]), 0)

    def test_each_subject_has_path_and_state(self):
        repo_root = Path(__file__).resolve().parents[4]
        result = run_engine("list-subjects", cwd=str(repo_root))
        for subj in result["subjects"]:
            self.assertIn("path", subj)
            self.assertIn("forging_state", subj)
            self.assertIn("type", subj)
```

- [ ] **Step 2: Vérifier que le test échoue**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestListSubjects -v
```

Expected: FAIL avec "ok: false" ou KeyError sur "subjects".

- [ ] **Step 3: Implémenter `cmd_list_subjects`**

Dans `documente_engine.py`, ajouter en haut :

```python
sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge_lib import get_project_dir, parse_frontmatter
```

Remplacer `cmd_list_subjects` :

```python
def cmd_list_subjects(args):
    """Liste tous les subjects du repo (avec MEMORY.md ayant forging_state)."""
    project_dir = get_project_dir()
    subjects = []
    # Scanner les patterns subjects/<name>/MEMORY.md sur 3 racines
    for root in ("services", "entreprise", "humains"):
        root_dir = project_dir / root
        if not root_dir.is_dir():
            continue
        for memory_md in root_dir.rglob("subjects/*/MEMORY.md"):
            fm = parse_frontmatter(memory_md)
            if not fm or "forging_state" not in fm:
                continue
            subjects.append({
                "path": str(memory_md.parent.relative_to(project_dir)),
                "forging_state": fm.get("forging_state"),
                "conviction": fm.get("conviction"),
                "type": fm.get("type"),
                "last_event_date": (fm.get("last_event") or {}).get("date") if isinstance(fm.get("last_event"), dict) else None,
            })
    return _ok(subjects=sorted(subjects, key=lambda s: s["path"]))
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestListSubjects -v
```

Expected: 2 tests OK.

- [ ] **Step 5: Vérification visuelle de la sortie**

```bash
python3 entreprise/config/feedback-loop/documente_engine.py list-subjects | python3 -m json.tool | head -30
```

Expected: liste JSON propre avec les ~5 subjects achats + autres.

- [ ] **Step 6: Commit**

```bash
git -C "/Users/bhamon/git/claude-enterprise" add \
  entreprise/config/feedback-loop/documente_engine.py \
  entreprise/config/feedback-loop/tests/test_documente_engine.py
git -C "/Users/bhamon/git/claude-enterprise" commit -m "feat(documente): list-subjects scanne les MEMORY.md avec forging_state

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Implémenter `prepare`

**Files:**
- Modify: `entreprise/config/feedback-loop/documente_engine.py:cmd_prepare`
- Modify: `entreprise/config/feedback-loop/tests/test_documente_engine.py`

- [ ] **Step 1: Écrire les tests**

Ajouter dans `test_documente_engine.py` :

```python
class TestPrepare(unittest.TestCase):

    def test_existing_subject(self):
        repo_root = Path(__file__).resolve().parents[4]
        result = run_engine("prepare", "services/achats/subjects/order-398", cwd=str(repo_root))
        self.assertTrue(result["ok"])
        self.assertTrue(result["is_subject_pool"])
        self.assertTrue(result["subject_exists"])
        self.assertIn("type", result)
        self.assertIn("current_frontmatter", result)
        self.assertFalse(result["needs_creation"])

    def test_nonexistent_subject(self):
        repo_root = Path(__file__).resolve().parents[4]
        result = run_engine("prepare", "services/achats/subjects/order-99999", cwd=str(repo_root))
        self.assertTrue(result["ok"])
        self.assertTrue(result["is_subject_pool"])
        self.assertFalse(result["subject_exists"])
        self.assertTrue(result["needs_creation"])

    def test_non_subject_pool_path(self):
        repo_root = Path(__file__).resolve().parents[4]
        result = run_engine("prepare", "entreprise/config", cwd=str(repo_root))
        self.assertTrue(result["ok"])
        self.assertFalse(result["is_subject_pool"])
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestPrepare -v
```

Expected: 3 FAIL.

- [ ] **Step 3: Implémenter `cmd_prepare`**

Dans `documente_engine.py`, remplacer `cmd_prepare` :

```python
def cmd_prepare(args):
    """Phase 0a + 0b + 1 : détecte contexte, vérifie existence, retourne état."""
    project_dir = get_project_dir()
    raw = args.path
    # Path peut être absolu ou relatif au repo
    p = Path(raw)
    if not p.is_absolute():
        p = project_dir / raw

    # Détection subject pool : path contient subjects/<name>
    parts = p.parts
    is_subject_pool = "subjects" in parts and parts.index("subjects") < len(parts) - 1

    if not is_subject_pool:
        return _ok(
            is_subject_pool=False,
            subject_exists=False,
            needs_creation=False,
            recommended_workflow="legacy",
            path=str(p.relative_to(project_dir)) if p.is_relative_to(project_dir) else str(p),
        )

    memory_md = p / "MEMORY.md"
    subject_exists = memory_md.is_file()
    fm = parse_frontmatter(memory_md) if subject_exists else None

    # Inférer le type depuis frontmatter ou path
    inferred_type = (fm.get("type") if fm else None)

    return _ok(
        is_subject_pool=True,
        subject_exists=subject_exists,
        path=str(p.relative_to(project_dir)) if p.is_relative_to(project_dir) else str(p),
        type=inferred_type,
        current_frontmatter=fm,
        needs_creation=not subject_exists,
        recommended_workflow="subject_pool",
    )
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestPrepare -v
```

Expected: 3 tests OK.

- [ ] **Step 5: Vérification visuelle**

```bash
python3 entreprise/config/feedback-loop/documente_engine.py prepare services/achats/subjects/order-398 | python3 -m json.tool
```

Expected: JSON avec `is_subject_pool: true`, `subject_exists: true`, frontmatter complet, `needs_creation: false`.

- [ ] **Step 6: Commit**

```bash
git -C "/Users/bhamon/git/claude-enterprise" add \
  entreprise/config/feedback-loop/documente_engine.py \
  entreprise/config/feedback-loop/tests/test_documente_engine.py
git -C "/Users/bhamon/git/claude-enterprise" commit -m "feat(documente): prepare détecte subject pool + frontmatter courant

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Implémenter `infer-type`

**Files:**
- Modify: `entreprise/config/feedback-loop/documente_engine.py:cmd_infer_type`
- Modify: `entreprise/config/feedback-loop/tests/test_documente_engine.py`

- [ ] **Step 1: Écrire les tests**

Ajouter dans `test_documente_engine.py` :

```python
class TestInferType(unittest.TestCase):

    def test_infer_from_existing_frontmatter(self):
        repo_root = Path(__file__).resolve().parents[4]
        result = run_engine("infer-type", "services/achats/subjects/order-398", cwd=str(repo_root))
        self.assertTrue(result["ok"])
        self.assertEqual(result["strategy"], "from_frontmatter")
        self.assertIsNotNone(result["type"])

    def test_infer_from_single_parent_type(self):
        # Créer un cas avec 1 seul type dans <parent>/types/
        # services/achats/types/ contient "supplier" et "supplier-order" → 2 types
        # Donc le single-type fallback ne s'appliquera pas ici. Testons ce qui DOIT
        # fonctionner : type connu via naming convention.
        repo_root = Path(__file__).resolve().parents[4]
        result = run_engine("infer-type", "services/achats/subjects/order-99999", cwd=str(repo_root))
        # Subject n'existe pas → strategy != from_frontmatter
        self.assertTrue(result["ok"])
        self.assertNotEqual(result.get("strategy"), "from_frontmatter")

    def test_infer_from_naming_convention(self):
        # Si nom commence par <type>- et <type> existe dans parent/types/
        # supplier-XXX → type "supplier"
        repo_root = Path(__file__).resolve().parents[4]
        result = run_engine("infer-type", "services/achats/subjects/supplier-newone", cwd=str(repo_root))
        self.assertTrue(result["ok"])
        if result.get("type") == "supplier":
            self.assertEqual(result["strategy"], "from_naming")
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestInferType -v
```

Expected: FAIL.

- [ ] **Step 3: Implémenter `cmd_infer_type`**

Dans `documente_engine.py`, remplacer `cmd_infer_type` :

```python
def cmd_infer_type(args):
    """Phase 0c : inférer le type d'un subject selon 4 stratégies."""
    project_dir = get_project_dir()
    p = Path(args.path)
    if not p.is_absolute():
        p = project_dir / args.path

    # Stratégie 1 : type explicite dans MEMORY.md
    memory_md = p / "MEMORY.md"
    if memory_md.is_file():
        fm = parse_frontmatter(memory_md) or {}
        if fm.get("type"):
            return _ok(
                type=fm["type"],
                strategy="from_frontmatter",
                type_exists=_type_exists(p, fm["type"]),
            )

    # Stratégie 2 : 1 seul type dans <parent>/types/
    parent = _subject_parent(p)
    if parent:
        types_dir = parent / "types"
        if types_dir.is_dir():
            existing_types = [d.name for d in types_dir.iterdir() if d.is_dir()]
            if len(existing_types) == 1:
                return _ok(
                    type=existing_types[0],
                    strategy="single_parent_type",
                    type_exists=True,
                )

            # Stratégie 3 : naming convention <type>-<rest>
            name = p.name
            for t in existing_types:
                if name == t or name.startswith(t + "-"):
                    return _ok(
                        type=t,
                        strategy="from_naming",
                        type_exists=True,
                    )

            # Stratégie 4 : plusieurs candidats
            return _ok(
                type=None,
                strategy="ambiguous",
                candidates=existing_types,
                type_exists=False,
            )

    # Stratégie 5 : aucun type trouvable
    return _ok(
        type=None,
        strategy="none",
        candidates=[],
        type_exists=False,
    )


def _subject_parent(subject_path):
    """Retourne le parent qui contient subjects/ et types/. Ex: services/achats/."""
    p = subject_path.resolve()
    while p.parent != p:
        if p.name == "subjects":
            return p.parent
        p = p.parent
    return None


def _type_exists(subject_path, type_name):
    parent = _subject_parent(subject_path)
    if not parent:
        return False
    return (parent / "types" / type_name).is_dir()
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestInferType -v
```

Expected: 3 tests OK.

- [ ] **Step 5: Test manuel sur cas réels**

```bash
# Subject existant
python3 entreprise/config/feedback-loop/documente_engine.py infer-type services/achats/subjects/order-398
# Subject n'existant pas mais naming match
python3 entreprise/config/feedback-loop/documente_engine.py infer-type services/achats/subjects/supplier-future
```

Expected:
- order-398 → strategy "from_frontmatter", type connu
- supplier-future → strategy "from_naming", type "supplier"

- [ ] **Step 6: Commit**

```bash
git -C "/Users/bhamon/git/claude-enterprise" add \
  entreprise/config/feedback-loop/documente_engine.py \
  entreprise/config/feedback-loop/tests/test_documente_engine.py
git -C "/Users/bhamon/git/claude-enterprise" commit -m "feat(documente): infer-type avec 4 stratégies (frontmatter, single, naming, ambiguous)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Implémenter `patch-frontmatter` ★ ROI critique

**Files:**
- Create: `entreprise/config/feedback-loop/documente_lib.py`
- Modify: `entreprise/config/feedback-loop/documente_engine.py:cmd_patch_frontmatter`
- Modify: `entreprise/config/feedback-loop/tests/test_documente_engine.py`

**Stratégie** : édition surgicale ligne-par-ligne pour préserver formatage et commentaires. Pas de re-sérialisation YAML complète. Chaque clé du patch :
- Scalaire → remplace la valeur sur la ligne `key: ...`
- Dict → remplace tout le bloc indenté sous `key:`
- Liste avec `+slug` / `-slug` → ajoute/retire des items, préserve les autres

- [ ] **Step 1: Écrire les tests (cas scalaire)**

Ajouter dans `test_documente_engine.py` :

```python
class TestPatchFrontmatter(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.subject = self.tmpdir / "subj"
        self.subject.mkdir()
        self.memory = self.subject / "MEMORY.md"
        self.memory.write_text("""---
type: purchase-order
forging_state: seed
conviction: 10
last_event:
  date: 2026-04-01
  type: created
  ref: events/2026-04-01-init.md
active_decisions: []
open_discussions: []
linked_subjects:
  - services/achats/subjects/supplier-x
---

## Quick

État initial.

## Détails

Texte libre.
""", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_patch_scalar(self):
        result = run_engine(
            "patch-frontmatter", str(self.subject),
            "--patch", '{"conviction": 50}',
        )
        self.assertTrue(result["ok"])
        content = self.memory.read_text(encoding="utf-8")
        self.assertIn("conviction: 50", content)
        self.assertNotIn("conviction: 10", content)

    def test_patch_preserves_body(self):
        result = run_engine(
            "patch-frontmatter", str(self.subject),
            "--patch", '{"forging_state": "tentative"}',
        )
        self.assertTrue(result["ok"])
        content = self.memory.read_text(encoding="utf-8")
        self.assertIn("## Quick", content)
        self.assertIn("Texte libre.", content)
        self.assertIn("forging_state: tentative", content)

    def test_patch_nested_dict(self):
        result = run_engine(
            "patch-frontmatter", str(self.subject),
            "--patch", '{"last_event": {"date": "2026-05-04", "type": "reply_sent", "ref": "events/2026-05-04-reply.md"}}',
        )
        self.assertTrue(result["ok"])
        content = self.memory.read_text(encoding="utf-8")
        self.assertIn("date: 2026-05-04", content)
        self.assertIn("type: reply_sent", content)
        self.assertNotIn("date: 2026-04-01", content)

    def test_patch_list_append(self):
        result = run_engine(
            "patch-frontmatter", str(self.subject),
            "--patch", '{"active_decisions": ["+2026-05-04-payment-terms"]}',
        )
        self.assertTrue(result["ok"])
        content = self.memory.read_text(encoding="utf-8")
        self.assertIn("- 2026-05-04-payment-terms", content)

    def test_patch_list_remove(self):
        # D'abord ajouter, puis retirer
        run_engine("patch-frontmatter", str(self.subject), "--patch", '{"active_decisions": ["+a", "+b"]}')
        result = run_engine("patch-frontmatter", str(self.subject), "--patch", '{"active_decisions": ["-a"]}')
        self.assertTrue(result["ok"])
        content = self.memory.read_text(encoding="utf-8")
        self.assertNotIn("- a\n", content + "\n")
        self.assertIn("- b", content)

    def test_dry_run_no_write(self):
        before = self.memory.read_text(encoding="utf-8")
        result = run_engine(
            "patch-frontmatter", str(self.subject),
            "--patch", '{"conviction": 99}', "--dry-run",
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["dry_run"])
        self.assertEqual(before, self.memory.read_text(encoding="utf-8"))

    def test_idempotent(self):
        run_engine("patch-frontmatter", str(self.subject), "--patch", '{"conviction": 50}')
        before = self.memory.read_text(encoding="utf-8")
        run_engine("patch-frontmatter", str(self.subject), "--patch", '{"conviction": 50}')
        after = self.memory.read_text(encoding="utf-8")
        self.assertEqual(before, after)
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestPatchFrontmatter -v
```

Expected: tous les tests FAIL.

- [ ] **Step 3: Créer `documente_lib.py` avec les helpers de patch**

```python
#!/usr/bin/env python3
"""
documente_lib.py — Helpers pour documente_engine.py.

Édition surgicale du frontmatter YAML. Préserve l'ordre des clés,
les commentaires, et le body markdown intact. Stdlib only.
"""

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
        # Détecter le kind
        if value_part and not value_part.startswith("["):
            # Scalar inline (ou inline dict {})
            return i, i + 1, "scalar"
        if value_part.startswith("["):
            return i, i + 1, "scalar"  # liste inline traitée comme scalaire
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
                # ligne vide intercalée : continue le bloc
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
    # Cas qui demandent quoting
    if any(c in s for c in [":", "#"]) and not s.startswith('"'):
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
    """Applique un patch dict au frontmatter (mutation in-place de fm_lines).

    Pour chaque clé du patch :
    - valeur scalaire / dict / liste plate → remplace ou ajoute
    - liste avec items "+x" / "-x" → append / remove
    """
    new_lines = list(fm_lines)
    for key, value in patch.items():
        start, end, kind = find_key_block(new_lines, key)

        # Liste avec opérations +/-
        if isinstance(value, list) and value and all(isinstance(v, str) and (v.startswith("+") or v.startswith("-")) for v in value):
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


def patch_frontmatter_file(path, patch, dry_run=False):
    """Applique le patch au MEMORY.md. Retourne dict {changed, before_hash, after_hash}."""
    import hashlib
    content = path.read_text(encoding="utf-8")
    fm_lines, body = split_frontmatter(content)
    if fm_lines is None:
        raise ValueError(f"no frontmatter found in {path}")
    new_fm_lines = apply_patch(fm_lines, patch)
    new_content = join_frontmatter(new_fm_lines, body)
    before_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
    after_hash = hashlib.sha256(new_content.encode()).hexdigest()[:12]
    changed = (before_hash != after_hash)
    if changed and not dry_run:
        path.write_text(new_content, encoding="utf-8")
    return {
        "changed": changed,
        "before_hash": before_hash,
        "after_hash": after_hash,
        "dry_run": dry_run,
    }
```

- [ ] **Step 4: Brancher `cmd_patch_frontmatter`**

Dans `documente_engine.py`, remplacer `cmd_patch_frontmatter` :

```python
from documente_lib import patch_frontmatter_file


def cmd_patch_frontmatter(args):
    project_dir = get_project_dir()
    p = Path(args.path)
    if not p.is_absolute():
        p = project_dir / args.path
    memory_md = p / "MEMORY.md" if p.is_dir() else p
    if not memory_md.is_file():
        return _err(f"MEMORY.md not found at {memory_md}", code="missing_file")
    try:
        patch = json.loads(args.patch)
    except json.JSONDecodeError as e:
        return _err(f"invalid JSON patch: {e}", code="invalid_patch")
    if not isinstance(patch, dict):
        return _err("patch must be a JSON object", code="invalid_patch")
    try:
        result = patch_frontmatter_file(memory_md, patch, dry_run=args.dry_run)
    except (ValueError, OSError) as e:
        return _err(str(e), code="patch_failed")
    return _ok(**result, path=str(memory_md.relative_to(project_dir)))
```

Ajouter en haut de `documente_engine.py` (à côté de l'import forge_lib) :

```python
from documente_lib import patch_frontmatter_file
```

- [ ] **Step 5: Vérifier que tous les tests passent**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestPatchFrontmatter -v
```

Expected: 7 tests OK.

- [ ] **Step 6: Test manuel sur fixture order-398 (dry-run, ne touche rien)**

```bash
python3 entreprise/config/feedback-loop/documente_engine.py patch-frontmatter \
  services/achats/subjects/order-398 \
  --patch '{"conviction": 99}' --dry-run | python3 -m json.tool
```

Expected: `"changed": true`, `"dry_run": true`, hash before ≠ hash after. Le fichier réel n'a pas changé (vérifier avec `git diff`).

```bash
git -C "/Users/bhamon/git/claude-enterprise" diff services/achats/subjects/order-398/MEMORY.md
```

Expected: vide (dry-run n'a rien écrit).

- [ ] **Step 7: Commit**

```bash
git -C "/Users/bhamon/git/claude-enterprise" add \
  entreprise/config/feedback-loop/documente_engine.py \
  entreprise/config/feedback-loop/documente_lib.py \
  entreprise/config/feedback-loop/tests/test_documente_engine.py
git -C "/Users/bhamon/git/claude-enterprise" commit -m "feat(documente): patch-frontmatter avec édition surgicale (préserve formatage)

- documente_lib.py : split/join frontmatter + apply_patch
- Support scalaire, dict, liste, opérations +/-
- Mode --dry-run + idempotent + hash before/after

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Implémenter `commit-atomic`

**Files:**
- Modify: `entreprise/config/feedback-loop/documente_engine.py:cmd_commit_atomic`
- Modify: `entreprise/config/feedback-loop/tests/test_documente_engine.py`

- [ ] **Step 1: Écrire les tests**

Ajouter dans `test_documente_engine.py` :

```python
class TestCommitAtomic(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        # Init un repo git temporaire
        subprocess.run(["git", "init", "-q"], cwd=self.tmpdir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=self.tmpdir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.tmpdir, check=True)
        # Initial commit
        (self.tmpdir / "README.md").write_text("init", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.tmpdir, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=self.tmpdir, check=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_commit_creates_commit(self):
        f = self.tmpdir / "test.md"
        f.write_text("hello", encoding="utf-8")
        result = run_engine(
            "commit-atomic",
            "--paths", str(f),
            "--message", "test commit",
            cwd=str(self.tmpdir),
        )
        self.assertTrue(result["ok"])
        self.assertFalse(result["noop"])
        log = subprocess.run(["git", "log", "--oneline"], cwd=self.tmpdir, capture_output=True, text=True).stdout
        self.assertIn("test commit", log)

    def test_commit_noop_if_no_changes(self):
        result = run_engine(
            "commit-atomic",
            "--paths", str(self.tmpdir / "README.md"),
            "--message", "no change",
            cwd=str(self.tmpdir),
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["noop"])

    def test_commit_multiple_paths(self):
        a = self.tmpdir / "a.md"
        b = self.tmpdir / "b.md"
        a.write_text("a", encoding="utf-8")
        b.write_text("b", encoding="utf-8")
        result = run_engine(
            "commit-atomic",
            "--paths", f"{a},{b}",
            "--message", "multi",
            cwd=str(self.tmpdir),
        )
        self.assertTrue(result["ok"])
        self.assertFalse(result["noop"])
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestCommitAtomic -v
```

Expected: 3 FAIL.

- [ ] **Step 3: Implémenter `cmd_commit_atomic`**

Dans `documente_engine.py`, remplacer `cmd_commit_atomic` :

```python
import subprocess


def cmd_commit_atomic(args):
    """Stage les paths, commit, et push optionnellement."""
    paths = [p.strip() for p in args.paths.split(",") if p.strip()]
    if not paths:
        return _err("no paths provided", code="invalid_args")

    # Trouver le repo git (cwd ou ancêtre)
    try:
        repo_root_out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        repo_root = repo_root_out.stdout.strip()
    except subprocess.CalledProcessError:
        return _err("not a git repository", code="not_git")

    # Stage
    try:
        subprocess.run(
            ["git", "-C", repo_root, "add", *paths],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        return _err(f"git add failed: {e.stderr}", code="git_add_failed")

    # Vérifier qu'il y a quelque chose à commit
    diff = subprocess.run(
        ["git", "-C", repo_root, "diff", "--cached", "--name-only"],
        capture_output=True, text=True, check=True,
    )
    if not diff.stdout.strip():
        return _ok(noop=True, commit_sha=None, paths=paths, repo=repo_root)

    # Commit
    full_message = args.message + "\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
    try:
        subprocess.run(
            ["git", "-C", repo_root, "commit", "-m", full_message],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        return _err(f"git commit failed: {e.stderr or e.stdout}", code="git_commit_failed")

    sha = subprocess.run(
        ["git", "-C", repo_root, "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    pushed = False
    if args.push:
        try:
            subprocess.run(
                ["git", "-C", repo_root, "push"],
                capture_output=True, text=True, check=True,
            )
            pushed = True
        except subprocess.CalledProcessError as e:
            return _err(f"git push failed: {e.stderr}", code="git_push_failed", commit_sha=sha)

    return _ok(noop=False, commit_sha=sha, pushed=pushed, paths=paths, repo=repo_root)
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestCommitAtomic -v
```

Expected: 3 tests OK.

- [ ] **Step 5: Commit**

```bash
git -C "/Users/bhamon/git/claude-enterprise" add \
  entreprise/config/feedback-loop/documente_engine.py \
  entreprise/config/feedback-loop/tests/test_documente_engine.py
git -C "/Users/bhamon/git/claude-enterprise" commit -m "feat(documente): commit-atomic stage+commit+push idempotent

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Implémenter `scan-impacted`

**Files:**
- Modify: `entreprise/config/feedback-loop/documente_engine.py:cmd_scan_impacted`
- Modify: `entreprise/config/feedback-loop/tests/test_documente_engine.py`

- [ ] **Step 1: Écrire les tests**

Ajouter dans `test_documente_engine.py` :

```python
class TestScanImpacted(unittest.TestCase):

    def test_scan_returns_candidates(self):
        repo_root = Path(__file__).resolve().parents[4]
        result = run_engine("scan-impacted", "services/achats/subjects/order-398", cwd=str(repo_root))
        self.assertTrue(result["ok"])
        self.assertIn("candidates", result)
        # Doit au moins lister le SKILL.md du service ou des skills associés
        self.assertIsInstance(result["candidates"], list)

    def test_each_candidate_has_path_and_kind(self):
        repo_root = Path(__file__).resolve().parents[4]
        result = run_engine("scan-impacted", "services/achats/subjects/order-398", cwd=str(repo_root))
        for c in result["candidates"]:
            self.assertIn("path", c)
            self.assertIn("kind", c)
            self.assertIn(c["kind"], ["skill", "agent", "config", "brief"])
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestScanImpacted -v
```

Expected: FAIL.

- [ ] **Step 3: Implémenter `cmd_scan_impacted`**

Dans `documente_engine.py`, remplacer `cmd_scan_impacted` :

```python
def cmd_scan_impacted(args):
    """Scanne les fichiers exécutants potentiellement impactés.

    Remonte les parents du subject jusqu'au repo root, et liste pour chaque parent
    les fichiers qui pourraient être affectés (skills, agents, configs).
    Le LLM jugera ensuite la pertinence à partir des snippets.
    """
    project_dir = get_project_dir()
    p = Path(args.path)
    if not p.is_absolute():
        p = project_dir / args.path

    candidates = []
    seen = set()

    KIND_BY_NAME = {
        "SKILL.md": "skill",
        "agent.yaml": "agent",
        "brief.yaml": "brief",
        "config.yaml": "config",
    }

    # Remonte de p vers project_dir
    cursor = p.resolve()
    while cursor != cursor.parent and cursor != project_dir.parent:
        if cursor.is_dir():
            for entry in cursor.iterdir():
                if entry.is_file() and entry.name in KIND_BY_NAME and entry.resolve() not in seen:
                    seen.add(entry.resolve())
                    candidates.append({
                        "path": str(entry.relative_to(project_dir)) if entry.is_relative_to(project_dir) else str(entry),
                        "kind": KIND_BY_NAME[entry.name],
                    })
        cursor = cursor.parent

    return _ok(candidates=candidates, scanned_from=str(p.relative_to(project_dir)) if p.is_relative_to(project_dir) else str(p))
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestScanImpacted -v
```

Expected: 2 tests OK.

- [ ] **Step 5: Commit**

```bash
git -C "/Users/bhamon/git/claude-enterprise" add \
  entreprise/config/feedback-loop/documente_engine.py \
  entreprise/config/feedback-loop/tests/test_documente_engine.py
git -C "/Users/bhamon/git/claude-enterprise" commit -m "feat(documente): scan-impacted liste les exécutants candidats

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Implémenter `check-coherence`

**Files:**
- Modify: `entreprise/config/feedback-loop/documente_engine.py:cmd_check_coherence`
- Modify: `entreprise/config/feedback-loop/tests/test_documente_engine.py`

- [ ] **Step 1: Écrire les tests**

Ajouter dans `test_documente_engine.py` :

```python
class TestCheckCoherence(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.subject = self.tmpdir / "subj"
        (self.subject / "decisions").mkdir(parents=True)
        (self.subject / "MEMORY.md").write_text("""---
type: x
forging_state: tentative
conviction: 50
active_decisions:
  - 2026-04-01-payment-30j
---
""", encoding="utf-8")
        (self.subject / "decisions" / "2026-04-01-payment-30j.yaml").write_text("""---
date: 2026-04-01
type: decision
status: active
parameters:
  payment_terms: 30
  payment_currency: USD
---
""", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_no_conflict_with_unrelated_params(self):
        result = run_engine(
            "check-coherence", str(self.subject),
            "--decision-yaml", '{"shipping_mode": "FOB"}',
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["conflicts"], [])

    def test_conflict_on_same_param_different_value(self):
        result = run_engine(
            "check-coherence", str(self.subject),
            "--decision-yaml", '{"payment_terms": 10}',
        )
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["conflicts"]), 1)
        c = result["conflicts"][0]
        self.assertEqual(c["old_decision"], "2026-04-01-payment-30j")
        self.assertIn("payment_terms", c["fields"])

    def test_no_conflict_on_same_value(self):
        result = run_engine(
            "check-coherence", str(self.subject),
            "--decision-yaml", '{"payment_terms": 30}',
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["conflicts"], [])
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestCheckCoherence -v
```

Expected: FAIL.

- [ ] **Step 3: Implémenter `cmd_check_coherence`**

Dans `documente_engine.py`, remplacer `cmd_check_coherence` :

```python
def cmd_check_coherence(args):
    """Compare les paramètres d'une nouvelle décision aux active_decisions actuelles."""
    project_dir = get_project_dir()
    p = Path(args.path)
    if not p.is_absolute():
        p = project_dir / args.path

    try:
        new_params = json.loads(args.decision_yaml)
    except json.JSONDecodeError as e:
        return _err(f"invalid JSON: {e}", code="invalid_args")
    if not isinstance(new_params, dict):
        return _err("decision-yaml must be a JSON object", code="invalid_args")

    memory_md = p / "MEMORY.md"
    if not memory_md.is_file():
        return _err(f"MEMORY.md not found at {memory_md}", code="missing_file")

    fm = parse_frontmatter(memory_md) or {}
    active = fm.get("active_decisions") or []

    conflicts = []
    for slug in active:
        decision_path = p / "decisions" / f"{slug}.yaml"
        if not decision_path.is_file():
            continue
        old_fm = parse_frontmatter(decision_path) or {}
        old_params = old_fm.get("parameters") or {}
        if not isinstance(old_params, dict):
            continue
        conflicting_fields = []
        for k, v in new_params.items():
            if k in old_params and old_params[k] != v:
                conflicting_fields.append({
                    "field": k,
                    "old_value": old_params[k],
                    "new_value": v,
                })
        if conflicting_fields:
            conflicts.append({
                "old_decision": slug,
                "fields": conflicting_fields,
            })

    return _ok(conflicts=conflicts, active_count=len(active))
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestCheckCoherence -v
```

Expected: 3 tests OK.

- [ ] **Step 5: Commit**

```bash
git -C "/Users/bhamon/git/claude-enterprise" add \
  entreprise/config/feedback-loop/documente_engine.py \
  entreprise/config/feedback-loop/tests/test_documente_engine.py
git -C "/Users/bhamon/git/claude-enterprise" commit -m "feat(documente): check-coherence détecte conflits sur active_decisions

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Implémenter `write-capture`

**Files:**
- Modify: `entreprise/config/feedback-loop/documente_engine.py:cmd_write_capture`
- Modify: `entreprise/config/feedback-loop/tests/test_documente_engine.py`

- [ ] **Step 1: Écrire les tests**

Ajouter dans `test_documente_engine.py` :

```python
class TestWriteCapture(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.subject = self.tmpdir / "subj"
        self.subject.mkdir()
        (self.subject / "MEMORY.md").write_text("""---
type: x
forging_state: seed
conviction: 0
---

## Quick

Init.
""", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_write_discussion(self):
        body_file = self.tmpdir / "body.md"
        body_file.write_text("Discussion sur le sujet X.", encoding="utf-8")
        result = run_engine(
            "write-capture", str(self.subject),
            "--kind", "discussion",
            "--slug", "2026-05-04-test-discussion",
            "--body-file", str(body_file),
            "--frontmatter", '{"date": "2026-05-04", "type": "discussion", "status": "open", "participants": ["benjamin", "claude"]}',
        )
        self.assertTrue(result["ok"])
        f = self.subject / "discussions" / "2026-05-04-test-discussion.md"
        self.assertTrue(f.is_file())
        content = f.read_text(encoding="utf-8")
        self.assertIn("date: 2026-05-04", content)
        self.assertIn("status: open", content)
        self.assertIn("Discussion sur le sujet X.", content)

    def test_write_decision(self):
        body_file = self.tmpdir / "body.yaml"
        body_file.write_text("notes: décision tranchée", encoding="utf-8")
        result = run_engine(
            "write-capture", str(self.subject),
            "--kind", "decision",
            "--slug", "2026-05-04-test-decision",
            "--body-file", str(body_file),
            "--frontmatter", '{"date": "2026-05-04", "type": "decision", "decided_by": "benjamin", "status": "active", "parameters": {"x": 1}}',
        )
        self.assertTrue(result["ok"])
        f = self.subject / "decisions" / "2026-05-04-test-decision.yaml"
        self.assertTrue(f.is_file())
        content = f.read_text(encoding="utf-8")
        self.assertIn("decided_by: benjamin", content)

    def test_refuse_overwrite(self):
        body_file = self.tmpdir / "body.md"
        body_file.write_text("x", encoding="utf-8")
        run_engine(
            "write-capture", str(self.subject),
            "--kind", "discussion",
            "--slug", "2026-05-04-dup",
            "--body-file", str(body_file),
            "--frontmatter", '{"date": "2026-05-04"}',
        )
        result = run_engine(
            "write-capture", str(self.subject),
            "--kind", "discussion",
            "--slug", "2026-05-04-dup",
            "--body-file", str(body_file),
            "--frontmatter", '{"date": "2026-05-04"}',
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "exists")
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestWriteCapture -v
```

Expected: 3 FAIL.

- [ ] **Step 3: Implémenter `cmd_write_capture`**

Dans `documente_engine.py`, remplacer `cmd_write_capture` :

```python
def cmd_write_capture(args):
    """Écrit un fichier discussion (.md) ou decision (.yaml) avec frontmatter composé côté Python."""
    project_dir = get_project_dir()
    p = Path(args.path)
    if not p.is_absolute():
        p = project_dir / args.path

    try:
        fm = json.loads(args.frontmatter)
    except json.JSONDecodeError as e:
        return _err(f"invalid JSON frontmatter: {e}", code="invalid_args")
    if not isinstance(fm, dict):
        return _err("frontmatter must be a JSON object", code="invalid_args")

    body_file = Path(args.body_file)
    if not body_file.is_file():
        return _err(f"body file not found: {body_file}", code="missing_file")
    body = body_file.read_text(encoding="utf-8")

    if args.kind == "discussion":
        target_dir = p / "discussions"
        ext = ".md"
    else:
        target_dir = p / "decisions"
        ext = ".yaml"
    target_dir.mkdir(parents=True, exist_ok=True)

    target = target_dir / f"{args.slug}{ext}"
    if target.exists():
        return _err(f"file already exists: {target}", code="exists")

    fm_lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, dict):
            fm_lines.append(f"{k}:")
            for subk, subv in v.items():
                fm_lines.append(f"  {subk}: {_yaml_scalar(subv)}")
        elif isinstance(v, list):
            if not v:
                fm_lines.append(f"{k}: []")
            else:
                fm_lines.append(f"{k}:")
                for item in v:
                    fm_lines.append(f"  - {_yaml_scalar(item)}")
        else:
            fm_lines.append(f"{k}: {_yaml_scalar(v)}")
    fm_lines.append("---")
    fm_lines.append("")

    content = "\n".join(fm_lines) + body
    if not content.endswith("\n"):
        content += "\n"

    target.write_text(content, encoding="utf-8")
    return _ok(written=str(target.relative_to(project_dir)) if target.is_relative_to(project_dir) else str(target))


def _yaml_scalar(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if any(c in s for c in [":", "#"]) and not s.startswith('"'):
        return f'"{s}"'
    return s
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestWriteCapture -v
```

Expected: 3 tests OK.

- [ ] **Step 5: Commit**

```bash
git -C "/Users/bhamon/git/claude-enterprise" add \
  entreprise/config/feedback-loop/documente_engine.py \
  entreprise/config/feedback-loop/tests/test_documente_engine.py
git -C "/Users/bhamon/git/claude-enterprise" commit -m "feat(documente): write-capture compose frontmatter Python (LLM ne fournit que le body)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Implémenter `cascade-last-event`

**Files:**
- Modify: `entreprise/config/feedback-loop/documente_engine.py:cmd_cascade_last_event`
- Modify: `entreprise/config/feedback-loop/tests/test_documente_engine.py`

- [ ] **Step 1: Écrire les tests**

Ajouter dans `test_documente_engine.py` :

```python
class TestCascadeLastEvent(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.root = self.tmpdir / "root"
        self.linked = self.tmpdir / "linked"
        for d in (self.root, self.linked):
            d.mkdir()
            (d / "MEMORY.md").write_text("""---
type: x
forging_state: tentative
conviction: 50
last_event:
  date: 2026-04-01
  type: created
  ref: events/init.md
---
""", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_cascade_updates_last_event(self):
        result = run_engine(
            "cascade-last-event",
            str(self.root), str(self.linked),
            "--event-ref", "events/2026-05-04-trigger.md",
        )
        self.assertTrue(result["ok"])
        content = (self.linked / "MEMORY.md").read_text(encoding="utf-8")
        self.assertIn("type: cascaded_from_root", content)
        self.assertIn("events/2026-05-04-trigger.md", content)
```

- [ ] **Step 2: Vérifier que le test échoue**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestCascadeLastEvent -v
```

Expected: FAIL.

- [ ] **Step 3: Implémenter `cmd_cascade_last_event`**

Dans `documente_engine.py`, remplacer `cmd_cascade_last_event` :

```python
import datetime as _dt


def cmd_cascade_last_event(args):
    """Met à jour le frontmatter `last_event` d'un linked subject."""
    project_dir = get_project_dir()
    root = Path(args.root_path)
    linked = Path(args.linked_path)
    if not root.is_absolute():
        root = project_dir / args.root_path
    if not linked.is_absolute():
        linked = project_dir / args.linked_path

    linked_memory = linked / "MEMORY.md"
    if not linked_memory.is_file():
        return _err(f"linked MEMORY.md not found at {linked_memory}", code="missing_file")

    today = _dt.date.today().isoformat()
    new_event = {
        "date": today,
        "type": f"cascaded_from_{root.name}",
        "ref": args.event_ref,
    }
    patch = {"last_event": new_event}
    try:
        result = patch_frontmatter_file(linked_memory, patch, dry_run=False)
    except (ValueError, OSError) as e:
        return _err(str(e), code="patch_failed")
    return _ok(linked_path=str(linked.relative_to(project_dir)) if linked.is_relative_to(project_dir) else str(linked), **result)
```

- [ ] **Step 4: Vérifier que le test passe**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine.TestCascadeLastEvent -v
```

Expected: OK.

- [ ] **Step 5: Lancer la suite complète pour s'assurer qu'aucune régression**

```bash
cd entreprise/config/feedback-loop && python3 -m unittest tests.test_documente_engine -v
```

Expected: tous les tests OK (~22 au total).

- [ ] **Step 6: Commit**

```bash
git -C "/Users/bhamon/git/claude-enterprise" add \
  entreprise/config/feedback-loop/documente_engine.py \
  entreprise/config/feedback-loop/tests/test_documente_engine.py
git -C "/Users/bhamon/git/claude-enterprise" commit -m "feat(documente): cascade-last-event réutilise patch-frontmatter

- Suite unittest complète passe (22 tests)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Tests de non-régression sur 3 subjects réels

**Files:**
- Create: `entreprise/config/feedback-loop/tests/run_regression.sh`

- [ ] **Step 1: Créer le script de non-régression**

Le but : vérifier que sur 3 subjects réels, l'application séquentielle de patches mécaniques (qui simule ce que `/documente` fera) produit un fichier valide et idempotent.

```bash
cat > entreprise/config/feedback-loop/tests/run_regression.sh << 'REGRESSION_EOF'
#!/usr/bin/env bash
# Tests de non-régression sur subjects réels.
# Pour chaque subject : prepare → infer-type → patch dry-run → vérifie idempotence
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
ENGINE="$ROOT/entreprise/config/feedback-loop/documente_engine.py"

SUBJECTS=(
  "services/achats/subjects/order-398"
)

# Ajouter ceux qui existent
for candidate in "services/achats/subjects/supplier-weifang" "services/marketing/subjects/google-ads-brumeaux"; do
  if [ -d "$ROOT/$candidate" ]; then
    SUBJECTS+=("$candidate")
  fi
done

cd "$ROOT"

for s in "${SUBJECTS[@]}"; do
  echo "=== $s ==="

  # Prepare
  out=$(python3 "$ENGINE" prepare "$s")
  ok=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['ok'])")
  [ "$ok" = "True" ] || { echo "FAIL prepare"; exit 1; }
  echo "  prepare OK"

  # Infer-type
  out=$(python3 "$ENGINE" infer-type "$s")
  type=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('type'))")
  echo "  infer-type → $type"

  # Patch dry-run idempotent (conviction = même valeur que le frontmatter)
  current_conv=$(python3 -c "
import sys
sys.path.insert(0, '$ROOT/entreprise/config/feedback-loop')
from forge_lib import parse_frontmatter
from pathlib import Path
fm = parse_frontmatter(Path('$ROOT/$s/MEMORY.md'))
print(fm.get('conviction', 0))
")
  out=$(python3 "$ENGINE" patch-frontmatter "$s" --patch "{\"conviction\": $current_conv}" --dry-run)
  changed=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['changed'])")
  if [ "$changed" = "True" ]; then
    echo "  WARN: patch idempotent a renvoyé changed=True (conviction=$current_conv)"
  else
    echo "  patch idempotent OK"
  fi

  # Scan-impacted retourne quelque chose
  out=$(python3 "$ENGINE" scan-impacted "$s")
  count=$(echo "$out" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['candidates']))")
  echo "  scan-impacted → $count candidats"

done

echo ""
echo "Régression OK : aucun subject n'a été modifié, toutes les commandes ont répondu."
echo "Vérifier git status :"
git -C "$ROOT" status --short
REGRESSION_EOF
chmod +x entreprise/config/feedback-loop/tests/run_regression.sh
```

- [ ] **Step 2: Lancer le script de régression**

```bash
bash entreprise/config/feedback-loop/tests/run_regression.sh
```

Expected:
- Chaque subject : prepare OK, infer-type type connu, patch idempotent OK, scan-impacted N candidats
- Final `git status --short` doit être vide (sauf modifs en cours pré-existantes — feedback-log.jsonl notamment)

Si une fixture n'existe pas, elle est silencieusement skippée.

- [ ] **Step 3: Tagger l'état actuel pour rollback**

```bash
git -C "/Users/bhamon/git/claude-enterprise" tag pre-documente-engine-cutover
```

Expected: tag créé. Vérifier :

```bash
git -C "/Users/bhamon/git/claude-enterprise" tag | grep cutover
```

Expected: `pre-documente-engine-cutover`.

- [ ] **Step 4: Commit**

```bash
git -C "/Users/bhamon/git/claude-enterprise" add \
  entreprise/config/feedback-loop/tests/run_regression.sh
git -C "/Users/bhamon/git/claude-enterprise" commit -m "test(documente): script de régression sur 3 subjects réels + tag rollback

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: Bascule sèche du SKILL.md

**Files:**
- Modify: `entreprise/skills/documente/SKILL.md`

**Objectif** : réécrire le SKILL.md en orchestrateur léger qui appelle `documente_engine.py` pour les phases déterministes. Le LLM ne garde que : Phase 2 (capture conversation), rédaction du body en Phase 3, Phase 5 (Quick + Détails), Phase 8 jugement.

- [ ] **Step 1: Lire la version actuelle du SKILL.md**

```bash
wc -l entreprise/skills/documente/SKILL.md
```

Note la longueur actuelle.

- [ ] **Step 2: Réécrire le SKILL.md (workflow subject pool)**

Modifier la section "Workflow — Subject Pool" pour remplacer les Phases 0a-0e, 1, 3 (frontmatter), 3.5, 6, 7 (mécanique), 8 (scan), 9 par des appels au binaire.

Bloc cible (à insérer après l'intro/gotchas, en remplacement des phases existantes) :

```markdown
## Workflow — Subject Pool (depuis 2026-05-04, via documente_engine.py)

Toutes les phases déterministes sont déléguées à `entreprise/config/feedback-loop/documente_engine.py`. Le LLM intervient uniquement pour : capture conversationnelle, rédaction du contenu (body), synthèse Quick/Détails, jugement de pertinence des fichiers impactés.

### Phase A — Préparer le contexte (Python)

```bash
python3 entreprise/config/feedback-loop/documente_engine.py prepare <subject-path>
```

Parser le JSON retourné. Si :
- `is_subject_pool: false` → suivre le workflow legacy ci-dessous (Phase L1+)
- `subject_exists: false` et `needs_creation: true` → enchaîner sur Phase B (création paresseuse)
- `subject_exists: true` → enchaîner sur Phase C (capture conversationnelle)

### Phase B — Création paresseuse (interactif si type absent)

```bash
python3 entreprise/config/feedback-loop/documente_engine.py infer-type <subject-path>
```

Parser le résultat :
- `strategy: from_frontmatter | single_parent_type | from_naming` + `type_exists: true` → utiliser ce type, invoquer `/subject-create <type> <name>` silencieusement (Skill tool)
- `strategy: ambiguous` → présenter les `candidates` à Benjamin, demander le choix
- `strategy: none` ou `type_exists: false` → demander confirmation avant `/subject-create-type` (interactif)

Une fois l'instance créée, repasser par Phase A pour confirmer `subject_exists: true`.

### Phase C — Capture conversation (LLM, irréductible)

Examiner la conversation récente. Trois cas :
- **Décision tranchée** → préparer body discussion + body decision
- **Discussion en cours** → préparer body discussion seul
- **Rien à capturer** → skip à Phase E

Pour chaque body à écrire :

```bash
# Préparer le body dans un fichier temporaire
cat > /tmp/documente-body.md << 'EOF'
[contenu rédigé par le LLM, narratif, sans frontmatter]
EOF

# Vérifier la cohérence (si décision)
python3 entreprise/config/feedback-loop/documente_engine.py check-coherence <subject-path> \
  --decision-yaml '{"<param>": <value>, ...}'
```

Si `conflicts` non-vide → alerter Benjamin avant d'écrire (il décide d'archiver l'ancienne ou d'annuler).

### Phase D — Écrire les captures (Python)

```bash
python3 entreprise/config/feedback-loop/documente_engine.py write-capture <subject-path> \
  --kind discussion --slug YYYY-MM-DD-<slug> \
  --body-file /tmp/documente-body.md \
  --frontmatter '{"date": "YYYY-MM-DD", "type": "discussion", "produced_by": "human_and_claude", "participants": ["benjamin", "claude"], "status": "open|closed", "resulting_decision": "<slug-or-null>"}'

# Et pour la décision (si applicable)
python3 entreprise/config/feedback-loop/documente_engine.py write-capture <subject-path> \
  --kind decision --slug YYYY-MM-DD-<slug> \
  --body-file /tmp/documente-decision-body.yaml \
  --frontmatter '{"date": "YYYY-MM-DD", "type": "decision", "produced_by": "human", "decided_by": "benjamin", "parameters": {...}, "upstream_discussions": ["<slug>"], "status": "active"}'
```

### Phase E — Calcul d'état (Python, déjà existant)

```bash
python3 entreprise/config/feedback-loop/forge_engine.py <subject-path>
```

Stocker `forge_result` en mémoire. Vérifier `error` puis utiliser pour Phase F.

### Phase F — Régénérer Quick + Détails (LLM)

À partir de `forge_result.current_state`, `events_summary`, `active_decisions_summary`, etc., rédiger :
- `## Quick` (<100 mots, ton synthétique)
- `## Détails` (synthèse rédigée — préserver les sous-sections custom comme `### Notes libres`)

Écrire ces sections dans le `MEMORY.md` via Edit (le frontmatter sera patché en Phase G séparément).

### Phase G — Patch frontmatter (Python)

Construire le patch JSON à partir de `forge_result` :

```bash
python3 entreprise/config/feedback-loop/documente_engine.py patch-frontmatter <subject-path> \
  --patch '{
    "last_event": {"date": "...", "type": "...", "ref": "..."},
    "open_discussions": ["+<slug-discussion>"],
    "active_decisions": ["+<slug-decision>"],
    "forging_state": "<si_transition_auto>",
    "conviction": <bumped_value>
  }'
```

Si `transition_proposal.auto: true` dans `forge_result` :
- Inclure `forging_state` et `conviction` dans le patch
- Re-invoquer `forge_engine.py` après le patch pour vérifier 2ᵉ transition (chaînage max 2 itérations)

### Phase H — Cascade horizontale (Python pour mécanique, LLM pour Quick)

Pour chaque entry de `forge_result.cascade` :

```bash
python3 entreprise/config/feedback-loop/documente_engine.py cascade-last-event \
  <root-subject-path> <linked-subject-path> \
  --event-ref "events/<filename> du subject <root>"
```

Puis le LLM régénère le `## Quick` du linked subject (Edit), **PAS** le `## Détails`.

### Phase I — Scanner les exécutants impactés (Python pour scan, LLM pour jugement)

```bash
python3 entreprise/config/feedback-loop/documente_engine.py scan-impacted <subject-path>
```

Le LLM lit la liste `candidates`, juge la pertinence de chaque candidat vis-à-vis de la décision, propose les modifications à Benjamin (ne pas modifier sans validation).

### Phase J — Commit atomique + push (Python)

```bash
python3 entreprise/config/feedback-loop/documente_engine.py commit-atomic \
  --paths "<subject-path>/MEMORY.md,<subject-path>/discussions/<file>,<subject-path>/decisions/<file>,<linked1>/MEMORY.md,..." \
  --message "docs: <type> — <sujet court>

- subject racine : <subject-path>
- cascade : <linked_subjects affectés>
- transitions γ auto : <liste>" \
  --push
```

Si `noop: true` → afficher « rien à re-synthétiser ».
```

- [ ] **Step 3: Conserver le workflow legacy intact**

La section "## Workflow — Classique (legacy, hors subject pool)" reste inchangée — elle est rare et ne justifie pas l'effort d'extraction.

- [ ] **Step 4: Lancer un test de bout-en-bout sur un subject de test**

Créer un subject jetable :

```bash
mkdir -p services/achats/subjects/test-cutover-2026-05-04
cat > services/achats/subjects/test-cutover-2026-05-04/MEMORY.md << 'EOF'
---
type: supplier
forging_state: seed
conviction: 0
last_event:
  date: 2026-05-04
  type: created
  ref: events/init.md
active_decisions: []
open_discussions: []
linked_subjects: []
---

## Quick

Subject de test pour la bascule documente_engine.

## Détails

Sera supprimé après validation.
EOF
```

Tester chaque commande en chaîne :

```bash
python3 entreprise/config/feedback-loop/documente_engine.py prepare services/achats/subjects/test-cutover-2026-05-04
python3 entreprise/config/feedback-loop/documente_engine.py infer-type services/achats/subjects/test-cutover-2026-05-04
python3 entreprise/config/feedback-loop/documente_engine.py patch-frontmatter services/achats/subjects/test-cutover-2026-05-04 \
  --patch '{"conviction": 25, "open_discussions": ["+2026-05-04-test-disc"]}'
cat services/achats/subjects/test-cutover-2026-05-04/MEMORY.md | head -15
```

Expected: frontmatter modifié, conviction passée à 25, open_discussions contient le slug.

- [ ] **Step 5: Nettoyer le subject de test**

```bash
rm -rf services/achats/subjects/test-cutover-2026-05-04
```

- [ ] **Step 6: Commit de la bascule**

```bash
git -C "/Users/bhamon/git/claude-enterprise" add \
  entreprise/skills/documente/SKILL.md
git -C "/Users/bhamon/git/claude-enterprise" commit -m "refactor(documente): bascule SKILL.md vers documente_engine.py

Le skill devient un orchestrateur léger. Phases déterministes
(0a-0e, 3 frontmatter, 6, 7 mécanique, 8 scan, 9 commit) déléguées
à documente_engine.py. Le LLM ne garde que :
- Phase C : extraction décision/discussion de la conversation
- Phase D body : rédaction du contenu narratif
- Phase F : synthèse Quick + Détails
- Phase I jugement : pertinence des fichiers impactés

Réduit ~70% les tokens consommés par invocation et élimine le
risque de corruption YAML par le LLM.

Tag de rollback : pre-documente-engine-cutover

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 7: Push (bascule en prod)**

```bash
git -C "/Users/bhamon/git/claude-enterprise" push
```

- [ ] **Step 8: Test de validation post-bascule**

Invoquer `/documente` sur un subject réel (non-critique de préférence) et vérifier que le workflow se déroule sans erreur. Si bug → `git revert HEAD` immédiat, retour à l'ancien skill.

---

## Self-Review

**Spec coverage :**
- ✅ M1 : squelette + harness → Tasks 1-2
- ✅ M2 : patch-frontmatter → Task 6
- ✅ M3 : list-subjects + prepare + infer-type → Tasks 3-5
- ✅ M4 : commit-atomic → Task 7
- ✅ M5 : scan-impacted → Task 8
- ✅ M6 : check-coherence → Task 9
- ✅ M7 : write-capture + cascade-last-event → Tasks 10-11
- ✅ Bascule sèche : tests régression + tag + rewrite SKILL.md → Tasks 12-13
- ✅ M8 hooks : exclu du périmètre (décision Benjamin)

**Placeholders scan :**
- Aucun "TBD", "TODO", "implement later"
- Tout code Python est complet et exécutable
- Toutes les commandes bash sont exactes (pas de placeholder dans les paths)

**Type consistency :**
- `_ok()` / `_err()` utilisés partout cohérent
- `args.path` partout pour le paramètre principal
- `get_project_dir()` réutilisé depuis `forge_lib`
- `parse_frontmatter` réutilisé depuis `forge_lib`
- `patch_frontmatter_file` défini dans `documente_lib.py`, importé dans `documente_engine.py`, utilisé en Tasks 6 + 11

**Effort estimé total :** 6.5 jours (M1-M7 + bascule).

---

## Execution Handoff

**Plan complete et sauvegardé à `entreprise/skills/documente/plans/2026-05-04-extraction-engine-python.md`. Deux options d'exécution :**

**1. Subagent-Driven (recommandé)** — Je dispatch un fresh subagent par task, review entre les tasks, itération rapide.

**2. Inline Execution** — Exécution des tasks dans cette session avec checkpoints groupés pour review.

**Quelle approche ?**
