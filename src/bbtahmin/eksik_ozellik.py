"""NBA eksik oyuncu özelliği: maçta olmayan düzenli oyuncuların takım için değeri.

Oyuncu değeri yalnızca o maçtan ÖNCEKİ maçlardan hesaplanır:
- dakika: takımın her maçında üstel ortalama (oynamadığı maçta 0 ile güncellenir, böylece uzun süredir
  yok olan oyuncunun ağırlığı azalır; takım ona göre uyum sağlamıştır),
- değer: oynadığı maçlardaki 48 dakikaya ölçeklenmiş +/- değerinin üstel ortalaması × dakika payı.
"Düzenli oyuncu" = bu sezon takımda oynamış ve dakika ortalaması ≥ DUZENLI_DK olan oyuncu.

Eksik oyuncu kümesi:
- backtest'te: düzenli olup o maçın oyuncu listesinde olmayanlar. Bu bir YAKLAŞIMDIR: son dakika kadrodan
  çıkan oyuncular maç öncesinde biliniyormuş gibi sayılır (gerçek kullanımda sakatlık raporu daha az bilir).
- tahminde: resmi sakatlık raporundaki Out oyuncuları (sorgu başına dışarıdan verilir).
Sezon değişince kadro durumu sıfırlanır (yaz transferleri "eksik" sayılmasın). Takas edilen oyuncu yeni
takımında oynayınca eski takımının kadrosundan çıkarılır.
"""
from collections import defaultdict
from itertools import groupby
import pandas as pd

EKSIK_FEATURES = ['eksik_dk_diff', 'eksik_deger_diff', 'eksik_dk_top']
# Kullanıldığı ligler. NBA walk-forward (skor modeli): log loss 0,6220 → 0,6169, isabet %65,27 → %65,82,
# fark MAE 10,67 → 10,58; tamamlanmış 10 sezonun 10'unda iyileşti (2026-10-22).
# Actual participants are known only after tipoff. Keep this research helper,
# but do not use its retrospective labels in default training/live predictions.
EKSIK_LIGLERI = set()
DUZENLI_DK = 12.
ALPHA = .2


