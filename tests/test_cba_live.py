import numpy as np
import pandas as pd
import pytest

from bbtahmin.live import project,state_features
from bbtahmin.veri.cba import parse_schedule
from bbtahmin.veri.cba_quarters import parse


class Constant:
    def __init__(self,value):self.value=value
    def predict(self,x):return np.full(len(x),self.value)


def test_cba_schedule_result_is_home_first_even_on_away_team_page():
    html='<table><tr><td data-th="Date">Dec 13, 2025</td><td data-th="Opponent">@ <a href="/team/412/Name">Name</a></td><td data-th="Result"><a href="/international/boxscore/date/name/517286">W, 74 - 84</a></td></tr></table>'
    result=parse_schedule(html,'287',2026)[0]
    assert result['ev']=='CBA_412' and result['dep']=='CBA_287'
    assert result['ev_skor']==74 and result['dep_skor']==84
    assert result['tarih_utc']==pd.Timestamp('2025-12-13T00:00Z')
    assert result['regulation_minutes']==40
    with pytest.raises(ValueError,match='order'):
        parse_schedule(html.replace('W,','L,'),'287',2026)


def test_quarters_must_match_scores_and_home_away_orientation():
    html='<table><thead><tr>'+''.join(f'<th>{v}</th>' for v in ['','1','2','3','4','Final'])+'</tr></thead><tbody>'
    for values in [['Away',20,20,20,20,80],['Home',25,25,25,25,100]]:
        html+='<tr>'+''.join(f'<td>{v}</td>' for v in values)+'</tr>'
    html+='</tbody></table>'
    assert parse(html,100,80)==([25]*4,[20]*4)
    with pytest.raises(ValueError,match='orientation'):parse(html,80,100)


@pytest.mark.parametrize('period,clock,minutes',[(1,'01:28',40),(1,'01:28',48),(3,'05:00',40)])
def test_live_clock_is_remaining_and_projections_cannot_erase_observed_points(period,clock,minutes):
    prior=dict(fark=1.,toplam=190.)
    r=project(prior,16,15,period,clock,minutes,[Constant(-100),Constant(5)],[12,18])
    mm,ss=map(int,clock.split(':'))
    elapsed=((period-1)*minutes*15+minutes*15-mm*60-ss)/(minutes*60)
    assert r['elapsed_fraction']==pytest.approx(elapsed)
    assert r['home_score']>=16 and r['away_score']>=15
    assert 0<=r['home_regulation_lead_probability']<=1


@pytest.mark.parametrize('period,clock',[(0,'01:00'),(5,'01:00'),(1,'10:01'),(1,'00:60'),(1,'10:00'),(4,'00:00')])
def test_invalid_or_overtime_states_fail(period,clock):
    with pytest.raises(ValueError):
        project(dict(fark=1.,toplam=190.),16,15,period,clock,40,[Constant(0),Constant(100)],[12,18])


def test_live_does_not_use_an_unknown_final_score_as_input():
    x=state_features(2.,190.,16,15,.2)
    assert x.shape==(5,) and np.isfinite(x).all()


def test_stale_and_future_manual_inputs_are_rejected_before_model_loading():
    from bbtahmin.live import predict
    with pytest.raises(ValueError,match='older'):
        predict('A','B',16,15,1,'01:28','2020-01-01T00:00Z')
    with pytest.raises(ValueError,match='non-future'):
        predict('A','B',16,15,1,'01:28','2099-01-01T00:00Z')


def test_live_fit_never_reads_target_season_targets():
    from bbtahmin.live import fit
    rng=np.random.default_rng(42);rows=[]
    for season in ['2023-24','2024-25','2025-26']:
        for i in range(90):
            x=rng.normal(size=5)
            rows.append(dict(sezon=season,mac_id=f'{season}_{i//3}',period=i%3+1,
                remaining_margin=float(x[0]+rng.normal()),remaining_total=float(80+x[1]+rng.normal()),
                **{f'x{j}':v for j,v in enumerate(x)}))
    data=pd.DataFrame(rows);m1,s1,_=fit(data,'2025-26')
    changed=data.copy();changed.loc[changed.sezon=='2025-26',['remaining_margin','remaining_total']]=100000
    m2,s2,_=fit(changed,'2025-26')
    assert s1==s2
    np.testing.assert_array_equal(m1[0].predict(data[[f'x{i}' for i in range(5)]]),
                                  m2[0].predict(data[[f'x{i}' for i in range(5)]]))


def test_cba_pregame_target_and_future_results_do_not_change_first_test_prediction():
    from bbtahmin.cba_model import walk_forward
    rng=np.random.default_rng(7);rows=[]
    for year,n in [(2021,240),(2022,120),(2023,5)]:
        for i in range(n):
            rows.append(dict(mac_id=f'{year}_{i}',lig='CBA',sezon=f'{year}-{str(year+1)[-2:]}',
                tarih_utc=pd.Timestamp(f'{year}-10-01',tz='UTC')+pd.Timedelta(days=i),
                ev='A' if i%2 else 'B',dep='B' if i%2 else 'A',
                ev_skor=100+int(rng.integers(-20,20)),dep_skor=99+int(rng.integers(-20,20)),
                regulation_minutes=48,tarafsiz_saha=False))
    original=pd.DataFrame(rows);p1=walk_forward(original)
    altered=original.copy();altered.loc[altered.sezon=='2023-24',['ev_skor','dep_skor']]=[135,80]
    p2=walk_forward(altered)
    fields=['p','margin_prediction','total_prediction']
    np.testing.assert_array_equal(p1.iloc[0][fields].to_numpy(),p2.iloc[0][fields].to_numpy())
