"""Tests du seam de config par-repo `.forge.yaml` (load_forge_config) + `forge init`.

Unitaires purs (pas de subprocess/git) → indépendants des échecs environnementaux
de test_documente_engine.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

import forge_lib
from forge_lib import load_forge_config


def _fresh(monkeypatch=None):
    # vide le cache mémoire entre deux cas (project_dir réutilisé sinon)
    forge_lib._CONFIG_CACHE.clear()


def test_no_config_ce_shaped(tmp_path):
    _fresh()
    (tmp_path / "entreprise").mkdir()
    c = load_forge_config(tmp_path)
    assert c["output_dir"] == (tmp_path / "entreprise").resolve()
    assert c["pool_roots"][:3] == ["services", "entreprise", "humains"]
    assert c["domain_roots"] == ["services", "humains", "entreprise"]
    assert c["skill_visibility"] == "entreprise"


def test_no_config_flat_repo(tmp_path):
    _fresh()
    (tmp_path / "subjects" / "x").mkdir(parents=True)
    c = load_forge_config(tmp_path)
    # pas de entreprise/ → on écrit à la racine, jamais un dossier fantôme
    assert c["output_dir"] == tmp_path.resolve()
    assert "." in c["pool_roots"]


def test_explicit_config_jcc(tmp_path):
    _fresh()
    (tmp_path / ".forge.yaml").write_text(
        "output_dir: .\npool_roots: [\".\"]\ndomain_roots: []\nskill_visibility: jcc\n",
        encoding="utf-8",
    )
    c = load_forge_config(tmp_path)
    assert c["output_dir"] == tmp_path.resolve()
    assert c["pool_roots"] == ["."]
    assert c["domain_roots"] == []
    assert c["skill_visibility"] == "jcc"
    # types_roots non spécifié → défaut = pool_roots
    assert c["types_roots"] == ["."]


def test_output_dir_subfolder(tmp_path):
    _fresh()
    (tmp_path / ".forge.yaml").write_text("output_dir: memoire\n", encoding="utf-8")
    c = load_forge_config(tmp_path)
    assert c["output_dir"] == (tmp_path / "memoire").resolve()


def test_malformed_config_no_raise(tmp_path):
    _fresh()
    (tmp_path / ".forge.yaml").write_text(":::garbage::\n\t- broken {[", encoding="utf-8")
    c = load_forge_config(tmp_path)  # ne doit pas lever
    assert c["output_dir"] == tmp_path.resolve()


def test_inline_comments_stripped(tmp_path):
    _fresh()
    (tmp_path / ".forge.yaml").write_text(
        'output_dir: docs        # commentaire inline\npool_roots: ["."]   # ici aussi\n',
        encoding="utf-8",
    )
    c = load_forge_config(tmp_path)
    assert c["output_dir"] == (tmp_path / "docs").resolve()
    assert c["pool_roots"] == ["."]


def test_output_dir_dot_normalized(tmp_path):
    _fresh()
    (tmp_path / ".forge.yaml").write_text("output_dir: .\n", encoding="utf-8")
    c = load_forge_config(tmp_path)
    assert c["output_dir"] == tmp_path.resolve()


def test_forge_init_writes_config_and_scaffolds(tmp_path, monkeypatch):
    _fresh()
    monkeypatch.setenv("CLAUDE_FORGE_PROJECT_DIR", str(tmp_path))
    import init_engine
    import argparse

    args = argparse.Namespace(
        output_dir=None, pool_root=None, types_root=None,
        skill_visibility=None, force=False,
    )
    res = init_engine.cmd_init(args)
    assert res["ok"] is True
    assert (tmp_path / ".forge.yaml").is_file()
    assert (tmp_path / "subjects" / ".gitkeep").is_file()
    assert (tmp_path / "types" / ".gitkeep").is_file()

    # refuse d'écraser sans --force
    _fresh()
    res2 = init_engine.cmd_init(args)
    assert res2["ok"] is False and res2["code"] == "exists"

    # --force écrase
    _fresh()
    args_force = argparse.Namespace(
        output_dir=None, pool_root=None, types_root=None,
        skill_visibility=None, force=True,
    )
    res3 = init_engine.cmd_init(args_force)
    assert res3["ok"] is True


def test_forge_init_active_post_bloc_par_defaut(tmp_path, monkeypatch):
    _fresh()
    monkeypatch.setenv("CLAUDE_FORGE_PROJECT_DIR", str(tmp_path))
    import init_engine
    import argparse

    res = init_engine.cmd_init(argparse.Namespace(
        output_dir=None, pool_root=None, types_root=None,
        skill_visibility=None, force=False, no_post_bloc=False,
    ))
    assert res["ok"] is True and res["post_bloc"] is True
    texte = (tmp_path / ".forge.yaml").read_text(encoding="utf-8")
    # même expression que le hook Stop : la ligne écrite doit l'activer
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "check_post_bloc", Path(__file__).resolve().parent.parent / "hooks" / "check-post-bloc.py")
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    assert hook.RE_ACTIF.search(texte)

    _fresh()
    res2 = init_engine.cmd_init(argparse.Namespace(
        output_dir=None, pool_root=None, types_root=None,
        skill_visibility=None, force=True, no_post_bloc=True,
    ))
    assert res2["post_bloc"] is False
    texte2 = (tmp_path / ".forge.yaml").read_text(encoding="utf-8")
    assert "post_bloc: false" in texte2
    assert not hook.RE_ACTIF.search(texte2)
