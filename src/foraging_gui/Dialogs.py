import time
import math
import json
import os
import shutil
import subprocess
from datetime import datetime
import logging
import webbrowser
from typing import Literal

import numpy as np
import pandas as pd
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QMessageBox, QGridLayout
from PyQt5.QtWidgets import QLabel, QDialogButtonBox, QFileDialog, QInputDialog, QLineEdit
from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtCore import QThreadPool, Qt, QAbstractTableModel, QTimer, pyqtSignal

from foraging_gui.MyFunctions import Worker
from foraging_gui.Visualization import PlotWaterCalibration
from aind_auto_train.schema.curriculum import DynamicForagingCurriculum
from foraging_gui.schema_widgets.opto_parameters_widget import OptoParametersWidget
from aind_behavior_dynamic_foraging.DataSchemas.optogenetics import Optogenetics

codebase_curriculum_schema_version = DynamicForagingCurriculum.model_fields['curriculum_schema_version'].default

logger = logging.getLogger(__name__)


class MouseSelectorDialog(QDialog):

    acceptedMouseID = pyqtSignal(str)

    def __init__(self, mice: list[str], box_letter: str, parent=None):
        """
        QDialog that allows users to type and select mouse id from slims
        :param mice: list of mice found on slims
        :param box_letter: box letter
        """

        super().__init__(parent)
        self.mice = [''] + mice
        self.setWindowTitle('Box {}, Load Mouse'.format(box_letter))
        self.setFixedSize(250, 125)

        QBtns = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtns)
        self.buttonBox.accepted.connect(self.check_mouse_selection)
        self.buttonBox.rejected.connect(self.reject)

        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(self.mice)
        self.combo.setEditable(True)
        self.combo.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.combo.completer().setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.combo.setValidator(QtGui.QIntValidator()) # set int validator

        font = self.combo.font()
        font.setPointSize(15)
        self.combo.setFont(font)


        msg = QLabel('Enter the Mouse ID: \nuse 0-9, single digit as test ID')
        font = msg.font()
        font.setPointSize(12)
        msg.setFont(font)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(msg)
        self.layout.addWidget(self.combo)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def check_mouse_selection(self):
        """
        Check if mouse selected is valid
        """

        text = self.combo.currentText()
        if text == "":
            return

        self.accept()
        self.acceptedMouseID.emit(text)

    def add_mice(self, mice: list[str]):
        """
        Function to add mice to combobox
        """

        self.mice = [''] + mice
        self.combo.clear()
        self.combo.addItems(self.mice)


class LickStaDialog(QDialog):
    '''Lick statistics dialog'''

    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        uic.loadUi('LicksDistribution.ui', self)

        self.MainWindow = MainWindow


class TimeDistributionDialog(QDialog):
    '''Simulated distribution of ITI/Delay/Block length'''

    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        uic.loadUi('TimeDistribution.ui', self)

        self.MainWindow = MainWindow


class OptogeneticsDialog(QDialog):
    '''Optogenetics dialog'''

    def __init__(self, MainWindow, opto_model: Optogenetics, parent=None):
        super().__init__(parent)
        uic.loadUi('Optogenetics.ui', self)
        self.opto_model = opto_model
        self.opto_widget = OptoParametersWidget(self.opto_model)
        # initialize model as no optogenetics
        self.opto_model.laser_colors = []
        self.opto_model.session_control = None
        self.opto_widget.apply_schema(self.opto_model)
        self.QScrollOptogenetics.setWidget(self.opto_widget)

        self.MainWindow = MainWindow

    def _connectSignalsSlots(self):

        self.Laser_calibration.currentIndexChanged.connect(self._Laser_calibration)
        self.Laser_calibration.activated.connect(self._Laser_calibration)
        self.SessionWideControl.currentIndexChanged.connect(self._SessionWideControl)

    def _Laser_calibration(self):
        ''''change the laser calibration date'''
        # find the latest calibration date for the selected laser
        Laser = self.Laser_calibration.currentText()
        latest_calibration_date = self._FindLatestCalibrationDate(Laser)
        # set the latest calibration date
        self.LatestCalibrationDate.setText(latest_calibration_date)

    def _FindLatestCalibrationDate(self, Laser):
        '''find the latest calibration date for the selected laser'''
        if not hasattr(self.MainWindow, 'LaserCalibrationResults'):
            return 'NA'
        Dates = []
        for Date in self.MainWindow.LaserCalibrationResults:
            if Laser in self.MainWindow.LaserCalibrationResults[Date].keys():
                Dates.append(Date)
        sorted_dates = sorted(Dates)
        if sorted_dates == []:
            return 'NA'
        else:
            return sorted_dates[-1]


