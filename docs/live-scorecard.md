# Live forecast scorecard

## Purpose

The live forecast scorecard evaluates immutable, checksum-verified frozen forecasts against final results already stored in the repository's local ledgers. It runs offline using existing ledger files only, without contacting external data providers or modifying any ledger.

It covers two sports from one shared calculation and renders both a machine-readable JSON file (`spec: "live-scorecard-v1"`) and a Markdown summary:

- **Basketball** — class order `home`, `away`.
- **Football** — class order `home`, `draw`, `away`.

## How to run

Run from the repository root:

```bash
python scripts/live_scorecard.py
```

`scripts/live_scorecard.py` adds `src/` to `sys.path` and invokes `bbtahmin.live_scorecard.build_scorecard` and `bbtahmin.live_scorecard.markdown`, writing outputs into `docs/kanit/live_scorecard/`.

## Inputs and outputs

### Inputs

- **Basketball settlement checks:** `data/basketball_ledger/check_*.json` (`spec: "daily-research-v1"`).
- **Basketball frozen forecasts:** `data/basketball_ledger/forecasts/*.json` (`spec: "prospective-v1"`), plus any JSON files under `data/argentina_ledger/forecasts/` and `docs/kanit/prospective/` referenced by a settlement batch's `record` path in `check_*.json`.
- **Football frozen forecasts:** `data/football_ledger/forecasts/*.json` (`spec: "football-prospective-v1"`).
- **Football daily report:** `data/football_ledger/latest.json` (`spec: "football-daily-v1"`, optional if absent).

### Outputs

- `docs/kanit/live_scorecard/scorecard.json` — JSON evaluation report (`spec: "live-scorecard-v1"`), containing `data_cutoff_utc`, `definitions`, and `sports` (`basketball`, `football`).
- `docs/kanit/live_scorecard/scorecard.md` — Markdown tables rendered from the same report object.

## Definitions

All definitions below follow `src/bbtahmin/live_scorecard.py` and the `Definitions` section of `docs/kanit/live_scorecard/scorecard.md`:

- **Cohort:** One game per league and event ID, using the earliest checksum-verified frozen forecast. A timezone-aware start timestamp must be present and strictly later than the freeze time (`frozen_at < start < known_at`). Basketball finals are joined by forecast checksum (`forecast_sha256` / `payload_sha256`) and fixture identity (`event_id`, `home`, `away`) across saved settlement checks, including checks that reference earlier Argentina and prospective forecast records. Football uses `publisher_final` entries from the saved daily report joined to immutable forecasts by fixture identity and freeze time (`recorded_at_utc`). Community publisher finals lack official verification. Football finals with date-only kickoff evidence (missing `verified_start_utc`) and matches flagged for `fixture_review` are excluded.
- **Cutoff:** Latest saved settlement check timestamp (`checked_at_utc`) used, with each sport's cutoff reported separately. Basketball includes per-record check timestamps (`settlements[*].checked_at_utc`), which can follow the report's start time.
- **Accuracy:** Fraction of games where the highest-probability class occurred. Ties break in class order (`home`, `away` for basketball; `home`, `draw`, `away` for football).
- **Log loss:** Mean negative natural log of the realized class probability, floored at `1e-15`.
- **Brier:** Mean squared error of the home-win probability for basketball, `(p_home − y_home)²`. Football sums the squared probability errors over `home`, `draw` and `away` before averaging.
- **Confidence intervals:** 95% Wilson score intervals for accuracy. Log loss and Brier use the 2.5th and 97.5th percentiles of 2,000 bootstrap samples of games with replacement (`NumPy` `default_rng` seed `20261124`, reset per cohort). Games are the resampling unit.
- **Baselines:**
  - **Always home (`always_home`):** Assigns probability `1` to `home` and `0` to every other class.
  - **Expanding league rate (`expanding_rate`):** Per-league class counts from eligible ledger finals known strictly before each forecast was frozen (`known_at < frozen_at`). Adds one prior count per class, giving a uniform forecast at cold start. Basketball uses the earliest saved final capture time (`captured_at`). Football uses the saved report's check time (`checked_at_utc`) because it has no per-game final observation times.
  - **Market (`market`):** Uses only complete decimal odds strictly greater than `1` from the frozen prediction (`decimal_odds` by class, or `oran_ev` and `oran_dep` for basketball). Normalizes reciprocals to sum to one. When odds are present, both the `Market` row and its companion `Model on market games` row (`model_same_games`) cover the same odds-available games; otherwise the row is reported as `Market (no market data)` with `n = 0`.
