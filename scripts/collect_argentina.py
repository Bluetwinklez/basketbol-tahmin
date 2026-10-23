"""Collect public Argentina sources and verify sufficient independent history."""
import json
from pathlib import Path
from bbtahmin.veri.argentina import collect

if __name__ == '__main__':
    games = collect()
    report = json.loads(Path('docs/kanit/competitions/ARG_LNB_collection.json').read_text())
    if report['errors'] or len(games) < 1000 or not report['official_current_refresh']:
        raise SystemExit('Argentina collection incomplete; inspect collection evidence before claiming support')
