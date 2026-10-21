import pandas as pd
import pytest
from bbtahmin.veri.schema import normalize
@pytest.fixture
def games():
    """Üç lig, iki sezon, dört takım; sonuçlar sezona ve maça göre değişir."""
    rows=[]
    teams=['A','B','C','D']
    for league in ['E','U','NBA']:
        for i in range(24):
            season='2020-21' if i<12 else '2021-22'
            start=pd.Timestamp('2020-10-01' if i<12 else '2021-10-01',tz='UTC')
            home,away=teams[i%4],teams[(i+1+i//4)%4]
            if home==away: away=teams[(i+2)%4]
            home_score,away_score=80+i,70+(i*7)%25
            if home_score==away_score: away_score+=3
            rows.append(dict(mac_id=f'{league}_{i}',lig=league,sezon=season,
                tarih_utc=start+pd.Timedelta(days=(i%12)*2,hours=18),
                ev=home,dep=away,ev_skor=home_score,dep_skor=away_score,ev_iy=40,dep_iy=35,
                uzatma=False,tarafsiz_saha=False,asama='normal',kaynak='fixture'))
    return normalize(rows)
