"""Auditable last-50 available league finals; never assert complete all-match history."""
import pandas as pd
from .data import key


def league_coverage(frame, now=None):
    """Separate missing/stale active seasons from the existence of history."""
    from .data import LEAGUES
    clock = pd.Timestamp(now or pd.Timestamp.now(tz='UTC'))
    if clock.tzinfo is None:
        raise ValueError('Coverage clock requires a timezone')
    today = clock.tz_convert('UTC').normalize().tz_localize(None)
    names = dict(LEAGUES, CO2='Colombian Primera B', USLC='USL Championship', USL1='USL League One')
    calendar = {'AR1','AR2','BR1','BR2','CO1','CO2','US1','USLC','USL1','JP1','CN1',
                'UY1','VE1','SV1','HN1','BO1'}
    start = today.year if today.month >= 7 else today.year-1
    rows = []
    for code, name in names.items():
        season = str(today.year) if code in calendar else f'{start}-{str(start+1)[-2:]}'
        finals = frame.loc[(frame.league == code) & (frame.status == 'final') &
                           (frame.date < today.strftime('%Y-%m-%d'))] if not frame.empty else frame
        current = finals.loc[finals.season == season] if not finals.empty else finals
        last = finals.date.max() if not finals.empty else None
        age = int((today-pd.Timestamp(current.date.max())).days) if not current.empty else None
        status = ('missing_archive' if finals.empty else 'missing_active_season' if current.empty else
                  'stale_active_history' if age > 90 else 'partial_active_history')
        rows.append(dict(league=code, name=name, expected_active_season=season,
                         historical_finals=len(finals), active_season_finals=len(current),
                         last_completed_date=last, active_history_age_days=age, status=status,
                         complete_season_verified=False, prediction_ready=False,
                         note='Archive coverage only. Verified fixture, club identities and sufficient current team histories remain required.'))
    return dict(checked_at_utc=clock.isoformat(), leagues=rows,
                note='A fresh capture does not make old match history current. No league is certified prediction-ready by archive counts alone.')


def last_matches(frame, league, team, cutoff, limit=50):
    if not 1 <= limit <= 100: raise ValueError('Limit must be between 1 and 100')
    team=key(team); cutoff=pd.Timestamp(cutoff).strftime('%Y-%m-%d')
    games=frame.loc[(frame.league==league)&(frame.status=='final')&(frame.date<cutoff)&((frame.home==team)|(frame.away==team))].sort_values(['date','event_id'],ascending=False).head(limit)
    rows=games.to_dict('records'); goals_for=[]; goals_against=[]
    for r in rows:
        home=r['home']==team;goals_for.append(int(r['home_goals'] if home else r['away_goals']));goals_against.append(int(r['away_goals'] if home else r['home_goals']))
    return dict(league=league,team=team,cutoff_exclusive=cutoff,requested=limit,available=len(rows),missing=max(0,limit-len(rows)),last_date=rows[0]['date'] if rows else None,goals_for=sum(goals_for),goals_against=sum(goals_against),wins=sum(a>b for a,b in zip(goals_for,goals_against)),draws=sum(a==b for a,b in zip(goals_for,goals_against)),losses=sum(a<b for a,b in zip(goals_for,goals_against)),matches=rows,note='Last available league finals, not verified complete last matches across all competitions. Archive gaps and club aliases may reduce coverage.')
