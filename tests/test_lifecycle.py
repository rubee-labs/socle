#!/usr/bin/env python3
"""Tests du cycle de vie 2 états (refonte 2026-09-14) — mapping legacy → actif/archived."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

from forge_engine import LEGACY_STATE_MAP, normalize_forging_state  # noqa: E402


class TestLifecycle2States(unittest.TestCase):

    def test_all_legacy_states_map_to_actif(self):
        for legacy in ("seed", "debating", "tentative", "stress_testing",
                       "doctrine", "in_service", "under_review", "mature"):
            normalized, was_legacy = normalize_forging_state(legacy)
            self.assertEqual(normalized, "actif", f"{legacy} devrait mapper vers actif")
            self.assertTrue(was_legacy, f"{legacy} devrait être flaggé legacy")

    def test_current_states_passthrough(self):
        self.assertEqual(normalize_forging_state("actif"), ("actif", False))
        self.assertEqual(normalize_forging_state("archived"), ("archived", False))

    def test_unknown_and_empty_default_to_actif(self):
        self.assertEqual(normalize_forging_state("n_importe_quoi"), ("actif", False))
        self.assertEqual(normalize_forging_state(None), ("actif", False))
        self.assertEqual(normalize_forging_state(""), ("actif", False))

    def test_map_targets_only_two_states(self):
        self.assertEqual(set(LEGACY_STATE_MAP.values()), {"actif", "archived"})


if __name__ == "__main__":
    unittest.main()
