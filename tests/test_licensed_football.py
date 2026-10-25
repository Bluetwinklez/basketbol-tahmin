import copy
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from bbtahmin.football.licensed import merge


def base():
    return dict(event_id='x',league='EN1',season='2026-27',date='2026-10-24',home='a',away='b',status='scheduled',home_goals=None,away_goals=None)


def overlay():
    return dict(base(),status='final',home_goals=2,away_goals=1,license='CC-BY-SA-4.0',
                source_kind='wikipedia_CC_BY_SA_independently_checked',source_url='https://en.wikipedia.org/wiki/Season',
                fixture_verification_url='https://www.espn.com/soccer/game/_/gameId/1',attribution='Wikipedia contributors',
                source_sha256='a'*64,actual_start_utc='2026-10-24T19:00Z',captured_at_utc='2026-10-25T12:00Z')


def test_overlay_preserves_original_and_rejects_identity_or_final_conflicts():
    original=base();new=merge([original],[overlay()])
    assert original['status']=='scheduled' and new[0]['status']=='final'
    for changed in (dict(overlay(),date='2026-10-23'),dict(overlay(),license='CC0'),dict(overlay(),actual_start_utc='2026-10-25T00:00Z')):
        with pytest.raises(ValueError):merge([original],[changed])
    with pytest.raises(ValueError):merge([dict(original,status='final',home_goals=0,away_goals=0)],[overlay()])
    corrected=dict(overlay(),date='2026-10-23',original_date='2026-10-24',date_correction_verified=True,actual_start_utc='2026-10-23T19:00Z')
    assert merge([original],[corrected])[0]['date']=='2026-10-23'


def test_licensed_scores_need_independent_exact_score_and_date():
    spec=importlib.util.spec_from_file_location('licensed_collect',Path(__file__).parents[1]/'scripts/collect_licensed_football.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=dict(license='CC-BY-SA-4.0',league='EN1',season='2026-27',captured_at_utc='2026-10-25T12:00Z',
                source_url='https://en.wikipedia.org/wiki/Season',license_url='https://creativecommons.org/licenses/by-sa/4.0/',sha256='a'*64,
                rows=[dict(home_name='A',away_name='B',home_goals=2,away_goals=1)])
    obs=dict(overlay(),home_name='A',away_name='B',start_utc='2026-10-24T19:00Z',captured_at='2026-10-25T12:00Z',
             source_url='https://www.espn.com/soccer/game/_/gameId/1',home_score=2,away_score=1)
    review=dict(status='confirmed',event_id='x',observation=obs)
    rows,_=module.build(pd.DataFrame([base()]),source,[review],'2026-10-25T13:00Z')
    assert rows[0]['home_goals']==2
    review['observation']=dict(obs,home_score=3)
    with pytest.raises(ValueError,match='score conflict'):module.build(pd.DataFrame([base()]),source,[review],'2026-10-25T13:00Z')


def test_validated_final_survives_source_omission_and_reissued_date_id():
    assert merge([],[overlay()])[0]['event_id']=='x'
    reissued=dict(base(),event_id='new-date-hash')
    retained=merge([reissued],[overlay()])
    assert len(retained)==1 and retained[0]['event_id']=='x'
    assert retained[0]['event_aliases']==['new-date-hash']
    with pytest.raises(ValueError):merge([dict(reissued,status='final',home_goals=0,away_goals=0)],[overlay()])


def test_conflicting_new_base_snapshot_retains_previous_bytes(tmp_path):
    from bbtahmin.football.storage import save
    save([base()],'EN1','2026-27',tmp_path)
    save([overlay()],'EN1','2026-27',tmp_path/'licensed_overlays')
    path=tmp_path/'EN1_2026-27.json.gz';original=path.read_bytes()
    with pytest.raises(ValueError):save([dict(base(),status='final',home_goals=0,away_goals=0)],'EN1','2026-27',tmp_path)
    assert path.read_bytes()==original
