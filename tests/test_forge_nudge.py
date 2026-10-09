"""Tests du hook SessionStart hooks/forge-nudge.sh : règle post-bloc chargée + nudge /forge-init.

Lancement : `python3 -m pytest tests/test_forge_nudge.py -q`.
"""

import os
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "forge-nudge.sh"
ENTETE = "socle : checklist post-bloc active"


def _run(repo, **env):
    e = {k: v for k, v in os.environ.items() if k not in ("SOCLE_POST_BLOC", "CLAUDE_PLUGIN_ROOT")}
    e.update(env)
    return subprocess.run(["bash", str(HOOK)], cwd=repo, env=e, capture_output=True, text=True, timeout=10)


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return tmp_path


def test_post_bloc_true_charge_la_regle(repo):
    (repo / ".forge.yaml").write_text("output_dir: .\npost_bloc: true   # actif\n", encoding="utf-8")
    out = _run(repo)
    assert out.returncode == 0
    assert ENTETE in out.stdout
    assert "# Checklist post-bloc" in out.stdout
    assert "✅ commit" in out.stdout


def test_post_bloc_false_silence(repo):
    (repo / ".forge.yaml").write_text("post_bloc: false\n", encoding="utf-8")
    out = _run(repo)
    assert out.returncode == 0 and out.stdout == ""


def test_sans_forge_yaml_silence(repo):
    out = _run(repo)
    assert out.returncode == 0 and out.stdout == ""


def test_variable_env_force(repo):
    out = _run(repo, SOCLE_POST_BLOC="1")
    assert ENTETE in out.stdout


def test_nudge_pool_non_configure(repo):
    (repo / "subjects").mkdir()
    out = _run(repo)
    assert "lance /forge-init" in out.stdout
    assert ENTETE not in out.stdout
