# Argentina Liga Nacional

The senior men's Liga Nacional is independently supported as `ARG_LNB`. Other Argentine divisions, Liga Argentina, women's competitions, youth and Super 20 are excluded. NBA remains a separate workflow and archive.

## Sources and use

- Current fixtures: the publicly used fixture handler on [the official Liga Nacional site](https://www.laliganacional.com.ar/laliga/fixture). Scores must also have a match page explicitly marked Finalizado; same Buenos Aires local-day scores are withheld.
- Historical seasons beginning in 2022: [Pick And Roll's LNB archive](https://pickandroll.com.ar/pnr-fixture/?comp=LNB&season=2022-23). This is a publisher source, not an official archive. Invalid final scores are quarantined with names, date and source in the collection report. Historical dates have day precision and unknown publication times; they cannot settle exact-time prospective forecasts.
- RealGM returned HTTP 403 during source verification. It is not used. The official handler did not return earlier-season history. Full schedule coverage is unverified.

```sh
python -m bbtahmin ulke-topla --ligler ARG_LNB --baslangic 2022
python scripts/evaluate_regional.py --ligler ARG_LNB --cikti docs/kanit/argentina_models
python -m bbtahmin gunluk --ligler ARG_LNB --guncelle --saat 168 --cikti rapor/daily
python -m bbtahmin app --cikti rapor/daily
python -m bbtahmin tahmin "Argentino J. - Quimsa" --lig ARG_LNB --tarih 2026-10-24T21:00:00-03:00
```

Use the actual confirmed fixture time for manual prediction. The browser app exposes an Argentina league filter, independent refresh, pending/final cards and existing JSON/CSV/Markdown exports. CLI and read-only MCP tools route the league to the same independent model. Exact team aliases include Argentino J., Atenas Cordoba and Lanus. Unknown names fail explicitly instead of matching another division.

## Model and persistence

Only `data/competitions/ARG_LNB.parquet` trains this league. Earlier seasons train the existing score/logistic/Elo models; the prior season calibrates and selects a variant, with target-day outcomes withheld. The backtest stores all candidates on the same cohort; it is retrospective, not prospective success evidence. No Argentine accuracy increase is presumed.

Teams without earlier-season observations in this league carry a blocking promoted-team diagnostic, even if they have several recent results. This is relevant to Lanus and Racing: numerical estimates are experimental and do not pass the diagnostic selection gate. Rosters, injuries and lower-division matches have not been collected. Nominal home court may differ from the actual venue.

Official provider tokens determine fixture identity; a date change retains the event identity and causes the existing immutable forecast to be retained for review. Conflicting saved scores fail rather than overwriting history. Source failure preserves the old archive and fixture snapshot and is visible in the refresh report. Daily and weekly refresh include Argentina; historical backfill starts in 2022.

## Evidence

- `docs/kanit/competitions/ARG_LNB_collection.json`: actual counts by season, source hashes, rejected rows and errors.
- `docs/kanit/argentina_models/summary.csv`, `folds.json`, `manifest.json`: chronological accuracy, log loss, score/total errors, selection and dataset/code hashes.
- `data/argentina_ledger/check_20261023T202439944423Z.json`: frozen pending forecasts and separate eventual result checks. No completed prospective games means no prospective accuracy.
- `tests/test_argentina.py`: aliases, clock conversion, postponed identities, final-status embargo, bad-score quarantine, conflict/source-failure preservation, day-only settlement rejection, separate prediction route and promoted-team diagnostic.
- `scripts/visual_smoke.cjs`: actual Chromium using deterministic API fixtures, eleven league filters and selected/empty states at desktop 1440px and mobile 390/320px. This verifies rendered layouts, not live provider connectivity.

## Measured first run (23 October 2026 UTC)

The archive contains **1,718 valid finals / 23 clubs**: 428 (2022–23), 431 (2023–24), 429 (2024–25), 395 (2025–26), and 35 (current 2026–27). One publisher result, Zárate–Instituto 0–20 on 23 January 2025, is excluded from statistical training; its administrative/forfeit status is unverified. The official listing contains 48 non-final/unverified fixtures, including dates beyond the seven-day forecast horizon.

On 824 completed-season target games (2024–25 and 2025–26), the selected prior-season policy gets **537/824 (65.17%)**, against a home-team baseline of **61.53%**. Log loss is 0.636758; mean team-score error is 8.12 points and total-score error 12.78. The current partial season is weaker: **18/35 (51.43%)**, below its home baseline of 57.14%. This does not establish improved current-season accuracy. The current policy chooses the equal ensemble using only the previous season; no candidate was promoted based on these current outcomes.

Ten future fixtures were frozen before tipoff; three pass the existing probability/diagnostic filters, and all ten remain pending. Argentino–Quimsa has Quimsa 75.16%, expected score 75.8–84.6 and total 160.4. Atenas–Lanus has Atenas 54.6%, expected score 82.3–79.9 and total 162.2, with a blocking missing-prior-league-history diagnostic for Lanus. These are uncertain model estimates; no prospective accuracy is available. The daily command reuses the checked-in original Argentina ledger even when a new local output directory is selected.

## CI and immutable-ledger verification (24 October 2026)

The final published-forecast regression test originally patched a nonexistent
`daily.tahmin_et` attribute. The daily runner imports the function locally from
`bbtahmin.tahmin`, so the test now patches that real dependency. Its guard still
raises if prediction is attempted; it is not disabled or weakened. The test also
checks that all ten original forecast files remain byte-for-byte unchanged
after opening a new output ledger. No model parameters, source data or frozen
forecasts were changed by this repair.

Local validation on the branch including the latest main: **289 Python tests
and 9 DOM UI tests passed**. The previous hosted failure is retained at
[run 40019201245](https://github.com/Bluetwinklez/basketbol-tahmin/actions/runs/40019201245);
new hosted checks must pass before merging PR #10.
