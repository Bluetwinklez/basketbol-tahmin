"""Rejected multi-output refreshes must preserve previously published bytes."""
import copy
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from bbtahmin.veri import asia


def game(identity='KBL_1'):
    return dict(mac_id=identity,lig='KBL',sezon='2025-26',tarih_utc='2025-10-01T10:00Z',
                ev='KBL_A',dep='KBL_B',ev_skor=80,dep_skor=75)


def snapshot():
    return {str(p):p.read_bytes() for directory in ('data','docs')
            for p in Path(directory).rglob('*') if p.is_file()}


def seed(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    teams={'KBL_A':dict(name='안양',aliases=['Anyang'])}
    fixtures=[dict(game('KBL_future'),tarih_utc='2027-01-01T10:00Z')]
    asia.save('KBL',[game()],teams,{'sources':['original']},fixtures)
    return teams,fixtures,snapshot()


def test_duplicate_fixtures_cannot_partially_publish_new_results(tmp_path,monkeypatch):
    teams,fixtures,before=seed(tmp_path,monkeypatch)
    with pytest.raises(ValueError,match='Duplicate current fixtures'):
        asia.save('KBL',[game('KBL_2')],{'KBL_A':dict(name='New name')},
                  {'sources':['new']},fixtures*2)
    assert snapshot()==before


def test_report_serialization_failure_preserves_all_files_and_inputs(tmp_path,monkeypatch):
    teams,fixtures,before=seed(tmp_path,monkeypatch)
    report={'sources':['new'],'bad':object()};original=copy.deepcopy(teams)
    with pytest.raises(TypeError):
        asia.save('KBL',[game('KBL_2')],teams,report,[])
    assert snapshot()==before
    assert teams==original and 'games' not in report


def test_staging_write_failure_preserves_outputs_and_cleans_temp_files(tmp_path,monkeypatch):
    teams,fixtures,before=seed(tmp_path,monkeypatch)
    original=asia.tempfile.NamedTemporaryFile;calls=[]
    def fail_second(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:raise OSError('simulated staging failure')
        return original(*args,**kwargs)
    monkeypatch.setattr(asia.tempfile,'NamedTemporaryFile',fail_second)
    with pytest.raises(OSError,match='staging failure'):
        asia.save('KBL',[game('KBL_2')],teams,{},[])
    assert snapshot()==before
    assert not list(Path('.').rglob('*.part'))


def test_success_updates_coherent_hash_and_utf8_catalog(tmp_path,monkeypatch):
    teams,fixtures,_=seed(tmp_path,monkeypatch)
    result=asia.save('KBL',[game('KBL_2')],teams,{'sources':['next']},[])
    assert len(result)==2
    path=Path('data/asia/KBL.parquet')
    report=json.loads(Path('docs/kanit/asia_data/KBL_collection.json').read_text('utf8'))
    assert report['games']==2 and report['dataset_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    assert report['sources']==['original','next']
    assert pd.read_parquet('data/asia/KBL_fixtures.parquet').empty
    assert json.loads(Path('data/asia/KBL_teams.json').read_text('utf8'))['KBL_A']['name']=='안양'
