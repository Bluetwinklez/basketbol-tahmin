"""Kutu skorlardan maç öncesi tempo, verim ve kadro devamlılığı özellikleri.

Hücum sayısı (possession) = 2'lik deneme + 3'lük deneme − ofansif ribaund + top kaybı + 0,44 × serbest atış
denemesi (Dean Oliver'ın yaygın yaklaşımı). Tempo 40 dakikaya ölçeklenir; uzatmalı maçlar şişirmez.
build_features ile aynı kural: bir günün sonuçları, o günün bütün tahminleri üretildikten sonra işlenir.
Kutu skoru olmayan lig (NBA) için özellikler lig varsayılanında sabit kalır.
"""
from collections import defaultdict
from itertools import groupby
import numpy as np
import pandas as pd

# Kutu özelliklerinin kullanıldığı ligler: backtest'te fayda sağladığı ölçülenler.
# NBA: 2026-10-22 denemesinde log loss 0,6220 → 0,6227, toplam MAE 14,88 → 14,93 (kötüleşti), kapalı.
# E/U: log loss 0,5955 → 0,5965 ve 0,6129 → 0,6158 (kötüleşti); toplam MAE yalnız U'da 14,59 → 14,54. Kapalı.
# Sayı reytingleri tempo/verim bilgisinin çoğunu zaten taşıyor olabilir. Veri ve kod duruyor.
KUTU_LIGLERI = set()
KUTU_FEATURES = ['k_tempo', 'k_ortg_diff', 'k_drtg_diff', 'k_bek_toplam', 'k_bek_fark', 'k_kadro_diff', 'k_kadro_ort']
VARSAYILAN = dict(tempo=72., ortg=108., kadro=.5)   # hiç veri yokken kullanılan nötr değerler


def mac_tablosu(kutu):
    """kutu.parquet (iki satır/maç) → mac_id başına ev/dep hücum sayısı, sayı ve süre."""
    k = kutu.copy()
    k['hucum'] = k.fga2 + k.fga3 - k.oreb + k.tov + .44 * k.fta
    ev = k[k.rol == 'ev'].set_index('mac_id')
    dep = k[k.rol == 'dep'].set_index('mac_id')
    t = pd.DataFrame(dict(ev_hucum=ev.hucum, dep_hucum=dep.hucum, ev_say=ev.say, dep_say=dep.say,
                          sure=ev.sure.where(ev.sure > 0, 2400.)))
    return t.dropna()


