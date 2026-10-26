# Incremental source refresh and intact failure evidence

On 26 October 2026, main was `228a4de3f1ead401010619279f97bbb55cdda698`, no pull requests were open, and the latest main code CI (40222976411) and observation run (40252823718) had succeeded. PR22 already supplied licensed results and league-specific forward experiments; this change does not repeat them.

## Problem and behavior

The football refresh called `git_source` 15 times for three shared repositories: two calls from European collection and two from each of seven calendar collectors. Repeated pulls were unnecessary and could change a shared source revision halfway through a run. A scoped refresh session now performs one clone/pull per source and reuses that checkout for the remaining collectors. The next invocation always checks upstream again. Explicit offline reads do not satisfy a fresh update request.

Failed updates are also retained as failures for that invocation, so dependent collectors do not repeatedly retry or treat a stale checkout as freshly downloaded evidence. Independent repositories and forecast settlement still run. The next invocation retries failed sources. This is not a persistent success cache or a change to final-result validation.

The scheduled workflow restores only source Git repositories from an Actions cache and saves them after collection, including partial collection. Each run has a new cache key (including attempt), restores the latest matching cache, and still pulls upstream. Forecasts, model artifacts and result snapshots are not restored from this cache. Cache misses retain the original shallow-clone behavior. No static regional archive is downloaded.

Nested source errors previously collided with the outer `source` keyword, replacing the real error with a duplicate-key TypeError. Reports now retain the original source/error and add the orchestration stage as `collector`; collection stays partial/nonzero and later collectors run.

## Validation and limits

Regression tests simulate the full shared-repository call sequence: 15 update requests become 3 Git operations; a second invocation performs 3 fresh pulls. A failed checkout is attempted once, remains an error for all eight dependent requests, retains its previous file, and is retried next invocation. Another test preserves the exact nested Argentina error and confirms all seven calendar collectors plus settlement still execute.

Run `python -m pytest -q`, `npm run test:ui`, and `PYTHONPATH=src python scripts/pin_improvement_baseline.py --verify-only`. The original manifest still verifies 329 pinned files (337 current files, including legitimate appends). Local results: 352 Python tests passed (13 existing pandas warnings), 10 UI tests passed, and `git diff --check` passed. Exact-head CI also runs rendered UI checks.

This maintenance change adds **zero match results** and changes no model, recorded prediction, selection policy or evaluation cohort. Existing historical accuracy, calibration, 1/X/2, goals, BTTS, error and interval metrics remain those of the versioned experiments. No accuracy improvement is claimed. Source files absent upstream and the separately reported Argentina natural-identity conflict remain data-quality issues; caching cannot manufacture missing results. First scheduled cache use and network savings in bytes/time require a subsequent real workflow run and are not claimed as measured here.
