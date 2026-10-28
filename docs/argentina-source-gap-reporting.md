# Argentina source gaps and four licensed football additions

On 28 October 2026, main was `c0644b7efbf2296619ee76f8272ffacef0282750`. Open PR26 changes tool attribution settings only; this work does not touch those files. Latest code tests and observation workflows succeeded. The stored sports refresh remains partial for unavailable football seasons, quarantined Japanese blank-score finals and a PBA HTTP 503. Prior fixes were retained.

## Refresh correctness

The Argentina adapter silently skipped missing season CSV files and reported an empty successful collection. It now records a pinned source path, season and retained-archive status for each missing requested file. A present file with no eligible rows reports the affected supported league and raw-file hash. License, stage, neutral-venue and score filters remain intact. Healthy later seasons continue importing. The wrapper propagates these structured errors through the existing partial/nonzero refresh reporting; Mexico backfill continues independently. Invalid source year ranges fail explicitly. Existing archives are not deleted when upstream input is absent.

Tests exercise missing files without changing prior bytes, entirely ineligible input, healthy current leagues after a missing backfill year, and nested error propagation with independent Mexico continuation.

## Verified data delta

The current source at `rhinoah/futbol-argentino-data` revision `07dc9c3ef323659a6b18b99356890918b54ac170` has an available 2026 CSV. It is not affected by the missing-file regression today. Its SHA-256 is `dbe8f7896e1f5f67e12a70811b397e6c52c138ae898c1b451f5634f2148090ec`.

Four distinct finals dated 26 October were added: Unión–Estudiantes (LP) 3–1, Instituto–Deportivo Riestra 1–0, Nueva Chicago–San Martín (SJ) 1–1, Defensores de Belgrano–San Miguel 0–0. AR1 grows from 447 to 449 current-season records; AR2 from 628 to 630. All previously stored result identities, dates, teams and scores were compared and preserved. The four new identities have no previous ordered-team encounter in their league-season archive. Per-row Wikipedia attribution, pinned publisher URLs, CC BY-SA 4.0 and day-only precision remain intact. These are publisher/community results, not official federation verification.

## Same-cohort retrospective check

Run `PYTHONPATH=src python scripts/evaluate_argentina_refresh.py`. The fixed four-event cohort is identical for all existing candidates, with all target-day and later rows excluded before fitting. No candidate, calibration or selection setting was tuned. Full predictions, input hashes, calibration bins, 1/X/2 losses, 1.5/2.5/3.5 totals, BTTS, team/total/margin errors and interval coverage are in `docs/kanit/football/argentina_refresh_20261028.json`.

| Candidate | Winner correct | Over/under 2.5 correct | BTTS correct | Total MAE |
| --- | --- | --- | --- | --- |
| Baseline | 2/4 | 3/4 | 2/4 | 1.1640 |
| Opponent | 1/4 | 3/4 | 3/4 | 1.0634 |
| Opponent low-score | 1/4 | 3/4 | 3/4 | 1.0634 |
| Ensemble | 2/4 | 3/4 | 3/4 | 1.1137 |

Always-home gets 2/4; always-under-2.5 gets 3/4; always-BTTS-no gets 2/4. All candidates cover 4/4 targets and their 80% total intervals contain 4/4 results. With only four observations these percentages and calibration bins are descriptive, not reliable calibration estimates. Historical publication availability is unknown. This is a post-result audit, not frozen prospective performance or a controlled old-versus-new-data ablation. No accuracy increase or production promotion is claimed.

## Checks and remaining gaps

363 Python tests and 10 UI tests pass locally; the evaluation script runs successfully. The original manifest verifies all 329 pinned files (377 current files include prior legitimate appends). Forecasts and basketball archives are unchanged. Exact-head CI must also pass before merge. Wider missing seasons, official football result verification and true Turkish all-competition latest-50 coverage remain unresolved; additional source availability is not inferred from successful transport.