def kutu_ozellikleri(games, kutu=None, oyuncular=None, alpha=.15):
    """games ile aynı sırada mac_id + KUTU_FEATURES tablosu döndürür."""
    maclar = mac_tablosu(kutu) if kutu is not None and len(kutu) else pd.DataFrame()
    dakika = {}
    if oyuncular is not None and len(oyuncular):
        for (mac, rol), g in oyuncular.groupby(['mac_id', 'rol']):
            dakika[(mac, rol)] = dict(zip(g.oyuncu, g.saniye))
    data = games.sort_values(['tarih_utc', 'mac_id'])
    gun = data.tarih_utc.dt.floor('D')
    durum = {}
    lig_tempo, lig_ortg, lig_kadro = {}, {}, defaultdict(lambda: [0., 0])
    out = []

    def takim(lig, ad, sezon):
        s = durum.setdefault((lig, ad), dict(tempo=None, ortg=None, drtg=None, sezon=sezon,
                                            onceki=set(), bu=defaultdict(float)))
        if s['sezon'] != sezon:
            # Yeni sezon: geçen sezon en az 100 dakika oynayanlar "dönen oyuncu" sayılır.
            s['onceki'] = {o for o, sn in s['bu'].items() if sn >= 6000}
            s['bu'], s['sezon'] = defaultdict(float), sezon
        return s

    for g_, satirlar in groupby(zip(data.itertuples(index=False), gun), key=lambda x: x[1]):
        bekleyen = []
        for row, _ in satirlar:
            h, a = takim(row.lig, row.ev, row.sezon), takim(row.lig, row.dep, row.sezon)
            lt = lig_tempo.get(row.lig, VARSAYILAN['tempo'])
            lo = lig_ortg.get(row.lig, VARSAYILAN['ortg'])
            th, ta = h['tempo'] or lt, a['tempo'] or lt
            oh, oa = h['ortg'] or lo, a['ortg'] or lo
            dh, da = h['drtg'] or lo, a['drtg'] or lo
            tempo = (th + ta) / 2
            ev_bek = tempo * (oh + da) / 2 / 100
            dep_bek = tempo * (oa + dh) / 2 / 100
            ks, kn = lig_kadro[row.lig]
            kv = ks / kn if kn else VARSAYILAN['kadro']

            def devamlilik(s):
                toplam = sum(s['bu'].values())
                if not toplam or not s['onceki']:
                    return kv
                return sum(sn for o, sn in s['bu'].items() if o in s['onceki']) / toplam
            ch, ca = devamlilik(h), devamlilik(a)
            out.append(dict(mac_id=row.mac_id, k_tempo=tempo, k_ortg_diff=oh - oa, k_drtg_diff=dh - da,
                            k_bek_toplam=ev_bek + dep_bek, k_bek_fark=ev_bek - dep_bek,
                            k_kadro_diff=ch - ca, k_kadro_ort=(ch + ca) / 2))
            bekleyen.append((row, h, a))
        for row, h, a in bekleyen:
            if row.mac_id not in maclar.index or pd.isna(row.ev_skor):
                continue
            m = maclar.loc[row.mac_id]
            hucum = (m.ev_hucum + m.dep_hucum) / 2
            if hucum <= 0:
                continue
            tempo = hucum * 2400 / m.sure
            for s, att, yed in ((h, m.ev_say, m.dep_say), (a, m.dep_say, m.ev_say)):
                ortg, drtg = 100 * att / hucum, 100 * yed / hucum
                s['tempo'] = tempo if s['tempo'] is None else s['tempo'] + alpha * (tempo - s['tempo'])
                s['ortg'] = ortg if s['ortg'] is None else s['ortg'] + alpha * (ortg - s['ortg'])
                s['drtg'] = drtg if s['drtg'] is None else s['drtg'] + alpha * (drtg - s['drtg'])
            lig_tempo[row.lig] = tempo if row.lig not in lig_tempo else lig_tempo[row.lig] + .01 * (tempo - lig_tempo[row.lig])
            lo = 100 * (m.ev_say + m.dep_say) / 2 / hucum
            lig_ortg[row.lig] = lo if row.lig not in lig_ortg else lig_ortg[row.lig] + .01 * (lo - lig_ortg[row.lig])
            for s, rol in ((h, 'ev'), (a, 'dep')):
                for o, sn in dakika.get((row.mac_id, rol), {}).items():
                    s['bu'][o] += sn
                toplam = sum(s['bu'].values())
                if toplam and s['onceki']:
                    oran = sum(sn for o, sn in s['bu'].items() if o in s['onceki']) / toplam
                    lig_kadro[row.lig][0] += oran
                    lig_kadro[row.lig][1] += 1
    return pd.DataFrame(out).set_index('mac_id').loc[games.mac_id].reset_index()


def yukle():
    """data/ altında varsa kutu ve oyuncu tablolarını döndürür, yoksa (None, None)."""
    from pathlib import Path
    kutular = [pd.read_parquet(p) for p in ('data/kutu.parquet', 'data/kutu_nba.parquet') if Path(p).exists()]
    if not kutular:
        return None, None
    oyuncular = [pd.read_parquet(p) for p in ('data/oyuncular.parquet', 'data/oyuncular_nba.parquet') if Path(p).exists()]
    return pd.concat(kutular, ignore_index=True), (pd.concat(oyuncular, ignore_index=True) if oyuncular else None)
