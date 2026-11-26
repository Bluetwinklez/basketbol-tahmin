# Football refit frequency at fixed forecast lead times

This retrospective replays the default opponent-adjusted model in nine European leagues. Each match has a shared hypothetical forecast day, either one or seven days before kickoff. The daily version fits on that cutoff date, the weekly version uses that week's Monday and the monthly version uses the first day of that month. Each fit excludes all results dated at or after its cutoff. The variants use identical fixtures and model settings.

| Archive and forecast lead | Games | Correct, daily / weekly / monthly | Log loss, daily / weekly / monthly | Distinct fit dates, daily / weekly / monthly |
| --- | ---: | --- | --- | --- |
| 2025–26, 1 day | 3,018 | 1,539 / 1,542 / 1,525 | 1.00537 / 1.00524 / 1.00609 | 969 / 291 / 84 |
| 2025–26, 7 days | 3,018 | 1,541 / 1,537 / 1,534 | 1.00564 / 1.00588 / 1.00591 | 969 / 295 / 83 |
| 2026–27 partial, 1 day | 1,075 | 563 / 564 / 566 | 0.99005 / 0.99042 / 0.99441 | 363 / 105 / 36 |
| 2026–27 partial, 7 days | 1,075 | 559 / 561 / 561 | 0.99252 / 0.99289 / 0.99707 | 363 / 109 / 38 |

The day-block accuracy interval includes zero for every weekly and monthly comparison. Weekly fitting uses around 70% fewer league-specific fit dates, but its accuracy signal changes with the forecast lead and evaluation period. Monthly fitting produced worse log loss in all four comparisons. The production schedule remains unchanged.

The lead times share fixtures and should be read separately. The archive cannot verify when the historical fixtures and results were published. The replay does not reproduce the actual freeze time of previously recorded forecasts. Run `python -m scripts.evaluate_football_refit_cadence --output report.json` to produce the report with league splits, confidence coverage, equal-coverage comparisons and input hashes. This run used the archives at `3c89477`.
