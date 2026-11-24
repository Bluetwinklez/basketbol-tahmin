# Football draw and double-chance view

## Why this view exists

In the live football forecast records, a draw was never selected as the single most likely 1X2 outcome (**0 times in 214 predictions**, even though **19%** of those matches ended in a draw). Presenting only a top 1X2 pick hides the draw probability mass on tight fixtures. Surfacing the draw probability directly alongside the top pick and showing double-chance combinations (`1X`, `X2`, `12`) makes the existing 1X2 distribution easier to read without changing the underlying model.

## How `1X`, `X2`, and `12` are derived

Double-chance probabilities are computed directly from the three stored 1X2 probabilities (`home`, `draw`, `away` in `prediction['probabilities']`):

- **`1X`** (home win or draw): `home + draw`
- **`X2`** (draw or away win): `draw + away`
- **`12`** (home win or away win): `home + away`

The best double chance is the entry with the highest probability. Ties break in order `1X`, `X2`, `12` (both in Python `max(...)` in `src/bbtahmin/football/exports.py` and in `mostLikely(...)` in `src/bbtahmin/ui/football.js`).

## CSV export (`prob_1x`, `prob_x2`, `prob_12`)

`export_csv()` in `src/bbtahmin/football/exports.py` appends three columns to the end of the football CSV export:

- `prob_1x` — `round(home + draw, 6)`
- `prob_x2` — `round(draw + away, 6)`
- `prob_12` — `round(home + away, 6)`

Values are calculated and rounded to six decimal places at export time. The export always covers the full report regardless of active browser filters.

## Markdown export (`Best double chance`)

`markdown()` in `src/bbtahmin/football/exports.py` adds a **`Best double chance`** column to the Markdown table:

```markdown
| Date | League | Fixture | Home / draw / away | Over 2.5 | Status | Best double chance |
```

Each row formats the highest double-chance option to one decimal place (for example `1X 78.4%`). Like the CSV export, the Markdown export always includes the full report and is not restricted by browser display filters.

## Local board display

On the `/football` board (`src/bbtahmin/ui/football.js`), each match card displays:

- `Top pick: <Home|Draw|Away> · Draw <pct>%` — the top 1X2 pick (from `prediction.predicted_outcome`, or the highest of `home`, `draw`, `away`) with the draw probability beside it.
- `Home <pct>% · Away <pct>% · Best double chance: <1X|X2|12> <pct>%` — home and away probabilities alongside the highest double-chance option and its percentage.

Percentages are formatted to one decimal place (`(100 * n).toFixed(1)%`, or `—` if non-finite).

## Display-only scope

This feature is strictly a presentation and export view. No football model, training data, probability calculation, calibration, or frozen forecast record in `data/football_ledger/forecasts/` is changed. See also [football.md](football.md#draw-and-double-chance).
