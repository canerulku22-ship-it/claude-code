"""Central configuration: paths, video format, safe zones and art constants.

Everything that more than one module needs to agree on lives here, so the
renderer, the sprite pipeline and the CLI never drift apart.
"""
from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------
# Paths (all relative to the rizz-island project folder)
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent

CAST_FILE = ROOT / "cast.json"            # story bible (characters, villa, premise)
STATE_FILE = ROOT / "season_state.json"   # couples, eliminations, storylines, episode no.
VOTES_FILE = ROOT / "votes.txt"           # pasted TikTok comments

CHAR_ART_DIR = ROOT / "characters"        # characters/<id>/<expression>.png (your AI art)
BG_DIR = ROOT / "backgrounds"             # backgrounds/<location>.png (your AI art)
SFX_DIR = ROOT / "sfx"                    # royalty-free sound effects you drop in
MUSIC_DIR = ROOT / "music"                # royalty-free background beats you drop in
VOICES_DIR = ROOT / "voices"              # downloaded Piper voice models (git-ignored)
EPISODES_DIR = ROOT / "episodes"          # episodes/epNN/{script.json, episode.mp4, ...}

BUILD_DIR = ROOT / "build"                # caches, safe to delete (git-ignored)
SPRITE_CACHE = BUILD_DIR / "sprites"      # processed, normalised character cut-outs
PLACEHOLDER_DIR = BUILD_DIR / "placeholders"  # procedurally drawn stand-in art
AUDITION_DIR = BUILD_DIR / "auditions"    # voice test clips

# --------------------------------------------------------------------------
# Character expressions
# --------------------------------------------------------------------------
# The six expressions you generate art for. "talking" is the mouth-open twin of
# "neutral" and is swapped in time with the voice.
EXPRESSIONS = ["neutral", "talking", "shocked", "angry", "smug", "in_love"]

# Optional extras. If present they make the animation richer:
#   blink            eyes closed, used for occasional idle blinks
#   <expr>_talking   mouth-open twin of an expression, so a character can stay
#                    angry/smug/etc. while talking. Without it the renderer holds
#                    the expression and fakes speech with a loudness "jaw bob".
OPTIONAL_EXPRESSIONS = ["blink"] + [f"{e}_talking" for e in ("shocked", "angry", "smug", "in_love")]

ALL_EXPRESSIONS = EXPRESSIONS + OPTIONAL_EXPRESSIONS

# Accept a few alternative spellings for art files people save by hand.
EXPRESSION_ALIASES = {
    "in-love": "in_love", "inlove": "in_love", "love": "in_love",
    "talk": "talking", "mouth_open": "talking", "mouth-open": "talking",
    "eyes_closed": "blink", "eyes-closed": "blink", "closed": "blink",
}

# --------------------------------------------------------------------------
# Normalised sprite canvas
# --------------------------------------------------------------------------
# Every processed sprite is placed on the same transparent canvas, feet on the
# same baseline and the body mass centred, so characters line up side by side
# and expression swaps never make a character jump.
SPRITE_W, SPRITE_H = 1200, 1600
SPRITE_BODY_H = 1080        # height of the "core body" (arms/antennae excluded) at scale 1.0
SPRITE_BASELINE = 1560      # y of the lowest opaque pixel (the feet)

# --------------------------------------------------------------------------
# Video format
# --------------------------------------------------------------------------
VIDEO_W, VIDEO_H = 1080, 1920
FPS = 30
TARGET_MIN_S, TARGET_MAX_S = 65.0, 80.0     # episodes must be over 60 s

PREVIEW_W, PREVIEW_H = 540, 960
PREVIEW_SECONDS = 15.0

# TikTok UI keep-out zones, as fractions of the frame. Captions, name tags and
# vote cards must stay inside the safe rectangle.
SAFE_TOP = 0.10      # top 10%: "Following | For You" tabs
SAFE_BOTTOM = 0.20   # bottom 20%: username, caption, music ticker
SAFE_RIGHT = 0.15    # right rail: like / comment / share buttons
SAFE_LEFT = 0.05     # small breathing room on the left


def safe_rect(w: int = VIDEO_W, h: int = VIDEO_H) -> tuple[int, int, int, int]:
    """Return the (left, top, right, bottom) pixel box that is clear of TikTok UI."""
    return (int(w * SAFE_LEFT), int(h * SAFE_TOP), int(w * (1 - SAFE_RIGHT)), int(h * (1 - SAFE_BOTTOM)))


# --------------------------------------------------------------------------
# Fonts (system fonts found in this environment; override with RIZZ_FONT_*)
# --------------------------------------------------------------------------
FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
    "/usr/share/fonts/opentype/inter/Inter-Black.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FONT_CANDIDATES_EMOJI = [
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
]


def find_font(candidates: list[str], env_var: str | None = None) -> str | None:
    """Return the first font file that exists (an env var can override the list)."""
    import os

    if env_var and os.environ.get(env_var) and Path(os.environ[env_var]).exists():
        return os.environ[env_var]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


# --------------------------------------------------------------------------
# Claude script writer
# --------------------------------------------------------------------------
SCRIPT_MODEL = "claude-opus-5-5"


# --------------------------------------------------------------------------
# Script vocabulary (shared by the script writer, renderer and sound mixer)
# --------------------------------------------------------------------------
SFX_CUES = ["record_scratch", "boom", "gasp", "drumroll", "airhorn", "whoosh", "ding", "pop",
            "phone_buzz", "crowd_ooh", "crowd_aww", "sparkle", "heartbeat", "buzzer", "rimshot",
            "splash", "boing"]
CAMERA_MOVES = {
    "wide": "everyone in the scene visible",
    "two_shot": "the speaker and the person they're talking to",
    "close_up": "tight on the speaker's face",
    "push_in": "slow creeping zoom on the speaker, for tension",
    "whip_pan": "fast blurred pan to the speaker, for a sudden turn",
}
EFFECTS = {
    "none": "no extra effect",
    "shake": "camera shake (shock, anger, big news)",
    "snap_zoom": "instant punch-in zoom (a zinger, a reveal)",
    "freeze_frame": "freeze on the reaction with a record scratch feel",
    "slow_mo": "brief slow-motion moment (dramatic entrance, heartbreak)",
}
TWIST_KINDS = {
    "text_bomb": "someone shouts '📱 I GOT A TEXT!' and reads a message from the producers",
    "new_arrival": "a bombshell walks into the villa (only characters listed as waiting bombshells)",
    "challenge_result": "the result of a silly villa challenge is revealed",
    "recoupling": "a recoupling at the fire pit; someone steals someone's partner",
}
