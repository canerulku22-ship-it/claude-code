# Episode 3: "If your shadow ever stops copying you at dinner" (3D stickman horror)

An original rule story set at a candlelit family dinner. Every shadow on the wall is its own flattened, animated stick
figure, so your shadow can behave on its own:

- **Hook:** a wide candlelit dinner; big shadows loom on the wall; yours starts a hair late.
- **Don't look at it:** you glance at the wall, and its white eyes flick open and shut.
- **Lag:** you lift your fork; your shadow lifts it one second later (a red "+1.0s" counter climbs).
- **It stops:** the shadow stops eating, turns, opens white eyes, and a smile draws on.
- **Never leave the table:** a red ring appears around your chair.
- **Dessert:** mom stands up and walks into the dark kitchen; the candles blow out with smoke.
- **Blackout:** only the shadow's eyes and smile glow, sliding toward mom's empty chair; your chair rattles.
- **Lights back:** "mom" is in her seat, smiling, and casts no shadow.
- **The wall:** her real shadow stands beside the kitchen doorway holding the cake, then pounds to get out.
- **Don't eat the cake:** the thing in mom's seat slides the cake to you, and her eyes go red.
- **CTA:** "Would you have stayed?", comment yes or no, with a follow button.

Rebuild with `./build.sh` (or `--skip-voice`). `tools/regap.py` re-times pauses without regenerating speech;
`tools/provisional.py` writes estimated timings for previewing before the voice exists.
