from pyqtgraph import PlotWidget, GraphItem, setConfigOption, colormap
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor, QPen
from PyQt5.QtWidgets import QMainWindow
from aind_dynamic_foraging_models.logistic_regression import fit_logistic_regression
import numpy as np
from typing import Union, List
import logging

setConfigOption('background', 'w')
setConfigOption('foreground', 'k')
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
        self._biases_scatter_items = []

        # create plot to show bias data
        self.bias_plot = PlotWidget()
        self.bias_plot.setRange(xRange=[0, 15], yRange=[2*-bias_threshold, 2*bias_threshold])
        self.bias_plot.setLabels(left=('Bias', ''), title='Bias')
        self.bias_plot.getAxis('left').setTicks([[(-bias_threshold, 'Left Bias'), (bias_threshold, 'Right Bias')]])
        self.bias_plot.addLine(y=bias_threshold, pen='r')  # add lines at threshold to make clearer when bias goes over
        self.bias_plot.addLine(y=-bias_threshold, pen='b')
        self.setCentralWidget(self.bias_plot)

        # create gradient pen
        cm = colormap.get('CET-D1')  # prepare a diverging color map
        cm.setMappingMode('diverging')  # set mapping mode
        self.bias_pen = cm.getPen(span=(-bias_threshold, bias_threshold),  width=5)  # blue at -threshold to red at +threshold

        # create leading point
        self._current_bias_point = GraphItem(pos=[[0, 0]],  pen=QPen(QColor('green')), brush=QColor('green'))
        self.bias_plot.addItem(self._current_bias_point)

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

        # calculate logistic regression and extract bias
        choice_history = np.array(choice_history)
        if len(choice_history[~np.isnan(choice_history)]) >= n_trial_back + 2:
            try:
                lr = fit_logistic_regression(choice_history=choice_history,
                                             reward_history=reward_history,
                                             n_trial_back=n_trial_back,
                                             selected_trial_idx=selected_trial_idx)
                bias = lr['df_beta'].loc['bias']['cross_validation'].values[0]
                self._biases.append(bias)

                # add to plot
                if len(self._biases) >= 2:
                    bias_count = len(self._biases)
                    scatter_item = self.bias_plot.plot([bias_count-1, bias_count], self._biases[-2:],
                                                       pen=self.bias_pen)
                    self._biases_scatter_items.append(scatter_item)

                    # remove and re-add point to be ontop of curve
                    self.bias_plot.removeItem(self._current_bias_point)
                    self.bias_plot.addItem(self._current_bias_point)

                    # to help graph from getting bloated and slow, prune data display in graph
                    if len(self._biases_scatter_items) >= n_trial_back+2:
                        self.bias_plot.removeItem(self._biases_scatter_items[0])
                        del self._biases_scatter_items[0]
                        # scroll graph with data
                        self.bias_plot.setRange(xRange=[bias_count-n_trial_back, bias_count],
                                                yRange=[2 * -self.bias_threshold, 2 * self.bias_threshold])
                # emit signal and flash current bias point if over
                if abs(bias) > self.bias_threshold:
                    self.biasOver.emit(bias)
                    self._current_bias_point.setData(pos=[[len(self._biases), bias]],
                                                     pen=QColor('purple'),
                                                     brush=QColor('purple'))

                else:
                    self._current_bias_point.setData(pos=[[len(self._biases), bias]],
                                                     pen=QColor('green'),
                                                     brush=QColor('green'))

            except ValueError as v:
                acceptable_errors = ['Cannot have number of splits n_splits=10 greater than the number of samples:',
                                     'n_splits=10 cannot be greater than the number of members in each class.']
                if any(x in str(v) for x in acceptable_errors):
                    self.log.info("Can't calculate bias because ", str(v))
                else:
                    raise v
    def clear(self):
        """Clear table of all items and clear biases list"""

        # re configure plot
        self.bias_plot.clear()
        self.bias_plot.addLine(y=self.bias_threshold, pen='r')  # add lines at threshold to make clearer when bias goes over
        self.bias_plot.addLine(y=-self.bias_threshold, pen='b')
        self.bias_plot.setRange(xRange=[0, 15], yRange=[2 * -self.bias_threshold, 2 * self.bias_threshold])

        self._biases = []
        self._biases_scatter_items = []

