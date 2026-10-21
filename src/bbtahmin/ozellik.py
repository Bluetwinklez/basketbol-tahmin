from collections import defaultdict,deque
from itertools import groupby
import numpy as np
import pandas as pd
from .elo import expected,update

# Rakibe göre düzeltilmiş sayı reytingleri için öğrenme hızları. Her biri ayrı özellik olur;
# hangisine ne kadar ağırlık verileceğini model eğitim penceresinde öğrenir.
RATING_RATES=(.04,.12)
RATING_FEATURES=[f'{kind}_{int(rate*100):02d}' for rate in RATING_RATES for kind in ('rmarj','rtop')]
FEATURES=['elo_diff','home','points_for_diff','points_against_diff','margin_diff','total_mean',
          'rest_diff','back_to_back_diff','load7_diff','road_streak_diff','games_diff','europe_load_diff',
          *RATING_FEATURES]
def build_features(games,k=20,advantage=50,shrink=.25,alpha=.2,mov=True):
    """Same UTC-day outcomes are withheld until all that day's predictions exist."""
    data=games.sort_values(['tarih_utc','mac_id']).copy()
    data['day_key']=data.tarih_utc.dt.floor('D')
    state={}
    europe=defaultdict(deque)
    league_points=defaultdict(lambda:[0.,0])  # lig -> [toplam sayı, takım-maç sayısı], yalnız geçmiş
    league_home=defaultdict(lambda:[0.,0])    # lig -> [ev-dep sayı farkı toplamı, tarafsız olmayan maç sayısı]
    league_mu={}                              # lig -> takım başına sayının üstel ortalaması (yıllar içinde kayan seviye)
    out=[]
    for day,batch in groupby(data.itertuples(index=False),key=lambda row:row.day_key):
        prepared=[]
        for row in batch:
            key=(row.lig,row.sezon)
            teams=[]
            for name in [row.ev,row.dep]:
                identity=(row.lig,name)
                if identity not in state:
                    state[identity]=dict(elo=1500.,season=row.sezon,pf=0.,pa=0.,n=0,seen=False,
                        dates=deque(),last=None,road=0,off={r:0. for r in RATING_RATES},dfn={r:0. for r in RATING_RATES})
                s=state[identity]
                if s['season']!=row.sezon:
                    s['elo']=1500+(1-shrink)*(s['elo']-1500)
                    for r in RATING_RATES:
                        s['off'][r]*=1-shrink; s['dfn'][r]*=1-shrink
                    s['season']=row.sezon
                    s['n']=0
                while s['dates'] and (day-s['dates'][0]).days>7: s['dates'].popleft()
                teams.append(s)
            h,a=teams
            total,count=league_points[row.lig]
            prior=total/count if count else 0.
            # Hiç maçı görülmemiş takım için ligin geçmiş ortalaması; 0 sayı sahte bir uç değer olurdu.
            hpf,hpa=(h['pf'],h['pa']) if h['seen'] else (prior,prior)
            apf,apa=(a['pf'],a['pa']) if a['seen'] else (prior,prior)
            neutral=False if pd.isna(row.tarafsiz_saha) else bool(row.tarafsiz_saha)
            home=0. if neutral else 1.
            rest=lambda s: min(30.,(day-s['last']).total_seconds()/86400) if s['last'] is not None else 30.
            rh,ra=rest(h),rest(a)
            loads=[]
            for name in [row.ev,row.dep]:
                while europe[name] and (day-europe[name][0]).days>7: europe[name].popleft()
                loads.append(len(europe[name]) if row.lig!='NBA' else 0)
            record=dict(mac_id=row.mac_id,elo_diff=h['elo']-a['elo'],home=home,
                points_for_diff=hpf-apf,points_against_diff=hpa-apa,
                margin_diff=(hpf-hpa)-(apf-apa),
                total_mean=(hpf+hpa+apf+apa)/2,
                rest_diff=rh-ra,back_to_back_diff=float(rh<=1)-float(ra<=1),
                load7_diff=len(h['dates'])-len(a['dates']),road_streak_diff=h['road']-a['road'],
                games_diff=h['n']-a['n'],europe_load_diff=loads[0]-loads[1],
                elo_p=expected(h['elo'],a['elo'],advantage*home))
            # Beklenen sayı = lig ortalaması ± ev avantajının yarısı + kendi hücumu − rakibin savunması.
            hsum,hcount=league_home[row.lig]
            half=home*(hsum/hcount if hcount else 0.)/2
            expected_points={}
            mu=league_mu.get(row.lig,prior)
            record['lig_ort']=2*mu   # maç öncesi lig toplam sayı seviyesi; toplam tahmini buna göre yapılır
            for r in RATING_RATES:
                eh=mu+half+h['off'][r]-a['dfn'][r]
                ea=mu-half+a['off'][r]-h['dfn'][r]
                expected_points[r]=(eh,ea)
                tag=f'{int(r*100):02d}'
                record[f'rmarj_{tag}']=eh-ea
                record[f'rtop_{tag}']=eh+ea
            out.append(record)
            prepared.append((row,h,a,home,expected_points))
        for row,h,a,home,expected_points in prepared:
            if pd.isna(row.ev_skor) or pd.isna(row.dep_skor): continue
            for r,(eh,ea) in expected_points.items():
                # Lig ortalaması henüz yoksa (ilk gün) hata sahte büyük olur; güncelleme atlanır.
                if league_points[row.lig][1]==0: break
                errh,erra=row.ev_skor-eh,row.dep_skor-ea
                h['off'][r]+=r*errh; a['dfn'][r]-=r*errh
                a['off'][r]+=r*erra; h['dfn'][r]-=r*erra
            if home:
                league_home[row.lig][0]+=float(row.ev_skor-row.dep_skor); league_home[row.lig][1]+=1
            mean=(row.ev_skor+row.dep_skor)/2
            league_mu[row.lig]=float(mean) if row.lig not in league_mu else league_mu[row.lig]+.01*(mean-league_mu[row.lig])
            h['elo'],a['elo']=update(h['elo'],a['elo'],row.ev_skor,row.dep_skor,k,advantage*home,mov)
            for s,pf,pa,is_away,name in [(h,row.ev_skor,row.dep_skor,False,row.ev),
                                       (a,row.dep_skor,row.ev_skor,True,row.dep)]:
                s['pf']=float(pf) if not s['n'] else alpha*pf+(1-alpha)*s['pf']
                s['pa']=float(pa) if not s['n'] else alpha*pa+(1-alpha)*s['pa']
                s['n']+=1; s['seen']=True; s['last']=day; s['dates'].append(day)
                league_points[row.lig][0]+=float(pf); league_points[row.lig][1]+=1
                s['road']=s['road']+1 if is_away else 0
                if row.lig in ('E','U'): europe[name].append(day)
    return pd.DataFrame(out).set_index('mac_id').loc[games.mac_id].reset_index()

def features_for_match(history,match,**params):
    """Query API never consumes target or subsequent outcomes."""
    cutoff=pd.Timestamp(match['tarih_utc']).tz_convert('UTC').floor('D')
    past=history[history.tarih_utc < cutoff]
    query=dict(match,ev_skor=None,dep_skor=None)
    combined=pd.DataFrame(past.to_dict('records')+[query])
    combined['tarih_utc']=pd.to_datetime(combined.tarih_utc,utc=True)
    return build_features(combined,**params).set_index('mac_id').loc[query['mac_id']]
