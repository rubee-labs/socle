#!/usr/bin/env python3
"""Tests unittest pour eval_engine.py."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
ENGINE = BIN / "eval_engine.py"


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


class TestPrepare(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        (self.tmpdir / ".git").mkdir()
        # Subject avec frontmatter + sources
        self.subj = self.tmpdir / "services" / "achats" / "subjects" / "order-test"
        self.subj.mkdir(parents=True)
        (self.subj / "MEMORY.md").write_text("""---
name: order-test
type: supplier-order
forging_state: tentative
conviction: 50
---

## Quick

État : tentative
Liens forts : ordered_from supplier:simon

## Détails

Synthèse de la commande.
""", encoding="utf-8")
        for kind in ("events", "discussions", "decisions"):
            (self.subj / kind).mkdir()
        (self.subj / "events" / "2026-04-15-alerte-stock.md").write_text(
            "---\ndate: 2026-04-15\ntype: email\n---\nAlerte stock.\n", encoding="utf-8")
        (self.subj / "decisions" / "2026-04-16-order-placed.yaml").write_text(
            "---\ndate: 2026-04-16\ntype: decision\nstatus: active\n---\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_prepare_returns_prompt_and_sources(self):
        result, exit_code = run_engine(
            "prepare", str(self.subj),
            env={"CLAUDE_FORGE_PROJECT_DIR": str(self.tmpdir)},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["subject_name"], "order-test")
        self.assertEqual(result["subject_type"], "supplier-order")
        # Le prompt doit mentionner les 4 axes
        prompt = result["prompt"]
        for axis in ("coherence", "completeness", "specificity", "citations"):
            self.assertIn(axis, prompt)
        # Sources scannées
        self.assertEqual(result["sources_summary"]["events"], 1)
        self.assertEqual(result["sources_summary"]["decisions"], 1)
        self.assertEqual(result["sources_summary"]["discussions"], 0)
        # 3 modèles attendus
        self.assertEqual(len(result["expected_models"]), 3)

    def test_prepare_no_memory_returns_error(self):
        bad = self.tmpdir / "no-memory"
        bad.mkdir()
        result, exit_code = run_engine(
            "prepare", str(bad),
            env={"CLAUDE_FORGE_PROJECT_DIR": str(self.tmpdir)},
        )
        self.assertFalse(result["ok"])
        self.assertEqual(exit_code, 1)


class TestAggregate(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _write_result(self, name, scores):
        """scores: dict axis -> {score, issues, suggestions}."""
        f = self.tmpdir / f"{name}.json"
        f.write_text(json.dumps(scores, ensure_ascii=False), encoding="utf-8")
        return str(f)

    def test_aggregate_3_evaluators(self):
        f1 = self._write_result("opus", {
            "coherence": {"score": 8, "issues": ["issue A"], "suggestions": ["sug A"]},
            "completeness": {"score": 6, "issues": ["issue B"], "suggestions": []},
            "specificity": {"score": 7, "issues": [], "suggestions": []},
            "citations": {"score": 9, "issues": [], "suggestions": []},
        })
        f2 = self._write_result("sonnet", {
            "coherence": {"score": 9, "issues": ["issue A"], "suggestions": []},
            "completeness": {"score": 5, "issues": ["issue C"], "suggestions": ["sug C"]},
            "specificity": {"score": 6, "issues": [], "suggestions": []},
            "citations": {"score": 8, "issues": [], "suggestions": []},
        })
        f3 = self._write_result("haiku", {
            "coherence": {"score": 8, "issues": [], "suggestions": []},
            "completeness": {"score": 8, "issues": [], "suggestions": []},
            "specificity": {"score": 8, "issues": [], "suggestions": []},
            "citations": {"score": 7, "issues": [], "suggestions": []},
        })
        result, exit_code = run_engine("aggregate", "--results", f1, f2, f3)
        self.assertTrue(result["ok"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["evaluator_count"], 3)
        # coherence : (8+9+8)/3 = 8.33...
        self.assertAlmostEqual(result["axes"]["coherence"]["score_mean"], 8.3, places=1)
        self.assertEqual(result["axes"]["coherence"]["score_min"], 8)
        self.assertEqual(result["axes"]["coherence"]["score_max"], 9)
        # Issues dédupliquées : "issue A" présent 2 fois, ne doit apparaître qu'une fois
        coherence_issues = result["axes"]["coherence"]["issues"]
        self.assertEqual(coherence_issues.count("issue A"), 1)
        # Suggestions agrégées
        completeness_sugs = result["axes"]["completeness"]["suggestions"]
        self.assertIn("sug C", completeness_sugs)

    def test_aggregate_handles_missing_axis(self):
        """Un évaluateur peut avoir omis un axe — l'agrégation ne plante pas."""
        f1 = self._write_result("partial", {
            "coherence": {"score": 7, "issues": [], "suggestions": []},
            # completeness, specificity, citations manquants
        })
        result, _ = run_engine("aggregate", "--results", f1)
        self.assertTrue(result["ok"])
        self.assertEqual(result["axes"]["coherence"]["score_mean"], 7.0)
        # Axes manquants = score_mean None
        self.assertIsNone(result["axes"]["completeness"]["score_mean"])

    def test_aggregate_invalid_json_fails(self):
        bad = self.tmpdir / "bad.json"
        bad.write_text("not json {{{", encoding="utf-8")
        result, exit_code = run_engine("aggregate", "--results", str(bad))
        self.assertFalse(result["ok"])
        self.assertEqual(exit_code, 1)


class TestWriteAnalysis(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.subj = self.tmpdir / "subject"
        self.subj.mkdir()
        (self.subj / "MEMORY.md").write_text("---\nname: x\n---\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_write_analysis_creates_file(self):
        score = {
            "evaluator_count": 3,
            "overall_score": 7.3,
            "axes": {
                "coherence": {"score_mean": 8.3, "score_min": 8, "score_max": 9, "score_count": 3,
                              "issues": ["X"], "suggestions": ["Y"]},
                "completeness": {"score_mean": 6.0, "score_min": 5, "score_max": 7, "score_count": 3,
                                 "issues": [], "suggestions": []},
                "specificity": {"score_mean": 7.0, "score_min": 6, "score_max": 8, "score_count": 3,
                                "issues": [], "suggestions": []},
                "citations": {"score_mean": 8.0, "score_min": 7, "score_max": 9, "score_count": 3,
                              "issues": [], "suggestions": []},
            },
        }
        result, exit_code = run_engine(
            "write-analysis", str(self.subj),
            "--score", json.dumps(score),
        )
        self.assertTrue(result["ok"])
        self.assertEqual(exit_code, 0)
        analysis_path = Path(result["analysis_path"])
        self.assertTrue(analysis_path.is_file())
        content = analysis_path.read_text(encoding="utf-8")
        # Frontmatter
        self.assertIn("type: analysis", content)
        self.assertIn("produced_by: claude", content)
        self.assertIn("evaluator_count: 3", content)
        # Score global affiché
        self.assertIn("7.3", content)
        # Issue présente
        self.assertIn("- X", content)
        # Suggestion présente
        self.assertIn("- Y", content)


if __name__ == "__main__":
    unittest.main()
