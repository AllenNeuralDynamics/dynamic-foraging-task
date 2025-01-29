import time
import math
import json
import os
import shutil
import subprocess
from datetime import datetime
import logging
import webbrowser
import re
import random
from typing import Literal,Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QMessageBox, QGridLayout
from PyQt5.QtWidgets import QLabel, QDialogButtonBox,QFileDialog,QInputDialog, QLineEdit
from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtCore import QThreadPool,Qt, QAbstractTableModel, QItemSelectionModel, QObject, QTimer
from PyQt5.QtSvg import QSvgWidget

from foraging_gui.MyFunctions import Worker,WorkerTagging
from foraging_gui.Visualization import PlotWaterCalibration
from aind_auto_train.curriculum_manager import CurriculumManager
from aind_auto_train.auto_train_manager import DynamicForagingAutoTrainManager
from aind_auto_train.schema.task import TrainingStage
from aind_auto_train.schema.curriculum import DynamicForagingCurriculum
from foraging_gui.GenerateMetadata import generate_metadata
codebase_curriculum_schema_version = DynamicForagingCurriculum.model_fields['curriculum_schema_version'].default

logger = logging.getLogger(__name__)

class MouseSelectorDialog(QDialog):
    
    def __init__(self, MainWindow, mice, parent=None):
        super().__init__(parent)
        self.mice = ['']+mice
        self.MainWindow = MainWindow
        self.setWindowTitle('Box {}, Load Mouse'.format(self.MainWindow.box_letter))
        self.setFixedSize(250,125)
        
        QBtns = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtns)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        combo = QtWidgets.QComboBox()
        combo.addItems(self.mice)
        combo.setEditable(True)
        combo.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        combo.completer().setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        font = combo.font()
        font.setPointSize(15)
        combo.setFont(font)
        self.combo = combo
        
        msg = QLabel('Enter the Mouse ID: \nuse 0-9, single digit as test ID')
        font = msg.font()
        font.setPointSize(12)
        msg.setFont(font)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(msg)
        self.layout.addWidget(self.combo)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

class LickStaDialog(QDialog):
    '''Lick statistics dialog'''
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        uic.loadUi('LicksDistribution.ui', self)
        
        self.MainWindow=MainWindow

class TimeDistributionDialog(QDialog):
    '''Simulated distribution of ITI/Delay/Block length'''
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        uic.loadUi('TimeDistribution.ui', self)
        
        self.MainWindow=MainWindow

class OptogeneticsDialog(QDialog):
    '''Optogenetics dialog'''
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        uic.loadUi('Optogenetics.ui', self)
        self.condition_idx = [1, 2, 3, 4, 5, 6] # corresponding to optogenetics condition 1, 2, 3, 4, 5, 6
        self.laser_tags=[1,2] # corresponding to Laser_1 and Laser_2
        self._connectSignalsSlots()
        self.MainWindow=MainWindow
        for i in self.condition_idx:
            getattr(self, f'_LaserColor')(i)
        self._Laser_calibration()
        self._SessionWideControl()
    def _connectSignalsSlots(self):
        for i in self.condition_idx:
            # Connect LaserColor signals
            self._connectSignalSlot(f'LaserColor_{i}', self._LaserColor, i)

            # Connect Protocol signals
            self._connectSignalSlot(f'Protocol_{i}', self._activated, i)
            self._connectSignalSlot(f'Protocol_{i}', self._LaserColor, i)

            # Connect Frequency signals
            self._connectSignalSlot(f'Frequency_{i}', self._Frequency, i)

            # Connect LaserStart and LaserEnd signals
            self._connectSignalSlot(f'LaserStart_{i}', self._activated, i)
            self._connectSignalSlot(f'LaserEnd_{i}', self._activated, i)

        self.Laser_calibration.currentIndexChanged.connect(self._Laser_calibration)
        self.Laser_calibration.activated.connect(self._Laser_calibration)
        self.SessionWideControl.currentIndexChanged.connect(self._SessionWideControl)

    def _connectSignalSlot(self, signal_name, slot_method, index):
        signal = getattr(self, signal_name)
        signal.currentIndexChanged.connect(lambda: slot_method(index))
        signal.activated.connect(lambda: slot_method(index))

    def _SessionWideControl(self):
        '''enable/disable items based on session wide control'''
        if self.SessionWideControl.currentText()=='on':
            enable=True
        else:
            enable=False
        self.label3_18.setEnabled(enable)
        self.label3_21.setEnabled(enable)
        self.FractionOfSession.setEnabled(enable)
        self.label3_19.setEnabled(enable)
        self.SessionStartWith.setEnabled(enable)
        self.label3_17.setEnabled(enable)
        self.SessionAlternating.setEnabled(enable)
    def _Laser_calibration(self):
        ''''change the laser calibration date'''
        # find the latest calibration date for the selected laser
        Laser=self.Laser_calibration.currentText()
        latest_calibration_date=self._FindLatestCalibrationDate(Laser)
        # set the latest calibration date
        self.LatestCalibrationDate.setText(latest_calibration_date)

    def _FindLatestCalibrationDate(self,Laser):
        '''find the latest calibration date for the selected laser'''
        if not hasattr(self.MainWindow,'LaserCalibrationResults'):
            return 'NA'
        Dates=[]
        for Date in self.MainWindow.LaserCalibrationResults:
            if Laser in self.MainWindow.LaserCalibrationResults[Date].keys():
                Dates.append(Date)
        sorted_dates = sorted(Dates)
        if sorted_dates==[]:
            return 'NA'
        else:
            return sorted_dates[-1]

    def _Frequency(self,Numb):
        try:
            Color = getattr(self, f"LaserColor_{str(Numb)}").currentText()
            Protocol = getattr(self, f"Protocol_{str(Numb)}").currentText()
            CurrentFrequency = getattr(self, f"Frequency_{str(Numb)}").currentText()
            latest_calibration_date=self._FindLatestCalibrationDate(Color)
            if latest_calibration_date=='NA':
                RecentLaserCalibration={}
            else:
                RecentLaserCalibration=self.MainWindow.LaserCalibrationResults[latest_calibration_date]
            for laser_tag in self.laser_tags:
                ItemsLaserPower=[]
                CurrentlaserPowerLaser = getattr(self, f"Laser{str(laser_tag)}_power_{str(Numb)}").currentText()
                if Protocol in ['Sine']:
                    for i in range(len(RecentLaserCalibration[Color][Protocol][CurrentFrequency][f"Laser_{str(laser_tag)}"]['LaserPowerVoltage'])):
                        ItemsLaserPower.append(str(RecentLaserCalibration[Color][Protocol][CurrentFrequency][f"Laser_{str(laser_tag)}"]['LaserPowerVoltage'][i]))
                if Protocol in ['Constant','Pulse']:
                    for i in range(len(RecentLaserCalibration[Color][Protocol][f"Laser_{str(laser_tag)}"]['LaserPowerVoltage'])):
                        ItemsLaserPower.append(str(RecentLaserCalibration[Color][Protocol][f"Laser_{str(laser_tag)}"]['LaserPowerVoltage'][i]))
                ItemsLaserPower=sorted(ItemsLaserPower)
                getattr(self, f"Laser{str(laser_tag)}_power_{str(Numb)}").clear()
                getattr(self, f"Laser{str(laser_tag)}_power_{str(Numb)}").addItems(ItemsLaserPower)
                index = getattr(self, f"Laser{str(laser_tag)}_power_{str(Numb)}").findText(CurrentlaserPowerLaser)
                if index != -1:
                    getattr(self, f"Laser{str(laser_tag)}_power_{str(Numb)}").setCurrentIndex(index)

        except Exception as e:
            logging.error(str(e))

    def _activated(self,Numb):
        '''enable/disable items based on protocols and laser start/end'''
        Inactlabel1=15 # pulse duration
        Inactlabel2=13 # frequency
        Inactlabel3=14 # Ramping down
        if getattr(self, f'Protocol_{Numb}').currentText() == 'Sine':
            getattr(self, f'label{Numb}_{Inactlabel1}').setEnabled(False)
            getattr(self, f'PulseDur_{Numb}').setEnabled(False)
            getattr(self, f'label{Numb}_{Inactlabel2}').setEnabled(True)
            getattr(self, f'Frequency_{Numb}').setEnabled(True)
            getattr(self, f'label{Numb}_{Inactlabel3}').setEnabled(True)
            getattr(self, f'RD_{Numb}').setEnabled(True)
            getattr(self, f'Frequency_{Numb}').setEditable(False)
        if getattr(self, f'Protocol_{Numb}').currentText() == 'Pulse':
            getattr(self, f'label{Numb}_{Inactlabel1}').setEnabled(True)
            getattr(self, f'PulseDur_{Numb}').setEnabled(True)
            getattr(self, f'label{Numb}_{Inactlabel2}').setEnabled(True)
            getattr(self, f'Frequency_{Numb}').setEnabled(True)
            getattr(self, f'label{Numb}_{Inactlabel3}').setEnabled(False)
            getattr(self, f'RD_{Numb}').setEnabled(False)
            getattr(self, f'Frequency_{Numb}').setEditable(True)
        if getattr(self, f'Protocol_{Numb}').currentText() == 'Constant':
            getattr(self, f'label{Numb}_{Inactlabel1}').setEnabled(False)
            getattr(self, f'PulseDur_{Numb}').setEnabled(False)
            getattr(self, f'label{Numb}_{Inactlabel2}').setEnabled(False)
            getattr(self, f'Frequency_{Numb}').setEnabled(False)
            getattr(self, f'label{Numb}_{Inactlabel3}').setEnabled(True)
            getattr(self, f'RD_{Numb}').setEnabled(True)
            getattr(self, f'Frequency_{Numb}').clear()
            getattr(self, f'Frequency_{Numb}').setEditable(False)
        if getattr(self, f'LaserStart_{Numb}').currentText() == 'NA':
            getattr(self, f'label{Numb}_9').setEnabled(False)
            getattr(self, f'OffsetStart_{Numb}').setEnabled(False)
        else:
            getattr(self, f'label{Numb}_9').setEnabled(True)
            getattr(self, f'OffsetStart_{Numb}').setEnabled(True)
        if getattr(self, f'LaserEnd_{Numb}').currentText() == 'NA':
            getattr(self, f'label{Numb}_11').setEnabled(False)
            getattr(self, f'OffsetEnd_{Numb}').setEnabled(False)
        else:
            getattr(self, f'label{Numb}_11').setEnabled(True)
            getattr(self, f'OffsetEnd_{Numb}').setEnabled(True)
    def _LaserColor(self,Numb):
        ''' enable/disable items based on laser (blue/green/orange/red/NA)'''
        Inactlabel=range(2,17)
        if getattr(self, 'LaserColor_' + str(Numb)).currentText() == 'NA':
            Label=False
        else:
            Label=True
            Color = getattr(self, 'LaserColor_' + str(Numb)).currentText()
            Protocol = getattr(self, 'Protocol_' + str(Numb)).currentText()
            CurrentFrequency = getattr(self, 'Frequency_' + str(Numb)).currentText()
            latest_calibration_date=self._FindLatestCalibrationDate(Color)
            if latest_calibration_date=='NA':
                RecentLaserCalibration={}
            else:
                RecentLaserCalibration=self.MainWindow.LaserCalibrationResults[latest_calibration_date]
            no_calibration=False
            if not RecentLaserCalibration=={}:
                if Color in RecentLaserCalibration.keys():
                    if Protocol in RecentLaserCalibration[Color].keys():
                        if Protocol=='Sine': 
                            Frequency=RecentLaserCalibration[Color][Protocol].keys()
                            ItemsFrequency=[]
                            for Fre in Frequency:
                                ItemsFrequency.append(Fre)
                            ItemsFrequency=sorted(ItemsFrequency)
                            getattr(self, f'Frequency_{Numb}').clear()
                            getattr(self, f'Frequency_{Numb}').addItems(ItemsFrequency)
                            if not CurrentFrequency in Frequency:
                                CurrentFrequency = getattr(self, 'Frequency_' + str(Numb)).currentText()
                            for laser_tag in self.laser_tags:
                                ItemsLaserPower=[]
                                for i in range(len(RecentLaserCalibration[Color][Protocol][CurrentFrequency][f"Laser_{laser_tag}"]['LaserPowerVoltage'])):
                                    ItemsLaserPower.append(str(RecentLaserCalibration[Color][Protocol][CurrentFrequency][f"Laser_{laser_tag}"]['LaserPowerVoltage'][i]))
                                ItemsLaserPower=sorted(ItemsLaserPower)
                                getattr(self, f"Laser{laser_tag}_power_{str(Numb)}").clear()
                                getattr(self, f"Laser{laser_tag}_power_{str(Numb)}").addItems(ItemsLaserPower)
                        elif Protocol=='Constant' or Protocol=='Pulse':
                            for laser_tag in self.laser_tags:
                                ItemsLaserPower=[]
                                for i in range(len(RecentLaserCalibration[Color][Protocol][f"Laser_{laser_tag}"]['LaserPowerVoltage'])):
                                    ItemsLaserPower.append(str(RecentLaserCalibration[Color][Protocol][f"Laser_{laser_tag}"]['LaserPowerVoltage'][i]))
                                ItemsLaserPower=sorted(ItemsLaserPower)
                                getattr(self, f"Laser{laser_tag}_power_{str(Numb)}").clear()
                                getattr(self, f"Laser{laser_tag}_power_{str(Numb)}").addItems(ItemsLaserPower)
                    else:
                        no_calibration=True
                else:
                    no_calibration=True
            else:
                no_calibration=True

            if no_calibration:
                for laser_tag in self.laser_tags:
                    getattr(self, f"Laser{laser_tag}_power_{str(Numb)}").clear()
                    logging.warning('No calibration for this protocol identified!',
                                    extra={'tags': [self.MainWindow.warning_log_tag]})

        getattr(self, 'Location_' + str(Numb)).setEnabled(Label)
        getattr(self, 'Laser1_power_' + str(Numb)).setEnabled(Label)
        getattr(self, 'Laser2_power_' + str(Numb)).setEnabled(Label)
        getattr(self, 'Probability_' + str(Numb)).setEnabled(Label)
        getattr(self, 'Duration_' + str(Numb)).setEnabled(Label)
        getattr(self, 'Condition_' + str(Numb)).setEnabled(Label)
        getattr(self, 'ConditionP_' + str(Numb)).setEnabled(Label)
        getattr(self, 'LaserStart_' + str(Numb)).setEnabled(Label)
        getattr(self, 'OffsetStart_' + str(Numb)).setEnabled(Label)
        getattr(self, 'LaserEnd_' + str(Numb)).setEnabled(Label)
        getattr(self, 'OffsetEnd_' + str(Numb)).setEnabled(Label)
        getattr(self, 'Protocol_' + str(Numb)).setEnabled(Label)
        getattr(self, 'Frequency_' + str(Numb)).setEnabled(Label)
        getattr(self, 'RD_' + str(Numb)).setEnabled(Label)
        getattr(self, 'PulseDur_' + str(Numb)).setEnabled(Label)

        for i in Inactlabel:
            getattr(self, 'label' + str(Numb) + '_' + str(i)).setEnabled(Label)
        if getattr(self, 'LaserColor_' + str(Numb)).currentText() != 'NA':
            getattr(self, '_activated')(Numb)


