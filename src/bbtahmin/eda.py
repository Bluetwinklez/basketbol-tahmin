import pandas as pd
import numpy as np
from pathlib import Path

def run_eda():
    output=Path('docs/kanit')
    games=pd.read_parquet('data/maclar.parquet')
    games['margin']=(games.ev_skor-games.dep_skor).astype(float)
    games['total']=(games.ev_skor+games.dep_skor).astype(float)
    games['home_win']=(games.ev_skor>games.dep_skor).astype(int)
    games.groupby(['lig','sezon']).agg(n=('mac_id','size'),home_win_rate=('home_win','mean'),
        mean_margin=('margin','mean'),sd_margin=('margin','std'),
        mean_total=('total','mean'),sd_total=('total','std')).to_csv(output/'dagilimlar.csv')
    games[['margin','total','home_win']].corr().to_csv(output/'korelasyon.csv')
    summaries=[]
    for league,g in games.groupby('lig'):
        q1,q3=g.margin.quantile([.25,.75])
        summaries.append(dict(lig=league,n=len(g),margin_iqr_outliers=int(((g.margin<q1-1.5*(q3-q1))|(g.margin>q3+1.5*(q3-q1))).sum()),
            missing_neutral=int(g.tarafsiz_saha.isna().sum())))
    pd.DataFrame(summaries).to_csv(output/'aykirilar.csv',index=False)
    path=output/'tahminler.csv'
    if path.exists():
        p=pd.read_csv(path)
        p=p.merge(games[['mac_id','tarafsiz_saha','ev','dep']],on='mac_id',validate='many_to_one')
        from .backtest import scores
        rows=[]
        for (league,model),g in p.groupby(['lig','model']):
            for group,mask in [('home_favored',g.p>=.5),('away_favored',g.p<.5)]:
                if mask.any():
                    rows.append(dict(lig=league,model=model,group=group,n=int(mask.sum()),**scores(g.loc[mask,'y'],g.loc[mask,'p'])))
        pd.DataFrame(rows).to_csv(output/'hata_analizi.csv',index=False)
    # Descriptive distribution only; no filter based on these full-data summaries.
