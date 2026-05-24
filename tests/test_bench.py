"""Tests minimaux pour bench_engine.py.

Couvre les 3 sous-commandes (prepare, run, report) sur un repo synthétique.
Pas de dépendance externe — tout est généré dans un tmpdir.
"""
import json
import subprocess
import sys
from pathlib import Path

BIN = Path(__file__).parent.parent / "bin"
sys.path.insert(0, str(BIN))

from bench_engine import (
    aggregate,
    find_subjects,
    generate_questions,
    retriever_r3_filesystem_grep,
    score,
)


def _make_subject(root, name, **fm_extra):
    """Crée un MEMORY.md minimal pour un subject de test."""
    subject_dir = root / "subjects" / name
    subject_dir.mkdir(parents=True, exist_ok=True)
    fm_lines = [
        "---",
        f"name: {name}",
        f"type: test-type",
        f"forging_state: actif",
        f"horizon: bounded",
    ]
    for k, v in fm_extra.items():
        fm_lines.append(f"{k}: {v}")
    fm_lines.append("---")
    fm_lines.append("")
    fm_lines.append("## Quick")
    fm_lines.append("")
    fm_lines.append(f"État de test pour {name}.")
    (subject_dir / "MEMORY.md").write_text("\n".join(fm_lines), encoding="utf-8")
    return subject_dir / "MEMORY.md"


def test_find_subjects(tmp_path):
    _make_subject(tmp_path, "alpha")
    _make_subject(tmp_path, "beta")
    # MEMORY.md sans forging_state ne doit pas être ramassé
    (tmp_path / "subjects" / "nope").mkdir(parents=True)
    (tmp_path / "subjects" / "nope" / "MEMORY.md").write_text(
        "---\nname: nope\n---\n", encoding="utf-8"
    )
    import os
    os.environ["CLAUDE_FORGE_PROJECT_DIR"] = str(tmp_path)
    try:
        # Re-import des helpers qui lisent la var d'env
        import importlib
        import forge_lib
        importlib.reload(forge_lib)
        import bench_engine
        importlib.reload(bench_engine)
        subjects = bench_engine.find_subjects(tmp_path)
    finally:
        del os.environ["CLAUDE_FORGE_PROJECT_DIR"]
    names = [fm.get("name") for _, fm in subjects]
    assert "alpha" in names
    assert "beta" in names
    assert "nope" not in names


def test_generate_questions_basic(tmp_path):
    _make_subject(tmp_path, "alpha")
    _make_subject(tmp_path, "beta", linked_subjects="[test-type:alpha]")
    from forge_lib import parse_frontmatter
    subjects = [(p, parse_frontmatter(p)) for p in tmp_path.rglob("MEMORY.md")]
    questions = generate_questions(subjects)
    # alpha : forging_state + type + horizon = 3 questions
    # beta : forging_state + type + horizon + linked = 4 questions
    assert len(questions) == 7
    fields = {q["field"] for q in questions}
    assert {"forging_state", "type", "horizon", "linked_subjects"}.issubset(fields)


def test_score_exact_and_substring():
    q = {"gold": "actif"}
    assert score(q, {"found": True, "answer": "actif"}) == {"exact": True, "substring": True}
    assert score(q, {"found": True, "answer": "ACTIF"}) == {"exact": True, "substring": True}
    assert score(q, {"found": True, "answer": "mature"}) == {"exact": False, "substring": False}
    assert score(q, {"found": False}) == {"exact": False, "substring": False}


def test_aggregate():
    results = [
        {"retriever": "R1", "retriever_label": "cascade", "exact": True, "substring": True, "latency_ms": 5},
        {"retriever": "R1", "retriever_label": "cascade", "exact": True, "substring": True, "latency_ms": 10},
        {"retriever": "R1", "retriever_label": "cascade", "exact": False, "substring": True, "latency_ms": 15},
    ]
    summary = aggregate(results)
    assert summary["R1"]["n"] == 3
    assert summary["R1"]["exact_count"] == 2
    assert summary["R1"]["substring_count"] == 3
    assert summary["R1"]["exact_rate"] == round(2/3, 3)


def test_retriever_r3_filesystem_grep(tmp_path):
    _make_subject(tmp_path, "alpha")
    q = {"subject_name": "alpha", "field": "forging_state", "gold": "actif"}
    result = retriever_r3_filesystem_grep(q, tmp_path)
    assert result["found"] is True
    assert result["answer"] == "actif"


def test_cli_smoke(tmp_path):
    """Smoke test des 3 sous-commandes via CLI."""
    _make_subject(tmp_path, "alpha")
    _make_subject(tmp_path, "beta")
    # SUBJECTS-INDEX minimal pour R1
    index_dir = tmp_path / "entreprise"
    index_dir.mkdir(exist_ok=True)
    (index_dir / "SUBJECTS-INDEX.md").write_text(
        "# SUBJECTS-INDEX\n\n"
        "- **alpha** (test-type) — `subjects/alpha/`\n"
        "- **beta** (test-type) — `subjects/beta/`\n",
        encoding="utf-8",
    )

    env = {"CLAUDE_FORGE_PROJECT_DIR": str(tmp_path), "PATH": __import__("os").environ.get("PATH", "")}
    corpus_path = tmp_path / "corpus.json"
    results_path = tmp_path / "results.json"

    # prepare
    r = subprocess.run(
        [sys.executable, str(BIN / "bench_engine.py"), "prepare",
         "--out", str(corpus_path)],
        env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert corpus_path.exists()
    corpus = json.loads(corpus_path.read_text())
    assert corpus["question_count"] >= 6

    # run
    r = subprocess.run(
        [sys.executable, str(BIN / "bench_engine.py"), "run",
         "--corpus", str(corpus_path), "--out", str(results_path)],
        env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert results_path.exists()
    results = json.loads(results_path.read_text())
    assert results["total_calls"] == corpus["question_count"] * 3

    # report
    r = subprocess.run(
        [sys.executable, str(BIN / "bench_engine.py"), "report",
         "--results", str(results_path)],
        env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "Récap par retriever" in r.stdout


def _parse_fm(path):
    """Tiny frontmatter parser for the tests (avoids reload dance)."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 4)
    if end < 0:
        return {}
    fm = {}
    for line in content[4:end].strip().split("\n"):
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm
