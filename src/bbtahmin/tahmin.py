"""Gelecek maçlar için kazanma olasılığı, skor, fark ve toplam tahmini.

Yalnızca tahmin anından önce oynanmış maçlar kullanılır. Elo parametreleri ve EWMA
azalması backtest'in o lig için en son seçtiği değerlerdir (docs/kanit/parametreler.json).
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
from .ozellik import build_features, FEATURES
from .kutu_ozellik import kutu_ozellikleri, yukle, KUTU_FEATURES, KUTU_LIGLERI
from .eksik_ozellik import eksik_ozellikleri, rapor_eslestir, EKSIK_FEATURES, EKSIK_LIGLERI, yukle as eksik_yukle
from .model import fit_predict, regression
from .takim_ad import coz

Z80 = norm.ppf(.9)  # %80 aralığın yarı genişliği (standart sapma cinsinden)
MODELLER = ('logistic', 'mov_elo', 'skor', 'topluluk', 'hist_gradient_boosting')
LIGLER = ('E', 'U', 'NBA', 'NBL')
LIG_ADI = {'E': 'EuroLeague', 'U': 'EuroCup', 'NBA': 'NBA', 'NBL': 'Avustralya NBL'}


def sezon_adi(tarih):
    yil = tarih.year if tarih.month >= 7 else tarih.year - 1
    return f'{yil}-{str(yil + 1)[-2:]}'


def _son(kayitlar):
    return sorted(kayitlar, key=lambda r: r['sezon'])[-1] if kayitlar else None


def parametreler(lig, yol='docs/kanit/parametreler.json', sezon=None):
    if str(yol)=='docs/kanit/parametreler.json':
        from .artifacts import require_verified_path
        yol=require_verified_path('parametreler.json')
    kayitlar = [r for r in json.loads(Path(yol).read_text('utf8')) if r.get('lig') == lig]
    if sezon is not None:
        kayitlar = [r for r in kayitlar if r['sezon'] <= sezon]
    mov = _son([r for r in kayitlar if r.get('model') == 'mov'])
    if not mov:
        raise ValueError(f'{lig} için doğrulanmış parametre yok; önce "python -m bbtahmin backtest" çalıştırın')
    ewma = _son([r for r in kayitlar if r.get('model') == 'ewma'])
    return mov, (ewma['alpha'] if ewma else .2)


def en_iyi_model(lig, yol='docs/kanit/toplam.csv', sezon=None):
    """Backtest'te o ligde en düşük log loss'u veren model."""
    if str(yol)=='docs/kanit/toplam.csv':
        # Derive choices from checksummed metrics, never an unsigned aggregate
        # or legacy participation-enhanced evaluation after an integrity failure.
        from .artifacts import require_verified_path
        metrics=pd.read_csv(require_verified_path('metrikler.csv'))
        metrics=metrics[(metrics.lig==lig) & metrics.model.isin(MODELLER)]
        if sezon is not None:
            metrics=metrics[metrics.sezon<sezon]
        if metrics.empty:
            return 'mov_elo'
        losses=metrics.assign(weighted=metrics.log_loss*metrics.n).groupby('model')[['weighted','n']].sum()
        return (losses.weighted/losses.n).idxmin()
    try:
        if sezon is not None:
            # Aggregate test results may include the target season. Model choice
            # for a historical query can use only earlier completed seasons.
            metrics = pd.read_csv(Path(yol).with_name('metrikler.csv'))
            metrics = metrics[(metrics.lig == lig) & (metrics.sezon < sezon) & metrics.model.isin(MODELLER)]
            if metrics.empty:
                return 'mov_elo'
            losses = metrics.assign(weighted=metrics.log_loss * metrics.n).groupby('model')[['weighted','n']].sum()
            return (losses.weighted / losses.n).idxmin()
        t = pd.read_csv(yol)
        t = t[(t.lig == lig) & t.model.isin(MODELLER)]
        return t.sort_values('log_loss').iloc[0].model if len(t) else 'topluluk'
    except (OSError, KeyError):
        return 'mov_elo' if sezon is not None else 'topluluk'


def aktif_kodlar(gecmis, lig, tarih, gun=400):
    """Son `gun` günde o ligde oynamış takımlar. Ligden ayrılmış takım (ör. 2022'den beri
    EuroLeague'de olmayan Zenit) eski reytingiyle tahmin edilmesin diye eşleşmez."""
    son = gecmis[(gecmis.lig == lig) & (gecmis.tarih_utc >= tarih - pd.Timedelta(days=gun))
                 & (gecmis.tarih_utc < tarih)]
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


def tahmin_et(lig, eslesmeler, tarih, veri='data/maclar.parquet', rapor=None):
    """eslesmeler: [(ev_kodu, dep_kodu)]. rapor: NBA sakatlık raporu (Out oyuncuları eksik sayılır)."""
    tarih = pd.Timestamp(tarih)
    tarih = tarih.tz_localize('Europe/Istanbul') if tarih.tzinfo is None else tarih
    tarih = tarih.tz_convert('UTC')
    gecmis = pd.read_parquet(veri)
    gecmis = gecmis[(gecmis.lig == lig) & (gecmis.ev_skor > 0) & (gecmis.dep_skor > 0)
                    & (gecmis.tarih_utc < tarih.floor('D'))].copy()
    mov, alpha = parametreler(lig, sezon=sezon_adi(tarih))
    sorgular = pd.DataFrame([dict(mac_id=f'SORGU_{i}', lig=lig, sezon=sezon_adi(tarih), tarih_utc=tarih,
                                  ev=ev, dep=dep, ev_skor=np.nan, dep_skor=np.nan, tarafsiz_saha=False)
                             for i, (ev, dep) in enumerate(eslesmeler)])
    hepsi = pd.concat([gecmis, sorgular], ignore_index=True)
    hepsi['tarih_utc'] = pd.to_datetime(hepsi.tarih_utc, utc=True)
    hepsi = hepsi.sort_values(['tarih_utc', 'mac_id']).reset_index(drop=True)
    x = build_features(hepsi, k=mov['k'], advantage=mov['home_advantage'], shrink=mov['shrink'],
                       alpha=alpha, mov=True)
    cols = list(FEATURES)
    x = x.reset_index(drop=True)
    kutu, oyuncular = yukle() if lig in KUTU_LIGLERI else (None,None)
    if kutu is not None and lig in KUTU_LIGLERI and kutu.mac_id.str.startswith(lig).any():
        kf = kutu_ozellikleri(hepsi, kutu, oyuncular).set_index('mac_id').loc[hepsi.mac_id].reset_index(drop=True)
        x = pd.concat([x, kf[KUTU_FEATURES]], axis=1)
        cols += KUTU_FEATURES
    oyuncu_mac = eksik_yukle() if lig in EKSIK_LIGLERI else None
    eksik_bilgi = {}
    if oyuncu_mac is not None and lig in EKSIK_LIGLERI:
        sorgu_eksik = {}
        for i, (ev, dep) in enumerate(eslesmeler):
            kume, eslesmeyen = rapor_eslestir(rapor, oyuncu_mac, [ev, dep])
            sorgu_eksik[f'SORGU_{i}'] = kume
            eksik_bilgi[i] = eslesmeyen
        ef = eksik_ozellikleri(hepsi, oyuncu_mac, sorgu_eksik).set_index('mac_id').loc[hepsi.mac_id].reset_index(drop=True)
        x = pd.concat([x, ef[EKSIK_FEATURES]], axis=1)
        cols += EKSIK_FEATURES
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
    # Current-season results must not train a model whose calibration holdout
    # is the preceding season. Match the chronological backtest split.
    egitim = (hepsi.sezon < tam[-1]).to_numpy() & ~sorgu
    p_log, _ = fit_predict('logistic', x, y, egitim, dogrulama, sorgu, cols)
    p_hgb, _ = fit_predict('hist_gradient_boosting', x, y, egitim, dogrulama, sorgu, cols)
    pm, rm = regression(x, fark, egitim, dogrulama, sorgu, cols)
    pt, rt = regression(x, toplam, egitim, dogrulama, sorgu, cols)
    pt = pt + rt['residual_mean']  # skor seviyesi artışı için doğrulama sezonu sapma düzeltmesi
    sm, st = max(rm['residual_sigma'], 1e-6), max(rt['residual_sigma'], 1e-6)
    olasilik = {'logistic': p_log, 'hist_gradient_boosting': p_hgb,
                'mov_elo': x.loc[sorgu, 'elo_p'].to_numpy(), 'skor': norm.cdf(pm / sm)}
    olasilik['topluluk'] = np.mean([olasilik['logistic'], olasilik['mov_elo'], olasilik['skor']], axis=0)
    secilen = en_iyi_model(lig, sezon=sezon_adi(tarih))
    # Uzatma olasılığı: normal süre farkının 0 olma yoğunluğu, ligin geçmiş uzatma oranına ölçeklenir.
    # Ölçek için tüm maçların fark dağılımı kullanılır (tahmin ve artık dağılımlarının toplamı).
    gecmis_fark = fark[~sorgu]
    uz_orani = float(hepsi.loc[~sorgu, 'uzatma'].fillna(False).astype(bool).mean()) if 'uzatma' in hepsi else 0.
    olcek = uz_orani / max(norm.pdf(0, gecmis_fark.mean(), gecmis_fark.std()), 1e-9)
    mac_sayisi = pd.concat([gecmis.ev, gecmis.dep]).value_counts()
    # Sorgular sıralamada yer değiştirebilir (SORGU_10 < SORGU_2); konumu kimlikten bul.
    sira = list(hepsi.loc[sorgu, 'mac_id'])
    sonuc = []
    from .artifacts import status
    artifact_status=status(dataset=veri)
    for n, (ev, dep) in enumerate(eslesmeler):
        i = sira.index(f'SORGU_{n}')
        p = float(olasilik[secilen][i])
        sonuc.append(dict(
            lig=lig, ev=ev, dep=dep, tarih_utc=tarih.isoformat(), model=secilen,
            ev_kazanir=p, ev_skor=float((pt[i] + pm[i]) / 2), dep_skor=float((pt[i] - pm[i]) / 2),
            fark=float(pm[i]), fark_80=(float(pm[i] - Z80 * sm), float(pm[i] + Z80 * sm)),
            toplam=float(pt[i]), toplam_80=(float(pt[i] - Z80 * st), float(pt[i] + Z80 * st)),
            tum_modeller={k: float(v[i]) for k, v in olasilik.items()},
            artifact_status=artifact_status,
            uzatma=float(np.clip(olcek * norm.pdf(0, pm[i], sm), 0, .5)),
            eksik_dk=(float(x.loc[np.flatnonzero(sorgu)[i], 'eksik_dk_diff']) * 48) if 'eksik_dk_diff' in x else None,
            eksik_eslesmeyen=eksik_bilgi.get(n, []),
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
        if 'secildi' in t:
            print(f"  Güven eşiği: %{t['guven_esigi']*100:.0f} — {'geçti' if t['secildi'] else 'eşik altında'}")
        print(f"  Skor:     {t['ev_skor']:.0f} – {t['dep_skor']:.0f}")
        print(f"  Fark:     {t['fark']:+.1f}  (%80 aralık {t['fark_80'][0]:+.0f} … {t['fark_80'][1]:+.0f})")
        print(f"  Toplam:   {t['toplam']:.1f}  (%80 aralık {t['toplam_80'][0]:.0f} … {t['toplam_80'][1]:.0f})")
        print(f"  Uzatma:   %{t['uzatma'] * 100:.1f}")
        if t.get('piyasa_ev') is not None:
            pe = t['piyasa_ev']
            print(f"  Piyasa:   ev %{pe * 100:.1f} / dep %{(1 - pe) * 100:.1f}  (oranlar {t['oran_ev']} / {t['oran_dep']}, marj çıkarıldı)")
        if t.get('eksik_dk') is not None:
            print(f"  Eksik etkisi: ev − dep eksik dakika farkı {t['eksik_dk']:+.0f} dk (modele dahil)")
        for kod in (t['ev'], t['dep']):
            eksik = [f"{o['oyuncu']} ({o['durum']})" for o in t.get('sakatlik', []) if o['takim'] == kod]
            if eksik:
                print(f"  Eksik {(gosterim or {}).get(kod, kod)}: {', '.join(eksik)}")
        diger = ', '.join(f'{k} %{v * 100:.0f}' for k, v in t['tum_modeller'].items())
        print(f"  Modeller: {diger}")
        if t['az_veri']:
            print(f"  [!] Az geçmiş verisi olan takım: {', '.join(t['az_veri'])}; tahmin güvenilirliği düşük")


def oran_ayir(mac):
    """'Ev - Dep @1.30/2.14' → ('Ev - Dep', 1.30, 2.14). Oran yoksa None."""
    if '@' not in mac:
        return mac, None, None
    metin, oran = mac.rsplit('@', 1)
    parca = [o.strip().replace(',', '.') for o in oran.split('/')]
    if len(parca) != 2:
        raise ValueError('Oranlar @ev/deplasman biçiminde iki değer olmalı')
    sayi = lambda o: float(o) if o and o not in ('-', '?') else None
    values = [sayi(o) for o in parca]
    from .odds import decimal_probability
    for value in values:
        if value is not None:
            decimal_probability(value)
    return metin.strip(), *values


def run(lig, maclar, tarih, json_cikti=False, kaydet=False, injury_report=False, confidence_threshold=None):
    if confidence_threshold is not None and (not np.isfinite(confidence_threshold) or not .5<=confidence_threshold<=1):
        raise ValueError('Confidence threshold must be between 0.5 and 1')
    gecmis = pd.read_parquet('data/maclar.parquet')
    tarih = tarih or pd.Timestamp.now(tz='Europe/Istanbul').isoformat()
    an = pd.Timestamp(tarih)
    an = (an.tz_localize('Europe/Istanbul') if an.tzinfo is None else an).tz_convert('UTC')
    gruplar, gosterim, atlanan, oranlar = {}, {}, [], {}
    for mac in maclar:
        try:
            mac, o1, o2 = oran_ayir(mac)
            parca = [s.strip() for s in mac.replace('–', '-').split(' - ')]
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
        oranlar[bulunan[1:]] = (o1, o2)
        gruplar.setdefault(bulunan[0], []).append(bulunan[1:])
    rapor = None
    if 'NBA' in gruplar and injury_report:
        from .veri.sakatlik import son_rapor
        try:
            rapor = son_rapor(an)
        except Exception as e:  # rapor alınamazsa tahmin eksiksiz kadro varsayımıyla verilir
            import sys
            print(f'[!] Sakatlık raporu alınamadı: {e}',file=sys.stderr)
    sonuclar = [t for l, es in gruplar.items() for t in tahmin_et(l, es, tarih, rapor=rapor if l == 'NBA' else None)]
    for t in sonuclar:
        if confidence_threshold is not None:
            t['guven_esigi']=confidence_threshold
            t['secildi']=max(t['ev_kazanir'],1-t['ev_kazanir'])>=confidence_threshold
        o1, o2 = oranlar.get((t['ev'], t['dep']), (None, None))
        t['oran_ev'], t['oran_dep'] = o1, o2
        t['piyasa_ev'] = (1 / o1) / (1 / o1 + 1 / o2) if o1 and o2 else None
        if rapor is not None and t['lig'] == 'NBA':
            ilgili = rapor[rapor.takim.isin([t['ev'], t['dep']]) & rapor.durum.isin(['Out', 'Doubtful', 'Questionable'])]
            t['sakatlik'] = ilgili[['takim', 'oyuncu', 'durum']].to_dict('records')
            t['sakatlik_raporu'] = rapor.attrs.get('rapor')
    if kaydet and sonuclar:
        from .defter import kaydet as defter_kaydet
        import sys
        print(f'[defter] {defter_kaydet(sonuclar)} tahmin kaydedildi: defter/tahminler.csv',
              file=sys.stderr if json_cikti else sys.stdout)
    if json_cikti:
        print(json.dumps(dict(tahminler=sonuclar, atlanan=atlanan), ensure_ascii=False, indent=2))
    else:
        yazdir(sonuclar, gosterim)
        for mac, neden in atlanan:
            print(f"\n[atlandı] {mac}\n  {neden}")
    return sonuclar
