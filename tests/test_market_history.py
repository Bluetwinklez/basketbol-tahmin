import copy
import json

import pytest

from bbtahmin.market_history import history


def snapshot(captured, odds=2., start='2020-01-02T00:00Z'):
    return dict(captured_at_utc=captured, events=[dict(event_id='123', home='A', away='B',
        competition_id='7', start_utc=start, promotion_flag=None,
        moneyline=dict(market_id='1_2', includes_overtime=True, price_field='odd',
                       home_odds=odds, away_odds=2., minimum_combination_count=1))])


def write(root, name, value):
    folder=root/'data/bulten';folder.mkdir(parents=True,exist_ok=True)
    (folder/name).write_text(json.dumps(value))


def test_asof_excludes_later_quotes_and_post_tipoff_and_deduplicates_latest(tmp_path):
    first=snapshot('2020-01-01T10:00Z',2.)
    write(tmp_path,'iddaa_a.json',first);write(tmp_path,'latest.json',first)
    write(tmp_path,'iddaa_b.json',snapshot('2020-01-01T11:00Z',1.5))
    write(tmp_path,'iddaa_c.json',snapshot('2020-01-02T00:00Z',1.1))
    before=history('123',tmp_path,'2020-01-01T10:30Z')
    assert before['observations']==1 and before['market_home_change']==0
    after=history('123',tmp_path,'2020-01-03T00:00Z',limit=1)
    assert after['observations']==2 and after['returned']==1 and after['truncated']
    assert after['first_observed']['home_odds']==2.
    assert after['latest_observed']['home_odds']==1.5
    assert after['market_home_change']==pytest.approx(1/1.5/(1/1.5+1/2)-.5)


def test_malformed_prices_and_unverified_market_are_counted_as_skipped(tmp_path):
    bad=snapshot('2020-01-01T10:00Z',float('nan'))
    write(tmp_path,'iddaa_bad.json',bad)
    other=copy.deepcopy(bad);other['events'][0]['moneyline']['includes_overtime']=False
    write(tmp_path,'latest.json',other)
    result=history('123',tmp_path,'2020-01-03T00:00Z')
    assert result['observations']==0 and result['skipped_files']==2


@pytest.mark.parametrize('change',['team','start','price'])
def test_conflicting_fixture_identity_or_same_instant_price_fails(tmp_path,change):
    value=snapshot('2020-01-01T10:00Z')
    write(tmp_path,'iddaa_a.json',value)
    other=copy.deepcopy(value)
    if change=='team':other['events'][0]['home']='OTHER'
    elif change=='start':other['events'][0]['start_utc']='2020-01-03T00:00Z'
    else:other['events'][0]['moneyline']['home_odds']=1.5
    write(tmp_path,'latest.json',other)
    with pytest.raises(ValueError,match='merge|Conflicting'):
        history('123',tmp_path,'2020-01-02T00:00Z')


@pytest.mark.parametrize('cutoff',['2020-01-01','2099-01-01T00:00Z','NaT'])
def test_invalid_asof_is_rejected(tmp_path,cutoff):
    with pytest.raises(ValueError,match='as_of'):
        history('123',tmp_path,cutoff)


def test_scheduled_odds_archive_merges_without_duplicate_latest(tmp_path):
    value=snapshot('2020-01-01T10:00Z')
    write(tmp_path,'iddaa_a.json',value)
    folder=tmp_path/'data/observations/odds';folder.mkdir(parents=True)
    (folder/'iddaa_b.json').write_text(json.dumps(snapshot('2020-01-01T11:00Z',1.5)))
    (folder/'latest.json').write_text((folder/'iddaa_b.json').read_text())
    result=history('123',tmp_path,'2020-01-01T12:00Z')
    assert result['observations']==2 and result['latest_observed']['home_odds']==1.5
