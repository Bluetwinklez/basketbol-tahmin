import pandas as pd
from bbtahmin.defter import doldur, ozet
from bbtahmin.tahmin import oran_ayir

def test_oran_ayir():
    assert oran_ayir('Washington - Milwaukee @1.30/2.14')==('Washington - Milwaukee',1.30,2.14)
    assert oran_ayir('Toronto - Chicago @-/3,79')==('Toronto - Chicago',None,3.79)
    assert oran_ayir('A - B')==('A - B',None,None)

def test_doldur_ve_ozet():
    defter=pd.DataFrame([dict(kayit_utc='2026-10-21T20:00Z',lig='NBA',mac_utc='2026-10-21T23:00:00+00:00',ev='WAS',dep='MIL',ev_kazanir=.3,fark=-2.,toplam=220.,
        toplam_80_alt=200,toplam_80_ust=240,piyasa_ev=.6,gercek_ev=None,gercek_dep=None)])
    maclar=pd.DataFrame([dict(lig='NBA',ev='WAS',dep='MIL',tarih_utc=pd.Timestamp('2026-10-22T00:00Z'),ev_skor=100,dep_skor=110),
                         dict(lig='NBA',ev='WAS',dep='MIL',tarih_utc=pd.Timestamp('2026-12-22T00:00Z'),ev_skor=130,dep_skor=90)])
    d=doldur(defter,maclar)
    assert (d.gercek_ev.iloc[0],d.gercek_dep.iloc[0])==(100,110)
    o=ozet(d)
    assert o['kazanan_isabet']==1.0 and o['piyasa_isabet']==0.0 and o['toplam_80_icinde']==1.0


def test_ambiguous_results_are_not_silently_assigned():
    d=pd.DataFrame([dict(lig='NBA',mac_utc='2026-10-21T23:00Z',ev='A',dep='B',gercek_ev=None,gercek_dep=None)])
    g=pd.DataFrame([dict(lig='NBA',ev='A',dep='B',tarih_utc=pd.Timestamp(t),ev_skor=100,dep_skor=90)
                    for t in ['2026-10-21T22:00Z','2026-10-22T00:00Z']])
    assert doldur(d,g).gercek_ev.isna().all()


def test_late_and_unverifiable_predictions_do_not_inflate_accuracy():
    base=dict(kayit_utc='2026-10-21T20:00Z',lig='NBA',mac_utc='2026-10-21T23:00Z',ev='A',dep='B',
        ev_kazanir=.8,fark=10.,toplam=190.,toplam_80_alt=170,toplam_80_ust=210,piyasa_ev=.7,gercek_ev=100,gercek_dep=90)
    d=pd.DataFrame([base,dict(base,kayit_utc='2026-10-21T21:00Z'),
                    dict(base,kayit_utc='2026-10-22T01:00Z'),dict(base,kayit_utc=None)])
    assert ozet(d)['mac']==1
    assert ozet(d.drop(columns='kayit_utc')) is None


def test_saving_a_postgame_prediction_is_rejected(tmp_path):
    import pytest
    from bbtahmin.defter import kaydet
    with pytest.raises(ValueError,match='before tipoff'):
        kaydet([dict(tarih_utc='2000-01-01T00:00Z',ev_kazanir=.5)],tmp_path/'ledger.csv')
    assert not (tmp_path/'ledger.csv').exists()


def test_espn_repeated_matchup_receives_only_its_own_dates_score(monkeypatch):
    import io,json
    from urllib.parse import parse_qs,urlparse
    from bbtahmin.defter import espn_doldur
    d=pd.DataFrame([dict(lig='NBA',mac_utc=t,ev='BOS',dep='NYK',gercek_ev=None,gercek_dep=None)
                    for t in ['2026-10-21T23:00Z','2026-10-23T23:00Z']])
    def response(request,**kwargs):
        day=parse_qs(urlparse(request.full_url).query)['dates'][0]
        score=100 if day=='20261021' else 120
        date='2026-10-21T23:00Z' if day=='20261021' else '2026-10-23T23:00Z'
        event=dict(date=date,competitions=[dict(status={'type':{'name':'STATUS_FINAL'}},competitors=[
            dict(homeAway='home',team={'abbreviation':'BOS'},score=str(score)),
            dict(homeAway='away',team={'abbreviation':'NYK'},score='90')])])
        return io.BytesIO(json.dumps(dict(events=[event])).encode())
    monkeypatch.setattr('urllib.request.urlopen',response)
    result=espn_doldur(d)
    assert result.gercek_ev.tolist()==[100,120]


def test_actual_tipoff_overrides_a_later_user_entered_time_for_accuracy():
    base=dict(lig='NBA',mac_utc='2026-10-22T00:00Z',gercek_mac_utc='2026-10-21T23:00Z',ev='A',dep='B',
        ev_kazanir=.8,fark=10.,toplam=190.,toplam_80_alt=170,toplam_80_ust=210,piyasa_ev=.7,gercek_ev=100,gercek_dep=90)
    late=pd.DataFrame([dict(base,kayit_utc='2026-10-21T23:30Z')])
    assert ozet(late) is None
    duplicate=pd.DataFrame([dict(base,kayit_utc='2026-10-21T21:00Z'),
                             dict(base,mac_utc='2026-10-21T23:30Z',kayit_utc='2026-10-21T22:00Z')])
    assert ozet(duplicate)['mac']==1
