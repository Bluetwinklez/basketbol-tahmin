import numpy as np
def decimal_probability(odds):
    if odds<=1: raise ValueError('Ondalık oran >1 olmalı')
    return 1/odds
def american_decimal(odds):
    if abs(odds)<100: raise ValueError('Geçersiz Amerikan oranı')
    return 1+odds/100 if odds>0 else 1+100/abs(odds)
def no_vig(home,away):
    p=np.array([decimal_probability(home),decimal_probability(away)])
    return p/p.sum()
def simulate(probabilities,outcomes,home_odds,away_odds,threshold,method):
    equity=peak=1.
    staked=profit=drawdown=0.
    bets=0
    for p,y,ho,ao in zip(probabilities,outcomes,home_odds,away_odds):
        market=no_vig(ho,ao)
        side=int((p-market[0]) < ((1-p)-market[1]))
        q=p if side==0 else 1-p
        odd=ho if side==0 else ao
        if q-market[side]<threshold or q*odd<=1: continue
        fraction=.01 if method=='fixed' else .25*(q*odd-1)/(odd-1)
        stake=equity*min(fraction,1)
        result=stake*(odd-1) if bool(y)==(side==0) else -stake
        equity+=result; staked+=stake; profit+=result; bets+=1
        peak=max(peak,equity); drawdown=max(drawdown,(peak-equity)/peak)
    return dict(roi=profit/staked if staked else None,max_drawdown=drawdown,bets=bets,final_equity=equity)
