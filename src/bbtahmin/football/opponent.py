"""Opponent-adjusted Poisson challenger; never silently replaces the baseline."""
import numpy as np
from scipy.optimize import minimize

from .model import GoalModel,metrics,score


class OpponentGoalModel(GoalModel):
    model_name='football-opponent-poisson-v1'

    def __init__(self, history, league, cutoff):
        super().__init__(history,league,cutoff)
        h=self.history
        self.teams=sorted(set(h.home)|set(h.away));self.indices={t:i for i,t in enumerate(self.teams)}
        n=len(self.teams)
        hi=np.array([self.indices[t] for t in h.home]);ai=np.array([self.indices[t] for t in h.away])
        attack=np.concatenate([hi,ai]);defence=np.concatenate([ai,hi])
        venue=np.concatenate([np.ones(len(h)),np.zeros(len(h))])
        y=np.concatenate([h.home_goals.to_numpy(float),h.away_goals.to_numpy(float)])
        w=np.tile(h.weight.to_numpy(float),2)
        # Fixed L2 penalty, no target-season hyperparameter selection.
        def loss(beta):
            eta=beta[0]+venue*beta[1]+beta[2:2+n][attack]+beta[2+n:][defence]
            mu=np.exp(eta);residual=w*(mu-y)
            penalty=np.concatenate([np.array([0.,.1]),np.full(2*n,2.)])
            value=float(np.sum(w*(mu-y*eta))+.5*np.sum(penalty*beta**2))
            gradient=np.concatenate([[residual.sum(),(residual*venue).sum()],
                                     np.bincount(attack,weights=residual,minlength=n),
                                     np.bincount(defence,weights=residual,minlength=n)])+penalty*beta
            return value,gradient
        initial=np.zeros(2+2*n);initial[0]=np.log(self.away_mean);initial[1]=np.log(self.home_mean/self.away_mean)
        fitted=minimize(loss,initial,jac=True,method='L-BFGS-B',
                        bounds=[(-3,3),(-1,1)]+[(-2,2)]*(2*n),options=dict(maxiter=300,ftol=1e-10))
        if not fitted.success or not np.isfinite(fitted.x).all():
            raise ValueError('Opponent model did not converge; no silent fallback')
        self.coefficients=fitted.x;self.fit_iterations=int(fitted.nit)

    def goal_rates(self,home,away):
        n=len(self.teams);b=self.coefficients
        def effects(team):
            i=self.indices.get(team)
            return (0.,0.) if i is None else (b[2+i],b[2+n+i])
        ha,hd=effects(home);aa,ad=effects(away)
        return float(np.clip(np.exp(b[0]+b[1]+ha+ad),.1,6)),float(np.clip(np.exp(b[0]+aa+hd),.1,6))

    def predict(self,home,away):
        p=super().predict(home,away)
        p.update(experimental=True,fit_iterations=self.fit_iterations,
                 note='Experimental jointly fitted opponent-adjusted attack/defence. Fixed L2=2, 180-day half-life, 1095-day window. No target-outcome tuning. Default baseline unchanged.')
        return p


def compare(frame,season='2025-26'):
    """Same available fixtures and monthly cutoffs for both candidates.

    Retrospective comparison only; not an automatic promotion policy.
    """
    output=[];summaries=[]
    target=frame.loc[(frame.status=='final')&(frame.season==season)]
    for league,group in target.groupby('league'):
        results={'baseline':[],'opponent':[]};skipped=[]
        for month,games in group.groupby(group.date.str[:7]):
            try:
                models={'baseline':GoalModel(frame,league,month+'-01'),
                        'opponent':OpponentGoalModel(frame,league,month+'-01')}
            except ValueError as exc:
                skipped.append(dict(month=month,games=len(games),reason=str(exc)));continue
            for g in games.to_dict('records'):
                item=dict(event_id=g['event_id'],league=league,date=g['date'],predictions={},results={})
                for name,model in models.items():
                    p=model.predict(g['home'],g['away']);r=score(p,int(g['home_goals']),int(g['away_goals']))
                    results[name].append(r);item['predictions'][name]=p;item['results'][name]=r
                output.append(item)
        summaries.append(dict(league=league,season=season,baseline=metrics(results['baseline']),opponent=metrics(results['opponent']),skipped=skipped))
    return dict(spec='football-challenger-v1',season=season,summaries=summaries,predictions=output,
                note='Identical monthly-cutoff cohort. Retrospective, partial source coverage. Candidate not promoted using this evaluation. Earliest future forecasts unchanged.')
