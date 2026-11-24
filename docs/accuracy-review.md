# Accuracy review (October 2026)

Why forecasts look weak, what was changed, and the measured effect. All comparisons use the same data, the same seasons and each module's own chronological walk-forward; the old numbers come from the previous commit run on the identical archive.

## Diagnosis

- **The live sample is too small to judge.** 25 settled basketball forecasts, 16 correct (64%). The 95% interval is roughly 45–83%.
- **Early season is the model's weakest period.** In the KBL walk-forward the first 30 games of a season hit 52%, games after the 180th hit 64%. Early-season probabilities are also overconfident (59% stated, 52% observed).
- **The ceiling of a scores-only model is low.** EuroLeague 2021–26: score model 64.65% vs "home always wins" 63.16%. Market odds, rosters, transfers and injuries are not model inputs. No historical odds archive is checked in, and odds/source hosts are not reachable from the evaluation environment.

## Changes

1. **Extended basketball features, selected per league on the preceding season** (`ozellik.select_columns`): season phase (`min_games_log`, `early`, `elo_diff_early`, `rmarj_12_early`), shrunk season-to-date margin, home-only/road-only form and previous-season margin. They help some leagues and hurt others (FEC, VTB, ABA, TR_BSL in exploratory tests), so each fold picks base or extended columns using only its validation season's log loss. Frozen shadow pipelines keep the base columns.
2. **Football default model is now the opponent-adjusted candidate** (`football/challenger.DEFAULT_VARIANT='opponent'`) for daily runs, CLI and MCP. `--model baseline` is still available.
3. **Windows-style ledger paths** (`data\...`) now resolve in the local application on Linux/macOS. 97 of 589 settlement records were affected; their frozen predictions previously did not display.

## Measured effect

Core leagues, `backtest --ilk-test 2021` (score model `skor`; test seasons 2021-22 to 2026-27 partial):

| League | Games | Log loss before → after | Accuracy before → after |
|---|---:|---|---|
| EuroLeague | 1,751 | 0.6169 → 0.6167 | 64.65% → 64.65% |
| EuroCup | 1,034 | 0.6101 → 0.6088 | 65.96% → 65.86% |
| NBA | 6,608 | 0.6199 → 0.6194 | 65.78% → 66.03% |
| NBL | 874 | 0.6660 → 0.6620 | 59.50% → 60.07% |

Separate league modules, each module's own `walk_forward` (selected/default policy):

| League | Games | Log loss before → after | Accuracy before → after |
|---|---:|---|---|
| ECW | 271 | 0.5764 → 0.5657 | 71.96% → 70.11% |
| FEC | 275 | 0.6130 → 0.6130 | 67.27% → 67.27% |
| VTB | 283 | 0.4257 → 0.4257 | 81.27% → 81.27% |
| ABA | 2,663 | 0.5263 → 0.5269 | 73.15% → 73.30% |
| UKR | 584 | 0.5172 → 0.5168 | 72.26% → 72.60% |
| TR_BSL | 2,014 | 0.5637 → 0.5643 | 71.95% → 71.85% |
| ARG_LNB | 865 | 0.6370 → 0.6370 | 64.74% → 64.74% |
| KBL | 1,872 | 0.6602 → 0.6604 | 61.65% → 61.70% |
| JP_B1 | 2,219 | 0.5877 → 0.5834 | 68.63% → 69.09% |
| JP_B2 | 1,260 | 0.5699 → 0.5699 | 70.32% → 70.32% |

Football (existing same-cohort comparison, 3,973 finals in 2025–26, [details](football-ensemble.md)): 1/X/2 accuracy 47.80% → 49.18%, multiclass log loss 1.02993 → 1.01780; lower log loss in 14 of 17 leagues.

**The basketball gain is small:** about +0.1 accuracy points pooled and slightly lower log loss, within noise for most single leagues. The football default change is the largest measured improvement.

## Tried and rejected

| Idea | Result |
|---|---|
| Phase-aware Platt calibration (score × early-season term) | Worse log loss in every league tested |
| Carrying last season's scoring form instead of resetting it | Mixed, worse in EuroCup |
| Resetting teams returning after 2+ seasons; new teams starting below 1500 Elo | Mixed, worse in EuroCup, ECW, Japan |
| Carrying EuroCup ratings into EuroLeague (and back) | EuroLeague slightly better, EuroCup worse (0.6101 → 0.6144); not adopted to avoid fitting test seasons |

## Closing odds (NBA), measured after the first PR

NBA closing moneylines for 2014-15…2022-23 were collected with the repository's existing SBR collector (`topla --sbr-izni`; the site's terms ask for written permission, and the file `data/oranlar.parquet` is deliberately **not committed**). Walk-forward, 2017-18…2022-23, 6,758 games with odds:

| Probability source | Log loss | Accuracy |
|---|---:|---:|
| Model (score model, extended features) | 0.6277 | 64.84% |
| No-vig closing market | 0.6070 | 67.15% |
| Model + market as a regression feature | 0.6094 | 66.79% |
| Logistic stack of both | 0.6087 | 66.84% |
| Logit blend, 10% model / 90% market | 0.6069 | 66.91% |

The market beats the model in every one of the six seasons. The model adds almost nothing on top of the closing line. `odds.market_blend` and a "Birleşik" line in `tahmin` (NBA only, when odds are supplied) implement the 10/90 blend; the frozen default forecast is unchanged. Limits: closing lines from one archive; Iddaa odds for other leagues have higher margins and are not validated; no other league has a historical odds archive.

## Tried: roster continuity (already in the repo)

`k_kadro_diff` / `k_kadro_ort` (minute share of last season's rotation) were already implemented and previously rejected. Re-tested on top of the extended features: EuroLeague 0.6169 → 0.6174, EuroCup 0.6105 → 0.6114, NBA 0.6193 → 0.6192 log loss. Not adopted.

## Not done: what would move accuracy materially

- **Odds for leagues other than the NBA.** Only the NBA has a historical odds archive here; Iddaa snapshots cover only recent days.
- **Roster continuity and transfers**, especially for European pre-season and early rounds.
- **Player availability** (injuries, rest) as a validated model input, not only display context.
