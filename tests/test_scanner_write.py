"""write_if_changed : pas de réécriture quand seul l'horodatage change."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
import forge_scanner  # noqa: E402


def _render(ts, body):
    return f"# SUBJECTS-INDEX\n\n_Régénéré automatiquement par forge_scanner.py — {ts}_\n\n{body}"


def test_skip_when_only_timestamp_differs(tmp_path):
    f = tmp_path / "SUBJECTS-INDEX.md"
    assert forge_scanner.write_if_changed(f, _render("2026-09-06T08:00:00", "41 subjects")) is True
    before = f.read_text(encoding="utf-8")
    assert forge_scanner.write_if_changed(f, _render("2026-09-06T09:00:00", "41 subjects")) is False
    assert f.read_text(encoding="utf-8") == before


def test_write_when_content_differs(tmp_path):
    f = tmp_path / "SUBJECTS-INDEX.md"
    forge_scanner.write_if_changed(f, _render("2026-09-06T08:00:00", "41 subjects"))
    assert forge_scanner.write_if_changed(f, _render("2026-09-06T09:00:00", "42 subjects")) is True
    assert "42 subjects" in f.read_text(encoding="utf-8")


def test_creates_missing_file(tmp_path):
    f = tmp_path / "sub" / "METRICS.md"
    assert forge_scanner.write_if_changed(f, "x") is True
    assert f.read_text(encoding="utf-8") == "x"


def test_status_n_ecrit_rien(tmp_path):
    """`scanner --status` est un compteur : aucun index écrit (0.7.3)."""
    import os
    import subprocess
    subj = tmp_path / "subjects" / "demo"
    subj.mkdir(parents=True)
    (subj / "MEMORY.md").write_text("---\nname: demo\nforging_state: actif\n---\n\n## Quick\n",
                                    encoding="utf-8")
    (tmp_path / ".forge.yaml").write_text("output_dir: .\n", encoding="utf-8")
    scanner = Path(__file__).resolve().parents[1] / "bin" / "forge_scanner.py"
    env = dict(os.environ, CLAUDE_FORGE_PROJECT_DIR=str(tmp_path))
    avant = sorted(p for p in tmp_path.rglob("*"))
    r = subprocess.run([sys.executable, str(scanner), "--status"], env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0 and "Forge:" in r.stdout
    assert sorted(p for p in tmp_path.rglob("*")) == avant
    subprocess.run([sys.executable, str(scanner)], env=env, capture_output=True, check=True)
    assert list(tmp_path.rglob("SUBJECTS-INDEX.md"))
