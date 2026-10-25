import copy

import pytest

from bbtahmin.football.fixture_confirmation import confirm,facts


def payload():
    return dict(leagues=[dict(slug='eng.1')],events=[dict(id='123',date='2026-10-27T19:00Z',season=dict(year=2026),
                competitions=[dict(timeValid=True,status=dict(type=dict(name='STATUS_SCHEDULED',completed=False)),
                    competitors=[dict(homeAway='home',team=dict(id='1',displayName='Club A')),
                                 dict(homeAway='away',team=dict(id='2',displayName='Club B'))])])])


def test_explicit_club_alias_date_and_competition_guards():
    observed=facts(payload(),'EN1','2026-10-26T12:00Z')
    fixture=dict(event_id='original',league='EN1',season='2026-27',date='2026-10-27',home='a fc',away='club b')
    assert confirm(fixture,observed,{'A FC':'Club A'})['status']=='confirmed'
    assert confirm(fixture,observed,{})['status']=='unconfirmed'
    assert confirm(dict(fixture,date='2026-10-28'),observed,{'A FC':'Club A'})['status']=='date_conflict'
    assert confirm(fixture,observed+observed,{'A FC':'Club A'})['status']=='ambiguous'
    assert confirm(dict(fixture,season='2025-26'),observed,{'A FC':'Club A'})['status']=='unconfirmed'
    with pytest.raises(ValueError):facts(payload(),'TR1','2026-10-26T12:00Z')


def test_live_scores_and_unknown_times_never_become_final_evidence():
    value=payload();game=value['events'][0]['competitions'][0]
    game['status']['type']=dict(name='STATUS_IN_PROGRESS',completed=False)
    assert facts(value,'EN1','2026-10-27T20:00Z')==[]
    game['status']['type']=dict(name='STATUS_FULL_TIME',completed=True)
    for side in game['competitors']:side['score']='0'
    assert facts(value,'EN1','2026-10-27T22:00Z')[0]['home_score']==0
    with pytest.raises(ValueError):facts(value,'EN1','2026-10-27T18:00Z')
    game['timeValid']=False
    assert facts(value,'EN1','2026-10-27T22:00Z')==[]
