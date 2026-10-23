# Basketball Pregame Research

A Python research package for pregame basketball probabilities, score margins and totals. It combines a reproducible historical archive, chronological model evaluation, an experimental Iddaa bulletin reader and a read-only local MCP server.

**The core archive contains 54,808 games; the separate Asian extension adds 9,243 results. More data has not established a general increase in prediction accuracy.** Results below distinguish full coverage from confidence-filtered subsets, and historical tests from live performance.

## What works

For daily use, run **`python -m bbtahmin gunluk --guncelle`** after installation. It refreshes supported schedules, preserves the earliest pregame forecasts, and writes a separate final-result/error report to `rapor/daily/latest.md`. Source failures and rejected forecasts remain visible. See [daily workflow, historical backfill and measurement limits](docs/daily-workflow.md).

| Capability | Status |
|---|---|
| EuroLeague, EuroCup, NBA and Australian NBL history | Available; 54,808 stored games |
| Chinese CBA | Separate 2,386-game archive, 20 teams; experimental CBA-only score model |
| EuroCup Women (ECW), FIBA Europe Cup men (FEC), VTB men | Separate experimental archives: 674 / 651 / 860 games; independent pregame models |
| KBL, Japan B1/B2, PBA conferences | 9,243 separate results; KBL/Japan and Governors Cup experimental models; other PBA cups have insufficient training folds |
| CBA in-play state | Experimental manual score/period/remaining-clock projection; regulation only, no automatic live scoreboard |
| Home-win probability, score, margin and total; 80% score intervals | Available; uncertainty estimates need continued validation |
| Home baseline, Elo, MOV Elo, logistic regression, gradient boosting, score regression, ensemble | Chronological evaluation; parameters selected using earlier seasons |
| Experimental Iddaa basketball bulletin | Website JSON backend tested; no API key; upstream may change |
| Two-way, overtime-inclusive moneyline and full-game totals | Explicit market checks; integer totals include push probability |
| Read-only MCP tools for local data, bulletin and predictions | Optional Python SDK extra; stdio tested |
| Local odds history and movement | Pregame snapshots only, historical knowledge cutoffs, duplicate/conflict checks |
| Adaptive form experiment | Optional earlier-season-gated monthly refits for ECW/FEC/VTB; default model remains fixed |
| Auxiliary domestic/ABA workload | 39 official-club observations; partial coverage, diagnostic only, explicit missingness |
| Confidence threshold and coverage report | Available; rejected predictions remain visible |
| NBA injury reports and lagged rotation | Timestamped report archive, exact fixture-date joins, prior-game minute estimates; not a validated player-impact model |
| Additional domestic/regional history | 1,878 separately stored results; explicit senior/gender links and source reports |
| Hierarchical attack/defence | Optional ECW research model; rejected as a default after mixed/worse evaluation |
| NBA/ESPN scoreboard observations | Actual observations archived separately; no validated NBA live predictor |
| Venue/travel context | Five verified-coordinate venues and cached schedule proxies; no actual itinerary inference |
| Retrospective player-absence feature | **Disabled by default:** actual participants are postgame knowledge |
| Four-factor/shooting profiles | Implemented and tested as an experiment; **not enabled by default** |
| Turkish BSL, other unsupported leagues, non-CBA in-play prediction | No trained model; bulletin presence does not imply model support |
| Betting execution, guaranteed returns | Not provided |

## Asian data extension

Added **9,243 distinct final results**: KBL **2,549**, Japan B1 **3,657**, Japan B2 **2,149**, PBA Governors Cup **322**, Commissioners Cup **291**, Philippine Cup **275**. These archives are independent of the existing 54,808-game core; player/fixture rows are not counted as extra completed games. There are also **1,018 validated PBA player-match observations**, currently excluded from default model inputs.

The extension fits fixed league-specific score/logistic/Elo/ensemble candidates using earlier-season training and calibration. It never silently borrows NBA/NBL models for these leagues. PBA conferences stay separate, the current Governors Cup campaign is explicitly matched rather than inferred from July, and Japanese 2026 league-format changes are recorded. Missing coverage, rejected player rows and skipped model folds are visible. See [Asian sources, training, limitations and refresh commands](docs/asian-data-and-models.md).

