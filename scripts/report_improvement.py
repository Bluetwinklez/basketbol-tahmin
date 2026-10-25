"""Summarize every completed fixed experiment without selecting a target winner."""
import argparse
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default='docs/kanit/improvement')
    parser.add_argument('--output',default='docs/kanit/improvement/report.md')
    args=parser.parse_args();root=Path(args.root)
    lines=['# Ölçülen iyileştirme deneyleri','',
           'Bunlar geçmiş dönem deneyleridir. Tarihsel yayın zamanları ve sezon bütünlüğü doğrulanmış değildir. '
           'Canlı başarı artışı veya varsayılan model değişikliği anlamına gelmez. Başarısız adaylar da deney dosyalarında korunur.','',
           '## Futbol: önceki dönemde seçilen politika','',
           'Adaylar: mevcut Poisson, 90 günlük yarı ömür, 16 maçlık küçültme, rakip düzeltmesi, düşük skor düzeltmesi ve sabit karışım. '
           'Kalibrasyon önceki sezonun ilk tarih yarısında, seçim ikinci yarısında yapılır. Hedef dönemin sonuçları seçime katılmaz.','',
           '| Lig | Hedef sezon | Maç | Mevcut isabet | Önceki dönemde seçilen politika | Politika isabeti | Log loss değişimi |',
           '|---|---|---:|---:|---|---:|---:|']
    path=root/'football/summary.json'
    if path.exists():
        for report in json.loads(path.read_text())['reports']:
            a=report['summaries']['baseline']['all'];b=report['summaries']['prior_selected_policy']['all']
            lines.append(f"| {report['league']} | {report['target_season']} | {a['games']} | {a['accuracy']:.2%} | {report['selected_using_prior_period']} + kalibrasyon | {b['accuracy']:.2%} | {b['log_loss']-a['log_loss']:+.5f} |")
    else: lines.append('| Deney henüz tamamlanmadı | | | | | | |')
    lines+=['','Negatif log loss değişimi daha iyidir. İsabet ve olasılık kalitesi farklı yönlere gidebilir. '
            'Aynı hedefte en iyi görünen aday seçilip ileri başarı diye sunulmaz.','',
            '## Basketbol: ortak deney modeli ve özellik katkıları','',
            'Ortak önceki-sezon öğrenici politikası tüm liglerin mevcut üretim modeliyle aynı değildir. '
            'Bu tablo özellik katkısını karşılaştırır; üretim başarı oranını göstermez. Ev özelliğini kaldırma deneyinde Elo ev avantajı korunur.','',
            '| Lig | Sezon | Aday | Maç | Referans isabet | Aday isabet | Log loss değişimi |',
            '|---|---|---|---:|---:|---:|---:|']
    path=root/'basketball/summary.json'
    if path.exists():
        for report in json.loads(path.read_text())['reports']:
            for season,variants in report['summaries'].items():
                base=variants['baseline']['all']
                for name,values in variants.items():
                    if name=='baseline':continue
                    candidate=values['all']
                    lines.append(f"| {report['league']} | {season} | {name} | {base['games']} | {base['accuracy']:.2%} | {candidate['accuracy']:.2%} | {candidate['log_loss']-base['log_loss']:+.5f} |")
    ablation=root/'football-data-ablation-v2/summary.json'
    if ablation.exists():
        data=json.loads(ablation.read_text())
        lines+=['','## Futbol: yalnız veri değişiminin etkisi','',
                f"{data['scored_fixture_count']} yeni lisanslı finalin tamamı, aynı Poisson modeli ve aynı maçlarla karşılaştırıldı. "
                'Yeni doğrulanmış sonuçlar ve açık tarih düzeltmeleri veri değişikliğidir. Hedef UTC gününün tamamı eğitimden çıkarıldı. '
                'Tarihsel yayın erişimi bilinmediğinden bu çalışma ileri dönem başarısı değildir.','',
                '| Lig | Maç | Eski veri isabeti | Ek veri isabeti | Eski / yeni log loss |',
                '|---|---:|---:|---:|---:|']
        for row in data['summaries']:
            a=row['variants']['old_data'];b=row['variants']['expanded_data']
            lines.append(f"| {row['league']} | {a['games']} | {a['winner_accuracy']:.2%} | {b['winner_accuracy']:.2%} | {a['log_loss']:.5f} / {b['log_loss']:.5f} |")
    calibration=root/'calibration/summary.json'
    if calibration.exists():
        report=json.loads(calibration.read_text());n=sum(len(r['reports']) for r in report['reports'])
        lines+=['','## Önceki dönem olasılık kalibrasyonu','',
                f'{len(report["reports"])} ligde {n} karşılaştırma kaydedildi. Sıcaklık parametresi yalnız daha önceki sezonun '
                'örneklem dışı tahminlerinde seçildi; hedef sezon etiketleri seçime katılmadı. Skor ortalamaları ve aralıkları değiştirilmedi.']
    shadow=Path('data/improvement_shadow/latest.json')
    if shadow.exists():
        forward=json.loads(shadow.read_text());identities=set()
        for path in Path('data/improvement_shadow/experiments').glob('*/forecasts/*.json'):
            fixture=json.loads(path.read_text(encoding='utf8'))['fixture'];identities.add((fixture['league'],fixture['event_id']))
        lines+=['','## Sonuç öncesi paralel kayıt','',
                f"{len(identities)} benzersiz maç için tahmin çifti bulunuyor. Kod/politika sürümleri ayrı deneylerdir; "
                'aynı maçın farklı sürümleri bağımsız maç gibi toplanmaz. İlk deneme sürümleri tam kaynak paketi içermediğinden yükseltme değerlendirmesine uygun değildir. '
                'Yeni sürümler kaynak kodunu, paket sürümlerini ve veri karmalarını saklar.','',
                '| Deney | Aktif | Sonuçlandı | Bekliyor | Kaynak paketi doğrulandı |',
                '|---|---|---:|---:|---|']
        for experiment in forward['experiments']:
            lines.append(f"| {experiment['experiment_id'][:12]} | {experiment.get('active_experiment',False)} | {experiment['settled_games']} | {experiment['pending']} | {experiment.get('source_snapshot_verified',False)} |")
    lines+=['','## Henüz tamamlanmayan doğrulama','',
            'Bağımsız gelecek sonuçlarının birikmesi ve kalan kaynak/takvim boşluklarının giderilmesi sürüyor. '
            'Yeni model otomatik olarak yayımlanmaz. Yeterli örneklem, gün sayısı, iki zaman diliminde tutarlılık, '
            'olasılık hatası ve seçim kapsamı koşulları birlikte incelenir. Bu koşullar tamamlanmadan canlı başarı iyileşti denmez.']
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(target)


if __name__=='__main__':main()
