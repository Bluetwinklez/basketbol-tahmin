import pandas as pd
COLUMNS = ['mac_id','lig','sezon','tarih_utc','ev','dep','ev_skor','dep_skor','uzatma','ev_iy','dep_iy','tarafsiz_saha','asama','kaynak']
def normalize(rows):
    df = pd.DataFrame(rows,columns=COLUMNS)
    df['tarih_utc'] = pd.to_datetime(df['tarih_utc'],utc=True)
    for c in ['ev_skor','dep_skor','ev_iy','dep_iy']:
        df[c] = pd.to_numeric(df[c],errors='coerce').astype('Int64')
    for c in ['uzatma','tarafsiz_saha']:
        df[c] = df[c].astype('boolean')
    if df['mac_id'].duplicated().any():
        raise ValueError('Tekrarlı mac_id')
    if ((df.ev_skor == df.dep_skor) & df.ev_skor.notna()).any():
        raise ValueError('Berabere sonuç')
    return df.sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
