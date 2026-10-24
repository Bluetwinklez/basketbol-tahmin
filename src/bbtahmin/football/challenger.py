"""Opponent-adjusted, pooled-venue Poisson and training-only low-score research.

Candidates are explicit opt-ins. Evaluation never promotes a model using its
target season. Historical publication availability remains unknown.
"""
import numpy as np
import pandas as pd

from .data import key
from .distributions import poisson
from .model import GoalModel, metrics, score

VARIANTS = ('baseline', 'opponent', 'opponent_dc', 'ensemble')


class OpponentGoalModel(GoalModel):
    def __init__(self, history, league, cutoff, low_score=True):
        super().__init__(history, league, cutoff)
        self.low_score = low_score
        h = self.history
        self.teams = sorted(set(h.home) | set(h.away))
        lookup = {team: i for i, team in enumerate(self.teams)}
        hi = np.array([lookup[t] for t in h.home]); ai = np.array([lookup[t] for t in h.away])
        hg = h.home_goals.to_numpy(float); ag = h.away_goals.to_numpy(float)
        w = h.weight.to_numpy(float); n = len(lookup)
        attack = np.ones(n); defence = np.ones(n)
        # Simultaneous damped updates; pseudo-observations regularize around 1.
        scored = np.bincount(hi, w*hg, minlength=n)+np.bincount(ai, w*ag, minlength=n)
        conceded = np.bincount(hi, w*ag, minlength=n)+np.bincount(ai, w*hg, minlength=n)
        prior = 8*(self.home_mean+self.away_mean)/2
        for _ in range(80):
            ae = (np.bincount(hi, w*self.home_mean*defence[ai], minlength=n)
                  + np.bincount(ai, w*self.away_mean*defence[hi], minlength=n))
            attack = .5*attack + .5*np.clip((scored+prior)/(ae+prior), .2, 5)
            de = (np.bincount(hi, w*self.away_mean*attack[ai], minlength=n)
                  + np.bincount(ai, w*self.home_mean*attack[hi], minlength=n))
            defence = .5*defence + .5*np.clip((conceded+prior)/(de+prior), .2, 5)
        self.strengths = {team: (float(attack[i]), float(defence[i])) for team, i in lookup.items()}
        lh = np.clip(self.home_mean*attack[hi]*defence[ai], .1, 6)
        la = np.clip(self.away_mean*attack[ai]*defence[hi], .1, 6)
        self.rho = 0.
        if low_score:
            # Only earlier training results estimate rho. Shrink toward independence.
            best = -np.inf
            for rho in np.linspace(-.15, .15, 61):
                factors = np.ones(len(h))
                factors[(hg == 0) & (ag == 0)] = (1-lh*la*rho)[(hg == 0) & (ag == 0)]
                factors[(hg == 0) & (ag == 1)] = (1+lh*rho)[(hg == 0) & (ag == 1)]
                factors[(hg == 1) & (ag == 0)] = (1+la*rho)[(hg == 1) & (ag == 0)]
                factors[(hg == 1) & (ag == 1)] = 1-rho
                if factors.min() <= 0:
                    continue
                objective = float(np.dot(w, np.log(factors))-20*rho*rho)
                if objective > best:
                    best, self.rho = objective, float(rho)

    def predict(self, home, away):
        result = super().predict(home, away)
        home, away = key(home), key(away)
        ha, hd = self.strengths.get(home, (1., 1.))
        aa, ad = self.strengths.get(away, (1., 1.))
        lh = float(np.clip(self.home_mean*ha*ad, .1, 6))
        la = float(np.clip(self.away_mean*aa*hd, .1, 6))
        grid = np.outer(poisson.pmf(np.arange(41), lh), poisson.pmf(np.arange(41), la))
        rho = self.rho
        factors = np.array([[1-lh*la*rho, 1+lh*rho], [1+la*rho, 1-rho]])
        # Bound rho at prediction time too: unseen pairings may have larger means.
        while factors.min() <= 0:
            rho *= .5
            factors = np.array([[1-lh*la*rho, 1+lh*rho], [1+la*rho, 1-rho]])
        grid[:2, :2] *= factors
        grid /= grid.sum()
        totals = np.indices(grid.shape).sum(axis=0)
        mass = np.bincount(totals.ravel(), weights=grid.ravel())
        cdf = mass.cumsum()
        probs = [float(np.tril(grid, -1).sum()), float(np.trace(grid)), float(np.triu(grid, 1).sum())]
        result.update(model='football-opponent-dc-v1' if self.low_score else 'football-opponent-v1',
                      expected_home_goals=lh, expected_away_goals=la,
                      probabilities=dict(zip(('home','draw','away'), probs)),
                      predicted_outcome=('home','draw','away')[int(np.argmax(probs))],
                      most_likely_score=list(map(int, np.unravel_index(grid.argmax(), grid.shape))),
                      over={str(line): float(grid[totals > line].sum()) for line in (1.5, 2.5, 3.5)},
                      both_teams_score=float(grid[1:, 1:].sum()),
                      total_goals_80=[int(np.searchsorted(cdf, .1)), int(np.searchsorted(cdf, .9))],
                      low_score_rho=rho, research_candidate=True,
                      note='Regulation only. Opponent-adjusted pooled venue strengths; low-score correction fitted on earlier results. Explicit research candidate, no automatic promotion or lineup/xG/odds inputs.')
        return result


def fit(history, league, cutoff, variant='baseline'):
    if variant not in VARIANTS:
        raise ValueError('Unknown football model candidate')
    if variant=='ensemble':
        from .ensemble import EnsembleGoalModel
        return EnsembleGoalModel(history,league,cutoff)
    return (GoalModel(history, league, cutoff) if variant == 'baseline' else
            OpponentGoalModel(history, league, cutoff, low_score=variant == 'opponent_dc'))


def compare(frame, season):
    """Monthly same-cohort evaluation, including baseline goal-market metrics."""
    summaries, predictions = [], []
    target = frame.loc[(frame.status == 'final') & (frame.season == season)].sort_values(['date','event_id'])
    for league, group in target.groupby('league'):
        cohorts = {v: [] for v in VARIANTS}; skipped = []
        for month, games in group.groupby(group.date.str[:7]):
            try:
                models = {v: fit(frame, league, month+'-01', v) for v in VARIANTS}
            except ValueError as exc:
                skipped.append(dict(month=month, games=len(games), reason=str(exc)))
                continue
            for game in games.to_dict('records'):
                for variant, model in models.items():
                    prediction = model.predict(game['home'], game['away'])
                    result = score(prediction, int(game['home_goals']), int(game['away_goals']))
                    cohorts[variant].append(result)
                    predictions.append(dict(event_id=game['event_id'], league=league, date=game['date'],
                                            variant=variant, prediction=prediction, result=result))
        summaries.append(dict(league=league, candidates={v: metrics(rows) for v,rows in cohorts.items()}, skipped=skipped))
    return dict(spec='football-candidate-comparison-v1', season=season, summaries=summaries,
                predictions=predictions, default_changed=False,
                note='Identical monthly cohorts. Earlier dates only; historical publication times unknown. Exploratory historical comparison, not prospective success. No automatic model promotion.')
