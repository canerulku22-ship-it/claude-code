"""Convenience launcher: finds Blender and runs render_episode.py headless.

    python run.py episodes/paper.json --preview
    python run.py episodes/paper.json                # full 1080x1920 render
    python run.py --check                            # are Blender and ffmpeg installed?

Any extra options are passed through to render_episode.py (see its header),
e.g. --stills, --resume, --samples 32, --dry-run.

It is equivalent to:
    blender -b --factory-startup -P render_episode.py -- --config <file> [options]
On a Linux machine without a display it wraps that in xvfb-run when
available, which lets Eevee use a proper OpenGL context (much faster).
Set the BLENDER environment variable to use a specific Blender binary.
"""

import glob
import os
import platform
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

INSTALL_HELP = """
Install hints
  Blender (free, 4.0 or newer): https://www.blender.org/download/
    macOS:   brew install --cask blender
    Windows: winget install BlenderFoundation.Blender
    Ubuntu:  sudo snap install blender --classic   (or: sudo apt install blender)
  ffmpeg (with libass, libx264):
    macOS:   brew install ffmpeg
    Windows: winget install Gyan.FFmpeg
    Ubuntu:  sudo apt install ffmpeg
  Headless Linux servers also want: sudo apt install xvfb
"""


def find_blender():
    env = os.environ.get("BLENDER")
    if env:
        return env
    found = shutil.which("blender")
    if found:
        return found
    candidates = []
    system = platform.system()
    if system == "Darwin":
        candidates = ["/Applications/Blender.app/Contents/MacOS/Blender",
                      os.path.expanduser("~/Applications/Blender.app/Contents/MacOS/Blender")]
    elif system == "Windows":
        candidates = sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender*\blender.exe"),
                            reverse=True)
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def check():
    ok = True
    blender = find_blender()
    if blender:
        out = subprocess.run([blender, "--version"], capture_output=True, text=True).stdout
        print("Blender:", (out.splitlines() or ["?"])[0], "->", blender)
    else:
        ok = False
        print("Blender: NOT FOUND")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        out = subprocess.run([ffmpeg, "-hide_banner", "-filters"], capture_output=True, text=True).stdout
        has_ass = " ass " in out
        print("ffmpeg:", ffmpeg, "(libass OK)" if has_ass else "(WARNING: no libass 'ass' filter)")
        ok = ok and has_ass
    else:
        ok = False
        print("ffmpeg: NOT FOUND")
    if not ok:
        print(INSTALL_HELP)
    return ok


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "--check":
        return 0 if check() else 1
    config, extra = args[0], args[1:]
    blender = find_blender()
    if not blender or not shutil.which("ffmpeg"):
        check()
        return 1
    cmd = [blender, "-b", "--factory-startup", "-P", os.path.join(HERE, "render_episode.py"),
           "--", "--config", os.path.abspath(config), *extra]
    if platform.system() == "Linux" and not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
        cmd = ["xvfb-run", "-a", "-s", "-screen 0 1280x1024x24", *cmd]
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
