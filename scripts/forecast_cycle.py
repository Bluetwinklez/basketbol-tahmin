"""Fetch official EuroLeague fixture/final facts; freeze and settlement remain separate."""
import argparse,json
from pathlib import Path
import pandas as pd
from bbtahmin.veri.competitions import fetch
from bbtahmin.prospective import generate,settle

URL='https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games'


def facts(payload,captured):
 if payload.get('total',len(payload.get('data',[])))!=len(payload.get('data',[])):raise ValueError('Incomplete official schedule')
 fixtures=[];results=[]
 for row in payload['data']:
  if row['season']['code']!='E2026':raise ValueError('Wrong season')
  start=pd.Timestamp(row['utcDate']);home=row['local']['club'];away=row['road']['club']
  common=dict(event_id=row['identifier'],source_url=URL,captured_at=captured,start_utc=start.isoformat(),
   league='E',home=home['code'],away=away['code'],home_name=home['name'],away_name=away['name'])
  if row.get('played'):
   h,a=row['local']['score'],row['road']['score']
   if type(h) is int and type(a) is int and min(h,a)>0 and h!=a and start<pd.Timestamp(captured):
    results.append(dict(common,status='final',home_score=h,away_score=a))
  elif row.get('confirmedDate') and row.get('confirmedHour') and row.get('gameStatus')=='Confirmed' and start>pd.Timestamp(captured):
   fixtures.append(dict(common,status='scheduled'))
 return fixtures,results


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--freeze',action='store_true');p.add_argument('--record',default='docs/kanit/prospective/2026-10-23.json')
 args=p.parse_args();captured=pd.Timestamp.now(tz='UTC').isoformat()
 payload=json.loads(fetch(URL,refresh=True));fixtures,results=facts(payload,captured)
 root=Path('docs/kanit/prospective');root.mkdir(parents=True,exist_ok=True)
 if args.freeze:
  path=root/'fixtures_2026-10-23.json';path.write_text(json.dumps(fixtures,indent=2))
  from bbtahmin.runtime_history import refresh_europe
  refresh_europe(payload,captured)
  result=generate(path,args.record)
 else:
  record=json.loads(Path(args.record).read_text());result=settle(record,results)
  stamp=pd.Timestamp(captured).strftime('%Y%m%dT%H%M%SZ');target=root/f'check_{stamp}.json'
  with target.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
 print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))

if __name__=='__main__':main()
