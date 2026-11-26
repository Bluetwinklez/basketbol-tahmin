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

def test_interrupted_match_is_deferred_only_until_reviewed_resume(tmp_path):
    import gzip
    import json
    from bbtahmin.football.data import load, row, write_json
    from bbtahmin.football.health import defer_interrupted_history, interrupted_reviews

    source='https://example.com/fixture'
    old=row('ES1','2026-27','2026-10-10','A','B',None,source,'2026-10-11T00:00Z')
    resumed=row('ES1','2026-27','2026-12-09','A','B',[1,0],source,'2026-12-10T00:00Z')
    unrelated=row('ES1','2026-27','2026-10-11','A','C',None,source,'2026-10-12T00:00Z')
    reviews={old['event_id']:dict(status='interrupted_pending_review', league='ES1',season='2026-27',
        home='a',away='b',original_date='2026-10-10', resume_at_utc='2026-12-09T19:00Z',
        checked_at_utc='2026-11-26T12:00Z', source_url=source, interruption_source_url=source)}
    write_json(tmp_path/'fixture_reviews.json',dict(spec='football-fixture-reviews-v1',reviews=reviews))
    (tmp_path/'ES1_2026-27.json.gz').write_bytes(gzip.compress(json.dumps({'rows':[old,resumed,unrelated]}).encode()))
    assert load(tmp_path,include_licensed=False).set_index('event_id').loc[resumed['event_id'],'status']=='final'
    frame=load(tmp_path)
    held=interrupted_reviews(reviews)
    assert set(held)=={old['event_id'], resumed['event_id']}
    assert frame['status'].eq('unverified').all()
    assert frame['home_goals'].isna().all()
    assert len(defer_interrupted_history(frame,held,'2026-11-25T12:00Z'))==3
    assert defer_interrupted_history(frame,held,'2026-11-26T12:00Z')['event_id'].tolist()==[unrelated['event_id']]
    assert len(defer_interrupted_history(frame,held,'2026-12-09T19:00Z'))==3

    from bbtahmin.football import daily
    write_json(tmp_path/'collection.json',dict(checked_at_utc='2026-12-08T11:00Z',errors=[]))
    ledger=tmp_path/'ledger'
    before=daily.run(root=tmp_path,output=ledger,now='2026-12-08T12:00Z',
                     require_fixture_confirmation=False)
    assert before['forecasts']==[]
    record=dict(fixture=dict(resumed,verified_start_utc='2026-12-09T19:00Z'),
                prediction={},recorded_at_utc='2026-10-09T18:00Z')
    record_path=ledger/'forecasts'/f"{resumed['event_id']}.json"
    write_json(record_path,dict(record,payload_sha256=daily.digest(record)))
    original=record_path.read_bytes()
    after=daily.run(root=tmp_path,output=ledger,now='2026-12-10T12:00Z',
                    require_fixture_confirmation=False)
    assert after['forecasts'][0]['status']=='fixture_review_required'
    assert after['forecasts'][0]['result'] is None
    assert after['pending']==1
    assert record_path.read_bytes()==original
