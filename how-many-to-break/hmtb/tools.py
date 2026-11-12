"""Finding Blender and ffmpeg, and telling you how to install them if they're missing."""

import os
import shutil
import subprocess
import sys

COMMON_BLENDER_PATHS = [
    "/Applications/Blender.app/Contents/MacOS/Blender",
    r"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    "/snap/bin/blender",
    "/usr/bin/blender",
]

INSTALL_HELP = """
How to install what's missing
-----------------------------
Blender (free, 4.2 LTS or newer; tested with 5.3):
  * Windows: winget install BlenderFoundation.Blender   (or the installer from blender.org)
  * macOS:   brew install --cask blender                 (or the .dmg from blender.org)
  * Linux:   sudo snap install blender --classic         (or the tarball from blender.org)
  * Or as a Python module (no app needed): pip install bpy, then set BLENDER_PYTHON
    to that Python. bpy 5.x needs Python 3.13, bpy 4.x needs Python 3.11.
  If Blender isn't on PATH, set BLENDER=/path/to/blender or pass --blender.

  Headless Linux servers without a GPU also need Mesa for Eevee:
    sudo apt install libegl1 libgl1-mesa-dri mesa-vulkan-drivers

ffmpeg:
  * Windows: winget install Gyan.FFmpeg
  * macOS:   brew install ffmpeg
  * Linux:   sudo apt install ffmpeg

Python packages for the overlay and audio steps:
  pip install -r requirements.txt
"""


def _python_has_bpy(python):
    try:
        r = subprocess.run([python, "-c", "import bpy; print(bpy.app.version_string)"],
                           capture_output=True, text=True, timeout=120)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def find_blender(explicit=None):
    """Return ("app", path) for a Blender executable or ("bpy", python) for the bpy module."""
    for cand in (explicit, os.environ.get("BLENDER")):
        if cand:
            if os.path.basename(cand).lower().startswith("python"):
                return ("bpy", cand)
            return ("app", cand)
    path = shutil.which("blender")
    if path:
        return ("app", path)
    for p in COMMON_BLENDER_PATHS:
        if os.path.exists(p):
            return ("app", p)
    for py in (os.environ.get("BLENDER_PYTHON"), sys.executable):
        if py and _python_has_bpy(py):
            return ("bpy", py)
    return None


def blender_version(found):
    kind, path = found
    if kind == "bpy":
        return _python_has_bpy(path)
    try:
        r = subprocess.run([path, "-b", "--factory-startup", "--version"], capture_output=True, text=True, timeout=120)
        for line in r.stdout.splitlines():
            if line.startswith("Blender"):
                return line.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def blender_command(found, script, args):
    kind, path = found
    if kind == "bpy":
        return [path, script] + list(args)
    return [path, "-b", "--factory-startup", "--python-exit-code", "1", "-P", script, "--"] + list(args)


def check(explicit_blender=None, verbose=True, need_blender=True):
    """Check every dependency. Returns True if everything needed is available."""
    ok = True
    lines = []
    found = find_blender(explicit_blender) if need_blender else None
    if found:
        ver = blender_version(found)
        lines.append("Blender : OK   %s (%s: %s)" % (ver or "unknown version", found[0], found[1]))
    elif need_blender:
        lines.append("Blender : MISSING")
        ok = False
    ff = shutil.which("ffmpeg")
    if ff:
        r = subprocess.run([ff, "-version"], capture_output=True, text=True)
        lines.append("ffmpeg  : OK   %s" % r.stdout.splitlines()[0])
    else:
        lines.append("ffmpeg  : MISSING")
        ok = False
    for mod in ("numpy", "PIL"):
        try:
            __import__(mod)
            lines.append("%-8s: OK" % mod)
        except ImportError:
            lines.append("%-8s: MISSING (pip install -r requirements.txt)" % mod)
            ok = False
    if verbose:
        print("\n".join(lines))
        if not ok:
            print(INSTALL_HELP)
    return ok
