import pytest

from bbtahmin.experiment_metrics import metrics, paired


def test_multiclass_confusion_coverage_and_certain_probability():
    report=metrics([0,1,2],[[1,0,0],[.2,.6,.2],[.6,.1,.3]],[True,False,False])
    assert report['all']['accuracy']==pytest.approx(2/3)
    assert report['selected']['accuracy']==1
    assert report['coverage']==pytest.approx(1/3)
    assert sum(b['games'] for b in report['confidence_bins'])==3
    assert report['confusion_actual_by_predicted']==[[1,0,0],[0,1,0],[1,0,0]]


def test_invalid_probability_and_misaligned_selections_rejected():
    for probabilities in ([[.4,.4]],[[float('nan'),0]],[[1.1,-.1]]):
        with pytest.raises(ValueError): metrics([0],probabilities)
    with pytest.raises(ValueError): metrics([0],[[.5,.5]],[1])


def test_paired_requires_same_cohort_and_bootstraps_days_deterministically():
    rows=[dict(event_id=str(i),day='2026-01-'+str(1+i//2),y=0,variant=v,p=p)
          for i in range(6) for v,p in [('base',[.4,.6]),('new',[.7,.3])]]
    report=paired(rows,'base','new',replicates=50)
    assert report==paired(rows,'base','new',replicates=50)
    assert report['day_blocks']==3
    assert report['changes']['accuracy']['delta']==1
    assert report['changes']['log_loss']['delta']<0
    with pytest.raises(ValueError): paired(rows[:-1],'base','new')
    with pytest.raises(ValueError): paired(rows+[rows[0]],'base','new')