class WaterCalibrationDialog(QDialog):
    '''Water valve calibration'''

    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        uic.loadUi('Calibration.ui', self)

        self.MainWindow = MainWindow
        self.calibrating_left = False
        self.calibrating_right = False
        self._LoadCalibrationParameters()
        if not hasattr(self.MainWindow, 'WaterCalibrationResults'):
            self.MainWindow.WaterCalibrationResults = {}
            self.WaterCalibrationResults = {}
        else:
            self.WaterCalibrationResults = self.MainWindow.WaterCalibrationResults
        self._connectSignalsSlots()
        self.ToInitializeVisual = 1
        self._UpdateFigure()
        self.setWindowTitle('Water Calibration: {}'.format(self.MainWindow.current_box))
        self.Warning.setText('')
        self.Warning.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')
        # find all buttons and set them to not be the default button
        for container in [self]:
            for child in container.findChildren((QtWidgets.QPushButton)):
                child.setDefault(False)
                child.setAutoDefault(False)

        # setup QTimers to keep lines open
        self.left_open_timer = QTimer(timeout=lambda: self.reopen_valve('Left'), interval=10000)
        self.right_open_timer = QTimer(timeout=lambda: self.reopen_valve('Right'), interval=10000)

        # setup QTimers to keep close lines after 5ml
        self.left_close_timer = QTimer(timeout=lambda: self.OpenLeft5ml.setChecked(False))  # trigger _ToggleValve call
        self.right_close_timer = QTimer(timeout=lambda: self.OpenRight5ml.setChecked(False))

        # setup Qtimers for updating text countdown
        self.left_text_timer = QTimer(timeout=lambda:
        self.OpenLeft5ml.setText(f'Open left 5ml: {round(self.left_close_timer.remainingTime() / 1000)}s'),
                                      interval=1000)
        self.right_text_timer = QTimer(timeout=lambda:
        self.OpenRight5ml.setText(f'Open right 5ml: {round(self.right_close_timer.remainingTime() / 1000)}s'),
                                       interval=1000)

    def _connectSignalsSlots(self):
        self.SpotCheckLeft.clicked.connect(lambda: self._SpotCheck('Left'))
        self.SpotCheckRight.clicked.connect(lambda: self._SpotCheck('Right'))

        # Set up OpenLeftForever button
        self.OpenLeftForever.clicked.connect(lambda: self._ToggleValve(self.OpenLeftForever, 'Left'))
        self.OpenLeftForever.clicked.connect(lambda: self.OpenLeft5ml.setDisabled(self.OpenLeftForever.isChecked()))
        # Set up OpenRightForever button
        self.OpenRightForever.clicked.connect(lambda: self._ToggleValve(self.OpenRightForever, 'Right'))
        self.OpenRightForever.clicked.connect(lambda: self.OpenRight5ml.setDisabled(self.OpenRightForever.isChecked()))
        # Set up OpenLeft5ml button
        self.OpenLeft5ml.toggled.connect(lambda val: self._ToggleValve(self.OpenLeft5ml, 'Left'))
        self.OpenLeft5ml.toggled.connect(lambda val: self.OpenLeftForever.setDisabled(val))
        # Set up OpenRight5ml button
        self.OpenRight5ml.toggled.connect(lambda val: self._ToggleValve(self.OpenRight5ml, 'Right'))
        self.OpenRight5ml.toggled.connect(lambda val: self.OpenRightForever.setDisabled(val))

        self.SaveLeft.clicked.connect(lambda: self._SaveValve('Left'))
        self.SaveRight.clicked.connect(lambda: self._SaveValve('Right'))
        self.StartCalibratingLeft.clicked.connect(self._StartCalibratingLeft)
        self.StartCalibratingRight.clicked.connect(self._StartCalibratingRight)
        self.Continue.clicked.connect(self._Continue)
        self.Repeat.clicked.connect(self._Repeat)
        self.Finished.clicked.connect(self._Finished)
        self.EmergencyStop.clicked.connect(self._EmergencyStop)
        self.showrecent.textChanged.connect(self._Showrecent)
        self.showspecificcali.activated.connect(self._ShowSpecifcDay)

    def _Showrecent(self):
        '''update the calibration figure'''
        self._UpdateFigure()

    def _ShowSpecifcDay(self):
        '''update the calibration figure'''
        self._UpdateFigure()

    def _Finished(self):
        if (not self.calibrating_left) and (not self.calibrating_right):
            return

        if self.calibrating_left and (not np.all(self.left_measurements)):
            reply = QMessageBox.question(self, "Box {}, Finished".format(self.MainWindow.box_letter),
                                         f"Calibration incomplete, are you sure you want to finish?\n",
                                         QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No)
            if reply == QMessageBox.No:
                return
        if self.calibrating_right and (not np.all(self.right_measurements)):
            reply = QMessageBox.question(self, "Box {}, Finished".format(self.MainWindow.box_letter),
                                         f"Calibration incomplete, are you sure you want to finish?\n",
                                         QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No)
            if reply == QMessageBox.No:
                return

        self.calibrating_left = False
        self.calibrating_right = False
        self.Continue.setStyleSheet("color: black;background-color : none")
        self.Repeat.setStyleSheet("color: black;background-color : none")
        self.Finished.setStyleSheet("color: black;background-color : none")
        self.StartCalibratingLeft.setStyleSheet("background-color : none")
        self.StartCalibratingRight.setStyleSheet("background-color : none")
        self.StartCalibratingLeft.setChecked(False)
        self.StartCalibratingRight.setChecked(False)
        self.StartCalibratingLeft.setEnabled(True)
        self.StartCalibratingRight.setEnabled(True)
        self.Warning.setText('Calibration Finished')
        self.Warning.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')

    def _Continue(self):
        '''Change the color of the continue button'''
        if (not self.calibrating_left) and (not self.calibrating_right):
            return

        self.Continue.setStyleSheet("color:  black; background-color : none")
        logging.info('Continue pressed')
        if self.calibrating_left:
            self._CalibrateLeftOne()
        if self.calibrating_right:
            self._CalibrateRightOne()

    def _Repeat(self):
        '''Change the color of the continue button'''

        if (not self.calibrating_left) and (not self.calibrating_right):
            return
        self.Repeat.setStyleSheet("color: black; background-color : none")
        if self.calibrating_left:
            self._CalibrateLeftOne(repeat=True)
        if self.calibrating_right:
            self._CalibrateRightOne(repeat=True)

    def _EmergencyStop(self):
        '''Change the color of the EmergencyStop button'''
        if self.EmergencyStop.isChecked():
            self.EmergencyStop.setStyleSheet("background-color : green;")
        else:
            self.EmergencyStop.setStyleSheet("background-color : none")

    def _SaveValve(self, valve: Literal['Left', 'Right']):
        """
        save the calibration result of the single point calibration (left valve)
        :param valve: string specifying valve side
        """
        save = getattr(self, f'Save{valve}')
        save.setStyleSheet("background-color : green;")
        QApplication.processEvents()

        valve_open_time = str(getattr(self, f'Spot{valve}OpenTime'))
        water_txt = getattr(self, f'TotalWaterSingle{valve}').text()
        before_txt = getattr(self, f'SpotCheckPreWeight{valve}').text()

        self._Save(
            valve=f'Spot{valve}',
            valve_open_time=str(valve_open_time),
            valve_open_interval=str(self.SpotInterval),
            cycle=str(self.SpotCycle),
            total_water=float(water_txt),
            tube_weight=float(before_txt),
            append=True)
        save.setStyleSheet("background-color : none")
        save.setChecked(False)

    def _LoadCalibrationParameters(self):
        self.WaterCalibrationPar = {}
        if os.path.exists(self.MainWindow.WaterCalibrationParFiles):
            with open(self.MainWindow.WaterCalibrationParFiles, 'r') as f:
                self.WaterCalibrationPar = json.load(f)
            logging.info('loaded water calibration parameters')
        else:
            logging.warning(
                'could not find water calibration parameters: {}'.format(self.MainWindow.WaterCalibrationParFiles))
            self.WaterCalibrationPar = {}

        # if no parameters are stored, store default parameters
        if 'Full' not in self.WaterCalibrationPar:
            self.WaterCalibrationPar['Full'] = {}
            self.WaterCalibrationPar['Full']['TimeMin'] = 0.02
            self.WaterCalibrationPar['Full']['TimeMax'] = 0.03
            self.WaterCalibrationPar['Full']['Stride'] = 0.01
            self.WaterCalibrationPar['Full']['Interval'] = 0.1
            self.WaterCalibrationPar['Full']['Cycle'] = 1000

        if 'Spot' not in self.WaterCalibrationPar:
            self.WaterCalibrationPar['Spot'] = {}
            self.WaterCalibrationPar['Spot']['Interval'] = 0.1
            self.WaterCalibrationPar['Spot']['Cycle'] = 200

        self.SpotCycle = float(self.WaterCalibrationPar['Spot']['Cycle'])
        self.SpotInterval = float(self.WaterCalibrationPar['Spot']['Interval'])

        # Add other calibration types to drop down list, but only if they have all parameters
        other_types = set(self.WaterCalibrationPar.keys()) - set(['Full', 'Spot'])
        required = set(['TimeMin', 'TimeMax', 'Stride', 'Interval', 'Cycle'])
        if len(other_types) > 0:
            for t in other_types:
                if required.issubset(set(self.WaterCalibrationPar[t].keys())):
                    self.CalibrationType.addItem(t)
                else:
                    logging.info('Calibration Type "{}" missing required fields'.format(t))

    def _StartCalibratingLeft(self):
        '''start the calibration loop of left valve'''

        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully == 0:
            self.StartCalibratingLeft.setChecked(False)
            self.StartCalibratingLeft.setStyleSheet("background-color : none")
            self.Warning.setText('Calibration was terminated!')
            self.Warning.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')
            self.StartCalibratingRight.setEnabled(True)
            return

        if self.StartCalibratingLeft.isChecked():
            # change button color
            self.StartCalibratingLeft.setStyleSheet("background-color : green;")
            QApplication.processEvents()
            # disable the right valve calibration
            self.StartCalibratingRight.setEnabled(False)
        else:
            self.StartCalibratingLeft.setChecked(True)
            self._Finished()
            return

        # Get Calibration parameters
        self.params = self.WaterCalibrationPar[self.CalibrationType.currentText()]

        # Populate options for calibrations
        self.left_opentimes = np.arange(
            float(self.params['TimeMin']),
            float(self.params['TimeMax']) + 0.0001,
            float(self.params['Stride'])
        )
        self.left_opentimes = [np.round(x, 3) for x in self.left_opentimes]
        self.LeftOpenTime.clear()
        for t in self.left_opentimes:
            self.LeftOpenTime.addItem('{0:.3f}'.format(t))
        self.WeightBeforeLeft.setText('')
        self.WeightAfterLeft.setText('')
        self.Warning.setText('')

        # Keep track of calibration status
        self.calibrating_left = True
        self.left_measurements = np.empty(np.shape(self.left_opentimes))
        self.left_measurements[:] = False

        # Start the first calibration
        self._CalibrateLeftOne()

    def _CalibrateLeftOne(self, repeat=False):
        '''
            Calibrate a single value
        '''

        # Determine what valve time we are measuring
        if not repeat:
            if np.all(self.left_measurements):
                self.Warning.setText('All measurements have been completed. Either press Repeat, or Finished')
                return
            next_index = np.where(self.left_measurements != True)[0][0]
            self.LeftOpenTime.setCurrentIndex(next_index)
        else:
            next_index = self.LeftOpenTime.currentIndex()
        logging.info('Calibrating left: {}'.format(self.left_opentimes[next_index]))

        # Shuffle weights of before/after
        self.WeightBeforeLeft.setText(self.WeightAfterLeft.text())
        self.WeightAfterLeft.setText('')

        # Prompt for before weight, using field value as default
        if self.WeightBeforeLeft.text() != '':
            before_weight = float(self.WeightBeforeLeft.text())
        else:
            before_weight = 0.0
        before_weight, ok = QInputDialog().getDouble(
            self,
            'Box {}, Left'.format(self.MainWindow.box_letter),
            "Before weight (g): ",
            before_weight,
            0, 1000, 4)
        if not ok:
            # User cancels
            self.Warning.setText('Press Continue, Repeat, or Finished')
            return
        self.WeightBeforeLeft.setText(str(before_weight))

        # Perform this measurement
        current_valve_opentime = self.left_opentimes[next_index]
        for i in range(int(self.params['Cycle'])):
            QApplication.processEvents()
            if (not self.EmergencyStop.isChecked()):
                self._CalibrationStatus(
                    float(current_valve_opentime),
                    self.WeightBeforeLeft.text(),
                    i, self.params['Cycle'], float(self.params['Interval'])
                )

                # set the valve open time
                self.MainWindow.Channel.LeftValue(float(current_valve_opentime) * 1000)
                # open the valve
                self.MainWindow.Channel3.ManualWater_Left(int(1))
                # delay
                time.sleep(current_valve_opentime + float(self.params['Interval']))
            else:
                self.Warning.setText('Please repeat measurement')
                self.WeightBeforeLeft.setText('')
                self.WeightAfterLeft.setText('')
                self.Repeat.setStyleSheet("color: white;background-color : mediumorchid;")
                self.Continue.setStyleSheet("color: black;background-color : none;")
                self.EmergencyStop.setChecked(False)
                self.EmergencyStop.setStyleSheet("background-color : none;")
                return

        # Prompt for weight
        final_tube_weight = 0.0
        final_tube_weight, ok = QInputDialog().getDouble(
            self,
            'Box {}, Left'.format(self.MainWindow.box_letter),
            "Weight after (g): ",
            final_tube_weight,
            0, 1000, 4)
        if not ok:
            self.Warning.setText('Please repeat measurement')
            self.WeightBeforeLeft.setText('')
            self.WeightAfterLeft.setText('')
            self.Repeat.setStyleSheet("color: white;background-color : mediumorchid;")
            self.Continue.setStyleSheet("color: black;background-color : none;")
            return
        self.WeightAfterLeft.setText(str(final_tube_weight))

        # Mark measurement as complete, save data, and update figure
        self.left_measurements[next_index] = True
        self._Save(
            valve='Left',
            valve_open_time=str(current_valve_opentime),
            valve_open_interval=str(self.params['Interval']),
            cycle=str(self.params['Cycle']),
            total_water=float(final_tube_weight),
            tube_weight=float(before_weight)
        )
        self._UpdateFigure()

        # Direct user for next steps
        if np.all(self.left_measurements):
            self.Warning.setText('Measurements recorded for all values. Please press Repeat, or Finished')
            self.Repeat.setStyleSheet("color: black;background-color : none;")
            self.Finished.setStyleSheet("color: white;background-color : mediumorchid;")
        else:
            self.Warning.setText('Please press Continue, Repeat, or Finished')
            self.Continue.setStyleSheet("color: white;background-color : mediumorchid;")
            self.Repeat.setStyleSheet("color: black;background-color : none;")

    def _StartCalibratingRight(self):
        '''start the calibration loop of right valve'''

        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully == 0:
            self.StartCalibratingRight.setChecked(False)
            self.StartCalibratingRight.setStyleSheet("background-color : none")
            self.Warning.setText('Calibration was terminated!')
            self.Warning.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')
            self.StartCalibratingRight.setEnabled(True)
            return

        if self.StartCalibratingRight.isChecked():
            # change button color
            self.StartCalibratingRight.setStyleSheet("background-color : green;")
            QApplication.processEvents()
            # disable the right valve calibration
            self.StartCalibratingRight.setEnabled(False)
        else:
            self.StartCalibratingRight.setChecked(True)
            self._Finished()
            return

        # Get Calibration parameters
        self.params = self.WaterCalibrationPar[self.CalibrationType.currentText()]

        # Populate options for calibrations
        self.right_opentimes = np.arange(
            float(self.params['TimeMin']),
            float(self.params['TimeMax']) + 0.0001,
            float(self.params['Stride'])
        )
        self.right_opentimes = [np.round(x, 3) for x in self.right_opentimes]
        self.RightOpenTime.clear()
        for t in self.right_opentimes:
            self.RightOpenTime.addItem('{0:.3f}'.format(t))
        self.WeightBeforeRight.setText('')
        self.WeightAfterRight.setText('')
        self.Warning.setText('')

        # Keep track of calibration status
        self.calibrating_right = True
        self.right_measurements = np.empty(np.shape(self.right_opentimes))
        self.right_measurements[:] = False

        # Start the first calibration
        self._CalibrateRightOne()

    def _CalibrateRightOne(self, repeat=False):
        '''
            Calibrate a single value
        '''

        # Determine what valve time we are measuring
        if not repeat:
            if np.all(self.right_measurements):
                self.Warning.setText('All measurements have been completed. Either press Repeat, or Finished')
                return
            next_index = np.where(self.right_measurements != True)[0][0]
            self.RightOpenTime.setCurrentIndex(next_index)
        else:
            next_index = self.RightOpenTime.currentIndex()
        logging.info('Calibrating right: {}'.format(self.right_opentimes[next_index]))

        # Shuffle weights of before/after
        self.WeightBeforeRight.setText(self.WeightAfterRight.text())
        self.WeightAfterRight.setText('')

        # Prompt for before weight, using field value as default
        if self.WeightBeforeRight.text() != '':
            before_weight = float(self.WeightBeforeRight.text())
        else:
            before_weight = 0.0
        before_weight, ok = QInputDialog().getDouble(
            self,
            'Box {}, Right'.format(self.MainWindow.box_letter),
            "Before weight (g): ",
            before_weight,
            0, 1000, 4)
        if not ok:
            # User cancels
            self.Warning.setText('Press Continue, Repeat, or Finished')
            return
        self.WeightBeforeRight.setText(str(before_weight))

        # Perform this measurement
        current_valve_opentime = self.right_opentimes[next_index]
        for i in range(int(self.params['Cycle'])):
            QApplication.processEvents()
            if (not self.EmergencyStop.isChecked()):
                self._CalibrationStatus(
                    float(current_valve_opentime),
                    self.WeightBeforeRight.text(),
                    i, self.params['Cycle'], float(self.params['Interval'])
                )

                # set the valve open time
                self.MainWindow.Channel.RightValue(float(current_valve_opentime) * 1000)
                # open the valve
                self.MainWindow.Channel3.ManualWater_Right(int(1))
                # delay
                time.sleep(current_valve_opentime + float(self.params['Interval']))
            else:
                self.Warning.setText('Please repeat measurement')
                self.WeightBeforeRight.setText('')
                self.WeightAfterRight.setText('')
                self.Repeat.setStyleSheet("color: white;background-color : mediumorchid;")
                self.Continue.setStyleSheet("color: black;background-color : none;")
                self.EmergencyStop.setChecked(False)
                self.EmergencyStop.setStyleSheet("background-color : none;")
                return

        # Prompt for weight
        final_tube_weight = 0.0
        final_tube_weight, ok = QInputDialog().getDouble(
            self,
            'Box {}, Right'.format(self.MainWindow.box_letter),
            "Weight after (g): ",
            final_tube_weight,
            0, 1000, 4)
        if not ok:
            self.Warning.setText('Please repeat measurement')
            self.WeightBeforeRight.setText('')
            self.WeightAfterRight.setText('')
            self.Repeat.setStyleSheet("color: white;background-color : mediumorchid;")
            self.Continue.setStyleSheet("color: black;background-color : none;")
            return
        self.WeightAfterRight.setText(str(final_tube_weight))

        # Mark measurement as complete, save data, and update figure
        self.right_measurements[next_index] = True
        self._Save(
            valve='Right',
            valve_open_time=str(current_valve_opentime),
            valve_open_interval=str(self.params['Interval']),
            cycle=str(self.params['Cycle']),
            total_water=float(final_tube_weight),
            tube_weight=float(before_weight)
        )
        self._UpdateFigure()

        # Direct user for next steps
        if np.all(self.right_measurements):
            self.Warning.setText('Measurements recorded for all values. Please press Repeat, or Finished')
            self.Repeat.setStyleSheet("color: black;background-color : none;")
        else:
            self.Warning.setText('Please press Continue, Repeat, or Finished')
            self.Continue.setStyleSheet("color: white;background-color : mediumorchid;")
            self.Repeat.setStyleSheet("color: black;background-color : none;")

    def _CalibrationStatus(self, opentime, weight_before, i, cycle, interval):
        self.Warning.setText(
            'Measuring left valve: {}s'.format(opentime) + \
            '\nEmpty tube weight: {}g'.format(weight_before) + \
            '\nCurrent cycle: ' + str(i + 1) + '/{}'.format(int(cycle)) + \
            '\nTime remaining: {}'.format(self._TimeRemaining(
                i, cycle, opentime, interval))
        )
        self.Warning.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')

    def _Save(self, valve, valve_open_time, valve_open_interval, cycle, total_water, tube_weight, append=False):
        '''save the calibrated result and update the figure'''
        if total_water == '' or tube_weight == '':
            return
        # total water equals to total water minus tube weight
        total_water = (total_water - tube_weight) * 1000  # The input unit is g and converted to mg.
        WaterCalibrationResults = self.WaterCalibrationResults.copy()
        current_time = datetime.now()
        date_str = current_time.strftime("%Y-%m-%d")
        # Check and assign items to the nested dictionary
        if date_str not in WaterCalibrationResults:
            WaterCalibrationResults[date_str] = {}
        if valve not in WaterCalibrationResults[date_str]:
            WaterCalibrationResults[date_str][valve] = {}
        if valve_open_time not in WaterCalibrationResults[date_str][valve]:
            WaterCalibrationResults[date_str][valve][valve_open_time] = {}
        if valve_open_interval not in WaterCalibrationResults[date_str][valve][valve_open_time]:
            WaterCalibrationResults[date_str][valve][valve_open_time][valve_open_interval] = {}
        if cycle not in WaterCalibrationResults[date_str][valve][valve_open_time][valve_open_interval]:
            WaterCalibrationResults[date_str][valve][valve_open_time][valve_open_interval][cycle] = []
        if append:
            WaterCalibrationResults[date_str][valve][valve_open_time][valve_open_interval][cycle].append(
                np.round(total_water, 1))
        else:
            WaterCalibrationResults[date_str][valve][valve_open_time][valve_open_interval][cycle] = [
                np.round(total_water, 1)]
        self.WaterCalibrationResults = WaterCalibrationResults.copy()

        # save to the json file
        if not os.path.exists(os.path.dirname(self.MainWindow.WaterCalibrationFiles)):
            os.makedirs(os.path.dirname(self.MainWindow.WaterCalibrationFiles))
        with open(self.MainWindow.WaterCalibrationFiles, "w") as file:
            json.dump(WaterCalibrationResults, file, indent=4)

        # update the figure
        self._UpdateFigure()

    def _UpdateFigure(self):
        '''plot the calibration result'''
        if self.ToInitializeVisual == 1:  # only run once
            PlotM = PlotWaterCalibration(water_win=self)
            self.PlotM = PlotM
            layout = self.VisuCalibration.layout()
            if layout is not None:
                for i in reversed(range(layout.count())):
                    layout.itemAt(i).widget().setParent(None)
                layout.invalidate()
            if layout is None:
                layout = QVBoxLayout(self.VisuCalibration)
            toolbar = NavigationToolbar(PlotM, self)
            toolbar.setMaximumHeight(20)
            toolbar.setMaximumWidth(300)
            layout.addWidget(toolbar)
            layout.addWidget(PlotM)
            self.ToInitializeVisual = 0
        self.PlotM._Update()

    def _ToggleValve(self, button, valve: Literal['Left', 'Right']):
        """
        Toggle open/close state of specified valve and set up logic based on button pressed
        :param button: button that was pressed
        :param valve: which valve to open. Restricted to Right or Left
        """

        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully == 0:
            return

        set_valve_time = getattr(self.MainWindow.Channel, f'{valve}Value')
        toggle_valve_state = getattr(self.MainWindow.Channel3, f'ManualWater_{valve}')
        open_timer = getattr(self, f'{valve.lower()}_open_timer')
        close_timer = getattr(self, f'{valve.lower()}_close_timer')
        text_timer = getattr(self, f'{valve.lower()}_text_timer')

        if button.isChecked():  # open valve
            button.setStyleSheet("background-color : green;")
            set_valve_time(float(1000) * 1000)  # set the valve open time to max value
            toggle_valve_state(int(1))  # set valve initially open

            if button.text() == f'Open {valve.lower()} 5ml':  # set up additional logic to only open for 5ml
                five_ml_time_ms = round(self._VolumeToTime(5000, valve) * 1000)  # calculate time for valve to stay open
                close_timer.setInterval(five_ml_time_ms)  # set interval of valve close time to be five_ml_time_ms
                close_timer.setSingleShot(True)  # only trigger once when 5ml has been expelled
                text_timer.start()  # start timer to update text
                close_timer.start()

            open_timer.start()

        else:  # close open valve
            # change button color
            button.setStyleSheet("background-color : none")
            open_timer.stop()
            if f'Open {valve.lower()} 5ml' in button.text():
                close_timer.stop()
                text_timer.stop()
                button.setText(f'Open {valve.lower()} 5ml')

            # close the valve
            toggle_valve_state(int(1))

            # reset the default valve open time
            time.sleep(0.01)
            set_valve_time(float(getattr(self.MainWindow, f'{valve}Value').text()) * 1000)

    def reopen_valve(self, valve: Literal['Left', 'Right']):
        """Function to reopen the right or left water line open. Valve must be open prior to calling this function.
        Calling ManualWater_ will toggle state of valve so need to call twice on already open valve.
        param valve: string specifying right or left valve"""

        # get correct function based on input valve name
        getattr(self.MainWindow.Channel3, f'ManualWater_{valve}')(int(1))  # close valve
        getattr(self.MainWindow.Channel3, f'ManualWater_{valve}')(int(1))  # open valve

    def _TimeRemaining(self, i, cycles, opentime, interval):
        total_seconds = (cycles - i) * (opentime + interval)
        minutes = int(np.floor(total_seconds / 60))
        seconds = int(np.ceil(np.mod(total_seconds, 60)))
        return '{}:{:02}'.format(minutes, seconds)

    def _VolumeToTime(self, volume, valve: Literal['Left', 'Right']):
        """
        Function to return the amount of time(s) it takes for water line to flush specified volume of water (mg)
        :param volume: volume to flush in mg
        :param valve: string specifying right or left valve
        """
        # x = (y-b)/m
        if hasattr(self.MainWindow, 'latest_fitting') and self.MainWindow.latest_fitting != {}:
            fit = self.MainWindow.latest_fitting[valve]
            m = fit[0]
            b = fit[1]
        else:
            m = 1
            b = 0
        return (volume - b) / m

    def _TimeToVolume(self, time):
        # y= mx +b
        if hasattr(self.MainWindow, 'latest_fitting'):
            print(self.MainWindow.latest_fitting)
        else:
            m = 1
            b = 0
        return time * m + b

    def _SpotCheck(self, valve: Literal['Left', 'Right']):

        """
        Calibration of valve in a different thread
        :param valve: string specifying which valve
        """

        spot_check = getattr(self, f'SpotCheck{valve}')
        save = getattr(self, f'Save{valve}')
        total_water = getattr(self, f'TotalWaterSingle{valve}')
        pre_weight = getattr(self, f'SpotCheckPreWeight{valve}')
        volume = getattr(self, f'Spot{valve}Volume').text()

        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully == 0:
            spot_check.setChecked(False)
            spot_check.setStyleSheet("background-color : none;")
            save.setStyleSheet("color: black;background-color : none;")
            total_water.setText('')
            pre_weight.setText('')
            return

        if spot_check.isChecked():
            if valve not in self.MainWindow.latest_fitting:
                reply = QMessageBox.critical(self, f'Spot check {valve.lower()}',
                                             'Please perform full calibration before spot check',
                                             QMessageBox.Ok)
                logging.warning('Cannot perform spot check before full calibration')
                spot_check.setStyleSheet("background-color : none;")
                spot_check.setChecked(False)
                self.Warning.setText('')
                pre_weight.setText('')
                total_water.setText('')
                save.setStyleSheet("color: black;background-color : none;")
                return

            logging.info(f'starting spot check {valve.lower()}')
            spot_check.setStyleSheet("background-color : green;")

            # Get empty tube weight, using field value as default
            if pre_weight.text() != '':
                empty_tube_weight = float(pre_weight.text())
            else:
                empty_tube_weight = 0.0
            empty_tube_weight, ok = QInputDialog().getDouble(
                self,
                f'Box {self.MainWindow.box_letter},  f{valve}',
                "Empty tube weight (g): ",
                empty_tube_weight,
                0, 1000, 4)
            if not ok:
                # User cancels
                logging.warning('user cancelled spot calibration')
                spot_check.setStyleSheet("background-color : none;")
                spot_check.setChecked(False)
                self.Warning.setText(f'Spot check {valve.lower()} cancelled')
                pre_weight.setText('')
                total_water.setText('')
                save.setStyleSheet("color: black;background-color : none;")
                return
            pre_weight.setText(str(empty_tube_weight))

        # Determine what open time to use
        open_time = self._VolumeToTime(float(volume), valve)
        open_time = np.round(open_time, 4)
        setattr(self, f'Spot{valve}OpenTime', open_time)
        logging.info('Using a calibration spot check of {}s to deliver {}uL'.format(open_time,
                                                                                    volume))

        # start the open/close/delay cycle
        for i in range(int(self.SpotCycle)):
            QApplication.processEvents()
            if spot_check.isChecked() and (not self.EmergencyStop.isChecked()):
                self.Warning.setText(
                    f'Measuring {valve.lower()} valve: {volume}uL' + \
                    '\nEmpty tube weight: {}g'.format(empty_tube_weight) + \
                    '\nCurrent cycle: ' + str(i + 1) + '/{}'.format(int(self.SpotCycle)) + \
                    '\nTime remaining: {}'.format(self._TimeRemaining(
                        i, self.SpotCycle, open_time, self.SpotInterval))
                )
                self.Warning.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')

                # set the valve open time
                getattr(self.MainWindow.Channel, f'{valve}Value')(float(open_time) * 1000)
                # open the valve
                getattr(self.MainWindow.Channel3, f'ManualWater_{valve}')(int(1))
                # delay
                time.sleep(open_time + self.SpotInterval)
            else:
                self.Warning.setText(f'Spot check {valve.lower()} cancelled')
                pre_weight.setText('')
                total_water.setText('')
                save.setStyleSheet("color: black;background-color : none;")
                self.EmergencyStop.setChecked(False)
                self.EmergencyStop.setStyleSheet("background-color : none;")
                spot_check.setChecked(False)
                spot_check.setStyleSheet("background-color : none")
                return

        # Get final value, using field as default
        if total_water.text() != '':
            final_tube_weight = float(total_water.text())
        else:
            final_tube_weight = 0.0
        final_tube_weight, ok = QInputDialog().getDouble(
            self,
            f'Box {self.MainWindow.box_letter}, {valve}',
            "Final tube weight (g): ",
            final_tube_weight,
            0, 1000, 4)
        total_water.setText(str(final_tube_weight))

        # Determine result
        result = (final_tube_weight - empty_tube_weight) / int(self.SpotCycle) * 1000

        error = result - float(volume)
        error = np.round(error, 4)
        self.Warning.setText(
            f'Measuring {valve.lower()} valve: {volume}uL' + \
            '\nEmpty tube weight: {}g'.format(empty_tube_weight) + \
            '\nFinal tube weight: {}g'.format(final_tube_weight) + \
            '\nAvg. error from target: {}uL'.format(error)
        )

        TOLERANCE = float(volume) * .15
        if np.abs(error) > TOLERANCE:
            reply = QMessageBox.critical(self, f'Spot check {valve}',
                                         'Measurement is outside expected tolerance.<br><br>'
                                         'If this is a typo, please press cancel.'
                                         '<br><br><span style="color:purple;font-weight:bold">IMPORTANT</span>: '
                                         'If the measurement was correctly entered, please press okay and repeat'
                                         'spot check once.'.format(np.round(result, 2)),
                                         QMessageBox.Ok | QMessageBox.Cancel)
            if reply == QMessageBox.Cancel:
                logging.warning('Spot check discarded due to type', extra={'tags': self.MainWindow.warning_log_tag})
            else:
                logging.error('Water calibration spot check, {}, exceeds tolerance: {}'.format(valve, error))
                save.setStyleSheet("color: white;background-color : mediumorchid;")
                self.Warning.setText(
                    f'Measuring {valve.lower()} valve: {volume}uL' + \
                    '\nEmpty tube weight: {}g'.format(empty_tube_weight) + \
                    '\nFinal tube weight: {}g'.format(final_tube_weight) + \
                    '\nAvg. error from target: {}uL'.format(error)
                )
                self._SaveValve(valve)
                if self.check_spot_failures(valve) >= 2:
                    msg = 'Two or more spot checks, {}, have failed in the last 30 days. Please create a SIPE ticket to ' \
                          'check rig.'.format(valve)
                    logging.error(msg, extra={'tags': self.MainWindow.warning_log_tag})
                    QMessageBox.critical(self, f'Spot check {valve}', msg, QMessageBox.Ok)
        else:
            self.Warning.setText(
                f'Measuring {valve.lower()} valve: {volume}uL' + \
                '\nEmpty tube weight: {}g'.format(empty_tube_weight) + \
                '\nFinal tube weight: {}g'.format(final_tube_weight) + \
                '\nAvg. error from target: {}uL'.format(error) + \
                '\nCalibration saved'
            )
            self._SaveValve(valve)

        # set the default valve open time
        value = getattr(self.MainWindow, f'{valve}Value').text()
        getattr(self.MainWindow.Channel, f'{valve}Value')(float(value) * 1000)

        spot_check.setChecked(False)
        spot_check.setStyleSheet("background-color : none")
        logging.info(f'Done with spot check {valve}')

    def check_spot_failures(self, valve: Literal['Left', 'Right']) -> int:

        """"
        Parse water calibration file to check if 2 spot failures have occurred in the past 30 days
        :param valve: side to check for failures
        :return integer signifying the number of spot checks that have failed within the last 30 days
        """

        today = datetime.now()
        # filter spot counts within the last 30 days
        spot_counts = {k: v for k, v in self.WaterCalibrationResults.items() if f'Spot{valve}' in v.keys()
                       and (today - datetime.strptime(k, "%Y-%m-%d")).days < 30}

        # based on information in spot check dictionary, calculate volume
        over_tolerance = 0
        volume = float(getattr(self, f'Spot{valve}Volume').text())
        TOLERANCE = volume * .15
        for info in spot_counts.values():
            for intervals in info[f'Spot{valve}'].values():
                for interval in intervals.values():
                    for cycle, measurements in interval.items():
                        for measurement in measurements:
                            result = float(measurement) / float(cycle)
                            if np.abs(np.round(result - volume, 4)) > TOLERANCE:
                                over_tolerance += 1
        return over_tolerance


