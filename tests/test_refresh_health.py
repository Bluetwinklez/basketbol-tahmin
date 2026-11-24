from bbtahmin.refresh_health import transitions


def report(status='partial', errors=None):
    return dict(status=status, errors=errors or [])


def test_new_continuing_and_resolved_keep_identity_and_latest_error():
    a=dict(league='A',error='503'); b=dict(league='B',error='timeout')
    fresh=dict(league='A',error='IncompleteRead'); c=dict(league='C',error='404')
    r=transitions({'basketball':report(errors=[a,b])},{'basketball':report(errors=[fresh,c])})['sports']['basketball']
    assert r['new_failures']==[c] and r['continuing_failures']==[fresh]
    assert r['no_longer_reported']==[b] and r['comparison_available']


def test_missing_or_failed_sport_does_not_clear_failures():
    error=dict(league='A',error='503')
    for current in ({}, {'basketball':dict(status='failed',error='offline')}):
        r=transitions({'basketball':report(errors=[error])},current)['sports']['basketball']
        assert r['no_longer_reported']==[] and r['unresolved_unobserved']==[error]
        assert not r['comparison_available']


def test_first_observation_is_baseline_not_new_outage():
    error=dict(league='A',error='503')
    r=transitions({}, {'football':report(errors=[error])})['sports']['football']
    assert r['baseline_failures']==[error] and r['new_failures']==[]
    assert not r['comparison_available']


def test_season_and_collector_are_distinct_and_input_unchanged():
    a=dict(league='A',season='2025',collector='one',error='missing')
    b=dict(a,season='2026'); c=dict(a,collector='two')
    old={'football':report(errors=[a,b,c])}
    r=transitions(old,{'football':report('succeeded')})['sports']['football']
    assert len(r['no_longer_reported'])==3 and old['football']['errors']==[a,b,c]


def test_backfill_and_active_failures_remain_distinct():
    a=dict(league='A',stage='historical_backfill',error='offline')
    b=dict(league='A',error='offline')
    r=transitions({'basketball':report(errors=[a,b])},{'basketball':report(errors=[b])})['sports']['basketball']
    assert r['no_longer_reported']==[a] and r['continuing_failures']==[b]


def test_duplicate_identity_is_rejected_not_silently_overwritten():
    import pytest
    a=dict(league='A',error='offline')
    with pytest.raises(ValueError): transitions({}, {'football':report(errors=[a,a])})
