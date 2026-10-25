"""Fixed, league-specific recency-weighted Poisson attack/defence baseline.

No in-sample outcome is used by its own prediction. Hyperparameters are fixed;
this is a research baseline, not an asserted accuracy improvement.
"""
import numpy as np
import pandas as pd
from .distributions import poisson

from .data import key


class GoalModel:
    def __init__(self, history, league, cutoff, *, half_life=180., shrinkage=8., window_days=1095):
        if (not np.isfinite([half_life,shrinkage]).all() or half_life<=0 or shrinkage<=0
                or type(window_days) is not int or window_days<1):
            raise ValueError('Positive finite recency, shrinkage and history window required')
        self.settings=dict(half_life_days=float(half_life),shrinkage_games=float(shrinkage),window_days=window_days)
        cutoff=pd.Timestamp(cutoff).normalize().tz_localize(None)
        history=history.loc[(history.league==league)&(history.status=='final')].copy()
        dates=pd.to_datetime(history.date)
        history=history.loc[(dates<cutoff)&(dates>=cutoff-pd.Timedelta(days=window_days))].copy()
        if len(history)<100: raise ValueError('At least 100 earlier league finals required')
        history['weight']=np.exp2(-(cutoff-pd.to_datetime(history.date)).dt.days/half_life)
        self.history, self.league, self.cutoff=history,league,cutoff
        weights=history.weight.to_numpy()
        self.home_mean=float(np.average(history.home_goals.astype(float),weights=weights))
        self.away_mean=float(np.average(history.away_goals.astype(float),weights=weights))
        self.home_mean=max(.1,self.home_mean); self.away_mean=max(.1,self.away_mean)
        self.ratings={}
        for venue, goals, conceded, base_for, base_against in [
                ('home','home_goals','away_goals',self.home_mean,self.away_mean),
                ('away','away_goals','home_goals',self.away_mean,self.home_mean)]:
            for team,g in history.groupby(venue):
                # Eight pseudo-matches shrink sparse/promoted clubs toward the league.
                attack=(float((g[goals]*g.weight).sum())+shrinkage*base_for)/(g.weight.sum()+shrinkage)/base_for
                defence=(float((g[conceded]*g.weight).sum())+shrinkage*base_against)/(g.weight.sum()+shrinkage)/base_against
                self.ratings[venue,team]=(attack,defence)
        self.baseline=history.assign(outcome=np.sign(history.home_goals-history.away_goals)).groupby('outcome').weight.sum()
        self.base_probs=np.array([self.baseline.get(1,0)+1,self.baseline.get(0,0)+1,self.baseline.get(-1,0)+1])
        self.base_probs=self.base_probs/self.base_probs.sum()

    def predict(self, home, away):
        home,away=key(home),key(away)
        if home==away: raise ValueError('Teams must differ')
        ha,hd=self.ratings.get(('home',home),(1.,1.))
        aa,ad=self.ratings.get(('away',away),(1.,1.))
        lh=float(np.clip(self.home_mean*ha*ad,.1,6))
        la=float(np.clip(self.away_mean*aa*hd,.1,6))
        grid=np.outer(poisson.pmf(np.arange(41),lh),poisson.pmf(np.arange(41),la))
        probs=[float(np.tril(grid,-1).sum()),float(np.trace(grid)),float(np.triu(grid,1).sum())]
        goals=lh+la
        counts={t:int(((self.history.home==t)|(self.history.away==t)).sum()) for t in (home,away)}
        recent={t:self.history.loc[(self.history.home==t)|(self.history.away==t),'date'].max() for t in (home,away)}
        issues=[]
        for team,count in counts.items():
            if count<10: issues.append(f'{team}: fewer than 10 prior matches')
            elif (self.cutoff-pd.Timestamp(recent[team])).days>90: issues.append(f'{team}: history older than 90 days')
            if ('home',team) not in self.ratings or ('away',team) not in self.ratings:
                issues.append(f'{team}: missing venue history; league prior used')
        return dict(model='football-poisson-v1',league=self.league,home=home,away=away,
                    expected_home_goals=lh,expected_away_goals=la,
                    probabilities=dict(zip(['home','draw','away'],probs)),
                    predicted_outcome=['home','draw','away'][int(np.argmax(probs))],
                    most_likely_score=list(map(int,np.unravel_index(grid.argmax(),grid.shape))),
                    over={str(t):float(poisson.sf(int(t),goals)) for t in (1.5,2.5,3.5)},
                    both_teams_score=float((1-np.exp(-lh))*(1-np.exp(-la))),
                    total_goals_80=[int(poisson.ppf(.1,goals)),int(poisson.ppf(.9,goals))],
                    training_cutoff_exclusive=self.cutoff.date().isoformat(),training_games=len(self.history),
                    prior_team_games=counts,issues=issues,recommendation_validated=False,
                    settings=self.settings,
                    note='Regulation only. Draw is a separate outcome. Independent Poisson assumptions; no injuries, lineups, xG or odds. Not a calibrated guarantee.')


