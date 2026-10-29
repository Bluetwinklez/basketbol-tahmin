# Validate every Asian refresh output before publication

On 29 October 2026, main was `9fca67f554522ac605d057ba31cc610716ae588a`. Open PR26 only concerns tool settings and is untouched. Latest code CI and pregame observations succeeded; sports run 40695559252 remains partial because of unavailable football sources and a PBA HTTP 503. The earlier Japanese quarantine and Argentina source-gap changes are already present.

## Failure and fix

`veri/asia.save` previously replaced the final-result parquet and team catalog before validating the incoming fixture list. Duplicate fixtures therefore raised an error after new result data had already been published. Invalid report serialization could fail even later, leaving the report hash inconsistent with the updated archive. These failure paths undermine the guarantee that a rejected update preserves previous data.

The writer now builds and serializes every intended output before publication: result parquet, UTF-8 team catalog, optional fixtures, optional PBA identity-remapped player rows, and merged collection report. The report hash is calculated from the exact prepared parquet bytes. Caller-owned catalog/report objects are copied rather than mutated while preparing outputs. Non-JSON report values are rejected before any existing file changes.

All prepared payloads are written to temporary sibling files first. Only after every staging write succeeds are files replaced; temporary files are removed on success or failure. Each individual replacement is atomic. This is **not** a multi-file crash transaction: process termination or an OS error during the replacement sequence can still leave a partially committed set. Validation, serialization and staging failures are handled before that sequence begins. Concurrent writers are not newly supported.

Existing result-conflict checks, PBA cross-provider identity rules, explicit 2026 Japanese competition identities, historical-only fixture retention and successful-empty-schedule revocation remain in place.

## Evidence

Four new regression tests cover:

- Duplicate fixtures after a valid new result: all previously published bytes remain identical.
- An unserializable report: archives, catalog, fixtures and report remain unchanged; caller inputs are unmodified.
- A simulated failure creating the second staging file: existing files remain unchanged and no temporary file remains.
- Successful publication: result count, dataset SHA-256, merged source list, empty-schedule revocation and a Korean UTF-8 club name agree.

Local validation: **367 Python tests passed**, with 13 existing pandas warnings; **10 UI tests passed**; `git diff --check` passed. `scripts/pin_improvement_baseline.py --verify-only` verified all **329 original files**, with 399 current forecast files including legitimate previous appends. Exact-head GitHub CI also runs rendered UI checks before merge.

This change adds **zero match results**, does not refit or promote a model, and does not rewrite forecasts or outcome metrics. Existing chronological cohort comparisons, calibration, football 1/X/2/goals/BTTS and basketball error/coverage reports remain unchanged. No accuracy increase is claimed. Source outages, missing league-seasons and broader all-competition history coverage remain separate outstanding issues.
