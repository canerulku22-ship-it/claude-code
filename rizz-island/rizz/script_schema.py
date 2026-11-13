"""The episode script format: JSON schema, checks, auto-fixes and a length estimate.

The schema is built per episode so its enums only allow characters who can
actually appear (the villa line-up, waiting bombshells) and, when the vote is
already decided, only the right person to dump.

Structured-output limits shape the design: every field is required (no
optional or nullable fields), and "none" is used where a value is absent.
"""
from __future__ import annotations

import re
from typing import Any

from . import config
from .cast import Cast

NONE = "none"
SWEARS = re.compile(r"\b(damn|hell|crap|sh[i1]t|f+u+c+k|bitch|ass(hole)?|bastard|sexy|sex|kiss(ing)? on the lips)\b", re.I)
WORDS_PER_SEC = 2.6          # Piper voices at speed 1.0 (measured on the cast)


# ==========================================================================
# Schema
# ==========================================================================
def _enum(values: list[str]) -> dict:
    return {"type": "string", "enum": list(dict.fromkeys(values))}


def _obj(props: dict[str, Any]) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def build_schema(cast: Cast, state: dict, dumped_choices: list[str]) -> dict:
    """JSON schema for one episode.

    dumped_choices: ["none"] for episode 1, [winner] after a counted vote, or
    the last cliffhanger's options when the writer decides.
    """
    villa = list(state["in_villa"])
    arrivals = list(state.get("bombshells_waiting", []))
    people = villa + arrivals
    expr = _enum(config.EXPRESSIONS)
    locs = _enum([k for k in cast.locations])
    sfx = _enum(config.SFX_CUES + [NONE])

    line = _obj({
        "speaker": _enum(people + ["narrator"]),
        "text": {"type": "string"},
        "expression": expr,
        "emphasis": {"type": "array", "items": {"type": "string"}},
        "camera": _enum(list(config.CAMERA_MOVES)),
        "effect": _enum(list(config.EFFECTS)),
        "sfx": sfx,
        "reaction_character": _enum(people + [NONE]),
        "reaction_expression": expr,
        "reaction_sfx": sfx,
    })
    scene = _obj({
        "id": {"type": "string"},
        "kind": _enum(["dialogue", "confessional"]),
        "location": locs,
        "characters": {"type": "array", "items": _enum(people)},
        "lines": {"type": "array", "items": line},
    })
    return _obj({
        "episode": {"type": "integer"},
        "title": {"type": "string"},
        "logline": {"type": "string"},
        "cold_open": _obj({
            "narrator_line": {"type": "string"},
            "caption": {"type": "string"},
            "character": _enum(people),
            "expression": expr,
            "location": locs,
        }),
        "vote_result": _obj({
            "kind": _enum(["none", "viewer_vote", "producer_decision"]),
            "dumped": _enum(dumped_choices),
            "narrator_line": {"type": "string"},
            "farewell_line": {"type": "string"},
            "farewell_expression": expr,
        }),
        "previously": {"type": "array", "items": _obj({
            "narrator_line": {"type": "string"},
            "characters": {"type": "array", "items": _enum(people)},
            "expression": expr,
            "location": locs,
        })},
        "scenes": {"type": "array", "items": scene},
        "twist": _obj({
            "kind": _enum(list(config.TWIST_KINDS)),
            "location": locs,
            "characters": {"type": "array", "items": _enum(people)},
            "headline": {"type": "string"},
            "text_message": {"type": "string"},
            "lines": {"type": "array", "items": line},
        }),
        "cliffhanger": _obj({
            "narrator_line": {"type": "string"},
            "vote_prompt": {"type": "string"},
            "vote_options": {"type": "array", "items": _enum(people)},
        }),
        "continuity": _obj({
            "couples": {"type": "array", "items": _obj({"a": _enum(people), "b": _enum(people)})},
            "storylines": {"type": "array", "items": {"type": "string"}},
            "running_jokes": {"type": "array", "items": {"type": "string"}},
            "rivalries": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "string"},
            "biggest_moment": {"type": "string"},
        }),
    })


# ==========================================================================
# Helpers
# ==========================================================================
def all_lines(script: dict) -> list[dict]:
    out = []
    for sc in script.get("scenes", []):
        out += sc.get("lines", [])
    out += script.get("twist", {}).get("lines", [])
    return out


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", text))


def _norm(w: str) -> str:
    return re.sub(r"[^a-z0-9']", "", w.lower())


