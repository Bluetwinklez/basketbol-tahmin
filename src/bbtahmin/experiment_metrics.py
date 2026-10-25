"""Shared binary/multiclass, paired-day evaluation for fixed research policies."""
import numpy as np


def validate(y, probabilities):
    y=np.asarray(y)
    p=np.asarray(probabilities,dtype=float)
    if (p.ndim!=2 or p.shape[1] not in (2,3) or len(y)!=len(p)
            or y.ndim!=1 or not np.isfinite(p).all() or (p<0).any() or (p>1).any()
            or not np.allclose(p.sum(axis=1),1.,atol=1e-8)
            or not np.isin(y,np.arange(p.shape[1])).all()):
        raise ValueError('Finite normalized two/three-class probabilities and aligned class labels required')
    return y.astype(int),p


def losses(y,p):
    y,p=validate(y,p)
    target=np.eye(p.shape[1])[y]
    return np.column_stack([(p.argmax(axis=1)==y).astype(float),
                            -np.log(np.clip(p[np.arange(len(y)),y],1e-15,1)),
                            ((p-target)**2).sum(axis=1)])


def metrics(y,p,selected=None):
    y,p=validate(y,p)
    if selected is None: selected=np.ones(len(y),dtype=bool)
    selected=np.asarray(selected)
    if selected.shape!=(len(y),) or selected.dtype.kind!='b':
        raise ValueError('One boolean selection flag per fixture required')
    def summarize(mask):
        n=int(mask.sum())
        if not n: return dict(games=0,accuracy=None,log_loss=None,brier=None)
        scores=losses(y[mask],p[mask]).mean(axis=0)
        return dict(games=n,accuracy=float(scores[0]),log_loss=float(scores[1]),brier=float(scores[2]))
    predictions=p.argmax(axis=1); confidence=p.max(axis=1)
    confusion=np.zeros((p.shape[1],p.shape[1]),dtype=int)
    np.add.at(confusion,(y,predictions),1)
    bins=[]
    bin_ids=np.minimum(9,np.floor(confidence*10).astype(int))
    for bin_id in range(10):
        lo,hi=bin_id/10,(bin_id+1)/10
        mask=bin_ids==bin_id
        if mask.any(): bins.append(dict(lower=float(lo),upper=float(min(hi,1.)),games=int(mask.sum()),
                                       mean_confidence=float(confidence[mask].mean()),
                                       accuracy=float((predictions[mask]==y[mask]).mean())))
    return dict(all=summarize(np.ones(len(y),bool)),selected=summarize(selected),
                coverage=float(selected.mean()) if len(y) else 0.,confusion_actual_by_predicted=confusion.tolist(),
                confidence_bins=bins,
                brier_convention='Sum over classes; binary value is twice the one-probability binary Brier.')


def paired(rows,reference,candidate,replicates=1000,seed=20261025):
    """Rows are keyed by fixture/day/y; candidates cannot silently change cohort."""
    if type(replicates) is not int or replicates<2: raise ValueError('At least two bootstrap replicates required')
    def index(variant):
        subset=[r for r in rows if r['variant']==variant]
        result={r['event_id']:r for r in subset}
        if len(result)!=len(subset): raise ValueError('Duplicate experiment fixture')
        return result
    a,b=index(reference),index(candidate)
    if not a or set(a)!=set(b): raise ValueError('Identical nonempty fixture cohorts required')
    ids=sorted(a)
    if any((a[i]['day'],a[i]['y'])!=(b[i]['day'],b[i]['y']) for i in ids):
        raise ValueError('Paired day/outcome mismatch')
    y=[a[i]['y'] for i in ids];pa=[a[i]['p'] for i in ids];pb=[b[i]['p'] for i in ids]
    delta=losses(y,pb)-losses(y,pa)
    days=np.array([a[i]['day'] for i in ids]);unique=sorted(set(days))
    # Bootstrap day totals rather than copying individual games each iteration.
    sums=np.array([delta[days==day].sum(axis=0) for day in unique])
    counts=np.array([(days==day).sum() for day in unique])
    rng=np.random.default_rng(seed)
    samples=[]
    for _ in range(replicates):
        draw=rng.integers(0,len(unique),len(unique))
        samples.append(sums[draw].sum(axis=0)/counts[draw].sum())
    intervals=np.quantile(samples,[.025,.975],axis=0)
    changes={name:dict(delta=float(delta[:,j].mean()),day_block_95_interval=intervals[:,j].tolist())
             for j,name in enumerate(('accuracy','log_loss','brier'))}
    curves=[]
    for variant,group in ((reference,a),(candidate,b)):
        ranked=sorted(ids,key=lambda i:(-max(group[i]['p']),i))
        for fraction in (.25,.5,.75,1.):
            keep=ranked[:max(1,int(np.ceil(len(ids)*fraction)))]
            curves.append(dict(variant=variant,requested_coverage=fraction,coverage=len(keep)/len(ids),
                               **metrics([group[i]['y'] for i in keep],[group[i]['p'] for i in keep])['all']))
    return dict(games=len(ids),day_blocks=len(unique),changes=changes,equal_coverage=curves,
                replicates=replicates,seed=seed,
                note='Candidate minus reference. Higher accuracy/lower losses are better. Exploratory intervals are not corrected for multiple candidate searches; historical comparisons cannot promote a model automatically.')
