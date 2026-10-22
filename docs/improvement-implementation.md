# Prediction reliability implementation

This release implements data-quality, reproducible research, runtime diagnostics and prospective verification. It does **not** establish a general improvement in winner accuracy. The default competition models remain unchanged because challengers have mixed results.

## Data added separately

- **561 Czech senior women's ZBL results**, 13 observed identities, seasons 2022–23 through partial 2026–27: 121 / 142 / 134 / 139 / 25. Every phase discovered in the official season selector was requested. Forfeits and future fixtures are excluded. Counts do not prove complete season coverage. Source table scores and home/away order are parsed and tested; independent cross-source verification, neutral venues and overtime remain unresolved.
- **359 EuroLeague Women results**, kept separate from men's competitions and the original ECW archive.
- **Two early ECW results** from a public historical page. This is explicitly **not** a complete early season.
- Explicit Czech senior-women mappings connect Žabiny Brno and KP Brno to their FIBA organisation identities. Other Czech teams retain a separate namespace; no fuzzy cross-gender or sponsor-name joins.
- Fresh official 2026–27 EuroLeague results use a runtime overlay. Existing benchmark archives stay unchanged; predictions flag that the runtime data differ from the evaluated dataset.

Sources and per-phase counts: [Czech collection](kanit/domestic/CZ_W_ZBL_collection.json), [ELW collection](kanit/competitions/ELW_collection.json). Raw page caches are not committed.

## Research results and rejection decisions

The completed 2025–26 ECW season contains the **same 214 target games** in every comparison:

| Candidate | Correct | Accuracy | Log loss | Brier |
|---|---:|---:|---:|---:|
| Existing score model | 150 | 70.09% | 0.604484 | 0.208212 |
| Direct logistic | 145 | 67.76% | 0.632319 | 0.215553 |
| Pooled women's-cup score features | 143 | 66.82% | 0.603103 | 0.206709 |
| Czech domestic form + score model | 152 | 71.03% | 0.612621 | 0.210117 |
| Czech domestic form + logistic | 147 | 68.69% | 0.655468 | 0.219786 |

Domestic form gains two winner picks but worsens both probability losses. Pooled cup features improve losses slightly but lose seven winner picks. Neither demonstrates broad superiority. A research policy selected using the preceding season also underperforms on ECW; it remains visible and **is not deployed**. Domestic features are separate lagged, shrunken summaries; domestic scores do not update European score states. The pooled-cup candidate is explicitly a rough exploratory ablation and does not solve cross-tier strength adjustment.

A further regularized club-strength candidate combines explicitly linked senior-women schedules with L2 team priors and time decay; its results are also published without automatic activation. This is not an explicit Bayesian league hierarchy.

These seasons have already been inspected. They are exploratory reused history, not a fresh holdout or proof from prospective predictions. Partial 2026–27 is separate. Eligibility flags are diagnostics, not learned or validated thresholds.

Evidence: [all variants](kanit/winner/summary.csv), [prior-only selections](kanit/winner/selections.json), [paired day-block comparisons](kanit/protocol/paired.json), [low-history strata](kanit/protocol/strata.csv), [equal-coverage curves](kanit/protocol/coverage_curves.csv).

## Four-match failure audit

[Review](kanit/governance/four_match_review.json) scores the original unmodified post-tipoff reconstructions. The group is 1/4 on winner accuracy. Each fixture has sparse-history issues, including the correct Helsinki–Žabiny pick. Filtering only the losers would be invalid. Missing data is a hypothesis, not a proven cause. These reconstructions never enter prospective accuracy.

## Data and information-time controls

`quality.py` reports per-team prior game counts, recency, exponentially decayed history and distinct opponents. It separates data adequacy from win probability, exposes score/winner disagreement and benchmark/runtime differences. Fewer than five observed games in 400 days or a last result older than 60 days trigger a diagnostic restriction. These thresholds are not validated recommendation rules.

When `--min-guven` is supplied, both the probability threshold and the diagnostic gate must pass. `threshold_passed`, `selection_eligible` and `secildi` remain separate. No output claims validated recommendations. Coverage reports retain all rows.

`context_import.py` accepts explicit senior gender identities, final scores, source URLs, event/capture/availability times and score verification. Rejected records go to quarantine. Conflicting observations, including conflicts across previous imports, require review. Missing historical publication time stays null; point-in-time queries conservatively use capture time. Imported data are not silently activated in the model.

## Uncertainty and monitoring

