import pandas as pd
from bbtahmin.defter import doldur, ozet
from bbtahmin.tahmin import oran_ayir

def test_oran_ayir():
    assert oran_ayir('Washington - Milwaukee @1.30/2.14')==('Washington - Milwaukee',1.30,2.14)
    assert oran_ayir('Toronto - Chicago @-/3,79')==('Toronto - Chicago',None,3.79)
    assert oran_ayir('A - B')==('A - B',None,None)

def test_doldur_ve_ozet():
    defter=pd.DataFrame([dict(lig='NBA',mac_utc='2026-10-21T23:00:00+00:00',ev='WAS',dep='MIL',ev_kazanir=.3,fark=-2.,toplam=220.,
        toplam_80_alt=200,toplam_80_ust=240,piyasa_ev=.6,gercek_ev=None,gercek_dep=None)])
    maclar=pd.DataFrame([dict(lig='NBA',ev='WAS',dep='MIL',tarih_utc=pd.Timestamp('2026-10-22T00:00Z'),ev_skor=100,dep_skor=110),
                         dict(lig='NBA',ev='WAS',dep='MIL',tarih_utc=pd.Timestamp('2026-12-22T00:00Z'),ev_skor=130,dep_skor=90)])
    d=doldur(defter,maclar)
    assert (d.gercek_ev.iloc[0],d.gercek_dep.iloc[0])==(100,110)
    o=ozet(d)
    assert o['kazanan_isabet']==1.0 and o['piyasa_isabet']==0.0 and o['toplam_80_icinde']==1.0