def normalise_case(script: dict, cast: Cast) -> None:
    """Structured outputs don't guarantee enum casing: lower-case every enum-ish value."""
    def fix(d: dict, keys: tuple[str, ...]) -> None:
        for k in keys:
            if isinstance(d.get(k), str):
                d[k] = d[k].lower()
            elif isinstance(d.get(k), list):
                d[k] = [v.lower() if isinstance(v, str) else v for v in d[k]]

    line_keys = ("speaker", "expression", "camera", "effect", "sfx", "reaction_character",
                 "reaction_expression", "reaction_sfx")
    fix(script.get("cold_open", {}), ("character", "expression", "location"))
    fix(script.get("vote_result", {}), ("kind", "dumped", "farewell_expression"))
    for p in script.get("previously", []):
        fix(p, ("characters", "expression", "location"))
    for sc in script.get("scenes", []):
        fix(sc, ("kind", "location", "characters"))
        for ln in sc.get("lines", []):
            fix(ln, line_keys)
    tw = script.get("twist", {})
    fix(tw, ("kind", "location", "characters"))
    for ln in tw.get("lines", []):
        fix(ln, line_keys)
    fix(script.get("cliffhanger", {}), ("vote_options",))
    for c in script.get("continuity", {}).get("couples", []):
        fix(c, ("a", "b"))


def autofix(script: dict, cast: Cast) -> list[str]:
    """Repair small, unambiguous problems in place. Returns notes about what changed."""
    notes: list[str] = []
    normalise_case(script, cast)
    for sc in script.get("scenes", []) + [script.get("twist", {})]:
        chars = sc.setdefault("characters", [])
        for ln in sc.get("lines", []):
            for who in (ln.get("speaker"), ln.get("reaction_character")):
                if who and who not in ("narrator", NONE) and who not in chars:
                    chars.append(who)
                    notes.append(f"added {who} to the cast of {sc.get('id', 'twist')}")
            # emphasis words must exist in the line (case-insensitive)
            words = {_norm(w) for w in ln.get("text", "").split()}
            keep = [e for e in ln.get("emphasis", []) if _norm(e) in words]
            if len(keep) != len(ln.get("emphasis", [])):
                notes.append(f"dropped emphasis words not in line: {ln.get('text', '')[:40]}")
            ln["emphasis"] = keep
    return notes


# ==========================================================================
# Length estimate
# ==========================================================================
def estimate_seconds(script: dict, cast: Cast) -> float:
    """Rough runtime from word counts, voice speeds and fixed beats (cards, reactions, cuts)."""
    def speech(text: str, who: str) -> float:
        voice = cast.narrator_voice if who == "narrator" else cast.characters[who].voice if who in cast.characters else {}
        return word_count(text) / (WORDS_PER_SEC * float(voice.get("speed", 1.0))) + 0.25

    t = 1.0 + speech(script["cold_open"]["narrator_line"], "narrator")          # tease + sting
    vr = script["vote_result"]
    if vr["kind"] != "none":
        t += speech(vr["narrator_line"], "narrator") + 1.6                    # drum roll + reveal
        if vr["dumped"] in cast.characters:
            t += speech(vr["farewell_line"], vr["dumped"]) + 0.6
    for p in script["previously"]:
        t += speech(p["narrator_line"], "narrator") + 0.15
    for sc in script["scenes"]:
        t += 0.5                                                               # scene change
        for ln in sc["lines"]:
            t += speech(ln["text"], ln["speaker"])
            if ln.get("reaction_character", NONE) != NONE:
                t += 0.6
            if ln.get("effect") in ("freeze_frame", "slow_mo"):
                t += 0.5
    tw = script["twist"]
    t += 1.4                                                                   # headline card
    for ln in tw["lines"]:
        t += speech(ln["text"], ln["speaker"]) + (0.6 if ln.get("reaction_character", NONE) != NONE else 0)
    t += speech(script["cliffhanger"]["narrator_line"], "narrator") + 4.0      # vote card hold
    return t


