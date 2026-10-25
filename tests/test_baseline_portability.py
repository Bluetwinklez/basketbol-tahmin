import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

from bbtahmin.football.daily import digest


def test_portable_pin_allows_only_newline_conversion_and_legacy_append(tmp_path,monkeypatch):
    script=Path(__file__).parents[1]/'scripts/pin_improvement_baseline.py'
    spec=importlib.util.spec_from_file_location('pin_baseline',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.chdir(tmp_path);monkeypatch.setattr('sys.argv',['pin_baseline'])
    monkeypatch.setattr(module,'load',lambda:pd.DataFrame())
    monkeypatch.setattr(module,'inventory',lambda *args:{})
    source=tmp_path/'data/forecasts/a.json';source.parent.mkdir(parents=True)
    payload=dict(spec='football-prospective-v1',prediction=dict(probability=.6))
    encoded=json.dumps(dict(payload,payload_sha256=digest(payload)),indent=2).encode()
    source.write_bytes(encoded.replace(b'\n',b'\r\n'))
    legacy=tmp_path/'defter/tahminler.csv';legacy.parent.mkdir();legacy.write_bytes(b'id,score\r\n1,90\r\n')
    module.main();module.main()  # Create then migrate after raw-byte validation.
    baseline=(tmp_path/'docs/kanit/improvement/baseline.json').read_bytes()
    source.write_bytes(encoded);legacy.write_bytes(b'id,score\n1,90\n2,85\n')
    monkeypatch.setattr('sys.argv',['pin_baseline','--verify-only']);module.main()
    assert (tmp_path/'docs/kanit/improvement/baseline.json').read_bytes()==baseline
    legacy.write_bytes(b'id,score\n1,91\n2,85\n')
    with pytest.raises(ValueError,match='Original forecast changed'):module.main()
