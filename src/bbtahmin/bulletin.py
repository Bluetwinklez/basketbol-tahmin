"""Local bulletin inspection and model/market comparison; no betting execution."""
from pathlib import Path

import pandas as pd
from scipy.stats import norm

from .odds import no_vig
from .veri.iddaa import load


def list_events(root='.',league=None,limit=30,now=None):
    if not 1<=limit<=200:
        raise ValueError('limit must be between 1 and 200')
    snapshot=load(Path(root)/'data/bulten/latest.json',now=now)
    cutoff=pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    events=[e for e in snapshot['events'] if pd.Timestamp(e['start_utc'])>cutoff
            and (league is None or e['model_league']==league)]
    return dict(captured_at_utc=snapshot['captured_at_utc'],age_minutes=snapshot['age_minutes'],
                stale=snapshot['stale'],total_upcoming=len(events),events=events[:limit])


def compare(prediction,event):
    comparison={}
    quote=event.get('moneyline')
    if quote:
        home=prediction['ev_kazanir'];away=1-home
        market=no_vig(quote['home_odds'],quote['away_odds'])
        comparison['moneyline']=dict(model_home=home,market_home=float(market[0]),
            home_edge=home-float(market[0]),home_expected_return=home*quote['home_odds']-1,
            away_expected_return=away*quote['away_odds']-1,
            minimum_combination_count=quote['minimum_combination_count'])
    comparison['totals']=[]
    sigma=(prediction['toplam_80'][1]-prediction['toplam'])/norm.ppf(.9)
    if sigma<=0:
        raise ValueError('Invalid model interval')
    for quote in event.get('totals',[]):
        line=quote['line']
        if (line*2)%1:
            continue  # quarter-lines need split-stake settlement, not this formula
        if float(line).is_integer():
            lower=norm.cdf((line-.5-prediction['toplam'])/sigma)
            upper=norm.cdf((line+.5-prediction['toplam'])/sigma)
            under,over,push=float(lower),float(1-upper),float(upper-lower)
        else:
            under=float(norm.cdf((line-prediction['toplam'])/sigma));over=1-under;push=0.
        comparison['totals'].append(dict(line=line,under=under,over=over,push=push,
            under_expected_return=under*(quote['under_odds']-1)-over,
            over_expected_return=over*(quote['over_odds']-1)-under,
            assumption='Normal total-score approximation; integer lines use continuity correction.'))
    comparison['note']='Model estimates, not observed accuracy. MBS/combination and promotion restrictions may prevent a standalone bet.'
    return comparison


def predict_event(event_id,root='.'):
    from .takim_ad import coz
    from .tahmin import aktif_kodlar,tahmin_et
    root=Path(root)
    if root.resolve()!=Path.cwd().resolve():
        raise ValueError('Run prediction from the configured project root so all artifacts have the same scope')
    snapshot=load(root/'data/bulten/latest.json')
    candidates=[e for e in snapshot['events'] if e['event_id']==str(event_id)]
    if len(candidates)!=1:
        raise ValueError('Event ID is not uniquely present in the local bulletin')
    event=candidates[0];league=event['model_league'];start=pd.Timestamp(event['start_utc'])
    now=pd.Timestamp.now(tz='UTC')
    if start<=now:
        raise ValueError('This is a pregame model; the event has already started')
    if not league:
        raise ValueError('This competition has no trained model in this project')
    if snapshot['stale']:
        raise ValueError('Bulletin is older than 15 minutes; refresh before comparing odds')
    games=pd.read_parquet(root/'data/maclar.parquet')
    codes=aktif_kodlar(games,league,now)
    home,away=coz(league,event['home'],codes),coz(league,event['away'],codes)
    if home==away:
        raise ValueError('Ambiguous matchup: both teams resolved to the same code')
    # The caller/CLI sets the project cwd for parameter and auxiliary data paths.
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=1):
        prediction=tahmin_et(league,[(home,away)],start,veri=str(root/'data/maclar.parquet'))[0]
    return dict(event=event,prediction=prediction,comparison=compare(prediction,event),
                injury_features='Disabled: historical participant lists are not pregame injury snapshots.')
