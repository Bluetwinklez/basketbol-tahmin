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


@pytest.mark.parametrize('failure', ['exit', 'timeout'])
def test_failed_initial_clone_is_cleaned_and_next_session_recovers(tmp_path, monkeypatch, failure):
    monkeypatch.chdir(tmp_path)
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        checkout = Path(command[-1])
        checkout.mkdir(parents=True)
        (checkout / 'partial.txt').write_text('partial download')
        if len(calls) == 1:
            if failure == 'timeout':
                raise subprocess.TimeoutExpired(command, 180)
            raise subprocess.CalledProcessError(128, command)
        (checkout / 'LICENSE.md').write_text('CC0')
    monkeypatch.setattr(data.subprocess, 'run', run)
    error = subprocess.TimeoutExpired if failure == 'timeout' else subprocess.CalledProcessError
    with data.source_refresh_session():
        for _ in range(3):
            with pytest.raises(error): data.git_source('europe')
        assert len(calls) == 1
        assert not Path('.runtime/openfootball/europe').exists()
        assert list(Path('.runtime/openfootball').iterdir()) == []
    with data.source_refresh_session():
        path = data.git_source('europe')
        assert (path / 'LICENSE.md').read_text() == 'CC0'
        assert data.git_source('europe') == path
        assert len(calls) == 2
        assert list(path.parent.iterdir()) == [path]
