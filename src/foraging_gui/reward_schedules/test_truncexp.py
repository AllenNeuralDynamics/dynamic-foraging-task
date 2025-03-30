# -*- coding: utf-8 -*-
"""
Compare two methods in generating truncated exponential distributions.

Related to https://github.com/AllenNeuralDynamics/aind-behavior-blog/discussions/442

1. stats.truncexpon (re-draw if a sample > max) --> more like exponential, but increasing hazard function
2. trunc_at_max (trunc to max if a sample > max) --> peak at the maximum value, but quite flat hazard function

"""

import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as stats
from mpl_toolkits.axes_grid1.inset_locator import inset_axes


def draw_dist_and_harzard(
    samples,
    title,
    ax_dist,
    ax_hazard,
    ax_dist_all,
    ax_hazard_all,
    inset_ax_all,
    color,
):
    hist, xx, _ = ax_dist.hist(samples, 100, density=True, color=color)
    hazard = hist / np.flip(np.flip(hist).cumsum())

    # Histogram
    ax_dist.set(title=title, ylim=(0, max(hist) * 1.5), ylabel="Density")
    ax_dist.axvline(
        samples.mean(), c="r", label=f"mean = {samples.mean():.2f}"
    )
    ax_dist.axvline(
        np.median(samples), c="k", label=f"median = {np.median(samples):.2f}"
    )
    ax_dist.legend()

    # Hazard function
    ax_hazard.plot(xx[:-1], hazard, color=color)  # Hazard func
    ax_hazard.set(ylabel="Hazard rate")

    # Zoomed in Hazard function
    inset_ax = inset_axes(
        ax_hazard, width="40%", height="40%", loc="upper left", borderpad=4
    )
    inset_ax.plot(xx[:-1], hazard, color=color)
    inset_ax.set(ylim=(0, 0.1), title="Zoom-in")

    # Overlay cumulative distribution
    ax_dist_all.plot(
        xx[:-1],
        hist.cumsum() / hist.sum(),
        label=title.split("\n")[0],
        color=color,
    )

    # Overlay hazard function
    ax_hazard_all.plot(xx[:-1], hazard, color=color)  # Hazard func

    # Zoomed in Hazard function
    inset_ax_all.plot(xx[:-1], hazard, color=color)

    return hist, xx, hazard


def test_truncexp(lower=20, upper=60, beta=20, n=100000):

    # TruncExp with Re-draw
    X = stats.truncexpon(b=(upper - lower) / beta, loc=lower, scale=beta)
    truncexp_redraw = X.rvs(n)

    # TruncExp with Trunc_at_max
    truncexp_trunc_at_max = np.random.exponential(beta, n) + lower
    larger_than_max = truncexp_trunc_at_max > upper
    truncexp_trunc_at_max[larger_than_max] = upper
    truncated_ratio = sum(larger_than_max) / n

    # Uniform
    uniform = np.random.uniform(lower, upper, n)

    # Plotting
    fig = plt.figure(figsize=(16, 7))
    fig.clf()
    ax = fig.subplots(2, 4)

    inset_ax_all = inset_axes(
        ax[1, 3], width="40%", height="40%", loc="upper left", borderpad=4
    )

    draw_dist_and_harzard(
        samples=truncexp_redraw,
        title=f"TruncExp (redraw)\nmin={lower}, max={upper}, beta={beta}",
        ax_dist=ax[0, 0],
        ax_hazard=ax[1, 0],
        ax_dist_all=ax[0, 3],
        ax_hazard_all=ax[1, 3],
        inset_ax_all=inset_ax_all,
        color="b",
    )
    draw_dist_and_harzard(
        samples=truncexp_trunc_at_max,
        title=f"TruncExp (trunc_at_max: {truncated_ratio:.2%})\n"
        f"min={lower}, max={upper}, beta={beta}",
        ax_dist=ax[0, 1],
        ax_hazard=ax[1, 1],
        ax_dist_all=ax[0, 3],
        ax_hazard_all=ax[1, 3],
        inset_ax_all=inset_ax_all,
        color="g",
    )
    draw_dist_and_harzard(
        samples=uniform,
        title=f"Uniform\nmin={lower}, max={upper}",
        ax_dist=ax[0, 2],
        ax_hazard=ax[1, 2],
        ax_dist_all=ax[0, 3],
        ax_hazard_all=ax[1, 3],
        inset_ax_all=inset_ax_all,
        color="gray",
    )
    fig.tight_layout()

    ax[0, 3].legend()
    ax[0, 3].set(title="Cumulative distribution")
    ax[1, 3].set(ylabel="Hazard rate")
    inset_ax_all.set(ylim=(0, 0.1), title="Zoom-in")

    return fig


if __name__ == "__main__":
    test_truncexp(lower=20, upper=60, beta=20)
    test_truncexp(lower=20, upper=80, beta=20)
    test_truncexp(lower=20, upper=100, beta=20)
    test_truncexp(lower=20, upper=200, beta=20, n=1000000)

    plt.show()
