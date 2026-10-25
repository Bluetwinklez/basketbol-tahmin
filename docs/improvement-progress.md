# Measured improvement delivery

User authorization: implement the detailed 13-step improvement plan in order, without questions; preserve original predictions, complete checks and reviewable GitHub delivery. On 25 October user also explicitly requested waiting for usage capacity and automatic continuation when it returns. A thread heartbeat named `Tahmin iyileştirmelerine limit açılınca devam` is active hourly (id `tahmin-iyile-tirmelerine-limit-a-l-nca-devam`). Do not create duplicates. Check account limits before resumed work. Stop heartbeat when the authorized work is complete.

## Current checkout

`work/basketbol-tahmin`, branch `feat/measured-improvement-cycle`, based on main `7d4e3f29b9ff4f310d0cf0dce87706ff470b5fd6`. Five existing dirty BSL/Ukraine archive/report files came from our earlier audit refresh; do not discard. Additional nine football active-season snapshots and collection report changed in the current CC0 refresh. No original forecast has been intentionally changed.

## Acceptance sequence

1. Pin baseline audit and all original forecast hashes, reproducible report and deduplication policy.
2. Audit current football result gaps against observed fixtures; refresh licensed sources, retain explicit unavailable-source blockers.
3. Quarantine date/club/competition mismatches; maintain corrections separately, never rewrite first forecasts.
4. Add model/code/data provenance and observable current-history gates to new records.
5. Build shared two/three-class evaluation: all games, selected games, coverage, class confusion, calibration, paired day-block intervals, equal coverage.
6. Fix chronological train/calibration/selection/test protocol and finite candidate list before experiments; preserve exploration/forward distinction.
7. Measure data-only change with unchanged model, then individual basketball and football feature/model ablations, including failures.
8. Fit calibration only on earlier out-of-sample forecasts; validate on later dates. Do not tune the existing 72 outcomes.
9. Freeze candidate and selection policy, run reference/candidate side by side before actual games, settle from validated finals.
10. Integrate independent scheduled collection/research/shadow status with existing CI; persist failures and hashes.
11. Run meaningful regression and existing full Python/UI checks, inspect exact-head GitHub CI, PR/merge within previously authorized scope.
12. Deliver evidence and honest remaining external/future dependencies. Future matches cannot be declared validated before completion; no default promotion without evidence.

## Verified baseline and source findings

User-facing audit is at ../../outputs/Tum-tahminler-denetim.json, Tum-tahminler.csv, Tum-tahminler-raporu.md. 281 unique forecasts; 72 result-bearing, 41 correct. Main timestamped basketball cohort 14/22; exact-day football 19/32; date-corrected football 3/9; legacy NBA/NBL 3/6; day-only BSL 2/3. 209 pending/live/unverified, not losses. Small partially settled cohorts are not a general benchmark.

Current source refresh command succeeded on the available CC0 files, `.runtime/improvement-source-refresh.log`. Revisions football.json e6744429ee395bc86f247348c6184bb08d4eb361 and europe 63df627f3c87ce71708f016522ea236cf74332c3. Active files EN1/EN2/DE1/ES1/IT1/FR1/NL1/PT1/TR1 exist, but recent results still stop in September. DE2/ES2/IT2/FR2/AT1/BE1/GR1/SC1 active files unavailable. New capture timestamps alone do not solve missing finals. Existing source terms constraints documented in delivery-scope.md remain binding; do not bulk import unlicensed provider data.

## Existing components to reuse

`football/model.py`: GoalModel, three-class score/metrics; `football/challenger.py`: baseline/opponent/opponent_dc/ensemble; `football/ensemble.py`: coherent score-grid mixture. `asia_model.py`: disjoint previous-season calibration/selection and candidate probabilities. `winner_model.py`: earlier-season candidate selection; `ozellik.py`: day-withheld rolling form, opponent strengths, rest, home, workload features. `evaluation.py`: binary paired day bootstrap/equal coverage. `prospective.py`: hash-verified append-only basket records. `daily.py`: earliest records + independent sources. `football/daily.py`: day-only pregame records, currently lacks code fingerprint and fixture calendar-gap gates. Reuse rather than duplicate existing learners.

## Pending next actions