Prior-season empirical residual quantiles are evaluated alongside the existing normal intervals on identical fixtures. Coverage, interval width and interval score are reported. Empirical intervals remain research-only; neither method promises conditional coverage for cold-start teams. See [interval comparison](kanit/intervals/summary.csv).

Feature-distribution shifts, missingness and reliability bins are written to [governance evidence](kanit/governance/). Two-standard-deviation shifts are diagnostic alerts, not validated retraining triggers. Small samples never automatically promote or retrain models.

CBA live inputs retain timestamp freshness and regulation-duration checks. Optional previous-state validation rejects out-of-order timestamps, other fixtures and backward scores/clocks unless an explicit source correction is recorded. No automatic live feed, possession/lineup feed or newly validated within-quarter model is claimed.

## Prospective protocol

`prospective.py` freezes confirmed future fixtures before tipoff using exclusive file creation. It stores fixture/source identities, capture time, complete probabilities/scores/intervals, data checks, code fingerprint, Git revision and dataset hashes. A SHA-256 payload detects subsequent modification; publishing the record to Git provides external pregame evidence. The checksum alone is not an external timestamp.

Results are separate files. Only verified final scores with matching event/team/league identities count. A changed actual tipoff or major reschedule requires review. Pending/cancelled games do not become losses or disappear. Duplicate results fail rather than choosing arbitrarily.

Settlement reports:

- Winner correct/incorrect, Brier and log loss.
- Home/away signed and absolute score errors.
- Mean absolute error across the two team scores.
- Total and margin signed/absolute errors.
- Percentage errors using actual positive team/total scores as denominators.
- Whether actual total/margin fell in the recorded 80% intervals.

Two matches are a small prospective demonstration, not a new general accuracy percentage. Results must never change the frozen predictions or be used to retune and rescore the same pair.

## Reproduce

```bash
python -m bbtahmin yerel-topla
python -m bbtahmin kadin-gecmis-topla
python -m bbtahmin veri-denetle
python scripts/evaluate_winners.py
python scripts/evaluate_protocol.py
python scripts/evaluate_intervals.py
python scripts/review_failures.py
python -m pytest -q
```

Import a separately verified JSONL archive:

```bash
python -m bbtahmin baglam-aktar --source observations.jsonl --identities identities.json
```

Each identity has `gender: Women|Men` and `category: senior`. Each observation requires `event_id`, `competition`, `season`, `gender`, `home`, `away`, positive integer `home_score`/`away_score`, timezone-aware `event_time`/`captured_at`, nullable `available_at`, HTTPS `source_url`, `status: final`, `date_precision: timestamp|day`, and `score_verified: true`. Review the source and identity before asserting verification. Importing is not independent verification.

Freeze and later check official EuroLeague fixtures:

```bash
# Refuses to overwrite an existing forecast file; uses the earliest two confirmed future fixtures.
python scripts/forecast_cycle.py --freeze --record docs/kanit/prospective/2026-10-23.json
# Read-only official refresh; writes a new result-check file, leaves predictions intact.
python scripts/forecast_cycle.py --record docs/kanit/prospective/2026-10-23.json
```

Generic CLI: `prospektif --fixtures FILE --output FILE --limit 2`, and `sonuc-kontrol --record FILE --results FILE --output FILE`.

## Work that cannot honestly be marked completed

| Workstream | Current state / remaining condition |
|---|---|
| Czech domestic history | Implemented separate archive and ablation; incomplete identity mappings and unverified completeness |
| Spain, Bulgaria, Slovenia, Finland, Austria and Estonia full league history | Not collected as complete archives; need reliable season adapters and source verification |
| WABA | Official senior schedule page inspected; embedded third-party widget requires a tested adapter and age/category validation; no fabricated results added |
| Hierarchical cross-league strengths | Not implemented; pooled ablation is not a substitute |
| Point-in-time expected rosters and injuries | No adequate historical archive; actual participants remain excluded from pregame features |
| Player transfer/rotation impact | Requires timestamped roster/minute data and independent ablation |
| True opening/closing odds | Local snapshots exist; no comprehensive historical provider contract or subscription purchased |
| Venue/travel and possession-level live modeling | Reliable historical source and evaluation still required |
| New untouched historical test | Cannot recreate an untouched past after inspecting its outcomes; use future frozen predictions |
| General success increase | Not established; retain default rather than ship a worse challenger |
| Two future game outcomes | Necessarily pending until official finals are available; scheduled follow-up handles this |

No API keys, paid subscription, inaccessible source, or future match outcome is invented. Next promotion requires same-fixture chronological comparisons, stable subgroup performance, an explicitly frozen candidate and independent prospective evidence. The two-game demonstration alone is insufficient.
