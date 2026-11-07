# Chef Cat's Pepperoni Pizza: ASMR cut

A 15.5-second, 1080 × 1920 (9:16), 30 fps ASMR version of
`../cat-chef-pizza-3d`.  There is no intro, no on-screen text and no music.
It goes straight into the cooking in close-up, with every sound synced to
the moment it happens on screen and panned to where it happens.

## The cut

| # | Shot | Frames | What you see and hear |
|---|------|--------|-----------------------|
| 1 | `S3_stretch` | 105 | Flour falls from the chef's paw (one tick per grain as it lands), seven kneading presses (one squish each), the toss, the slap of the landing with a flour puff, a sneeze, two pats on the rim. |
| 2 | `S4_top` | 135 | A dollop of sauce plops, then a wet smear that follows the spoon's speed. 1,300 mozzarella shreds patter down (one tick each on its landing frame), 24 pepperoni slices tap down one by one, oregano crackles. |
| 3 | `S5_bake` | 105 | Seen from inside the oven: the peel scrapes over the stone in time with its movement, the fire crackles, and every cheese bubble pops on the frame it bursts, while the chef purrs and peeks in. |
| 4 | `S6_slice` | 120 | The pizza wheel rolls (its sound follows its speed) and crunches each time it crosses the crust; the cheese pull squelches as the slice lifts and every string snaps on the frame it breaks; then a crunchy bite, three chews and a purr. |

## How the sync works

The sound cues are generated from the same data that drives the animation,
not placed by hand:

* particle landings (`e + flight time`) for flour, cheese, oregano and
  pepperoni;
* paw contact frames from the kneading motion;
* spoon, peel, wheel and slice speeds, sampled per frame, as amplitude
  envelopes;
* the cycle phase of each looping cheese bubble, so pops land on the frame
  the bubble collapses (only for bubbles that are visible);
* each cheese string's stretched length, so its snap plays on the frame it
  breaks.

Each cue carries a 3D position that is projected through the shot camera
and turned into a stereo pan.  `audio.py` synthesises all of it (no
samples) and mixes it dry, with a light presence lift and faint room tone.
`config.py` turns off graphics (`GRAPHICS`), whip transitions
(`TRANSITIONS`) and music (`MUSIC`).

## Pipeline

```
build.py   -> out/cat_chef_asmr.blend + out/timeline.json
render.py  -> out/frames/<shot>/####.png
audio.py   -> out/soundtrack.wav
post.py    -> out/cat_chef_asmr_3d.mp4
```

Rendered at 60 % with 10 adaptive samples and OIDN on a 4-core CPU, then
upscaled to 1080 × 1920 in `post.py`.
