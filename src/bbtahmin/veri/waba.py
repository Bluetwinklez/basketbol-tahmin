"""Senior WABA results from the public widget embedded by the official league.

JavaScript string literals are decoded as data, never evaluated. Source timezone
is not certified, so dates retain day precision with an extra modeling-day embargo.
"""
import hashlib, re, time
from urllib.parse import urlencode
from bs4 import BeautifulSoup
import pandas as pd
from .competitions import fetch
from .regional import save, key

PAGE='https://waba-league.com/season/schedule-3/'
SERVICE='https://widgets.baskethotel.com/widget-service/show?'


def unescape(value):
    escapes={'n':'\n','r':'\r','t':'\t','\\':'\\',"'":"'",'"':'"','/':'/'}
    def convert(m):
        if m[1].startswith('u'):return chr(int(m[1][1:],16))
        if m[1] not in escapes:raise ValueError('Unsupported widget string escape')
        return escapes[m[1]]
    return re.sub(r'\\(u[0-9a-fA-F]{4}|.)',convert,value)


def html(response):
    match=re.search(r"MBT\.API\.update\('[^']+',\s*'((?:\\.|[^'\\])*)'\)",response)
    if not match:raise ValueError('Changed public widget response')
    return unescape(match[1])


def parse(text,year,url,captured):
    soup=BeautifulSoup(text,'html.parser');rows=[];excluded=0
    for tr in soup.select('tr[id*="-schedule-line-container-"]'):
        cells=tr.find_all('td',recursive=False)
        if len(cells)<4:raise ValueError('Changed senior WABA result row')
        date=cells[0].get_text(' ',strip=True);score=cells[2].get_text('',strip=True)
        match=re.fullmatch(r'(\d{2}\.\d{2}\.\d{4})(?:\s+\d{2}:\d{2})?',date)
        points=re.fullmatch(r'(\d+)\s*:\s*(\d+)',score)
        if not match or not points:excluded+=1;continue
        day=pd.Timestamp(pd.to_datetime(match[1],format='%d.%m.%Y'),tz='UTC')
        hs,ds=map(int,points.groups())
        if min(hs,ds)<=0 or hs==ds or day+pd.Timedelta(days=2)>pd.Timestamp(captured):excluded+=1;continue
        if not year<=day.year<=year+1:raise ValueError('Wrong WABA season response')
        names=[cells[i].get_text(' ',strip=True) for i in (1,3)]
        explicit={'Cinkarna Celje':'ECW_58477','Montana 2003':'ECW_813'}
        identity=lambda n:explicit.get(n,key('WABA_W_',n))
        gid=tr['id'].rsplit('-',1)[-1]
        if not gid.isdigit():raise ValueError('Missing WABA game identity')
        rows.append(dict(mac_id='WABA_W_'+gid,lig='WABA_W',sezon=f'{year}-{str(year+1)[-2:]}',
            tarih_utc=day,model_time_utc=day+pd.Timedelta(days=1),source_date_label=date,
            ev=identity(names[0]),dep=identity(names[1]),ev_skor=hs,dep_skor=ds,
            home_name=names[0],away_name=names[1],gender='Women',regulation_minutes=40,tarafsiz_saha=False,
            source_url=PAGE,listing_url=PAGE,captured_at_utc=captured,available_at_utc=None,date_precision='day',
            venue_name=cells[4].get_text(' ',strip=True) if len(cells)>4 else None,neutral_venue_verified=False))
    return rows,excluded


def collect(years=(2022,2023,2024,2025,2026)):
    page=fetch(PAGE,refresh=True)
    if not re.search(r'fibaLeagueId\s*=\s*31913\s*;',page):raise ValueError('Not verified senior WABA league')
    config=re.search(r'https://widgets\.baskethotel\.com/static/api/[a-z0-9]+/config\.js',page)
    if not config:raise ValueError('Official widget configuration missing')
    cfg=fetch(config[0]);api=re.search(r"MBT\.API\.ApiId\s*=\s*'([a-z0-9]+)'",cfg)
    if not api:raise ValueError('Published widget identifier missing')
    def request(season=None,state=None,page_number=1):
        p={'api':api[1],'lang':'en','nnav':'1','request[0][container]':'schedule-long-widget',
           'request[0][widget]':'303'}
        if season is None:
            p.update({'request[0][param][league_id]':'31913','request[0][param][show_season_selector]':'1'})
        else:
            p.update({'request[0][container]':'253-303-container','request[0][part]':'schedule_and_results',
                'request[0][state]':state,'request[0][param][season_id]':season,
                'request[0][param][filter][type]':'results_only','request[0][param][page]':page_number})
        url=SERVICE+urlencode(p);return url,html(fetch(url,refresh=season is None or int(year)>=2026))
    _,initial=request();soup=BeautifulSoup(initial,'html.parser')
    catalog={o.get_text(strip=True):o['value'] for o in soup.select('select[id$="filter-season"] option')}
    match=re.search(r"state:\s*'([^']+)'",initial)
    if not match:raise ValueError('Published widget state missing')
    records=[];sources=[];counts=[];captured=pd.Timestamp.now(tz='UTC').isoformat()
    for year in years:
        season=catalog.get(f'{year}-{year+1}')
        if season is None:raise ValueError('Requested season not in official WABA selector')
        ids=set();accepted=0;excluded=0
        for page_number in range(1,31):
            url,text=request(season,match[1],page_number);rows,n=parse(text,year,url,captured)
            current={r['mac_id'] for r in rows}
            if ids & current:raise ValueError('Repeated WABA pagination; refusing duplicate pages')
            ids|=current;records+=rows;accepted+=len(rows);excluded+=n
            sources.append(dict(listing_url=PAGE,provider_season_id=season,page=page_number,
                response_html_sha256=hashlib.sha256(text.encode()).hexdigest()))
            # Only request another page when the returned UI advertises it.
            next_pages={int(n) for n in re.findall(r'id=["\'][^"\']+-page-(\d+)["\']',text)}
            if not any(n>page_number for n in next_pages):break
            time.sleep(1.1)
        else:raise ValueError('WABA pagination bound reached')
        counts.append(dict(year=year,accepted=accepted,excluded=excluded,pages=page_number))
        print('WABA',year,accepted,flush=True)
    return save('WABA_W',records,dict(source=PAGE,sources=sources,counts=counts,captured_at_utc=captured,
        coverage='Senior league 31913 only; all returned results pages with advertised pagination. Exact source timezones, neutral sites, overtime, publication time and completeness unverified. Date-only rows use model_time_utc one day after their source calendar date; same-UTC-day withholding then provides an extra day embargo. Not a domestic country-membership source.'))


if __name__=='__main__':collect()
