"""Independent Asian-league archives; no mixing of divisions or PBA conferences."""
import hashlib,json
from pathlib import Path
import pandas as pd

CODES=('KBL','JP_B1','JP_B2','PBA_GOV','PBA_COM','PBA_PHI')
NAMES={'KBL':'Korean Basketball League','JP_B1':'Japan B1 / B.PREMIER',
       'JP_B2':'Japan B2 / B.ONE','PBA_GOV':"PBA Governors Cup",
       'PBA_COM':"PBA Commissioners Cup",'PBA_PHI':"PBA Philippine Cup"}


def cross_source_pba(g):
    """Only match distinct providers with the same campaign, teams and points."""
    aliases={};drop=[]
    rg=g[g.mac_id.str.startswith('PBA_R')]
    for row in g[g.mac_id.str.startswith('PBA_SM_')].itertuples():
        points={row.ev:row.ev_skor,row.dep:row.dep_skor}
        candidates=[r.mac_id for r in rg.itertuples() if r.sezon==row.sezon
            and abs(r.tarih_utc-row.tarih_utc)<=pd.Timedelta(days=1)
            and {r.ev:r.ev_skor,r.dep:r.dep_skor}==points]
        if len(candidates)>1:raise ValueError('Ambiguous PBA cross-source fixture; refusing arbitrary merge')
        if candidates:aliases[row.mac_id]=candidates[0];drop.append(row.Index)
    return g.drop(index=drop),aliases


def save(code,records,teams,report,fixtures=None):
    if code not in CODES:raise ValueError('Unsupported Asian competition')
    g=pd.DataFrame(records)
    if g.empty:raise ValueError('No verified final observations for '+code)
    g['tarih_utc']=pd.to_datetime(g.tarih_utc,utc=True)
    if set(g.lig)!={code} or (g.ev==g.dep).any() or (g[['ev_skor','dep_skor']]<=0).any().any():
        raise ValueError('Invalid final or competition identity')
    if (g.ev_skor==g.dep_skor).any() or (g.tarih_utc>=pd.Timestamp.now(tz='UTC')).any():raise ValueError('Nonfinal or future result')
    root=Path('data/asia');root.mkdir(parents=True,exist_ok=True);path=root/f'{code}.parquet'
    if path.exists():g=pd.concat([pd.read_parquet(path),g],ignore_index=True)
    fields=['lig','sezon','tarih_utc','ev','dep','ev_skor','dep_skor']
    for _,part in g.groupby('mac_id'):
        if len(part[fields].drop_duplicates())!=1:raise ValueError('Conflicting persisted Asian result')
    g=g.drop_duplicates('mac_id').sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    aliases={}
    if code=='PBA_GOV':g,aliases=cross_source_pba(g)
    temp=path.with_suffix('.part');g.to_parquet(temp,index=False);temp.replace(path)
    catalog=root/f'{code}_teams.json';old=json.loads(catalog.read_text()) if catalog.exists() else {}
    for key,entry in teams.items():
        previous=old.get(key,{})
        entry['aliases']=sorted(set(entry.get('aliases',[])+previous.get('aliases',[])+([previous['name']] if previous.get('name') else [])))
        old[key]=entry
    catalog.write_text(json.dumps(old,ensure_ascii=False,indent=2))
    if fixtures:
        f=pd.DataFrame(fixtures)
        if f.mac_id.duplicated().any():raise ValueError('Duplicate current fixtures')
        f.to_parquet(root/f'{code}_fixtures.parquet',index=False)
    report.update(games=len(g),teams=len(set(g.ev)|set(g.dep)),seasons=g.groupby('sezon').size().to_dict(),
        dataset_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),trained=False)
    evidence=Path('docs/kanit/asia_data');evidence.mkdir(parents=True,exist_ok=True)
    report_path=evidence/f'{code}_collection.json'
    if report_path.exists():
        previous=json.loads(report_path.read_text())
        report['sources']=list(dict.fromkeys(previous.get('sources',[])+report.get('sources',[])))
        counts={}
        for item in previous.get('counts',[])+report.get('counts',[]):
            key=tuple((k,item[k]) for k in ('year','calendar_year','end_year') if k in item)
            counts[key or json.dumps(item,sort_keys=True)]=item
        report['counts']=list(counts.values())
        aliases={**previous.get('source_event_aliases',{}),**aliases}
        if 'current_model_season' in previous and 'current_model_season' not in report:report['current_model_season']=previous['current_model_season']
    if aliases:
        report['source_event_aliases']=aliases
        boxes=root/'PBA_GOV_player_boxes.parquet'
        if boxes.exists():
            b=pd.read_parquet(boxes);b['mac_id']=b.mac_id.map(lambda k:aliases.get(k,k))
            b.drop_duplicates(['mac_id','team','player_id']).to_parquet(boxes,index=False)
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return g
