"""Auditable last-50 available league finals; never assert complete all-match history."""
import pandas as pd
from .data import key


def last_matches(frame, league, team, cutoff, limit=50):
    if not 1 <= limit <= 100: raise ValueError('Limit must be between 1 and 100')
    team=key(team); cutoff=pd.Timestamp(cutoff).strftime('%Y-%m-%d')
    games=frame.loc[(frame.league==league)&(frame.status=='final')&(frame.date<cutoff)&((frame.home==team)|(frame.away==team))].sort_values(['date','event_id'],ascending=False).head(limit)
    rows=games.to_dict('records'); goals_for=[]; goals_against=[]
    for r in rows:
        home=r['home']==team;goals_for.append(int(r['home_goals'] if home else r['away_goals']));goals_against.append(int(r['away_goals'] if home else r['home_goals']))
    return dict(league=league,team=team,cutoff_exclusive=cutoff,requested=limit,available=len(rows),missing=max(0,limit-len(rows)),last_date=rows[0]['date'] if rows else None,goals_for=sum(goals_for),goals_against=sum(goals_against),wins=sum(a>b for a,b in zip(goals_for,goals_against)),draws=sum(a==b for a,b in zip(goals_for,goals_against)),losses=sum(a<b for a,b in zip(goals_for,goals_against)),matches=rows,note='Last available league finals, not verified complete last matches across all competitions. Archive gaps and club aliases may reduce coverage.')
