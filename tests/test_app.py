import csv
import io
import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from bbtahmin.app import AppServer, AppState, export_csv, options


def report():
    return dict(spec='daily-research-v1',checked_at_utc='2026-10-23T12:00:00+00:00',
                upcoming=[],skipped=[],sources={},settlements=[],
                performance=dict(settled_games=0,pending_games=0,winner_accuracy=None,mean_score_mae=None),note='Test report')


@pytest.fixture
def local_app(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    state=AppState(tmp_path/'ledger',runner=lambda **kwargs:report())
    server=AppServer(port=0,state=state)
    thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True);thread.start()
    yield server,state
    server.shutdown();server.server_close();thread.join(timeout=2)


def request(server,path='/',data=None,headers=None):
    if data is not None:data=json.dumps(data).encode()
    req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}{path}',data=data,headers=headers or {})
    try:
        response=urllib.request.urlopen(req,timeout=3)
    except urllib.error.HTTPError as exc:response=exc
    with response:return response.status,response.headers,response.read()


def wait_job(state):
    deadline=time.monotonic()+3
    while state.snapshot()['job']['status']=='running' and time.monotonic()<deadline:time.sleep(.01)
    return state.snapshot()


def test_app_serves_packaged_assets_without_exposing_files(local_app):
    server,state=local_app
    status,headers,html=request(server)
    assert status==200 and state.token.encode() in html and b'__CSRF_TOKEN__' not in html
    assert "frame-ancestors 'none'" in headers['Content-Security-Policy']
    for asset in ('app.js','app.css'):assert request(server,'/'+asset)[0]==200
    assert request(server,'/../pyproject.toml')[0]==404
    assert request(server,'/api/export.json')[0]==404


def test_job_runs_in_background_and_exports_real_report(local_app):
    server,state=local_app;seen={}
    def run(**kwargs):seen.update(kwargs);return report()
    state.runner=run
    status,_,_=request(server,'/api/run',dict(leagues=['E'],hours=24,threshold=.7,refresh=False),
                       {'Content-Type':'application/json','X-App-Token':state.token})
    assert status==202
    snapshot=wait_job(state)
    assert snapshot['job']['status']=='succeeded' and not snapshot['sample']
    assert seen['leagues']==['E'] and seen['hours']==24 and seen['update'] is False
    assert request(server,'/api/export.csv')[0]==200
    assert request(server,'/api/export.md')[0]==200
    assert json.loads(request(server,'/api/export.json')[2])['report']['performance']['winner_accuracy'] is None


def test_only_one_model_job_can_run_and_failures_preserve_report(local_app):
    server,state=local_app;entered=threading.Event();release=threading.Event();original=report();state.report=original
    def blocked(**kwargs):
        entered.set();release.wait(timeout=2);raise ValueError('source unavailable')
    state.runner=blocked;state.submit(dict(leagues=['E']))
    assert entered.wait(timeout=1)
    try:
        with pytest.raises(RuntimeError,match='already in progress'):state.submit(dict(leagues=['E']))
        assert request(server,'/api/state')[0]==200
    finally:release.set()
    snapshot=wait_job(state)
    assert snapshot['job']['status']=='failed' and snapshot['report']==original
    assert 'source unavailable' in snapshot['job']['message']


def test_cross_origin_bad_host_and_missing_token_are_rejected(local_app):
    server,state=local_app
    assert request(server,headers={'Host':'attacker.example'})[0]==403
    assert request(server,'/api/run',dict(leagues=['E']),{'Content-Type':'application/json'})[0]==403
    assert request(server,'/api/run',dict(leagues=['E']),{'Content-Type':'application/json',
        'X-App-Token':state.token,'Origin':'https://attacker.example'})[0]==403
    assert state.job['status']=='idle'


@pytest.mark.parametrize('payload',[
    dict(leagues=[]),dict(leagues=['WNBL']),dict(hours=True),dict(hours=169),dict(hours=1.5),
    dict(threshold=float('nan')),dict(threshold=True),dict(threshold=1.01),dict(refresh='yes'),
    dict(output='/tmp/elsewhere'),[],
])
def test_run_options_reject_unsupported_inputs(payload):
    with pytest.raises(ValueError):options(payload)


def test_unresolved_source_outcomes_are_partial_not_success(local_app):
    _,state=local_app
    def partial(**kwargs):
        value=report();value['sources']={'E':dict(status='failed',error='HTTP 403')};return value
    state.runner=partial;state.submit(dict(leagues=['E']))
    assert wait_job(state)['job']['status']=='partial'


def test_csv_export_has_point_errors_and_neutralizes_formula_names():
    row=dict(fixture=dict(league='E',home_name='=FORMULA()',away_name='Away'),
             prediction=dict(ev_skor=90.,dep_skor=80.),
             game=dict(event_id='game',home='H',away='A',status='final',actual_home=85,actual_away=82,
                       winner_correct=True,home_absolute_error=5.,away_absolute_error=2.,
                       total_absolute_error=3.,margin_absolute_error=7.,total_in_80=True,margin_in_80=True))
    rows=list(csv.DictReader(io.StringIO(export_csv(report(),[row]).decode('utf-8-sig'))))
    assert rows[0]['home']=="'=FORMULA()" and rows[0]['margin_absolute_error']=='7.0'
