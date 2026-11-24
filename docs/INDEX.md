# Documentation Index

Guide to the documents under `docs/` and the `docs/kanit/` evidence directory. For project overview, installation and common commands, see [README.md](../README.md).

## Operations and daily workflow

- [daily-workflow.md](daily-workflow.md) — Daily basketball forecast refresh (`gunluk --guncelle`), immutable ledger and settlement rules, and historical backfill commands.
- [local-app.md](local-app.md) — Startup, daily usage, security boundaries and testing for the local browser application (`python -m bbtahmin app`).
- [sports-upgrade.md](sports-upgrade.md) — Cross-sport reliability expansion adding Belgium/Greece/Scotland football archives, explicit football research candidates, Turkish basketball duplicate/identity safeguards, board exports and weekly refresh/Playwright checks.

## Basketball models and leagues

- [accuracy-review.md](accuracy-review.md) — October 2026 accuracy diagnosis, per-league extended basketball feature selection, promotion of the opponent-adjusted football default, rejected ideas and NBA closing-odds blend measurements.
- [asian-data-and-models.md](asian-data-and-models.md) — Separate archives (12,850 distinct finals), source checks, independent prior-season models and retrospective results for KBL, Japan B1/B2 and PBA conferences.
- [cba-live.md](cba-live.md) — Experimental Chinese CBA archive (2,386 games), pregame Ridge score model and manual-input regulation live-state projection model with replay limits.
- [competitions.md](competitions.md) — Independent fixed Ridge pregame models, sources, cold-start diagnostics and 2025–26 retrospective evaluation for EuroCup Women (`ECW`), FIBA Europe Cup men (`FEC`) and VTB United League men (`VTB`).
- [adaptive-form.md](adaptive-form.md) — Exploratory `--adaptive-form` monthly-refit policy for `ECW`/`FEC`/`VTB` and auxiliary official-club domestic workload diagnostics (39 games).
- [regional-expansion.md](regional-expansion.md) — 23 October 2026 expansion adding the 3,023-game senior ABA League archive/model and connecting `ABA`, `ECW` and `FEC` to the daily workflow.
- [domestic-expansion.md](domestic-expansion.md) — Separate senior men's archives, sources and chronological evaluations for Turkish BSL (2,523 games) and Ukrainian SuperLeague (997 games), noting that Swedish SBL remains disabled.
- [argentina.md](argentina.md) — Separate senior men's Argentina Liga Nacional (`ARG_LNB`) archive, sources, prior-season model evaluation, promoted-team diagnostics and immutable-ledger checks.

## Football models and coverage

- [football.md](football.md) — Football research workflow, OpenFootball CC0 archives (initial 59,240 finals across 14 leagues), Poisson baseline evaluation, scheduled refresh, TR2 2019–20 historical import and ongoing integrity/calibration audits.
- [football-ensemble.md](football-ensemble.md) — Fixed equal-weight joint-score `ensemble` candidate, per-market reliability reporting and matched 2025–26 evaluation across 3,973 games in 17 leagues.
- [requested-football-coverage.md](requested-football-coverage.md) — Audit of nine screenshot pairings, addition of 2,716 Brazil Série B (2018–2025) CC0 finals with 2024 chronological evaluation, and explicit unsupported-league blocks.
- [screenshot-leagues.md](screenshot-leagues.md) — Integration of Argentine Primera Nacional (`AR2`), current `AR1` (CC BY-SA 4.0) and historical Mexican second tier (`MX2`, CC0) archives alongside remaining unresolved screenshot competition gaps.
- [regional-football.md](regional-football.md) — Historical 2018–2023 publisher archives (7,538 finals under ODC-By 1.0) for Uruguay, Venezuela, El Salvador, Honduras and Bolivia first divisions, without active 2026 coverage.
- [football-americas.md](football-americas.md) — Addition of 3,344 CC0 OpenFootball finals for Brazil Série A (2,937), Argentina Primera (240) and Colombia Primera A (167), calendar refresh support, Brazil 2025 monthly cohort evaluation and remaining screenshot gaps.
- [licensed-football-supplement.md](licensed-football-supplement.md) — CC BY-SA 4.0 Wikipedia score-matrix overlay rules (`data/football/licensed_overlays/`), exact fixture/score verification and quarantine safeguards leaving CC0 base snapshots unchanged.
- [argentina-source-gap-reporting.md](argentina-source-gap-reporting.md) — Structured missing/ineligible season CSV reporting in the Argentina football adapter, four verified 26 October CC BY-SA 4.0 finals (`AR1` 447→449, `AR2` 628→630) and a four-match same-cohort retrospective check.
- [turkish-history-coverage.md](turkish-history-coverage.md) — Audit of available Turkish Süper Lig last-50 league histories (noting missing seasons, cups and aliases) and addition of 1,391 partial historical CC0 finals across MLS, Japan J1 and China Super League.

