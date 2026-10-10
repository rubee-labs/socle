"""Types et capacités des subjects (design 2026-10-10 §2)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
import forge_lib  # noqa: E402
from subject_lib import (  # noqa: E402
    ALL_CAPABILITIES, DEFAULT_CAPABILITIES,
    has_capability, load_type_index, resolve_type, type_capabilities,
)

CE_RULES = (
    "type_by_path:\n"
    '  - {pattern: "*/skills/*/cas/*", type: skill-cas}\n'
    '  - {pattern: "*/skills/*", type: skill}\n'
    '  - {pattern: "*/tools/*", type: tool}\n'
    '  - {pattern: "services/*", type: service}\n'
)


def _repo(tmp_path, forge_yaml=""):
    forge_lib._CONFIG_CACHE.clear()
    if forge_yaml:
        (tmp_path / ".forge.yaml").write_text(forge_yaml, encoding="utf-8")
    return tmp_path


def _dir(root, rel, frontmatter=None):
    d = root / rel
    d.mkdir(parents=True, exist_ok=True)
    if frontmatter is not None:
        (d / "MEMORY.md").write_text(f"---\n{frontmatter}\n---\n", encoding="utf-8")
    return d


def test_types_generiques_du_plugin(tmp_path):
    idx = load_type_index(_repo(tmp_path))
    for t in ("skill", "skill-cas", "tool", "agent", "service"):
        assert idx[t]["capabilities"] == DEFAULT_CAPABILITIES, t
        assert idx[t]["source"] == "plugin"
    assert idx["projet"]["capabilities"] == ALL_CAPABILITIES


def test_type_metier_sans_champ_capabilities_a_tout(tmp_path):
    root = _repo(tmp_path)
    _dir(root, "services/achats/types/supplier")
    (root / "services/achats/types/supplier/REFERENCE.md").write_text(
        "---\ntype: supplier\nhorizon: permanent\n---\n", encoding="utf-8")
    idx = load_type_index(root)
    assert idx["supplier"]["capabilities"] == ALL_CAPABILITIES
    assert idx["supplier"]["source"] == "repo"


def test_depot_surcharge_le_plugin(tmp_path):
    root = _repo(tmp_path)
    _dir(root, "types/tool")
    (root / "types/tool/REFERENCE.md").write_text(
        "---\ntype: tool\ncapabilities: [memory, decisions, lifecycle, links]\n---\n", encoding="utf-8")
    assert load_type_index(root)["tool"]["capabilities"] == ["memory", "decisions", "lifecycle", "links"]


def test_type_inconnu_capacites_par_defaut(tmp_path):
    caps, connu = type_capabilities("inexistant", load_type_index(_repo(tmp_path)))
    assert caps == DEFAULT_CAPABILITIES and connu is False


def test_has_capability(tmp_path):
    idx = load_type_index(_repo(tmp_path))
    assert has_capability({"type": "projet"}, idx, "events")
    assert not has_capability({"type": "tool"}, idx, "events")
    assert not has_capability({}, idx, "links")


def test_type_de_l_en_tete_gagne(tmp_path):
    root = _repo(tmp_path, CE_RULES)
    d = _dir(root, "entreprise/tools/x", "type: projet")
    assert resolve_type(d, root) == {"type": "projet", "source": "frontmatter"}


def test_type_by_path(tmp_path):
    root = _repo(tmp_path, CE_RULES)
    d = _dir(root, "entreprise/tools/factures", "entite: factures")
    assert resolve_type(d, root) == {"type": "tool", "source": "type_by_path"}


def test_ordre_des_motifs(tmp_path):
    root = _repo(tmp_path, CE_RULES)
    d = _dir(root, "services/achats/skills/reassort/cas/conteneur")
    assert resolve_type(d, root)["type"] == "skill-cas"
    d2 = _dir(root, "services/amazon/ads/skills/observation")
    assert resolve_type(d2, root)["type"] == "skill"


def test_motif_sans_segment_initial(tmp_path):
    root = _repo(tmp_path, CE_RULES)
    d = _dir(root, "skills/racine")
    assert resolve_type(d, root) == {"type": None, "source": "claude"}


def test_sans_regle_choix_de_claude(tmp_path):
    root = _repo(tmp_path)
    d = _dir(root, "docs/notes", "entite: notes")
    assert resolve_type(d, root) == {"type": None, "source": "claude"}
