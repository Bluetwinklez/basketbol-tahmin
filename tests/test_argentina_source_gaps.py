import csv
import json
from pathlib import Path
import pytest
from bbtahmin.football import screenshots


def source(tmp_path, monkeypatch):
    p=tmp_path/'upstream';p.mkdir();(p/'data').mkdir()
    (p/'LICENSE-DATOS.md').write_text('CC BY-SA 4.0')
    monkeypatch.setattr(screenshots.subprocess,'check_output',lambda *a,**k:'revision123')
    return p


def test_missing_current_source_retains_archive_and_reports_pinned_path(tmp_path, monkeypatch):
    p=source(tmp_path,monkeypatch);root=tmp_path/'archive';root.mkdir()
    prior=root/'AR2_2026.json.gz';prior.write_bytes(b'original snapshot')
    report=screenshots.argentina(p,root=root,first=2026)
    assert report['partial'] and not report['files']
    assert report['errors'][0]['season']=='2026'
    assert '/revision123/data/partidos-2026.csv' in report['errors'][0]['source_url']
    assert prior.read_bytes()==b'original snapshot'
    assert json.loads((root/'screenshot_argentina_collection.json').read_text())==report


def test_ineligible_rows_are_not_reported_as_success(tmp_path,monkeypatch):
    p=source(tmp_path,monkeypatch)
    (p/'data/partidos-2026.csv').write_text('source\nhttps://unlicensed.example/game\n')
    report=screenshots.argentina(p,root=tmp_path/'output',first=2026)
    assert report['partial'] and not report['files']
    assert {e['league'] for e in report['errors']}=={'AR1','AR2'}
    assert all(e['source_sha256'] and e['retained_previous'] for e in report['errors'])


def test_refresh_forwards_source_gaps_and_continues_mexico(monkeypatch):
    import sys
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts'))
    import refresh_screenshot_leagues as refresh
    monkeypatch.setattr(refresh.subprocess,'run',lambda *a,**k:None)
    error=dict(source='argentina',season='2026',error='Source file unavailable',retained_previous=True)
    monkeypatch.setattr(refresh,'argentina',lambda *a,**k:dict(files=[],errors=[error]))
    monkeypatch.setattr(refresh,'git_source',lambda *a:'world')
    monkeypatch.setattr(refresh,'mexico',lambda *a:dict(files=[{'season':'2024-25'}],errors=[]))
    report=refresh.run(backfill=True)
    assert report['errors']==[error]
    assert report['files']==[{'season':'2024-25'}]


def test_missing_backfill_does_not_block_healthy_current_leagues(tmp_path,monkeypatch):
    p=source(tmp_path,monkeypatch)
    common=dict(source='https://es.wikipedia.org/wiki/Example',phase='zonas',neutral=False,
        date='2026-10-01',home_pens='',away_pens='',home_score=2,away_score=1,
        home_team='Home',away_team='Away')
    rows=[dict(common,tournament=t) for t in ('Primera Nacional','Primera Division')]
    with (p/'data/partidos-2026.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    report=screenshots.argentina(p,root=tmp_path/'output',first=2025)
    assert report['partial'] and report['errors'][0]['season']=='2025'
    assert {f['league'] for f in report['files']}=={'AR1','AR2'}
    assert all(f['rows']==1 for f in report['files'])
