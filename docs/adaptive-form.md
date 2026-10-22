# Adaptive form experiment and auxiliary club workload

Two independent additions address changing team strength and missing domestic schedules. They do not reuse final outcomes to rewrite the frozen October 22 forecasts.

## Earlier-season selection of monthly model refits

`--adaptive-form` is an optional experiment for `ECW`, `FEC` and `VTB`. It uses the same fixed Ridge alpha 10 and existing day-batched features as the baseline. A monthly candidate refits on completed earlier seasons plus target-season games before the current UTC month. Current-month outcomes never fit that month's estimator; earlier-day outcomes can still update the existing rolling features.

Before a target season, compare fixed and monthly variants on the preceding season. Select monthly only when both margin MAE and raw total MAE improve by more than 1% and winner accuracy does not decline. Otherwise retain the fixed model. Residual variance and total bias are estimated from the selected preceding-season predictions. This is selection of an update policy; it is not a fitted injury or domestic-form model.

| Completed 2025–26 | Games | Fixed correct | Policy correct | Accuracy, fixed → policy | Total MAE, fixed → policy |
|---|---:|---:|---:|---:|---:|
| EuroCup Women | 214 | 150 | 152 | 70.09% → 71.03% | 13.624 → 13.609 |
| FIBA Europe Cup | 195 | 133 | 133 | 68.21% → 68.21% | 12.124 → 12.124 |
| VTB | 254 | 206 | 206 | 81.10% → 81.10% | 13.491 → 13.491 |

ECW log loss changed from 0.604484 to 0.603451; Brier from 0.208212 to 0.207610. The other leagues retained the fixed model. Two extra correct selections in one season are **small exploratory evidence**, not a demonstrated general advantage. These historical research seasons have already been inspected; they are not a new untouched holdout. Partial 2026–27 is reported separately. The preceding-season gate currently retains fixed updates for all three leagues in 2026–27. Do not force the monthly option simply because the old ECW test had a higher percentage.

The default predictor and bulletin use the fixed model. The optional policy selects its own update behavior from earlier data; the flag does not force monthly refitting. [Per-game rows, policy selections, dataset hashes and tests](kanit/adaptive/) are committed. Original score archives, baseline research artifacts and frozen forecasts remain unchanged.

```bash
python scripts/evaluate_adaptive.py
python -m bbtahmin tahmin "ZKK Celje - KP Brno" --lig ECW --tarih 2026-10-22T19:00+03:00 --adaptive-form --json
```

The historical named matchup is a replay example, not a new pre-tipoff prediction. The CLI requires an explicit supported league for this experiment. Recording still requires a future tipoff.

## Auxiliary official-club schedules

A separate archive stores 39 finished observations: 31 Czech women's ŽBL games from [Žabiny Brno's senior schedule](https://www.bkzabiny.cz/tym/9-a-tym/zapasy), plus five Austrian BSL and three ABA men's games from [BC Vienna's official schedule](https://bcvienna.com/en/schedule/).

These are **club cohorts, not complete national-league archives**. Known identities explicitly map Žabiny and KP Brno to distinct ECW organisations and BC Vienna to its FEC organisation. Other opponents receive gender/source-specific namespaces; no fuzzy cross-gender merging is performed. European competition rows are excluded from this auxiliary archive to avoid duplicate workload observations.

Dates use explicit Europe/Prague or Europe/Vienna localization before UTC conversion. Vienna's score orientation was not independently verified, so those scores are not stored. Czech score facts are retained as unverified source values. Neither source's scores enter a strength model. Source capture time is recorded; it is not a claim about historical publication or revision time.

`auxiliary_workload` in prediction JSON reports observed auxiliary games in the preceding 7/14 days, time since the latest observation, and whether a recent observation exists. All target UTC-day fixtures and subsequent fixtures are withheld. Missing or stale observations are `null`, **not evidence of no matches**. Rest means time since the latest stored auxiliary observation, not verified recovery time. Coverage is explicitly partial and these are separate from European workload; do not add overlapping future imports without event deduplication.

```bash
python -m bbtahmin baglam-topla
python scripts/evaluate_club_context.py
```

The score-model admission report requires at least 50 covered earlier training games and 20 covered preceding-season validation games before a feature experiment is even eligible. Current data fails that preliminary gate in all leagues: there is no covered training history. ECW has 12 covered 2025–26 test games, and FEC has three covered partial 2026–27 games. **These rows currently provide diagnostics only, not a claimed score-model improvement.** Collect older, broader national-league histories before testing this feature group against identical baseline fixtures. Unexpected page layouts, ambiguous identities, future finished fixtures, conflicting dates and gender mismatches fail explicitly.

## Validation and next step

163 offline tests pass, including target/future outcome mutation, current-month estimator exclusion, previous-season-only policy selection, official-page parsers, time-zone conversion, gender checks, missingness and default-model compatibility. Actual CLI and MCP checks are recorded alongside research outputs.

Next collect additional historical club/league seasons and genuine pre-tipoff roster/injury snapshots. Evaluate them with identical chronological folds and report winner accuracy, log loss/Brier and score MAE together. Preserve failed experiments and keep the default stable until independent future evidence supports a change.
