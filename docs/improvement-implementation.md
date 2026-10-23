# Prediction reliability implementation

The data/validation implementation is delivered and tested. A higher general winner-success rate is **not established**. New candidates remain research-only because same-fixture evaluation does not support replacing the baseline. Future match results, missing historical publication records and provider access cannot be manufactured by completing code.

## Separately stored data

| Archive | Results | Scope and source checks |
|---|---:|---|
| Czech women ZBL | 561 | Official discovered season phases; exact Žabiny/KP Brno links; forfeits excluded |
| Bulgarian women A group | 249 | Official senior category only; friendlies excluded; exact Montana link |
| Slovenian women first league | 331 | Official FEMALE/ABSOLUTE/FIRST season IDs; finished games only; exact Celje link |
| Finnish women Korisliiga | 310 | Official FEMALE/SENIOR identity; dated confirmed scores; undated playoff series totals excluded |
| Girona senior women | 123 | FEB widget final and calendar scores/side IDs must agree; actual tipoff and quarter sums checked |
| Senior WABA | 261 | Official league 31913, discovered season selector and advertised pagination; Celje/Montana links |
| Pärnu men | 43 | Official club calendar; named Estonian/Latvian domestic competitions only; European duplicates excluded |
| EuroLeague Women | 359 | Separate women's cup archive; explicit organisation namespace |
| Early EuroCup Women | 2 | Limited historical source; not a complete season |

The domestic/regional total is **1,878**, including 561 from the previous release. This follow-up adds **1,317 results**. These counts are stored observations, not proof of full season/league coverage or independent cross-source verification. Source details, season counts, exclusions and file hashes are in [collection reports](kanit/domestic/).

Finnish 2022–23 and 2023–24 responses lack status fields: all 286 returned rows are excluded, not silently called confirmed finals. Girona game 2344939 has a stale non-final widget despite a calendar result; it is rejected and listed in the report. Girona is a regular-calendar club cohort, not all Spanish teams or playoff coverage. Pärnu is a club cohort, not the full Estonian/Latvian league.

WABA source times do not certify a timezone. Its original calendar date remains `tarih_utc` with `date_precision: day`; `model_time_utc` is one day later. Both domestic features and the hierarchy use this conservative modeling time and withhold the entire UTC day. The embargo avoids pretending that an uncertain local tipoff is an exact UTC timestamp. WABA does not assign a domestic country group to its participating clubs.

Historical publication times, some neutral venues, overtime details and complete coverage remain unknown. Default benchmarks are not silently expanded. The official EuroLeague runtime overlay is separately fingerprinted.

## Measured results and deployment decision

The completed 2025–26 ECW comparison uses the **same 214 games** for every candidate:

| Candidate | Correct | Accuracy | Log loss | Brier |
|---|---:|---:|---:|---:|
| Existing score model | 150 | 70.09% | 0.604484 | 0.208212 |
| Expanded domestic form + score | 150 | 70.09% | 0.607545 | 0.209006 |
| Expanded domestic form + logistic | 147 | 68.69% | 0.644414 | 0.217811 |
| Linked hierarchical attack/defence | 143 | 66.82% | 0.626473 | 0.217827 |
| Pooled women's-cup score features | 143 | 66.82% | 0.603103 | 0.206709 |
| Direct logistic | 145 | 67.76% | 0.632319 | 0.215553 |
| Czech club-strength ablation | 137 | 64.02% | 0.645803 | 0.226205 |

