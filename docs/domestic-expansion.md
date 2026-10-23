# Turkish BSL and Ukrainian SuperLeague expansion

The daily application supports 10 competitions. This release adds **3,520 distinct finished games** in two separate senior men's archives: **2,523 Turkish BSL results** (2016–17 through the partial 2026–27 season) and **997 Ukrainian SuperLeague results** (2020–21 through partial 2026–27). These are additional archives, not replacement rows in the 54,808-game core or the 12,850-game Asian dataset.

## Use

```sh
python -m bbtahmin app
python -m bbtahmin gunluk --ligler UKR TR_BSL --saat 168 --guncelle
python -m bbtahmin ulke-topla --ligler UKR TR_BSL --baslangic 2020
python scripts/evaluate_regional.py --ligler UKR TR_BSL --cikti docs/kanit/domestic_models
```

Existing stored history is preserved when refreshing the active season. League filters, team-name matching, Iddaa group mapping, quality checks, CLI predictions and read-only MCP tools include the new competitions. Each league fits its own model from its own observations; it does not inherit NBA or ABA fitted weights. Regional CLI fitting limits native numerical threads to avoid oversubscribing the local computer.

## Sources and limitations

Ukraine uses the [FBU senior men's calendar](https://fbu.ua/statistics/league-224/calendar), its publicly advertised BasketHotel widget and full-season XLSX results/schedule exports. The league, season, header, team IDs, positive final scores and unique game identities are validated. Export game numbers can repeat in reverse fixtures; identity includes both teams. Federation local time is interpreted as Europe/Kyiv, including daylight saving changes. Same-day scores and in-progress schedule scores are not imported as finals. Wartime centralized venues make nominal home court an uncertain proxy. Ambiguous older season identifiers are excluded.

Turkey uses [TBLStat](https://bsl.tblstat.net/) for historical numerical results and dated club schedules. The season results listing omits dates for normal-season games: these games enter only after their exact game IDs are matched to club schedule dates. Dates seen from both clubs must agree. These historical records retain **day precision**, not invented tipoff times. Current fixtures and 32 prior results were captured from beIN's public BSL fixture/standings pages using an explicit cross-source team-ID map. Unknown provider identity 12998 is deliberately unmapped. Current standings may expose only a rolling window. The latest beIN refresh returned no valid structured fixture data; the source error is recorded and the previously captured fixture snapshot is retained. It is not represented as a successful refresh. See [Turkey collection evidence](kanit/competitions/TR_BSL_collection.json) and [Ukraine evidence](kanit/competitions/UKR_collection.json).

Day-precision Turkish results cannot automatically settle timestamped prospective forecasts. Such forecasts remain pending until compatible, source-confirmed final evidence exists. Neither source establishes complete historical coverage or historical publication times. Provider endpoints can change.

Swedish SBL is **not enabled** in this release. The accessible club feed returned only Södertälje games, and the federation's historical embed was unavailable. A club-only cohort is not labeled full-league training data.

## Chronological evaluation

Training uses earlier seasons; the preceding season's first UTC-day half calibrates score probabilities and its second half selects the candidate with lowest log loss. Target-season outcomes never choose that season's candidate. Within-season features exclude same-day outcomes. All candidates are evaluated on identical target games. Earliest seasons without enough preceding history are excluded. These tests use retrospectively collected data; they are not prospective success rates.

| League / cohort | Prior-selected policy | Fixed score | Fixed Elo | Fixed ensemble | Always home |
|---|---:|---:|---:|---:|---:|
| Ukraine completed seasons | 402/554 (72.56%) | 403/554 (72.74%) | 391/554 (70.58%) | 402/554 (72.56%) | 51.08% |
| Turkish BSL completed seasons | 1,420/1,974 (71.94%) | 1,423/1,974 (72.09%) | 1,416/1,974 (71.73%) | 1,428/1,974 (72.34%) | 60.03% |
| Ukraine current partial season | 13/21 (61.90%) | See full report | See full report | See full report | 52.38% |
| Turkish BSL current partial season | 23/32 (71.88%) | See full report | See full report | See full report | 65.63% |

The policy is not uniformly better than fixed alternatives. Broader support is established; a general increase in accuracy is not. Partial cohorts of 21 or 32 games are particularly small.

| Completed-season score errors | Mean team absolute error | Total absolute error | Margin absolute error | Nominal total 80% interval coverage |
|---|---:|---:|---:|---:|
| Ukraine | 8.56 points | 13.12 points | 10.28 points | 78.70% |
| Turkish BSL | 8.53 points | 13.73 points | 10.04 points | 79.69% |

Score errors use the common score model; winner variants do not change them. Interval coverage is empirical across this historical cohort, not a conditional guarantee. [All candidate metrics](kanit/domestic_models/summary.csv), [fold selections](kanit/domestic_models/folds.json) and [source/data fingerprints](kanit/domestic_models/manifest.json) are retained with per-game predictions.

## Actual prospective run and validation

A saved-source run recorded **12 future forecasts**: five Ukraine and seven Turkey fixtures on 24–25 October 2026. Five passed the configured diagnostics/probability filter. **All 12 are pending; observed winner accuracy is unavailable.** The five Ukrainian forecasts from the earlier run were reused without rewriting. The original two EuroLeague forecasts and the previous ABA/ECW/FEC forecasts remain unchanged. [Actual run and separate outcome/error columns](kanit/domestic_runtime/latest.md).

Validation: **258 Python tests and 8 UI tests passed**. Added cases cover repeated FBU game numbers, reverse fixtures, timezone conversion, mixed leagues, duplicate identities, same-day/live score exclusion, dated normal-season recovery, unknown team mappings, independent model routing, and preserving prior data during provider failure. Existing local-server and browser-DOM tests also pass. No new rendered-browser visual verification or public hosting deployment is claimed.
