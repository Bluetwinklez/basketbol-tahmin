import pandas as pd
from bbtahmin.football.coverage import last_matches
from bbtahmin.football.data import row

def test_last50_excludes_today_foreign_and_unfinished():
    rows=[row('TR1','2025-26',f'2025-08-{i:02d}','A','B',[2,1],'source','2026-10-25') for i in range(1,26)]
    rows += [row('EN1','2025-26','2025-08-01','A','B',[9,0],'source','2026-10-25'),row('TR1','2025-26','2025-08-26','A','B',[5,0],'source','2026-10-25')]
    r=last_matches(pd.DataFrame(rows),'TR1','A','2025-08-26',20)
    assert r['available']==20 and r['wins']==20 and r['goals_for']==40
    assert r['matches'][0]['date']=='2025-08-25'
    r=last_matches(pd.DataFrame(rows),'TR1','A','2025-08-26')
    assert r['missing']==25


def test_current_coverage_does_not_equate_refresh_or_history_to_readiness():
    from bbtahmin.football.coverage import league_coverage
    data=[row('TR1','2025-26','2025-09-01','A','B',[1,0],'source','2026-10-25T12:00Z'),
          row('BR2','2026','2026-01-01','A','B',[1,0],'source','2026-10-25T12:00Z'),
          row('AR2','2026','2026-10-19','A','B',[1,0],'source','2026-10-25T12:00Z')]
    report=league_coverage(pd.DataFrame(data),now='2026-10-25T12:00Z')
    leagues={x['league']:x for x in report['leagues']}
    assert leagues['TR1']['status']=='missing_active_season'
    assert leagues['BR2']['status']=='stale_active_history'
    assert leagues['AR2']['status']=='partial_active_history'
    assert leagues['CO2']['status']=='missing_archive'
    assert leagues['USL1']['historical_finals']==0
    assert all(not x['prediction_ready'] for x in leagues.values())
    assert league_coverage(pd.DataFrame(),now='2026-10-25T12:00Z')['leagues']


def test_team_inventory_excludes_other_season_clubs_but_uses_prior_history():
    from bbtahmin.football.coverage import team_history_coverage
    records=[row('TR1','2025-26','2025-08-01','A','Old',[2,0],'source','2026-10-25'),
             row('TR1','2026-27','2026-10-20','A','B',None,'source','2026-10-25'),
             row('TR1','2026-27','2026-10-25','A','B',[9,0],'source','2026-11-01'),
             row('EN1','2025-26','2025-08-01','A','B',[8,0],'source','2026-10-25')]
    r=team_history_coverage(pd.DataFrame(records),'TR1','2026-27','2026-10-25',1)
    teams={t['team']:t for t in r['teams']}
    assert set(teams)=={'a','b'}
    assert teams['a']['available']==1 and teams['a']['goals_for']==2
    assert teams['b']['available']==0 and teams['b']['missing']==1
    assert teams['a']['event_ids']==[records[0]['event_id']]
    assert teams['a']['source_kinds']=={'community_CC0_not_official':1}
    assert r['teams_with_requested_history']==1 and r['missing_team_match_records']==1
    assert all(not t['complete_history_verified'] for t in teams.values())


def test_empty_team_inventory_does_not_invent_membership():
    from bbtahmin.football.coverage import team_history_coverage
    r=team_history_coverage(pd.DataFrame(),'TR1','2026-27','2026-10-25')
    assert r['teams']==[] and r['archived_season_teams']==0


def test_team_inventory_rejects_noninteger_limits():
    import pytest
    from bbtahmin.football.coverage import team_history_coverage
    for limit in (0,101,1.5,True):
        with pytest.raises(ValueError):
            team_history_coverage(pd.DataFrame(),'TR1','2026-27','2026-10-25',limit)


def test_empty_archive_returns_explicit_missing_history():
    for frame in (pd.DataFrame(), pd.DataFrame(columns=['league','status'])):
        r=last_matches(frame,'TR1','A','2026-11-24')
        assert r['available']==0 and r['missing']==50 and r['matches']==[]
        assert r['last_date'] is None
        assert r['wins']==r['draws']==r['losses']==r['goals_for']==r['goals_against']==0
        assert r['team']=='a' and r['cutoff_exclusive']=='2026-11-24'


def test_direct_history_rejects_invalid_limits_before_empty_archive():
    import pytest
    for limit in (0,101,1.5,True,'50',None):
        with pytest.raises(ValueError,match='integer'):
            last_matches(pd.DataFrame(),'TR1','A','2026-11-24',limit)


def test_missing_team_in_populated_archive_returns_empty_history():
    frame=pd.DataFrame([row('TR1','2026-27','2026-10-20','A','B',[1,0],'source','2026-11-24')])
    r=last_matches(frame,'TR1','Unknown','2026-11-24',10)
    assert r['available']==0 and r['missing']==10
