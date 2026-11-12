# Sound effect slots

Every sound in an episode is synthesised by `foldlib/audio.py`, so this
folder can stay empty. To use your own royalty-free sound instead, drop a
file here named after its slot. Any format ffmpeg reads works (wav, mp3,
ogg, flac). Add variants as `slot_1.wav`, `slot_2.wav`... and one is picked
at random each time (seeded, so renders are repeatable).

| Slot              | When it plays                                         |
|-------------------|-------------------------------------------------------|
| `title_sting`     | frame 0, under the hook title                         |
| `fold_flip`       | the sheet's flap swinging over (folds 1-10)           |
| `fold_crease`     | the crisp crease as the fold lands                    |
| `grow_whoosh`     | each doubling of the column                           |
| `grow_tick`       | the column landing on its new height                  |
| `landmark_chime`  | a landmark appears                                    |
| `landmark_whoosh` | the camera pulls back to frame a landmark             |
| `riser`           | rising tone during the pull-back (trimmed to fit)     |
| `finale_hit`      | the big hit when the last fold lands                  |
| `cta_pop`         | "What should we fold next?"                           |
| `music`           | optional background bed, mixed about 20 dB down       |

The timing comes from `events.json`, which the renderer writes next to the
frames. To try new sounds without re-rendering, run
`python post.py --events output/<episode>/full/events.json`.

An episode can use its own folder via `"sfx_dir": "my_sounds"` in its JSON
(relative to the JSON file); files there take priority over this folder.
