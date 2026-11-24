import json
import threading
import urllib.error
import urllib.request

import pytest

from bbtahmin.app import AppServer, AppState


def _sample_scorecard():
    return {
        'spec': 'live-scorecard-v1',
        'data_cutoff_utc': '2026-11-23T18:40:38+00:00',
        'definitions': {'cohort': 'Test cohort'},
        'sports': {
            'basketball': {
                'cutoff_utc': '2026-11-23T18:39:45+00:00',
                'class_order': ['home', 'away'],
                'total': {},
                'leagues': {},
            },
            'football': {
                'cutoff_utc': '2026-11-23T18:40:38+00:00',
                'class_order': ['home', 'draw', 'away'],
                'total': {},
                'leagues': {},
            },
        },
    }


@pytest.fixture
def local_app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    state = AppState(tmp_path / 'ledger', runner=lambda **kwargs: {})
    server = AppServer(port=0, state=state)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.01), daemon=True)
    thread.start()
    yield server, tmp_path
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def _request(server, path, headers=None):
    req = urllib.request.Request(f'http://127.0.0.1:{server.server_port}{path}', headers=headers or {})
    try:
        response = urllib.request.urlopen(req, timeout=3)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        return response.status, response.headers, response.read()


def test_performance_page_and_script_are_served(local_app):
    server, _ = local_app
    status, headers, html = _request(server, '/performance')
    assert status == 200
    assert 'text/html' in headers['Content-Type']
    assert "frame-ancestors 'none'" in headers['Content-Security-Policy']
    assert b'/performance.js' in html
    assert b'/app.css' in html
    assert b'Baselines are on the same games. This is not evidence of beating the market.' in html

    js_status, js_headers, js_body = _request(server, '/performance.js')
    assert js_status == 200
    assert 'text/javascript' in js_headers['Content-Type']
    assert b'/api/performance' in js_body


def test_api_performance_returns_404_when_scorecard_missing_or_invalid(local_app):
    server, tmp_path = local_app
    status, _, body = _request(server, '/api/performance')
    assert status == 404
    assert 'error' in json.loads(body)

    scorecard_path = tmp_path / 'docs' / 'kanit' / 'live_scorecard' / 'scorecard.json'
    scorecard_path.parent.mkdir(parents=True, exist_ok=True)
    scorecard_path.write_text('{not valid json', encoding='utf8')
    assert _request(server, '/api/performance')[0] == 404

    scorecard_path.write_text(json.dumps({'spec': 'wrong-spec'}), encoding='utf8')
    assert _request(server, '/api/performance')[0] == 404


def test_api_performance_serves_valid_scorecard_json(local_app):
    server, tmp_path = local_app
    scorecard_path = tmp_path / 'docs' / 'kanit' / 'live_scorecard' / 'scorecard.json'
    scorecard_path.parent.mkdir(parents=True, exist_ok=True)
    expected = _sample_scorecard()
    scorecard_path.write_text(json.dumps(expected), encoding='utf8')

    status, headers, body = _request(server, '/api/performance')
    assert status == 200
    assert 'application/json' in headers['Content-Type']
    assert json.loads(body) == expected


def test_performance_routes_reject_bad_host(local_app):
    server, _ = local_app
    assert _request(server, '/performance', headers={'Host': 'attacker.example'})[0] == 403
    assert _request(server, '/api/performance', headers={'Host': 'attacker.example'})[0] == 403
