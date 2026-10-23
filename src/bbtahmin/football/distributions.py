"""Small Poisson utilities for bounded football goal means; no SciPy runtime."""
import math

import numpy as np


class poisson:
    @staticmethod
    def pmf(counts, mean):
        values = np.asarray(counts)
        return np.array([math.exp(-mean + int(k)*math.log(mean) - math.lgamma(int(k)+1))
                         if int(k) >= 0 else 0. for k in values.flat]).reshape(values.shape)

    @staticmethod
    def sf(count, mean):
        # Sum the upper tail directly, avoiding cancellation for unlikely overs.
        start = max(0, int(count)+1)
        return min(1., math.fsum(float(poisson.pmf([k], mean)[0]) for k in range(start, 101)))

    @staticmethod
    def ppf(probability, mean):
        cumulative = 0.
        for k in range(101):
            cumulative += float(poisson.pmf([k], mean)[0])
            if cumulative >= probability:
                return k
        raise ValueError('Goal quantile outside supported range')
