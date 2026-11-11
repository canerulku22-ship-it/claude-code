# Your Money Is Melting: inflation explainer (vertical short)

A 72-second, 1080×1920 faceless explainer about inflation and the Cantillon effect. It is built entirely
from code: Kokoro TTS voiceover, Whisper word timings, GSAP/canvas motion graphics rendered frame by frame in
headless Chromium, and procedural sound design.

| File | What it is |
| --- | --- |
| `output/money_melting_full.mp4` | Final video: voice + SFX + music bed (-14 LUFS) |
| `output/money_melting_nomusic.mp4` | Voice + SFX only. Use it to add a trending sound inside TikTok/Reels |
| `output/cover.jpg` | First frame, usable as a cover |
| `script.json` | The script: spoken text, caption styling, pauses |

## Structure and engagement beats

| Time | Scene | What happens on screen |
| --- | --- | --- |
| 0:00 | Hook | A live counter drains from $1,000 with red drips and a "lost so far" ticker; the money then goes invisible |
| 0:03 | Quick test | Stamp slam, then a quiz: A $1,000 / B $900 / C $800, a 3-2-1 countdown and **"Comment A, B or C"** |
| 0:11 | Reveal | C lights up, 2 of 10 blocks break off ("−$200"), and a $0.00 receipt gets stamped "Still −$200" |
| 0:16 | Inflation | Letters drop in; groceries, rent, gas and insurance cards pop on each spoken word; a year ticker runs 2020→2026 |
| 0:21 | Savings | 3D account panel (~3% prices vs ~0.4% interest, "$1,000 earns ≈ $4 a year"); a shelf empties as buying power drains to 80% |
| 0:28 | Twist | "Econ 101" dossier with redacted lines, stamped CLASSIFIED. The music drops out |
| 0:30 | The flow | Beat drop. New money cascades to Banks → Wall Street (1st) → Asset owners (2nd) → You (last) while a price meter climbs |
| 0:40 | Paycheck | +$100 arrives as rent, food and gas go up, so it "buys $91 worth" |
| 0:44 | The name | Silence, then a title slam for **THE CANTILLON EFFECT**, then a **save prompt** (a cursor taps the bookmark) |
| 0:48 | Who gets richer | Homes and stocks shoot up while salary stays flat; "THE GAP" fills in red |
| 0:55 | By design | A clock spins through the work week, the dollar is drawn as a blueprint (156×66 mm), and a dart hits the Fed's 2% target |
| 1:01 | Every. Single. Year. | The bill shrinks to $0.98, $0.96, $0.94 on each word; 10 years leaves $0.82 |
| 1:03 | Close | "Safe" gets struck through to NOT SAFE, the $1,000 literally melts, then a **Follow for Part 2** end card with a tap animation and **Comment "PART 2"** |

The whole video also has karaoke captions (gold = emphasis, red = loss, green = gain), a progress bar, camera
pushes, punches and shakes, and glitch, whip and flash transitions.

## Facts used (keep them current)
- $1,000 from 2020 buys ≈ $800 today: US CPI rose roughly 25% from 2020 to 2025.
- The average US savings rate is ~0.4% (FDIC national rate); inflation is ~3%.
- The Federal Reserve targets 2% inflation per year, so 1/1.02ⁿ gives $0.98, $0.96, $0.94, and $0.82 after 10 years.
- A US bill measures 156 × 66 mm. Richard Cantillon lived 1680–1734.

## Rebuild or edit
1. Edit `script.json` (text, caption colors, pauses) and/or `web/scenes.js` (visuals; every time is tied to spoken words through `w(segment, word)`).
2. Run `./build.sh models/` to regenerate everything, or `./build.sh --skip-voice` to keep the existing voiceover.
   Kokoro models come from `huggingface.co/fastrtc/kokoro-onnx`. Python packages: `kokoro-onnx faster-whisper soundfile scipy`.
3. To preview one moment: `node tools/render.js stills 12.5 45.2` writes `out/stills/`.

**Use your own voice:** record yourself reading every `tts` line in order (pause where the script pauses,
e.g. ~1.5 s after "Lock in your guess" for the countdown), then run
`python tools/voiceover.py --own-voice my_read.wav` and `./build.sh --skip-voice`. Whisper aligns your read to the
script, so every caption, counter and animation re-syncs to your timing.
