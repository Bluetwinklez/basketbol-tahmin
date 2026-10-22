# Runtime verification — 2026-10-22

The tested GitHub commit is `39659689dde6c867ee36004df1acbc827402b99e`.
Its Git tree (`c51dcd0a6576f19c1bfab483e5707d37a5981567`) matched the local source/data checkout.
GitHub Actions [run 39773281849](https://github.com/Bluetwinklez/basketbol-tahmin/actions/runs/39773281849) succeeded; the local pinned-dependency suite also passed **127 tests**.

## Fresh model execution

Seven models were retrained and evaluated from the historical dataset:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m bbtahmin backtest --ilk-test 2025 --cikti docs/kanit/runtime_validation
python -m pytest -q --junitxml=docs/kanit/runtime_validation/tests.xml
```

On Windows set the two environment variables separately, or omit them if thread limits are unnecessary.
The fresh run produced 15,932 prediction rows: seven models across 2,276 fixtures, including partial 2026–27 results. All rows matched the corresponding archived fixture/model/outcome; maximum absolute probability difference was **2.04e-14**. No current-game participation features were used. Environment versions, parameters, input and prediction fingerprints are retained in `manifest.json`; deterministic gzip stores the unmodified prediction CSV.

The following **completed 2025–26** results use a model selected only from evaluation seasons **before** 2025–26, rather than choosing the best model after observing the season:

| League | Previously selected model | Correct / games | Accuracy |
|---|---|---:|---:|
| NBA | Score | 897 / 1,322 | 67.85% |
| EuroLeague | Score | 250 / 402 | 62.19% |
| EuroCup | Score | 130 / 195 | 66.67% |
| NBL | MOV Elo | 114 / 179 | 63.69% |
| Combined | Per-league prior selection | 1,391 / 2,098 | 66.30% |

Partial 2026–27 data is excluded from this table. Individual model metrics, parameters and all game probabilities are included here; `verification.json` records matching checks and selected results.

## Five-season selection policy check

The existing prediction archive was independently re-scored after checking its decompressed SHA-256 against the benchmark manifest. For each 2021–22 through 2025–26 target season, `en_iyi_model(league, sezon=season)` selected a model only from earlier evaluation seasons. The first season falls back to MOV Elo because this verified evaluation begins in 2021–22.

| League | Correct / games | Prior-season selection accuracy |
|---|---:|---:|
| NBA | 4,347 / 6,605 | 65.81% |
| EuroLeague | 1,092 / 1,690 | 64.62% |
| EuroCup | 638 / 970 | 65.77% |
| NBL | 488 / 824 | 59.22% |
| Combined | 6,565 / 10,089 | 65.07% |

`historical_summary.json` lists every season's chosen model and separately includes fixed-current-model diagnostics. These differ from selecting the model using only earlier seasons: for example, the NBL fixed ensemble has 61.04% on the same five-season games, whereas the chronological selection policy achieved 59.22%. They must not be presented as the same strategy.

## Application and unsupported-fixture checks

- A new three-request Iddaa bulletin refresh succeeded and returned 134 basketball events at capture time.
- A real bulletin event, Miami–Detroit (`3235425`, scheduled `2026-10-24T00:00:00Z`), produced a score-model forecast with home probability `0.471624721971028`. This is a **pregame** estimate for an upcoming fixture, not a live prediction or an observed success. The artifact and dataset checks both passed; see `live_smoke.json`.
- The user's screenshot showed live Chinese CBA fixtures Jilin–Xinjiang (16–15) and Beijing–Shenzhen (22–15). Team resolution correctly rejected both. The project has **zero CBA games and no in-play model**; no model probabilities were generated. These screenshot scores were not verified against a live feed; see `unsupported_live_fixtures.json`.

Historical accuracy is not a live record. Supporting these CBA games would require CBA training history plus a separately evaluated in-play model using score, period, remaining time and other available game state.
