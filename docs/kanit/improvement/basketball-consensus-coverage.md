# Basketball confidence ranking at equal coverage

The reference selects games whose predicted winner has probability 0.65 or above. The candidate keeps the same winner picks, probabilities and number of slots per league and UTC day. It ranks games by the lowest probability any of score regression, logistic regression and Elo assigns to the reference winner. Ties use the original confidence and then the fixture ID. Earlier seasons train the learners and select the reference. All scores from the target UTC day are withheld during feature generation.

| Archive cohort | Available | Selected per rule | Replaced selections | Reference correct | Candidate correct |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023–24 | 1,055 | 634 | 22 | 476 | 475 |
| 2024–25 | 1,121 | 545 | 8 | 441 | 442 |
| 2025–26 | 1,181 | 617 | 10 | 463 | 466 |
| Completed seasons | 3,357 | 1,796 | 40 | 1,380 | 1,383 |
| 2026–27 partial archive | 369 | 172 | 7 | 127 | 128 |

Completed-season selected accuracy was 76.84% for the reference and 77.00% for the candidate, a difference of +0.17 percentage points. The 95% day-block interval for the difference was −0.32 to +0.66 points. The first period lost 0.10 points and the second gained 0.49 points. KBL had two fewer correct selections across the completed seasons. The evidence leaves the production selection rule unchanged.

This is an archive replay. Ranking assumes the complete same-day batch of available fixtures is known when it is formed. The archive cannot verify point-in-time calendar availability. Different selected sets also make this a comparison of selection policies, with no change to accuracy or probability losses for the full fixture set.

Run `python -m scripts.evaluate_basketball_consensus_coverage --output report.json` from the repository root. The report records input and script hashes, the selected reference learners, UTC-day intervals and temporal splits. This run used the archives at `c1b250a3769c4e94b9ff0d7a2c43f7538815d770`.
