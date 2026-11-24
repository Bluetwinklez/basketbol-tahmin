import pytest
from bbtahmin.football.evaluation_audit import simple_baselines


def rows():
    return [dict(event_id=e, variant=v, result=dict(actual_home=h, actual_away=a))
            for v in ('a', 'b') for e,h,a in [('one',2,0),('two',1,1)]]


def test_comparators_exclude_targets_skipped_by_models():
    r = simple_baselines(rows(), ('a','b'), ['one','two','skipped'])
    assert r['games'] == 2 and r['skipped_targets'] == 1
    assert r['coverage'] == 2/3
    assert r['always_home_accuracy'] == .5
    assert r['always_under_2_5_accuracy'] == 1
    assert r['always_btts_no_accuracy'] == .5
    assert r['event_ids'] == ['one','two']


@pytest.mark.parametrize('fault', ['missing','score','duplicate','unknown','target_duplicate'])
def test_invalid_pairing_is_rejected(fault):
    items=rows(); targets=['one','two']
    if fault=='missing': items.pop()
    if fault=='score': items[-1]['result']['actual_home']=4
    if fault=='duplicate': items.append(items[0])
    if fault=='unknown': items[0]['variant']='unknown'
    if fault=='target_duplicate': targets.append('one')
    with pytest.raises(ValueError): simple_baselines(items, ('a','b'), targets)


def test_empty_cohort_has_no_success_rate():
    r=simple_baselines([], ('a','b'), ['skipped'])
    assert r['games']==0 and r['coverage']==0
    assert r['always_home_accuracy'] is None
    assert r['always_under_2_5_accuracy'] is None
    assert r['always_btts_no_accuracy'] is None
