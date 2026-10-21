"""Gelecek maçlar için kazanma olasılığı, skor, fark ve toplam tahmini.

Yalnızca tahmin anından önce oynanmış maçlar kullanılır. Elo parametreleri ve EWMA
azalması backtest'in o lig için en son seçtiği değerlerdir (docs/kanit/parametreler.json).
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
from .ozellik import build_features
from .model import fit_predict, regression
from .takim_ad import coz

Z80 = norm.ppf(.9)  # %80 aralığın yarı genişliği (standart sapma cinsinden)
MODELLER = ('logistic', 'mov_elo', 'skor', 'topluluk', 'hist_gradient_boosting')
LIGLER = ('E', 'U', 'NBA')
LIG_ADI = {'E': 'EuroLeague', 'U': 'EuroCup', 'NBA': 'NBA'}


def sezon_adi(tarih):
    yil = tarih.year if tarih.month >= 7 else tarih.year - 1
    return f'{yil}-{str(yil + 1)[-2:]}'


def _son(kayitlar):
    return sorted(kayitlar, key=lambda r: r['sezon'])[-1] if kayitlar else None


def parametreler(lig, yol='docs/kanit/parametreler.json'):
    kayitlar = [r for r in json.loads(Path(yol).read_text('utf8')) if r.get('lig') == lig]
    mov = _son([r for r in kayitlar if r.get('model') == 'mov'])
    if not mov:
        raise ValueError(f'{lig} için doğrulanmış parametre yok; önce "python -m bbtahmin backtest" çalıştırın')
    ewma = _son([r for r in kayitlar if r.get('model') == 'ewma'])
    return mov, (ewma['alpha'] if ewma else .2)


def en_iyi_model(lig, yol='docs/kanit/toplam.csv'):
    """Backtest'te o ligde en düşük log loss'u veren model."""
    try:
        t = pd.read_csv(yol)
        t = t[(t.lig == lig) & t.model.isin(MODELLER)]
        return t.sort_values('log_loss').iloc[0].model if len(t) else 'topluluk'
    except (OSError, KeyError):
        return 'topluluk'


def aktif_kodlar(gecmis, lig, tarih, gun=400):
    """Son `gun` günde o ligde oynamış takımlar. Ligden ayrılmış takım (ör. 2022'den beri
    EuroLeague'de olmayan Zenit) eski reytingiyle tahmin edilmesin diye eşleşmez."""
    son = gecmis[(gecmis.lig == lig) & (gecmis.tarih_utc >= tarih - pd.Timedelta(days=gun))]
    return set(son.ev) | set(son.dep)


def lig_bul(ev, dep, gecmis, tarih):
    """Lig verilmediyse iki takımın da bulunduğu ligi seçer (EuroLeague önce)."""
    hatalar = []
    for lig in LIGLER:
        kodlar = aktif_kodlar(gecmis, lig, tarih)
        try:
            return lig, coz(lig, ev, kodlar), coz(lig, dep, kodlar)
        except ValueError as e:
            hatalar.append(f'{LIG_ADI[lig]}: {e}')
    raise ValueError('Takımlar desteklenen liglerde bulunamadı (EuroLeague, EuroCup, NBA).\n  ' + '\n  '.join(hatalar))


def tahmin_et(lig, eslesmeler, tarih, veri='data/maclar.parquet'):
    """eslesmeler: [(ev_kodu, dep_kodu)]. Her maç için sözlük döndürür."""
    tarih = pd.Timestamp(tarih)
    tarih = tarih.tz_localize('Europe/Istanbul') if tarih.tzinfo is None else tarih
    tarih = tarih.tz_convert('UTC')
    gecmis = pd.read_parquet(veri)
    gecmis = gecmis[(gecmis.lig == lig) & gecmis.ev_skor.notna() & gecmis.dep_skor.notna()
                    & (gecmis.tarih_utc < tarih.floor('D'))].copy()
    mov, alpha = parametreler(lig)
    sorgular = pd.DataFrame([dict(mac_id=f'SORGU_{i}', lig=lig, sezon=sezon_adi(tarih), tarih_utc=tarih,
                                  ev=ev, dep=dep, ev_skor=np.nan, dep_skor=np.nan, tarafsiz_saha=False)
                             for i, (ev, dep) in enumerate(eslesmeler)])
    hepsi = pd.concat([gecmis, sorgular], ignore_index=True)
    hepsi['tarih_utc'] = pd.to_datetime(hepsi.tarih_utc, utc=True)
    hepsi = hepsi.sort_values(['tarih_utc', 'mac_id']).reset_index(drop=True)
    x = build_features(hepsi, k=mov['k'], advantage=mov['home_advantage'], shrink=mov['shrink'],
                       alpha=alpha, mov=True)
    sorgu = hepsi.mac_id.str.startswith('SORGU_').to_numpy()
    y = (hepsi.ev_skor > hepsi.dep_skor).fillna(False).to_numpy(dtype=int)
    fark = (hepsi.ev_skor - hepsi.dep_skor).fillna(0).to_numpy(dtype=float)
    toplam = (hepsi.ev_skor + hepsi.dep_skor).fillna(0).to_numpy(dtype=float)
    # Doğrulama: en az 150 maçı olan son tamamlanmış sezon (süren sezonun ilk haftaları kalibrasyon için az).
    sayim = hepsi[~sorgu].sezon.value_counts()
    tam = sorted(s for s, n in sayim.items() if n >= 150 and s != sezon_adi(tarih))
    if not tam:
        raise ValueError(f'{lig}: kalibrasyon için tamamlanmış sezon yok')
    dogrulama = (hepsi.sezon == tam[-1]).to_numpy() & ~sorgu
    egitim = ~dogrulama & ~sorgu
    p_log, _ = fit_predict('logistic', x, y, egitim, dogrulama, sorgu)
    p_hgb, _ = fit_predict('hist_gradient_boosting', x, y, egitim, dogrulama, sorgu)
    pm, rm = regression(x, fark, egitim, dogrulama, sorgu)
    pt, rt = regression(x, toplam, egitim, dogrulama, sorgu)
    pt = pt + rt['residual_mean']  # skor seviyesi artışı için doğrulama sezonu sapma düzeltmesi
    sm, st = max(rm['residual_sigma'], 1e-6), max(rt['residual_sigma'], 1e-6)
    olasilik = {'logistic': p_log, 'hist_gradient_boosting': p_hgb,
                'mov_elo': x.loc[sorgu, 'elo_p'].to_numpy(), 'skor': norm.cdf(pm / sm)}
    olasilik['topluluk'] = np.mean([olasilik['logistic'], olasilik['mov_elo'], olasilik['skor']], axis=0)
    secilen = en_iyi_model(lig)
    mac_sayisi = pd.concat([gecmis.ev, gecmis.dep]).value_counts()
    # Sorgular sıralamada yer değiştirebilir (SORGU_10 < SORGU_2); konumu kimlikten bul.
    sira = list(hepsi.loc[sorgu, 'mac_id'])
    sonuc = []
    for n, (ev, dep) in enumerate(eslesmeler):
        i = sira.index(f'SORGU_{n}')
        p = float(olasilik[secilen][i])
        sonuc.append(dict(
            lig=lig, ev=ev, dep=dep, tarih_utc=tarih.isoformat(), model=secilen,
            ev_kazanir=p, ev_skor=float((pt[i] + pm[i]) / 2), dep_skor=float((pt[i] - pm[i]) / 2),
            fark=float(pm[i]), fark_80=(float(pm[i] - Z80 * sm), float(pm[i] + Z80 * sm)),
            toplam=float(pt[i]), toplam_80=(float(pt[i] - Z80 * st), float(pt[i] + Z80 * st)),
            tum_modeller={k: float(v[i]) for k, v in olasilik.items()},
            az_veri=[t for t in (ev, dep) if mac_sayisi.get(t, 0) < 10]))
    return sonuc


def alt_ust(t, cizgi):
    """Verilen toplam çizgisi için üst olasılığı (normal dağılım, %80 aralıktan sapma geri çıkarılır)."""
    sigma = (t['toplam_80'][1] - t['toplam']) / Z80
    return float(1 - norm.cdf((cizgi - t['toplam']) / sigma))


def yazdir(sonuclar, gosterim=None):
    for t in sonuclar:
        ev, dep = (gosterim or {}).get(t['ev'], t['ev']), (gosterim or {}).get(t['dep'], t['dep'])
        p = t['ev_kazanir']
        favori, fp = (ev, p) if p >= .5 else (dep, 1 - p)
        print(f"\n{LIG_ADI[t['lig']]}: {ev} – {dep}")
        print(f"  Kazanan:  {favori} %{fp * 100:.1f}   (ev %{p * 100:.1f} / dep %{(1 - p) * 100:.1f}, model: {t['model']})")
        print(f"  Skor:     {t['ev_skor']:.0f} – {t['dep_skor']:.0f}")
        print(f"  Fark:     {t['fark']:+.1f}  (%80 aralık {t['fark_80'][0]:+.0f} … {t['fark_80'][1]:+.0f})")
        print(f"  Toplam:   {t['toplam']:.1f}  (%80 aralık {t['toplam_80'][0]:.0f} … {t['toplam_80'][1]:.0f})")
        diger = ', '.join(f'{k} %{v * 100:.0f}' for k, v in t['tum_modeller'].items())
        print(f"  Modeller: {diger}")
        if t['az_veri']:
            print(f"  [!] Az geçmiş verisi olan takım: {', '.join(t['az_veri'])}; tahmin güvenilirliği düşük")


def run(lig, maclar, tarih, json_cikti=False):
    gecmis = pd.read_parquet('data/maclar.parquet')
    tarih = tarih or pd.Timestamp.now(tz='Europe/Istanbul').isoformat()
    an = pd.Timestamp(tarih)
    an = (an.tz_localize('Europe/Istanbul') if an.tzinfo is None else an).tz_convert('UTC')
    gruplar, gosterim, atlanan = {}, {}, []
    for mac in maclar:
        parca = [s.strip() for s in mac.replace('–', '-').split(' - ')]
        try:
            if len(parca) != 2:
                raise ValueError('"Ev - Deplasman" biçiminde olmalı')
            if lig:
                kodlar = aktif_kodlar(gecmis, lig, an)
                bulunan = (lig, coz(lig, parca[0], kodlar), coz(lig, parca[1], kodlar))
            else:
                bulunan = lig_bul(parca[0], parca[1], gecmis, an)
        except ValueError as e:
            atlanan.append((mac, str(e)))
            continue
        gosterim[bulunan[1]], gosterim[bulunan[2]] = parca
        gruplar.setdefault(bulunan[0], []).append(bulunan[1:])
    sonuclar = [t for l, es in gruplar.items() for t in tahmin_et(l, es, tarih)]
    if json_cikti:
        print(json.dumps(dict(tahminler=sonuclar, atlanan=atlanan), ensure_ascii=False, indent=2))
    else:
        yazdir(sonuclar, gosterim)
        for mac, neden in atlanan:
            print(f"\n[atlandı] {mac}\n  {neden}")
    return sonuclar
