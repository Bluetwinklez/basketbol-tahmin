"""An explicitly blank official final must not discard healthy league results."""
import json

import pytest

from bbtahmin.veri import japan
from test_asia import japan_row

TITLE='<div class="champion-box"><span class="title">2026.10.03</span></div>'


def test_blank_final_is_quarantined_with_identity_and_never_scored():
    blank=japan_row('2').replace('>85<','><').replace('>80<','><')
    rejected=[]
    rows,fixtures,_,_,excluded=japan.parse_topics(
        [TITLE+japan_row('1')+blank],2026,1,'2026-10-27T00:00Z',rejected=rejected)
    assert [r['mac_id'] for r in rows]==['JP_B1_1']
    assert not fixtures and excluded==1
    assert rejected[0]['mac_id']=='JP_B1_2'
    assert rejected[0]['source_url'].endswith('ScheduleKey=2')
    assert rejected[0]['source_state']=='FINAL'
    assert rejected[0]['tarih_utc']=='2026-10-03T10:05:00+00:00'
    # Callers without an explicit quarantine sink still fail closed.
    with pytest.raises(ValueError,match='valid Japanese scores'):
        japan.parse_topics([TITLE+blank],2026,1,'2026-10-27T00:00Z')


@pytest.mark.parametrize('replacement',['?', '85x', ''])
def test_one_bad_score_does_not_silently_become_blank_quarantine(replacement):
    bad=japan_row().replace('>85<','>'+replacement+'<')
    with pytest.raises(ValueError,match='valid Japanese scores'):
        japan.parse_topics([TITLE+bad],2026,1,'2026-10-27T00:00Z',rejected=[])


def test_partial_collection_saves_healthy_results_from_both_divisions(monkeypatch):
    blank=japan_row('2').replace('>85<','><').replace('>80<','><')
    def fetch(url,refresh=False):
        if 'data_format' in url:
            return json.dumps(dict(topics=[TITLE+japan_row('1')+blank],index=None))
        division=1 if 'tab=1' in url else 2
        return f"var year = '2026'; var tab = '{division}'; var event = '{2 if division==1 else 7}';"
    monkeypatch.setattr(japan,'fetch',fetch)
    monkeypatch.setattr(japan.time,'sleep',lambda _:None)
    saved=[]
    monkeypatch.setattr(japan,'save',lambda code,records,teams,report,fixtures:saved.append((code,records,report)))
    with pytest.raises(ValueError,match='valid results saved'):
        japan.collect(years=(2026,),divisions=(1,2))
    assert [x[0] for x in saved]==['JP_B1','JP_B2']
    for code,records,report in saved:
        assert len(records)==1 and records[0]['ev_skor']==85
        assert report['partial'] is True
        assert report['rejected_finals'][0]['mac_id']==code+'_2'


def test_quarantined_identity_cannot_repeat_across_pages(monkeypatch):
    blank=japan_row('2').replace('>85<','><').replace('>80<','><')
    def fetch(url,refresh=False):
        if 'data_format' in url:
            return json.dumps(dict(topics=[TITLE+blank],index=20 if 'index=0' in url else None))
        return "var year = '2026'; var tab = '1'; var event = '2';"
    monkeypatch.setattr(japan,'fetch',fetch)
    monkeypatch.setattr(japan.time,'sleep',lambda _:None)
    monkeypatch.setattr(japan,'save',lambda *args:pytest.fail('Repeated pages must not publish'))
    with pytest.raises(ValueError,match='Repeated Japanese pagination'):
        japan.collect(years=(2026,),divisions=(1,))