class WaterCalibrationDialog(QDialog):
    '''Water valve calibration'''
    def __init__(self, MainWindow,parent=None):
        super().__init__(parent)
        uic.loadUi('Calibration.ui', self)
        
        self.MainWindow=MainWindow
        self.calibrating_left = False
        self.calibrating_right= False
        self._LoadCalibrationParameters()
        if not hasattr(self.MainWindow,'WaterCalibrationResults'):
            self.MainWindow.WaterCalibrationResults={}
            self.WaterCalibrationResults={}
        else:
            self.WaterCalibrationResults=self.MainWindow.WaterCalibrationResults
        self._connectSignalsSlots()
        self.ToInitializeVisual=1
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
        self.left_close_timer = QTimer(timeout=lambda:  self.OpenLeft5ml.setChecked(False))  # trigger _ToggleValve call
        self.right_close_timer = QTimer(timeout=lambda: self.OpenRight5ml.setChecked(False))

        # setup Qtimers for updating text countdown
        self.left_text_timer = QTimer(timeout=lambda:
                      self.OpenLeft5ml.setText(f'Open left 5ml: {round(self.left_close_timer.remainingTime()/1000)}s'),
                      interval=1000)
        self.right_text_timer = QTimer(timeout=lambda:
                     self.OpenRight5ml.setText(f'Open right 5ml: {round(self.right_close_timer.remainingTime()/1000)}s'),
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
        self.calibrating_right= False
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
            valve= f'Spot{valve}',
            valve_open_time=str(valve_open_time),
            valve_open_interval=str(self.SpotInterval),
            cycle=str(self.SpotCycle),
            total_water=float(water_txt),
            tube_weight=float(before_txt),
            append=True)
        save.setStyleSheet("background-color : none")
        save.setChecked(False)

    def _LoadCalibrationParameters(self):
        self.WaterCalibrationPar={}
        if os.path.exists(self.MainWindow.WaterCalibrationParFiles):
            with open(self.MainWindow.WaterCalibrationParFiles, 'r') as f:
                self.WaterCalibrationPar = json.load(f)
            logging.info('loaded water calibration parameters')
        else:
            logging.warning('could not find water calibration parameters: {}'.format(self.MainWindow.WaterCalibrationParFiles))
            self.WaterCalibrationPar = {}

        # if no parameters are stored, store default parameters
        if 'Full' not in self.WaterCalibrationPar:
            self.WaterCalibrationPar['Full'] = {}
            self.WaterCalibrationPar['Full']['TimeMin'] = 0.02
            self.WaterCalibrationPar['Full']['TimeMax'] = 0.03
            self.WaterCalibrationPar['Full']['Stride']  = 0.01
            self.WaterCalibrationPar['Full']['Interval']= 0.1
            self.WaterCalibrationPar['Full']['Cycle']   = 1000

        if 'Spot' not in self.WaterCalibrationPar:
            self.WaterCalibrationPar['Spot'] = {}
            self.WaterCalibrationPar['Spot']['Interval']= 0.1
            self.WaterCalibrationPar['Spot']['Cycle']   = 200           
       
        self.SpotCycle = float(self.WaterCalibrationPar['Spot']['Cycle'])
        self.SpotInterval = float(self.WaterCalibrationPar['Spot']['Interval'])

        # Add other calibration types to drop down list, but only if they have all parameters
        other_types = set(self.WaterCalibrationPar.keys()) - set(['Full','Spot'])
        required = set(['TimeMin','TimeMax','Stride','Interval','Cycle'])
        if len(other_types) > 0:
            for t in other_types:
                if required.issubset(set(self.WaterCalibrationPar[t].keys())):
                    self.CalibrationType.addItem(t)
                else:
                    logging.info('Calibration Type "{}" missing required fields'.format(t))
    
    def _StartCalibratingLeft(self):
        '''start the calibration loop of left valve'''

        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
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
            float(self.params['TimeMax'])+0.0001,
            float(self.params['Stride'])
            )
        self.left_opentimes = [np.round(x,3) for x in self.left_opentimes]
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

    def _CalibrateLeftOne(self,repeat=False):
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

        #Prompt for before weight, using field value as default
        if self.WeightBeforeLeft.text() != '':
             before_weight = float(self.WeightBeforeLeft.text()) 
        else:
             before_weight = 0.0 
        before_weight, ok = QInputDialog().getDouble(
             self,
             'Box {}, Left'.format(self.MainWindow.box_letter),
              "Before weight (g): ", 
              before_weight,
              0,1000,4)
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
                    i,self.params['Cycle'], float(self.params['Interval'])
                    )

                # set the valve open time
                self.MainWindow.Channel.LeftValue(float(current_valve_opentime)*1000) 
                # open the valve
                self.MainWindow.Channel3.ManualWater_Left(int(1))
                # delay
                time.sleep(current_valve_opentime+float(self.params['Interval']))
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
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
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
            float(self.params['TimeMax'])+0.0001,
            float(self.params['Stride'])
            )
        self.right_opentimes = [np.round(x,3) for x in self.right_opentimes]
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

    def _CalibrateRightOne(self,repeat=False):
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

        #Prompt for before weight, using field value as default
        if self.WeightBeforeRight.text() != '':
             before_weight = float(self.WeightBeforeRight.text()) 
        else:
             before_weight = 0.0 
        before_weight, ok = QInputDialog().getDouble(
             self,
             'Box {}, Right'.format(self.MainWindow.box_letter),
              "Before weight (g): ", 
              before_weight,
              0,1000,4)
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
                    i,self.params['Cycle'], float(self.params['Interval'])
                    )

                # set the valve open time
                self.MainWindow.Channel.RightValue(float(current_valve_opentime)*1000) 
                # open the valve
                self.MainWindow.Channel3.ManualWater_Right(int(1))
                # delay
                time.sleep(current_valve_opentime+float(self.params['Interval']))
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
        
    def _CalibrationStatus(self,opentime, weight_before, i, cycle, interval):
        self.Warning.setText(
            'Measuring left valve: {}s'.format(opentime) + \
            '\nEmpty tube weight: {}g'.format(weight_before) + \
            '\nCurrent cycle: '+str(i+1)+'/{}'.format(int(cycle)) + \
            '\nTime remaining: {}'.format(self._TimeRemaining(
                i,cycle,opentime,interval))
            )
        self.Warning.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')

    def _Save(self,valve,valve_open_time,valve_open_interval,cycle,total_water,tube_weight,append=False):
        '''save the calibrated result and update the figure'''
        if total_water=='' or tube_weight=='':
            return
        # total water equals to total water minus tube weight
        total_water=(total_water-tube_weight)*1000 # The input unit is g and converted to mg.
        WaterCalibrationResults=self.WaterCalibrationResults.copy()
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
            WaterCalibrationResults[date_str][valve][valve_open_time][valve_open_interval][cycle].append(np.round(total_water,1))
        else:
            WaterCalibrationResults[date_str][valve][valve_open_time][valve_open_interval][cycle]=[np.round(total_water,1)]
        self.WaterCalibrationResults=WaterCalibrationResults.copy()

        # save to the json file
        if not os.path.exists(os.path.dirname(self.MainWindow.WaterCalibrationFiles)):
            os.makedirs(os.path.dirname(self.MainWindow.WaterCalibrationFiles))
        with open(self.MainWindow.WaterCalibrationFiles, "w") as file:
            json.dump(WaterCalibrationResults, file,indent=4)

        # update the figure
        self._UpdateFigure()

    def _UpdateFigure(self):
        '''plot the calibration result'''
        if self.ToInitializeVisual==1: # only run once
            PlotM=PlotWaterCalibration(water_win=self)
            self.PlotM=PlotM
            layout=self.VisuCalibration.layout()
            if layout is not None:
                for i in reversed(range(layout.count())):
                    layout.itemAt(i).widget().setParent(None)
                layout.invalidate()
            if layout is None:
                layout=QVBoxLayout(self.VisuCalibration)
            toolbar = NavigationToolbar(PlotM, self)
            toolbar.setMaximumHeight(20)
            toolbar.setMaximumWidth(300)
            layout.addWidget(toolbar)
            layout.addWidget(PlotM)
            self.ToInitializeVisual=0
        self.PlotM._Update()

    def _ToggleValve(self, button, valve: Literal['Left', 'Right']):
        """
        Toggle open/close state of specified valve and set up logic based on button pressed
        :param button: button that was pressed
        :param valve: which valve to open. Restricted to Right or Left
        """

        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
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

            if button.text() == f'Open {valve.lower()} 5ml':    # set up additional logic to only open for 5ml
                five_ml_time_ms = round(self._VolumeToTime(5000, valve) * 1000)  # calculate time for valve to stay open
                close_timer.setInterval(five_ml_time_ms)  # set interval of valve close time to be five_ml_time_ms
                close_timer.setSingleShot(True)  # only trigger once when 5ml has been expelled
                text_timer.start()  # start timer to update text
                close_timer.start()

            open_timer.start()

        else:   # close open valve
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
            set_valve_time(float(getattr(self.MainWindow, f'{valve}Value').text())*1000)

    def reopen_valve(self, valve: Literal['Left', 'Right']):
        """Function to reopen the right or left water line open. Valve must be open prior to calling this function.
        Calling ManualWater_ will toggle state of valve so need to call twice on already open valve.
        param valve: string specifying right or left valve"""

        # get correct function based on input valve name
        getattr(self.MainWindow.Channel3, f'ManualWater_{valve}')(int(1))  # close valve
        getattr(self.MainWindow.Channel3, f'ManualWater_{valve}')(int(1))  # open valve

    def _TimeRemaining(self,i, cycles, opentime, interval):
        total_seconds = (cycles-i)*(opentime+interval)
        minutes = int(np.floor(total_seconds/60))
        seconds = int(np.ceil(np.mod(total_seconds,60)))
        return '{}:{:02}'.format(minutes, seconds)
    
    def _VolumeToTime(self, volume, valve: Literal['Left', 'Right'] ):
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
        return (volume-b)/m

    def _TimeToVolume(self,time):
        # y= mx +b        
        if hasattr(self.MainWindow, 'latest_fitting'):
            print(self.MainWindow.latest_fitting)
        else:
            m = 1
            b = 0
        return time*m+b

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
                logging.error('Water calibration spot check exceeds tolerance: {}'.format(error))
                save.setStyleSheet("color: white;background-color : mediumorchid;")
                self.Warning.setText(
                    f'Measuring {valve.lower()} valve: {volume}uL' + \
                    '\nEmpty tube weight: {}g'.format(empty_tube_weight) + \
                    '\nFinal tube weight: {}g'.format(final_tube_weight) + \
                    '\nAvg. error from target: {}uL'.format(error)
                )
                self._SaveValve(valve)
                if self.check_spot_failures(valve) >= 2:
                    msg = 'Two or more spot checks have failed in the last 30 days. Please create a SIPE ticket to ' \
                          'check rig.'
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
                       and (today-datetime.strptime(k, "%Y-%m-%d")).days < 30}

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
        
        self.MainWindow=MainWindow
        self._connectSignalsSlots()
        self.camera_start_time=''
        self.camera_stop_time=''

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
        if hasattr(self.MainWindow,'Ot_log_folder'):
            try:
                subprocess.Popen(['explorer', os.path.join(os.path.dirname(os.path.dirname(self.MainWindow.Ot_log_folder)),'behavior-videos')])
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
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
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
        if self.AutoControl.currentText()=='Yes':
            self.StartRecording.setChecked(False)
            
    def _StartCamera(self):
        '''Start/stop the camera recording based on if the StartRecording button is toggled on/off'''

        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
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
            if self.MainWindow.logging_type!=0:
                self.MainWindow.Ot_log_folder=self.MainWindow._restartlogging()
            # set to check drop frame as true
            self.MainWindow.to_check_drop_frames=1
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
        self.MainWindow=MainWindow
        uic.loadUi('CalibrationLaser.ui', self)
        
        self._connectSignalsSlots()
        self.SleepComplete=1
        self.SleepComplete2=0
        self.Initialize1=0
        self.Initialize2=0
        self.threadpool1=QThreadPool()
        self.threadpool2=QThreadPool()
        self.laser_tags=[1,2]
        self.condition_idx=[1,2,3,4,5,6]
    def _connectSignalsSlots(self):
        self.Open.clicked.connect(self._Open)
        self.KeepOpen.clicked.connect(self._KeepOpen)
        self.CopyFromOpto.clicked.connect(self._CopyFromOpto)
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
        if self.Location_1.currentText()=='Laser_1':
            self.MainWindow.Opto_dialog.laser_1_calibration_voltage.setText(self.voltage.text())
            self.MainWindow.Opto_dialog.laser_1_calibration_power.setText(self.LaserPowerMeasured.text())
        elif self.Location_1.currentText()=='Laser_2':
            self.MainWindow.Opto_dialog.laser_2_calibration_voltage.setText(self.voltage.text())
            self.MainWindow.Opto_dialog.laser_2_calibration_power.setText(self.LaserPowerMeasured.text())
            
    def _FLush_DO0(self):
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        self.MainWindow.Channel.DO0(int(1))
        self.MainWindow.Channel.receive()
    def _FLush_DO1(self):
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        self.MainWindow.Channel.DO1(int(1))
    def _FLush_DO2(self):
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        #self.MainWindow.Channel.DO2(int(1))
        self.MainWindow.Channel.receive()
    def _FLush_DO3(self):
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        self.MainWindow.Channel.DO3(int(1))
        self.MainWindow.Channel.receive()
    def _FLush_Port2(self):
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        self.MainWindow.Channel.Port2(int(1))

    def _LaserColor_1(self):
        self._LaserColor(1)
    def _activated_1(self):
        self._activated(1)
    def _activated(self,Numb):
        '''enable/disable items based on protocols and laser start/end'''
        Inactlabel1=15 # pulse duration
        Inactlabel2=13 # frequency
        Inactlabel3=14 # Ramping down
        if getattr(self, 'Protocol_'+str(Numb)).currentText() == 'Sine':
            getattr(self, 'label'+str(Numb)+'_'+str(Inactlabel1)).setEnabled(False)
            getattr(self, 'PulseDur_'+str(Numb)).setEnabled(False)
            getattr(self, 'label'+str(Numb)+'_'+str(Inactlabel2)).setEnabled(True)
            getattr(self, 'Frequency_'+str(Numb)).setEnabled(True)
            getattr(self, 'label'+str(Numb)+'_'+str(Inactlabel3)).setEnabled(True)
            getattr(self, 'RD_'+str(Numb)).setEnabled(True)
        if getattr(self, 'Protocol_'+str(Numb)).currentText() =='Pulse':
            getattr(self, 'label'+str(Numb)+'_'+str(Inactlabel1)).setEnabled(True)
            getattr(self, 'PulseDur_'+str(Numb)).setEnabled(True)
            getattr(self, 'label'+str(Numb)+'_'+str(Inactlabel2)).setEnabled(True)
            getattr(self, 'Frequency_'+str(Numb)).setEnabled(True)
            getattr(self, 'label'+str(Numb)+'_'+str(Inactlabel3)).setEnabled(False)
            getattr(self, 'RD_'+str(Numb)).setEnabled(False)
        if getattr(self, 'Protocol_'+str(Numb)).currentText() =='Constant':
            getattr(self, 'label'+str(Numb)+'_'+str(Inactlabel1)).setEnabled(False)
            getattr(self, 'PulseDur_'+str(Numb)).setEnabled(False)
            getattr(self, 'label'+str(Numb)+'_'+str(Inactlabel2)).setEnabled(False)
            getattr(self, 'Frequency_'+str(Numb)).setEnabled(False)
            getattr(self, 'label'+str(Numb)+'_'+str(Inactlabel3)).setEnabled(True)
            getattr(self, 'RD_'+str(Numb)).setEnabled(True)
    
    def _LaserColor(self,Numb):
        ''' enable/disable items based on laser (blue/green/orange/red/NA)'''
        Inactlabel=[2,3,5,12,13,14,15]
        if getattr(self, 'LaserColor_'+str(Numb)).currentText()=='NA':
            Label=False
        else:
            Label=True
        getattr(self, 'Location_'+str(Numb)).setEnabled(Label)
        getattr(self, 'Duration_'+str(Numb)).setEnabled(Label)
        getattr(self, 'Protocol_'+str(Numb)).setEnabled(Label)
        getattr(self, 'Frequency_'+str(Numb)).setEnabled(Label)
        getattr(self, 'RD_'+str(Numb)).setEnabled(Label)
        getattr(self, 'PulseDur_'+str(Numb)).setEnabled(Label)
        for i in Inactlabel:
            getattr(self, 'label'+str(Numb)+'_'+str(i)).setEnabled(Label)
        if getattr(self, 'LaserColor_'+str(Numb)).currentText() != 'NA':
            getattr(self, '_activated_' + str(Numb))()
    
    def _GetLaserWaveForm(self):
        '''Get the waveform of the laser. It dependens on color/duration/protocol(frequency/RD/pulse duration)/locations/laser power'''
        N=str(1)
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
            setattr(self, 'WaveFormLocation_' + str(i+1), self.my_wave)
            setattr(self, f"Location{i+1}_Size", getattr(self, f"WaveFormLocation_{i+1}").size)
            #send waveform and send the waveform size
            getattr(self.MainWindow.Channel, 'Location'+str(i+1)+'_Size')(int(getattr(self, 'Location'+str(i+1)+'_Size')))
            getattr(self.MainWindow.Channel4, 'WaveForm' + str(1)+'_'+str(i+1))(str(getattr(self, 'WaveFormLocation_'+str(i+1)).tolist())[1:-1])
        FinishOfWaveForm=self.MainWindow.Channel4.receive()  
    def _ProduceWaveForm(self,Amplitude):
        '''generate the waveform based on Duration and Protocol, Laser Power, Frequency, RampingDown, PulseDur and the sample frequency'''
        if self.CLP_Protocol=='Sine':
            resolution=self.CLP_SampleFrequency*self.CLP_CurrentDuration # how many datapoints to generate
            cycles=self.CLP_CurrentDuration*self.CLP_Frequency # how many sine cycles
            length = np.pi * 2 * cycles
            self.my_wave = Amplitude*(1+np.sin(np.arange(0+1.5*math.pi, length+1.5*math.pi, length / resolution)))/2
            # add ramping down
            if self.CLP_RampingDown>0:
                if self.CLP_RampingDown>self.CLP_CurrentDuration:
                    logging.warning('Ramping down is longer than the laser duration!',
                                    extra={'tags': [self.MainWindow.warning_log_tag]})
                else:
                    Constant=np.ones(int((self.CLP_CurrentDuration-self.CLP_RampingDown)*self.CLP_SampleFrequency))
                    RD=np.arange(1,0, -1/(np.shape(self.my_wave)[0]-np.shape(Constant)[0]))
                    RampingDown = np.concatenate((Constant, RD), axis=0)
                    self.my_wave=self.my_wave*RampingDown
            self.my_wave=np.append(self.my_wave,[0,0])
        elif self.CLP_Protocol=='Pulse':
            if self.CLP_PulseDur=='NA':
                logging.warning('Pulse duration is NA!', extra={'tags': [self.MainWindow.warning_log_tag]})
            else:
                self.CLP_PulseDur=float(self.CLP_PulseDur)
                PointsEachPulse=int(self.CLP_SampleFrequency*self.CLP_PulseDur)
                PulseIntervalPoints=int(1/self.CLP_Frequency*self.CLP_SampleFrequency-PointsEachPulse)
                if PulseIntervalPoints<0:
                    logging.warning('Pulse frequency and pulse duration are not compatible!',
                                    extra={'tags': [self.MainWindow.warning_log_tag]})
                TotalPoints=int(self.CLP_SampleFrequency*self.CLP_CurrentDuration)
                PulseNumber=np.floor(self.CLP_CurrentDuration*self.CLP_Frequency) 
                EachPulse=Amplitude*np.ones(PointsEachPulse)
                PulseInterval=np.zeros(PulseIntervalPoints)
                WaveFormEachCycle=np.concatenate((EachPulse, PulseInterval), axis=0)
                self.my_wave=np.empty(0)
                # pulse number should be greater than 0
                if PulseNumber>1:
                    for i in range(int(PulseNumber-1)):
                        self.my_wave=np.concatenate((self.my_wave, WaveFormEachCycle), axis=0)
                else:
                    logging.warning('Pulse number is less than 1!', extra={'tags': [self.MainWindow.warning_log_tag]})
                    return
                self.my_wave=np.concatenate((self.my_wave, EachPulse), axis=0)
                self.my_wave=np.concatenate((self.my_wave, np.zeros(TotalPoints-np.shape(self.my_wave)[0])), axis=0)
                self.my_wave=np.append(self.my_wave,[0,0])
        elif self.CLP_Protocol=='Constant':
            resolution=self.CLP_SampleFrequency*self.CLP_CurrentDuration # how many datapoints to generate
            self.my_wave=Amplitude*np.ones(int(resolution))
            if self.CLP_RampingDown>0:
            # add ramping down
                if self.CLP_RampingDown>self.CLP_CurrentDuration:
                    logging.warning('Ramping down is longer than the laser duration!',
                                    extra={'tags': [self.MainWindow.warning_log_tag]})
                else:
                    Constant=np.ones(int((self.CLP_CurrentDuration-self.CLP_RampingDown)*self.CLP_SampleFrequency))
                    RD=np.arange(1,0, -1/(np.shape(self.my_wave)[0]-np.shape(Constant)[0]))
                    RampingDown = np.concatenate((Constant, RD), axis=0)
                    self.my_wave=self.my_wave*RampingDown
            self.my_wave=np.append(self.my_wave,[0,0])
        else:
            logging.warning('Unidentified optogenetics protocol!', extra={'tags': [self.MainWindow.warning_log_tag]})

    def _GetLaserAmplitude(self):
        '''the voltage amplitude dependens on Protocol, Laser Power, Laser color, and the stimulation locations<>'''
        if self.CLP_Location=='Laser_1':
            self.CurrentLaserAmplitude=[self.CLP_InputVoltage,0]
        elif self.CLP_Location=='Laser_2':
            self.CurrentLaserAmplitude=[0,self.CLP_InputVoltage]
        elif self.CLP_Location=='Both':
            self.CurrentLaserAmplitude=[self.CLP_InputVoltage,self.CLP_InputVoltage]
        else:
            logging.warning('No stimulation location defined!', extra={'tags': [self.MainWindow.warning_log_tag]})

    # get training parameters
    def _GetTrainingParameters(self,win):
        '''Get training parameters'''
        Prefix='LC' # laser calibration
        # Iterate over each container to find child widgets and store their values in self
        for container in [win.LaserCalibration_dialog]:
            # Iterate over each child of the container that is a QLineEdit or QDoubleSpinBox
            for child in container.findChildren((QtWidgets.QLineEdit, QtWidgets.QDoubleSpinBox)):
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store the child's text value
                setattr(self, Prefix+'_'+child.objectName(), child.text())
            # Iterate over each child of the container that is a QComboBox
            for child in container.findChildren(QtWidgets.QComboBox):
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store the child's current text value
                setattr(self, Prefix+'_'+child.objectName(), child.currentText())
            # Iterate over each child of the container that is a QPushButton
            for child in container.findChildren(QtWidgets.QPushButton):
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store whether the child is checked or not
                setattr(self, Prefix+'_'+child.objectName(), child.isChecked())
    def _InitiateATrial(self):
        '''Initiate calibration in bonsai'''
        # start generating waveform in bonsai
        self.MainWindow.Channel.OptogeneticsCalibration(int(1))
        self.MainWindow.Channel.receive()
    def _CopyFromOpto(self):
        '''Copy the optogenetics parameters'''
        condition=self.CopyCondition.currentText().split('_')[1]
        copylaser=self.CopyLaser.currentText().split('_')[1]
        if self.MainWindow.Opto_dialog.__getattribute__("LaserColor_" + condition).currentText()=="NA":
            return
        #self.Duration_1.setText(self.MainWindow.Opto_dialog.__getattribute__("Duration_" + condition).text())
        self.Frequency_1.setText(self.MainWindow.Opto_dialog.__getattribute__("Frequency_" + condition).currentText())
        self.RD_1.setText(self.MainWindow.Opto_dialog.__getattribute__("RD_" + condition).text())
        self.PulseDur_1.setText(self.MainWindow.Opto_dialog.__getattribute__("PulseDur_" + condition).text())
        self.LaserColor_1.setCurrentIndex(self.MainWindow.Opto_dialog.__getattribute__("LaserColor_" + condition).currentIndex())
        self.Location_1.setCurrentIndex(self.Location_1.findText(self.CopyLaser.currentText()))
        if self.MainWindow.Opto_dialog.__getattribute__("Protocol_" + condition).currentText()=='Pulse':
            ind=self.Protocol_1.findText('Constant')
        else:
            ind=self.MainWindow.Opto_dialog.__getattribute__("Protocol_" + condition).currentIndex()
        self.Protocol_1.setCurrentIndex(ind)
        self.voltage.setText(str(eval(self.MainWindow.Opto_dialog.__getattribute__(f"Laser{copylaser}_power_{condition}").currentText())[0]))
        

    def _Capture(self):
        '''Save the measured laser power'''
        self.Capture.setStyleSheet("background-color : green;")
        QApplication.processEvents()
        self._GetTrainingParameters(self.MainWindow)
        self.Warning.setText('')
        if self.Location_1.currentText()=='Both':
            self.Warning.setText('Data not captured! Please choose left or right, not both!')
            self.Warning.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')
            self.Warning.setAlignment(Qt.AlignCenter)
            return
        if self.LaserPowerMeasured.text()=='':
            self.Warning.setText('Data not captured! Please enter power measured!')
            self.Warning.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')
            self.Warning.setAlignment(Qt.AlignCenter)
            return
        for attr_name in dir(self):
            if attr_name.startswith('LC_'):
                if hasattr(self,'LCM_'+attr_name[3:]): # LCM means measured laser power from calibration
                    self.__getattribute__('LCM_'+attr_name[3:]).append(getattr(self,attr_name))
                else:
                    setattr(self,'LCM_'+attr_name[3:],[getattr(self,attr_name)])
        # save the measure time
        if hasattr(self,'LCM_MeasureTime'):
            current_time = datetime.now()
            date_str = current_time.strftime("%Y-%m-%d")
            time_str = current_time.strftime("%H:%M:%S")
            self.LCM_MeasureTime.append(date_str+' '+time_str)
        else:
            current_time = datetime.now()
            date_str = current_time.strftime("%Y-%m-%d")
            time_str = current_time.strftime("%H:%M:%S")
            self.LCM_MeasureTime=[date_str+' '+time_str]
        time.sleep(0.01)
        self.Capture.setStyleSheet("background-color : none")
        self.Capture.setChecked(False)
    def _Save(self):
        '''Save captured laser calibration results to json file and update the GUI'''
        self.Save.setStyleSheet("background-color : green;")
        QApplication.processEvents()
        if not hasattr(self.MainWindow,'LaserCalibrationResults'):
            self.MainWindow.LaserCalibrationResults={}
            LaserCalibrationResults={}
        else:
            LaserCalibrationResults=self.MainWindow.LaserCalibrationResults
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
        delete_indices=both_indices+empty_indices
        delete_indices=list(set(delete_indices))
        delete_indices.sort(reverse=True)
        for index in delete_indices:
            del self.LCM_MeasureTime[index]
            del self.LCM_LaserColor_1[index]
            del self.LCM_Protocol_1[index]
            del self.LCM_Frequency_1[index]
            del self.LCM_LaserPowerMeasured[index]
            del self.LCM_Location_1[index]
            del self.LCM_voltage[index]
        LCM_MeasureTime_date=[]
        for i in range(len(self.LCM_MeasureTime)):
            LCM_MeasureTime_date.append(self.LCM_MeasureTime[i].split()[0])
        date_unique = list(set(LCM_MeasureTime_date))
        for i in range(len(date_unique)):
            current_date=date_unique[i]
            current_date_name=current_date
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
            current_date_ind=[index for index, value in enumerate(LCM_MeasureTime_date) if value == current_date]
            laser_colors= self._extract_elements(self.LCM_LaserColor_1,current_date_ind) 
            laser_colors_unique= list(set(laser_colors))
            for j in range(len(laser_colors_unique)):
                current_color=laser_colors_unique[j]
                current_color_ind=[index for index, value in enumerate(self.LCM_LaserColor_1) if value == current_color]
                current_color_ind=list(set(current_color_ind) & set(current_date_ind))
                Protocols= self._extract_elements(self.LCM_Protocol_1,current_color_ind)
                Protocols_unique=list(set(Protocols))
                for k in range(len(Protocols_unique)):
                    current_protocol=Protocols_unique[k]
                    current_protocol_ind=[index for index, value in enumerate(self.LCM_Protocol_1) if value == current_protocol]
                    current_protocol_ind = list(set(current_protocol_ind) & set(current_color_ind))
                    if current_protocol=='Sine':
                        Frequency=self._extract_elements(self.LCM_Frequency_1,current_protocol_ind)
                        Frequency_unique=list(set(Frequency))
                        for m in range(len(Frequency_unique)):
                            current_frequency=Frequency_unique[m]
                            current_frequency_ind=[index for index, value in enumerate(self.LCM_Frequency_1) if value == current_frequency]
                            current_frequency_ind = list(set(current_frequency_ind) & set(current_protocol_ind))
                            for laser_tag in self.laser_tags:
                                ItemsLaserPower=self._get_laser_power_list(current_frequency_ind,laser_tag)
                                LaserCalibrationResults=initialize_dic(LaserCalibrationResults,key_list=[current_date_name,current_color,current_protocol,current_frequency,f"Laser_{laser_tag}"])
                                if 'LaserPowerVoltage' not in LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency][f"Laser_{laser_tag}"]:
                                    LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency][f"Laser_{laser_tag}"]['LaserPowerVoltage']=ItemsLaserPower
                                else:
                                    LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency][f"Laser_{laser_tag}"]['LaserPowerVoltage']=self._unique(LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency][f"Laser_{laser_tag}"]['LaserPowerVoltage']+ItemsLaserPower)
                    elif current_protocol=='Constant' or current_protocol=='Pulse':
                            for laser_tag in self.laser_tags:
                                ItemsLaserPower=self._get_laser_power_list(current_protocol_ind,laser_tag)
                                # Check and assign items to the nested dictionary
                                LaserCalibrationResults=initialize_dic(LaserCalibrationResults,key_list=[current_date_name,current_color,current_protocol,f"Laser_{laser_tag}"])
                                if 'LaserPowerVoltage' not in LaserCalibrationResults[current_date_name][current_color][current_protocol][f"Laser_{laser_tag}"]:
                                    LaserCalibrationResults[current_date_name][current_color][current_protocol][f"Laser_{laser_tag}"]['LaserPowerVoltage']=ItemsLaserPower
                                else:
                                    LaserCalibrationResults[current_date_name][current_color][current_protocol][f"Laser_{laser_tag}"]['LaserPowerVoltage']=self._unique(LaserCalibrationResults[current_date_name][current_color][current_protocol][f"Laser_{laser_tag}"]['LaserPowerVoltage']+ItemsLaserPower)
                                if current_protocol=='Constant':# copy results of constant to pulse 
                                    LaserCalibrationResults=initialize_dic(LaserCalibrationResults,key_list=[current_date_name,current_color,'Pulse',f"Laser_{laser_tag}"])
                                    if 'LaserPowerVoltage' not in LaserCalibrationResults[current_date_name][current_color]['Pulse'][f"Laser_{laser_tag}"]:
                                        LaserCalibrationResults[current_date_name][current_color]['Pulse'][f"Laser_{laser_tag}"]['LaserPowerVoltage']=ItemsLaserPower
                                    else:
                                        LaserCalibrationResults[current_date_name][current_color]['Pulse'][f"Laser_{laser_tag}"]['LaserPowerVoltage']=self._unique(LaserCalibrationResults[current_date_name][current_color]['Pulse'][f"Laser_{laser_tag}"]['LaserPowerVoltage']+ItemsLaserPower)
        # save to json file
        if not os.path.exists(os.path.dirname(self.MainWindow.LaserCalibrationFiles)):
            os.makedirs(os.path.dirname(self.MainWindow.LaserCalibrationFiles))
        with open(self.MainWindow.LaserCalibrationFiles, "w") as file:
            json.dump(LaserCalibrationResults, file,indent=4)
        self.Warning.setText('')
        if LaserCalibrationResults=={}:
            self.Warning.setText('Data not saved! Please enter power measured!')
            self.Warning.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')
            self.Warning.setAlignment(Qt.AlignCenter)
            return
        self.MainWindow.LaserCalibrationResults=LaserCalibrationResults
        self.MainWindow._GetLaserCalibration()
        for i in self.condition_idx:
            getattr(self.MainWindow.Opto_dialog, f'_LaserColor')(i)
        time.sleep(0.01)
        self.Save.setStyleSheet("background-color : none")
        self.Save.setChecked(False)
        # Clear captured data
        self.LCM_MeasureTime=[]
        self.LCM_LaserColor_1=[]
        self.LCM_Protocol_1=[]
        self.LCM_Frequency_1=[]
        self.LCM_LaserPowerMeasured=[]
        self.LCM_Location_1=[]
        self.LCM_voltage=[]
    def _get_laser_power_list(self,ind,laser_tag):
        '''module to get the laser power list'''
        ItemsLaserPower=[]
        current_laser_tag_ind=[index for index, value in enumerate(self.LCM_Location_1) if value == f"Laser_{laser_tag}"]
        ind = list(set(ind) & set(current_laser_tag_ind))
        input_voltages= self._extract_elements(self.LCM_voltage,ind)
        laser_power_measured=self._extract_elements(self.LCM_LaserPowerMeasured,ind)
        input_voltages_unique=list(set(input_voltages))
        for n in range(len(input_voltages_unique)):
            current_voltage=input_voltages_unique[n]
            laser_ind = [k for k in range(len(input_voltages)) if input_voltages[k] == current_voltage]
            measured_power=self._extract_elements(laser_power_measured,laser_ind) 
            measured_power_mean=self._getmean(measured_power)
            ItemsLaserPower.append([float(current_voltage), measured_power_mean])
        return ItemsLaserPower
    
    def _unique(self,input):
        '''average the laser power with the same input voltage'''
        if input==[]:
            return []
        items=[]
        input_array=np.array(input)
        voltage_unique=list(set(input_array[:,0]))
        for current_votage in voltage_unique:
            laser_power=input_array[ np.logical_and(input_array[:,0]==current_votage,input_array[:,1]!='NA') ][:,1]
            mean_laser_power=self._getmean(list(laser_power))
            items.append([float(current_votage), mean_laser_power])
        return items
    def _extract_elements(self,my_list, indices):
        extracted_elements = [my_list[index] for index in indices]
        return extracted_elements
    def _getmean(self,List):
        if List==[]:
            return 'NA'
        Sum=0
        N=0
        for i in range(len(List)):
            try:
                Sum=Sum+float(List[i])
                N=N+1
            except Exception as e:
                logging.error(str(e))

        Sum=Sum/N
        return Sum
    def _Sleep(self,SleepTime):
        time.sleep(SleepTime)
    def _thread_complete(self):
        self.SleepComplete=1
    def _thread_complete2(self):
        self.SleepComplete2=1
    def _Open(self):
        '''Open the laser only once'''
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        if self.Open.isChecked():
            self.SleepComplete2=0
            # change button color and disable the open button
            self.Open.setEnabled(False)
            self.Open.setStyleSheet("background-color : green;")
            self._GetTrainingParameters(self.MainWindow)
            self._GetLaserWaveForm()
            self.worker2 = Worker(self._Sleep,float(self.LC_Duration_1)+1)
            self.worker2.signals.finished.connect(self._thread_complete2)
            self._InitiateATrial()
            self.SleepStart=1
            while 1:
                QApplication.processEvents()
                if  self.SleepStart==1: # only run once
                    self.SleepStart=0
                    self.threadpool2.start(self.worker2)
                if self.Open.isChecked()==False or self.SleepComplete2==1:
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
            self.LC_RD_1=0 # set RM to zero
            self._GetLaserWaveForm()
            if self.Initialize1==0:
                self.worker1 = Worker(self._Sleep,float(self.LC_Duration_1))
                self.worker1.signals.finished.connect(self._thread_complete)
                self.Initialize1=1
            time.sleep(1)
            while 1:
                QApplication.processEvents()
                if  self.SleepComplete==1:
                    self.SleepComplete=0
                    self._InitiateATrial()
                    self.threadpool1.start(self.worker1)
                if self.KeepOpen.isChecked()==False:
                    break
            self.KeepOpen.setStyleSheet("background-color : none")
            self.KeepOpen.setChecked(False)
        else:
            # change button color
            self.KeepOpen.setStyleSheet("background-color : none")
            self.KeepOpen.setChecked(False)

