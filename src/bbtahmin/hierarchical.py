"""Hierarchical Gaussian-prior MAP attack/defence model across linked competitions.

Competition scoring levels, country groups from verified domestic membership and
club deviations have separate fixed shrinkage priors. Fit remains research-only.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.stats import norm
from sklearn.linear_model import Ridge

SPEC='linked-women-hierarchical-map-v1'


def observations(g=None):
    from . import competition_model as base
    g=base.load('ECW') if g is None else g.copy()
    if set(g.lig)!={'ECW'}:raise ValueError('Only verified senior-women targets allowed')
    parts=[g];groups={}
    side=Path('data/competitions/ELW.parquet')
    if side.exists():
        p=pd.read_parquet(side)
        if set(p.lig)!={'ELW'}:raise ValueError('Mixed competition namespace')
        p['ev']=p.ev.str.replace('ELW_','ECW_',n=1);p['dep']=p.dep.str.replace('ELW_','ECW_',n=1);parts.append(p)
    for path in sorted(Path('data/domestic').glob('*.parquet')):
        if path.name.endswith('_fixtures.parquet'):continue
        p=pd.read_parquet(path)
        if 'gender' not in p or set(p.gender)!={'Women'}:continue
        if len(set(p.lig))!=1:raise ValueError('Mixed domestic league')
        country=str(p.lig.iloc[0]).split('_')[0]
        for t in (set(p.ev)|set(p.dep)) if country!='WABA' else []:
            if t in groups and groups[t]!=country:raise ValueError('Conflicting verified domestic country membership')
            groups[t]=country
        parts.append(p)
    all_games=pd.concat(parts,ignore_index=True).sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    if 'model_time_utc' in all_games:
        all_games['tarih_utc']=pd.to_datetime(all_games.model_time_utc,utc=True).fillna(all_games.tarih_utc)
        all_games=all_games.sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    if all_games.mac_id.duplicated().any():raise ValueError('Duplicate linked fixture')
    if (all_games.ev==all_games.dep).any() or (all_games.ev_skor<=0).any() or (all_games.dep_skor<=0).any():raise ValueError('Invalid finished score')
    return g,all_games,groups


def schema(history,groups):
    teams=sorted(set(history.ev)|set(history.dep));countries=sorted(set(groups.get(t,'unknown') for t in teams))
    keys=[]
    for comp in sorted(history.lig.unique()):keys += [('level',comp),('home',comp)]
    for country in countries:keys += [('group_off',country),('group_def',country)]
    for team in teams:keys += [('club_off',team),('club_def',team)]
    return {key:i for i,key in enumerate(keys)}


def design(g,keys,groups):
    rows=[];cols=[];values=[]
    penalties={'level':.0001,'home':1.,'group_off':20.,'group_def':20.,'club_off':10.,'club_def':10.}
    for i,r in enumerate(g.itertuples()):
        if ('level',r.lig) not in keys:raise ValueError('Unknown target competition scoring level')
        for side,(team,opponent,home_sign) in enumerate([(r.ev,r.dep,.5),(r.dep,r.ev,-.5)]):
            neutral=False if pd.isna(r.tarafsiz_saha) else bool(r.tarafsiz_saha)
            entries=[(('level',r.lig),1.),(('home',r.lig),0. if neutral else home_sign),
                (('group_off',groups.get(team,'unknown')),1.),(('group_def',groups.get(opponent,'unknown')),1.),
                (('club_off',team),1.),(('club_def',opponent),1.)]
            for key,value in entries:
                if key in keys:
                    rows.append(2*i+side);cols.append(keys[key]);values.append(value/np.sqrt(penalties[key[0]]))
    return csr_matrix((values,(rows,cols)),shape=(2*len(g),len(keys)))


def fit_predict(history,queries,cutoff,groups):
    date=pd.Timestamp(cutoff)
    if date.tzinfo is None:raise ValueError('Timezone-aware cutoff required')
    h=history[history.tarih_utc<date.floor('D')].copy()
    if len(h)<150:raise ValueError('Insufficient linked training history')
    domestic=h[~h.lig.isin(['ECW','ELW'])]
    known=set(domestic.ev)|set(domestic.dep)
    groups={t:country for t,country in groups.items() if t in known}
    keys=schema(h,groups);x=design(h,keys,groups)
    age=(date-h.tarih_utc).dt.total_seconds().to_numpy()/86400
    weights=np.repeat(np.exp(-np.log(2)*age/365),2)
    y=h[['ev_skor','dep_skor']].to_numpy(float).reshape(-1)
    estimator=Ridge(alpha=1.,fit_intercept=False,solver='lsqr',tol=1e-8).fit(x,y,sample_weight=weights)
    prediction=estimator.predict(design(queries,keys,groups)).reshape(-1,2)
    return np.maximum(prediction,0.)


def rolling(exposure,queries,groups):
    result=np.empty((len(queries),2));days=queries.tarih_utc.dt.floor('D')
    for day in sorted(days.unique()):
        mask=(days==day).to_numpy()
        result[mask]=fit_predict(exposure,queries.loc[mask],day,groups)
    return result


def fold(g,exposure,groups,season):
    earlier=sorted(s for s in g.sezon.unique() if s<season)
    if len(earlier)<2:raise ValueError('Two earlier target seasons required')
    previous=earlier[-1];val=g[g.sezon==previous];test=g[g.sezon==season]
    pv=rolling(exposure,val,groups)
    pt=rolling(exposure,test,groups)
    residual=(val.ev_skor-val.dep_skor).to_numpy(float)-(pv[:,0]-pv[:,1])
    sigma=max(float(np.std(residual,ddof=1)),1.)
    days=val.tarih_utc.dt.floor('D');unique=sorted(days.unique());boundary=unique[len(unique)//2]
    selection_sigma=max(float(np.std(residual[(days<boundary).to_numpy()],ddof=1)),1.)
    return norm.cdf((pv[:,0]-pv[:,1])/selection_sigma),norm.cdf((pt[:,0]-pt[:,1])/sigma),pt


def predict(home,away,when):
    from .competition_model import predict as baseline
    g,exposure,groups=observations();date=pd.Timestamp(when)
    if date.tzinfo is None:raise ValueError('Timezone-aware fixture required')
    g=g[g.tarih_utc<date.floor('D')];exposure=exposure[exposure.tarih_utc<date.floor('D')]
    year=date.year if date.month>=7 else date.year-1;season=f'{year}-{str(year+1)[-2:]}'
    earlier=sorted(s for s,n in g.groupby('sezon').size().items() if s<season and n>=100)
    if not earlier:raise ValueError('No earlier calibration season')
    previous=earlier[-1];val=g[g.sezon==previous]
    pv=rolling(exposure,val,groups)
    query=pd.DataFrame([dict(mac_id='QUERY',lig='ECW',ev=home,dep=away,tarih_utc=date,tarafsiz_saha=False)])
    pt=fit_predict(exposure,query,date,groups)[0]
    actual=np.column_stack([(val.ev_skor-val.dep_skor).to_numpy(),(val.ev_skor+val.dep_skor).to_numpy()])
    estimates=np.column_stack([pv[:,0]-pv[:,1],pv[:,0]+pv[:,1]])
    sigma=np.maximum(np.std(actual-estimates,axis=0,ddof=1),1.)
    margin,total=float(pt[0]-pt[1]),float(pt.sum());prob=float(norm.cdf(margin/sigma[0]));z=norm.ppf(.9)
    result=baseline('ECW',home,away,date)
    result.pop('empirical_intervals_research',None)
    result.update(model=SPEC,ev_kazanir=prob,ev_skor=float(pt[0]),dep_skor=float(pt[1]),fark=margin,toplam=total,
        fark_80=[margin-z*sigma[0],margin+z*sigma[0]],toplam_80=[max(0.,total-z*sigma[1]),total+z*sigma[1]],
        tum_modeller={SPEC:prob},hierarchical_research=True,
        hierarchical_note='Fixed Gaussian shrinkage MAP; conditional posterior uncertainty not included. Country membership comes from retrospectively collected domestic history. No independent superiority claim.')
    return result
