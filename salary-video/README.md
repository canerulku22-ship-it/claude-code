# Salary-breakdown video

Renders a ~1 minute vertical video (1080×1920, 30 fps, H.264): what a job pays in another
country, every deduction (tax, insurance, student loan, pension), the cost of living, what's
left, a comparison with the same job at home, then "Would you move?". Made for TikTok, Reels
and Shorts; it has no audio track, so add music in the app.

```sh
python3 make_video.py configs/denmark-mcdonalds-manager.json out.mp4   # full render (~1 min)
python3 make_video.py configs/denmark-mcdonalds-manager.json --stills  # 6 PNG frames in the current dir
```

Needs Python 3 with Pillow, and ffmpeg. Uses Inter Display if it is installed under
`/usr/share/fonts/opentype/inter/`, otherwise DejaVu Sans.

## New episode

Copy a file in `configs/`, change the numbers and text, render. Keep the sources and
assumptions for the figures in the `_notes` list; the script ignores it.

## Config

| Key | Required | Meaning |
| --- | --- | --- |
| `episode`, `country`, `region` | `region` optional | Pill at the top: `McDonald's manager \| Denmark (Copenhagen)` |
| `hook_lines`, `hook_country` | yes | Up to 3 opening lines, then the country in big yellow type |
| `hook_question` | no | Line under the country, default `What would I keep?` |
| `wage_line` | yes | Small line under "MONTHLY BREAKDOWN" (job, hours, city) |
| `symbol`, `symbol_after` | `symbol` | Local currency; `symbol_after: true` gives `1,234 kr` |
| `home_symbol`, `home_symbol_after` | no | Viewer's currency, default `£` |
| `rate_to_home` | yes | 1 local unit in home currency |
| `gross` | yes | Monthly gross pay, local currency |
| `deductions`, `ded_label` | `deductions` | Up to 5 `[name, amount]` pairs, under the label (default `TAX & DEDUCTIONS`) |
| `bills`, `bills_label` | `bills` | Up to 6 `[name, amount]` pairs, under the label (default `COST OF LIVING`) |
| `bar_label`, `pct_line` | no | `LEFT FROM MY PAY` and `That's {pct}% of my pay` by default |
| `compare`, `home_country` | no | Table of the same job at home: `{"title", "gross", "take_home", "left"}`, monthly, home currency. Rows appear for the keys you give; each adds 1 s. Older `compare_value` / `compare_title` configs still work. |
| `question`, `cta`, `next_label` | no | End-card text; `\n` in `question` splits it over two lines |
| `footnote` | yes | Small print under the card; `\n` splits it over two lines |

Length grows with the number of lines: 2.2 s per deduction, 2.5 s per bill.