def initialize_dic(dic_name,key_list=[]):
    '''initialize the parameters'''
    if key_list==[]:
        return dic_name
    key = key_list[0]
    key_list_new = key_list[1:]
    if key not in dic_name:
        dic_name[key]={}
    initialize_dic(dic_name[key],key_list=key_list_new)
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
        self.GoCueDecibel.setText(str(self.MainWindow.Other_go_cue_decibel))
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
            grid_layout.addWidget(label, i+1, 0)
            grid_layout.addWidget(getattr(self, f'LickSpoutReference{axis.upper()}'), i+1, 1)
        # add in lick spout distance
        grid_layout.addWidget(self.label_96, len(positions.keys())+1, 0)
        grid_layout.addWidget(self.LickSpoutDistance, len(positions.keys())+1, 1)
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
        self.GoCueDecibel.textChanged.connect(self._save_go_cue_decibel)
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
        self.current_project_name=self.ProjectName.currentText()
        self.funding_institution=self.project_info['Funding Institution'][current_project_index]
        self.grant_number=self.project_info['Grant Number'][current_project_index]
        self.investigators=self.project_info['Investigators'][current_project_index]
        self.fundee=self.project_info['Fundee'][current_project_index]
        self.FundingSource.setText(str(self.funding_institution))
        self.Investigators.setText(str(self.investigators))
        self.GrantNumber.setText(str(self.grant_number))
        self.Fundee.setText(str(self.fundee))

    def _save_lick_spout_distance(self):
        '''save the lick spout distance'''
        self.MainWindow.Other_lick_spout_distance=self.LickSpoutDistance.text()

    def _save_go_cue_decibel(self):
        '''save the go cue decibel'''
        self.MainWindow.Other_go_cue_decibel=self.GoCueDecibel.text()

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
        self._manage_signals(enable=False,keys=['ProjectName'],action=self._show_project_info)
        self.ProjectName.addItems(project_names)
        self._manage_signals(enable=True,keys=['ProjectName'],action=self._show_project_info)
        self._show_project_info()

    def _get_basics(self):
        '''get the basic information'''
        self.probe_types = ['StickMicroscopes','EphysProbes']
        self.metadata_keys = ['microscopes','probes']
        self.widgets = [self.Microscopes,self.Probes]
    
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
        
    def _update_metadata(self,update_rig_metadata=True,update_session_metadata=True,dont_clear=False):
        '''update the metadata'''
        if (update_rig_metadata) and ('rig_metadata_file' in self.meta_data):
            if os.path.basename(self.meta_data['rig_metadata_file'])!=self.RigMetadataFile.text() and self.RigMetadataFile.text() != '':
                if dont_clear==False:
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
        self.meta_data=self.MainWindow._Concat(widget_dict, self.meta_data, 'session_metadata')
        self.meta_data['rig_metadata_file'] = self.RigMetadataFile.text()
        
    def _save_metadata(self):
        '''save the metadata collected from this dialogue to an independent json file'''
        # save metadata parameters
        self._save_metadata_dialog_parameters()
        # Save self.meta_data to JSON
        metadata_dialog_folder=self.MainWindow.metadata_dialog_folder
        if not os.path.exists(metadata_dialog_folder):
            os.makedirs(metadata_dialog_folder)
        json_file=os.path.join(metadata_dialog_folder, self.MainWindow.current_box+'_'+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+ '_metadata_dialog.json')

        with open(json_file, 'w') as file:
            json.dump(self.meta_data, file, indent=4)
    
    def _get_widgets(self):
        '''get the widgets used for saving/loading metadata'''
        exclude_widgets=self._get_children_keys(self.Probes)
        exclude_widgets+=self._get_children_keys(self.Microscopes)
        exclude_widgets+=['EphysProbes','RigMetadataFile','StickMicroscopes']
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
            probe_type=probe_types[i]
            metadata_key=metadata_keys[i]
            widget=widgets[i]
            current_probe = getattr(self, probe_type).currentText()
            self.meta_data['session_metadata'] = initialize_dic(self.meta_data['session_metadata'], key_list=[metadata_key, current_probe])
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
            action=self._save_configuration

            self._manage_signals(enable=False, keys=self._get_children_keys(widget),action=action)
            self._manage_signals(enable=False, keys=[probe_type], action=self._show_angles)
            
            current_probe = getattr(self, probe_type).currentText()
            self.meta_data['session_metadata'] = initialize_dic(self.meta_data['session_metadata'], key_list=[metadata_key])
            if current_probe == '' or current_probe not in self.meta_data['session_metadata'][metadata_key]:
                self._clear_angles(self._get_children_keys(widget))
                self._manage_signals(enable=True, keys=[probe_type], action=self._show_angles)
                self._manage_signals(enable=True, keys=self._get_children_keys(widget), action=action)
                continue

            self.meta_data['session_metadata'] = initialize_dic(self.meta_data['session_metadata'], key_list=[metadata_key, current_probe])
            keys = self._get_children_keys(widget)
            for key in keys:
                self.meta_data['session_metadata'][metadata_key][current_probe].setdefault(key, '')
                getattr(self, key).setText(self.meta_data['session_metadata'][metadata_key][current_probe][key])

            self._manage_signals(enable=True, keys=self._get_children_keys(widget), action=action)
            self._manage_signals(enable=True, keys=[probe_type], action=self._show_angles)
            

    def _get_children_keys(self,parent_widget = None):
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
        items=[]
        if 'stick_microscopes' in self.meta_data['rig_metadata']:
            for i in range(len(self.meta_data['rig_metadata']['stick_microscopes'])):
                items.append(self.meta_data['rig_metadata']['stick_microscopes'][i]['name'])
        if items==[]:
            self.StickMicroscopes.clear()
            self._show_angles()
            return
        
        self._manage_signals(enable=False,keys=['StickMicroscopes'],action=self._show_angles)
        self._manage_signals(enable=False,keys=self._get_children_keys(self.Microscopes),action=self._save_configuration)
        self.StickMicroscopes.clear()
        self.StickMicroscopes.addItems(items)
        self._manage_signals(enable=True,keys=['StickMicroscopes'],action=self._show_angles)
        self._manage_signals(enable=True,keys=self._get_children_keys(self.Microscopes),action=self._save_configuration)
        self._show_angles()

    def _show_ephys_probes(self):
        '''setting the ephys probes from the rig metadata'''
        if self.meta_data['rig_metadata'] == {}:
            self.EphysProbes.clear()
            self._show_angles()
            return
        items=[]
        if 'ephys_assemblies' in self.meta_data['rig_metadata']:
            for assembly in self.meta_data['rig_metadata']['ephys_assemblies']:
                for probe in assembly['probes']:
                    items.append(probe['name'])
        if items==[]:
            self.EphysProbes.clear()
            self._show_angles()
            return
        
        self._manage_signals(enable=False,keys=['EphysProbes'],action=self._show_angles)
        self._manage_signals(enable=False,keys=self._get_children_keys(self.Probes),action=self._save_configuration)
        self.EphysProbes.clear()
        self.EphysProbes.addItems(items)
        self._manage_signals(enable=True,keys=['EphysProbes'],action=self._show_angles)
        self._manage_signals(enable=True,keys=self._get_children_keys(self.Probes),action=self._save_configuration)
        self._show_angles()
    
    def _manage_signals(self, enable=True,keys='',signals='',action=''):
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
            keys=self._get_children_keys(self.Probes)
        if signals == '':
            signals = []
            for attr in keys:
                if isinstance(getattr(self, attr),QtWidgets.QLineEdit):
                    signals.append(getattr(self, attr).textChanged)
                elif isinstance(getattr(self, attr),QtWidgets.QComboBox):
                    signals.append(getattr(self, attr).currentIndexChanged)
        if action == '':
            action = self._save_configuration

        for signal in signals:
            if enable:
                signal.connect(action)
            else:
                signal.disconnect(action)

    def _SelectRigMetadata(self,rig_metadata_file=None):
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
        
