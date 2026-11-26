Türkçe: [README.tr.md](README.tr.md)

# Basketball and Football Pregame Research

A Python research package (`bbtahmin`) for pregame basketball and football probabilities, score/goal margins and totals. It combines reproducible historical archives, chronological walk-forward evaluation, an experimental Iddaa bulletin reader, a local browser app and a read-only local MCP server.

## Scope: leagues and models

- **Core basketball (54,808 stored games; the separate Asian archives contain 12,850 results):** NBA, EuroLeague (`E`), EuroCup (`U`) and Australian NBL. Models: home baseline, Elo, MOV Elo, logistic regression, gradient boosting, score regression and ensemble, evaluated chronologically with prior-season parameter/model selection and per-league extended feature selection. Retrospective player-absence features and four-factor/shooting profiles are disabled by default.
- **Additional basketball archives (separate models):** Chinese CBA (2,386 games, plus experimental manual regulation live-state projection), EuroCup Women (`ECW`, 678), FIBA Europe Cup men (`FEC`, 651), VTB men (860), ABA League senior men (3,023), Turkish BSL (2,523), Ukrainian SuperLeague (997), Argentina Liga Nacional (`ARG_LNB`) and Asian archives (12,850 distinct finals: KBL 2,549, Japan B1 5,644, Japan B2 3,769, PBA Governors Cup 322, Commissioners Cup 291, Philippine Cup 275).
- **Football (separate workflow):** 62,373 stored community-source finals across 17 European leagues (including Turkish Süper Lig), plus separate historical archives for requested leagues. Predicts regulation 1/X/2, goal totals and both-teams-score probabilities; the opponent-adjusted model is the default (`--model baseline` and `ensemble` remain available).
- **Explicit limits:** Japan 2026–27 B.PREMIER/B.ONE legacy model transfer is blocked until separately validated; unsupported leagues (e.g. Swedish SBL) have no enabled model; betting execution and guaranteed returns are not provided. Current delivery audit and unresolved acceptance criteria: [scope ledger](docs/delivery-scope.md) (see also [docs/screenshot-leagues.md](docs/screenshot-leagues.md)). Screenshot pairings, unknown dates and source verification are tracked separately from model performance.

## Honest performance summary

**More data has not established a general increase in prediction accuracy.** All figures below are retrospective chronological backtests, not live results or betting guarantees; prospective football and recent expansion cohorts remain pending or too small to validate general accuracy.

Fixed-model results on the last five completed core basketball seasons (**2021–22 through 2025–26**, excluding actual-participant absence labels; [docs/kanit/pregame_verified](docs/kanit/pregame_verified)):

| League | Model | Games | Winner accuracy | Log loss |
|---|---|---:|---:|---:|
| NBA | Score regression | 6,605 | 65.80% | 0.61977 |
| EuroLeague | Score regression | 1,690 | 64.62% | 0.61594 |
| EuroCup | Score regression | 970 | 65.88% | 0.60567 |
| NBL | Ensemble | 824 | 61.04% | 0.65857 |

- **Confidence filtering vs. full coverage:** on the same 6,605 NBA games, filtering to ≥70% predicted winner probability yields 79.69% accuracy on 1,684 games (25.50% coverage; [confidence.csv](docs/kanit/pregame_verified/confidence.csv)). This is a subset diagnostic, not overall accuracy.
- **October 2026 accuracy review:** per-league extended basketball features gave small gains (e.g. NBA 65.78% → 66.03%), while promoting the opponent-adjusted football default raised same-cohort 2025–26 1/X/2 accuracy from 47.80% to 49.18% across 3,973 games in 17 leagues ([docs/accuracy-review.md](docs/accuracy-review.md)).
- **NBA closing odds:** On 6,758 matched games (2017–18 through 2022–23), the no-vig market outperformed the score model. The blend fitted on earlier seasons stayed close to the market. See the [market comparison](docs/kanit/piyasa.csv) and [betting simulation](docs/kanit/bahis.csv).
- **NBA odds in the CLI:** Add `@1.65/2.30` to a `tahmin` matchup to see `Piyasa` (no-vig market), `Birleşik` (fixed 90% market, 10% model logit blend), and `Harman` when [fitted coefficients](docs/kanit/harman.json) are available. SBR odds collection via `topla --sbr-izni` requires written permission.
- **Phase 1:** Adds pregame evidence verification, requires a signed manifest for fitted blends, and runs tests on Windows and Linux.
- **Other leagues:** Asian, regional, domestic and CBA retrospective evaluations (and partial-season caveats) are documented in [docs/INDEX.md](docs/INDEX.md). Historical snapshots in [docs/sonuclar.md](docs/sonuclar.md) include legacy absence features and must not be presented as current pregame performance.

## Install

Requires **Python 3.12+** (Node.js 18+ only for the legacy `scripts/fetch.mjs` collector).

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
```

Optional read-only local MCP server extra: `python -m pip install -e '.[mcp]'`.

The checked-in Parquet files can be used immediately. `requirements-lock.txt` records an older Windows environment and contains a machine-specific editable-install path; `requirements.txt` is the portable direct-dependency specification.

## Common commands

```bash
# 1. Open the local browser application (basketball and football boards)
python -m bbtahmin app

# 2. Run daily basketball refresh, freeze pregame forecasts and write rapor/daily/latest.md
python -m bbtahmin gunluk --guncelle

# 3. Inspect a pregame basketball prediction with hypothetical decimal odds
python -m bbtahmin tahmin "BOS - LAL @1.65/2.30" --lig NBA --tarih 2026-10-25T20:00 --json

# 4. Refresh the experimental Iddaa basketball bulletin snapshot (3 read-only GETs)
python -m bbtahmin bulten --guncelle --limit 10

# 5. Refresh active football seasons and freeze 7-day pregame forecasts
python -m bbtahmin futbol daily --refresh --days 7

# 6. Run the offline test suite (or reproduce core backtest via `python -m bbtahmin backtest --ilk-test 2021 --cikti docs/kanit/pregame_verified`)
python -m pytest -q
```

## Data, license and documentation

- **Data:** checked-in Parquet archives live under `data/` and can be used immediately after install. Raw download caches (`data/raw/`), local bulletin history (`data/bulten/`) and local daily reports (`rapor/`) are gitignored. See [data/KAYNAKLAR.md](data/KAYNAKLAR.md) and [docs/data-expansion.md](docs/data-expansion.md) for table schemas and source provenance.
- **License:** repository code is licensed under the [MIT License](LICENSE). Third-party historical data archives retain their upstream licenses and attributions (including CC0, CC BY-SA 4.0 and ODC-By 1.0); see [data/KAYNAKLAR.md](data/KAYNAKLAR.md), [data/football/ARGENTINA-LICENSE-DATOS.md](data/football/ARGENTINA-LICENSE-DATOS.md) and the per-dataset docs.
- **Documentation:** browse the full topic-grouped index at [docs/INDEX.md](docs/INDEX.md). Detailed release history and earlier README sections were moved verbatim to [docs/CHANGELOG.md](docs/CHANGELOG.md).

[Security policy](SECURITY.md) · [Repository security audit](SECURITY_AUDIT.md)
