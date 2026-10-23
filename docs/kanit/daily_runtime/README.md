# Real daily CLI verification — 23 October 2026

Executed from the repository root using the code/data snapshot at commit `bb24ea10d1f414289c0e846023a4d293d85161d2`:

```bash
python -m bbtahmin gunluk --ligler E KBL PBA_GOV --cikti docs/kanit/daily_runtime --json
```

The readers reused locally captured source schedules. EuroLeague, KBL and current PBA provider refreshes had succeeded earlier in this session; their capture times and collection reports are preserved in the data/source inventories. This is not an automatic scoreboard feed.

- **9 upcoming forecasts**, no skipped fixture/model errors.
- **2 original EuroLeague forecasts reused unchanged**, plus **7 newly frozen forecasts** with input/source fingerprints and payload checksums.
- **4** meet the configured 65% probability filter and data diagnostic gate; this is not validated recommendation accuracy.
- **0 settled / 9 pending**, therefore winner accuracy is **unavailable**, not 0% or a prospective success claim.
- The earlier smoke run contained ten upcoming events. One had started before this recorded run, and was correctly omitted from new pregame forecasting.

See [readable report](latest.md), the timestamped `check_*.json` and the `forecasts/` directory. Keep this same `--cikti` directory to continue checking this demonstration. The original two-record EuroLeague file under `../prospective/` remains authoritative and unchanged.

The report retains forecasts that fail the data/probability filter. PBA's adjacent-calibration-season gate is not passed; its day-only final archive cannot silently settle an exact-time prospective record. Pending/unverified results are excluded from all performance numbers.
