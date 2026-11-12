"""The series' signature look, kept in one place.

Every episode uses these values, so counters, colours and layout stay
identical across the series. Episode configs only change the material.

Overlay coordinates are in a 1080x1920 canvas; the preview is scaled down.
"""

# --- Canvas and TikTok-safe layout ------------------------------------------

WIDTH, HEIGHT = 1080, 1920
SAFE_TOP = int(HEIGHT * 0.10)       # top 10% stays clear (TikTok header)
SAFE_BOTTOM = int(HEIGHT * 0.80)    # bottom 20% stays clear (caption + music)
SAFE_RIGHT = 930                    # right rail (like/comment/share buttons)
MARGIN_LEFT = 54

# Where the stack's foot sits on screen (fractions of width/height). The
# subject sits a little left of centre to stay clear of the right rail.
SUBJECT_X = 0.47
SUBJECT_Y_FOLDING = 0.545           # while folding the sheet (seen from above)
SUBJECT_Y_COLUMN = 0.63             # once it is a column (low camera)
SUBJECT_Y_SPACE = 0.575             # in space, so the Earth clears the counters

# --- Overlay typography ------------------------------------------------------

FONT_HEAVY = "Inter Display Black"  # numbers, title, landmark names
FONT_LABEL = "Inter Display"        # small caps labels (bold weight)

# Colours as hex (sRGB). The overlay converts them to ASS colours.
ACCENT = "#FFC23D"                  # signature amber: labels and highlights
INK = "#0B0F14"                     # panel fill
WHITE = "#FFFFFF"
PANEL_ALPHA = 0.74                  # opacity of counter panels

TITLE_Y = 640                       # centre line of the hook title
HEADLINE_Y = 880                    # finale headline ("PAST THE MOON!")

# Counter blocks: (x, y) is the panel's top-left corner.
FOLDS_BOX = dict(x=MARGIN_LEFT, y=SAFE_TOP + 22, label_size=40, value_size=150)
LAYERS_BOX = dict(x=MARGIN_LEFT, y=1232, label_size=34, value_size=74)
THICK_BOX = dict(x=MARGIN_LEFT, y=1386, label_size=34, value_size=74)

# Per-character cell widths (in em) so digits never jitter as they change.
DIGIT_EM = 0.64
COMMA_EM = 0.30
SPACE_EM = 0.28
LETTER_EM = 0.66

# --- 3D look ----------------------------------------------------------------

# Environment keyed by log10(view height in metres). The renderer blends
# between the stops, so the journey goes desk -> sky -> stratosphere -> space.
#   (log10 V, sky zenith, sky horizon, ground, grid strength, stars, sun power)
ENVIRONMENT_STOPS = [
    (-2.0, "#7FB3D5", "#DCEAF0", "#2A4352", 1.00, 0.0, 3.0),
    (0.5,  "#74ADD3", "#D6E7EF", "#2A4352", 1.00, 0.0, 3.0),
    (2.0,  "#64A3D0", "#D0E4EE", "#2F4D5B", 0.70, 0.0, 3.0),
    (3.3,  "#4A89C4", "#BDD8EA", "#3B5B57", 0.25, 0.0, 3.1),
    (4.3,  "#22508F", "#9FC4E3", "#4A7057", 0.00, 0.0, 3.2),
    (5.3,  "#081736", "#4373AA", "#4A7057", 0.00, 0.35, 3.6),
    (6.2,  "#02050D", "#0B1730", "#4A7057", 0.00, 1.00, 4.8),
    (10.0, "#010207", "#02040A", "#4A7057", 0.00, 1.00, 5.2),
]

# Key light: comes from the camera's left (azimuth offset) and drops lower
# once the camera is low, so the column's visible faces stay well lit.
SUN_AZIMUTH_OFFSET_DEG = -48.0
SUN_ELEVATION_FOLDING_DEG = 54.0
SUN_ELEVATION_COLUMN_DEG = 34.0

# Above this view height (metres) the flat ground becomes the Earth sphere.
EARTH_SWITCH_M = 9000.0

EARTH_OCEAN = "#1D5B9A"
EARTH_LAND = "#4A7057"
EARTH_LAND_DRY = "#A8925F"
MOON_COLOUR = "#C9C4BB"
GRID_LINE = "#557587"

# Display width of the column as a fraction of the view height once it is
# too thin to see at true scale (true scale is used whenever it is wider).
COLUMN_MIN_WIDTH = 0.030
COLUMN_MIN_WIDTH_SPACE = 0.017     # slimmer once Earth and Moon are in view

# Colour management. "Standard" keeps the palette exact on screen: a hex
# colour here (or the config's material colour) is what the viewer sees.
# Lights are calibrated so a sunlit top face receives about 1.0.
VIEW_TRANSFORMS = ("Standard",)
VIEW_LOOKS = ("None",)
VIEW_EXPOSURE = 0.0

# Camera
CAMERA_FOV_DEG = 32.0
ELEVATION_FOLDING_DEG = 36.0      # looking down on the flat sheet
ELEVATION_STACK_DEG = 20.0        # lower as the stack gets thick
ELEVATION_COLUMN_DEG = 6.0        # low, so the column rises against the sky
AZIMUTH_START_DEG = -24.0
AZIMUTH_END_DEG = -14.0

# How much of the frame height the stack fills when the camera settles.
FILL_FOLDING = 0.42
FILL_COLUMN = 0.30
FILL_LANDMARK = 0.40
