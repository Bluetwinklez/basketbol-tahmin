import csv
import io
from copy import deepcopy

import pytest

from bbtahmin.football.exports import export_csv, markdown


@pytest.mark.parametrize(
    ('home', 'draw', 'away', 'best'),
    [
        (0.4567894, 0.3, 0.2432106, '1X 75.7%'),
        (0.2, 0.3, 0.5, 'X2 80.0%'),
        (0.4, 0.15, 0.45, '12 85.0%'),
    ],
)
def test_double_chance_exports_preserve_existing_fields(home, draw, away, best):
    report = {'forecasts': [{
        'fixture': {'league': 'TR1', 'date': '2026-10-25', 'home_name': 'A', 'away_name': 'B'},
        'prediction': {
            'model': 'test-model',
            'probabilities': {'home': home, 'draw': draw, 'away': away},
            'over': {'1.5': 0.7, '2.5': 0.4, '3.5': 0.2},
            'both_teams_score': 0.5,
        },
        'status': 'publisher_final',
        'result': {
            'actual_home': 2, 'actual_away': 1, 'winner_correct': True,
            'total_absolute_error': 0.5, 'margin_absolute_error': 0.25,
        },
    }]}
    original = deepcopy(report)

    header, row = list(csv.reader(io.StringIO(export_csv(report).decode('utf-8-sig'))))
    assert header[:-3] == [
        'league', 'date', 'home', 'away', 'status', 'model', 'home_probability', 'draw_probability',
        'away_probability', 'over_1.5', 'over_2.5', 'over_3.5', 'both_teams_score', 'actual_home',
        'actual_away', 'winner_correct', 'total_absolute_error', 'margin_absolute_error',
    ]
    assert row[:-3] == [
        'TR1', '2026-10-25', 'A', 'B', 'publisher_final', 'test-model', str(home), str(draw),
        str(away), '0.7', '0.4', '0.2', '0.5', '2', '1', 'True', '0.5', '0.25',
    ]
    assert header[-3:] == ['prob_1x', 'prob_x2', 'prob_12']
    prob_1x, prob_x2, prob_12 = map(float, row[-3:])
    assert (prob_1x, prob_x2, prob_12) == tuple(round(value, 6) for value in (home + draw, draw + away, home + away))
    assert (prob_1x + away, prob_x2 + home, prob_12 + draw) == pytest.approx((1, 1, 1), abs=0.0000005)

    lines = markdown(report).decode('utf-8').splitlines()
    assert lines[-3].endswith('| Status | Best double chance |')
    assert lines[-1].endswith(f'| 40.0% | publisher_final | {best} |')
    assert report == original
