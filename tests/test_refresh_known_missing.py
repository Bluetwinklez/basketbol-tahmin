import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from bbtahmin.refresh_health import classify_errors, load_known_missing, refresh_exit_code
from scripts import refresh_sports


TODAY = date(2026, 11, 24)
EXCEPTION = dict(sport='basketball', league='PBA_GOV', reason='Repeated HTTP 503', review_by='2026-11-24')
FAILURE = dict(league='PBA_GOV', status='failed', error='HTTP 503')


def test_repository_nba_entry_classifies_by_league():
    path = Path(__file__).resolve().parents[1] / 'data' / 'refresh' / 'known_missing.json'
    entries = load_known_missing(path)
    blocked = dict(league='NBA', status='failed',
                   error='RuntimeError: HTTP 403: https://site.api.espn.com/robots.txt')
    different_error = dict(blocked, error='ValueError: Invalid scoreboard payload')

    assert classify_errors('basketball', [blocked, different_error], entries) == {
        'known_missing': [blocked, different_error],
        'unexpected': [],
    }


@pytest.mark.parametrize(('entry', 'error', 'expected'), [
    (EXCEPTION, FAILURE, 0),
    (dict(EXCEPTION, collector='other'), FAILURE, 1),
    (dict(EXCEPTION, sport='football'), FAILURE, 1),
    (EXCEPTION, dict(FAILURE, league='KBL'), 1),
    (dict(EXCEPTION, review_by='2026-11-23'), FAILURE, 1),
    (dict(EXCEPTION, review_by='2026-11-23'), None, 1),
])
def test_refresh_exit_code(tmp_path, entry, error, expected):
    path = tmp_path / 'known_missing.json'
    path.write_text(json.dumps([entry]), encoding='utf8')
    entries = load_known_missing(path)
    errors = [error] if error else []
    report = dict(status='partial' if errors else 'succeeded', errors=errors,
                  **classify_errors('basketball', errors, entries))
    assert refresh_exit_code({'basketball': report}, entries, TODAY) == expected
    assert report['known_missing'] + report['unexpected'] == errors


@pytest.mark.parametrize('payload', [
    {}, [None], [dict(EXCEPTION, review_by='2026-02-30')], [dict(EXCEPTION, review_by='20261124')],
    [dict(EXCEPTION, source=42)], [dict(EXCEPTION, typo='PBA_GOV')],
    [dict(sport='basketball', stage='current', reason='Repeated HTTP 503', review_by='2026-11-24')],
    [{key: value for key, value in EXCEPTION.items() if key != 'sport'}],
])
def test_malformed_known_missing_entry_raises_value_error(tmp_path, payload):
    path = tmp_path / 'known_missing.json'
    path.write_text(json.dumps(payload), encoding='utf8')
    with pytest.raises(ValueError):
        load_known_missing(path)


@pytest.mark.parametrize('whole_sport_failure', [False, True])
def test_refresh_writes_report_and_returns_exit_code(tmp_path, monkeypatch, whole_sport_failure):
    monkeypatch.chdir(tmp_path)
    directory = tmp_path / 'data' / 'refresh'
    directory.mkdir(parents=True)
    (directory / 'known_missing.json').write_text(
        json.dumps([dict(EXCEPTION, review_by='2099-01-01')]), encoding='utf8')

    def run(**kwargs):
        if whole_sport_failure:
            raise RuntimeError('offline')
        return dict(sources={'PBA_GOV': dict(status='failed', error='HTTP 503')})

    monkeypatch.setattr(refresh_sports, 'basketball_run', run)
    assert refresh_sports.refresh(SimpleNamespace(sport='basketball', backfill=False)) == int(whole_sport_failure)
    path, = directory.glob('*Z.json')
    report = json.loads(path.read_text(encoding='utf8'))['basketball']
    assert report['unexpected'] == []
    if whole_sport_failure:
        assert report == dict(status='failed', error='RuntimeError: offline', known_missing=[], unexpected=[])
    else:
        assert report == dict(status='partial', errors=[FAILURE], known_missing=[FAILURE], unexpected=[])
