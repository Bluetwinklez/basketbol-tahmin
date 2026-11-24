"""Compare refresh failures without treating unobserved sources as recovered."""

def transitions(previous, current):
    def failures(report):
        found = {}
        for error in report.get('errors', []):
            identity = tuple(str(error.get(k, '')) for k in
                             ('collector', 'source', 'league', 'season', 'stage', 'repository'))
            if identity in found:
                raise ValueError('Duplicate refresh failure identity')
            found[identity] = error
        return found
    result = {}
    for sport in sorted(set(previous) | set(current)):
        old, new = previous.get(sport, {}), current.get(sport, {})
        before, after = failures(old), failures(new)
        observed = new.get('status') in ('partial', 'succeeded')
        comparable = old.get('status') in ('partial', 'succeeded')
        result[sport] = dict(
            status=new.get('status', 'not_observed'),
            new_failures=[after[k] for k in sorted(after.keys()-before.keys())] if comparable else [],
            continuing_failures=[after[k] for k in sorted(after.keys() & before.keys())],
            no_longer_reported=[before[k] for k in sorted(before.keys()-after.keys())] if observed else [],
            unresolved_unobserved=[before[k] for k in sorted(before.keys()-after.keys())] if not observed else [],
            baseline_failures=list(after.values()) if not comparable else [],
            comparison_available=observed and comparable)
    return dict(sports=result, note='Failure transitions only, not proof of complete data, source freshness or official result verification. A missing sport or failed whole-sport refresh cannot clear previous failures.')
