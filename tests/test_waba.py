import pandas as pd
import pytest
from bbtahmin.veri.waba import html,parse
from bbtahmin.domestic_features import features


def test_widget_is_decoded_as_data_and_uncertain_clock_gets_day_embargo():
    response="MBT.API.update('x', '<div>Celje\\nWomen<\\/div>');"
    assert html(response)=='<div>Celje\nWomen</div>'
    with pytest.raises(ValueError):html('process.exit()')
    text='''<table><tr id="253-303-schedule-line-container-123"><td>07.10.2026 18:00</td>
        <td>Cinkarna Celje</td><td>83<span></span>:<b>53</b></td><td>Montana 2003</td><td>Hall</td></tr></table>'''
    rows,n=parse(text,2026,'https://example.org','2026-10-23T00:00Z')
    assert n==0 and rows[0]['ev']=='ECW_58477' and rows[0]['dep']=='ECW_813'
    assert rows[0]['date_precision']=='day'
    assert rows[0]['model_time_utc']==pd.Timestamp('2026-10-08T00:00Z')
    d=pd.DataFrame(rows)
    q=pd.DataFrame([dict(mac_id='q',ev='ECW_58477',dep='OTHER',tarih_utc=pd.Timestamp('2026-10-08T18:00Z'))])
    assert features(q,d).dom_home_missing.iloc[0]==1
    q['tarih_utc']=pd.Timestamp('2026-10-09T18:00Z')
    assert features(q,d).dom_home_missing.iloc[0]==0


def test_recent_domestic_form_is_invariant_to_archive_file_order():
    d=pd.DataFrame([dict(ev='H',dep='A',tarih_utc=pd.Timestamp('2025-01-01T00:00Z')+pd.Timedelta(days=i),
        ev_skor=50+i,dep_skor=60) for i in range(20)])
    q=pd.DataFrame([dict(mac_id='q',ev='H',dep='A',tarih_utc=pd.Timestamp('2025-02-01T18:00Z'))])
    assert features(q,d).equals(features(q,d.iloc[::-1]))
