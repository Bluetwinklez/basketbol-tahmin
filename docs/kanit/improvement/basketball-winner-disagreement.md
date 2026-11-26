# Basketball winner probabilities and predicted-margin disagreements

The reference is the shared chronological research model. The diagnostic candidate follows score regression only when its predicted margin and the reference's top winner point in opposite directions. Both variants use away as the tie break at exactly 50%. The prior-season policy allows the switch only after at least 20 previous disagreements and a gain in accuracy and log loss with no Brier regression on those matches. Each league makes that decision before the target season.

| Archive cohort | Games | Disagreements | Reference correct | Always switch | Prior-season rule |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024–25 | 1,121 | 32 | 772 | 774 | 772 |
| 2025–26 | 1,181 | 34 | 791 | 793 | 792 |
| 2026–27 partial | 369 | 26 | 236 | 238 | 236 |

Only Türkiye BSL qualified for the override in one target season. The preceding season supplied 24 disagreements. The override produced one extra correct prediction in the 2025–26 BSL archive. No league qualified in the 2026–27 partial replay.

A separate check of the checksum-verified, frozen basketball scorecard at the 26 November 2026 18:47 UTC basketball cutoff found 10 disagreements with a nonzero predicted margin across 387 settled games. The probability pick was right six times and the margin pick four. This descriptive live check compares saved predictions on a filtered subset. Production stays with the existing winner probability.

Run `python -m scripts.evaluate_basketball_winner_disagreement --output report.json` to reproduce the archive replay at `f45c5cd`. The report includes paired day-block uncertainty, temporal splits, confidence coverage and archive hashes. Historical publication availability remains unverified.
