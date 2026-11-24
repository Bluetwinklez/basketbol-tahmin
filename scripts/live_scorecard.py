"""Write the scorecard from the repository's existing local ledgers."""

import json
import sys
from pathlib import Path


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(root, output):
    from bbtahmin.live_scorecard import build_scorecard, markdown

    basketball = root / "data/basketball_ledger"
    football = root / "data/football_ledger"
    basketball_checks = [_read(path) for path in sorted(basketball.glob("check_*.json"))]
    basketball_paths = set((basketball / "forecasts").glob("*.json"))
    # Daily basketball checks also settle frozen records from these two older ledgers.
    references = {Path(batch["record"].replace("\\", "/"))
                  for check in basketball_checks for batch in check["settlements"]}
    for folder in ("data/argentina_ledger/forecasts", "docs/kanit/prospective"):
        basketball_paths.update(
            path for path in (root / folder).glob("*.json") if path.relative_to(root) in references
        )
    football_report = football / "latest.json"
    report = build_scorecard(
        [_read(path) for path in sorted(basketball_paths)],
        basketball_checks,
        [_read(path) for path in sorted((football / "forecasts").glob("*.json"))],
        _read(football_report) if football_report.exists() else None,
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "scorecard.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (output / "scorecard.md").write_text(markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    run(root, root / "docs/kanit/live_scorecard")
