"""Observable fixture gaps and history ages, independent of win probability.

An overdue scheduled row is unresolved, not proof the match was played. These
conservative diagnostics never certify calendar completeness or model accuracy.
"""
import pandas as pd


def assess(frame, fixture, now, max_age_days=30):
    clock = pd.Timestamp(now)
    if clock.tzinfo is None or pd.isna(clock):
        raise ValueError('History health clock requires a timezone')
    if type(max_age_days) is not int or max_age_days < 1:
        raise ValueError('Positive integer history age required')
    today = clock.tz_convert('UTC').strftime('%Y-%m-%d')
    cutoff = min(today, fixture['date'])
    league = frame.loc[(frame.league == fixture['league']) & (frame.date < cutoff)]
    issues, teams = [], {}
    for team in (fixture['home'], fixture['away']):
        observed = league.loc[(league.home == team) | (league.away == team)]
        finals = observed.loc[observed.status == 'final']
        last = None if finals.empty else finals.date.max()
        age = None if last is None else (pd.Timestamp(cutoff)-pd.Timestamp(last)).days
        # Ignore only yesterday: day-only source reporting can lag one day.
        overdue = observed.loc[(observed.season == fixture['season']) & (observed.status != 'final') &
                               (observed.date < (pd.Timestamp(cutoff)-pd.Timedelta(days=1)).strftime('%Y-%m-%d'))]
        current = finals.loc[finals.season == fixture['season']] if 'season' in finals else finals.iloc[:0]
        teams[team] = dict(prior_finals=len(finals), active_season_finals=len(current),
                           last_final_date=last, days_since_last_final=age,
                           unresolved_past_fixture_ids=sorted(overdue.event_id.tolist()))
        if last is None:
            issues.append(f'{team}: no prior completed history')
        elif age > max_age_days:
            issues.append(f'{team}: latest completed history is {age} days old')
        if not overdue.empty:
            issues.append(f'{team}: {len(overdue)} unresolved past fixtures; refresh/review required')
    return dict(spec='football-history-health-v1', checked_at_utc=clock.isoformat(),
                information_cutoff_exclusive=cutoff, teams=teams,
                diagnostic_gate_passed=not issues, blocking_issues=issues,
                max_history_age_days=max_age_days, calendar_completeness_verified=False,
                note='Diagnostic policy, not a validated success threshold. Unresolved fixtures may be postponed or missing results. Fresh source captures do not make old histories current.')


def inventory(frame, now):
    """One league report plus team-specific observed schedule discrepancies."""
    clock = pd.Timestamp(now)
    if clock.tzinfo is None or pd.isna(clock):
        raise ValueError('History inventory clock requires a timezone')
    day = clock.tz_convert('UTC').strftime('%Y-%m-%d')
    rows = []
    for code, group in frame.groupby('league'):
        past = group.loc[group.date < day]
        finals = past.loc[past.status == 'final']
        unresolved = past.loc[(past.status != 'final') &
                              (past.date < (pd.Timestamp(day)-pd.Timedelta(days=1)).strftime('%Y-%m-%d'))]
        rows.append(dict(league=code, last_final_date=None if finals.empty else finals.date.max(),
                         unresolved_past_fixtures=len(unresolved),
                         unresolved_fixture_ids=sorted(unresolved.event_id.tolist()),
                         completeness_verified=False))
    return dict(checked_at_utc=clock.isoformat(), leagues=rows,
                note='Observed source rows only; absent fixtures cannot be discovered from this archive alone.')
