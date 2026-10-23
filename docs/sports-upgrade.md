# Football and basketball reliability expansion

## Data added

The football archive adds **3,133 distinct community-source regulation finals** in
15 league-season snapshots: Belgium (`BE1`), Greece (`GR1`) and Scotland (`SC1`),
each with available 2018–19, 2019–20, 2020–21, 2024–25 and 2025–26 observations.
This extends the preceding 59,240-game archive to **62,373 stored finals across
17 leagues**, assuming the preceding snapshots remain present. These are partial
publisher cohorts, not a claim that all five seasons are complete. No active
2026–27 schedule is available for these three additions.

Sources are pinned to OpenFootball `football.json` commit
`e6744429ee395bc86f247348c6184bb08d4eb361` (CC0). Each compressed snapshot retains
the immutable source URL, capture timestamp and source SHA-256. Exact counts and
gaps are in [expansion evidence](../data/football/expansion_20261023.json).
The collector now recognizes all three codes, including the explicit `sco.1`
filename mapping. Unknown/mixed leagues, duplicate natural fixture identities,
and invalid final scores fail archive loading.

Basketball training data is protected from Turkish cross-provider duplicates:
matching competition, season, Istanbul day and home/away teams count once;
conflicting scores require manual review. Reverse fixtures remain distinct.
Existing archive identities are retained during collection. Turkish future
fixtures now use stable provider IDs; the saved identity registry migrates
previously captured fixture IDs so postponements do not create a second frozen
forecast. Old forecast files are never rewritten. Historical-only duplicate
cleaning is applied defensively when the Turkish regional model loads.

## Explicit football research candidates

`opponent` pools team scoring/conceding strength across venues and adjusts for
opponent strength, with damped updates and eight-match prior shrinkage.
`opponent_dc` adds a training-only low-score correction for 0–0, 0–1, 1–0 and
1–1 outcomes, inspired by the [Dixon–Coles score model](https://doi.org/10.1111/1467-9876.00065).
This implementation is a regularized research variant, not a reproduction of
the paper's fitting procedure or profitability claims. Both preserve the
existing 1,095-day window, 180-day half-life, league isolation and day embargo.
Every goal market is derived from the same joint score distribution.

Defaults remain the established baseline. Explicit opt-in commands:

```sh
python -m bbtahmin futbol compare --season 2025-26 --output rapor/football-comparison
python -m bbtahmin futbol predict --model opponent_dc --league TR1 --home Galatasaray --away Fenerbahçe --date 2026-10-25
python -m bbtahmin futbol daily --model opponent --days 7 --output rapor/football-research
```

The named prediction is a hypothetical inspection example, not a verified
fixture. A distinct output directory separates an experiment's ledger; within
any ledger, an earlier forecast wins even if a new model is requested.

On **229 available 2025–26 results**, monthly fits use only earlier dates:

| League | Games | Baseline accuracy / log loss | Opponent accuracy / log loss | Opponent + low-score accuracy / log loss |
|---|---:|---:|---:|---:|
| Belgium | 104 | 46.15% / 1.0491 | 48.08% / 1.0100 | 48.08% / 1.0077 |
| Greece | 62 | 56.45% / 0.9677 | 56.45% / 0.9522 | 56.45% / 0.9543 |
| Scotland | 63 | 42.86% / 1.0913 | 42.86% / 1.0839 | 42.86% / 1.0940 |

The opponent candidate lowers log loss in these three small cohorts, but the
low-score extension worsens it in Scotland. Winner accuracy changes by only two
games in Belgium. This does not establish general or prospective improvement.
No historical-publication-time guarantee, current-season completeness or model
promotion is inferred. Full winner, goal-market Brier/accuracy, total/margin
errors and intervals: [comparison](kanit/sports_expansion/football_comparison.json),
with [individual predictions](kanit/sports_expansion/football_predictions.json.gz).

## Boards and exports

Football adds pending/community-final filtering, full-report JSON/CSV/Markdown
exports, an empty state, persistent request errors and expanded model/source
details. The API supplies all supported league options, even without forecasts.
CSV escapes spreadsheet formula prefixes; view filters never restrict exports.
Official verification remains unavailable and is distinct from community finals.
Refreshing status no longer rebuilds unchanged cards or enables buttons during
an active job. Both boards have a sport switch visible on narrow screens.

Basketball card details show three example half-point totals around the model
mean, using the nominal normal interval. These are display-only approximations,
not bookmaker lines or separately calibrated market forecasts. They do not
change the frozen prediction, selection gate or outcome accounting. Expanded
details survive a newer report when the same event remains visible.

## Refresh and validation

The existing daily refresh remains at 06:30 UTC. A Sunday **04:45 UTC / 07:45
Europe/Istanbul** run requests historical football files plus Turkish BSL from
2010 and Ukraine from 2016. Sources may lack those seasons. Per-source failures
remain explicit; previously stored results and forecasts are retained. This is
a collection capability, not a claim that those historical basketball backfills
have already succeeded.

```sh
python scripts/refresh_sports.py --backfill
python -m unittest discover -s tests -p test_sports_upgrade.py -v
npm run test:ui
# Development-only rendered fixture test:
npm install --no-save --package-lock=false playwright@1.62.1
npx playwright install chromium
node scripts/visual_smoke.cjs
```

The rendered test exercises actual Chromium at 1440×900, 390×844 and 320×844,
with deterministic intercepted API responses. It checks all ten basketball
filters, domestic labels, pending/final rows, selected/empty views, expanded
details, football status filters, persistent errors and page overflow. It saves
screenshots and a validation manifest as a CI artifact. It is **not** a live
provider, real loopback-server or physical-phone test. Python HTTP tests cover
the actual export routes separately. The complete Python/DOM/rendered suites
run in GitHub Actions; local environment blocks are recorded honestly below.
