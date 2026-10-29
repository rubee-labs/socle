"""Tests du hook Stop hooks/check-post-bloc.py (checklist post-bloc vérifiée par code).

Portés de claude-enterprise (entreprise/scripts/tests/test_check_post_bloc.py), plus :
activation par .forge.yaml, noms accentués, exclusions configurées, journal dans .git/.
Lancement : `python3 -m pytest tests/test_check_post_bloc.py -q`.
"""

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "check-post-bloc.py"
TODAY = dt.date.today().isoformat()
ENTITE = "services/finance/tools/factures"


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    (r / ".forge.yaml").write_text('post_bloc: true\npost_bloc_exclusions: ["data/cache/"]\n', encoding="utf-8")
    ent = r / ENTITE
    ent.mkdir(parents=True)
    (ent / "MEMORY.md").write_text(f"---\nentite: factures\nderniere_maj: {TODAY}\n---\n# Etat\n", encoding="utf-8")
    (r / "entreprise").mkdir()
    (r / "entreprise" / "SUBJECTS-INDEX.md").write_text("index\n", encoding="utf-8")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "init")
    return r


@pytest.fixture
def transcript(tmp_path):
    def _make(start=None):
        start = start or (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=5))
        p = tmp_path / "transcript.jsonl"
        p.write_text(json.dumps({"type": "user", "timestamp": start.isoformat()}) + "\n", encoding="utf-8")
        return str(p)
    return _make


@pytest.fixture
def run_hook(tmp_path):
    def _run(repo, payload, log=True):
        env = {k: v for k, v in os.environ.items() if k not in ("SOCLE_POST_BLOC", "SOCLE_POST_BLOC_LOG", "CE_POST_BLOC_LOG")}
        env["CLAUDE_PROJECT_DIR"] = str(repo)
        if log:
            env["SOCLE_POST_BLOC_LOG"] = str(tmp_path / "post_bloc_hook.log")
        payload.setdefault("cwd", str(repo))
        payload.setdefault("session_id", "s1")
        out = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                             capture_output=True, text=True, env=env, timeout=10)
        assert out.returncode == 0, out.stderr
        return json.loads(out.stdout) if out.stdout.strip() else None
    return _run


# --- comportements portés de CE -------------------------------------------------

def test_rien_a_signaler_quand_arbre_propre(repo, transcript, run_hook):
    assert run_hook(repo, {"transcript_path": transcript()}) is None


def test_bloque_fichier_non_commite_dans_entite(repo, transcript, run_hook):
    (repo / ENTITE / "cli.py").write_text("x", encoding="utf-8")
    res = run_hook(repo, {"transcript_path": transcript()})
    assert res and res["decision"] == "block"
    assert ENTITE in res["reason"] and "1 fichier(s) non committé(s)" in res["reason"]


