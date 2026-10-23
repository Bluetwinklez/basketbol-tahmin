"""Archive actual pregame reports and compute lagged rotation context without absence inference."""
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
from .quality import timestamp


def archive_injuries(when=None,hours=2):
    from .veri.sakatlik import son_rapor,URL
    requested=timestamp(when or pd.Timestamp.now(tz='UTC'))
    if requested>pd.Timestamp.now(tz='UTC'):raise ValueError('Future report capture time forbidden')
    table=son_rapor(requested,geriye_saat=hours)
    now=pd.Timestamp.now(tz='UTC')
    if 'published_at_utc' not in table.attrs:raise ValueError('No official report available in requested bounded window')
    published=timestamp(table.attrs['published_at_utc']);name=table.attrs['rapor'].removesuffix(' ET')
    source='https://ak-static.cms.nba.com/referee/injury/Injury-Report_'+name+'.pdf'
    if published>now:raise ValueError('Future injury report')
    records=json.loads(table.to_json(orient='records'))
    payload=dict(published_at_utc=published.isoformat(),captured_at_utc=now.isoformat(),source_url=source,
        records=records,source_pdf_sha256=table.attrs.get('source_pdf_sha256'),used_in_default_model=False,
        note='Actual pregame report observation. Unknown game dates remain null. Missing report/player is not an available-player assertion. No historical backfill or retrospective participant inference.')
    raw=json.dumps(payload,sort_keys=True,allow_nan=False).encode();digest=hashlib.sha256(raw).hexdigest()
    root=Path('data/observations/injuries');root.mkdir(parents=True,exist_ok=True)
    target=root/(pd.Timestamp(published).strftime('%Y%m%dT%H%M%SZ')+'_'+digest[:12]+'.json')
    with target.open('x') as f:json.dump(payload,f,indent=2,ensure_ascii=False,allow_nan=False)
    return dict(path=str(target),rows=len(records),published_at_utc=published.isoformat(),sha256=digest)


def injuries_asof(reports,away,home,fixture_time,cutoff):
    cutoff=timestamp(cutoff);fixture=timestamp(fixture_time);day=fixture.tz_convert('America/New_York').strftime('%Y-%m-%d')
    valid=[]
    for report in reports:
        published=timestamp(report['published_at_utc']);captured=timestamp(report['captured_at_utc'])
        if not published<=captured<=cutoff or cutoff-published>pd.Timedelta(hours=48):continue
        rows=[r for r in report['records'] if r.get('mac')==away+'@'+home and r.get('game_date')==day]
        if rows:valid.append((published,captured,rows))
    if not valid:return dict(known=False,players=None,reason='No timely observed report matched to this fixture date')
    published,captured,rows=max(valid,key=lambda item:(item[0],item[1]))
    return dict(known=True,players=rows,published_at_utc=published.isoformat(),captured_at_utc=captured.isoformat())


def rotation(history,team,when,league_minutes=48):
    """Historical player rows only. Does not know target-game participants or assert injuries."""
    cutoff=timestamp(when).floor('D')
    required={'takim','oyuncu_id','tarih_utc','mac_id','dakika','pm'}
    if required-set(history.columns):raise ValueError('Missing lagged player schema')
    h=history[(history.takim==team)&(history.tarih_utc<cutoff)&(history.tarih_utc>=cutoff-pd.Timedelta(days=60))].copy()
    if h.empty:return dict(known=False,players=None,continuity=None,minute_concentration=None)
    if h.duplicated(['mac_id','oyuncu_id']).any():raise ValueError('Duplicate player appearances')
    if not np.isfinite(h[['dakika','pm']].to_numpy(float)).all() or (h.dakika<0).any():raise ValueError('Invalid player values')
    ids=h.groupby('mac_id').tarih_utc.max().sort_values().tail(10).index;h=h[h.mac_id.isin(ids)]
    table=h.pivot(index='mac_id',columns='oyuncu_id',values='dakika').reindex(ids).fillna(0.)
    age=(cutoff-h.groupby('mac_id').tarih_utc.max().reindex(ids)).dt.total_seconds()/86400
    weights=np.exp(-np.log(2)*age.to_numpy()/14);minute=np.average(table.to_numpy(),axis=0,weights=weights)
    if minute.sum()<=0:return dict(known=False,players=None,continuity=None,minute_concentration=None)
    shares=minute/minute.sum();last=table.iloc[-1].to_numpy();last_shares=last/last.sum() if last.sum()>0 else shares
    continuity=float(np.minimum(shares,last_shares).sum());players=[]
    for player,share,expected in zip(table.columns,shares,minute):
        p=h[h.oyuncu_id==player];minutes=float(p.dakika.sum())
        # Historical +/- is descriptive and shrunk; not a causal player value estimate.
        impact=float(p.pm.sum()*league_minutes/(minutes+200))
        players.append(dict(player_id=str(player),expected_minutes=float(min(expected,league_minutes)),
            recent_observed_minutes=float(expected),minute_share=float(share),shrunk_plus_minus_rate=impact))
    return dict(known=True,prior_games=len(ids),players=players,continuity=continuity,
        summed_recent_minutes=float(minute.sum()),minute_concentration=float(np.sum(shares**2)),last_observed_at_utc=h.tarih_utc.max().isoformat(),
        note='Lagged rotation estimate from observed past appearances, not a confirmed target roster. No missing-current-participant feature.')


def load_players():
    games=pd.read_parquet('data/maclar.parquet');games=games[games.lig=='NBA']
    p=pd.read_parquet('data/nba_oyuncu_mac.parquet')
    merged=p.merge(games[['mac_id','tarih_utc','ev','dep']],on='mac_id',validate='many_to_one')
    if not merged.rol.isin(['ev','dep']).all():raise ValueError('Unknown player home/away role')
    merged['takim']=np.where(merged.rol=='ev',merged.ev,merged.dep)
    return merged


def context(home,away,when,as_of=None):
    if home==away:raise ValueError('Same team on both sides')
    if as_of is not None and timestamp(as_of)>pd.Timestamp.now(tz='UTC'):raise ValueError('Future information cutoff forbidden')
    fixture=timestamp(when);cutoff=min(fixture,timestamp(as_of or pd.Timestamp.now(tz='UTC')))
    players=load_players();reports=[json.loads(p.read_text()) for p in sorted(Path('data/observations/injuries').glob('*.json'))]
    return dict(league='NBA',home=home,away=away,fixture_utc=fixture.isoformat(),information_cutoff_utc=cutoff.isoformat(),
        home_rotation=rotation(players,home,cutoff),away_rotation=rotation(players,away,cutoff),
        injury_observation=injuries_asof(reports,away,home,fixture,cutoff),used_in_default_model=False,
        note='Expected rotation is descriptive lagged context; actual target-game participants are never inputs. Effects on winning probability require prospective validation.')
