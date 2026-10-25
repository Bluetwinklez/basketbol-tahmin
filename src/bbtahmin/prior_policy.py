"""Choose a research pipeline using only earlier out-of-sample predictions."""
import numpy as np
from scipy.special import softmax

from .experiment_metrics import metrics

TEMPERATURES=(.75,1.,1.25,1.5,2.)


def calibrated(probabilities,temperature):
    if temperature not in TEMPERATURES:raise ValueError('Unknown predeclared calibration temperature')
    return softmax(np.log(np.clip(probabilities,1e-15,1))/temperature,axis=-1)


def learn(rows,variants,cutoff,basketball=False):
    prior=[r for r in rows if r['day']<cutoff and r['variant'] in variants]
    if not prior:raise ValueError('No earlier OOS evidence')
    season=max(r['season'] for r in prior);prior=[r for r in prior if r['season']==season]
    days=sorted({r['day'] for r in prior});boundary=days[len(days)//2]
    settings={};validation={};cohorts=[]
    for variant in variants:
        group=[r for r in prior if r['variant']==variant]
        if basketball:
            group=[dict(r,p=r['p'][::-1],y=1-r['y']) for r in group]  # home first, including ties
        if len({r['event_id'] for r in group})!=len(group):raise ValueError('Duplicate prior policy fixture')
        cohorts.append({r['event_id'] for r in group})
        cal=[r for r in group if r['day']<boundary];selection=[r for r in group if r['day']>=boundary]
        if min(len(cal),len(selection))<30:raise ValueError('Need 30 prior calibration and 30 disjoint selection games')
        t=min(TEMPERATURES,key=lambda t:(metrics([r['y'] for r in cal],calibrated([r['p'] for r in cal],t))['all']['log_loss'],abs(t-1)))
        settings[variant]=t
        validation[variant]=metrics([r['y'] for r in selection],calibrated([r['p'] for r in selection],t))['all']
    if any(c!=cohorts[0] for c in cohorts):raise ValueError('Prior candidate cohorts differ')
    reference=validation['baseline']
    eligible=[v for v in variants if v!='baseline' and validation[v]['accuracy']>=reference['accuracy']+.01 and
              validation[v]['log_loss']<=reference['log_loss']-.005 and validation[v]['brier']<=reference['brier']]
    chosen=min(eligible,key=lambda v:(validation[v]['log_loss'],v)) if eligible else 'baseline'
    return dict(variant=chosen,temperature=settings[chosen],prior_season=season,last_prior_day=max(days),
                calibration_before_day=boundary,prior_games=len(cohorts[0]),validation=validation,temperatures=settings,
                rule='First prior OOS UTC-day half calibrates; second half selects. Require +1 percentage point accuracy, -0.005 log loss and no worse Brier versus calibrated baseline. Otherwise retain baseline. No current/future outcome selection.')