def test_signale_derniere_maj_perimee(repo, transcript, run_hook):
    (repo / ENTITE / "MEMORY.md").write_text("---\nentite: factures\nderniere_maj: 2026-01-01\n---\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "old")
    (repo / ENTITE / "cli.py").write_text("x", encoding="utf-8")
    res = run_hook(repo, {"transcript_path": transcript()})
    assert res and f"derniere_maj 2026-01-01 ≠ {TODAY}" in res["reason"]


def test_index_scanner_exclus_quel_que_soit_son_dossier(repo, transcript, run_hook):
    (repo / "entreprise/SUBJECTS-INDEX.md").write_text("index modifié\n", encoding="utf-8")
    (repo / "SUBJECT-POOL-METRICS.md").write_text("m\n", encoding="utf-8")
    assert run_hook(repo, {"transcript_path": transcript()}) is None


def test_silence_si_stop_hook_active(repo, transcript, run_hook):
    (repo / ENTITE / "cli.py").write_text("x", encoding="utf-8")
    assert run_hook(repo, {"transcript_path": transcript(), "stop_hook_active": True}) is None


def test_ignore_fichier_modifie_avant_la_session(repo, transcript, run_hook):
    f = repo / ENTITE / "cli.py"
    f.write_text("x", encoding="utf-8")
    vieux = (dt.datetime.now() - dt.timedelta(hours=2)).timestamp()
    os.utime(f, (vieux, vieux))
    assert run_hook(repo, {"transcript_path": transcript()}) is None


def test_bloque_une_seule_fois_par_ensemble_de_fichiers(repo, transcript, run_hook):
    (repo / ENTITE / "cli.py").write_text("x", encoding="utf-8")
    t = transcript()
    assert run_hook(repo, {"transcript_path": t})["decision"] == "block"
    assert run_hook(repo, {"transcript_path": t}) is None
    (repo / ENTITE / "autre.py").write_text("y", encoding="utf-8")
    assert run_hook(repo, {"transcript_path": t})["decision"] == "block"


def test_avertissement_taille_avec_plafond_par_defaut(repo, transcript, run_hook):
    (repo / ENTITE / "MEMORY.md").write_text(f"---\nentite: factures\nderniere_maj: {TODAY}\n---\n" + "x" * 9000, encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "gros")
    (repo / ENTITE / "cli.py").write_text("x", encoding="utf-8")
    res = run_hook(repo, {"transcript_path": transcript()})
    assert "Ko > 8 Ko" in res["reason"] and f"/documente {ENTITE}" in res["reason"]


def test_plafond_surcharge_par_frontmatter(repo, transcript, run_hook):
    (repo / ENTITE / "MEMORY.md").write_text(f"---\nentite: factures\nderniere_maj: {TODAY}\nmemory_max_kb: 20\n---\n" + "x" * 9000, encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "gros")
    (repo / ENTITE / "cli.py").write_text("x", encoding="utf-8")
    assert "Ko >" not in run_hook(repo, {"transcript_path": transcript()})["reason"]


def test_fichier_hors_entite_signale_sans_memory(repo, transcript, run_hook):
    (repo / "README.md").write_text("x", encoding="utf-8")
    res = run_hook(repo, {"transcript_path": transcript()})
    assert res and "hors entité : 1 fichier(s)" in res["reason"]


def test_payload_invalide_silencieux(repo, tmp_path):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(repo), SOCLE_POST_BLOC_LOG=str(tmp_path / "log"))
    out = subprocess.run([sys.executable, str(HOOK)], input="pas du json", capture_output=True, text=True, env=env)
    assert out.returncode == 0 and out.stdout == ""


# --- nouveautés SOCLE ---------------------------------------------------------------