- **Calibration:** Grouped by highest forecast probability in left-closed 10 percentage-point bins, with `100%` included in the last bin (`90%–100%`). Observed frequency is the fraction whose top pick occurred. Bins begin at `50%` for basketball (`50%–60%` through `90%–100%`) and `30%` for football (`30%–40%` through `90%–100%`) to cover all 1X2 favourites.
- **Football top picks vs. actual outcomes:** For football, the scorecard also tabulates per-class `top_pick_n`, `top_pick_rate`, `actual_n`, and `actual_rate`.

## Current snapshot summary

From `docs/kanit/live_scorecard/scorecard.md` (data cutoff UTC `2026-11-23T18:40:38.014012+00:00`):

- **Basketball** (ledger cutoff `2026-11-23T18:39:45.724905+00:00`, `n = 360` across `ABA`, `ARG_LNB`, `E`, `ECW`, `FEC`, `KBL`, `UKR`):
  - **Model:** Accuracy `68.6% [63.6%, 73.2%]`, Log loss `0.5888 [0.5512, 0.6309]`, Brier `0.2036 [0.1871, 0.2223]`.
  - **Always home:** Accuracy `57.8% [52.6%, 62.8%]`, Log loss `14.5830 [12.8561, 16.3100]`, Brier `0.4222 [0.3722, 0.4722]`.
  - **Expanding league rate:** Accuracy `57.5% [52.3%, 62.5%]`, Log loss `0.6914 [0.6744, 0.7103]`, Brier `0.2485 [0.2404, 0.2571]`.
  - **Market:** `no market data` (`n = 0`).
- **Football** (ledger cutoff `2026-11-23T18:40:38.014012+00:00`, `n = 149` across `DE1`, `EN1`, `EN2`, `ES1`, `FR1`, `IT1`, `NL1`, `PT1`, `TR1`, with `TR1` at `n = 0`):
  - Excluded `126` publisher finals without a verified kickoff timestamp (`DE1 15, EN1 16, EN2 19, ES1 7, FR1 11, IT1 27, NL1 15, PT1 11, TR1 5`).
  - **Model:** Accuracy `55.7% [47.7%, 63.4%]`, Log loss `0.9801 [0.9184, 1.0421]`, Brier `0.5821 [0.5381, 0.6267]`.
  - **Always home:** Accuracy `44.3% [36.6%, 52.3%]`, Log loss `19.2397 [16.4581, 22.0214]`, Brier `1.1141 [0.9530, 1.2752]`.
  - **Expanding league rate:** Accuracy `44.3% [36.6%, 52.3%]`, Log loss `1.0986 [1.0986, 1.0986]`, Brier `0.6667 [0.6667, 0.6667]`.
  - **Market:** `no market data` (`n = 0`).
  - **Top picks vs. actuals (Total):** `home` `95` (`63.8%`) vs `66` (`44.3%`); `draw` `0` (`0.0%`) vs `31` (`20.8%`); `away` `54` (`36.2%`) vs `52` (`34.9%`).

## Limitations

- **Uniform expanding-rate baseline in football:** Football has no per-game final observation timestamps, so `expanding_rate` uses the single saved report's `checked_at_utc` as `known_at`. Because every forecast in that snapshot was frozen before `checked_at_utc`, all football forecasts receive uniform expanding rates (`1/3` per class; Log loss `1.0986`, Brier `0.6667`, with accuracy ties broken to `home`).
- **No market data:** Complete decimal odds are absent from the frozen forecasts in the current ledger snapshot (`Market (no market data)`, `n = 0` for both sports), so no market benchmark is available.
- **Matches without verified start timestamps are excluded:** Only games with a timezone-aware start strictly after the freeze are scored. In football, finals with date-only kickoff evidence (missing `verified_start_utc`) and matches flagged for `fixture_review` are excluded (`126` publisher finals excluded in the current snapshot, leaving `TR1` at `n = 0`).
- **Unverified football publisher finals:** Football relies on community `publisher_final` entries from `data/football_ledger/latest.json`, which lack official verification.
- **Small per-league samples:** Individual leagues have small counts (for example `PT1` `n = 4`, `DE1` `n = 12`, `UKR` `n = 23`), resulting in wide 95% confidence intervals.

## How not to read the results

- **No profitability or market-beating claim:** Beating naive baselines (`Always home` or `Expanding league rate`) is not evidence of beating betting markets or generating profit. Market comparison is currently unavailable (`n = 0`).
- **Not a general performance guarantee:** Point estimates on small per-league cohorts or sparse calibration bins have wide uncertainty and should not be extrapolated as stable long-run accuracy.
- **Not proof of complete coverage or official verification:** Excluded matches without verified kickoff times and unverified community publisher finals mean the scored cohort is a filtered subset of ledger activity.
