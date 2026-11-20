# "Where will you be born this time?" UK edition: Birmingham

A life-story short in the flat 2D cartoon format: a globe spins and zooms into the UK, then Birmingham. A "ticket to
life" card shows the odds, then the video follows "Gaz" from birth to old age through local quirks, stat cards and
running jokes, and loops back to the globe: "Where will you be born next time?"

Every spoken sentence contains "bloody". The strong swears are bleeped in the main mix, and the captions mask them
(f*****g), so the video is safer to monetise.

## Story beats and facts

| Beat | Fact used |
| --- | --- |
| Ticket to life: **1 in 200** | About 657k UK births a year (ONS, NRS, NISRA) out of about 132M world births (UN), 2023 |
| About **15,000** babies a year in Birmingham | ONS births by local authority (approximate) |
| More miles of canal than Venice (35 against about 26) | Canal & River Trust |
| "Second city" (Manchester disagrees) | Common rivalry |
| Spaghetti Junction, **1972** | Gravelly Hill Interchange opened in May 1972 |
| Age 5: Cadbury World; Cadbury in Birmingham since **1824** | John Cadbury's Bull Street shop, 1824; Cadbury World, Bournville |
| Age 16: flat cap, Peaky Blinders | The show is set in Small Heath, Birmingham |
| About **100 million** cups of tea a day | UK Tea & Infusions Association |
| The balti, "supposedly" invented in Birmingham | Balti Triangle origin claim |
| Age 22: London, "a cob?" | "Cob" is the Midlands word for a bread roll |
| Accent poll | The Brummie accent keeps ranking near the bottom of attractiveness polls |
| Age 30: Black Sabbath, heavy metal | Black Sabbath formed in Aston, Birmingham, in 1968 |
| About **80 years** | ONS national life tables, 2021–23 |
| "Tara-a-bit" | The Brummie goodbye |

## How it's built

- `web/core.js` is a 2D canvas engine: one paused GSAP timeline, scenes as pure functions of time, and captions in a
  dark box with orange key words.
- `web/art.js` holds the cartoon kit: people of any age with poses and faces, plus the props and backdrops
  (Birmingham and London skylines, canal, Spaghetti Junction, coach, pub, balti and so on).
- `web/globe.js` draws an orthographic Earth from Natural Earth outlines (`world-atlas`) with `d3-geo`.
- `web/shots.js` is the storyboard: one scene per narration line, with elements popping in on their words.
- Narration uses Chatterbox, cloned from a synthetic British voice sample (Kokoro `bm_george`). Each line is the
  better of two takes, checked against a Whisper transcript.
- `tools/mix.py` writes three mixes: `mix_bleep` (the main one, with swears bleeped), `mix_full` (uncut) and
  `mix_nomusic`. It also adds the sound effects: horn, splash, splat, guitar riff, cheer, sizzle, boings and so on.

```
python tools/voiceover.py --engine chatterbox --takes 2 --exaggeration 0.7 --cfg 0.3   # py3.11 env with chatterbox-tts
node tools/render.js cues && python tools/mix.py && node tools/render.js all 4
tools/encode.sh
```
