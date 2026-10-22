"""Small, deterministic quarter-score sample for chronological live research."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

from .cba import fetch


def parse(html,home_final,away_final):
    soup=BeautifulSoup(html,'html.parser')
    for table in soup.select('table'):
        headers=[t.get_text(strip=True) for t in table.select('thead th')]
        if headers[1:5]!=['1','2','3','4'] or headers[-1]!='Final':continue
        rows=table.select('tbody tr')
        if len(rows)!=2:continue
        values=[[int(t.get_text(strip=True)) for t in row.select('td')[1:]] for row in rows]
        away,home=values
        if home[-1]!=home_final or away[-1]!=away_final:raise ValueError('Quarter table disagrees with fixture orientation/final')
        if sum(home[:-1])!=home[-1] or sum(away[:-1])!=away[-1]:raise ValueError('Quarter sum mismatch')
        return home[:4],away[:4]
    raise ValueError('Missing quarter table')


def collect(per_season=40):
    g=pd.read_parquet('data/cba_games.parquet');sample=[]
    for season in ['2023-24','2024-25','2025-26']:
        group=g[g.sezon==season].sort_values(['tarih_utc','mac_id'])
        if len(group)<per_season:raise ValueError('Insufficient quarter sample season')
        sample.extend(group.iloc[np.linspace(0,len(group)-1,per_season,dtype=int)].to_dict('records'))
    errors=[];records=[]
    def one(row):
        try:
            home,away=parse(fetch(row['boxscore_path']),row['ev_skor'],row['dep_skor'])
            return dict(mac_id=row['mac_id'],sezon=row['sezon'],tarih_utc=row['tarih_utc'],
                        home_quarters=home,away_quarters=away),None
        except Exception as e:return None,dict(mac_id=row['mac_id'],error=str(e))
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result,error in pool.map(one,sample):
            if result:records.append(result)
            else:errors.append(error)
    pd.DataFrame(records).to_parquet('data/cba_quarters.parquet',index=False)
    Path('docs/kanit/cba/quarter_collection.json').write_text(json.dumps(dict(games=len(records),errors=errors,
        sampling='40 uniformly spaced fixtures per season, 2023-24 through 2025-26; no outcome-based selection'),indent=2))
    print('Quarter games collected:',len(records),flush=True)


if __name__=='__main__':collect()
