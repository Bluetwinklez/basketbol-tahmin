# Daily forecasts and result tracking

Run from the repository root after installing Python 3.12+ and the dependencies:

```bash
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
python -m bbtahmin gunluk --guncelle
```

This command refreshes public EuroLeague, KBL, Japanese B1/B2 and current PBA Governors Cup schedules/results. It generates forecasts for confirmed fixtures within the next 48 hours, keeps the first forecast for each event, checks available finals, and prints a readable table. A probability filter defaults to 65%; passing it is not a validated recommendation or a guaranteed success rate.

The report is written to `rapor/daily/latest.md`. Timestamped JSON checks and exclusive-create forecast files retain the detailed evidence. The directory is local and ignored by Git: back it up if you use it as your prospective record. Always reuse the same `--cikti` directory. The original checked-in EuroLeague forecasts under `docs/kanit/prospective/` are also reused automatically, ahead of any later prediction of the same event. Each fixture is counted once, using its earliest known record.

```bash
# Japanese leagues only, next 24 hours.
python -m bbtahmin gunluk --guncelle --ligler JP_B1 JP_B2 --saat 24
# Read the existing snapshots without contacting providers.
python -m bbtahmin gunluk
# Machine-readable output; lower-probability/rejected forecasts remain visible.
python -m bbtahmin gunluk --min-guven 0.70 --json
# Keep a separate explicitly named research ledger.
python -m bbtahmin gunluk --guncelle --cikti rapor/my-ledger
```

`--guncelle` is a one-time refresh when the command runs. It does not install a scheduler or continuously monitor scores. Run it again after games finish to check results. Refresh failures are shown per source, and no new forecast is made for a failed source. Fixtures must have been captured within 24 hours. Existing predictions remain readable when a source becomes stale, but are not marked selected. Changed fixture identities/tipoffs require explicit review; their original forecasts remain intact. A checksum failure in an existing forecast stops the run instead of silently replacing it.

## What the performance numbers mean

Only final results with compatible event/league/team identities, a sufficiently precise start time and a valid capture time enter accuracy. Pending, failed and unverified matches are excluded. With zero finals, accuracy is **unavailable**, not 0%. The report retains winner correctness, both team errors, team MAE, total and margin errors, probability scores, and 80% total/margin interval coverage. JSON also retains signed and percentage errors. Signed error is forecast minus actual; absolute errors are measured in points.

The PBA publisher's historical final clocks have only day precision in the validated archive. Those rows cannot automatically settle exact-time prospective forecasts; they stay pending until better timestamped final evidence is supplied. The current PBA model also fails its adjacent-calibration-season gate. WNBL is not Australian NBL, and no automatic live predictor is offered for these leagues. Unsupported leagues are not silently routed through a different model.

The daily report is a small prospective research ledger, separate from historical test metrics. It makes no profitability claim. Small batches cannot establish general accuracy.

## Historical data expansion

Older Japanese regular-season numeric results are collected from the official public schedule with division, season, pagination, final-score and source-identity checks. The established Japanese models retain their **2021–22 onward** cohort. Earlier data is stored for a separately measured broader-history challenger, rather than silently changing production forecasts.

```bash
# Source years are inclusive. For Japan these are season START years.
python -m bbtahmin asya-topla --kaynaklar Japan --baslangic 2016 --bitis 2020
# Refresh current sources without backfilling history.
python -m bbtahmin asya-topla --current-only
# Compare expanded history and the established default on IDENTICAL fixtures.
python scripts/evaluate_history_expansion.py
# Reproduce the established Asian models and all held-out metrics.
python scripts/evaluate_asia.py
python -m bbtahmin veri-denetle
```

For KBL, explicit source-year bounds refer to calendar years; for RealGM PBA, they refer to source season-end years. The current PBA publisher is separately refreshed because its campaign is explicitly identified, not inferred from July.

The expansion comparison reports matched winner accuracy, log loss, Brier score, team/total/margin MAE and paired day-bootstrap log-loss differences. Completed observed cohorts and partial 2026–27 results are separate. More rows alone do not establish completeness or predictive improvement. Retrospective source publication times, roster histories and the Japanese league reorganisation remain limitations.
