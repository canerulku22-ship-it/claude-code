# Salary-breakdown video

Renders a vertical video (1080×1920, 30 fps, H.264 + AAC) for TikTok, Reels and Shorts:

1. a 3D globe spins, slows onto the country and drops a pin on it
2. hook: "How much would you earn working as a … in …"
3. payslip: gross pay, then every deduction (tax, insurance, student loan, pension)
4. cost of living, with a running "left from your pay" bar
5. what's left each month
6. student loans: the country vs the UK
7. "Would you move to …?"

Each line is narrated and the timing follows the narration. Sound effects (whooshes, pops,
counter ticks, a cash ding, impacts, a sonar ping for the pin) are synthesised. The soundtrack
is mixed with the effects ducked under the voice and normalised to -14 LUFS.

```sh
python3 make_video.py configs/denmark-mcdonalds-manager.json out.mp4   # full render (~1 min on 4 cores)
python3 make_video.py configs/denmark-mcdonalds-manager.json --stills  # key frames as PNG
```

Needs Python 3 with Pillow and numpy, and ffmpeg. Uses Inter Display if it is installed under
`/usr/share/fonts/opentype/inter/`, otherwise DejaVu Sans. Caches (globe texture, voice clips)
go in `.cache/`; render parts go in `build/` next to the output.

## Voice

`"voice": {"engine": "flite", "voice": "slt", "speed": 1.22}` uses ffmpeg's built-in synthesiser.
It needs nothing extra but sounds robotic. For a natural voice use Kokoro:

```sh
pip install kokoro-onnx
mkdir -p models && cd models
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

then set `"voice": {"engine": "kokoro", "voice": "bm_george", "speed": 1.1, "lang": "en-gb"}`.
British voices include `bm_george`, `bm_lewis`, `bm_daniel`, `bf_emma` and `bf_isabella`.

## New episode

Copy a file in `configs/`, change the numbers, text and narration, render. Keep the sources and
assumptions for the figures in the `_notes` list; the script ignores it. Write numbers in the
narration as words ("forty thousand kroner") so the voice reads them correctly.

## Config

| Key | Required | Meaning |
| --- | --- | --- |
| `episode`, `country`, `region` | `region` optional | Pill at the top: `McDonald's manager \| Denmark (Copenhagen)` |
| `flag`, `home_flag` | no | Two-letter flag codes for the map label and the loans table (DK, SE, NO, FI, IS, DE, NL, AT, FR, IT, IE, BE, PL, GB) |
| `globe`, `map_country`, `map_point` | no | `globe: false` skips the intro. The country highlighted on the globe defaults to `country`; the pin goes at `[lon, lat]`, or the centre of the country |
| `globe_lines` | no | Up to 2 lines of text above the spinning globe |
| `hook_lines`, `hook_country`, `hook_question` | first two | Title card: up to 3 lines, the country in big yellow type, then a question |
| `wage_line` | yes | Small line under "MONTHLY BREAKDOWN" (job, hours, city) |
| `symbol`, `symbol_after` | `symbol` | Local currency; `symbol_after: true` gives `1,234 kr` |
| `home_symbol`, `home_symbol_after` | no | Viewer's currency, default `£` |
| `rate_to_home` | yes | 1 local unit in home currency |
| `gross` | yes | Monthly gross pay, local currency |
| `deductions`, `ded_label` | `deductions` | Up to 5 `[name, amount, narration]` rows under the label (default `TAX & DEDUCTIONS`) |
| `bills`, `bills_label` | `bills` | Up to 6 `[name, amount, narration]` rows under the label (default `COST OF LIVING`) |
| `bar_label`, `pct_line` | no | `LEFT FROM MY PAY` and `That's {pct}% of my pay` by default |
| `loans` | no | Student-loan scene: `title`, `subtitle`, `say` (narration), `footnote`, and up to 4 `rows` of `{"label", "here", "home", "better": "here"/"home", "say"}`; the better side is green |
| `compare`, `home_country` | no | Pay table after "what's left" when there is no `loans` scene: `{"title", "gross", "take_home", "left"}` monthly in home currency. Older `compare_value` / `compare_title` configs still work |
| `question`, `cta`, `next_label` | no | End card; `\n` in `question` splits it over two lines |
| `footnote` | yes | Small print under the card; `\n` splits it over two lines |
| `voice` | no | Text-to-speech engine and settings (above). Without it the video has sound effects only |
| `vo` | no | Narration for `globe` (said while it spins), `globe_country` (said as the pin lands), `hook`, `pay`, `take_home`, `left`, `question` |

`data/countries-50m.json` is from world-atlas (Natural Earth); see `data/LICENSE-world-atlas`.
