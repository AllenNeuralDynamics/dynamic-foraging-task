# -*- coding: utf-8 -*-
"""
Compare two methods in generating truncated exponential distributions.

Related to https://github.com/AllenNeuralDynamics/aind-behavior-blog/discussions/442

1. stats.truncexpon (re-draw if a sample > max) --> more like exponential, but increasing hazard function
2. trunc_at_max (trunc to max if a sample > max) --> peak at the maximum value, but quite flat hazard function

"""

import scipy.stats as stats
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

def draw_dist_and_harzard(ax_dist, ax_hazard, samples, title):
    hist, xx, _ = ax_dist.hist(samples, 100, density=True)
    hazard = hist / np.flip(np.flip(hist).cumsum())
    
    # Histogram
    ax_dist.set(title=title,
                ylim=(0, max(hist) * 1.5), ylabel='Density'
                )
    ax_dist.axvline(samples.mean(), c='r', label=f'mean = {samples.mean():.2f}')
    ax_dist.axvline(np.median(samples), c='k', label=f'median = {np.median(samples):.2f}')
    ax_dist.legend()

    # Hazard function
    ax_hazard.plot(xx[:-1], hazard)  # Hazard func
    ax_hazard.set(ylabel='Hazard rate')
    
    # Zoomed in Hazard function
    inset_ax = inset_axes(ax_hazard, width="40%", height="40%", 
                          loc="upper left", borderpad=4)
    inset_ax.plot(xx[:-1], hazard)
    inset_ax.set(ylim=(0, 0.1), title='Zoom-in')
    
    return hist, xx, hazard


def test_truncexp(lower=20, 
                  upper=60,
                  beta=20,
                  n=100000):

    # TruncExp with Re-draw
    X = stats.truncexpon(b=(upper-lower)/beta, loc=lower, scale=beta)
    truncexp_redraw = X.rvs(n)

    # TruncExp with Trunc_at_max
    truncexp_trunc_at_max = np.random.exponential(beta, n) + lower
    larger_than_max = truncexp_trunc_at_max > upper
    truncexp_trunc_at_max[larger_than_max] = upper
    truncated_ratio = sum(larger_than_max) / n
    
    # Uniform
    uniform = np.random.uniform(lower, upper, n)

    # Plotting
    fig = plt.figure(figsize=(13, 7))
    fig.clf()
    ax = fig.subplots(2, 3)

    draw_dist_and_harzard(ax[0, 0], ax[1, 0], 
                          samples=truncexp_redraw,
                          title=f'TruncExp (redraw)\nmin={lower}, max={upper}, beta={beta}')
    draw_dist_and_harzard(ax[0, 1], ax[1, 1], 
                          samples=truncexp_trunc_at_max,
                          title=f'TruncExp (trunc_at_max: {truncated_ratio:.2%})\n'
                          f'min={lower}, max={upper}, beta={beta}')
    draw_dist_and_harzard(ax[0, 2], ax[1, 2],
                          samples=uniform,
                          title=f'Uniform\nmin={lower}, max={upper}')

    fig.tight_layout()
    
    return fig


if __name__ == '__main__':
    test_truncexp(lower=20, upper=60, beta=20)
    test_truncexp(lower=20, upper=80, beta=20)
    test_truncexp(lower=20, upper=100, beta=20)
    test_truncexp(lower=40, upper=80, beta=20)

    plt.show()