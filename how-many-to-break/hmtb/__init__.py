"""Shared, Blender-free code for the "How many ___ to break ___?" pipeline.

Everything in this package runs in plain Python (no bpy), so the timeline, stacking
maths, overlay and audio can be imported by both the Blender render script and the
host-side post-processing tools.
"""

import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
FULL_RES = (1080, 1920)
PREVIEW_RES = (540, 960)
PREVIEW_SECONDS = 10.0
