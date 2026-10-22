# Research review and development priorities

Reviewed on **2026-10-22**. Repository existence, documented promises and successful live requests are distinguished below. No paid plan was purchased, no credentials were requested, and third-party MCP code was inspected rather than executed.

## Corrections to the API/MCP proposal

| Claim / option | Finding | Project decision |
|---|---|---|
| No Iddaa MCP exists | Incorrect. [borakilicoglu/iddaa-mcp](https://github.com/borakilicoglu/iddaa-mcp), inspected revision `121dc3a72bc76ccfc7ed523f16679d2ff5dc3ed9`, exposes stdio/HTTP tools and a sport-type filter. | Link the project; implement a separate small Python reader with explicit market semantics. Do not copy its progression/staking strategies. |
| An MCP always needs a dynamic external API | Incorrect. [MCP architecture](https://modelcontextprotocol.io/docs/learn/architecture) supports local servers; [SDK resources](https://py.sdk.modelcontextprotocol.io/get-started/first-steps/) can expose files or computed values. | This project's MCP reads local project data and makes no provider requests. |
| Iddaa/Nesine have no usable data access whatsoever | Too broad. The Iddaa website JSON backend returned basketball events, competitions and market configuration without authentication during this review. | Experimental Iddaa-only reader; do not call it a supported public developer contract, a Nesine API or a guaranteed service. |
| NosyAPI is a ready active alternative | Its [Iddaa program page](https://www.nosyapi.com/api/iddaa-oranlari-ve-programi-api) documents basketball and test credits **but explicitly says the service is disabled**. Its [results product](https://www.nosyapi.com/api/iddaa-oranlari-ve-programi-sonuclari-api) is separate and warns of incomplete coverage. | Do not ship a supposedly active connector, assume quota/storage rights or ask for a key to a disabled service. |
| xiddaa is a verified basketball source | The [provider site](https://xiddaa.com/) advertises a football-focused model, paid access and snapshot history. Basketball coverage was not verified. | No basketball integration based solely on that marketing page. |
| Sportmonks link solves basketball | The supplied [Sports Betting API link](https://www.sportmonks.com/football-api/solutions/sports-betting-api/) is specifically a football product. | Do not represent it as this project's NBA/EuroLeague source. |
| The Odds API | [Official v4 docs](https://the-odds-api.com/liveapi/guides/v4/) document odds/snapshot timestamps; historical endpoints require paid plans. | Candidate for authorized historical market evaluation, not proof of free historical Iddaa/Nesine coverage. |
| SportsGameOdds | A separate provider, not another name for The Odds API. Its [basketball product](https://sportsgameodds.com/sports/basketball-odds-api) documents NBA and other basketball leagues and a quota-limited free tier. | Candidate to test by league, market and bookmaker; no assumption that local Turkish bookmaker codes are included. |

A website's internal endpoint being reachable does not establish a stable schema, redistribution rights or service agreement. The reader is bounded, read-only, explicitly refreshed and fails when expected fields change. No bypass or browser scraping was required. Source URL and observed capture time are preserved. The checked-in latest snapshot is a dated observation, not a promise of current odds after checkout.

## What was inspected in other repositories

| Primary source | Useful idea | Review conclusion |
|---|---|---|
| [kyleskom/NBA-Machine-Learning-Sports-Betting](https://github.com/kyleskom/NBA-Machine-Learning-Sports-Betting) | Stats/odds pipeline, manual prices, calibrated model workflows, comparative models and display | Useful architecture; advertised results are not comparable without matching test games and knowledge cutoffs. No XGBoost/NN dependency was added just because another repo uses it. |
| [ugurakami/BasketbolBet](https://github.com/ugurakami/BasketbolBet) | Recent form, first-half ratio and calibrated classifiers | The reference is now accessible; earlier README statements that it was unavailable described an older workspace. Inspected `model_v4_2_optimal.py`: outer TimeSeriesSplit exists, but inner `CalibratedClassifierCV(cv=3)` is not an explicitly chronological calibration splitter. This is a temporal-audit concern, not proof of comparable performance or a reason to copy the model wholesale. |
| [swar/nba_api](https://github.com/swar/nba_api) | Official NBA endpoint client and advanced player/team data | Already used by the project; an SDK's availability does not guarantee endpoint availability from every environment. |
| [dblackrun/pbpstats](https://github.com/dblackrun/pbpstats) / [docs](https://pbpstats.readthedocs.io/en/latest/) | Possession data, lineups on the floor and shot-zone profiles | Strong candidate for lagged player/rotation value and lineup continuity. Same-game lineups cannot be treated as known pregame. |
| [sportsdataverse/hoopR](https://github.com/sportsdataverse/hoopR) | Schedule, box-score and play-by-play workflows | Useful source ecosystem; existing sportsdataverse files are already normalized in this repository. |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | Typed local tools and stdio transport | Optional SDK 2.3.0 integration added and tested with a real protocol client. |
| [scikit-learn calibration docs](https://scikit-learn.org/stable/modules/calibration.html) | Calibration is evaluated separately from hit rate | Continue chronological holdouts. Calibrated probabilities, confidence intervals and accuracy are different measurements. |

## Bugs and gaps addressed in this review

1. **Postgame participant leakage:** the default NBA absence feature inferred missing players from actual same-game participants. It is now disabled; research helpers and old evidence remain labeled. Official-report display is optional and does not change the model.
2. **Future-report lookup:** a future requested fixture could make the report downloader try future PDF filenames. The cutoff is now `min(now, fixture_time)` and a publication timestamp is retained.
3. **Wrong ledger result:** repeated team pairings on different dates could receive the same ESPN/BDL score. Date/time matching is now scoped, a unique local candidate is required, and a six-hour tolerance replaces the broad 36-hour match.
4. **Inflated live accuracy:** records without verifiable pregame capture times, late records and duplicate predictions are excluded or deduplicated. One fixture is counted once using the latest valid pregame prediction. Confidence-filtered accuracy is reported with coverage.
5. **Invalid price handling:** NaN/infinite/<=1 decimal prices, malformed odds pairs and unequal simulation-array lengths are rejected. Unsupported simulation methods cannot silently become Kelly mode.
6. **Stale evaluation artifacts:** new manifests fingerprint the dataset, feature semantics and parameter/metric files. Predictions prefer the verified evaluation and report its status. Legacy actual-participation metrics are not relabeled as current results.
7. **Unnecessary loading/network work:** disabled auxiliary feature tables are not loaded for every prediction; injury-PDF downloads require explicit `--sakatlik`.
8. **Operational access:** explicit bulletin refresh, freshness checks, supported-league checks, overtime/period checks, integer-line push handling, read-only MCP tools and offline CI were added.

## Measured model experiments

The fresh seven-model benchmark is [pregame_verified](kanit/pregame_verified/completed_seasons.csv). It selects hyperparameters only on earlier data and contains no actual-participation features. Partial 2026–27 metrics are stored separately by season and are excluded from the completed-season table and same-season model selection.

Four-factor candidates add lagged offensive/allowed effective field-goal percentage, turnover rate, offensive rebounding share, free-throw scoring rate, three-point attempt mix and overtime-adjusted pace. Profiles update only after the entire UTC day's feature rows are emitted. Tests mutate target/future boxes and verify that the target's features do not change.

The [ablation](kanit/feature_research/summary.csv) keeps games and fold parameters identical across variants. NBA logistic log loss changed approximately **0.61992 to 0.61962**, while accuracy did not improve. The score regression and European variants worsened. European rich-box coverage starts much later than match history, creating severe coverage/regime shifts. **No four-factor candidate was activated by default.** These are exploratory results without a prospective or statistical superiority claim.

A separate [confidence report](kanit/pregame_verified/confidence.csv) shows that higher observed hit rates on strong favorites come with lower coverage: NBA score-model accuracy was **65.80% across 6,605 games**, versus **79.69% across 1,684 selected games (25.50% coverage)** at a 70% predicted-winner threshold. Wilson intervals and all fixed thresholds are published. This is a subset diagnostic, not a new universal accuracy figure or a betting-profit result.

## Prioritized additions that could improve real pregame performance

| Priority | Addition | Why it may help | Evidence / acceptance requirement |
|---|---|---|---|
| 1 | Timestamped official injury and expected-lineup history | Replaces postgame absence proxies with information actually available before tipoff | Published/observed timestamps, fixture identity, status revisions; chronological ablation against injury-free baseline |
| 1 | Opening/current/closing odds snapshots | Supplies a strong market baseline and allows movement/closing-line comparison | Same settlement rules, bookmaker identity, MBS/promotion restrictions, timestamps before each prediction cutoff; never train an early forecast with a later closing quote |
| 2 | Player and rotation impact | Team averages miss star absences, minutes changes and transfers | Lagged minutes/value estimates from player/PBP data; no current-game participation leakage |
| 2 | Domestic league workload for European clubs | European-only history misses local games, rest and congestion | Reliable BSL/ACB/etc. schedules and cross-source team identity; joint workload features from past games only |
| 2 | Better calibration and predictive intervals | Useful probabilities need more than winner hit rate | Chronological calibration folds, reliability curves, Brier/log loss and interval coverage; compare to Elo and market |
| 3 | Travel, timezone and venue context | May explain fatigue and home/neutral effects | Verified arena coordinates, schedule-derived travel, cross-season stability; retain only if held-out metrics improve |
| 3 | Distribution/selection models for totals and handicaps | One normal residual distribution may miss tails, push rules and heteroscedasticity | Separate regulation/OT targets, integer/half/quarter-line settlement and out-of-sample proper scores |
| 3 | More frequent retraining and artifact caching | Could adapt to roster and pace shifts and reduce repeated work | Monthly walk-forward testing, training-cutoff/model fingerprints, benchmark against season-boundary refits |

The next genuine bottleneck is **point-in-time information and validation**, not another unverified high-accuracy GitHub model or merely increasing archive row counts.
