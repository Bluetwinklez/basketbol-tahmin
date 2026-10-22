import hashlib
import json

from bbtahmin.artifacts import verified_manifest,verified_path
from bbtahmin.ozellik import FEATURES
from bbtahmin.eksik_ozellik import EKSIK_LIGLERI
from bbtahmin.kutu_ozellik import KUTU_LIGLERI


def test_partial_mismatched_and_tampered_benchmarks_are_not_selected(tmp_path):
    assert verified_manifest(tmp_path) is None
    contents={'metrikler.csv':'lig,model\nNBA,skor\n','parametreler.json':'[]'}
    for name,content in contents.items():
        (tmp_path/name).write_text(content)
    meta=dict(base_features=FEATURES,absence_leagues=sorted(EKSIK_LIGLERI),box_leagues=sorted(KUTU_LIGLERI),
              files={name:hashlib.sha256(value.encode()).hexdigest() for name,value in contents.items()})
    (tmp_path/'manifest.json').write_text(json.dumps(meta))
    assert verified_path('metrikler.csv',tmp_path)==tmp_path/'metrikler.csv'
    (tmp_path/'metrikler.csv').write_text('changed')
    assert verified_manifest(tmp_path) is None
    (tmp_path/'metrikler.csv').write_text(contents['metrikler.csv'])
    meta['absence_leagues']=['NBA'];(tmp_path/'manifest.json').write_text(json.dumps(meta))
    assert verified_manifest(tmp_path) is None
