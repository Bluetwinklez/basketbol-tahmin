import copy,json
import numpy as np
import pandas as pd
import pytest
from bbtahmin import prospective as model
from bbtahmin.context_import import validate,asof
from bbtahmin.quality import assess,validate_prediction
from bbtahmin.evaluation import paired,equal_coverage
from bbtahmin.domestic_features import features
from bbtahmin.veri.domestic import parse


def prediction():
    return dict(lig='ECW',ev='H',dep='A',tarih_utc='2026-10-23T17:00:00Z',model='test',
        ev_kazanir=.7,ev_skor=82.,dep_skor=76.,toplam=158.,fark=6.,toplam_80=[140.,176.],fark_80=[-10.,22.])


def fixture():
    return dict(event_id='F1',source_url='https://example.org/fixture',captured_at='2026-10-22T20:00:00Z',
        start_utc='2026-10-23T17:00:00Z',league='ECW',home='H',away='A',status='scheduled')


def test_frozen_forecast_never_overwrites_and_checks_checksum(tmp_path):
    path=tmp_path/'forecast.json'
    frozen=model.freeze([prediction()],[fixture()],path,now='2026-10-22T21:00:00Z')
    assert model.verify(json.loads(path.read_text()))==frozen
    with pytest.raises(FileExistsError):model.freeze([prediction()],[fixture()],path,now='2026-10-22T21:00:00Z')
    altered=copy.deepcopy(frozen);altered['forecasts'][0]['prediction']['ev_kazanir']=.9
    with pytest.raises(ValueError,match='checksum'):model.verify(altered)


@pytest.mark.parametrize('change',[{'start_utc':'2026-10-22T19:00:00Z'},{'home':'OTHER'},{'status':'live'},
    {'captured_at':'2026-10-20T20:00:00Z'},{'captured_at':'2026-10-22T22:00:00Z'}])
def test_invalid_or_late_freeze_rejected(tmp_path,change):
    f=fixture();f.update(change)
    with pytest.raises(ValueError):model.freeze([prediction()],[f],tmp_path/'x.json',now='2026-10-22T21:00:00Z')


def test_exact_settlement_and_pending_never_in_accuracy(tmp_path):
    frozen=model.freeze([prediction()],[fixture()],tmp_path/'x.json',now='2026-10-22T21:00:00Z')
    pending=model.settle(frozen,[],now='2026-10-24T00:00:00Z');assert pending['winner_accuracy'] is None
    r=dict(fixture(),status='final',home_score=80,away_score=90,captured_at='2026-10-23T20:00:00Z')
    done=model.settle(frozen,[r],now='2026-10-24T00:00:00Z');g=done['games'][0]
    assert not g['winner_correct'] and g['home_signed_error']==2 and g['away_signed_error']==-14
    assert g['total_absolute_error']==12 and g['margin_absolute_error']==16 and g['score_mae']==8
    assert g['total_percentage_error']==pytest.approx(1200/170)
    r['home']='OTHER'
    with pytest.raises(ValueError,match='identity'):model.settle(frozen,[r])


def test_actual_tipoff_before_record_invalidates_forecast(tmp_path):
    frozen=model.freeze([prediction()],[fixture()],tmp_path/'x.json',now='2026-10-22T21:00:00Z')
    r=dict(fixture(),status='final',start_utc='2026-10-22T20:30:00Z',home_score=80,away_score=90,captured_at='2026-10-23T20:00:00Z')
    with pytest.raises(ValueError,match='pretipoff'):model.settle(frozen,[r],now='2026-10-24T00:00:00Z')


def observation():
    return dict(event_id='D1',competition='CZ_W_ZBL',season='2025-26',gender='Women',home='H',away='A',
        home_score=80,away_score=70,event_time='2026-01-01T12:00:00Z',captured_at='2026-10-22T12:00:00Z',
        available_at=None,source_url='https://example.org/game',status='final',date_precision='timestamp',score_verified=True)


