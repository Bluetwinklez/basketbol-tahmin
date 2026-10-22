import argparse
def main():
    parser=argparse.ArgumentParser(description='Sızıntısız basketbol tahmin sistemi')
    sub=parser.add_subparsers(dest='command',required=True)
    collect=sub.add_parser('topla')
    collect.add_argument('--ligler',nargs='+',choices=['E','U','NBA','NBL'],default=['E','U','NBA'])
    collect.add_argument('--baslangic',type=int,default=2007)
    collect.add_argument('--bitis',type=int,default=2025)
    collect.add_argument('--sbr-izni',action='store_true',
        help='SBR oran arşivini kullanma izniniz olduğunu onaylar (site şartları yazılı izin ister)')
    sub.add_parser('topla-kutu',help='EuroLeague/EuroCup kutu skorlarını ve oyuncu dakikalarını topla')
    expand=sub.add_parser('genislet',help='Geçmiş maçları ve ayrıntılı NBA istatistiklerini ekle; mevcut sonuçları korur')
    expand.add_argument('--baslangic',type=int,default=1993,help='Sezon başlangıç yılı')
    expand.add_argument('--bitis',type=int,help='Varsayılan: içinde bulunulan sezon')
    expand.add_argument('--yalniz-skor',action='store_true',help='NBA takım/oyuncu ayrıntılarını indirme')
    expand.add_argument('--ligler',nargs='+',choices=['E','U','NBA'],default=['E','U','NBA'])
    bt=sub.add_parser('backtest')
    bt.add_argument('--ligler',nargs='+',choices=['E','U','NBA','NBL'])
    bt.add_argument('--cikti',default='docs/kanit',help='Başka klasör verilirse deneme koşusu: rapor yazılmaz')
    bt.add_argument('--ilk-test',type=int,help='İlk değerlendirilecek sezonun başlangıç yılı; eğitim geçmişi korunur')
    prediction=sub.add_parser('tahmin',help='Gelecek maçları tahmin et: tahmin "Fenerbahçe - Real Madrid" "Celtics - Lakers"')
    prediction.add_argument('maclar',nargs='+',help='"Ev - Deplasman" biçiminde bir ya da daha çok maç')
    prediction.add_argument('--lig',choices=['E','U','NBA','NBL'],help='Verilmezse takım adlarından bulunur')
    prediction.add_argument('--tarih',help='Maç zamanı, ör. 2026-10-23T20:45 (saat dilimi yoksa İstanbul). Varsayılan: şimdi')
    prediction.add_argument('--json',action='store_true',help='Çıktıyı JSON olarak ver')
    prediction.add_argument('--kaydet',action='store_true',help='Tahminleri defter/tahminler.csv dosyasına ekle')
    prediction.add_argument('--sakatlik',action='store_true',help='Resmi NBA sakatlık raporunu bilgi amaçlı ayrıca indir')
    prediction.add_argument('--min-guven',type=float,help='0.5–1 arası eşik; eşik altındaki maçlar da açıkça gösterilir')
    sub.add_parser('defter',help='Defterdeki tahminleri gerçek sonuçlarla puanla')
    bulletin=sub.add_parser('bulten',help='Deneysel İddaa web bültenini oku; varsayılan yerel snapshot')
    bulletin.add_argument('--guncelle',action='store_true',help='Web backendinden üç salt-okunur GET isteği yap')
    bulletin.add_argument('--lig',choices=['E','U','NBA','NBL'])
    bulletin.add_argument('--limit',type=int,default=30)
    bulletin.add_argument('--tahmin',help='Yerel bültendeki bir etkinlik kimliği için model/piyasa karşılaştırması')
    args=parser.parse_args()
    if args.command=='bulten':
        import json
        if args.guncelle:
            from .veri.iddaa import collect
            collect()
        from .bulletin import list_events,predict_event
        result=predict_event(args.tahmin) if args.tahmin else list_events(league=args.lig,limit=args.limit)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    elif args.command=='topla':
        from .veri.collect import run
        run(args.ligler,args.baslangic,args.bitis,args.sbr_izni)
    elif args.command=='genislet':
        from .veri.genislet import run
        run(args.baslangic,args.bitis,not args.yalniz_skor,
            europe=[l for l in args.ligler if l in ('E','U')],nba='NBA' in args.ligler)
    elif args.command=='topla-kutu':
        import pandas as pd
        from .veri.kutu import topla
        from .veri import nba_kutu
        maclar=pd.read_parquet('data/maclar.parquet')
        nba_kutu.topla(maclar)
        topla(maclar)
    elif args.command=='backtest':
        from .backtest import run
        run(args.ligler,args.cikti,args.ilk_test)
    elif args.command=='defter':
        from .defter import run
        run()
    else:
        from .tahmin import run
        run(args.lig,args.maclar,args.tarih,args.json,args.kaydet,args.sakatlik,args.min_guven)
if __name__=='__main__':main()
