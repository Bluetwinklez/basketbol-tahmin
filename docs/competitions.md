# Separate ECW, FEC and VTB support

The extension adds pregame models for EuroCup Women (`ECW`), FIBA Europe Cup men (`FEC`) and VTB United League men (`VTB`). These are independent fixed Ridge models; they do not share player identities, outcomes, calibration or fitted parameters with men's EuroCup, CBA or the original four-league model. No live-state prediction has been validated for these competitions.

## Sources and coverage

| Code | Stored finished games | Seasons | Source |
|---|---:|---|---|
| ECW | 674 | 2023–24 through partial 2026–27 | Official FIBA public results pages |
| FEC | 651 | 2023–24 through partial 2026–27 | Official FIBA public results pages |
| VTB | 860 | 2023–24 through partial 2026–27 | Public RealGM current-team schedules |

These are separate files in `data/competitions/`, leaving the original 54,808-game archive and CBA archive intact. [Collection reports](kanit/competitions/) list source URLs and season counts. Raw website pages are excluded from Git. FIBA has public pages; this collector does not establish a supported developer API contract or use authenticated GDAP endpoints.

FIBA parsing validates competition name, gender and season and uses stable organisation IDs instead of season-specific team IDs. Unfinished, live, future, zero-score and tied games do not enter the binary-winner archive. Tied aggregate-leg games therefore remain outside these results. Fixtures are stored separately. Nominal home/away comes from the source; neutral venues are not independently verified. Scores may include overtime. Historical completeness is not guaranteed.

VTB coverage follows the **current 11-team catalog** into previous seasons. Games between departed teams can be missing; this is not a complete historical league archive. Dates have day precision, not verified tipoff times. The collector excludes same-day results; the ledger does not use day-only dates to certify pre-tipoff records. An independently timestamped result source is still needed for VTB/CBA ledger settlement.

Current-season pages refresh when the collector is rerun; older pages are cached. Conflicting persisted scores fail explicitly rather than silently overwriting history. This preserves an audit trail but requires reviewing a legitimate source correction.

## Historical evaluation

Fixed specification: StandardScaler and Ridge alpha 10 for margin and total. Seasons before the preceding season train the inner model. The preceding season supplies residual variance and total bias; the final model refits on all earlier seasons. Target-season outcomes update features only after their UTC day ends; they never fit or calibrate that season's model. No hyperparameters were tuned against these test seasons. Future predictions repeat this procedure using earlier-day results only.

| Completed 2025–26 test | Correct / games | Winner accuracy | Always-home baseline | Total MAE, points |
|---|---:|---:|---:|---:|
| ECW | 150 / 214 | 70.09% | 49.07% | 13.62 |
| FEC | 133 / 195 | 68.21% | 61.03% | 12.12 |
| VTB | 206 / 254 | 81.10% | 52.36% | 13.49 |

One completed test season per league is limited evidence. These percentages measure winner selection, not exact-score accuracy or profitability. Partial 2026–27 is separate in [summary.csv](kanit/competitions/summary.csv); it must not replace the completed-season result. Per-game predictions and a dataset-hash manifest make the evaluation reproducible. This extends coverage; it does not demonstrate improvement of the original NBA/NBL models or an advantage over bookmaker odds.

## Cold starts and reliability

Teams with fewer than five stored competition games in the preceding 400 days are explicitly flagged `az_veri`. This includes several requested screenshot teams. Missing domestic-league games, lineups, injuries and roster turnover are not invented or filled with men's competition results. Low-history estimates rely heavily on league priors. Their probability and 80% score intervals have **not** been separately validated. The displayed interval is a residual-normal approximation, not a guaranteed coverage level.

To improve this model responsibly, prioritize timestamped domestic-league history and roster availability, exact event identities and tipoffs, additional held-out seasons, and cold-start-specific calibration. Measure log loss, Brier score, total MAE and interval coverage alongside winner accuracy before enabling new features.

## Run

```bash
python -m bbtahmin lig-topla --ligler ECW FEC VTB
python scripts/evaluate_competitions.py
python -m bbtahmin tahmin "ZKK Celje - KP Brno" --lig ECW --tarih 2026-10-22T19:00+03:00 --json
python -m bbtahmin bulten --lig ECW
```

The named historical matchup is a replay example. Use a verified future fixture and `--kaydet` to make a new pre-tipoff record. Bulletin support requires a fresh stored snapshot; mapping a competition name does not establish that every market or team has sufficient history. MCP's existing bulletin tools support these codes; `dataset_status` exposes archive counts and `research_results` exposes their historical metrics.

[The five screenshot reconstructions](kanit/competitions/2026-10-22_reconstruction.json) were generated **after scheduled tipoff**, using earlier-day outcomes only. They are explicitly ineligible for prospective accuracy and must never be presented as forecasts published before these matches. Historical source revisions can also differ from what was available at the original time. The five earlier CBA prospective records remain unchanged.