class CameraDialog(QDialog):
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        uic.loadUi('Camera.ui', self)

        self.MainWindow = MainWindow
        self._connectSignalsSlots()
        self.camera_start_time = ''
        self.camera_stop_time = ''

        self.info_label = QLabel(parent=self)
        self.info_label.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')
        self.info_label.move(50, 350)
        self.info_label.setFixedSize(171, 51)
        self.info_label.setAlignment(Qt.AlignCenter)

    def _connectSignalsSlots(self):
        self.StartRecording.toggled.connect(self._StartCamera)
        self.StartPreview.toggled.connect(self._start_preview)
        self.AutoControl.currentIndexChanged.connect(self._AutoControl)
        self.OpenSaveFolder.clicked.connect(self._OpenSaveFolder)

    def _OpenSaveFolder(self):
        '''Open the log/save folder of the camera'''

        text = self.info_label.text()
        if hasattr(self.MainWindow, 'Ot_log_folder'):
            try:
                subprocess.Popen(['explorer',
                                  os.path.join(os.path.dirname(os.path.dirname(self.MainWindow.Ot_log_folder)),
                                               'behavior-videos')])
            except Exception as e:
                logging.error(str(e))
                logging.warning('No logging folder found!', extra={'tags': self.MainWindow.warning_log_tag})
                if 'No logging folder found!' not in text:
                    self.info_label.setText(text + '\n No logging folder found!')
        else:
            logging.warning('No logging folder found!', extra={'tags': self.MainWindow.warning_log_tag})
            if 'No logging folder found!' not in text:
                self.info_label.setText(text + '\n No logging folder found!')

    def _start_preview(self):
        '''Start the camera preview'''
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully == 0:
            return
        if self.StartPreview.isChecked():
            # disable the start recording button
            self.StartRecording.setEnabled(False)
            # subscribe to the camera preview
            self.MainWindow.Channel.CameraStartType(int(2))
            # set the camera frequency
            self.MainWindow.Channel.CameraFrequency(int(self.FrameRate.text()))
            # start the video triggers
            self.MainWindow.Channel.CameraControl(int(1))

            self.StartPreview.setStyleSheet("background-color : green;")
            logging.info('Camera is on', extra={'tags': self.MainWindow.warning_log_tag})
            self.info_label.setText('Camera is on')

        else:
            # enable the start recording button
            self.StartRecording.setEnabled(True)
            # stop camera triggers
            self.MainWindow.Channel.CameraControl(int(2))
            # stop the camera preview workflow
            self.MainWindow.Channel.StopCameraPreview(int(1))

            self.StartPreview.setStyleSheet("background-color : none;")
            logging.info('Camera is off', extra={'tags': self.MainWindow.warning_log_tag})
            self.info_label.setText('Camera is off')

    def _AutoControl(self):
        '''Trigger the camera during the start of a new behavior session'''
        if self.AutoControl.currentText() == 'Yes':
            self.StartRecording.setChecked(False)

    def _StartCamera(self):
        '''Start/stop the camera recording based on if the StartRecording button is toggled on/off'''

        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully == 0:
            return
        if self.StartRecording.isChecked():
            self.StartRecording.setStyleSheet("background-color : green;")
            logging.info('Camera is turning on', extra={'tags': self.MainWindow.warning_log_tag})
            self.info_label.setText('Camera is turning on')
            QApplication.processEvents()
            # untoggle the preview button
            if self.StartPreview.isChecked():
                self.StartPreview.setChecked(False)
                # sleep for 1 second to make sure the trigger is off
                time.sleep(1)
            # Start logging if the formal logging is not started
            if self.MainWindow.logging_type != 0 or self.MainWindow.logging_type == -1:
                self.MainWindow.Ot_log_folder = self.MainWindow._restartlogging()
            # set to check drop frame as true
            self.MainWindow.to_check_drop_frames = 1
            # disable the start preview button
            self.StartPreview.setEnabled(False)
            # disable the Load button
            self.MainWindow.Load.setEnabled(False)
            # disable the Animal ID
            self.MainWindow.ID.setEnabled(False)
            # set the camera start type
            self.MainWindow.Channel.CameraStartType(int(1))
            # set the camera frequency.
            self.MainWindow.Channel.CameraFrequency(int(self.FrameRate.text()))
            # start the video triggers
            self.MainWindow.Channel.CameraControl(int(1))
            time.sleep(5)
            self.camera_start_time = str(datetime.now())
            logging.info('Camera is on!', extra={'tags': [self.MainWindow.warning_log_tag]})
            self.info_label.setText('Camera is on!')
        else:
            self.StartRecording.setStyleSheet("background-color : none")
            logging.info('Camera is turning off', extra={'tags': self.MainWindow.warning_log_tag})
            self.info_label.setText('Camera is turning off')
            QApplication.processEvents()
            self.MainWindow.Channel.CameraControl(int(2))
            self.camera_stop_time = str(datetime.now())
            time.sleep(5)
            logging.info('Camera is off!', extra={'tags': [self.MainWindow.warning_log_tag]})
            self.info_label.setText('Camera is off!')


