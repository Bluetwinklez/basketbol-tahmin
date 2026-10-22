import pandas as pd
import pytest

from bbtahmin.veri.genislet import halftime, materialize_boxes, merge_games, nba_code, nba_rows, save_table
from bbtahmin.veri.schema import normalize


def game(**changes):
    row = dict(mac_id='NBA_202410220BOS', lig='NBA', sezon='2024-25',
               tarih_utc='2024-10-22T23:30Z', ev='BOS', dep='NYK', ev_skor=132, dep_skor=109,
               uzatma=False, ev_iy=None, dep_iy=None, tarafsiz_saha=None, asama='normal', kaynak='original')
    return dict(row, **changes)


def test_additive_merge_enriches_without_overwriting_results():
    old = normalize([game()])
    new, report = merge_games(old, [game(ev_iy=74, dep_iy=55, tarafsiz_saha=True, kaynak='new'),
                                   game(mac_id='new_game', tarih_utc='2024-10-23T22:00Z')])
    assert len(new) == 2 and report['added'] == 1 and report['enriched'] == 1
    matched = new.set_index('mac_id').loc[old.mac_id.iloc[0]]
    assert matched.ev_iy == 74 and matched.tarafsiz_saha
    assert matched.kaynak == 'original' and matched.ev_skor == 132
    repeated, again = merge_games(new, new.to_dict('records'))
    pd.testing.assert_frame_equal(repeated, new)
    assert again['added'] == again['enriched'] == 0


def test_conflicting_score_cannot_overwrite_or_enrich_existing_game():
    old = normalize([game()])
    new, report = merge_games(old, [game(ev_skor=99, ev_iy=50)])
    pd.testing.assert_frame_equal(old, new)
    assert len(report['conflicts']) == 1


def test_shifted_source_date_cannot_duplicate_an_existing_result():
    old = normalize([game()])
    incoming = game(mac_id='NBA_202410230BOS',tarih_utc='2024-10-23T12:00Z',kaynak='other-source')
    new, report = merge_games(old,[incoming])
    pd.testing.assert_frame_equal(old,new)
    assert report['added'] == 0
    assert report['conflicts'][0]['reason'] == 'possible duplicate with shifted source date'


def test_historical_charlotte_franchises_remain_distinct():
    assert nba_code('CHH', 'Charlotte Hornets', 2002) == 'NOP'
    assert nba_code('CHA', 'Charlotte Hornets', 2025) == 'CHO'
    assert nba_code('SEA', 'Seattle SuperSonics', 2007) == 'OKC'
    assert nba_code('NJ', 'New Jersey Nets', 2010) == 'BRK'


@pytest.mark.parametrize('text', [
    "[{'value': 23.0, 'period': 1.0}\n {'value': 19.0, 'period': 2.0}]",
    "[{'displayValue': '23', 'period': 1, 'value': 23.0}\n {'period': 2, 'value': 19.0}]",
])
def test_halftime_key_order_and_numpy_repr(text):
    assert halftime(text) == 42
    assert halftime(None) is None
    assert halftime("[{'period': 1, 'value': 23.0}]") is None


def test_nba_schedule_uses_local_day_for_id_and_utc_for_prediction():
    row = dict(game_id=123, season_type=2, status_type_completed=True,
               date='2024-10-23T00:00Z', game_date=pd.Timestamp('2024-10-22'),
               home_abbreviation='BOS', home_display_name='Boston Celtics', home_score=100,
               away_abbreviation='NY', away_display_name='New York Knicks', away_score=90,
               status_period=5, neutral_site=True)
    schedule = pd.DataFrame([row, dict(row, game_id=124, season_type=1),
                             dict(row, game_id=125, status_type_completed=False),
                             dict(row, game_id=126, home_score=90)])
    rows, mapping, rejected = nba_rows(schedule, 2025, 'source')
    assert len(rows) == 1 and len(rejected) == 1
    assert rows[0]['mac_id'] == 'NBA_202410220BOS'
    assert rows[0]['tarih_utc'] == pd.Timestamp('2024-10-23T00:00Z')
    assert rows[0]['uzatma'] and rows[0]['tarafsiz_saha']
    assert mapping == {'123': 'NBA_202410220BOS'}


def test_detail_merge_retains_other_seasons(tmp_path):
    path = tmp_path / 'details.parquet'
    save_table([dict(mac_id='old', rol='ev', points=90)], path, ['mac_id', 'rol'])
    save_table([dict(mac_id='new', rol='ev', points=100)], path, ['mac_id', 'rol'])
    save_table([dict(mac_id='new', rol='ev', points=101)], path, ['mac_id', 'rol'])
    table = pd.read_parquet(path).set_index('mac_id')
    assert len(table) == 2 and table.loc['old', 'points'] == 90 and table.loc['new', 'points'] == 101


def test_nullable_numeric_player_id_does_not_duplicate_existing_string_id(tmp_path):
    path = tmp_path/'players.parquet'
    save_table([dict(mac_id='m',rol='ev',oyuncu='123',saniye=600)],path,['mac_id','rol','oyuncu'])
    save_table([dict(mac_id='m',rol='ev',oyuncu='123.0',saniye=660)],path,['mac_id','rol','oyuncu'])
    result = pd.read_parquet(path)
    assert len(result) == 1 and result.oyuncu.iloc[0] == '123' and result.saniye.iloc[0] == 660


def test_foreign_season_records_are_rejected():
    row = dict(game_id=1,season_type=2,status_type_completed=True,season=1999)
    rows, mapping, rejected = nba_rows(pd.DataFrame([row]),2000,'source')
    assert not rows and not mapping
    assert rejected[0]['error'] == 'record belongs to a different season'


def test_materialize_boxes_requires_both_sides_and_counts_multiple_overtimes(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path/'data').mkdir()
    columns = dict(field_goals_attempted=80,three_point_field_goals_attempted=25,free_throws_attempted=20,
                   offensive_rebounds=10,defensive_rebounds=30,total_turnovers=12,fouls=18,team_score=100)
    pd.DataFrame([dict(columns,mac_id=mac,rol=rol) for mac,rol in
                  [('valid','ev'),('valid','dep'),('incomplete','ev')]]).to_parquet('data/nba_takim_istatistik.parquet')
    pd.DataFrame([dict(mac_id='valid',status_period=6)]).to_parquet('data/nba_mac_baglami.parquet')
    games = normalize([game(mac_id='valid'),game(mac_id='incomplete')])
    materialize_boxes(games)
    result = pd.read_parquet('data/kutu_nba.parquet')
    assert set(result.mac_id) == {'valid'}
    assert set(result.sure) == {3480.}
    assert set(result.fga2) == {55}
