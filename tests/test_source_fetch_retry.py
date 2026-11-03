import hashlib
import io
from urllib.error import HTTPError
import pytest
from bbtahmin.veri import competitions as c

URL='https://example.org/results'


def setup(tmp_path,monkeypatch):
    monkeypatch.setattr(c,'ROOT',tmp_path)
    p=tmp_path/(hashlib.sha256(URL.encode()).hexdigest()+'.html');p.write_text('old')
    sleeps=[];monkeypatch.setattr(c.time,'sleep',sleeps.append)
    return p,sleeps


def test_transient_503_recovers_and_cached_read_does_not_download(tmp_path,monkeypatch):
    p,sleeps=setup(tmp_path,monkeypatch);calls=[]
    def get(*a,**k):
        calls.append(1)
        if len(calls)==1:raise HTTPError(URL,503,'unavailable',{},None)
        return io.BytesIO('new ü'.encode())
    monkeypatch.setattr(c.urllib.request,'urlopen',get)
    assert c.fetch(URL,True)=='new ü'
    assert c.fetch(URL)=='new ü' and len(calls)==2 and sleeps==[1]
    assert not list(tmp_path.glob('*.part'))


@pytest.mark.parametrize('status,headers,attempts',[(503,{},3),(403,{},1),(429,{},1),(503,{'Retry-After':'60'},1),(503,{'Retry-After':'Wed, 01 Jan 2030 00:00:00 GMT'},1)])
def test_failure_preserves_previous_cache_and_stays_failure(tmp_path,monkeypatch,status,headers,attempts):
    p,sleeps=setup(tmp_path,monkeypatch);calls=[]
    def get(*a,**k):
        calls.append(1);raise HTTPError(URL,status,'failure',headers,None)
    monkeypatch.setattr(c.urllib.request,'urlopen',get)
    with pytest.raises(HTTPError):c.fetch(URL,True)
    assert p.read_text()=='old' and len(calls)==attempts
    assert sleeps==([1,2] if attempts==3 else [])


@pytest.mark.parametrize('payload,error',[(b'\xff',UnicodeDecodeError),(b'x'*6_000_001,ValueError)])
def test_invalid_response_does_not_poison_cache(tmp_path,monkeypatch,payload,error):
    p,_=setup(tmp_path,monkeypatch)
    monkeypatch.setattr(c.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(payload))
    with pytest.raises(error):c.fetch(URL,True)
    assert p.read_text()=='old'