Inspect uncommitted implementation after each resumed run. Implement baseline manifest and football history health/provenance first, add regression tests, then shared multiclass experiment lifecycle and fixed ablations. `.runtime/audit_all.py` contains explicit reviewed football club aliases and date-mismatch resolution used for the prior user audit; move useful logic into tested modules rather than depend on ignored script. Do not rerun that script blindly: it overwrites final audit files and lacks the final report augmentation.

No new PR or model promotion for this iteration yet. No subagents authorized. Python .venv/Scripts/python.exe; PYTHONUTF8=1, PYTHONPATH=src. Use `.runtime/` for temp tests. Network exec may require approved escalation. Final user artifacts only in ../../outputs/. Future dependencies must remain visible instead of claiming all 13 steps have already finished.

## Implemented checkpoint, 25 October

- `scripts/pin_improvement_baseline.py` pinned and verifies 329 original forecast files (including legacy CSV). No original payload changed. Baseline is `docs/kanit/improvement/baseline.json`.
- `football/health.py`: 30-day diagnostic history age, unresolved active-season past fixtures, per-team provenance. Does not call postponed games completed or assert missing calendars complete. New daily forecasts fail closed on these issues; existing records remain visible.
- `football/daily.py`: code fingerprint, model variant, health/policy metadata on new records; excludes records written after a replay clock; loads `fixture_reviews.json`, blocks new quarantined fixtures and does not settle reviewed conflicts automatically.
- `register_fixture_reviews.py` imported all 15 explicitly reviewed prior date conflicts into separate registry; originals unchanged. Automated independent verification of all future football fixtures still pending.
- `experiment_metrics.py`: normalized 2/3-class metrics, confusion, calibration bins, selected coverage, identical-cohort day bootstrap and equal-coverage comparisons. Binary Brier here is the two-class sum (twice single-probability Brier); do not compare unconverted to old binary reports.
- GoalModel exposes explicit recency/shrinkage/window research settings; exact old defaults retained.
- Football finite experiment: 9 leagues, 3,018 target matches, development 2024-25, target 2025-26. Monthly chronological predictions; temperature calibration on first development date half; learner selection second half. All 6 raw and 6 calibrated candidates plus prior-selected policy reported. No target-based promotion. Raw gzip rows, score errors, confusion, coverage and paired comparisons under `docs/kanit/improvement/football/`. Historical season completeness/publication unknown (TR1 target only 99 available).
- Basketball common learner ablation: 8 leagues, 3,794 matches across last 2 available completed seasons, 6 variants (form alpha .1/.2/.35, removal of rest/opponent-rating/home features), existing Asia fit_fold previous-season disjoint calibration/selection reused across league-specific inputs. This common research reference IS NOT every league's production model. Home-removal retains Elo home advantage. All records/folds/errors under `docs/kanit/improvement/basketball/`.
- Final tests 331 passed, 13 existing pandas warnings; XML `.runtime/improvement-package-tests.xml`. UI 9/9 passed `.runtime/improvement-ui-tests.log`. Prior target-label-independence and quarantine tests pass. `git diff --check` clean.
- Turkish experiment report generated by `scripts/report_improvement.py`, copied to ../../outputs/Iyilestirme-deneyleri.md. Regenerate after script wording fix.

Next required implementation: new append-only parallel reference/candidate forecast lifecycle, pinned candidate/selection registry with coherent per-league support, earlier-OOS basketball calibration measurement, actual data-only football ablation if licensed missing data becomes available, automated fixture validation coverage, CI refresh/settlement integration and promotion gates (minimum sample is a checkpoint not proof). Do not invent a historical data gain when current refresh adds no unique football finals. Capture experiment script hashes and verify input stability in future protocol versions; initial protocols fingerprint src and input files, and their original fingerprints must not be silently rewritten after later source changes. Do not rerun into the same experiment output folder after source changes; use versioned output.

Both historical experiment runners completed successfully; if PTY sessions 72765/57113 still appear, inspect status before launching duplicates. Full regression session 91974 completed in log. Git publication/PR state should be inspected on resume; it was about to be performed at this checkpoint. Heartbeat remains active, hourly, and should wait if account capacity is exhausted; then resume these remaining items without asking the user.
