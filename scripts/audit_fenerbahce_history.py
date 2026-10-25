"""Export available earlier club history, without claiming calendar completeness."""
import pandas as pd

from bbtahmin.runtime_history import load
from bbtahmin.football.data import write_json


def main():
    cutoff = pd.Timestamp('2026-10-23T00:00Z')
    core = load()
    domestic = pd.read_parquet('data/competitions/TR_BSL.parquet')
    euro = core[(core.lig == 'E') & ((core.ev == 'ULK') | (core.dep == 'ULK'))].copy()
    bsl = domestic[(domestic.ev == 'TR_BSL_4') | (domestic.dep == 'TR_BSL_4')].copy()
    euro['club_team_id'] = 'ULK'
    bsl['club_team_id'] = 'TR_BSL_4'
    games = pd.concat([euro, bsl], ignore_index=True)
    games.tarih_utc = pd.to_datetime(games.tarih_utc, utc=True)
    games = games[games.tarih_utc < cutoff].sort_values(['tarih_utc', 'mac_id'], ascending=False)
    if games.mac_id.duplicated().any():
        raise ValueError('Duplicate club archive fixture')
    rows = []
    for game in games.head(50).to_dict('records'):
        home = game['ev'] == game['club_team_id']
        text = lambda key: game.get(key) if isinstance(game.get(key), str) else None
        rows.append(dict(event_id=game['mac_id'], competition=game['lig'], season=game['sezon'],
                         start_utc=game['tarih_utc'].isoformat(), listed_side='home' if home else 'away',
                         venue_verified=False,
                         opponent_id=game['dep'] if home else game['ev'],
                         points_for=int(game['ev_skor'] if home else game['dep_skor']),
                         points_against=int(game['dep_skor'] if home else game['ev_skor']),
                         source_url=text('source_url'), source_kind=text('source_kind') or text('kaynak')))
    write_json('docs/kanit/delivery_audit/fenerbahce_last50_candidates.json', dict(
        club='Fenerbahce senior men basketball', cutoff_exclusive_utc=cutoff.isoformat(),
        available_candidates=len(rows), matches=rows, complete_actual_last50_verified=False,
        complete_calendar_reference=None,
        missing_checks=['Turkish cup and Super Cup calendar',
                        'Independent BSL/EuroLeague calendar completeness',
                        'Cancelled, postponed, awarded games and neutral venues'],
        identity_basis='Explicit Fenerbahce names in official EuroLeague ULK and Turkish BSL TR_BSL_4 catalogs',
        note='Available club history only; not proof of actual latest 50 completed games. No model input or past forecast changed.'))


if __name__ == '__main__':
    main()
