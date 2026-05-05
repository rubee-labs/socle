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
        field_names = [f["field"] for f in c["fields"]]
        self.assertIn("payment_terms", field_names)

    def test_no_conflict_on_same_value(self):
        result = run_engine(
            "check-coherence", str(self.subject),
            "--decision-yaml", '{"payment_terms": 30}',
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["conflicts"], [])


class TestScanImpacted(unittest.TestCase):

    def test_scan_returns_candidates(self):
        repo_root = Path(__file__).resolve().parents[4]
        result = run_engine("scan-impacted", "services/achats/subjects/order-398", cwd=str(repo_root))
        self.assertTrue(result["ok"])
        self.assertIn("candidates", result)
        self.assertIsInstance(result["candidates"], list)

    def test_each_candidate_has_path_and_kind(self):
        repo_root = Path(__file__).resolve().parents[4]
        result = run_engine("scan-impacted", "services/achats/subjects/order-398", cwd=str(repo_root))
        for c in result["candidates"]:
            self.assertIn("path", c)
            self.assertIn("kind", c)
            self.assertIn(c["kind"], ["skill", "agent", "config", "brief"])


class TestCommitAtomic(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q"], cwd=self.tmpdir, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=self.tmpdir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.tmpdir, check=True)
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
        run_engine("patch-frontmatter", str(self.subject), "--patch", '{"active_decisions": ["+a", "+b"]}')
        result = run_engine("patch-frontmatter", str(self.subject), "--patch", '{"active_decisions": ["-a"]}')
        self.assertTrue(result["ok"])
        content = self.memory.read_text(encoding="utf-8")
        self.assertNotIn("- a\n", content)
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


class TestInferType(unittest.TestCase):

    def test_infer_from_existing_frontmatter(self):
        repo_root = Path(__file__).resolve().parents[4]
        result = run_engine("infer-type", "services/achats/subjects/order-398", cwd=str(repo_root))
        self.assertTrue(result["ok"])
        self.assertEqual(result["strategy"], "from_frontmatter")
        self.assertIsNotNone(result["type"])

    def test_infer_from_naming_convention(self):
        # Si nom commence par <type>- et <type> existe dans parent/types/
        # supplier-XXX → type "supplier"
        repo_root = Path(__file__).resolve().parents[4]
        result = run_engine("infer-type", "services/achats/subjects/supplier-newone", cwd=str(repo_root))
        self.assertTrue(result["ok"])
        # Doit trouver "supplier" via naming (services/achats/types/supplier existe)
        self.assertEqual(result["type"], "supplier")
        self.assertEqual(result["strategy"], "from_naming")

    def test_no_match_returns_ambiguous_or_none(self):
        repo_root = Path(__file__).resolve().parents[4]
        # Subject avec un nom qui ne matche aucun type
        result = run_engine("infer-type", "services/achats/subjects/zzz-no-match-xyz", cwd=str(repo_root))
        self.assertTrue(result["ok"])
        self.assertIn(result.get("strategy"), ["ambiguous", "none"])


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


if __name__ == "__main__":
    unittest.main()