## Data sources, audits and roadmap

- [data-expansion.md](data-expansion.md) — October 2026 core basketball archive expansion from 26,200 to 54,808 games, NBA/European box-score/shot/play-by-play tables, quality controls and history-length comparison.
- [improvement-implementation.md](improvement-implementation.md) — Implementation report for separately stored domestic/regional women's and club archives (1,878 results), rejected ECW candidates, NBA injury/rotation/venue context and frozen prospective verification.
- [improvement-progress.md](improvement-progress.md) — Running delivery ledger for the 13-step measured improvement plan covering baseline forecast pinning (329 files), football health/quarantine gates, finite ablations, licensed overlays, shadow epochs and CI/locale follow-ups.
- [research-and-roadmap.md](research-and-roadmap.md) — Source-backed review of Iddaa/odds APIs, MCP architecture, external basketball repositories, fixed leakage/ledger bugs, measured ablations and prioritized research additions.
- [delivery-scope.md](delivery-scope.md) — Active delivery audit ledger tracking verified PRs, data-only ablations, source-permission constraints and unresolved acceptance criteria.
- [japan-partial-refresh.md](japan-partial-refresh.md) — Quarantine of official B.LEAGUE `FINAL` rows with two empty score fields while preserving 12 healthy finals (`B.PREMIER` +11, `B.ONE` +1) and surfacing an explicit partial-refresh failure.
- [asia-refresh-preflight.md](asia-refresh-preflight.md) — Preflight validation and sibling staging of all Asian refresh outputs in `veri/asia.save` before single-file atomic replacement so rejected updates preserve prior data.
- [source-refresh-reuse.md](source-refresh-reuse.md) — Session-scoped Git source reuse, atomic initial OpenFootball clones, `IncompleteRead` retries, intact nested failure reporting and offline refresh-health diffing (`scripts/audit_refresh_health.py`).
- [source-fetch-recovery.md](source-fetch-recovery.md) — Bounded three-attempt retry logic (HTTP 502/503/504 and short numeric `Retry-After`) plus UTF-8/size validation and atomic cache replacement in the shared competition fetcher.

## Evaluation, evidence and historical records

- [sonuclar.md](sonuclar.md) — **[Historical / Superseded]** Early Turkish-language backtest snapshot (2026-10-22, 26,200 games) retained as a historical record only; includes legacy absence-enhanced results that must not be presented as current pregame performance.
- [CHANGELOG.md](CHANGELOG.md) — Verbatim archive of release-history, expansion and detailed operational sections moved out of the root `README.md`.
- [requested-matches.json](requested-matches.json) — Machine-readable scope ledger (`requested-match-scope-v1`, checked 2026-10-25) tracking 39 requested football and basketball screenshot pairings, identity verification status and unverified-date limitations.
- `kalibrasyon_*.png` — Calibration curve plots stored directly under `docs/` for historical evaluation snapshots.
- `kanit/` — Evidence directory storing reproducible evaluation summaries, dataset audits, collection manifests, test XMLs, calibration reports and frozen prospective records, including:
  - [kanit/runtime_validation/README.md](kanit/runtime_validation/README.md) — 2026-10-22 runtime verification retraining all seven core models, confirming archival reproducibility within `2.04e-14`, and comparing five-season prior-selection accuracy.
  - [kanit/history_expansion/README.md](kanit/history_expansion/README.md) — 2026-10-23 matched-cohort comparison of adding 3,607 earlier Japanese B1/B2 finals, explaining why the 2021–22 onward default was retained.
