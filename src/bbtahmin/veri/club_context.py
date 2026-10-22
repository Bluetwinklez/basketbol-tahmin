"""Small official-club fixture cohorts for auxiliary workload, never a full league archive."""
import hashlib,json,re
from pathlib import Path
from urllib.parse import urljoin,urlparse,parse_qs
import pandas as pd
from bs4 import BeautifulSoup
from .competitions import fetch

SOURCES={'zabiny':'https://www.bkzabiny.cz/tym/9-a-tym/zapasy',
         'vienna':'https://bcvienna.com/en/schedule/'}
DATA=Path('data/context/club_games.parquet')


def identity(source,name):
    known={'zabiny':{'Žabiny Brno':'ECW_892','KP Brno':'ECW_891'},'vienna':{'BC Vienna':'FEC_73436'}}
    if name in known[source]:return known[source][name]
    prefix='CZ_W_' if source=='zabiny' else 'AT_M_'
    return prefix+hashlib.sha256(name.encode()).hexdigest()[:16]


def parse_zabiny(html):
    soup=BeautifulSoup(html,'html.parser');rows=[]
    for a in soup.select('a.team-game-item[href]'):
        meta=a.select_one('.team-game-meta');score=a.select_one('.game-result-clean-result')
        if meta is None or score is None or 'Chance ŽBL' not in meta.get_text(' ',strip=True):continue
        m=re.fullmatch(r'(\d+):(\d+)',score.get_text(strip=True))
        names=[n.get_text(' ',strip=True) for n in a.select('.game-detail-teams-names strong')]
        date=a.select_one('.date-small')
        d=re.search(r'(\d+)\.\s*(\d+)\.\s*(\d{4})\s+(\d\d?:\d\d)',date.get_text(' ',strip=True) if date else '')
        if not m or len(names)!=2 or not d:continue
        when=pd.Timestamp(f'{d[3]}-{int(d[2]):02d}-{int(d[1]):02d} {d[4]}',tz='Europe/Prague').tz_convert('UTC')
        rows.append(dict(event_id='ZAB_'+a['href'].rsplit('/',1)[-1],source_url=urljoin(SOURCES['zabiny'],a['href']),
            competition='CZ_W_ZBL',gender='Women',home=identity('zabiny',names[0]),away=identity('zabiny',names[1]),
            home_name=names[0],away_name=names[1],tarih_utc=when,home_score=int(m[1]),away_score=int(m[2]),score_verified=False))
    if not rows:raise ValueError('No dated finished senior women ZBL games found')
    return rows


def parse_vienna(html):
    soup=BeautifulSoup(html,'html.parser');rows=[]
    for card in soup.select('.bcv-bsl-card'):
        comp=card.select_one('.bcv-bsl-competition-strip');status=card.select_one('.bcv-bsl-status')
        if comp is None or status is None or status.get_text(strip=True)!='Final':continue
        text=comp.get_text(' ',strip=True)
        competition='AT_M_BSL' if 'Basketball Superliga' in text else 'ABA_M' if 'ABA League' in text else None
        if not competition:continue  # European results already exist; never count twice.
        names=[n.get_text(' ',strip=True) for n in card.select('.bcv-bsl-team-name')]
        dates=card.select('.bcv-bsl-meta-item');link=card.select_one('.bcv-bsl-card-hitarea[href]')
        date=next((n.get_text(' ',strip=True) for n in dates if '·' in n.get_text()),None)
        if len(names)!=2 or not date or link is None:raise ValueError('Changed official club layout')
        # Club page labels local Vienna times; venue time zones are not inferred.
        when=pd.Timestamp(pd.to_datetime(date,format='%A, %B %d, %Y · %I.%M %p')).tz_localize('Europe/Vienna').tz_convert('UTC')
        event=parse_qs(urlparse(link['href']).query).get('game',[None])[0]
        if not event:raise ValueError('Missing public fixture ID')
        rows.append(dict(event_id='VIE_'+event,source_url=link['href'],competition=competition,gender='Men',
            home=identity('vienna',names[0]),away=identity('vienna',names[1]),home_name=names[0],away_name=names[1],
            tarih_utc=when,home_score=None,away_score=None,score_verified=False))
    if not rows:raise ValueError('No finished BSL/ABA games found')
    return rows


def validate(g,now=None):
    g=g.copy();g['tarih_utc']=pd.to_datetime(g.tarih_utc,utc=True,errors='raise')
    now=pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    if g.empty or g.event_id.duplicated().any():raise ValueError('Empty or duplicate auxiliary fixtures')
    if (g.home==g.away).any() or (g.tarih_utc>=now).any():raise ValueError('Invalid or future finished fixture')
    allowed={'CZ_W_ZBL':'Women','AT_M_BSL':'Men','ABA_M':'Men'}
    for r in g.itertuples():
        if allowed.get(r.competition)!=r.gender:raise ValueError('Competition/gender mismatch')
        ids=[r.home,r.away]
        if r.gender=='Women' and any(t.startswith(('FEC_','AT_M_')) for t in ids):raise ValueError('Cross-gender identity')
        if r.gender=='Men' and any(t.startswith(('ECW_','CZ_W_')) for t in ids):raise ValueError('Cross-gender identity')
    return g.sort_values(['tarih_utc','event_id']).reset_index(drop=True)


def collect():
    captured=pd.Timestamp.now(tz='UTC')
    records=[]
    for source,parser in [('zabiny',parse_zabiny),('vienna',parse_vienna)]:
        records+=parser(fetch(SOURCES[source],refresh=True))
    g=validate(pd.DataFrame(records),captured)
    g['captured_at_utc']=captured;DATA.parent.mkdir(parents=True,exist_ok=True)
    if DATA.exists():
        old=pd.read_parquet(DATA);combined=pd.concat([old,g],ignore_index=True)
        for _,part in combined.groupby('event_id'):
            if len(part[['home','away','tarih_utc','competition','gender']].drop_duplicates())!=1:
                raise ValueError('Conflicting auxiliary fixture identity or date')
        g=combined.drop_duplicates('event_id',keep='first').sort_values(['tarih_utc','event_id'])
    temp=DATA.with_suffix('.part');g.to_parquet(temp,index=False);temp.replace(DATA)
    report=dict(captured_at_utc=captured.isoformat(),games=len(g),competitions=g.groupby('competition').size().to_dict(),
        source_urls=SOURCES,sha256=hashlib.sha256(DATA.read_bytes()).hexdigest(),
        limitations='Official club cohorts, incomplete historical coverage. Vienna score orientation not independently verified, so its scores are not stored. Czech scores are source facts but not independently verified. Only auxiliary workload uses these rows; no score-strength features. Source capture is not original historical publication time.')
    root=Path('docs/kanit/context');root.mkdir(parents=True,exist_ok=True)
    (root/'collection.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    return g


if __name__=='__main__':collect()