def test_inactif_sans_interrupteur_forge_yaml(repo, transcript, run_hook):
    (repo / ".forge.yaml").write_text("output_dir: .\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "sans post_bloc")
    (repo / ENTITE / "cli.py").write_text("x", encoding="utf-8")
    assert run_hook(repo, {"transcript_path": transcript()}) is None


def test_nom_accentue_detecte(repo, transcript, run_hook):
    (repo / ENTITE / "procédure-été.md").write_text("x", encoding="utf-8")
    res = run_hook(repo, {"transcript_path": transcript()})
    assert res and ENTITE in res["reason"] and "1 fichier(s) non committé(s)" in res["reason"]


def test_exclusions_configurees(repo, transcript, run_hook):
    (repo / "data" / "cache").mkdir(parents=True)
    (repo / "data" / "cache" / "x.json").write_text("{}", encoding="utf-8")
    assert run_hook(repo, {"transcript_path": transcript()}) is None


def test_journal_par_defaut_dans_git_dir(repo, transcript, run_hook):
    (repo / ENTITE / "cli.py").write_text("x", encoding="utf-8")
    assert run_hook(repo, {"transcript_path": transcript()}, log=False)["decision"] == "block"
    assert (repo / ".git" / "socle" / "post_bloc_hook.log").is_file()


# --- travail dans un autre dépôt sans /documente (0.7.4, incident CE du 29/10/2026) ----------

def _outil(nom, **entree):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": nom, "input": entree}]}}


@pytest.fixture
def autre_depot(tmp_path):
    r = tmp_path / "eaisy"
    r.mkdir()
    _git(r, "init", "-q")
    return r


@pytest.fixture
def transcript_outils(transcript):
    def _make(*evenements):
        chemin = transcript()
        with open(chemin, "a", encoding="utf-8") as f:
            for e in evenements:
                f.write(json.dumps(e) + "\n")
        return chemin
    return _make


def test_commit_dans_un_autre_depot_sans_documente_bloque(repo, autre_depot, transcript_outils, run_hook):
    t = transcript_outils(_outil("Bash", command=f"git -C {autre_depot} commit -q -m x"))
    res = run_hook(repo, {"transcript_path": t})
    assert res and res["decision"] == "block"
    assert "eaisy" in res["reason"] and "/documente" in res["reason"]
    assert "subject" in res["reason"] and "thème" in res["reason"]


def test_ecriture_dans_un_autre_depot_sans_documente_bloque(repo, autre_depot, transcript_outils, run_hook):
    (autre_depot / "admin").mkdir()
    t = transcript_outils(_outil("Write", file_path=str(autre_depot / "admin" / "todos.py"), content="x"))
    res = run_hook(repo, {"transcript_path": t})
    assert res and "eaisy" in res["reason"]


def test_documente_ecrit_leve_le_blocage(repo, autre_depot, transcript_outils, run_hook):
    t = transcript_outils(
        _outil("Bash", command=f"git -C {autre_depot} push -q origin main"),
        _outil("Bash", command="forge documente commit-atomic --paths x/MEMORY.md --message m --push"),
    )
    assert run_hook(repo, {"transcript_path": t}) is None


def test_memory_edite_dans_le_depot_leve_le_blocage(repo, autre_depot, transcript_outils, run_hook):
    t = transcript_outils(
        _outil("Bash", command=f"git -C {autre_depot} commit -m x"),
        _outil("Edit", file_path=str(repo / ENTITE / "MEMORY.md"), old_string="a", new_string="b"),
    )
    assert run_hook(repo, {"transcript_path": t}) is None


def test_documente_prepare_seul_ne_suffit_pas(repo, autre_depot, transcript_outils, run_hook):
    t = transcript_outils(
        _outil("Bash", command=f"git -C {autre_depot} commit -m x"),
        _outil("Bash", command=f"cd {autre_depot} && forge documente prepare docs"),
    )
    assert run_hook(repo, {"transcript_path": t})["decision"] == "block"


def test_commit_dans_le_depot_courant_ou_hors_git_ignore(repo, tmp_path, transcript_outils, run_hook):
    t = transcript_outils(
        _outil("Bash", command=f"git -C {repo} commit -m x"),
        _outil("Write", file_path=str(tmp_path / "scratch" / "notes.md"), content="x"),
    )
    assert run_hook(repo, {"transcript_path": t}) is None


def test_autre_depot_signale_une_seule_fois(repo, autre_depot, transcript_outils, run_hook):
    t = transcript_outils(_outil("Bash", command=f"git -C {autre_depot} commit -m x"))
    assert run_hook(repo, {"transcript_path": t})["decision"] == "block"
    assert run_hook(repo, {"transcript_path": t}) is None


def test_cd_puis_commit_apres_point_virgule_ou_pipe(repo, autre_depot, transcript_outils, run_hook):
    cmd = f"cd {autre_depot} && grep -rn x . | head -5; git add -A && git commit -q -m fusion"
    res = run_hook(repo, {"transcript_path": transcript_outils(_outil("Bash", command=cmd))})
    assert res and "eaisy" in res["reason"]


def test_cd_vers_le_depot_courant_puis_commit_ignore(repo, autre_depot, transcript_outils, run_hook):
    cmd = f"cd {autre_depot} && git status; cd {repo} && git commit -m x"
    assert run_hook(repo, {"transcript_path": transcript_outils(_outil("Bash", command=cmd))}) is None
