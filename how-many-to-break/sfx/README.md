# Custom sound effect slots

Every sound is generated procedurally by `hmtb/audio.py`, so this folder can stay empty.
To use a royalty-free recording instead, drop a file here named after its slot. Any
format ffmpeg can read works (`.wav`, `.mp3`, `.ogg`, `.flac`...).

For variety, add numbered variations: `impact_bowling_ball_1.wav`, `impact_bowling_ball_2.wav`, ...
Each event picks one of them, the same one on every re-render.

The first slot that has a file wins, from most to least specific:

| Event | Slots (most specific first) | When it plays |
|---|---|---|
| Title hit | `intro` | frame 0, under the title |
| Pill pop | `pop` | when "Guess in the comments" appears |
| End card | `outro` | when "What should we break next?" appears |
| Object lands | `impact_<drop_object>`, `impact` | every drop, e.g. `impact_bowling_ball` |
| Counter tick | `tick` | with each impact (quiet UI tick) |
| Falling whoosh | `whoosh` | as each object falls in |
| Creak | `creak_<material>`, `creak` | at crack stages, plus random strain creaks |
| Crack | `crack_<material>`, `crack` | at each crack stage |
| Shatter | `shatter_<material>`, `shatter` | at the break (slowed down for slow motion) |
| Boom | `boom` | sub-bass hit under the break |
| Debris | `debris_<material>`, `debris_part`, `debris` | shards and pieces landing after the break |
| Riser | `riser` | the build-up just before the final drop |
| Music | `music` | replaces the procedural tension drone (looped, low) |

Materials: `glass` (glass table), `fabric` (trampoline), `shell` (egg), `wood` (chair).
Drop objects: `bowling_ball`, `watermelon`, `brick`, `iphone`, `anvil`.

The event times come from `out/<episode>/events.json`, which the render writes. To
rebuild just the audio and video after changing sounds, without re-rendering the 3D:

    python make_episode.py episodes/<episode>.json --skip-render
