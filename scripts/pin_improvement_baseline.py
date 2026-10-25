"""Pin original forecast hashes before experiments; refuse later replacement."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from bbtahmin.football.daily import digest
from bbtahmin.football.data import load, write_json
from bbtahmin.football.health import inventory
from bbtahmin.prospective import verify


def forecast_files():
    found = {}
    for folder in ('data', 'docs/kanit'):
        for path in sorted(Path(folder).rglob('*.json')):
            try:
                record = json.loads(path.read_text(encoding='utf8'))
            except (ValueError, OSError):
                continue
            if not isinstance(record, dict):
                continue
            if record.get('spec') == 'prospective-v1':
                verify(record)
            elif record.get('spec') in ('football-prospective-v1', 'football-prospective-v2'):
                payload = dict(record)
                expected = payload.pop('payload_sha256')
                if digest(payload) != expected:
                    raise ValueError(f'Invalid original forecast: {path}')
            else:
                continue
            found[path.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    legacy = Path('defter/tahminler.csv')
    if legacy.exists():
        found[legacy.as_posix()] = hashlib.sha256(legacy.read_bytes()).hexdigest()
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='docs/kanit/improvement')
    args = parser.parse_args()
    root = Path(args.output)
    path = root/'baseline.json'
    current = forecast_files()
    if path.exists():
        pinned = json.loads(path.read_text(encoding='utf8'))
        for name, expected in pinned['forecast_files'].items():
            if current.get(name) != expected:
                raise ValueError(f'Original forecast changed or disappeared: {name}')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf8') as stream:
            json.dump(dict(spec='improvement-baseline-v1', pinned_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),
                           forecast_files=current,
                           policy='First recorded pregame forecast; duplicates never count twice. Existing outcome audit is diagnostic, not an untouched holdout.'), stream, indent=2)
    write_json(root/'football_history_health.json', inventory(load(), pd.Timestamp.now(tz='UTC')))
    print(json.dumps(dict(verified_pinned_files=len(json.loads(path.read_text())['forecast_files']),
                          current_forecast_files=len(current))))


if __name__ == '__main__':
    main()
