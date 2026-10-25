import importlib.util
import json
from pathlib import Path

import pytest


def module():
    spec=importlib.util.spec_from_file_location('wiki_inspection',Path(__file__).parents[1]/'scripts/inspect_wikipedia_football.py')
    loaded=importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded)
    return loaded


def test_score_matrix_requires_license_and_does_not_invent_dates():
    m=module()
    html='''<link rel="license" href="https://creativecommons.org/licenses/by-sa/4.0/deed.en">
    <table><tr><th>Home \\ Away</th><th><a href="/a">A</a></th><th><a href="/b">B</a></th></tr>
    <tr><th><a href="/a">Club A</a></th><td>—</td><td>2–1</td></tr>
    <tr><th><a href="/b">Club B</a></th><td>6 Dec</td><td>—</td></tr></table>'''
    rows=m.parse(html.encode())
    assert len(rows)==1 and rows[0]['date'] is None
    with pytest.raises(ValueError):m.parse(html.replace('by-sa/4.0','by/4.0').encode())


def test_source_refresh_failures_are_persisted_and_exit_nonzero(tmp_path,monkeypatch):
    m=module();monkeypatch.chdir(tmp_path);monkeypatch.setattr(m,'PAGES',{'EN1':'Premier_League','TR1':'Süper_Lig'})
    def fail(*args,**kwargs):raise OSError('source unavailable')
    monkeypatch.setattr(m,'fetch_bytes',fail)
    assert m.main()==1
    report=json.loads(Path('data/football/licensed_source_refresh.json').read_text(encoding='utf8'))
    assert len(report['results'])==2 and all('error' in r for r in report['results'])
