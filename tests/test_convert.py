"""Conversion au format unique (design 2026-10-10 §3) : rien n'est perdu."""
import json
import re
import subprocess
import sys
from pathlib import Path

BIN = Path(__file__).resolve().parents[1] / "bin"
sys.path.insert(0, str(BIN))
from convert_lib import convert_memory_text, new_memory_text  # noqa: E402

ANCIEN = """---
entite: entreprise/tools/modern-sky
type: tool
derniere_maj: 2026-10-04
---

# Memory — modern-sky

## Doctrine en vigueur

### Git

- toujours yarn

## Décisions actives

1. D1 → decisions/a.yaml

## Décisions remplacées

- D0 (2026-01-01)

## Discussions ouvertes

```bash
## pas une section
```
"""


def _contenu(text):
    """Lignes non vides, sans marqueurs de titre : ce qui ne doit jamais disparaître."""
    return [re.sub(r"^#+\s*", "", l).strip() for l in text.splitlines() if l.strip() and l.strip() != "---"]


def _titres(text):
    out, fence = [], False
    for l in text.splitlines():
        if l.lstrip().startswith("```"):
            fence = not fence
        elif not fence and l.startswith("## "):
            out.append(l)
    return out


def test_rien_n_est_perdu():
    out = convert_memory_text(ANCIEN, name="modern-sky", type_name="tool", today="2026-10-11")
    for ligne in _contenu(ANCIEN):
        assert ligne in _contenu(out), ligne


def test_en_tete_complete_sans_ecraser():
    out = convert_memory_text(ANCIEN, name="modern-sky", type_name="projet", today="2026-10-11")
    fm = out.split("---")[1]
    assert "entite: entreprise/tools/modern-sky" in fm
    assert "name: modern-sky" in fm
    assert "type: tool" in fm and "type: projet" not in fm
    assert "forging_state: actif" in fm
    assert "derniere_maj: 2026-10-04" in fm


def test_sections_dans_l_ordre_canonique():
    out = convert_memory_text(ANCIEN, name="modern-sky", type_name="tool", today="2026-10-11")
    assert _titres(out) == ["## Quick", "## Doctrine en vigueur", "## Décisions actives", "## Détails"]
    details = out.split("## Détails", 1)[1]
    assert "### Décisions remplacées" in details and "### Discussions ouvertes" in details


def test_titres_internes_descendus_d_un_niveau():
    src = ANCIEN.replace("## Discussions ouvertes", "## Divers\n\n### Sous-titre")
    out = convert_memory_text(src, name="m", type_name="tool", today="2026-10-11")
    assert "#### Sous-titre" in out.split("## Détails", 1)[1]


def test_titre_dans_bloc_de_code_ignore():
    out = convert_memory_text(ANCIEN, name="m", type_name="tool", today="2026-10-11")
    assert "## pas une section" in out
    assert "## pas une section" not in _titres(out)


def test_bloc_okf_conserve_en_fin():
    src = ANCIEN + "\n<!-- okf-links:start -->\n## Liens\n\n- [[x]]\n<!-- okf-links:end -->\n"
    out = convert_memory_text(src, name="m", type_name="tool", today="2026-10-11")
    assert out.rstrip().endswith("<!-- okf-links:end -->")
    assert out.count("<!-- okf-links:start -->") == 1
    assert _titres(out)[-1] == "## Liens"


def test_derniere_maj_ajoutee_si_absente():
    src = ANCIEN.replace("derniere_maj: 2026-10-04\n", "")
    out = convert_memory_text(src, name="m", type_name="tool", today="2026-10-11")
    assert "derniere_maj: 2026-10-11" in out


def test_sans_frontmatter():
    out = convert_memory_text("# Titre\n\n## Notes\n\n- a\n", name="m", type_name="tool", today="2026-10-11")
    assert out.startswith("---\nname: m\ntype: tool\nforging_state: actif\nderniere_maj: 2026-10-11\n---\n")
    assert "### Notes" in out


def test_nouveau_memory():
    out = new_memory_text(name="treso", type_name="projet", today="2026-10-11")
    assert out == "---\nname: treso\ntype: projet\nforging_state: actif\nderniere_maj: 2026-10-11\n---\n\n# treso\n\n## Quick\n"


def _run(*args, project):
    out = subprocess.run([sys.executable, str(BIN / "documente_engine.py"), *args],
                         capture_output=True, text=True, cwd=project,
                         env={"CLAUDE_FORGE_PROJECT_DIR": str(project), "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin"})
    return json.loads(out.stdout)


def test_convert_ecrit_puis_noop(tmp_path):
    d = tmp_path / "entreprise/tools/modern-sky"
    d.mkdir(parents=True)
    (d / "MEMORY.md").write_text(ANCIEN, encoding="utf-8")
    r1 = _run("convert", "entreprise/tools/modern-sky", "--type", "tool", project=tmp_path)
    assert r1["ok"] and r1["action"] == "converted" and r1["name"] == "modern-sky"
    avant = (d / "MEMORY.md").read_text(encoding="utf-8")
    r2 = _run("convert", "entreprise/tools/modern-sky", "--type", "tool", project=tmp_path)
    assert r2["action"] == "noop"
    assert (d / "MEMORY.md").read_text(encoding="utf-8") == avant


def test_convert_deja_subject_noop(tmp_path):
    d = tmp_path / "x"
    d.mkdir()
    texte = "---\nname: x\ntype: tool\nforging_state: actif\n---\n\n## Quick\n"
    (d / "MEMORY.md").write_text(texte, encoding="utf-8")
    assert _run("convert", "x", "--type", "projet", project=tmp_path)["action"] == "noop"
    assert (d / "MEMORY.md").read_text(encoding="utf-8") == texte


def test_convert_cree_si_absent(tmp_path):
    r = _run("convert", "entreprise/projets/treso", "--type", "projet", "--name", "tresorerie", project=tmp_path)
    assert r["action"] == "created"
    assert "name: tresorerie" in (tmp_path / "entreprise/projets/treso/MEMORY.md").read_text(encoding="utf-8")


def test_convert_dry_run_n_ecrit_rien(tmp_path):
    d = tmp_path / "x"
    d.mkdir()
    (d / "MEMORY.md").write_text(ANCIEN, encoding="utf-8")
    r = _run("convert", "x", "--type", "tool", "--dry-run", project=tmp_path)
    assert r["action"] == "converted" and r["dry_run"] is True
    assert (d / "MEMORY.md").read_text(encoding="utf-8") == ANCIEN


def test_titres_canoniques_sans_accents_reconnus():
    # 24 MEMORY.md de CE écrivent « Decisions actives » / « Regles apprises » sans accents :
    # ils doivent atterrir dans la section canonique, pas sous ## Détails.
    ancien = "---\ntype: service\n---\n\n## Decisions actives\n\n1. D1 → decisions/a.yaml\n\n## Regles apprises\n\n- R1\n"
    out = convert_memory_text(ancien, name="x", type_name="service", today="2026-10-11")
    assert "## Décisions actives\n\n1. D1 → decisions/a.yaml" in out
    assert "## Règles apprises\n\n- R1" in out
    assert "### Decisions actives" not in out
    assert "### Regles apprises" not in out
