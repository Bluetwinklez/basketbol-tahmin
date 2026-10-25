"""Inspect attribution-licensed score matrices; dates remain unverified.

These candidates are not training data. A score matrix alone cannot establish
when a game happened, and a community page is not official result confirmation.
"""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup
import pandas as pd

from bbtahmin.veri.public_bytes import fetch_bytes
from bbtahmin.football.data import write_json

PAGES={'EN1':'Premier_League','EN2':'EFL_Championship','DE1':'Bundesliga','ES1':'La_Liga',
       'IT1':'Serie_A','FR1':'Ligue_1','NL1':'Eredivisie','PT1':'Primeira_Liga','TR1':'Süper_Lig'}


def parse(raw):
    soup=BeautifulSoup(raw,'html.parser')
    if not soup.find(['a','link'],href=re.compile(r'^https?://creativecommons\.org/licenses/by-sa/4\.0(?:/|$)')):
        raise ValueError('Page-specific CC BY-SA 4.0 footer not found')
    tables=[t for t in soup.select('table') if re.search(r'Home\s*[\\/]\s*Away',t.get_text(' ',strip=True)[:80],re.I)]
    if len(tables)!=1:raise ValueError('Unique home/away score matrix required')
    rows=tables[0].find_all('tr');header=rows[0].find_all(['th','td'],recursive=False)[1:]
    columns=[cell.find('a')['href'] for cell in header]
    if not columns or len(columns)!=len(set(columns)):raise ValueError('Ambiguous matrix club headers')
    names={};body=[]
    for row in rows[1:]:
        cells=row.find_all(['th','td'],recursive=False)
        if len(cells)!=len(columns)+1:continue
        anchor=cells[0].find('a')
        if anchor is None or anchor['href'] not in columns:raise ValueError('Unknown matrix row identity')
        identity=anchor['href']
        if identity in names:raise ValueError('Duplicate matrix club row')
        names[identity]=anchor.get_text(' ',strip=True);body.append((identity,cells[1:]))
    if set(names)!=set(columns):raise ValueError('Incomplete matrix team identity')
    results=[]
    for home,cells in body:
        for away,cell in zip(columns,cells):
            for note in cell.select('sup'):note.decompose()
            text=cell.get_text(' ',strip=True)
            match=re.fullmatch(r'(\d{1,2})\s*[–−-]\s*(\d{1,2})',text)
            if match:
                if home==away:raise ValueError('Matrix score against same club')
                h,a=map(int,match.groups())
                if max(h,a)>30:raise ValueError('Invalid matrix score')
                results.append(dict(home_name=names[home],away_name=names[away],home_wiki=home,away_wiki=away,
                                    home_goals=h,away_goals=a,date=None))
            elif text not in ('','—','–','-','a') and not re.fullmatch(r'\d{1,2} [A-Z][a-z]{2}',text):
                raise ValueError(f'Unparsed matrix cell: {text}')
    return results


def main():
    clock=pd.Timestamp.now(tz='UTC');year=clock.year if clock.month>=7 else clock.year-1
    season=f'{year}–{str(year+1)[-2:]}'
    output=Path('.runtime/wiki_football');output.mkdir(parents=True,exist_ok=True)
    reports=[]
    for code,page in PAGES.items():
        url='https://en.wikipedia.org/wiki/'+quote(season+'_'+page)
        try:
            raw=fetch_bytes(url,refresh=True);rows=parse(raw)
            report=dict(league=code,season=season.replace('–','-'),source_url=url,
                        captured_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),sha256=hashlib.sha256(raw).hexdigest(),
                        license='CC-BY-SA-4.0',attribution='Wikipedia contributors',
                        license_url='https://creativecommons.org/licenses/by-sa/4.0/',rows=rows,
                        training_imported=False,note='No match dates in score matrix. Independent exact fixture/date/score checks required before any training import.')
            (output/(code+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
            reports.append(dict(league=code,dated=False,score_pairs=len(rows)))
        except Exception as exc:reports.append(dict(league=code,error=f'{type(exc).__name__}: {exc}'))
    (output/'report.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf8')
    write_json('data/football/licensed_source_refresh.json',dict(checked_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),results=reports))
    print(json.dumps(reports,ensure_ascii=False))
    return 1 if any('error' in r for r in reports) else 0


if __name__=='__main__':raise SystemExit(main())
