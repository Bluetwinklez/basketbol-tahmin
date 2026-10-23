import asyncio
import json

import pandas as pd
import pytest


def test_readonly_mcp_discovery_and_local_dataset_call(tmp_path,monkeypatch):
    pytest.importorskip('mcp.server',reason='Install .[mcp] to run the protocol test')
    from mcp import Client
    from bbtahmin.mcp_server import create_server
    (tmp_path/'data').mkdir()
    pd.DataFrame([dict(mac_id='m',lig='NBA',tarih_utc=pd.Timestamp('2026-01-01',tz='UTC'))]).to_parquet(tmp_path/'data/maclar.parquet')
    def no_network(*args,**kwargs):
        raise AssertionError('Local MCP calls must not fetch providers')
    monkeypatch.setattr('urllib.request.urlopen',no_network)
    async def check():
        async with Client(create_server(tmp_path)) as client:
            tools=(await client.list_tools()).tools
            assert {t.name for t in tools}=={'dataset_status','bulletin_events','predict_bulletin_event','bulletin_history','predict_live_cba','research_results','football_status','predict_football'}
            assert all(t.annotations.read_only_hint for t in tools)
            result=await client.call_tool('dataset_status',{})
            assert not result.is_error
            value=result.structured_content or json.loads(result.content[0].text)
            assert value['games']==1 and value['leagues']=={'NBA':1}
            football=await client.call_tool('football_status',{})
            assert not football.is_error
            result=await client.call_tool('bulletin_history',{'event_id':'not-present'})
            assert not result.is_error
            value=result.structured_content or json.loads(result.content[0].text)
            assert value['observations']==0
    asyncio.run(check())
