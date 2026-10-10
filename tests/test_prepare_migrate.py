"""prepare 0.7.0 (subject = en-tête) et forge migrate --dry-run."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
sys.path.insert(0, str(BIN))
from forge_lib import find_subjects, iter_memory_files  # noqa: E402

RULES = 'type_by_path:\n  - {pattern: "*/tools/*", type: tool}\n'


def _run(*args, project, via_forge=False):
    cmd = ["bash", str(BIN / "forge"), *args] if via_forge else [sys.executable, str(BIN / "documente_engine.py"), *args]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=project,
                         env={"CLAUDE_FORGE_PROJECT_DIR": str(project), "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin"})
    return json.loads(out.stdout)


def _repo(tmp_path):
    (tmp_path / ".forge.yaml").write_text(RULES, encoding="utf-8")
    for rel, fm in (("entreprise/tools/factures", "entite: factures"),
                    ("docs/notes", "entite: notes"),
                    ("services/achats/subjects/order-1", "name: order-1\ntype: projet\nforging_state: actif")):
        d = tmp_path / rel
        d.mkdir(parents=True)
        (d / "MEMORY.md").write_text(f"---\n{fm}\n---\n", encoding="utf-8")
    return tmp_path


def test_prepare_subject(tmp_path):
    r = _run("prepare", "services/achats/subjects/order-1", project=_repo(tmp_path))
    assert r["is_subject"] and not r["needs_conversion"] and not r["needs_creation"]
    assert r["type"] == "projet" and r["type_source"] == "frontmatter"
    assert r["capabilities"] == ["memory", "decisions", "lifecycle", "events", "links"]
    assert "is_subject_pool" not in r and "recommended_workflow" not in r


def test_prepare_ancien_format_hors_subjects(tmp_path):
    r = _run("prepare", "entreprise/tools/factures", project=_repo(tmp_path))
    assert not r["is_subject"] and r["needs_conversion"]
    assert r["type"] == "tool" and r["type_source"] == "type_by_path"
    assert r["capabilities"] == ["memory", "decisions", "lifecycle"]
    assert r["default_name"] == "factures"


def test_prepare_type_a_choisir(tmp_path):
    r = _run("prepare", "docs/notes", project=_repo(tmp_path))
    assert r["type"] is None and r["type_source"] == "claude"
    assert "tool" in r["known_types"] and "projet" in r["known_types"]


def test_prepare_dossier_neuf(tmp_path):
    r = _run("prepare", "entreprise/projets/neuf", project=_repo(tmp_path))
    assert r["needs_creation"] and not r["subject_exists"]


def test_migrate_exige_dry_run(tmp_path):
    r = _run("migrate", project=_repo(tmp_path), via_forge=True)
    assert not r["ok"] and r["code"] == "dry_run_required"


def test_migrate_liste_sans_ecrire(tmp_path):
    root = _repo(tmp_path)
    avant = {p: p.read_text(encoding="utf-8") for p in iter_memory_files(root)}
    r = _run("migrate", "--dry-run", project=root, via_forge=True)
    assert r["ok"] and r["total"] == 2
    assert {x["path"]: x["type"] for x in r["pending"]} == {"docs/notes": None, "entreprise/tools/factures": "tool"}
    assert r["by_source"] == {"claude": 1, "type_by_path": 1}
    assert {p: p.read_text(encoding="utf-8") for p in iter_memory_files(root)} == avant
    # cohérence : à convertir + subjects = tous les MEMORY.md
    assert r["total"] + len(find_subjects(root)) == len(avant)
