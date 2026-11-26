# Football Elo with explicit draw probability

This archive replay compares the existing opponent-adjusted goal model with an Elo rating model that assigns an explicit weight to draws. The outcome distribution follows [Davidson's extension of Bradley–Terry](https://doi.org/10.1080/01621459.1970.10481082). The update is Elo-style, with actual draws worth half a point. The fixed home bonus is 60 points and the update rate is 30. The expanding draw rate starts with a 14-in-50 prior.

The two models use identical fixtures and weekly cutoffs at a seven-day simulated forecast lead. Both see matches strictly before their cutoff. Following Antigravity's chronology review, all games from the same archived date update ratings together after the day's predictions have been formed. Archived result publication and live fixture availability are unverified.

| Archive | Games | Correct, reference / Elo | Log loss, reference / Elo | Highest-confidence quarter, reference / Elo |
| --- | ---: | --- | --- | --- |
| 2025–26 | 3,018 | 1,537 / 1,512 | 1.00588 / 1.00514 | 528 / 544 of 755 |
| 2026–27 partial | 1,075 | 561 / 555 | 0.99289 / 0.98485 | 190 / 193 of 269 |

Elo lost correct picks across all games, and both paired accuracy intervals include zero. It selected a more accurate highest-confidence quarter in these samples and in both chronological halves of each sample. Each model ranks the archived fixtures within the entire evaluation period. Using different selected fixtures and a cutoff known only after the period makes this a ranking diagnostic. A pregame selection rule and separate forward evidence are needed before changing production.

Run `python -m scripts.evaluate_football_davidson_elo --output report.json` from the repository root. The report includes the paired intervals, per-league results, temporal splits, aligned coverage and archive hashes. This run used `bb32d5f`.
