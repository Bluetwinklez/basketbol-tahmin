# Basketball workload decay

This retrospective compares two ways to measure workload over seven UTC days in EuroLeague, KBL, ABA and Türkiye BSL. The reference counts completed games equally. The candidate gives each completed game a weight of `2^(-days / 2)`. The rest of the feature set and the season-by-season training, calibration and learner selection rules are shared. Both versions withhold the entire target UTC day and exclude reviewed forfeits. The replay only measures games in the observed competition.

| Evaluation season | Games | Reference correct | Candidate correct | Accuracy difference | Log loss difference | Brier difference |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023–24 | 1,055 | 730 | 731 | +0.09 pp | −0.000073 | −0.000005 |
| 2024–25 | 1,121 | 772 | 771 | −0.09 pp | −0.000016 | +0.000040 |
| 2025–26 | 1,181 | 791 | 786 | −0.42 pp | +0.000216 | +0.000150 |
| Completed seasons | 3,357 | 2,293 | 2,288 | −0.15 pp | +0.000048 | +0.000065 |
| 2026–27 archive through the evaluation snapshot | 369 | 236 | 237 | +0.27 pp | +0.000361 | +0.000234 |

Positive differences in log loss or Brier represent worse probability estimates. On completed seasons the paired 95% day-block interval for the accuracy difference was −0.41 to +0.12 percentage points. At a top-class probability of 0.65 or higher, coverage on completed seasons was 53.50% for the reference and 53.35% for the candidate. The replay does not establish a gain across seasons. The candidate stays out of production.

Run `python -m scripts.evaluate_basketball_rest_decay --output report.json` from the repository root. These figures use the archive at `341fa6929c206dc1aa57aeaa0d2c18054aad4fd3`. The report includes input and script hashes, learner choices, period splits and equal-coverage comparisons. This shared research learner does not reproduce every production league model. Historical result publication times were unavailable.
