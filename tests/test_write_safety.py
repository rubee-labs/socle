"""Tests pour `expected_hash` write safety (patch_frontmatter_file).

Pattern adopté d'Optimike Obsidian MCP `expectedHash` (analyse Forge-Lab #7
2026-05-26). Couvre :
- backward compat (sans expected_hash → comportement actuel)
- hash correct → write OK
- hash incorrect → refus explicite, pas d'overwrite
- workflow compute-hash + patch-frontmatter via CLI
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BIN = Path(__file__).parent.parent / "bin"
sys.path.insert(0, str(BIN))

from documente_lib import patch_frontmatter_file


def _make_memory(tmp_path, name="alpha", state="actif"):
    content = (
        "---\n"
        f"name: {name}\n"
        "type: test-type\n"
        f"forging_state: {state}\n"
        "horizon: bounded\n"
        "---\n"
        "\n"
        "## Quick\n"
        "\n"
        f"Test for {name}.\n"
    )
    memory = tmp_path / "MEMORY.md"
    memory.write_text(content, encoding="utf-8")
    return memory, content


def _hash(content):
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def test_backward_compat_no_expected_hash(tmp_path):
    """Sans expected_hash, comportement inchangé (backward compat)."""
    memory, content = _make_memory(tmp_path)
    result = patch_frontmatter_file(memory, {"forging_state": "mature"})
    assert result["changed"] is True
    assert result["stale_hash"] is False
    assert result["before_hash"] == _hash(content)
    # Le fichier a été modifié
    new_content = memory.read_text(encoding="utf-8")
    assert "forging_state: mature" in new_content


def test_expected_hash_correct_allows_write(tmp_path):
    """Hash correct → write OK."""
    memory, content = _make_memory(tmp_path)
    current_hash = _hash(content)
    result = patch_frontmatter_file(
        memory, {"forging_state": "mature"},
        expected_hash=current_hash,
    )
    assert result["changed"] is True
    assert result["stale_hash"] is False
    assert result["before_hash"] == current_hash


def test_expected_hash_stale_refuses_write(tmp_path):
    """Hash incorrect → refus, fichier inchangé."""
    memory, content = _make_memory(tmp_path)
    result = patch_frontmatter_file(
        memory, {"forging_state": "mature"},
        expected_hash="0000000000ab",  # bidon
    )
    assert result["changed"] is False
    assert result["stale_hash"] is True
    assert result["expected_hash"] == "0000000000ab"
    assert result["before_hash"] == _hash(content)
    # Le fichier doit être identique
    assert memory.read_text(encoding="utf-8") == content


def test_expected_hash_stale_does_not_compute_after_hash(tmp_path):
    """Quand stale, on n'a pas besoin de calculer l'after_hash (court-circuit)."""
    memory, _ = _make_memory(tmp_path)
    result = patch_frontmatter_file(
        memory, {"forging_state": "mature"},
        expected_hash="deadbeef0000",
    )
    assert result["after_hash"] is None


def test_dry_run_with_expected_hash(tmp_path):
    """dry_run + expected_hash correct : pas de write malgré le hash ok."""
    memory, content = _make_memory(tmp_path)
    current_hash = _hash(content)
    result = patch_frontmatter_file(
        memory, {"forging_state": "mature"},
        dry_run=True,
        expected_hash=current_hash,
    )
    assert result["changed"] is True
    assert result["dry_run"] is True
    assert result["stale_hash"] is False
    # Fichier inchangé (dry_run)
    assert memory.read_text(encoding="utf-8") == content


def test_dry_run_stale_signals_stale_not_change(tmp_path):
    """dry_run + expected_hash stale : on signale stale, pas de change."""
    memory, content = _make_memory(tmp_path)
    result = patch_frontmatter_file(
        memory, {"forging_state": "mature"},
        dry_run=True,
        expected_hash="0000baddcafe",
    )
    assert result["stale_hash"] is True
    assert result["changed"] is False
    assert memory.read_text(encoding="utf-8") == content


def test_cli_compute_hash(tmp_path):
    """forge documente compute-hash <path> renvoie le hash sha256[:12]."""
    memory, content = _make_memory(tmp_path)
    r = subprocess.run(
        [sys.executable, str(BIN / "documente_engine.py"),
         "compute-hash", str(memory)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["ok"] is True
    assert out["hash"] == _hash(content)


def test_cli_patch_with_correct_expected_hash(tmp_path):
    """CLI : patch-frontmatter --expected-hash <correct> → OK."""
    memory, content = _make_memory(tmp_path)
    current_hash = _hash(content)
    r = subprocess.run(
        [sys.executable, str(BIN / "documente_engine.py"),
         "patch-frontmatter", str(memory),
         "--patch", json.dumps({"forging_state": "mature"}),
         "--expected-hash", current_hash],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["ok"] is True
    assert out["changed"] is True
    assert out["stale_hash"] is False


def test_cli_patch_with_stale_expected_hash(tmp_path):
    """CLI : patch-frontmatter --expected-hash <stale> → erreur code stale_hash."""
    memory, content = _make_memory(tmp_path)
    r = subprocess.run(
        [sys.executable, str(BIN / "documente_engine.py"),
         "patch-frontmatter", str(memory),
         "--patch", json.dumps({"forging_state": "mature"}),
         "--expected-hash", "0000000000ab"],
        capture_output=True, text=True,
    )
    # exit 0 même pour les erreurs métier (cf. patterns Forge — l'erreur est dans le JSON)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["ok"] is False
    assert out["code"] == "stale_hash"
    assert out["stale_hash"] is True
    # Fichier inchangé
    assert memory.read_text(encoding="utf-8") == content


def test_concurrent_session_scenario(tmp_path):
    """Scénario réel : 2 sessions A et B lisent le fichier, A patche, B patche
    avec son hash périmé → B est refusé (pas de commit tronqué)."""
    memory, content = _make_memory(tmp_path)
    hash_at_t0 = _hash(content)
    # Session A patche
    res_a = patch_frontmatter_file(
        memory, {"forging_state": "mature"},
        expected_hash=hash_at_t0,
    )
    assert res_a["changed"] is True
    # Session B tente de patcher avec son hash périmé (capturé avant A)
    res_b = patch_frontmatter_file(
        memory, {"horizon": "permanent"},
        expected_hash=hash_at_t0,
    )
    assert res_b["stale_hash"] is True
    assert res_b["changed"] is False
    # Le patch de A est conservé, B n'a pas écrasé
    final = memory.read_text(encoding="utf-8")
    assert "forging_state: mature" in final
    assert "horizon: bounded" in final  # B n'a pas écrasé
