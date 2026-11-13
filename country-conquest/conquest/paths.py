"""Filesystem locations used by the pipeline (all relative to the project root)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"          # downloaded third-party data (gitignored)
CACHE = ASSETS / "cache"          # derived data: projected world, rasterised flags
CONFIGS = ROOT / "configs"        # base configs you edit
EPISODES = ROOT / "episodes"      # one frozen JSON config per episode
OUT = ROOT / "out"                # rendered videos, events logs, audio
SEASONS = ROOT / "seasons"        # archived final states of finished seasons
STATE = ROOT / "state.json"       # series state: ownership, champion, streak
DEFAULT_CONFIG = CONFIGS / "default.json"
