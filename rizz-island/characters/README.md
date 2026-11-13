# Character art

Save AI-generated images as `characters/<id>/<expression>.png` (`.jpg` and `.webp` work too).
The ids are the `id` fields in `cast.json`.

| file | required | used for |
|---|---|---|
| `neutral.png` | yes | idle, and the fallback for anything missing |
| `talking.png` | recommended | mouth-open twin of neutral, swapped with the voice |
| `shocked.png`, `angry.png`, `smug.png`, `in_love.png` | recommended | reactions (`in-love.png` also works) |
| `blink.png` | optional | eyes closed, for idle blinks |
| `shocked_talking.png`, `angry_talking.png`, `smug_talking.png`, `in_love_talking.png` | optional | lets a character keep the expression while talking; without them the renderer does a "jaw bob" |

Plain white backgrounds are fine: the pipeline removes them with rembg, trims,
and scales every character to the same body height with the feet on one baseline.
As soon as `neutral.png` exists for a character, that character switches from the
placeholder to your art. Run `python rizz_island.py --art` and check
`review/cast_sheet.jpg`.
