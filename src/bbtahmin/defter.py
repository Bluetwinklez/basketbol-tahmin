"""Tahmin defteri: maç öncesi tahminleri zaman damgasıyla saklar, sonuç gelince puanlar.

defter/tahminler.csv git'e girer; böylece bir tahminin maçtan önce yapıldığı commit geçmişinden görülür.
"""
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

YOL = Path('defter/tahminler.csv')


def kaydet(sonuclar, yol=YOL):
    simdi = datetime.now(timezone.utc).isoformat(timespec='seconds')
    yeni = pd.DataFrame([dict(
        kayit_utc=simdi, lig=t['lig'], mac_utc=t['tarih_utc'], ev=t['ev'], dep=t['dep'], model=t['model'],
        ev_kazanir=round(t['ev_kazanir'], 4), ev_skor=round(t['ev_skor'], 1), dep_skor=round(t['dep_skor'], 1),
        fark=round(t['fark'], 1), toplam=round(t['toplam'], 1),
        toplam_80_alt=round(t['toplam_80'][0]), toplam_80_ust=round(t['toplam_80'][1]),
        oran_ev=t.get('oran_ev'), oran_dep=t.get('oran_dep'),
        piyasa_ev=round(t['piyasa_ev'], 4) if t.get('piyasa_ev') is not None else None,
        uzatma=round(t.get('uzatma', np.nan), 4),
        eksik_ev=sum(o['takim'] == t['ev'] and o['durum'] == 'Out' for o in t.get('sakatlik', [])),
        eksik_dep=sum(o['takim'] == t['dep'] and o['durum'] == 'Out' for o in t.get('sakatlik', [])),
        gercek_ev=None, gercek_dep=None) for t in sonuclar])
    yol.parent.mkdir(exist_ok=True)
    eski = pd.read_csv(yol) if yol.exists() else pd.DataFrame()
    pd.concat([eski, yeni], ignore_index=True).to_csv(yol, index=False)
    return len(yeni)


def doldur(defter, maclar):
    """Gerçek skoru boş satırları, aynı lig/takımlar ve ±36 saat içindeki oynanmış maçla doldurur."""
    oynanan = maclar[maclar.ev_skor.notna()].copy()
    oynanan['tarih_utc'] = pd.to_datetime(oynanan.tarih_utc, utc=True)
    for i, r in defter[defter.gercek_ev.isna()].iterrows():
        an = pd.Timestamp(r.mac_utc)
        aday = oynanan[(oynanan.lig == r.lig) & (oynanan.ev == r.ev) & (oynanan.dep == r.dep)
                       & ((oynanan.tarih_utc - an).abs() <= pd.Timedelta(hours=36))]
        if len(aday):
            defter.loc[i, ['gercek_ev', 'gercek_dep']] = aday.iloc[0][['ev_skor', 'dep_skor']].to_numpy(dtype=float)
    return defter


def espn_doldur(defter):
    """NBA satırlarını ESPN skor tablosundan doldurur (yalnızca bitmiş maçlar).
    Basketball Reference sayfaları önbellekte olduğu için süren gecenin sonuçlarını göstermez."""
    import json
    import urllib.request
    from .veri.nba_kutu import ESPN_KOD
    bos = defter[(defter.lig == 'NBA') & defter.gercek_ev.isna()]
    gunler = {pd.Timestamp(t).tz_convert('America/New_York').strftime('%Y%m%d') for t in bos.mac_utc}
    for gun in gunler:
        try:
            istek = urllib.request.Request(f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={gun}',
                                           headers={'User-Agent': 'bbtahmin/0.1'})
            with urllib.request.urlopen(istek, timeout=20) as y:
                olaylar = json.load(y)['events']
        except Exception:
            continue
        for e in olaylar:
            c = e['competitions'][0]
            if c['status']['type']['name'] != 'STATUS_FINAL':
                continue
            t = {x['homeAway']: (ESPN_KOD.get(x['team']['abbreviation'], x['team']['abbreviation']), float(x['score']))
                 for x in c['competitors']}
            satir = bos[(bos.ev == t['home'][0]) & (bos.dep == t['away'][0])].index
            defter.loc[satir, ['gercek_ev', 'gercek_dep']] = [t['home'][1], t['away'][1]]
    return defter


