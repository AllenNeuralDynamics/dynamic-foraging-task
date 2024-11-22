from pyqtgraph import PlotWidget, GraphItem, setConfigOption, colormap, PlotDataItem, TextItem, FillBetweenItem
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

    biasOver = pyqtSignal(float, int)   # emit bias and trial number it occurred
    biasError = pyqtSignal(str, int)    # emit error and trial number it occurred
    biasValue = pyqtSignal(float, int)  # emit bias and trial number it occurred

    def __init__(self, bias_threshold: float = .7, x_range: int = 15, *args, **kwargs):
        """
        :param bias_limit: decimal to alert user if bias is above between 0 and 1
        :param x_range: total number of values displayed on the x axis as graph is scrolling
        """

        super().__init__(*args, **kwargs)
        self.log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.bias_threshold = bias_threshold

        # initialize biases as empy list and x_range
        self._biases = []
        self._x_range = x_range

        # create plot to show bias data
        self.bias_plot = PlotWidget()
        self.bias_plot.getViewBox().invertY(True)
        self.bias_plot.setMouseEnabled(False)
        self.bias_plot.setMouseTracking(False)
        self.bias_plot.setRange(xRange=[1, self.x_range], yRange=[-self.bias_threshold - .3, .3 + self.bias_threshold])
        self.bias_plot.setLabels(left='Bias', bottom='Trial #')    # make label bigger
        self.bias_plot.getAxis('left').setTicks([[(-bias_threshold, 'L'),
                                                  (bias_threshold, 'R')]])
        self.bias_plot.addLine(y=0, pen='black')  # add line at 0 to help user see if slight bias
        self.bias_plot.addLine(y=bias_threshold, pen='b')  # add lines at threshold to make clearer when bias goes over
        self.bias_plot.addLine(y=-bias_threshold, pen='r')
        self.setCentralWidget(self.bias_plot)

        # create gradient pen
        cm = colormap.get('CET-D1')  # prepare a diverging color map
        cm.reverse()  # reverse to red == left and blue == right
        cm.setMappingMode('diverging')  # set mapping mode
        self.bias_pen = cm.getPen(span=(1.5 * -bias_threshold,
                                        1.5 * bias_threshold),
                                  width=5)  # red at -threshold to blue at +threshold

        # create upper and lower CI curves
        self._upper_scatter_item = PlotDataItem([0], [0], pen='lightgray')
        self._lower_scatter_item = PlotDataItem([0], [0], pen='lightgray')
        self.bias_plot.addItem(self._upper_scatter_item)
        self.bias_plot.addItem(self._lower_scatter_item)
        self.bias_plot.addItem(FillBetweenItem(curve1=self._upper_scatter_item,
                                               curve2=self._lower_scatter_item,
                                               pen='lightgray',
                                               brush='lightgray'))


        # create scatter curve item
        self._biases_scatter_item = PlotDataItem([0], [0], pen=self.bias_pen)
        self.bias_plot.addItem(self._biases_scatter_item)

        # create leading point
        self._current_bias_point = GraphItem(pos=[[0, 0]], pen=QPen(QColor('green')), brush=QColor('green'), size=9)
        self.bias_plot.addItem(self._current_bias_point)

        # create bias label
        self.bias_label = TextItem(color='black', anchor=(-.02, 0))
        self.biasValue.connect(lambda bias, trial: self.bias_label.setText(str(round(bias, 3))))
        self.biasValue.connect(lambda bias, trial: self.bias_label.setPos(self._current_bias_point.pos[0][0], bias))
        self.bias_plot.addItem(self.bias_label)

    @property
    def bias_threshold(self) -> float:
        """Decimal threshold at which alert user if bias is above"""
        return self._bias_threshold

    @bias_threshold.setter
    def bias_threshold(self, value: float) -> None:
        """
        Set decimal threshold at which alert user if bias is above
        :param value: float value to set bias to
        """
        if not 0 <= value <= 1:
            self._bias_threshold = .7
            raise ValueError(f'bias_threshold must be set between 0 and 1. Setting to .7')
        else:
            self._bias_threshold = value

    @property
    def x_range(self) -> int:
        """total number of values displayed on the x axis as graph is scrolling"""
        return self._x_range

    @x_range.setter
    def x_range(self, value: int) -> None:
        """
        total number of values displayed on the x axis as graph is scrolling
        :param value: int value to set x range to
        """
        last_x = self._biases_scatter_item.xData[-1] if self._biases_scatter_item.xData[-1] > value else value
        self.bias_plot.setRange(xRange=[last_x - value, value])
        self._x_range = value

    def calculate_bias(self,
                       trial_num: int,
                       choice_history: Union[List, np.ndarray],
                       reward_history: Union[List, np.ndarray],
                       n_trial_back: int = 5,
                       selected_trial_idx: Union[List, np.ndarray] = None,
                       cv: int = 10,
                       ):

        """Fit logistic regression model to choice and reward history.
               1. use cross-validataion to determine the best L2 penality parameter, C
               2. use bootstrap to determine the CI and std

           Parameters
           ----------
           trial_num : int
               Trial number of currently at
           choice_history : Union[List, np.ndarray]
               Choice history (0 = left choice, 1 = right choice).
           reward_history : Union[List, np.ndarray]
               Reward history (0 = unrewarded, 1 = rewarded).
           n_trial_back : int, optional
               Number of trials back into history. Defaults to 15.
           selected_trial_idx : Union[List, np.ndarray], optional
               If None, use all trials;
               else, only look at selected trials for fitting, but using the full history.
           cv : int, optional
                Number of folds in cross validation, by default 10
           """

        # calculate logistic regression and extract bias
        choice_history = np.array(choice_history)
        if len(choice_history[~np.isnan(choice_history)]) >= n_trial_back + 2:
            trial_count = len(choice_history)

            # Determine if we have valid data to fit model
            unique = np.unique(choice_history[~np.isnan(choice_history)])
            if len(unique) == 2:
                lr = fit_logistic_regression(choice_history=choice_history,
                                             reward_history=reward_history,
                                             n_trial_back=n_trial_back,
                                             selected_trial_idx=selected_trial_idx,
                                             cv=cv,
                                             fit_exponential=False)
                bias = lr['df_beta'].loc['bias']['cross_validation'].values[0]
                self.log.info(f"Bias: {bias} Trial Count: {trial_count}")
                self._biases.append(bias)
                self.biasValue.emit(bias, trial_count)

                # add confidence intervals
                upper = lr['df_beta'].loc['bias']['bootstrap_CI_upper'].values[0]
                lower = lr['df_beta'].loc['bias']['bootstrap_CI_lower'].values[0]
            elif len(unique) == 0:
                # no choices, report bias confidence as (-inf, +inf)
                bias = 0
                upper = 1
                lower = -1
            elif unique[0] == 0:
                # only left choices, report bias confidence as (-inf, 0)
                bias = -1
                upper = 0
                lower = -1

            elif unique[0] == 1:
                # only right choices, report bias confidence as (0, +inf)
                bias = 1
                upper = 1
                lower = 0

            else:   # skip bias calculation if no conditions are met
                return

            # update
            self._upper_scatter_item.setData(x=np.append(self._upper_scatter_item.xData, trial_num),
                                             y=np.append(self._upper_scatter_item.yData, upper))
            self._lower_scatter_item.setData(x=np.append(self._lower_scatter_item.xData, trial_num),
                                             y=np.append(self._lower_scatter_item.yData, lower))

            # add to plot
            if len(self._biases) >= 2:
                # append data with latest
                x = np.append(self._biases_scatter_item.xData, trial_num)
                y = np.append(self._biases_scatter_item.yData, bias)

                self._biases_scatter_item.setData(x=x, y=y)

                # auto scroll graph
                if trial_num >= self.bias_plot.getAxis('bottom').range[1]-50:
                    self.bias_plot.setRange(xRange=[trial_num - self.x_range if self.x_range < trial_num else 2,
                                                    trial_num+50])

            # emit signal and flash current bias point if over
            if abs(bias) > self.bias_threshold:
                self.log.info(f"Bias value calculated over a threshold of {self.bias_threshold}. Bias: {bias} "
                              f"Trial Count: {trial_count}")
                self.biasOver.emit(bias, trial_count)
                self._current_bias_point.setData(pos=[[trial_num, bias]],
                                                 pen=QColor('purple'),
                                                 brush=QColor('purple'),
                                                 size=9)

            else:
                self._current_bias_point.setData(pos=[[trial_num, bias]],
                                                 pen=QColor('green'),
                                                 brush=QColor('green'),
                                                 size=9)

    def clear(self):
        """Clear table of all items and clear biases list"""

        # re configure plot
        self.bias_plot.clear()
        self.bias_plot.addLine(y=0, pen='black')  # add line at 0 to help user see if slight bias
        self.bias_plot.addLine(y=self.bias_threshold,
                               pen='b')  # add lines at threshold to make clearer when bias goes over
        self.bias_plot.addLine(y=-self.bias_threshold, pen='r')
        self.bias_plot.setRange(xRange=[1, self.x_range], yRange=[-self.bias_threshold - .3, .3 + self.bias_threshold])

        # reset bias list
        self._biases = []
        # reset upper and lower ci
        self.bias_plot.addItem(self._upper_scatter_item)
        self.bias_plot.addItem(self._lower_scatter_item)
        self.bias_plot.addItem(FillBetweenItem(curve1=self._upper_scatter_item,
                                               curve2=self._lower_scatter_item,
                                               pen='lightgray',
                                               brush='lightgray'))
        # reset scatter curve item
        self._biases_scatter_item = PlotDataItem([0], [0], pen=self.bias_pen)
        self.bias_plot.addItem(self._biases_scatter_item)
        # reset leading point
        self._current_bias_point = GraphItem(pos=[[0, 0]], pen=QPen(QColor('green')), brush=QColor('green'), size=9)
        self.bias_plot.addItem(self._current_bias_point)
        # reset bias label
        self.bias_label.setText('')
        self.bias_plot.addItem(self.bias_label)
