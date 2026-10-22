# Experimental Chinese CBA support

CBA support uses a separate archive and separate models. The existing 54,808-game archive and verified NBA/European/NBL model artifacts are unchanged. `data/cba_games.parquet` adds 2,386 dated results from 20 teams, 2021–22 through the observed portion of 2026–27. `data/cba_teams.json` maps the user's Jilin, Xinjiang, Beijing Ducks and Shenzhen names to stable provider IDs; Beijing Ducks and Beijing BeiKong remain distinct.

## Sources and collection

- Numeric final-score facts come from [RealGM CBA team schedules](https://basketball.realgm.com/international/league/40/Chinese-CBA/team/287/Beijing-Shougang/schedule/2026). Each game is deduplicated by box-score ID, win/loss markers check home/away orientation, and conflicting copies fail rather than overwrite stored results. A refresh preserves existing games.
- Quarter scores come from the corresponding public box-score tables. The sample selects 40 uniformly spaced fixtures per season in 2023–24, 2024–25 and 2025–26, without selecting on outcomes. Quarter sums and final-score orientation are checked. Capture reports list any failures.
- Public website access is experimental, not an official supported developer API. Requests are cached with two workers; no account, paid plan, proxy or access-control bypass is used.
- [SportsDataverse's CBA documentation](https://py.sportsdataverse.org/docs/cba/reference/cba/other) records the duration change: older samples use 48 regulation minutes, 2025–26 uses 40. Our season mapping uses 48 through 2024–25 and 40 from 2025–26. Unknown/different rules require a new model regime; contradictory live duration inputs fail.
- The alternate public research spreadsheet lacked exact game dates and was not used for chronological modeling. The official data-site wrappers were reviewed, but their environment/access restrictions were not bypassed. A paid API was not required for this implementation.

Schedule timestamps have **day precision**, encoded as UTC midnight calendar-day keys, not actual tipoff timestamps. Predictions conservatively exclude the entire target Chinese calendar date. Nominal schedule home/away is available; neutral/bubble venue status is not independently verified. Pregame results may include overtime points.

```bash
python -m bbtahmin cba-topla
python -m bbtahmin.veri.cba_quarters
python scripts/evaluate_cba.py
python -m bbtahmin tahmin "Jilin - Xinjiang" "Beijing - Shenzhen" --lig CBA --tarih 2026-10-22T14:52:00+03:00 --json
```

The last command is a historical pregame reconstruction, not a forecast recorded before that fixture began. Collector raw HTML is cached under ignored `data/raw/cba`; only normalized facts and evidence are committed.

## Pregame method

Historical scores are standardized to 40 minutes before the existing lagged feature builder runs. Two fixed Ridge regressions (`alpha=10`, standardized features) estimate margin and total. The immediately preceding season calibrates residual variance and total-score bias; model coefficients are then refit on earlier training plus calibration seasons. Target-season outcomes never train those coefficients. Published targets are rescaled to the requested season's regulation duration. Complete versus partial seasons, correct counts, home-only baseline and errors are retained in [pregame_summary.json](kanit/cba/pregame_summary.json).

## Live-state method and limitations

The live model predicts **remaining regulation margin and total** from a strictly prior pregame estimate plus the observed score, elapsed fraction and remaining fraction. Fixed Ridge regressions learn from real quarter-end states in earlier seasons. Residual variance is calibrated on the preceding season and scales with remaining time. It never receives the target game's final score as an input. A target game's snapshots stay in one season fold, preventing within-game train/test leakage.

The independently held-out 2025–26 quarter sample and [live_summary.json](kanit/cba/live_summary.json) report each period separately, including total MAE, interval coverage and comparison to the unchanged pregame forecast. Three states from one game are correlated and are not three independent matches. Regulation ties are excluded from lead-probability scoring; full-game overtime settlement is not modeled.

| Observed state | Test games / decisive regulation results | Lead accuracy | Total-score MAE | Nominal 80% interval coverage |
|---|---:|---:|---:|---:|
| End of quarter 1 | 40 / 39 | 79.49% | 13.24 points | 72.5% |
| Halftime | 40 / 39 | 92.31% | 11.16 points | 85.0% |
| End of quarter 3 | 40 / 39 | 94.87% | 6.02 points | 90.0% |

This is the **same small 40-game sample**, observed at different stages. The frozen pregame predictor had 76.92% lead accuracy and 11.34-point total MAE on that sample: the live total projection **worsened after the first quarter**, and its 80% interval under-covered. Later score information reduced error, but these numbers do not establish a general improvement or a large-sample live success rate. The screenshot's within-quarter states are outside this exact validation setting.

**This is an experimental manual-state model, not an automatic live feed.** Validation at quarter boundaries does not establish calibration at every within-quarter second. `home_regulation_lead_probability` is a normal-approximation probability of leading at the end of regulation, not an overtime-inclusive sportsbook moneyline probability. Projected scores never drop below already observed points. Overtime, invalid clocks, future observations and stale live inputs are rejected. No bet or live ledger record is placed.

```bash
python -m bbtahmin canli --ev Jilin --dep Xinjiang --skor 16 15 --periyot 1 --kalan 01:28 --tarih 2026-10-22T14:52:00+03:00 --replay
python -m bbtahmin canli --ev Beijing --dep Shenzhen --skor 22 15 --periyot 1 --kalan 01:43 --tarih 2026-10-22T14:52:00+03:00 --replay
```

`--kalan` is the clock **remaining in the named period**. For a current manual observation, supply its actual timezone-aware timestamp and omit `--replay`; observations older than 120 seconds fail. These examples replay the user's screenshot, assume its displayed 14:52 clock corresponds to the conversation date in Istanbul, and are not current scoreboard observations or pre-tipoff predictions. Future/target-day results are excluded from their priors. If the screenshot date/time differs, supply the actual observation timestamp.

The optional MCP server adds a read-only `predict_live_cba` tool with the same explicit manual-state inputs and replay checks. Use the server's `--root` entrypoint to keep data/artifacts scoped to one checkout.
