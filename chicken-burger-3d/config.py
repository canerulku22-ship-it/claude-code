"""
Production config for "The Ultimate Crispy Chicken Burger" 3D film.

Everything recipe-specific lives here so the film can be matched exactly to
the reference cooking video: ingredient list, preparation steps, assembly
order, sauce colour and the (optional) frying-temperature graphic.
"""

# ---------------------------------------------------------------- output ---
FPS = 30
RES_X, RES_Y = 1080, 1920           # final delivery, vertical 9:16
# Cycles renders at RES * RENDER_SCALE, post.py upscales to RES and adds the
# crisp 2D motion graphics at native resolution. Use 1.0 on a fast machine.
RENDER_SCALE = 0.6
SAMPLES = 12                        # Cycles samples (adaptive + OIDN denoise)
VIEW_TRANSFORM = "Khronos PBR Neutral"
EXPOSURE = -0.35

# --------------------------------------------------------------- timeline ---
# (scene id, frames). Every length is a multiple of 15 frames so each cut
# lands on a beat of the 120 BPM soundtrack.
SHOTS = [
    ("S1_intro",        75),
    ("S2_ingredients", 120),
    ("S3_prep",        150),
    ("S4_fry",         135),
    ("S5_build",       120),
    ("S6_exploded",     90),
    ("S7_final",       105),
]
BPM = 120

# ------------------------------------------------------------ the recipe ---
# Ingredient line-up (Scene 2) in order of appearance: (key, on-screen label)
INGREDIENTS = [
    ("chicken",   "CHICKEN FILLET"),
    ("seasoning", "SEASONING"),
    ("egg",       "EGG WASH"),
    ("flour",     "FLOUR"),
    ("buns",      "BURGER BUNS"),
    ("sauce",     "SAUCE"),
    ("lettuce",   "LETTUCE"),
    ("cheese",    "CHEESE"),
]

# Chicken preparation steps (Scene 3) with their on-screen titles.
PREP_STEPS = [
    ("season", "01", "SEASON"),
    ("dip",    "02", "DIP"),
    ("coat",   "03", "COAT"),
]
FRY_TITLE = ("04", "FRY")
BUILD_TITLE = ("05", "BUILD")

# Burger build order, bottom -> top (Scenes 5, 6 and the hero burger).
ASSEMBLY_ORDER = ["bun_bottom", "sauce", "lettuce", "cheese", "chicken", "bun_top"]
LAYER_LABELS = {
    "bun_bottom": "TOASTED BUN",
    "sauce":      "SAUCE",
    "lettuce":    "LETTUCE",
    "cheese":     "CHEESE",
    "chicken":    "CRISPY CHICKEN",
    "bun_top":    "SESAME BUN",
}

# Only show a frying temperature if it is verified from the source video,
# e.g. "175°C". None = no temperature graphic.
FRY_TEMPERATURE_LABEL = None

SAUCE_COLOR = (0.93, 0.50, 0.24)     # creamy burger sauce (linear RGB)

FINAL_TEXT = ("THE ULTIMATE", "CRISPY CHICKEN", "BURGER")

# ----------------------------------------------------------------- brand ---
BRAND = {
    "cream": (255, 244, 224),
    "red":   (232, 65, 44),
    "gold":  (245, 178, 46),
    "ink":   (20, 18, 16),
}
FONT_BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
FONT_SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"


def shot_starts():
    """Global (1-based) start frame of every shot."""
    out, f = {}, 1
    for name, n in SHOTS:
        out[name] = f
        f += n
    return out


TOTAL_FRAMES = sum(n for _, n in SHOTS)
