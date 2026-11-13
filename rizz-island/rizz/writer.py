"""The script writer: asks Claude for the next episode as structured JSON.

Inputs:  the story bible (cast.json), the season state (couples, rivalries,
         running jokes, eliminations, episode log) and the latest vote result.
Output:  episodes/epNN/script.json (the source of truth, edit it freely) and
         episodes/epNN/script.md (a readable screenplay view of the same thing).

The reply is constrained to the episode JSON schema (structured outputs), then
checked in Python (timing, everyone gets a line, PG, continuity...). If checks
fail, the problems go back to Claude in the same conversation for a fix.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from . import config
from .cast import Cast
from .script_schema import NONE, all_lines, autofix, build_schema, estimate_seconds, validate
from .state import episode_dir, singles

MAX_REPAIRS = 2


class ScriptError(RuntimeError):
    pass


# ==========================================================================
# Prompt
# ==========================================================================
def system_prompt(cast: Cast) -> str:
    """Stable instructions + the story bible (identical every episode, so it caches well)."""
    show = cast.show
    bible = {
        "show": show,
        "locations": cast.locations,
        "characters": [{k: v for k, v in c.raw.items() if k not in ("voice", "nicknames", "scale")}
                       for c in cast.characters.values()],
    }
    cams = "\n".join(f"  - {k}: {v}" for k, v in config.CAMERA_MOVES.items())
    fx = "\n".join(f"  - {k}: {v}" for k, v in config.EFFECTS.items())
    twists = "\n".join(f"  - {k}: {v}" for k, v in config.TWIST_KINDS.items())
    return f"""You are the head writer of {show.get('title', 'Rizz Island')}, an animated TikTok reality show. {show.get('premise', '')}

Each episode you write becomes a 65–80 second vertical video: AI voices read the lines, big word-by-word captions pop on screen, and cartoon cut-out characters bounce, react and get zoomed and shaken by chaotic "brain rot" editing. Your JSON is the whole blueprint, so every field matters.

