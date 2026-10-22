"""Experimental CBA remaining-score regression, trained on real quarter states.

Clock input is REMAINING time in the named period, never elapsed time. Periods
1..4 only; overtime requires a separately evaluated model and is rejected.
"""
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import cba_model


def state_features(prior_margin,prior_total,home_score,away_score,elapsed_fraction):
    f=elapsed_fraction;r=1-f
    return np.array([prior_margin*r,prior_total*r,(home_score-away_score)*r/f,
                     (home_score+away_score)*r/f,r],dtype=float)


def training_states(g=None,quarters=None):
    g=cba_model.load() if g is None else g
    quarters=pd.read_parquet('data/cba_quarters.parquet') if quarters is None else quarters
    prior=cba_model.walk_forward(g).set_index('mac_id');rows=[]
    for q in quarters.itertuples():
        if q.mac_id not in prior.index:continue
        p=prior.loc[q.mac_id]
        h,a=np.asarray(q.home_quarters,dtype=float),np.asarray(q.away_quarters,dtype=float)
        for period in [1,2,3]:
            hs,as_=float(h[:period].sum()),float(a[:period].sum())
            x=state_features(p.margin_prediction,p.total_prediction,hs,as_,period/4)
            rows.append(dict(mac_id=q.mac_id,sezon=q.sezon,tarih_utc=q.tarih_utc,period=period,
                home=hs,away=as_,regulation_tied=bool(h.sum()==a.sum()),remaining_margin=float(h[period:].sum()-a[period:].sum()),
                remaining_total=float(h[period:].sum()+a[period:].sum()),y=int(p.y),
                **{f'x{i}':float(v) for i,v in enumerate(x)}))
    return pd.DataFrame(rows)


def fit(states,test_season):
    history=states[states.sezon<test_season]
    seasons=sorted(history.sezon.unique())
    if len(seasons)<2:raise ValueError('Live model needs two earlier quarter-score seasons')
    val=history.sezon==seasons[-1];train=history.sezon<seasons[-1]
    if train.sum()<60 or val.sum()<60:raise ValueError('Insufficient live training/calibration sample')
    cols=[f'x{i}' for i in range(5)];models=[];sigma=[]
    for target in ['remaining_margin','remaining_total']:
        def estimator():return make_pipeline(StandardScaler(),Ridge(alpha=10.))
        initial=estimator().fit(history.loc[train,cols],history.loc[train,target])
        residual=history.loc[val,target]-initial.predict(history.loc[val,cols])
        # Variance scales with remaining time; calibrate its rate on held-out games.
        remain=1-history.loc[val,'period'].to_numpy()/4
        sigma.append(max(float(np.std(residual.to_numpy()/np.sqrt(remain),ddof=1)),1.))
        models.append(estimator().fit(history[cols],history[target]))
    return models,sigma,dict(training_games=int(history.mac_id.nunique()),calibration_season=seasons[-1])


def project(prior,home_score,away_score,period,remaining,minutes,models,sigma):
    if minutes not in (40,48):raise ValueError('Regulation duration must be 40 or 48 minutes')
    if type(period) is not int or not 1<=period<=4:raise ValueError('Only regulation periods 1..4 supported; no overtime')
    if any(type(s) is not int or not 0<=s<=250 for s in [home_score,away_score]):raise ValueError('Scores must be nonnegative integers <=250')
    try:
        mm,ss=map(int,remaining.split(':'))
    except (ValueError,AttributeError):raise ValueError('Clock must be MM:SS remaining in this period') from None
    if not 0<=ss<60 or not 0<=mm*60+ss<=minutes*15:raise ValueError('Clock exceeds period duration')
    elapsed=(period-1)*minutes*15+(minutes*15-mm*60-ss)
    f=elapsed/(minutes*60)
    if not 0<f<1:raise ValueError('Need an in-progress regulation game with time remaining')
    x=state_features(prior['fark'],prior['toplam'],home_score,away_score,f).reshape(1,-1)
    x=pd.DataFrame(x,columns=[f'x{i}' for i in range(5)])
    rm=float(models[0].predict(x)[0]);rt=max(float(models[1].predict(x)[0]),0.)
    # Neither team's projected final score may fall below its observed score.
    rh=max((rt+rm)/2,0.);ra=max((rt-rm)/2,0.)
    h,a=home_score+rh,away_score+ra
    sm,st=[s*np.sqrt(1-f) for s in sigma];z=norm.ppf(.9)
    return dict(home_score=h,away_score=a,total=h+a,margin=h-a,
        home_regulation_lead_probability=float(norm.cdf((h-a)/sm)),
        total_80=[max(home_score+away_score,h+a-z*st),h+a+z*st],
        elapsed_fraction=f,regulation_minutes=minutes,period=period,remaining=remaining,
        score_observed=[home_score,away_score],experimental=True,
        note='Regulation score projection. Win probability uses normal residual approximation; '
             'quarter-boundary evaluation does not establish within-quarter calibration. No overtime projection.')


