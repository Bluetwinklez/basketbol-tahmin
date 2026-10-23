"""Display-only basketball totals from the model's nominal normal interval."""
import math


def total_estimates(prediction):
    mean = prediction.get('toplam')
    interval = prediction.get('toplam_80', [])
    if not isinstance(mean, (int, float)) or len(interval) != 2:
        return []
    if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in [mean, *interval]):
        return []
    low, high = interval
    if not 0 <= low <= mean <= high or high <= low:
        return []
    # Conservative when a total interval has been clipped at zero.
    sigma = max(mean-low, high-mean)/1.2815515655446004
    centre = math.floor(mean)+.5
    rows = []
    for line in (centre-10, centre, centre+10):
        if line <= 0:
            continue
        under = .5*(1+math.erf((line-mean)/(sigma*math.sqrt(2))))
        rows.append(dict(line=line, over=1-under, under=under,
                         method='nominal_normal_interval', calibrated=False))
    return rows
