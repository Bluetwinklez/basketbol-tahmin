import sys
from pathlib import Path

import pytest

from bbtahmin.football.data import row
from bbtahmin.football.screenshots import save


def fixture():
    return row('AR2', '2026', '2026-10-01', 'A', 'B', [1, 0], 'source', '2026-10-25')


def test_existing_file_does_not_hide_duplicate_incoming_rows(tmp_path):
    a = fixture()
    save([a], 'AR2', '2026', tmp_path)
    path = tmp_path / 'AR2_2026.json.gz'
    original = path.read_bytes()
    for rows in ([a, a], [a, dict(a, home_goals=2)],
                 [a, dict(a, event_id='different-provider-id')]):
        with pytest.raises(ValueError, match='Duplicate'):
            save(rows, 'AR2', '2026', tmp_path)
        assert path.read_bytes() == original


def test_wrong_season_or_changed_identity_cannot_replace_snapshot(tmp_path):
    a = fixture()
    save([a], 'AR2', '2026', tmp_path)
    path = tmp_path / 'AR2_2026.json.gz'
    original = path.read_bytes()
    for changed in (dict(a, season='2025'), dict(a, league='AR1'), dict(a, away='c')):
        with pytest.raises(ValueError):
            save([changed], 'AR2', '2026', tmp_path)
        assert path.read_bytes() == original


def test_partial_refresh_keeps_final_and_does_not_downgrade(tmp_path):
    import gzip
    import json
    a = fixture()
    save([a], 'AR2', '2026', tmp_path)
    save([dict(a, status='scheduled', home_goals=None, away_goals=None)], 'AR2', '2026', tmp_path)
    save([], 'AR2', '2026', tmp_path)
    assert json.loads(gzip.decompress((tmp_path/'AR2_2026.json.gz').read_bytes()))['rows'] == [a]


def test_source_failure_does_not_stop_other_collectors_or_settlement(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    import refresh_sports
    import refresh_screenshot_leagues
    calls = []
    def fail(*args, **kwargs):
        raise RuntimeError('upstream unavailable')
    monkeypatch.setattr(refresh_screenshot_leagues, 'run', fail)
    monkeypatch.setattr(refresh_sports, 'collect', fail)
    def calendar(**kwargs):
        calls.append(kwargs['code'])
        if kwargs['code'] == 'BR2': raise RuntimeError('calendar outage')
        return dict(errors=[])
    monkeypatch.setattr(refresh_sports, 'calendar_collect', calendar)
    monkeypatch.setattr(refresh_sports, 'football_run', lambda **kwargs: calls.append('settled') or {})
    reports = []
    monkeypatch.setattr(refresh_sports, 'write_json', lambda path, value: reports.append(value))
    monkeypatch.setattr(sys, 'argv', ['refresh_sports', '--sport', 'football'])
    assert refresh_sports.main() == 1
    assert calls == ['BR2','BR1','AR1','CO1','US1','JP1','CN1','settled']
    assert reports[0]['football']['status'] == 'partial'
    assert len(reports[0]['football']['errors']) == 3


@pytest.mark.parametrize('captured,issue', [
    ('2026-10-23T15:00Z', 'future'),
    ('2026-10-23T12:00', 'timezone'),
])
def test_future_or_naive_fixture_capture_is_not_frozen(tmp_path, monkeypatch, captured, issue):
    import pandas as pd
    from bbtahmin.football import daily
    from bbtahmin.football.data import write_json
    game=row('AR2','2026','2026-10-25','A','B',None,'source',captured)
    monkeypatch.setattr(daily,'load',lambda root:pd.DataFrame([game]))
    write_json(tmp_path/'collection.json',dict(checked_at_utc=captured,errors=[]))
    result=daily.run(require_fixture_confirmation=False, output=tmp_path/'ledger',root=tmp_path,now='2026-10-23T13:00Z')
    assert result['pending']==0 and issue in result['skipped'][0]['reason']


def test_stale_team_history_cannot_enter_prospective_ledger(tmp_path, monkeypatch):
    import pandas as pd
    from bbtahmin.football import daily, challenger
    from bbtahmin.football.data import write_json
    game=row('AR2','2026','2026-10-25','A','B',None,'source','2026-10-23T12:00Z')
    monkeypatch.setattr(daily,'load',lambda root:pd.DataFrame([game]))
    class Model:
        def predict(self,*args):return dict(issues=['a: history older than 90 days'])
    monkeypatch.setattr(challenger,'fit',lambda *args:Model())
    write_json(tmp_path/'collection.json',dict(checked_at_utc='2026-10-23T12:00Z',errors=[]))
    result=daily.run(require_fixture_confirmation=False, output=tmp_path/'ledger',root=tmp_path,now='2026-10-23T13:00Z')
    assert result['pending']==0 and 'Insufficient history' in result['skipped'][0]['reason']
