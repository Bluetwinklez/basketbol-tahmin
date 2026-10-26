"""Network reuse must not turn failed or stale checkouts into fresh evidence."""
import subprocess
import sys
from pathlib import Path

import pytest

from bbtahmin.football import data


def test_shared_sources_update_once_per_run_and_again_next_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        if command[1] == 'clone':
            Path(command[-1]).mkdir(parents=True)
    monkeypatch.setattr(data.subprocess, 'run', run)
    for expected in (3, 6):
        with data.source_refresh_session():
            # European collection followed by seven calendar collectors.
            data.git_source('football.json')
            data.git_source('europe')
            for _ in range(7):
                data.git_source('south-america')
                data.git_source('football.json')
        assert len(calls) == expected
    assert [c[1] for c in calls[:3]] == ['clone'] * 3
    assert all('pull' in c for c in calls[3:])
    # Non-session callers continue to request fresh updates.
    data.git_source('europe')
    assert len(calls) == 7


def test_failed_pull_is_reused_as_failure_and_retried_next_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = Path('.runtime/openfootball/football.json')
    path.mkdir(parents=True)
    (path/'retained.txt').write_text('previous source')
    calls = []
    def fail(command, **kwargs):
        calls.append(command)
        raise subprocess.CalledProcessError(1, command, stderr=b'upstream offline')
    monkeypatch.setattr(data.subprocess, 'run', fail)
    with data.source_refresh_session():
        # Reading an explicitly offline checkout cannot satisfy a fresh pull.
        assert data.git_source('football.json', refresh=False) == path
        for _ in range(8):
            with pytest.raises(subprocess.CalledProcessError):
                data.git_source('football.json')
        assert len(calls) == 1
    with data.source_refresh_session():
        with pytest.raises(subprocess.CalledProcessError):
            data.git_source('football.json')
    assert len(calls) == 2
    assert (path/'retained.txt').read_text() == 'previous source'


def test_refresh_retains_nested_source_errors_and_continues(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts'))
    import refresh_sports
    import refresh_screenshot_leagues
    original = dict(source='argentina', error='missing current CSV', retained_previous=True)
    monkeypatch.setattr(refresh_screenshot_leagues, 'run', lambda *a: dict(errors=[original]))
    monkeypatch.setattr(refresh_sports, 'collect', lambda **kw: dict(errors=[]))
    calls = []
    monkeypatch.setattr(refresh_sports, 'calendar_collect', lambda **kw: calls.append(kw['code']) or {})
    monkeypatch.setattr(refresh_sports, 'football_run', lambda **kw: calls.append('settled') or {})
    reports = []
    monkeypatch.setattr(refresh_sports, 'write_json', lambda path, value: reports.append(value))
    monkeypatch.setattr(sys, 'argv', ['refresh_sports', '--sport', 'football'])
    assert refresh_sports.main() == 1
    assert reports[0]['football']['errors'] == [dict(original, collector='screenshots')]
    assert 'collector' not in original
    assert calls == ['BR2', 'BR1', 'AR1', 'CO1', 'US1', 'JP1', 'CN1', 'settled']
