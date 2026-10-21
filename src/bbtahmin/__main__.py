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
    sub.add_parser('backtest')
    prediction=sub.add_parser('tahmin')
    prediction.add_argument('--lig',required=True,choices=['E','U','NBA'])
    prediction.add_argument('--ev',required=True)
    prediction.add_argument('--dep',required=True)
    prediction.add_argument('--tarih',required=True)
    args=parser.parse_args()
    if args.command=='topla':
        from .veri.collect import run
        run(args.ligler,args.baslangic,args.bitis,args.sbr_izni)
    elif args.command=='backtest':
        from .backtest import run
        run()
    else:
        from .tahmin import run
        run(args.lig,args.ev,args.dep,args.tarih)
if __name__=='__main__':main()
