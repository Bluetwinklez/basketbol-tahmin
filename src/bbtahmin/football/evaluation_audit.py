"""Validate paired candidate cohorts before reporting simple comparators."""


def simple_baselines(rows, variants, target_ids):
    variants = tuple(variants)
    if not variants or len(set(variants)) != len(variants):
        raise ValueError('Expected distinct candidate names')
    targets = list(target_ids)
    if len(set(targets)) != len(targets):
        raise ValueError('Duplicate target identity')
    cohorts = {v: {} for v in variants}
    for row in rows:
        variant, event = row['variant'], row['event_id']
        if variant not in cohorts or event not in targets:
            raise ValueError('Unexpected candidate or target identity')
        if event in cohorts[variant]:
            raise ValueError('Duplicate candidate event')
        result = row['result']
        cohorts[variant][event] = (result['actual_home'], result['actual_away'])
    reference = cohorts[variants[0]]
    if any(cohort != reference for cohort in cohorts.values()):
        raise ValueError('Candidate cohorts or observed scores differ')
    n = len(reference)
    scores = list(reference.values())
    return dict(games=n, eligible_targets=len(targets), skipped_targets=len(targets)-n,
                coverage=n/len(targets) if targets else None,
                event_ids=sorted(reference),
                always_home_accuracy=sum(h>a for h,a in scores)/n if n else None,
                always_under_2_5_accuracy=sum(h+a<2.5 for h,a in scores)/n if n else None,
                always_btts_no_accuracy=sum(h==0 or a==0 for h,a in scores)/n if n else None,
                note='Identical evaluated events for every candidate and comparator; archive coverage is not season completeness.')


def paired_accuracy(rows, variants, target_ids):
    """Count paired gains/losses against fixed comparators, without refitting."""
    import math
    rows = list(rows)
    variants = tuple(variants)
    cohort = simple_baselines(rows, variants, target_ids)
    counts = {v: {m: dict(both_correct=0, candidate_only=0, comparator_only=0,
                         both_wrong=0) for m in ('winner', 'over_2_5', 'btts')}
              for v in variants}
    for row in rows:
        h, a = row['result']['actual_home'], row['result']['actual_away']
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or
               not math.isfinite(x) or x < 0 or x > 30 or x != int(x) for x in (h, a)):
            raise ValueError('Invalid observed regulation goals')
        p = row['prediction']
        winner = p['predicted_outcome']
        if winner not in ('home', 'draw', 'away'):
            raise ValueError('Invalid predicted outcome')
        over, btts = p['over']['2.5'], p['both_teams_score']
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or
               not math.isfinite(x) or not 0 <= x <= 1 for x in (over, btts)):
            raise ValueError('Invalid market probability')
        actual = 'home' if h > a else 'away' if a > h else 'draw'
        decisions = {'winner': (winner == actual, actual == 'home'),
                     'over_2_5': ((over >= .5) == (h+a > 2.5), h+a < 2.5),
                     'btts': ((btts >= .5) == (min(h,a) > 0), min(h,a) == 0)}
        for market, (candidate, comparator) in decisions.items():
            bucket = ('both_correct' if comparator else 'candidate_only') if candidate else (
                'comparator_only' if comparator else 'both_wrong')
            counts[row['variant']][market][bucket] += 1
    n = cohort['games']
    for markets in counts.values():
        for result in markets.values():
            result['games'] = n
            result['candidate_accuracy'] = (result['both_correct']+result['candidate_only'])/n if n else None
            result['comparator_accuracy'] = (result['both_correct']+result['comparator_only'])/n if n else None
            result['accuracy_delta'] = (result['candidate_only']-result['comparator_only'])/n if n else None
    return dict(cohort=cohort, comparisons=counts,
                comparators=dict(winner='always_home', over_2_5='always_under_2_5', btts='always_btts_no'),
                note='Fixed 0.5 binary threshold (ties select yes). Paired descriptive counts, not significance or prospective success. No threshold tuning or model selection.')
