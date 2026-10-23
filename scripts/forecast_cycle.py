"""Fetch official EuroLeague fixture/final facts; freeze and settlement remain separate."""
import argparse,json
from pathlib import Path
import pandas as pd
from bbtahmin.veri.competitions import fetch
from bbtahmin.prospective import generate,settle

URL='https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games'


def facts(payload,captured):
 from bbtahmin.euro_facts import facts as official_facts
 return official_facts(payload,captured,'E2026',URL)


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
