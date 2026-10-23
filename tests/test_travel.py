import pytest
from bbtahmin.travel import distance,context


def test_distance_symmetry_and_unknown_venue_does_not_become_zero():
    a=dict(latitude=0,longitude=0,timezone='UTC');b=dict(latitude=0,longitude=1,timezone='Europe/Istanbul')
    assert distance(a,b)==pytest.approx(111.195,abs=.001)
    assert distance(a,b)==pytest.approx(distance(b,a))
    assert distance(a,a)==0
    snapshot=dict(captured_at_utc='2026-10-20T00:00Z',source_url='https://example.org',games=[
        dict(event_id='past',start_utc='2026-10-19T12:00Z',home='H',away='X',venue_id='v1',played=True),
        dict(event_id='next',start_utc='2026-10-23T12:00Z',home='H',away='A',venue_id='v2',played=False)])
    registry=dict(captured_at_utc='2026-10-20T00:00Z',venues={'v1':a,'v2':b})
    result=context(snapshot,registry,'next','2026-10-22T00:00Z')
    assert result['teams']['H']['scheduled_leg_km']==pytest.approx(111.195,abs=.001)
    assert result['teams']['H']['timezone_shift_hours']==3
    assert result['teams']['A']['scheduled_leg_km'] is None
    assert not result['used_in_default_model']
    with pytest.raises(ValueError):context(snapshot,registry,'next','2026-10-19T00:00Z')
    with pytest.raises(ValueError):context(snapshot,registry,'next','2026-10-23T13:00Z')
