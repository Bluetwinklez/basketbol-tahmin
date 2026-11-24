import json
from pathlib import Path

import pandas as pd

from bbtahmin import daily, euro_facts, tahmin
from bbtahmin.prospective import verify


SNAPSHOT = Path('data/schedules/E.json')


def euro_game(identifier, season, utc_date, home=('ULK', 'Fenerbahce Beko'),
              away=('IST', 'Anadolu Efes'), *, played=False, scores=(0, 0)):
    return dict(
        identifier=identifier,
        season=dict(code=season),
        utcDate=utc_date,
        local=dict(club=dict(code=home[0], name=home[1]), score=scores[0]),
        road=dict(club=dict(code=away[0], name=away[1]), score=scores[1]),
        played=played,
        confirmedDate=True,
        confirmedHour=True,
        gameStatus='Confirmed',
    )


def write_euro_snapshot(rows, captured_at, season):
    url = daily.EURO_URL.format(season=season)
    payload = dict(data=rows, total=len(rows))
    fixtures, results = euro_facts.facts(payload, captured_at, season, url)
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(dict(fixtures=fixtures, results=results), indent=2), encoding='utf8')
    return fixtures, results


def make_prediction(league, home, away, start_utc, *, ev_skor=88.0, dep_skor=78.0, ev_kazanir=0.72):
    fark = ev_skor - dep_skor
    toplam = ev_skor + dep_skor
    return dict(
        lig=league,
        ev=home,
        dep=away,
        tarih_utc=start_utc,
        model='test',
        ev_kazanir=ev_kazanir,
        ev_skor=ev_skor,
        dep_skor=dep_skor,
        fark=fark,
        toplam=toplam,
        fark_80=[fark - 14.0, fark + 14.0],
        toplam_80=[toplam - 21.0, toplam + 21.0],
        selection_eligible=True,
    )