def is_file_in_use(file_path):
    '''check if the file is open'''
    if os.path.exists(file_path):
        try:
            os.rename(file_path, file_path)
            return False
        except OSError as e:
            return True


class LaserCalibrationDialog(QDialog):
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        self.MainWindow = MainWindow
        uic.loadUi('CalibrationLaser.ui', self)

        self._connectSignalsSlots()
        self.SleepComplete = 1
        self.SleepComplete2 = 0
        self.Initialize1 = 0
        self.Initialize2 = 0
        self.threadpool1 = QThreadPool()
        self.threadpool2 = QThreadPool()
        self.laser_tags = [1, 2]
        self.condition_idx = [1, 2, 3, 4, 5, 6]

    def _connectSignalsSlots(self):
        self.Open.clicked.connect(self._Open)
        self.KeepOpen.clicked.connect(self._KeepOpen)
        # self.CopyFromOpto.clicked.connect(self._CopyFromOpto)
        self.Save.clicked.connect(self._Save)
        self.Capture.clicked.connect(self._Capture)
        self.LaserColor_1.currentIndexChanged.connect(self._LaserColor_1)
        self.Protocol_1.activated.connect(self._activated_1)
        self.Protocol_1.currentIndexChanged.connect(self._activated_1)
        self.Flush_DO0.clicked.connect(self._FLush_DO0)
        self.Flush_DO1.clicked.connect(self._FLush_DO1)
        self.Flush_DO2.clicked.connect(self._FLush_DO2)
        self.Flush_DO3.clicked.connect(self._FLush_DO3)
        self.Flush_Port2.clicked.connect(self._FLush_Port2)
        self.CopyToSession.clicked.connect(self._CopyToSession)

    def _CopyToSession(self):
        '''Copy the calibration data to the session calibration'''
        if self.Location_1.currentText() == 'Laser_1':
            self.MainWindow.Opto_dialog.laser_1_calibration_voltage.setText(self.voltage.text())
            self.MainWindow.Opto_dialog.laser_1_calibration_power.setText(self.LaserPowerMeasured.text())
        elif self.Location_1.currentText() == 'Laser_2':
            self.MainWindow.Opto_dialog.laser_2_calibration_voltage.setText(self.voltage.text())
            self.MainWindow.Opto_dialog.laser_2_calibration_power.setText(self.LaserPowerMeasured.text())

    def _FLush_DO0(self):
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully == 0:
            return
        self.MainWindow.Channel.DO0(int(1))
        self.MainWindow.Channel.receive()

    def _FLush_DO1(self):
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully == 0:
            return
        self.MainWindow.Channel.DO1(int(1))

    def _FLush_DO2(self):
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully == 0:
            return
        # self.MainWindow.Channel.DO2(int(1))
        self.MainWindow.Channel.receive()

    def _FLush_DO3(self):
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully == 0:
            return
        self.MainWindow.Channel.DO3(int(1))
        self.MainWindow.Channel.receive()

    def _FLush_Port2(self):
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully == 0:
            return
        self.MainWindow.Channel.Port2(int(1))

    def _LaserColor_1(self):
        self._LaserColor(1)

    def _activated_1(self):
        self._activated(1)

    def _activated(self, Numb):
        '''enable/disable items based on protocols and laser start/end'''
        Inactlabel1 = 15  # pulse duration
        Inactlabel2 = 13  # frequency
        Inactlabel3 = 14  # Ramping down
        if getattr(self, 'Protocol_' + str(Numb)).currentText() == 'Sine':
            getattr(self, 'label' + str(Numb) + '_' + str(Inactlabel1)).setEnabled(False)
            getattr(self, 'PulseDur_' + str(Numb)).setEnabled(False)
            getattr(self, 'label' + str(Numb) + '_' + str(Inactlabel2)).setEnabled(True)
            getattr(self, 'Frequency_' + str(Numb)).setEnabled(True)
            getattr(self, 'label' + str(Numb) + '_' + str(Inactlabel3)).setEnabled(True)
            getattr(self, 'RD_' + str(Numb)).setEnabled(True)
        if getattr(self, 'Protocol_' + str(Numb)).currentText() == 'Pulse':
            getattr(self, 'label' + str(Numb) + '_' + str(Inactlabel1)).setEnabled(True)
            getattr(self, 'PulseDur_' + str(Numb)).setEnabled(True)
            getattr(self, 'label' + str(Numb) + '_' + str(Inactlabel2)).setEnabled(True)
            getattr(self, 'Frequency_' + str(Numb)).setEnabled(True)
            getattr(self, 'label' + str(Numb) + '_' + str(Inactlabel3)).setEnabled(False)
            getattr(self, 'RD_' + str(Numb)).setEnabled(False)
        if getattr(self, 'Protocol_' + str(Numb)).currentText() == 'Constant':
            getattr(self, 'label' + str(Numb) + '_' + str(Inactlabel1)).setEnabled(False)
            getattr(self, 'PulseDur_' + str(Numb)).setEnabled(False)
            getattr(self, 'label' + str(Numb) + '_' + str(Inactlabel2)).setEnabled(False)
            getattr(self, 'Frequency_' + str(Numb)).setEnabled(False)
            getattr(self, 'label' + str(Numb) + '_' + str(Inactlabel3)).setEnabled(True)
            getattr(self, 'RD_' + str(Numb)).setEnabled(True)

    def _LaserColor(self, Numb):
        ''' enable/disable items based on laser (blue/green/orange/red/NA)'''
        Inactlabel = [2, 3, 5, 12, 13, 14, 15]
        if getattr(self, 'LaserColor_' + str(Numb)).currentText() == 'NA':
            Label = False
        else:
            Label = True
        getattr(self, 'Location_' + str(Numb)).setEnabled(Label)
        getattr(self, 'Duration_' + str(Numb)).setEnabled(Label)
        getattr(self, 'Protocol_' + str(Numb)).setEnabled(Label)
        getattr(self, 'Frequency_' + str(Numb)).setEnabled(Label)
        getattr(self, 'RD_' + str(Numb)).setEnabled(Label)
        getattr(self, 'PulseDur_' + str(Numb)).setEnabled(Label)
        for i in Inactlabel:
            getattr(self, 'label' + str(Numb) + '_' + str(i)).setEnabled(Label)
        if getattr(self, 'LaserColor_' + str(Numb)).currentText() != 'NA':
            getattr(self, '_activated_' + str(Numb))()

    def _GetLaserWaveForm(self):
        '''Get the waveform of the laser. It dependens on color/duration/protocol(frequency/RD/pulse duration)/locations/laser power'''
        N = str(1)
        # CLP, current laser parameter
        self.CLP_Color = getattr(self, 'LC_LaserColor_' + N)
        self.CLP_Location = getattr(self, 'LC_Location_' + N)
        self.CLP_Duration = float(getattr(self, 'LC_Duration_' + N))
        self.CLP_Protocol = getattr(self, 'LC_Protocol_' + N)
        self.CLP_Frequency = float(getattr(self, 'LC_Frequency_' + N))
        self.CLP_RampingDown = float(getattr(self, 'LC_RD_' + N))
        self.CLP_PulseDur = getattr(self, 'LC_PulseDur_' + N)
        self.CLP_SampleFrequency = float(self.LC_SampleFrequency)
        self.CLP_CurrentDuration = self.CLP_Duration
        self.CLP_InputVoltage = float(self.voltage.text())
        # generate the waveform based on self.CLP_CurrentDuration and Protocol, Frequency, RampingDown, PulseDur
        self._GetLaserAmplitude()
        # send the trigger source. It's '/Dev1/PFI0' ( P2.0 of NIdaq USB6002) by default
        self.MainWindow.Channel.TriggerSource('/Dev1/PFI0')
        # dimension of self.CurrentLaserAmplitude indicates how many locations do we have
        for i in range(len(self.CurrentLaserAmplitude)):
            # in some cases the other paramters except the amplitude could also be different
            self._ProduceWaveForm(self.CurrentLaserAmplitude[i])
            setattr(self, 'WaveFormLocation_' + str(i + 1), self.my_wave)
            setattr(self, f"Location{i + 1}_Size", getattr(self, f"WaveFormLocation_{i + 1}").size)
            # send waveform and send the waveform size
            getattr(self.MainWindow.Channel, 'Location' + str(i + 1) + '_Size')(
                int(getattr(self, 'Location' + str(i + 1) + '_Size')))
            getattr(self.MainWindow.Channel4, 'WaveForm' + str(1) + '_' + str(i + 1))(
                str(getattr(self, 'WaveFormLocation_' + str(i + 1)).tolist())[1:-1])
        FinishOfWaveForm = self.MainWindow.Channel4.receive()

    def _ProduceWaveForm(self, Amplitude):
        '''generate the waveform based on Duration and Protocol, Laser Power, Frequency, RampingDown, PulseDur and the sample frequency'''
        if self.CLP_Protocol == 'Sine':
            resolution = self.CLP_SampleFrequency * self.CLP_CurrentDuration  # how many datapoints to generate
            cycles = self.CLP_CurrentDuration * self.CLP_Frequency  # how many sine cycles
            length = np.pi * 2 * cycles
            self.my_wave = Amplitude * (
                        1 + np.sin(np.arange(0 + 1.5 * math.pi, length + 1.5 * math.pi, length / resolution))) / 2
            # add ramping down
            if self.CLP_RampingDown > 0:
                if self.CLP_RampingDown > self.CLP_CurrentDuration:
                    logging.warning('Ramping down is longer than the laser duration!',
                                    extra={'tags': [self.MainWindow.warning_log_tag]})
                else:
                    Constant = np.ones(
                        int((self.CLP_CurrentDuration - self.CLP_RampingDown) * self.CLP_SampleFrequency))
                    RD = np.arange(1, 0, -1 / (np.shape(self.my_wave)[0] - np.shape(Constant)[0]))
                    RampingDown = np.concatenate((Constant, RD), axis=0)
                    self.my_wave = self.my_wave * RampingDown
            self.my_wave = np.append(self.my_wave, [0, 0])
        elif self.CLP_Protocol == 'Pulse':
            if self.CLP_PulseDur == 'NA':
                logging.warning('Pulse duration is NA!', extra={'tags': [self.MainWindow.warning_log_tag]})
            else:
                self.CLP_PulseDur = float(self.CLP_PulseDur)
                PointsEachPulse = int(self.CLP_SampleFrequency * self.CLP_PulseDur)
                PulseIntervalPoints = int(1 / self.CLP_Frequency * self.CLP_SampleFrequency - PointsEachPulse)
                if PulseIntervalPoints < 0:
                    logging.warning('Pulse frequency and pulse duration are not compatible!',
                                    extra={'tags': [self.MainWindow.warning_log_tag]})
                TotalPoints = int(self.CLP_SampleFrequency * self.CLP_CurrentDuration)
                PulseNumber = np.floor(self.CLP_CurrentDuration * self.CLP_Frequency)
                EachPulse = Amplitude * np.ones(PointsEachPulse)
                PulseInterval = np.zeros(PulseIntervalPoints)
                WaveFormEachCycle = np.concatenate((EachPulse, PulseInterval), axis=0)
                self.my_wave = np.empty(0)
                # pulse number should be greater than 0
                if PulseNumber > 1:
                    for i in range(int(PulseNumber - 1)):
                        self.my_wave = np.concatenate((self.my_wave, WaveFormEachCycle), axis=0)
                else:
                    logging.warning('Pulse number is less than 1!', extra={'tags': [self.MainWindow.warning_log_tag]})
                    return
                self.my_wave = np.concatenate((self.my_wave, EachPulse), axis=0)
                self.my_wave = np.concatenate((self.my_wave, np.zeros(TotalPoints - np.shape(self.my_wave)[0])), axis=0)
                self.my_wave = np.append(self.my_wave, [0, 0])
        elif self.CLP_Protocol == 'Constant':
            resolution = self.CLP_SampleFrequency * self.CLP_CurrentDuration  # how many datapoints to generate
            self.my_wave = Amplitude * np.ones(int(resolution))
            if self.CLP_RampingDown > 0:
                # add ramping down
                if self.CLP_RampingDown > self.CLP_CurrentDuration:
                    logging.warning('Ramping down is longer than the laser duration!',
                                    extra={'tags': [self.MainWindow.warning_log_tag]})
                else:
                    Constant = np.ones(
                        int((self.CLP_CurrentDuration - self.CLP_RampingDown) * self.CLP_SampleFrequency))
                    RD = np.arange(1, 0, -1 / (np.shape(self.my_wave)[0] - np.shape(Constant)[0]))
                    RampingDown = np.concatenate((Constant, RD), axis=0)
                    self.my_wave = self.my_wave * RampingDown
            self.my_wave = np.append(self.my_wave, [0, 0])
        else:
            logging.warning('Unidentified optogenetics protocol!', extra={'tags': [self.MainWindow.warning_log_tag]})

    def _GetLaserAmplitude(self):
        '''the voltage amplitude dependens on Protocol, Laser Power, Laser color, and the stimulation locations<>'''
        if self.CLP_Location == 'Laser_1':
            self.CurrentLaserAmplitude = [self.CLP_InputVoltage, 0]
        elif self.CLP_Location == 'Laser_2':
            self.CurrentLaserAmplitude = [0, self.CLP_InputVoltage]
        elif self.CLP_Location == 'Both':
            self.CurrentLaserAmplitude = [self.CLP_InputVoltage, self.CLP_InputVoltage]
        else:
            logging.warning('No stimulation location defined!', extra={'tags': [self.MainWindow.warning_log_tag]})

    # get training parameters
    def _GetTrainingParameters(self, win):
        '''Get training parameters'''
        Prefix = 'LC'  # laser calibration
        # Iterate over each container to find child widgets and store their values in self
        for container in [win.LaserCalibration_dialog]:
            # Iterate over each child of the container that is a QLineEdit or QDoubleSpinBox
            for child in container.findChildren((QtWidgets.QLineEdit, QtWidgets.QDoubleSpinBox)):
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store the child's text value
                setattr(self, Prefix + '_' + child.objectName(), child.text())
            # Iterate over each child of the container that is a QComboBox
            for child in container.findChildren(QtWidgets.QComboBox):
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store the child's current text value
                setattr(self, Prefix + '_' + child.objectName(), child.currentText())
            # Iterate over each child of the container that is a QPushButton
            for child in container.findChildren(QtWidgets.QPushButton):
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store whether the child is checked or not
                setattr(self, Prefix + '_' + child.objectName(), child.isChecked())

    def _InitiateATrial(self):
        '''Initiate calibration in bonsai'''
        # start generating waveform in bonsai
        self.MainWindow.Channel.OptogeneticsCalibration(int(1))
        self.MainWindow.Channel.receive()

    def _CopyFromOpto(self):
        '''Copy the optogenetics parameters'''
        condition = self.CopyCondition.currentText().split('_')[1]
        copylaser = self.CopyLaser.currentText().split('_')[1]
        if self.MainWindow.Opto_dialog.__getattribute__("LaserColor_" + condition).currentText() == "NA":
            return
        # self.Duration_1.setText(self.MainWindow.Opto_dialog.__getattribute__("Duration_" + condition).text())
        self.Frequency_1.setText(self.MainWindow.Opto_dialog.__getattribute__("Frequency_" + condition).currentText())
        self.RD_1.setText(self.MainWindow.Opto_dialog.__getattribute__("RD_" + condition).text())
        self.PulseDur_1.setText(self.MainWindow.Opto_dialog.__getattribute__("PulseDur_" + condition).text())
        self.LaserColor_1.setCurrentIndex(
            self.MainWindow.Opto_dialog.__getattribute__("LaserColor_" + condition).currentIndex())
        self.Location_1.setCurrentIndex(self.Location_1.findText(self.CopyLaser.currentText()))
        if self.MainWindow.Opto_dialog.__getattribute__("Protocol_" + condition).currentText() == 'Pulse':
            ind = self.Protocol_1.findText('Constant')
        else:
            ind = self.MainWindow.Opto_dialog.__getattribute__("Protocol_" + condition).currentIndex()
        self.Protocol_1.setCurrentIndex(ind)
        self.voltage.setText(str(
            eval(self.MainWindow.Opto_dialog.__getattribute__(f"Laser{copylaser}_power_{condition}").currentText())[0]))

    def _Capture(self):
        '''Save the measured laser power'''
        self.Capture.setStyleSheet("background-color : green;")
        QApplication.processEvents()
        self._GetTrainingParameters(self.MainWindow)
        self.Warning.setText('')
        if self.Location_1.currentText() == 'Both':
            self.Warning.setText('Data not captured! Please choose left or right, not both!')
            self.Warning.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')
            self.Warning.setAlignment(Qt.AlignCenter)
            return
        if self.LaserPowerMeasured.text() == '':
            self.Warning.setText('Data not captured! Please enter power measured!')
            self.Warning.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')
            self.Warning.setAlignment(Qt.AlignCenter)
            return
        for attr_name in dir(self):
            if attr_name.startswith('LC_'):
                if hasattr(self, 'LCM_' + attr_name[3:]):  # LCM means measured laser power from calibration
                    self.__getattribute__('LCM_' + attr_name[3:]).append(getattr(self, attr_name))
                else:
                    setattr(self, 'LCM_' + attr_name[3:], [getattr(self, attr_name)])
        # save the measure time
        if hasattr(self, 'LCM_MeasureTime'):
            current_time = datetime.now()
            date_str = current_time.strftime("%Y-%m-%d")
            time_str = current_time.strftime("%H:%M:%S")
            self.LCM_MeasureTime.append(date_str + ' ' + time_str)
        else:
            current_time = datetime.now()
            date_str = current_time.strftime("%Y-%m-%d")
            time_str = current_time.strftime("%H:%M:%S")
            self.LCM_MeasureTime = [date_str + ' ' + time_str]
        time.sleep(0.01)
        self.Capture.setStyleSheet("background-color : none")
        self.Capture.setChecked(False)

    def _Save(self):
        '''Save captured laser calibration results to json file and update the GUI'''
        self.Save.setStyleSheet("background-color : green;")
        QApplication.processEvents()
        if not hasattr(self.MainWindow, 'LaserCalibrationResults'):
            self.MainWindow.LaserCalibrationResults = {}
            LaserCalibrationResults = {}
        else:
            LaserCalibrationResults = self.MainWindow.LaserCalibrationResults
        try:
            self.LCM_MeasureTime.copy()
        except Exception as e:
            logging.error(str(e))
            self.Warning.setText('Data not saved! Please Capture the power first!')
            self.Warning.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')
            self.Warning.setAlignment(Qt.AlignCenter)
            return
        # delete invalid indices
        empty_indices = [index for index, value in enumerate(self.LCM_LaserPowerMeasured) if value == '']
        both_indices = [index for index, value in enumerate(self.LCM_Location_1) if value == 'Both']
        delete_indices = both_indices + empty_indices
        delete_indices = list(set(delete_indices))
        delete_indices.sort(reverse=True)
        for index in delete_indices:
            del self.LCM_MeasureTime[index]
            del self.LCM_LaserColor_1[index]
            del self.LCM_Protocol_1[index]
            del self.LCM_Frequency_1[index]
            del self.LCM_LaserPowerMeasured[index]
            del self.LCM_Location_1[index]
            del self.LCM_voltage[index]
        LCM_MeasureTime_date = []
        for i in range(len(self.LCM_MeasureTime)):
            LCM_MeasureTime_date.append(self.LCM_MeasureTime[i].split()[0])
        date_unique = list(set(LCM_MeasureTime_date))
        for i in range(len(date_unique)):
            current_date = date_unique[i]
            current_date_name = current_date
            '''
            #give different names to calibrations in the same day
            while 1:
                if len(current_date_name.split('_'))==1:
                    current_date_name=current_date_name+'_1'
                else:
                    current_date_name=current_date_name.split('_')[0]+'_'+str(int(current_date_name.split('_')[1])+1)
                if not current_date_name in LaserCalibrationResults.keys():
                    break
            '''
            current_date_ind = [index for index, value in enumerate(LCM_MeasureTime_date) if value == current_date]
            laser_colors = self._extract_elements(self.LCM_LaserColor_1, current_date_ind)
            laser_colors_unique = list(set(laser_colors))
            for j in range(len(laser_colors_unique)):
                current_color = laser_colors_unique[j]
                current_color_ind = [index for index, value in enumerate(self.LCM_LaserColor_1) if
                                     value == current_color]
                current_color_ind = list(set(current_color_ind) & set(current_date_ind))
                Protocols = self._extract_elements(self.LCM_Protocol_1, current_color_ind)
                Protocols_unique = list(set(Protocols))
                for k in range(len(Protocols_unique)):
                    current_protocol = Protocols_unique[k]
                    current_protocol_ind = [index for index, value in enumerate(self.LCM_Protocol_1) if
                                            value == current_protocol]
                    current_protocol_ind = list(set(current_protocol_ind) & set(current_color_ind))
                    if current_protocol == 'Sine':
                        Frequency = self._extract_elements(self.LCM_Frequency_1, current_protocol_ind)
                        Frequency_unique = list(set(Frequency))
                        for m in range(len(Frequency_unique)):
                            current_frequency = Frequency_unique[m]
                            current_frequency_ind = [index for index, value in enumerate(self.LCM_Frequency_1) if
                                                     value == current_frequency]
                            current_frequency_ind = list(set(current_frequency_ind) & set(current_protocol_ind))
                            for laser_tag in self.laser_tags:
                                ItemsLaserPower = self._get_laser_power_list(current_frequency_ind, laser_tag)
                                LaserCalibrationResults = initialize_dic(LaserCalibrationResults,
                                                                         key_list=[current_date_name, current_color,
                                                                                   current_protocol, current_frequency,
                                                                                   f"Laser_{laser_tag}"])
                                if 'LaserPowerVoltage' not in \
                                        LaserCalibrationResults[current_date_name][current_color][current_protocol][
                                            current_frequency][f"Laser_{laser_tag}"]:
                                    LaserCalibrationResults[current_date_name][current_color][current_protocol][
                                        current_frequency][f"Laser_{laser_tag}"]['LaserPowerVoltage'] = ItemsLaserPower
                                else:
                                    LaserCalibrationResults[current_date_name][current_color][current_protocol][
                                        current_frequency][f"Laser_{laser_tag}"]['LaserPowerVoltage'] = self._unique(
                                        LaserCalibrationResults[current_date_name][current_color][current_protocol][
                                            current_frequency][f"Laser_{laser_tag}"][
                                            'LaserPowerVoltage'] + ItemsLaserPower)
                    elif current_protocol == 'Constant' or current_protocol == 'Pulse':
                        for laser_tag in self.laser_tags:
                            ItemsLaserPower = self._get_laser_power_list(current_protocol_ind, laser_tag)
                            # Check and assign items to the nested dictionary
                            LaserCalibrationResults = initialize_dic(LaserCalibrationResults,
                                                                     key_list=[current_date_name, current_color,
                                                                               current_protocol, f"Laser_{laser_tag}"])
                            if 'LaserPowerVoltage' not in \
                                    LaserCalibrationResults[current_date_name][current_color][current_protocol][
                                        f"Laser_{laser_tag}"]:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol][
                                    f"Laser_{laser_tag}"]['LaserPowerVoltage'] = ItemsLaserPower
                            else:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol][
                                    f"Laser_{laser_tag}"]['LaserPowerVoltage'] = self._unique(
                                    LaserCalibrationResults[current_date_name][current_color][current_protocol][
                                        f"Laser_{laser_tag}"]['LaserPowerVoltage'] + ItemsLaserPower)
                            if current_protocol == 'Constant':  # copy results of constant to pulse
                                LaserCalibrationResults = initialize_dic(LaserCalibrationResults,
                                                                         key_list=[current_date_name, current_color,
                                                                                   'Pulse', f"Laser_{laser_tag}"])
                                if 'LaserPowerVoltage' not in \
                                        LaserCalibrationResults[current_date_name][current_color]['Pulse'][
                                            f"Laser_{laser_tag}"]:
                                    LaserCalibrationResults[current_date_name][current_color]['Pulse'][
                                        f"Laser_{laser_tag}"]['LaserPowerVoltage'] = ItemsLaserPower
                                else:
                                    LaserCalibrationResults[current_date_name][current_color]['Pulse'][
                                        f"Laser_{laser_tag}"]['LaserPowerVoltage'] = self._unique(
                                        LaserCalibrationResults[current_date_name][current_color]['Pulse'][
                                            f"Laser_{laser_tag}"]['LaserPowerVoltage'] + ItemsLaserPower)
        # save to json file
        if not os.path.exists(os.path.dirname(self.MainWindow.LaserCalibrationFiles)):
            os.makedirs(os.path.dirname(self.MainWindow.LaserCalibrationFiles))
        with open(self.MainWindow.LaserCalibrationFiles, "w") as file:
            json.dump(LaserCalibrationResults, file, indent=4)
        self.Warning.setText('')
        if LaserCalibrationResults == {}:
            self.Warning.setText('Data not saved! Please enter power measured!')
            self.Warning.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')
            self.Warning.setAlignment(Qt.AlignCenter)
            return
        self.MainWindow.LaserCalibrationResults = LaserCalibrationResults
        self.MainWindow._GetLaserCalibration()
        for i in self.condition_idx:
            getattr(self.MainWindow.Opto_dialog, f'_LaserColor')(i)
        time.sleep(0.01)
        self.Save.setStyleSheet("background-color : none")
        self.Save.setChecked(False)
        # Clear captured data
        self.LCM_MeasureTime = []
        self.LCM_LaserColor_1 = []
        self.LCM_Protocol_1 = []
        self.LCM_Frequency_1 = []
        self.LCM_LaserPowerMeasured = []
        self.LCM_Location_1 = []
        self.LCM_voltage = []

    def _get_laser_power_list(self, ind, laser_tag):
        '''module to get the laser power list'''
        ItemsLaserPower = []
        current_laser_tag_ind = [index for index, value in enumerate(self.LCM_Location_1) if
                                 value == f"Laser_{laser_tag}"]
        ind = list(set(ind) & set(current_laser_tag_ind))
        input_voltages = self._extract_elements(self.LCM_voltage, ind)
        laser_power_measured = self._extract_elements(self.LCM_LaserPowerMeasured, ind)
        input_voltages_unique = list(set(input_voltages))
        for n in range(len(input_voltages_unique)):
            current_voltage = input_voltages_unique[n]
            laser_ind = [k for k in range(len(input_voltages)) if input_voltages[k] == current_voltage]
            measured_power = self._extract_elements(laser_power_measured, laser_ind)
            measured_power_mean = self._getmean(measured_power)
            ItemsLaserPower.append([float(current_voltage), measured_power_mean])
        return ItemsLaserPower

    def _unique(self, input):
        '''average the laser power with the same input voltage'''
        if input == []:
            return []
        items = []
        input_array = np.array(input)
        voltage_unique = list(set(input_array[:, 0]))
        for current_votage in voltage_unique:
            laser_power = input_array[np.logical_and(input_array[:, 0] == current_votage, input_array[:, 1] != 'NA')][:,
                          1]
            mean_laser_power = self._getmean(list(laser_power))
            items.append([float(current_votage), mean_laser_power])
        return items

    def _extract_elements(self, my_list, indices):
        extracted_elements = [my_list[index] for index in indices]
        return extracted_elements

    def _getmean(self, List):
        if List == []:
            return 'NA'
        Sum = 0
        N = 0
        for i in range(len(List)):
            try:
                Sum = Sum + float(List[i])
                N = N + 1
            except Exception as e:
                logging.error(str(e))

        Sum = Sum / N
        return Sum

    def _Sleep(self, SleepTime):
        time.sleep(SleepTime)

    def _thread_complete(self):
        self.SleepComplete = 1

    def _thread_complete2(self):
        self.SleepComplete2 = 1

    def _Open(self):
        '''Open the laser only once'''
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully == 0:
            return
        if self.Open.isChecked():
            self.SleepComplete2 = 0
            # change button color and disable the open button
            self.Open.setEnabled(False)
            self.Open.setStyleSheet("background-color : green;")
            self._GetTrainingParameters(self.MainWindow)
            self._GetLaserWaveForm()
            self.worker2 = Worker(self._Sleep, float(self.LC_Duration_1) + 1)
            self.worker2.signals.finished.connect(self._thread_complete2)
            self._InitiateATrial()
            self.SleepStart = 1
            while 1:
                QApplication.processEvents()
                if self.SleepStart == 1:  # only run once
                    self.SleepStart = 0
                    self.threadpool2.start(self.worker2)
                if self.Open.isChecked() == False or self.SleepComplete2 == 1:
                    break
            self.Open.setStyleSheet("background-color : none")
            self.Open.setChecked(False)
            self.Open.setEnabled(True)
        else:
            # change button color
            self.Open.setStyleSheet("background-color : none")
            self.Open.setChecked(False)
            self.Open.setEnabled(True)

    def _KeepOpen(self):
        '''Keep the laser open'''
        if self.KeepOpen.isChecked():
            # change button color
            self.KeepOpen.setStyleSheet("background-color : green;")
            self._GetTrainingParameters(self.MainWindow)
            self.LC_RD_1 = 0  # set RM to zero
            self._GetLaserWaveForm()
            if self.Initialize1 == 0:
                self.worker1 = Worker(self._Sleep, float(self.LC_Duration_1))
                self.worker1.signals.finished.connect(self._thread_complete)
                self.Initialize1 = 1
            time.sleep(1)
            while 1:
                QApplication.processEvents()
                if self.SleepComplete == 1:
                    self.SleepComplete = 0
                    self._InitiateATrial()
                    self.threadpool1.start(self.worker1)
                if self.KeepOpen.isChecked() == False:
                    break
            self.KeepOpen.setStyleSheet("background-color : none")
            self.KeepOpen.setChecked(False)
        else:
            # change button color
            self.KeepOpen.setStyleSheet("background-color : none")
            self.KeepOpen.setChecked(False)


