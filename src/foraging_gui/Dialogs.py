import time,math
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
class OptogeneticsDialog(QDialog,Ui_Optogenetics):
    '''Optogenetics dialog'''
    def __init__(self, MainWindow, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self._connectSignalsSlots()
    def _connectSignalsSlots(self):
        self.Laser_1.currentIndexChanged.connect(self._Laser_1)
        self.Laser_2.currentIndexChanged.connect(self._Laser_2)
        self.Laser_3.currentIndexChanged.connect(self._Laser_3)
        self.Laser_4.currentIndexChanged.connect(self._Laser_4)
        self.Protocol_1.activated.connect(self._activated_1)
        self.Protocol_2.activated.connect(self._activated_2)
        self.Protocol_3.activated.connect(self._activated_3)
        self.Protocol_4.activated.connect(self._activated_4)
        self.Protocol_1.currentIndexChanged.connect(self._activated_1)
        self.Protocol_2.currentIndexChanged.connect(self._activated_2)
        self.Protocol_3.currentIndexChanged.connect(self._activated_3)
        self.Protocol_4.currentIndexChanged.connect(self._activated_4)
        
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
        Inactlabel=range(2,16)
        if eval('self.Laser_'+str(Numb)+'.currentText()')=='NA':
            Label=False
        else:
            Label=True
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
        self._connectSignalsSlots()
    def _connectSignalsSlots(self):
        self.OpenLeft.clicked.connect(self._OpenLeft)
        self.OpenRight.clicked.connect(self._OpenRight)
        self.OpenLeftForever.clicked.connect(self._OpenLeftForever)
        self.OpenRightForever.clicked.connect(self._OpenRightForever)
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
        self.Frequency_1.setText(self.MainWindow.Opto_dialog.__getattribute__("Frequency_" + str(N)).text())
        self.RD_1.setText(self.MainWindow.Opto_dialog.__getattribute__("RD_" + str(N)).text())
        self.PulseDur_1.setText(self.MainWindow.Opto_dialog.__getattribute__("PulseDur_" + str(N)).text())
        self.Laser_1.setCurrentIndex(self.MainWindow.Opto_dialog.__getattribute__("Laser_" + str(N)).currentIndex())
        self.Location_1.setCurrentIndex(self.MainWindow.Opto_dialog.__getattribute__("Location_" + str(N)).currentIndex())
        self.LaserPower_1.setCurrentIndex(self.MainWindow.Opto_dialog.__getattribute__("LaserPower_" + str(N)).currentIndex())
        self.Protocol_1.setCurrentIndex(self.MainWindow.Opto_dialog.__getattribute__("Protocol_" + str(N)).currentIndex())
    def _Save(self):
        '''Save the measured laser power'''
        self.Save.setStyleSheet("background-color : green;")
        QApplication.processEvents()
        self._GetTrainingParameters(self.MainWindow)
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
            self.LCM_MeasureTime.append([date_str+' '+time_str])
        else:
            current_time = datetime.now()
            date_str = current_time.strftime("%Y-%m-%d")
            time_str = current_time.strftime("%H:%M:%S")
            self.LCM_MeasureTime=[date_str+' '+time_str]
        time.sleep(1)
        self.Save.setStyleSheet("background-color : none")
        self.Save.setChecked(False)

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
