# Refresh known-missing list and source health rules

## Purpose

`data/refresh/known_missing.json` tracks upstream source outages and missing season files that are already known during scheduled `scripts/refresh_sports.py` runs.

Its goal is to separate expected, previously documented failures (`known_missing`) from new or unexpected failures (`unexpected`) without hiding errors or treating unobserved sources as recovered. Every recorded error stays in the saved refresh report under `errors`; `known_missing.json` only classifies those errors and enforces an expiration date (`review_by`) so outages cannot stay muted indefinitely.

## Entry format

`data/refresh/known_missing.json` must be a JSON list of objects, validated by `load_known_missing()` in `src/bbtahmin/refresh_health.py`.

Allowed fields:

- **Required on every entry:**
  - `sport` — `"football"` or `"basketball"`.
  - `reason` — non-empty string describing why the source is known missing.
  - `review_by` — strict ISO-8601 date (`YYYY-MM-DD`, validated with `date.fromisoformat(value).isoformat() == value`).
- **Match fields** (`MATCH_FIELDS = {'collector', 'source', 'league', 'stage'}`):
  - At least one of `collector`, `source`, or `league` must be present on every entry.
  - `stage` is optional (for example `"historical_backfill"`).

Validation rules:

- No keys outside `{'sport', 'reason', 'review_by', 'collector', 'source', 'league', 'stage'}` are permitted.
- Every field value must be a non-empty, non-whitespace string.
- Any schema or date-format violation raises `ValueError` at refresh startup.

## Matching rule

`classify_errors(sport, errors, entries)` in `src/bbtahmin/refresh_health.py` evaluates each error in a sport's `errors` list:

- An error matches an entry when `entry['sport'] == sport` **and** for every key in `MATCH_FIELDS` (`collector`, `source`, `league`, `stage`) that is present in the entry, `error.get(key) == entry[key]`.
- Errors that match at least one entry are placed in `known_missing`.
- All remaining errors are placed in `unexpected`.

In `scripts/refresh_sports.py`:

- Football collector errors have `source` (defaulting to the collector name) and `collector` (the `attempt` name: `screenshots`, `football`, `BR2`, `BR1`, `AR1`, `CO1`, `US1`, `JP1`, `CN1`, or `football_ledger`).
- Basketball errors come from historical backfill (`league`, `error`, `stage="historical_backfill"`) and failed entries in `report['sources']` (`league` plus the source error fields).

## Exit code rule

At the end of a run, `scripts/refresh_sports.py` returns `refresh_exit_code(results, entries, finished.date())` from `src/bbtahmin/refresh_health.py`. The process exits with code **`1`** if **any** of the following conditions holds, and **`0`** otherwise:

1. Any sport report in `results` has `status == "failed"` (an uncaught whole-sport exception).
2. Any sport report in `results` has a non-empty `unexpected` list.
3. Any entry in `data/refresh/known_missing.json` has an expired review date (`date.fromisoformat(entry['review_by']) < today`, where `today` is the UTC date when the refresh finished).

Notes:

- An entry whose `review_by` equals `today` is not yet expired; exit code `1` triggers once `review_by < today`.
- Expiration is checked across all entries in `known_missing.json`, even when `--sport` restricts the run to a single sport.

## Adding, updating, or removing entries

- **Add an entry:** Inspect the latest timestamped report in `data/refresh/<YYYYMMDDTHHMMSSZ>.json`, copy the exact `sport` and matching fields (`collector`, `source`, `league`, and `stage` if present) from the error under `<sport>.errors` / `<sport>.unexpected`, add a concise `reason`, and set `review_by` to a future `YYYY-MM-DD` date.
- **Update an entry:** When `review_by` is approaching or expired, re-check the upstream source. If the outage persists, update `reason` and advance `review_by` to a new `YYYY-MM-DD` date.
- **Remove an entry:** Once the source recovers and no longer fails in refresh reports, delete its object from `data/refresh/known_missing.json`.

## `PBA_GOV` auto-disable rule

During basketball refreshes, `scripts/refresh_sports.py` checks `auto_disabled(saved_reports(directory), sport, 'PBA_GOV', pd.Timestamp.now(tz='UTC'), threshold=3, retry_days=7)`:

