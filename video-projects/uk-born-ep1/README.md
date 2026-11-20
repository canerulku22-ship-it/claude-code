# UK "Where will you be born?" (part 1: Scunthorpe)

A British banter short. A 3D extruded map of the UK sits in a cartoon sea, and a red map pin bounces between towns
with near-miss jokes before landing on a "random" town. Then come four real facts about the town, roasted.

- **Hook:** a "WHERE WILL YOU BE BORN?" title card with a Union flag and the full UK map, on screen from frame one.
- **Spin:** the pin drops onto Birmingham, then bounces to London ("Nah mate, you can't afford it" with a £££££ tag),
  Cornwall ("too many bloody tourists" as a crowd of tiny tourists pops up) and Edinburgh ("way too posh", where the
  pin gets a top hat). Under a drumroll it skips Manchester, Leeds, Hull and Lincoln, then lands.
- **Landing:** Scunthorpe. A sad trombone plays, the pin wilts, a rain cloud parks over the town, and the narrator
  says "Oh, for f*ck's sake."
- **Fact 1:** the name has a swear word in it. A "BEEP" bar covers the middle letters. A 1996 sign-up window throws
  "Offensive language detected", then a stamp reads "THE SCUNTHORPE PROBLEM (look it up)".
- **Fact 2:** the "Industrial Garden Town" sign, then a wheelie bin turned into a water feature.
- **Fact 3:** the steelworks ("CLOSING?"), then Parliament recalled on Saturday 12 April 2025, then "Westminster +
  Scunthorpe" with a heart.
- **Fact 4:** Keegan and Botham in claret-and-blue on the Scunthorpe United pitch. Then they run off: "SMART LADS".
- **CTA:** a "Certificate of birth: Scunthorpe, Condolences: ✓" card, then "Where did yours land? Comment your town,
  I'll roast it". Follow for part 2.

The facts are real (the AOL 1996 filter incident, the town's "Industrial Garden Town" nickname, the Saturday recall of
Parliament in April 2025 over British Steel, and Keegan and Botham playing for Scunthorpe United). The banter is opinion.

## Pieces

- `tools/build_map.js` turns Natural Earth 1:10m outlines (npm `world-atlas`, public domain) into `web/mapdata.js`.
  The England/Scotland and England/Wales borders are hand-approximated dashed lines.
- Narration uses the stock British Kokoro voice `bm_george` (`--lang en-gb --speed 1.08`), with each line checked
  against a Whisper transcript. Phonetic `say` overrides fix "Edinburgh" and "wheelie bin".
- `#word#` in a caption marks a swear. Captions show it masked (f*ck), and `tools/mix.py` writes three mixes:
  `mix_full` (uncut), `mix_bleep` (1 kHz bleeps over the swears), and `mix_nomusic`.
- The music is a procedural ukulele-style I–V–vi–IV loop at 118 bpm. The sound effects are boings, a drumroll, a
  sad trombone and a bleep.

## Rebuild

```
node tools/build_map.js
python tools/voiceover.py --engine kokoro --voice bm_george --lang en-gb --speed 1.08 --takes 4 --models <kokoro dir>
node tools/render.js cues && python tools/mix.py && node tools/render.js all 4
tools/encode.sh   # uncut, bleeped and no-music MP4s
```
