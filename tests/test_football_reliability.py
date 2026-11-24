"""Calibration must distinguish missing evidence from perfect predictions."""
import json
from pathlib import Path
import pytest


@pytest.fixture
def reliability(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts'))
    from evaluate_football_ensemble import reliability
    return reliability


def test_empty_is_serializable_absence_of_evidence(reliability):
    result = reliability([], [])
    assert result == dict(n=0, brier=None, log_loss=None, expected_calibration_error=None, bins=[])
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('p,y', [
    ([.5], []), ([[.5]], [[1]]), ([float('nan')], [1]),
    ([.5], [float('inf')]), ([-.01], [0]), ([1.01], [1]), ([.5], [.5]),
])
def test_invalid_observations_fail_closed(reliability, p, y):
    with pytest.raises(ValueError): reliability(p, y)


def test_boundary_probabilities_are_counted_once(reliability):
    result = reliability([0, .1, .5, 1], [0, 0, 1, 1])
    assert result['n'] == sum(b['n'] for b in result['bins']) == 4
    assert result['brier'] == pytest.approx(.065)
    assert result['expected_calibration_error'] == pytest.approx(.15)
    assert result['log_loss'] == pytest.approx(.1996269240544429)
    json.dumps(result, allow_nan=False)
