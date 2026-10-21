import json
def collect(http, competition, year):
    url=f'https://api-live.euroleague.net/v2/competitions/{competition}/seasons/{competition}{year}/games'
    payload=json.loads(http.get(url))
    games=payload['data']
    if payload.get('total',len(games)) != len(games):
        raise ValueError('Sayfalama: eksik maç')
    rows=[]
    for g in games:
        if not g.get('played') or g['local']['score']==g['road']['score']:
            continue
        h,a=g['local'],g['road']
        def halftime(t):
            p=t.get('partials') or {}
            v=[p.get('partials1'),p.get('partials2')]
            return sum(v) if all(x is not None for x in v) else None
        phase=g.get('phaseType',{}).get('code','')
        rows.append(dict(mac_id=g['identifier'],lig=competition,sezon=f'{year}-{str(year+1)[-2:]}',
            tarih_utc=g['utcDate'],ev=h['club']['code'],dep=a['club']['code'],
            ev_skor=h['score'],dep_skor=a['score'],ev_iy=halftime(h),dep_iy=halftime(a),
            uzatma=bool((h.get('partials') or {}).get('extraPeriods')),
            tarafsiz_saha=bool(g.get('isNeutralVenue')) or phase=='FF',
            asama='final-four' if phase=='FF' else 'playoff' if phase in ('PO','QF','4F','8F','2F','Final','PI') else 'normal',kaynak=url))
    return rows,dict(listed=len(games),played=sum(bool(g.get('played')) for g in games),
        excluded_ties=sum(bool(g.get('played')) and g['local']['score']==g['road']['score'] for g in games))
