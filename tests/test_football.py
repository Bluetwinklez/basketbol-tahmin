import json

import numpy as np
import pandas as pd
import pytest

from bbtahmin.football.data import parse_json,parse_turkey,row,write_json
from bbtahmin.football.model import GoalModel,score


def history():
    rows=[]
    for i in range(160):
        day=(pd.Timestamp('2025-01-01')+pd.Timedelta(days=i)).strftime('%Y-%m-%d')
        rows.append(dict(league='TR1',status='final',date=day,home='a' if i%2 else 'b',away='b' if i%2 else 'a',home_goals=i%4,away_goals=i%3))
    return pd.DataFrame(rows)


def test_zero_goals_draws_and_source_schema():
    payload=dict(name='Test 2026/27',matches=[dict(date='2026-10-20',team1='A',team2='B',score=[0,0]),
                                            dict(date='2026-10-25',team1='B',team2='A',score=None)])
    rows=parse_json(payload,'EN1','2026-27','source','2026-10-23T10:00Z')
    assert rows[0]['status']=='final' and rows[0]['home_goals']==0
    assert rows[1]['status']=='scheduled' and rows[1]['home_goals'] is None
    payload['matches'][0]['score']={'ft':[-1,0]}
    with pytest.raises(ValueError):parse_json(payload,'EN1','2026-27','source','2026-10-23T10:00Z')


def test_no_same_day_or_future_training_scores():
    for day in ['2026-10-23','2026-10-24']:
        r=row('TR1','2026-27',day,'A','B',[3,1],'source','2026-10-23T22:00Z')
        assert r['status']=='unverified' and r['home_goals'] is None


def test_turkey_both_layouts_and_reordered_dates():
    text='= Turkey | Süper Lig 2026/27\nSat Oct 24 2026\n  19:00   A  2-1 (1-0)  B\nSun Oct 25\n  20:00   C    v D    0-0\nSat Jan 2\n  18:00   E  v  F\nSat Dec 26 2026\n  17:00   A  v  C\n'
    r=parse_turkey(text,'2026-27','source','2027-06-01T00:00Z')
    assert len(r)==4 and r[1]['home_goals']==0
    assert r[2]['date']=='2027-01-02' and r[3]['date']=='2026-12-26'


def test_model_excludes_same_day_future_and_other_leagues():
    h=history();m=GoalModel(h,'TR1','2025-07-01');p=m.predict('a','b')
    extra=h.iloc[:1].copy();extra['date']='2025-07-01';extra['home_goals']=30
    foreign=h.copy();foreign.league='EN1';foreign.home_goals=30
    new=GoalModel(pd.concat([h,extra,foreign]),'TR1','2025-07-01').predict('a','b')
    assert p==new
    assert sum(p['probabilities'].values())==pytest.approx(1)
    assert 0<p['over']['3.5']<p['over']['2.5']<p['over']['1.5']<1
    assert m.predict('unknown','a')['issues']


def test_three_way_draw_scoring_and_errors():
    p=GoalModel(history(),'TR1','2025-07-01').predict('a','b')
    p['predicted_outcome']='draw'
    r=score(p,0,0)
    assert r['winner_correct'] and np.isfinite(r['log_loss'])
    assert r['total_absolute_error']==pytest.approx(p['expected_home_goals']+p['expected_away_goals'])


def test_frozen_ledger_reuses_forecast_and_checks_integrity(tmp_path,monkeypatch):
    from bbtahmin.football import daily
    fixture=row('TR1','2026-27','2026-10-25','A','B',None,'source','2026-10-23T12:00Z')
    # History from earlier dates and a separate fixture only.
    h=history();h['date']=(pd.to_datetime(h.date)+pd.Timedelta(days=365)).dt.strftime('%Y-%m-%d')
    h['event_id']=['h'+str(i) for i in range(len(h))]
    f=pd.concat([h,pd.DataFrame([fixture])],ignore_index=True)
    monkeypatch.setattr(daily,'load',lambda root:f)
    write_json(tmp_path/'collection.json',dict(checked_at_utc='2026-10-23T12:00Z',errors=[]))
    out=tmp_path/'ledger'
    r=daily.run(output=out,root=tmp_path,now='2026-10-23T13:00Z')
    assert r['pending']==1 and r['official_winner_accuracy'] is None
    file=next((out/'forecasts').glob('*.json'));original=file.read_bytes()
    daily.run(output=out,root=tmp_path,now='2026-10-24T13:00Z')
    assert file.read_bytes()==original
    tamper=json.loads(original);tamper['prediction']['expected_home_goals']=20
    file.write_text(json.dumps(tamper))
    with pytest.raises(ValueError,match='hash'):daily.run(output=out,root=tmp_path,now='2026-10-24T13:00Z')


def test_stale_future_fixture_is_not_frozen(tmp_path,monkeypatch):
    from bbtahmin.football import daily
    f=pd.DataFrame([row('TR1','2026-27','2026-10-25','A','B',None,'source','2026-10-01T12:00Z')])
    monkeypatch.setattr(daily,'load',lambda root:f)
    write_json(tmp_path/'collection.json',dict(checked_at_utc='2026-10-01T12:00Z',errors=[]))
    r=daily.run(output=tmp_path/'ledger',root=tmp_path,now='2026-10-23T13:00Z')
    assert not r['forecasts'] and '72 hours' in r['skipped'][0]['reason']


def test_collection_retains_conflicting_finals(tmp_path):
    import subprocess
    from bbtahmin.football.data import collect,load
    source=tmp_path/'source';source.mkdir();(source/'LICENSE.md').write_text('CC0 1.0 Universal')
    subprocess.run(['git','init',str(source)],check=True,capture_output=True)
    subprocess.run(['git','-C',str(source),'-c','user.name=test','-c','user.email=test@example.com','commit','--allow-empty','-m','test'],check=True,capture_output=True)
    season=source/'2024-25';season.mkdir()
    payload=dict(name='Premier League 2024/25',matches=[dict(date='2024-08-01',team1='A',team2='B',score={'ft':[1,0]})])
    file=season/'en.1.json';file.write_text(json.dumps(payload));root=tmp_path/'data'
    collect(2024,2024,json_dir=source,europe_dir=source,root=root)
    assert load(root).iloc[0].home_goals==1
    payload['matches'][0]['score']['ft']=[0,2];file.write_text(json.dumps(payload))
    with pytest.raises(RuntimeError,match='retained'):
        collect(2024,2024,json_dir=source,europe_dir=source,root=root)
    r=json.loads((root/'collection.json').read_text())
    assert any('Conflicting' in e['error'] for e in r['errors'])
    assert load(root).iloc[0].home_goals==1
