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
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QThreadPool,Qt, QAbstractTableModel, QItemSelectionModel, QObject
from PyQt5.QtSvg import QSvgWidget

from MyFunctions import Worker
from Visualization import PlotWaterCalibration
from aind_auto_train.curriculum_manager import CurriculumManager
from aind_auto_train.auto_train_manager import DynamicForagingAutoTrainManager
from aind_auto_train.schema.task import TrainingStage

logger = logging.getLogger(__name__)

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
        
        self._connectSignalsSlots()
        self.MainWindow=MainWindow
        self._Laser_1()
        self._Laser_2()
        self._Laser_3()
        self._Laser_4()
        self._Laser_calibration()
    def _connectSignalsSlots(self):
        self.Laser_1.currentIndexChanged.connect(self._Laser_1)
        self.Laser_2.currentIndexChanged.connect(self._Laser_2)
        self.Laser_3.currentIndexChanged.connect(self._Laser_3)
        self.Laser_4.currentIndexChanged.connect(self._Laser_4)
        self.Laser_1.activated.connect(self._Laser_1)
        self.Laser_2.activated.connect(self._Laser_2)
        self.Laser_3.activated.connect(self._Laser_3)
        self.Laser_4.activated.connect(self._Laser_4)
        self.Protocol_1.activated.connect(self._activated_1)
        self.Protocol_2.activated.connect(self._activated_2)
        self.Protocol_3.activated.connect(self._activated_3)
        self.Protocol_4.activated.connect(self._activated_4)
        self.Protocol_1.currentIndexChanged.connect(self._activated_1)
        self.Protocol_2.currentIndexChanged.connect(self._activated_2)
        self.Protocol_3.currentIndexChanged.connect(self._activated_3)
        self.Protocol_4.currentIndexChanged.connect(self._activated_4)
        self.Protocol_1.activated.connect(self._Laser_1)
        self.Protocol_2.activated.connect(self._Laser_2)
        self.Protocol_3.activated.connect(self._Laser_3)
        self.Protocol_4.activated.connect(self._Laser_4)
        self.Protocol_1.currentIndexChanged.connect(self._Laser_1)
        self.Protocol_2.currentIndexChanged.connect(self._Laser_2)
        self.Protocol_3.currentIndexChanged.connect(self._Laser_3)
        self.Protocol_4.currentIndexChanged.connect(self._Laser_4)
        self.Frequency_1.activated.connect(self._Frequency_1)
        self.Frequency_2.activated.connect(self._Frequency_2)
        self.Frequency_3.activated.connect(self._Frequency_3)
        self.Frequency_4.activated.connect(self._Frequency_4)
        self.Frequency_1.currentIndexChanged.connect(self._Frequency_1)
        self.Frequency_2.currentIndexChanged.connect(self._Frequency_2)
        self.Frequency_3.currentIndexChanged.connect(self._Frequency_3)
        self.Frequency_4.currentIndexChanged.connect(self._Frequency_4)
        self.LaserStart_1.activated.connect(self._activated_1)
        self.LaserStart_2.activated.connect(self._activated_2)
        self.LaserStart_3.activated.connect(self._activated_3)
        self.LaserStart_4.activated.connect(self._activated_4)
        self.LaserStart_1.currentIndexChanged.connect(self._activated_1)
        self.LaserStart_2.currentIndexChanged.connect(self._activated_2)
        self.LaserStart_3.currentIndexChanged.connect(self._activated_3)
        self.LaserStart_4.currentIndexChanged.connect(self._activated_4)
        self.LaserEnd_1.activated.connect(self._activated_1)
        self.LaserEnd_2.activated.connect(self._activated_2)
        self.LaserEnd_3.activated.connect(self._activated_3)
        self.LaserEnd_4.activated.connect(self._activated_4)
        self.LaserEnd_1.currentIndexChanged.connect(self._activated_1)
        self.LaserEnd_2.currentIndexChanged.connect(self._activated_2)
        self.LaserEnd_3.currentIndexChanged.connect(self._activated_3)
        self.LaserEnd_4.currentIndexChanged.connect(self._activated_4)
        self.Laser_calibration.currentIndexChanged.connect(self._Laser_calibration)
        self.Laser_calibration.activated.connect(self._Laser_calibration)
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

    def _Frequency_1(self):
        self._Frequency(1)
    def _Frequency_2(self):
        self._Frequency(2)
    def _Frequency_3(self):
        self._Frequency(3)
    def _Frequency_4(self):
        self._Frequency(4)
    def _Laser_1(self):
        self._Laser(1)
    def _Laser_2(self):
        self._Laser(2)
    def _Laser_3(self):
        self._Laser(3)
    def _Laser_4(self):
        self._Laser(4)
    def _activated_1(self):
        self._activated(1)
    def _activated_2(self):
        self._activated(2)
    def _activated_3(self):
        self._activated(3)
    def _activated_4(self):
        self._activated(4)
    def _Frequency(self,Numb):
        try:
            ItemsLeft=[]
            ItemsRight=[]
            Color=eval('self.Laser_'+str(Numb)+'.currentText()')
            Protocol=eval('self.Protocol_'+str(Numb)+'.currentText()')
            CurrentFrequency=eval('self.Frequency_'+str(Numb)+'.currentText()')
            CurrentlaserPowerLeft=eval('self.LaserPowerLeft_'+str(Numb)+'.currentText()')
            CurrentlaserPowerRight=eval('self.LaserPowerRight_'+str(Numb)+'.currentText()')
            latest_calibration_date=self._FindLatestCalibrationDate(Color)
            if latest_calibration_date=='NA':
                RecentLaserCalibration={}
            else:
                RecentLaserCalibration=self.MainWindow.LaserCalibrationResults[latest_calibration_date]
            if Protocol=='Sine':
                for i in range(len(RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Left']['LaserPowerVoltage'])):
                    ItemsLeft.append(str(RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Left']['LaserPowerVoltage'][i]))
                for i in range(len(RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Right']['LaserPowerVoltage'])):
                    ItemsRight.append(str(RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Right']['LaserPowerVoltage'][i]))

            elif Protocol=='Constant' or Protocol=='Pulse':
                for i in range(len(RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Left']['LaserPowerVoltage'])):
                    ItemsLeft.append(str(RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Left']['LaserPowerVoltage'][i]))
                for i in range(len(RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Right']['LaserPowerVoltage'])):
                    ItemsRight.append(str(RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Right']['LaserPowerVoltage'][i]))
            ItemsLeft=sorted(ItemsLeft)
            ItemsRight=sorted(ItemsRight)
            eval('self.LaserPowerLeft_'+str(Numb)+'.clear()')
            eval('self.LaserPowerLeft_'+str(Numb)+'.addItems(ItemsLeft)')
            if eval('self.LaserPowerLeft_'+str(Numb)+'.findText(CurrentlaserPowerLeft)'):
                index = eval('self.LaserPowerLeft_'+str(Numb)+'.findText(CurrentlaserPowerLeft)')
                if index != -1:
                    eval('self.LaserPowerLeft_'+str(Numb)+'.setCurrentIndex(index)')
            eval('self.LaserPowerRight_'+str(Numb)+'.clear()')
            eval('self.LaserPowerRight_'+str(Numb)+'.addItems(ItemsRight)')
            if eval('self.LaserPowerRight_'+str(Numb)+'.findText(CurrentlaserPowerRight)'):
                index = eval('self.LaserPowerRight_'+str(Numb)+'.findText(CurrentlaserPowerRight)')
                if index != -1:
                    eval('self.LaserPowerRight_'+str(Numb)+'.setCurrentIndex(index)')
        except Exception as e:
            logging.error(str(e))

    def _activated(self,Numb):
        '''enable/disable items based on protocols and laser start/end'''
        Inactlabel1=15 # pulse duration
        Inactlabel2=13 # frequency
        Inactlabel3=14 # Ramping down
        if eval('self.Protocol_'+str(Numb)+'.currentText()')=='Sine':
            eval('self.label'+str(Numb)+'_'+str(Inactlabel1)+'.setEnabled('+str(False)+')')
            eval('self.PulseDur_'+str(Numb)+'.setEnabled('+str(False)+')')
            eval('self.label'+str(Numb)+'_'+str(Inactlabel2)+'.setEnabled('+str(True)+')')
            eval('self.Frequency_'+str(Numb)+'.setEnabled('+str(True)+')')
            eval('self.label'+str(Numb)+'_'+str(Inactlabel3)+'.setEnabled('+str(True)+')')
            eval('self.RD_'+str(Numb)+'.setEnabled('+str(True)+')')
            eval('self.Frequency_'+str(Numb)+'.setEditable(False)')
        if eval('self.Protocol_'+str(Numb)+'.currentText()')=='Pulse':
            eval('self.label'+str(Numb)+'_'+str(Inactlabel1)+'.setEnabled('+str(True)+')')
            eval('self.PulseDur_'+str(Numb)+'.setEnabled('+str(True)+')')
            eval('self.label'+str(Numb)+'_'+str(Inactlabel2)+'.setEnabled('+str(True)+')')
            eval('self.Frequency_'+str(Numb)+'.setEnabled('+str(True)+')')
            eval('self.label'+str(Numb)+'_'+str(Inactlabel3)+'.setEnabled('+str(False)+')')
            eval('self.RD_'+str(Numb)+'.setEnabled('+str(False)+')')
            eval('self.Frequency_'+str(Numb)+'.setEditable(True)')
        if eval('self.Protocol_'+str(Numb)+'.currentText()')=='Constant':
            eval('self.label'+str(Numb)+'_'+str(Inactlabel1)+'.setEnabled('+str(False)+')')
            eval('self.PulseDur_'+str(Numb)+'.setEnabled('+str(False)+')')
            eval('self.label'+str(Numb)+'_'+str(Inactlabel2)+'.setEnabled('+str(False)+')')
            eval('self.Frequency_'+str(Numb)+'.setEnabled('+str(False)+')')
            eval('self.label'+str(Numb)+'_'+str(Inactlabel3)+'.setEnabled('+str(True)+')')
            eval('self.RD_'+str(Numb)+'.setEnabled('+str(True)+')')
            eval('self.Frequency_'+str(Numb)+'.clear()')
            eval('self.Frequency_'+str(Numb)+'.setEditable(False)')
        if eval('self.LaserStart_'+str(Numb)+'.currentText()')=='NA':
            eval('self.label'+str(Numb)+'_'+str(9)+'.setEnabled('+str(False)+')')
            eval('self.OffsetStart_'+str(Numb)+'.setEnabled('+str(False)+')')
        else:
            eval('self.label'+str(Numb)+'_'+str(9)+'.setEnabled('+str(True)+')')
            eval('self.OffsetStart_'+str(Numb)+'.setEnabled('+str(True)+')')
        if eval('self.LaserEnd_'+str(Numb)+'.currentText()')=='NA':
            eval('self.label'+str(Numb)+'_'+str(11)+'.setEnabled('+str(False)+')')
            eval('self.OffsetEnd_'+str(Numb)+'.setEnabled('+str(False)+')')
        else:
            eval('self.label'+str(Numb)+'_'+str(11)+'.setEnabled('+str(True)+')')
            eval('self.OffsetEnd_'+str(Numb)+'.setEnabled('+str(True)+')')
    def _Laser(self,Numb):
        ''' enable/disable items based on laser (blue/green/orange/red/NA)'''
        Inactlabel=range(2,17)
        if eval('self.Laser_'+str(Numb)+'.currentText()')=='NA':
            Label=False
        else:
            Label=True
            Color=eval('self.Laser_'+str(Numb)+'.currentText()')
            Protocol=eval('self.Protocol_'+str(Numb)+'.currentText()')
            CurrentFrequency=eval('self.Frequency_'+str(Numb)+'.currentText()')
            latest_calibration_date=self._FindLatestCalibrationDate(Color)
            if latest_calibration_date=='NA':
                RecentLaserCalibration={}
            else:
                RecentLaserCalibration=self.MainWindow.LaserCalibrationResults[latest_calibration_date]
            if not RecentLaserCalibration=={}:
                if Color in RecentLaserCalibration.keys():
                    if Protocol in RecentLaserCalibration[Color].keys():
                        if Protocol=='Sine': 
                            Frequency=RecentLaserCalibration[Color][Protocol].keys()
                            ItemsFrequency=[]
                            for Fre in Frequency:
                                ItemsFrequency.append(Fre)
                            ItemsFrequency=sorted(ItemsFrequency)
                            eval('self.Frequency_'+str(Numb)+'.clear()')
                            eval('self.Frequency_'+str(Numb)+'.addItems(ItemsFrequency)')
                            if not CurrentFrequency in Frequency:
                                CurrentFrequency=eval('self.Frequency_'+str(Numb)+'.currentText()')
                            ItemsLeft=[]
                            ItemsRight=[]
                            for i in range(len(RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Left']['LaserPowerVoltage'])):
                                ItemsLeft.append(str(RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Left']['LaserPowerVoltage'][i]))
                            for i in range(len(RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Right']['LaserPowerVoltage'])):
                                ItemsRight.append(str(RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Right']['LaserPowerVoltage'][i]))
                            ItemsLeft=sorted(ItemsLeft)
                            ItemsRight=sorted(ItemsRight)
                            eval('self.LaserPowerLeft_'+str(Numb)+'.clear()')
                            eval('self.LaserPowerLeft_'+str(Numb)+'.addItems(ItemsLeft)')
                            eval('self.LaserPowerRight_'+str(Numb)+'.clear()')
                            eval('self.LaserPowerRight_'+str(Numb)+'.addItems(ItemsRight)')
                        elif Protocol=='Constant' or Protocol=='Pulse':
                            ItemsLeft=[]
                            ItemsRight=[]
                            for i in range(len(RecentLaserCalibration[Color][Protocol]['Left']['LaserPowerVoltage'])):
                                ItemsLeft.append(str(RecentLaserCalibration[Color][Protocol]['Left']['LaserPowerVoltage'][i]))
                            for i in range(len(RecentLaserCalibration[Color][Protocol]['Right']['LaserPowerVoltage'])):
                                ItemsRight.append(str(RecentLaserCalibration[Color][Protocol]['Right']['LaserPowerVoltage'][i]))
                            ItemsLeft=sorted(ItemsLeft)
                            ItemsRight=sorted(ItemsRight)
                            eval('self.LaserPowerLeft_'+str(Numb)+'.clear()')
                            eval('self.LaserPowerLeft_'+str(Numb)+'.addItems(ItemsLeft)')
                            eval('self.LaserPowerLeft_'+str(Numb)+'.clear()')
                            eval('self.LaserPowerLeft_'+str(Numb)+'.addItems(ItemsRight)')
                        self.MainWindow.WarningLabel.setText('')
                        self.MainWindow.WarningLabel.setStyleSheet("color: gray;")
                    else:
                        eval('self.LaserPowerLeft_'+str(Numb)+'.clear()')
                        eval('self.LaserPowerRight_'+str(Numb)+'.clear()')
                        self.MainWindow.WarningLabel.setText('No calibration for this protocol identified!')
                        self.MainWindow.WarningLabel.setStyleSheet("color: purple;")
                else:
                    eval('self.LaserPowerLeft_'+str(Numb)+'.clear()')
                    eval('self.LaserPowerRight_'+str(Numb)+'.clear()')
                    self.MainWindow.WarningLabel.setText('No calibration for this laser identified!')
                    self.MainWindow.WarningLabel.setStyleSheet("color: purple;")
            else:
                eval('self.LaserPowerLeft_'+str(Numb)+'.clear()')
                eval('self.LaserPowerRight_'+str(Numb)+'.clear()')
                self.MainWindow.WarningLabel.setText('No calibration for this laser identified!')
                self.MainWindow.WarningLabel.setStyleSheet("color: purple;")

        eval('self.Location_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.LaserPowerLeft_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.LaserPowerRight_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.Probability_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.Duration_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.Condition_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.ConditionP_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.LaserStart_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.OffsetStart_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.LaserEnd_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.OffsetEnd_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.Protocol_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.Frequency_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.RD_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.PulseDur_'+str(Numb)+'.setEnabled('+str(Label)+')')
        for i in Inactlabel:
            eval('self.label'+str(Numb)+'_'+str(i)+'.setEnabled('+str(Label)+')')
        if eval('self.Laser_'+str(Numb)+'.currentText()')!='NA':    
            eval('self._activated_'+str(Numb)+'()')

class WaterCalibrationDialog(QDialog):
    '''Water valve calibration'''
    def __init__(self, MainWindow,parent=None):
        super().__init__(parent)
        uic.loadUi('Calibration.ui', self)
        
        self.MainWindow=MainWindow
        self.FinishLeftValve=0
        if not hasattr(self.MainWindow,'WaterCalibrationResults'):
            self.MainWindow.LaserCalibrationResults={}
            self.WaterCalibrationResults={}
        else:
            self.WaterCalibrationResults=self.MainWindow.WaterCalibrationResults
        self._connectSignalsSlots()
        self.ToInitializeVisual=1
        self._UpdateFigure()
        if hasattr(self.MainWindow,'tower_number'):
            self.setWindowTitle("Water Calibration: Tower "+'_'+str(self.MainWindow.tower_number))
        else:
            self.setWindowTitle('Water Calibration') 
    def _connectSignalsSlots(self):
        self.OpenLeft.clicked.connect(self._OpenLeft)
        self.OpenRight.clicked.connect(self._OpenRight)
        self.OpenLeftForever.clicked.connect(self._OpenLeftForever)
        self.OpenRightForever.clicked.connect(self._OpenRightForever)
        self.SaveLeft.clicked.connect(self._SaveLeft)
        self.SaveRight.clicked.connect(self._SaveRight)
        self.CalibrationType.currentIndexChanged.connect(self._CalibrationType)
        self.StartCalibratingLeft.clicked.connect(self._StartCalibratingLeft)
        self.StartCalibratingRight.clicked.connect(self._StartCalibratingRight)
        self.Continue.clicked.connect(self._Continue)
        self.EmergencyStop.clicked.connect(self._EmergencyStop)
        self.showrecent.textChanged.connect(self._Showrecent)
        self.showspecificcali.activated.connect(self._ShowSpecifcDay)
        self.SaveCalibrationPar.clicked.connect(self._SaveCalibrationPar)
    def _SaveCalibrationPar(self):
        '''save the calibration parameters'''
        # load the pre-stored calibration parameters
        self._LoadCaliPar()
        # get the current calibration parameters
        CalibrationType=self.CalibrationType.currentText()
        Keys=['TimeLeftMin','TimeLeftMax','StrideLeft','TimeRightMin','TimeRightMax','StrideRight','IntervalLeft_2','IntervalRight_2']
        widget_dict = {w.objectName(): w for w in self.findChildren((QtWidgets.QPushButton,QtWidgets.QLineEdit,QtWidgets.QTextEdit, QtWidgets.QComboBox,QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox))}
        for K in Keys:
            for key in widget_dict.keys():
                try:
                    if key==K:
                        widget = widget_dict[key]
                        self.WaterCalibrationPar[CalibrationType][K]=widget.text()
                except Exception as e:
                    logging.error('Water Calibration {}'.format(str(e)))
        # save
        if not os.path.exists(os.path.dirname(self.MainWindow.WaterCalibrationParFiles)):
            os.makedirs(os.path.dirname(self.MainWindow.WaterCalibrationParFiles))
        with open(self.MainWindow.WaterCalibrationParFiles, "w") as file:
            json.dump(self.WaterCalibrationPar, file,indent=4) 
        self.SaveCalibrationPar.setChecked(False)
        self.Warning
        self.Warning.setText('Calibration parameters saved for calibration type: '+CalibrationType)
        self.Warning.setStyleSheet("color: purple;")

    def _Showrecent(self):
        '''update the calibration figure'''
        self._UpdateFigure()
    def _ShowSpecifcDay(self):
        '''update the calibration figure'''
        self._UpdateFigure()
        
    def _Continue(self):
        '''Change the color of the continue button'''
        if self.Continue.isChecked():
            self.Continue.setStyleSheet("background-color : green;")
        else:
            self.Continue.setStyleSheet("background-color : none")
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
        valve='Left'
        valve_open_time=str(float(self.OpenLeftTime.text()))
        valve_open_interval=str(float(self.IntervalLeft.text()))
        cycle=str(float(self.CycleLeft.text()))
        try:
            total_water=float(self.TotalWaterSingleLeft.text())  
        except Exception as e:
            total_water=''
            logging.error(str(e))
        self._Save(valve=valve,valve_open_time=valve_open_time,valve_open_interval=valve_open_interval,cycle=cycle,total_water=total_water,tube_weight=0)
        self.SaveLeft.setStyleSheet("background-color : none")
        self.SaveLeft.setChecked(False)
    def _SaveRight(self):
        '''save the calibration result of the single point calibration (right valve)'''
        self.SaveRight.setStyleSheet("background-color : green;")
        QApplication.processEvents()
        valve='Right'
        valve_open_time=str(float(self.OpenRightTime.text()))
        valve_open_interval=str(float(self.IntervalRight.text()))
        cycle=str(float(self.CycleRight.text()))
        try:
            total_water=float(self.TotalWaterSingleRight.text()) 
        except Exception as e:
            total_water=''
            logging.error(str(e))
        self._Save(valve=valve,valve_open_time=valve_open_time,valve_open_interval=valve_open_interval,cycle=cycle,total_water=total_water,tube_weight=0)
        self.SaveRight.setStyleSheet("background-color : none")
        self.SaveRight.setChecked(False)
    def _CalibrationType(self):
        '''change the calibration parameters based on the calibration type'''
        # load the pre-stored calibration parameters
        self._LoadCaliPar()
        # set calibration parameters
        CalibrationType=self.CalibrationType.currentText()
        Keys=['TimeLeftMin','TimeLeftMax','StrideLeft','TimeRightMin','TimeRightMax','StrideRight','IntervalLeft_2','IntervalRight_2']
        widget_dict = {w.objectName(): w for w in self.findChildren((QtWidgets.QPushButton,QtWidgets.QLineEdit,QtWidgets.QTextEdit, QtWidgets.QComboBox,QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox))}
        # set attributes
        for K in Keys:
            for key in widget_dict.keys():
                try:
                    if key==K:
                        widget = widget_dict[key]
                        widget.setText(str(self.WaterCalibrationPar[CalibrationType][K]))
                except Exception as e:
                    logging.error(str(e))

    def _LoadCaliPar(self):
        '''load the pre-stored calibration parameters'''
        self.WaterCalibrationPar={}
        self.WaterCalibrationPar['Monthly']={}
        self.WaterCalibrationPar['Biweekly']={}
        if os.path.exists(self.MainWindow.WaterCalibrationParFiles):
            with open(self.MainWindow.WaterCalibrationParFiles, 'r') as f:
                self.WaterCalibrationPar = json.load(f)
        # if no parameters are stored, store default parameters
        SaveTag=0
        if self.WaterCalibrationPar['Monthly']=={}:
            self.WaterCalibrationPar['Monthly']['TimeLeftMin']=0.005
            self.WaterCalibrationPar['Monthly']['TimeLeftMax']=0.08
            self.WaterCalibrationPar['Monthly']['StrideLeft']=0.005
            self.WaterCalibrationPar['Monthly']['TimeRightMin']=0.005
            self.WaterCalibrationPar['Monthly']['TimeRightMax']=0.08
            self.WaterCalibrationPar['Monthly']['StrideRight']=0.005
            self.WaterCalibrationPar['Monthly']['IntervalLeft_2']=0.5
            SaveTag=1
        if self.WaterCalibrationPar['Biweekly']=={}:
            self.WaterCalibrationPar['Biweekly']['TimeLeftMin']=0.02
            self.WaterCalibrationPar['Biweekly']['TimeLeftMax']=0.06
            self.WaterCalibrationPar['Biweekly']['StrideLeft']=0.01
            self.WaterCalibrationPar['Biweekly']['TimeRightMin']=0.02
            self.WaterCalibrationPar['Biweekly']['TimeRightMax']=0.06
            self.WaterCalibrationPar['Biweekly']['StrideRight']=0.01
            self.WaterCalibrationPar['Biweekly']['IntervalLeft_2']=0.5
            SaveTag=1
        if SaveTag==1:
            if not os.path.exists(os.path.dirname(self.MainWindow.WaterCalibrationParFiles)):
                os.makedirs(os.path.dirname(self.MainWindow.WaterCalibrationParFiles))
            with open(self.MainWindow.WaterCalibrationParFiles, "w") as file:
                json.dump(self.WaterCalibrationPar, file,indent=4)

    def _StartCalibratingLeft(self):
        '''start the calibration loop of left valve'''
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        if self.StartCalibratingLeft.isChecked():
            # change button color
            self.StartCalibratingLeft.setStyleSheet("background-color : green;")
            QApplication.processEvents()
            # disable the right valve calibration
            self.StartCalibratingRight.setEnabled(False)
            self.label_15.setEnabled(False)
            self.label_14.setEnabled(False)
            self.label_17.setEnabled(False)
            self.label_18.setEnabled(False)
            self.label_22.setEnabled(False)
            self.label_16.setEnabled(False)
            self.label_25.setEnabled(False)
            self.TimeRightMin.setEnabled(False)
            self.TimeRightMax.setEnabled(False)
            self.StrideRight.setEnabled(False)
            self.CycleCaliRight.setEnabled(False)
            self.IntervalRight_2.setEnabled(False)
            self.WeightAfterRight.setEnabled(False)
            self.WeightBeforeRight.setEnabled(False)
            self.label_27.setEnabled(False)
            self.TubeWeightRight.setEnabled(False)
            # check the continue button
            self.Continue.setChecked(True)
            self.Continue.setStyleSheet("background-color : green;")
        else:
            self.StartCalibratingLeft.setStyleSheet("background-color : none")
            self.Warning.setText('Calibration was terminated!')
            self.Warning.setStyleSheet("color: purple;")
        N=0
        for current_valve_opentime in np.arange(float(self.TimeLeftMin.text()),float(self.TimeLeftMax.text())+0.0001,float(self.StrideLeft.text())):
            N=N+1
            if N==1:
                # disable TubeWeightRight
                self.TubeWeightLeft.setEnabled(False)
                self.label_26.setEnabled(False)
                if self.TubeWeightLeft.text()!='':
                    self.WeightBeforeLeft.setText(self.TubeWeightLeft.text())
                self.TubeWeightLeft.setText('')
            else:
                # enable TubeWeightRight
                self.TubeWeightLeft.setEnabled(True)
                self.label_26.setEnabled(True)
            while 1:
                if not self.StartCalibratingLeft.isChecked():
                    break
                if self.Continue.isChecked():
                    # start the open/close/delay cycle
                    for i in range(int(self.CycleCaliLeft.text())):
                        QApplication.processEvents()
                        while 1:
                            QApplication.processEvents()
                            if (not self.EmergencyStop.isChecked()) or (not self.StartCalibratingLeft.isChecked()):
                                break
                        if self.StartCalibratingLeft.isChecked():
                            # print the current calibration value
                            self.Warning.setText('You are calibrating Left valve: '+ str(round(float(current_valve_opentime),4))+'   Current cycle:'+str(i+1)+'/'+self.CycleCaliLeft.text())
                            self.Warning.setStyleSheet("color: purple;")
                            # set the valve open time
                            self.MainWindow.Channel.LeftValue(float(current_valve_opentime)*1000) 
                            # open the valve
                            self.MainWindow.Channel3.ManualWater_Left(int(1))
                            # delay
                            time.sleep(current_valve_opentime+float(self.IntervalLeft_2.text()))
                        else:
                            break
                self.Continue.setChecked(False)
                self.Continue.setStyleSheet("background-color : none")
                if i==range(int(self.CycleCaliLeft.text()))[-1]:
                    self.Warning.setText('Finish calibrating left valve: '+ str(round(float(current_valve_opentime),4))+'\nPlease enter the \"weight after(mg)\" and click the \"Continue\" button to start calibrating the next value.\nOr enter a negative value to repeat the current calibration.')
                self.Warning.setStyleSheet("color: purple;")
                self.TubeWeightLeft.setEnabled(True)
                self.label_26.setEnabled(True)
                # Waiting for the continue button to be clicked
                continuetag=1
                while 1:
                    QApplication.processEvents()
                    if not self.StartCalibratingLeft.isChecked():
                        break
                    if self.Continue.isChecked():
                        # save the calibration data after the current calibration is completed
                        if i==range(int(self.CycleCaliLeft.text()))[-1]:
                            # save the data
                            valve='Left'
                            valve_open_time=str(round(float(current_valve_opentime),4))
                            valve_open_interval=str(round(float(self.IntervalLeft_2.text()),4))
                            cycle=str(int(self.CycleCaliLeft.text()))
                            if self.WeightAfterLeft.text()=='':
                                self.Warning.setText('Please enter the measured \"weight after(mg)\" and click the continue button again!\nOr enter a negative value to repeat the current calibration.')
                                continuetag=0
                                self.Continue.setChecked(False)
                                self.Continue.setStyleSheet("background-color : none")
                            else:
                                try:
                                    continuetag=1
                                    total_water=float(self.WeightAfterLeft.text())
                                    tube_weight=self.WeightBeforeLeft.text()
                                    if tube_weight=='':
                                        tube_weight=0
                                    else:
                                        tube_weight=float(tube_weight)
                                    if total_water>=0:
                                        self._Save(valve=valve,valve_open_time=valve_open_time,valve_open_interval=valve_open_interval,cycle=cycle,total_water=total_water,tube_weight=tube_weight)
                                    # clear the weight before/tube/weight after
                                    self.WeightAfterLeft.setText('')
                                    if self.TubeWeightLeft.text()=='':
                                        self.WeightBeforeLeft.setText(str(total_water))
                                    else:
                                        self.WeightBeforeLeft.setText(self.TubeWeightLeft.text())
                                    self.TubeWeightLeft.setText('')
                                except Exception as e:
                                    logging.error(str(e))
                                    continuetag=0
                                    self.Warning.setText('Please enter the correct weight after(mg)/weight before(mg) and click the continue button again!\nOr enter a negative value to repeat the current calibration.')
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
            if self.StartCalibratingLeft.isChecked() and current_valve_opentime==np.arange(float(self.TimeLeftMin.text()),float(self.TimeLeftMax.text())+0.0001,float(self.StrideLeft.text()))[-1]:
                self.Warning.setText('Calibration is complete!')
                self._UpdateFigure()
        except Exception as e:
            logging.error(str(e))
            self.Warning.setText('Calibration is not complete! Parameters error!')
            self.Warning.setStyleSheet("color: purple;")
        # set the default valve open time
        self.MainWindow.Channel.LeftValue(float(self.MainWindow.LeftValue.text())*1000)
        # enable the right valve calibration
        self.StartCalibratingRight.setEnabled(True)
        self.label_15.setEnabled(True)
        self.label_14.setEnabled(True)
        self.label_17.setEnabled(True)
        self.label_18.setEnabled(True)
        self.label_22.setEnabled(True)
        self.label_13.setEnabled(True)
        self.label_16.setEnabled(True)
        self.label_25.setEnabled(True)
        self.TimeRightMin.setEnabled(True)
        self.TimeRightMax.setEnabled(True)
        self.StrideRight.setEnabled(True)
        self.CycleCaliRight.setEnabled(True)
        self.IntervalRight_2.setEnabled(True)
        self.WeightAfterRight.setEnabled(True)
        self.WeightBeforeRight.setEnabled(True) 
        self.label_27.setEnabled(True)
        self.TubeWeightRight.setEnabled(True)
        # change the color to be normal
        self.StartCalibratingLeft.setStyleSheet("background-color : none")
        self.StartCalibratingLeft.setChecked(False)
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
            self.TubeWeightLeft.setEnabled(False)
            # check the continue button
            self.Continue.setChecked(True)
            self.Continue.setStyleSheet("background-color : green;")
        else:
            self.StartCalibratingRight.setStyleSheet("background-color : none")
            self.Warning.setText('Calibration was terminated!')
            self.Warning.setStyleSheet("color: purple;")
        N=0
        for current_valve_opentime in np.arange(float(self.TimeRightMin.text()),float(self.TimeRightMax.text())+0.0001,float(self.StrideRight.text())):
            N=N+1
            if N==1:
                # disable TubeWeightRight
                self.TubeWeightRight.setEnabled(False)
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
                            self.Warning.setStyleSheet("color: purple;")
                            # set the valve open time
                            self.MainWindow.Channel.RightValue(float(current_valve_opentime)*1000) 
                            # open the valve
                            self.MainWindow.Channel3.ManualWater_Right(int(1))
                            # delay
                            time.sleep(current_valve_opentime+float(self.IntervalRight_2.text()))
                        else:
                            break
                self.Continue.setChecked(False)
                self.Continue.setStyleSheet("background-color : none")
                if i==range(int(self.CycleCaliRight.text()))[-1]:
                    self.Warning.setText('Finish calibrating Right valve: '+ str(round(float(current_valve_opentime),4))+'\nPlease enter the \"weight after(mg)\" and click the \"Continue\" button to start calibrating the next value.\nOr enter a negative value to repeat the current calibration.')
                    self.Warning.setStyleSheet("color: purple;")
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
            self.Warning.setStyleSheet("color: purple;")

        # set the default valve open time
        self.MainWindow.Channel.RightValue(float(self.MainWindow.RightValue.text())*1000)
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
        self.StartCalibratingRight.setChecked(False)
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
            self.MainWindow.Channel.LeftValue(float(1000)*1000) 
            # open the valve
            self.MainWindow.Channel3.ManualWater_Left(int(1))
        else:
            # change button color
            self.OpenLeftForever.setStyleSheet("background-color : none")
            # close the valve 
            self.MainWindow.Channel.LeftValue(float(0.001)*1000)
            self.MainWindow.Channel3.ManualWater_Left(int(1))
            # set the default valve open time
            self.MainWindow.Channel.LeftValue(float(self.MainWindow.LeftValue.text())*1000)

    def _OpenRightForever(self):
        '''Open the right valve forever'''
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        if self.OpenRightForever.isChecked():
            # change button color
            self.OpenRightForever.setStyleSheet("background-color : green;")
            # set the valve open time
            self.MainWindow.Channel.RightValue(float(1000)*1000) 
            # open the valve
            self.MainWindow.Channel3.ManualWater_Right(int(1))
        else:
            # change button color
            self.OpenRightForever.setStyleSheet("background-color : none")
            # close the valve 
            self.MainWindow.Channel.RightValue(float(0.001)*1000)
            self.MainWindow.Channel3.ManualWater_Right(int(1))
            # set the default valve open time
            self.MainWindow.Channel.RightValue(float(self.MainWindow.RightValue.text())*1000)

    def _OpenLeft(self):    
        '''Calibration of left valve in a different thread'''
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        if self.OpenLeft.isChecked():
            # change button color
            self.OpenLeft.setStyleSheet("background-color : green;")
        else:
            self.OpenLeft.setStyleSheet("background-color : none")
        # start the open/close/delay cycle
        for i in range(int(self.CycleLeft.text())):
            QApplication.processEvents()
            if self.OpenLeft.isChecked():
                # set the valve open time
                self.MainWindow.Channel.LeftValue(float(self.OpenLeftTime.text())*1000) 
                # open the valve
                self.MainWindow.Channel3.ManualWater_Left(int(1))
                # delay
                time.sleep(float(self.OpenLeftTime.text())+float(self.IntervalLeft.text()))
            else:
                break
        self.OpenLeft.setChecked(False)        
        # set the default valve open time
        self.MainWindow.Channel.LeftValue(float(self.MainWindow.LeftValue.text())*1000)
    def _OpenRight(self):
        '''Calibration of right valve'''
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        if self.OpenRight.isChecked():
            # change button color
            self.OpenRight.setStyleSheet("background-color : green;")
        else:
            self.OpenRight.setStyleSheet("background-color : none")
        # start the open/close/delay cycle
        for i in range(int(self.CycleRight.text())):
            QApplication.processEvents()
            if self.OpenRight.isChecked():
                # set the valve open time
                self.MainWindow.Channel.RightValue(float(self.OpenRightTime.text())*1000) 
                # open the valve
                self.MainWindow.Channel3.ManualWater_Right(int(1))
                # delay
                time.sleep(float(self.OpenRightTime.text())+float(self.IntervalRight.text()))
            else:
                break
        self.OpenRight.setChecked(False)  
        # set the default valve open time
        self.MainWindow.Channel.RightValue(float(self.MainWindow.RightValue.text())*1000)

class CameraDialog(QDialog):
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        uic.loadUi('Camera.ui', self)
        
        self.MainWindow=MainWindow
        self._connectSignalsSlots()
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
                subprocess.Popen(['explorer', os.path.join(os.path.dirname(self.MainWindow.Ot_log_folder),'VideoFolder')])
            except Exception as e:
                logging.error(str(e))
                self.WarningLabelOpenSave.setText('No logging folder found!')
                self.WarningLabelOpenSave.setStyleSheet("color: purple;")
        else:
            self.WarningLabelOpenSave.setText('No logging folder found!')
            self.WarningLabelOpenSave.setStyleSheet("color: purple;")

    def _RestartLogging(self):
        '''Restart the logging (create a new logging folder)'''
        self.MainWindow._ConnectBonsai()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        if self.CollectVideo.currentText()=='Yes':
            # formal logging
            self.MainWindow.Ot_log_folder=self.MainWindow._restartlogging()
        else:
            # temporary logging
            self.MainWindow.Ot_log_folder=self.MainWindow._restartlogging(self.MainWindow.temporary_video_folder)
        self.WarningLabelLogging.setText('Logging has restarted!')
        self.WarningLabelLogging.setStyleSheet("color: purple;")

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
            self.MainWindow.Channel.CameraFrequency(int(self.FrameRate.text()))
            if self.AutoControl.currentText()=='No':
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
            # start the video triggers
            self.MainWindow.Channel.CameraControl(int(1))
            self.MainWindow.WarningLabelCamera.setText('Camera is on!')
            self.MainWindow.WarningLabelCamera.setStyleSheet("color: purple;")
            self.WarningLabelCameraOn.setText('Camera is on!')
            self.WarningLabelCameraOn.setStyleSheet("color: purple;")
            self.WarningLabelLogging.setText('')
            self.WarningLabelLogging.setStyleSheet("color: None;")
            self.WarningLabelOpenSave.setText('')
        else:
            self.StartCamera.setStyleSheet("background-color : none")
            self.MainWindow.Channel.CameraControl(int(2))
            self.MainWindow.WarningLabelCamera.setText('Camera is off!')
            self.MainWindow.WarningLabelCamera.setStyleSheet("color: purple;")
            self.WarningLabelCameraOn.setText('Camera is off!')
            self.WarningLabelCameraOn.setStyleSheet("color: purple;")
            self.WarningLabelLogging.setText('')
            self.WarningLabelLogging.setStyleSheet("color: None;")
            self.WarningLabelOpenSave.setText('')
    
    def _SaveVideoData(self):
        '''Save the video data'''
        self.MainWindow._GetSaveFileName()
        video_folder=self.MainWindow.video_folder
        video_folder=os.path.join(video_folder,self.MainWindow.Tower.currentText(),self.MainWindow.AnimalName.text())
        if not os.path.exists(video_folder):
            os.makedirs(video_folder)
        base_name=os.path.splitext(os.path.basename(self.MainWindow.SaveFileJson))[0]
        
        side_camera_file=os.path.join(video_folder,base_name+'_side_camera.avi')
        bottom_camera_file=os.path.join(video_folder,base_name+'_bottom_camera.avi')
        side_camera_csv=os.path.join(video_folder,base_name+'_side_camera.csv')
        bottom_camera_csv=os.path.join(video_folder,base_name+'_bottom_camera.csv')
        if is_file_in_use(side_camera_file) or is_file_in_use(bottom_camera_file) or is_file_in_use(side_camera_csv) or is_file_in_use(bottom_camera_csv):              
            self.WarningLabelFileIsInUse.setText('File is in use. Please restart the bonsai!')
            self.WarningLabelFileIsInUse.setStyleSheet("color: purple;")
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
            self.WarningLabelFileIsInUse.setStyleSheet("color: purple;")
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

class ManipulatorDialog(QDialog):
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        uic.loadUi('Manipulator.ui', self)

class MotorStageDialog(QDialog):
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        uic.loadUi('MotorStage.ui', self)
        
        self.MainWindow=MainWindow

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
    def _connectSignalsSlots(self):
        self.Open.clicked.connect(self._Open)
        self.KeepOpen.clicked.connect(self._KeepOpen)
        self.CopyFromOpto.clicked.connect(self._CopyFromOpto)
        self.Save.clicked.connect(self._Save)
        self.Capture.clicked.connect(self._Capture)
        self.Laser_1.currentIndexChanged.connect(self._Laser_1)
        self.Protocol_1.activated.connect(self._activated_1)
        self.Protocol_1.currentIndexChanged.connect(self._activated_1)
        self.Flush_DO0.clicked.connect(self._FLush_DO0)
        self.Flush_DO1.clicked.connect(self._FLush_DO1)
        self.Flush_DO2.clicked.connect(self._FLush_DO2)
        self.Flush_DO3.clicked.connect(self._FLush_DO3)
        self.Flush_Port2.clicked.connect(self._FLush_Port2)
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

    def _Laser_1(self):
        self._Laser(1)
    def _activated_1(self):
        self._activated(1)
    def _activated(self,Numb):
        '''enable/disable items based on protocols and laser start/end'''
        Inactlabel1=15 # pulse duration
        Inactlabel2=13 # frequency
        Inactlabel3=14 # Ramping down
        if eval('self.Protocol_'+str(Numb)+'.currentText()')=='Sine':
            eval('self.label'+str(Numb)+'_'+str(Inactlabel1)+'.setEnabled('+str(False)+')')
            eval('self.PulseDur_'+str(Numb)+'.setEnabled('+str(False)+')')
            eval('self.label'+str(Numb)+'_'+str(Inactlabel2)+'.setEnabled('+str(True)+')')
            eval('self.Frequency_'+str(Numb)+'.setEnabled('+str(True)+')')
            eval('self.label'+str(Numb)+'_'+str(Inactlabel3)+'.setEnabled('+str(True)+')')
            eval('self.RD_'+str(Numb)+'.setEnabled('+str(True)+')')
        if eval('self.Protocol_'+str(Numb)+'.currentText()')=='Pulse':
            eval('self.label'+str(Numb)+'_'+str(Inactlabel1)+'.setEnabled('+str(True)+')')
            eval('self.PulseDur_'+str(Numb)+'.setEnabled('+str(True)+')')
            eval('self.label'+str(Numb)+'_'+str(Inactlabel2)+'.setEnabled('+str(True)+')')
            eval('self.Frequency_'+str(Numb)+'.setEnabled('+str(True)+')')
            eval('self.label'+str(Numb)+'_'+str(Inactlabel3)+'.setEnabled('+str(False)+')')
            eval('self.RD_'+str(Numb)+'.setEnabled('+str(False)+')')
        if eval('self.Protocol_'+str(Numb)+'.currentText()')=='Constant':
            eval('self.label'+str(Numb)+'_'+str(Inactlabel1)+'.setEnabled('+str(False)+')')
            eval('self.PulseDur_'+str(Numb)+'.setEnabled('+str(False)+')')
            eval('self.label'+str(Numb)+'_'+str(Inactlabel2)+'.setEnabled('+str(False)+')')
            eval('self.Frequency_'+str(Numb)+'.setEnabled('+str(False)+')')
            eval('self.label'+str(Numb)+'_'+str(Inactlabel3)+'.setEnabled('+str(True)+')')
            eval('self.RD_'+str(Numb)+'.setEnabled('+str(True)+')')
    
    def _Laser(self,Numb):
        ''' enable/disable items based on laser (blue/green/orange/red/NA)'''
        Inactlabel=[2,3,5,12,13,14,15]
        if eval('self.Laser_'+str(Numb)+'.currentText()')=='NA':
            Label=False
        else:
            Label=True
        eval('self.Location_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.LaserPower_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.Duration_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.Protocol_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.Frequency_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.RD_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.PulseDur_'+str(Numb)+'.setEnabled('+str(Label)+')')
        for i in Inactlabel:
            eval('self.label'+str(Numb)+'_'+str(i)+'.setEnabled('+str(Label)+')')
        if eval('self.Laser_'+str(Numb)+'.currentText()')!='NA':    
            eval('self._activated_'+str(Numb)+'()')
    
    def _GetLaserWaveForm(self):
        '''Get the waveform of the laser. It dependens on color/duration/protocol(frequency/RD/pulse duration)/locations/laser power'''
        N=str(1)
        # CLP, current laser parameter
        self.CLP_Color=eval('self.LC_Laser_'+N)
        self.CLP_Location=eval('self.LC_Location_'+N)
        self.CLP_LaserPower=eval('self.LC_LaserPower_'+N)
        self.CLP_Duration=float(eval('self.LC_Duration_'+N))
        self.CLP_Protocol=eval('self.LC_Protocol_'+N)
        self.CLP_Frequency=float(eval('self.LC_Frequency_'+N))
        self.CLP_RampingDown=float(eval('self.LC_RD_'+N))
        self.CLP_PulseDur=eval('self.LC_PulseDur_'+N)
        self.CLP_SampleFrequency=float(self.LC_SampleFrequency)
        self.CLP_CurrentDuration=self.CLP_Duration
        self.CLP_InputVoltage=float(self.voltage.text())
        # generate the waveform based on self.CLP_CurrentDuration and Protocol, Frequency, RampingDown, PulseDur
        self._GetLaserAmplitude()
        # dimension of self.CurrentLaserAmplitude indicates how many locations do we have
        for i in range(len(self.CurrentLaserAmplitude)):
            # in some cases the other paramters except the amplitude could also be different
            self._ProduceWaveForm(self.CurrentLaserAmplitude[i])
            setattr(self, 'WaveFormLocation_' + str(i+1), self.my_wave)
            setattr(self, f"Location{i+1}_Size", getattr(self, f"WaveFormLocation_{i+1}").size)
            #send waveform and send the waveform size
            eval('self.MainWindow.Channel.Location'+str(i+1)+'_Size'+'(int(self.Location'+str(i+1)+'_Size))')
            eval('self.MainWindow.Channel4.WaveForm' + str(1)+'_'+str(i+1)+'('+'str('+'self.WaveFormLocation_'+str(i+1)+'.tolist()'+')[1:-1]'+')')
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
                    self.win.WarningLabel.setStyleSheet("color: purple;")
                else:
                    Constant=np.ones(int((self.CLP_CurrentDuration-self.CLP_RampingDown)*self.CLP_SampleFrequency))
                    RD=np.arange(1,0, -1/(np.shape(self.my_wave)[0]-np.shape(Constant)[0]))
                    RampingDown = np.concatenate((Constant, RD), axis=0)
                    self.my_wave=self.my_wave*RampingDown
            self.my_wave=np.append(self.my_wave,[0,0])
        elif self.CLP_Protocol=='Pulse':
            if self.CLP_PulseDur=='NA':
                self.win.WarningLabel.setText('Pulse duration is NA!')
                self.win.WarningLabel.setStyleSheet("color: purple;")
            else:
                self.CLP_PulseDur=float(self.CLP_PulseDur)
                PointsEachPulse=int(self.CLP_SampleFrequency*self.CLP_PulseDur)
                PulseIntervalPoints=int(1/self.CLP_Frequency*self.CLP_SampleFrequency-PointsEachPulse)
                if PulseIntervalPoints<0:
                    self.win.WarningLabel.setText('Pulse frequency and pulse duration are not compatible!')
                    self.win.WarningLabel.setStyleSheet("color: purple;")
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
                    self.win.WarningLabel.setStyleSheet("color: purple;")
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
                    self.win.WarningLabel.setStyleSheet("color: purple;")
                else:
                    Constant=np.ones(int((self.CLP_CurrentDuration-self.CLP_RampingDown)*self.CLP_SampleFrequency))
                    RD=np.arange(1,0, -1/(np.shape(self.my_wave)[0]-np.shape(Constant)[0]))
                    RampingDown = np.concatenate((Constant, RD), axis=0)
                    self.my_wave=self.my_wave*RampingDown
            self.my_wave=np.append(self.my_wave,[0,0])
        else:
            self.win.WarningLabel.setText('Unidentified optogenetics protocol!')
            self.win.WarningLabel.setStyleSheet("color: purple;")

    def _GetLaserAmplitude(self):
        '''the voltage amplitude dependens on Protocol, Laser Power, Laser color, and the stimulation locations<>'''
        if self.CLP_Location=='Left':
            self.CurrentLaserAmplitude=[self.CLP_InputVoltage,0]
        elif self.CLP_Location=='Right':
            self.CurrentLaserAmplitude=[0,self.CLP_InputVoltage]
        elif self.CLP_Location=='Both':
            self.CurrentLaserAmplitude=[self.CLP_InputVoltage,self.CLP_InputVoltage]
        else:
            self.win.WarningLabel.setText('No stimulation location defined!')
            self.win.WarningLabel.setStyleSheet("color: purple;")
   
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
        # send the trigger source. It's '/Dev1/PFI0' ( P2.0 of NIdaq USB6002) by default 
        self.MainWindow.Channel.TriggerSource('/Dev1/PFI0')
        # start generating waveform in bonsai
        self.MainWindow.Channel.OptogeneticsCalibration(int(1))
    def _CopyFromOpto(self):
        '''Copy the optogenetics parameters'''
        N=[]
        for i in range(100):
            variable_name = "Laser_" + str(i)
            if hasattr(self.MainWindow.Opto_dialog,variable_name):
                current_text = self.MainWindow.Opto_dialog.__getattribute__(variable_name).currentText()
                if current_text !='NA':
                    N=i
                    break
        if N==[]:
            return
        self.Duration_1.setText(self.MainWindow.Opto_dialog.__getattribute__("Duration_" + str(N)).text())
        self.Frequency_1.setText(self.MainWindow.Opto_dialog.__getattribute__("Frequency_" + str(N)).currentText())
        self.RD_1.setText(self.MainWindow.Opto_dialog.__getattribute__("RD_" + str(N)).text())
        self.PulseDur_1.setText(self.MainWindow.Opto_dialog.__getattribute__("PulseDur_" + str(N)).text())
        self.Laser_1.setCurrentIndex(self.MainWindow.Opto_dialog.__getattribute__("Laser_" + str(N)).currentIndex())
        self.Location_1.setCurrentIndex(self.MainWindow.Opto_dialog.__getattribute__("Location_" + str(N)).currentIndex())
        self.LaserPower_1.clear()
        items=[]
        for index in range(self.MainWindow.Opto_dialog.__getattribute__("LaserPower_" + str(N)).count()):
            item = self.MainWindow.Opto_dialog.__getattribute__("LaserPower_" + str(N)).itemText(index)
            items.append(item)
        self.LaserPower_1.addItems(items)
        self.LaserPower_1.setCurrentIndex(self.MainWindow.Opto_dialog.__getattribute__("LaserPower_" + str(N)).currentIndex())
        self.Protocol_1.setCurrentIndex(self.MainWindow.Opto_dialog.__getattribute__("Protocol_" + str(N)).currentIndex())

    def _Capture(self):
        '''Save the measured laser power'''
        self.Capture.setStyleSheet("background-color : green;")
        QApplication.processEvents()
        self._GetTrainingParameters(self.MainWindow)
        self.Warning.setText('')
        if self.Location_1.currentText()=='Both':
            self.Warning.setText('Data not captured! Please choose left or right, not both!')
            self.Warning.setStyleSheet("color: purple;")
            self.Warning.setAlignment(Qt.AlignCenter)
            return
        if self.LaserPowerMeasured.text()=='':
            self.Warning.setText('Data not captured! Please enter power measured!')
            self.Warning.setStyleSheet("color: purple;")
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
            self.Warning.setStyleSheet("color: purple;")
            self.Warning.setAlignment(Qt.AlignCenter)
            return
        # delete invalid indices
        LCM_MeasureTime=self.LCM_MeasureTime.copy()
        LCM_Laser_1=self.LCM_Laser_1.copy()
        LCM_Protocol_1=self.LCM_Protocol_1.copy()
        LCM_Frequency_1=self.LCM_Frequency_1.copy()
        LCM_LaserPowerMeasured=self.LCM_LaserPowerMeasured.copy()
        LCM_Location_1=self.LCM_Location_1.copy()
        LCM_voltage=self.LCM_voltage.copy()
        empty_indices = [index for index, value in enumerate(self.LCM_LaserPowerMeasured) if value == '']
        both_indices = [index for index, value in enumerate(self.LCM_Location_1) if value == 'Both']
        delete_indices=both_indices+empty_indices
        delete_indices=list(set(delete_indices))
        delete_indices.sort(reverse=True)
        for index in delete_indices:
            del LCM_MeasureTime[index]
            del LCM_Laser_1[index]
            del LCM_Protocol_1[index]
            del LCM_Frequency_1[index]
            del LCM_LaserPowerMeasured[index]
            del LCM_Location_1[index]
            del LCM_voltage[index]
        LCM_MeasureTime_date=[]
        for i in range(len(LCM_MeasureTime)):
            LCM_MeasureTime_date.append(LCM_MeasureTime[i].split()[0])
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
            laser_colors= self._extract_elements(LCM_Laser_1,current_date_ind) 
            laser_colors_unique= list(set(laser_colors))
            for j in range(len(laser_colors_unique)):
                current_color=laser_colors_unique[j]
                current_color_ind=[index for index, value in enumerate(laser_colors) if value == current_color]
                Protocols= self._extract_elements(LCM_Protocol_1,current_color_ind)
                Protocols_unique=list(set(Protocols))
                for k in range(len(Protocols_unique)):
                    current_protocol=Protocols_unique[k]
                    current_protocol_ind=[index for index, value in enumerate(Protocols) if value == current_protocol]
                    if current_protocol=='Sine':
                        Frequency=self._extract_elements(LCM_Frequency_1,current_protocol_ind)
                        Frequency_unique=list(set(Frequency))
                        for m in range(len(Frequency_unique)):
                            current_frequency=Frequency_unique[m]
                            current_frequency_ind=[index for index, value in enumerate(Frequency) if value == current_frequency]
                            input_voltages= self._extract_elements(LCM_voltage,current_frequency_ind)
                            input_voltages_unique=list(set(input_voltages))
                            ItemsLeft=[]
                            ItemsRight=[]
                            for n in range(len(input_voltages_unique)):
                                current_voltage=input_voltages_unique[n]
                                left_laser_ind=[]
                                right_laser_ind=[]
                                for k in range(len(input_voltages)):
                                    if input_voltages[k]==current_voltage and LCM_Location_1[k]=='Left':
                                        left_laser_ind.append(k)
                                    elif input_voltages[k]==current_voltage and LCM_Location_1[k]=='Right':
                                        right_laser_ind.append(k)
                                left_measured_power=self._extract_elements(LCM_LaserPowerMeasured,left_laser_ind) 
                                right_measured_power=self._extract_elements(LCM_LaserPowerMeasured,right_laser_ind) 
                                left_measured_power_mean=self._getmean(left_measured_power)
                                right_measured_power_mean=self._getmean(right_measured_power)
                                ItemsLeft.append([float(current_voltage), left_measured_power_mean])
                                ItemsRight.append([float(current_voltage), right_measured_power_mean])
                            # Check and assign items to the nested dictionary
                            if current_date_name not in LaserCalibrationResults:
                                LaserCalibrationResults[current_date_name] = {}
                            if current_color not in LaserCalibrationResults[current_date_name]:
                                LaserCalibrationResults[current_date_name][current_color] = {}
                            if current_protocol not in LaserCalibrationResults[current_date_name][current_color]:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol] = {}
                            if current_frequency not in LaserCalibrationResults[current_date_name][current_color][current_protocol]:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency] = {}
                            if 'Left' not in LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency]:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency]['Left'] = {}
                            if 'Right' not in LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency]:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency]['Right'] = {}
                            if 'LaserPowerVoltage' not in LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency]['Left']:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency]['Left']['LaserPowerVoltage']=ItemsLeft
                            else:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency]['Left']['LaserPowerVoltage']=self._unique(LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency]['Left']['LaserPowerVoltage']+ItemsLeft)

                            if 'LaserPowerVoltage' not in LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency]['Right']:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency]['Right']['LaserPowerVoltage']=ItemsRight
                            else:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency]['Right']['LaserPowerVoltage']=self._unique(LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency]['Right']['LaserPowerVoltage']+ItemsRight)
                    elif current_protocol=='Constant' or current_protocol=='Pulse':
                            input_voltages= self._extract_elements(LCM_voltage,current_protocol_ind)
                            input_voltages_unique=list(set(input_voltages))
                            ItemsLeft=[]
                            ItemsRight=[]
                            for n in range(len(input_voltages_unique)):
                                current_voltage=input_voltages_unique[n]
                                left_laser_ind=[]
                                right_laser_ind=[]
                                for k in range(len(input_voltages)):
                                    if input_voltages[k]==current_voltage and LCM_Location_1[k]=='Left':
                                        left_laser_ind.append(k)
                                    elif input_voltages[k]==current_voltage and LCM_Location_1[k]=='Right':
                                        right_laser_ind.append(k)
                                left_measured_power=self._extract_elements(LCM_LaserPowerMeasured,left_laser_ind) 
                                right_measured_power=self._extract_elements(LCM_LaserPowerMeasured,right_laser_ind) 
                                left_measured_power_mean=self._getmean(left_measured_power)
                                right_measured_power_mean=self._getmean(right_measured_power)
                                ItemsLeft.append([float(current_voltage), left_measured_power_mean])
                                ItemsRight.append([float(current_voltage), right_measured_power_mean])
                            # Check and assign items to the nested dictionary
                            if current_date_name not in LaserCalibrationResults:
                                LaserCalibrationResults[current_date_name] = {}
                            if current_color not in LaserCalibrationResults[current_date_name]:
                                LaserCalibrationResults[current_date_name][current_color] = {}
                            if current_protocol not in LaserCalibrationResults[current_date_name][current_color]:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol] = {}
                            if 'Left' not in LaserCalibrationResults[current_date_name][current_color][current_protocol]:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol]['Left']={}
                            if 'Right' not in LaserCalibrationResults[current_date_name][current_color][current_protocol]:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol]['Right']={}
                            if 'LaserPowerVoltage' not in LaserCalibrationResults[current_date_name][current_color][current_protocol]['Left']:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol]['Left']['LaserPowerVoltage']=ItemsLeft
                            else:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol]['Left']['LaserPowerVoltage']=self._unique(LaserCalibrationResults[current_date_name][current_color][current_protocol]['Left']['LaserPowerVoltage']+ItemsLeft)
                            if 'LaserPowerVoltage' not in LaserCalibrationResults[current_date_name][current_color][current_protocol]['Right']:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol]['Right']['LaserPowerVoltage']=ItemsRight
                            else:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol]['Right']['LaserPowerVoltage']=self._unique(LaserCalibrationResults[current_date_name][current_color][current_protocol]['Right']['LaserPowerVoltage']+ItemsRight)
                           
                            if current_protocol=='Constant':# copy results of constant to pulse 
                                if 'Pulse' not in LaserCalibrationResults[current_date_name][current_color]:
                                    LaserCalibrationResults[current_date_name][current_color]['Pulse'] = {}
                                if 'Left' not in LaserCalibrationResults[current_date_name][current_color]['Pulse']:
                                    LaserCalibrationResults[current_date_name][current_color]['Pulse']['Left']={}
                                if 'Right' not in LaserCalibrationResults[current_date_name][current_color]['Pulse']:
                                    LaserCalibrationResults[current_date_name][current_color]['Pulse']['Right']={}
                                if 'LaserPowerVoltage' not in LaserCalibrationResults[current_date_name][current_color]['Pulse']['Left']:
                                    LaserCalibrationResults[current_date_name][current_color]['Pulse']['Left']['LaserPowerVoltage']=ItemsLeft
                                else:
                                    LaserCalibrationResults[current_date_name][current_color]['Pulse']['Left']['LaserPowerVoltage']=self._unique(LaserCalibrationResults[current_date_name][current_color]['Pulse']['Left']['LaserPowerVoltage']+ItemsLeft)
                                if 'LaserPowerVoltage' not in LaserCalibrationResults[current_date_name][current_color]['Pulse']['Right']:
                                    LaserCalibrationResults[current_date_name][current_color]['Pulse']['Right']['LaserPowerVoltage']=ItemsRight
                                else:
                                    LaserCalibrationResults[current_date_name][current_color]['Pulse']['Right']['LaserPowerVoltage']=self._unique(LaserCalibrationResults[current_date_name][current_color]['Pulse']['Right']['LaserPowerVoltage']+ItemsRight)
        
        # save to json file
        if not os.path.exists(os.path.dirname(self.MainWindow.LaserCalibrationFiles)):
            os.makedirs(os.path.dirname(self.MainWindow.LaserCalibrationFiles))
        with open(self.MainWindow.LaserCalibrationFiles, "w") as file:
            json.dump(LaserCalibrationResults, file,indent=4)
        self.Warning.setText('')
        if LaserCalibrationResults=={}:
            self.Warning.setText('Data not saved! Please enter power measured!')
            self.Warning.setStyleSheet("color: purple;")
            self.Warning.setAlignment(Qt.AlignCenter)
            return
        self.MainWindow.LaserCalibrationResults=LaserCalibrationResults
        self.MainWindow._GetLaserCalibration()
        self.MainWindow.Opto_dialog._Laser_1()
        self.MainWindow.Opto_dialog._Laser_2()
        self.MainWindow.Opto_dialog._Laser_3()
        self.MainWindow.Opto_dialog._Laser_4()
        time.sleep(0.01)
        self.Save.setStyleSheet("background-color : none")
        self.Save.setChecked(False)
    def _unique(self,input):
        '''average the laser power with the same input voltage'''
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
            QApplication.processEvents()
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
        self.svg_rules = None
        self.svg_paras = None        

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
        self.pushButton_show_rules_in_browser.clicked.connect(
            self._show_rules_in_browser
        )
        self.pushButton_show_paras_in_browser.clicked.connect(
            self._show_paras_in_browser
        )
        self.pushButton_show_all_training_history.clicked.connect(
            self._show_all_training_history
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
            self.label_subject_id.setStyleSheet("color: purple;")
            
            # disable some stuff
            self.checkBox_override_stage.setChecked(False)
            self.checkBox_override_stage.setEnabled(False)
            self.pushButton_apply_auto_train_paras.setEnabled(False)
            
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
                self.curriculum_in_use = self.curriculum_manager.get_curriculum(
                    curriculum_name=self.last_session['curriculum_name'],
                    curriculum_schema_version=self.last_session['curriculum_schema_version'],
                    curriculum_version=self.last_session['curriculum_version'],
                )['curriculum']
            
                # update stage info
                self.label_last_actual_stage.setText(str(self.last_session['current_stage_actual']))
                self.label_next_stage_suggested.setText(str(self.last_session['next_stage_suggested']))
                self.label_next_stage_suggested.setStyleSheet("color: black;")
            else:
                self.label_last_actual_stage.setText('irrelevant (curriculum overridden)')
                self.label_next_stage_suggested.setText('irrelevant')
                self.label_next_stage_suggested.setStyleSheet("color: purple;")
                
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
            
            # disable apply curriculum                        
            self.pushButton_apply_curriculum.setEnabled(False)
            self._remove_border_curriculum_selection()
            
            # Reset override curriculum
            self.checkBox_override_curriculum.setChecked(False)
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
                                 'Error',
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
            saved_curriculums_local=self.MainWindow.default_saveFolder + '/curriculum_manager/',
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
        
        # Retrieve svgs
        self.svg_rules = self.selected_curriculum['diagram_rules_name']
        self.svg_paras = self.selected_curriculum['diagram_paras_name']
                        
    def _show_rules_in_browser(self):
        if self.svg_rules is not None:
            webbrowser.open(self.svg_rules)
            
    def _show_paras_in_browser(self):
        if self.svg_paras is not None:
            webbrowser.open(self.svg_paras)
            
    def _show_all_training_history(self):
        all_progress_plotly = self.auto_train_manager.plot_all_progress(
            x_axis='session',
            sort_by='subject_id',
            sort_order='descending',
            if_show_fig=True
        )
        all_progress_plotly.show()

        
    def _update_available_training_stages(self):
        if self.curriculum_in_use is not None:
            available_training_stages = [v.name for v in 
                                        self.curriculum_in_use.parameters.keys()]
        else:
            available_training_stages = []
            
        self.comboBox_override_stage.clear()
        self.comboBox_override_stage.addItems(available_training_stages)
                
    def _override_stage_clicked(self, state):
        if state:
            self.comboBox_override_stage.setEnabled(True)
        else:
            self.comboBox_override_stage.setEnabled(False)
        self._update_stage_to_apply()
        
    def _override_curriculum_clicked(self, state):
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
        elif self.last_session is not None:
            self.stage_in_use = self.last_session['next_stage_suggested']
        else:
            self.stage_in_use = 'unknown training stage'
        
        self.pushButton_apply_auto_train_paras.setText(
            f"Apply and lock\n"
            + '\n'.join(get_curriculum_string(self.curriculum_in_use).split('(')).strip(')') 
            + f"\n{self.stage_in_use}"
        )
                
    def _apply_curriculum(self):
        # Check if a curriculum is selected
        if not hasattr(self, 'selected_curriculum') or self.selected_curriculum is None:
            QMessageBox.critical(self, "Error", "Please select a curriculum!")
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
                        next_stage_suggested='STAGE_1',
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
                QMessageBox.information(self, "Info", "Selected curriculum is the same as the one in use. No change is made.")
                return
            else:
                # Confirm with the user about overriding the curriculum
                reply = QMessageBox.question(self, "Confirm",
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
            
    def update_auto_train_lock(self, engaged):
        if engaged:
            # Update the flag
            self.auto_train_engaged = True

            # Get parameter settings
            paras = self.curriculum_in_use.parameters[
                TrainingStage[self.stage_in_use]
            ]
            
            # Convert to GUI format and set the parameters
            paras_dict = paras.to_GUI_format()
            self.widgets_locked_by_auto_train = self._set_training_parameters(
                paras_dict=paras_dict,
                if_press_enter=True
            )
            
            if self.widgets_locked_by_auto_train == []:  # Error in setting parameters
                self.update_auto_train_lock(engaged=False)  # Uncheck the "apply" button
                return
                
            self.widgets_locked_by_auto_train.extend(
                [self.MainWindow.TrainingStage,
                self.MainWindow.SaveTraining]
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
                                    
        else:
            # Update the flag
            self.auto_train_engaged = False
            
            # Uncheck the button (when this is called from the MainWindow, not from actual button click)
            self.pushButton_apply_auto_train_paras.setChecked(False)

            # Unlock the previously engaged widgets
            for widget in self.widgets_locked_by_auto_train:
                widget.setEnabled(True)
                # clear style
                widget.setStyleSheet("")
            self.MainWindow.TrainingParameters.setStyleSheet("")
            self.MainWindow.label_auto_train_stage.setText("off curriculum")
            self.MainWindow.label_auto_train_stage.setStyleSheet("color: purple;")


            # enable override
            self.checkBox_override_stage.setEnabled(True)
            self.comboBox_override_stage.setEnabled(self.checkBox_override_stage.isChecked())


    def _set_training_parameters(self, paras_dict, if_press_enter=False):
        """Accepts a dictionary of parameters and set the GUI accordingly
        Trying to refactor Foraging.py's _TrainingStage() here.
        
        paras_dict: a dictionary of parameters following Xinxin's convention
        if_press_enter: if True, press enter after setting the parameters
        """
        # Track widgets that have been set by auto training
        widgets_set = []
        
        # Loop over para_dict and try to set the values
        for key, value in paras_dict.items():
            if key == 'task':
                widget_task = self.MainWindow.Task
                task_ind = widget_task.findText(paras_dict['task'])
                if task_ind < 0:
                    logger.error(f"Task {paras_dict['task']} not found!")
                    QMessageBox.critical(self, "Error", f'''Task "{paras_dict['task']}" not found. Check the curriculum!''')
                    return [] # Return an empty list without setting anything
                else:
                    widget_task.setCurrentIndex(task_ind)
                    logger.info(f"Task is set to {paras_dict['task']}")
                    widgets_set.append(widget_task)
                    continue  # Continue to the next parameter
            
            # For other parameters, try to find the widget and set the value               
            widget = self.MainWindow.findChild(QObject, key)
            if widget is None:
                logger.info(f''' Widget "{key}" not found. skipped...''')
                continue
            
            # If the parameter is disabled by the GUI in the first place, skip it
            # For example, the field "uncoupled reward" in a coupled task.
            if not widget.isEnabled():
                logger.info(f''' Widget "{key}" has been disabled by the GUI. skipped...''')
                continue
            
            # Set the value according to the widget type
            if isinstance(widget, (QtWidgets.QLineEdit, 
                                   QtWidgets.QTextEdit)):
                widget.setText(value)
            elif isinstance(widget, QtWidgets.QComboBox):
                ind = widget.findText(value)
                if ind < 0:
                    logger.error(f"Parameter choice {key}={value} not found!")
                    continue  # Still allow other parameters to be set
                else:
                    widget.setCurrentIndex(ind)
            elif isinstance(widget, (QtWidgets.QDoubleSpinBox)):
                widget.setValue(float(value))
            elif isinstance(widget, QtWidgets.QSpinBox):
                widget.setValue(int(value))    
            elif isinstance(widget, QtWidgets.QPushButton):
                if key=='AutoReward':
                    widget.setChecked(bool(value))
                    self.MainWindow._AutoReward()            
            
            # Append the widgets that have been set
            widgets_set.append(widget)
            logger.info(f"{key} is set to {value}")
        
        # Mimic an "ENTER" press event to update the parameters
        if if_press_enter:
            self.MainWindow._keyPressEvent()
    
        return widgets_set
        
    
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
