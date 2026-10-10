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
