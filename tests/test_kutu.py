import numpy as np
import pandas as pd
import pytest
from bbtahmin.kutu_ozellik import kutu_ozellikleri, mac_tablosu, KUTU_FEATURES
from bbtahmin.veri.kutu import ayristir


def sahte_kutu(games):
    """Her maç için tutarlı ama maça göre değişen kutu skoru ve oyuncu dakikaları."""
    takim, oyuncu = [], []
    for i, r in enumerate(games.itertuples()):
        for rol, say, ad in (('ev', r.ev_skor, r.ev), ('dep', r.dep_skor, r.dep)):
            takim.append(dict(mac_id=r.mac_id, rol=rol, say=say, fga2=35 + i % 5, fga3=20 + i % 7, fta=15 + i % 4,
                              oreb=9 + i % 3, dreb=25, tov=12 + i % 6, faul=20, sure=2400.))
            for j in range(8):
                # Sezon içinde kadro değişsin: ikinci sezonda bazı oyuncular yeni.
                kod = f'{ad}{j if r.sezon == "2020-21" or j < 5 else j + 10}'
                oyuncu.append(dict(mac_id=r.mac_id, rol=rol, oyuncu=kod, saniye=1500. - 100 * j))
    return pd.DataFrame(takim), pd.DataFrame(oyuncu)


@pytest.mark.parametrize('league', ['E', 'U'])
@pytest.mark.parametrize('position', [3, 9, 15, 20])
def test_kutu_ozellikleri_gelecegi_kullanmaz(games, league, position):
    g = games[games.lig == league].sort_values(['tarih_utc', 'mac_id']).reset_index(drop=True)
    kutu, oyuncu = sahte_kutu(g)
    hedef = g.iloc[position]
    tam = kutu_ozellikleri(g, kutu, oyuncu).set_index('mac_id').loc[hedef.mac_id]
    gun = hedef.tarih_utc.floor('D')
    gecmis = g[g.tarih_utc < gun]
    sorgu = g[g.mac_id == hedef.mac_id].assign(ev_skor=np.nan, dep_skor=np.nan)
    kisa = pd.concat([gecmis, sorgu], ignore_index=True)
    k2 = kutu[kutu.mac_id.isin(gecmis.mac_id)]
    o2 = oyuncu[oyuncu.mac_id.isin(gecmis.mac_id)]
    kesik = kutu_ozellikleri(kisa, k2, o2).set_index('mac_id').loc[hedef.mac_id]
    pd.testing.assert_series_equal(tam[KUTU_FEATURES], kesik[KUTU_FEATURES], check_exact=True)


def test_kutu_yoksa_sabit_varsayilan(games):
    g = games[games.lig == 'NBA']
    f = kutu_ozellikleri(g, None, None)
    assert (f[KUTU_FEATURES].nunique() == 1).all()


def test_kadro_devamliligi_yeni_sezonda_duser(games):
    g = games[games.lig == 'E'].sort_values(['tarih_utc', 'mac_id']).reset_index(drop=True)
    kutu, oyuncu = sahte_kutu(g)
    f = kutu_ozellikleri(g, kutu, oyuncu).set_index('mac_id')
    ikinci = g[g.sezon == '2021-22'].mac_id
    # İkinci sezonun sonlarında devamlılık ölçülmüş olmalı ve %100'ün altında kalmalı (3 yeni oyuncu).
    assert f.loc[ikinci.iloc[-1], 'k_kadro_ort'] < 1


def test_hucum_sayisi_formulu():
    k = pd.DataFrame([dict(mac_id='E1', rol='ev', say=80, fga2=40, fga3=20, fta=20, oreb=10, dreb=25, tov=12, faul=20, sure=2400.),
                      dict(mac_id='E1', rol='dep', say=70, fga2=38, fga3=22, fta=10, oreb=8, dreb=24, tov=15, faul=22, sure=2400.)])
    t = mac_tablosu(k).loc['E1']
    assert t.ev_hucum == pytest.approx(40 + 20 - 10 + 12 + .44 * 20)
    assert t.dep_hucum == pytest.approx(38 + 22 - 8 + 15 + .44 * 10)


def test_ayristir_bos_yanit():
    assert ayristir('E2020_1', None) == ([], [])
    assert ayristir('E2020_1', {'local': {}, 'road': {}}) == ([], [])
