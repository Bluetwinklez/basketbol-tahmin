# Delivery scope and evidence ledger

Audit started 25 October 2026 from main `0fafc2ef6345a19f447f36f2be046a9a26a41f29`. No open PR was returned. The latest code test run was successful (40134216022); both subsequent scheduled sports refresh runs failed. Run 40190799925 failed at `git pull --rebase`: the Asia collection reports were modified but not staged. Refresh also reported unavailable football seasons and an Argentina natural-identity conflict. These are separate failures.

This is an active delivery ledger, **not a statement that the full requested project is complete**. `requested-matches.json` records 38 known pairings with unknown fixture attributes left null. Four original images were retrieved from accessible chats and visually inspected. The remaining original images were not supplied by chat retrieval. Prior assistant prose is a discovery lead, not independently verified evidence. Repeated pairings without verified dates are not counted as distinct fixtures.

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


## Verified follow-up

PR #17 merged as c25335afc90b5b275db9a11feb4377bc2de4a4fa after push and PR test workflows succeeded (40191994720 / 40192052691), including rendered Chromium UI checks. Local validation passed 312 Python and 9 UI tests before the subsequent Argentina fix.

Argentina investigation found 35 existing official finals with identical exact UTC tipoffs, ordered club IDs and scores, but 35 changed opaque URL tokens. The reconciliation only reuses a unique prior official timestamp identity, including prior scheduled fixtures. Changed times, ambiguous identities and day-only publisher results do not link. Score conflicts remain fatal. A fresh official collection completed with 1,721 finals (38 in 2026–27), 83 explicit identity links and no source errors. Three genuinely new finals were added; token rotations are not counted as new games. The local Argentina daily replay reports ten upcoming forecasts with no skipped source errors. Existing frozen records remain unchanged.

The refreshed independent archives add 56 unique basketball finals against the pinned starting main: Japan B.PREMIER 11, Japan B.ONE 13 (legacy storage paths retained), KBL 7, PBA Governors Cup 1, ABA 8, ECW 1, BSL 4, Ukraine 5, EuroLeague runtime overlay 3 and Argentina LNB 3. All are partial coverage. Football adds zero new unique finals. `python scripts/audit_delivery.py` reproduces the league/season inventories and confirms all 105 original football/basketball/Argentina forecast payloads unchanged.

The same 380-match 2024 BR2 chronological cohort was rerun. Winner accuracy remains baseline 51.58%, opponent 52.63%; no data or model accuracy increase is established. Floating point rounding differences across platforms are not improvements. KBL requested-fixture reconstructions, if generated, are explicitly post-result research and excluded from forward success rates.


Source terms follow-up: https://football-data.co.uk/contact.php limits its free CSV use to personal/academic research with at most twice-weekly light downloads and explicitly declines AI/commercial usage requests. It was not used to fill or republish missing Turkish seasons. The CC0 evrimulgen/turkey archive stops at 2019–20 and cannot establish current latest-50 coverage. These source limits are recorded rather than silently bypassed.

An additional replay leak was fixed: a historical requested clock cannot reuse a forecast recorded later. Regression coverage now explicitly verifies that exclusion while retaining original payloads. Argentina replay tests use recorded source fixtures, because a current refresh correctly moves some earlier fixtures into finals.


The second validation passes 315 Python tests. A repeatable Windows early-POST rejection reset was fixed by consuming only bounded request bodies before returning authentication errors; host/origin/token checks remain enforced. Four additional repository-backed screenshot pairings (Helsinki–Brno, Pärnu–Vienna, Celje–Brno, Montana–Girona) bring the scope registry to 38. Additional durable-chat retrieval was attempted: one large prior turn exceeds the retrieval service response limit; it was not claimed reviewed.


## Identity and reporting follow-up

PR #18 merged as 39ec87d3abd8e31d83f8f11a887b99d5b86f1cda after successful exact-head push and PR CI, including rendered UI. Team-name resolution now accepts only a unique explicit normalized alias or team code. Prefix/fuzzy matches are suggestions only; shared aliases cannot collapse into one arbitrary team. Historical football coverage is exposed separately from active-season availability through `python -m bbtahmin futbol coverage`, `/api/football/coverage`, and the existing read-only MCP `football_status` tool. The 90-day history diagnostic is not an accuracy guarantee; no coverage count automatically certifies a fixture prediction.

Football score reports now include home, away and combined team-score MAE with their explicit sample count. Older result objects that lack team errors report no such metric rather than silently treating missing errors as zero. The unchanged BR2 chronological cohort is regenerated to include these measures; defaults remain unchanged.


Final local follow-up validation: 321 Python tests pass. On the unchanged 380-game 2024 BR2 cohort, baseline 1/X/2 accuracy remains 51.58% and combined team-score MAE is 0.79609 goals; the existing opponent candidate remains 52.63% / 0.79394. These are different existing candidates, not evidence of a new-model gain. `audit_fenerbahce_history.py` exports 50 available BSL/EuroLeague candidates before the original 23 October forecast date, while explicitly leaving actual all-competition latest-50 completeness unverified. Missing cup/Super Cup calendars and venue checks are not filled with old or duplicate records.


## Measured data-only ablation and current resume point

PR #19 merged as de35010e7c4aa342dfef0dd4418146df240e4d2d after successful exact-head CI. The runtime KBL ablation compares the fixed existing model policy with the pinned initial archive versus expanded history on exactly the seven newly imported finals, with no outcome-based cohort filtering and no tuning. Both variants withhold the target UTC day. Old versus expanded: winner 3/7 versus 4/7; log loss 0.66185 versus 0.64662; Brier 0.23506 versus 0.22780; team-score MAE 10.16039 versus 10.10140; total MAE 17.54743 versus 17.45059; margin MAE worsens 6.75613 to 6.94140. Total 80% coverage is 4/7 for both. Wilson winner intervals are broad and overlap. The experiment is retrospective with unknown historical publication availability, not forward success and not proof of general improvement. No new model or default was promoted.

The current scope still requires independent source/fixture work: recover remaining original images (one prior durable turn exceeds retrieval response limits); verify exact dates and identities for unresolved pairings; obtain reusable current CO2/USL/regional/Mexico histories; add Uruguay/Sudamericana/WNBL coverage; validate Japanese competition transfer separately; establish actual Turkish all-competition last-50 calendars; measure any future candidate on an untouched chronological holdout. The completed engineering and refreshed records do not satisfy those missing acceptance criteria. All work and scripts are committed through reviewable PRs rather than an untracked background process.
