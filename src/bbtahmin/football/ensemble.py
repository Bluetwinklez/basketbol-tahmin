"""Fixed equal-weight joint-score ensemble; experimental, no target tuning."""
import numpy as np

from .distributions import poisson


def grid(prediction):
    h=prediction['expected_home_goals'];a=prediction['expected_away_goals']
    result=np.outer(poisson.pmf(np.arange(41),h),poisson.pmf(np.arange(41),a))
    rho=prediction.get('low_score_rho',0.)
    result[:2,:2]*=np.array([[1-h*a*rho,1+h*rho],[1+a*rho,1-rho]])
    if not np.isfinite(result).all() or result.min()<0 or result.sum()<=0:
        raise ValueError('Invalid candidate joint score distribution')
    return result/result.sum()


def combine(baseline,opponent):
    for field in ('league','home','away','training_cutoff_exclusive'):
        if baseline[field]!=opponent[field]:raise ValueError('Candidate identity/cutoff mismatch')
    joint=.5*grid(baseline)+.5*grid(opponent)
    h,a=np.indices(joint.shape);totals=h+a
    mass=np.bincount(totals.ravel(),weights=joint.ravel());cdf=mass.cumsum()
    probs=[float(np.tril(joint,-1).sum()),float(np.trace(joint)),float(np.triu(joint,1).sum())]
    result=dict(baseline)
    result.update(model='football-joint-ensemble-v1',research_candidate=True,
        expected_home_goals=float((h*joint).sum()),expected_away_goals=float((a*joint).sum()),
        probabilities=dict(zip(('home','draw','away'),probs)),
        predicted_outcome=('home','draw','away')[int(np.argmax(probs))],
        most_likely_score=list(map(int,np.unravel_index(joint.argmax(),joint.shape))),
        over={str(line):float(joint[totals>line].sum()) for line in (1.5,2.5,3.5)},
        both_teams_score=float(joint[1:,1:].sum()),
        total_goals_80=[int(np.searchsorted(cdf,.1)),int(np.searchsorted(cdf,.9))],
        ensemble_weights={'baseline':.5,'opponent_dc':.5},
        note='Fixed equal-weight joint-score mixture. All markets use the same distribution. Experimental; no automatic promotion, target tuning or guaranteed success.')
    return result


class EnsembleGoalModel:
    def __init__(self,history,league,cutoff):
        from .model import GoalModel
        from .challenger import OpponentGoalModel
        self.baseline=GoalModel(history,league,cutoff)
        self.opponent=OpponentGoalModel(history,league,cutoff,low_score=True)

    def predict(self,home,away):
        return combine(self.baseline.predict(home,away),self.opponent.predict(home,away))
