# Salary-breakdown video

Renders a ~45–60 s vertical video (1080×1920, 30 fps, H.264) that walks from gross pay
through deductions and monthly bills to "what's left", then ends on a comment prompt.
Made for TikTok, Reels and Shorts; it has no audio track, so add music in the app.

```sh
python3 make_video.py config.example.json out.mp4      # full render (~50 s)
python3 make_video.py config.example.json --stills     # 6 PNG frames in the current dir
```

Needs Python 3 with Pillow, and ffmpeg. Uses Inter Display if it is installed under
`/usr/share/fonts/opentype/inter/`, otherwise DejaVu Sans.

## Config

| Key | Required | Meaning |
| --- | --- | --- |
| `episode`, `country`, `region` | `region` optional | Pill at the top: `EP 1 \| Germany (Berlin)` |
| `hook_lines`, `hook_country` | yes | Up to 3 opening lines, then the country in big yellow type |
| `wage_line` | yes | Small line under "MONTHLY BREAKDOWN" (job, hours, tax setup) |
| `symbol`, `symbol_after` | `symbol` | Local currency; `symbol_after: true` gives `1,234 kr` |
| `home_symbol`, `home_symbol_after` | no | Viewer's currency, default `£` |
| `rate_to_home` | yes | 1 local unit in home currency |
| `gross` | yes | Monthly gross pay, local currency |
| `deductions` | yes | Up to 5 `[name, amount]` pairs; more are dropped |
| `bills` | yes | Up to 6 `[name, amount]` pairs; more are dropped |
| `compare_value`, `compare_title`, `home_country` | no | Comparison box: take-home here vs `compare_value` (home currency) at home |
| `question`, `cta`, `next_label` | no | End-card text |
| `footnote` | yes | Small print shown under the card |

Length grows with the number of lines: 2.2 s per deduction, 2.5 s per bill.
