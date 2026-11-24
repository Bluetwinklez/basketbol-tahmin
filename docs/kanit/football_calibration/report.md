# Football live calibration report

Ledger cutoff (UTC) **2026-11-23T18:40:38.014012+00:00**.
Scored **149** checksum-verified frozen forecasts joined to community publisher finals under the live scorecard rules.

Excluded **234** snapshot rows. 126 publisher finals lacked a verified kickoff and 27 rows required fixture review. Other nonfinal rows **81** (81 pending).
Frozen fixtures absent from the snapshot **13**.
Missing verified kickoffs by league (DE1 15, EN1 16, EN2 19, ES1 7, FR1 11, IT1 27, NL1 15, PT1 11, TR1 5).

## 1X2 walk-forward temperature

Walk-forward temperature fitting could not run at all. 0 of 149 games had at least 30 earlier finals known before freeze because the football ledger has no per-game result times. No temperature was applied, and no calibration conclusion is possible yet. Reliability bins and logistic slopes are descriptive only for the original frozen forecasts.

**Verdict — inconclusive (n too small)**

The grid is 0.5, 0.6, 0.75, 1, 1.25, 1.5, 2.
Each fit minimizes multiclass log loss using at least 30 eligible finals recorded strictly before the forecast freeze. Ties prefer the temperature closest to 1, then the lower temperature.
The scorecard uses the saved daily report check time for when each final became known. Kickoff and match date do not establish when scores were available.

| Forecast | n | Accuracy (95% CI) | Log loss (95% CI) | Brier (95% CI) |
|---|---:|---:|---:|---:|
| Unscaled | 149 | 55.7% [47.7%, 63.8%] | 0.9801 [0.9177, 1.0408] | 0.5821 [0.5382, 0.6247] |
| Unscaled fallback | 149 | 55.7% [47.7%, 63.8%] | 0.9801 [0.9177, 1.0408] | 0.5821 [0.5382, 0.6247] |
| Paired improvement | 149 | 0.0% [0.0%, 0.0%] | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |

## 1X2 reliability

Reliability bins and logistic slopes are descriptive only for the original frozen forecasts.
Each class is fitted against the other two using an unpenalized logistic intercept and slope on the class forecast log-odds. Perfect calibration corresponds to intercept 0 and slope 1. A slope above 1 indicates too little spread on the log-odds scale.
Bins include the lower edge and exclude the upper edge, with 100% in the final bin. Logistic intervals require finite fits on at least 95% of bootstrap draws.

### Top pick

| Probability bin | n | Mean forecast | Observed frequency |
|---|---:|---:|---:|
| 0%–10% | 0 | — | — |
| 10%–20% | 0 | — | — |
| 20%–30% | 0 | — | — |
| 30%–40% | 25 | 38.7% | 40.0% |
| 40%–50% | 69 | 44.6% | 50.7% |
| 50%–60% | 34 | 54.2% | 64.7% |
| 60%–70% | 16 | 64.1% | 87.5% |
| 70%–80% | 3 | 70.9% | 33.3% |
| 80%–90% | 2 | 82.9% | 50.0% |
| 90%–100% | 0 | — | — |

### Home vs rest

Intercept **0.1180 [-0.2613, 0.5521]**. Slope **1.3966 [0.7237, 2.3368]**. Finite bootstrap fits **2,000**.

| Probability bin | n | Mean forecast | Observed frequency |
|---|---:|---:|---:|
| 0%–10% | 0 | — | — |
| 10%–20% | 2 | 16.5% | 0.0% |
| 20%–30% | 22 | 26.1% | 22.7% |
| 30%–40% | 39 | 35.7% | 28.2% |
| 40%–50% | 42 | 44.9% | 47.6% |
| 50%–60% | 25 | 54.5% | 64.0% |
| 60%–70% | 14 | 64.2% | 85.7% |
| 70%–80% | 3 | 70.9% | 33.3% |
| 80%–90% | 2 | 82.9% | 50.0% |
| 90%–100% | 0 | — | — |

### Draw vs rest

Intercept **-0.9933 [-3.3884, 3.3104]**. Slope **0.2907 [-1.6278, 4.0802]**. Finite bootstrap fits **2,000**.

