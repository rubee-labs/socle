"""check-memory + patch-section : MEMORY.md borné (décision CE 2026-09-06)."""
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1] / "bin" / "documente_engine.py"
TODAY = dt.date.today().isoformat()

SAMPLE = """---
entite: factures
type: tool
derniere_maj: 2026-07-16
memory_max_kb: 12
---

# Etat — factures

## Doctrine en vigueur

- règle A

## Décisions actives

1. **D1** (2026-07-01)
2. **D2** (2026-07-02)

## État

- 2026-07-06 : run 1
- **2026-07-07 : run 2**
  - détail
- 2026-07-08 : run 3
"""


def run(*args):
    out = subprocess.run([sys.executable, str(ENGINE), *args], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_check_memory_diagnostic(tmp_path):
    md = tmp_path / "MEMORY.md"
    md.write_text(SAMPLE, encoding="utf-8")
    r = run("check-memory", str(tmp_path))
    assert r["ok"] and r["max_kb"] == 12 and r["over"] is False
    assert r["derniere_maj"] == "2026-07-16" and r["derniere_maj_today"] is False
    assert r["journal_lines"] == {"## État": 3}
    assert r["decisions_actives"] == 2 and r["has_quick"] is False


def test_check_memory_over_default_cap(tmp_path):
    md = tmp_path / "MEMORY.md"
    md.write_text("---\nentite: x\n---\n## Quick\n\n" + "x" * 9000, encoding="utf-8")
    r = run("check-memory", str(md))
    assert r["max_kb"] == 8 and r["over"] is True and r["has_quick"] is True


def test_patch_section_replace_keeps_rest(tmp_path):
    md = tmp_path / "MEMORY.md"
    md.write_text(SAMPLE, encoding="utf-8")
    body = tmp_path / "quick.md"
    body.write_text("État : ok\nDernier run : 2026-09-06", encoding="utf-8")
    r = run("patch-section", str(tmp_path), "--section", "## Décisions actives", "--body-file", str(body), "--touch-derniere-maj")
    assert r["action"] == "replaced"
    new = md.read_text(encoding="utf-8")
    assert "## Décisions actives\n\nÉtat : ok\nDernier run : 2026-09-06\n\n## État" in new
    assert "- règle A" in new and "- 2026-07-08 : run 3" in new
    assert f"derniere_maj: {TODAY}" in new and "memory_max_kb: 12" in new
    assert "**D1**" not in new


def test_patch_section_create_when_missing(tmp_path):
    md = tmp_path / "MEMORY.md"
    md.write_text(SAMPLE, encoding="utf-8")
    body = tmp_path / "q.md"
    body.write_text("Quick borné", encoding="utf-8")
    r = run("patch-section", str(md), "--section", "Quick", "--body-file", str(body))
    assert r["action"] == "created"
    assert md.read_text(encoding="utf-8").endswith("## Quick\n\nQuick borné\n")


def test_patch_section_stale_hash_refused(tmp_path):
    md = tmp_path / "MEMORY.md"
    md.write_text(SAMPLE, encoding="utf-8")
    body = tmp_path / "q.md"
    body.write_text("x", encoding="utf-8")
    r = run("patch-section", str(md), "--section", "## Quick", "--body-file", str(body), "--expected-hash", "000000000000")
    assert r["ok"] is False and r["code"] == "stale_hash"
    good = hashlib.sha256(SAMPLE.encode("utf-8")).hexdigest()[:12]
    r = run("patch-section", str(md), "--section", "## Quick", "--body-file", str(body), "--expected-hash", good)
    assert r["ok"] is True


def test_patch_section_idempotent(tmp_path):
    md = tmp_path / "MEMORY.md"
    md.write_text(SAMPLE, encoding="utf-8")
    body = tmp_path / "q.md"
    body.write_text("même contenu", encoding="utf-8")
    run("patch-section", str(md), "--section", "## Doctrine en vigueur", "--body-file", str(body))
    once = md.read_text(encoding="utf-8")
    run("patch-section", str(md), "--section", "## Doctrine en vigueur", "--body-file", str(body))
    assert md.read_text(encoding="utf-8") == once
