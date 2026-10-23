"""Observable data adequacy, not a fabricated probability of model correctness."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ARCHIVES={'core':'data/maclar.parquet','CBA':'data/cba_games.parquet',
          **{c:f'data/competitions/{c}.parquet' for c in ('ECW','FEC','VTB','ELW','ABA','UKR','TR_BSL')},
          'CZ_W_ZBL':'data/domestic/CZ_W_ZBL.parquet','E_recent':'data/recent/E.parquet'}


def timestamp(value):
    t=pd.Timestamp(value)
    if pd.isna(t) or t.tzinfo is None:raise ValueError('A timezone-aware timestamp is required')
    return t.tz_convert('UTC')


def validate_prediction(p):
    for k in ('ev_kazanir','ev_skor','dep_skor','toplam','fark'):
        if not np.isfinite(p[k]):raise ValueError(f'Non-finite prediction: {k}')
    if not 0<=p['ev_kazanir']<=1 or min(p['ev_skor'],p['dep_skor'])<0:
        raise ValueError('Invalid probability or score')
    if p['ev']==p['dep']:raise ValueError('Same team on both sides')
    if not np.isclose(p['ev_skor']+p['dep_skor'],p['toplam']) or not np.isclose(p['ev_skor']-p['dep_skor'],p['fark']):
        raise ValueError('Inconsistent score, total and margin')
    for key,value in [('toplam_80',p['toplam']),('fark_80',p['fark'])]:
        lo,hi=p[key]
        if not np.isfinite([lo,hi]).all() or not lo<=value<=hi:raise ValueError('Invalid prediction interval')
    timestamp(p['tarih_utc'])


def team_history(g,team,cutoff):
    cutoff=timestamp(cutoff).floor('D')
    dates=pd.to_datetime(g.tarih_utc,utc=True)
    past=g[((g.ev==team)|(g.dep==team))&(dates<cutoff)].copy()
    past['tarih_utc']=pd.to_datetime(past.tarih_utc,utc=True)
    age=(cutoff-past.tarih_utc).dt.total_seconds()/86400
    weights=np.exp(-np.log(2)*age/180)
    recent=past[age<=400]
    return dict(all_prior_games=len(past),recent_400d_games=len(recent),
        days_since_last=float(age.min()) if len(age) else None,
        effective_games_180d_half_life=float(weights.sum()),
        opponents=int(pd.concat([recent.loc[recent.ev==team,'dep'],recent.loc[recent.dep==team,'ev']]).nunique()),
        seasons=sorted(past.sezon.unique().tolist()))


def assess(p,g,now=None):
    validate_prediction(p)
    now=timestamp(now or pd.Timestamp.now(tz='UTC'))
    cutoff=min(now,pd.Timestamp(p['tarih_utc'])).floor('D')
    g=g[g.lig==p['lig']]
    history={t:team_history(g,t,cutoff) for t in (p['ev'],p['dep'])}
    reasons=[]
    for team,h in history.items():
        if h['recent_400d_games']<5:reasons.append(f'{team}: fewer than five observed games in 400 days')
        if h['days_since_last'] is None or h['days_since_last']>60:reasons.append(f'{team}: missing or stale recent results')
    blocking=list(reasons)
    if p.get('calibration_regime_gap'):
        issue='Prior calibration season is not adjacent; current-regime calibration is unverified'
        reasons.append(issue);blocking.append(issue)
    if p.get('artifact_status',{}).get('dataset_matches_evaluation') is False:
        reasons.append('Prediction dataset differs from the historical benchmark dataset')
    if ((p['ev_kazanir']>.5 and p['fark']<0) or (p['ev_kazanir']<.5 and p['fark']>0)):
        reasons.append('Winner model and score model favor different teams')
        blocking.append('Winner model and score model favor different teams')
    return dict(status='limited' if reasons else 'observed_history_available',
        issues=reasons,blocking_issues=blocking,diagnostic_gate_passed=not blocking,team_history=history,information_cutoff_utc=cutoff.isoformat(),
        recommendation_validated=False,
        thresholds='Five games / 400 days and 60-day staleness are diagnostic flags, not validated selection thresholds.',
        unknowns=['Full domestic schedule coverage','Expected roster and injuries','Historical publication times for retrospectively collected results'],
        note='Data adequacy is separate from win probability; no validated recommendation or accuracy guarantee.')


def inventory(root=Path('.')):
    root=Path(root);report=[]
    archives=dict(ARCHIVES)
    archives.update({p.stem:str(p.relative_to(root)) for p in (root/'data/domestic').glob('*.parquet') if not p.name.endswith('_fixtures.parquet')})
    archives.update({p.stem:str(p.relative_to(root)) for p in (root/'data/asia').glob('*.parquet') if p.stem in ('KBL','JP_B1','JP_B2','PBA_GOV','PBA_COM','PBA_PHI')})
    for name,rel in archives.items():
        path=root/rel
        if not path.exists():continue
        g=pd.read_parquet(path)
        for (code,season),part in g.groupby(['lig','sezon']):
            times=pd.to_datetime(part.tarih_utc,utc=True)
            report.append(dict(archive=rel,league=code,season=season,games=len(part),
                teams=int(pd.concat([part.ev,part.dep]).nunique()),first=times.min().isoformat(),last=times.max().isoformat(),
                duplicate_ids=int(part.mac_id.duplicated().sum()),same_team=int((part.ev==part.dep).sum()),
                invalid_scores=int(((part.ev_skor<=0)|(part.dep_skor<=0)|(part.ev_skor==part.dep_skor)).sum()),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                completeness='Unknown: result count alone does not establish complete season coverage',
                cohort_warning=code=='VTB'))
    return report


def write_inventory(destination='docs/kanit/governance'):
    root=Path(destination);root.mkdir(parents=True,exist_ok=True)
    report=inventory();pd.DataFrame(report).to_csv(root/'coverage.csv',index=False)
    (root/'coverage.json').write_text(json.dumps(report,indent=2))
    return report
