# Football live calibration report

Ledger cutoff (UTC) **2026-11-25T17:34:24.215088+00:00**.
Scored **159** checksum-verified frozen forecasts joined to community publisher finals under the live scorecard rules.

Excluded **240** snapshot rows. 126 publisher finals lacked a verified kickoff and 27 rows required fixture review. Other nonfinal rows **87** (87 pending).
Frozen fixtures absent from the snapshot **1**.
Missing verified kickoffs by league (DE1 15, EN1 16, EN2 19, ES1 7, FR1 11, IT1 27, NL1 15, PT1 11, TR1 5).

## 1X2 walk-forward temperature

Walk-forward temperature fitting could not run at all. 0 of 159 games had at least 30 earlier finals known before freeze because the football ledger has no per-game result times. No temperature was applied, and no calibration conclusion is possible yet. Reliability bins and logistic slopes are descriptive only for the original frozen forecasts.

**Verdict — inconclusive (n too small)**

The grid is 0.5, 0.6, 0.75, 1, 1.25, 1.5, 2.
Each fit minimizes multiclass log loss using at least 30 eligible finals recorded strictly before the forecast freeze. Ties prefer the temperature closest to 1, then the lower temperature.
The scorecard uses the saved daily report check time for when each final became known. Kickoff and match date do not establish when scores were available.

| Forecast | n | Accuracy (95% CI) | Log loss (95% CI) | Brier (95% CI) |
|---|---:|---:|---:|---:|
| Unscaled | 159 | 54.1% [46.5%, 61.6%] | 0.9901 [0.9291, 1.0464] | 0.5891 [0.5465, 0.6291] |
| Unscaled fallback | 159 | 54.1% [46.5%, 61.6%] | 0.9901 [0.9291, 1.0464] | 0.5891 [0.5465, 0.6291] |
| Paired improvement | 159 | 0.0% [0.0%, 0.0%] | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |

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
| 30%–40% | 26 | 38.6% | 38.5% |
| 40%–50% | 74 | 44.6% | 48.6% |
| 50%–60% | 38 | 54.3% | 63.2% |
| 60%–70% | 16 | 64.1% | 87.5% |
| 70%–80% | 3 | 70.9% | 33.3% |
| 80%–90% | 2 | 82.9% | 50.0% |
| 90%–100% | 0 | — | — |

### Home vs rest

Intercept **0.1126 [-0.2471, 0.5367]**. Slope **1.3205 [0.6832, 2.2082]**. Finite bootstrap fits **2,000**.

| Probability bin | n | Mean forecast | Observed frequency |
|---|---:|---:|---:|
| 0%–10% | 0 | — | — |
| 10%–20% | 2 | 16.5% | 0.0% |
| 20%–30% | 22 | 26.1% | 22.7% |
| 30%–40% | 43 | 35.6% | 30.2% |
| 40%–50% | 44 | 44.9% | 47.7% |
| 50%–60% | 29 | 54.6% | 62.1% |
| 60%–70% | 14 | 64.2% | 85.7% |
| 70%–80% | 3 | 70.9% | 33.3% |
| 80%–90% | 2 | 82.9% | 50.0% |
| 90%–100% | 0 | — | — |

### Draw vs rest

Intercept **-0.7332 [-3.0220, 3.3981]**. Slope **0.4511 [-1.4446, 4.1281]**. Finite bootstrap fits **2,000**.

| Probability bin | n | Mean forecast | Observed frequency |
|---|---:|---:|---:|
| 0%–10% | 1 | 9.5% | 100.0% |
| 10%–20% | 17 | 17.8% | 5.9% |
| 20%–30% | 141 | 24.4% | 23.4% |
| 30%–40% | 0 | — | — |
| 40%–50% | 0 | — | — |
| 50%–60% | 0 | — | — |
| 60%–70% | 0 | — | — |
| 70%–80% | 0 | — | — |
| 80%–90% | 0 | — | — |
| 90%–100% | 0 | — | — |

### Away vs rest

Intercept **0.4102 [-0.1255, 1.0275]**. Slope **1.5656 [0.9049, 2.4360]**. Finite bootstrap fits **2,000**.

