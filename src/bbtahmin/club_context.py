"""Auxiliary workload observations with explicit missingness; no invented domestic form."""
import pandas as pd
from .veri.club_context import DATA,validate

FEATURES=['aux_home_observed','aux_away_observed','aux_load7_diff','aux_load14_diff','aux_rest_diff']


def load():
    return validate(pd.read_parquet(DATA)) if DATA.exists() else pd.DataFrame()


def team_status(g,team,when):
    date=pd.Timestamp(when)
    if date.tzinfo is None:raise ValueError('Timezone-aware cutoff required')
    cutoff=date.tz_convert('UTC').floor('D')
    if g.empty:past=g
    else:past=g[((g.home==team)|(g.away==team))&(g.tarih_utc<cutoff)]
    if past.empty:return dict(observed=False,games_7d=None,games_14d=None,rest_days=None,latest_game_utc=None)
    last=past.tarih_utc.max();rest=(cutoff-last).total_seconds()/86400
    if rest>30:return dict(observed=False,games_7d=None,games_14d=None,rest_days=None,latest_game_utc=last.isoformat())
    return dict(observed=True,games_7d=int((past.tarih_utc>=cutoff-pd.Timedelta(days=7)).sum()),
        games_14d=int((past.tarih_utc>=cutoff-pd.Timedelta(days=14)).sum()),rest_days=rest,latest_game_utc=last.isoformat())


def features(games,context=None):
    context=load() if context is None else context;rows=[]
    for r in games.itertuples():
        h,a=team_status(context,r.ev,r.tarih_utc),team_status(context,r.dep,r.tarih_utc)
        # Unobserved values use zero only alongside an explicit availability indicator.
        value=lambda s,k:float(s[k]) if s['observed'] else 0.
        rows.append(dict(mac_id=r.mac_id,aux_home_observed=int(h['observed']),aux_away_observed=int(a['observed']),
            aux_load7_diff=value(h,'games_7d')-value(a,'games_7d'),
            aux_load14_diff=value(h,'games_14d')-value(a,'games_14d'),aux_rest_diff=value(h,'rest_days')-value(a,'rest_days')))
    return pd.DataFrame(rows)
