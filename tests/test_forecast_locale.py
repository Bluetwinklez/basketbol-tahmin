"""Real subprocess regression with UTF-8 mode disabled (Windows cp1254)."""
import json
import os
from pathlib import Path
import subprocess
import sys

from bbtahmin.football.daily import digest
from bbtahmin.football.data import row,write_json


def test_utf8_forecast_survives_non_utf8_process_locale(tmp_path):
    root=tmp_path/'football';output=tmp_path/'ledger';(output/'forecasts').mkdir(parents=True)
    fixture=row('EN1','2026-27','2026-10-24','A','B',None,'https://example.com','2026-10-23T12:00Z')
    fixture['home_name']='İstanbul Žalgiris 서울'
    prediction=dict(model='test',expected_home_goals=1.2,expected_away_goals=.8,
                    probabilities=dict(home=.5,draw=.3,away=.2),predicted_outcome='home',
                    over={'1.5':.6,'2.5':.4,'3.5':.2},both_teams_score=.4,total_goals_80=[0,4])
    payload=dict(spec='football-prospective-v1',recorded_at_utc='2026-10-23T13:00Z',fixture=fixture,prediction=prediction)
    write_json(output/'forecasts/original.json',dict(payload,payload_sha256=digest(payload)))
    write_json(root/'collection.json',dict(checked_at_utc='2026-10-25T12:00Z',errors=[]))
    write_json(tmp_path/'frame.json',[dict(fixture,status='final',home_goals=1,away_goals=0)])
    original=(output/'forecasts/original.json').read_bytes()
    script=tmp_path/'check.py'
    script.write_text(f'''import json
from pathlib import Path
import pandas as pd
from bbtahmin.football import daily
daily.load=lambda root:pd.DataFrame(json.loads(Path({str(tmp_path/'frame.json')!r}).read_text(encoding='utf8')))
report=daily.run(root={str(root)!r},output={str(output)!r},now='2026-10-25T13:00Z',require_fixture_confirmation=False)
print(report['publisher_performance']['games'])
''',encoding='utf8')
    env=dict(os.environ,PYTHONUTF8='0',PYTHONPATH=str(Path(__file__).parents[1]/'src'))
    process=subprocess.run([sys.executable,str(script)],env=env,capture_output=True,timeout=30)
    assert process.returncode==0,process.stderr.decode('utf8',errors='replace')
    assert process.stdout.strip()==b'1'
    assert (output/'forecasts/original.json').read_bytes()==original
