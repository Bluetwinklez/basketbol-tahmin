"""Conservative same-fixture checks before basketball data reaches model fitting."""
import pandas as pd


def reconcile_results(frame):
    """Deduplicate identical day/team observations, reject ambiguous conflicts.

    Retain the first identity so existing ledger references remain usable.
    Reverse home/away games are distinct. A same-day doubleheader is ambiguous
    and requires provider review rather than silent double weighting.
    """
    g = frame.copy()
    dates = pd.to_datetime(g.tarih_utc, utc=True)
    # Turkish domestic calendar facts use the federation's local day.
    day = dates.dt.tz_convert('Europe/Istanbul').dt.strftime('%Y-%m-%d')
    keys = list(zip(g.lig, g.sezon, day, g.ev, g.dep))
    seen, keep = {}, []
    for position, (identity, row) in enumerate(zip(keys, g.to_dict('records'))):
        previous = seen.get(identity)
        if previous is None:
            seen[identity] = row; keep.append(position)
        elif any(previous[k] != row[k] for k in ('ev_skor','dep_skor')):
            raise ValueError('Conflicting cross-provider fixture results; manual review required')
    return g.iloc[keep].reset_index(drop=True)
