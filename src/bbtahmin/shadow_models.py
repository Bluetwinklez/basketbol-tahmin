"""Fixed experimental challengers for forward pairs, no production promotion."""
import numpy as np
import pandas as pd
from scipy.stats import norm

from .quality import assess


def basketball(p,clock):
    return dict(league=p['lig'],home=p['ev'],away=p['dep'],model=p['model'],
                probabilities=[p['ev_kazanir'],1-p['ev_kazanir']],class_labels=['home','away'],
                expected_home=p['ev_skor'],expected_away=p['dep_skor'],
                information_cutoff_utc=clock.isoformat(),
                eligible=bool(p.get('selection_eligible',False) and max(p['ev_kazanir'],1-p['ev_kazanir'])>=.65))


def slow_form(code,fixture,clock,policy):
    """Frozen earlier-OOS feature/calibration policy, separately for each league."""
    from .asia_model import fit_fold
    from .ozellik import build_features,RATING_FEATURES
    from .prior_policy import calibrated
    from .runtime_history import load as core
    from pathlib import Path
    if code=='E': games=core();games=games.loc[games.lig==code].copy()
    else: games=pd.read_parquet(Path('data/asia' if code=='KBL' else 'data/competitions')/(code+'.parquet'))
    if set(games.lig)!={code} or games.mac_id.duplicated().any():raise ValueError('Mixed or duplicate challenger league history')
    scores=games[['ev_skor','dep_skor']].to_numpy(float)
    if not np.isfinite(scores).all() or (scores<=0).any() or (scores[:,0]==scores[:,1]).any():
        raise ValueError('Invalid challenger basketball finals')
    games=games.loc[games.tarih_utc<clock].sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    start=pd.Timestamp(fixture['start_utc']);year=start.year if start.month>=7 else start.year-1
    season=f'{year}-{str(year+1)[-2:]}'
    query=dict(mac_id='SHADOW_QUERY',lig=code,sezon=season,tarih_utc=start,ev=fixture['home'],dep=fixture['away'],
               ev_skor=np.nan,dep_skor=np.nan,tarafsiz_saha=False)
    combined=pd.concat([games,pd.DataFrame([query])],ignore_index=True)
    variant=policy['variant']
    if variant not in ('baseline','form_slow','form_fast','without_rest','without_opponent_ratings','without_home'):
        raise ValueError('Unknown frozen basketball pipeline')
    features=build_features(combined,alpha=.1 if variant=='form_slow' else .35 if variant=='form_fast' else .2)
    removed=(('rest_diff','back_to_back_diff','load7_diff','road_streak_diff','europe_load_diff') if variant=='without_rest'
             else RATING_FEATURES if variant=='without_opponent_ratings' else ('home',) if variant=='without_home' else ())
    for column in removed:features[column]=0.
    probabilities,scores,errors,info=fit_fold(combined,features,season)
    i=combined.loc[combined.sezon==season,'mac_id'].tolist().index('SHADOW_QUERY')
    total=max(0.,float(scores[1][i]+errors[1]['bias']));margin=float(np.clip(scores[0][i],-total,total))
    p=float(probabilities[info['selected']][i]);z=float(norm.ppf(.9))
    native=dict(lig=code,ev=fixture['home'],dep=fixture['away'],tarih_utc=start.isoformat(),
                model='shadow-prior-pipeline-v1/'+variant+'/'+info['selected'],ev_kazanir=p,ev_skor=(total+margin)/2,dep_skor=(total-margin)/2,
                toplam=total,fark=margin,toplam_80=[max(0.,total-z*errors[1]['sigma']),total+z*errors[1]['sigma']],
                fark_80=[margin-z*errors[0]['sigma'],margin+z*errors[0]['sigma']],
                calibration_regime_gap=info['calibration_season_gap']>1 or int(season[:4])-int(policy['prior_season'][:4])!=1)
    health=assess(native,games,now=clock)
    native['selection_eligible']=health['diagnostic_gate_passed']
    result=basketball(native,clock);result['history_health']=health;result['prior_selection']=info
    result['probabilities']=calibrated(result['probabilities'],policy['temperature']).tolist()
    result['eligible']=bool(health['diagnostic_gate_passed'] and max(result['probabilities'])>=.65)
    result['frozen_pipeline_policy']=policy
    return result


def football(p,fixture,clock,health):
    return dict(league=fixture['league'],home=fixture['home'],away=fixture['away'],model=p['model'],
                probabilities=[p['probabilities'][k] for k in ('home','draw','away')],class_labels=['home','draw','away'],
                expected_home=p['expected_home_goals'],expected_away=p['expected_away_goals'],
                information_cutoff_utc=clock.isoformat(),history_health=health,
                eligible=bool(health['diagnostic_gate_passed'] and not p['issues'] and max(p['probabilities'].values())>=.65))
