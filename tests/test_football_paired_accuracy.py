import pytest
from bbtahmin.football.evaluation_audit import paired_accuracy


def records():
    return [dict(event_id=str(i), variant='model', result=dict(actual_home=h, actual_away=a),
                 prediction=dict(predicted_outcome=p, over={'2.5':o}, both_teams_score=b))
            for i,(h,a,p,o,b) in enumerate([(2,0,'home',.2,.2),(0,1,'away',.1,.1),
                                           (1,0,'away',.7,.7),(1,1,'home',.8,.8)])]


def test_paired_wins_losses_and_no_accuracy_gain():
    r=paired_accuracy(records(),['model'],['0','1','2','3'])
    w=r['comparisons']['model']['winner']
    assert [w[k] for k in ('both_correct','candidate_only','comparator_only','both_wrong')]==[1,1,1,1]
    assert w['accuracy_delta']==0 and w['candidate_accuracy']==.5
    assert r['comparisons']['model']['over_2_5']['accuracy_delta']==-.5
    assert r['comparisons']['model']['btts']['accuracy_delta']==0


@pytest.mark.parametrize('bad', [float('nan'),float('inf'),-.1,1.1,True])
def test_bad_probability_rejected(bad):
    r=records();r[0]['prediction']['over']['2.5']=bad
    with pytest.raises(ValueError): paired_accuracy(r,['model'],['0','1','2','3'])


def test_empty_and_tie_threshold():
    assert paired_accuracy([],['model'],[])['comparisons']['model']['winner']['accuracy_delta'] is None
    r=records()[:1];r[0]['prediction']['over']['2.5']=.5
    assert paired_accuracy(r,['model'],['0'])['comparisons']['model']['over_2_5']['comparator_only']==1


def test_different_cohorts_rejected():
    with pytest.raises(ValueError): paired_accuracy(records(),['model','missing'],['0','1','2','3'])


@pytest.mark.parametrize('bad', [-1, 1.5, float('nan'), True, 31])
def test_invalid_observation_rejected(bad):
    r=records();r[0]['result']['actual_home']=bad
    with pytest.raises(ValueError): paired_accuracy(r,['model'],['0','1','2','3'])


def test_iterable_input_is_not_consumed_by_validation():
    assert paired_accuracy(iter(records()),['model'],['0','1','2','3'])['comparisons']['model']['winner']['both_correct']==1
