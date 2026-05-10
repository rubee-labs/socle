#!/usr/bin/env python3
"""Tests unittest pour autolink_engine.py + helpers de forge_lib.py."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
ENGINE = BIN / "autolink_engine.py"

sys.path.insert(0, str(BIN))
from forge_lib import (  # noqa: E402
    parse_inline_dict,
    parse_subject_slug,
    parse_typed_linked_types,
)


def run_engine(*args, env=None):
    """Invoque autolink_engine.py et retourne le JSON parsé."""
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


class TestParseInlineDict(unittest.TestCase):

    def test_simple_dict(self):
        result = parse_inline_dict("{name: ordered_from, type: supplier}")
        self.assertEqual(result, {"name": "ordered_from", "type": "supplier"})

    def test_empty_dict(self):
        self.assertEqual(parse_inline_dict("{}"), {})

    def test_not_a_dict_returns_inline_marker(self):
        result = parse_inline_dict("plain string")
        self.assertEqual(result, {"_inline": "plain string"})


class TestParseTypedLinkedTypes(unittest.TestCase):

    def test_old_format_flat_list(self):
        result = parse_typed_linked_types(["supplier", "product-line"])
        self.assertEqual(result, [
            {"name": "supplier", "type": "supplier"},
            {"name": "product-line", "type": "product-line"},
        ])

    def test_new_format_inline_string(self):
        # tel que parse_simple_yaml l'expose : strings brutes commençant par {
        result = parse_typed_linked_types([
            "{name: ordered_from, type: supplier}",
            "{name: contains, type: product-line}",
        ])
        self.assertEqual(result, [
            {"name": "ordered_from", "type": "supplier"},
            {"name": "contains", "type": "product-line"},
        ])

    def test_new_format_dict(self):
        result = parse_typed_linked_types([
            {"name": "ordered_from", "type": "supplier"},
        ])
        self.assertEqual(result, [{"name": "ordered_from", "type": "supplier"}])

    def test_empty_input(self):
        self.assertEqual(parse_typed_linked_types([]), [])
        self.assertEqual(parse_typed_linked_types(None), [])

    def test_invalid_items_silently_ignored(self):
        result = parse_typed_linked_types([
            "{partial: only}",        # missing type
            {"name": "x"},            # missing type
            123,                      # not str/dict
            "supplier",               # valid old-format
        ])
        self.assertEqual(result, [{"name": "supplier", "type": "supplier"}])


class TestParseSubjectSlug(unittest.TestCase):

    def test_canonical_colon_format(self):
        result = parse_subject_slug("supplier:weifang")
        self.assertEqual(result["type"], "supplier")
        self.assertEqual(result["name"], "weifang")

    def test_dash_format_with_known_types(self):
        result = parse_subject_slug("supplier-weifang", known_types={"supplier", "product-line"})
        self.assertEqual(result["type"], "supplier")
        self.assertEqual(result["name"], "weifang")

    def test_dash_format_picks_longest_known_type(self):
        result = parse_subject_slug(
            "product-line-guirlande-guinguette",
            known_types={"supplier", "product-line", "product"},
        )
        self.assertEqual(result["type"], "product-line")
        self.assertEqual(result["name"], "guirlande-guinguette")

    def test_unknown_prefix_returns_none_type(self):
        result = parse_subject_slug("foo-bar-baz", known_types={"supplier"})
        self.assertIsNone(result["type"])
        self.assertEqual(result["name"], "foo-bar-baz")

    def test_empty_input(self):
        result = parse_subject_slug("")
        self.assertIsNone(result["type"])


class TestExtractCommand(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        # Faux repo Git
        (self.tmpdir / ".git").mkdir()
        # Type supplier-order avec typed_relations enrichis
        type_dir = self.tmpdir / "services" / "achats" / "types" / "supplier-order"
        type_dir.mkdir(parents=True)
        (type_dir / "REFERENCE.md").write_text("""---
type: supplier-order
typical_linked_types:
  - {name: ordered_from, type: supplier}
  - {name: contains, type: product-line}
  - {name: shipped_via, type: freight-forwarder}
---

# supplier-order
""", encoding="utf-8")
        # Type supplier (déclare juste son nom — utile pour known_types)
        (self.tmpdir / "services" / "achats" / "types" / "supplier").mkdir(parents=True)
        (self.tmpdir / "services" / "achats" / "types" / "supplier" / "REFERENCE.md").write_text("""---
