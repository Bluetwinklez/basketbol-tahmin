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
    parser.add_argument('--verify-only',action='store_true',help='Verify without writing reports or changing the baseline')
    args = parser.parse_args()
    root = Path(args.output)
    path = root/'baseline.json'
    current = forecast_files()
    if path.exists():
        pinned = json.loads(path.read_text(encoding='utf8'))
        for name, expected in pinned['forecast_files'].items():
            if name in pinned.get('portable_forecast_files',{}):
                raw=Path(name).read_bytes().replace(b'\r\n',b'\n')
                if name=='defter/tahminler.csv':raw=raw[:pinned['portable_legacy_prefix_length']]
                if hashlib.sha256(raw).hexdigest()!=pinned['portable_forecast_files'][name]:
                    raise ValueError(f'Original forecast changed: {name}')
                continue
            if name=='defter/tahminler.csv' and pinned.get('legacy_csv_prefix_length'):
                raw=Path(name).read_bytes()[:pinned['legacy_csv_prefix_length']]
                if hashlib.sha256(raw).hexdigest()!=expected: raise ValueError('Original legacy forecast rows changed')
                continue
            if current.get(name) != expected:
                raise ValueError(f'Original forecast changed or disappeared: {name}')
        if not args.verify_only and 'legacy_csv_prefix_length' not in pinned and 'defter/tahminler.csv' in pinned['forecast_files']:
            # Migrate only after the original whole-file hash was verified.
            pinned['legacy_csv_prefix_length']=Path('defter/tahminler.csv').stat().st_size
            write_json(path,pinned)
        if not args.verify_only and 'portable_forecast_files' not in pinned:
            # Preserve the original raw hashes too. Migration is permitted only
            # after every original raw file was checked above on this checkout.
            pinned['portable_forecast_files']={name:hashlib.sha256(Path(name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
                                               for name in pinned['forecast_files']}
            if 'defter/tahminler.csv' in pinned['forecast_files']:
                pinned['portable_legacy_prefix_length']=len(Path('defter/tahminler.csv').read_bytes().replace(b'\r\n',b'\n'))
            write_json(path,pinned)
    else:
        if args.verify_only: raise ValueError('Pinned original forecast baseline missing')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf8') as stream:
            json.dump(dict(spec='improvement-baseline-v1', pinned_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),
                           forecast_files=current,legacy_csv_prefix_length=Path('defter/tahminler.csv').stat().st_size if Path('defter/tahminler.csv').exists() else None,
                           policy='First recorded pregame forecast; duplicates never count twice. Existing outcome audit is diagnostic, not an untouched holdout.'), stream, indent=2)
    if not args.verify_only:
        write_json(root/'football_history_health.json', inventory(load(), pd.Timestamp.now(tz='UTC')))
    print(json.dumps(dict(verified_pinned_files=len(json.loads(path.read_text())['forecast_files']),
                          current_forecast_files=len(current))))


if __name__ == '__main__':
    main()
