"""Paired fixture comparisons, day-block uncertainty and observable strata."""
import numpy as np
import pandas as pd


def metrics(y,p):
    y=np.asarray(y);p=np.asarray(p,dtype=float)
    if len(y)==0:return dict(n=0,accuracy=None,log_loss=None,brier=None)
    if not np.isin(y,[0,1]).all() or not np.isfinite(p).all() or not ((0<=p)&(p<=1)).all():raise ValueError('Invalid probability or label')
    clipped=np.clip(p,1e-12,1-1e-12)
    return dict(n=len(y),accuracy=float(np.mean((p>=.5)==y)),
        log_loss=float(-np.mean(y*np.log(clipped)+(1-y)*np.log(1-clipped))),brier=float(np.mean((p-y)**2)))


def paired(reference,candidate,replicates=1000,seed=20261022):
    keys=['mac_id','y','day']
    if reference.mac_id.duplicated().any() or candidate.mac_id.duplicated().any():raise ValueError('One record per fixture required')
    if set(reference.mac_id)!=set(candidate.mac_id):raise ValueError('Identical fixture cohort required')
    a=reference.set_index('mac_id').sort_index();b=candidate.set_index('mac_id').loc[a.index]
    if not a[['y','day']].equals(b[['y','day']]):raise ValueError('Outcome/day mismatch')
    metrics(a.y,a.p);metrics(b.y,b.p)
    y=a.y.to_numpy();pa=np.clip(a.p.to_numpy(),1e-12,1-1e-12);pb=np.clip(b.p.to_numpy(),1e-12,1-1e-12)
    if not np.isfinite(np.r_[pa,pb]).all():raise ValueError('Non-finite comparison probabilities')
    delta=np.column_stack([((pb>=.5)==y).astype(float)-((pa>=.5)==y).astype(float),
        -(y*np.log(pb)+(1-y)*np.log(1-pb))+(y*np.log(pa)+(1-y)*np.log(1-pa)),(pb-y)**2-(pa-y)**2])
    blocks=[delta[a.day.to_numpy()==d] for d in sorted(a.day.unique())]
    if not blocks:raise ValueError('Empty comparison')
    rng=np.random.default_rng(seed);samples=np.array([np.concatenate([blocks[i] for i in rng.integers(0,len(blocks),len(blocks))]).mean(axis=0) for _ in range(replicates)])
    result={}
    for i,name in enumerate(('accuracy','log_loss','brier')):
        lo,hi=np.quantile(samples[:,i],[.025,.975]);result[name]=dict(delta=float(delta[:,i].mean()),day_block_95_interval=[float(lo),float(hi)])
    return dict(n=len(a),day_blocks=len(blocks),replicates=replicates,seed=seed,changes=result,
        interpretation='Candidate minus reference. Higher accuracy / lower losses are better. Exploratory day-block percentile intervals; few blocks and repeated model searches limit inference.')


def equal_coverage(reference,candidate,fractions=(.25,.5,.75,1.)):
    if set(reference.mac_id)!=set(candidate.mac_id):raise ValueError('Identical fixture cohort required')
    rows=[]
    for label,p in [('reference',reference),('candidate',candidate)]:
        ordered=p.assign(confidence=np.maximum(p.p,1-p.p)).sort_values(['confidence','mac_id'],ascending=[False,True])
        for fraction in fractions:
            n=max(1,int(np.ceil(len(p)*fraction)));part=ordered.head(n)
            rows.append(dict(variant=label,requested_coverage=fraction,coverage=n/len(p),**metrics(part.y,part.p)))
    return rows
