# Broader-history challenger: 23 October 2026

New numeric finals from the official Japanese regular-season schedule are kept separately by division. The established 2021–22 onward model cohort remains the default.

| Archive | Before | After | Added finals | Added observed seasons |
|---|---:|---:|---:|---|
| JP_B1 | 3,657 | 5,644 | 1,987 | 2016-17, 2017-18, 2018-19, 2019-20 |
| JP_B2 | 2,149 | 3,769 | 1,620 | 2016-17, 2017-18, 2018-19 |

**3,607 additional distinct finals**; the Asian archives increase from 9,243 to **12,850** games. These are not extra player rows, fixture copies or additions to the separate 54,808-game core benchmark. Counts do not establish complete season coverage.

## Identical-fixture comparisons

Previous-season-selected policy, using identical held-out fixture IDs on both sides. The completed matched cohort is 2023–24 through 2025–26; partial 2026–27 is shown separately.

| League / cohort | Default correct / games | Expanded correct / games | Default accuracy | Expanded accuracy | Default / expanded log loss | Default / expanded team MAE |
|---|---:|---:|---:|---:|---:|---:|
| JP_B1 / past matched | 1523/2219 | 1517/2219 | 68.63% | 68.36% | 0.587668 / 0.584960 | 8.46 / 8.42 |
| JP_B1 / partial 2026–27 | 77/116 | 80/116 | 66.38% | 68.97% | 0.617870 / 0.605812 | 9.81 / 9.81 |
| JP_B2 / past matched | 886/1260 | 878/1260 | 70.32% | 69.68% | 0.569942 / 0.565920 | 8.65 / 8.66 |
| JP_B2 / partial 2026–27 | 72/108 | 70/108 | 66.67% | 64.81% | 0.643189 / 0.636317 | 9.08 / 8.94 |

**Decision: keep the established default.** Expanded history improves probability log loss, but reduces winner accuracy on both completed matched cohorts. Partial current-season winner counts improve for B1 and deteriorate for B2. These mixed retrospective results are not evidence of a general accuracy increase. No test-season result chooses a learner within a fold. The broader-history research policy is not promoted after inspecting these outcomes.

Both summaries include Brier, total/margin MAE and a fixed-seed 2,000-draw paired day-block bootstrap. The B1 completed-cohort log-loss difference interval excludes zero; B2’s does not. These are exploratory comparisons, not an untouched prospective validation or a multiple-comparison-adjusted guarantee.

## Evidence and reproduction

- [B1 summary](JP_B1/summary.json) and [B2 summary](JP_B2/summary.json) retain full metrics, fold decisions, hashes and skipped folds.
- Each directory includes compressed per-fixture tables for `selected_policy` and the fixed `score` comparison. Gzip is lossless; the CSV fields retain both forecasts and actual outcomes.
- The B1 model-source snapshot is available at commit `81a45e6a69cfd3007d2c6acc2c58b77a2d28031e`; later daily-report fixes do not change Asian model fitting. The B2 and refreshed default manifests record their respective model-source fingerprints.
- [Collection inventories](../asia_data/) retain exact URLs, per-season counts and coverage limitations. Historical publication times, old club continuity and neutral venues remain unverified.

```bash
python scripts/evaluate_history_expansion.py --ligler JP_B1 --output docs/kanit/history_expansion/JP_B1
python scripts/evaluate_history_expansion.py --ligler JP_B2 --output docs/kanit/history_expansion/JP_B2
```

The original two frozen EuroLeague forecasts remain unchanged. Daily prospective records and historical challenger comparisons remain separate.
