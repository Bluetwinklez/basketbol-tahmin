"""Observable fixture gaps and history ages, independent of win probability.

An overdue scheduled row is unresolved, not proof the match was played. These
conservative diagnostics never certify calendar completeness or model accuracy.
"""
import pandas as pd

from ..quality import timestamp


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


def held_fixture_reviews(reviews):
    """Index both archive IDs for fixtures held for a scheduling review."""
    from .data import row

    result = {}
    for event_id, review in reviews.items():
        status = review.get("status")
        if status == "interrupted_pending_review":
            resume = timestamp(review["resume_at_utc"])
            notice_url = review["interruption_source_url"]
        elif status == "postponed_pending_review":
            resume = timestamp(review["rescheduled_start_utc"])
            notice_url = review["postponement_source_url"]
            if not review["reschedule_source_url"].startswith("https://"):
                raise ValueError("Club or league rescheduling evidence required")
        else:
            continue
        checked = timestamp(review["checked_at_utc"])
        resume_day = resume.strftime("%Y-%m-%d")
        if not (review["original_date"] < resume_day and pd.Timestamp(review["original_date"], tz="UTC") <= checked < resume):
            raise ValueError("Fixture review must precede the new start and follow the original date")
        if not review["source_url"].startswith("https://") or not notice_url.startswith("https://"):
            raise ValueError("Fixture hold requires a postponement or interruption notice and new start evidence")
        for day in (review["original_date"], resume_day):
            alias = row(review["league"], review["season"], day, review["home"], review["away"],
                        None, review["source_url"], checked.isoformat())["event_id"]
            if (day == review["original_date"] and alias != event_id) or alias in result:
                raise ValueError("Invalid or ambiguous held fixture identity")
            result[alias] = dict(review, reviewed_start_utc=resume.isoformat())
    return result


def defer_held_history(frame, held_fixtures, now):
    clock = timestamp(now)
    pending = {
        identity for identity, review in held_fixtures.items()
        if timestamp(review["checked_at_utc"]) <= clock < timestamp(review["reviewed_start_utc"])
    }
    return frame.loc[~(frame["event_id"].isin(pending) & frame["status"].ne("final"))]
