# Daily NBA schedule and forecast integration

## How NBA enters the daily forecast list

`NBA` is included in `daily.LEAGUES` (`src/bbtahmin/daily.py`) alongside the other daily basketball competitions (`E`, `KBL`, `JP_B1`, `JP_B2`, `PBA_GOV`, `ABA`, `ECW`, `FEC`, `UKR`, `TR_BSL`, `ARG_LNB`).

- **Refresh (`daily.refresh` / `python -m bbtahmin gunluk --guncelle`):** `NBA` is refreshed as its own source group `('NBA', ['NBA'])` by calling `bbtahmin.veri.nba_schedule.collect()` and writing `data/schedules/NBA.json`.
- **Loading (`daily.source_facts('NBA')`):** Reads `fixtures` and `results` from `data/schedules/NBA.json`. If the snapshot does not exist, `source_facts` raises `ValueError('No NBA schedule snapshot; run with --guncelle')`, which `daily.run` records in `report['skipped']` without generating forecasts.
- **Forecasting and settlement (`daily.run`):**
  - Scheduled fixtures with `start_utc` strictly in `(clock, clock + hours]` (default `hours=48`, allowed range `1..168`) are passed to `tahmin_et('NBA', [(home, away)], start_utc)` and frozen as immutable `prospective-v1` records under `<output>/forecasts/<sha256("NBA:" + event_id)>.json`.
  - If an immutable forecast already exists for `('NBA', event_id)`, the earliest `recorded_at_utc` record is reused. If `event_id`, `league`, `home`, `away`, or `start_utc` differs from the stored fixture, `daily.run` retains the original forecast and records `'Fixture changed; original forecast retained, manual review required'` under `report['skipped']`.
  - Completed `results` from `data/schedules/NBA.json` are merged into `all_results` and passed to `settle(...)` to settle previously frozen NBA forecasts.

## Data source and calendar window

`src/bbtahmin/veri/nba_schedule.py` fetches dated ESPN NBA scoreboards:

- **Endpoint:** `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=YYYYMMDD` (using `ESPN` from `src/bbtahmin/live_feed.py`).
- **HTTP client:** `CachedHTTP().get(url, nba=True, refresh=True)` (with `robots=True` default).
- **Calendar anchor:** `pd.Timestamp.now(tz='America/New_York').date()`.
- **Calendar window:** `range(-1, 8)` — **9 dated scoreboards in total**:
  - Yesterday (`offset = -1`)
  - Today (`offset = 0`)
  - Seven days ahead (`offset = 1..7`)
- **Deduplication and filtering in `collect()`:**
  - Scheduled fixtures are kept only when `timestamp(fixture['start_utc']) > captured` (strictly in the future relative to the fetch timestamp) and deduplicated by `event_id`.
  - Finals (`results`) are collected only from `offset <= 0` (yesterday and today) and deduplicated by `event_id`.
  - Any `event_id` present in `results` is excluded from the returned `fixtures` list.

## Snapshot file (`data/schedules/NBA.json`)

`daily.refresh` writes `data/schedules/NBA.json` atomically using a temporary `.part` file in `data/schedules/` (`NamedTemporaryFile(..., suffix='.part', delete=False)`) followed by `staged.replace(target)`, cleaning up the temporary file in `finally`.

Top-level JSON structure:

- `fixtures` — list of scheduled fixture objects.
- `results` — list of final result objects.

Fields on every `fixtures` and `results` entry:

| Field | Description |
|---|---|
| `event_id` | ESPN `event['id']` (must be non-empty and unique within a scoreboard payload). |
| `league` | Always `'NBA'`. |
| `home` | Canonical archive 3-letter home team code (`ARCHIVE_CODES`). |
| `away` | Canonical archive 3-letter away team code (`ARCHIVE_CODES`). |
| `home_name` | `home['team']['displayName']`, falling back to `home`. |
| `away_name` | `away['team']['displayName']`, falling back to `away`. |
| `start_utc` | ISO-8601 UTC start timestamp parsed from `event['date']`. |
| `captured_at` | ISO-8601 UTC timestamp when that dated scoreboard was fetched. |
| `source_url` | Exact dated scoreboard URL queried for the event. |
| `status` | `'scheduled'` for `fixtures`, `'final'` for `results`. |

Additional fields on `results` entries (`status == 'final'`):

| Field | Description |
|---|---|
| `home_score` | Integer final home score (`int(home['score'])`). |
| `away_score` | Integer final away score (`int(away['score'])`). |

## Team code mapping and unknown codes

`ARCHIVE_CODES` defines the 30 canonical NBA team codes used in `data/maclar.parquet` (`ev`/`dep`):

