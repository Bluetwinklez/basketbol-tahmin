[Türkçe](README.tr.md)

# Basketball and Football Match Forecasts

`bbtahmin` is a Python research project for pregame basketball and football forecasts. Run the local browser app, inspect the forecasts saved by GitHub Actions, or reproduce a chronological backtest from the included archives.

[![Tests](https://github.com/Bluetwinklez/basketbol-tahmin/actions/workflows/tests.yml/badge.svg)](https://github.com/Bluetwinklez/basketbol-tahmin/actions/workflows/tests.yml)
[![Sports data refresh](https://github.com/Bluetwinklez/basketbol-tahmin/actions/workflows/sports-data.yml/badge.svg)](https://github.com/Bluetwinklez/basketbol-tahmin/actions/workflows/sports-data.yml)

[Latest scorecard](docs/kanit/live_scorecard/scorecard.md) · [Paired experiment status](data/improvement_shadow/latest.json) · [Documentation](docs/INDEX.md) · [Changelog](docs/CHANGELOG.md)

## Quick start

Clone the repository and run the commands from its root. Use Python 3.12 or newer.

```bash
git clone https://github.com/Bluetwinklez/basketbol-tahmin.git
cd basketbol-tahmin
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
python -m bbtahmin app
```

The app opens at `http://127.0.0.1:8765`. Use the basketball board, `/football` for football, and `/performance` for measured accuracy and probability losses. The browser app runs locally without a Node.js build. Node.js 22 is used for the frontend tests. [Local app guide](docs/local-app.md)

## What you can forecast

| Sport | Outputs | Coverage |
| --- | --- | --- |
| Basketball | Winner probability, expected team scores, margin, total and uncertainty intervals | Core historical models for NBA, EuroLeague, EuroCup and Australian NBL. Separate archives and models cover KBL, ABA, Türkiye BSL, EuroCup Women, FIBA Europe Cup and other competitions. |
| Football | Regulation-time 1/X/2, expected goals, goal totals and both teams to score. The board also derives double chance from 1/X/2. | European and American archives. Scheduled forecasts depend on a current, independently confirmed kickoff and adequate team history. The default is the opponent-adjusted model. |

Historical coverage, manual forecasts and scheduled forecasts depend on different sources. NBA historical and manual forecasts are supported. Automated NBA schedules are currently blocked by source access. Japan's 2026–27 B.PREMIER/B.ONE requires separate model validation before forecasts can be enabled. [League coverage](docs/delivery-scope.md) · [NBA status](docs/nba-daily.md) · [Refresh exceptions](docs/refresh-known-missing.md)

## Commands and outputs

| Task | Command | Output |
| --- | --- | --- |
| Run basketball using saved sources | `python -m bbtahmin gunluk --ligler E KBL` | Local forecasts and daily report in `rapor/daily/` |
| Refresh basketball and run | `python -m bbtahmin gunluk --ligler E KBL --guncelle` | Updates public sources before the local run |
| Run football using saved sources | `python -m bbtahmin futbol daily --days 7` | Local report in `rapor/football/latest.json` |
| Refresh football and run | `python -m bbtahmin futbol daily --refresh --days 7` | Refreshes the current archive and fixture confirmations |
| Produce a manual NBA forecast | `python -m bbtahmin tahmin "BOS - LAL @1.65/2.30" --lig NBA --json` | JSON with experimental odds comparison |
| Read the experimental İddaa bulletin | `python -m bbtahmin bulten --guncelle --limit 10` | Refreshes and reads the local bulletin snapshot |
| Rebuild the offline scorecard | `python scripts/live_scorecard.py` | Markdown and JSON in `docs/kanit/live_scorecard/` |
| Check pinned forecast files | `python scripts/pin_improvement_baseline.py --verify-only` | Verifies the original file hashes |

The [repository refresh workflow](.github/workflows/sports-data.yml) publishes to the checked-in ledgers and scorecards. Local daily commands use the `rapor/` directory by default. Reuse the same local output directory to preserve the earliest local forecasts. For an existing experiment, use the published report or `python scripts/run_shadow_cycle.py --settle-only`. [Daily workflow](docs/daily-workflow.md) · [Football workflow](docs/football.md)

## Performance and evidence

The live scorecard measures saved pregame forecasts after a final is observed. It reports sample size, accuracy, log loss, Brier score, calibration and baselines. Dates, exclusions and results are in the versioned report. Use both accuracy and coverage when reading confidence filters. Historical replays and paired pregame experiments have separate evidence.

| Evidence | Where to look |
| --- | --- |
| Recorded forecasts and observed results | [Live scorecard](docs/kanit/live_scorecard/scorecard.md) · [Method](docs/live-scorecard.md) |
| Fixed reference and candidate on the same upcoming fixture | [Published experiment report](data/improvement_shadow/latest.json) · [Improvement plan and gates](docs/improvement-progress.md) |
| Reproducible historical comparisons | [Basketball backtests](docs/kanit/pregame_verified/completed_seasons.csv) · [Football and basketball review](docs/accuracy-review.md) · [Workload experiment](docs/kanit/improvement/basketball-rest-decay.md) |
| Closing-odds evidence for the matched NBA historical sample | [Market comparison](docs/kanit/piyasa.csv) · [Simulation](docs/kanit/bahis.csv) |

Forecasts are for research and do not provide betting execution or guaranteed returns. Missing source data, uncertain kickoff times and disputed results remain visible in the reports.

## Development and data

```bash
python -m pytest -q
npm ci --no-audit --no-fund
npm run test:ui
```

The optional read-only local MCP server is available with `python -m pip install -e '.[mcp]'` and `bbtahmin-mcp`. Use `requirements.txt` for a portable install. `requirements-lock.txt` records an older Windows environment.

Code is [MIT licensed](LICENSE). The archives retain their separate [source licenses and attributions](data/KAYNAKLAR.md). Raw caches, local bulletin history and local reports are ignored by Git. [Security policy](SECURITY.md) · [Security audit](SECURITY_AUDIT.md)