**Defaults remain unchanged.** Expanded domestic form does not gain winner picks. The hierarchy is worse on these outcomes. Slightly better losses in a pooled candidate do not offset its seven fewer correct picks. The earlier Czech-only 152/214 result is preserved in the [previous release](https://github.com/Bluetwinklez/basketbol-tahmin/blob/ba29b1cf503040cecfdc8f8a65bfb4115c8e51f5/docs/kanit/winner/summary.csv); it must not be presented as the result of today's expanded data.

On partial 2026–27, domestic logistic gets **42/51 (82.35%)**, compared with baseline **41/51 (80.39%)**, with lower log loss (0.409184 vs 0.429685). This small already-inspected sample is not a completed season, independent holdout or proof of a stable improvement. The prior-season selection policy gets only 37/51; failed policies remain reported.

For expanded domestic score on the completed season, the paired day-block 95% interval for the accuracy difference is approximately **−1.84 to +2.19 percentage points**. There is no demonstrated accuracy gain. Confidence filtering reports its coverage and never becomes the all-game success rate.

Evidence: [all variants](kanit/winner/summary.csv), [prior-only selections](kanit/winner/selections.json), [paired comparisons](kanit/protocol/paired.json), [strata](kanit/protocol/strata.csv), [equal-coverage curves](kanit/protocol/coverage_curves.csv).

## Model and evaluation implementation

`hierarchical.py` implements fixed Gaussian-prior MAP attack and defence effects: separate competition scoring/home levels, country groups and shrunk club deviations. It is a regularized hierarchy, not posterior sampling. All fits stop before the query's UTC day; daily rolling validation/test predictions can update with already completed earlier days. Country membership is used only after an earlier domestic observation exists. Men's results never enter this women-only model. Residual intervals do not include full parameter uncertainty or guarantee cold-start coverage.

`winner_model.py` separates the preceding season by UTC-day halves: the first calibrates score residual scales; the second selects candidates. The target season never selects its own model. Future/test outcomes cannot determine calibration. Challenger rules require extra correct picks, lower log loss and no worse Brier in the earlier selection window. Historical seasons have already been inspected, so every result is exploratory reuse.

A discovered domestic-form bug used concatenated archive order for the last ten games. It now sorts by effective event time first; reversing input archive order leaves form unchanged. Evaluation hashes input datasets and source code before/after the run and refuses changing inputs. The paired report refuses stale winner manifests.

`--hierarchical` exposes the rejected ECW candidate explicitly for research; it cannot combine with monthly adaptive form. Ordinary predictions continue to use the established model. No four-match-specific parameters were fitted.

## Information-time player context and actual observations

`player_context.py` archives an actual official NBA injury PDF with publication time, actual capture time and PDF hash. Reports match exact away/home codes **and the fixture's US Eastern calendar date**. Both publication and capture must precede the cutoff; stale or missing reports mean unknown availability. A missing player/report is never interpreted as available or injured.

Lagged rotation uses only prior UTC days, the most recent ten observed games within 60 days, and recency-weighted minutes. It does not use target-game participants or force an incomplete rotation to total 240 minutes. Continuity and shrunk historical plus/minus are descriptive; they are not validated causal player-impact adjustments. Future information cutoffs are refused.

The real collection smoke run captured **85 injury-report rows**, a public ESPN scoreboard with **two listed events / zero in-play events**, and **176 Iddaa basketball events with zero schema rejections**. That verifies collection, not live-prediction accuracy. An earlier 63-row report remains immutable. Repeated observations are snapshots, not extra unique injuries.

`live_feed.py` supports strict NBA/ESPN score-period-clock parsing. The NBA CDN was unavailable with HTTP 403; the independently accessible ESPN provider is the default, with unverified source freshness when no update timestamp exists. This is observation collection, not a trained NBA in-play model. Manual CBA projections remain a separate experimental feature.

`.github/workflows/observations.yml` schedules captures at **20:15 and 23:15 UTC**, also allowing manual dispatch. Source failures remain in run reports; total provider failure fails the job. Only observation files are committed; models and frozen forecasts are not rewritten. Runtime provider access and repository write permissions are not guaranteed by an offline test. `bulten --gecmis` reads both manual and scheduled quote archives with cutoff/deduplication/conflict checks. First/last observed quotes are not certified opening/closing prices.

## Venue and workload context

`travel.py` computes great-circle distance from the last observed venue to the scheduled venue, elapsed tipoff hours and timezone offset differences. Unknown venues remain null. These are schedule proxies, not actual flights, intermediate stops or full recovery time, and do not alter predictions.

Five arena identities were matched against official schedule names/addresses and one-off OpenStreetMap observations. Registry attribution: **© OpenStreetMap contributors, ODbL 1.0**; source links are retained. No generic runtime geocoder was installed. The included official schedule cache could not be freshly refreshed after HTTP 403, so `source_freshness_verified` stays false. Only necessary schedule facts are retained. Examples are [here](kanit/context/venue_examples.json), including a documented hypothetical player-context smoke example.

## Existing safeguards retained

Data adequacy is separate from win probability. Fewer than five observed games in 400 days, results older than 60 days and score/winner disagreement can block diagnostic selection. These thresholds are not validated success rules. `--min-guven` requires both probability and diagnostic gates, while retaining all rows.

Explicit senior/gender identity imports validate event/capture/publication times and quarantine invalid rows. Cross-batch conflicts require review. Empirical intervals and feature shifts remain research diagnostics. CBA transitions reject stale/wrong-fixture/backward states unless an explicit source correction is recorded.

The [four-match review](kanit/governance/four_match_review.json) remains **1/4** for the original post-tipoff reconstructions. All four have sparse-history issues, including the correct one. They are not prospective forecasts, and their original predictions are not rewritten after results.

## Prospective verification

The two October 23 forecasts in [the frozen record](kanit/prospective/2026-10-23.json) are unchanged. Payload SHA-256: `d786691850bb74207e9ecac38ea6c06c4ce38dde7d874d9ba5a58df0238352a0`. Source/model changes do not retroactively regenerate them. Publishing to Git provides external pregame evidence; a checksum alone is not an external timestamp.

New freezes conservatively fingerprint side datasets and observation archives as well as the core data and source code. Exclusive file creation prevents overwrites. Final-result checks require matching event, team, league and tipoff identities, and write separate records with:

- Winner correctness, Brier and log loss.
- Team score signed/absolute errors and score MAE.
- Total and margin signed/absolute errors.
- Percentage errors using actual positive scores as denominators.
- Recorded 80% interval coverage.

The established scheduled follow-up checks official finals; outcomes remain pending before the games finish. Neither a two-game result nor choosing only successful examples establishes general accuracy.

## Reproduce

```bash
python -m pip install -e '.[mcp]'
python -m bbtahmin bolgesel-topla
python -m bbtahmin slovenya-topla
python -m bbtahmin finlandiya-topla
python -m bbtahmin girona-topla
python -m bbtahmin waba-topla
python -m bbtahmin veri-denetle
python scripts/evaluate_winners.py
python scripts/evaluate_protocol.py
python scripts/collect_observations.py
python -m pytest -q
# Later, when official finals exist; never use --freeze to overwrite the record:
python scripts/forecast_cycle.py --record docs/kanit/prospective/2026-10-23.json
```

The latest full local suite has **205 passing tests**, including the optional MCP protocol client. Tests cover source/gender/final-state identity, series exclusion, date embargoes, future mutation isolation, archive order, injury capture/fixture date and venue unknowns. See [test evidence](kanit/remaining_tests.xml). Runtime collection and CLI smoke checks are separate from offline tests.

## Research/source conditions still unresolved

| Condition | Honest state |
|---|---|
| Complete Austria/Estonia/Spain/Finland history | Club cohorts or selected validated seasons exist; not complete league archives. Austrian federation routes tested in this environment returned 404. Existing Vienna/ABA workload remains diagnostic only. |
| Historical point-in-time rosters/transfers | New actual snapshots and lagged rotations implemented; missing historic publication records cannot be reconstructed from postgame participants. |
| Learned injury, transfer, travel or possession-level effects | Context/collection implemented where source facts exist; independent sufficiently covered training/evaluation still needed before activation. |
| True bookmaker opening/closing prices | Actual local quote capture implemented; no paid provider contract or invented retrospective timestamps. |
| New untouched historical holdout | Already inspected past cannot become untouched; future frozen forecasts are required. |
| General accuracy increase | Not established; worse/mixed challengers remain inactive. |
| Future two-game final report | Requires actual official final results; scheduled follow-up already exists. |

These are data, evidence and future-event conditions, not undisclosed completed features. No paid subscription, API credential, inaccessible result or successful forecast is invented.
