import pytest
from bbtahmin.football.data import parse_text, row, key


def test_calendar_dates_do_not_roll_january_forward():
    rows=parse_text('= Brasileiro Série B 2025\nSat Jan 4\n  A  v  B    0-0\nSat Nov 1\n  B  v  A    2-1\n','BR2','2025','source','2026-10-24T00:00Z')
    assert [r['date'] for r in rows]==['2025-01-04','2025-11-01']
    assert rows[0]['home_goals']==0
    assert rows[0]['source_kind']=='community_CC0_not_official'


def test_wrong_competition_and_out_of_season_rejected():
    with pytest.raises(ValueError): parse_text('= Brasileiro Série A 2025\n','BR2','2025','source','2026-10-24')
    with pytest.raises(ValueError): row('BR2','2025','2026-01-04','A','B',[0,0],'source','2026-10-24')
    assert key('CRB AL')==key('CR Brasil AL')
    assert key('Londrina PR')!=key('Londrina')


def test_calendar_future_score_is_not_training_data():
    r=row('BR2','2026','2026-10-24','A','B',[4,1],'source','2026-10-24T23:00Z')
    assert r['status']=='unverified' and r['home_goals'] is None


def test_pandemic_extension_is_explicit_and_bounded():
    rows=parse_text('= Brasileiro Série B 2020\nFri Jan 29\n  A  v  B    1-0\n','BR2','2020','source','2026-10-24')
    assert rows[0]['date']=='2021-01-29'
    with pytest.raises(ValueError): row('BR2','2020','2021-02-01','A','B',[0,0],'source','2026-10-24')


def test_collector_retains_conflicts_and_reports_missing_source(tmp_path):
    import json
    import gzip
    import subprocess
    from bbtahmin.football.calendar import collect
    source=tmp_path/'source';source.mkdir();(source/'LICENSE.md').write_text('CC0 1.0 Universal')
    subprocess.run(['git','init',str(source)],check=True,capture_output=True)
    subprocess.run(['git','-C',str(source),'-c','user.name=test','-c','user.email=test@example.com','commit','--allow-empty','-m','fixture'],check=True,capture_output=True)
    folder=source/'2024';folder.mkdir()
    path=folder/'br.2.json';payload=dict(name='Brasileiro Série B 2024',matches=[dict(date='2024-04-01',team1='A',team2='B',score={'ft':[1,0]})])
    path.write_text(json.dumps(payload));root=tmp_path/'data'
    report=collect(2024,2024,directory=source,json_directory=source,root=root)
    assert report['files'][0]['finals']==1
    target=root/'BR2_2024.json.gz';original=target.read_bytes()
    payload['matches'][0]['score']['ft']=[0,3];path.write_text(json.dumps(payload))
    report=collect(2024,2024,directory=source,json_directory=source,root=root)
    assert 'Conflicting' in report['errors'][0]['error']
    assert target.read_bytes()==original
    report=collect(2025,2025,directory=source,json_directory=source,root=root)
    assert report['errors'] and target.read_bytes()==original
