import time,math,json,os
from PyQt5.QtWidgets import QApplication, QDialog, QMainWindow, QMessageBox,QFileDialog,QVBoxLayout
from PyQt5 import QtWidgets
from Optogenetics import Ui_Optogenetics
from Calibration import Ui_WaterCalibration
from Camera import Ui_Camera
from MotorStage import Ui_MotorStage
from Manipulator import Ui_Manipulator
from CalibrationLaser import Ui_CalibrationLaser
from MyFunctions import Worker
import numpy as np
from PyQt5.QtCore import QThreadPool,Qt
from datetime import datetime
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from Visualization import PlotWaterCalibration
class OptogeneticsDialog(QDialog,Ui_Optogenetics):
    '''Optogenetics dialog'''
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        self.setupUi(self)
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
            Items=[]
            Color=eval('self.Laser_'+str(Numb)+'.currentText()')
            Protocol=eval('self.Protocol_'+str(Numb)+'.currentText()')
            CurrentFrequency=eval('self.Frequency_'+str(Numb)+'.currentText()')
            CurrentlaserPower=eval('self.LaserPower_'+str(Numb)+'.currentText()')
            if Protocol=='Sine':
                for i in range(len(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['LaserPowerVoltage'])):
                    Items.append(str(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['LaserPowerVoltage'][i]))
            elif Protocol=='Constant' or Protocol=='Pulse':
                for i in range(len(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['LaserPowerVoltage'])):
                    Items.append(str(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['LaserPowerVoltage'][i]))
            Items=sorted(Items)
            eval('self.LaserPower_'+str(Numb)+'.clear()')
            eval('self.LaserPower_'+str(Numb)+'.addItems(Items)')
            if eval('self.LaserPower_'+str(Numb)+'.findText(CurrentlaserPower)'):
                index = eval('self.LaserPower_'+str(Numb)+'.findText(CurrentlaserPower)')
                if index != -1:
                    eval('self.LaserPower_'+str(Numb)+'.setCurrentIndex(index)')
        except:
            pass
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
            #eval('self.Frequency_'+str(Numb)+'.clear()')
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
        if hasattr(self.MainWindow,'RecentCalibrationDate'):
            self.RecentCalibration.setText(self.MainWindow.RecentCalibrationDate)
        else:
            self.RecentCalibration.setText('NA')
        Inactlabel=range(2,16)
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
                            Items=[]
                            for i in range(len(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['LaserPowerVoltage'])):
                                Items.append(str(self.MainWindow.RecentLaserCalibration[Color][Protocol][CurrentFrequency]['LaserPowerVoltage'][i]))
                            Items=sorted(Items)
                            eval('self.LaserPower_'+str(Numb)+'.clear()')
                            eval('self.LaserPower_'+str(Numb)+'.addItems(Items)')
                        elif Protocol=='Constant' or Protocol=='Pulse':
                            Items=[]
                            for i in range(len(self.MainWindow.RecentLaserCalibration[Color][Protocol]['LaserPowerVoltage'])):
                                Items.append(str(self.MainWindow.RecentLaserCalibration[Color][Protocol]['LaserPowerVoltage'][i]))
                            Items=sorted(Items)
                            eval('self.LaserPower_'+str(Numb)+'.clear()')
                            eval('self.LaserPower_'+str(Numb)+'.addItems(Items)')
                        self.MainWindow.WarningLabel.setText('')
                        self.MainWindow.WarningLabel.setStyleSheet("color: gray;")
                    else:
                        eval('self.LaserPower_'+str(Numb)+'.clear()')
                        self.MainWindow.WarningLabel.setText('No calibration for this protocol identified!')
                        self.MainWindow.WarningLabel.setStyleSheet("color: red;")
                else:
                    eval('self.LaserPower_'+str(Numb)+'.clear()')
                    self.MainWindow.WarningLabel.setText('No calibration for this laser identified!')
                    self.MainWindow.WarningLabel.setStyleSheet("color: red;")
            else:
                eval('self.LaserPower_'+str(Numb)+'.clear()')
                self.MainWindow.WarningLabel.setText('No calibration for this laser identified!')
                self.MainWindow.WarningLabel.setStyleSheet("color: red;")

        eval('self.Location_'+str(Numb)+'.setEnabled('+str(Label)+')')
        eval('self.LaserPower_'+str(Numb)+'.setEnabled('+str(Label)+')')
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

