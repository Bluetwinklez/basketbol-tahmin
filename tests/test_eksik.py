import numpy as np
import pandas as pd
import pytest
from bbtahmin.eksik_ozellik import eksik_ozellikleri, EKSIK_FEATURES


def sahte_oyuncular(games):
    """Her takımda 8 oyuncu; bazı maçlarda yıldız (oyuncu 0) yok."""
    satirlar = []
    for i, r in enumerate(games.itertuples()):
        for rol, takim in (('ev', r.ev), ('dep', r.dep)):
            for j in range(8):
                if j == 0 and i % 5 == 3:
                    continue           # yıldız bu maçı kaçırıyor
                satirlar.append(dict(mac_id=r.mac_id, rol=rol, oyuncu_id=f'{takim}{j}', ad=f'{takim} {j}',
                                     dakika=36. - 3 * j, pm=float((i * 7 + j) % 11 - 5)))
    return pd.DataFrame(satirlar)


@pytest.mark.parametrize('position', [4, 8, 13, 18, 23])
def test_eksik_ozellik_gelecegi_kullanmaz(games, position):
    g = games[games.lig == 'NBA'].sort_values(['tarih_utc', 'mac_id']).reset_index(drop=True)
    om = sahte_oyuncular(g)
    hedef = g.iloc[position]
    tam = eksik_ozellikleri(g, om).set_index('mac_id').loc[hedef.mac_id]
    gecmis = g[g.tarih_utc < hedef.tarih_utc.floor('D')]
    kisa = pd.concat([gecmis, g[g.mac_id == hedef.mac_id].assign(ev_skor=np.nan, dep_skor=np.nan)], ignore_index=True)
    # Hedef maçın katılım listesi kalır (yaklaşımın parçası), sonraki maçların hiçbir verisi kalmaz.
    om2 = om[om.mac_id.isin(set(gecmis.mac_id) | {hedef.mac_id})]
    kesik = eksik_ozellikleri(kisa, om2).set_index('mac_id').loc[hedef.mac_id]
    pd.testing.assert_series_equal(tam[EKSIK_FEATURES], kesik[EKSIK_FEATURES], check_exact=True)


def test_yildiz_yoksa_eksik_artar(games):
    g = games[games.lig == 'NBA'].sort_values(['tarih_utc', 'mac_id']).reset_index(drop=True)
    f = eksik_ozellikleri(g, sahte_oyuncular(g)).set_index('mac_id')
    # i % 5 == 3 maçlarında yıldızlar yok. Takımın o sezonki ilk maçında kadro henüz bilinmediği için
    # her eksikli maç pozitif olmayabilir; ama eksiksiz maçlar mutlaka 0, eksiklilerden en az biri > 0.
    eksikli = [g.mac_id[i] for i in range(len(g)) if i % 5 == 3]
    eksiksiz = [m for m in g.mac_id if m not in eksikli]
    assert (f.loc[eksiksiz, 'eksik_dk_top'] == 0).all()
    assert (f.loc[eksikli, 'eksik_dk_top'] > 0).any()


def test_yeni_sezonda_ayrilan_oyuncu_eksik_sayilmaz():
    t = lambda d: pd.Timestamp(d, tz='UTC')
    games = pd.DataFrame([
        dict(mac_id='m1', lig='NBA', sezon='2020-21', tarih_utc=t('2021-03-01'), ev='A', dep='B', ev_skor=100, dep_skor=90),
        dict(mac_id='m2', lig='NBA', sezon='2021-22', tarih_utc=t('2021-10-20'), ev='A', dep='B', ev_skor=100, dep_skor=90)])
    om = pd.DataFrame([dict(mac_id='m1', rol='ev', oyuncu_id='eski', ad='', dakika=35., pm=5.),
                       dict(mac_id='m1', rol='dep', oyuncu_id='b1', ad='', dakika=35., pm=-5.),
                       dict(mac_id='m2', rol='ev', oyuncu_id='yeni', ad='', dakika=35., pm=5.),
                       dict(mac_id='m2', rol='dep', oyuncu_id='b1', ad='', dakika=35., pm=-5.)])
    f = eksik_ozellikleri(games, om).set_index('mac_id')
    assert f.loc['m2', 'eksik_dk_top'] == 0


def test_takas_edilen_oyuncu_eski_takimda_eksik_sayilmaz():
    t = lambda d: pd.Timestamp(d, tz='UTC')
    games = pd.DataFrame([
        dict(mac_id=f'm{i}', lig='NBA', sezon='2021-22', tarih_utc=t(f'2021-11-0{i}'), ev=ev, dep=dep, ev_skor=100, dep_skor=90)
        for i, (ev, dep) in enumerate([('A', 'B'), ('C', 'B'), ('A', 'D')], 1)])
    om = pd.DataFrame([dict(mac_id='m1', rol='ev', oyuncu_id='x', ad='', dakika=35., pm=5.),
                       dict(mac_id='m2', rol='ev', oyuncu_id='x', ad='', dakika=35., pm=5.),     # x C'ye takas edildi
                       dict(mac_id='m3', rol='ev', oyuncu_id='a2', ad='', dakika=30., pm=1.)])
    f = eksik_ozellikleri(games, om).set_index('mac_id')
    assert f.loc['m3', 'eksik_dk_diff'] == 0
