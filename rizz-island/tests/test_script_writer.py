"""Tests for the script schema checks, season state updates and the writer's repair loop.

The scripts here are tiny synthetic fixtures built in code, only for testing
the plumbing: they are not episodes. The Claude call is stubbed out.

Run: python -m pytest tests -q
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rizz import config, writer  # noqa: E402
from rizz.cast import load_cast  # noqa: E402
from rizz.script_schema import autofix, build_schema, estimate_seconds, validate  # noqa: E402
from rizz.state import apply_episode, initial_state  # noqa: E402

CAST = load_cast()


def ln(speaker, text, expr="neutral", react="none"):
    return {"speaker": speaker, "text": text, "expression": expr, "emphasis": [text.split()[0]],
            "camera": "two_shot", "effect": "none", "sfx": "none", "reaction_character": react,
            "reaction_expression": "shocked", "reaction_sfx": "none"}


def fixture_script(episode=1, dumped="none", kind="none"):
    """Smallest script that satisfies every rule (each islander speaks, ~70 s)."""
    filler = "short test line"
    ids = CAST.ids()
    scenes = [
        {"id": "s1", "kind": "dialogue", "location": "pool", "characters": ids[:4],
         "lines": [ln(c, f"{filler} for {c} here") for c in ids[:4]] * 2},
        {"id": "s2", "kind": "confessional", "location": "confessional", "characters": [ids[4]],
         "lines": [ln(ids[4], f"{filler} said alone to camera")]},
        {"id": "s3", "kind": "dialogue", "location": "lounge", "characters": ids[4:],
         "lines": [ln(c, f"{filler} for {c} there", react=ids[0]) for c in ids[4:]] * 2},
    ]
    return {
        "episode": episode, "title": "Test", "logline": "A test.",
        "cold_open": {"narrator_line": "and then something happened", "caption": "UH OH",
                      "character": ids[0], "expression": "shocked", "location": "firepit"},
        "vote_result": {"kind": kind, "dumped": dumped, "narrator_line": "you voted" if kind != "none" else "",
                        "farewell_line": "bye everyone" if kind != "none" else "", "farewell_expression": "angry"},
        "previously": [{"narrator_line": "welcome to the villa where nothing goes to plan",
                        "characters": ids[:2], "expression": "smug", "location": "pool"}] * 2,
        "scenes": scenes,
        "twist": {"kind": "text_bomb", "location": "firepit", "characters": ids[:3], "headline": "📱 I GOT A TEXT!",
                  "text_message": "Recoupling tonight", "lines": [ln(ids[1], "I got a text everyone listen up")] * 3},
        "cliffhanger": {"narrator_line": "who will survive the recoupling tonight", "vote_prompt": "Who should be DUMPED?",
                        "vote_options": ids[4:6]},
        "continuity": {"couples": [{"a": ids[0], "b": ids[1]}], "storylines": ["s"], "running_jokes": ["j"],
                       "rivalries": [], "summary": "Stuff happened.", "biggest_moment": "The text."},
    }


@pytest.fixture
def state():
    return initial_state(CAST)


def test_fixture_is_valid_against_schema_and_rules(state):
    s = fixture_script()
    schema = build_schema(CAST, state, ["none"])
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(s, schema)
    errors, _ = validate(s, CAST, state, 1)
    assert errors == []
    assert config.TARGET_MIN_S - 3 <= estimate_seconds(s, CAST) <= config.TARGET_MAX_S + 4


def test_schema_has_no_optional_or_union_fields(state):
    """Structured outputs allow few optional/union params: we use none at all."""
    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert set(node["required"]) == set(node["properties"])
                assert node["additionalProperties"] is False
            assert "anyOf" not in node and not isinstance(node.get("type"), list)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(build_schema(CAST, state, ["none"]))


def test_rules_catch_problems(state):
    s = fixture_script()
    s["scenes"][2]["lines"] = [x for x in s["scenes"][2]["lines"] if x["speaker"] != "broccolo"]
    s["scenes"][0]["lines"][0]["text"] = " ".join(["word"] * 20)
    s["twist"]["lines"][0]["text"] = "what the hell"
    s["cliffhanger"]["vote_options"] = ["discotto"]
    errors, _ = validate(s, CAST, state, 1)
    joined = "\n".join(errors)
    assert "silent: broccolo" in joined
    assert "line too long" in joined
    assert "not PG" in joined
    assert "vote_options" in joined


def test_dumped_islander_cannot_return(state):
    st = copy.deepcopy(state)
    st["episode"] = 1
    s = fixture_script(episode=2, dumped="discotto", kind="viewer_vote")
    errors, _ = validate(s, CAST, st, 2)
    assert any("discotto speaks" in e and "just dumped" in e for e in errors)


def test_autofix_adds_missing_cast_and_drops_bad_emphasis(state):
    s = fixture_script()
    s["scenes"][0]["characters"] = s["scenes"][0]["characters"][:1]
    s["scenes"][0]["lines"][0]["emphasis"] = ["NOT-IN-LINE"]
    s["scenes"][0]["lines"][1]["speaker"] = s["scenes"][0]["lines"][1]["speaker"].upper()   # enum casing drift
    autofix(s, CAST)
    assert len(s["scenes"][0]["characters"]) == 4
    assert s["scenes"][0]["lines"][0]["emphasis"] == []
    assert s["scenes"][0]["lines"][1]["speaker"].islower()


def test_apply_episode_updates_state(state):
    st = copy.deepcopy(state)
    s1 = fixture_script()
    st = apply_episode(st, s1)
    assert st["episode"] == 1 and st["pending_vote"]["options"] == s1["cliffhanger"]["vote_options"]
    assert st["couples"] == [["baguettini", "conetta"]]
    s2 = fixture_script(episode=2, dumped="discotto", kind="viewer_vote")
    st = apply_episode(st, s2)
    assert "discotto" not in st["in_villa"] and st["eliminated"][0]["id"] == "discotto"


def test_writer_repair_loop(monkeypatch, tmp_path, state):
    """First reply breaks a rule, the problem goes back, the second reply is saved."""
    monkeypatch.setattr(config, "EPISODES_DIR", tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-used")
    bad = fixture_script()
    bad["cliffhanger"]["vote_options"] = []
    replies = [bad, fixture_script()]
    seen_messages = []

    def fake_call(system, messages, schema, log=print):
        seen_messages.append(copy.deepcopy(messages))
        block = SimpleNamespace(type="text", text=json.dumps(replies.pop(0)), to_dict=lambda: {"type": "text"})
        return SimpleNamespace(content=[block])

    monkeypatch.setattr(writer, "call_claude", fake_call)
    path = writer.write_script(CAST, state, log=lambda *_: None)
    assert json.loads(path.read_text())["cliffhanger"]["vote_options"]
    assert len(seen_messages) == 2 and "vote_options" in seen_messages[1][-1]["content"]
    assert (path.parent / "script.md").read_text().startswith("# Episode 1")


def test_final_json_text_skips_text_before_fallback():
    msg = SimpleNamespace(content=[SimpleNamespace(type="text", text="{partial"),
                                   SimpleNamespace(type="fallback"),
                                   SimpleNamespace(type="text", text='{"ok": 1}')])
    assert writer._final_json_text(msg) == '{"ok": 1}'
