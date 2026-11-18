# Episode 5: "If your elevator ever stops on a floor you didn't press" (3D stickman horror)

An original rule story set in a steel elevator car that opens onto a long apartment hallway. The car's back wall is a
real mirror (a three.js `Reflector`), and the twist happens only in the reflection. The characters use the
translucent glowing style from episode 4: you are warm white, and the thing is cold blue.

- **Hook:** alone in the elevator. The display climbs 4, 5, 6 and stops. Only "8" is lit on the panel.
- **Don't step out:** a ding, and the doors open onto a dark hallway.
- **Exactly like yours:** the same red-diamond carpet and the same flickering light.
- **At the very end:** the end lamp sputters on, showing a figure standing face to the wall (telephoto zoom).
- **Don't speak, don't hold the door:** your hand drifts toward the door and pulls back. You press close, once.
- **Closing slowly:** from behind you, the doors creep shut while the figure stays still.
- **Halfway:** a clunk, the display glitches red, and the figure is reflected in the mirror. You look down.
- **Not facing the wall anymore:** through the gap, the end of the hall is empty. Then the figure is closer, with
  white eyes, then closer again, smiling.
- **Press close again:** it sprints. The doors slam on it with a bang, then silence.
- **The mirror:** you turn around. The reflection shows you, and in the corner behind you, a figure face to the wall.
  It turns its head all the way around, the lights die, and the display shows a red "?".
- **CTA:** from the hallway of your floor the doors open. You're standing inside, and only the mirror shows who's
  riding with you. "Would you have stepped out?", comment yes or no, and a follow button.

The narration uses the stock American-English Kokoro voice `am_michael` at speed 0.9, with each line checked against
a Whisper transcript. `?style=solid` renders matte figures instead (`STYLE=solid node tools/render.js all 4`).

Rebuild with `./build.sh [models_dir]` (or `--skip-voice`).