def validate_transition(previous,home,away,home_score,away_score,period,remaining,observed_at,correction=False):
    from .quality import timestamp
    if previous.get('home')!=home or previous.get('away')!=away:raise ValueError('Previous state belongs to another fixture')
    if timestamp(observed_at)<=timestamp(previous['observed_at_utc']):raise ValueError('Out-of-order or duplicate observation')
    old_h,old_a=previous['score_observed']
    def seconds(clock):
        parts=clock.split(':')
        if len(parts)!=2 or not all(p.isdigit() for p in parts):raise ValueError('Invalid remaining clock')
        mm,ss=map(int,parts)
        if ss>=60:raise ValueError('Invalid remaining clock')
        return mm*60+ss
    backward=period<previous['period'] or (period==previous['period'] and seconds(remaining)>seconds(previous['remaining']))
    if not correction and (home_score<old_h or away_score<old_a or backward):
        raise ValueError('Score/clock went backwards; explicit source correction required')
    return dict(previous_observed_at_utc=previous['observed_at_utc'],explicit_source_correction=bool(correction))


def predict(home,away,home_score,away_score,period,remaining,observed_at,minutes=None,replay=False,
            previous_state=None,score_correction=False):
    date=pd.Timestamp(observed_at);now=pd.Timestamp.now(tz='UTC')
    if date.tzinfo is None or pd.isna(date) or date>now:raise ValueError('Observation needs a valid non-future timezone-aware timestamp')
    if not replay and (now-date).total_seconds()>120:raise ValueError('Live observation older than 120 seconds; use explicit replay for historical inputs')
    transition=validate_transition(previous_state,home,away,home_score,away_score,period,remaining,date,score_correction) if previous_state is not None else None
    prior=cba_model.predict(home,away,date)
    duration=prior['regulation_minutes'] if minutes is None else minutes
    if duration!=prior['regulation_minutes']:raise ValueError('Duration disagrees with the trained CBA season regime')
    states=training_states();cutoff=pd.Timestamp(date.tz_convert('Asia/Shanghai').date(),tz='UTC')
    states=states[states.tarih_utc<cutoff]
    season=f'{date.year if date.month>=7 else date.year-1}-{str((date.year if date.month>=7 else date.year-1)+1)[-2:]}'
    models,sigma,info=fit(states,season)
    result=project(prior,home_score,away_score,period,remaining,duration,models,sigma)
    quarter_path=Path('data/cba_quarters.parquet')
    quarter_fingerprint=hashlib.sha256(quarter_path.read_bytes()).hexdigest()
    evidence=Path('docs/kanit/cba/manifest.json')
    manifest=json.loads(evidence.read_text()) if evidence.exists() else {}
    result.update(home=home,away=away,observed_at_utc=date.tz_convert('UTC').isoformat(),
        replay=bool(replay),transition=transition,input_source='Manual observed game state; not an automatic live feed',
        prior=prior,model='cba-remaining-ridge-v1',quarter_dataset_sha256=quarter_fingerprint,
        quarter_dataset_matches_evaluation=manifest.get('files',{}).get(str(quarter_path))==quarter_fingerprint,**info)
    return result
