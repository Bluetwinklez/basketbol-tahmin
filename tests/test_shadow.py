import copy
import json

import pytest

from bbtahmin.shadow import checked,evaluate,freeze,register


@pytest.fixture
def tmp_path(tmp_path_factory):
    # Two SHA-256 names already consume 128 characters. Long test names in
    # pytest's default temporary directory exceed Windows MAX_PATH.
    return tmp_path_factory.mktemp('shadow')


def fixture():
    return dict(event_id='one',league='KBL',home='a',away='b',start_utc='2026-10-27T12:00Z',
                captured_at='2026-10-26T12:00Z',source_url='https://example.org/one',status='scheduled')


def test_register_reuses_json_equivalent_policy_without_rewriting(tmp_path):
    policy=dict(version=1,leagues=('E','KBL'),nested={'thresholds':(.5,.65)})
    directory,identity=register(tmp_path,policy)
    original={p.name:p.read_bytes() for p in directory.iterdir()}
    repeated,repeat_id=register(tmp_path,policy)
    decoded,decoded_id=register(tmp_path,json.loads(json.dumps(policy)))
    assert repeated==decoded==directory and repeat_id==decoded_id==identity
    assert {p.name:p.read_bytes() for p in directory.iterdir()}==original
    _,changed_id=register(tmp_path,dict(policy,leagues=('E','ABA')))
    assert changed_id!=identity


def predictions():
    p=dict(model='model',league='KBL',home='a',away='b',probabilities=[.6,.4],class_labels=['home','away'],
           expected_home=81.,expected_away=75.,eligible=True,information_cutoff_utc='2026-10-26T13:00:00+00:00')
    return dict(reference=p,candidate=dict(p,probabilities=[.7,.3]))


def test_pair_is_immutable_and_settles_from_pregame_timestamped_final(tmp_path):
    directory,identity=register(tmp_path,dict(version=1))
    record=freeze(directory,identity,fixture(),predictions(),{'source':'hash'},now='2026-10-26T13:00Z')
    changed=predictions();changed['candidate']['probabilities']=[.1,.9]
    assert freeze(directory,identity,fixture(),changed,{},now='2026-10-26T13:00Z')==record
    result=dict(fixture(),status='final',home_score=90,away_score=80,captured_at='2026-10-27T15:00Z')
    report=evaluate(directory,[result],now='2026-10-27T16:00Z')
    assert report['settled_games']==1
    assert report['leagues'][0]['summary']['candidate']['all']['accuracy']==1
    assert report['leagues'][0]['production_promoted'] is False
    assert report['leagues'][0]['promotion_review_eligible'] is False
    assert evaluate(directory,[dict(result,status='in_play')],now='2026-10-27T16:00Z')['pending']==1
    assert evaluate(directory,[dict(result,home='c')],now='2026-10-27T16:00Z')['settled_games']==0


def test_missing_pair_future_capture_tamper_and_policy_change(tmp_path):
    directory,identity=register(tmp_path,dict(version=1))
    with pytest.raises(ValueError):freeze(directory,identity,fixture(),{'reference':predictions()['reference']},{},now='2026-10-26T13:00Z')
    with pytest.raises(ValueError):freeze(directory,identity,fixture(),predictions(),{},now='2026-10-26T11:00Z')
    record=freeze(directory,identity,fixture(),predictions(),{},now='2026-10-26T13:00Z')
    broken=copy.deepcopy(record);broken['predictions']['candidate']['probabilities']=[.9,.1]
    with pytest.raises(ValueError):checked(broken)
    newer,new_id=register(tmp_path,dict(version=2))
    assert identity!=new_id and directory!=newer
    assert len(list((directory/'forecasts').glob('*.json')))==1


def test_publisher_id_keeps_one_pair_when_archive_date_hash_changes(tmp_path):
    directory,identity=register(tmp_path,dict(version=1))
    f=dict(fixture(),provider_event_id='123')
    record=freeze(directory,identity,f,predictions(),{},now='2026-10-26T13:00Z')
    changed=dict(f,event_id='replacement-date-hash')
    assert freeze(directory,identity,changed,predictions(),{},now='2026-10-26T13:00Z')==record
    assert len(list((directory/'forecasts').glob('*.json')))==1
    result=dict(changed,status='final',home_score=90,away_score=80,captured_at='2026-10-27T15:00Z')
    assert evaluate(directory,[result],now='2026-10-27T16:00Z')['settled_games']==1