| Probability bin | n | Mean forecast | Observed frequency |
|---|---:|---:|---:|
| 0%–10% | 2 | 6.5% | 0.0% |
| 10%–20% | 23 | 16.0% | 13.0% |
| 20%–30% | 44 | 25.8% | 27.3% |
| 30%–40% | 49 | 35.2% | 30.6% |
| 40%–50% | 30 | 44.1% | 50.0% |
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
| Pre-freeze rate | 159 | 57.2% [49.7%, 64.8%] | 0.6931 [0.6931, 0.6931] | 0.2500 [0.2500, 0.2500] |
| Frozen forecast | 159 | 52.2% [44.7%, 59.7%] | 0.6854 [0.6510, 0.7219] | 0.2462 [0.2299, 0.2635] |
| Paired improvement | 159 | -5.0% [-13.8%, 3.8%] | 0.0078 [-0.0287, 0.0421] | 0.0038 [-0.0135, 0.0201] |

Frozen probability coverage **100.0%** of **159** eligible games. Ten-bin ECE **0.0848**.

Descriptive ten-bin expected calibration error on original frozen probabilities; not a calibration fit, significance test or evidence of future success.
Bins are [lower, upper), with probability 1 included in the last bin. ECE weights each nonempty bin's absolute forecast-frequency gap by its game count; it depends on binning and sample size. Empty cohorts have no ECE.

| Probability bin | n | Mean forecast | Observed frequency |
|---|---:|---:|---:|
| 0%–10% | 0 | — | — |
| 10%–20% | 0 | — | — |
| 20%–30% | 0 | — | — |
| 30%–40% | 6 | 38.3% | 66.7% |
| 40%–50% | 44 | 46.1% | 56.8% |
| 50%–60% | 60 | 54.7% | 51.7% |
| 60%–70% | 34 | 64.1% | 55.9% |
| 70%–80% | 14 | 73.8% | 85.7% |
| 80%–90% | 1 | 81.4% | 0.0% |
| 90%–100% | 0 | — | — |

### BTTS

**Verdict — no_skill_over_baseline**

Missing frozen market probabilities **0**. Mean baseline probability **50.0%**.

| Forecast | n | Hit rate (95% CI) | Log loss (95% CI) | Brier (95% CI) |
|---|---:|---:|---:|---:|
| Pre-freeze rate | 159 | 56.6% [49.1%, 64.2%] | 0.6931 [0.6931, 0.6931] | 0.2500 [0.2500, 0.2500] |
| Frozen forecast | 159 | 57.9% [50.3%, 65.4%] | 0.6660 [0.6388, 0.6953] | 0.2367 [0.2237, 0.2509] |
| Paired improvement | 159 | 1.3% [-5.7%, 8.2%] | 0.0272 [-0.0021, 0.0543] | 0.0133 [-0.0009, 0.0263] |

Frozen probability coverage **100.0%** of **159** eligible games. Ten-bin ECE **0.0256**.

Descriptive ten-bin expected calibration error on original frozen probabilities; not a calibration fit, significance test or evidence of future success.
Bins are [lower, upper), with probability 1 included in the last bin. ECE weights each nonempty bin's absolute forecast-frequency gap by its game count; it depends on binning and sample size. Empty cohorts have no ECE.

| Probability bin | n | Mean forecast | Observed frequency |
|---|---:|---:|---:|
| 0%–10% | 0 | — | — |
| 10%–20% | 0 | — | — |
| 20%–30% | 0 | — | — |
| 30%–40% | 0 | — | — |
| 40%–50% | 32 | 46.7% | 46.9% |
| 50%–60% | 74 | 54.7% | 52.7% |
| 60%–70% | 47 | 63.5% | 68.1% |
| 70%–80% | 6 | 73.0% | 66.7% |
| 80%–90% | 0 | — | — |
| 90%–100% | 0 | — | — |

## Confidence intervals and verdicts

Percentile intervals use 2,000 game resamples with replacement and seed 20261124. Paired intervals resample each forecast and its comparator together, conditional on the chronological predictions already made. Positive improvement favors the candidate. Multiclass Brier sums squared errors across home, draw and away.

A verdict requires at least 30 comparable games, counting only games with a fitted temperature toward the 1X2 minimum. A smaller sample or an unavailable interval yields `inconclusive (n too small)`. A strictly positive lower 95% bound on mean log-loss improvement yields `skill_over_baseline` for goal markets and `supports recalibration` for 1X2. A lower bound at or below zero yields `no_skill_over_baseline` for goal markets and `does not support recalibration` for 1X2.

The three verdicts use the same 159-game cohort without any adjustment for multiple comparisons, so a borderline confidence interval (for example, a lower bound within 0.005 of zero) is weak evidence at most.
