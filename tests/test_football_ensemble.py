import numpy as np
import pandas as pd
import pytest
from bbtahmin.football.challenger import fit
from bbtahmin.football.ensemble import combine,grid


def history():
    return pd.DataFrame([dict(league='TR1',status='final',date=(pd.Timestamp('2025-01-01')+pd.Timedelta(days=i)).strftime('%Y-%m-%d'),home='a' if i%2 else 'b',away='b' if i%2 else 'a',home_goals=i%4,away_goals=i%3) for i in range(160)])


def test_ensemble_excludes_current_day_future_and_foreign_scores():
    h=history();p=fit(h,'TR1','2025-07-01','ensemble').predict('a','b')
    bad=h.iloc[:1].copy();bad.date='2025-07-01';bad.home_goals=30
    foreign=h.copy();foreign.league='EN1';foreign.home_goals=30
    q=fit(pd.concat([h,bad,foreign]),'TR1','2025-07-01','ensemble').predict('a','b')
    assert p==q
    assert sum(p['probabilities'].values())==pytest.approx(1)
    assert p['over']['3.5']<=p['over']['2.5']<=p['over']['1.5']


def test_candidate_identity_mismatch_fails():
    h=history();p=fit(h,'TR1','2025-07-01').predict('a','b')
    with pytest.raises(ValueError,match='mismatch'):combine(p,dict(p,home='other'))
    with pytest.raises(ValueError,match='mismatch'):combine(p,dict(p,training_cutoff_exclusive='2025-07-02'))


def test_probability_mixture_is_bounded_by_component_probabilities():
    h=history();a=fit(h,'TR1','2025-07-01').predict('a','b');b=fit(h,'TR1','2025-07-01','opponent_dc').predict('a','b');p=combine(a,b)
    for k in ('home','draw','away'):
        assert min(a['probabilities'][k],b['probabilities'][k])-1e-12<=p['probabilities'][k]<=max(a['probabilities'][k],b['probabilities'][k])+1e-12
    assert p['recommendation_validated'] is False


def test_invalid_low_score_distribution_rejected():
    p=fit(history(),'TR1','2025-07-01').predict('a','b');p['low_score_rho']=100
    with pytest.raises(ValueError):grid(p)
