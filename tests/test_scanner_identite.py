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
