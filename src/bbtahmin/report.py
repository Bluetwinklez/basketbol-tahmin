from xml.etree import ElementTree
import json
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd

def markdown(df):
    def fmt(v):
        if isinstance(v,(list,dict)): return json.dumps(v,ensure_ascii=False)
        if pd.isna(v):return '—'
        return f'{v:.4f}' if isinstance(v,(float,np.floating)) else str(v).replace('|','/')
    return '| '+' | '.join(map(str,df.columns))+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join('| '+' | '.join(fmt(v) for v in row)+' |' for row in df.itertuples(index=False,name=None))

def significance(pred):
    records=[]
    rng=np.random.default_rng(42)
    for league,g in pred.groupby('lig'):
        elo=g[g.model=='elo'][['mac_id','sezon','y','p']].rename(columns={'p':'elo'})
        for model in ['logistic','hist_gradient_boosting','mov_elo']:
            both=g[g.model==model].merge(elo,on=['mac_id','sezon','y'],validate='one_to_one')
            loss=lambda p: -(both.y*np.log(np.clip(p,1e-6,1-1e-6))+(1-both.y)*np.log(np.clip(1-p,1e-6,1-1e-6)))
            both['delta']=loss(both.p)-loss(both.elo)
            d=both.groupby('sezon').delta.mean().to_numpy()
            if len(d)<2:continue
            boot=rng.choice(d,size=(10000,len(d)),replace=True).mean(axis=1)
            signs=rng.choice([-1,1],size=(10000,len(d)))
            p=(1+np.sum(abs((signs*d).mean(axis=1))>=abs(d.mean())))/10001
            records.append(dict(lig=league,model=model,seasons=len(d),mean_season_logloss_delta=float(d.mean()),
                ci_low=float(np.quantile(boot,.025)),ci_high=float(np.quantile(boot,.975)),p=float(p)))
    result=pd.DataFrame(records)
    if len(result):
        result['p_holm']=np.nan
        for _,part in result.groupby('lig'):
            order=part.p.sort_values().index
            adjusted=np.maximum.accumulate([(len(part)-i)*part.p[index] for i,index in enumerate(order)])
            result.loc[order,'p_holm']=np.minimum(adjusted,1)
    return result

RUN_COMMANDS=['python .runtime/run.py -m bbtahmin topla --ligler NBA --baslangic 2016 --bitis 2025',
    'python .runtime/run.py -m bbtahmin backtest',
    'python .runtime/run.py -m pytest -q -p no:cacheprovider tests --junitxml=docs/kanit/pytest.xml',
    'python .runtime/run.py -m pytest -q -p no:cacheprovider tests/negative_control.py --junitxml=docs/kanit/negatif_kontrol.xml',
    '# .runtime/run.py: sistem CPython 3.12.10 + .venv site-packages (eşdeğeri: .venv/Scripts/python.exe -m bbtahmin ...)',
    '# E/U ve NBA 2014-15, 2015-16 ham yanıtları önceki koşudan önbellekte (data/raw); yeniden indirilmedi.']

def odds_section(folder,collection):
    lines=['## NBA piyasa kıyası ve bahis simülasyonu','']
    unmatched=collection.get('unmatched_odds_rows')
    if (folder/'piyasa.csv').exists():
        market=pd.read_csv(folder/'piyasa.csv')
        bets=pd.read_csv(folder/'bahis.csv')
        lines += ['Aynı maç alt kümesinde model ve vig\'i çıkarılmış kapanış olasılığı:','',markdown(market),'',
            'Bahis simülasyonu (eşik yalnız önceki sezonların walk-forward tahminlerinden; sabit pay=%1 güncel sermaye, çeyrek Kelly):','',
            markdown(bets),'',
            f"Eşleşmeyen oran satırı: {unmatched['count']} / {unmatched['total']}; nedenler: {json.dumps(unmatched['reasons'],ensure_ascii=False)}.",'']
    else:
        lines += ['**Yapılmadı.** NBA piyasa kıyası, eğitimde avantaj eşiği seçimi, ROI / en büyük düşüş / bahis sayısı hesaplanmadı: '
            'kapanış oranı kullanılmadı. Sportsbook Reviews Online arşivi robots.txt ile izinli ve 2014-15…2022-23 sayfaları oran tablosu içeriyor; '
            'ancak sitenin Terms sayfası "içerik yazılı izin olmadan kullanılamaz veya çoğaltılamaz" diyor. Görev kullanım şartlarına uymayı istediği için '
            'oranlar ayrıştırılmadı. İzin alındığında `python -m bbtahmin topla --ligler NBA --baslangic 2014 --sbr-izni` ve ardından `backtest` ile '
            'bu bölüm otomatik dolar (ayrıştırıcı, eşleştirme, vig çıkarma ve eşik seçimi fixture testleriyle doğrulandı).','',
            'Eşleşmeyen oran satırı sayısı: **hesaplanmadı (oran satırı ayrıştırılmadı)**. Açık franchise eşlemesi src/bbtahmin/veri/teams.py içinde.','']
    return lines

