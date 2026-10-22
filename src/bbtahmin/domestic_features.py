"""Lagged within-domestic-competition form, separate from European score updates."""
import numpy as np
import pandas as pd

COLUMNS=['dom_margin_diff','dom_total_mean','dom_home_missing','dom_away_missing','dom_home_stale','dom_away_stale']


def features(g,domestic,point_in_time=False):
    d=domestic.copy();d['tarih_utc']=pd.to_datetime(d.tarih_utc,utc=True)
    rows=[]
    for game in g.itertuples():
        cutoff=pd.Timestamp(game.tarih_utc).floor('D');past=d[d.tarih_utc<cutoff]
        if point_in_time:
            availability=pd.to_datetime(past.available_at_utc,utc=True).fillna(pd.to_datetime(past.captured_at_utc,utc=True))
            past=past[availability<=cutoff]
        stats=[]
        for team in (game.ev,game.dep):
            team_games=past[((past.ev==team)|(past.dep==team)) & (past.tarih_utc>=cutoff-pd.Timedelta(days=180))].tail(10)
            if len(team_games)==0:stats.append((0.,0.,1.,1.));continue
            margin=np.where(team_games.ev==team,team_games.ev_skor-team_games.dep_skor,team_games.dep_skor-team_games.ev_skor)
            # Prior shrinkage avoids interpreting one domestic blowout as established form.
            form=float(np.sum(margin)/(len(margin)+5))
            total=float((team_games.ev_skor+team_games.dep_skor).mean())
            stale=float((cutoff-team_games.tarih_utc.max()).days>45)
            stats.append((form,total,0.,stale))
        h,a=stats
        rows.append(dict(mac_id=game.mac_id,dom_margin_diff=h[0]-a[0],dom_total_mean=(h[1]+a[1])/2,
            dom_home_missing=h[2],dom_away_missing=a[2],dom_home_stale=h[3],dom_away_stale=a[3]))
    return pd.DataFrame(rows)