class AutoTrainDialog(QDialog):
    '''For automatic training'''

    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        uic.loadUi('AutoTrain.ui', self)
        self.MainWindow = MainWindow
        
        # Initializations
        self.auto_train_engaged = False
        self.widgets_locked_by_auto_train = []
        self.stage_in_use = None
        self.curriculum_in_use = None

        # Connect to Auto Training Manager and Curriculum Manager
        self.aws_connected = self._connect_auto_training_manager()
        
        # Disable Auto Train button if not connected to AWS
        if not self.aws_connected:
            self.MainWindow.AutoTrain.setEnabled(False)
            return
        
        self._connect_curriculum_manager()
        
        # Signals slots
        self._setup_allbacks()
        
        # Sync selected subject_id
        self.update_auto_train_fields(subject_id=self.MainWindow.behavior_session_model.subject)
                
    def _setup_allbacks(self):
        self.checkBox_show_this_mouse_only.stateChanged.connect(
            self._show_auto_training_manager
        )
        self.checkBox_override_stage.stateChanged.connect(
            self._override_stage_clicked
        )
        self.comboBox_override_stage.currentIndexChanged.connect(
            self._update_stage_to_apply
        )
        self.pushButton_apply_auto_train_paras.clicked.connect(
            self.update_auto_train_lock
        )
        self.checkBox_override_curriculum.stateChanged.connect(
            self._override_curriculum_clicked
        )
        self.pushButton_apply_curriculum.clicked.connect(
            self._apply_curriculum
        )
        self.pushButton_show_curriculum_in_streamlit.clicked.connect(
            self._show_curriculum_in_streamlit
        )
        self.pushButton_show_auto_training_history_in_streamlit.clicked.connect(
            self._show_auto_training_history_in_streamlit
        )
        self.pushButton_preview_auto_train_paras.clicked.connect(
            self._preview_auto_train_paras
        )
        
    def update_auto_train_fields(self, 
                                 subject_id: str, 
                                 curriculum_just_overridden: bool = False,
                                 auto_engage: bool = False):
        # Do nothing if not connected to AWS
        if not self.aws_connected:
            return
        
        self.selected_subject_id = subject_id
        self.label_subject_id.setText(self.selected_subject_id)
        
        # Get the latest entry from auto_train_manager
        self.df_this_mouse = self.df_training_manager.query(
            f"subject_id == '{self.selected_subject_id}'"
        )
        
        if self.df_this_mouse.empty:
            logger.info(f"No entry found in df_training_manager for subject_id: {self.selected_subject_id}")
            self.last_session = None
            self.curriculum_in_use = None
            self.label_session.setText('subject not found')
            self.label_curriculum_name.setText('subject not found')
            self.label_last_actual_stage.setText('subject not found')
            self.label_next_stage_suggested.setText('subject not found')
            self.label_subject_id.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')
            
            # disable some stuff
            self.checkBox_override_stage.setChecked(False)
            self.checkBox_override_stage.setEnabled(False)
            self.pushButton_apply_auto_train_paras.setEnabled(False)
            self.pushButton_preview_auto_train_paras.setEnabled(False)
            
            # override curriculum is checked by default and disabled
            self.checkBox_override_curriculum.setChecked(True)
            self.checkBox_override_curriculum.setEnabled(False)
            
            # prompt user to create a new mouse
            if self.isVisible():
                QMessageBox.information(
                    self,
                    "Info",
                    f"Mouse {self.selected_subject_id} does not exist in the auto training manager!\n"
                    f"If it is a new mouse (not your typo), please select a curriculum to add it."
                )
                
            self.tableView_df_curriculum.clearSelection() # Unselect any curriculum
            self.selected_curriculum = None
            self.pushButton_apply_curriculum.setEnabled(True)
            self._add_border_curriculum_selection()
                        
        else: # If the mouse exists in the auto_train_manager
            # get curriculum in use from the last session, unless we just overrode it
            if not curriculum_just_overridden:
                # fetch last session
                self.last_session = self.df_this_mouse.iloc[0]  # The first row is the latest session
                
                last_curriculum_schema_version = self.last_session['curriculum_schema_version']
                if codebase_curriculum_schema_version != last_curriculum_schema_version:
                    # schema version don't match. prompt user to choose another curriculum
                    if self.isVisible():
                        QMessageBox.information(
                            self,
                            "Info",
                            f"The curriculum_schema_version of the last session ({last_curriculum_schema_version}) does not match "
                            f"that of the current code base ({codebase_curriculum_schema_version})!\n"
                            f"This is likely because the AutoTrain system has been updated since the last session.\n\n"
                            f"Please choose another valid curriculum and a training stage for this mouse."
                        )
                    
                    # Clear curriculum in use
                    self.curriculum_in_use = None
                    self.pushButton_preview_auto_train_paras.setEnabled(False)

                    # Turn on override curriculum
                    self.checkBox_override_curriculum.setChecked(True)
                    self.checkBox_override_curriculum.setEnabled(False)
                    self.tableView_df_curriculum.clearSelection() # Unselect any curriculum
                    self.selected_curriculum = None
                    self.pushButton_apply_curriculum.setEnabled(True)
                    self._add_border_curriculum_selection()
                    
                    # Update UI
                    self._update_available_training_stages()
                    self._update_stage_to_apply()
                    
                    # Update df_auto_train_manager and df_curriculum_manager
                    self._show_auto_training_manager()
                    self._show_available_curriculums()      
                    
                    # Eearly return
                    return
                else:
                    self.curriculum_in_use = self.curriculum_manager.get_curriculum(
                        curriculum_name=self.last_session['curriculum_name'],
                        curriculum_schema_version=last_curriculum_schema_version,
                        curriculum_version=self.last_session['curriculum_version'],
                    )['curriculum']

                    self.pushButton_preview_auto_train_paras.setEnabled(True)
            
                # update stage info
                self.label_last_actual_stage.setText(str(self.last_session['current_stage_actual']))
                self.label_next_stage_suggested.setText(str(self.last_session['next_stage_suggested']))
                self.label_next_stage_suggested.setStyleSheet("color: black;")
                                
            else:
                self.label_last_actual_stage.setText('irrelevant (curriculum overridden)')
                self.label_next_stage_suggested.setText('irrelevant')
                self.label_next_stage_suggested.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')
                
                # Set override stage automatically
                self.checkBox_override_stage.setChecked(True)
                self.checkBox_override_stage.setEnabled(True)
            
            # update more info
            self.label_curriculum_name.setText(
                get_curriculum_string(self.curriculum_in_use)
                )
            self.label_session.setText(str(self.last_session['session']))
            self.label_subject_id.setStyleSheet("color: black;")
            
            # enable apply training stage
            self.pushButton_apply_auto_train_paras.setEnabled(True)
            self.pushButton_preview_auto_train_paras.setEnabled(True)
            
            # disable apply curriculum                        
            self.pushButton_apply_curriculum.setEnabled(False)
            self._remove_border_curriculum_selection()
            
            # Reset override curriculum
            self.checkBox_override_curriculum.setChecked(False)
            if not self.auto_train_engaged:
                self.checkBox_override_curriculum.setEnabled(True)
                    
        # Update UI
        self._update_available_training_stages()
        self._update_stage_to_apply()
        
        # Update df_auto_train_manager and df_curriculum_manager
        self._show_auto_training_manager()
        self._show_available_curriculums()
        
        # auto engage
        if auto_engage:
            try:
                self.pushButton_apply_auto_train_paras.click()
                logger.info(f"Auto engage successful for mouse {self.selected_subject_id}")
            except Exception as e:
                logger.warning(f"Auto engage failed: {str(e)}")


    def _add_border_curriculum_selection(self):
        self.tableView_df_curriculum.setStyleSheet(
                '''
                QTableView::item:selected {
                background-color: lightblue;
                color: black;
                            }

                QTableView {
                                border:7px solid rgb(255, 170, 255);
                }
                '''
        )
    
    def _remove_border_curriculum_selection(self):
        self.tableView_df_curriculum.setStyleSheet(
                '''
                QTableView::item:selected {
                background-color: lightblue;
                color: black;
                            }
                '''
        )
                
    def _connect_auto_training_manager(self):
        try:
            self.auto_train_manager = DynamicForagingAutoTrainManager(
                manager_name='447_demo',
                df_behavior_on_s3=dict(bucket='aind-behavior-data',
                                    root='foraging_nwb_bonsai_processed/',
                                    file_name='df_sessions.pkl'),
                df_manager_root_on_s3=dict(bucket='aind-behavior-data',
                                        root='foraging_auto_training/')
            )
        except:
            logger.error("AWS connection failed!")
            QMessageBox.critical(self.MainWindow,
                                 'Box {}, Error'.format(self.MainWindow.box_letter),
                                 f'AWS connection failed!\n'
                                 f'Please check your AWS credentials at ~\.aws\credentials and restart the GUI!\n\n'
                                 f'The AutoTrain will be disabled until the connection is restored.')
            return False
        df_training_manager = self.auto_train_manager.df_manager
        
        # Format dataframe
        df_training_manager['session'] = df_training_manager['session'].astype(int)
        df_training_manager['foraging_efficiency'] = \
            df_training_manager['foraging_efficiency'].round(3)
            
        # Sort by subject_id and session
        df_training_manager.sort_values(
            by=['subject_id', 'session'],
            ascending=[False, False],  # Newest sessions on the top,
            inplace=True
        )
        self.df_training_manager = df_training_manager
        return True
            
    def _show_auto_training_manager(self):
        if_this_mouse_only = self.checkBox_show_this_mouse_only.isChecked()
        
        if if_this_mouse_only:
            df_training_manager_to_show = self.df_this_mouse
        else:
            df_training_manager_to_show = self.df_training_manager
                
        df_training_manager_to_show = df_training_manager_to_show[
                ['subject_id',
                 'session',
                 'session_date',
                 'curriculum_name', 
                 'curriculum_version',
                 'curriculum_schema_version',
                 'task',
                 'current_stage_suggested',
                 'current_stage_actual',
                 'decision',
                 'next_stage_suggested',
                 'if_closed_loop',
                 'if_overriden_by_trainer',
                 'finished_trials',
                 'foraging_efficiency',
                 ]
            ]
        
        # Show dataframe in QTableView
        model = PandasModel(df_training_manager_to_show)
        self.tableView_df_training_manager.setModel(model)
        
        # Format table
        self.tableView_df_training_manager.resizeColumnsToContents()
        self.tableView_df_training_manager.setSortingEnabled(False)
        
        # Highlight the latest session
        if self.last_session is not None:
            session_index = df_training_manager_to_show.reset_index().index[
                (df_training_manager_to_show['subject_id'] == self.last_session['subject_id']) &
                (df_training_manager_to_show['session'] == self.last_session['session'])
            ][0]
            _index = self.tableView_df_training_manager.model().index(session_index, 0)
            self.tableView_df_training_manager.clearSelection()
            self.tableView_df_training_manager.selectionModel().select(
                _index,
                QItemSelectionModel.Select | QItemSelectionModel.Rows
            )
            self.tableView_df_training_manager.scrollTo(_index)

    def _connect_curriculum_manager(self):
        self.curriculum_manager = CurriculumManager(
            saved_curriculums_on_s3=dict(
                bucket='aind-behavior-data',
                root='foraging_auto_training/saved_curriculums/'
            ),
            # saved to tmp folder under user's home directory
            saved_curriculums_local=os.path.expanduser('~/.aind_auto_train/curriculum_manager/')
        )

    def _show_available_curriculums(self):
        self.df_curriculums = self.curriculum_manager.df_curriculums()

        # Show dataframe in QTableView
        model = PandasModel(self.df_curriculums)
        self.tableView_df_curriculum.setModel(model)
        
        # Format table
        self.tableView_df_curriculum.resizeColumnsToContents()
        self.tableView_df_curriculum.setSortingEnabled(True)
        
        # Add callback
        self.tableView_df_curriculum.clicked.connect(self._update_curriculum_diagrams)
        
        self._sync_curriculum_in_use_to_table()
        
    def _sync_curriculum_in_use_to_table(self):
        # Auto select the curriculum_in_use, if any
        if self.curriculum_in_use is None:
            return
            
        self.tableView_df_curriculum.clearSelection() # Unselect any curriculum

        curriculum_index = self.df_curriculums.reset_index().index[
            (self.df_curriculums['curriculum_name'] == self.curriculum_in_use.curriculum_name) &
            (self.df_curriculums['curriculum_version'] == self.curriculum_in_use.curriculum_version) &
            (self.df_curriculums['curriculum_schema_version'] == self.curriculum_in_use.curriculum_schema_version)
        ][0]

        # Auto click the curriculum of the latest session
        _index = self.tableView_df_curriculum.model().index(curriculum_index, 0)
        self.tableView_df_curriculum.selectionModel().select(
            _index,
            QItemSelectionModel.Select | QItemSelectionModel.Rows
        )
        self.tableView_df_curriculum.scrollTo(_index)

        self._update_curriculum_diagrams(_index) # Update diagrams
        
    def _update_curriculum_diagrams(self, index):
        # Retrieve selected curriculum
        row = index.row()
        selected_row = self.df_curriculums.iloc[row]
        logger.info(f"Selected curriculum: {selected_row.to_dict()}")
        self.selected_curriculum = self.curriculum_manager.get_curriculum(
            curriculum_name=selected_row['curriculum_name'],
            curriculum_schema_version=selected_row['curriculum_schema_version'],
            curriculum_version=selected_row['curriculum_version'],
        )
                                            
    def _show_curriculum_in_streamlit(self):
        if self.selected_curriculum is not None:
            webbrowser.open(
                'https://foraging-behavior-browser.allenneuraldynamics-test.org/'
                '?tab_id=tab_auto_train_curriculum'
                f'&auto_training_curriculum_name={self.selected_curriculum["curriculum"].curriculum_name}'
                f'&auto_training_curriculum_version={self.selected_curriculum["curriculum"].curriculum_version}'
                f'&auto_training_curriculum_schema_version={self.selected_curriculum["curriculum"].curriculum_schema_version}'
            )
                        
    def _show_auto_training_history_in_streamlit(self):
        webbrowser.open(
            'https://foraging-behavior-browser.allenneuraldynamics-test.org/?'
            f'&filter_subject_id={self.selected_subject_id}'
            f'&tab_id=tab_auto_train_history'
            f'&auto_training_history_x_axis=session'
            f'&auto_training_history_sort_by=subject_id'
            f'&auto_training_history_sort_order=descending'
        )

        
    def _update_available_training_stages(self):            
        # If AutoTrain is engaged, and override stage is checked
        if self.auto_train_engaged and self.checkBox_override_stage.isChecked():
            # Restore stage_in_use. No need to reload available stages
            self.comboBox_override_stage.setCurrentText(self.stage_in_use)
        else:
            # Reload available stages
            if self.curriculum_in_use is not None:
                available_training_stages = [v.name for v in 
                                            self.curriculum_in_use.parameters.keys()]
            else:
                available_training_stages = []
                
            self.comboBox_override_stage.clear()
            self.comboBox_override_stage.addItems(available_training_stages)

                
    def _override_stage_clicked(self, state):
        logger.info(f"Override stage clicked: state={state}")
        if state:
            self.comboBox_override_stage.setEnabled(True)
        else:
            self.comboBox_override_stage.setEnabled(False)
        self._update_stage_to_apply()
        
    def _override_curriculum_clicked(self, state):
        logger.info(f"Override stage clicked: state={state}")
        if state:
            self.pushButton_apply_curriculum.setEnabled(True)
            self._add_border_curriculum_selection()
        else:
            self.pushButton_apply_curriculum.setEnabled(False)
            self._remove_border_curriculum_selection()
        
        # Always sync
        self._sync_curriculum_in_use_to_table()
            
    def _update_stage_to_apply(self):
        if self.checkBox_override_stage.isChecked():
            self.stage_in_use = self.comboBox_override_stage.currentText()
            logger.info(f"Stage overridden to: {self.stage_in_use}")
        elif self.last_session is not None:
            self.stage_in_use = self.last_session['next_stage_suggested']
        else:
            self.stage_in_use = 'unknown training stage'
        
        self.pushButton_apply_auto_train_paras.setText(
            f"Apply and lock\n"
            + '\n'.join(get_curriculum_string(self.curriculum_in_use).split('(')).strip(')') 
            + f"\n{self.stage_in_use}"
        )
        
        logger.info(f"Current stage to apply: {self.stage_in_use} @"
                    f"{get_curriculum_string(self.curriculum_in_use)}")
                
    def _apply_curriculum(self):
        # Check if a curriculum is selected
        if not hasattr(self, 'selected_curriculum') or self.selected_curriculum is None:
            QMessageBox.critical(self, "Box {}, Error".format(self.MainWindow.box_letter), "Please select a curriculum!")
            return
        
        # Always enable override stage
        self.checkBox_override_stage.setEnabled(True)
        
        if self.df_this_mouse.empty:
            # -- This is a new mouse, we add the first dummy session --
            # Update global curriculum_in_use
            self.curriculum_in_use = self.selected_curriculum['curriculum']
            
            # Add a dummy entry to df_training_manager
            self.df_training_manager = pd.concat(
                [self.df_training_manager, 
                pd.DataFrame.from_records([
                    dict(subject_id=self.selected_subject_id,
                        session=0,
                        session_date='unknown',
                        curriculum_name=self.curriculum_in_use.curriculum_name,
                        curriculum_version=self.curriculum_in_use.curriculum_version,
                        curriculum_schema_version=self.curriculum_in_use.curriculum_schema_version,
                        task=None,
                        current_stage_suggested=None,
                        current_stage_actual=None,
                        decision=None,
                        next_stage_suggested='STAGE_1_WARMUP' 
                            if 'STAGE_1_WARMUP' in [k.name for k in self.curriculum_in_use.parameters.keys()]
                            else 'STAGE_1',
                        if_closed_loop=None,
                        if_overriden_by_trainer=None,
                        finished_trials=None,
                        foraging_efficiency=None,
                        )
                ])]
            )
            logger.info(f"Added a dummy session 0 for mouse {self.selected_subject_id} ")
            
            self.checkBox_override_curriculum.setChecked(False)
            self.checkBox_override_curriculum.setEnabled(True)
        
            # Refresh the GUI
            self.update_auto_train_fields(subject_id=self.selected_subject_id)
        else:
            # -- This is an existing mouse, we are changing the curriculum --
            # Not sure whether we should leave this option open. But for now, I allow this freedom.            
            if self.selected_curriculum['curriculum'] == self.curriculum_in_use:
                # The selected curriculum is the same as the one in use
                logger.info(f"Selected curriculum is the same as the one in use. No change is made.")
                QMessageBox.information(self, "Box {}, Info".format(self.MainWindow.box_letter), "Selected curriculum is the same as the one in use. No change is made.")
                return
            else:
                # Confirm with the user about overriding the curriculum
                reply = QMessageBox.question(self, "Box {}, Confirm".format(self.MainWindow.box_letter),
                                             f"Are you sure you want to override the curriculum?\n"
                                             f"If yes, please also manually select a training stage.",
                                             QMessageBox.Yes | QMessageBox.No,
                                             QMessageBox.No)
                if reply == QMessageBox.Yes:                
                    # Update curriculum in use
                    logger.info(f"Change curriculum from "
                                f"{get_curriculum_string(self.curriculum_in_use)} to "
                                f"{get_curriculum_string(self.selected_curriculum['curriculum'])}")
                    self.curriculum_in_use = self.selected_curriculum['curriculum']
                        
            self.checkBox_override_curriculum.setChecked(False)
            self.pushButton_apply_curriculum.setEnabled(False)
            self._remove_border_curriculum_selection() # Remove the highlight of curriculum table view

            # Refresh the GUI
            self.update_auto_train_fields(subject_id=self.selected_subject_id,
                                          curriculum_just_overridden=reply == QMessageBox.Yes)
        
    def _preview_auto_train_paras(self, preview_checked):
        """Apply parameters to the GUI without applying and locking the widgets.
        """
        
        if preview_checked:
            if self.curriculum_in_use is None:
                return
            
            # Get parameter settings
            paras = self.curriculum_in_use.parameters[
                TrainingStage[self.stage_in_use]
            ]
            
            # Convert to GUI format and set the parameters
            paras_dict = paras.to_GUI_format()
            widgets_set, self.widgets_changed = self._set_training_parameters(
                paras_dict=paras_dict,
                if_apply_and_lock=False
            )
            
            # Clear the style of all widgets
            for widget in widgets_set:
                widget.setStyleSheet("font-weight: normal")
            
            # Highlight the changed widgets
            for widget in self.widgets_changed.keys():
                widget.setStyleSheet(
                    '''
                        background-color: rgb(225, 225, 0);
                        font-weight: bold
                    '''
                )
        elif hasattr(self, 'widgets_changed'):  # Revert to previous values
            paras_to_revert = {widget.objectName():value 
                               for widget, value in self.widgets_changed.items()}
            
            _, widgets_changed = self._set_training_parameters(
                paras_dict=paras_to_revert,
                if_apply_and_lock=False
            )            
            
            # Clear the style of all widgets
            for widget in widgets_changed:
                widget.setStyleSheet("font-weight: normal")
            
            self.widgets_changed = {}
                    
    def update_auto_train_lock(self, engaged):
        if engaged:
            logger.info(f"AutoTrain engaged! {self.stage_in_use} @ {get_curriculum_string(self.curriculum_in_use)}")
            
            # Update the flag
            self.auto_train_engaged = True

            # Get parameter settings
            paras = self.curriculum_in_use.parameters[
                TrainingStage[self.stage_in_use]
            ]
            
            # Convert to GUI format and set the parameters
            paras_dict = paras.to_GUI_format()
            self.widgets_locked_by_auto_train, _ = self._set_training_parameters(
                paras_dict=paras_dict,
                if_apply_and_lock=True
            )
            
            if self.widgets_locked_by_auto_train == []:  # Error in setting parameters
                self.update_auto_train_lock(engaged=False)  # Uncheck the "apply" button
                return

            # lock the widgets that have been set by auto training 
            for widget in self.widgets_locked_by_auto_train:
                # Exclude some fields so that RAs can change them without going off-curriculum
                # See https://github.com/AllenNeuralDynamics/aind-behavior-blog/issues/620
                if widget.objectName() in ["auto_stop_ignore_win", "MaxTrial", "MaxTime"]:
                    continue
                widget.setEnabled(False)
                # set the border color to green
                widget.setStyleSheet("border: 2px solid  rgb(0, 214, 103);")
                
            self.MainWindow.TrainingParameters.setStyleSheet(
                '''QGroupBox {
                        border: 5px solid  rgb(0, 214, 103)
                    }
                '''
            )
            self.MainWindow.label_auto_train_stage.setText(
                '\n'.join(get_curriculum_string(self.curriculum_in_use).split('(')).strip(')') 
                + f", {self.stage_in_use}"
            )
            self.MainWindow.label_auto_train_stage.setStyleSheet("color: rgb(0, 214, 103);")
            
            # disable override
            self.checkBox_override_stage.setEnabled(False)
            self.comboBox_override_stage.setEnabled(False)
            
            # disable preview
            self.pushButton_preview_auto_train_paras.setEnabled(False)
                                    
        else:
            logger.info("AutoTrain disengaged!")

            # Update the flag
            self.auto_train_engaged = False
            
            # Uncheck the button (when this is called from the MainWindow, not from actual button click)
            self.pushButton_apply_auto_train_paras.setChecked(False)
            self.pushButton_preview_auto_train_paras.setEnabled(True)

            # Unlock the previously engaged widgets
            for widget in self.widgets_locked_by_auto_train:
                widget.setEnabled(True)
                # clear style
                widget.setStyleSheet("")
            self.MainWindow.TrainingParameters.setStyleSheet("")
            self.MainWindow.label_auto_train_stage.setText("off curriculum")
            self.MainWindow.label_auto_train_stage.setStyleSheet(f'color: {self.MainWindow.default_warning_color};')


            # enable override
            self.checkBox_override_stage.setEnabled(True)
            self.comboBox_override_stage.setEnabled(self.checkBox_override_stage.isChecked())


    def _set_training_parameters(self, paras_dict, if_apply_and_lock=False):
        """Accepts a dictionary of parameters and set the GUI accordingly
        Trying to refactor Foraging.py's _TrainingStage() here.
        
        paras_dict: a dictionary of parameters following Xinxin's convention
        if_apply_and_lock: if True, press enter after setting the parameters
        """
        # Track widgets that have been set by auto training
        widgets_set = []
        widgets_changed = {}  # Dict of {changed_key: previous_value}
        
        # If warmup exists, always turn it off first, set other parameters, 
        # and then turn it to the desired state
        keys = list(paras_dict.keys())
        if 'warmup' in keys:
            keys.remove('warmup') 
            keys += ['warmup']
            
            # Set warmup to off first so that all AutoTrain parameters
            # can be correctly registered in WarmupBackup if warmup is turned on later
            if paras_dict and paras_dict['warmup'] != self.MainWindow.warmup.currentText():
                widgets_changed.update(
                    {self.MainWindow.warmup: 
                     self.MainWindow.warmup.currentText()
                     }
                ) # Track the changes
            
            index=self.MainWindow.warmup.findText('off')
            self.MainWindow.warmup.setCurrentIndex(index)
                                       
        # Loop over para_dict and try to set the values
        for key in keys:
            value = paras_dict[key]
            
            if key == 'task':
                widget_task = self.MainWindow.Task
                task_ind = widget_task.findText(paras_dict['task'])
                if task_ind < 0:
                    logger.error(f"Task {paras_dict['task']} not found!")
                    QMessageBox.critical(self, "Box {}, Error".format(self.MainWindow.box_letter), 
                        f'''Task "{paras_dict['task']}" not found. Check the curriculum!''')
                    return [] # Return an empty list without setting anything
                else:
                    if task_ind != widget_task.currentIndex():
                        widgets_changed.update(
                            {widget_task: widget_task.currentIndex()}
                        ) # Track the changes
                    widget_task.setCurrentIndex(task_ind)
                    logger.info(f"Task is set to {paras_dict['task']}")
                    widgets_set.append(widget_task)
                    
                    continue  # Continue to the next parameter
            
            # For other parameters, try to find the widget and set the value               
            widget = self.MainWindow.findChild(QObject, key)
            if widget is None:
                logger.info(f''' Widget "{key}" not found. skipped...''')
                continue
            
            # Enable warmup-related widgets if warmup will be turned on later.
            # Otherwise, they are now disabled (see 30 lines above) 
            # and thus cannot be set by AutoTrain (see above line)
            if 'warm' in key and paras_dict['warmup'] == 'on':
                widget.setEnabled(True)
            
            # If the parameter is disabled by the GUI in the first place, skip it
            # For example, the field "uncoupled reward" in a coupled task.
            if not widget.isEnabled():
                logger.info(f''' Widget "{key}" has been disabled by the GUI. skipped...''')
                continue
            
            # Set the value according to the widget type
            if isinstance(widget, (QtWidgets.QLineEdit, 
                                   QtWidgets.QTextEdit)):
                if value != widget.text():
                    widgets_changed.update({widget: widget.text()}) # Track the changes
                    widget.setText(value)
            elif isinstance(widget, QtWidgets.QComboBox):
                ind = widget.findText(value)
                if ind < 0:
                    logger.error(f"Parameter choice {key}={value} not found!")
                    continue  # Still allow other parameters to be set
                else:
                    if ind != widget.currentIndex():
                        widgets_changed.update({widget: widget.currentText()}) # Track the changes
                        widget.setCurrentIndex(ind)
            elif isinstance(widget, (QtWidgets.QDoubleSpinBox)):
                if float(value) != widget.value():
                    widgets_changed.update({widget: widget.value()}) # Track the changes
                    widget.setValue(float(value))
            elif isinstance(widget, QtWidgets.QSpinBox):
                if float(value) != widget.value():
                    widgets_changed.update({widget: widget.value()}) # Track the changes
                    widget.setValue(int(value))    
            elif isinstance(widget, QtWidgets.QPushButton):
                if key=='AutoReward':
                    if bool(value) != widget.isChecked():
                        widgets_changed.update({widget: widget.isChecked()})  # Track the changes
                        widget.setChecked(bool(value))
                        self.MainWindow._AutoReward()            
            
            # Append the widgets that have been set
            widgets_set.append(widget)
            logger.info(f"{key} is set to {value}")
            
            # Lock all water reward-related widgets if one exists
            if 'LeftValue' in key:
                widgets_set.extend(
                    [self.MainWindow.findChild(QObject, 'LeftValue'),
                     self.MainWindow.findChild(QObject, 'LeftValue_volume')
                    ]
                )
            if 'RightValue' in key:
                widgets_set.extend(
                    [self.MainWindow.findChild(QObject, 'RightValue'),
                     self.MainWindow.findChild(QObject, 'RightValue_volume')
                    ]
                )
        
        # Mimic an "ENTER" press event to update the parameters
        if if_apply_and_lock:
            self.MainWindow._keyPressEvent()
        
        return widgets_set, widgets_changed
            
    def _clear_layout(self, layout):
        # Remove all existing widgets from the layout
        for i in reversed(range(layout.count())): 
            layout.itemAt(i).widget().setParent(None)

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
    

