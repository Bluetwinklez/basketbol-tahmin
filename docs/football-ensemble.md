# Joint-score ensemble and probability reliability

An explicit `ensemble` candidate mixes the established baseline and the opponent-adjusted low-score model at fixed equal weights. All 1/X/2, goal-total, both-teams-score and interval outputs derive from the same mixed joint score distribution. It does not independently blend incompatible market probabilities. Candidate identity and training cutoff must agree. No target outcomes choose weights or promote a default.

```sh
python -m bbtahmin futbol predict --model ensemble --league TR1 --home Galatasaray --away Fenerbahçe --date 2026-10-25
python -m bbtahmin futbol daily --model ensemble --output rapor/football-ensemble
python scripts/evaluate_football_ensemble.py
```

Use a separate daily output directory for each experiment. Existing earliest forecasts are reused rather than overwritten. Read-only MCP `predict_football` accepts optional `model_variant`; the baseline remains its default. Manual fixture identity is not verified. The browser and scheduled daily workflow continue using their established baseline.

## Matched historical evaluation

All four candidates predict the same 3,973 available 2025–26 finals in 17 leagues. Training stops before each target month. Earlier results only; partial archives and unknown historical publication times mean retrospective research, not prospective success evidence.

| Candidate | 1/X/2 accuracy | Multiclass log loss | 2.5 goal direction accuracy | 2.5 goal Brier |
|---|---:|---:|---:|---:|
| Baseline | 47.80% | 1.02993 | 54.47% | 0.248693 |
| Opponent | 49.18% | 1.01780 | 55.58% | 0.247784 |
| Opponent + low-score | 49.21% | 1.01787 | 55.58% | 0.247784 |
| Equal joint ensemble | 48.78% | 1.02218 | 55.10% | 0.247501 |

The ensemble improves these aggregate measures versus the baseline, but does not beat the opponent candidates on winner accuracy or multiclass log loss. No uniform improvement or statistical significance is asserted. Market-direction accuracy uses a fixed 50% threshold, not an odds/value rule, and does not measure returns. These are not the 23 forward football outcomes recently checked in conversation; those are a separate small cohort and were not used to tune this candidate.

The evaluator additionally reports binary log loss, Brier score, ten-bin reliability tables and expected calibration error separately for home win, draw, away win, over 1.5/2.5/3.5 and both teams to score. Bin sample counts and observed frequencies remain visible. These measure calibration; they are not fitted calibration corrections. Aggregate and per-league results are in `docs/kanit/football_ensemble/comparison.json`; matched per-game probabilities and actual goals are retained in `paired_results.json.gz`. Reproduce using the script and the checked-in archive. No roster, injury, odds or shot-based xG inputs were added.

Validation: 293 Python tests and 9 DOM tests pass, including same-day/future/foreign-league exclusion, joint probability bounds, mismatched-candidate rejection and invalid-score-distribution rejection. An actual CLI manual ensemble forecast completed. Frozen prospective forecast files and training archives are unchanged. No new rendered-browser review is claimed for this CLI/MCP/model change.
