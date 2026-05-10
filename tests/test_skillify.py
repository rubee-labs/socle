#!/usr/bin/env python3
"""Tests unittest pour skillify_engine.py."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
ENGINE = BIN / "skillify_engine.py"


def run_engine(*args, env=None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    result = subprocess.run(
        [sys.executable, str(ENGINE), *args],
        capture_output=True,
        text=True,
        env=full_env,
    )
    if result.returncode not in (0, 1):
        raise AssertionError(
            f"engine crashed (exit {result.returncode}):\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
    if not result.stdout.strip():
        raise AssertionError(f"empty stdout (exit {result.returncode}, stderr: {result.stderr})")
    return json.loads(result.stdout), result.returncode


class TestScaffold(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        (self.tmpdir / ".git").mkdir()
        (self.tmpdir / "skills").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_scaffold_creates_5_stubs(self):
        result, exit_code = run_engine(
            "scaffold", "verify-webhooks",
            "--description", "Vérifie que les ngrok webhooks sont actifs et joignables depuis l'extérieur.",
            "--triggers", "verify webhook,check tunnel",
            env={"CLAUDE_FORGE_PROJECT_DIR": str(self.tmpdir)},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(exit_code, 0)
        skill_dir = self.tmpdir / "skills" / "verify-webhooks"
        self.assertTrue(skill_dir.is_dir())
        self.assertTrue((skill_dir / "SKILL.md").is_file())
        self.assertTrue((skill_dir / "scripts" / "verify-webhooks.py").is_file())
        self.assertTrue((skill_dir / "tests" / "test_verify-webhooks.py").is_file())
        self.assertTrue((skill_dir / "fixtures" / "verify-webhooks.routing.jsonl").is_file())
        self.assertTrue((skill_dir / "EVAL.md").is_file())
        # Triggers dans la fixture
        fixture = (skill_dir / "fixtures" / "verify-webhooks.routing.jsonl").read_text(encoding="utf-8")
        self.assertIn("verify webhook", fixture)
        self.assertIn("check tunnel", fixture)

    def test_scaffold_refuses_existing(self):
        skill_dir = self.tmpdir / "skills" / "existing-skill"
        skill_dir.mkdir()
        result, exit_code = run_engine(
            "scaffold", "existing-skill",
            env={"CLAUDE_FORGE_PROJECT_DIR": str(self.tmpdir)},
        )
        self.assertFalse(result["ok"])
        self.assertEqual(exit_code, 1)
        self.assertIn("existe déjà", result["error"])

    def test_scaffold_targets_entreprise_skills_when_present(self):
        """Si entreprise/skills/ existe, scaffold doit cibler là plutôt que skills/."""
        ent_skills = self.tmpdir / "entreprise" / "skills"
        ent_skills.mkdir(parents=True)
        result, exit_code = run_engine(
            "scaffold", "ent-skill",
            env={"CLAUDE_FORGE_PROJECT_DIR": str(self.tmpdir)},
        )
        self.assertTrue(result["ok"])
        self.assertTrue((ent_skills / "ent-skill" / "SKILL.md").is_file())
        # Pas dans skills/ root
        self.assertFalse((self.tmpdir / "skills" / "ent-skill" / "SKILL.md").exists())


class TestCheck(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.skill = self.tmpdir / "test-skill"
        self.skill.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _write_complete_skill(self, with_stubs=False):
        stub_marker = "SKILLIFY_STUB" if with_stubs else "real-content"
        (self.skill / "SKILL.md").write_text(f"""---
name: test-skill
description: >-
  Un skill complet pour les tests, suffisamment long pour passer le check 30 chars.
visibilité: entreprise
---

# Test Skill

## Quand utiliser

- Quand on teste

## Workflow

### Phase 1 — Préparation

Faire X.

## Gotchas

- Piège typique : Y

## Critères d'évaluation

- **EVAL 1** : marker={stub_marker}
""", encoding="utf-8")
        (self.skill / "scripts").mkdir()
        (self.skill / "tests").mkdir()

    def test_check_complete_skill_passes(self):
        self._write_complete_skill()
        result, exit_code = run_engine("check", str(self.skill))
        self.assertTrue(result["ok"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["summary"]["failed_critical"], [])

    def test_check_residual_stubs_fails_critical(self):
        self._write_complete_skill(with_stubs=True)
        result, exit_code = run_engine("check", str(self.skill))
        self.assertFalse(result["ok"])
        self.assertIn("no_residual_stubs", result["summary"]["failed_critical"])

    def test_check_missing_skill_md_fails(self):
        # Pas de SKILL.md
        result, exit_code = run_engine("check", str(self.skill))
        self.assertFalse(result["ok"])
        self.assertIn("skill_md_exists", result["summary"]["failed_critical"])

    def test_check_short_description_fails(self):
        (self.skill / "SKILL.md").write_text("""---
name: test-skill
description: short
---

# X

## Quand utiliser
- a
## Workflow
### Phase 1
B
## Gotchas
- c
## Critères d'évaluation
- EVAL 1
""", encoding="utf-8")
        result, exit_code = run_engine("check", str(self.skill))
        self.assertFalse(result["ok"])
        self.assertIn("description_long_enough", result["summary"]["failed_critical"])

    def test_check_distinguishes_critical_from_hygiene(self):
        """scripts_dir et tests_dir absents = warning, pas critique."""
        (self.skill / "SKILL.md").write_text("""---
name: test-skill
description: >-
  Un skill complet pour les tests, suffisamment long pour passer 30 chars.
---

# X

## Quand utiliser
- a
## Workflow
### Phase 1
B
## Gotchas
- c
## Critères d'évaluation
- EVAL 1 : marker
""", encoding="utf-8")
        # Pas de scripts/ ni tests/
        result, _ = run_engine("check", str(self.skill))
        self.assertTrue(result["ok"])  # ok parce que les hygiene checks ne bloquent pas
        self.assertEqual(set(result["summary"]["failed_hygiene"]),
                         {"scripts_dir", "tests_dir"})


class TestAudit(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        (self.tmpdir / ".git").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _write_minimal_skill(self, name, complete=True):
        sd = self.tmpdir / "skills" / name
        sd.mkdir(parents=True)
        if complete:
            (sd / "SKILL.md").write_text(f"""---
name: {name}
description: >-
  Skill {name} décrit suffisamment long pour passer le seuil de 30 caractères.
---

# {name}

## Quand utiliser
- cas
## Workflow
### Phase 1
fait X
## Gotchas
- piège
## Critères d'évaluation
- EVAL 1
""", encoding="utf-8")
        else:
            (sd / "SKILL.md").write_text("---\nname: bad\n---\n", encoding="utf-8")
        return sd

    def test_audit_classifies_skills(self):
        self._write_minimal_skill("good", complete=True)
        self._write_minimal_skill("bad", complete=False)
        result, _ = run_engine(
            "audit",
            env={"CLAUDE_FORGE_PROJECT_DIR": str(self.tmpdir)},
        )
        # 1 ok (warn pour hygiene) + 1 fail
        self.assertEqual(result["summary"]["fail"], 1)
        self.assertEqual(result["summary"]["warn"], 1)
        self.assertFalse(result["ok"])  # car 1 fail


if __name__ == "__main__":
    unittest.main()