# ==========================================================================
# Checks
# ==========================================================================
def validate(script: dict, cast: Cast, state: dict, episode: int) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors are sent back to Claude for a rewrite."""
    E: list[str] = []
    W: list[str] = []
    villa = set(state["in_villa"])
    arrivals = set(state.get("bombshells_waiting", []))
    vr = script["vote_result"]
    dumped = vr["dumped"] if vr["kind"] != "none" else None

    if script.get("episode") != episode:
        E.append(f"'episode' must be {episode}")
    if episode == 1 and vr["kind"] != "none":
        E.append("episode 1 has no vote result: vote_result.kind must be 'none'")
    if episode > 1 and vr["kind"] == "none":
        E.append("episodes after the first must open with the vote result")

    # who may appear after the dumping
    tw = script["twist"]
    arriving = set(tw["characters"]) & arrivals if tw["kind"] == "new_arrival" else set()
    if tw["kind"] == "new_arrival" and not arriving:
        E.append("twist kind 'new_arrival' needs a waiting bombshell in twist.characters"
                 + ("" if arrivals else " — there are none, so pick another twist kind"))
    in_scenes = villa - {dumped}            # bombshells only exist from the twist onwards
    present = in_scenes | arriving          # who is around for the twist, the vote and the couples

    scenes = script["scenes"]
    n_dlg = sum(1 for s in scenes if s["kind"] == "dialogue")
    n_conf = sum(1 for s in scenes if s["kind"] == "confessional")
    if not 2 <= n_dlg <= 3:
        E.append(f"need 2–3 dialogue scenes (got {n_dlg})")
    if not 1 <= n_conf <= 3:
        E.append(f"need 1–3 confessional scenes (got {n_conf})")

    spoken: set[str] = set()
    for sc in scenes:
        if sc["kind"] == "confessional":
            if len(sc["characters"]) != 1:
                E.append(f"confessional {sc['id']} must have exactly one character")
            if sc["location"] != "confessional" and "confessional" in cast.locations:
                W.append(f"confessional {sc['id']} is not set in the confessional location")
        for ln in sc["lines"]:
            who = ln["speaker"]
            if who != "narrator" and who not in in_scenes:
                E.append(f"{who} speaks in {sc['id']} but is not in the villa yet or any more"
                         + (" (just dumped)" if who == dumped else ""))
            if sc["kind"] == "confessional" and who not in sc["characters"] + ["narrator"]:
                E.append(f"in confessional {sc['id']} only {sc['characters']} may talk")
            spoken.add(who)
    for ln in tw["lines"]:
        if ln["speaker"] != "narrator" and ln["speaker"] not in present:
            E.append(f"{ln['speaker']} speaks in the twist but is not in the villa")
        spoken.add(ln["speaker"])

    for ln in all_lines(script):
        n = word_count(ln["text"])
        if n > 18:
            E.append(f"line too long ({n} words, max 16): \"{ln['text']}\"")
        elif n > 14:
            W.append(f"long line ({n} words): \"{ln['text']}\"")
        if not ln["text"].strip():
            E.append("empty line text")
    if not 1 <= len(tw["lines"]) <= 6:
        E.append(f"twist needs 1–6 lines (got {len(tw['lines'])})")

    missing = sorted(present - spoken)
    if missing:
        E.append(f"every islander needs at least one line; silent: {', '.join(missing)}")

    co = script["cold_open"]
    if word_count(co["narrator_line"]) > 12:
        E.append("cold_open.narrator_line must be 12 words or fewer (it plays in the first 2 seconds)")
    if co["character"] not in in_scenes | arriving:
        E.append(f"cold_open.character {co['character']} is not in the villa this episode")
    if not 1 <= len(script["previously"]) <= 4:
        E.append(f"previously needs 1–4 beats (got {len(script['previously'])})")

    opts = script["cliffhanger"]["vote_options"]
    if len(set(opts)) != len(opts) or not 2 <= len(opts) <= 4:
        E.append("cliffhanger.vote_options needs 2–4 different islanders")
    for o in opts:
        if o not in present:
            E.append(f"vote option {o} is not in the villa at the end of the episode")

    seen: set[str] = set()
    for c in script["continuity"]["couples"]:
        for who in (c["a"], c["b"]):
            if who in seen:
                E.append(f"{who} is in more than one couple")
            if who not in present:
                E.append(f"couple member {who} is not in the villa at the end of the episode")
            seen.add(who)
        if c["a"] == c["b"]:
            E.append(f"{c['a']} can't be coupled with themselves")

    texts = [co["narrator_line"], co["caption"], vr["narrator_line"], vr["farewell_line"], tw["headline"],
             tw["text_message"], script["cliffhanger"]["narrator_line"], script["cliffhanger"]["vote_prompt"]]
    texts += [p["narrator_line"] for p in script["previously"]] + [ln["text"] for ln in all_lines(script)]
    for t in texts:
        if SWEARS.search(t):
            E.append(f"not PG: \"{t}\"")

    secs = estimate_seconds(script, cast)
    if secs < config.TARGET_MIN_S - 3:
        E.append(f"too short: about {secs:.0f}s estimated, needs {config.TARGET_MIN_S:.0f}–{config.TARGET_MAX_S:.0f}s "
                 f"(add a few lines or reactions)")
    elif secs > config.TARGET_MAX_S + 4:
        E.append(f"too long: about {secs:.0f}s estimated, needs {config.TARGET_MIN_S:.0f}–{config.TARGET_MAX_S:.0f}s "
                 f"(cut lines or shorten them)")
    return E, W
