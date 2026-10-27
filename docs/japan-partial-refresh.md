# Preserve healthy Japanese finals when the official schedule has blank scores

## Observed failure

On 27 October 2026, main `86a31ea5c72d3757340ce5ad3c70add4adf73f93` had no open PRs. The latest sports refresh (Actions run 40357333873) persisted partial results and failed its final completeness step. Japan B.PREMIER and B.ONE both reported `Final without valid Japanese scores`; the latest code CI was successful. PR23 source caching and PR24 shadow-policy fixes were already merged.

A live public B.LEAGUE schedule response reproduced the error. For example, official schedule IDs 506497 and 506498 had `FINAL` labels and two present but empty score elements. These are missing facts, not zero-zero finals and not evidence of a different winner.

## Change

Only the specific case of two present, empty score fields is quarantined. The report retains the official event ID, source URL, tipoff, observation time, source state and exact empty score text. Quarantined records do not enter the result archive or training/accuracy cohort. Missing elements, nonnumeric scores and one-sided missing scores still fail closed. The public parser also fails closed unless its caller provides an explicit quarantine sink.

Collection continues through the advertised pages, validates healthy finals and saves each healthy division through the existing identity/conflict-checked archive writer. Duplicate pagination checks include quarantined IDs. After processing both requested divisions, the collector raises an explicit partial-refresh error if any blank finals remain. Therefore the scheduler retains healthy updates while surfacing failure; its existing failed-source gate prevents new predictions from that partially refreshed source. Existing frozen forecasts are untouched.

No official result is inferred from odds or community data. Legacy storage IDs JP_B1/JP_B2 retain the explicit 2026 competition identities JP_PREMIER/JP_ONE, and unvalidated model transfer remains blocked.

## Validation

359 Python tests and 10 UI tests passed locally. Tests cover healthy-plus-blank batches, source identity evidence, strict rejection of malformed scores, both divisions being saved before partial failure, and repeated quarantined pagination. The baseline manifest verifies all 329 original files; 363 current files include legitimate prior appends. No original forecast is regenerated.

This is collection recovery, not a new model. Historical calibration, 1/X/2, football goal totals/BTTS and basketball score-error/interval comparisons are unchanged. No measured accuracy gain or model promotion is claimed. Missing football seasons and Japanese blank-score source records remain explicit external gaps. The collection evidence JSON records actual archive additions separately from these code tests.

## Collected evidence

The live 27 October run completed all 39 B.PREMIER and 37 B.ONE pages. It added 12 distinct official-source finals: B.PREMIER 5,655 → 5,666 (+11), B.ONE 3,782 → 3,783 (+1). Every previously stored result identity and score was compared and remains unchanged. Five B.PREMIER and eleven B.ONE blank-score finals remain quarantined; the collector deliberately returned nonzero after retaining valid updates. Updated future fixtures remain subject to failed-source and competition-transfer gates.

`docs/kanit/asia_data/japan_refresh_recovery_20261027.json` contains the twelve new results, official links, baseline commit, response hashes and validation counts. All fetched responses came from this run; already downloaded pages from the initial failed request were reused rather than downloaded twice. This is public schedule result evidence; neutral venues and overtime remain unverified as documented by the existing source adapter.
