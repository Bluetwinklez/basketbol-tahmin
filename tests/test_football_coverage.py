import pandas as pd
from bbtahmin.football.coverage import last_matches
from bbtahmin.football.data import row

def test_last50_excludes_today_foreign_and_unfinished():
    rows=[row('TR1','2025-26',f'2025-08-{i:02d}','A','B',[2,1],'source','2026-10-25') for i in range(1,26)]
    rows += [row('EN1','2025-26','2025-08-01','A','B',[9,0],'source','2026-10-25'),row('TR1','2025-26','2025-08-26','A','B',[5,0],'source','2026-10-25')]
    r=last_matches(pd.DataFrame(rows),'TR1','A','2025-08-26',20)
    assert r['available']==20 and r['wins']==20 and r['goals_for']==40
    assert r['matches'][0]['date']=='2025-08-25'
    r=last_matches(pd.DataFrame(rows),'TR1','A','2025-08-26')
    assert r['missing']==25
