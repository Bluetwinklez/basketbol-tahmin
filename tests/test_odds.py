import pandas as pd
import pytest
from bbtahmin.odds import american_decimal,no_vig
from bbtahmin.veri.nba_odds import moneyline,parse_season,match
from bbtahmin.veri.schema import normalize

HEADER='<tr><td>Date</td><td>Rot</td><td>VH</td><td>Team</td><td>1st</td><td>2nd</td><td>3rd</td><td>4th</td><td>Final</td><td>Open</td><td>Close</td><td>ML</td><td>2H</td></tr>'
def line(date,vh,team,final,ml):
    return f'<tr><td>{date}</td><td>501</td><td>{vh}</td><td>{team}</td><td>25</td><td>25</td><td>25</td><td>25</td><td>{final}</td><td>220</td><td>220</td><td>{ml}</td><td>110</td></tr>'
HTML='<table>'+HEADER+''.join([
    line('1019','V','Brooklyn',104,'105'),line('1019','H','Milwaukee',127,'-125'),
    line('1019','V','GoldenState',121,'+140'),line('1019','H','LA Lakers',114,'-160'),
    line('1020','V','Gotham',90,'110'),line('1020','H','Boston',100,'-130'),
    line('105','V','Utah',99,'NL'),line('105','H','Denver',101,'-150'),
    line('810','N','Boston',100,'-200'),line('810','N','Miami',90,'170')])+'</table>'

def test_moneyline_signs():
    assert moneyline('+155')==155 and moneyline('-125')==-125
    assert moneyline('NL') is None and moneyline('pk') is None and moneyline('2.5') is None

def test_parse_season_pairs_and_years():
    rows=parse_season(HTML,2021)
    assert len(rows)==5
    first=rows[0]
    assert (first['ev_adi'],first['dep_adi'],first['ev_ml'],first['dep_ml'])==('Milwaukee','Brooklyn',-125,105)
    assert first['tarih_yerel']==pd.Timestamp('2021-10-19')
    assert rows[3]['tarih_yerel']==pd.Timestamp('2022-01-05')
    assert rows[4]['tarafsiz'] and rows[4]['tarih_yerel']==pd.Timestamp('2021-08-10')

def test_odds_to_probability_round_trip():
    home,away=american_decimal(-125),american_decimal(105)
    p=no_vig(home,away)
    assert p.sum()==pytest.approx(1) and p[0]>.5
    assert 1/home+1/away>1  # vig present before removal

def test_threshold_chosen_only_from_prior_seasons():
    import numpy as np
    from bbtahmin.backtest import market_and_betting
    rng=np.random.default_rng(0)
    rows,odds=[],[]
    for s,season in enumerate(['2018-19','2019-20','2020-21']):
        for i in range(200):
            mid=f'NBA_{s}_{i}'
            p=float(rng.uniform(.3,.7))
            y=int(rng.uniform()<p)
            for model in ['elo','logistic','hist_gradient_boosting','mov_elo']:
                rows.append(dict(mac_id=mid,lig='NBA',sezon=season,model=model,y=y,p=p))
            odds.append(dict(mac_id=mid,ev_ml=-110,dep_ml=-110))
    pred,odds=pd.DataFrame(rows),pd.DataFrame(odds)
    market,bets=market_and_betting(pred,odds)
    assert set(market.model)>={'piyasa_vigsiz','logistic'}
    first=bets[bets.sezon=='2018-19']
    assert (first.status!='ok').all()
    later=bets[(bets.sezon=='2020-21')&(bets.status=='ok')]
    assert len(later)==6 and later.threshold.isin([.01,.02,.03,.05,.075,.1]).all()
    # Test sezonunun sonuçları değişse de seçilen eşik değişmemeli.
    flipped=pred.copy()
    flipped.loc[flipped.sezon=='2020-21','y']=1-flipped.loc[flipped.sezon=='2020-21','y']
    _,bets2=market_and_betting(flipped,odds)
    a=bets[bets.status=='ok'].set_index(['sezon','model','method']).threshold
    b=bets2[bets2.status=='ok'].set_index(['sezon','model','method']).threshold
    pd.testing.assert_series_equal(a,b)

def test_match_counts_unmatched():
    def game(i,day,hour,home,away,hs,as_,neutral=False):
        return dict(mac_id=f'NBA_{i}',lig='NBA',sezon='2021-22',tarih_utc=pd.Timestamp(day+f' {hour}:00',tz='UTC'),
            ev=home,dep=away,ev_skor=hs,dep_skor=as_,uzatma=False,ev_iy=None,dep_iy=None,
            tarafsiz_saha=neutral,asama='normal',kaynak='fixture')
    # 23:30 UTC on 19 Oct = 19:30 US-Eastern on 19 Oct; 01:00 UTC on 6 Jan = 20:00 Eastern on 5 Jan.
    games=normalize([game(1,'2021-10-19','23','MIL','BRK',127,104),game(2,'2021-10-20','02','LAL','GSW',114,121),
        game(3,'2022-01-06','01','DEN','UTA',101,99),game(4,'2021-08-10','20','MIA','BOS',90,100,True)])
    matched,unmatched=match(parse_season(HTML,2021),games)
    assert set(matched.mac_id)=={'NBA_1','NBA_2','NBA_4'}
    neutral=matched.set_index('mac_id').loc['NBA_4']
    assert (neutral.ev_ml,neutral.dep_ml)==(170,-200)
    reasons=sorted(u['neden'] for u in unmatched)
    assert len(unmatched)==2 and reasons[0]=='Eşleşmeyen takım: Gotham' and reasons[1]=='Moneyline yok'

def test_harman_uses_only_prior_seasons_and_learns_market_weight():
    import numpy as np
    from bbtahmin.backtest import harman_fit,harman_p
    rng=np.random.default_rng(1)
    market=rng.uniform(.2,.8,4000)
    y=(rng.uniform(size=4000)<market).astype(int)
    part=pd.DataFrame(dict(market=market,p=rng.uniform(.2,.8,4000),y=y))
    a,bm,bp=harman_fit(part)
    assert bm==pytest.approx(1,abs=.15) and abs(bp)<.15  # gürültü modelin ağırlığı ~0
    assert harman_p([0.,1.,0.],np.array([.7]),np.array([.1]))[0]==pytest.approx(.7)

def test_tahmin_harman_needs_odds_and_coefficients(tmp_path):
    import json
    from bbtahmin.tahmin import harman
    yol=tmp_path/'harman.json'
    yol.write_text(json.dumps({'NBA':{'skor':{'katsayi':[0.,1.,0.]}}}),'utf8')
    t=dict(lig='NBA',model='skor',ev_kazanir=.4,piyasa_ev=.65)
    assert harman(t,yol)==pytest.approx(.65)
    assert harman(dict(t,piyasa_ev=None),yol) is None
    assert harman(dict(t,lig='E'),yol) is None
    yol.write_text(json.dumps({'NBA':{'skor':{'katsayi':[0.,1.,0.],'sezonlar':['2021-22','2022-23']}}}),'utf8')
    assert harman(t,yol) is None  # no cutoff: cannot establish prior training
    assert harman(dict(t,tarih_utc='2022-12-01T20:00Z'),yol) is None
    assert harman(dict(t,tarih_utc='2021-12-01T20:00Z'),yol) is None
    assert harman(dict(t,tarih_utc='2023-12-01T20:00Z'),yol)==pytest.approx(.65)
