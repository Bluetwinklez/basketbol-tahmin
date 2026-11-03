# Bounded transient-source recovery and cache preservation

On 3 November 2026, main was `2910a52955e034314f49a3b03a9823fcde835138`. Open PRs 26, 29, 30 and 31 concern settings, model features and market evidence; their files are not changed here. Latest pregame observation run 41565238166 succeeded. Sports refresh 41481518320 failed with missing football source seasons and a PBA HTTP 503 in the retained report.

The shared competition fetcher previously made one request and wrote response bytes before checking UTF-8 readability. A transient 503 immediately aborted collection; an unreadable response could replace a previously readable cache.

## Behavior

- Retry HTTP 502, 503 and 504 only, up to three total attempts, with one- and two-second backoff by default.
- Honor numeric Retry-After values up to five seconds. Longer or date-form instructions are surfaced immediately rather than retrying earlier than requested. Access denials, rate limits and other HTTP statuses are not retried.
- Persistent failure still raises to the collector. Cached data is not returned as a successful fresh response after an unsuccessful refresh.
- Validate the existing six-million-byte limit and UTF-8 decoding before publication; stage bytes in a sibling temporary file, atomically replace the single cache file and clean staging files.
- An existing cache requested with refresh=False performs no network request, preserving the current no-unnecessary-download behavior.

Tests simulate recovery after a 503, exhausted retries, 403/429 rejection, long/date Retry-After handling, oversized responses and malformed UTF-8. Failure paths retain the prior cache. Successful recovery is a transport test, not a claim that the live PBA service has recovered or that the payload passes each sport's downstream schema checks.

## Validation and scope

375 Python tests and 10 UI tests passed locally; git diff --check passed. Original integrity verification passed for all 329 pinned files, with 558 current forecast files including previous legitimate appends. Exact-head CI must pass before merge.

Zero new match results are added. No model parameters, defaults, earlier forecasts, cohort selection or outcome measurements change. Existing calibration, 1/X/2, goals, BTTS, score-error and coverage evidence remains unchanged. No accuracy gain is claimed. Missing upstream seasons and persistent provider outages still require source recovery or separately authorized, licensed alternatives. Retry support does not establish new data coverage.
