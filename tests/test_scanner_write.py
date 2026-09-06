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