`ATL`, `BOS`, `BRK`, `CHI`, `CHO`, `CLE`, `DAL`, `DEN`, `DET`, `GSW`, `HOU`, `IND`, `LAC`, `LAL`, `MEM`, `MIA`, `MIL`, `MIN`, `NOP`, `NYK`, `OKC`, `ORL`, `PHI`, `PHO`, `POR`, `SAC`, `SAS`, `TOR`, `UTA`, `WAS`.

`ESPN_CODES` (`{**ESPN_KOD, **CODES}` from `src/bbtahmin/veri/nba_kutu.py` and `src/bbtahmin/live_feed.py`) maps ESPN abbreviations to canonical archive codes:

| ESPN code | Archive code |
|---|---|
| `BKN` | `BRK` |
| `CHA` | `CHO` |
| `GS` | `GSW` |
| `NO` | `NOP` |
| `NY` | `NYK` |
| `PHX` | `PHO` |
| `SA` | `SAS` |
| `UTAH` | `UTA` |
| `WSH` | `WAS` |

All other abbreviations pass through unchanged and must belong to `ARCHIVE_CODES`.

**Unknown codes:** `parse_espn` collects every unrecognized raw tricode across the scoreboard into a set and, after scanning all events, raises `ValueError('Unknown ESPN NBA team tricodes: ...')` with the sorted list of unknown codes. No partial snapshot is written when unknown codes appear.

`parse_espn` also rejects payloads without a league entry whose `abbreviation == 'NBA'`, missing or non-list `events`, missing or duplicate `event_id`, competitions count other than `1`, competitor sets other than `{'home', 'away'}`, or identical home and away team codes.

## Scheduled vs. final classification

`_status()` in `src/bbtahmin/veri/nba_schedule.py` inspects `game.get('status', event.get('status', {})).get('type', {})`:

- **`scheduled`:** `state == 'pre'`, `name in (None, 'STATUS_SCHEDULED')`, and `completed is not True`.
- **`final`:** `state == 'post'`, `name in (None, 'STATUS_FINAL')`, and `completed is True`.
- **`other` (ignored):** Any other status combination (for example `state == 'in'` / `STATUS_IN_PROGRESS` or `state == 'pre'` / `STATUS_POSTPONED`) is skipped. Events with `game.get('timeValid') is False` are also skipped.

Because in-progress and postponed games are ignored, an in-progress game leaves a frozen forecast `pending`; only an explicit `final` result settles it.

## Freshness rules

- **At collection time (`nba_schedule.collect`):** Scheduled fixtures are retained only if `timestamp(fixture['start_utc']) > captured`.
- **At forecast freeze time (`daily.run`):** For any fixture without an existing immutable forecast:
  - `captured = timestamp(f['captured_at'])` must satisfy `captured <= clock` and `clock - captured <= 24 hours`. Otherwise `daily.run` skips the fixture with `'Fixture capture is stale or in the future; refresh first'`.
  - `f['status']` must be `'scheduled'`.
  - The `NBA` source must not have been skipped (`skip_sources`) or failed during refresh.
- **On upcoming report rows:** `source_confirmation_fresh` is `True` only when `captured <= clock`, `clock - captured <= 24 hours`, and the source was neither skipped nor failed. `selected` additionally requires `prediction.get('selection_eligible', False)` and `max(ev_kazanir, 1 - ev_kazanir) >= threshold` (default `0.65`).

## Failure behavior

- If `collect()` or snapshot writing raises an exception, `daily.refresh` catches it for `NBA` alone, records `outcomes['NBA'] = {'status': 'failed', 'error': '<Type>: <message>'}`, and continues refreshing other leagues.
- Because `data/schedules/NBA.json` is replaced atomically only after all 9 dated fetches succeed, a failure on any date preserves the prior `data/schedules/NBA.json` unchanged and leaves no `.part` file behind.
- In `daily.run`, a failed refresh blocks new NBA forecasts (`'Refresh failed; no new forecast from this source'`), marks `source_confirmation_fresh` and `selected` as `False`, and appends `Source refresh failed (NBA): <error>` to `rapor/daily/latest.md`.
- In scheduled `scripts/refresh_sports.py` runs, failed `report['sources']` entries are written to `basketball.errors` and classified via `data/refresh/known_missing.json` (any `unexpected` error causes exit code `1`); see [refresh-known-missing.md](refresh-known-missing.md).

## What is not verified

**Live ESPN endpoint behavior is not verified offline.** `tests/test_nba_schedule.py` exercises `parse_espn`, `daily.refresh`, and `daily.run` using synthetic scoreboard payloads and a monkeypatched `CachedHTTP.get`. Live ESPN availability, `robots.txt` or rate-limit responses, undocumented status names, schema changes, or unexpected tricodes (such as exhibition/All-Star teams) on the live feed cannot be verified by the offline test suite.
