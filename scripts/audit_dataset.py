"""Validate persisted data, optionally proving original results were preserved."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


def run(baseline=None):
    games = pd.read_parquet('data/maclar.parquet')
    assert not games.mac_id.duplicated().any(), 'Duplicate game IDs'
    assert games[['tarih_utc','ev','dep','ev_skor','dep_skor']].notna().all().all(), 'Missing completed-game fields'
    assert (games.ev_skor != games.dep_skor).all(), 'Tied final result'
    assert ((games.ev_skor >= 0) & (games.dep_skor >= 0)).all(), 'Negative final score'
    assert (games.ev != games.dep).all(), 'Same team on both sides'
    report = dict(timestamp=pd.Timestamp.now(tz='UTC').isoformat(), games=len(games), files={})
    unusual = games[(games.ev_skor == 0) | (games.dep_skor == 0)]
    report['zero_score_results_excluded_from_models'] = unusual[['mac_id','ev_skor','dep_skor']].to_dict('records')
    if baseline:
        old = pd.read_parquet(baseline).set_index('mac_id')
        new = games.set_index('mac_id').reindex(old.index)
        for column in ['lig','sezon','tarih_utc','ev','dep','ev_skor','dep_skor']:
            assert new[column].equals(old[column]), f'Original result changed: {column}'
        report.update(original_games=len(old),added_games=len(games)-len(old),original_results_preserved=True)
    keys = {
        'kutu':['mac_id','rol'],'kutu_nba':['mac_id','rol'],
        'oyuncular':['mac_id','rol','oyuncu'],'oyuncular_nba':['mac_id','rol','oyuncu'],
        'nba_oyuncu_mac':['mac_id','oyuncu_id'],
        'nba_mac_baglami':['mac_id'], 'nba_takim_istatistik':['mac_id','rol'],
        'nba_oyuncu_istatistik':['mac_id','rol','athlete_id'],
        'avrupa_takim_istatistik':['mac_id','team_code'],
        'avrupa_oyuncu_istatistik':['mac_id','team_code','person_code'],
        'avrupa_sutlar':['mac_id','sequence'],'avrupa_olaylar':['mac_id','play_number'],
    }
    for name, unique in keys.items():
        path = Path(f'data/{name}.parquet')
        if not path.exists():
            continue
        table = pd.read_parquet(path)
        assert not table.duplicated(unique).any(), f'Duplicate detail rows: {name}'
        assert table.mac_id.isin(games.mac_id).all(), f'Orphan detail rows: {name}'
        report['files'][name] = dict(rows=len(table),games=table.mac_id.nunique(),bytes=path.stat().st_size,
                                    sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    coverage = games.groupby('lig').agg(games=('mac_id','size'),first=('tarih_utc','min'),last=('tarih_utc','max'))
    report['coverage'] = {league: {k:str(v) if k in ('first','last') else int(v) for k,v in row.items()}
                          for league,row in coverage.to_dict('index').items()}
    Path('docs/kanit/dataset_audit.json').write_text(json.dumps(report,indent=2),'utf8')
    print(json.dumps(report,indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline')
    args = parser.parse_args()
    run(args.baseline)
