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

## Atomic initial source checkouts (2026-11-17)

Initial OpenFootball clones now run in a temporary sibling directory. The final
cache path is created only after the clone succeeds. If Git exits unsuccessfully
or times out after writing partial files, the staging directory is removed and
the error remains cached for the current refresh session. The next session retries
a clean clone rather than attempting `git pull` inside an incomplete checkout.
Existing successful repositories still use incremental `pull --ff-only`; an
explicit offline read retains its existing semantics. This does not bypass
license, source revision, fixture identity or score-conflict validation.

Regression tests simulate partial downloads for both process failure and timeout,
assert cleanup and single-attempt failure reuse, then verify recovery and reuse
in the next session. No source downloads, archived match changes, frozen forecast
changes or model promotions are needed for this fix. Existing missing upstream
season files and PBA HTTP 503 errors are separate and remain unresolved.

The 2026-11-16 refresh also recorded an ARG_LNB `IncompleteRead` after 1,084,997
bytes. The shared basketball HTML fetcher now retries this transient read failure
within its existing three-attempt budget (one- and two-second waits). It discards
partial bytes, closes each response and preserves the last complete cache if all
attempts fail. Tests cover recovery and exhaustion. This is tested recovery logic,
not a claim that the upstream service has recovered or that new results were added.

## Offline failure transitions (2026-11-23)

Run `PYTHONPATH=src python scripts/audit_refresh_health.py PREVIOUS CURRENT
--output REPORT` (on one line) to compare two archived refresh reports without
network requests. The report pins both input SHA-256 hashes and distinguishes
new failures, continuing failures, failures no longer reported and unresolved
failures in an unobserved sport. A missing or wholly failed sport cannot clear
previous failures. First observations are baselines, not newly detected outages.
Collector, source, league, season, stage and repository define failure identity;
duplicate identities are rejected rather than silently overwriting evidence.

`docs/kanit/source_health_20261123.json` compares the final reports of November 21
and 22. This is diagnostic evidence only: a failure no longer appearing does not
prove complete data or upstream recovery. In particular, historical-backfill
stages may not run daily. No downloads, new matches, forecast edits, model refits
or accuracy claims accompany this tool. Existing chronological model/calibration
reports remain unchanged.
