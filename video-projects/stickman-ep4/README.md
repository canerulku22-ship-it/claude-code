# Episode 4: "If you ever fall asleep on the last bus home" (3D stickman horror, glow A/B)

An original rule story on a night bus. The characters are translucent and glow (a fresnel "ghost" shader with a slow
shimmer). The bus is a single model, interior and shell, that stays at the origin. The road, streetlights, reflector
posts and bus stops scroll past it according to a distance integral of the bus's speed, so the exterior and interior
shots share one set of geometry.

- **Hook:** the bus at night, headlights on, with passengers glowing in the windows.
- **Silent:** you wake up against the window; the engine cuts out and the cabin lights flicker.
- **Don't look:** over your shoulder down the aisle, then a dolly between the still rows, then from the front:
  faceless, perfectly still.
- **The driver:** his back, the wheel, the road in the headlights. His head ticks, once.
- **Count the stops:** the LED sign counts 1, 2, 3. Each stop is a little darker outside (a time-skip cut hides the
  distance between stops).
- **Fourth stop:** a red "STOP 4" and a hard brake, and everyone stands up on the same frame.
- **Stay in your seat:** you grip the seat in front, and a red ring locks you in.
- **Walk past:** the door opens onto nothing. They walk down the aisle in step and step off into the dark.
- **Whisper:** the last one stops beside you and leans in. Its white eyes and smile are inches from your bowed head.
- **Hands:** the doors close. You look down, and your hands start to glow like theirs, then the rest of you does too.
  The driver turns his head all the way around, with red eyes.
- **CTA:** the bus ("NOT IN SERVICE") pulls away into the dark. "Would you have stayed?", comment yes or no, follow.

## Narration

The narrator is a stock American-English Kokoro voice (`am_michael`, speed 0.9), used as it ships with no voice
cloning, so the accent is clearly American for a US audience. Each line is transcribed by Whisper, and a line is
re-synthesized at a slightly different speed until the transcript matches the script. The earlier Chatterbox engine
is still available with `--engine chatterbox`.

## Glow vs solid (A/B test)

The style is a URL switch (`?style=solid`), so the same episode renders twice with only the character look changed:

- **glow** (default): every character is a translucent ghost. You start warm white, the passengers and driver are
  cold blue-white, and the twist turns you cold.
- **solid**: matte white figures, as in episodes 1-3. Passengers turn into light only as they step off the bus, and
  your hands (then your whole body) turn into light at the twist.

`STYLE=solid node tools/render.js all 4` renders into `out/frames_solid`. `./build.sh` encodes both versions.

Rebuild with `./build.sh` (or `--skip-voice`). `tools/regap.py` re-times pauses without regenerating speech, and
`tools/provisional.py` writes estimated timings so you can preview before the voice exists.
