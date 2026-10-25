"""Existing learner ablations, whole-day features and prior-season policy.

Feature removal measures contribution; it is not a claim that the feature was
previously absent. All variants, including worse ones, remain in the report.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from bbtahmin.asia_model import fit_fold
from bbtahmin.experiment_metrics import metrics,paired
from bbtahmin.football.data import write_json
from bbtahmin.ozellik import build_features,RATING_FEATURES
from bbtahmin.prospective import fingerprint

VARIANTS=('baseline','form_slow','form_fast','without_rest','without_opponent_ratings','without_home')
REST=('rest_diff','back_to_back_diff','load7_diff','road_streak_diff','europe_load_diff')


def load(code):
    if code in ('E','NBA','NBL'):
        from bbtahmin.runtime_history import load as core
        games=core();paths=[Path('data/maclar.parquet')]
        if code=='E' and Path('data/recent/E.parquet').exists(): paths.append(Path('data/recent/E.parquet'))
    else:
        path=Path(f'data/asia/{code}.parquet') if code=='KBL' else Path(f'data/competitions/{code}.parquet')
        paths=[path];games=pd.read_parquet(path)
    games=games.loc[games.lig==code].sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    if games.mac_id.duplicated().any() or games.empty: raise ValueError('Empty or duplicate league history')
    return games,{p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def evaluate(code,games):
    active=pd.Timestamp.now(tz='UTC');year=active.year if active.month>=7 else active.year-1
    seasons=sorted(s for s in games.sezon.unique() if int(s[:4])<year)[-2:]
    rows=[];folds=[];skipped=[]
    for variant in VARIANTS:
        alpha=.1 if variant=='form_slow' else .35 if variant=='form_fast' else .2
        features=build_features(games,alpha=alpha)
        removed=(REST if variant=='without_rest' else RATING_FEATURES if variant=='without_opponent_ratings'
                 else ('home',) if variant=='without_home' else ())
        # Explicit removal, retaining identical scaler/learner dimensions.
        # Elo's built-in home advantage is reported separately and stays fixed.
        for column in removed: features[column]=0.
        for season in seasons:
            try: probabilities,scores,errors,info=fit_fold(games,features,season)
            except ValueError as exc:
                skipped.append(dict(variant=variant,season=season,reason=str(exc)));continue
            folds.append(dict(variant=variant,removed_features=list(removed),form_alpha=alpha,**info))
            for i,game in enumerate(games.loc[games.sezon==season].itertuples()):
                p=float(probabilities[info['selected']][i]);margin=float(scores[0][i])
                total=max(0.,float(scores[1][i]+errors[1]['bias']));margin=float(np.clip(margin,-total,total))
                cutoff=game.tarih_utc.floor('D');recent=games.loc[(games.tarih_utc<cutoff)&(games.tarih_utc>=cutoff-pd.Timedelta(days=400))]
                counts=[int(((recent.ev==t)|(recent.dep==t)).sum()) for t in (game.ev,game.dep)]
                ages=[None if recent.loc[(recent.ev==t)|(recent.dep==t)].empty else
                      (cutoff-recent.loc[(recent.ev==t)|(recent.dep==t),'tarih_utc'].max()).days for t in (game.ev,game.dep)]
                gate=min(counts)>=5 and all(age is not None and age<=60 for age in ages) and info['calibration_season_gap']==1
                rows.append(dict(event_id=game.mac_id,day=cutoff.strftime('%Y-%m-%d'),league=code,season=season,
                                 variant=variant,y=int(game.ev_skor>game.dep_skor),p=[1-p,p],
                                 selected=bool(gate and max(p,1-p)>=.65 and (p-.5)*margin>=0),
                                 team_score_mae=(abs((total+margin)/2-game.ev_skor)+abs((total-margin)/2-game.dep_skor))/2,
                                 total_mae=abs(total-game.ev_skor-game.dep_skor),margin_mae=abs(margin-game.ev_skor+game.dep_skor),
                                 total_in_80=bool(abs(total-game.ev_skor-game.dep_skor)<=1.2815515655446004*errors[1]['sigma'])))
    summaries={};comparisons={}
    for season in seasons:
        part=[r for r in rows if r['season']==season]
        if not part: continue
        summaries[season]={}
        for variant in VARIANTS:
            group=[r for r in part if r['variant']==variant]
            if not group: continue
            summaries[season][variant]=dict(**metrics([r['y'] for r in group],[r['p'] for r in group],[r['selected'] for r in group]),
                score_errors={k:float(np.mean([r[k] for r in group])) for k in ('team_score_mae','total_mae','margin_mae','total_in_80')})
            if variant!='baseline': comparisons[season+':'+variant]=paired(part,'baseline',variant)
    return dict(league=code,rows=rows,folds=folds,skipped=skipped,summaries=summaries,comparisons=comparisons,
                reference='Common prior-season learner policy; not identical to every production league model.',
                evidence_kind='exploratory_retrospective',production_default_changed=False,
                limitations='Already inspected historical seasons; publication availability unverified. Removal of home feature retains Elo home adjustment; this is a partial feature ablation. No observed possessions/rosters invented. Only previous seasons calibrate and choose learners; target outcomes never choose policy.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--leagues',nargs='+',default=['KBL','E','ABA','ECW','FEC','TR_BSL','UKR','ARG_LNB'])
    parser.add_argument('--output',default='docs/kanit/improvement/basketball')
    args=parser.parse_args();root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
    loaded={code:load(code) for code in args.leagues};code_hash=fingerprint()
    protocol=dict(variants=VARIANTS,leagues=args.leagues,source_code_sha256=code_hash,
                  inputs={c:v[1] for c,v in loaded.items()},selection_threshold=.65,
                  last_completed_seasons=2,predeclared_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),
                  note='Fixed previous-season disjoint calibration/selection, last two available past seasons; completeness unverified. No promotion.')
    path=root/'protocol.json'
    if path.exists():
        previous=json.loads(path.read_text())
        if any(previous.get(k)!=json.loads(json.dumps(v)) for k,v in protocol.items() if k!='predeclared_at_utc'):
            raise ValueError('Inputs/policy changed; use a new output version')
    else: write_json(path,protocol)
    reports=[]
    with threadpool_limits(limits=1):
        for code,(games,hashes) in loaded.items():
            report=evaluate(code,games)
            if fingerprint()!=code_hash: raise ValueError('Source changed during evaluation')
            (root/(code+'.json.gz')).write_bytes(gzip.compress(json.dumps(report,allow_nan=False).encode(),mtime=0))
            reports.append({k:v for k,v in report.items() if k!='rows'})
            print(code,{s:{v:m['all'] for v,m in variants.items()} for s,variants in report['summaries'].items()},flush=True)
    write_json(root/'summary.json',dict(protocol=protocol,reports=reports))


if __name__=='__main__': main()
