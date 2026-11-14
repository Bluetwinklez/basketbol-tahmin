# Football data and goal research

Football runs separately from basketball: distinct archives, league models, draw outcomes, regulation goals and a separate immutable forecast ledger. Open the local application with `python -m bbtahmin app` and choose **Football** at `/football`. The saved demonstration is labeled; **Refresh & run** refreshes active source seasons and creates a local report in `rapor/football`.

## Available data

The initial import stores **59,240 distinct regulation final scores across 14 leagues**, including **1,884 Turkish Süper Lig scores**. There are 2,511 scheduled rows across all source seasons; that number is not the number of usable upcoming games. The actual seven-day run froze **95 future forecasts**, including 9 Turkish fixtures. All 95 are pending; no prospective accuracy is available. The historical basketball datasets and previously frozen forecasts are unchanged.

Sources are [OpenFootball football.json](https://github.com/openfootball/football.json) and [OpenFootball Europe / Turkey](https://github.com/openfootball/europe/tree/master/turkey), both CC0. This is a community-maintained archive, **not an official federation feed**. Sources, immutable upstream commit links, source hashes, capture times and season counts are retained in `data/football/collection.json` and compressed per-season snapshots. Day precision is retained even when the source includes a clock without verified timezone semantics.

Coverage is incomplete. Turkey has 2018–19, 2019–20, 2020–21 and 2023–24 onward; some later seasons are partial. The source currently lacks active-season files for DE2, ES2, IT2, FR2 and AT1. They have historical support, not current schedule support. Retrieving a repository today does not establish that its results were updated today. The collection report surfaces these gaps; model output independently flags sparse or stale team history.

## Commands

```sh
# Initial backfill; existing valid finals are preserved on failed/regressed sources.
python -m bbtahmin futbol collect --first 2010
# Refresh the current season only.
python -m bbtahmin futbol collect --current-only
# Future source fixtures; preserve earliest prediction, no same-day fixtures.
python -m bbtahmin futbol daily --refresh --days 7
# Manual inspection: not a source-verified fixture or a stored prediction.
python -m bbtahmin futbol predict --league TR1 --home Galatasaray --away Fenerbahçe --date 2026-10-25
# Monthly chronological holdout on available 2025–26 results.
python -m bbtahmin futbol evaluate --season 2025-26 --output rapor/football
# Scheduled pipeline, also available for local/manual runs.
python scripts/refresh_sports.py --sport all
```

League codes: TR1, EN1, EN2, DE1, DE2, ES1, ES2, IT1, IT2, FR1, FR2, NL1, PT1, AT1, BE1, GR1, SC1. The three additions contribute 3,133 stored finals but have no active source schedules; see [sports expansion](sports-upgrade.md) for coverage and explicit research model candidates. Team names use source identities; known Turkish spelling/sponsor aliases are explicit. Unknown teams receive league priors with a warning, not fuzzy identity guesses. Read-only MCP exposes `football_status` and `predict_football`; it does not refresh or place bets.

## Model and measurement

The fixed Poisson baseline estimates separate home/away attack and defence per league using a 1,095-day lookback, a 180-day half-life and eight pseudo-matches of shrinkage. There is no pooling of basketball points into football goals. It exposes home/draw/away probabilities, expected team goals, the most probable scoreline, over 1.5/2.5/3.5 probabilities, both-teams-score probability and a nominal 80% total-goal interval. Expected goals here are model means, **not observed shot-based xG**. Lineups, injuries, odds and player effects are not inputs.

Evaluation fits using only matches before each target month. No same-day/future outcomes fit a prediction. Parameters were fixed before the holdout; target results do not select a candidate. Historical publication times are unknown, so these are retrospective tests. Available 2025–26 cohorts contain **3,744 games**, with **1,789 correct 1/X/2 predictions (47.78%)**. This is not complete coverage of all leagues' seasons and is not prospective performance. The fixed league-frequency comparator uses identical games. The model trails it on winner accuracy in ES2 and IT2; no general accuracy improvement is claimed.

Per-league accuracy, log loss, multiclass Brier score, goal-market accuracy/Brier, total/margin MAE and interval coverage are in `docs/kanit/football/evaluation.json`; all individual predictions are in `predictions.json.gz`. Discrete goal intervals can cover more than their nominal probability; coverage is empirical, not a conditional promise. The baseline comparison covers only 1/X/2, not goal markets.

## Forecasts and ongoing refresh

`data/football_ledger/forecasts/` contains earliest future day-level forecasts with payload hashes, capture times, model cutoffs and archive fingerprints. Re-runs reuse them. Settlement reports are separate; pending, stale, unknown and same-day results do not become finals. A postponed fixture with a changed date is not automatically joined to an old forecast. Only earlier-date finals with matching competition/date/teams can produce a publisher-result comparison. Community-source results are explicitly labeled **not officially verified**, and official accuracy remains unavailable. An independent official final-confirmation adapter is not implemented in this release.

The `Refresh sports data and frozen forecasts` workflow runs daily at **06:30 UTC / 09:30 Europe/Istanbul**, plus manual dispatch. Football and the 10 existing daily basketball competitions refresh independently. Earlier season backfills are not repeated every day. Compressed source snapshots, source failures and both sports' forecast ledgers are persisted to the repository. Frozen forecasts are never regenerated using their outcome. Partial refreshes are persisted but mark the job failed; missing provider data cannot become a successful empty refresh. GitHub scheduling/provider availability is not guaranteed. This is scheduled data collection and forecasting, not autonomous model promotion: changes must pass evaluation and tests.

## Calendar source isolation (2026-11-04)

AR1, CO1, US1, JP1 and CN1 calendar imports fetch only `openfootball/football.json`.
They no longer download or require the unrelated `south-america` Brazilian text archive.
BR1 and BR2 retain their text fallback and JSON preference. Reports include a
`revisions` map for all consulted repositories and `source_revision` per imported
file, matching its pinned source URL; the legacy `revision` field is preserved.
Missing season files remain explicit coverage errors and retain existing snapshots.
CC0 validation, day precision and community/not-official result labels still apply.

This collector reliability change adds no verified match records and makes no
claim of improved prediction accuracy. Existing 1/X/2, goal totals, both-teams-score,
calibration, error and coverage evidence is unchanged; no model candidate or frozen
forecast is modified. Regression tests exercise each of the five JSON-only leagues
with an unavailable unrelated source, missing season files and invalid licenses.

## Empty-source protection (2026-11-05)

The shared football archive writer rejects empty source snapshots before merging
or touching disk. Previously an empty JSON matches list could be reported as a
successful refresh while removing stored scheduled fixtures; retained finals could
also make an empty refresh look productive. Collectors now surface an explicit
`Empty football source snapshot` error and preserve the complete prior archive.
An empty first import creates no archive. Legitimate off-season empty responses
therefore mean unavailable coverage, not successful current-season coverage.
Nonempty schedules without final scores remain supported.

Regression coverage checks lists and generators, first imports and existing mixed
final/scheduled archives, and error propagation for all five JSON-only calendar
leagues. This change adds no match records or model performance evidence. Existing
chronological evaluation, official/community distinctions and frozen forecasts
remain unchanged.

## Paired comparator audit (2026-11-06)

The requested-football evaluator now calculates constant home-win, under-2.5 and
BTTS-no comparators only on the events scored by every model. Previously it used
all season finals even if model fitting skipped a month. The cohort validator
rejects duplicate events, unexpected candidates/targets, mismatched candidate
cohorts and conflicting observed scores. Empty evaluated cohorts have null success
rates, not zero-percent performance. Coverage reports both eligible and evaluated
archive events; it does not certify season completeness.

Run `PYTHONPATH=src python scripts/audit_requested_football_cohort.py` to audit the
saved BR2 2024 predictions without refitting or modifying any forecast. Evidence
is in `docs/kanit/requested_football/cohort_audit_20261106.json`, including the
source prediction hash, exact cohort IDs, 1/X/2 and goal-market metrics, probability
reliability bins, score errors and interval coverage for all four candidates.

All four candidates cover the same 380 stored events (no skipped targets in this
existing evidence, so comparator rates are unchanged). Winner accuracy is 51.58%
for the original baseline and 52.63% for the opponent candidate, versus 52.37% for
always-home: only one additional correct result for the opponent candidate.
The ensemble's over/under-2.5 accuracy is 63.42%, versus 62.63% for always-under.
These are exploratory retrospective community-source results from one season,
not official prospective verification or evidence of general improvement. No new
matches, production model changes or rewritten historical predictions accompany
this audit. Missing source seasons and provider outages remain separate issues.

## Missing calibration evidence (2026-11-12)

The shared reliability calculation used by football evaluation scripts now returns
`n: 0`, empty bins and null Brier/log-loss/calibration-error values for empty
cohorts. It previously divided by zero after computing empty means, preventing
reports for unsupported cohorts. A missing measurement is never reported as zero
error or perfect calibration.

Mismatched array lengths, multidimensional arrays, nonfinite values, probabilities
outside [0, 1] and nonbinary outcomes raise explicit errors rather than producing
misleading calibration evidence. Valid boundary probabilities remain included in
exactly one bin. Regression tests check these cases and hand-calculated metrics.
All 28 saved calibration reports (four BR2 candidates across seven markets, 380
matches each) were recomputed from the existing prediction archive and match the
6 November audit exactly. No predictions were refitted or edited, no new matches
were imported, and no improvement in model performance is claimed.

## Turkish team last-50 inventory (2026-11-13)

Reproduce the read-only coverage audit with:

```sh
PYTHONPATH=src python scripts/audit_football_team_history.py --season 2026-27 --cutoff 2026-11-13 --output docs/kanit/football/team_history_20261113.json
```

The report inventories clubs appearing in the archived season and lists up to 50
earlier available league finals per team, across seasons. It includes exact event
IDs, source-kind counts, date range, results/goals summaries and archive SHA-256
fingerprints. It downloads nothing and does not alter archives or forecasts.
Same-day/future results, unfinished fixtures and other leagues are excluded.
Season membership is archive-derived, not an independently certified roster.

Of 18 archived TR1 clubs, 15 have 50 available earlier league finals. Amed has 10,
Çorum has 9 and Kocaelispor has 21, leaving 110 missing team-match records against
the requested threshold. This is not 110 distinct missing fixtures: a match can
contribute to both participating teams. The 50-record threshold does not certify
complete recent history, all-competition coverage, official results or prediction
readiness. Promoted clubs and source gaps need separate licensed backfills; the
report does not invent missing matches. New imported records in this change: zero.
No model evaluation or performance metric is changed by this inventory.

## Turkish second-tier historical expansion (2026-11-14)

TR2 (Turkish 1. Lig) now has 306 normal-season finals for 2019–20, stored separately
from TR1 and basketball. The source is OpenFootball Europe, CC0-1.0, pinned at
`63df627f3c87ce71708f016522ea236cf74332c3`, path `turkey/2019-20_tr2.txt`.
Archive metadata records its source URL, capture time and normalized source-text
SHA-256. These are community results, not official federation verification.

The importer requires the explicit playoff boundary and 306 games across 18
clubs before writing. Five playoff games (including a penalty final) are excluded.
July dates in this specific pandemic-extended season belong to 2020, not 2019.
Duplicate/conflicting records retain the existing archive. Manual backfill:
`PYTHONPATH=src python scripts/collect_turkish_second.py`. It is intentionally
excluded from daily refresh and does not imply current TR2 coverage. It does not
fill the current Amed/Çorum/Kocaelispor gaps or pool TR2 into their TR1 histories.

Reproduce evaluation with `PYTHONPATH=src python scripts/evaluate_turkish_second.py`.
Evidence is in `docs/kanit/football/TR2_2019-20_evaluation.json`. All four fixed
candidates use identical monthly earlier-only cohorts: 194 of 306 games (63.40%);
112 early games lack the required 100 earlier league finals and are excluded.
The report includes 1/X/2 accuracy/log loss/Brier, goal-total and BTTS metrics,
calibration bins, score errors, interval coverage and exact comparator event IDs.
Winner accuracy is 43.81% baseline, 46.39% opponent/ensemble and 46.91% opponent-DC,
versus 42.27% always-home. However, all candidates trail always-under (54.64%) on
2.5-goal accuracy (52.06–54.12%). One historical season is limited retrospective
evidence with unknown publication history, not prospective success or proof that
more data improves the existing models. No model is promoted and no frozen
prediction is changed.