def initialize_dic(dic_name, key_list=[]):
    '''initialize the parameters'''
    if key_list == []:
        return dic_name
    key = key_list[0]
    key_list_new = key_list[1:]
    if key not in dic_name:
        dic_name[key] = {}
    initialize_dic(dic_name[key], key_list=key_list_new)
    return dic_name


class MetadataDialog(QDialog):
    '''For adding metadata to the session'''

    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        uic.loadUi('MetaData.ui', self)
        self.MainWindow = MainWindow
        self._connectSignalsSlots()
        self.meta_data = {}
        self.meta_data['rig_metadata'] = {}
        self.meta_data['session_metadata'] = {}
        self.meta_data['rig_metadata_file'] = ''
        self.LickSpoutDistance.setText(str(self.MainWindow.Other_lick_spout_distance))
        self._get_basics()
        self._show_project_names()

        # create reference position boxes based on stage coordinate keys
        positions = self.MainWindow._GetPositions() if self.MainWindow._GetPositions() is not None else {}
        grid_layout = QGridLayout()
        # add in reference area widget
        grid_layout.addWidget(self.label_95, 0, 0)
        grid_layout.addWidget(self.LickSpoutReferenceArea, 0, 1)
        for i, axis in enumerate(positions.keys()):
            label = QLabel(f'{axis.upper()} (um):')
            setattr(self, f'LickSpoutReference{axis.upper()}', QLineEdit())
            grid_layout.addWidget(label, i + 1, 0)
            grid_layout.addWidget(getattr(self, f'LickSpoutReference{axis.upper()}'), i + 1, 1)
        # add in lick spout distance
        grid_layout.addWidget(self.label_96, len(positions.keys()) + 1, 0)
        grid_layout.addWidget(self.LickSpoutDistance, len(positions.keys()) + 1, 1)
        self.groupBox.setLayout(grid_layout)

    def _connectSignalsSlots(self):
        self.SelectRigMetadata.clicked.connect(lambda: self._SelectRigMetadata(rig_metadata_file=None))
        self.EphysProbes.currentIndexChanged.connect(self._show_angles)
        self.StickMicroscopes.currentIndexChanged.connect(self._show_angles)
        self.ArcAngle.textChanged.connect(self._save_configuration)
        self.ModuleAngle.textChanged.connect(self._save_configuration)
        self.ProbeTarget.textChanged.connect(self._save_configuration)
        self.RotationAngle.textChanged.connect(self._save_configuration)
        self.ManipulatorX.textChanged.connect(self._save_configuration)
        self.ManipulatorY.textChanged.connect(self._save_configuration)
        self.ManipulatorZ.textChanged.connect(self._save_configuration)
        self.SaveMeta.clicked.connect(self._save_metadata)
        self.LoadMeta.clicked.connect(self._load_metadata)
        self.ClearMetadata.clicked.connect(self._clear_metadata)
        self.Stick_ArcAngle.textChanged.connect(self._save_configuration)
        self.Stick_ModuleAngle.textChanged.connect(self._save_configuration)
        self.Stick_RotationAngle.textChanged.connect(self._save_configuration)
        self.ProjectName.currentIndexChanged.connect(self._show_project_info)
        self.LickSpoutDistance.textChanged.connect(self._save_lick_spout_distance)

    def _set_reference(self, reference: dict):
        '''
        set the reference
        :param referencee: dictionary with keys that correspond to reference QLinEdits attributes
        '''
        self.reference = reference
        for axis, pos in reference.items():
            line_edit = getattr(self, f'LickSpoutReference{axis.upper()}')
            line_edit.setText(str(pos))

    def _show_project_info(self):
        '''show the project information based on current project name'''
        current_project_index = self.ProjectName.currentIndex()
        self.current_project_name = self.ProjectName.currentText()
        self.funding_institution = self.project_info['Funding Institution'][current_project_index]
        self.grant_number = self.project_info['Grant Number'][current_project_index]
        self.investigators = self.project_info['Investigators'][current_project_index]
        self.fundee = self.project_info['Fundee'][current_project_index]
        self.FundingSource.setText(str(self.funding_institution))
        self.Investigators.setText(str(self.investigators))
        self.GrantNumber.setText(str(self.grant_number))
        self.Fundee.setText(str(self.fundee))

    def _save_lick_spout_distance(self):
        '''save the lick spout distance'''
        self.MainWindow.Other_lick_spout_distance = self.LickSpoutDistance.text()

    def _show_project_names(self):
        '''show the project names from the project spreadsheet'''
        # load the project spreadsheet
        project_info_file = self.MainWindow.project_info_file
        if not os.path.exists(project_info_file):
            return
        self.project_info = pd.read_excel(project_info_file)
        project_names = self.project_info['Project Name'].tolist()
        # show the project information
        # adding project names to the project combobox
        self._manage_signals(enable=False, keys=['ProjectName'], action=self._show_project_info)
        self.ProjectName.addItems(project_names)
        self._manage_signals(enable=True, keys=['ProjectName'], action=self._show_project_info)
        self._show_project_info()

    def _get_basics(self):
        '''get the basic information'''
        self.probe_types = ['StickMicroscopes', 'EphysProbes']
        self.metadata_keys = ['microscopes', 'probes']
        self.widgets = [self.Microscopes, self.Probes]

    def _clear_metadata(self):
        '''clear the metadata'''
        self.meta_data = {}
        self.meta_data['rig_metadata'] = {}
        self.meta_data['session_metadata'] = {}
        self.meta_data['rig_metadata_file'] = ''
        self.ExperimentDescription.clear()
        self._update_metadata()

    def _load_metadata(self):
        '''load the metadata from a json file'''
        metadata_dialog_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Metadata File",
            self.MainWindow.metadata_dialog_folder,
            "JSON Files (*.json)"
        )
        if not metadata_dialog_file:
            return
        if os.path.exists(metadata_dialog_file):
            with open(metadata_dialog_file, 'r') as file:
                self.meta_data = json.load(file)
        self.meta_data['metadata_dialog_file'] = metadata_dialog_file
        self._update_metadata(dont_clear=True)

    def _update_metadata(self, update_rig_metadata=True, update_session_metadata=True, dont_clear=False):
        '''update the metadata'''
        if (update_rig_metadata) and ('rig_metadata_file' in self.meta_data):
            if os.path.basename(self.meta_data[
                                    'rig_metadata_file']) != self.RigMetadataFile.text() and self.RigMetadataFile.text() != '':
                if dont_clear == False:
                    # clear probe angles if the rig metadata file is changed
                    self.meta_data['session_metadata']['probes'] = {}
                    self.meta_data['session_metadata']['microscopes'] = {}
            self.RigMetadataFile.setText(os.path.basename(self.meta_data['rig_metadata_file']))
        if update_session_metadata:
            widget_dict = self._get_widgets()
            self._set_widgets_value(widget_dict, self.meta_data['session_metadata'])

        self._show_ephys_probes()
        self._show_stick_microscopes()
        self._iterate_probes_microscopes()

    def _iterate_probes_microscopes(self):
        '''iterate the probes and microscopes to save the probe information'''
        keys = ['EphysProbes', 'StickMicroscopes']
        for key in keys:
            current_combo = getattr(self, key)
            current_index = current_combo.currentIndex()
            for index in range(current_combo.count()):
                current_combo.setCurrentIndex(index)
            current_combo.setCurrentIndex(current_index)

    def _set_widgets_value(self, widget_dict, metadata):
        '''set the widgets value'''
        for key, value in widget_dict.items():
            if key in metadata:
                if isinstance(value, QtWidgets.QLineEdit):
                    value.setText(metadata[key])
                elif isinstance(value, QtWidgets.QTextEdit):
                    value.setPlainText(metadata[key])
                elif isinstance(value, QtWidgets.QComboBox):
                    index = value.findText(metadata[key])
                    if index != -1:
                        value.setCurrentIndex(index)
            elif isinstance(value, QtWidgets.QComboBox):
                value.setCurrentIndex(0)
            elif isinstance(value, QtWidgets.QLineEdit):
                value.setText('')
            elif isinstance(value, QtWidgets.QTextEdit):
                value.setPlainText('')

    def _clear_angles(self, keys):
        '''Clear the angles and target area for the given widget
        Parameters
        ----------
        keys : List of str
            The key to clear

        '''
        for key in keys:
            getattr(self, key).setText('')

    def _save_metadata_dialog_parameters(self):
        '''save the metadata dialog parameters'''
        widget_dict = self._get_widgets()
        self.meta_data = self.MainWindow._Concat(widget_dict, self.meta_data, 'session_metadata')
        self.meta_data['rig_metadata_file'] = self.RigMetadataFile.text()

    def _save_metadata(self):
        '''save the metadata collected from this dialogue to an independent json file'''
        # save metadata parameters
        self._save_metadata_dialog_parameters()
        # Save self.meta_data to JSON
        metadata_dialog_folder = self.MainWindow.metadata_dialog_folder
        if not os.path.exists(metadata_dialog_folder):
            os.makedirs(metadata_dialog_folder)
        json_file = os.path.join(metadata_dialog_folder, self.MainWindow.current_box + '_' + datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S") + '_metadata_dialog.json')

        with open(json_file, 'w') as file:
            json.dump(self.meta_data, file, indent=4)

    def _get_widgets(self):
        '''get the widgets used for saving/loading metadata'''
        exclude_widgets = self._get_children_keys(self.Probes)
        exclude_widgets += self._get_children_keys(self.Microscopes)
        exclude_widgets += ['EphysProbes', 'RigMetadataFile', 'StickMicroscopes']
        widget_dict = {w.objectName(): w for w in self.findChildren(
            (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QComboBox))
                       if w.objectName() not in exclude_widgets}
        return widget_dict

    def _save_configuration(self):
        '''save the angles and target area of the selected probe type ('StickMicroscopes','EphysProbes')'''

        probe_types = self.probe_types
        metadata_keys = self.metadata_keys
        widgets = self.widgets

        for i in range(len(probe_types)):
            probe_type = probe_types[i]
            metadata_key = metadata_keys[i]
            widget = widgets[i]
            current_probe = getattr(self, probe_type).currentText()
            self.meta_data['session_metadata'] = initialize_dic(self.meta_data['session_metadata'],
                                                                key_list=[metadata_key, current_probe])
            keys = self._get_children_keys(widget)
            for key in keys:
                self.meta_data['session_metadata'][metadata_key][current_probe][key] = getattr(self, key).text()

    def _show_angles(self):
        '''
        show the angles and target area of the selected probe type ('StickMicroscopes','EphysProbes')
        '''

        probe_types = self.probe_types
        metadata_keys = self.metadata_keys
        widgets = self.widgets

        for i in range(len(probe_types)):
            probe_type = probe_types[i]
            metadata_key = metadata_keys[i]
            widget = widgets[i]
            action = self._save_configuration

            self._manage_signals(enable=False, keys=self._get_children_keys(widget), action=action)
            self._manage_signals(enable=False, keys=[probe_type], action=self._show_angles)

            current_probe = getattr(self, probe_type).currentText()
            self.meta_data['session_metadata'] = initialize_dic(self.meta_data['session_metadata'],
                                                                key_list=[metadata_key])
            if current_probe == '' or current_probe not in self.meta_data['session_metadata'][metadata_key]:
                self._clear_angles(self._get_children_keys(widget))
                self._manage_signals(enable=True, keys=[probe_type], action=self._show_angles)
                self._manage_signals(enable=True, keys=self._get_children_keys(widget), action=action)
                continue

            self.meta_data['session_metadata'] = initialize_dic(self.meta_data['session_metadata'],
                                                                key_list=[metadata_key, current_probe])
            keys = self._get_children_keys(widget)
            for key in keys:
                self.meta_data['session_metadata'][metadata_key][current_probe].setdefault(key, '')
                getattr(self, key).setText(self.meta_data['session_metadata'][metadata_key][current_probe][key])

            self._manage_signals(enable=True, keys=self._get_children_keys(widget), action=action)
            self._manage_signals(enable=True, keys=[probe_type], action=self._show_angles)

    def _get_children_keys(self, parent_widget=None):
        '''get the children QLineEidt objectName'''
        if parent_widget is None:
            parent_widget = self.Probes
        probe_keys = []
        for child_widget in parent_widget.children():
            if isinstance(child_widget, QtWidgets.QLineEdit):
                probe_keys.append(child_widget.objectName())
            if isinstance(child_widget, QtWidgets.QGroupBox):
                for child_widget2 in child_widget.children():
                    if isinstance(child_widget2, QtWidgets.QLineEdit):
                        probe_keys.append(child_widget2.objectName())
        return probe_keys

    def _show_stick_microscopes(self):
        '''setting the stick microscopes from the rig metadata'''
        if self.meta_data['rig_metadata'] == {}:
            self.StickMicroscopes.clear()
            self._show_angles()
            self.meta_data['session_metadata']['microscopes'] = {}
            return
        items = []
        if 'stick_microscopes' in self.meta_data['rig_metadata']:
            for i in range(len(self.meta_data['rig_metadata']['stick_microscopes'])):
                items.append(self.meta_data['rig_metadata']['stick_microscopes'][i]['name'])
        if items == []:
            self.StickMicroscopes.clear()
            self._show_angles()
            return

        self._manage_signals(enable=False, keys=['StickMicroscopes'], action=self._show_angles)
        self._manage_signals(enable=False, keys=self._get_children_keys(self.Microscopes),
                             action=self._save_configuration)
        self.StickMicroscopes.clear()
        self.StickMicroscopes.addItems(items)
        self._manage_signals(enable=True, keys=['StickMicroscopes'], action=self._show_angles)
        self._manage_signals(enable=True, keys=self._get_children_keys(self.Microscopes),
                             action=self._save_configuration)
        self._show_angles()

    def _show_ephys_probes(self):
        '''setting the ephys probes from the rig metadata'''
        if self.meta_data['rig_metadata'] == {}:
            self.EphysProbes.clear()
            self._show_angles()
            return
        items = []
        if 'ephys_assemblies' in self.meta_data['rig_metadata']:
            for assembly in self.meta_data['rig_metadata']['ephys_assemblies']:
                for probe in assembly['probes']:
                    items.append(probe['name'])
        if items == []:
            self.EphysProbes.clear()
            self._show_angles()
            return

        self._manage_signals(enable=False, keys=['EphysProbes'], action=self._show_angles)
        self._manage_signals(enable=False, keys=self._get_children_keys(self.Probes), action=self._save_configuration)
        self.EphysProbes.clear()
        self.EphysProbes.addItems(items)
        self._manage_signals(enable=True, keys=['EphysProbes'], action=self._show_angles)
        self._manage_signals(enable=True, keys=self._get_children_keys(self.Probes), action=self._save_configuration)
        self._show_angles()

    def _manage_signals(self, enable=True, keys='', signals='', action=''):
        '''manage signals
        Parameters
        ----------
        enable : bool
            enable (connect) or disable (disconnect) the signals
        action : function
            the function to be connected or disconnected
        keys : list
            the keys of the widgets to be connected or disconnected
        '''
        if keys == '':
            keys = self._get_children_keys(self.Probes)
        if signals == '':
            signals = []
            for attr in keys:
                if isinstance(getattr(self, attr), QtWidgets.QLineEdit):
                    signals.append(getattr(self, attr).textChanged)
                elif isinstance(getattr(self, attr), QtWidgets.QComboBox):
                    signals.append(getattr(self, attr).currentIndexChanged)
        if action == '':
            action = self._save_configuration

        for signal in signals:
            if enable:
                signal.connect(action)
            else:
                signal.disconnect(action)

    def _SelectRigMetadata(self, rig_metadata_file=None):
        '''Select the rig metadata file and load it
        Parameters
        ----------
        rig_metadata_file : str
            The rig metadata file path

        Returns
        -------
        None
        '''
        if rig_metadata_file is None:
            rig_metadata_file, _ = QFileDialog.getOpenFileName(
                self,
                "Select Rig Metadata File",
                self.MainWindow.rig_metadata_folder,
                "JSON Files (*.json)"
            )
        if not rig_metadata_file:
            return
        self.meta_data['rig_metadata_file'] = rig_metadata_file
        self.meta_data['session_metadata']['RigMetadataFile'] = rig_metadata_file
        if os.path.exists(rig_metadata_file):
            with open(rig_metadata_file, 'r') as file:
                self.meta_data['rig_metadata'] = json.load(file)

        # Update the text box
        self._update_metadata(update_session_metadata=False)

def get_curriculum_string(curriculum):
    if curriculum is None:
        return "unknown curriculum"
    else:
        return (f"{curriculum.curriculum_name} "
                f"(v{curriculum.curriculum_version}"
                f"@{curriculum.curriculum_schema_version})")


# --- Helpers ---
class PandasModel(QAbstractTableModel):
    ''' A helper class to display pandas dataframe in QTableView
    https://learndataanalysis.org/display-pandas-dataframe-with-pyqt5-qtableview-widget/
    '''

    def __init__(self, data):
        QAbstractTableModel.__init__(self)
        self._data = data.copy()

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._data.columns[col]
        return None