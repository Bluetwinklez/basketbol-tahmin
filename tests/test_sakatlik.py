import time
from bbtahmin.veri.sakatlik import ayristir

METIN = """Injury Report: 10/21/26 05:00 PM
10/21/2026 07:00(ET) ATL@ORL AtlantaHawks Dennis,RayJ Questionable GLeague-Two-Way
Gueye,Mouhamed Out Injury/Illness-LeftFootFracture
OrlandoMagic Black,Anthony Out Injury/Illness-RightAnkleSprain
07:30(ET) CHA@BKN CharlotteHornets White,Coby Out Injury/Illness-LeftCalfStrain
BrooklynNets Bilodeau,Tyler Out Injury/Illness-RightShoulderSprain"""

def test_ayristir_takim_ve_mac_kodlari():
    t = ayristir(METIN)
    assert len(t) == 5
    assert t.iloc[0].to_dict() == dict(mac='ATL@ORL', takim='ATL', oyuncu='Dennis,RayJ', durum='Questionable', neden='GLeague-Two-Way')
    assert t.iloc[2].takim == 'ORL'
    # Rapordaki BKN/CHA, veri setindeki BRK/CHO kodlarına çevrilir.
    assert set(t[t.mac == 'CHO@BRK'].takim) == {'CHO', 'BRK'}

def test_uzun_satirda_takilmaz():
    satir = 'A' * 40 + ' ' + ' '.join(['kelime'] * 60)
    t0 = time.time()
    ayristir(f"ATL@ORL AtlantaHawks {satir}\n" * 50)
    assert time.time() - t0 < 2


def test_future_fixture_never_requests_a_future_injury_report(tmp_path,monkeypatch):
    import sys,types,urllib.error,re
    import pandas as pd
    from bbtahmin.veri import sakatlik
    urls=[]
    monkeypatch.setitem(sys.modules,'pdfplumber',types.SimpleNamespace())
    monkeypatch.setattr(sakatlik,'ONBELLEK',tmp_path)
    def missing(request,**kwargs):
        urls.append(request.full_url)
        raise urllib.error.HTTPError(request.full_url,404,'missing',None,None)
    monkeypatch.setattr('urllib.request.urlopen',missing)
    result=sakatlik.son_rapor(pd.Timestamp.now(tz='UTC')+pd.Timedelta(days=100),geriye_saat=.25)
    assert result.empty and len(urls)==1
    date=re.search(r'Injury-Report_(\d{4}-\d{2}-\d{2})_',urls[0])[1]
    assert date<=pd.Timestamp.now(tz='America/New_York').strftime('%Y-%m-%d')
