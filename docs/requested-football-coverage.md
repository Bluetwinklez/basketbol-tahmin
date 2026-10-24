# Screenshot competition coverage

The 24 October 2026 screenshots contain nine distinct pairings across Colombia Primera B, USL League One, USL Championship, El Salvador Primera División, Honduras Liga Nacional, Bolivia División Profesional and Brazil Série B. These competitions must not be mapped to European leagues or to each other's team names.

## Data added

The calendar-year importer adds 2,716 community CC0 finals from eight Série B seasons (2018–2025). The 2019 archive contains 379 finals and 2025 only 57: these are partial archives, not assertions of complete seasons. Sources are pinned OpenFootball south-america / football.json revisions with per-file hashes and row provenance. They are not official result verification. The 2020 pandemic season explicitly permits January 2021 through its documented final date, 29 January; other calendar seasons cannot silently spill into another year.

`CRB AL` is an explicit alias for the archive's `CR Brasil AL`; `Londrina PR` is kept distinct from unverified name variants. Existing earliest forecasts and screenshot manual selections are not rewritten or scored as model forecasts.

## Current limitations

No 2026 Série B source file is available in the selected CC0 repositories. CRB–Londrina is therefore blocked for current recommendations: historical data exists but is stale. The eight other screenshot pairings have no licensed competition archive integrated yet. The audit lists them explicitly as unsupported; no made-up score or probability is substituted. No live red-card or in-play goal model was added.

The daily refresh uses current calendar years only, while weekly backfill refreshes historical years. A missing active source is surfaced as a partial refresh, retains prior archives and never replaces them with empty data. The calendar report is separate from the European collector's report.

## Model validation

Run `PYTHONPATH=src python scripts/evaluate_requested_football.py`. It compares baseline, opponent, opponent_dc and fixed-weight ensemble on the same 380 completed 2024 Série B matches, each trained only before the first day of its target month. All four report three-way results, goal total/margin errors, interval coverage, over 1.5/2.5/3.5, BTTS and probability calibration bins. Always-home, always-under-2.5 and always-BTTS-no comparisons are included. Historical publication times are unknown; this is retrospective research, not forward validation.

The baseline gets 51.58% match outcomes and 62.63% over/under 2.5 directions right; the opponent candidate gets 52.63% and 62.63%. The ensemble reaches 63.42% goal directions (241/380), compared with 62.63% (238/380) for always-under. This three-match difference does not establish a reliable goal-direction improvement or justify changing the default model. More imported history is a coverage increase, not proof of improved future accuracy. Full metrics, calibration and per-match paired predictions are in `docs/kanit/requested_football/`.
