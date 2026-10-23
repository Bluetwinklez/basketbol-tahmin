# Opponent-adjusted football challenger and wider coverage

This follow-up adds **17,037 distinct historical final scores**, bringing the CC0 community archive from **59,240 to 76,277** across **20 leagues**. Basketball archives and all 95 previously frozen football forecasts remain unchanged.

| New historical league | Code | Distinct finals |
|---|---|---:|
| Belgian First Division A | BE1 | 1,249 |
| Greek Super League | GR1 | 1,018 |
| Scottish Premiership | SC1 | 866 |
| English League One | EN3 | 5,724 |
| English League Two | EN4 | 5,684 |
| Austrian 2. Liga | AT2 | 2,496 |

These six leagues have no current-season source files in the captured upstream revision. They have historical support, not live or upcoming schedule coverage. The collector can refresh selected leagues with `--leagues`, retains per-source hashes, and now reports a per-league inventory: stored seasons, latest final date, active-season finals, active-snapshot availability and future fixture count. The import encountered twelve identical repeated League Two fixture rows; it removed the exact duplicates and reports their count. Conflicting duplicate scores still reject the source snapshot. A repeated fixture is not an additional completed game.

## Challenger

The established baseline calculates separate smoothed home/away scoring averages. The experimental challenger jointly fits league-specific attack, defence and home advantage using a weighted Poisson likelihood. Opponent strength therefore enters the fit directly. Its fixed configuration is a 1,095-day lookback, 180-day half-life and L2 team penalty of 2. There is no target-outcome parameter search. The numerical fit must converge; failure is explicit rather than silently producing baseline output under a new name. Unknown clubs get prior effects plus visible warnings.

The existing baseline remains the default. The Football screen offers **Experimental opponent model · separate ledger**. Choosing it and running creates records in the `opponent/` child ledger. Switching models does not reuse or overwrite baseline forecasts. Manual CLI/MCP requests support the challenger too; manual fixture identity remains unverified.

```sh
python -m bbtahmin futbol collect --leagues BE1 GR1 SC1 EN3 EN4 AT2 --first 2010
python -m bbtahmin futbol compare --season 2025-26 --output rapor/football-challenger
python -m bbtahmin futbol predict --model opponent --league TR1 --home Galatasaray --away Fenerbahçe --date 2026-10-25
python -m bbtahmin futbol daily --model opponent --output rapor/football
python scripts/football_comparison_evidence.py
```

## Same-cohort retrospective comparison

Both candidates train only on dates before each target month and predict identical available 2025–26 finals. All fixtures remain in the evaluation, including sparse-history warnings. Neither candidate is selected or promoted based on the target outcome. Historical publication times are unknown, and multiple source seasons are incomplete.

| Cohort | Baseline correct | Opponent correct | Accuracy change |
|---|---:|---:|---:|
| Original 14 leagues, identical to PR #8 | 1,789/3,744 (47.78%) | 1,819/3,744 (48.58%) | +0.80 percentage points |
| Expanded 20 leagues | 2,242/4,701 (47.69%) | 2,279/4,701 (48.48%) | +0.79 percentage points |
| Turkish subset | 45/99 (45.45%) | 48/99 (48.48%) | +3.03 percentage points |

On the original cohort, mean log loss changes by -0.01107 (lower is better). Paired fixture-date-block bootstrap gives a descriptive 95% interval of **-0.13 to +1.64 percentage points** for winner-accuracy change, and **-0.01624 to -0.00608** for log-loss change. The original accuracy interval includes zero. The expanded accuracy interval is 0.00 to +1.59 percentage points; it is not a prospective success guarantee. All bootstrap samples keep both candidate predictions paired; 2,500 resamples use seed 1729.

Results are mixed by league. Winner accuracy falls in AT1, EN1, ES2, FR1, FR2, GR1 and SC1. Full goal-market Brier/accuracy, team-total/margin errors, interval coverage and 1/X/2 metrics for both models are in `docs/kanit/football_challenger/evaluation.json`; compressed individual paired predictions and bootstrap evidence are retained alongside it. Neither more data nor this retrospective aggregate establishes general future improvement.

Validation includes no-target/same-day-outcome leakage, unknown-team warnings, optimizer failure, separate model ledgers, duplicate/conflicting imports, HTTP model validation and DOM model switching. No rendered-browser visual review or hosted deployment is claimed. Daily scheduled source collection still uses the established baseline; challenger promotion requires a separately defined prospective policy and further evidence.
