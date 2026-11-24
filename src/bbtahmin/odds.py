import numpy as np
def decimal_probability(odds):
    if not np.isfinite(odds) or odds<=1: raise ValueError('Ondalık oran sonlu ve >1 olmalı')
    return 1/odds
def american_decimal(odds):
    if not np.isfinite(odds) or abs(odds)<100: raise ValueError('Geçersiz Amerikan oranı')
    return 1+odds/100 if odds>0 else 1+100/abs(odds)
def no_vig(home,away):
    p=np.array([decimal_probability(home),decimal_probability(away)])
    return p/p.sum()
# NBA 2017-18…2022-23 (6.758 oranlı maç, ardışık sezon testi): kapanış oranı tek başına log loss 0,6070 /
# isabet %67,15; model tek başına 0,6277 / %64,84. Model ağırlığı 0,1 ile 0,6069 / %66,91: model piyasaya
# neredeyse hiçbir şey eklemiyor. Yalnız kapanışa yakın, düşük marjlı oranlar için doğrulandı.
MARKET_BLEND_MODEL_WEIGHT=.1
def market_blend(model_p,market_p,model_weight=MARKET_BLEND_MODEL_WEIGHT):
    """Logit uzayında model ve marjı çıkarılmış piyasa olasılığı karışımı (ev kazanır olasılığı)."""
    if not 0<=model_weight<=1: raise ValueError('Model ağırlığı 0-1 arasında olmalı')
    logit=lambda p:float(np.log(np.clip(p,1e-4,1-1e-4)/(1-np.clip(p,1e-4,1-1e-4))))
    return float(1/(1+np.exp(-(model_weight*logit(model_p)+(1-model_weight)*logit(market_p)))))
def simulate(probabilities,outcomes,home_odds,away_odds,threshold,method):
    if method not in ('fixed','kelly'): raise ValueError('method must be fixed or kelly')
    if not np.isfinite(threshold) or not 0<=threshold<=1: raise ValueError('Invalid threshold')
    if len({len(v) for v in (probabilities,outcomes,home_odds,away_odds)})!=1:
        raise ValueError('Simulation inputs must have equal lengths')
    equity=peak=1.
    staked=profit=drawdown=0.
    bets=0
    for p,y,ho,ao in zip(probabilities,outcomes,home_odds,away_odds):
        if not np.isfinite(p) or not 0<=p<=1 or y not in (0,1):
            raise ValueError('Invalid probability or outcome')
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
