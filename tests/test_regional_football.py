import pandas as pd
from bbtahmin.football.regional import normalize

def test_regional_import_excludes_extra_time_foreign_and_unknown_scores():
    a=dict(home='A',away='B',date='2023-05-01',gh=2,ga=1,competition='uruguay',full_time='F',level='national',home_ident='a-id',away_ident='b-id')
    rows=normalize(pd.DataFrame([a,dict(a,full_time='P'),dict(a,full_time='E'),dict(a,competition='england'),dict(a,gh=None),dict(a,date='2026-01-01'),dict(a,home='B')]),'source','2026-10-25')
    assert len(rows)==1 and rows[0]['league']=='UY1'
    assert rows[0]['license']=='ODC-By-1.0'
    assert rows[0]['source_home_ident']=='a-id'
    assert rows[0]['source_kind']!='official'
