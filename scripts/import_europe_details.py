"""Import numeric European box scores/shots/events from a public archive snapshot.

Optional dependency: pip install duckdb==1.4.1
Download the documented database URL, then run with --database PATH.
Every imported game must match this project's official results and team codes.
These are postgame observations: future pregame features MUST lag them by date.
"""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from bbtahmin.veri.genislet import save_table

SOURCE = 'https://github.com/McNews11/euroleague-open-data'
DATABASE_URL = 'https://raw.githubusercontent.com/McNews11/euroleague-open-data/main/data/euroleague.duckdb'


def run(database):
    import duckdb
    database = Path(database)
    connection = duckdb.connect(str(database), read_only=True)
    try:
        matches = pd.read_parquet('data/maclar.parquet').set_index('mac_id')
        remote = connection.execute('SELECT * FROM games').fetchdf()
        remote['mac_id'] = remote.season_code + '_' + remote.game_code.astype(str)
        paired = remote[remote.mac_id.isin(matches.index)].set_index('mac_id')
        verified = paired[(paired.home_team_code == matches.ev.reindex(paired.index)) &
                          (paired.away_team_code == matches.dep.reindex(paired.index)) &
                          (paired.home_score == matches.ev_skor.reindex(paired.index)) &
                          (paired.away_score == matches.dep_skor.reindex(paired.index))]
        valid = set(verified.index)
        report = dict(source=SOURCE,database_url=DATABASE_URL,
                      snapshot_sha256=hashlib.sha256(database.read_bytes()).hexdigest(),
                      timestamp=pd.Timestamp.now(tz='UTC').isoformat(),
                      verified_games=len(valid),rejected_games=len(remote)-len(valid),tables={},
                      usage='Postgame facts only. Do not use same-game shots/events as pregame features.')
        selections = {
            'boxscores_team': ('avrupa_takim_istatistik', ['season_code','game_code','team_code','is_home',
                'seconds_played','points','fg2m','fg2a','fg3m','fg3a','ftm','fta','rebounds_total',
                'rebounds_defensive','rebounds_offensive','assists','steals','turnovers','blocks_favour',
                'blocks_against','fouls_committed','fouls_received','plus_minus'], ['mac_id','team_code']),
            'boxscores_player': ('avrupa_oyuncu_istatistik', ['season_code','game_code','team_code','person_code',
                'is_home','is_starter','seconds_played','points','fg2m','fg2a','fg3m','fg3a','ftm','fta',
                'rebounds_total','rebounds_defensive','rebounds_offensive','assists','steals','turnovers',
                'blocks_favour','blocks_against','fouls_committed','fouls_received','plus_minus'],
                ['mac_id','team_code','person_code']),
            'shots': ('avrupa_sutlar', ['season_code','game_code','sequence','team_code','person_code',
                'action_id','points','coord_x','coord_y','zone','is_fastbreak','is_second_chance',
                'is_points_off_turnover','minute','console_clock','score_home','score_away'], ['mac_id','sequence']),
            'play_by_play': ('avrupa_olaylar', ['season_code','game_code','period','play_number','play_type',
                'team_code','person_code','minute','marker_time','score_home','score_away'], ['mac_id','play_number']),
        }
        for table, (filename, columns, keys) in selections.items():
            data = connection.execute(f'SELECT {", ".join(columns)} FROM {table}').fetchdf()
            data['mac_id'] = data.season_code + '_' + data.game_code.astype(str)
            data = data[data.mac_id.isin(valid)].copy()
            data['kaynak'] = SOURCE
            count = save_table(data.to_dict('records'),f'data/{filename}.parquet',keys)
            report['tables'][filename] = dict(rows=count,games=data.mac_id.nunique())
        # Feed the established box-score feature loader while keeping the richer
        # fact tables separate. Do not alter existing official box-score rows.
        t = pd.read_parquet('data/avrupa_takim_istatistik.parquet')
        box = pd.DataFrame(dict(mac_id=t.mac_id,rol=t.is_home.map({True:'ev',False:'dep'}),
            say=t.points,fga2=t.fg2a,fga3=t.fg3a,fta=t.fta,oreb=t.rebounds_offensive,
            dreb=t.rebounds_defensive,tov=t.turnovers,faul=t.fouls_committed,sure=t.seconds_played/5))
        # Team seconds are the sum of five players; the model expects game duration.
        if Path('data/kutu.parquet').exists():
            old = pd.read_parquet('data/kutu.parquet')
            box = box[~box.mac_id.isin(old.mac_id)]
        report['new_standard_box_rows'] = len(box)
        save_table(box.to_dict('records'),'data/kutu.parquet',['mac_id','rol'])
        p = pd.read_parquet('data/avrupa_oyuncu_istatistik.parquet')
        p = p[p.seconds_played > 0]
        players = pd.DataFrame(dict(mac_id=p.mac_id,rol=p.is_home.map({True:'ev',False:'dep'}),
                                    oyuncu=p.person_code,saniye=p.seconds_played))
        if Path('data/oyuncular.parquet').exists():
            old = pd.read_parquet('data/oyuncular.parquet')
            players = players[~players.mac_id.isin(old.mac_id)]
        save_table(players.to_dict('records'),'data/oyuncular.parquet',['mac_id','rol','oyuncu'])
        Path('docs/kanit/avrupa_detay.json').write_text(json.dumps(report,indent=2),'utf8')
        print(json.dumps(report,indent=2))
        return report
    finally:
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',required=True)
    args = parser.parse_args()
    run(args.database)
