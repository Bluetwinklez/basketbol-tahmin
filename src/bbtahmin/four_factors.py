"""Lagged shooting/possession profiles; never reads a target game's box score.

Offense and allowed-opponent profiles are updated after the whole UTC day.
Unknown teams use the league's observed historical average, with coverage flags.
"""
from collections import defaultdict
from itertools import groupby
from pathlib import Path

import numpy as np
import pandas as pd

RATES=('efg','tov','orb','ft','three','pace')
FACTOR_FEATURES=[f'ff_{name}_{kind}' for name in RATES for kind in ('diff','mean')]+['ff_coverage_diff','ff_coverage_min']
# Candidates only. No league is activated until chronological tests justify it.
FACTOR_LEAGUES=set()


def load_boxes(root='data'):
    root=Path(root);tables=[]
    for filename,europe in [('nba_takim_istatistik.parquet',False),('avrupa_takim_istatistik.parquet',True)]:
        path=root/filename
        if not path.exists():
            continue
        t=pd.read_parquet(path)
        if europe:
            t=t.rename(columns={'fgm':'fgm_unused','fg2m':'two_made','fg3m':'three_made','fg2a':'two_attempted',
                'fg3a':'three_attempted','ftm':'free_made','fta':'free_attempted','rebounds_offensive':'oreb',
                'rebounds_defensive':'dreb','turnovers':'tov'})
            t['made']=t.two_made+t.three_made;t['attempted']=t.two_attempted+t.three_attempted
            t['rol']=t.is_home.map({True:'ev',False:'dep'})
        else:
            t=t.rename(columns={'field_goals_made':'made','field_goals_attempted':'attempted',
                'three_point_field_goals_made':'three_made','three_point_field_goals_attempted':'three_attempted',
                'free_throws_made':'free_made','free_throws_attempted':'free_attempted',
                'offensive_rebounds':'oreb','defensive_rebounds':'dreb','total_turnovers':'tov'})
        cols=['mac_id','rol','made','attempted','three_made','three_attempted','free_made','free_attempted','oreb','dreb','tov']
        tables.append(t[cols].copy())
    if not tables:
        return pd.DataFrame()
    t=pd.concat(tables,ignore_index=True).drop_duplicates(['mac_id','rol'])
    numeric=[c for c in t if c not in ('mac_id','rol')]
    t[numeric]=t[numeric].apply(pd.to_numeric,errors='coerce')
    t=t.dropna(subset=numeric)
    t=t[(t.attempted>0)&np.isfinite(t[numeric]).all(axis=1)&(t[numeric]>=0).all(axis=1)&(t.made<=t.attempted)
        &(t.three_made<=t.three_attempted)&(t.three_attempted<=t.attempted)&(t.free_made<=t.free_attempted)]
    duration=[]
    for path in [root/'kutu.parquet',root/'kutu_nba.parquet']:
        if path.exists():
            duration.append(pd.read_parquet(path)[['mac_id','rol','sure']])
    if duration:
        d=pd.concat(duration).drop_duplicates(['mac_id','rol'])
        t=t.merge(d,on=['mac_id','rol'],how='left',validate='one_to_one')
    else:
        t['sure']=np.nan
    return t


def build_factors(games,boxes,alpha=.15):
    if not 0<alpha<=1:
        raise ValueError('alpha must be in (0,1]')
    records={}
    if boxes is not None and not boxes.empty:
        records={(r.mac_id,r.rol):r for r in boxes.itertuples(index=False)}
    states={};league_sum=defaultdict(lambda:np.zeros(len(RATES)));league_n=defaultdict(int);out=[]
    data=games.sort_values(['tarih_utc','mac_id'])
    for _,batch in groupby(data.itertuples(index=False),lambda r:r.tarih_utc.floor('D')):
        pending=[]
        for r in batch:
            prior=league_sum[r.lig]/max(1,league_n[r.lig])
            profiles=[]
            for team in (r.ev,r.dep):
                s=states.get((r.lig,team))
                if s is None:
                    s=dict(off=prior.copy(),defense=prior.copy(),n=0)
                    states[r.lig,team]=s
                profiles.append(s)
            h,a=profiles
            ho,hd=(h['off'],h['defense']) if h['n'] else (prior,prior)
            ao,ad=(a['off'],a['defense']) if a['n'] else (prior,prior)
            eh,ea=(ho+ad)/2,(ao+hd)/2
            row=dict(mac_id=r.mac_id,ff_coverage_diff=np.log1p(h['n'])-np.log1p(a['n']),
                     ff_coverage_min=np.log1p(min(h['n'],a['n'])))
            for i,name in enumerate(RATES):
                row[f'ff_{name}_diff']=float(eh[i]-ea[i])
                row[f'ff_{name}_mean']=float((eh[i]+ea[i])/2)
            out.append(row);pending.append((r,h,a))
        for r,h,a in pending:
            if pd.isna(r.ev_skor) or pd.isna(r.dep_skor):
                continue
            hb,ab=records.get((r.mac_id,'ev')),records.get((r.mac_id,'dep'))
            if hb is None or ab is None:
                continue
            def rates(b,opp):
                possessions=b.attempted-b.oreb+b.tov+.44*b.free_attempted
                duration=b.sure if pd.notna(b.sure) and b.sure>0 else (2880 if r.lig=='NBA' else 2400)
                regulation=2880 if r.lig=='NBA' else 2400
                return np.array([(b.made+.5*b.three_made)/b.attempted,b.tov/max(1,possessions),
                    b.oreb/max(1,b.oreb+opp.dreb),b.free_made/b.attempted,
                    b.three_attempted/b.attempted,possessions*regulation/duration])
            hv,av=rates(hb,ab),rates(ab,hb)
            for s,off,defense in [(h,hv,av),(a,av,hv)]:
                if s['n']:
                    s['off']+=alpha*(off-s['off']);s['defense']+=alpha*(defense-s['defense'])
                else:
                    s['off'],s['defense']=off.copy(),defense.copy()
                s['n']+=1
                league_sum[r.lig]+=off;league_n[r.lig]+=1
    return pd.DataFrame(out).set_index('mac_id').loc[games.mac_id].reset_index()
