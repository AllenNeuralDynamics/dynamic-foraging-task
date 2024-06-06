import time
import math
import json
import os
import shutil
import subprocess
from datetime import datetime
import logging
import webbrowser

import numpy as np
import pandas as pd
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QMessageBox 
from PyQt5.QtWidgets import QLabel, QDialogButtonBox,QFileDialog,QInputDialog, QLineEdit
from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtCore import QThreadPool,Qt, QAbstractTableModel, QItemSelectionModel, QObject, QEvent
from PyQt5.QtSvg import QSvgWidget

from foraging_gui.MyFunctions import Worker
from foraging_gui.Visualization import PlotWaterCalibration
from aind_auto_train.curriculum_manager import CurriculumManager
from aind_auto_train.auto_train_manager import DynamicForagingAutoTrainManager
from aind_auto_train.schema.task import TrainingStage

from aind_auto_train.schema.curriculum import DynamicForagingCurriculum
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
        
        msg = QLabel('Enter the Mouse ID: ')
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
        self.condition_idx = [1, 2, 3, 4] # corresponding to optogenetics condition 1, 2, 3, 4
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
                        self.MainWindow.WarningLabel.setText('')
                        self.MainWindow.WarningLabel.setStyleSheet("color: gray;")
                    else:
                        no_calibration=True
                else:
                    no_calibration=True
            else:
                no_calibration=True

            if no_calibration:
                for laser_tag in self.laser_tags:
                    getattr(self, f"Laser{laser_tag}_power_{str(Numb)}").clear()
                    self.MainWindow.WarningLabel.setText('No calibration for this protocol identified!')
                    self.MainWindow.WarningLabel.setStyleSheet(self.MainWindow.default_warning_color)

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
        self.Warning.setStyleSheet(self.MainWindow.default_warning_color)

    def _connectSignalsSlots(self):
        self.SpotCheckLeft.clicked.connect(self._SpotCheckLeft)
        self.SpotCheckRight.clicked.connect(self._SpotCheckRight)
        self.OpenLeftForever.clicked.connect(self._OpenLeftForever)
        self.OpenRightForever.clicked.connect(self._OpenRightForever)
        self.SaveLeft.clicked.connect(self._SaveLeft)
        self.SaveRight.clicked.connect(self._SaveRight)
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
        self.Continue.setStyleSheet("background-color : none")
        self.Repeat.setStyleSheet("background-color : none")
        self.Finished.setStyleSheet("background-color : none")
        self.StartCalibratingLeft.setStyleSheet("background-color : none")
        self.StartCalibratingRight.setStyleSheet("background-color : none")
        self.StartCalibratingLeft.setChecked(False)
        self.StartCalibratingRight.setChecked(False)
        self.StartCalibratingLeft.setEnabled(True)
        self.StartCalibratingRight.setEnabled(True)
        self.Warning.setText('Calibration Finished')
        self.Warning.setStyleSheet(self.MainWindow.default_warning_color)

 
    def _Continue(self):
        '''Change the color of the continue button'''
        self.Continue.setStyleSheet("background-color : none")
        logging.info('Continue pressed')
        if self.calibrating_left:
            self._CalibrateLeftOne()
        if self.calibrating_right:
            self._CalibrateRightOne()

    def _Repeat(self):
        '''Change the color of the continue button'''
        self.Repeat.setStyleSheet("background-color : none")
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

    def _SaveLeft(self):
        '''save the calibration result of the single point calibration (left valve)'''
        self.SaveLeft.setStyleSheet("background-color : green;")
        QApplication.processEvents()
        
        # DEBUG, check if self.SpotLeftFinished ==1 
        valve='SpotLeft'
        valve_open_time=str(self.SpotLeftOpenTime)
        try:
            total_water=float(self.TotalWaterSingleLeft.text())  
        except Exception as e:
            total_water=''
            logging.error(str(e))
        self._Save(
            valve=valve,
            valve_open_time=valve_open_time,
            valve_open_interval=self.SpotInterval,
            cycle=self.SpotCycle,
            total_water=total_water,
            tube_weight=0) ##DEBUG, why is this 0?
        self.SaveLeft.setStyleSheet("background-color : none")
        self.SaveLeft.setChecked(False)

    def _SaveRight(self):
        '''save the calibration result of the single point calibration (right valve)'''
        self.SaveRight.setStyleSheet("background-color : green;")
        QApplication.processEvents()
        valve='SpotRight'
        valve_open_time=str(self.SpotRightOpenTime)
        try:
            total_water=float(self.TotalWaterSingleRight.text()) 
        except Exception as e:
            total_water=''
            logging.error(str(e))
        self._Save(
            valve=valve,
            valve_open_time=valve_open_time,
            valve_open_interval=self.SpotInterval,
            cycle=self.SpotCycle,
            total_water=total_water,
            tube_weight=0
            )
        self.SaveRight.setStyleSheet("background-color : none")
        self.SaveRight.setChecked(False)

    def _LoadCalibrationParameters(self):
        self.WaterCalibrationPar={}       
        if os.path.exists(self.MainWindow.WaterCalibrationParFiles):
            with open(self.MainWindow.WaterCalibrationParFiles, 'r') as f:
                self.WaterCalibrationPar = json.load(f)
            logging.info('loaded water calibration parameters')
        else:
            logging.error('could not find water calibration parameters: {}'.format(self.MainWindow.WaterCalibrationParFiles))
            raise Exception('Missing water calibration parameter file: {}'.format(self.MainWindow.WaterCalibrationParFiles))

        self.SpotCycle = float(self.WaterCalibrationPar['Spot']['Cycle'])
        self.SpotInterval = float(self.WaterCalibrationPar['Spot']['Interval'])

        # if no parameters are stored, store default parameters
        if 'Full' not in self.WaterCalibrationPar:
            self.WaterCalibrationPar['Full']['TimeMin']=0.005
            self.WaterCalibrationPar['Full']['TimeMax']=0.08
            self.WaterCalibrationPar['Full']['Stride']=0.005
            self.WaterCalibrationPar['Full']['Interval']=0.05

    def _StartCalibratingLeft(self):
        '''start the calibration loop of left valve'''
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            self.StartCalibratingLeft.setChecked(False)
            self.StartCalibratingLeft.setStyleSheet("background-color : none")
            self.Warning.setText('Calibration was terminated!')
            self.Warning.setStyleSheet(self.MainWindow.default_warning_color)
            self.StartCalibratingRight.setEnabled(True)
            self.WeightAfterRight.setEnabled(True)
            self.WeightBeforeRight.setEnabled(True)
            return

        if self.StartCalibratingLeft.isChecked():
            # change button color
            self.StartCalibratingLeft.setStyleSheet("background-color : green;")
            QApplication.processEvents()
            # disable the right valve calibration
            self.StartCalibratingRight.setEnabled(False)
            self.WeightAfterRight.setEnabled(False)
            self.WeightBeforeRight.setEnabled(False)
        else:
            self.StartCalibratingLeft.setChecked(True)
            self._Finished()
            return

        # Get Calibration parameters
        params = self.WaterCalibrationPar[self.CalibrationType.currentText()]

        # Populate options for calibrations
        self.left_opentimes = np.arange(float(params['TimeMin']),float(params['TimeMax'])+0.0001,float(params['Stride']))
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

        # Determine what valve time we are measuring
        if not repeat: 
            if np.all(self.left_measurements):
                self.Warning.setText('All measurements have been completed. Either press Repeat, or Finished')
                return
            next_index = np.where(self.left_measurements != True)[0][0]
            self.LeftOpenTime.setCurrentIndex(next_index)
        else:
            next_index = self.LeftOpenTime.getCurrentIndex()
        logging.info('Calibrating left: {}'.format(self.left_opentimes[next_index])) 
 
        # Shuffle weights
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
              0,1000,2)
        if not ok:
            # User cancels
            self.Warning.setText('Press Continue, Repeat, or Finished')
            return

        current_valve_opentime = self.left_opentimes(next_index)
        for i in range(int(params['Cycle'])):
            QApplication.processEvents()
            if (not self.EmergencyStop.isChecked()):
                self._CalibrationStatus(
                    float(current_valve_opentime), 
                    self.WeightBeforeLeft.text(),
                    i,params['Cycle'], float(params['Interval'])
                    )

                # set the valve open time
                ## DEBUGGING ##self.MainWindow.Channel.LeftValue(float(self.SpotLeftOpenTime.text())*1000) 
                # open the valve
                ## DEBUGGING ##self.MainWindow.Channel3.ManualWater_Left(int(1))
                # delay
                time.sleep(current_valve_opentime+float(params['Interval']))
            else:
                self.Warning.setText('Calibration cancelled')
                self.WeightBeforeLeft.setText('')
                self.WeightAfterLeft.setText('')
                self.Repeat.setStyleSheet("color: white;background-color : mediumorchid;")
                self.Continue.setStyleSheet("color: black;background-color : none;")
                return

        # Prompt for weight
        final_tube_weight = 0.0
        final_tube_weight, ok = QInputDialog().getDouble(
            self,
            'Box {}, Left'.format(self.MainWindow.box_letter),
            "Weight after (g): ", 
            final_tube_weight,
            0, 1000, 2)
        if not ok:
            self.Warning.setText('Calibration cancelled')
            self.WeightBeforeLeft.setText('')
            self.WeightAfterLeft.setText('')
            self.Repeat.setStyleSheet("color: white;background-color : mediumorchid;")
            self.Continue.setStyleSheet("color: black;background-color : none;")
            return

        self.WeightAfterLeft.setText(str(final_tube_weight))

        self.left_measurements[next_index] = True
        self._Save(
            valve='Left',
            valve_open_time=current_valve_opentime,
            valve_open_interval=params['Interval'],
            cycle=params['Cycle'],
            total_water=float(self.WeightAfterLeft.text()),
            tube_weight=float(self.WeightBeforeLeft.text())
            )
        self._UpdateFigure()
 
        
    def _CalibrationStatus(self,opentime, weight_before, i, cycle, interval):
        self.Warning.setText(
            'Measuring left valve: {}s'.format(opentime) + \
            '\nEmpty tube weight: {}g'.format(weight_before) + \
            '\nCurrent cycle: '+str(i+1)+'/{}'.format(int(cycle)) + \
            '\nTime remaining: {}'.format(self._TimeRemaining(
                i,cycle,opentime,interval))
            )
        self.Warning.setStyleSheet(self.MainWindow.default_warning_color)



    #def _StartCalibratingLeft_v1(self):
    #    if True:
    #        N=N+1
    #        if N==1:
    #            # disable TubeWeightRight
    #            self.TubeWeightLeft.setEnabled(False)
    #            if self.TubeWeightLeft.text()!='':
    #                self.WeightBeforeLeft.setText(self.TubeWeightLeft.text())
    #            self.TubeWeightLeft.setText('')
    #        else:
    #            # enable TubeWeightRight
    #            self.TubeWeightLeft.setEnabled(True)
    #        while 1:
    #            if not self.StartCalibratingLeft.isChecked():
    #                break
    #            if self.Continue.isChecked():
    #                # start the open/close/delay cycle
    #                for i in range(int(self.CycleCaliLeft.text())):
    #                    QApplication.processEvents()
    #                    while 1:
    #                        QApplication.processEvents()
    #                        if (not self.EmergencyStop.isChecked()) or (not self.StartCalibratingLeft.isChecked()):
    #                            break
    #                    if self.StartCalibratingLeft.isChecked():
    #                        # print the current calibration value
    #                        self.Warning.setText('You are calibrating Left valve: '+ str(round(float(current_valve_opentime),4))+'   Current cycle:'+str(i+1)+'/'+self.CycleCaliLeft.text())
    #                        self.Warning.setStyleSheet(self.MainWindow.default_warning_color)
    #                        # set the valve open time
    #                        ## DEBUGGING ##self.MainWindow.Channel.LeftValue(float(current_valve_opentime)*1000) 
    #                        # open the valve
    #                        ## DEBUGGING ##self.MainWindow.Channel3.ManualWater_Left(int(1))
    #                        # delay
    #                        time.sleep(current_valve_opentime+float(self.IntervalLeft_2.text()))
    #                    else:
    #                        break
    #            self.Continue.setChecked(False)
    #            self.Continue.setStyleSheet("background-color : none")
    #            if i==range(int(self.CycleCaliLeft.text()))[-1]:
    #                self.Warning.setText('Finish calibrating left valve: '+ str(round(float(current_valve_opentime),4))+'\nPlease enter the \"weight after(mg)\" and click the \"Continue\" button to start calibrating the next value.\nOr enter a negative value to repeat the current calibration.')
    #            self.Warning.setStyleSheet(self.MainWindow.default_warning_color)
    #            self.TubeWeightLeft.setEnabled(True)
    #            self.label_26.setEnabled(True)
    #            # Waiting for the continue button to be clicked
    #            continuetag=1
    #            while 1:
    #                QApplication.processEvents()
    #                if not self.StartCalibratingLeft.isChecked():
    #                    break
    #                if self.Continue.isChecked():
    #                    # save the calibration data after the current calibration is completed
    #                    if i==range(int(self.CycleCaliLeft.text()))[-1]:
    #                        # save the data
    #                        valve='Left'
    #                        valve_open_time=str(round(float(current_valve_opentime),4))
    #                        valve_open_interval=str(round(float(self.IntervalLeft_2.text()),4))
    #                        cycle=str(int(self.CycleCaliLeft.text()))
    #                        if self.WeightAfterLeft.text()=='':
    #                            self.Warning.setText('Please enter the measured \"weight after(mg)\" and click the continue button again!\nOr enter a negative value to repeat the current calibration.')
    #                            continuetag=0
    #                            self.Continue.setChecked(False)
    #                            self.Continue.setStyleSheet("background-color : none")
    #                        else:
    #                            try:
    #                                continuetag=1
    #                                total_water=float(self.WeightAfterLeft.text())
    #                                tube_weight=self.WeightBeforeLeft.text()
    #                                if tube_weight=='':
    #                                    tube_weight=0
    #                                else:
    #                                    tube_weight=float(tube_weight)
    #                                if total_water>=0:
    #                                    self._Save(valve=valve,valve_open_time=valve_open_time,valve_open_interval=valve_open_interval,cycle=cycle,total_water=total_water,tube_weight=tube_weight)
    #                                # clear the weight before/tube/weight after
    #                                self.WeightAfterLeft.setText('')
    #                                if self.TubeWeightLeft.text()=='':
    #                                    self.WeightBeforeLeft.setText(str(total_water))
    #                                else:
    #                                    self.WeightBeforeLeft.setText(self.TubeWeightLeft.text())
    #                                self.TubeWeightLeft.setText('')
    #                            except Exception as e:
    #                                logging.error(str(e))
    #                                continuetag=0
    #                                self.Warning.setText('Please enter the correct weight after(mg)/weight before(mg) and click the continue button again!\nOr enter a negative value to repeat the current calibration.')
    #                    if continuetag==1:
    #                        break
    #            # Repeat current calibration when negative value is entered
    #            QApplication.processEvents()
    #            try:
    #                if total_water=='' or total_water<=0:
    #                    pass
    #                else:
    #                    break
    #            except Exception as e:
    #                logging.error(str(e))
    #                break
    #    try: 
    #        # calibration complete indication
    #        if self.StartCalibratingLeft.isChecked() and current_valve_opentime==np.arange(float(self.TimeLeftMin.text()),float(self.TimeLeftMax.text())+0.0001,float(self.StrideLeft.text()))[-1]:
    #            self.Warning.setText('Calibration is complete!')
    #            self._UpdateFigure()
    #    except Exception as e:
    #        logging.error(str(e))
    #        self.Warning.setText('Calibration is not complete! Parameters error!')
    #        self.Warning.setStyleSheet(self.MainWindow.default_warning_color)
    #    # set the default valve open time
    #    ## DEBUGGING ##self.MainWindow.Channel.LeftValue(float(self.MainWindow.LeftValue.text())*1000)
    #    # enable the right valve calibration
    #    self.StartCalibratingRight.setEnabled(True)
    #    self.label_15.setEnabled(True)
    #    self.label_14.setEnabled(True)
    #    self.label_17.setEnabled(True)
    #    self.label_18.setEnabled(True)
    #    self.label_22.setEnabled(True)
    #    self.label_13.setEnabled(True)
    #    self.label_16.setEnabled(True)
    #    self.label_25.setEnabled(True)
    #    self.TimeRightMin.setEnabled(True)
    #    self.TimeRightMax.setEnabled(True)
    #    self.StrideRight.setEnabled(True)
    #    self.CycleCaliRight.setEnabled(True)
    #    self.IntervalRight_2.setEnabled(True)
    #    self.WeightAfterRight.setEnabled(True)
    #    self.WeightBeforeRight.setEnabled(True) 
    #    self.label_27.setEnabled(True)
    #    self.TubeWeightRight.setEnabled(True)
    #    # change the color to be normal
    #    self.StartCalibratingLeft.setStyleSheet("background-color : none")
    #    self.StartCalibratingLeft.setChecked(False)

    def _StartCalibratingRight(self):
        '''start the calibration loop of right valve'''
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        if self.StartCalibratingRight.isChecked():
            # change button color
            self.StartCalibratingRight.setStyleSheet("background-color : green;")
            QApplication.processEvents()
            # disable the left valve calibration
            self.StartCalibratingLeft.setEnabled(False)
            self.label_9.setEnabled(False)
            self.label_10.setEnabled(False)
            self.label_11.setEnabled(False)
            self.label_12.setEnabled(False)
            self.label_23.setEnabled(False)
            self.label_13.setEnabled(False)
            self.label_24.setEnabled(False)
            self.label_26.setEnabled(False)
            self.TimeLeftMin.setEnabled(False)
            self.TimeLeftMax.setEnabled(False)
            self.StrideLeft.setEnabled(False)
            self.CycleCaliLeft.setEnabled(False)
            self.IntervalLeft_2.setEnabled(False)
            self.WeightAfterLeft.setEnabled(False)
            self.WeightBeforeLeft.setEnabled(False)
            # check the continue button
            self.Continue.setChecked(True)
            self.Continue.setStyleSheet("background-color : green;")
        else:
            self.StartCalibratingRight.setStyleSheet("background-color : none")
            self.Warning.setText('Calibration was terminated!')
            self.Warning.setStyleSheet(self.MainWindow.default_warning_color)
        N=0
        for current_valve_opentime in np.arange(float(self.TimeRightMin.text()),float(self.TimeRightMax.text())+0.0001,float(self.StrideRight.text())):
            N=N+1
            if N==1:
                # disable TubeWeightRight
                self.label_27.setEnabled(False)
                if self.TubeWeightRight.text()!='':
                    self.WeightBeforeRight.setText(self.TubeWeightRight.text())
                self.TubeWeightRight.setText('')
            else:
                # enable TubeWeightRight
                self.TubeWeightRight.setEnabled(True)
                self.label_27.setEnabled(True)
            while 1:
                QApplication.processEvents()
                if not self.StartCalibratingRight.isChecked():
                    break
                if self.Continue.isChecked():
                    # start the open/close/delay cycle
                    for i in range(int(self.CycleCaliRight.text())):
                        QApplication.processEvents()
                        while 1:
                            QApplication.processEvents()
                            if (not self.EmergencyStop.isChecked()) or (not self.StartCalibratingRight.isChecked()):
                                break
                        if self.StartCalibratingRight.isChecked():
                            # print the current calibration value
                            self.Warning.setText('You are calibrating Right valve: '+ str(round(float(current_valve_opentime),4))+'   Current cycle:'+str(i+1)+'/'+self.CycleCaliRight.text())
                            self.Warning.setStyleSheet(self.MainWindow.default_warning_color)
                            # set the valve open time
                            ## DEBUGGING ##self.MainWindow.Channel.RightValue(float(current_valve_opentime)*1000) 
                            # open the valve
                            ## DEBUGGING ##self.MainWindow.Channel3.ManualWater_Right(int(1))
                            # delay
                            time.sleep(current_valve_opentime+float(self.IntervalRight_2.text()))
                        else:
                            break
                self.Continue.setChecked(False)
                self.Continue.setStyleSheet("background-color : none")
                if i==range(int(self.CycleCaliRight.text()))[-1]:
                    self.Warning.setText('Finish calibrating Right valve: '+ str(round(float(current_valve_opentime),4))+'\nPlease enter the \"weight after(mg)\" and click the \"Continue\" button to start calibrating the next value.\nOr enter a negative value to repeat the current calibration.')
                    self.Warning.setStyleSheet(self.MainWindow.default_warning_color)
                self.TubeWeightRight.setEnabled(True)
                self.label_27.setEnabled(True)
                # Waiting for the continue button to be clicked
                continuetag=1
                while 1:
                    QApplication.processEvents()
                    if not self.StartCalibratingRight.isChecked():
                        break
                    if self.Continue.isChecked():
                        # save the calibration data after the current calibration is completed
                        if i==range(int(self.CycleCaliRight.text()))[-1]:
                            # save the data
                            valve='Right'
                            valve_open_time=str(round(float(current_valve_opentime),4))
                            valve_open_interval=str(round(float(self.IntervalRight_2.text()),4))
                            cycle=str(int(self.CycleCaliRight.text()))
                            if self.WeightAfterRight.text()=='':
                                self.Warning.setText('Please enter the measured \"weight after(mg)\" and click the continue button again!\nOr enter a negative value to repeat the current calibration.')
                                continuetag=0
                                self.Continue.setChecked(False)
                                self.Continue.setStyleSheet("background-color : none")
                            else:
                                try:
                                    continuetag=1
                                    total_water=float(self.WeightAfterRight.text())
                                    tube_weight=self.WeightBeforeRight.text()
                                    if tube_weight=='':
                                        tube_weight=0
                                    else:
                                        tube_weight=float(tube_weight)
                                    if total_water>=0:
                                        self._Save(valve=valve,valve_open_time=valve_open_time,valve_open_interval=valve_open_interval,cycle=cycle,total_water=total_water,tube_weight=tube_weight)
                                    # clear the weight before/tube/weight after
                                    self.WeightAfterRight.setText('')
                                    if self.TubeWeightRight.text()=='':
                                        self.WeightBeforeRight.setText(str(total_water))
                                    else:
                                        self.WeightBeforeRight.setText(self.TubeWeightRight.text())
                                    self.TubeWeightRight.setText('')
                                except Exception as e:
                                    logging.error(str(e))
                                    continuetag=0
                                    self.Warning.setText('Please enter the correct weight after(mg)/tube weight(mg) and click the continue button again!\nOr enter a negative value to repeat the current calibration.')
                        if continuetag==1:
                            break
                # Repeat current calibration when negative value is entered
                QApplication.processEvents()
                try:
                    if total_water=='' or total_water<=0:
                        pass
                    else:
                        break
                except Exception as e:
                    logging.error(str(e))
                    break
        try: 
            # calibration complete indication
            if self.StartCalibratingRight.isChecked() and current_valve_opentime==np.arange(float(self.TimeRightMin.text()),float(self.TimeRightMax.text())+0.0001,float(self.StrideRight.text()))[-1]:
                self.Warning.setText('Calibration is complete!')
                self._UpdateFigure()
        except Exception as e:
            logging.error(str(e))
            self.Warning.setText('Calibration is not complete! Parameters error!')
            self.Warning.setStyleSheet(self.MainWindow.default_warning_color)

        # set the default valve open time
        ## DEBUGGING ##self.MainWindow.Channel.RightValue(float(self.MainWindow.RightValue.text())*1000)
        # enable the left valve calibration
        self.StartCalibratingLeft.setEnabled(True)
        self.label_9.setEnabled(True)
        self.label_10.setEnabled(True)
        self.label_11.setEnabled(True)
        self.label_12.setEnabled(True)
        self.label_23.setEnabled(True)
        self.label_13.setEnabled(True)
        self.label_24.setEnabled(True)
        self.label_26.setEnabled(True)
        self.TimeLeftMin.setEnabled(True)
        self.TimeLeftMax.setEnabled(True)
        self.StrideLeft.setEnabled(True)
        self.CycleCaliLeft.setEnabled(True)
        self.IntervalLeft_2.setEnabled(True)
        self.WeightAfterLeft.setEnabled(True) 
        self.WeightBeforeLeft.setEnabled(True)
        self.TubeWeightLeft.setEnabled(True)
        # change the color to be normal
        self.StartCalibratingRight.setStyleSheet("background-color : none")
        self.StartCalibratingRight.setChecked(False
)
    def _Save(self,valve,valve_open_time,valve_open_interval,cycle,total_water,tube_weight):
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
            WaterCalibrationResults[date_str][valve][valve_open_time][valve_open_interval][cycle] = {}
        if WaterCalibrationResults[date_str][valve][valve_open_time][valve_open_interval][cycle]=={}:
            WaterCalibrationResults[date_str][valve][valve_open_time][valve_open_interval][cycle]=[total_water]
        else:
            WaterCalibrationResults[date_str][valve][valve_open_time][valve_open_interval][cycle].append(total_water)
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

    def _OpenLeftForever(self):
        '''Open the left valve forever'''
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        if self.OpenLeftForever.isChecked():
            # change button color
            self.OpenLeftForever.setStyleSheet("background-color : green;")
            # set the valve open time
            ## DEBUGGING ##self.MainWindow.Channel.LeftValue(float(1000)*1000) 
            # open the valve
            ## DEBUGGING ##self.MainWindow.Channel3.ManualWater_Left(int(1))
        else:
            # change button color
            self.OpenLeftForever.setStyleSheet("background-color : none")
            # close the valve 
            ## DEBUGGING ##self.MainWindow.Channel.LeftValue(float(0.001)*1000)
            ## DEBUGGING ##self.MainWindow.Channel3.ManualWater_Left(int(1))
            # set the default valve open time
            ## DEBUGGING ##self.MainWindow.Channel.LeftValue(float(self.MainWindow.LeftValue.text())*1000)

    def _OpenRightForever(self):
        '''Open the right valve forever'''
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        if self.OpenRightForever.isChecked():
            # change button color
            self.OpenRightForever.setStyleSheet("background-color : green;")
            # set the valve open time
            ## DEBUGGING ##self.MainWindow.Channel.RightValue(float(1000)*1000) 
            # open the valve
            ## DEBUGGING ##self.MainWindow.Channel3.ManualWater_Right(int(1))
        else:
            # change button color
            self.OpenRightForever.setStyleSheet("background-color : none")
            # close the valve 
            ## DEBUGGING ##self.MainWindow.Channel.RightValue(float(0.001)*1000)
            ## DEBUGGING ##self.MainWindow.Channel3.ManualWater_Right(int(1))
            # set the default valve open time
            ## DEBUGGING ##self.MainWindow.Channel.RightValue(float(self.MainWindow.RightValue.text())*1000)

    def _TimeRemaining(self,i, cycles, opentime, interval):
        total_seconds = (cycles-i)*(opentime+interval)
        minutes = int(np.floor(total_seconds/60))
        seconds = int(np.ceil(np.mod(total_seconds,60)))
        return '{}:{:02}'.format(minutes, seconds)
    
    def _VolumeToTime(self,volume,valve):
        # x = (y-b)/m 
        if hasattr(self.MainWindow, 'latest_fitting'):
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

    def _SpotCheckLeft(self):    
        '''Calibration of left valve in a different thread'''

        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            self.SpotCheckLeft.setChecked(False)        
            self.SpotCheckLeft.setStyleSheet("background-color : none;")
            self.SaveLeft.setStyleSheet("color: black;background-color : none;")
            self.TotalWaterSingleLeft.setText('')
            self.SpotCheckPreWeightLeft.setText('')
            return

        if self.SpotCheckLeft.isChecked():
            logging.info('starting spot check left')
            self.SpotCheckLeft.setStyleSheet("background-color : green;")
    
            # Get empty tube weight, using field value as default
            if self.SpotCheckPreWeightLeft.text() != '':
                empty_tube_weight = float(self.SpotCheckPreWeightLeft.text()) 
            else:
                empty_tube_weight = 0.0 
            empty_tube_weight, ok = QInputDialog().getDouble(
                self,
                'Box {}, Left'.format(self.MainWindow.box_letter),
                "Empty tube weight (g): ", 
                empty_tube_weight,
                0,1000,2)
            if not ok:
                # User cancels
                logging.warning('user cancelled spot calibration')
                self.SpotCheckLeft.setStyleSheet("background-color : none;")
                self.SpotCheckLeft.setChecked(False)        
                self.Warning.setText('Spot check left cancelled')
                self.SpotCheckPreWeightLeft.setText('')
                self.TotalWaterSingleLeft.setText('')
                self.SaveLeft.setStyleSheet("color: black;background-color : none;")
                return
            self.SpotCheckPreWeightLeft.setText(str(empty_tube_weight))

        # Determine what open time to use
        self.SpotLeftFinished=0
        self.SpotLeftOpenTime = self._VolumeToTime(float(self.SpotLeftVolume.text()),'Left')
        self.SpotLeftOpenTime = np.round(self.SpotLeftOpenTime,4)
        logging.info('Using a calibration spot check of {}s to deliver {}uL'.format(self.SpotLeftOpenTime,self.SpotLeftVolume.text()))

        # start the open/close/delay cycle
        for i in range(int(self.SpotCycle)):
            QApplication.processEvents()
            if self.SpotCheckLeft.isChecked() and (not self.EmergencyStop.isChecked()):
                self.Warning.setText(
                    'Measuring left valve: {}uL'.format(self.SpotLeftVolume.text()) + \
                    '\nEmpty tube weight: {}g'.format(empty_tube_weight) + \
                    '\nCurrent cycle: '+str(i+1)+'/{}'.format(int(self.SpotCycle)) + \
                    '\nTime remaining: {}'.format(self._TimeRemaining(
                        i,self.SpotCycle,self.SpotLeftOpenTime,self.SpotInterval))
                    )
                self.Warning.setStyleSheet(self.MainWindow.default_warning_color)

                # set the valve open time
                ## DEBUGGING ##self.MainWindow.Channel.LeftValue(float(self.SpotLeftOpenTime.text())*1000) 
                # open the valve
                ## DEBUGGING ##self.MainWindow.Channel3.ManualWater_Left(int(1))
                # delay
                time.sleep(self.SpotLeftOpenTime+self.SpotInterval)
            else:
                self.Warning.setText('Spot check left cancelled')
                self.SpotCheckPreWeightLeft.setText('')
                self.TotalWaterSingleLeft.setText('')
                self.SaveLeft.setStyleSheet("color: black;background-color : none;")
                break
            self.SpotLeftFinished=1

        if self.SpotLeftFinished == 1:
            # Get final value, using field as default
            if self.TotalWaterSingleLeft.text() != '':
                final_tube_weight = float(self.TotalWaterSingleLeft.text()) 
            else:
                final_tube_weight = 0.0
            final_tube_weight, ok = QInputDialog().getDouble(
                self,
                'Box {}, Left'.format(self.MainWindow.box_letter),
                "Final tube weight (g): ", 
                final_tube_weight,
                0, 1000, 2)
            self.TotalWaterSingleLeft.setText(str(final_tube_weight))

            #Determine result
            result = (final_tube_weight - empty_tube_weight)/int(self.SpotCycle)*1000
            error = result - float(self.SpotLeftVolume.text())
            error = np.round(error,4)
            self.Warning.setText(
                'Measuring left valve: {}uL'.format(self.SpotLeftVolume.text()) + \
                '\nEmpty tube weight: {}g'.format(empty_tube_weight) + \
                '\nFinal tube weight: {}g'.format(final_tube_weight) + \
                '\nAvg. error from target: {}uL'.format(error)
                )        
            TOLERANCE = float(self.SpotLeftVolume.text())/10
            if np.abs(error) > TOLERANCE:
                reply = QMessageBox.question(self, 'Spot check left', 
                    'Avg. error ({}uL) is outside expected tolerance. Please confirm you entered information correctly, and then repeat check'.format(error), 
                    QMessageBox.Ok)
                logging.error('Water calibration spot check exceeds tolerance: {}'.format(error))  
                self.SaveLeft.setStyleSheet("color: white;background-color : mediumorchid;")
                self.Warning.setText(
                    'Measuring left valve: {}uL'.format(self.SpotLeftVolume.text()) + \
                    '\nEmpty tube weight: {}g'.format(empty_tube_weight) + \
                    '\nFinal tube weight: {}g'.format(final_tube_weight) + \
                    '\nAvg. error from target: {}uL'.format(error)
                    )
            else:
                self.Warning.setText(
                    'Measuring left valve: {}uL'.format(self.SpotLeftVolume.text()) + \
                    '\nEmpty tube weight: {}g'.format(empty_tube_weight) + \
                    '\nFinal tube weight: {}g'.format(final_tube_weight) + \
                    '\nAvg. error from target: {}uL'.format(error) + \
                    '\nCalibration saved'
                    )
                self._SaveLeft()


        # set the default valve open time
        ## DEBUGGING ##self.MainWindow.Channel.LeftValue(float(self.MainWindow.LeftValue.text())*1000)

        self.SpotCheckLeft.setChecked(False)        
        self.SpotCheckLeft.setStyleSheet("background-color : none")
        logging.info('Done with spot check Left')

    def _SpotCheckRight(self):
        '''Calibration of right valve in a different thread'''

        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            self.SpotCheckRight.setChecked(False)        
            self.SpotCheckRight.setStyleSheet("background-color : none;")
            self.SaveRight.setStyleSheet("color: black;background-color : none;")
            self.TotalWaterSingleRight.setText('')
            self.SpotCheckPreWeightRight.setText('')
            return

        if self.SpotCheckRight.isChecked() and (not self.EmergencyStop.isChecked()):
            logging.info('starting spot check right')
            self.SpotCheckRight.setStyleSheet("background-color : green;")
    
            # Get empty tube weight, using field value as default
            if self.SpotCheckPreWeightRight.text() != '':
                empty_tube_weight = float(self.SpotCheckPreWeightRight.text()) 
            else:
                empty_tube_weight = 0.0 
            empty_tube_weight, ok = QInputDialog().getDouble(
                self,
                'Box {}, Right'.format(self.MainWindow.box_letter),
                "Empty tube weight (g): ", 
                empty_tube_weight,
                0,1000,2)
            if not ok:
                # User cancels
                logging.warning('user cancelled spot calibration')
                self.SpotCheckRight.setStyleSheet("background-color : none;")
                self.SpotCheckRight.setChecked(False)        
                self.Warning.setText('Spot check right cancelled')
                self.SpotCheckPreWeightRight.setText('')
                self.TotalWaterSingleRight.setText('')
                self.SaveRight.setStyleSheet("color: black;background-color : none;")
                return
            self.SpotCheckPreWeightRight.setText(str(empty_tube_weight))

        # Determine what open time to use
        self.SpotRightFinished=0
        self.SpotRightOpenTime = self._VolumeToTime(float(self.SpotRightVolume.text()),'Right')
        self.SpotRightOpenTime = np.round(self.SpotRightOpenTime,4)
        logging.info('Using a calibration spot check of {}s to deliver {}uL'.format(self.SpotRightOpenTime,self.SpotRightVolume.text()))

        # start the open/close/delay cycle
        for i in range(int(self.SpotCycle)):
            QApplication.processEvents()
            if self.SpotCheckRight.isChecked():
                self.Warning.setText(
                    'Measuring right valve: {}uL'.format(self.SpotRightVolume.text()) + \
                    '\nEmpty tube weight: {}g'.format(empty_tube_weight) + \
                    '\nCurrent cycle: '+str(i+1)+'/{}'.format(int(self.SpotCycle)) + \
                    '\nTime remaining: {}'.format(self._TimeRemaining(
                        i,self.SpotCycle,self.SpotRightOpenTime,self.SpotInterval))
                    )
                self.Warning.setStyleSheet(self.MainWindow.default_warning_color)

                # set the valve open time
                ## DEBUGGING ##self.MainWindow.Channel.RightValue(float(self.SpotRightOpenTime.text())*1000) 
                # open the valve
                ## DEBUGGING ##self.MainWindow.Channel3.ManualWater_Right(int(1))
                # delay
                time.sleep(self.SpotRightOpenTime+self.SpotInterval)
            else:
                self.Warning.setText('Spot check right cancelled')
                self.SpotCheckPreWeightRight.setText('')
                self.TotalWaterSingleRight.setText('')
                self.SaveRight.setStyleSheet("color: black;background-color : none;")
                break
            self.SpotRightFinished=1

        if self.SpotRightFinished == 1:
            # Get final value, using field as default
            if self.TotalWaterSingleRight.text() != '':
                final_tube_weight = float(self.TotalWaterSingleRight.text()) 
            else:
                final_tube_weight = 0.0
            final_tube_weight, ok = QInputDialog().getDouble(
                self,
                'Box {}, Right'.format(self.MainWindow.box_letter),
                "Final tube weight (g): ", 
                final_tube_weight,
                0, 1000, 2)
            self.TotalWaterSingleRight.setText(str(final_tube_weight))

            #Determine result
            result = (final_tube_weight - empty_tube_weight)/int(self.SpotCycle)*1000
            error = result - float(self.SpotRightVolume.text())
            error = np.round(error,4)
        
            TOLERANCE = float(self.SpotRightVolume.text())/10
            if np.abs(error) > TOLERANCE:
                reply = QMessageBox.question(self, 'Spot check right', 
                    'Avg. error ({}uL) is outside expected tolerance. Please confirm you entered information correctly, and then repeat check'.format(error), 
                    QMessageBox.Ok)
                logging.error('Water calibration spot check exceeds tolerance: {}'.format(error))  
                self.SaveRight.setStyleSheet("color: white;background-color : mediumorchid;")
                self.Warning.setText(
                    'Measuring right valve: {}uL'.format(self.SpotRightVolume.text()) + \
                    '\nEmpty tube weight: {}g'.format(empty_tube_weight) + \
                    '\nFinal tube weight: {}g'.format(final_tube_weight) + \
                    '\nAvg. error from target: {}uL'.format(error)
                    )
            else:
                self.Warning.setText(
                    'Measuring right valve: {}uL'.format(self.SpotRightVolume.text()) + \
                    '\nEmpty tube weight: {}g'.format(empty_tube_weight) + \
                    '\nFinal tube weight: {}g'.format(final_tube_weight) + \
                    '\nAvg. error from target: {}uL'.format(error) + \
                    '\nCalibration saved'
                    )
                self._SaveRight()

        # set the default valve open time
        ## DEBUGGING ##self.MainWindow.Channel.RightValue(float(self.MainWindow.RightValue.text())*1000)

        self.SpotCheckRight.setChecked(False)        
        self.SpotCheckRight.setStyleSheet("background-color : none")
        logging.info('Done with spot check Right')
        

