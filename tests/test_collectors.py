import json
from bbtahmin.veri.euroleague import collect
from bbtahmin.veri.http import CachedHTTP
def test_euroleague_fixture():
    game=dict(played=True,identifier='E2020_1',utcDate='2020-10-01T18:00:00Z',
        phaseType={'code':'FF'},local=dict(club={'code':'A'},score=90,partials={'partials1':20,'partials2':25,'extraPeriods':{}}),
        road=dict(club={'code':'B'},score=80,partials={'partials1':20,'partials2':20,'extraPeriods':{}}))
    class HTTP:
        def get(self,url):return json.dumps(dict(data=[game],total=1))
    rows,details=collect(HTTP(),'E',2020)
    assert rows[0]['ev_iy']==45 and rows[0]['tarafsiz_saha'] and details['played']==1
    game['phaseType']['code']='Final'
    assert collect(HTTP(),'U',2020)[0][0]['asama']=='playoff'
def test_cache_no_network(tmp_path,monkeypatch):
    import hashlib
    from pathlib import Path
    monkeypatch.chdir(tmp_path)
    url='https://example.test/a'
    path=Path('data/raw/example.test')/hashlib.sha256(url.encode()).hexdigest()
    path.parent.mkdir(parents=True)
    path.write_bytes(b'cached')
    path.with_suffix('.json').write_text('{"status":200}')
    def forbidden(*a,**k):raise AssertionError('Ağ çağrısı olmamalı')
    monkeypatch.setattr('subprocess.run',forbidden)
    assert CachedHTTP().get(url)==b'cached'