| Probability bin | n | Mean forecast | Observed frequency |
|---|---:|---:|---:|
| 0%–10% | 1 | 9.5% | 100.0% |
| 10%–20% | 17 | 17.8% | 5.9% |
| 20%–30% | 131 | 24.5% | 22.1% |
| 30%–40% | 0 | — | — |
| 40%–50% | 0 | — | — |
| 50%–60% | 0 | — | — |
| 60%–70% | 0 | — | — |
| 70%–80% | 0 | — | — |
| 80%–90% | 0 | — | — |
| 90%–100% | 0 | — | — |

### Away vs rest

Intercept **0.5431 [-0.0179, 1.2140]**. Slope **1.6587 [1.0321, 2.5682]**. Finite bootstrap fits **2,000**.

| Probability bin | n | Mean forecast | Observed frequency |
|---|---:|---:|---:|
| 0%–10% | 2 | 6.5% | 0.0% |
| 10%–20% | 22 | 15.9% | 13.6% |
| 20%–30% | 40 | 25.9% | 27.5% |
| 30%–40% | 47 | 35.3% | 31.9% |
| 40%–50% | 27 | 44.2% | 55.6% |
| 50%–60% | 9 | 53.4% | 66.7% |
| 60%–70% | 2 | 63.0% | 100.0% |
| 70%–80% | 0 | — | — |
| 80%–90% | 0 | — | — |
| 90%–100% | 0 | — | — |

## Goal markets

These verdicts measure the frozen model's skill against a constant-rate baseline known before each game. Both forecasts are scored on games with the frozen probability and both final scores. The baseline uses the expanding league event rate from scorecard-eligible finals known strictly before freeze, with one prior count for each outcome (50% at cold start). The hit-rate threshold is 50%, with ties predicting yes. Binary Brier uses the squared error of the yes probability.

### Over 2.5 goals

**Verdict — no_skill_over_baseline**

Missing frozen market probabilities **0**. Mean baseline probability **50.0%**.

| Forecast | n | Hit rate (95% CI) | Log loss (95% CI) | Brier (95% CI) |
|---|---:|---:|---:|---:|
| Pre-freeze rate | 149 | 57.7% [49.7%, 65.8%] | 0.6931 [0.6931, 0.6931] | 0.2500 [0.2500, 0.2500] |
| Frozen forecast | 149 | 52.3% [44.3%, 60.4%] | 0.6826 [0.6480, 0.7190] | 0.2448 [0.2286, 0.2619] |
| Paired improvement | 149 | -5.4% [-14.1%, 3.4%] | 0.0105 [-0.0259, 0.0451] | 0.0052 [-0.0119, 0.0214] |

### BTTS

**Verdict — skill_over_baseline**

Missing frozen market probabilities **0**. Mean baseline probability **50.0%**.

| Forecast | n | Hit rate (95% CI) | Log loss (95% CI) | Brier (95% CI) |
|---|---:|---:|---:|---:|
| Pre-freeze rate | 149 | 57.0% [49.0%, 65.1%] | 0.6931 [0.6931, 0.6931] | 0.2500 [0.2500, 0.2500] |
| Frozen forecast | 149 | 57.7% [49.7%, 65.8%] | 0.6615 [0.6317, 0.6917] | 0.2346 [0.2203, 0.2493] |
| Paired improvement | 149 | 0.7% [-6.0%, 8.1%] | 0.0316 [0.0014, 0.0614] | 0.0154 [0.0007, 0.0297] |

## Confidence intervals and verdicts

Percentile intervals use 2,000 game resamples with replacement and seed 20261124. Paired intervals resample each forecast and its comparator together, conditional on the chronological predictions already made. Positive improvement favors the candidate. Multiclass Brier sums squared errors across home, draw and away.

A verdict requires at least 30 comparable games, counting only games with a fitted temperature toward the 1X2 minimum. A smaller sample or an unavailable interval yields `inconclusive (n too small)`. A strictly positive lower 95% bound on mean log-loss improvement yields `skill_over_baseline` for goal markets and `supports recalibration` for 1X2. A lower bound at or below zero yields `no_skill_over_baseline` for goal markets and `does not support recalibration` for 1X2.

The three verdicts use the same 149-game cohort without any adjustment for multiple comparisons, so a borderline confidence interval (for example, a lower bound within 0.005 of zero) is weak evidence at most.