def write_report():
    folder=Path('docs/kanit')
    suite=ElementTree.parse(folder/'pytest.xml').getroot().find('testsuite')
    negative=ElementTree.parse(folder/'negatif_kontrol.xml').getroot().find('testsuite')
    test_summary=(f"Pytest: {suite.attrib['tests']} test; {suite.attrib['failures']} başarısız, {suite.attrib['errors']} hata, {suite.attrib['skipped']} atlanan. "
        f"Ayrı negatif kontrol (tests/negative_control.py, kasıtlı sızıntılı özellik): {negative.attrib['tests']} test, {negative.attrib['failures']} başarısız — beklenen sonuç, sızıntı yakalandı.")
    counts=pd.read_csv(folder/'mac_sayilari.csv')
    metrics=pd.read_csv(folder/'metrikler.csv')
    totals=pd.read_csv(folder/'toplam.csv')
    pred=pd.read_csv(folder/'tahminler.csv')
    collection=json.loads((folder/'toplama.json').read_text('utf8'))
    profile=json.loads((folder/'profil.json').read_text('utf8'))
    partial=[f"{x['lig']} {x['sezon']}" for x in collection['sources'] if x.get('partial')]
    partial_text=', '.join(partial)+' (tam sezon gibi yorumlanmamalı)' if partial else 'yok'
    inventory=pd.DataFrame(collection['sources'])
    counts=inventory[['lig','sezon']].merge(counts,on=['lig','sezon'],how='left').fillna({'mac_sayisi':0})
    counts['mac_sayisi']=counts.mac_sayisi.astype(int)
    counts['durum']=['kısmi' if r.get('partial',False) else 'alınamadı' if r['status']=='error' else 'alındı' for r in collection['sources']]
    counts.to_csv(folder/'mac_sayilari_tam.csv',index=False)
    sig=significance(pred)
    sig.to_csv(folder/'anlamlilik.csv',index=False)
    lines=['# Gerçek çalıştırma sonuçları','',
        f'Rapor zamanı (UTC): {datetime.now(timezone.utc).isoformat()}. Toplama: {collection["timestamp"]}.',
        '', 'Tam komutlar ve ortam: [README](../README.md) ve [ortam.txt](kanit/ortam.txt).',
        '', 'Çalıştırma (bu raporu üreten gerçek komutlar, proje kökünden):', '', '```', *RUN_COMMANDS, '```',
        '', '## Toplam değerlendirme', '',
        '"home" = ev sahibi kazanır: her maçta ev sahibi seçilir, olasılık olarak eğitim penceresindeki ev galibiyet oranı verilir (doğruluk p=1 ile aynıdır; log loss sonsuza gitmez). Fark MAE için ev sahibi tabanı eğitim ortalama farkını, Elo tabanları eğitimde Elo farkından öğrenilen doğrusal regresyonu kullanır. Sınıflandırıcıların MAE değeri ortak Ridge regresyonunundur.',
        '',markdown(totals),'','## Lig ve sezon bazında yan yana','',
        f'Hücre: log loss / Brier / doğruluk / fark MAE. Her ligin ilk iki mevcut sezonu yalnız eğitim ve kronolojik doğrulama içindir; test yapılmadı. BasketbolBet: **yapılamadı (referans bulunamadı)**. Kısmi toplanan sezonlar: {partial_text}.','']
    for league,g in metrics.groupby('lig'):
        pivot=g.assign(value=g.apply(lambda r:f'{r.log_loss:.4f} / {r.brier:.4f} / {r.accuracy:.4f} / {r.margin_mae:.2f}',axis=1)).pivot(index='sezon',columns='model',values='value').reset_index()
        lines += [f'### {league}', '',markdown(pivot),'']
    lines += ['## Toplanan maç sayıları','',markdown(counts),'',
        'Oynanmayan maçlar alınmadı. EuroCup iki ayaklı eşleşme beraberlikleri dışlandı; adetler toplama.json / excluded_ties alanında. Pandemi sezonları eksik kalmıştır.',
        '', '## Kaynak erişimi ve oranlar','']
    errors=[dict(lig=x['lig'],sezon=x['sezon'],hata=x.get('error') or '; '.join(x.get('errors',[])))
        for x in collection['sources'] if x['status']!='ok' or x.get('partial')]
    lines += [markdown(pd.DataFrame(errors)) if errors else 'Skor kaynaklarında raporlanan hata yok.','',
        'Oran sezonları ve kaynak mesajları:','',markdown(pd.DataFrame(collection['odds'])),'']
    lines += odds_section(folder,collection)
    lines += ['## Yöntem ve belirsizlik','',
        'Sezon başlangıcında yeniden eğitim; test sırasında yalnız önceki günlerin özellik durumu güncellenir. Son eğitim sezonu doğrulama, daha eski sezonlar iç eğitimdir. Elo K, ev avantajı, sezon çekmesi, EWMA, lojistik C, boosting yaprak sayısı ve Ridge alpha yalnız bu eğitim penceresinde ızgara ile seçilir. Platt kalibrasyonu önceki sezonda, o sezonu görmeyen model tahminlerinden öğrenilir. Aynı UTC gününün sonuçları birlikte geciktirilir. Izgaralar önceden tanımlıdır; geniş kapsamlı hiperparametre optimizasyonu yapılmadı.',
        '', 'Model − Elo log loss farkı: negatif daha iyi. Sezonlara eşit ağırlık; 10.000 sezon bootstrap örneğiyle %95 aralık ve 10.000 işaret permütasyonuyla iki yönlü p. Karşılaştırmalara lig içinde Holm düzeltmesi. Az sezon ve sezonlar arası bağımlılık nedeniyle sonuç keşifseldir; p<0,05 olmadan üstünlük iddiası yok. İkiden az test sezonu olan ligde anlamlılık hesabı yapılmaz.',
        '',markdown(sig),'',
        'Regresyon artıklarının normal dağılım sınaması, çarpıklık, basıklık ve sigma: parametreler.json. Normal varsayımı reddedilirse handikap olasılığı doğrulanmış kabul edilmez. Gerçek handikap ve toplam skor çizgileri yok; alt/üst bahisleri değerlendirilmedi.',
        '',f'Veri: {profile["rows"]} satır; yinelenen maç: {profile["duplicates"]}. Eksik alanlar profil.json içinde. NBA ilk yarı ve tarafsız saha bilgisi yok; özellikte ev avantajı var kabul edildi. Avrupa yorgunluğu yalnız Avrupa maçlarından; yerel lig verisi yok.',
        '', 'Öneri: sezonlar arasındaki tutarlılığı ve kalibrasyonu birlikte değerlendirin. Kapanış oranı olmadan bahis kararı çıkarılamaz. Demografik veri yok; demografik adalet iddiası yapılmadı.',
        '', '## PLAN.md farkları ve yapılmayanlar','',
        '- Paket: görev kök bbtahmin/ diyor; PLAN önceliğiyle src/bbtahmin/ kullanıldı.',
        '- İstek sınırı: görevde en fazla 15/dk, PLAN içinde 20/dk. İlk koşu 15/dk ile HTTP 429 aldığı için ikisinden de sıkı 10/dk ve en az 6,1 sn aralık uygulandı.',
        '- PLAN, SBR oran arşivini "200" olarak listeler. 2014-15…2022-23 sayfaları tablo içerir; 2023-24 ve sonrası ana sayfaya yönlenir. Sitenin Terms sayfası içeriğin yazılı izin olmadan kullanılmasını yasakladığı için oranlar varsayılan olarak kullanılmadı (görev: kullanım şartlarına uy).',
        '- PLAN Elo için K≈20 ve %25 sezon çekmesi önerir; sabitlemek yerine K∈{10,20,30}, ev avantajı∈{0,50,100}, çekme∈{0,0,25,0,5} eğitim penceresinde seçildi.',
        '- BasketbolBet referansı (data/raw/basketbolbet/main.py) bu çalışma kopyasında yok; karşılaştırma yapılmadı. Formül uydurulmadı, kod kopyalanmadı.',
        '- Yerel lig toplayıcıları yapılmadı: PLAN da kaynağı "araştırılacak" olarak bırakır.',
        '- PLAN aylık yeniden eğitimi isteğe bağlı bırakır; yalnız sezon başında yeniden eğitim yapıldı (sezon içinde Elo/EWMA durumu her gün güncellenir).',
        '- Tahmin komutu seçilmiş saf Elo verir; sınıflandırıcı gelecek maç servisi yapılmadı.',
        '', '## Referans ve test kanıtları','',
        'data/raw/basketbolbet/main.py ve data/raw altındaki benzer referans klasörleri bu çalışma kopyasında bulunamadı; gerçek referans yolu yok. Ignore doğrulaması: .gitignore:1:data/raw/ data/raw/basketbolbet/main.py. Ayrıntı: kanit/ortam.txt.',
        '', 'Normal test sonucu: kanit/pytest.txt ve pytest.xml. Kasıtlı sızıntılı negatif kontrol ayrı koşuda başarısız olmalıdır: kanit/negatif_kontrol.txt. Bu beklenen başarısızlık, gerçek test paketinde kalan hata değildir.',
        '', '## Tekrarlanabilirlik','',
        'kanit/: metrikler.csv, toplam.csv, tahminler.csv, kalibrasyon.csv, anlamlilik.csv, parametreler.json, profil.json, mac_sayilari.csv, mac_sayilari_tam.csv, toplama.json. Kalibrasyon PNG: docs/. Ham yanıtlar ve HTTP meta verileri: git dışı data/raw/. Gerçek pip freeze: requirements-lock.txt. Commit/merge yapılmadı.','']
    lines += ['## Test sonucu','',test_summary,'','## Kalibrasyon görselleri','']
    for league in sorted(pred.lig.unique()):
        lines += [f'![{league} kalibrasyon](kalibrasyon_{league}.png)','']
    lines += ['## Ek keşif ve hata analizi','',
        'Lig-sezon skor dağılımları ve ev galibiyet oranı: kanit/dagilimlar.csv. Korelasyon: kanit/korelasyon.csv. IQR ile işaretlenen aykırılar: kanit/aykirilar.csv (silinmedi). Ev/deplasman favorisi alt gruplarında hata ölçümleri: kanit/hata_analizi.csv. Bunlar tanımlayıcıdır; eğitim/test ayırımı için kullanılmadı.',
        '', 'Kalibrasyon cezalandırılmamış Platt; boosting yaprak/regularizasyon/ağaç sayısı adayları ve seçilenleri parametreler.json içindedir. Hiç maçı görülmemiş takımın EWMA atılan/yenen sayısı, ligin o güne kadarki ortalamasıyla başlatılır (0 ile başlatmak sahte uç değer üretiyordu).',
        '']
    lines += ["\nMOV tanımı, [FiveThirtyEight'in resmi NBA Elo açıklamasına](https://fivethirtyeight.com/features/how-we-calculate-nba-elo-ratings/) dayanır: (kazananın sayı farkı + 3)^0,8 / (7,5 + 0,006 × kazanan yönündeki maç öncesi Elo farkı). Ev avantajı bu farka dahil edilir. Yayımlanmış formül sabitleri kullanılır; K, ev avantajı ve sezon çekmesi eğitimde seçilir. Formül için sayısal birim testi vardır.\n", '']
    gates=[]
    for league,t in totals.groupby('lig'):
        baseline=t[t.model=='elo'].iloc[0]
        home=t[t.model=='home'].iloc[0]
        for model in ['logistic','hist_gradient_boosting']:
            row=t[t.model==model].iloc[0]
            beats=bool(row.log_loss<baseline.log_loss and row.brier<baseline.brier
                and row.log_loss<home.log_loss and row.brier<home.brier)
            matching=sig[(sig.lig==league)&(sig.model==model)] if not sig.empty else pd.DataFrame()
            supported=bool(len(matching) and matching.iloc[0].p_holm<.05
                and matching.iloc[0].mean_season_logloss_delta<0 and matching.iloc[0].ci_high<0)
            gates.append(dict(lig=league,model=model,
                logloss_delta_vs_elo=row.log_loss-baseline.log_loss,
                brier_delta_vs_elo=row.brier-baseline.brier,
                both_baselines='evet' if beats else 'hayır',
                statistical_support='evet' if supported else 'kanıt yok / yetersiz sezon'))
    gate=pd.DataFrame(gates)
    gate.to_csv(folder/'model_kapisi.csv',index=False)
    lines += ['## Model seçim kararı','',
        'PLAN koşulu: yeni model, ev sahibi ve saf Elo tabanlarını hem log loss hem Brier ile geçmeli. Bu tablo gözlenen farkı ve sezon bazında istatistiksel desteği ayırır. Test sonuçlarına bakarak yeni hiperparametre ayarlanmadı.',
        '',markdown(gate),'',
        'Taban çizgisini geçmeyen modeller önerilmez. Küçük gözlenen fark tek başına üretim kararı değildir. Tahmin komutu doğrulanmış parametrelerle saf Elo referansını sunar; sınıflandırıcılar araştırma karşılaştırmasıdır.',
        '']
    Path('docs/sonuclar.md').write_text('\n'.join(lines),'utf8')
