# Your Money Is Melting — v2 (real 3D, shot-for-shot with the reference)

72 s, 1080×1920 vertical explainer on inflation and the Cantillon effect. v2 keeps the reference video's frame
compositions (black void, glowing mannequins on a mirror floor, neon line UI) and upgrades everything else:

| | v1 | v2 |
| --- | --- | --- |
| Rendering | CSS/canvas 2D | **Three.js 3D**: lit glossy figures, blurred mirror-floor reflections, fog, tuned bloom, film grain/vignette/chromatic aberration |
| Voice | Kokoro (flat) | **Chatterbox** expressive narration, deep documentary timbre; every line rendered twice and the take Whisper transcribes word-for-word is kept |
| Camera | 2D pans/zooms | real 3D dolly, pan, push-in, tilt and crane moves per shot |
| Structure | our own scenes | the reference's 18 shots, in order, plus a Part 2 end card |

## Shot list
| # | Shot (mirrors reference) | Upgrades |
| --- | --- | --- |
| 1 | YOUR SAVINGS · REAL VALUE, red glitch number dripping | live ticking value, RGB-split glitch, drips on threads that fall and reflect, close→wide reveal, "▼ You didn't notice" |
| 2 | PAYCHECK +5% vs PRICES +12% columns | glass 3D columns rise on the words, "?" pops on "less" |
| 3 | INFLATION over a small figure | letters resolve from blur, glow dims on "silence" |
| 4 | PRICES 2020→2024 category row | camera pans item to item, prices tick up and flip red on each spoken word |
| 5 | Tilted SAVINGS ACCOUNT panel | +3% prices vs ~0.4% interest bars, "≈ almost nothing" |
| 6 | BALANCE $1,000 ✓ SAME + shelves | items drop off the shelf as buying power drains 100%→80% |
| 7 | $1,000 TODAY = $800 5 YEARS AGO stacks | bills drop in, the top two glitch out into red particles: "Disappeared" |
| 8 | ECONOMICS 101 board | typed list, red strike-through, "NOT TAUGHT" |
| 9 | New money + NOT EVERYONE AT THE SAME TIME | $ stream; figures light up one after another |
| 10–11 | Banks → Wall Street → Asset owners → You | money river where most cash *stops* at the first stations; "✓ Bought $100"; "Prices $100 → $110" |
| 12 | YOUR PAYCHECK +$100, ▲ COSTS MORE | card dims to "= $91 of stuff", floor glow turns red |
| 13 | THE CANTILLON EFFECT over a line of figures | title resolve + glint sweep, flash/shake/bloom hit, music drops out before it |
| 14 | WHO GETS RICHER? chart | camera tracks the line heads; the gap fills red |
| 15 | 50+ HRS / WEEK under a spotlight | volumetric cone, hour counter |
| 16 | Neon dollar bill, value bleeding | Fed target ~2%/yr: $1.00→$0.98→$0.96→$0.94 on "Every. Single. Year.", "-2%" shards fly off |
| 17–18 | SITTING STILL · SAFE → NOT SAFE, then the crowd | crane-up reveal; red $ stream flows from your vault to everyone else; "−$200" |
| 19 | Part 2 end card | follow button tap, "Comment PART 2" after the voice ends |

## Rebuild
`./build.sh` (or `./build.sh --skip-voice` to keep `audio/vo.wav`). Needs Node + Playwright Chromium (WebGL runs on
SwiftShader, ~1 s/frame), ffmpeg, and Python with `chatterbox-tts faster-whisper soundfile scipy`.
- Edit words/captions in `script.json`, visuals in `web/shots.js` (all timing keyed to spoken words via `w(seg, word)`).
- Fix a single bad voice take: `python tools/redo_lines.py s10.1` (regenerates until the transcript matches exactly and re-times everything after it).
- Your own voice: `python tools/voiceover.py --own-voice my_read.wav`, then `./build.sh --skip-voice`.
- Preview frames: `node tools/render.js stills 12.5 40`.

Voice timbre comes from `audio/voice_prompt.wav`, a synthetic clip from Kokoro's `am_onyx` preset — no real person's
voice is cloned.
