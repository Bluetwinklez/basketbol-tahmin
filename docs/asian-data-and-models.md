# Asian league data and independent models

This extension adds separate senior men's archives for KBL, Japan B1/B2 (including the source's 2026 B.PREMIER/B.ONE reorganisation), and three PBA conferences. These are new cohorts, not extra rows silently mixed into NBA, NBL or European training.

The archives now contain **12,850 distinct finals**, including **3,607** older Japanese results added after the initial 9,243-game extension. The Japanese default still uses 2021–22 onward; [matched broader-history comparisons](kanit/history_expansion/README.md) retain the mixed results and explain why the challenger is not promoted.

## Sources and identity checks

- **KBL:** official public website API at `https://api.kbl.or.kr/`. Public website routing headers are required. Exact senior regular-season catalog/game keys, season windows, final flags and positive non-tied scores are checked. D-League, cups, playoffs and all-stars are excluded. Calendar responses were collected from 2017 through 2026; initial and current seasons are partial. Independent completeness is unknown.
- **Japan:** official `https://www.bleague.jp/schedule/`, using the website's actual `year`, `mon=all`, `tab` and `event` filters and advancing JSON pagination. B1 and B2 are stored separately. Historic regular-round labels and 2026 blank round labels require different parsing. All-star cards are excluded; playoffs/cups are outside the requested regular event. Public logo codes identify clubs; historical ownership continuity is unverified. The current-year parser was re-run from downloaded pages after the format change; reports identify this as cached reparsing rather than a second live confirmation.
- **PBA history:** independent RealGM public team schedules. The URL's conference name does **not** filter all rows: each row's explicit conference label is mandatory. Team-copy duplicates, score orientation and W/L agreement are checked. Missing year selectors are recorded as unknown coverage, not zero-game seasons.
- **Current Governors Cup:** independent `https://www.sportsmetric.ph/leagues/pba` publisher data, parsed as JSON/React data without executing page scripts. The observed campaign is season 50 (`2025-26`), not a July-based `2026-27` label. A season-specific Macau identity link is supported by eleven matching date/opponent/score pairs. Sixty-nine shared results are linked to RealGM; only one additional final is added. Three recent score pairs were spot-checked against the official PBA homepage; this does not independently verify all history.

PBA nominal sides are retained, but no verified home-court advantage is assumed. Historical day-only dates remain day-only; the entire target UTC day is withheld from features. Result collection timestamps do not establish original publication times. HTTP failures are reported; unavailable detailed endpoints are not bypassed.

## Player boxes

The current PBA publisher snapshot contains **1,018 validated player-match rows**. Checks include nonnegative integer counts, makes versus attempts, team point sums, scoring identities allowing unreported four-point makes, and conflicting player IDs. There are **674 rejection records**, which are reasons/rows rather than a count of distinct players. Some team boxes remain partial after quarantine.

The validated snapshot replaces its previous version so rejected old rows cannot survive a refresh. These are postgame facts with season-scoped provider IDs. **They are not inputs to the default prediction models**, and their existence establishes no improvement in player-impact estimation.

## Training and evaluation

`asia-separate-prior-policy-v1` fits fixed Ridge margin/total regressions and logistic regression, with Elo and an equal three-model ensemble as probability candidates. Each division/conference is independent. It requires two earlier seasons with at least 50 observations and at least 150 games before the calibration season. Insufficient folds fail explicitly; thresholds are not lowered to force a model.

The preceding adequate season's first UTC-day half calibrates the score probability scale; its second half selects the candidate by log loss. Coefficients are then refit on all preceding seasons. The target season's labels never select a model. Features use only earlier UTC days, including already observed earlier days of the target season. Score intervals use prior residuals and are not guaranteed conditional coverage.

Reports retain every variant, skipped folds, probabilities, actual scores, total/margin errors, score MAE, interval coverage and Wilson accuracy intervals. Selection additionally requires sufficient recent history, a non-stale last result, adjacent-season calibration and agreement between probability and score direction. Selected coverage is separate from full-cohort accuracy. This is historical walk-forward research, not a prospective betting record.

## Measured historical results

Full-cohort results from the fixed previous-season selection policy; the fixed score candidate is retained as a comparison, not chosen after seeing these test outcomes. "Past season" refers to the archive cohort, not a completeness certification.

| Archive | Evaluated past seasons | Correct / games | Prior-selected policy | Fixed score candidate | Points MAE per team |
|---|---|---:|---:|---:|---:|
| KBL | 2021-22–2025-26 | 864/1347 | 64.14% | 62.14% | 8.42 |
| JP_B1 | 2023-24–2025-26 | 1523/2219 | 68.63% | 68.81% | 8.46 |
| JP_B2 | 2023-24–2025-26 | 886/1260 | 70.32% | 71.19% | 8.65 |

KBL's prior-selected policy beats its fixed score candidate on these five seasons, but the policy is slightly worse on both Japanese archives. This does not establish a general benefit from adding more data or from model selection. The latest KBL past season alone is **167/270 (61.85%)**, with **13.59 points total-score MAE**.

Partial observed cohorts are separate: KBL 2026–27 **15/32 (46.88%)**, Japan B1 2026–27 **77/116 (66.38%)**, Japan B2 **72/108 (66.67%)**. PBA Governors Cup season 50 is **45/70 (64.29%)**, but its calibration season is several years old and all 70 predictions fail the adjacent-season selection gate. Its only other scored cohort has **0/2** correct, plainly insufficient for validation. Commissioners and Philippine Cup have **no eligible evaluation fold** because earlier training history is too sparse. Data is stored without claiming trainable/validated models for those cups.

The real KT–Dongbu bulletin integration check produced finite scores and exposed a probability/score-direction disagreement, correctly marking the prediction ineligible. [Integration evidence](kanit/asia_data/kbl_runtime_check.json) is not a live accuracy test. No result was used to rewrite the earlier frozen EuroLeague forecasts.

## Reproduce and refresh

```bash
# Initial historical collection; public provider availability and runtime vary.
python -m bbtahmin asya-topla --kaynaklar KBL Japan PBA
# Smaller refresh: current KBL calendar, Japanese season and PBA publisher.
python -m bbtahmin asya-topla --kaynaklar KBL Japan PBA --current-only
# Refit and evaluate the resulting stable archives; no paid keys needed.
python scripts/evaluate_asia.py
python -m pytest -q
# Hypothetical usage example; obtain an actual fixture from the bulletin first.
python -m bbtahmin tahmin "KT Sonicboom - Dongbu Promy" --lig KBL --tarih 2026-10-23T10:00:00Z --json
```

PBA predictions require an exact observed conference fixture to avoid inventing campaign boundaries. A skipped conference can have stored data without a trainable model. There is no validated automatic in-play model for these leagues. The existing frozen two-game EuroLeague record remains unchanged.

Collection evidence: [source reports](kanit/asia_data). Evaluation evidence: [summary](kanit/asia_models/summary.csv), [fold decisions and skipped reasons](kanit/asia_models/folds.json), [reproducibility manifest](kanit/asia_models/manifest.json). Verification: [213 passing tests](kanit/asia_tests.xml); 13 existing pandas FutureWarnings remain.
