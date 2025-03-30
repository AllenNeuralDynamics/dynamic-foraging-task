import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Qt5Agg")

#  np.random.seed(56)

import logging

logger = logging.getLogger(__name__)


class UncoupledBlocks:
    """
    Generate uncoupled block reward schedule
    (by on-line updating)

    adapted from Cohen lab's Arduino code (with some bug fixes?)
    """

    def __init__(
        self,
        rwd_prob_array=[0.1, 0.5, 0.9],
        block_min=20,
        block_max=35,
        persev_add=True,
        perseverative_limit=4,
        max_block_tally=4,  # Max number of consecutive blocks in which one side has higher rwd prob than the other
    ) -> None:

        self.__dict__.update(locals())
        self.block_stagger = int(
            (round(block_max - block_min - 0.5) / 2 + block_min) / 2
        )

        self.rwd_tally = {"L": 0, "R": 0}
        self.trial_now = -1  # Index of trial number, starting from 0

        self.block_ends = {
            "L": [],
            "R": [],
        }  # Trial number on which each block ends
        self.block_rwd_prob = {"L": [], "R": []}  # Reward probability
        self.block_ind = {
            "L": 0,
            "R": 0,
        }  # Index of current block (= len(block_end_at_trial))

        self.trial_rwd_prob = {"L": [], "R": []}  # Rwd prob per trial

        self.force_by_tally = {"L": [], "R": []}
        self.force_by_both_lowest = {"L": [], "R": []}

        # Anti-persev
        self.persev_consec_on_min_prob = {"L": 0, "R": 0}
        self.persev_add_at_trials = []
        self.choice_history = []

        # Manually block hold
        self.hold_this_block = False

        self.generate_first_block()

    def generate_first_block(self):
        for side in ["L", "R"]:
            self.generate_next_block(side)

        # Avoid both blocks have the lowest reward prob
        while np.all(
            [
                x[0] == np.min(self.rwd_prob_array)
                for x in self.block_rwd_prob.values()
            ]
        ):
            self.block_rwd_prob[np.random.choice(["L", "R"])][0] = (
                np.random.choice(self.rwd_prob_array)
            )  # Random change one side to another prob

        # Start with block stagger: the lower side makes the first block switch earlier
        smaller_side = min(
            self.block_rwd_prob, key=lambda x: self.block_rwd_prob[x][0]
        )
        self.block_ends[smaller_side][0] -= self.block_stagger

        self.block_effective_ind = 1  # Effective block ind

    def generate_next_block(
        self, side, check_higher_in_a_row=True, check_both_lowest=True
    ):
        msg = ""
        other_side = list({"L", "R"} - {side})[0]
        random_block_len = np.random.randint(
            low=self.block_min, high=self.block_max + 1
        )

        if self.block_ind[side] == 0:  # The first block
            self.block_ends[side].append(random_block_len)
            self.block_rwd_prob[side].append(
                np.random.choice(self.rwd_prob_array)
            )

        else:  # Not the first block
            self.block_ends[side].append(
                random_block_len
                + self.block_ends[side][self.block_ind[side] - 1]
            )

            # If this side has higher prob for too long, force it to be the lowest
            if check_higher_in_a_row:
                # For each effective block, update number of times each side >= the other side
                this_prev = self.block_rwd_prob[side][self.block_ind[side] - 1]
                other_now = self.block_rwd_prob[other_side][
                    self.block_ind[other_side]
                ]
                if this_prev > other_now:
                    self.rwd_tally[side] += 1
                    self.rwd_tally[other_side] = 0
                elif this_prev == other_now:
                    self.rwd_tally[side] += 1
                    self.rwd_tally[other_side] += 1
                else:
                    self.rwd_tally[other_side] += 1
                    self.rwd_tally[side] = 0

                if (
                    self.rwd_tally[side] >= self.max_block_tally
                ):  # Only check higher-in-a-row for this side
                    msg = f"--- {self.trial_now}: {side} is higher for {self.rwd_tally[side]} eff_blocks, force {side} to lowest ---\n"
                    logger.info(msg)
                    self.block_rwd_prob[side].append(min(self.rwd_prob_array))
                    self.rwd_tally[side] = self.rwd_tally[other_side] = 0
                    self.force_by_tally[side].append(self.trial_now)
                else:  # Otherwise, randomly choose one
                    self.block_rwd_prob[side].append(
                        np.random.choice(self.rwd_prob_array)
                    )
            else:
                self.block_rwd_prob[side].append(
                    np.random.choice(self.rwd_prob_array)
                )

            # Don't repeat the previous rwd prob
            # (this will not mess up with the "forced" case since the previous block cannot be the lowest prob in the first place)
            while (
                self.block_rwd_prob[side][-2] == self.block_rwd_prob[side][-1]
            ):
                self.block_rwd_prob[side][-1] = np.random.choice(
                    self.rwd_prob_array
                )

            # If the other side is already at the lowest prob AND this side just generates the same
            # (either through "forced" case or not), push the previous lowest side to a higher prob
            if check_both_lowest and self.block_rwd_prob[side][
                -1
            ] == self.block_rwd_prob[other_side][-1] == min(
                self.rwd_prob_array
            ):
                # Stagger this side
                self.block_ends[side][-1] -= self.block_stagger

                # Force block switch of the other side
                msg += f"--- {self.trial_now}: both side is the lowest, push {side} to higher ---"
                logger.info(msg)
                self.force_by_both_lowest[side].append(self.trial_now)
                self.block_ends[other_side][-1] = self.trial_now
                self.block_ind[
                    other_side
                ] += 1  # Two sides change at the same time, no need to add block_effective_ind twice
                self.generate_next_block(
                    other_side,
                    check_higher_in_a_row=False,
                    check_both_lowest=False,
                )  # Just generate new block, no need to do checks
        return msg

    def auto_shape_perseverance(self):
        msg = ""
        for s in ["L", "R"]:
            if self.choice_history[-1] == s:
                self.persev_consec_on_min_prob[list({"L", "R"} - {s})[0]] = (
                    0  # Reset other side as soon as there is an opposite choice
                )
                if self.trial_rwd_prob[s][-2] == min(
                    self.rwd_prob_array
                ):  # If last choice is on side with min_prob (0.1), add counter
                    self.persev_consec_on_min_prob[s] += 1

        for s in ["L", "R"]:
            if self.persev_consec_on_min_prob[s] >= self.perseverative_limit:
                for ss in ["L", "R"]:
                    self.block_ends[ss][
                        -1
                    ] += (
                        self.perseverative_limit
                    )  # Add 'perseverative_limit' trials to both blocks
                    self.persev_consec_on_min_prob[ss] = 0
                msg = f"persev at side = {s}, added {self.perseverative_limit} trials to both sides"
                logger.info(msg)
                self.persev_add_at_trials.append(self.trial_now)
        return msg

    def add_choice(self, this_choice):
        self.choice_history.append(this_choice)

    def next_trial(self):
        msg = ""
        self.trial_now += 1  # Starts from 0; initialized from -1

        # Block switch?
        if not self.hold_this_block:
            for s in ["L", "R"]:
                if self.trial_now >= self.block_ends[s][self.block_ind[s]]:
                    # In case a block is mannually 'held', update the actual block transition
                    self.block_ends[s][self.block_ind[s]] = self.trial_now

                    self.block_ind[s] += 1
                    self.block_effective_ind += 1
                    msg = (
                        self.generate_next_block(
                            s,
                            check_higher_in_a_row=True,
                            check_both_lowest=True,
                        )
                        + "\n"
                    )

        # Fill new value
        for s in ["L", "R"]:
            self.trial_rwd_prob[s].append(
                self.block_rwd_prob[s][self.block_ind[s]]
            )

        # Anti-persev
        if (
            not self.hold_this_block
            and self.persev_add
            and len(self.choice_history)
        ):
            msg = msg + self.auto_shape_perseverance()
        else:
            for s in ["L", "R"]:
                self.persev_consec_on_min_prob[s] = 0

        assert (
            (self.trial_now + 1)
            == len(self.trial_rwd_prob["L"])
            == len(self.trial_rwd_prob["R"])
        )
        assert all(
            [
                self.block_ind["L"] + 1
                == len(self.block_rwd_prob["L"])
                == len(self.block_ends["L"])
                for s in ["L", "R"]
            ]
        )

        return (
            [
                self.trial_rwd_prob[s][-2] != self.trial_rwd_prob[s][-1]
                for s in ["L", "R"]
            ]  # Whether block just switched
            if self.trial_now > 0
            else [0, 0]
        ), msg

    def plot_reward_schedule(self):
        fig, ax = plt.subplots(2, 1, figsize=[15, 7], sharex="col")

        def annotate_block(ax):
            for s, col in zip(["L", "R"], ["r", "b"]):
                [
                    ax.axvline(
                        x + (0.1 if s == "R" else 0),
                        0,
                        1,
                        color=col,
                        ls="--",
                        lw=0.5,
                    )
                    for x in self.block_ends[s]
                ]
                [
                    ax.plot(x, 1.2, marker=">", color=col)
                    for x in self.force_by_tally[s]
                ]
                [
                    ax.plot(x, 1.1, marker="v", color=col)
                    for x in self.force_by_both_lowest[s]
                ]

            for s, col, pos, m in zip(
                ["L", "R", "ignored"],
                ["r", "b", "k"],
                [0, 1, 0.95],
                ["|", "|", "x"],
            ):
                this_choice = np.where(np.array(self.choice_history) == s)
                ax.plot(this_choice, [pos] * len(this_choice), m, color=col)

            ax.plot(
                self.persev_add_at_trials,
                [1.05] * len(self.persev_add_at_trials),
                marker="+",
                ls="",
                color="c",
            )

        for s, col in zip(["L", "R"], ["r", "b"]):
            ax[0].plot(
                self.trial_rwd_prob[s], col, marker=".", alpha=0.5, lw=2
            )
        annotate_block(ax[0])

        ax[1].plot(
            np.array(self.trial_rwd_prob["L"])
            + np.array(self.trial_rwd_prob["R"]),
            label="sum",
        )
        ax[1].plot(
            np.array(self.trial_rwd_prob["R"])
            / (
                np.array(self.trial_rwd_prob["L"])
                + np.array(self.trial_rwd_prob["R"])
            ),
            label="R/(L+R)",
        )
        ax[1].legend()
        annotate_block(ax[1])

        plt.show()


if __name__ == "__main__":
    total_trial = 1000

    reward_schedule = UncoupledBlocks(perseverative_limit=4)

    while reward_schedule.trial_now <= total_trial:
        reward_schedule.next_trial()
        """
        run protocol here
        """
        reward_schedule.add_choice(
            ["L", "R", "ignored"][
                np.random.choice([0] * 100 + [1] * 20 + [2] * 1)
            ]
        )

        reward_schedule.hold_this_block = 500 < reward_schedule.trial_now < 700

    reward_schedule.plot_reward_schedule()
    print(f"effective blocks = {reward_schedule.block_effective_ind}")

    pass
    # %%
