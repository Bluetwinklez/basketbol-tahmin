"""Write the football calibration report from the local live scorecard inputs."""

import json
import sys
from pathlib import Path


def run(root, output):
    from bbtahmin.football_calibration_report import build_report, markdown
    from scripts.evaluate_improvement_football import TEMPERATURES, temperature
    from scripts.live_scorecard import _read

    ledger = root / "data/football_ledger"
    snapshot = ledger / "latest.json"
    report = build_report(
        [_read(path) for path in sorted((ledger / "forecasts").glob("*.json"))],
        _read(snapshot) if snapshot.exists() else None,
        (.5, .6, *TEMPERATURES),
        temperature,
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (output / "report.md").write_text(markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root / "src"), str(root)]
    run(root, root / "docs/kanit/football_calibration")
