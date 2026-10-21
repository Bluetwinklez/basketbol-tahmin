import argparse
def main():
    parser=argparse.ArgumentParser(description='Sızıntısız basketbol tahmin sistemi')
    sub=parser.add_subparsers(dest='command',required=True)
    collect=sub.add_parser('topla')
    collect.add_argument('--ligler',nargs='+',choices=['E','U','NBA'],default=['E','U','NBA'])
    collect.add_argument('--baslangic',type=int,default=2007)
    collect.add_argument('--bitis',type=int,default=2025)
    collect.add_argument('--sbr-izni',action='store_true',
        help='SBR oran arşivini kullanma izniniz olduğunu onaylar (site şartları yazılı izin ister)')
    sub.add_parser('topla-kutu',help='EuroLeague/EuroCup kutu skorlarını ve oyuncu dakikalarını topla')
    bt=sub.add_parser('backtest')
    bt.add_argument('--ligler',nargs='+',choices=['E','U','NBA'])
    bt.add_argument('--cikti',default='docs/kanit',help='Başka klasör verilirse deneme koşusu: rapor yazılmaz')
    prediction=sub.add_parser('tahmin',help='Gelecek maçları tahmin et: tahmin "Fenerbahçe - Real Madrid" "Celtics - Lakers"')
    prediction.add_argument('maclar',nargs='+',help='"Ev - Deplasman" biçiminde bir ya da daha çok maç')
    prediction.add_argument('--lig',choices=['E','U','NBA'],help='Verilmezse takım adlarından bulunur')
    prediction.add_argument('--tarih',help='Maç zamanı, ör. 2026-10-23T20:45 (saat dilimi yoksa İstanbul). Varsayılan: şimdi')
    prediction.add_argument('--json',action='store_true',help='Çıktıyı JSON olarak ver')
    prediction.add_argument('--kaydet',action='store_true',help='Tahminleri defter/tahminler.csv dosyasına ekle')
    sub.add_parser('defter',help='Defterdeki tahminleri gerçek sonuçlarla puanla')
    args=parser.parse_args()
    if args.command=='topla':
        from .veri.collect import run
        run(args.ligler,args.baslangic,args.bitis,args.sbr_izni)
    elif args.command=='topla-kutu':
        import pandas as pd
        from .veri.kutu import topla
        from .veri import nba_kutu
        maclar=pd.read_parquet('data/maclar.parquet')
        nba_kutu.topla(maclar)
        topla(maclar)
    elif args.command=='backtest':
        from .backtest import run
        run(args.ligler,args.cikti)
    elif args.command=='defter':
        from .defter import run
        run()
    else:
        from .tahmin import run
        run(args.lig,args.maclar,args.tarih,args.json,args.kaydet)
if __name__=='__main__':main()
