# Historical data expansion — 2026-10-22

The persisted game archive grew from **26,200 to 54,808 games (+28,608; 109.2%)**.
All original game IDs, dates, teams and final scores were preserved. The audit
checks this against the original dataset, not just the collection log.

| League | Before | After | Earliest season |
|---|---:|---:|---|
| NBA | 15,482 | 41,620 | 1993–94 |
| EuroLeague | 5,100 | 6,664 | 2000–01 |
| EuroCup | 3,965 | 4,871 | 2002–03 |
| Australian NBL | 1,653 | 1,653 | 2015–16 |

These counts describe available records, not a claim of complete season coverage.
Per-season counts are in [genislet_kapsam.csv](kanit/genislet_kapsam.csv).

## Additional observations

| File | Rows | Contents |
|---|---:|---|
| `data/nba_takim_istatistik.parquet` | 82,912 | Team shooting, rebounds, assists, steals, blocks, turnovers and fouls |
| `data/nba_oyuncu_istatistik.parquet` | 1,071,430 | Player box-score rows, including recorded DNP/zero-minute observations |
| `data/nba_mac_baglami.parquet` | 41,578 | Source game ID, UTC start, venue, neutral site and number of periods |
| `data/avrupa_takim_istatistik.parquet` | 2,246 | European team box-score details |
| `data/avrupa_oyuncu_istatistik.parquet` | 26,448 | European player box-score details |
| `data/avrupa_sutlar.parquet` | 178,177 | Shot coordinates, shot type, points, clock and score |
| `data/avrupa_olaylar.parquet` | 625,187 | Structured play-by-play codes, period, clock, player/team and score |

The established NBA box-score feature files now contain **82,914 team rows** and
**855,193 positive-minute player rows**. Numeric IDs such as `123.0` are normalized
to `123` before merging; otherwise a single athlete could be counted twice.

NBA archives are the same sportsdataverse/ESPN release source already used by
this project: [schedules](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_nba_schedules),
[team boxes](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_nba_team_boxscores),
[player boxes](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_nba_player_boxscores).
European results come directly from the EuroLeague API. Additional European
observations come from the [euroleague-open-data snapshot](https://github.com/McNews11/euroleague-open-data);
all 1,123 imported games matched the official result and both team codes.
The snapshot checksum and import counts are in [avrupa_detay.json](kanit/avrupa_detay.json).

## Quality controls

- Collection is additive and restartable. A failed source cannot erase existing seasons.
- Current-season responses refresh instead of remaining permanently cached.
- Foreign-season records, All-Star teams and invalid NBA scores are rejected.
- Five source conflicts were quarantined: one disagreeing score and four likely
  duplicate games with a shifted source date. Existing results won each conflict.
- Four zero-score results remain in the factual archive, including administrative
  scorelines; training and prediction exclude them as ordinary played games.
- Detail rows must reference a retained game. Game and detail keys are unique.
- NBA game duration accounts for multiple overtime periods when the source records them.
- Shot/event tables contain postgame facts. They are **not same-game pregame features**.
  Rich new fact tables are retained for future chronological feature experiments;
  they are not all automatically enabled in the current model.

The complete persisted-file checksums and counts are in [dataset_audit.json](kanit/dataset_audit.json).

## Prediction checks and measured results

Live training previously included current-season results while calibrating against
the preceding season. Training now ends before the validation season, matching
the chronological backtest. Historical queries also exclude future parameter folds,
future model-selection results and future team activity.

We compared the score model on **10,089 identical games** in the last five completed
seasons (2021–22 through 2025–26). Elo/EWMA parameters were held identical across
variants for each fold. Retrospective player-absence labels and newly imported
shot/player statistics were excluded, so this is a focused data/history experiment,
not a replacement for the seven-model benchmark.

| League | Original log loss | Expanded history log loss | Experimental adaptive history |
|---|---:|---:|---:|
| EuroLeague | 0.61557 | 0.61554 | 0.61533 |
| NBA | 0.61946 | 0.61967 | 0.61950 |
| NBL | 0.66102 | 0.66102 | 0.66785 |
| EuroCup | 0.60694 | 0.60560 | 0.60666 |

Lower is better. Results are mixed; there is **no established overall accuracy
increase or statistical superiority**. NBA total-score MAE improved from 14.721 to
14.676 points, while win-probability log loss did not improve. Adaptive history
selection tests Ridge alpha and 3/5/10/all earlier training seasons against the
preceding validation season; it remains an **experiment, disabled by default**
because it harmed NBL and did not consistently improve the other leagues.

The earlier results in `docs/sonuclar.md` and `docs/kanit/toplam.csv` are retained
historical benchmark snapshots. They have not been relabeled as results for the
expanded dataset. See [folds](kanit/data_expansion_model/folds.csv),
[summary](kanit/data_expansion_model/summary.csv) and [method](kanit/data_expansion_model/method.json).
Two hypothetical prediction smoke checks cover EuroLeague and NBA; they do not
assert that those matchups are scheduled fixtures.

## Reproduce

From the repository root, after the normal project installation:

```bash
python -m bbtahmin genislet
python -m bbtahmin genislet --ligler NBA --baslangic 1993 --bitis 2026
python -m bbtahmin genislet --ligler E U --yalniz-skor
python scripts/audit_dataset.py
python -m pytest -q
```

For the fixed original comparison, extract the original archive from commit
`a4cbbef9908b7ef590f0896498786a8fdcc8adff`, then run:

```bash
git show a4cbbef:data/maclar.parquet > /tmp/original-games.parquet
PYTHONPATH=src python scripts/audit_dataset.py --baseline /tmp/original-games.parquet
PYTHONPATH=src python scripts/evaluate_expansion.py --baseline /tmp/original-games.parquet
```

The optional European detail importer needs `duckdb==1.4.1` and the database
snapshot described in its manifest. It imports factual fields only and verifies
the game join before writing any detail rows:

```bash
python -m pip install duckdb==1.4.1
PYTHONPATH=src python scripts/import_europe_details.py --database /path/to/euroleague.duckdb
```

Future work: evaluate genuinely pregame injury snapshots, lagged shooting profiles,
and player role changes. The existing retrospective absence feature still has the
availability limitation documented in the README; its backtest is not proof of
achievable live injury-report performance.
