"""Read-only local MCP tools backed by project files, not an external API.

Install the optional MCP extra; run python -m bbtahmin.mcp_server --root PATH.
Refreshing providers, placing bets and modifying the ledger are not MCP tools.
"""
import argparse
import contextlib
import json
import os
from pathlib import Path
import sys


def create_server(root):
    import pandas as pd
    from mcp.server import MCPServer
    from mcp.types import ToolAnnotations
    from .bulletin import list_events,predict_event

    root=Path(root).resolve()
    if not (root/'data/maclar.parquet').is_file():
        raise ValueError('Configured project root has no data/maclar.parquet')
    server=MCPServer('Basketball Research',instructions='Read-only pregame research. Report snapshot age and experimental status. Never interpret estimated probabilities as guaranteed accuracy.')
    readonly=ToolAnnotations(readOnlyHint=True,destructiveHint=False,idempotentHint=True,openWorldHint=False)

    @server.tool(annotations=readonly)
    def dataset_status() -> dict:
        """Show stored league coverage and whether the bulletin exists; no network requests."""
        g=pd.read_parquet(root/'data/maclar.parquet')
        cba=root/'data/cba_games.parquet'
        context=root/'data/context/club_games.parquet'
        governance=root/'docs/kanit/governance/coverage.json'
        coverage=json.loads(governance.read_text()) if governance.exists() else None
        return dict(coverage_inventory=coverage,auxiliary_club_games=len(pd.read_parquet(context)) if context.exists() else 0,games=len(g),leagues={str(k):int(v) for k,v in g.groupby('lig').size().items()},
                    asian_archives={p.stem:len(pd.read_parquet(p)) for p in (root/'data/asia').glob('*.parquet') if p.stem in ('KBL','JP_B1','JP_B2','PBA_GOV','PBA_COM','PBA_PHI')},
                    cba_games=len(pd.read_parquet(cba)) if cba.exists() else 0,
                    experimental_competitions={code:len(pd.read_parquet(path)) for code in ('ECW','FEC','VTB','ABA','UKR','TR_BSL') if (path:=root/f'data/competitions/{code}.parquet').exists()},
                    latest_game_utc=g.tarih_utc.max().isoformat(),bulletin_available=(root/'data/bulten/latest.json').exists())

    @server.tool(annotations=readonly)
    def bulletin_events(league: str | None = None,limit: int = 30) -> dict:
        """List future fixtures from the local bulletin with capture age; does not refresh."""
        if league is not None and league not in ('E','U','NBA','NBL','CBA','ECW','FEC','VTB','ABA','UKR','TR_BSL','KBL','JP_B1','JP_B2','PBA_GOV','PBA_COM','PBA_PHI'):
            raise ValueError('Unknown supported model league')
        return list_events(root,league,limit)

    @server.tool(annotations=readonly)
    def predict_bulletin_event(event_id: str) -> dict:
        """Compare the pregame model with a fresh local event's overtime-inclusive odds."""
        if Path.cwd().resolve()!=root:
            raise ValueError('Start the server through its --root entrypoint before predicting')
        with contextlib.redirect_stdout(sys.stderr):
            return predict_event(event_id,root)

    @server.tool(annotations=readonly)
    def bulletin_history(event_id: str, as_of: str | None = None, limit: int = 200) -> dict:
        """Read local pregame odds observations up to a past cutoff; never refresh."""
        from .market_history import history
        return history(event_id,root,as_of,limit)

    @server.tool(annotations=readonly)
    def predict_live_cba(home: str,away: str,home_score: int,away_score: int,
                         period: int,remaining: str,observed_at: str,replay: bool=False) -> dict:
        """Experimental CBA regulation projection from manual scores and MM:SS remaining.

        No automatic scoreboard feed. Stale inputs require explicit historical replay.
        """
        if Path.cwd().resolve()!=root:raise ValueError('Start through the --root entrypoint')
        from .cba_model import load
        from .takim_ad import coz
        from .live import predict
        g=load();codes=set(g.ev)|set(g.dep)
        with contextlib.redirect_stdout(sys.stderr):
            return predict(coz('CBA',home,codes),coz('CBA',away,codes),home_score,away_score,
                           period,remaining,observed_at,replay=replay)

    @server.tool(annotations=readonly)
    def research_results() -> dict:
        """Read fixed research summaries; these are not prospective live accuracy figures."""
        result={}
        for name,filename in [('pregame_verified','completed_seasons.csv'),
                              ('data_expansion_model','summary.csv'),('feature_research','summary.csv'),
                              ('calibration_research','summary.csv'),('competitions','summary.csv'),('adaptive','summary.csv'),('winner','summary.csv'),('protocol','strata.csv'),('asia_models','summary.csv'),('regional_models','summary.csv')]:
            path=root/f'docs/kanit/{name}/{filename}'
            if path.exists():
                t=pd.read_csv(path)
                result[name]=json.loads(t.to_json(orient='records'))
        return dict(exploratory=True,reports=result)
    return server


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,help='Absolute path to the project checkout')
    args=parser.parse_args();root=Path(args.root).resolve()
    server=create_server(root)
    os.chdir(root)
    server.run(transport='stdio')


if __name__=='__main__':
    main()
