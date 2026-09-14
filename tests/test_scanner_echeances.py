#!/usr/bin/env python3
"""Tests du volet échéances du scanner (2026-09-14, analyse YOINK) —
décisions actives dont confirmation.echeance est passée sans verdict."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

from forge_scanner import detect_overdue_decisions  # noqa: E402


def _decision(status="active", echeance="2020-01-01", verdict=None):
    body = f"""---
date: 2026-01-01
type: decision
produced_by: human
decided_by: benjamin
status: {status}
---

contexte: >
  Un contexte de test.

decision: >
  Une règle de test.

confirmation:
  preuve: un fichier attendu
  echeance: {echeance}
"""
    if verdict:
        body += f"  verdict: {{date: {verdict}, resultat: tenue}}\n"
    return body


class TestOverdueDecisions(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.subject = self.tmpdir / "services" / "test" / "subjects" / "demo"
        (self.subject / "decisions").mkdir(parents=True)
        (self.subject / "MEMORY.md").write_text(
            "---\nname: demo\nforging_state: actif\n---\n\n## Quick\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _run(self):
        subjects = [(self.subject / "MEMORY.md", {"forging_state": "actif"})]
        return detect_overdue_decisions(subjects, project_dir=self.tmpdir)

    def _write(self, name, content):
        (self.subject / "decisions" / name).write_text(content, encoding="utf-8")

    def test_active_past_echeance_without_verdict_alerts(self):
        self._write("2026-01-01-test.yaml", _decision(echeance="2020-01-01"))
        alerts = self._run()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["type"], "decision_echue")
        self.assertIn("2020-01-01", alerts[0]["detail"])
        self.assertIn("decisions/2026-01-01-test.yaml", alerts[0]["subject"])

    def test_verdict_present_silences_alert(self):
        self._write("2026-01-01-test.yaml", _decision(echeance="2020-01-01", verdict="2020-01-02"))
        self.assertEqual(self._run(), [])

    def test_future_echeance_no_alert(self):
        self._write("2026-01-01-test.yaml", _decision(echeance="2099-01-01"))
        self.assertEqual(self._run(), [])

    def test_archived_decision_no_alert(self):
        self._write("2026-01-01-test.yaml", _decision(status="archived", echeance="2020-01-01"))
        self.assertEqual(self._run(), [])

    def test_decision_without_echeance_no_alert(self):
        self._write("2026-01-01-test.yaml", "---\nstatus: active\n---\n\ndecision: >\n  sans confirmation\n")
        self.assertEqual(self._run(), [])


if __name__ == "__main__":
    unittest.main()
