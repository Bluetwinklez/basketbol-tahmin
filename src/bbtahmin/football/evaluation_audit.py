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
