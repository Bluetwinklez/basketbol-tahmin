import copy
import json
from pathlib import Path

import pandas as pd
import pytest

from bbtahmin import daily
from bbtahmin.prospective import verify


def fixture():
    return dict(event_id='JP_B1_123', league='JP_B1', home='H', away='A',
                home_name='Home', away_name='Away', start_utc='2026-10-23T17:00:00Z',
                captured_at='2026-10-23T10:00:00Z', source_url='https://www.bleague.jp/game_detail/?ScheduleKey=123',
                status='scheduled')


def prediction():
    return dict(lig='JP_B1', ev='H', dep='A', tarih_utc='2026-10-23T17:00:00Z', model='test',
                ev_kazanir=.7, ev_skor=90., dep_skor=80., fark=10., toplam=170.,
                fark_80=[-5.,25.], toplam_80=[140.,200.], selection_eligible=True)


def setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f, p = fixture(), prediction()
    monkeypatch.setattr(daily, 'source_facts', lambda code: ([copy.deepcopy(f)], []))
    from bbtahmin import tahmin
    monkeypatch.setattr(tahmin, 'tahmin_et', lambda *a, **k: [copy.deepcopy(p)])
    return f, p


def test_daily_freezes_once_and_keeps_first_prediction(tmp_path, monkeypatch):
    f, p = setup(tmp_path, monkeypatch)
    first = daily.run(['JP_B1'], now='2026-10-23T12:00Z')
    path = Path(first['upcoming'][0]['record'])
    original = path.read_bytes()
    p['ev_skor'], p['dep_skor'] = 100., 70.
    again = daily.run(['JP_B1'], now='2026-10-23T13:00Z')
    assert path.read_bytes() == original
    assert verify(json.loads(original))
    assert again['upcoming'][0]['prediction']['ev_skor'] == 90.
    assert again['upcoming'][0]['record_status'] == 'existing_immutable'
    assert again['performance']['winner_accuracy'] is None
    assert again['performance']['pending_games'] == 1
    assert 'not available' in Path('rapor/daily/latest.md').read_text()


def test_daily_final_settlement_reports_all_errors_and_does_not_count_pending(tmp_path, monkeypatch):
    f, p = setup(tmp_path, monkeypatch)
    before = daily.run(['JP_B1'], now='2026-10-23T12:00Z')
    original = Path(before['upcoming'][0]['record']).read_bytes()
    final = dict(f, status='final', captured_at='2026-10-23T20:00Z', home_score=85, away_score=82)
    monkeypatch.setattr(daily, 'source_facts', lambda code: ([], [final]))
    after = daily.run(['JP_B1'], now='2026-10-23T21:00Z')
    perf = after['performance']
    assert perf == dict(settled_games=1, pending_games=0, winner_accuracy=1.,
                        mean_score_mae=3.5, mean_total_absolute_error=3., mean_margin_absolute_error=7.)
    game = after['settlements'][0]['games'][0]
    assert game['home_signed_error'] == 5 and game['away_signed_error'] == -2
    assert game['total_in_80'] and game['margin_in_80']
    assert Path(before['upcoming'][0]['record']).read_bytes() == original


@pytest.mark.parametrize('change', ['stale', 'started', 'unconfirmed', 'future_capture'])
def test_daily_never_freezes_invalid_fixture(tmp_path, monkeypatch, change):
    f, _ = setup(tmp_path, monkeypatch)
    if change == 'stale': f['captured_at'] = '2026-10-20T10:00Z'
    if change == 'started': f['start_utc'] = '2026-10-23T11:00Z'
    if change == 'unconfirmed': f['status'] = 'live'
    if change == 'future_capture': f['captured_at'] = '2026-10-24T10:00Z'
    result = daily.run(['JP_B1'], now='2026-10-23T12:00Z')
    assert not result['upcoming']
    assert not list(Path('rapor/daily').rglob('forecasts/*.json'))


def test_changed_fixture_does_not_replace_record(tmp_path, monkeypatch):
    f, _ = setup(tmp_path, monkeypatch)
    first = daily.run(['JP_B1'], now='2026-10-23T12:00Z')
    original = Path(first['upcoming'][0]['record']).read_bytes()
    f['away'] = 'OTHER'
    after = daily.run(['JP_B1'], now='2026-10-23T13:00Z')
    assert not after['upcoming'] and 'Fixture changed' in after['skipped'][0]['reason']
    assert Path(first['upcoming'][0]['record']).read_bytes() == original


