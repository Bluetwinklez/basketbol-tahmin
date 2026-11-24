"""Compare refresh failures without treating unobserved sources as recovered."""
import json
import re
from datetime import date, datetime, timedelta, timezone


MATCH_FIELDS = {'collector', 'source', 'league', 'stage'}
OBSERVED = ('partial', 'succeeded')


def load_known_missing(path):
    entries = json.loads(path.read_text(encoding='utf8'))
    if not isinstance(entries, list):
        raise ValueError('known_missing must be a list')
    allowed = MATCH_FIELDS | {'sport', 'reason', 'review_by'}
    for index, entry in enumerate(entries, 1):
        if (not isinstance(entry, dict) or entry.keys() - allowed
                or not {'sport', 'reason', 'review_by'} <= entry.keys()
                or not {'collector', 'source', 'league'} & entry.keys()
                or any(not isinstance(value, str) or not value.strip() for value in entry.values())
                or entry['sport'] not in ('football', 'basketball')):
            raise ValueError(f'Invalid known_missing entry {index}')
        try:
            if date.fromisoformat(entry['review_by']).isoformat() != entry['review_by']:
                raise ValueError
        except ValueError as exc:
            raise ValueError(f'Invalid review_by in known_missing entry {index}') from exc
    return entries


def classify_errors(sport, errors, entries):
    known, unexpected = [], []
    for error in errors:
        matched = any(entry['sport'] == sport and all(error.get(key) == entry[key]
                      for key in MATCH_FIELDS & entry.keys()) for entry in entries)
        (known if matched else unexpected).append(error)
    return dict(known_missing=known, unexpected=unexpected)


def refresh_exit_code(results, entries, today):
    return int(any(report['status'] == 'failed' or report['unexpected'] for report in results.values())
               or any(date.fromisoformat(entry['review_by']) < today for entry in entries))


def saved_reports(directory):
    for path in sorted(directory.glob('*.json'), reverse=True):
        if re.fullmatch(r'[0-9]{8}T[0-9]{6}Z', path.stem):
            observed_at = datetime.strptime(path.stem, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
            yield observed_at, json.loads(path.read_text(encoding='utf8'))


def auto_disabled(reports, sport, league, now, *, threshold, retry_days):
    """Use consecutive observed attempts, newest first. Skips leave the retry clock alone."""
    failures, last_failure = 0, None
    for observed_at, report in reports:
        source = report.get(sport, {})
        if source.get('status') not in OBSERVED or any(
                skip['league'] == league for skip in source.get('skipped_auto_disabled', [])):
            continue
        if not any(error.get('league') == league for error in source.get('errors', [])):
            break
        if last_failure is None:
            last_failure = observed_at
            if now - last_failure >= timedelta(days=retry_days):
                return None
        failures += 1
    if failures >= threshold:
        return dict(league=league, failure_count=failures, last_failure=last_failure.date().isoformat())
    return None

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
        observed = new.get('status') in OBSERVED
        comparable = old.get('status') in OBSERVED
        skipped = {item['league'] for item in new.get('skipped_auto_disabled', [])}
        gone = sorted(before.keys()-after.keys())
        result[sport] = dict(
            status=new.get('status', 'not_observed'),
            new_failures=[after[k] for k in sorted(after.keys()-before.keys())] if comparable else [],
            continuing_failures=[after[k] for k in sorted(after.keys() & before.keys())],
            no_longer_reported=[before[k] for k in gone if observed and before[k].get('league') not in skipped],
            unresolved_unobserved=[before[k] for k in gone if not observed or before[k].get('league') in skipped],
            baseline_failures=list(after.values()) if not comparable else [],
            comparison_available=observed and comparable)
    return dict(sports=result, note='Failure transitions only, not proof of complete data, source freshness or official result verification. A missing sport or failed whole-sport refresh cannot clear previous failures.')
