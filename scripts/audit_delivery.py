"""Inventory distinct finals and preserve original forecasts against a pinned base."""
import argparse
import gzip
import io
import json
import subprocess
from pathlib import Path

import pandas as pd

from bbtahmin.football.data import load, write_json

BASE = '0fafc2ef6345a19f447f36f2be046a9a26a41f29'


def original(base, path):
    result = subprocess.run(['git', 'show', f'{base}:{path}'], capture_output=True)
    return result.stdout if result.returncode == 0 else None


def run(base=BASE, output='docs/kanit/delivery_audit'):
    target = Path(output)
    football = []
    frame = load()
    for (league, season), part in frame[frame.status == 'final'].groupby(['league', 'season']):
        path = f'data/football/{league}_{season}.json.gz'
        raw = original(base, path)
        previous = json.loads(gzip.decompress(raw))['rows'] if raw else []
        ids = {r['event_id'] for r in previous if r['status'] == 'final'}
        football.append(dict(league=league, season=season, stored_unique_finals=len(part),
                             new_unique_finals=len(set(part.event_id)-ids),
                             first_date=part.date.min(), last_date=part.date.max(),
                             source_kinds=sorted(part.source_kind.unique()), complete_season_verified=False))
    basketball = []
    for root in ('data/asia', 'data/competitions', 'data/recent'):
        for path in sorted(Path(root).glob('*.parquet')):
            games = pd.read_parquet(path)
            if not {'mac_id', 'ev_skor', 'dep_skor'} <= set(games):
                continue
            raw = original(base, path.as_posix())
            previous = pd.read_parquet(io.BytesIO(raw)) if raw else pd.DataFrame(columns=['mac_id'])
            added = games[~games.mac_id.isin(previous.mac_id)]
            for season, part in games.groupby('sezon'):
                code = str(part.lig.iloc[0])
                # Legacy Japanese storage filenames are not current competition identities.
                competition = {'JP_B1': 'JP_PREMIER', 'JP_B2': 'JP_ONE'}.get(code, code) if season >= '2026-27' else code
                basketball.append(dict(path=path.as_posix(), competition=competition, season=season,
                                       stored_unique_finals=int(part.mac_id.nunique()),
                                       new_unique_finals=int(added[added.sezon == season].mac_id.nunique()),
                                       last_utc=str(part.tarih_utc.max()), completeness_verified=False))
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', base,
                                     'data/football_ledger/forecasts', 'data/basketball_ledger/forecasts',
                                     'data/argentina_ledger/forecasts']).decode().splitlines()
    changed = [name for name in names if json.loads(Path(name).read_text('utf8')) !=
               json.loads(original(base, name))]
    if changed:
        raise ValueError(f'Original forecast payloads changed: {changed}')
    now = pd.Timestamp.now(tz='UTC').isoformat()
    write_json(target/'football_inventory.json', dict(base=base, checked_at_utc=now, seasons=football,
               note='Last archive date does not establish completeness or valid current forecasts.'))
    write_json(target/'basketball_inventory.json', dict(base=base, checked_at_utc=now,
               basketball_inventory=basketball, original_forecast_files=len(names),
               changed_original_forecasts=changed, comparison='Parsed JSON payload equality; checkout newline translation excluded.'))
    result = dict(new_football_finals=sum(r['new_unique_finals'] for r in football),
                  new_basketball_finals=sum(r['new_unique_finals'] for r in basketball),
                  unchanged_original_forecasts=len(names))
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default=BASE)
    parser.add_argument('--output', default='docs/kanit/delivery_audit')
    args = parser.parse_args()
    run(args.base, args.output)
