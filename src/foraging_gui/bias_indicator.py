from pyqtgraph import PlotWidget, GraphItem, mkPen
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QMainWindow
from aind_dynamic_foraging_models.logistic_regression import fit_logistic_regression
import numpy as np
from typing import Union, List
import logging

class BiasIndicator(QMainWindow):
    """Widget to calculate, display, and alert user of lick bias"""

    biasOver = pyqtSignal(float)

    def __init__(self, bias_threshold: float = .7, *args, **kwargs):
        """
        :param bias_limit: decimal to alert user if bias is above between 0 and 1
        """

        self.log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        super().__init__(*args, **kwargs)

        self.bias_threshold = bias_threshold

        # initialize biases as empy list
        self._biases = []
        self._bias_items = []
        self._graph_items = []

        # create plot to show bias data
        self.bias_plot = PlotWidget()
        self.bias_plot.getViewBox().state['targetRange'] = [[-1, 30], [-5, 5]]  # Setting autopan range
        self.bias_plot.getViewBox().state['autoPan'] = [True, False]  # auto pan along x axis
        self.bias_plot.getViewBox().state['autoRange'] = [True, False]
        self.bias_plot.setLabels(left=('Bias', ''), bottom=('Time', 's'), title='Bias')
        self.bias_plot.getAxis('left').setTicks([[(-2.5, 'Left'), (2.5, 'Right')]])
        self.setCentralWidget(self.bias_plot)

    @property
    def bias_threshold(self):
        """Decimal threshold at which alert user if bias is above"""
        return self._bias_threshold

    @bias_threshold.setter
    def bias_threshold(self, value):

        if not 0 <= value <= 1:
            self._bias_threshold = .7
            raise ValueError(f'bias_threshold must be set between 0 and 1. Setting to .7')
        else:
            self._bias_threshold = value

    def calculate_bias(self,
                       choice_history: Union[List, np.ndarray],
                       reward_history: Union[List, np.ndarray],
                       n_trial_back: int = 15,
                       selected_trial_idx: Union[List, np.ndarray] = None,
                       ):

        """Fit logistic regression model to choice and reward history.
               1. use cross-validataion to determine the best L2 penality parameter, C
               2. use bootstrap to determine the CI and std

           Parameters
           ----------
           choice_history : Union[List, np.ndarray]
               Choice history (0 = left choice, 1 = right choice).
           reward_history : Union[List, np.ndarray]
               Reward history (0 = unrewarded, 1 = rewarded).
           n_trial_back : int, optional
               Number of trials back into history. Defaults to 15.
           selected_trial_idx : Union[List, np.ndarray], optional
               If None, use all trials;
               else, only look at selected trials for fitting, but using the full history.
           """

        # calculate logistic regression and extract bia
        if len(choice_history) > n_trial_back + 2:
            try:
                lr = fit_logistic_regression(choice_history=choice_history,
                                             reward_history=reward_history,
                                             n_trial_back=n_trial_back,
                                             selected_trial_idx=selected_trial_idx)
                bias = lr['df_beta'].loc['bias']['cross_validation'].values[0]
                self._biases.append(bias)

                # add to plot
                if len(self._biases) >= 2:
                    bias_item = self.bias_plot.plot([len(self._biases)-1, len(self._biases)], self._biases[-2:])
                    self._bias_items.append(bias_item)
                    graph_item = GraphItem(pos=[[len(self._biases), bias]])
                    self.bias_plot.addItem(graph_item)
                    self._graph_items.append(graph_item)

                # to help graph from getting bloated and slow, prune data display in graph
                if len(self._bias_items) >= 32:
                    self.bias_plot.removeItem(self._bias_items[0])
                    del self._bias_items[0]
                    self.bias_plot.removeItem(self._graph_items[0])
                    del self._graph_items[0]

                if abs(bias) > self.bias_threshold:
                    self.biasOver.emit('right' if bias > 0 else 'left')

            except ValueError as v:
                print(v)
                acceptable_errors = ['Cannot have number of splits n_splits=10 greater than the number of samples:',
                                     'n_splits=10 cannot be greater than the number of members in each class.']
                if any(x in str(v) for x in acceptable_errors):
                    self.log.info("Can't calculate bias because ", str(v).lower())
                else:
                    raise v