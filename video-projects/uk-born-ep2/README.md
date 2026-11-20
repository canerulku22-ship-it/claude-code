# UK "Where will you be born?" (part 2: Slough)

The same 3D UK map and pin as part 1, with more motion and a faster, more expressive narrator.

- **Hook:** the "WHERE WILL YOU BE BORN? PART 2" card. It shrinks into a top bar when the spin starts, and a
  slot-machine reel underneath whizzes through town names, slows down, and locks on SLOUGH as the pin lands.
- **Spin:** a follow camera leans toward the pin and punches in on every landing. A dotted arc trails each hop, a
  dotted route is drawn across the map, and each landing gets a confetti burst and a shockwave ring.
  - Manchester: a rain cloud and an umbrella ("bring a brolly, forever").
  - Brighton: circling seagulls, one of which nicks the chips.
  - The Highlands: a midge swarm that closes in on "eat you alive".
  - Windsor: the pin gets a crown and a fanfare. "Nah" is a record scratch, the crown drops, and a crash zoom with
    speed lines shows the pin hop two miles up the road.
- **Landing:** SLOUGH drops in letter by letter, with a sad trombone, a 💀 sticker, a wilting pin and a rain cloud.
  Then "You poor bastard."
- **Facts** (cards spring in, then whip out to the next):
  1. A poet begged for Slough to be bombed. Betjeman's "Come, friendly bombs, and fall on Slough!" (1937) types out
     on a scroll in time with the narration, then a "FAIR." stamp.
  2. The Office was set in Slough: a CRT telly showing a grey office, then "NO SET NEEDED".
  3. The Mars bar was first made in Slough in 1932: the year counts up and the bar slides out of its wrapper, then
     "ONLY SWEET THING".
  4. William Herschel, who discovered Uranus, lived in Slough: a starfield, a wobbling planet and a telescope, then
     "CHECKS OUT".
- **CTA:** "BORN IN SLOUGH", "UNLUCKY, MATE", then "COMMENT YOUR TOWN, I'LL ROAST IT NEXT". Follow for part 3.

Captions highlight the word being spoken in a yellow box (red for swears and danger words). Swears are masked in the
captions.

## Voice

The narration uses Chatterbox (`--engine chatterbox --exaggeration 0.7 --cfg 0.3`), cloned from
`audio/voice_prompt.wav`. That prompt is a synthetic British clip made with the stock Kokoro voice `bm_george`, so no
real person's voice is cloned. It reads about 3.5 words a second, against about 2.8 for part 1's plain Kokoro read,
and the pauses are shorter, so the video is 63 s instead of 76 s. Each line is the better of two takes, checked
against a Whisper transcript.

## Rebuild

```
python tools/voiceover.py --engine chatterbox --takes 2 --exaggeration 0.7 --cfg 0.3   # py3.11 env with chatterbox-tts
node tools/render.js cues && python tools/mix.py && node tools/render.js all 4
tools/encode.sh   # uncut, bleeped and no-music MP4s
```
