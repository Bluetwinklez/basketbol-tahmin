import json

import pandas as pd
import pytest

from bbtahmin.veri.aba import parse_calendar


def page(year=2026, date='23.10.2026 17:00 CET', score='', game=50):
    url = f'https://www.aba-liga.com/match/{game}/{year % 100}/1/Overview/q1/1/home/cluj-sc-derby/'
    return f'''<select id="season"><option selected value="{year % 100}/1/">Season</option></select>
    <table><tr><td><p class="hidden-xs"><a href="{url}">Cluj <span>:</span> SC Derby</a></p>
    <p class="visible-xs"><a href="{url}">CLU <span>:</span> SCD</a></p></td>
    <td class="scoretable">{score}</td><td class="locationtable">{date}</td></tr></table>'''


def test_aba_uses_senior_season_and_dst_wall_clock():
    records, fixtures, teams, _ = parse_calendar(page(), 2026, '2026-10-23T13:00Z')
    assert not records
    assert fixtures[0]['tarih_utc'] == pd.Timestamp('2026-10-23T15:00Z')
    assert fixtures[0]['status'] == 'scheduled' and 'ABA_SCD' in teams
    winter = parse_calendar(page(date='23.11.2026 17:00 CET'), 2026, '2026-10-23T13:00Z')[1][0]
    assert winter['tarih_utc'] == pd.Timestamp('2026-11-23T16:00Z')
    with pytest.raises(ValueError, match='season or division'):
        parse_calendar(page().replace('26/1/', '26/7/'), 2026, '2026-10-23T13:00Z')


def test_aba_same_day_running_score_never_becomes_final():
    records, fixtures, _, _ = parse_calendar(page(score='94 : 82'), 2026, '2026-10-23T20:00Z')
    assert not records and fixtures[0]['status'] == 'unverified'
    records, _, _, _ = parse_calendar(page(score='94 : 82'), 2026, '2026-10-24T00:01Z')
    assert records[0]['ev_skor'] == 94 and records[0]['dep_skor'] == 82
    assert not parse_calendar(page(score='0 : 0'), 2026, '2026-10-24T00:01Z')[0]


def test_aba_wrong_year_and_duplicate_games_fail_closed():
    with pytest.raises(ValueError, match='outside requested'):
        parse_calendar(page(date='23.10.2024 17:00 CET'), 2026, '2026-10-23T13:00Z')
    with pytest.raises(ValueError, match='Duplicate'):
        parse_calendar(page()+page(), 2026, '2026-10-23T13:00Z')


def test_aba_daily_reads_provenance_and_ignores_legacy_missing_provenance(tmp_path, monkeypatch):
    from bbtahmin.daily import source_facts
    monkeypatch.chdir(tmp_path)
    root = tmp_path/'data/competitions'; root.mkdir(parents=True)
    records, fixtures, _, _ = parse_calendar(page(score='94 : 82'), 2026, '2026-10-24T00:01Z')
    pd.DataFrame(records).to_parquet(root/'ABA.parquet')
    pd.DataFrame(fixtures).to_parquet(root/'ABA_fixtures.parquet')
    f, r = source_facts('ABA')
    assert f[0]['home'] == 'ABA_CLU' and r[0]['home_score'] == 94
    pd.DataFrame(fixtures).drop(columns=['captured_at_utc']).to_parquet(root/'ABA_fixtures.parquet')
    with pytest.raises(ValueError, match='refresh first'):
        source_facts('ABA')


def test_aba_aliases_and_runtime_route_are_independent(monkeypatch):
    from bbtahmin import regional_model
    from bbtahmin.tahmin import _tahmin_et
    monkeypatch.setattr(regional_model, 'predict', lambda *args: dict(route=args))
    result = _tahmin_et('ABA', [('ABA_CLU', 'ABA_SCD')], '2026-10-23T15:00Z')
    assert result[0]['route'][0] == 'ABA'
    with pytest.raises(ValueError, match='own preceding-season'):
        _tahmin_et('ABA', [('ABA_CLU', 'ABA_SCD')], '2026-10-23T15:00Z', adaptive_form=True)


def test_aba_bulletin_groups_do_not_route_juniors_or_second_division():
    from bbtahmin.veri.iddaa import LEAGUES, key
    assert LEAGUES[key('ABA LİGA, GRUP B')] == 'ABA'
    assert LEAGUES.get(key('ABA Liga 2')) is None
    assert LEAGUES.get(key('ABA Liga U19')) is None
