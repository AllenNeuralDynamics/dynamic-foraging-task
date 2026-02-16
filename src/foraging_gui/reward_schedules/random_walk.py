import matplotlib.pyplot as plt
import numpy as np

# matplotlib.use('Qt5Agg')

#  np.random.seed(56)


class RandomWalkReward:
    """
    Generate reward schedule with random walk

    (see Miller et al. 2021, https://www.biorxiv.org/content/10.1101/461129v3.full.pdf)
    """

    def __init__(
        self,
        p_min=[0, 0],  # L and R
        p_max=[1, 1],  # L and R
        sigma=[0.15, 0.15],  # L and R
        mean=[0, 0],  # L and R
    ) -> None:

        self.__dict__.update(locals())

        if not isinstance(sigma, list):
            sigma = [sigma, sigma]  # Backward compatibility

        if not isinstance(p_min, list):
            p_min = [p_min, p_min]  # Backward compatibility

        if not isinstance(p_max, list):
            p_max = [p_max, p_max]  # Backward compatibility

        self.p_min, self.p_max, self.sigma, self.mean = (
            p_min,
            p_max,
            sigma,
            mean,
        )

        self.trial_rwd_prob = {"L": [], "R": []}  # Rwd prob per trial
        self.choice_history = []

        self.hold_this_block = False
        self.first_trial()

    def first_trial(self):
        self.trial_now = 0
        for i, side in enumerate(["L", "R"]):
            self.trial_rwd_prob[side].append(
                np.random.uniform(self.p_min[i], self.p_max[i])
            )

    def next_trial(self):
        self.trial_now += 1
        for i, side in enumerate(["L", "R"]):
            if not self.hold_this_block:
                p = np.random.normal(
                    self.trial_rwd_prob[side][-1] + self.mean[i], self.sigma[i]
                )
                p = min(self.p_max[i], max(self.p_min[i], p))
            else:
                p = self.trial_rwd_prob[side][-1]
            self.trial_rwd_prob[side].append(p)

    def add_choice(self, this_choice):
        self.choice_history.append(this_choice)

    def auto_corr(self, data):
        mean = np.mean(data)
        # Variance
        var = np.var(data)
        # Normalized data
        ndata = data - mean
        acorr = np.correlate(ndata, ndata, "full")[len(ndata) - 1 :]
        acorr = acorr / var / len(ndata)
        return acorr

    def plot_reward_schedule(self, axes=None):
        MAX_TRIALS = 1000
        standalone = axes is None

        if standalone:
            fig, axes = plt.subplot_mosaic(
                [["history", "autocorr"], ["sum", "autocorr"]],
                figsize=[15, 4],
                gridspec_kw=dict(width_ratios=[4, 1], hspace=0.1, wspace=0.2),
            )
            axes["sum"].sharex(axes["history"])

        for s, col in zip(["L", "R"], ["r", "b"]):
            axes["history"].plot(
                self.trial_rwd_prob[s][:MAX_TRIALS], col, marker=".", alpha=0.5, lw=2
            )
            axes["autocorr"].plot(self.auto_corr(self.trial_rwd_prob[s]), col)

        p_l = np.array(self.trial_rwd_prob["L"])[:MAX_TRIALS]
        p_r = np.array(self.trial_rwd_prob["R"])[:MAX_TRIALS]
        axes["sum"].plot(p_l + p_r, label="sum")
        axes["sum"].plot(p_r / (p_l + p_r), label="R/(L+R)")
        axes["sum"].legend()

        axes["autocorr"].set(title=f"auto correlation from {self.trial_now-1} trials", xlim=[0, 100])
        axes["autocorr"].axhline(y=0, c="k", ls="--")
        axes["autocorr"].set_box_aspect(1)
        axes["history"].set_title(f"sigma = {self.sigma}", loc="left")

        if standalone:
            plt.show()


if __name__ == "__main__":
    total_trial = 10000
    sigmas = [0.05, 0.1, 0.15]

    mosaic_layout = []
    for i in range(len(sigmas)):
        mosaic_layout += [[f"h{i}", f"a{i}"], [f"s{i}", f"a{i}"]]

    fig, ax = plt.subplot_mosaic(
        mosaic_layout,
        figsize=[15, 4 * len(sigmas)],
        gridspec_kw=dict(width_ratios=[4, 1], hspace=0.3, wspace=0.2),
    )

    for i, sigma in enumerate(sigmas):
        reward_schedule = RandomWalkReward(
            p_min=[0.1, 0.1], p_max=0.9, sigma=[sigma, sigma], mean=[-0.0, 0.0]
        )
        while reward_schedule.trial_now <= total_trial:
            reward_schedule.next_trial()

        axes = {"history": ax[f"h{i}"], "sum": ax[f"s{i}"], "autocorr": ax[f"a{i}"]}
        ax[f"s{i}"].sharex(ax[f"h{i}"])
        if i > 0:
            ax[f"h{i}"].sharex(ax["h0"])
        reward_schedule.plot_reward_schedule(axes=axes)

    # Hide x tick labels on all left-column axes except the bottom sum panel
    for i in range(len(sigmas)):
        ax[f"h{i}"].tick_params(labelbottom=False)
        if i < len(sigmas) - 1:
            ax[f"s{i}"].tick_params(labelbottom=False)

    plt.show()
    # %%
