import json
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from .http import CachedHTTP
from .schema import normalize
from . import euroleague,nba_bref,nba_odds
def run(leagues=('E','U','NBA'),start=2007,end=2025,sbr_permission=False):
    http=CachedHTTP()
    rows,status,odds=[],[],[]
    odds_rows=[]
    for league in leagues:
        for year in range(max(start,2014) if league=='NBA' else start,end+1):
            item=dict(lig=league,sezon=f'{year}-{str(year+1)[-2:]}')
            try:
                if league=='NBA':
                    games,details=nba_bref.collect(http,year)
                    item.update(details)
                else:
                    games,details=euroleague.collect(http,league,year)
                    item.update(details)
                rows.extend(games)
                item.update(status='ok',count=len(games))
            except Exception as e:
                item.update(status='error',count=0,error=str(e))
            status.append(item)
            print(json.dumps(item,ensure_ascii=False),flush=True)
    if 'NBA' in leagues:
        for year in range(max(start,2014),end+1):
            item=dict(sezon=f'{year}-{str(year+1)[-2:]}')
            if not sbr_permission:
                item.update(status='atlandı',error=f'SBR kullanım şartları yazılı izin gerektiriyor ({nba_odds.TERMS}); --sbr-izni verilmedi')
            else:
                try:
                    season=nba_odds.collect(http,year)
                    odds_rows.extend(season)
                    item.update(status='ok',rows=len(season))
                except Exception as e:
                    item.update(status='missing',error=str(e))
            odds.append(item)
    df=normalize(rows)
    path=Path('data/maclar.parquet')
    path.parent.mkdir(exist_ok=True)
    if path.exists():
        old=pd.read_parquet(path)
        successful={(x['lig'],x['sezon']) for x in status if x['status']=='ok' and not x.get('partial')}
        incoming=set(df.mac_id)
        keep=old[[(r.lig,r.sezon) not in successful and r.mac_id not in incoming for r in old.itertuples()]]
        df=normalize(pd.concat([keep,df]).to_dict('records'))
    df.to_parquet(path,index=False)
    Path('docs/kanit').mkdir(parents=True,exist_ok=True)
    previous_path=Path('docs/kanit/toplama.json')
    if previous_path.exists():
        previous=json.loads(previous_path.read_text('utf8'))
        touched={(r['lig'],r['sezon']) for r in status}
        status=[r for r in previous['sources'] if (r['lig'],r['sezon']) not in touched]+status
        if 'NBA' not in leagues: odds=previous.get('odds',[])
    unmatched=None
    if odds_rows:
        matched,unmatched_rows=nba_odds.match(odds_rows,df)
        matched.to_parquet('data/oranlar.parquet',index=False)
        unmatched=dict(count=len(unmatched_rows),total=len(odds_rows),
            reasons=pd.Series([u['neden'] for u in unmatched_rows],dtype=str).value_counts().to_dict(),
            examples=[{k:str(v) for k,v in u.items()} for u in unmatched_rows[:20]])
    elif 'NBA' in leagues and not sbr_permission and Path('data/oranlar.parquet').exists():
        Path('data/oranlar.parquet').unlink()
    evidence=dict(timestamp=datetime.now(timezone.utc).isoformat(),sources=status,odds=odds,
        unmatched_odds_rows=unmatched,http=http.events,
        limitations=['NBA neutral courts unknown'])
    Path('docs/kanit/toplama.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),'utf8')
    return df
