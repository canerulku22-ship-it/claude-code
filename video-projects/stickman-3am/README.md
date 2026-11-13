# "If your phone ever lights up at 3:07 AM": 3D stickman horror short

An original, roughly 60-second creepy "rules" story in the black-and-white stickman format, made in real 3D (Three.js) with
smooth, tweened character animation.

- **Look:** white pictogram props and a poseable stick figure on a black mirror floor, with few color accents: the yellow
  moon/sun, the red warning X, red danger words, red eyes. Grain, vignette, desaturation, and light flickers.
- **Story beats:** the phone lights up at 3:07, a text from your own number, a "Do not read it" X, the phone flipped
  face down, the blanket pulled over the head, a warning text ("Look at the door"), the door creaking open on a backlit
  double, the double's smile drawing on, a red threshold line it leans over but can't cross, knocks, the clock racing
  to 3:33, the door slamming, morning, the message marked "Read 3:08 AM", then red eyes under the bed.
- **Engagement:** a hook line on screen from frame one, karaoke caps captions, a twist ending, and a CTA asking
  "Would you have looked? Comment yes or no", with a follow button.
- **Sound:** procedural drone + heartbeat that tracks tension, phone buzz, creak, knocks, whisper, flicker, slam,
  stingers, ticking clock, morning birds.

| File | Purpose |
| --- | --- |
| `script.json` | narration + caption markup (`!red!` danger words) |
| `web/stick.js` | poseable stick figure (joints, poses, face/smile, glowing eyes) |
| `web/props.js` | bed, nightstand, phone with live screen, window (moon/sun), door + hallway light, clock, red X |
| `web/shots.js` | the 12 beats: camera, lighting, animation, sound cues |
| `tools/mix.py` | horror sound design + mix |

Rebuild: `./build.sh` (or `--skip-voice`). Preview: `node tools/render.js stills 5 20 50`.
Voice: Chatterbox, timbre from a synthetic Kokoro preset (`audio/voice_prompt.wav`); `python tools/voiceover.py --own-voice my_read.wav` re-syncs everything to your own recording.
