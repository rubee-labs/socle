"""resolve_link 0.7.0 : par name d'en-tête, puis par dossier ; homonymes = None."""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))


def _memory(root, rel, frontmatter):
    d = root / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / "MEMORY.md").write_text(f"---\n{frontmatter}\n---\n", encoding="utf-8")
    return d / "MEMORY.md"


def _engine(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_FORGE_PROJECT_DIR", str(tmp_path))
    import forge_lib
    forge_lib._CONFIG_CACHE.clear()
    import forge_engine
    return importlib.reload(forge_engine)


def test_par_name_hors_subjects(tmp_path, monkeypatch):
    cible = _memory(tmp_path, "entreprise/projets/treso", "name: tresorerie\ntype: projet\nforging_state: actif")
    src = _memory(tmp_path, "services/achats/subjects/order-1", "name: order-1\ntype: supplier-order\nforging_state: actif")
    eng = _engine(tmp_path, monkeypatch)
    assert eng.resolve_link("projet:tresorerie", src.parent) == cible
    assert eng.resolve_link("tresorerie", src.parent) == cible


def test_type_verifie_sur_le_name(tmp_path, monkeypatch):
    _memory(tmp_path, "a/weifang", "name: weifang\ntype: tool\nforging_state: actif")
    eng = _engine(tmp_path, monkeypatch)
    assert eng.resolve_link("supplier:weifang", tmp_path) is None


def test_liens_historiques_par_dossier(tmp_path, monkeypatch):
    sw = _memory(tmp_path, "services/achats/subjects/supplier-weifang", "type: supplier\nforging_state: actif")
    o = _memory(tmp_path, "services/achats/subjects/order-398", "type: supplier-order\nforging_state: actif")
    eng = _engine(tmp_path, monkeypatch)
    assert eng.resolve_link("supplier:weifang", o.parent) == sw
    assert eng.resolve_link("order-398", sw.parent) == o


def test_homonymes_refuses(tmp_path, monkeypatch):
    _memory(tmp_path, "services/achats/subjects/x1", "name: dup\ntype: tool\nforging_state: actif")
    _memory(tmp_path, "services/marketing/subjects/x2", "name: dup\ntype: tool\nforging_state: actif")
    eng = _engine(tmp_path, monkeypatch)
    assert eng.resolve_link("dup", tmp_path) is None


def test_ancien_format_jamais_cible(tmp_path, monkeypatch):
    _memory(tmp_path, "services/achats/subjects/vieux", "name: vieux\ntype: tool")
    eng = _engine(tmp_path, monkeypatch)
    assert eng.resolve_link("vieux", tmp_path) is None
