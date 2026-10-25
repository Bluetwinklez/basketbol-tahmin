import json

import pandas as pd
import pytest

from bbtahmin.football.health import assess, inventory
from bbtahmin.football.model import GoalModel


def rows():
    return pd.DataFrame([
        dict(event_id='done', league='EN1', season='2026-27', date='2026-10-01',
             home='a', away='b', status='final', home_goals=2, away_goals=1),
        dict(event_id='unknown', league='EN1', season='2026-27', date='2026-10-10',
             home='a', away='c', status='scheduled', home_goals=None, away_goals=None),
        dict(event_id='foreign', league='TR1', season='2026-27', date='2026-10-24',
             home='a', away='b', status='final', home_goals=0, away_goals=1),
    ])


def test_fresh_capture_does_not_hide_unresolved_schedule():
    fixture=dict(league='EN1',season='2026-27',date='2026-10-27',home='a',away='b')
    result=assess(rows(),fixture,'2026-10-25T12:00Z')
    assert not result['diagnostic_gate_passed']
    assert result['teams']['a']['unresolved_past_fixture_ids']==['unknown']
    assert result['teams']['b']['last_final_date']=='2026-10-01'
    assert result['calendar_completeness_verified'] is False


def test_missing_finals_cannot_be_repaired_by_future_or_foreign_scores():
    fixture=dict(league='EN1',season='2026-27',date='2026-11-10',home='a',away='b')
    result=assess(rows(),fixture,'2026-11-05T12:00Z')
    assert result['teams']['a']['days_since_last_final']==35
    assert any('35 days' in issue for issue in result['blocking_issues'])
    with pytest.raises(ValueError): assess(rows(),fixture,'2026-11-05')
    assert inventory(rows(),'2026-10-25T12:00Z')['leagues'][0]['unresolved_past_fixtures']==1


def test_model_default_settings_unchanged_and_experiments_explicit():
    history=pd.DataFrame([dict(league='EN1',status='final',date=(pd.Timestamp('2025-01-01')+pd.Timedelta(days=i)).strftime('%Y-%m-%d'),
                              home='a' if i%2 else 'b',away='b' if i%2 else 'a',home_goals=i%4,away_goals=i%3) for i in range(160)])
    original=GoalModel(history,'EN1','2025-07-01').predict('a','b')
    explicit=GoalModel(history,'EN1','2025-07-01',half_life=180.,shrinkage=8.,window_days=1095).predict('a','b')
    assert original==explicit
    assert GoalModel(history,'EN1','2025-07-01',half_life=90.).predict('a','b')['probabilities']!=original['probabilities']
    with pytest.raises(ValueError): GoalModel(history,'EN1','2025-07-01',half_life=float('nan'))


def test_known_fixture_conflict_blocks_new_forecast(tmp_path,monkeypatch):
    from bbtahmin.football import daily
    from bbtahmin.football.data import row,write_json
    game=row('EN1','2026-27','2026-10-27','A','B',None,'https://example.com','2026-10-25T11:00Z')
    monkeypatch.setattr(daily,'load',lambda root:pd.DataFrame([game]))
    write_json(tmp_path/'collection.json',dict(checked_at_utc='2026-10-25T11:00Z',errors=[]))
    write_json(tmp_path/'fixture_reviews.json',dict(spec='football-fixture-reviews-v1',reviews={game['event_id']:dict(status='quarantined_date_conflict')}))
    report=daily.run(root=tmp_path,output=tmp_path/'ledger',now='2026-10-25T12:00Z')
    assert not report['forecasts']
    assert 'quarantined' in report['skipped'][0]['reason']
