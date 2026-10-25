import argparse
def main():
    from .veri.asia import CODES as ASIA_CODES
    from .daily import LEAGUES as DAILY_LEAGUES
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
    prediction.add_argument('--lig',choices=['E','U','NBA','NBL','CBA','ECW','FEC','VTB','ABA','UKR','TR_BSL','ARG_LNB',*ASIA_CODES],help='Verilmezse takım adlarından bulunur')
    prediction.add_argument('--tarih',help='Maç zamanı, ör. 2026-10-23T20:45 (saat dilimi yoksa İstanbul). Varsayılan: şimdi')
    prediction.add_argument('--hierarchical',action='store_true',help='Research-only linked senior-women attack/defence model; ECW only')
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
    bulletin.add_argument('--lig',choices=['E','U','NBA','NBL','CBA','ECW','FEC','VTB','ABA','UKR','TR_BSL','ARG_LNB',*ASIA_CODES])
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
    feed=sub.add_parser('canli-veri-topla',help='Archive NBA scoreboard observations; no validated live predictor')
    feed.add_argument('--provider',choices=['espn','nba'],default='espn')
    sub.add_parser('bolgesel-topla',help='Collect official Bulgarian women and public Parnu domestic observations')
    sub.add_parser('slovenya-topla',help='Collect verified senior-women first-league official results')
    sub.add_parser('finlandiya-topla',help='Collect dated senior-women Finnish league results')
    sub.add_parser('girona-topla',help='Collect Girona senior-women match facts with actual FEB tipoff times')
    sub.add_parser('waba-topla',help='Collect verified senior WABA results with conservative day precision')
    domestic=sub.add_parser('ulke-topla',help='Collect separate Ukraine, Turkish BSL or Argentina LNB archives (Argentina starts in 2022)')
    domestic.add_argument('--ligler',nargs='+',choices=['UKR','TR_BSL','ARG_LNB'],default=['UKR','TR_BSL'])
    domestic.add_argument('--baslangic',type=int,default=2020)
    domestic.add_argument('--bitis',type=int)
    aba=sub.add_parser('aba-topla',help='Collect official senior ABA seasons separately')
    aba.add_argument('--baslangic',type=int,default=2010)
    aba.add_argument('--bitis',type=int)
    aba.add_argument('--guncelle',action='store_true')
    asia=sub.add_parser('asya-topla',help='Collect separate KBL/Japan/PBA-conference archives')
    asia.add_argument('--kaynaklar',nargs='+',choices=['KBL','Japan','PBA'],default=['KBL','Japan','PBA'])
    asia.add_argument('--current-only',action='store_true',help='Refresh current schedules without repeating historical backfills')
    asia.add_argument('--baslangic',type=int,help='First source year (Japanese season start, PBA season end, KBL calendar year)')
    asia.add_argument('--bitis',type=int,help='Last source year, inclusive; requires --baslangic')
    daily=sub.add_parser('gunluk',help='Refresh fixtures, freeze pregame forecasts and report separate final-result errors')
    daily.add_argument('--ligler',nargs='+',choices=DAILY_LEAGUES,default=list(DAILY_LEAGUES))
    daily.add_argument('--guncelle',action='store_true',help='Refresh public schedules and current results; failures remain visible')
    daily.add_argument('--saat',type=int,default=48,help='Upcoming fixture horizon, 1..168 hours')
    daily.add_argument('--min-guven',type=float,default=.65,help='Probability filter, not an observed accuracy guarantee')
    daily.add_argument('--cikti',default='rapor/daily',help='Persistent local record directory; reuse it to retain prospective history')
    daily.add_argument('--json',action='store_true',help='Machine-readable report instead of the console Markdown table')
    app=sub.add_parser('app',help='Open the local browser application for forecasts and result tracking')
    app.add_argument('--port',type=int,default=8765)
    app.add_argument('--cikti',default='rapor/daily',help='Reuse the same local forecast ledger as gunluk')
    app.add_argument('--no-browser',action='store_true',help='Print the local address without opening a browser')
    injuries=sub.add_parser('sakatlik-arsivle',help='Archive an actual timestamped official NBA report')
    injuries.add_argument('--hours',type=float,default=2)
    players=sub.add_parser('oyuncu-baglam',help='Lagged NBA rotation and genuinely observed dated injury context')
    players.add_argument('--ev',required=True);players.add_argument('--dep',required=True)
    players.add_argument('--tarih',required=True);players.add_argument('--asof')
    travel=sub.add_parser('seyahat-baglam',help='Observed venue-to-venue schedule proxies; no inferred actual itinerary')
    travel.add_argument('--event-id',required=True);travel.add_argument('--asof',required=True)
    football=sub.add_parser('futbol',help='Separate football data, goal forecasts and chronological evaluation')
    football.add_argument('action',choices=['collect','daily','predict','evaluate','compare','coverage'])
    football.add_argument('--model',choices=['baseline','opponent','opponent_dc','ensemble'],default='baseline')
    football.add_argument('--first',type=int,default=2010)
    football.add_argument('--last',type=int)
    football.add_argument('--current-only',action='store_true')
    football.add_argument('--refresh',action='store_true')
    football.add_argument('--league',choices=__import__('bbtahmin.football.data',fromlist=['LEAGUES']).LEAGUES)
    football.add_argument('--home');football.add_argument('--away');football.add_argument('--date')
    football.add_argument('--season');football.add_argument('--days',type=int,default=7)
    football.add_argument('--output',default='rapor/football')
    args=parser.parse_args()
    if args.command=='futbol':
        import json
        import pandas as pd
        from pathlib import Path
        from .football.data import collect,load,write_json
        from .football.model import GoalModel,evaluate
        if args.action=='coverage':
            from .football.coverage import league_coverage
            result=league_coverage(load())
        elif args.action=='collect':
            result=collect(args.first,args.last,current_only=args.current_only)
        elif args.action=='daily':
            from .football.daily import run as football_run
            if args.refresh: collect(current_only=True)
            result=football_run(args.days,args.output,model_variant=args.model)
        elif args.action in ('evaluate','compare'):
            import gzip
            if args.action == 'compare':
                from .football.challenger import compare
                if not args.season: parser.error('compare requires --season')
                result=compare(load(),args.season)
            else: result=evaluate(load(),args.season)
            predictions=result.pop('predictions')
            target=Path(args.output);target.mkdir(parents=True,exist_ok=True)
            (target/'predictions.json.gz').write_bytes(gzip.compress(json.dumps(predictions,ensure_ascii=False,allow_nan=False).encode(),mtime=0))
            result['predictions_file']='predictions.json.gz'
            write_json(target/('comparison.json' if args.action == 'compare' else 'evaluation.json'),result)
        else:
            if not all((args.league,args.home,args.away,args.date)):
                parser.error('predict requires --league, --home, --away and --date')
            if pd.Timestamp(args.date).date()<pd.Timestamp.now(tz='UTC').date():
                parser.error('Use evaluate for historical predictions')
            cutoff=min(pd.Timestamp(args.date).date(),pd.Timestamp.now(tz='UTC').date())
            from .football.challenger import fit
            result=fit(load(),args.league,str(cutoff),args.model).predict(args.home,args.away)
            result['fixture_date']=args.date
            result['fixture_verified']=False
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    elif args.command=='app':
        from .app import serve
        serve(args.port,args.cikti,not args.no_browser)
    elif args.command=='gunluk':
        import json
        from .daily import run,markdown
        result=run(args.ligler,args.cikti,args.guncelle,args.saat,args.min_guven)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False) if args.json else markdown(result))
    elif args.command in ('veri-denetle','baglam-aktar','prospektif','sonuc-kontrol'):
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
    elif args.command=='canli-veri-topla':
        import json
        from .live_feed import capture
        print(json.dumps(capture(args.provider),indent=2))
    elif args.command=='ulke-topla':
        from importlib import import_module
        for code in args.ligler:
            module={'UKR':'ukraine','TR_BSL':'turkey','ARG_LNB':'argentina'}[code]
            import_module('.veri.'+module,'bbtahmin').collect(args.baslangic,args.bitis)
    elif args.command=='aba-topla':
        from .veri.aba import collect
        collect(args.baslangic,args.bitis,args.guncelle)
    elif args.command=='asya-topla':
        import pandas as pd
        today=pd.Timestamp.now(tz='UTC');year=today.year if today.month>=7 else today.year-1
        if args.current_only and (args.baslangic is not None or args.bitis is not None):
            parser.error('--current-only cannot be combined with historical year bounds')
        if args.bitis is not None and args.baslangic is None:parser.error('--bitis requires --baslangic')
        last=args.bitis if args.bitis is not None else today.year
        if args.baslangic is not None and not 1990<=args.baslangic<=last<=today.year+1:
            parser.error('Invalid historical source-year bounds')
        for source in args.kaynaklar:
            if source=='KBL':from .veri.korea import collect
            elif source=='Japan':from .veri.japan import collect
            else:from .veri.philippines import collect
            if args.current_only:
                if source=='KBL':collect(first=today.year,last=today.year)
                elif source=='Japan':collect(years=(year,))
                # PBA's current publisher is refreshed below; do not assume a July campaign boundary.
            elif args.baslangic is not None:
                if source=='Japan':collect(years=tuple(range(args.baslangic,last+1)))
                else:collect(first=args.baslangic,last=last)
            else:collect()
            if source=='PBA':
                from .veri.pba_current import collect as current_pba
                current_pba()
    elif args.command in ('finlandiya-topla','girona-topla','waba-topla'):
        if args.command=='finlandiya-topla':from .veri.finland import collect
        elif args.command=='waba-topla':from .veri.waba import collect
        else:from .veri.spain import collect
        collect()
    elif args.command=='bolgesel-topla':
        from .veri.regional import bulgaria,parnu
        bulgaria();parnu()
    elif args.command=='slovenya-topla':
        from .veri.slovenia import collect
        collect()
    elif args.command=='sakatlik-arsivle':
        import json
        from .player_context import archive_injuries
        if not 0<args.hours<=6:parser.error('--hours must be >0 and <=6')
        print(json.dumps(archive_injuries(hours=args.hours),indent=2))
    elif args.command=='seyahat-baglam':
        import json
        from .travel import local_context
        print(json.dumps(local_context(args.event_id,args.asof),indent=2,allow_nan=False))
    elif args.command=='oyuncu-baglam':
        import json
        from .player_context import context
        print(json.dumps(context(args.ev,args.dep,args.tarih,args.asof),indent=2,allow_nan=False))
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
        run(args.lig,args.maclar,args.tarih,args.json,args.kaydet,args.sakatlik,args.min_guven,args.adaptive_form,args.hierarchical)
if __name__=='__main__':main()