## Audience and content
The audience skews young. Keep it PG: crushes, coupling up, jealousy, betrayals, scheming, silly insults (food puns, roasting someone's crust or florets). Nothing sexual, no kissing beyond a peck on the cheek, no swearing or near-swears, no real people, brands, songs or existing internet characters. Mean is fine if it's funny and nobody is cruel about real-world traits.

## Episode structure and timing
1. cold_open (0–3 s): the narrator teases this episode's biggest moment without resolving it, 12 words max, e.g. "…and then Baguettini did THE unthinkable 😱". `caption` is the 2–5 word on-screen hook. `character`/`expression` is the frozen reaction shot shown under it.
2. vote_result (episode 2 onwards, ~6 s): the narrator reveals who the viewers dumped ("YOU voted… 🥁"), then the dumped islander gets one short farewell line. In episode 1 set kind "none", dumped "none" and leave the text fields empty.
3. previously (~5 s): 2–3 fast narrator beats recapping earlier episodes. In episode 1, use them instead to introduce the couples and singles at speed.
4. scenes (~40 s): 2–3 short dialogue scenes (3–6 lines each, 2–4 characters) and 1–2 confessionals (one character alone on the pink chair talking to camera, 1–2 lines). Interleave confessionals between dialogue scenes like a real reality show.
5. twist (~10 s): one of
{twists}
   `headline` is the big on-screen card (e.g. "📱 I GOT A TEXT!"); `text_message` is the message, challenge result or announcement, short.
6. cliffhanger (~8 s): a narrator line that leaves things hanging, then `vote_prompt` (e.g. "Who should be DUMPED from the island? Comment their name 👇") and 2–4 `vote_options`: the islanders most at risk, usually singles or whoever caused the most chaos.

Length: aim for 130–165 spoken words in total, narrator included. Lines are short and punchy: usually 4–12 words, never more than 16, one idea per line. Fast back-and-forth beats long speeches.

## Craft
- Keep continuity with the season state: pay off storylines, call back running jokes and earlier episodes, respect who is coupled, single or gone.
- Give every islander in the villa at least one line or a clear moment. Spread the spotlight; the vote only works if viewers care about everyone.
- Each character sounds like themselves (see personality and catchphrase). Use catchphrases sparingly: at most two per episode, at the perfect moment.
- Escalate: a small spark, a bigger fight, the twist, then a cliffhanger. Write for laughs as well as drama.
- The narrator is dry, sarcastic and roasts everyone equally.
- Text is spoken by text-to-speech: write words, not stage directions or sound descriptions. CAPS for a shouted word or two is fine; an emoji at the end of an occasional line is fine (it is shown, not spoken). Use "..." for dramatic pauses.

## Line fields
- expression: the face for that line. Vary them; reactions sell the drama.
- emphasis: 1–2 words copied exactly from the line that should pop in the captions (the punchline, the name, the insult).
- camera:
{cams}
- effect:
{fx}
  Use effects on maybe a third of lines, saving shake / freeze_frame / snap_zoom for the biggest beats.
- sfx: a meme sound on the line ("none" most of the time).
- reaction_character / reaction_expression / reaction_sfx: an on-screen cutaway reaction right after the line (e.g. Polpetta, angry, record_scratch). Use on big beats, about one line in three; otherwise "none" (with any expression).
- The narrator can also have lines inside scenes for quick asides (speaker "narrator").

## continuity
Update the season bible after this episode: couples as they stand at the end, 3–6 active storylines, the running jokes worth keeping (add new ones that landed), rivalries, a 2–3 sentence summary for future recaps, and the single biggest moment.

## Story bible
```json
{json.dumps(bible, indent=1, ensure_ascii=False)}
```"""


def user_prompt(cast: Cast, state: dict, episode: int, vote: dict | None, brief: str) -> str:
    """What's different this episode: the season so far and how the last vote went."""
    name = lambda cid: cast.characters[cid].short_name if cid in cast.characters else cid  # noqa: E731
    season = {
        "season": state["season"],
        "episode_to_write": episode,
        "in_villa": [name(c) + f" ({c})" for c in state["in_villa"]],
        "couples": [f"{name(a)} & {name(b)}" for a, b in state["couples"]],
        "singles": [name(c) for c in singles(state)],
        "eliminated": [f"{name(e['id'])} (episode {e['episode']}, {e['how']})" for e in state["eliminated"]],
        "storylines": state["storylines"],
        "rivalries": state["rivalries"],
        "running_jokes": state["running_jokes"],
        "episode_log": state["episode_log"],
        "bombshells_waiting_to_arrive": [name(c) + f" ({c})" for c in state.get("bombshells_waiting", [])],
    }
    if episode == 1:
        vote_text = "This is episode 1: there is no vote result yet (vote_result.kind = \"none\", dumped = \"none\")."
    elif vote and vote.get("winner"):
        tally = ", ".join(f"{name(k)} {v}" for k, v in sorted(vote["tally"].items(), key=lambda kv: -kv[1]))
        vote_text = (f"The viewers voted. {name(vote['winner'])} got the most votes to be dumped "
                     f"({vote['total']} votes counted: {tally}). Open with that reveal: vote_result.kind = "
                     f"\"viewer_vote\", dumped = \"{vote['winner']}\". They leave the villa now and must not "
                     f"appear after their farewell.")
    else:
        opts = ", ".join(name(o) for o in (state.get("pending_vote") or {}).get("options", [])) or "any islander"
        vote_text = (f"No votes were counted for last episode's vote ({opts}). Decide who leaves based on the "
                     f"story so far: vote_result.kind = \"producer_decision\", and the narrator says the producers "
                     f"made the call because the viewers stayed quiet. They must not appear after their farewell.")
    arrivals = ("A waiting bombshell may arrive in the twist (kind \"new_arrival\")."
                if state.get("bombshells_waiting") else "No bombshells are waiting, so don't use the \"new_arrival\" twist.")
    extra = f"\n\nShowrunner's note for this episode: {brief.strip()}" if brief.strip() else ""
    return (f"Write episode {episode}.\n\n{vote_text}\n{arrivals}\n\nSeason so far:\n```json\n"
            f"{json.dumps(season, indent=1, ensure_ascii=False)}\n```{extra}")


def dumped_choices(state: dict, episode: int, vote: dict | None) -> list[str]:
    if episode == 1:
        return [NONE]
    if vote and vote.get("winner"):
        return [vote["winner"]]
    opts = [o for o in (state.get("pending_vote") or {}).get("options", []) if o in state["in_villa"]]
    return opts or list(state["in_villa"])


# ==========================================================================
# Claude call
# ==========================================================================
def _final_json_text(message) -> str:
    """The JSON text of the reply (after any server-side fallback hand-over)."""
    parts: list[str] = []
    for block in message.content:
        if block.type == "fallback":       # a fallback model took over: only its text counts
            parts = []
        elif block.type == "text":
            parts.append(block.text)
    return "".join(parts)


def call_claude(system: str, messages: list[dict], schema: dict, log=print):
    """One streamed, schema-constrained request. Returns the final message."""
    import anthropic

    client = anthropic.Anthropic()
    params = dict(
        model=config.SCRIPT_MODEL,
        max_tokens=64000,
        system=system,
        messages=messages,
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": schema}},
        # Refusal fallbacks are opt-in: if the model declines, the API re-runs the
        # request on a fallback model in the same call ("default" routes by category).
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    try:
        try:
            with client.beta.messages.stream(**params) as stream:
                msg = stream.get_final_message()
        except anthropic.BadRequestError as e:
            if "fallback" not in str(e.message).lower():
                raise
            log("    (refusal fallbacks unavailable for this key; retrying without them)")
            params.pop("betas"), params.pop("fallbacks")
            with client.beta.messages.stream(**params) as stream:
                msg = stream.get_final_message()
    except anthropic.AuthenticationError as e:
        raise ScriptError("The Claude API rejected the API key. Check ANTHROPIC_API_KEY.") from e
    except anthropic.PermissionDeniedError as e:
        raise ScriptError(f"The API key isn't allowed to use {config.SCRIPT_MODEL}: {e.message}") from e
    except anthropic.RateLimitError as e:
        raise ScriptError("Rate limited by the Claude API; wait a minute and try again.") from e
    except anthropic.BadRequestError as e:
        raise ScriptError(f"The Claude API refused the request: {e.message}") from e
    except anthropic.APIStatusError as e:
        raise ScriptError(f"Claude API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise ScriptError("Couldn't reach the Claude API (network problem).") from e

    if msg.stop_reason == "refusal":
        cat = getattr(getattr(msg, "stop_details", None), "category", None)
        raise ScriptError(f"Claude declined to write this episode (category: {cat}). Try a different --brief.")
    if msg.stop_reason == "max_tokens":
        raise ScriptError("The reply was cut off (max_tokens). Try again.")
    u = msg.usage
    log(f"    {msg.model}: {u.input_tokens} in / {u.output_tokens} out tokens, request {msg._request_id}")
    return msg


def has_credentials() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


# ==========================================================================
# Public entry point
# ==========================================================================
def write_script(cast: Cast, state: dict, vote: dict | None = None, brief: str = "",
                 dry_run: bool = False, log=print) -> Path:
    """Write episodes/epNN/script.json for the next episode and return its path."""
    episode = int(state["episode"]) + 1
    out_dir = episode_dir(episode)
    out_dir.mkdir(parents=True, exist_ok=True)
    system = system_prompt(cast)
    user = user_prompt(cast, state, episode, vote, brief)
    schema = build_schema(cast, state, dumped_choices(state, episode, vote))

    if dry_run:
        (out_dir / "prompt.md").write_text(f"# System\n\n{system}\n\n# User\n\n{user}\n", encoding="utf-8")
        (out_dir / "schema.json").write_text(json.dumps(schema, indent=1), encoding="utf-8")
        log(f"  dry run: wrote {out_dir.relative_to(config.ROOT)}/prompt.md and schema.json (no API call)")
        return out_dir / "prompt.md"

    if not has_credentials():
        raise ScriptError("ANTHROPIC_API_KEY is not set, so the script writer can't call Claude. "
                          "Set it (see README) or use --dry-run to see the prompt.")

    log(f"  asking {config.SCRIPT_MODEL} for episode {episode}...")
    messages: list[dict[str, Any]] = [{"role": "user", "content": user}]
    script: dict | None = None
    for attempt in range(MAX_REPAIRS + 1):
        t0 = time.time()
        msg = call_claude(system, messages, schema, log)
        try:
            script = json.loads(_final_json_text(msg))
        except json.JSONDecodeError as e:
            raise ScriptError(f"Claude's reply wasn't valid JSON: {e}") from e
        for note in autofix(script, cast):
            log(f"    fixed: {note}")
        errors, warnings = validate(script, cast, state, episode)
        log(f"    draft {attempt + 1}: ~{estimate_seconds(script, cast):.0f}s, {len(all_lines(script))} lines, "
            f"{len(errors)} problems ({time.time() - t0:.0f}s)")
        if not errors:
            for w in warnings:
                log(f"    note: {w}")
            break
        for e in errors:
            log(f"    problem: {e}")
        if attempt == MAX_REPAIRS:
            log("  ! saving the last draft with problems; edit script.json by hand")
            break
        # Same conversation: pass the reply back unchanged, then ask for a fix.
        messages += [{"role": "assistant", "content": [b.to_dict() for b in msg.content]},
                     {"role": "user", "content": "Please fix these problems and return the complete corrected "
                                                 "episode JSON:\n- " + "\n- ".join(errors)}]

    assert script is not None
    path = out_dir / "script.json"
    if path.exists():
        path.replace(out_dir / "script.prev.json")    # keep the previous draft
    path.write_text(json.dumps(script, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "script.md").write_text(screenplay(script, cast), encoding="utf-8")
    return path


# ==========================================================================
# Readable screenplay view
# ==========================================================================
def screenplay(script: dict, cast: Cast) -> str:
    """Markdown rendering of a script for reading (script.json stays the source of truth)."""
    def who(cid: str) -> str:
        if cid == "narrator":
            return "NARRATOR"
        c = cast.characters.get(cid)
        return f"{c.emoji} {c.short_name.upper()}" if c else cid.upper()

    def line(ln: dict) -> str:
        tags = [ln["expression"]]
        if ln["camera"] != "two_shot":
            tags.append(ln["camera"])
        if ln["effect"] != NONE:
            tags.append(ln["effect"])
        if ln["sfx"] != NONE:
            tags.append(f"sfx:{ln['sfx']}")
        text = ln["text"]
        for e in ln.get("emphasis", []):
            text = text.replace(e, f"**{e}**", 1)
        s = f"- **{who(ln['speaker'])}** _({', '.join(tags)})_: {text}"
        if ln.get("reaction_character", NONE) != NONE:
            rs = f", sfx:{ln['reaction_sfx']}" if ln["reaction_sfx"] != NONE else ""
            s += f"\n  - ↳ reaction: {who(ln['reaction_character'])} _{ln['reaction_expression']}{rs}_"
        return s

    L = [f"# Episode {script['episode']}: {script['title']}", "", f"_{script['logline']}_", "",
         f"Estimated length: ~{estimate_seconds(script, cast):.0f}s", ""]
    co = script["cold_open"]
    L += ["## Cold open", f"- **NARRATOR**: {co['narrator_line']}",
          f"- on screen: **{co['caption']}** over {who(co['character'])} ({co['expression']}) at the {co['location']}", ""]
    vr = script["vote_result"]
    if vr["kind"] != NONE:
        L += ["## Vote result", f"- **NARRATOR**: {vr['narrator_line']}",
              f"- **{who(vr['dumped'])}** _({vr['farewell_expression']})_: {vr['farewell_line']}", ""]
    L += ["## Previously on Rizz Island"] + [f"- **NARRATOR**: {p['narrator_line']}" for p in script["previously"]] + [""]
    for sc in script["scenes"]:
        title = "Confessional" if sc["kind"] == "confessional" else "Scene"
        L += [f"## {title} {sc['id']} — {sc['location']} ({', '.join(who(c) for c in sc['characters'])})"]
        L += [line(ln) for ln in sc["lines"]] + [""]
    tw = script["twist"]
    L += [f"## Twist: {tw['kind']} — {tw['location']}", f"- card: **{tw['headline']}**", f"- message: {tw['text_message']}"]
    L += [line(ln) for ln in tw["lines"]] + [""]
    ch = script["cliffhanger"]
    L += ["## Cliffhanger", f"- **NARRATOR**: {ch['narrator_line']}", f"- card: **{ch['vote_prompt']}**",
          f"- options: {', '.join(who(o) for o in ch['vote_options'])}", ""]
    cont = script["continuity"]
    L += ["## Continuity (applied to season_state.json after the full render)",
          f"- couples: {', '.join(who(c['a']) + ' & ' + who(c['b']) for c in cont['couples']) or 'none'}",
          f"- summary: {cont['summary']}", f"- biggest moment: {cont['biggest_moment']}"]
    L += [f"- storyline: {s}" for s in cont["storylines"]]
    return "\n".join(L) + "\n"