def bdl_doldur(defter):
    """ESPN'in dolduramadığı NBA satırları için yedek kaynak: balldontlie (BALLDONTLIE_API_KEY gerekir).
    Anahtar yalnızca ortam değişkeninden okunur; yoksa sessizce atlanır."""
    import json
    import os
    import urllib.request
    anahtar = os.environ.get('BALLDONTLIE_API_KEY')
    if not anahtar:
        try:   # setx ile kaydedilen değer açık oturuma yansımamış olabilir
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as k:
                anahtar = winreg.QueryValueEx(k, 'BALLDONTLIE_API_KEY')[0]
        except Exception:
            return defter
    kod = {'BKN': 'BRK', 'CHA': 'CHO', 'PHX': 'PHO'}
    bos = defter[(defter.lig == 'NBA') & defter.gercek_ev.isna()]
    for gun in {pd.Timestamp(t).tz_convert('America/New_York').strftime('%Y-%m-%d') for t in bos.mac_utc}:
        try:
            istek = urllib.request.Request(f'https://api.balldontlie.io/v1/games?dates[]={gun}&per_page=100',
                                           headers={'Authorization': anahtar, 'User-Agent': 'bbtahmin/0.1'})
            with urllib.request.urlopen(istek, timeout=20) as y:
                maclar = json.load(y)['data']
        except Exception:
            continue
        for m in maclar:
            if m.get('status') != 'Final':
                continue
            ev = kod.get(m['home_team']['abbreviation'], m['home_team']['abbreviation'])
            dep = kod.get(m['visitor_team']['abbreviation'], m['visitor_team']['abbreviation'])
            satir = bos[(bos.ev == ev) & (bos.dep == dep)].index
            defter.loc[satir, ['gercek_ev', 'gercek_dep']] = [float(m['home_team_score']), float(m['visitor_team_score'])]
    return defter


def ozet(defter):
    d = defter.dropna(subset=['gercek_ev']).copy()
    if d.empty:
        return None
    y = (d.gercek_ev > d.gercek_dep).astype(int)
    p = d.ev_kazanir.clip(1e-6, 1 - 1e-6)
    toplam = d.gercek_ev + d.gercek_dep
    sonuc = dict(mac=len(d), kazanan_isabet=float(((p >= .5) == (y == 1)).mean()),
                 log_loss=float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()),
                 fark_mae=float((d.fark - (d.gercek_ev - d.gercek_dep)).abs().mean()),
                 toplam_mae=float((d.toplam - toplam).abs().mean()),
                 toplam_80_icinde=float(((toplam >= d.toplam_80_alt) & (toplam <= d.toplam_80_ust)).mean()))
    m = d.dropna(subset=['piyasa_ev'])
    if len(m):
        ym, pm = (m.gercek_ev > m.gercek_dep).astype(int), m.piyasa_ev.clip(1e-6, 1 - 1e-6)
        pmod = m.ev_kazanir.clip(1e-6, 1 - 1e-6)
        sonuc.update(piyasali_mac=len(m),
                     piyasa_isabet=float(((pm >= .5) == (ym == 1)).mean()),
                     piyasa_log_loss=float(-(ym * np.log(pm) + (1 - ym) * np.log(1 - pm)).mean()),
                     model_log_loss_ayni_maclar=float(-(ym * np.log(pmod) + (1 - ym) * np.log(1 - pmod)).mean()))
    return sonuc


def run(yol=YOL):
    if not yol.exists():
        print('Defter boş.')
        return
    defter = bdl_doldur(espn_doldur(doldur(pd.read_csv(yol), pd.read_parquet('data/maclar.parquet'))))
    defter.to_csv(yol, index=False)
    for r in defter.itertuples():
        fav, fp = (r.ev, r.ev_kazanir) if r.ev_kazanir >= .5 else (r.dep, 1 - r.ev_kazanir)
        if pd.isna(r.gercek_ev):
            durum = 'sonuç bekleniyor'
        else:
            kazanan = r.ev if r.gercek_ev > r.gercek_dep else r.dep
            top = r.gercek_ev + r.gercek_dep
            durum = (f"{r.gercek_ev:.0f}-{r.gercek_dep:.0f} | kazanan {'TUTTU' if kazanan == fav else 'tutmadı'}"
                     f" | toplam {top:.0f} ({'aralıkta' if r.toplam_80_alt <= top <= r.toplam_80_ust else 'aralık dışı'})")
        print(f"{str(r.mac_utc)[:16]} {r.lig} {r.ev}-{r.dep}: {fav} %{fp * 100:.0f}, toplam {r.toplam} → {durum}")
    o = ozet(defter)
    if o:
        print('\nÖzet:', ', '.join(f'{k}={v:.3f}' if isinstance(v, float) else f'{k}={v}' for k, v in o.items()))