def test_daily_euroleague_e2e_freeze_reuse_and_settlement(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    season = 'E2026'
    start_utc = '2026-10-23T18:00:00Z'
    write_euro_snapshot(
        [euro_game('E2026_101', season, start_utc)],
        captured_at='2026-10-23T10:00:00Z',
        season=season,
    )

    calls = []
    scores = dict(ev_skor=88.0, dep_skor=78.0)

    def predict(league, teams, start):
        calls.append((league, teams, start))
        home, away = teams[0]
        return [make_prediction(league, home, away, start, **scores)]

    monkeypatch.setattr(tahmin, 'tahmin_et', predict)

    # First run creates an immutable forecast record.
    first = daily.run(['E'], now='2026-10-23T12:00Z')
    assert len(first['upcoming']) == 1
    assert first['upcoming'][0]['record_status'] == 'new_immutable'
    assert first['upcoming'][0]['selected'] is True
    assert first['performance']['settled_games'] == 0
    assert first['performance']['pending_games'] == 1
    assert first['performance']['winner_accuracy'] is None
    assert calls == [('E', [('ULK', 'IST')], '2026-10-23T18:00:00+00:00')]

    record_file = Path(first['upcoming'][0]['record'])
    assert record_file.exists()
    original_bytes = record_file.read_bytes()
    assert verify(json.loads(original_bytes))
    assert Path('rapor/daily/latest.md').exists()
    assert len(list(Path('rapor/daily').glob('check_*.json'))) == 1

    # Second run reuses the same immutable record without modifying it or re-predicting.
    scores.update(ev_skor=99.0, dep_skor=69.0)
    second = daily.run(['E'], now='2026-10-23T13:00Z')
    assert len(second['upcoming']) == 1
    assert second['upcoming'][0]['record'] == str(record_file)
    assert second['upcoming'][0]['record_status'] == 'existing_immutable'
    assert second['upcoming'][0]['prediction']['ev_skor'] == 88.0
    assert second['upcoming'][0]['prediction']['dep_skor'] == 78.0
    assert second['performance']['settled_games'] == 0
    assert second['performance']['pending_games'] == 1
    assert record_file.read_bytes() == original_bytes
    assert len(calls) == 1

    # Separate run settles the frozen forecast once the final result is available.
    write_euro_snapshot(
        [euro_game('E2026_101', season, start_utc, played=True, scores=(86, 80))],
        captured_at='2026-10-23T21:00:00Z',
        season=season,
    )
    settled = daily.run(['E'], now='2026-10-23T22:00Z')
    assert not settled['upcoming']
    assert settled['performance'] == dict(
        settled_games=1,
        pending_games=0,
        winner_accuracy=1.0,
        mean_score_mae=2.0,
        mean_total_absolute_error=0.0,
        mean_margin_absolute_error=4.0,
    )
    game = settled['settlements'][0]['games'][0]
    assert game['event_id'] == 'E2026_101'
    assert game['status'] == 'final'
    assert game['actual_home'] == 86
    assert game['actual_away'] == 80
    assert game['winner_correct'] is True
    assert game['home_signed_error'] == 2.0
    assert game['away_signed_error'] == -2.0
    assert game['total_in_80'] is True
    assert game['margin_in_80'] is True
    assert record_file.read_bytes() == original_bytes


def test_daily_euroleague_source_failure_blocks_new_forecast_and_preserves_existing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base_now = pd.Timestamp.now(tz='UTC').floor('s')
    year = base_now.year if base_now.month >= 7 else base_now.year - 1
    season = f'E{year}'

    existing_game = euro_game(
        f'{season}_201',
        season,
        (base_now + pd.Timedelta(hours=6)).isoformat(),
        home=('ULK', 'Fenerbahce Beko'),
        away=('IST', 'Anadolu Efes'),
    )
    write_euro_snapshot(
        [existing_game],
        captured_at=(base_now - pd.Timedelta(minutes=10)).isoformat(),
        season=season,
    )

    calls = []

    def predict(league, teams, start):
        calls.append((league, teams, start))
        home, away = teams[0]
        return [make_prediction(league, home, away, start)]

    monkeypatch.setattr(tahmin, 'tahmin_et', predict)

    first = daily.run(['E'])
    assert len(first['upcoming']) == 1
    assert first['upcoming'][0]['record_status'] == 'new_immutable'
    existing_record = Path(first['upcoming'][0]['record'])
    original_bytes = existing_record.read_bytes()
    assert len(calls) == 1

    # Add a second future game to the local snapshot, then fail source refresh.
    new_game = euro_game(
        f'{season}_202',
        season,
        (base_now + pd.Timedelta(hours=8)).isoformat(),
        home=('MAD', 'Real Madrid'),
        away=('BAR', 'FC Barcelona'),
    )
    write_euro_snapshot(
        [existing_game, new_game],
        captured_at=(base_now - pd.Timedelta(minutes=5)).isoformat(),
        season=season,
    )
    monkeypatch.setattr(
        daily,
        'refresh',
        lambda leagues: {'E': dict(status='failed', error='RuntimeError: HTTP 503')},
    )

    failed = daily.run(['E'], update=True)
    assert failed['sources']['E']['status'] == 'failed'
    assert existing_record.read_bytes() == original_bytes
    assert list(Path('rapor/daily/forecasts').glob('*.json')) == [existing_record]
    assert len(calls) == 1
    assert len(failed['upcoming']) == 1
    assert failed['upcoming'][0]['fixture']['event_id'] == f'{season}_201'
    assert failed['upcoming'][0]['record_status'] == 'existing_immutable'
    assert failed['upcoming'][0]['source_confirmation_fresh'] is False
    assert failed['upcoming'][0]['selected'] is False
    assert any(
        item.get('event_id') == f'{season}_202' and 'Refresh failed' in item['reason']
        for item in failed['skipped']
    )
    assert 'HTTP 503' in Path('rapor/daily/latest.md').read_text(encoding='utf8')