class WaterCalibrationDialog(QDialog,Ui_WaterCalibration):
    '''Water valve calibration'''
    def __init__(self, MainWindow,parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.MainWindow=MainWindow
        #self.threadpoolL=QThreadPool() # calibration for left valve
        #self.threadpoolR=QThreadPool() # calibration for right valve
        #self.OpenLeftTag=0
        #self.OpenRightTag=0
        self.FinishLeftValve=0
        if not hasattr(self.MainWindow,'WaterCalibrationResults'):
            self.MainWindow.LaserCalibrationResults={}
            self.WaterCalibrationResults={}
        else:
            self.WaterCalibrationResults=self.MainWindow.WaterCalibrationResults
        self._connectSignalsSlots()
        self.ToInitializeVisual=1
        self._UpdateFigure()
        if hasattr(self.MainWindow,'bonsai_tag'):
            self.setWindowTitle("Water Calibration: Tower "+'_'+str(self.MainWindow.bonsai_tag))
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
                except:
                    print('Water calibration parameters saved incorrectly!')
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
        except:
            total_water=''
        self._Save(valve=valve,valve_open_time=valve_open_time,valve_open_interval=valve_open_interval,cycle=cycle,total_water=total_water)
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
        except:
            total_water=''
        self._Save(valve=valve,valve_open_time=valve_open_time,valve_open_interval=valve_open_interval,cycle=cycle,total_water=total_water)
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
                except:
                    print('Water calibration parameters uploaded incorrectly!')
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
            self.TimeRightMin.setEnabled(False)
            self.TimeRightMax.setEnabled(False)
            self.StrideRight.setEnabled(False)
            self.CycleCaliRight.setEnabled(False)
            self.IntervalRight_2.setEnabled(False)
            self.TotalWaterRight.setEnabled(False)
            # check the continue button
            self.Continue.setChecked(True)
            self.Continue.setStyleSheet("background-color : green;")
        else:
            self.StartCalibratingLeft.setStyleSheet("background-color : none")
            self.Warning.setText('Calibration was terminated!')
            self.Warning.setStyleSheet("color: red;")
        

        for current_valve_opentime in np.arange(float(self.TimeLeftMin.text()),float(self.TimeLeftMax.text()),float(self.StrideLeft.text())):
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
                            self.Warning.setText('You are calibrating Right valve: '+ str(current_valve_opentime)+'   Current cycle:'+str(i+1)+'/'+self.CycleCaliLeft.text())
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
                    self.Warning.setText('Finish calibrating left valve: '+ str(current_valve_opentime)+'\nPlease enter the measured water and click the \"Continue\" button to start calibrating the next value.\nOr enter a negative value to repeat the current calibration.')
                self.Warning.setStyleSheet("color: red;")
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
                            valve_open_time=str(float(current_valve_opentime))
                            valve_open_interval=str(float(self.IntervalLeft_2.text()))
                            cycle=str(float(self.CycleCaliLeft.text()))
                            if self.TotalWaterLeft.text()=='':
                                self.Warning.setText('Please enter the measured total water and click the continue button again!\nOr enter a negative value to repeat the current calibration.')
                                continuetag=0
                                self.Continue.setChecked(False)
                                self.Continue.setStyleSheet("background-color : none")
                            else:
                                try:
                                    continuetag=1
                                    total_water=float(self.TotalWaterLeft.text())
                                    self._Save(valve=valve,valve_open_time=valve_open_time,valve_open_interval=valve_open_interval,cycle=cycle,total_water=total_water)
                                    # clear the total water
                                    self.TotalWaterLeft.setText('')
                                except:
                                    continuetag=0
                                    self.Warning.setText('Please enter the correct total water(mg) and click the continue button again!\nOr enter a negative value to repeat the current calibration.')
                        if continuetag==1:
                            break
                # Repeat current calibration when negative value is entered
                QApplication.processEvents()
                try:
                    if total_water=='' or total_water<=0:
                        pass
                    else:
                        break
                except:
                    break
        try: 
            # calibration complete indication
            if self.StartCalibratingLeft.isChecked() and current_valve_opentime==np.arange(float(self.TimeLeftMin.text()),float(self.TimeLeftMax.text()),float(self.StrideLeft.text()))[-1]:
                self.Warning.setText('Calibration is complete!')
                self._UpdateFigure()
        except:
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
        self.TimeRightMin.setEnabled(True)
        self.TimeRightMax.setEnabled(True)
        self.StrideRight.setEnabled(True)
        self.CycleCaliRight.setEnabled(True)
        self.IntervalRight_2.setEnabled(True)
        self.TotalWaterRight.setEnabled(True) 
        # change the color to be normal
        self.StartCalibratingLeft.setStyleSheet("background-color : none")
        self.StartCalibratingLeft.setChecked(False)
    def _StartCalibratingRight(self):
        '''start the calibration loop of right valve'''
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
            self.TimeLeftMin.setEnabled(False)
            self.TimeLeftMax.setEnabled(False)
            self.StrideLeft.setEnabled(False)
            self.CycleCaliLeft.setEnabled(False)
            self.IntervalLeft_2.setEnabled(False)
            self.TotalWaterLeft.setEnabled(False)
            # check the continue button
            self.Continue.setChecked(True)
            self.Continue.setStyleSheet("background-color : green;")
        else:
            self.StartCalibratingRight.setStyleSheet("background-color : none")
            self.Warning.setText('Calibration was terminated!')
            self.Warning.setStyleSheet("color: red;")
        for current_valve_opentime in np.arange(float(self.TimeRightMin.text()),float(self.TimeRightMax.text()),float(self.StrideRight.text())):
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
                            self.Warning.setText('You are calibrating Right valve: '+ str(current_valve_opentime)+'   Current cycle:'+str(i+1)+'/'+self.CycleCaliRight.text())
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
                    self.Warning.setText('Finish calibrating Right valve: '+ str(current_valve_opentime)+'\nPlease enter the measured water and click the \"Continue\" button to start calibrating the next value.\nOr enter a negative value to repeat the current calibration.')
                    self.Warning.setStyleSheet("color: red;")
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
                            valve_open_time=str(float(current_valve_opentime))
                            valve_open_interval=str(float(self.IntervalRight_2.text()))
                            cycle=str(float(self.CycleCaliRight.text()))
                            if self.TotalWaterRight.text()=='':
                                self.Warning.setText('Please enter the measured total water and click the continue button again!\nOr enter a negative value to repeat the current calibration.')
                                continuetag=0
                                self.Continue.setChecked(False)
                                self.Continue.setStyleSheet("background-color : none")
                            else:
                                try:
                                    continuetag=1
                                    total_water=float(self.TotalWaterRight.text())
                                    self._Save(valve=valve,valve_open_time=valve_open_time,valve_open_interval=valve_open_interval,cycle=cycle,total_water=total_water)
                                    # clear the total water
                                    self.TotalWaterRight.setText('')
                                except:
                                    continuetag=0
                                    self.Warning.setText('Please enter the correct total water(mg) and click the continue button again!\nOr enter a negative value to repeat the current calibration.')
                        if continuetag==1:
                            break
                # Repeat current calibration when negative value is entered
                QApplication.processEvents()
                try:
                    if total_water=='' or total_water<=0:
                        pass
                    else:
                        break
                except:
                    break
        try: 
            # calibration complete indication
            if self.StartCalibratingRight.isChecked() and current_valve_opentime==np.arange(float(self.TimeRightMin.text()),float(self.TimeRightMax.text()),float(self.StrideRight.text()))[-1]:
                self.Warning.setText('Calibration is complete!')
                self._UpdateFigure()
        except:
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
        self.TimeLeftMin.setEnabled(True)
        self.TimeLeftMax.setEnabled(True)
        self.StrideLeft.setEnabled(True)
        self.CycleCaliLeft.setEnabled(True)
        self.IntervalLeft_2.setEnabled(True)
        self.TotalWaterLeft.setEnabled(True) 
        # change the color to be normal
        self.StartCalibratingRight.setStyleSheet("background-color : none")
        self.StartCalibratingRight.setChecked(False)
    def _Save(self,valve,valve_open_time,valve_open_interval,cycle,total_water):
        '''save the calibrated result and update the figure'''
        if total_water=='':
            return
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
        if self.OpenLeftForever.isChecked():
            # change button color
            self.OpenLeftForever.setStyleSheet("background-color : green;")
            # set the valve open time
            self.MainWindow.Channel.LeftValue(float(10000)*1000) 
            # open the valve
            self.MainWindow.Channel3.ManualWater_Left(int(1))
        else:
            # change button color
            self.OpenLeftForever.setStyleSheet("background-color : none")
            # close the valve 
            self.MainWindow.Channel.LeftValue(float(0.1)*1000)
            self.MainWindow.Channel3.ManualWater_Left(int(1))
            # set the default valve open time
            self.MainWindow.Channel.LeftValue(float(self.MainWindow.LeftValue.text())*1000)

    def _OpenRightForever(self):
        if self.OpenRightForever.isChecked():
            # change button color
            self.OpenRightForever.setStyleSheet("background-color : green;")
            # set the valve open time
            self.MainWindow.Channel.RightValue(float(10000)*1000) 
            # open the valve
            self.MainWindow.Channel3.ManualWater_Right(int(1))
        else:
            # change button color
            self.OpenRightForever.setStyleSheet("background-color : none")
            # close the valve 
            self.MainWindow.Channel.RightValue(float(0.1)*1000)
            self.MainWindow.Channel3.ManualWater_Right(int(1))
            # set the default valve open time
            self.MainWindow.Channel.RightValue(float(self.MainWindow.RightValue.text())*1000)
    """
    def _thread_completeLeft(self):
        '''Finish of left valve calibration'''
        self.FinishLeftValve=1
        print(self.FinishLeftValve)
    def _OpenLeft(self):
        '''Calibration of left valve'''
        if self.OpenLeftTag==0:
            workerLeft = Worker(self._OpenLeftThread,self.MainWindow.Channel)
            workerLeft.signals.finished.connect(self._thread_completeLeft)
            self.workerLeft=workerLeft
            self.OpenLeftTag=1
        else:
            workerLeft=self.workerLeft
        if self.OpenLeft.isChecked() and self.FinishLeftValve==1:
            self.FinishLeftValve=0
            self.threadpoolL.start(workerLeft)
    """
    def _OpenLeft(self):    
        '''Calibration of left valve in a different thread'''
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

class CameraDialog(QDialog,Ui_Camera):
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        self.setupUi(self)

class ManipulatorDialog(QDialog,Ui_Manipulator):
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        self.setupUi(self)

class MotorStageDialog(QDialog,Ui_MotorStage):
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.MainWindow=MainWindow

class LaserCalibrationDialog(QDialog,Ui_CalibrationLaser):
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        self.MainWindow=MainWindow
        self.setupUi(self)
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
            # send waveforms
            setattr(self, f"Location{i+1}_Size", getattr(self, f"WaveFormLocation_{i+1}").size)
            # send the waveform size
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
        except:
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
                            Items=[]
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
                                Items.append([float(current_voltage), left_measured_power_mean, right_measured_power_mean])
                            # Check and assign items to the nested dictionary
                            if current_date_name not in LaserCalibrationResults:
                                LaserCalibrationResults[current_date_name] = {}
                            if current_color not in LaserCalibrationResults[current_date_name]:
                                LaserCalibrationResults[current_date_name][current_color] = {}
                            if current_protocol not in LaserCalibrationResults[current_date_name][current_color]:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol] = {}
                            if current_frequency not in LaserCalibrationResults[current_date_name][current_color][current_protocol]:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency] = {}
                            LaserCalibrationResults[current_date_name][current_color][current_protocol][current_frequency]['LaserPowerVoltage']=Items
                    elif current_protocol=='Constant' or current_protocol=='Pulse':
                            input_voltages= self._extract_elements(LCM_voltage,current_protocol_ind)
                            input_voltages_unique=list(set(input_voltages))
                            Items=[]
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
                                Items.append([float(current_voltage), left_measured_power_mean, right_measured_power_mean])
                            # Check and assign items to the nested dictionary
                            if current_date_name not in LaserCalibrationResults:
                                LaserCalibrationResults[current_date_name] = {}
                            if current_color not in LaserCalibrationResults[current_date_name]:
                                LaserCalibrationResults[current_date_name][current_color] = {}
                            if current_protocol not in LaserCalibrationResults[current_date_name][current_color]:
                                LaserCalibrationResults[current_date_name][current_color][current_protocol] = {}
                            LaserCalibrationResults[current_date_name][current_color][current_protocol]['LaserPowerVoltage']=Items
                            if current_protocol=='Constant':# copy results of constant to pulse 
                                if 'Pulse' not in LaserCalibrationResults[current_date_name][current_color]:
                                    LaserCalibrationResults[current_date_name][current_color]['Pulse'] = {}
                                LaserCalibrationResults[current_date_name][current_color]['Pulse']['LaserPowerVoltage']=Items
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
    def _extract_elements(self,my_list, indices):
        extracted_elements = [my_list[index] for index in indices]
        return extracted_elements
    def _getmean(self,List):
        if List==[]:
            return 'NA'
        Sum=0
        for i in range(len(List)):
            Sum=Sum+float(List[i])
        Sum=Sum/len(List)
        return Sum
    def _Sleep(self,SleepTime):
        time.sleep(SleepTime)
    def _thread_complete(self):
        self.SleepComplete=1
    def _thread_complete2(self):
        self.SleepComplete2=1
    def _Open(self):
        '''Open the laser only once'''
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
                    #time.sleep(float(self.TP_Duration_1)+0.1)
                    #time.sleep(0.1)
                if self.KeepOpen.isChecked()==False:
                    break
            self.KeepOpen.setStyleSheet("background-color : none")
            self.KeepOpen.setChecked(False)
        else:
            # change button color
            self.KeepOpen.setStyleSheet("background-color : none")
            self.KeepOpen.setChecked(False)
