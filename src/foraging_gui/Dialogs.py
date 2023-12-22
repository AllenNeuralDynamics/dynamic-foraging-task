import time
import math
import json
import os
import shutil
import subprocess
from datetime import datetime
import logging

import numpy as np
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QThreadPool,Qt, QAbstractTableModel
from PyQt5.QtSvg import QSvgWidget

from MyFunctions import Worker
from Visualization import PlotWaterCalibration
from aind_auto_train.curriculum_manager import CurriculumManager
from aind_auto_train.auto_train_manager import DynamicForagingAutoTrainManager

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
            if Protocol=='Sine':
                for i in range(len(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Left']['LaserPowerVoltage'])):
                    ItemsLeft.append(str(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Left']['LaserPowerVoltage'][i]))
                for i in range(len(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Right']['LaserPowerVoltage'])):
                    ItemsRight.append(str(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Right']['LaserPowerVoltage'][i]))

            elif Protocol=='Constant' or Protocol=='Pulse':
                for i in range(len(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Left']['LaserPowerVoltage'])):
                    ItemsLeft.append(str(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Left']['LaserPowerVoltage'][i]))
                for i in range(len(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Right']['LaserPowerVoltage'])):
                    ItemsRight.append(str(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Right']['LaserPowerVoltage'][i]))
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
        self.LatestCalibrationDate.setText(self.MainWindow.RecentCalibrationDate)
        Inactlabel=range(2,17)
        if eval('self.Laser_'+str(Numb)+'.currentText()')=='NA':
            Label=False
        else:
            Label=True
            Color=eval('self.Laser_'+str(Numb)+'.currentText()')
            Protocol=eval('self.Protocol_'+str(Numb)+'.currentText()')
            CurrentFrequency=eval('self.Frequency_'+str(Numb)+'.currentText()')
            if hasattr(self.MainWindow,'RecentLaserCalibration'):
                if Color in self.MainWindow.RecentLaserCalibration.keys():
                    if Protocol in self.MainWindow.RecentLaserCalibration[Color].keys():
                        if Protocol=='Sine': 
                            Frequency=self.MainWindow.RecentLaserCalibration[Color][Protocol].keys()
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
                            for i in range(len(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Left']['LaserPowerVoltage'])):
                                ItemsLeft.append(str(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Left']['LaserPowerVoltage'][i]))
                            for i in range(len(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Right']['LaserPowerVoltage'])):
                                ItemsRight.append(str(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['Right']['LaserPowerVoltage'][i]))
                            ItemsLeft=sorted(ItemsLeft)
                            ItemsRight=sorted(ItemsRight)
                            eval('self.LaserPowerLeft_'+str(Numb)+'.clear()')
                            eval('self.LaserPowerLeft_'+str(Numb)+'.addItems(ItemsLeft)')
                            eval('self.LaserPowerRight_'+str(Numb)+'.clear()')
                            eval('self.LaserPowerRight_'+str(Numb)+'.addItems(ItemsRight)')
                        elif Protocol=='Constant' or Protocol=='Pulse':
                            ItemsLeft=[]
                            ItemsRight=[]
                            for i in range(len(self.MainWindow.RecentLaserCalibration[Color][Protocol]['Left']['LaserPowerVoltage'])):
                                ItemsLeft.append(str(self.MainWindow.RecentLaserCalibration[Color][Protocol]['Left']['LaserPowerVoltage'][i]))
                            for i in range(len(self.MainWindow.RecentLaserCalibration[Color][Protocol]['Right']['LaserPowerVoltage'])):
                                ItemsRight.append(str(self.MainWindow.RecentLaserCalibration[Color][Protocol]['Right']['LaserPowerVoltage'][i]))
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
                        self.MainWindow.WarningLabel.setStyleSheet("color: red;")
                else:
                    eval('self.LaserPowerLeft_'+str(Numb)+'.clear()')
                    eval('self.LaserPowerRight_'+str(Numb)+'.clear()')
                    self.MainWindow.WarningLabel.setText('No calibration for this laser identified!')
                    self.MainWindow.WarningLabel.setStyleSheet("color: red;")
            else:
                eval('self.LaserPowerLeft_'+str(Numb)+'.clear()')
                eval('self.LaserPowerRight_'+str(Numb)+'.clear()')
                self.MainWindow.WarningLabel.setText('No calibration for this laser identified!')
                self.MainWindow.WarningLabel.setStyleSheet("color: red;")

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
        self.Warning.setStyleSheet("color: red;")

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
        self.MainWindow._CheckBonsaiConnection()
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
            self.Warning.setStyleSheet("color: red;")
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
                            self.Warning.setStyleSheet("color: red;")
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
                self.Warning.setStyleSheet("color: red;")
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
            self.Warning.setStyleSheet("color: red;")
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
        self.MainWindow._CheckBonsaiConnection()
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
            self.Warning.setStyleSheet("color: red;")
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
                            self.Warning.setStyleSheet("color: red;")
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
                    self.Warning.setStyleSheet("color: red;")
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
            self.Warning.setStyleSheet("color: red;")

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
        self.MainWindow._CheckBonsaiConnection()
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
        self.MainWindow._CheckBonsaiConnection()
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
        self.MainWindow._CheckBonsaiConnection()
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
        self.MainWindow._CheckBonsaiConnection()
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
                self.WarningLabelOpenSave.setStyleSheet("color: red;")
        else:
            self.WarningLabelOpenSave.setText('No logging folder found!')
            self.WarningLabelOpenSave.setStyleSheet("color: red;")

    def _RestartLogging(self):
        '''Restart the logging (create a new logging folder)'''
        self.MainWindow._CheckBonsaiConnection()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        if self.CollectVideo.currentText()=='Yes':
            # formal logging
            self.MainWindow.Ot_log_folder=self.MainWindow._restartlogging()
        else:
            # temporary logging
            self.MainWindow.Ot_log_folder=self.MainWindow._restartlogging(self.MainWindow.temporary_video_folder)
        self.WarningLabelLogging.setText('Logging has restarted!')
        self.WarningLabelLogging.setStyleSheet("color: red;")

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
        self.MainWindow._CheckBonsaiConnection()
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
        self.MainWindow._CheckBonsaiConnection()
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
            self.MainWindow.WarningLabelCamera.setStyleSheet("color: red;")
            self.WarningLabelCameraOn.setText('Camera is on!')
            self.WarningLabelCameraOn.setStyleSheet("color: red;")
            self.WarningLabelLogging.setText('')
            self.WarningLabelLogging.setStyleSheet("color: None;")
            self.WarningLabelOpenSave.setText('')
        else:
            self.StartCamera.setStyleSheet("background-color : none")
            self.MainWindow.Channel.CameraControl(int(2))
            self.MainWindow.WarningLabelCamera.setText('Camera is off!')
            self.MainWindow.WarningLabelCamera.setStyleSheet("color: red;")
            self.WarningLabelCameraOn.setText('Camera is off!')
            self.WarningLabelCameraOn.setStyleSheet("color: red;")
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
            self.WarningLabelFileIsInUse.setStyleSheet("color: red;")
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
            self.WarningLabelFileIsInUse.setStyleSheet("color: red;")
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
        self.MainWindow._CheckBonsaiConnection()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        self.MainWindow.Channel.DO0(int(1))
        self.MainWindow.Channel.receive()
    def _FLush_DO1(self):
        self.MainWindow._CheckBonsaiConnection()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        self.MainWindow.Channel.DO1(int(1))
    def _FLush_DO2(self):
        self.MainWindow._CheckBonsaiConnection()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        #self.MainWindow.Channel.DO2(int(1))
        self.MainWindow.Channel.receive()
    def _FLush_DO3(self):
        self.MainWindow._CheckBonsaiConnection()
        if self.MainWindow.InitializeBonsaiSuccessfully==0:
            return
        self.MainWindow.Channel.DO3(int(1))
        self.MainWindow.Channel.receive()
    def _FLush_Port2(self):
        self.MainWindow._CheckBonsaiConnection()
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
                    self.win.WarningLabel.setStyleSheet("color: red;")
                else:
                    Constant=np.ones(int((self.CLP_CurrentDuration-self.CLP_RampingDown)*self.CLP_SampleFrequency))
                    RD=np.arange(1,0, -1/(np.shape(self.my_wave)[0]-np.shape(Constant)[0]))
                    RampingDown = np.concatenate((Constant, RD), axis=0)
                    self.my_wave=self.my_wave*RampingDown
            self.my_wave=np.append(self.my_wave,[0,0])
        elif self.CLP_Protocol=='Pulse':
            if self.CLP_PulseDur=='NA':
                self.win.WarningLabel.setText('Pulse duration is NA!')
                self.win.WarningLabel.setStyleSheet("color: red;")
            else:
                self.CLP_PulseDur=float(self.CLP_PulseDur)
                PointsEachPulse=int(self.CLP_SampleFrequency*self.CLP_PulseDur)
                PulseIntervalPoints=int(1/self.CLP_Frequency*self.CLP_SampleFrequency-PointsEachPulse)
                if PulseIntervalPoints<0:
                    self.win.WarningLabel.setText('Pulse frequency and pulse duration are not compatible!')
                    self.win.WarningLabel.setStyleSheet("color: red;")
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
                    self.win.WarningLabel.setStyleSheet("color: red;")
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
                    self.win.WarningLabel.setStyleSheet("color: red;")
                else:
                    Constant=np.ones(int((self.CLP_CurrentDuration-self.CLP_RampingDown)*self.CLP_SampleFrequency))
                    RD=np.arange(1,0, -1/(np.shape(self.my_wave)[0]-np.shape(Constant)[0]))
                    RampingDown = np.concatenate((Constant, RD), axis=0)
                    self.my_wave=self.my_wave*RampingDown
            self.my_wave=np.append(self.my_wave,[0,0])
        else:
            self.win.WarningLabel.setText('Unidentified optogenetics protocol!')
            self.win.WarningLabel.setStyleSheet("color: red;")

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
            self.win.WarningLabel.setStyleSheet("color: red;")
   
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
            self.Warning.setStyleSheet("color: red;")
            self.Warning.setAlignment(Qt.AlignCenter)
            return
        if self.LaserPowerMeasured.text()=='':
            self.Warning.setText('Data not captured! Please enter power measured!')
            self.Warning.setStyleSheet("color: red;")
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
            self.Warning.setStyleSheet("color: red;")
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
            self.Warning.setStyleSheet("color: red;")
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
        self.MainWindow._CheckBonsaiConnection()
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

        # Sync selected subject_id
        self.update_subject_id(self.MainWindow.ID.text())

        # Connect to auto training manager
        self._connect_auto_training_manager()
        self._show_auto_training_manager()

        # Connect to curriculum manager
        self._connect_curriculum_manager()
        self._show_available_curriculums()
    
    def update_subject_id(self, subject_id: str):
        self.selected_subject_id = subject_id
        self.label_subject_id.setText(self.selected_subject_id)
        
        #TODO: update subject_id in auto_train_manager
        
    def _connect_auto_training_manager(self):
        self.auto_train_manager = DynamicForagingAutoTrainManager(
            manager_name='447_demo',
            df_behavior_on_s3=dict(bucket='aind-behavior-data',
                                   root='foraging_nwb_bonsai_processed/',
                                   file_name='df_sessions.pkl'),
            df_manager_root_on_s3=dict(bucket='aind-behavior-data',
                                       root='foraging_auto_training/')
        )
    
    def _show_auto_training_manager(self, subject_id=None):
        self.df_training_manager = self.auto_train_manager.df_manager
        
        # Show dataframe in QTableView
        model = PandasModel(
            self.df_training_manager[
                ['subject_id',
                 'session',
                 'session_date',
                 'curriculum_task',
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
        )
        
        # Format table
        self.tableView_df_training_manager.setModel(model)
        self.tableView_df_training_manager.resizeColumnsToContents()
        self.tableView_df_training_manager.setSortingEnabled(True)


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
        
        # Get clicked row
        self.tableView_df_curriculum.clicked.connect(self._curriculum_selected)
        
    def _curriculum_selected(self, index):
        # Retrieve selected curriculum
        row = index.row()
        selected_row = self.df_curriculums.iloc[row]
        logger.info(f"Selected curriculum: {selected_row.to_dict()}")
        self.selected_curriculum = self.curriculum_manager.get_curriculum(
            curriculum_task=selected_row['curriculum_task'],
            curriculum_schema_version=selected_row['curriculum_schema_version'],
            curriculum_version=selected_row['curriculum_version'],
        )
        
        # Retrieve svgs
        svg_rule = self.selected_curriculum['diagram_rules_name']
        svg_paras = self.selected_curriculum['diagram_paras_name']
        
        # Render svgs with KeepAspectRatio
        svgWidget_rules = QSvgWidget(svg_rule)
        svgWidget_rules.renderer().setAspectRatioMode(Qt.KeepAspectRatio)
        
        svgWidget_paras = QSvgWidget(svg_paras)
        svgWidget_paras.renderer().setAspectRatioMode(Qt.KeepAspectRatio)
        
        # Add the SVG widgets to the layout
        layout = self.horizontalLayout_diagram
        # Remove all existing widgets from the layout
        for i in reversed(range(layout.count())): 
            layout.itemAt(i).widget().setParent(None)
        layout.addWidget(svgWidget_rules)
        layout.addWidget(svgWidget_paras)
                        
        
        
# --- Helpers ---
class PandasModel(QAbstractTableModel):
    ''' A helper class to display pandas dataframe in QTableView
    https://learndataanalysis.org/display-pandas-dataframe-with-pyqt5-qtableview-widget/
    '''
    def __init__(self, data):
        QAbstractTableModel.__init__(self)
        self._data = data

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

    def sort(self, column, order):
        colname = self._data.columns.tolist()[column]
        self.layoutAboutToBeChanged.emit()
        self._data.sort_values(
            colname,
            ascending=order == Qt.AscendingOrder,
            inplace=True
        )
        self._data.reset_index(inplace=True, drop=True)
        self.layoutChanged.emit()
