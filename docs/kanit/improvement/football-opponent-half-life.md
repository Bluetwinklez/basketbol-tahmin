# Recency in the opponent-adjusted football model

The model gives earlier results exponentially less weight. This replay compares half-lives of 90, 180 and 360 days in nine European leagues. It uses the same opponent-strength algorithm, archive window, team identities and matched seven-day lead with weekly cutoffs for all variants. The 180-day version reproduces the production model at the same cutoff.

For each league and target season, the first date half of the preceding season chooses a half-life by log loss. The second half must show at least one percentage point higher accuracy, at least 0.005 lower log loss and a Brier score no worse than the 180-day reference. Otherwise the fixed policy keeps 180 days. Antigravity's review reinforced that the candidate must be fixed before the target dates. Raw variants are also reported to show their performance under the same fixtures.

| Archive cohort | Games | Correct, 90 / 180 / 360 days | Log loss, 90 / 180 / 360 days |
| --- | ---: | --- | --- |
| 2025–26 | 3,018 | 1,515 / 1,537 / 1,529 | 1.01423 / 1.00588 / 1.00271 |
| 2026–27 partial | 1,075 | 551 / 561 / 561 | 1.00216 / 0.99289 / 0.99136 |

No league passed the validation gate in either period. The raw 360-day variant lowered full-season log loss by 0.00317 (95% day-block interval −0.00542 to −0.00088), while losing eight correct picks. In the partial season its log-loss interval included zero. It selected more matches at a probability of 0.65 or above, but the number and composition of selected games changed. Production still uses 180 days.

Reproduce with `python -m scripts.evaluate_football_opponent_half_life --output report.json`. The report contains matched day-block intervals, temporal splits, confidence coverage and upstream archive hashes. This is a historical replay with publication availability unverified, using the archives at `377c168`.
