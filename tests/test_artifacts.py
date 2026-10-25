import hashlib
import json
import pytest

from bbtahmin.artifacts import verified_manifest,verified_path
from bbtahmin.ozellik import FEATURES
from bbtahmin.eksik_ozellik import EKSIK_LIGLERI
from bbtahmin.kutu_ozellik import KUTU_LIGLERI


def test_partial_mismatched_and_tampered_benchmarks_are_not_selected(tmp_path):
    assert verified_manifest(tmp_path) is None
    contents={'metrikler.csv':'lig,model\nNBA,skor\n','parametreler.json':'[]'}
    for name,content in contents.items():
        (tmp_path/name).write_bytes(content.encode())
    meta=dict(base_features=FEATURES,absence_leagues=sorted(EKSIK_LIGLERI),box_leagues=sorted(KUTU_LIGLERI),
              files={name:hashlib.sha256(value.encode()).hexdigest() for name,value in contents.items()})
    (tmp_path/'manifest.json').write_text(json.dumps(meta))
    assert verified_path('metrikler.csv',tmp_path)==tmp_path/'metrikler.csv'
    (tmp_path/'metrikler.csv').write_text('changed')
    assert verified_manifest(tmp_path) is None
    (tmp_path/'metrikler.csv').write_text(contents['metrikler.csv'])
    meta['absence_leagues']=['NBA'];(tmp_path/'manifest.json').write_text(json.dumps(meta))
    assert verified_manifest(tmp_path) is None


def test_default_predictions_cannot_fall_back_to_legacy_artifacts(tmp_path,monkeypatch):
    from bbtahmin.tahmin import parametreler,en_iyi_model
    monkeypatch.chdir(tmp_path)
    old=tmp_path/'docs/kanit';old.mkdir(parents=True)
    (old/'parametreler.json').write_text('[{"lig":"NBA","model":"mov","sezon":"2025-26","k":20}]')
    (old/'toplam.csv').write_text('lig,model,log_loss\nNBA,logistic,0.01\n')
    with pytest.raises(ValueError,match='pregame_verified'):
        parametreler('NBA')
    with pytest.raises(ValueError,match='pregame_verified'):
        en_iyi_model('NBA')


def test_default_model_choice_ignores_unsigned_aggregate(tmp_path,monkeypatch):
    from bbtahmin.tahmin import en_iyi_model
    root=tmp_path/'docs/kanit/pregame_verified';root.mkdir(parents=True)
    metrics='lig,sezon,model,n,log_loss\nNBA,2024-25,skor,100,0.6\nNBA,2024-25,logistic,100,0.7\n'
    (root/'parametreler.json').write_text('[]');(root/'metrikler.csv').write_text(metrics)
    (root/'toplam.csv').write_text('lig,model,log_loss\nNBA,logistic,0.01\n')
    meta=dict(base_features=FEATURES,absence_leagues=sorted(EKSIK_LIGLERI),box_leagues=sorted(KUTU_LIGLERI),
        files={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['parametreler.json','metrikler.csv']})
    (root/'manifest.json').write_text(json.dumps(meta));monkeypatch.chdir(tmp_path)
    assert en_iyi_model('NBA')=='skor'
    assert en_iyi_model('NBA',sezon='2025-26')=='skor'