type: supplier
typical_linked_types: []
---
""", encoding="utf-8")
        # Subject order-400 qui pointe vers supplier:simon
        subj_dir = self.tmpdir / "services" / "achats" / "subjects" / "order-400"
        subj_dir.mkdir(parents=True)
        (subj_dir / "MEMORY.md").write_text("""---
name: order-400
type: supplier-order
forging_state: tentative
conviction: 50
linked_subjects:
  - supplier:simon
  - product-line:guirlande-guinguette
---

# order-400
""", encoding="utf-8")
        self.subj_path = subj_dir

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_extract_returns_typed_edges(self):
        result, exit_code = run_engine(
            "extract", str(self.subj_path),
            env={"CLAUDE_FORGE_PROJECT_DIR": str(self.tmpdir)},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["subject_name"], "order-400")
        self.assertEqual(result["subject_type"], "supplier-order")
        edges = result["edges"]
        self.assertEqual(len(edges), 2)
        # Edge vers supplier:simon doit avoir le nom `ordered_from`
        supplier_edge = next(e for e in edges if e["target_type"] == "supplier")
        self.assertEqual(supplier_edge["name"], "ordered_from")
        self.assertEqual(supplier_edge["target_name"], "simon")
        # Edge vers product-line doit avoir le nom `contains`
        pl_edge = next(e for e in edges if e["target_type"] == "product-line")
        self.assertEqual(pl_edge["name"], "contains")

    def test_extract_no_frontmatter_returns_error(self):
        bad = self.tmpdir / "services" / "achats" / "subjects" / "no-frontmatter"
        bad.mkdir(parents=True)
        (bad / "MEMORY.md").write_text("just text, no frontmatter\n", encoding="utf-8")
        result, exit_code = run_engine(
            "extract", str(bad),
            env={"CLAUDE_FORGE_PROJECT_DIR": str(self.tmpdir)},
        )
        self.assertFalse(result["ok"])
        self.assertEqual(exit_code, 1)


class TestGraphQueryCommand(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        (self.tmpdir / ".git").mkdir()
        # Type supplier-order
        t1 = self.tmpdir / "services" / "achats" / "types" / "supplier-order"
        t1.mkdir(parents=True)
        (t1 / "REFERENCE.md").write_text("""---
type: supplier-order
typical_linked_types:
  - {name: ordered_from, type: supplier}
---
""", encoding="utf-8")
        t2 = self.tmpdir / "services" / "achats" / "types" / "supplier"
        t2.mkdir(parents=True)
        (t2 / "REFERENCE.md").write_text("""---
type: supplier
typical_linked_types: []
---
""", encoding="utf-8")
        # 3 orders qui pointent toutes vers supplier:simon
        for n in ("400", "401", "402"):
            sd = self.tmpdir / "services" / "achats" / "subjects" / f"order-{n}"
            sd.mkdir(parents=True)
            (sd / "MEMORY.md").write_text(f"""---
name: order-{n}
type: supplier-order
linked_subjects:
  - supplier:simon
---
""", encoding="utf-8")
        # Le supplier lui-même
        sd = self.tmpdir / "services" / "achats" / "subjects" / "simon"
        sd.mkdir(parents=True)
        (sd / "MEMORY.md").write_text("""---
name: simon
type: supplier
linked_subjects: []
---
""", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_incoming_edges_to_supplier(self):
        # Toutes les commandes pointent vers supplier:simon avec ordered_from
        result, exit_code = run_engine(
            "graph-query", "supplier:simon",
            "--type", "ordered_from",
            "--direction", "incoming",
            env={"CLAUDE_FORGE_PROJECT_DIR": str(self.tmpdir)},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(exit_code, 0)
        # 3 orders incoming
        sources = {m["from"] for m in result["matches"] if m["direction"] == "incoming"}
        self.assertEqual(sources, {
            "supplier-order:order-400",
            "supplier-order:order-401",
            "supplier-order:order-402",
        })
        for m in result["matches"]:
            self.assertEqual(m["name"], "ordered_from")

    def test_filter_by_edge_type_excludes_non_matching(self):
        result, _ = run_engine(
            "graph-query", "supplier:simon",
            "--type", "shipped_via",  # aucun match attendu
            env={"CLAUDE_FORGE_PROJECT_DIR": str(self.tmpdir)},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["matches"], [])


if __name__ == "__main__":
    unittest.main()
