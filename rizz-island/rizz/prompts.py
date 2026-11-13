"""Write image_prompts.md: ready-to-paste prompts for an AI image generator.

Generated from cast.json so that new bombshell characters get prompts too:
add them to cast.json and run `python rizz_island.py --prompts`.

Every prompt ends with the same STYLE line, which is what keeps the cast
looking like one show.
"""
from __future__ import annotations

from pathlib import Path

from . import config
from .cast import Cast, Character

STYLE = ("Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, "
         "smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible "
         "from head to toe with space around it, front-facing, centred, plain pure white background, "
         "no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.")

BG_STYLE = ("Glossy 3D cartoon render, same art style as a modern animated movie, vertical 9:16 composition, "
            "empty scene with no characters and no text or signs with words, eye-level camera, an open clear "
            "floor area in the lower middle of the frame where characters will stand, slightly soft focus in "
            "the far background, vibrant saturated colours, bright and fun reality-TV villa vibe.")

# (face, pose with arms, pose without arms)
EXPRESSIONS: dict[str, tuple[str, str, str]] = {
    "neutral": ("a friendly, relaxed expression with the mouth closed in a small smile",
                "arms relaxed at the sides",
                "relaxed upright posture"),
    "talking": ("the mouth wide open mid-word as if talking, otherwise the IDENTICAL expression, pose, "
                "framing and size as the neutral image",
                "arms relaxed at the sides exactly as in the neutral image",
                "posture exactly as in the neutral image"),
    "shocked": ("a shocked expression: eyes huge and wide, eyebrows raised high, mouth open in a round 'O'",
                "both hands raised up beside the face in surprise",
                "body leaning back in surprise"),
    "angry": ("an angry expression: eyebrows angled sharply down, gritted teeth, slightly flushed",
              "fists planted on the hips",
              "body puffed up and tense"),
    "smug": ("a smug expression: half-closed eyes, one eyebrow raised, a sly sideways smirk",
             "arms crossed",
             "head tilted slightly, chin up"),
    "in_love": ("in love: big glossy heart-shaped eyes, rosy blushing cheeks, a dreamy smile",
                "hands clasped together beside one cheek",
                "swaying dreamily to one side"),
}
OPTIONAL = {
    "blink": "eyes fully closed (a calm blink), mouth closed in a small smile",
    "shocked_talking": "the shocked expression but with the mouth open even wider mid-word",
    "angry_talking": "the angry expression but shouting, mouth open showing teeth",
    "smug_talking": "the smug expression but with the mouth half open mid-word, still smirking",
    "in_love_talking": "the in-love expression but with the mouth open mid-word, still heart-eyed",
}


def character_lock(c: Character) -> str:
    """The sentence that pins down who the character is; repeated in every prompt."""
    raw = c.raw
    extra = " No arms or hands." if raw.get("no_arms") else ""
    return (f"{raw['name']}, an original cartoon character for a reality show: {raw['look']}. "
            f"Signature colour {c.color}.{extra}")


def expression_prompt(c: Character, expr: str) -> str:
    face, arms, no_arms = EXPRESSIONS[expr]
    pose = no_arms if c.raw.get("no_arms") else arms
    return f"{character_lock(c)} Showing {face}, {pose}. {STYLE}"


def write_prompts(cast: Cast, out: Path = config.ROOT / "image_prompts.md") -> Path:
    L: list[str] = []
    add = L.append
    add("# Rizz Island — image prompts\n")
    add("Generated from `cast.json` by `python rizz_island.py --prompts` (re-run after adding a bombshell).\n")
    add("## How to get a consistent cast\n")
    add("1. **Start with each character's `neutral` image.** Regenerate until you love it: it becomes the "
        "reference for everything else.")
    add("2. **Make the other expressions *from* that neutral image**, using your generator's reference / "
        "image-edit feature (for example \"edit image\", \"character reference\" or \"image prompt\") together "
        "with the expression prompt. Fresh generations from text alone drift.")
    add("3. **`talking` must match `neutral` exactly except the mouth.** Use edit/inpaint mode and change only "
        "the mouth; it is swapped with neutral many times a second.")
    add("4. Keep the **same canvas shape for all images** (portrait 2:3 or 9:16 works best) and the whole "
        "body in frame. White backgrounds are fine: they are removed automatically.")
    add("5. Save as `characters/<id>/<expression>.png`, then run `python rizz_island.py --art` and check "
        "`review/cast_sheet.jpg`. Anything missing keeps using the placeholder set until `neutral.png` exists.\n")
    add("**Shared style line** (already included at the end of every prompt below):\n")
    add(f"> {STYLE}\n")
    add("Content guardrails: PG only, original characters, no real people, no logos or brand names.\n")

    add("## Characters\n")
    for c in cast.characters.values():
        add(f"### {c.emoji} {c.name} — save to `characters/{c.id}/`\n")
        for expr in EXPRESSIONS:
            add(f"**{expr}.png**\n")
            add("```text")
            add(expression_prompt(c, expr))
            add("```\n")
        add("<details><summary>Optional extras (blink + mouth-open reactions), for image-edit mode</summary>\n")
        for name, desc in OPTIONAL.items():
            base = "neutral" if name == "blink" else name.replace("_talking", "")
            add(f"**{name}.png** (edit `{base}.png`)\n")
            add("```text")
            add(f"Edit this image of {c.raw['name']}: change only the face to show {desc}. Keep the character, "
                f"pose, framing, size, colours, lighting and white background exactly the same. {STYLE}")
            add("```\n")
        add("</details>\n")

    add("## Backgrounds\n")
    add("Save to `backgrounds/<location>.png`. Portrait, ideally 1440x2560 or larger (the extra room is used "
        "for camera moves). Leave the lower middle open: characters stand there.\n")
    add(f"**Shared background style line** (included below):\n\n> {BG_STYLE}\n")
    for loc, desc in BACKGROUNDS.items():
        add(f"**{loc}.png** — {cast.locations.get(loc, '')}\n")
        add("```text")
        add(f"{desc} {BG_STYLE}")
        add("```\n")
    out.write_text("\n".join(L), encoding="utf-8")
    return out


BACKGROUNDS = {
    "pool": "A sunny luxury villa pool deck: a turquoise infinity pool with sparkling water, pink-and-white "
            "striped sun loungers, a giant inflatable flamingo, tall palm trees, white villa walls with "
            "pastel accents, bright blue sky with puffy clouds.",
    "firepit": "The villa fire pit at night: a round stone fire pit with glowing orange flames, curved cushioned "
               "benches with pink and teal pillows, string lights and tiki torches, a deep purple starry sky, "
               "dramatic warm firelight.",
    "lounge": "A bright villa lounge: pastel pink and teal bean bags, a curved velvet sofa, a glowing neon heart "
              "shape on the wall (no words), tropical plants, a shiny floor, colourful cushions.",
    "beach": "A private tropical beach at golden hour: soft pale sand, a small wooden pier, calm turquoise sea, "
             "leaning palm trees, a heart-shaped arch of pink flowers, warm sunset sky.",
    "hideout": "The hideout: a small, dim secret room behind the villa kitchen, shelves of jars and snacks, one "
               "hanging lamp casting a warm pool of light, a lumpy beanbag, cosy teal and purple shadows, "
               "a sneaky gossip-den feeling.",
    "confessional": "The reality-show confessional booth: a single plush pink egg-shaped chair in the centre "
                    "against glossy wallpaper of pink and gold tropical leaves, soft spotlight from the front, "
                    "symmetrical, front-facing camera.",
}
