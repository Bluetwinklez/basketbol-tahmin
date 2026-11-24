import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from bbtahmin import daily
from bbtahmin.refresh_health import auto_disabled, saved_reports, transitions
from scripts import refresh_sports


PBA = 'PBA_GOV'
FAILURE = dict(league=PBA, status='failed', error='HTTP 503')
FAILED = dict(basketball=dict(status='partial', errors=[FAILURE]))
SUCCEEDED = dict(basketball=dict(status='succeeded', errors=[]))
LAST_FAILURE = datetime(2026, 11, 23, 14, tzinfo=timezone.utc)


def save(directory, when, report):
    (directory / when.strftime('%Y%m%dT%H%M%SZ.json')).write_text(json.dumps(report), encoding='utf8')


def seed(directory, last_failure=LAST_FAILURE):
    for days in (2, 0, 1):
        save(directory, last_failure - timedelta(days=days), FAILED)


def decision(directory, now):
    return auto_disabled(saved_reports(directory), 'basketball', PBA, now, threshold=3, retry_days=7)


def test_pba_disables_after_three_consecutive_observed_failures(tmp_path):
    seed(tmp_path)
    save(tmp_path, LAST_FAILURE + timedelta(hours=1), dict(football=dict(status='succeeded')))
    save(tmp_path, LAST_FAILURE + timedelta(hours=2), dict(basketball=dict(status='failed')))
    assert decision(tmp_path, LAST_FAILURE + timedelta(days=1)) == dict(
        league=PBA, failure_count=3, last_failure='2026-11-23')
    save(tmp_path, LAST_FAILURE - timedelta(hours=12), SUCCEEDED)
    assert decision(tmp_path, LAST_FAILURE + timedelta(days=1)) is None


def test_pba_retry_waits_seven_days_since_last_attempt(tmp_path):
    seed(tmp_path)
    skipped = decision(tmp_path, LAST_FAILURE + timedelta(days=1))
    save(tmp_path, LAST_FAILURE + timedelta(days=6), dict(
        basketball=dict(status='succeeded', errors=[], skipped_auto_disabled=[skipped])))
    retry = LAST_FAILURE + timedelta(days=7)
    assert decision(tmp_path, retry - timedelta(seconds=1)) == skipped
    assert decision(tmp_path, retry) is None
    save(tmp_path, retry, FAILED)
    assert decision(tmp_path, retry + timedelta(days=1)) == dict(
        league=PBA, failure_count=4, last_failure='2026-11-30')


def test_successful_pba_retry_resets_the_streak(tmp_path):
    seed(tmp_path)
    retry = LAST_FAILURE + timedelta(days=7)
    assert decision(tmp_path, retry) is None
    save(tmp_path, retry, SUCCEEDED)
    assert decision(tmp_path, retry + timedelta(hours=1)) is None
    save(tmp_path, retry + timedelta(days=1), FAILED)
    assert decision(tmp_path, retry + timedelta(days=2)) is None


def test_refresh_skips_pba_collector_and_preserves_unobserved_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    directory = tmp_path / 'data' / 'refresh'
    directory.mkdir(parents=True)
    (directory / 'known_missing.json').write_text('[]', encoding='utf8')
    last_failure = datetime.now(timezone.utc) - timedelta(days=1)
    seed(directory, last_failure)
    calls = []
    monkeypatch.setattr(daily, 'refresh', lambda leagues: calls.append(leagues) or {})
    monkeypatch.setattr(daily, 'source_facts', lambda code: ([], []))
    assert refresh_sports.refresh(SimpleNamespace(sport='basketball', backfill=False)) == 0
    assert calls == [[code for code in daily.LEAGUES if code != PBA]]
    _, report = next(saved_reports(directory))
    assert report['basketball'] == dict(status='succeeded', errors=[], known_missing=[], unexpected=[],
        skipped_auto_disabled=[dict(league=PBA, failure_count=3, last_failure=last_failure.date().isoformat())])
    change = transitions(FAILED, report)['sports']['basketball']
    assert change['no_longer_reported'] == []
    assert change['unresolved_unobserved'] == [FAILURE]
