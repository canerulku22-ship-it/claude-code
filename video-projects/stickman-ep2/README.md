# Episode 2: "If your room ever has two doors" (3D stickman horror)

Original rule story in the black-and-white stickman format, built on the episode 1 engine with much more animation:

- **Hook:** a second, too-tall door grows out of the floor (dust, rumble, flicker) and a "NEVER OPEN" tag pops.
- **Comparison:** measuring lines draw up both doors, NORMAL vs TOO TALL.
- **Knocks:** the clock flips to 3:00, the tall door jolts on every knock (3 + 3), and the kid trembles in bed.
- **The voice:** speech bubbles type "SWEETIE? IT'S MOM." and "OPEN THE DOOR." Cut to mom asleep down the hall (Zzz).
- **The escape:** the lever turns, the door creaks open, and a stretched figure with black eyes peeks out and tracks the kid,
  who gets out of bed and walks (full walk cycle with footsteps) to the real door.
- **Hallway:** the kid walks to the bathroom while the creature steps out of the bedroom behind them, in the foreground.
- **Bathroom:** the kid locks the door (click), slides down to hug their knees, two feet step into the light under the
  door, then three knocks.
- **Morning:** the extra door dissolves into dust.
- **Twist:** mom asks "Why did you knock on my door last night?" Flashback: the creature knocks on her door,
  "MOM? IT'S ME. OPEN UP." Back in the kitchen, mom's head tilts, the smile draws on, and her eyes go red.
- **CTA:** both doors on an end card; the tall one creaks open and eyes blink inside.

`web/shots.js` holds every beat; `web/stick.js` adds hair, huddle, hand-over-mouth, and knocking poses; `web/props.js` adds
doors with lever and knock jolts, light under the door with feet shadows, bathroom/kitchen sets, and speech bubbles.
Rebuild with `./build.sh` (or `--skip-voice`).
