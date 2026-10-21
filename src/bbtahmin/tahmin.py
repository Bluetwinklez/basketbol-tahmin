import json
from pathlib import Path
import numpy as np
import pandas as pd
from .ozellik import features_for_match
def run(league,home,away,date):
    history=pd.read_parquet('data/maclar.parquet')
    date=pd.Timestamp(date)
    if date.tzinfo is None: raise ValueError('Saat dilimi gerekli: ör. 2026-10-25T18:00:00Z')
    date=date.tz_convert('UTC')
    known=set(history.loc[history.lig==league,'ev'])|set(history.loc[history.lig==league,'dep'])
    if home==away or home not in known or away not in known:
        raise ValueError('Distinct known source team codes are required')
    match=dict(mac_id='QUERY',lig=league,sezon=f'{date.year if date.month>=7 else date.year-1}-{str(date.year+1 if date.month>=7 else date.year)[-2:]}',
        tarih_utc=date,ev=home,dep=away,tarafsiz_saha=False,ev_skor=None,dep_skor=None)
    parameters=json.loads(Path('docs/kanit/parametreler.json').read_text('utf8'))
    # Use only tuning records whose entire validation season precedes query time.
    eligible=[r for r in parameters if r.get('lig')==league and r.get('model')=='elo'
              and int(r['sezon'][:4])<=int(match['sezon'][:4])]
    if not eligible: raise ValueError('Önceden doğrulanmış Elo penceresi yok; önce backtest çalıştırın')
    p=sorted(eligible,key=lambda r:r['sezon'])[-1]
    features=features_for_match(history[history.lig==league],match,k=p['k'],advantage=p['home_advantage'],
                                shrink=p['shrink'],mov=False)
    result=dict(lig=league,ev=home,dep=away,tarih_utc=date.isoformat(),model='elo',
                ev_kazanma_olasiligi=float(features.elo_p),parametre_sezonu=p['sezon'])
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result
