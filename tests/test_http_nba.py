import json
from pathlib import Path
from bbtahmin.veri.http import CachedHTTP

def test_rate_limit_and_fixed_spacing(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    clock=[100.]
    starts=[]
    monkeypatch.setattr('time.monotonic',lambda:clock[0])
    monkeypatch.setattr('time.sleep',lambda n:clock.__setitem__(0,clock[0]+n))
    def fake_run(args,**kwargs):
        starts.append(clock[0])
        Path(args[3]).write_bytes(b'ok')
        class Result:
            returncode=0
            stdout=json.dumps({'status':200,'url':args[2]})
        return Result()
    monkeypatch.setattr('subprocess.run',fake_run)
    http=CachedHTTP()
    for i in range(40):
        http.get(f'https://example.test/{i}',nba=True,robots=False)
    assert all(b-a>=6.099 for a,b in zip(starts,starts[1:]))
    assert all(sum(t<=s<t+60 for s in starts)<=10 for t in starts)

def test_429_stops_host(tmp_path,monkeypatch):
    import pytest
    monkeypatch.chdir(tmp_path)
    calls=[]
    def fake_run(args,**kwargs):
        calls.append(args)
        Path(args[3]).write_bytes(b'blocked')
        class Result:
            returncode=0
            stdout=json.dumps({'status':429,'url':args[2]})
        return Result()
    monkeypatch.setattr('subprocess.run',fake_run)
    http=CachedHTTP()
    with pytest.raises(RuntimeError,match='429'):http.get('https://example.test/a',robots=False)
    with pytest.raises(RuntimeError,match='429'):http.get('https://example.test/b',robots=False)
    assert len(calls)==1

def test_explicit_refresh_replaces_stale_success_cache(tmp_path,monkeypatch):
    import hashlib
    monkeypatch.chdir(tmp_path)
    url='https://example.test/current-season'
    path=Path('data/raw/example.test')/hashlib.sha256(url.encode()).hexdigest()
    path.parent.mkdir(parents=True)
    path.write_bytes(b'old')
    path.with_suffix('.json').write_text('{"status":200}')
    calls=[]
    def fake_run(args,**kwargs):
        calls.append(args)
        Path(args[3]).write_bytes(b'new')
        class Result:
            returncode=0
            stdout=json.dumps({'status':200,'url':args[2]})
        return Result()
    monkeypatch.setattr('subprocess.run',fake_run)
    http=CachedHTTP()
    assert http.get(url,robots=False)==b'old'
    assert http.get(url,robots=False,refresh=True)==b'new'
    assert http.get(url,robots=False)==b'new'
    assert len(calls)==1

def test_nba_schedule_fixture():
    from bbtahmin.veri.nba_bref import collect
    base='<div class="filter"><a href="/leagues/NBA_2025_games-october.html">Oct</a></div>'
    body='<table id="schedule"><tbody><tr>'
    fields={'date_game':'date','game_start_time':'7:30p','home_team_name':'Boston Celtics',
        'visitor_team_name':'New York Knicks','home_pts':'132','visitor_pts':'109','overtimes':''}
    for key,value in fields.items():
        extra=' csk="202410220BOS"' if key=='date_game' else ''
        body+=f'<td data-stat="{key}"{extra}>{value}</td>'
    body+='</tr></tbody></table>'
    class HTTP:
        def get(self,url,**kwargs):return (base if url.endswith('games.html') else body).encode()
    rows,details=collect(HTTP(),2024)
    assert len(rows)==1 and rows[0]['ev']=='BOS' and not details['partial']
    assert rows[0]['tarih_utc'].isoformat()=='2024-10-22T23:30:00+00:00'

    base2='<div class="filter"><a href="/leagues/NBA_2025_games-april.html">Apr</a><a href="/leagues/NBA_2025_games-may.html">May</a></div>'
    april=body.replace('202410220BOS','202504180BOS').replace('<tbody>','<tbody><tr><th>Playoffs</th></tr>')
    may=body.replace('202410220BOS','202505010BOS')
    class MultiHTTP:
        def get(self,url,**kwargs):
            return (base2 if url.endswith('games.html') else april if 'april' in url else may).encode()
    postseason,_=collect(MultiHTTP(),2024)
    assert len(postseason)==2 and all(r['asama']=='playoff' for r in postseason)
