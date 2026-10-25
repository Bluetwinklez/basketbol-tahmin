import importlib.util
from pathlib import Path

import pytest


def test_date_conflict_is_retained_without_rewriting_original():
    spec=importlib.util.spec_from_file_location('fixture_reviews',Path(__file__).parents[1]/'scripts/register_fixture_reviews.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original=dict(sport='football',status='date_mismatch_pending',event_id='EN1_1',league='EN1',
                  fixture_start='2026-10-25',actual_start='2026-10-26T20:00Z',
                  prediction=dict(home='a',away='b'),result_source='https://example.com/game/1',provider_event_id='1')
    audit=dict(checked_at_utc='2026-10-25T12:00Z',rows=[original])
    reviews=module.register(audit)
    assert original['fixture_start']=='2026-10-25'
    assert reviews['EN1_1']['status']=='quarantined_date_conflict'
    assert reviews['EN1_1']['observed_start_utc'].startswith('2026-10-26')
    audit['rows'].append(original)
    with pytest.raises(ValueError,match='Ambiguous'): module.register(audit)