- `saved_reports(directory)` reads `data/refresh/*.json` files whose stem matches `YYYYMMDDTHHMMSSZ` in reverse chronological order (newest first), using the filename timestamp as UTC observation time.
- Reports where `basketball.status` is not in `OBSERVED` (`"partial"`, `"succeeded"`) or where `PBA_GOV` is already listed in `skipped_auto_disabled` are skipped during scanning so skips do not disturb the retry clock.
- Scanning stops (`break`) at the first observed report that has no error for `PBA_GOV`.
- If the most recent failure (`last_failure`) is at least `7` days old (`now - last_failure >= timedelta(days=7)`), `auto_disabled` returns `None` and `PBA_GOV` is retried.
- Otherwise, once `PBA_GOV` has at least `3` consecutive observed failures (`threshold=3`), `auto_disabled` returns `{"league": "PBA_GOV", "failure_count": <n>, "last_failure": "<YYYY-MM-DD>"}`.
- When auto-disabled, `PBA_GOV` is passed in `skip_sources` to `basketball_run(...)` and recorded under `skipped_auto_disabled`.
- In `transitions()` (`src/bbtahmin/refresh_health.py`), a previously failing league that is in `skipped_auto_disabled` is placed in `unresolved_unobserved` rather than `no_longer_reported`, so an auto-disabled source is not mistaken for a recovered source.

## Report fields

Each refresh writes `data/refresh/<YYYYMMDDTHHMMSSZ>.json` keyed by sport (`football`, `basketball`). Each sport object contains:

- `status` — `"succeeded"` (no errors), `"partial"` (one or more errors in `errors`), or `"failed"` (whole-sport exception, with `error`).
- `errors` — full list of errors observed during the run (present for `"succeeded"` and `"partial"`).
- `known_missing` — errors from `errors` that matched an entry in `data/refresh/known_missing.json`.
- `unexpected` — errors from `errors` that matched no entry in `data/refresh/known_missing.json`.
- `skipped_auto_disabled` — included only when at least one source was auto-disabled; list of `{league, failure_count, last_failure}` objects.

## Current known-missing entries

As recorded in `data/refresh/known_missing.json` (all 15 entries have `review_by`: **`2026-12-08`**):

| Sport | League | Source | Collector | Reason | `review_by` |
|---|---|---|---|---|---|
| `football` | `DE2` | `football` | `football` | Current-season source file unavailable in the November 17–23 refresh reports. | `2026-12-08` |
| `football` | `ES2` | `football` | `football` | Current-season source file unavailable in the November 17–23 refresh reports. | `2026-12-08` |
| `football` | `IT2` | `football` | `football` | Current-season source file unavailable in the November 17–23 refresh reports. | `2026-12-08` |
| `football` | `FR2` | `football` | `football` | Current-season source file unavailable in the November 17–23 refresh reports. | `2026-12-08` |
| `football` | `AT1` | `football` | `football` | Current-season source file unavailable in the November 17–23 refresh reports. | `2026-12-08` |
| `football` | `BE1` | `football` | `football` | Current-season source file unavailable in the November 17–23 refresh reports. | `2026-12-08` |
| `football` | `GR1` | `football` | `football` | Current-season source file unavailable in the November 17–23 refresh reports. | `2026-12-08` |
| `football` | `SC1` | `football` | `football` | Current-season source file unavailable in the November 17–23 refresh reports. | `2026-12-08` |
| `football` | `BR2` | `BR2` | `BR2` | Current-season calendar source unavailable in the November 17–23 refresh reports. | `2026-12-08` |
| `football` | `AR1` | `AR1` | `AR1` | Current-season calendar source unavailable in the November 17–23 refresh reports. | `2026-12-08` |
| `football` | `CO1` | `CO1` | `CO1` | Current-season calendar source unavailable in the November 17–23 refresh reports. | `2026-12-08` |
| `football` | `US1` | `US1` | `US1` | Current-season calendar source unavailable in the November 17–23 refresh reports. | `2026-12-08` |
| `football` | `JP1` | `JP1` | `JP1` | Current-season calendar source unavailable in the November 17–23 refresh reports. | `2026-12-08` |
| `football` | `CN1` | `CN1` | `CN1` | Current-season calendar source unavailable in the November 17–23 refresh reports. | `2026-12-08` |
| `basketball` | `PBA_GOV` | *(not set)* | *(not set)* | PBA source returned HTTP 503 in consecutive November 17–23 refresh reports. | `2026-12-08` |
