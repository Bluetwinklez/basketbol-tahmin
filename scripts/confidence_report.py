"""Report hit rate together with coverage and Wilson intervals; never hide abstentions."""
import math
from pathlib import Path

import numpy as np
import pandas as pd


def confidence_table(predictions,thresholds=(.5,.6,.65,.7,.75,.8,.85,.9)):
    if not predictions.p.between(0,1).all() or not predictions.y.isin([0,1]).all():
        raise ValueError('Invalid probability or outcome in prediction evidence')
    rows=[]
    for (league,model),g in predictions.groupby(['lig','model']):
        for threshold in thresholds:
            selected=g[np.maximum(g.p,1-g.p)>=threshold]
            n=len(selected)
            if n:
                correct=int(((selected.p>=.5)==(selected.y==1)).sum());rate=correct/n
                z=1.959963984540054;denom=1+z*z/n
                center=(rate+z*z/(2*n))/denom
                half=z*math.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/denom
                low,high=center-half,center+half
            else:
                correct=0;rate=low=high=None
            rows.append(dict(lig=league,model=model,threshold=threshold,total_games=len(g),
                             selected_games=n,coverage=n/len(g),correct=correct,
                             accuracy=rate,wilson95_low=low,wilson95_high=high))
    return pd.DataFrame(rows)


if __name__=='__main__':
    root=Path('docs/kanit/pregame_verified')
    path=root/'tahminler.csv'
    predictions=pd.read_csv(path if path.exists() else root/'tahminler.csv.gz')
    now=pd.Timestamp.now(tz='UTC');year=now.year if now.month>=7 else now.year-1
    predictions=predictions[predictions.sezon.str[:4].astype(int)<year]
    result=confidence_table(predictions)
    result.to_csv(root/'confidence.csv',index=False)
    print(result[(result.lig=='NBA')&(result.model=='skor')].to_string(index=False))