class OpticalTaggingDialog(QDialog):
    
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        uic.loadUi('OpticalTagging.ui', self)
        self._connectSignalsSlots()
        self.MainWindow = MainWindow
        self.current_optical_tagging_par={}
        self.optical_tagging_par={}
        self.cycle_finish_tag = 1
        self.thread_finish_tag = 1
        self.threadpool = QThreadPool()
        # find all buttons and set them to not be the default button
        for container in [self]:
            for child in container.findChildren((QtWidgets.QPushButton)):     
                child.setDefault(False)
                child.setAutoDefault(False)
                
    def _connectSignalsSlots(self):
        self.Start.clicked.connect(self._Start)
        self.WhichLaser.currentIndexChanged.connect(self._WhichLaser)
        self.Restart.clicked.connect(self._start_over)
        self.Save.clicked.connect(self._Save)
        self.ClearData.clicked.connect(self._clear_data)
    
    def _Save(self):
        '''Save the optical tagging results'''
        if self.optical_tagging_par=={}:
            return
        # giving the user a warning message to show "This will only save the current parameters and results related to the random reward. If you want to save more including the metadata, please go to the main window and click the save button."
        QMessageBox.warning(
            self,
            "Save Warning",
            "Only the current parameters and results related to the optical tagging will be saved. "
            "To save additional data, including metadata, please use the Save button in the main window."
        )
        # get the save folder
        if self.MainWindow.CreateNewFolder == 1:
            self.MainWindow._GetSaveFolder()
            self.MainWindow.CreateNewFolder = 0

        save_file=self.MainWindow.SaveFileJson
        if not os.path.exists(os.path.dirname(save_file)):
            os.makedirs(os.path.dirname(save_file))
            logging.info(f"Created new folder: {os.path.dirname(save_file)}")
            
        self.optical_tagging_par["task_parameters"]={
            "laser_name": self.WhichLaser.currentText(),
            "protocol": self.Protocol.currentText(),
            "laser_1_color": self.Laser_1_color.currentText(),
            "laser_2_color": self.Laser_2_color.currentText(),
            "laser_1_power": self.Laser_1_power.text(),
            "laser_2_power": self.Laser_2_power.text(),
            "frequency": self.Frequency.text(),
            "pulse_duration": self.Pulse_duration.text(),
            "duration_each_cycle": self.Duration_each_cycle.text(),
            "interval_between_cycles": self.Interval_between_cycles.text(),
            "cycles_each_condition": self.Cycles_each_condition.text(),
        }
        # save the data 
        with open(save_file, 'w') as f:
            json.dump(self.optical_tagging_par, f, indent=4)
        
    def _Start(self):
        '''Start the optical tagging'''
        # restart the logging if it is not started
        if self.MainWindow.logging_type!=0 :
            self.MainWindow.Ot_log_folder=self.MainWindow._restartlogging()

        # toggle the button color
        if self.Start.isChecked():
            self.Start.setStyleSheet("background-color : green;")
        else:
            self.Start.setStyleSheet("background-color : none")
            return
        # generate random conditions including lasers, laser power, laser color, and protocol
        if self.cycle_finish_tag==1:
            # generate new random conditions
            self._generate_random_conditions()
            self.index=list(range(len(self.current_optical_tagging_par['protocol_sampled_all'])))
            self.cycle_finish_tag = 0

        # send the trigger source
        self.MainWindow.Channel.TriggerSource('/Dev1/PFI0')

        # start the optical tagging in a different thread
        worker_tagging = WorkerTagging(self._start_optical_tagging)
        worker_tagging.signals.update_label.connect(self.label_show_current.setText)  # Connect to label update
        worker_tagging.signals.finished.connect(self._thread_complete_tag)

        # get the first start time
        if "optical_tagging_start_time" not in self.optical_tagging_par:
            self.optical_tagging_par["optical_tagging_start_time"] = str(datetime.now())
        if self.optical_tagging_par["optical_tagging_start_time"]=='':
            self.optical_tagging_par["optical_tagging_start_time"] = str(datetime.now())

        # Execute
        if self.thread_finish_tag == 1:
            self.threadpool.start(worker_tagging)
        else:
            self.Start.setChecked(False)
            self.Start.setStyleSheet("background-color : none")
        #self._start_optical_tagging()

    def _clear_data(self):
        '''Clear the optical tagging data'''
        # ask for confirmation
        reply = QMessageBox.question(self, 'Message', 'Are you sure to clear the optical tagging data?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.cycle_finish_tag = 1
            self.Start.setChecked(False)
            self.Start.setStyleSheet("background-color : none")
            # wait for the thread to finish
            while self.thread_finish_tag == 0:
                QApplication.processEvents()
                time.sleep(0.1)
            self.optical_tagging_par={}
            self.label_show_current.setText('')
            self.LocationTag.setValue(0)

    def _start_over(self):
        '''Stop the optical tagging and start over (parameters will be shuffled)'''
        # ask for confirmation
        reply = QMessageBox.question(self, 'Message', 'Are you sure to start over the optical tagging?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.cycle_finish_tag = 1
            self.Start.setChecked(False)
            self.Start.setStyleSheet("background-color : none")

    def _thread_complete_tag(self):
        '''Complete the optical tagging'''
        self.thread_finish_tag = 1
        # Add 1 to the location tag when the cycle is finished
        if self.cycle_finish_tag == 1:
            self.LocationTag.setValue(self.LocationTag.value()+1)
        self.Start.setChecked(False)
        self.Start.setStyleSheet("background-color : none")
        # update the stop time
        self.optical_tagging_par["optical_tagging_end_time"] = str(datetime.now())
        # toggle the start button in the main window
        self.MainWindow.unsaved_data=True
        self.MainWindow.Save.setStyleSheet("color: white;background-color : mediumorchid;")

    def _start_optical_tagging(self,update_label):
        '''Start the optical tagging in a different thread'''
        self.thread_finish_tag = 0
        # iterate each condition
        for i in self.index[:]:
            if self.Start.isChecked():
                if i == self.index[-1]:
                    self.cycle_finish_tag = 1
                # exclude the index that has been run
                self.index.remove(i)
                success_tag=0
                # get the current parameters
                protocol = self.current_optical_tagging_par['protocol_sampled_all'][i]
                frequency = self.current_optical_tagging_par['frequency_sampled_all'][i]
                pulse_duration = self.current_optical_tagging_par['pulse_duration_sampled_all'][i]
                laser_name = self.current_optical_tagging_par['laser_name_sampled_all'][i]
                target_power = self.current_optical_tagging_par['target_power_sampled_all'][i]
                laser_color = self.current_optical_tagging_par['laser_color_sampled_all'][i]
                duration_each_cycle = self.current_optical_tagging_par['duration_each_cycle_sampled_all'][i]
                interval_between_cycles = self.current_optical_tagging_par['interval_between_cycles_sampled_all'][i]
                location_tag = self.current_optical_tagging_par['location_tag_sampled_all'][i]
                # produce the waveforms
                my_wave=self._produce_waveforms(protocol=protocol, 
                                                frequency=frequency, 
                                                pulse_duration=pulse_duration, 
                                                laser_name=laser_name, 
                                                target_power=target_power, 
                                                laser_color=laser_color, 
                                                duration_each_cycle=duration_each_cycle
                                            )
                my_wave_control=self._produce_waveforms(protocol=protocol,
                                                        frequency=frequency,
                                                        pulse_duration=pulse_duration,
                                                        laser_name=laser_name,
                                                        target_power=0,
                                                        laser_color=laser_color,
                                                        duration_each_cycle=duration_each_cycle
                                                    )
                if my_wave is None:
                    continue
                # send the waveform and size to the bonsai
                if laser_name=='Laser_1':
                    getattr(self.MainWindow.Channel, 'Location1_Size')(int(my_wave.size))
                    getattr(self.MainWindow.Channel4, 'WaveForm1_1')(str(my_wave.tolist())[1:-1])
                    getattr(self.MainWindow.Channel, 'Location2_Size')(int(my_wave_control.size))
                    getattr(self.MainWindow.Channel4, 'WaveForm1_2')(str(my_wave_control.tolist())[1:-1])
                elif laser_name=='Laser_2':
                    getattr(self.MainWindow.Channel, 'Location2_Size')(int(my_wave.size))
                    getattr(self.MainWindow.Channel4, 'WaveForm1_2')(str(my_wave.tolist())[1:-1])
                    getattr(self.MainWindow.Channel, 'Location1_Size')(int(my_wave_control.size))
                    getattr(self.MainWindow.Channel4, 'WaveForm1_1')(str(my_wave_control.tolist())[1:-1])
                FinishOfWaveForm=self.MainWindow.Channel4.receive() 
                # initiate the laser
                # need to change the bonsai code to initiate the laser
                self._initiate_laser()
                # receiving the timestamps of laser start and saving them. The laser waveforms should be sent to the NI-daq as a backup. 
                Rec=self.MainWindow.Channel.receive()

                if Rec[0].address=='/ITIStartTimeHarp':
                    laser_start_timestamp=Rec[1][1][0]
                    # change the success_tag to 1
                    success_tag=1
                else:
                    laser_start_timestamp=-999 # error tag

                # save the data 
                self._save_data(protocol=protocol,
                                frequency=frequency,
                                pulse_duration=pulse_duration,
                                laser_name=laser_name,
                                target_power=target_power,
                                laser_color=laser_color,
                                duration_each_cycle=duration_each_cycle,
                                interval_between_cycles=interval_between_cycles,
                                location_tag=location_tag,
                                laser_start_timestamp=laser_start_timestamp,
                                success_tag=success_tag
                            )
                # show current cycle and parameters
                # Emit signal to update the label
                update_label(
                    f"Cycles: {i+1}/{len(self.current_optical_tagging_par['protocol_sampled_all'])} \n"
                    f"Color: {laser_color}\n"
                    f"Laser: {laser_name}\n"
                    f"Power: {target_power} mW\n"
                    f"protocol: {protocol}\n"
                    f"Frequency: {frequency} Hz\n"
                    f"Pulse Duration: {pulse_duration} ms\n"
                    f"Duration: {duration_each_cycle} s\n"
                    f"Interval: {interval_between_cycles} s"
                )
                # wait to start the next cycle
                time.sleep(duration_each_cycle+interval_between_cycles)
            else:
                break

    def _save_data(self, protocol, frequency, pulse_duration, laser_name, target_power, laser_color, duration_each_cycle, interval_between_cycles, location_tag, laser_start_timestamp, success_tag):
        '''Extend the current parameters to self.optical_tagging_par'''
        if 'protocol' not in self.optical_tagging_par.keys():
            self.optical_tagging_par['protocol']=[]
            self.optical_tagging_par['frequency']=[]
            self.optical_tagging_par['pulse_duration']=[]
            self.optical_tagging_par['laser_name']=[]
            self.optical_tagging_par['target_power']=[]
            self.optical_tagging_par['laser_color']=[]
            self.optical_tagging_par['duration_each_cycle']=[]
            self.optical_tagging_par['interval_between_cycles']=[]
            self.optical_tagging_par['location_tag']=[]
            self.optical_tagging_par['laser_start_timestamp']=[]
            self.optical_tagging_par['success_tag']=[]
        else:
            self.optical_tagging_par['protocol'].append(protocol)
            self.optical_tagging_par['frequency'].append(frequency)
            self.optical_tagging_par['pulse_duration'].append(pulse_duration)
            self.optical_tagging_par['laser_name'].append(laser_name)
            self.optical_tagging_par['target_power'].append(target_power)
            self.optical_tagging_par['laser_color'].append(laser_color)
            self.optical_tagging_par['duration_each_cycle'].append(duration_each_cycle)
            self.optical_tagging_par['interval_between_cycles'].append(interval_between_cycles)
            self.optical_tagging_par['location_tag'].append(location_tag)
            self.optical_tagging_par['laser_start_timestamp'].append(laser_start_timestamp)
            self.optical_tagging_par['success_tag'].append(success_tag)

    def _initiate_laser(self):
        '''Initiate laser in bonsai'''
        # start generating waveform in bonsai
        self.MainWindow.Channel.OptogeneticsCalibration(int(1))

    def _generate_random_conditions(self):
        """
        Generate random conditions for the optical tagging process. Each condition corresponds to one cycle, with parameters randomly selected for each duration. 

        The parameters are chosen as follows:
        - **Lasers**: One of the following is selected: `Laser_1` or `Laser_2`.
        - **Laser Power**: If `Laser_1` is selected, `Laser_1_power` is used. If `Laser_2` is selected, `Laser_2_power` is used.
        - **Laser Color**: If `Laser_1` is selected, `Laser_1_color` is used. If `Laser_2` is selected, `Laser_2_color` is used.
        *Note: `Laser`, `Laser Power`, and `Laser Color` are selected together as a group.*

        Additional parameters:
        - **Protocol**: Currently supports only `Pulse`.
        - **Frequency (Hz)**: Applied to both lasers during the cycle.
        - **Pulse Duration (ms)**: Applied to both lasers during the cycle.
        """
        # get the protocol
        protocol = self.Protocol.currentText()
        if protocol!='Pulse':
            raise ValueError(f"Unknown protocol: {protocol}")
        # get the number of cycles
        number_of_cycles = int(math.floor(float(self.Cycles_each_condition.text())))
        # get the frequency
        frequency_list = list(map(int, extract_numbers_from_string(self.Frequency.text())))
        # get the pulse duration (seconds)
        pulse_duration_list = extract_numbers_from_string(self.Pulse_duration.text())
        # get the laser name
        if self.WhichLaser.currentText()=="Both":
            laser_name_list = ['Laser_1','Laser_2']
            laser_config = {
                'Laser_1': (self.Laser_1_power, self.Laser_1_color),
                'Laser_2': (self.Laser_2_power, self.Laser_2_color)
            }
        elif self.WhichLaser.currentText() in ['Laser_1','Laser_2']:
            laser_name_list = [self.WhichLaser.currentText()]
            if laser_name_list[0]=='Laser_1':
                laser_config = {
                    'Laser_1': (self.Laser_1_power, self.Laser_1_color)
                }
            elif laser_name_list[0]=='Laser_2':
                laser_config = {
                    'Laser_2': (self.Laser_2_power, self.Laser_2_color)
                }
        else:
            # give an popup error window if the laser is not selected
            QMessageBox.critical(self.MainWindow, "Error", "Please select the laser to use.")
            return
        
        # Generate combinations for each laser
        protocol_sampled, frequency_sampled, pulse_duration_sampled, laser_name_sampled, target_power_sampled, laser_color_sampled,duration_each_cycle_sampled,interval_between_cycles_sampled = zip(*[
            (protocol, frequency, pulse_duration, laser_name, target_power, laser_config[laser_name][1].currentText(),duration_each_cycle,interval_between_cycles)
            for frequency in frequency_list
            for pulse_duration in pulse_duration_list
            for laser_name, (power_field, _) in laser_config.items()
            for target_power in extract_numbers_from_string(power_field.text())
            for duration_each_cycle in extract_numbers_from_string(self.Duration_each_cycle.text())
            for interval_between_cycles in extract_numbers_from_string(self.Interval_between_cycles.text())
        ])

        self.current_optical_tagging_par['protocol_sampled_all'] = []
        self.current_optical_tagging_par['frequency_sampled_all'] = []
        self.current_optical_tagging_par['pulse_duration_sampled_all'] = []
        self.current_optical_tagging_par['laser_name_sampled_all'] = []
        self.current_optical_tagging_par['target_power_sampled_all'] = []
        self.current_optical_tagging_par['laser_color_sampled_all'] = []
        self.current_optical_tagging_par['duration_each_cycle_sampled_all'] = []
        self.current_optical_tagging_par['interval_between_cycles_sampled_all'] = []
        self.current_optical_tagging_par['location_tag_sampled_all'] = []
        for i in range(number_of_cycles):
            # Generate a random index to sample conditions
            random_indices = random.sample(range(len(protocol_sampled)), len(protocol_sampled))
            # Use the random indices to shuffle the conditions
            protocol_sampled_now = [protocol_sampled[i] for i in random_indices]
            frequency_sampled_now = [frequency_sampled[i] for i in random_indices]
            pulse_duration_sampled_now = [pulse_duration_sampled[i] for i in random_indices]
            laser_name_sampled_now = [laser_name_sampled[i] for i in random_indices]
            target_power_sampled_now = [target_power_sampled[i] for i in random_indices]
            laser_color_sampled_now = [laser_color_sampled[i] for i in random_indices]
            duration_each_cycle_sampled = [duration_each_cycle_sampled[i] for i in random_indices]
            # Append the conditions
            self.current_optical_tagging_par['protocol_sampled_all'].extend(protocol_sampled_now)
            self.current_optical_tagging_par['frequency_sampled_all'].extend(frequency_sampled_now)
            self.current_optical_tagging_par['pulse_duration_sampled_all'].extend(pulse_duration_sampled_now)
            self.current_optical_tagging_par['laser_name_sampled_all'].extend(laser_name_sampled_now)
            self.current_optical_tagging_par['target_power_sampled_all'].extend(target_power_sampled_now)
            self.current_optical_tagging_par['laser_color_sampled_all'].extend(laser_color_sampled_now)
            self.current_optical_tagging_par['duration_each_cycle_sampled_all'].extend(duration_each_cycle_sampled)
            self.current_optical_tagging_par['interval_between_cycles_sampled_all'].extend(interval_between_cycles_sampled)
            self.current_optical_tagging_par['location_tag_sampled_all'].extend([float(self.LocationTag.value())]*len(protocol_sampled))

    def _WhichLaser(self):
        '''Select the laser to use and disable non-relevant widgets'''
        laser_name = self.WhichLaser.currentText()
        if laser_name=='Laser_1':
            self.Laser_2_power.setEnabled(False)
            self.label1_16.setEnabled(False)
            self.label1_3.setEnabled(True)
            self.Laser_1_power.setEnabled(True)
        elif laser_name=='Laser_2':
            self.Laser_1_power.setEnabled(False)
            self.label1_3.setEnabled(False)
            self.label1_16.setEnabled(True)
            self.Laser_2_power.setEnabled(True)
        else:
            self.Laser_1_power.setEnabled(True)
            self.Laser_2_power.setEnabled(True)
            self.label1_3.setEnabled(True)
            self.label1_16.setEnabled(True)
    
    def _produce_waveforms(self,protocol:str,frequency:int,pulse_duration:float,laser_name:str,target_power:float,laser_color:str,duration_each_cycle:float):
        '''Produce the waveforms for the optical tagging'''
        # get the amplitude of the laser
        if target_power==0:
            # force the input_voltage to be 0 when the target_power is 0
            input_voltage=0
        else:
            input_voltage=self._get_laser_amplitude(target_power=target_power,
                                                    laser_color=laser_color,
                                                    protocol=protocol,
                                                    laser_name=laser_name
                                                )
        if input_voltage is None:
            return
        
        # produce the waveform
        my_wave=self._get_laser_waveform(protocol=protocol,
                                         frequency=frequency,
                                         pulse_duration=pulse_duration,
                                         input_voltage=input_voltage,
                                         duration_each_cycle=duration_each_cycle
                                    )
        
        return my_wave
    
    def _get_laser_waveform(self,protocol:str,frequency:int,pulse_duration:float,input_voltage:float,duration_each_cycle:float)->np.array:
        '''Get the waveform for the laser
        Args:
            protocol: The protocol to use (only 'Pulse' is supported).
            frequency: The frequency of the pulse.
            pulse_duration: The duration of the pulse.
            input_voltage: The input voltage of the laser.
        Returns:
            np.array: The waveform of the laser.
        '''
        # get the waveform
        if protocol!='Pulse':
            logger.warning(f"Unknown protocol: {protocol}")
            return
        sample_frequency=5000 # should be replaced
        PointsEachPulse=int(sample_frequency*pulse_duration/1000)
        PulseIntervalPoints=int(1/frequency*sample_frequency-PointsEachPulse)
        if PulseIntervalPoints<0:
            logging.warning('Pulse frequency and pulse duration are not compatible!',
                            extra={'tags': [self.MainWindow.warning_log_tag]})
        TotalPoints=int(sample_frequency*duration_each_cycle)
        PulseNumber=np.floor(duration_each_cycle*frequency) 
        EachPulse=input_voltage*np.ones(PointsEachPulse)
        PulseInterval=np.zeros(PulseIntervalPoints)
        WaveFormEachCycle=np.concatenate((EachPulse, PulseInterval), axis=0)
        my_wave=np.empty(0)
        # pulse number should be greater than 0
        if PulseNumber>1:
            for i in range(int(PulseNumber-1)):
                my_wave=np.concatenate((my_wave, WaveFormEachCycle), axis=0)
        else:
            logging.warning('Pulse number is less than 1!', extra={'tags': [self.MainWindow.warning_log_tag]})
            return
        my_wave=np.concatenate((my_wave, EachPulse), axis=0)
        my_wave=np.concatenate((my_wave, np.zeros(TotalPoints-np.shape(my_wave)[0])), axis=0)
        my_wave=np.append(my_wave,[0,0])
        return my_wave

    def _get_laser_amplitude(self,target_power:float,laser_color:str,protocol:str,laser_name:str)->float:
        '''Get the amplitude of the laser based on the calibraion results
        Args:
            target_power: The target power of the laser.
            laser_color: The color of the laser.
            protocol: The protocol to use.
        Returns:
            float: The amplitude of the laser.
        '''
        # get the current calibration results
        latest_calibration_date=find_latest_calibration_date(self.MainWindow.LaserCalibrationResults,laser_color)
        # get the selected laser
        if latest_calibration_date=='NA':
            logger.info(f"No calibration results found for {laser_color}")
            return
        else:
            try:
                calibration_results=self.MainWindow.LaserCalibrationResults[latest_calibration_date][laser_color][protocol][laser_name]['LaserPowerVoltage']
            except:
                logger.info(f"No calibration results found for {laser_color} and {laser_name}")
                return
        # fit the calibration results with a linear model
        slope,intercept=fit_calibration_results(calibration_results)
        # Find the corresponding input voltage for a target laser power
        input_voltage_for_target = (target_power - intercept) / slope
        return round(input_voltage_for_target, 2)
    
def fit_calibration_results(calibration_results: list) -> Tuple[float, float]:
    """
    Fit the calibration results with a linear model.

    Args:
        calibration_results: A list of calibration results where each entry is [input_voltage, laser_power].

    Returns:
        A tuple (slope, intercept) of the fitted linear model.
    """
    # Convert to numpy array for easier manipulation
    calibration_results = np.array(calibration_results)

    # Separate input voltage and laser power
    input_voltage = calibration_results[:, 0].reshape(-1, 1)  # X (features)
    laser_power = calibration_results[:, 1]  # y (target)

    # Fit the linear model
    model = LinearRegression()
    model.fit(input_voltage, laser_power)

    # Extract model coefficients
    slope = model.coef_[0]
    intercept = model.intercept_

    return slope, intercept
            
def find_latest_calibration_date(calibration:list,laser_color:str)->str:
    """
    Find the latest calibration date for the selected laser.

    Args:
        calibration: The calibration object.
        Laser: The selected laser color.

    Returns:
        str: The latest calibration date for the selected laser.
    """
    Dates=[]
    for Date in calibration:
        if laser_color in calibration[Date].keys():
            Dates.append(Date)
    sorted_dates = sorted(Dates)
    if sorted_dates==[]:
        return 'NA'
    else:
        return sorted_dates[-1]
    
def extract_numbers_from_string(input_string:str)->list:
    """
    Extract numbers from a string.

    Args:
        string: The input string.

    Returns:
        list: The list of numbers.
    """
    # Regular expression to match floating-point numbers
    float_pattern = r"[-+]?\d*\.\d+|\d+"  # Matches numbers like 0.4, -0.5, etc.
    return [float(num) for num in re.findall(float_pattern, input_string)]

class RandomRewardDialog(QDialog):
    
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        uic.loadUi('RandomReward.ui', self)
        self._connectSignalsSlots()
        self.MainWindow = MainWindow
        self.threadpool = QThreadPool()
        self.cycle_finish_tag = 1
        self.thread_finish_tag = 1
        self.random_reward_par={}
        # find all buttons and set them to not be the default button
        for container in [self]:
            for child in container.findChildren((QtWidgets.QPushButton)):     
                child.setDefault(False)
                child.setAutoDefault(False)
        self.random_reward_par['RandomWaterVolume']=[0,0]

    def _connectSignalsSlots(self):
        self.Start.clicked.connect(self._Start)
        self.Start.toggled.connect(self._enable_disable)
        self.WhichSpout.currentIndexChanged.connect(self._WhichSpout)
        self.Restart.clicked.connect(self._start_over)
        self.ClearData.clicked.connect(self._clear_data)
        self.Save.clicked.connect(self._Save)
    
    def _enable_disable(self):
        """
        Enables or disables the 'GiveLeft' and 'GiveRight' buttons based on the state of the 'Start' button.

        When 'Start' is checked (active), 'GiveLeft' and 'GiveRight' buttons are disabled.
        When 'Start' is unchecked (inactive), 'GiveLeft' and 'GiveRight' buttons are enabled.

        This prevents users from manually triggering left or right rewards while a session is running.

        Returns:
            None
        """
        # Disable 'GiveLeft' and 'GiveRight' when 'Start' is checked (active)
        # Enable them when 'Start' is unchecked (inactive)
        self.MainWindow.GiveLeft.setEnabled(not self.Start.isChecked())
        self.MainWindow.GiveRight.setEnabled(not self.Start.isChecked())

    def _Save(self):
        '''Save the random reward results'''
        if self.random_reward_par=={}:
            return
        # giving the user a warning message to show "This will only save the current parameters and results related to the random reward. If you want to save more including the metadata, please go to the main window and click the save button."
        QMessageBox.warning(
            self,
            "Save Warning",
            "Only the current parameters and results related to the random reward will be saved. "
            "To save additional data, including metadata, please use the Save button in the main window."
        )
        # get the save folder
        if self.MainWindow.CreateNewFolder == 1:
            self.MainWindow._GetSaveFolder()
            self.MainWindow.CreateNewFolder = 0

        save_file=self.MainWindow.SaveFileJson
        if not os.path.exists(os.path.dirname(save_file)):
            os.makedirs(os.path.dirname(save_file))
            logging.info(f"Created new folder: {os.path.dirname(save_file)}")

        self.random_reward_par['task_parameters'] = {
            'task': 'Random reward',
            'spout': self.WhichSpout.currentText(),
            'left_reward_volume': self.LeftVolume.text(),
            'right_reward_volume': self.RightVolume.text(),
            'reward_number_each_condition': self.RewardN.text(),
            'interval_distribution': self.IntervalDistribution.currentText(),
            'interval_beta': self.IntervalBeta.text(),
            'interval_min': self.IntervalMin.text(),
            'interval_max': self.IntervalMax.text(),
        }

        # save the data in the standard format and folder
        with open(save_file, 'w') as f:
            json.dump(self.random_reward_par, f, indent=4)

    def _clear_data(self):
        '''Clear the data'''
        # ask user if they want to clear the data
        reply = QMessageBox.question(self, 'Message', 'Do you want to clear the data?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.cycle_finish_tag = 1
            self.Start.setChecked(False)
            self.Start.setStyleSheet("background-color : none")
            # wait for the thread to finish
            while self.thread_finish_tag == 0:
                QApplication.processEvents()
                time.sleep(0.1)
            self.random_reward_par={}
            self.random_reward_par['RandomWaterVolume']=[0,0]
            self.label_show_current.setText('')

    def _start_over(self):
        '''Stop the random reward and start over (parameters will be shuffled)'''
        # ask user if they want to start over
        reply = QMessageBox.question(self, 'Message', 'Do you want to start over?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.cycle_finish_tag = 1
            self.Start.setChecked(False)
            self.Start.setStyleSheet("background-color : none")
        else:
            return

    def _Start(self):
        '''Start giving random rewards'''
        # restart the logging if it is not started
        if self.MainWindow.logging_type!=0 :
            self.MainWindow.Ot_log_folder=self.MainWindow._restartlogging()

        # toggle the button color
        if self.Start.isChecked():
            self.Start.setStyleSheet("background-color : green;")
        else:
            self.Start.setStyleSheet("background-color : none")
            return
        # generate random conditions including lick spouts, reward volume, and reward interval
        if self.cycle_finish_tag==1:
            # generate new random conditions
            self._generate_random_conditions()
            self.index=list(range(len(self.current_random_reward_par['volumes_all_random'])))
            self.cycle_finish_tag = 0

        # start the random reward in a different thread
        worker_random_reward = WorkerTagging(self._start_random_reward)
        worker_random_reward.signals.update_label.connect(self.label_show_current.setText)  # Connect to label update
        worker_random_reward.signals.finished.connect(self._thread_complete_tag)

        # get the first start time
        if "random_reward_start_time" not in self.random_reward_par:
            self.random_reward_par["random_reward_start_time"] = str(datetime.now())
        if self.random_reward_par["random_reward_start_time"]=='':
            self.random_reward_par["random_reward_start_time"] = str(datetime.now())

        # Execute
        if self.thread_finish_tag==1:
            self.threadpool.start(worker_random_reward)
        else:
            self.Start.setChecked(False)
            self.Start.setStyleSheet("background-color : none")

    def _start_random_reward(self,update_label):
        '''Start the random reward in a different thread'''
        if self.thread_finish_tag==0:
            self.Start.setChecked(False)
            self.Start.setStyleSheet("background-color : none")
            return
        # iterate each condition
        self.thread_finish_tag = 0
        for i in self.index[:]:
            if self.Start.isChecked():
                if i == self.index[-1]:
                    self.cycle_finish_tag = 1
                # exclude the index that has been run
                # check if i is in the index
                if i in self.index:
                    self.index.remove(i)
                else:
                    continue
                # get the current parameters
                volume = self.current_random_reward_par['volumes_all_random'][i]
                side = self.current_random_reward_par['sides_all_random'][i]
                interval = self.current_random_reward_par['reward_intervals'][i]
                # get all licks
                self._get_lick_timestampes()
                # give the reward
                self._give_reward(volume=volume, side=side)
                # receiving the timestamps of reward start time. 
                reward_start_timestamp_computer, reward_start_timestamp_harp=self._receiving_timestamps(side=side)
                # save the data 
                self._save_data(volume=volume, side=side, interval=interval,timestamp_computer=reward_start_timestamp_computer,timestamp_harp=reward_start_timestamp_harp)
                # show current cycle and parameters
                # Emit signal to update the label
                if side==0:
                    side_spout='Left'
                elif side==1:
                    side_spout='Right'
                update_label(
                    f"Cycles: {i+1}/{len(self.current_random_reward_par['volumes_all_random'])} \n"
                    f"Volume: {volume} uL\n"
                    f"Side: {side_spout}\n"
                    f"Interval: {interval} s"
                )
                # wait to start the next cycle (minus 0.2s to account for the delay to wait for the value to be set)
                time.sleep(interval-0.2)
                if self.CheckRewardCollection.currentText()=='Yes':
                    # check if the reward has been collected by the animal
                    received_licks=self._get_lick_timestampes(side=side)
                    sleep_again=0
                    if not received_licks:
                        sleep_again=1
                        # show the licks have not been received
                        update_label(
                            f"Cycles: {i+1}/{len(self.current_random_reward_par['volumes_all_random'])} \n"
                            f"Volume: {volume} uL\n"
                            f"Side: {side_spout}\n"
                            f"Interval: {interval} s\n"
                            f"Reward not collected"
                        )
                    else:
                        continue
                    # if not received any licks, sleep until we receive a lick
                    while (not received_licks) and self.Start.isChecked():
                        time.sleep(0.01)
                        received_licks=self._get_lick_timestampes(side=side)
                    if not self.Start.isChecked():
                        update_label(
                            f"Cycles: {i+1}/{len(self.current_random_reward_par['volumes_all_random'])} \n"
                            f"Volume: {volume} uL\n"
                            f"Side: {side_spout}\n"
                            f"Interval: {interval} s\n"
                            f"User stopped"
                        )
                    else:
                        update_label(
                            f"Cycles: {i+1}/{len(self.current_random_reward_par['volumes_all_random'])} \n"
                            f"Volume: {volume} uL\n"
                            f"Side: {side_spout}\n"
                            f"Interval: {interval} s\n"
                            f"Reward collected"
                        )
                        if sleep_again==1:
                            # sleep another interval-0.2s when detected a lick
                            time.sleep(interval-0.2)
            else:
                break
    
    def _get_lick_timestampes(self,side=None)->bool:
        '''Get the lick timestamps'''
        if 'left_lick_time' not in self.random_reward_par:
            self.random_reward_par['left_lick_time'] = []
            self.random_reward_par['right_lick_time'] = []

        Return = False # no licks received
        while not self.MainWindow.Channel2.msgs.empty():
            Rec = self.MainWindow.Channel2.receive()
            address = Rec[0].address
            lick_time = Rec[1][1][0]

            if address == '/LeftLickTime':
                self.random_reward_par['left_lick_time'].append(lick_time)
                if side==0:
                    Return = True # left licks received
            elif address == '/RightLickTime':
                self.random_reward_par['right_lick_time'].append(lick_time)
                if side==1:
                    Return = True # right licks received
        return Return
            
    def _receiving_timestamps(self, side: int):
        """Receives the timestamps of reward start time from OSC messages.

        Ensures both '/RandomLeftWaterStartTime' and '/LeftRewardDeliveryTimeHarp' 
        are received before returning when side == 0, and both '/RandomRightWaterStartTime' and
        '/RightRewardDeliveryTimeHarp' are received before returning when side == 1.
        
        Args:
            side (int): 0 for left, 1 for right.
        
        Returns:
            tuple: (random water start time, reward delivery time harp)
        """
        if side == 0:
            random_left_water_start_time = None
            random_left_reward_delivery_time_harp = None

            while random_left_water_start_time is None or random_left_reward_delivery_time_harp is None:
                Rec = self.MainWindow.Channel2.receive()
                if Rec[0].address == '/RandomLeftWaterStartTime':
                    random_left_water_start_time = Rec[1][1][0]
                elif Rec[0].address == '/LeftRewardDeliveryTimeHarp':
                    random_left_reward_delivery_time_harp = Rec[1][1][0]

            return random_left_water_start_time, random_left_reward_delivery_time_harp

        elif side == 1:
            random_right_water_start_time = None
            random_right_reward_delivery_time_harp = None

            while random_right_water_start_time is None or random_right_reward_delivery_time_harp is None:
                Rec = self.MainWindow.Channel2.receive()
                if Rec[0].address == '/RandomRightWaterStartTime':
                    random_right_water_start_time = Rec[1][1][0]
                elif Rec[0].address == '/RightRewardDeliveryTimeHarp':
                    random_right_reward_delivery_time_harp = Rec[1][1][0]

            return random_right_water_start_time, random_right_reward_delivery_time_harp


    def _save_data(self, volume:float, side:int, interval:float, timestamp_computer:float, timestamp_harp:float):
        '''Extend the current parameters to self.random_reward_par'''
        if 'volumes' not in self.random_reward_par.keys():
            self.random_reward_par['volumes']=[]
            self.random_reward_par['sides']=[]
            self.random_reward_par['intervals']=[]
            self.random_reward_par['reward_start_timestamp_computer']=[]
            self.random_reward_par['reward_start_timestamp_harp']=[]
        else:
            self.random_reward_par['volumes'].append(volume)
            self.random_reward_par['sides'].append(side)
            self.random_reward_par['intervals'].append(interval)
            self.random_reward_par['reward_start_timestamp_computer'].append(timestamp_computer)
            self.random_reward_par['reward_start_timestamp_harp'].append(timestamp_harp)

    def _thread_complete_tag(self):
        '''Complete the random reward'''
        self.thread_finish_tag = 1
        self.Start.setChecked(False)
        self.Start.setStyleSheet("background-color : none")
        # update the stop time
        self.random_reward_par["random_reward_end_time"] = str(datetime.now())
        # update the reward suggestion
        self.MainWindow._UpdateSuggestedWater()

    def _give_reward(self,volume:float,side:int):
        '''Give the reward'''
        if side==0:
            left_valve_open_time=((float(volume)-self.MainWindow.latest_fitting['Left'][1])/self.MainWindow.latest_fitting['Left'][0])*1000
            # set the left valve open time
            self.MainWindow.Channel.LeftValue(float(left_valve_open_time))
            # add 0.2s for the value to be set
            time.sleep(0.2)
            # open the left valve (adding 0.2s for the value to be set)
            self.MainWindow.Channel3.RandomWater_Left(int(1))
            self.random_reward_par['RandomWaterVolume'][0]=self.random_reward_par['RandomWaterVolume'][0]+float(volume)/1000
        elif side==1:
            right_valve_open_time=((float(volume)-self.MainWindow.latest_fitting['Right'][1])/self.MainWindow.latest_fitting['Right'][0])*1000
            # set the right valve open time 
            self.MainWindow.Channel.RightValue(float(right_valve_open_time))
            # add 0.2s for the value to be set
            time.sleep(0.2)
            # open the left valve (adding 0.2s for the value to be set)
            self.MainWindow.Channel3.RandomWater_Right(int(1))
            self.random_reward_par['RandomWaterVolume'][1]=self.random_reward_par['RandomWaterVolume'][1]+float(volume)/1000

    def _WhichSpout(self):
        '''Select the lick spout to use and disable non-relevant widgets'''
        spout_name = self.WhichSpout.currentText()
        if spout_name=='Left':
            self.label1_21.setEnabled(False)
            self.RightVolume.setEnabled(False)
            self.label1_6.setEnabled(True)
            self.LeftVolume.setEnabled(True)
        elif spout_name=='Right':
            self.label1_6.setEnabled(False)
            self.LeftVolume.setEnabled(False)
            self.label1_21.setEnabled(True)
            self.RightVolume.setEnabled(True)
        else:
            self.label1_6.setEnabled(True)
            self.LeftVolume.setEnabled(True)
            self.label1_21.setEnabled(True)
            self.RightVolume.setEnabled(True)

    def _generate_random_conditions(self):
        """
        Generate random conditions

        The parameters are chosen as follows:
        - **Lick Spouts**: One of the following is selected: `Left`, `Right`, or `Both`.
        - **Reward Volume**: If `Left` is selected, `LeftVolume` is used. If `Right` is selected, `RightVolume` is used.
        - **Reward Interval**: The interval between rewards.
        """
        # Get the volume and reward sides
        spout_name = self.WhichSpout.currentText()

        if spout_name == 'Both':
            # Extract volumes from left and right spouts
            left_volumes = extract_numbers_from_string(self.LeftVolume.text())
            right_volumes = extract_numbers_from_string(self.RightVolume.text())
            volumes = left_volumes + right_volumes  # Combine into a single list

            # Create sides: 0 for left, 1 for right
            sides = np.zeros(len(left_volumes)).tolist() + np.ones(len(right_volumes)).tolist()

        elif spout_name == 'Left':
            # Extract volumes and assign sides for left spout
            volumes = extract_numbers_from_string(self.LeftVolume.text())
            sides = np.zeros(len(volumes)).tolist()  # 0 for left

        elif spout_name == 'Right':
            # Extract volumes and assign sides for right spout
            volumes = extract_numbers_from_string(self.RightVolume.text())
            sides = np.ones(len(volumes)).tolist()  # 1 for right

        else:
            # Popup error if spout is not selected or invalid input
            QMessageBox.critical(self.MainWindow, "Error", "Please select a valid lick spout.")
            return

        # get all rewards
        volumes_all = volumes*int(self.RewardN.value())
        sides_all = sides*int(self.RewardN.value())

        # randomize the rewards and sides
        random_indices = random.sample(range(len(volumes_all)), len(volumes_all))
        volumes_all_random = [volumes_all[i] for i in random_indices]
        sides_all_random = [sides_all[i] for i in random_indices]

        # get the reward interval
        if self.IntervalDistribution.currentText() == "Exponential":
            reward_intervals = np.random.exponential(float(self.IntervalBeta.text()), len(volumes_all_random))+float(self.IntervalMin.text())
            if self.IntervalMax.text()!='':
                reward_intervals = np.minimum(reward_intervals,float(self.IntervalMax.text()))
            # keep one decimal
            reward_intervals = np.round(reward_intervals,1)
        elif self.IntervalDistribution.currentText() == "Uniform":
            reward_intervals = np.random.uniform(float(self.IntervalMin.text()), float(self.IntervalMax.text()), len(volumes_all_random))
            # keep one decimal
            reward_intervals = np.round(reward_intervals,1)

        # save the data
        self.current_random_reward_par={}
        self.current_random_reward_par['volumes_all_random']=volumes_all_random
        self.current_random_reward_par['sides_all_random']=sides_all_random
        self.current_random_reward_par['reward_intervals']=reward_intervals


        

        
        
