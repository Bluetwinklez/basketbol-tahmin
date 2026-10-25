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
    lines+=['','## Henüz tamamlanmayan doğrulama','',
            'Gelecekteki maçlardan bağımsız örneklem birikmesi, paralel aday kayıt akışının tamamlanması, '
            'bağımsız güncel fikstür doğrulamasının genişletilmesi ve kalan kaynak boşluklarının giderilmesi ayrı kabul koşullarıdır. '
            'Bu koşullar tamamlanmadan canlı başarı iyileşti denmez.']
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(target)


if __name__=='__main__':main()