class CameraDialog(QDialog):
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        uic.loadUi('Camera.ui', self)
        
        self.MainWindow=MainWindow
        self._connectSignalsSlots()
        self.camera_start_time=''
        self.camera_stop_time=''
    def _connectSignalsSlots(self):
        self.StartCamera.clicked.connect(self._StartCamera)
        self.ClearTemporaryVideo.clicked.connect(self._ClearTemporaryVideo)
        self.AutoControl.currentIndexChanged.connect(self._AutoControl)
        self.RestartLogging.clicked.connect(self._RestartLogging)
        self.OpenSaveFolder.clicked.connect(self._OpenSaveFolder)

    def _OpenSaveFolder(self):
        '''Open the log/save folder of the camera'''
        if hasattr(self.MainWindow,'Ot_log_folder'):
            try:
                subprocess.Popen(['explorer', os.path.join(os.path.dirname(os.path.dirname(self.MainWindow.Ot_log_folder)),'behavior-videos')])
            except Exception as e:
                logging.error(str(e))
                self.WarningLabelOpenSave.setText('No logging folder found!')
                self.WarningLabelOpenSave.setStyleSheet(self.MainWindow.default_warning_color)
        else:
            self.WarningLabelOpenSave.setText('No logging folder found!')
            self.WarningLabelOpenSave.setStyleSheet(self.MainWindow.default_warning_color)

    def _RestartLogging(self):
        '''Restart the logging (create a new logging folder)'''
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        if self.CollectVideo.currentText()=='Yes':
            # formal logging
            self.MainWindow.CreateNewFolder=1
            self.MainWindow.Ot_log_folder=self.MainWindow._restartlogging()
        else:
            # temporary logging
            self.MainWindow.Ot_log_folder=self.MainWindow._restartlogging(self.MainWindow.temporary_video_folder)
        self.WarningLabelLogging.setText('Logging has restarted!')
        self.WarningLabelLogging.setStyleSheet(self.MainWindow.default_warning_color)

    def _AutoControl(self):
        '''Trigger the camera during the start of a new behavior session'''
        if self.AutoControl.currentText()=='Yes':
            #self.StartCamera.setEnabled(False)
            self.label_8.setEnabled(False)
            self.CollectVideo.setEnabled(False)
            self.RestartLogging.setEnabled(False)
            self.StartCamera.setChecked(False)
            index = self.CollectVideo.findText('Yes')
            if index != -1:
                self.CollectVideo.setCurrentIndex(index)
        else:
            #self.StartCamera.setEnabled(True)
            self.label_8.setEnabled(True)
            self.CollectVideo.setEnabled(True)
            self.RestartLogging.setEnabled(True)
            index = self.CollectVideo.findText('No')
            if index != -1:
                self.CollectVideo.setCurrentIndex(index)
            
    def _ClearTemporaryVideo(self):
        '''Clear temporary video files'''
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        try:
            # Remove a directory and its contents (recursively)
            if os.path.exists(self.MainWindow.temporary_video_folder):
                shutil.rmtree(self.MainWindow.temporary_video_folder)
                logging.info(f"Directory '{self.MainWindow.temporary_video_folder}' and its contents removed successfully.")
            else:
                logging.info(f"Directory '{self.MainWindow.temporary_video_folder}' does not exist.")
        except Exception as e:
            logging.error(str(e))

    def _StartCamera(self):
        '''Start/stop the camera'''
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            self.MainWindow._ConnectBonsai()
            if self.MainWindow.InitializeBonsaiSuccessfully==0:
                return 
        if self.StartCamera.isChecked():
            self.StartCamera.setStyleSheet("background-color : green;")
            if self.AutoControl.currentText()=='No':
                # If the behavior start button is checked, set the CollectVideo to Yes.
                if self.MainWindow.Start.isChecked():
                    index=self.CollectVideo.findText('Yes')
                    self.CollectVideo.setCurrentIndex(index)
                # Do not restart logging when automatic control is "yes" as logging will start in behavior control
                if self.CollectVideo.currentText()=='Yes':
                    # Start logging if the formal logging is not started
                    if self.MainWindow.loggingstarted!=0:
                        self.MainWindow.Ot_log_folder=self.MainWindow._restartlogging()
                else:
                    if self.MainWindow.loggingstarted!=1:
                        # Start logging if the temporary logging is not started
                        self.MainWindow.Ot_log_folder=self.MainWindow._restartlogging(self.MainWindow.temporary_video_folder)
            '''
            # This part was dropped due to the new logging method
            # save the video data
            if self.CollectVideo.currentText()=='Yes':
                Re=self._SaveVideoData()
            if self.CollectVideo.currentText()=='No' or Re==False:
                video_folder=self.MainWindow.video_folder
                video_folder=os.path.join(video_folder,'Tmp')
                if not os.path.exists(video_folder):
                    os.makedirs(video_folder)
                side_camera_file=os.path.join(video_folder,'side_camera.avi')
                bottom_camera_file=os.path.join(video_folder,'bottom_camera.avi')
                side_camera_csv=os.path.join(video_folder,'side_camera.csv')
                bottom_camera_csv=os.path.join(video_folder,'bottom_camera.csv')
                self.MainWindow.Channel.SideCameraFile(side_camera_file)
                self.MainWindow.Channel.BottomCameraFile(bottom_camera_file)
                self.MainWindow.Channel.SideCameraCSV(side_camera_csv)
                self.MainWindow.Channel.BottomCameraCSV(bottom_camera_csv)
            '''
            # set the camera frequency. It's better to set the frequency after the temporary logging. 
            self.MainWindow.Channel.CameraFrequency(int(self.FrameRate.text()))
            # start the video triggers
            self.MainWindow.Channel.CameraControl(int(1))
            time.sleep(5)
            self.camera_start_time = str(datetime.now())
            self.MainWindow.WarningLabelCamera.setText('Camera is on!')
            self.MainWindow.WarningLabelCamera.setStyleSheet(self.MainWindow.default_warning_color)
            self.WarningLabelCameraOn.setText('Camera is on!')
            self.WarningLabelCameraOn.setStyleSheet(self.MainWindow.default_warning_color)
            self.WarningLabelLogging.setText('')
            self.WarningLabelLogging.setStyleSheet("color: None;")
            self.WarningLabelOpenSave.setText('')
        else:
            self.StartCamera.setStyleSheet("background-color : none")
            self.MainWindow.Channel.CameraControl(int(2))
            self.camera_stop_time = str(datetime.now())
            time.sleep(5)
            self.MainWindow.WarningLabelCamera.setText('Camera is off!')
            self.MainWindow.WarningLabelCamera.setStyleSheet(self.MainWindow.default_warning_color)
            self.WarningLabelCameraOn.setText('Camera is off!')
            self.WarningLabelCameraOn.setStyleSheet(self.MainWindow.default_warning_color)
            self.WarningLabelLogging.setText('')
            self.WarningLabelLogging.setStyleSheet("color: None;")
            self.WarningLabelOpenSave.setText('')
    
    def _SaveVideoData(self):
        '''Save the video data'''
        self.MainWindow._GetSaveFileName()
        video_folder=self.MainWindow.video_folder
        video_folder=os.path.join(video_folder,self.MainWindow.current_box,self.MainWindow.AnimalName.text())
        if not os.path.exists(video_folder):
            os.makedirs(video_folder)
        base_name=os.path.splitext(os.path.basename(self.MainWindow.SaveFileJson))[0]
        
        side_camera_file=os.path.join(video_folder,base_name+'_side_camera.avi')
        bottom_camera_file=os.path.join(video_folder,base_name+'_bottom_camera.avi')
        side_camera_csv=os.path.join(video_folder,base_name+'_side_camera.csv')
        bottom_camera_csv=os.path.join(video_folder,base_name+'_bottom_camera.csv')
        if is_file_in_use(side_camera_file) or is_file_in_use(bottom_camera_file) or is_file_in_use(side_camera_csv) or is_file_in_use(bottom_camera_csv):              
            self.WarningLabelFileIsInUse.setText('File is in use. Please restart the bonsai!')
            self.WarningLabelFileIsInUse.setStyleSheet(self.MainWindow.default_warning_color)
            return False
        else:
            self.WarningLabelFileIsInUse.setText('')
        N=0
        while 1:
            if os.path.isfile(side_camera_file) or os.path.isfile(bottom_camera_file) or os.path.isfile(side_camera_csv) or os.path.isfile(bottom_camera_csv):
                N=N+1
                side_camera_file=os.path.join(video_folder,base_name+'_'+str(N)+'_side_camera.avi')
                bottom_camera_file=os.path.join(video_folder,base_name+'_'+str(N)+'_bottom_camera.avi')
                side_camera_csv=os.path.join(video_folder,base_name+'_'+str(N)+'_side_camera.csv')
                bottom_camera_csv=os.path.join(video_folder,base_name+'_'+str(N)+'_bottom_camera.csv')
            else:
                break
        if is_file_in_use(side_camera_file) or is_file_in_use(bottom_camera_file) or is_file_in_use(side_camera_csv) or is_file_in_use(bottom_camera_csv):
            self.WarningLabelFileIsInUse.setText('File is in use. Please restart the bonsai!')
            self.WarningLabelFileIsInUse.setStyleSheet(self.MainWindow.default_warning_color)
            return False
        else:
            self.WarningLabelFileIsInUse.setText('')
        self.MainWindow.Channel.SideCameraFile(side_camera_file)
        self.MainWindow.Channel.BottomCameraFile(bottom_camera_file)
        self.MainWindow.Channel.SideCameraCSV(side_camera_csv)
        self.MainWindow.Channel.BottomCameraCSV(bottom_camera_csv)
        self.MainWindow.TP_side_camera_file=side_camera_file
        self.MainWindow.TP_bottom_camera_file=bottom_camera_file
        self.MainWindow.TP_side_camera_csv=side_camera_csv
        self.MainWindow.TP_bottom_camera_csv=bottom_camera_csv
        return True
    
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
        self.condition_idx=[1,2,3,4]
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
        if getattr(self, 'LaserColor_'+str(Numb)+'.currentText()')=='NA':
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
        if getattr(self, 'LaserColor_'+str(Numb)+'.currentText')() != 'NA':
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
                    self.win.WarningLabel.setText('Ramping down is longer than the laser duration!')
                    self.win.WarningLabel.setStyleSheet(self.MainWindow.default_warning_color)
                else:
                    Constant=np.ones(int((self.CLP_CurrentDuration-self.CLP_RampingDown)*self.CLP_SampleFrequency))
                    RD=np.arange(1,0, -1/(np.shape(self.my_wave)[0]-np.shape(Constant)[0]))
                    RampingDown = np.concatenate((Constant, RD), axis=0)
                    self.my_wave=self.my_wave*RampingDown
            self.my_wave=np.append(self.my_wave,[0,0])
        elif self.CLP_Protocol=='Pulse':
            if self.CLP_PulseDur=='NA':
                self.win.WarningLabel.setText('Pulse duration is NA!')
                self.win.WarningLabel.setStyleSheet(self.MainWindow.default_warning_color)
            else:
                self.CLP_PulseDur=float(self.CLP_PulseDur)
                PointsEachPulse=int(self.CLP_SampleFrequency*self.CLP_PulseDur)
                PulseIntervalPoints=int(1/self.CLP_Frequency*self.CLP_SampleFrequency-PointsEachPulse)
                if PulseIntervalPoints<0:
                    self.win.WarningLabel.setText('Pulse frequency and pulse duration are not compatible!')
                    self.win.WarningLabel.setStyleSheet(self.MainWindow.default_warning_color)
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
                    self.win.WarningLabel.setText('Pulse number is less than 1!')
                    self.win.WarningLabel.setStyleSheet(self.MainWindow.default_warning_color)
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
                    self.win.WarningLabel.setText('Ramping down is longer than the laser duration!')
                    self.win.WarningLabel.setStyleSheet(self.MainWindow.default_warning_color)
                else:
                    Constant=np.ones(int((self.CLP_CurrentDuration-self.CLP_RampingDown)*self.CLP_SampleFrequency))
                    RD=np.arange(1,0, -1/(np.shape(self.my_wave)[0]-np.shape(Constant)[0]))
                    RampingDown = np.concatenate((Constant, RD), axis=0)
                    self.my_wave=self.my_wave*RampingDown
            self.my_wave=np.append(self.my_wave,[0,0])
        else:
            self.win.WarningLabel.setText('Unidentified optogenetics protocol!')
            self.win.WarningLabel.setStyleSheet(self.MainWindow.default_warning_color)

    def _GetLaserAmplitude(self):
        '''the voltage amplitude dependens on Protocol, Laser Power, Laser color, and the stimulation locations<>'''
        if self.CLP_Location=='Laser_1':
            self.CurrentLaserAmplitude=[self.CLP_InputVoltage,0]
        elif self.CLP_Location=='Laser_2':
            self.CurrentLaserAmplitude=[0,self.CLP_InputVoltage]
        elif self.CLP_Location=='Both':
            self.CurrentLaserAmplitude=[self.CLP_InputVoltage,self.CLP_InputVoltage]
        else:
            self.win.WarningLabel.setText('No stimulation location defined!')
            self.win.WarningLabel.setStyleSheet(self.MainWindow.default_warning_color)
   
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
        self.Protocol_1.setCurrentIndex(self.MainWindow.Opto_dialog.__getattribute__("Protocol_" + condition).currentIndex())
        self.voltage.setText(str(eval(self.MainWindow.Opto_dialog.__getattribute__(f"Laser{copylaser}_power_{condition}").currentText())[0]))
        

    def _Capture(self):
        '''Save the measured laser power'''
        self.Capture.setStyleSheet("background-color : green;")
        QApplication.processEvents()
        self._GetTrainingParameters(self.MainWindow)
        self.Warning.setText('')
        if self.Location_1.currentText()=='Both':
            self.Warning.setText('Data not captured! Please choose left or right, not both!')
            self.Warning.setStyleSheet(self.MainWindow.default_warning_color)
            self.Warning.setAlignment(Qt.AlignCenter)
            return
        if self.LaserPowerMeasured.text()=='':
            self.Warning.setText('Data not captured! Please enter power measured!')
            self.Warning.setStyleSheet(self.MainWindow.default_warning_color)
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
            self.Warning.setStyleSheet(self.MainWindow.default_warning_color)
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
            self.Warning.setStyleSheet(self.MainWindow.default_warning_color)
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
        self.RigMetadataFile.textChanged.connect(self._removing_warning)
        self.ClearMetadata.clicked.connect(self._clear_metadata)
        self.Stick_ArcAngle.textChanged.connect(self._save_configuration)
        self.Stick_ModuleAngle.textChanged.connect(self._save_configuration)
        self.Stick_RotationAngle.textChanged.connect(self._save_configuration)
        self.ProjectName.currentIndexChanged.connect(self._show_project_info)
        self.GoCueDecibel.textChanged.connect(self._save_go_cue_decibel)
        self.LickSpoutDistance.textChanged.connect(self._save_lick_spout_distance)

    def _set_reference(self, reference):
        '''set the reference'''
        self.reference = reference
        self.LickSpoutReferenceX.setText(str(reference[0]))
        self.LickSpoutReferenceY.setText(str(reference[1]))
        self.LickSpoutReferenceZ.setText(str(reference[2]))

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

    def _removing_warning(self):
        '''remove the warning'''
        if self.RigMetadataFile.text()!='':
            self.MainWindow._manage_warning_labels(self.MainWindow.MetadataWarning,warning_text='')

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
        if (update_rig_metadata or update_session_metadata) and ('rig_metadata_file' in self.meta_data):
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
        aws_connected = self._connect_auto_training_manager()
        
        # Disable Auto Train button if not connected to AWS
        if not aws_connected:
            self.MainWindow.AutoTrain.setEnabled(False)
            return
        
        self._connect_curriculum_manager()
        
        # Signals slots
        self._setup_allbacks()
        
        # Sync selected subject_id
        self.update_auto_train_fields(subject_id=self.MainWindow.ID.text())
                
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
        
    def update_auto_train_fields(self, subject_id: str, curriculum_just_overridden: bool = False):
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
            self.label_subject_id.setStyleSheet(self.MainWindow.default_warning_color)
            
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
                self.label_next_stage_suggested.setStyleSheet(self.MainWindow.default_warning_color)
                
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
            QMessageBox.critical(self,
                                 'Box {}, Error'.format(self.MainWindow.box_letter),
                                 f'AWS connection failed!\n'
                                 f'Please check your AWS credentials at ~\.aws\credentials!')
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
                
            self.widgets_locked_by_auto_train.extend(
                [self.MainWindow.TrainingStage]
                )

            # lock the widgets that have been set by auto training 
            for widget in self.widgets_locked_by_auto_train:
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
            self.MainWindow.label_auto_train_stage.setStyleSheet(self.MainWindow.default_warning_color)


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
