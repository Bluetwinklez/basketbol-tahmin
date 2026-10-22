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
    prediction.add_argument('--lig',choices=['E','U','NBA','NBL','CBA','ECW','FEC','VTB'],help='Verilmezse takım adlarından bulunur')
    prediction.add_argument('--tarih',help='Maç zamanı, ör. 2026-10-23T20:45 (saat dilimi yoksa İstanbul). Varsayılan: şimdi')
    prediction.add_argument('--adaptive-form',action='store_true',help='Deneysel: önceki sezonun testine göre aylık model güncellemesi; yalnız ECW/FEC/VTB')
    prediction.add_argument('--json',action='store_true',help='Çıktıyı JSON olarak ver')
    prediction.add_argument('--kaydet',action='store_true',help='Tahminleri defter/tahminler.csv dosyasına ekle')
    prediction.add_argument('--sakatlik',action='store_true',help='Resmi NBA sakatlık raporunu bilgi amaçlı ayrıca indir')
    prediction.add_argument('--min-guven',type=float,help='0.5–1 arası eşik; eşik altındaki maçlar da açıkça gösterilir')
    sub.add_parser('defter',help='Defterdeki tahminleri gerçek sonuçlarla puanla')
    sub.add_parser('baglam-topla',help='Resmi kulüp sayfalarından ayrı yerel maç yükü gözlemlerini topla')
    sub.add_parser('cba-topla',help='Tarihli CBA sonuçlarını ayrı arşive topla')
    regional=sub.add_parser('lig-topla',help='Kadınlar EuroCup, FIBA Avrupa Kupası ve VTB sonuçlarını topla')
    regional.add_argument('--ligler',nargs='+',choices=['ECW','FEC','VTB'],default=['ECW','FEC','VTB'])
    live=sub.add_parser('canli',help='Deneysel CBA canlı durumundan normal süre skor projeksiyonu')
    live.add_argument('--ev',required=True);live.add_argument('--dep',required=True)
    live.add_argument('--skor',nargs=2,type=int,required=True,metavar=('EV','DEP'))
    live.add_argument('--periyot',type=int,required=True)
    live.add_argument('--kalan',required=True,help='Periyotta KALAN süre MM:SS')
    live.add_argument('--tarih',required=True,help='Skorun gözlendiği saat dilimli zaman')
    live.add_argument('--dakika',type=int,choices=[40,48])
    live.add_argument('--previous-state',help='Previous live JSON output for transition validation')
    live.add_argument('--score-correction',action='store_true',help='Explicitly flag a provider clock/score correction')
    live.add_argument('--replay',action='store_true',help='Eski durumun tarihsel tekrarını açıkça etiketle')
    bulletin=sub.add_parser('bulten',help='Deneysel İddaa web bültenini oku; varsayılan yerel snapshot')
    bulletin.add_argument('--guncelle',action='store_true',help='Web backendinden üç salt-okunur GET isteği yap')
    bulletin.add_argument('--lig',choices=['E','U','NBA','NBL','CBA','ECW','FEC','VTB'])
    bulletin.add_argument('--limit',type=int,default=30)
    action=bulletin.add_mutually_exclusive_group()
    action.add_argument('--tahmin',help='Yerel bültendeki bir etkinlik kimliği için model/piyasa karşılaştırması')
    action.add_argument('--gecmis',help='Etkinlik kimliğinin yerel maç önü oran geçmişi')
    bulletin.add_argument('--asof',help='Oran geçmişi için saat dilimli bilgi kesim zamanı; gelecekte olamaz')
    sub.add_parser('yerel-topla',help='Collect official Czech senior women results separately')
    sub.add_parser('kadin-gecmis-topla',help='Collect separate EuroLeague Women and early EuroCup Women history')
    sub.add_parser('veri-denetle',help='Write league/season coverage and data-quality inventory')
    imported=sub.add_parser('baglam-aktar',help='Validate and quarantine versioned official result imports')
    imported.add_argument('--source',required=True);imported.add_argument('--identities',required=True)
    future=sub.add_parser('prospektif',help='Freeze the earliest verified future fixtures without overwriting')
    future.add_argument('--fixtures',required=True);future.add_argument('--output',required=True)
    future.add_argument('--limit',type=int,default=2)
    settled=sub.add_parser('sonuc-kontrol',help='Score verified final results without rewriting frozen forecasts')
    settled.add_argument('--record',required=True);settled.add_argument('--results',required=True)
    settled.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.command in ('veri-denetle','baglam-aktar','prospektif','sonuc-kontrol'):
        import json
        from pathlib import Path
        if args.command=='veri-denetle':
            from .quality import write_inventory
            result=write_inventory()
        elif args.command=='baglam-aktar':
            from .context_import import ingest
            result=ingest(args.source,args.identities)
        elif args.command=='prospektif':
            from .prospective import generate
            if args.limit<1:parser.error('--limit must be positive')
            result=generate(args.fixtures,args.output,args.limit)
        else:
            from .prospective import settle
            result=settle(json.loads(Path(args.record).read_text()),json.loads(Path(args.results).read_text()))
            target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    elif args.command=='yerel-topla':
        from .veri.domestic import collect
        collect()
    elif args.command=='kadin-gecmis-topla':
        from .veri.competitions import collect_fiba
        from .veri.women_history import collect
        collect_fiba('ELW');collect()
    elif args.command=='baglam-topla':
        from .veri.club_context import collect
        collect()
    elif args.command=='lig-topla':
        from .veri.competitions import collect
        collect(args.ligler)
    elif args.command=='cba-topla':
        from .veri.cba import collect
        collect()
    elif args.command=='canli':
        import json
        from pathlib import Path
        from .live import predict
        from .cba_model import load
        from .takim_ad import coz
        g=load();codes=set(g.ev)|set(g.dep)
        result=predict(coz('CBA',args.ev,codes),coz('CBA',args.dep,codes),*args.skor,
                       args.periyot,args.kalan,args.tarih,args.dakika,args.replay,
                       json.loads(Path(args.previous_state).read_text()) if args.previous_state else None,args.score_correction)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    elif args.command=='bulten':
        import json
        if args.asof and not args.gecmis:
            parser.error('--asof requires --gecmis')
        if args.guncelle and args.asof:
            parser.error('Historical as-of queries cannot refresh providers')
        if args.guncelle:
            from .veri.iddaa import collect
            collect()
        from .bulletin import list_events,predict_event
        if args.gecmis:
            from .market_history import history
            result=history(args.gecmis,as_of=args.asof,limit=args.limit)
        else:
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
        run(args.lig,args.maclar,args.tarih,args.json,args.kaydet,args.sakatlik,args.min_guven,args.adaptive_form)
if __name__=='__main__':main()
