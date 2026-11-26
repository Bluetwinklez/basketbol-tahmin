# Premier League priors for newly promoted clubs

This retrospective tests a forecast correction for clubs entering the Premier League from the Championship. A club needs the same archived identity in both divisions, at least 40 Championship appearances before 1 July and no Premier League appearances in the preceding season. The candidate turns off as the club reaches eight completed top-tier matches known at the monthly model fitting cutoff.

The common prior estimates attack and defence factors from the three earlier promotion cohorts' actual-to-expected goals against incumbent clubs, stabilised by 16 pseudo-goals. The club-specific alternative follows Antigravity's suggestion of carrying a team-level estimate across tiers. It adds one regularised slope for each club's prior Championship goal difference per game, shrunk by 16 appearances. The slope and the centering value are learned only from the earlier cohorts. Expected goals use the opponent-adjusted model and only results available before each monthly cutoff.

| Target archive | Matches affected | Reference correct | Common correct | Club-specific correct | Log loss, reference / common / club-specific |
| --- | ---: | ---: | ---: | ---: | --- |
| 2024–25 | 25 | 14 | 16 | 16 | 0.91615 / 0.80465 / 0.80131 |
| 2025–26 | 25 | 11 | 11 | 12 | 0.96164 / 1.02144 / 1.02474 |
| 2026–27 partial | 25 | 10 | 11 | 11 | 0.99257 / 1.00521 / 1.00521 |

The club-specific candidate gained four correct picks over 75 affected fixtures. Its day-block accuracy interval includes zero in every season. Log loss and Brier worsened in the last two archive periods. The latest fitted strength-transfer slope was effectively zero. The production model remains unchanged.

Run `python -m scripts.evaluate_football_promoted_prior --output report.json` from the repository root. The report contains the whole-league comparison, earlier/later UTC-day results, confidence coverage, selection counts, and input hashes. The run used the archive at `8cca5b5`. Historical publication times and applicability to other league systems remain unverified.
