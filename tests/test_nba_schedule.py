import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from bbtahmin import daily, tahmin
from bbtahmin.veri import nba_schedule


NOW = '2026-11-24T01:00:00Z'
SOURCE = f'{nba_schedule.ESPN}?dates=20261123'
SNAPSHOT = Path('data/schedules/NBA.json')


def event(event_id, date, state, name, completed=False, codes=('BKN', 'PHX'), scores=(None, None)):
    competitors = [
        dict(homeAway='away', team=dict(abbreviation=codes[1], displayName='Away Team')),
        dict(homeAway='home', team=dict(abbreviation=codes[0], displayName='Home Team')),
    ]
    if scores[0] is not None:
        competitors[0]['score'], competitors[1]['score'] = map(str, reversed(scores))
    return dict(id=event_id, date=date, competitions=[dict(
        competitors=competitors, status=dict(type=dict(state=state, name=name, completed=completed)))])


def scoreboard(*events):
    return dict(leagues=[dict(abbreviation='NBA')], events=list(events))


def scheduled():
    return event('401001', '2026-11-24T02:00Z', 'pre', 'STATUS_SCHEDULED')


def final():
    return event('401002', '2026-11-23T00:00Z', 'post', 'STATUS_FINAL',
                 completed=True, codes=('GS', 'NY'), scores=(112, 107))


def test_parse_scheduled_and_final_event_provenance():
    live = event('401003', '2026-11-24T00:30Z', 'in', 'STATUS_IN_PROGRESS', scores=(41, 34))
    postponed = event('401004', '2026-11-24T03:00Z', 'pre', 'STATUS_POSTPONED')
    fixtures, results = nba_schedule.parse_espn(scoreboard(scheduled(), final(), live, postponed), NOW, SOURCE)
    assert fixtures == [dict(event_id='401001', league='NBA', home='BRK', away='PHO',
                             home_name='Home Team', away_name='Away Team',
                             start_utc='2026-11-24T02:00:00+00:00', captured_at='2026-11-24T01:00:00+00:00',
                             source_url=SOURCE, status='scheduled')]
    assert results == [dict(event_id='401002', league='NBA', home='GSW', away='NYK',
                            home_name='Home Team', away_name='Away Team',
                            start_utc='2026-11-23T00:00:00+00:00', captured_at='2026-11-24T01:00:00+00:00',
                            source_url=SOURCE, status='final', home_score=112, away_score=107)]


def test_unknown_tricodes_are_reported_together():
    unknown = event('401005', '2026-11-24T02:00Z', 'pre', 'STATUS_SCHEDULED', codes=('ZZZ', 'XYZ'))
    with pytest.raises(ValueError, match='Unknown ESPN NBA team tricodes: XYZ, ZZZ'):
        nba_schedule.parse_espn(scoreboard(scheduled(), unknown), NOW, SOURCE)


def test_refresh_fetches_dated_boards_and_keeps_snapshot_on_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    clock = pd.Timestamp(NOW)
    monkeypatch.setattr(nba_schedule, 'pd', SimpleNamespace(
        Timestamp=SimpleNamespace(now=lambda tz: clock.tz_convert(tz))))
    calls = []

    def get(self, url, nba=False, robots=True, refresh=False):
        assert nba and robots and refresh
        calls.append(url)
        if url.endswith('20261122'):
            payload = scoreboard(final())
        elif url == SOURCE:
            payload = scoreboard(scheduled())
        else:
            payload = scoreboard()
        return json.dumps(payload).encode()

    monkeypatch.setattr(nba_schedule.CachedHTTP, 'get', get)
    assert daily.refresh(['NBA'])['NBA']['status'] == 'refreshed'
    assert calls == [f'{nba_schedule.ESPN}?dates={day}' for day in (
        '20261122', '20261123', '20261124', '20261125', '20261126',
        '20261127', '20261128', '20261129', '20261130')]
    fixtures, results = daily.source_facts('NBA')
    assert [row['source_url'] for row in fixtures + results] == [SOURCE, calls[0]]
    original = SNAPSHOT.read_bytes()

    def fail(self, url, **kwargs):
        if url.endswith('20261130'):
            raise RuntimeError('sample provider failure')
        return get(self, url, **kwargs)

    monkeypatch.setattr(nba_schedule.CachedHTTP, 'get', fail)
    assert daily.refresh(['NBA'])['NBA']['status'] == 'failed'
    assert SNAPSHOT.read_bytes() == original
    assert list(SNAPSHOT.parent.iterdir()) == [SNAPSHOT]


def test_daily_includes_nba_when_snapshot_exists_and_settles_only_final(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []

    def predict(league, teams, start):
        calls.append((league, teams, start))
        home, away = teams[0]
        return [dict(lig=league, ev=home, dep=away, tarih_utc=start, model='test',
                     ev_kazanir=.7, ev_skor=110., dep_skor=100., fark=10., toplam=210.,
                     fark_80=[-5., 25.], toplam_80=[180., 240.], selection_eligible=True)]

    monkeypatch.setattr(tahmin, 'tahmin_et', predict)
    assert 'NBA' in daily.LEAGUES
    missing = daily.run(['NBA'], now=NOW)
    assert not missing['upcoming'] and not calls
    assert missing['skipped'] == [dict(league='NBA', reason='No NBA schedule snapshot; run with --guncelle')]

    SNAPSHOT.parent.mkdir(parents=True)

    def write_capture(payload, captured):
        fixtures, results = nba_schedule.parse_espn(payload, captured, SOURCE)
        SNAPSHOT.write_text(json.dumps(dict(fixtures=fixtures, results=results)), encoding='utf8')
        assert daily.source_facts('NBA') == (fixtures, results)

    write_capture(scoreboard(scheduled()), '2026-11-22T23:00Z')
    stale = daily.run(['NBA'], now=NOW)
    assert not stale['upcoming'] and not calls
    assert 'stale' in stale['skipped'][0]['reason']

    write_capture(scoreboard(scheduled()), NOW)
    first = daily.run(['NBA'], now=NOW)
    assert [entry['record_status'] for entry in first['upcoming']] == ['new_immutable']
    assert calls == [('NBA', [('BRK', 'PHO')], '2026-11-24T02:00:00+00:00')]

    write_capture(scoreboard(event('401001', '2026-11-24T02:00Z', 'in', 'STATUS_IN_PROGRESS',
                                   scores=(41, 34))), '2026-11-24T03:00Z')
    live_report = daily.run(['NBA'], now='2026-11-24T03:00Z')
    assert not live_report['upcoming']
    assert live_report['performance']['pending_games'] == 1

    write_capture(scoreboard(event('401001', '2026-11-24T02:00Z', 'post', 'STATUS_FINAL',
                                   completed=True, scores=(112, 107))), '2026-11-24T05:00Z')
    final_report = daily.run(['NBA'], now='2026-11-24T05:00Z')
    assert final_report['performance']['settled_games'] == 1