def test_source_failure_cannot_make_new_forecast(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(daily, 'refresh', lambda leagues: {'JP_B1': dict(status='failed', error='HTTP 403')})
    result = daily.run(['JP_B1'], update=True)
    assert not result['upcoming']
    assert 'HTTP 403' in Path('rapor/daily/latest.md').read_text()


def test_stale_existing_record_remains_visible_but_is_not_selected(tmp_path, monkeypatch):
    f, _ = setup(tmp_path, monkeypatch)
    daily.run(['JP_B1'], now='2026-10-23T12:00Z')
    f['captured_at'] = '2026-10-20T10:00Z'
    after = daily.run(['JP_B1'], now='2026-10-23T13:00Z')
    assert len(after['upcoming']) == 1
    assert not after['upcoming'][0]['source_confirmation_fresh']
    assert not after['upcoming'][0]['selected']


def test_day_only_final_cannot_settle_timestamped_fixture(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = Path('data/asia'); root.mkdir(parents=True)
    base = dict(mac_id='PBA_SM_game', lig='PBA_GOV', ev='H', dep='A', tarih_utc=pd.Timestamp('2026-10-23T00:00Z'),
                captured_at_utc='2026-10-23T20:00Z', source_url='https://example.org/game', date_precision='day',
                ev_skor=80, dep_skor=75)
    pd.DataFrame([base]).to_parquet(root/'PBA_GOV.parquet')
    pd.DataFrame([dict(base, status='scheduled')]).to_parquet(root/'PBA_GOV_fixtures.parquet')
    fixtures, finals = daily.source_facts('PBA_GOV')
    assert len(fixtures) == 1 and not finals


def test_euro_schedule_checks_season_identity_and_duplicate_ids():
    from bbtahmin.euro_facts import facts
    team = lambda code: dict(club=dict(code=code, name=code), score=0)
    row = dict(identifier='E2026_1', season=dict(code='E2026'), utcDate='2026-10-23T17:00Z',
               local=team('H'), road=team('A'), played=False, confirmedDate=True, confirmedHour=True, gameStatus='Confirmed')
    payload = dict(data=[row], total=1)
    fixtures, finals = facts(payload, '2026-10-23T12:00Z', 'E2026', 'https://example.org')
    assert len(fixtures) == 1 and not finals
    with pytest.raises(ValueError, match='Wrong official season'):
        facts(payload, '2026-10-23T12:00Z', 'E2025', 'https://example.org')
    with pytest.raises(ValueError, match='Duplicate official fixture'):
        facts(dict(data=[row,row], total=2), '2026-10-23T12:00Z', 'E2026', 'https://example.org')


def test_daily_reuses_project_forecast_and_counts_duplicate_ledger_once(tmp_path, monkeypatch):
    from bbtahmin.prospective import freeze
    f, p = setup(tmp_path, monkeypatch)
    path=Path('docs/kanit/prospective/original.json')
    freeze([p],[f],path,now='2026-10-23T11:00Z')
    path.with_name('fixtures.json').write_text(json.dumps([f]))
    duplicate=Path('rapor/daily/forecasts/later.json')
    freeze([dict(p, ev_kazanir=.9)],[f],duplicate,now='2026-10-23T11:30Z')
    from bbtahmin import tahmin
    monkeypatch.setattr(tahmin, 'tahmin_et', lambda *a, **k: pytest.fail('Known fixture must not be predicted again'))
    report=daily.run(['JP_B1'],now='2026-10-23T12:00Z')
    assert report['upcoming'][0]['record']==str(path)
    assert report['upcoming'][0]['prediction']['ev_kazanir']==.7
    assert report['performance']['pending_games']==1
    assert len(report['settlements'])==1


def test_damaged_existing_record_cannot_be_silently_replaced(tmp_path,monkeypatch):
    setup(tmp_path,monkeypatch)
    before=daily.run(['JP_B1'],now='2026-10-23T12:00Z')
    path=Path(before['upcoming'][0]['record'])
    record=json.loads(path.read_text());record['forecasts'][0]['prediction']['ev_kazanir']=.99
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError,match='Invalid existing forecast record'):
        daily.run(['JP_B1'],now='2026-10-23T13:00Z')
