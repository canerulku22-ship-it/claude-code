# Same Position. Different Level.

A 49-second vertical (1080×1920, 30 fps) motivational video about feeling stuck while you are
actually levelling up. It has a voiceover, an original synthesised soundtrack and sound design,
and motion graphics throughout.

**Final video:** `out/level-up.mp4` (H.264 + AAC, mastered to -14 LUFS for Reels / TikTok / Shorts)
**Stems for re-editing:** `out/stems/voiceover.m4a`, `out/stems/music_sfx.m4a`

## The idea

Viewed from above, a spiral staircase looks like walking in circles: same spot, every lap.
Viewed from the side, every lap is higher. The video is built on that single visual:
**same position, different level.** A game HUD runs throughout. `POS` stays at `000.0` the whole
time while `ALT` and the XP bar keep climbing, until the final `LVL 07 → 08`.

## Script and beats

| Time | Voiceover | Visual |
|---:|---|---|
| 0.3s | You feel stuck. | "STUCK." slams in and a pink cage closes around it, over a heartbeat |
| 1.8s | Same room. Same routine. Same view. | "SAME" marquee; room / clock / window icons; day counter racing while "POSITION: UNCHANGED" |
| 5.5s | Like you've been running for months... and going nowhere. | Hamster wheel, progress bar that hits 97% and resets to 0% (twice) |
| 9.2s | But here's the thing. | Tape-stop: picture and music grind to a halt, cut to black |
| 10.8s | Look at a spiral staircase from above, and it looks like you're walking in circles. | Top-down 3D staircase, "going in circles" ring text, a dot that keeps passing the same pin |
| 15.7s | Same spot. Every single lap. | A ping every lap at "YOU ARE HERE" |
| 18.5s | Now look from the side. | Camera swings 70° down to a side view and the staircase rises into a tower. Riser and snare roll |
| 20.2s | Every lap... you're higher. | Laps light up lime and get labelled, and ALT starts counting |
| 22.2s | Same position. | Silence before the drop |
| 23.7s | **Different level.** | **DROP**: shockwave, light rays, particle burst |
| 25.5s | Every rep nobody saw. That's XP. (×3) | "+250 / +500 / +1000 XP" flies into the HUD bar; achievement cards stack up |
| 36.0s | You're not stuck. You're loading. | "STUCK." gets struck through and becomes "LOADING..."; bar fills to 100% |
| 38.7s | So keep climbing. | Isometric staircase, a cube hopping up on the beat |
| 40.5s | Because one day you'll look down, and you won't even recognize where you started. | Camera looks down a tall spiral tower to a tiny "START" pin far below |
| 45.5s | **Level up.** | XP bar charges, then explodes into "LEVEL UP" with LVL 07 → 08 |

## How it's made

Everything is generated from code, so you can change any line, colour or timing and rebuild.

- `build_audio.py` does three things:
  - Voiceover: Kokoro TTS, an open-weights model (Apache-2.0) that runs locally. The voice is a blend of `am_michael` and `am_onyx`, then EQ, compression and light reverb.
  - Music and SFX: synthesised from scratch with numpy/scipy, so there are no licensing issues. The heartbeat and clock intro, the circling arpeggio, the riser into the drop, the 120 BPM drop (Am–F–C–G with sidechain pump) and the A-major level-up fanfare are all made here. So are the whooshes, booms, glitches, lap pings, XP coins and loading blips.
  - Timeline: lines after the drop snap to the beat. The script writes `build/timeline.json` (every line, beat and impact) and the visuals key off it, so sound and picture stay in sync when the script changes.
- `scene.html` is a canvas renderer. Each frame is a pure function of time.
- `render.js` steps through the frames in headless Chromium (Playwright) and pipes them to ffmpeg.

### Rebuild

```bash
pip install kokoro-onnx soundfile scipy
# Kokoro model files (~350 MB) from github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
mkdir -p models && cd models
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
cd ..
python3 build_audio.py          # -> build/timeline.json, voiceover/music/mix wavs, mix_master.wav
node render.js                  # -> out/level-up.mp4   (needs Playwright + Chromium, ffmpeg)
node render.js --stills 24.6,47 # quick PNG checks of single frames
```

To change the script, edit `SCRIPT` in `build_audio.py`. Each entry is the line plus the pause
before it. To change the voice, edit `VOICE_BLEND`/`SPEED`. To change the look, edit the colour
tokens at the top of `scene.html`.

Fonts: Inter Display and JetBrains Mono (both SIL Open Font License).
