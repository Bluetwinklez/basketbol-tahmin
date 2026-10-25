# Delivery scope and evidence ledger

Audit started 25 October 2026 from main `0fafc2ef6345a19f447f36f2be046a9a26a41f29`. No open PR was returned. The latest code test run was successful (40134216022); both subsequent scheduled sports refresh runs failed. Run 40190799925 failed at `git pull --rebase`: the Asia collection reports were modified but not staged. Refresh also reported unavailable football seasons and an Argentina natural-identity conflict. These are separate failures.

This is an active delivery ledger, **not a statement that the full requested project is complete**. `requested-matches.json` records 34 known pairings with unknown fixture attributes left null. Four original images were retrieved from accessible chats and visually inspected. The remaining original images were not supplied by chat retrieval. Prior assistant prose is a discovery lead, not independently verified evidence. Repeated pairings without verified dates are not counted as distinct fixtures.

| Requirement | Current state / missing information | Next action | Validation / evidence |
|---|---|---|---|
| All messages and images | Four images inspected; other originals unavailable through retrieved chats | Recover remaining original attachments and exact fixture dates | requested-matches.json; inspected image filenames |
| Repository audit | Current main inspected; source collectors, models, daily workflows, CLI/MCP tests inspected | Verify new PR CI and merge SHA | GitHub run links and regression XML |
| Requested football leagues | Historical AR1/AR2/MX2/BR1/BR2/TR1 and five regional archives exist; CO2/USLC/USL1 missing; many current seasons absent | Obtain properly licensed current feeds and missing histories | kanit/delivery_audit/football_inventory.json |
| Requested basketball leagues | Existing NBA/NBL/KBL/BSL/LNB support is partial; WNBL, Uruguay and Sudamericana gaps remain | Add separate validated sources/models; do not substitute men's NBL for WNBL | Source collection reports, same-cohort tests |
| Identity | Japanese 2026-27 screenshot B2 label is wrong; official B.ONE roster includes the five pairings | Complete fixture-level IDs, dates and remaining club mappings | Official B.LEAGUE roster https://www.bleague.jp/news_detail/id=620570 and Fukui–Saitama ScheduleKey=507278 |
| Source permission | Existing imports retain CC0, CC BY-SA and ODC-By attribution; no new redistribution permission inferred | Establish terms before new bulk publication | regional-football.md; ARGENTINA-LICENSE-DATOS.md; source URLs per row |
| Actual Turkish latest 50 | Available-league audit is not all-competition completeness; cups, missing seasons and aliases remain | Verify complete club calendars before asserting latest 50 | turkish-history-coverage.md; kanit/turkish_last50/coverage.json.gz |
| Source refresh | Fixed independent football attempts, duplicate hiding, cross-season writes and unstaged Asia reports | Resolve remaining provider conflicts; refresh current seasons | test_archive_integrity.py; persisted data/refresh reports |
| Model experiments | Defaults retained; legacy Japan models blocked after July 2026; no accuracy increase claimed | Separate competition-transfer experiment and data-expansion ablation | asia_model.py; same-cohort BR2 evaluation |
| Honest metrics | Existing chronological football/basketball comparisons retained | Add remaining team-score and uncertainty reports on untouched cohorts | kanit/requested_football; kanit/asia_models |
| Requested predictions | Incomplete identity/date/history must block current forecasts; no invented probabilities | Run verified sufficient fixtures; label reconstructions separately | Immutable forecast ledgers and skipped reasons |
| Preserve first forecasts | Existing JSON records untouched; new data hashes use portable path keys | Verify final diff contains no changed original prediction payload | football/daily.py; prospective.py; ledger tests |
| Tests and publication | Regression tests and live refresh being executed; CI not yet run for this branch | Publish PR, inspect exact-head checks, merge only on success | GitHub PR and Actions URLs to be appended |

## Source investigation

- Official Japanese 2026-27 B.PREMIER/B.ONE/B.NEXT membership: https://www.bleague.jp/news_detail/id=620570. Tachikawa's official club page identifies B.ONE and the Gifu fixture: https://www.bleague.jp/club_detail/?TeamID=2727. Legacy storage filenames remain for compatibility, but current records expose `competition_code`; legacy models cannot automatically transfer across this reorganisation.
- USL official season results exist at https://www.uslleagueone.com/2025-scores. The separately published cup results contain penalty-decided matches (https://www.uslleagueone.com/2025-round-1-results); these must not be imported as League One regulation matches. Bulk redistribution permission and a validated parser have not been established.
- Colombia Primera B has a distinct feed offered at https://anysport.io/leagues/colombia-primera-b/ and CSV/API access at https://footystats.org/colombia/categoria-primera-b/datasets. No subscription or account was opened. These are source leads, not permission to republish their databases.
- TFF's official 2021-22 fixtures exist at https://www.tff.org/default.aspx?pageID=1576; absence from selected CC0 archives is not absence of real fixtures. A complete dated parser and reuse terms remain to be checked.

## Resume state

Branch `fix/archive-integrity-and-scope` is a fresh isolated clone. Runtime files, virtual environment and logs are under `.runtime/` and `.venv/` (ignored). Run with Python 3.12 and UTF-8 on Windows. Source-refresh logs are `.runtime/live-refresh.log`; regression output `.runtime/full-tests.log`; XML `.runtime/tests.xml`. A live refresh succeeded for most basketball sources but retained an Argentina duplicate-identity failure and explicit missing football-source errors. Do not describe the refresh as successful overall. No new unique football finals were added in this refresh; capture timestamps and schedules were refreshed.

Remaining immediate actions: finish final regression, examine Argentina duplicate groups before linking identities, complete inventory/coverage regeneration, review code/data diffs, publish PR with verified checks, merge, and continue the unresolved rows above. Do not silently promote the research model or rewrite earliest forecasts.