def eksik_ozellikleri(games, oyuncu_mac, sorgu_eksik=None):
    """games ile aynı sırada mac_id + EKSIK_FEATURES. sorgu_eksik: {mac_id: {takim_kodu: set(oyuncu_id)}}."""
    sorgu_eksik = sorgu_eksik or {}
    katilim = defaultdict(dict)   # (mac_id, rol) -> {oyuncu_id: (dakika, pm)}
    if oyuncu_mac is not None and len(oyuncu_mac):
        for r in oyuncu_mac.itertuples(index=False):
            if r.dakika and r.dakika > 0:
                katilim[(r.mac_id, r.rol)][r.oyuncu_id] = (float(r.dakika), float(r.pm))
    data = games.sort_values(['tarih_utc', 'mac_id'])
    gun = data.tarih_utc.dt.floor('D')
    kadro = defaultdict(dict)      # takım -> {oyuncu: dict(dk, deger)}
    sezon = {}
    takimi = {}                    # oyuncu -> son oynadığı takım
    son = {}                       # oyuncu -> bilinen son değer (sezon sıfırlamasından etkilenmez)
    out = []

    def eksik_toplam(takim, eksikler, rapordan=False):
        # Rapordan gelen oyuncu bu sezon henüz oynamadıysa (sezon başı, uzun sakatlık) son bilinen değeri
        # kullanılır: rapor oyuncunun bu takımda olduğunu zaten söylüyor. Backtest yolu bunu kullanmaz.
        k = kadro[takim]
        kaynak = lambda o: k.get(o) or (son.get(o) if rapordan else None)
        oyuncular = [kaynak(o) for o in eksikler if kaynak(o) and kaynak(o)['dk'] >= DUZENLI_DK]
        return sum(o['dk'] for o in oyuncular), sum(o['dk'] / 48 * o['deger'] for o in oyuncular)

    for _, satirlar in groupby(zip(data.itertuples(index=False), gun), key=lambda x: x[1]):
        bekleyen = []
        for row, _ in satirlar:
            for takim in (row.ev, row.dep):
                if sezon.get(takim) != row.sezon:
                    kadro[takim], sezon[takim] = {}, row.sezon
            rapordan = row.mac_id in sorgu_eksik
            if rapordan:
                ek_h = sorgu_eksik[row.mac_id].get(row.ev, set())
                ek_a = sorgu_eksik[row.mac_id].get(row.dep, set())
            else:
                ek_h = set(kadro[row.ev]) - set(katilim.get((row.mac_id, 'ev'), {}))
                ek_a = set(kadro[row.dep]) - set(katilim.get((row.mac_id, 'dep'), {}))
                # Oyuncu listesi hiç yoksa (eşleşmeyen maç) eksik bilinmiyor: 0 kabul edilir.
                if not katilim.get((row.mac_id, 'ev')):
                    ek_h = set()
                if not katilim.get((row.mac_id, 'dep')):
                    ek_a = set()
            dh, vh = eksik_toplam(row.ev, ek_h, rapordan)
            da, va = eksik_toplam(row.dep, ek_a, rapordan)
            out.append(dict(mac_id=row.mac_id, eksik_dk_diff=(dh - da) / 48, eksik_deger_diff=vh - va,
                            eksik_dk_top=(dh + da) / 48))
            bekleyen.append(row)
        for row in bekleyen:
            if pd.isna(row.ev_skor):
                continue
            for takim, rol in ((row.ev, 'ev'), (row.dep, 'dep')):
                oynayan = katilim.get((row.mac_id, rol), {})
                if not oynayan:
                    continue
                k = kadro[takim]
                for o, d in list(k.items()):
                    if o not in oynayan:
                        d['dk'] *= 1 - ALPHA
                for o, (dk, pm) in oynayan.items():
                    eski = takimi.get(o)
                    if eski and eski != takim:
                        kadro[eski].pop(o, None)
                    takimi[o] = takim
                    deger = pm * 48 / dk if dk >= 5 else 0.
                    if o not in k:
                        k[o] = dict(dk=dk, deger=deger)
                    else:
                        k[o]['dk'] += ALPHA * (dk - k[o]['dk'])
                        if dk >= 5:
                            k[o]['deger'] += ALPHA * (deger - k[o]['deger'])
                    son[o] = k[o]   # aynı nesne: sezon içi azalmalar da yansır
    return pd.DataFrame(out).set_index('mac_id').loc[games.mac_id].reset_index()


def yukle():
    from pathlib import Path
    yol = Path('data/nba_oyuncu_mac.parquet')
    return pd.read_parquet(yol) if yol.exists() else None


def _anahtar(ad):
    return ''.join(c for c in str(ad).casefold() if c.isalnum())


def rapor_eslestir(rapor, oyuncu_mac, takimlar, durumlar=('Out',)):
    """Sakatlık raporu satırlarını ('Beal,Bradley') oyuncu kimliklerine çevirir.
    Ad eşleşmesi tüm NBA oyuncuları arasında yapılır; aynı adlıda en son oynayan seçilir.
    Hiç NBA maçı olmayan (çaylak) oyuncular eşleşmez: geçmiş değerleri olmadığı için etkileri 0'dır.
    {takim: set(oyuncu_id)} ve eşleşmeyen adlar döner."""
    sonuc, eslesmeyen = {t: set() for t in takimlar}, []
    if rapor is None or oyuncu_mac is None or rapor.empty:
        return sonuc, eslesmeyen
    for r in rapor[rapor.durum.isin(durumlar) & rapor.takim.isin(takimlar)].itertuples():
        soyad, _, ad = r.oyuncu.partition(',')
        hedef = _anahtar(ad + soyad)
        aday = oyuncu_mac[oyuncu_mac.ad.map(_anahtar) == hedef]
        if aday.empty:
            eslesmeyen.append(r.oyuncu)
            continue
        sonuc[r.takim].add(aday.sort_values('mac_id').oyuncu_id.iloc[-1])
    return sonuc, eslesmeyen