def test_capture_time_not_event_time_controls_import_availability():
    identities={t:dict(gender='Women',category='senior') for t in ['H','A']}
    accepted,rejected=validate([observation()],identities,now='2026-10-23T00:00:00Z')
    assert len(accepted)==1 and not rejected
    assert asof(accepted,'2026-02-01T00:00:00Z')==[]
    assert len(asof(accepted,'2026-10-23T00:00:00Z'))==1
    invalid=dict(observation(),gender='Men')
    accepted,rejected=validate([invalid],identities,now='2026-10-23T00:00:00Z')
    assert not accepted and 'gender' in rejected[0]['reason']


def test_conflicting_import_scores_fail_explicitly():
    identities={t:dict(gender='Women',category='senior') for t in ['H','A']}
    with pytest.raises(ValueError,match='Conflicting'):validate([observation(),dict(observation(),home_score=90)],identities,now='2026-10-23T00:00:00Z')


def test_same_day_and_future_results_cannot_improve_quality():
    p=prediction();g=pd.DataFrame([dict(mac_id='G',lig='ECW',sezon='2026-27',ev='H',dep='A',tarih_utc=pd.Timestamp('2026-10-22T10:00:00Z'))])
    q=assess(p,g,now='2026-10-22T21:00:00Z')
    assert q['team_history']['H']['all_prior_games']==0 and q['status']=='limited'
    assert not q['recommendation_validated']


def test_score_probability_disagreement_visible_and_invalid_scores_rejected():
    p=prediction();p['ev_kazanir']=.2
    g=pd.DataFrame(columns=['lig','sezon','ev','dep','tarih_utc'])
    q=assess(p,g,now='2026-10-22T21:00:00Z')
    assert any('different teams' in issue for issue in q['issues'])
    p['ev_skor']=-1
    with pytest.raises(ValueError):validate_prediction(p)


def test_paired_comparison_matches_cohorts_and_day_blocks():
    a=pd.DataFrame(dict(mac_id=['a','b','c','d'],day=['1','1','2','2'],y=[1,0,1,0],p=[.7,.7,.7,.7]))
    b=a.copy();b['p']=[.7,.3,.7,.3]
    r=paired(a,b,replicates=100)
    assert r['day_blocks']==2 and r['changes']['accuracy']['delta']==.5
    assert r==paired(a,b,replicates=100)
    assert len(equal_coverage(a,b))==8
    with pytest.raises(ValueError,match='Identical'):paired(a,b.iloc[:2])
    b.loc[0,'y']=0
    with pytest.raises(ValueError,match='mismatch'):paired(a,b)


def test_domestic_feature_available_time_and_future_score_isolation():
    g=pd.DataFrame([dict(mac_id='T',ev='H',dep='A',tarih_utc=pd.Timestamp('2026-10-22T12:00:00Z'))])
    d=pd.DataFrame([dict(ev='H',dep='B',tarih_utc=pd.Timestamp('2026-10-21T12:00:00Z'),ev_skor=80,dep_skor=70,
        captured_at_utc='2026-10-23T12:00:00Z',available_at_utc=None)])
    assert features(g,d,point_in_time=True).dom_home_missing.iloc[0]==1
    assert features(g,d).dom_home_missing.iloc[0]==0
    d.loc[0,'tarih_utc']=pd.Timestamp('2026-10-22T01:00:00Z')
    assert features(g,d).dom_home_missing.iloc[0]==1


def test_official_domestic_parser_side_orientation_and_namespace():
    html='''<title>ŽBL.BASKETBALL</title><table><tbody><tr><td>1</td><td>1</td>
    <td data-sort="2025-09-26-18-30"></td><td><div class="text-nowrap">Žabiny Brno</div><div class="text-nowrap">KP Brno</div></td>
    <td><a href="/zapas/123#tab-pane-one"><div>84</div>67</a></td><td></td><td>Play-off</td></tr></tbody></table>'''
    r,f=parse(html,2025,'https://zbl.basketball/zapasy','2026-10-22T21:00:00Z')
    assert r[0]['ev']=='ECW_892' and r[0]['dep']=='ECW_891'
    assert r[0]['ev_skor']==84 and r[0]['dep_skor']==67
    with pytest.raises(ValueError,match='Wrong official'):parse(html.replace('ŽBL','NBL'),2025,'url','2026-10-22T21:00:00Z')


