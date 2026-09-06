"""Tests du parseur frontmatter minimal (forge_lib.parse_simple_yaml).

Régression 2026-09-06 : `last_event:` (dict imbriqué) était lu comme []
sur 39/39 subjects de claude-enterprise → stagnation calculée depuis
created_at, cascade et coordinator aveugles.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
from forge_lib import parse_simple_yaml, parse_frontmatter  # noqa: E402


def test_nested_dict_is_a_dict():
    fm = parse_simple_yaml("last_event:\n  date: 2026-09-04\n  type: reply_sent\n  ref: events/x.md\n")
    assert fm["last_event"] == {"date": "2026-09-04", "type": "reply_sent", "ref": "events/x.md"}


def test_empty_key_stays_empty_list():
    fm = parse_simple_yaml("linked_subjects:\nname: x\n")
    assert fm["linked_subjects"] == []
    assert fm["name"] == "x"


def test_trailing_empty_key_is_empty_list():
    fm = parse_simple_yaml("name: x\nlinked_evals:\n")
    assert fm["linked_evals"] == []


def test_block_list_still_parsed():
    fm = parse_simple_yaml("linked_subjects:\n  - supplier:leadlux\n  - freight-forwarder:sparx\n")
    assert fm["linked_subjects"] == ["supplier:leadlux", "freight-forwarder:sparx"]


def test_list_of_inline_dicts_with_comments():
    text = (
        "linked_records:\n"
        "  - {type: order_id, value: 400, source: mcp_achats}\n"
        "  - {type: order_amount, value: \"54838.10 USD\", source: mcp_achats}  # corrigé\n"
    )
    fm = parse_simple_yaml(text)
    assert len(fm["linked_records"]) == 2


def test_real_subject_shape(tmp_path):
    md = tmp_path / "MEMORY.md"
    md.write_text(
        "---\n"
        "name: order-400\n"
        "type: supplier-order\n"
        "forging_state: seed\n"
        "created_at: 2026-04-29\n"
        "archived_at: null\n"
        "\n"
        "linked_subjects:\n"
        "  - supplier:leadlux\n"
        "\n"
        "active_decisions:\n"
        "  - 2026-06-17-bascule\n"
        "open_discussions:\n"
        "  - 2026-08-28-reconciliation\n"
        "\n"
        "last_event:\n"
        "  date: 2026-09-04\n"
        "  type: reply_sent\n"
        "  ref: events/2026-09-04-liberation.md\n"
        "\n"
        "stress_tests_passed: 0\n"
        "compiled_artifacts: []\n"
        "last_synthesis:\n"
        "  by: agent-achats\n"
        "  at: \"2026-09-04T11:57:10+02:00\"\n"
        "---\n\n## Quick\n",
        encoding="utf-8",
    )
    fm = parse_frontmatter(md)
    assert fm["last_event"]["date"] == "2026-09-04"
    assert fm["last_synthesis"]["by"] == "agent-achats"
    assert fm["linked_subjects"] == ["supplier:leadlux"]
    assert fm["archived_at"] is None
    assert fm["compiled_artifacts"] == []