Full-cohort historical winner accuracy for the prior-selected policy is **64.14% (864/1,347)** on the last five KBL archive seasons, **68.63% (1,523/2,219)** across three Japanese B1 seasons, and **70.32% (886/1,260)** across three B2 seasons. Fixed score candidates score 62.14%, 68.81% and 71.19% respectively: model selection is not uniformly better. Partial current KBL is only **15/32 (46.88%)**. Governors Cup is 45/70 in its partial campaign, with an old calibration regime and no eligible selections; the other two cups lack a qualifying training fold. These are retrospective observations, not promised live success rates. [All variants, errors and partial cohorts](docs/kanit/asia_models/summary.csv).

## Reliability development and prospective verification

The reliability releases add **1,878 separately stored domestic/regional results**: Czech women 561, Bulgarian women 249, Slovenian women 331, Finnish women 310, Girona women 123, WABA women 261 and Pärnu men 43. There are also **359 EuroLeague Women results** and **two early ECW results**. These are separate archives/cohorts, not a claim of complete league coverage. This follow-up adds 1,317 results beyond the preceding release. A fresh official EuroLeague runtime overlay preserves the frozen benchmark dataset. See [implementation, measured failures and remaining source gaps](docs/improvement-implementation.md).

On the same **214 ECW 2025–26 games**, the baseline and expanded domestic-form candidate both get **150 correct (70.09%)**; their log losses are **0.604484 and 0.607545**. The new hierarchical attack/defence candidate gets **143/214 (66.82%)**, log loss **0.626473**. Neither replaces the default. The earlier Czech-only 152/214 result belongs to the [preceding release](https://github.com/Bluetwinklez/basketbol-tahmin/blob/ba29b1cf503040cecfdc8f8a65bfb4115c8e51f5/docs/kanit/winner/summary.csv), not the expanded-input experiment. All variants, failed selection policies and day-block uncertainty intervals remain visible. **No general accuracy increase is established.**

Predictions now expose data adequacy independently of estimated win probability. Sparse/stale history and score/winner disagreements can block confidence-filtered selection. Diagnostic thresholds are not validated success guarantees. Immutable future-fixture records and separate final-result checks report both point and percentage errors.

```bash
python -m bbtahmin veri-denetle
python scripts/evaluate_winners.py
python scripts/evaluate_protocol.py
python scripts/evaluate_intervals.py
```

## Additional data and context commands

```bash
python -m bbtahmin bolgesel-topla
python -m bbtahmin slovenya-topla
python -m bbtahmin finlandiya-topla
python -m bbtahmin girona-topla
python -m bbtahmin waba-topla
python -m bbtahmin sakatlik-arsivle --hours 2
python -m bbtahmin canli-veri-topla --provider espn
python scripts/collect_observations.py
# Hypothetical fixture for inspecting lagged context, not a verified schedule:
python -m bbtahmin oyuncu-baglam --ev BOS --dep PHI --tarih 2026-10-24T00:00:00Z
```

The collection workflow archives actual injury reports, ESPN observations and experimental Iddaa quotes at **20:15 and 23:15 UTC** and supports manual dispatch. Partial failures remain visible; total failure fails the job. Scheduling is not a guarantee of provider availability. Locally observed odds are readable with `bulten --gecmis EVENT_ID`; they are not verified opening/closing prices. No betting orders or paid API subscriptions are created.

`--hierarchical` is an **ECW-only research option**, incompatible with `--adaptive-form`; it is not the default. `seyahat-baglam --event-id EVENT_ID --asof UTC_TIMESTAMP` reads a local venue snapshot and exposes unknowns. The included schedule cache could not be freshly confirmed after an HTTP 403; its freshness remains explicitly unverified. Straight-line venue distances are not actual team travel. See [context evidence](docs/kanit/context/venue_examples.json).

## Frozen two-game prospective demonstration

Predictions were generated by this project's existing score model with fresh official EuroLeague results, recorded at **2026-10-22 21:30:47 UTC**, before both scheduled tipoffs. The earliest two confirmed future EuroLeague fixtures were selected; neither was chosen using its outcome.

| Fixture | Tipoff, Europe/Istanbul | Rounded score forecast | Home-win probability |
|---|---|---|---:|
| Žalgiris – ASVEL | 23 October 2026, 20:00 | 91–82 | 76.36% |
| Olympiacos – Fenerbahçe | 23 October 2026, 21:15 | 91–82 | 78.25% |

These are model probabilities, **not observed success rates**. [Frozen inputs, full-precision scores, intervals and hashes](docs/kanit/prospective/2026-10-23.json) remain unchanged. New result-check files report final scores, winner correctness and point/percentage errors. The fresh runtime overlay differs from the historical benchmark dataset and is explicitly flagged. Two games cannot validate general accuracy.

## Install

Python **3.12+**. The legacy Basketball Reference/EuroLeague collector also requires Node.js **18+** for `scripts/fetch.mjs`.

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
```

The checked-in Parquet files can be used immediately. `requirements-lock.txt` records an older Windows environment and contains a machine-specific editable-install path; `requirements.txt` is the portable direct-dependency specification.

## Predict and record

```bash
python -m bbtahmin tahmin "Celtics - Lakers" --lig NBA --tarih 2026-10-25T20:00 --json
python -m bbtahmin tahmin "Fenerbahçe - Monaco" --lig E --tarih 2026-10-25T20:00 --min-guven 0.70
python -m bbtahmin tahmin "Celtics - Lakers @1.90/1.95" --lig NBA --tarih 2026-10-25T20:00 --kaydet
python -m bbtahmin defter
```

These named matchups are **hypothetical usage examples**, not confirmed fixtures. Times without an offset mean Europe/Istanbul. An actual fixture ID from the bulletin is preferable when comparing odds.

`--min-guven 0.70` marks a matchup as selected only when the model gives either team at least 70% and the diagnostic history/consistency gate passes. It does not delete lower-confidence predictions or turn an estimated probability into observed accuracy. The ledger refuses post-tipoff records, excludes unverifiable/late records from performance summaries and reports selected coverage separately. Ambiguous result matches remain unresolved.

Optional `--sakatlik` reads the official NBA injury PDF, capped at the earlier of now and the requested fixture time. It does not modify the default model. No report is downloaded by default.

## Iddaa bulletin and odds comparison

```bash
# Three read-only GET requests; writes an observed-time snapshot.
python -m bbtahmin bulten --guncelle --limit 10
# Read the saved snapshot without a network request.
python -m bbtahmin bulten --lig NBA --limit 10
# Replace EVENT_ID with an ID actually returned above.
python -m bbtahmin bulten --tahmin EVENT_ID
```

Inspect locally recorded odds changes without downloading new data:

```bash
python -m bbtahmin bulten --gecmis EVENT_ID
python -m bbtahmin bulten --gecmis EVENT_ID --asof 2026-10-22T10:00:00Z
```

History uses only snapshots captured before tipoff and no later than the requested cutoff. Duplicate captures count once; conflicting prices or changed fixture identities fail explicitly. The first and last **locally observed** quotes are not verified bookmaker opening/closing prices. Refreshes build a local archive under `data/bulten/`; archive files are ignored by Git and are not a historical data download. Movement is a diagnostic and remains outside the prediction model.

This is an **experimental adapter for Iddaa's website backend**, not a contracted developer API and not a Nesine API. It does not log in, purchase a plan or submit a bet. Snapshots older than 15 minutes cannot be used for an odds comparison; started fixtures are refused by the pregame model.

Market configuration is checked explicitly. Regulation/first-half/three-way markets are not treated as two-way overtime moneylines. Unsupported competitions, including women's competitions without a matching model, cannot silently use the men's model. Source minimum-combination counts and alternative price fields are retained; expected-return arithmetic is not proof that a standalone selection is executable or profitable. Quarter-point Asian totals are excluded from the simple settlement calculation.

The statement that no Iddaa MCP exists is incorrect: [`borakilicoglu/iddaa-mcp`](https://github.com/borakilicoglu/iddaa-mcp) exists. Its source helped identify the website endpoint; it is not bundled or executed here. MCP also does **not** require a dynamic external API: the local server below reads project files. See [the source-backed API/MCP review](docs/research-and-roadmap.md).

## Current evaluation

The new seven-model run is under [`docs/kanit/pregame_verified`](docs/kanit/pregame_verified). It excludes actual-participant absence labels. Each test season uses only preceding seasons for fitting/tuning; same-UTC-day outcomes are withheld from pregame features. Models refit at season boundaries, not monthly.

The following are **fixed-model results on the last five completed seasons, 2021–22 through 2025–26**. The current incomplete season is excluded. These are not live results, a comparison with identical previous injury-based metrics, or an out-of-sample evaluation of choosing the winning model after seeing this table.

| League | Model | Games | Winner accuracy | Log loss |
|---|---|---:|---:|---:|
| NBA | Score regression | 6,605 | 65.80% | 0.61977 |
| EuroLeague | Score regression | 1,690 | 64.62% | 0.61594 |
| EuroCup | Score regression | 970 | 65.88% | 0.60567 |
| NBL | Ensemble | 824 | 61.04% | 0.65857 |

Lower log loss is better. The NBL score baseline on the same 824 games was 60.19% / 0.66102; the ensemble comparison is encouraging but does not establish a prospective improvement. Predictions select models only from evaluation seasons earlier than the requested season.

### Higher hit rate requires reporting what was excluded

For the NBA score model on those **same 6,605 games**:

| Minimum predicted winner probability | Selected games | Coverage | Observed accuracy | Wilson 95% interval |
|---|---:|---:|---:|---:|
| 50% — all games | 6,605 | 100.00% | 65.80% | 64.65–66.93% |
| 70% | 1,684 | 25.50% | 79.69% | 77.70–81.54% |
| 75% | 988 | 14.96% | 82.59% | 80.10–84.83% |

The 79.69% number describes a selected quarter of the games, **not overall accuracy**, future certainty or profitability. Thresholds are descriptive diagnostics, not a claim that a threshold optimized on this report will generalize. Full tables: [confidence.csv](docs/kanit/pregame_verified/confidence.csv).

Artifact manifests record feature semantics, data fingerprints and parameter/metric checksums. Prediction output includes artifact status for the actual input dataset. Default prediction fails with a rebuild instruction if the verified benchmark is missing or invalid; it cannot silently switch to legacy parameters or use an unsigned aggregate to select a model. Old reports in `docs/sonuclar.md` and top-level `docs/kanit` are retained as historical snapshots; their absence-enhanced results must not be presented as current, achievable pregame performance.

An additional chronological Platt-calibration experiment uses strictly earlier seasons' out-of-sample score predictions. EuroLeague accuracy changed from **64.49% to 65.42%** on 1,391 matched games, but NBA accuracy did not improve and NBL deteriorated. These 2022–23 through 2025–26 comparisons exclude the 2021–22 warmup season from both variants and are **not directly comparable to the five-season table above**. The candidate remains disabled pending untouched future evaluation. [Fold results and method](docs/kanit/calibration_research/).

## Reproduce or extend the data

```bash
python -m bbtahmin genislet
python -m bbtahmin genislet --ligler NBA --baslangic 1993 --bitis 2026
python -m bbtahmin genislet --ligler E U --yalniz-skor
python scripts/audit_dataset.py
python -m bbtahmin backtest --ilk-test 2021 --cikti docs/kanit/pregame_verified
python scripts/confidence_report.py
PYTHONPATH=src python scripts/evaluate_features.py
python scripts/evaluate_calibration.py
```

`--ilk-test` limits evaluated test seasons; it does not discard earlier training history. For standalone scripts on Windows, use `$env:PYTHONPATH='src'` instead of the POSIX prefix when needed.

| Archive | Coverage / contents |
|---|---|
| Games | NBA 1993–94 onward; EuroLeague 2000–01; EuroCup 2002–03; NBL 2015–16 |
| NBA player statistics | 1,071,430 provider player-box rows; includes recorded zero-minute/DNP observations |
| NBA team statistics | 82,912 detailed team-box rows |
| European shots | 178,177 structured shot observations |
| European play-by-play | 625,187 structured events |

Available records are not a claim of complete coverage for every season or league. Data collectors preserve existing results, quarantine conflicting scores/shifted-date duplicates, normalize athlete IDs and retain source provenance. Four zero-score/administrative records remain in the factual archive but are excluded from ordinary-game modeling. Rich shot/player data is not automatically a same-game pregame feature.

Sources: official EuroLeague API, Basketball Reference, ESPN/sportsdataverse, nba_api, nblR and verified numeric fields from euroleague-open-data. See [data expansion](docs/data-expansion.md), [source notes](data/KAYNAKLAR.md) and [dataset audit](docs/kanit/dataset_audit.json). The SBR collector remains permission-gated; no closing-odds profitability result is claimed.

## Experimental CBA and live-state projections

CBA has a separate **2,386-game** archive and a CBA-only model. The completed 2025–26 pregame test achieved **329/453 correct (72.63%)**; the current 2026–27 sample is only **14/25 (56.00%)** and is reported separately. These figures do not establish live accuracy. An additional remaining-score model uses real historical quarter states and explicit manual score, period and remaining-clock inputs. It is experimental, regulation-only and has no automatic scoreboard feed. Old screenshot inputs require `--replay`.

```bash
python -m bbtahmin tahmin "Jilin - Xinjiang" --lig CBA --json
python -m bbtahmin canli --ev Jilin --dep Xinjiang --skor 16 15 --periyot 1 --kalan 01:28 --tarih 2026-10-22T14:52:00+03:00 --replay
```

See [CBA methods, sources, evaluation and replay limits](docs/cba-live.md). The older runtime-verification report describes CBA as unsupported at that earlier commit; this extension adds support separately and preserves those historical observations.

## EuroCup Women, FIBA Europe Cup and VTB

Three separate pregame models add **2,185 games** without changing the original archive. In the completed 2025–26 historical test, ECW achieved **150/214 (70.09%)**, FEC **133/195 (68.21%)**, and VTB **206/254 (81.10%)**. Each has only one completed test season; VTB historical coverage follows current teams. These are historical winner-selection rates, not live or exact-score accuracy. Low-history teams are explicitly flagged.

```bash
python -m bbtahmin lig-topla --ligler ECW FEC VTB
python scripts/evaluate_competitions.py
python -m bbtahmin bulten --lig ECW
```

See [sources, coverage, test results and replay limits](docs/competitions.md). The five October 22 screenshot reconstructions were generated after tipoff and are excluded from prospective performance. No in-play support is implied for these competitions.

## Adaptive form and domestic workload research

An optional monthly-refit policy selected only from earlier-season results improved the same 214-game ECW 2025–26 test from **150 to 152 correct (70.09% → 71.03%)**, with a small log-loss improvement. FEC and VTB retained the fixed baseline. This is exploratory reuse of existing research seasons; no general accuracy increase has been established. The current 2026–27 selection keeps fixed updates in all three leagues.

Use `tahmin --lig ECW --adaptive-form` with the usual matchup and timestamp arguments to inspect the optional policy. Defaults remain unchanged. A separate official-club archive adds **39 domestic/ABA observations** and explicit workload diagnostics; older training coverage is insufficient to include them in score fitting. See [methods, commands and limitations](docs/adaptive-form.md).

## Optional local MCP server

```bash
python -m pip install -e '.[mcp]'
python -m bbtahmin.mcp_server --root /absolute/path/to/basketbol-tahmin
```

Example configuration for a stdio-capable MCP host:

```json
{
  "mcpServers": {
    "basketball-research": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "bbtahmin.mcp_server", "--root", "/absolute/path/to/basketbol-tahmin"]
    }
  }
}
```

On Windows, use the absolute `.venv\\Scripts\\python.exe` path, escaped for JSON. Tools: `dataset_status`, `bulletin_events`, `bulletin_history`, `predict_bulletin_event`, `predict_live_cba`, `research_results`. They are read-only and do not refresh upstream data or modify the ledger. Run the bulletin refresh explicitly in the CLI. The server was tested over actual stdio and an in-memory protocol client; no host configuration is changed by installing the package.

## Tests and next priorities

```bash
python -m pytest -q
```

Tests are offline. Install the MCP extra to include its protocol test; otherwise that optional test skips. GitHub Actions installs the extra and runs the suite.

Latest local verification (2026-10-23): **213 tests passed**, including the optional MCP protocol test, source identity/final-score boundaries, date-only embargoes, archive-order invariance, future-result isolation, player-report availability and travel unknowns. See [latest test evidence](docs/kanit/asia_tests.xml). Earlier reports remain historical snapshots. The server exposes six read-only tools.

A [fresh runtime verification](docs/kanit/runtime_validation/README.md) retrained all seven models for 2025–26 and partial 2026–27, reproduced 15,932 archived prediction rows within 2.04e-14, exercised a real bulletin fixture, and documented the rejection of unsupported live CBA games. It also reports the chronological **model-selection policy** separately from the fixed-model tables above: NBA 65.81% and NBL 59.22% across five completed seasons.

The highest-priority research additions are point-in-time injury/lineup history, timestamped market snapshots, stronger player/rotation value estimates, domestic-league workload and travel, and chronological calibration/interval checks. The implemented shooting-profile experiment did not consistently improve outcomes and remains disabled. Detailed priorities, reviewed repositories, provider limitations and measured ablations are in [research-and-roadmap.md](docs/research-and-roadmap.md).