def metrics(items):
    if not items: return dict(games=0,winner_accuracy=None,log_loss=None,brier=None,total_mae=None,margin_mae=None,total_in_80=None,home_score_mae=None,away_score_mae=None,team_score_mae=None,team_score_games=0)
    result=dict(games=len(items),winner_accuracy=float(np.mean([x['winner_correct'] for x in items])),
                log_loss=float(np.mean([x['log_loss'] for x in items])),brier=float(np.mean([x['brier'] for x in items])),
                total_mae=float(np.mean([x['total_absolute_error'] for x in items])),
                margin_mae=float(np.mean([x['margin_absolute_error'] for x in items])),
                total_in_80=float(np.mean([x['total_in_80'] for x in items])))
    scored=[x for x in items if 'home_absolute_error' in x and 'away_absolute_error' in x]
    result.update(team_score_games=len(scored),
                  home_score_mae=float(np.mean([x['home_absolute_error'] for x in scored])) if scored else None,
                  away_score_mae=float(np.mean([x['away_absolute_error'] for x in scored])) if scored else None,
                  team_score_mae=float(np.mean([(x['home_absolute_error']+x['away_absolute_error'])/2 for x in scored])) if scored else None)
    result['goal_markets']={market:dict(accuracy=float(np.mean([x['goal_markets'][market]['correct'] for x in items])),
        brier=float(np.mean([x['goal_markets'][market]['brier'] for x in items])))
        for market in ('over_1.5','over_2.5','over_3.5','both_teams_score')}
    return result


def score(prediction, home, away):
    outcome='home' if home>away else 'away' if home<away else 'draw'
    probs=prediction['probabilities']; values=np.array([probs[k] for k in ('home','draw','away')])
    target=np.array([k==outcome for k in ('home','draw','away')],dtype=float)
    ph,pa=prediction['expected_home_goals'],prediction['expected_away_goals']
    markets={}
    for line in (1.5,2.5,3.5):
        probability=prediction['over'][str(line)];actual=home+away>line
        markets['over_'+str(line)]=dict(actual=actual,correct=(probability>=.5)==actual,brier=(probability-float(actual))**2)
    probability=prediction['both_teams_score'];actual=home>0 and away>0
    markets['both_teams_score']=dict(actual=actual,correct=(probability>=.5)==actual,brier=(probability-float(actual))**2)
    return dict(actual_home=home,actual_away=away,actual_outcome=outcome,goal_markets=markets,
                winner_correct=prediction['predicted_outcome']==outcome,
                home_absolute_error=abs(ph-home),away_absolute_error=abs(pa-away),
                total_absolute_error=abs(ph+pa-home-away),margin_absolute_error=abs((ph-pa)-(home-away)),
                total_in_80=prediction['total_goals_80'][0]<=home+away<=prediction['total_goals_80'][1],
                log_loss=float(-np.log(max(probs[outcome],1e-15))),brier=float(np.sum((values-target)**2)))


def evaluate(frame, season=None):
    """Monthly expanding holdout; all training precedes the evaluation month.

    Compare model and fixed league-frequency baseline on identical matches.
    Publication history is unknown: retrospective, never prospective evidence.
    """
    now=pd.Timestamp.now(tz='UTC'); active=now.year if now.month>=7 else now.year-1
    season=season or f'{active-1}-{str(active)[-2:]}'
    output=[]; summaries=[]
    for league,group in frame.loc[(frame.status=='final')&(frame.season==season)].groupby('league'):
        cohort=[]; baseline=[]; skipped=[]
        for month, games in group.groupby(group.date.str[:7]):
            try: model=GoalModel(frame,league,month+'-01')
            except ValueError as exc:
                skipped.append(dict(month=month,games=len(games),reason=str(exc))); continue
            for g in games.to_dict('records'):
                p=model.predict(g['home'],g['away']); result=score(p,int(g['home_goals']),int(g['away_goals']))
                cohort.append(result)
                b=dict(p,probabilities=dict(zip(('home','draw','away'),map(float,model.base_probs))),
                       predicted_outcome=['home','draw','away'][int(model.base_probs.argmax())])
                baseline.append(score(b,int(g['home_goals']),int(g['away_goals'])))
                output.append(dict(event_id=g['event_id'],league=league,date=g['date'],season=season,
                                   home=g['home_name'],away=g['away_name'],prediction=p,result=result))
        summaries.append(dict(league=league,season=season,model=metrics(cohort),league_frequency_baseline={k:v for k,v in metrics(baseline).items() if k in ('games','winner_accuracy','log_loss','brier')},skipped=skipped,coverage='Available publisher finals only; season completeness not certified'))
    return dict(spec='football-retrospective-v1',season=season,summaries=summaries,predictions=output,
                note='Retrospective monthly holdout; unknown historical publication times. No tuning on target outcomes. Not prospective accuracy. Fixed 180-day half-life, 1095-day window and 8-game shrinkage. No general accuracy improvement established.')

