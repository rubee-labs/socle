"""write-capture : champs MADR (options_considerees, confirmation) attendus dans une décision.

Décision CE 2026-09-07 : une décision documente les options écartées et la preuve
qui confirmera son application. Absence = avertissement structuré, jamais un refus
(les skills appelants ne doivent pas casser), mais le récap de /documente l'affiche.
"""
import json
import subprocess
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1] / "bin" / "documente_engine.py"

FM = json.dumps({"date": "2026-09-07", "sujet": "test", "parameters": {"x": 1}})

BODY_COMPLET = """contexte: >
  Pourquoi on décide.

options_considerees:
  - option: A — ne rien faire
    retenue: false
    raison: le journal continue de grossir
  - option: B — plafond par entité
    retenue: true
    raison: garde la doctrine dense, interdit le journal

decision: plafond relevable à 20 Ko sous conditions

confirmation:
  preuve: check-memory over=false + hook Stop sans avertissement pendant 7 jours
  echeance: 2026-09-14
"""

BODY_SANS_MADR = """contexte: >
  Pourquoi on décide.
decision: plafond relevable à 20 Ko
"""


def run(*args):
    out = subprocess.run([sys.executable, str(ENGINE), *args], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _write(tmp_path, body, slug, kind="decision"):
    body_file = tmp_path / f"{slug}.body"
    body_file.write_text(body, encoding="utf-8")
    return run("write-capture", str(tmp_path), "--kind", kind, "--slug", slug,
               "--body-file", str(body_file), "--frontmatter", FM)


def test_decision_complete_sans_avertissement(tmp_path):
    r = _write(tmp_path, BODY_COMPLET, "2026-09-07-complete")
    assert r["ok"] is True
    assert r["madr_missing"] == []
    assert r.get("warnings", []) == []
    assert (tmp_path / "decisions" / "2026-09-07-complete.yaml").exists()


def test_decision_sans_madr_ecrite_mais_avertie(tmp_path):
    r = _write(tmp_path, BODY_SANS_MADR, "2026-09-07-incomplete")
    assert r["ok"] is True, "l'absence des champs MADR n'est jamais un refus"
    assert r["madr_missing"] == ["options_considerees", "confirmation"]
    assert any("options_considerees" in w and "confirmation" in w for w in r["warnings"])
    assert (tmp_path / "decisions" / "2026-09-07-incomplete.yaml").exists()


def test_cle_indentee_ne_compte_pas(tmp_path):
    body = "contexte:\n  options_considerees: pas au niveau racine\n  confirmation: idem\n"
    r = _write(tmp_path, body, "2026-09-07-indentee")
    assert r["madr_missing"] == ["options_considerees", "confirmation"]


def test_discussion_jamais_concernee(tmp_path):
    r = _write(tmp_path, "# Discussion\n\nsans champs MADR\n", "2026-09-07-disc", kind="discussion")
    assert r["ok"] is True
    assert "madr_missing" not in r
    assert r.get("warnings", []) == []