def test_live_transitions_reject_stale_wrong_fixture_and_unmarked_corrections():
    from bbtahmin.live import validate_transition
    previous=dict(home='H',away='A',score_observed=[20,18],period=2,remaining='08:00',observed_at_utc='2026-10-22T12:00:00Z')
    assert validate_transition(previous,'H','A',22,18,2,'07:30','2026-10-22T12:01:00Z')['explicit_source_correction'] is False
    with pytest.raises(ValueError,match='backwards'):validate_transition(previous,'H','A',19,18,2,'07:30','2026-10-22T12:01:00Z')
    assert validate_transition(previous,'H','A',19,18,2,'07:30','2026-10-22T12:01:00Z',True)['explicit_source_correction']
    with pytest.raises(ValueError,match='Out-of-order'):validate_transition(previous,'H','A',22,18,2,'07:30','2026-10-22T11:59:00Z')
    with pytest.raises(ValueError,match='another'):validate_transition(previous,'H','B',22,18,2,'07:30','2026-10-22T12:01:00Z')


def test_runtime_overlay_preserves_originals_and_rejects_conflicts():
    from bbtahmin.runtime_history import merge
    g=pd.DataFrame([dict(mac_id='g',lig='E',sezon='2025-26',tarih_utc=pd.Timestamp('2026-01-01T12:00:00Z'),ev='H',dep='A',ev_skor=80,dep_skor=70)])
    assert len(merge(g,g))==1
    changed=g.copy();changed['ev_skor']=90
    with pytest.raises(ValueError,match='conflicts'):merge(g,changed)


def test_monitoring_reports_missingness_without_automatic_retraining():
    from bbtahmin.monitoring import distribution_shift,reliability
    report=distribution_shift(pd.DataFrame({'f':[1.,2.,3.]}),pd.DataFrame({'f':[100.,np.nan]}),['f'])
    assert report['features'][0]['diagnostic_alert'] and report['features'][0]['current_missing_fraction']==.5
    assert report['automatic_retraining'] is False
    assert sum(b['n'] for b in reliability([0,1],[0.,1.])['bins'])==2


def test_cross_batch_import_conflict_cannot_silently_revise_history(tmp_path):
    from bbtahmin.context_import import ingest
    identities=tmp_path/'identities.json';identities.write_text(json.dumps({t:dict(gender='Women',category='senior') for t in ['H','A']}))
    first=tmp_path/'first.jsonl';first.write_text(json.dumps(observation())+'\n')
    destination=tmp_path/'imports';ingest(first,identities,destination)
    second=tmp_path/'second.jsonl';second.write_text(json.dumps(dict(observation(),home_score=90))+'\n')
    with pytest.raises(ValueError,match='Persisted'):ingest(second,identities,destination)


def test_empirical_quantiles_do_not_read_test_outcomes():
    from bbtahmin import competition_model as m
    from bbtahmin.ozellik import build_features
    g=m.load('ECW');x=build_features(g);seasons=sorted(g.sezon.unique())
    train=(g.sezon<seasons[1]).to_numpy();val=(g.sezon==seasons[1]).to_numpy();test=(g.sezon==seasons[2]).to_numpy()
    _,before=m.fit(x,g,train,val,test)
    changed=g.copy();changed.loc[test,'ev_skor']=200
    _,after=m.fit(x,changed,train,val,test)
    assert before==after


def test_club_strength_predictions_never_fit_same_day_or_future_results():
    from bbtahmin.club_strength import predict
    rows=[]
    for i in range(170):
        rows.append(dict(mac_id=str(i),ev='H' if i%2 else 'A',dep='A' if i%2 else 'H',
            ev_skor=(80 if i%2 else 70)+i%7,dep_skor=75+i%5,tarafsiz_saha=False,
            tarih_utc=pd.Timestamp('2025-01-01T12:00:00Z')+pd.Timedelta(days=i)))
    history=pd.DataFrame(rows);queries=history.tail(1).copy();cutoff='2025-06-15T00:00:00Z'
    a=predict(history,queries,cutoff)
    changed=history.copy();changed.loc[changed.tarih_utc>=pd.Timestamp(cutoff),['ev_skor','dep_skor']]=[10,200]
    np.testing.assert_array_equal(a,predict(changed,queries,cutoff))
