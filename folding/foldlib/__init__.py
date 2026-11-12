"""foldlib - shared code for the "Folding it 1 to 42 times" animation pipeline.

Everything at this package level is plain Python (standard library only) so
it can be imported both inside Blender and from a normal Python interpreter.
The `foldlib.blender` sub-package needs `bpy` and is only imported by the
Blender render script.
"""

import os

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(PACKAGE_DIR)
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
SFX_DIR = os.path.join(ASSETS_DIR, "sfx")
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
