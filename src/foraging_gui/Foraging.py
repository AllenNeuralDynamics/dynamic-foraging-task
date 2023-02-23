import sys, os, time, random
import numpy as np
from datetime import date,timedelta,datetime
from PyQt5.QtWidgets import QApplication, QDialog, QMainWindow, QMessageBox,QFileDialog,QVBoxLayout
from PyQt5 import QtCore,QtWidgets
from scipy.io import savemat, loadmat
from scipy import stats
#from PyQt5.uic import loadUi
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from threading import Event
from ForagingGUI import Ui_ForagingGUI
from Optogenetics import Ui_Optogenetics
from Camera import Ui_Camera
from MotorStage import Ui_MotorStage
from Manipulator import Ui_Manipulator
from Calibration import Ui_Calibration
import rigcontrol
from pyOSC3.OSC3 import OSCStreamingClient
from PyQt5.QtCore import *
import traceback
import subprocess
import h5py

class Window(QMainWindow, Ui_ForagingGUI):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.connectSignalsSlots()
        self.default_saveFolder='E:\\DynamicForagingGUI\\Behavior\\'
        self.StartANewSession=1 # to decide if should start a new session
        self.InitializeVisual=0
        self.Visualization.setTitle(str(date.today()))
        self._InitializeBonsai()
        self.threadpool=QThreadPool()
        self.threadpool2=QThreadPool()
        self.OpenOptogenetics=0
        self._Optogenetics() # open the optogenetics panel 
    def _InitializeBonsai(self):
        #os.system(" E:\\GitHub\\dynamic-foraging-task\\bonsai\\Bonsai.exe E:\\GitHub\\dynamic-foraging-task\\src\\workflows\\foraging.bonsai  --start") 
        #workflow_file = "E:\\GitHub\\dynamic-foraging-task\\src\\workflows\\foraging.bonsai"
        #result=subprocess.run(["E:\\GitHub\\dynamic-foraging-task\\bonsai\\Bonsai.exe", "workflows", "--start", workflow_file], check=True)
        #output = result.stdout.decode()
        #workflow_id = re.search(r"Workflow started with ID: (.+)", output).group(1)
        #print(f"Workflow started with ID {workflow_id}")
        self.ip = "127.0.0.1"
        self.request_port = 4002
        self.client = OSCStreamingClient()  # Create client
        self.client.connect((self.ip, self.request_port))
        self.rig = rigcontrol.RigClient(self.client)
        self.request_port2 = 4003
        self.client2 = OSCStreamingClient()  # Create client
        self.client2.connect((self.ip, self.request_port2))
        self.rig2 = rigcontrol.RigClient(self.client2)
        self.request_port3 = 4004
        self.client3 = OSCStreamingClient()  # Create client
        self.client3.connect((self.ip, self.request_port3))
        self.rig3 = rigcontrol.RigClient(self.client3)

    def connectSignalsSlots(self):
        self.action_About.triggered.connect(self._about)
        self.action_Camera.triggered.connect(self._Camera)
        self.action_Optogenetics.triggered.connect(self._Optogenetics)
        self.action_Manipulator.triggered.connect(self._Manipulator)
        self.action_MotorStage.triggered.connect(self._MotorStage)
        self.action_Calibration.triggered.connect(self._Calibration)
        self.action_Snipping.triggered.connect(self._Snipping)
        self.action_Open.triggered.connect(self._Open)
        self.action_Save.triggered.connect(self._Save)
        self.action_Exit.triggered.connect(self._Exit)
        self.action_New.triggered.connect(self._New)
        self.action_Clear.triggered.connect(self._Clear)
        self.action_Start.triggered.connect(self.Start.click)
        self.action_NewSession.triggered.connect(self.NewSession.click)
        self.Load.clicked.connect(self._Open)
        self.Save.clicked.connect(self._Save)
        self.Clear.clicked.connect(self._Clear)
        self.Start.clicked.connect(self._Start)
        self.NewSession.clicked.connect(self._NewSession)
        self.OptogeneticsB.activated.connect(self._OptogeneticsB) # turn on/off optogenetics

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Foraging Close', 'Do you want to save the result?',QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self._Save()
            event.accept()
            self.Start.setChecked(False)
            self.client.close()
            self.client2.close()
            self.client3.close()
            print('Window closed')
        elif reply == QMessageBox.No:
            event.accept()
            self.Start.setChecked(False)
            self.client.close()
            self.client2.close()
            self.client3.close()
            print('Window closed')
        else:
            event.ignore()
    def _Exit(self):
        response = QMessageBox.question(self,'Save and Exit:', "Do you want to save the result?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,QMessageBox.Yes)
        if response==QMessageBox.Yes:
            self._Save()
            self.close()
        elif response==QMessageBox.No:
            self.close()
    def _Snipping(self):
        os.system("start %windir%\system32\SnippingTool.exe") 
    def _Optogenetics(self):
        '''will be triggered when the optogenetics icon is pressed'''
        if self.OpenOptogenetics==0:
            self.Opto_dialog = OptogeneticsDialog(self)
            self.OpenOptogenetics=1
        if self.action_Optogenetics.isChecked()==True:
            self.Opto_dialog.show()
        else:
            self.Opto_dialog.hide()

    def _Camera(self):
        self.Camera_dialog = CameraDialog(self)
        self.Camera_dialog.show()
    def _Manipulator(self):
        self.ManipulatoB_dialog = ManipulatorDialog(self)
        self.ManipulatoB_dialog.show()
    def _MotorStage(self):
        self.MotorStage_dialog = MotorStageDialog(self)
        self.MotorStage_dialog.show()
    def _Calibration(self):
        self.Calibration_dialog = CalibrationDialog(self)
        self.Calibration_dialog.show()
    def _about(self):
        QMessageBox.about(
            self,
            "Foraging",
            "<p>Version 1</p>"
            "<p>Date: Dec 1, 2022</p>"
            "<p>Behavior control</p>"
            "<p>Visualization</p>"
            "<p>Analysis</p>"
            "<p></p>",
        )
    def _Save(self):
        SaveFile=self.default_saveFolder+self.AnimalName.text()+'_'+str(date.today())+'.mat'
        N=0
        while 1:
            if os.path.isfile(SaveFile):
                N=N+1
                SaveFile=self.default_saveFolder+self.AnimalName.text()+'_'+str(date.today())+'_'+str(N)+'.mat'
            else:
                break
        self.SaveFile = QFileDialog.getSaveFileName(self, 'Save File',SaveFile)[0]
        if self.SaveFile != '':
            if hasattr(self, 'GeneratedTrials'):
                if hasattr(self.GeneratedTrials, 'Obj'):
                    Obj=self.GeneratedTrials.Obj
            else:
                Obj={}
            for child in self.TrainingParameters.findChildren(QtWidgets.QDoubleSpinBox)+self.centralwidget.findChildren(QtWidgets.QLineEdit):
                Obj[child.objectName()]=child.text()
            for child in self.centralwidget.findChildren(QtWidgets.QComboBox):
                Obj[child.objectName()]=child.currentText()
            if 'Opto_dialog' in self.__dict__:
                for child in self.Opto_dialog.findChildren(QtWidgets.QDoubleSpinBox)+self.Opto_dialog.findChildren(QtWidgets.QLineEdit):
                    Obj[child.objectName()]=child.text()
                for child in self.Opto_dialog.findChildren(QtWidgets.QComboBox):
                    Obj[child.objectName()]=child.currentText()

            
            # save behavor events
            if hasattr(self, 'GeneratedTrials'):
                # Do something if self has the GeneratedTrials attribute
                # Create an empty dictionary to store the fields with the 'B_' prefix and other behavior events
                Obj['LeftLickTime']=self.GeneratedTrials.LeftLickTime
                Obj['RightLickTime']=self.GeneratedTrials.RightLickTime
                Obj['TrialStartTime']=self.GeneratedTrials.TrialStartTime
                Obj['TrialEndTime']=self.GeneratedTrials.TrialEndTime
                Obj['GoCueTime']=self.GeneratedTrials.GoCueTime
                # Iterate over all attributes of the GeneratedTrials object
                for attr_name in dir(self.GeneratedTrials):
                    if attr_name.startswith('B_'):
                        # Add the field to the dictionary with the 'B_' prefix removed
                        #print(attr_name)
                        #if attr_name=='B_RewardFamilies':
                        #    pass
                        #else:
                            Obj[attr_name] = getattr(self.GeneratedTrials, attr_name)
            savemat(self.SaveFile, Obj)           

    def _Open(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Open file', self.default_saveFolder, "Behavior files (*.mat)")
        if fname:
            Obj = loadmat(fname)
            self.Obj = Obj
            widget_dict = {w.objectName(): w for w in self.centralwidget.findChildren((QtWidgets.QLineEdit, QtWidgets.QComboBox,QtWidgets.QDoubleSpinBox))}
            widget_dict.update({w.objectName(): w for w in self.TrainingParameters.findChildren(QtWidgets.QDoubleSpinBox)})
            widget_dict.update({w.objectName(): w for w in self.Opto_dialog.findChildren((QtWidgets.QLineEdit, QtWidgets.QComboBox,QtWidgets.QDoubleSpinBox))})  # update optogenetics parameters from the loaded file

            for key in widget_dict.keys():
                if key in Obj:
                    widget = widget_dict[key]
                    value=Obj[key]
                    if len(value)==0:
                        value=np.array([''], dtype='<U1')
                    if isinstance(widget, QtWidgets.QLineEdit):
                        widget.setText(value[-1])
                    elif isinstance(widget, QtWidgets.QComboBox):
                        index = widget.findText(value[-1])
                        if index != -1:
                            widget.setCurrentIndex(index)
                    elif isinstance(widget, QtWidgets.QDoubleSpinBox):
                        widget.setValue(float(value[-1]))
                else:
                    widget = widget_dict[key]
                    if not isinstance(widget, QtWidgets.QComboBox):
                        widget.clear()
            try:
                # visualization when loading the data
                self._LoadVisualization()
            except Exception as e:
                # Catch the exception and print error information
                print("An error occurred:")
                print(traceback.format_exc())

    def _LoadVisualization(self):
        '''To visulize the training when loading a session'''
        self.NewSession.click()
        self.InitializeVisual=0
        Obj=self.Obj
        self.GeneratedTrials=GenerateTrials(self)
        # Iterate over all attributes of the GeneratedTrials object
        for attr_name in dir(self.GeneratedTrials):
            if attr_name in Obj.keys():
                try:
                    # Get the value of the attribute from Obj
                    if attr_name.startswith('TP_'):
                        value = Obj[attr_name][-1]
                    else:
                        value = Obj[attr_name]
                    # Set the attribute in the GeneratedTrials object
                    setattr(self.GeneratedTrials, attr_name, value)
                except:
                    pass
        # this is a bug to use the scipy.io.loadmat or savemat (it will change the dimension of the nparray)
        self.GeneratedTrials.B_AnimalResponseHistory=self.GeneratedTrials.B_AnimalResponseHistory[0]
        self.GeneratedTrials.TrialStartTime=self.GeneratedTrials.TrialStartTime[0]
        self.GeneratedTrials.TrialEndTime=self.GeneratedTrials.TrialEndTime[0]
        self.GeneratedTrials.GoCueTime=self.GeneratedTrials.GoCueTime[0]

        PlotM=PlotV(win=self,GeneratedTrials=self.GeneratedTrials,width=5, height=4)
        layout=self.Visualization.layout()
        if layout is not None:
            for i in reversed(range(layout.count())):
                layout.itemAt(i).widget().setParent(None)
            layout.invalidate()
        layout=self.Visualization.layout()
        if layout is None:
            layout=QVBoxLayout(self.Visualization)
        toolbar = NavigationToolbar(PlotM, self)
        toolbar.setMaximumHeight(20)
        toolbar.setMaximumWidth(300)
        layout.addWidget(toolbar)
        layout.addWidget(PlotM)
        PlotM._Update(GeneratedTrials=self.GeneratedTrials)
        

    def _Clear(self):
        for child in self.TrainingParameters.findChildren(QtWidgets.QLineEdit):
            child.clear()
        for child in self.centralwidget.findChildren(QtWidgets.QLineEdit):
            child.clear()
    def _New(self):
        self._Clear()
    def _NewSession(self):
        if self.NewSession.isChecked():
            reply = QMessageBox.question(self, 'New Session:', 'Do you want to save the result?',QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                self.NewSession.setStyleSheet("background-color : green;")
                self.Start.setStyleSheet("background-color : none")
                self._Save()
                self.Start.setChecked(False)
                self.StartANewSession=1
                print('Saved')
            elif reply == QMessageBox.No:
                self.NewSession.setStyleSheet("background-color : green;")
                self.Start.setStyleSheet("background-color : none")
                self.Start.setChecked(False)
                self.StartANewSession=1
            else:
                self.NewSession.setChecked(False)
                pass
        else:
            self.NewSession.setStyleSheet("background-color : none")
    def _thread_complete(self):
        self.ANewTrial=1

    def _Start(self):
        if self.Start.isChecked():
            # change button color and mark the state change
            self.Start.setStyleSheet("background-color : green;")
            self.NewSession.setStyleSheet("background-color : none")
            self.NewSession.setChecked(False)
        else:
            self.Start.setStyleSheet("background-color : none")
            ''' # update graph when session is stopped
            try:
                time.sleep(self.GeneratedTrials.B_ITIHistory[-1]+3)
                self.PlotM._Update(GeneratedTrials=self.GeneratedTrials)
            except:
                pass
            '''
        # to see if we should start a new session
        if self.StartANewSession==1:
            GeneratedTrials=GenerateTrials(self)
            self.GeneratedTrials=GeneratedTrials
            self.StartANewSession=0
            PlotM=PlotV(win=self,GeneratedTrials=GeneratedTrials,width=5, height=4)
            #generate the first trial outside the loop, only for new session
            self.ANewTrial=1
            GeneratedTrials._GenerateATrial()
        else:
            GeneratedTrials=self.GeneratedTrials

        if self.InitializeVisual==0: # only run once
            self.PlotM=PlotM
            layout=self.Visualization.layout()
            if layout is not None:
                for i in reversed(range(layout.count())):
                    layout.itemAt(i).widget().setParent(None)
                layout.invalidate()
            if layout is None:
                layout=QVBoxLayout(self.Visualization)
            toolbar = NavigationToolbar(PlotM, self)
            toolbar.setMaximumHeight(20)
            toolbar.setMaximumWidth(300)
            layout.addWidget(toolbar)
            layout.addWidget(PlotM)
            self.InitializeVisual=1
        else:
            PlotM=self.PlotM

        # start the trial loop
        while self.Start.isChecked():
            QApplication.processEvents()
            if self.ANewTrial==1 and GeneratedTrials.GeneFinish==1: 
                self.ANewTrial=0     
                #initiate the generated trial
                GeneratedTrials._InitiateATrial(self.rig)
                #get the response of the animal using a different thread
                worker = Worker(GeneratedTrials._GetAnimalResponse,self.rig,self.rig3)
                worker.signals.finished.connect(self._thread_complete)
                self.threadpool.start(worker)
                #get the licks of the animal using a different thread
                workerLick = Worker(GeneratedTrials._GetLicks,self.rig2)
                self.threadpool2.start(workerLick) 
                #update the visualization
                PlotM._Update(GeneratedTrials=GeneratedTrials)
                print(GeneratedTrials.B_CurrentTrialN)
                #generate a new trial
                GeneratedTrials.GeneFinish=0
                GeneratedTrials._GenerateATrial()
    def _OptogeneticsB(self):
        ''' optogenetics control in the main window'''
        if self.OptogeneticsB.currentText()=='on':
            self._Optogenetics() # press the optogenetics icon
            self.action_Optogenetics.setChecked(True)
            self.Opto_dialog.show()
        else:
            self.action_Optogenetics.setChecked(False)
            self.Opto_dialog.hide()

class OptogeneticsDialog(QDialog,Ui_Optogenetics):
    '''Optogenetics dialog'''
    def __init__(self, parent=None):
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
            eval('self.RD_'+str(Numb)+'.setEnabled('+str(True)+')')
        if eval('self.Protocol_'+str(Numb)+'.currentText()')=='Constant':
            eval('self.label'+str(Numb)+'_'+str(Inactlabel1)+'.setEnabled('+str(False)+')')
            eval('self.PulseDur_'+str(Numb)+'.setEnabled('+str(False)+')')
            eval('self.label'+str(Numb)+'_'+str(Inactlabel2)+'.setEnabled('+str(False)+')')
            eval('self.Frequency_'+str(Numb)+'.setEnabled('+str(True)+')')
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
        Inactlabel=range(1,16)
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

class CameraDialog(QDialog,Ui_Camera):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

class ManipulatorDialog(QDialog,Ui_Manipulator):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

class MotorStageDialog(QDialog,Ui_MotorStage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

class CalibrationDialog(QDialog,Ui_Calibration):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

class GenerateTrials():
    def __init__(self,win):
        self.win=win
        self.B_RewardFamilies=[[[8,1],[6, 1],[3, 1],[1, 1]],[[8, 1], [1, 1]],[[1,0],[.9,.1],[.8,.2],[.7,.3],[.6,.4],[.5,.5]],[[6, 1],[3, 1],[1, 1]]]
        self.B_RewardFamilies = [[[float(x) for x in y] for y in z] for z in self.B_RewardFamilies]
        self.B_RewardFamilies = np.array(self.B_RewardFamilies)
        self.B_CurrentTrialN=0
        self.B_LickPortN=2
        self.B_ANewBlock=np.array([1,1]).astype(int)
        self.B_RewardProHistory=np.array([[],[]]).astype(int)
        self.B_BlockLenHistory=[[],[]]
        self.B_BaitHistory=np.array([[],[]]).astype(bool)
        self.B_ITIHistory=[]
        self.B_DelayHistory=[]
        self.B_ResponseTimeHistory=[]
        self.B_CurrentRewardProb=np.empty((2,))
        self.B_AnimalCurrentResponse=[]
        self.B_AnimalResponseHistory=np.array([]).astype(float) # 0 lick left; 1 lick right; 2 no response
        self.B_Baited=np.array([False,False]).astype(bool)
        self.B_CurrentRewarded=np.array([[False],[False]]).astype(bool) # whether to receive reward
        self.B_RewardedHistory=np.array([[],[]]).astype(bool)
        self.B_Time=[]
        self.LeftLickTime=np.array([]).astype(float)
        self.RightLickTime=np.array([]).astype(float)
        self.TrialStartTime=np.array([]).astype(float)
        self.TrialEndTime=np.array([]).astype(float)
        self.GoCueTime=np.array([]).astype(float)
        self.ResponseTime=win.ResponseTime.text
        self.Obj={}
        # get all of the training parameters of the current trial
        self._GetTrainingParameters(self.win)
    def _GenerateATrial(self):
        # get all of the training parameters of the current trial
        self._GetTrainingParameters(self.win)
        # save all of the parameters in each trial
        self._SaveParameters()
        self.RewardPairs=self.B_RewardFamilies[int(self.TP_RewardFamily)-1][:int(self.TP_RewardPairsN)]
        self.RewardProb=np.array(self.RewardPairs)/np.expand_dims(np.sum(self.RewardPairs,axis=1),axis=1)*float(self.TP_BaseRewardSum)
        # determine the reward probability of the next trial based on tasks
        if (self.TP_Task in ['Coupled Baiting','Coupled Without Baiting']) and any(self.B_ANewBlock==1):
            # get the reward probabilities pool
            RewardProbPool=np.append(self.RewardProb,np.fliplr(self.RewardProb),axis=0)
            # exclude the previous reward probabilities
            if self.B_RewardProHistory.size!=0:
                RewardProbPool=RewardProbPool[RewardProbPool!=self.B_RewardProHistory[:,-1]]
                RewardProbPool=RewardProbPool.reshape(int(RewardProbPool.size/self.B_LickPortN),self.B_LickPortN)
            # get the reward probabilities of the current block
            self.B_CurrentRewardProb=RewardProbPool[random.choice(range(np.shape(RewardProbPool)[0]))]
            # randomly draw a block length between Min and Max
            self.BlockLen = np.array(int(np.random.exponential(float(self.TP_BlockBeta),1)+float(self.TP_BlockMin)))
            if self.BlockLen>float(self.TP_BlockMax):
                self.BlockLen=int(self.TP_BlockMax)
            for i in range(len(self.B_ANewBlock)):
                self.B_BlockLenHistory[i].append(self.BlockLen)
            self.B_ANewBlock=np.array([0,0])
        elif (self.TP_Task in ['Uncoupled Baiting','Uncoupled Without Baiting'])  and any(self.B_ANewBlock==1):
            # get the reward probabilities pool
            for i in range(len(self.B_ANewBlock)):
                if self.B_ANewBlock[i]==1:
                    RewardProbPool=np.append(self.RewardProb,np.fliplr(self.RewardProb),axis=0)
                    RewardProbPool=RewardProbPool[:,i]
                    # exclude the previous reward probabilities
                    if self.B_RewardProHistory.size!=0:
                        RewardProbPool=RewardProbPool[RewardProbPool!=self.B_RewardProHistory[i,-1]]
                    # get the reward probabilities of the current block
                    self.B_CurrentRewardProb[i]=RewardProbPool[random.choice(range(np.shape(RewardProbPool)[0]))]
                    # randomly draw a block length between Min and Max
                    self.BlockLen = np.array(int(np.random.exponential(float(self.TP_BlockBeta),1)+float(self.TP_BlockMin)))
                    if self.BlockLen>float(self.TP_BlockMax):
                        self.BlockLen=int(self.TP_BlockMax)
                    self.B_BlockLenHistory[i].append(self.BlockLen)
                    self.B_ANewBlock[i]=0
        self.B_RewardProHistory=np.append(self.B_RewardProHistory,self.B_CurrentRewardProb.reshape(self.B_LickPortN,1),axis=1)
        # decide if block transition will happen at the next trial
        for i in range(len(self.B_ANewBlock)):
            if self.B_CurrentTrialN>=sum(self.B_BlockLenHistory[i]):
                self.B_ANewBlock[i]=1
        # transition to the next block when NextBlock button is clicked
        if self.TP_NextBlock:
            self.B_ANewBlock[:]=1
            self.win.NextBlock.setChecked(False)
        
        # get the ITI time and delay time
        self.CurrentITI = float(np.random.exponential(float(self.TP_ITIBeta),1)+float(self.TP_ITIMin))
        if self.CurrentITI>float(self.TP_ITIMax):
            self.CurrentITI=float(self.TP_ITIMax)
        self.CurrentDelay = float(np.random.exponential(float(self.TP_DelayBeta),1)+float(self.TP_DelayMin))
        if self.CurrentDelay>float(self.TP_DelayMax):
            self.CurrentDelay=float(self.TP_DelayMax)
        self.B_ITIHistory.append(self.CurrentITI)
        self.B_DelayHistory.append(self.CurrentDelay)
        self.B_ResponseTimeHistory.append(float(self.ResponseTime()))
        # generate the optogenetics waveform of the next trial
        
        # send the waveform to Bonsai temporarily stored for using in the next trial 
        # laser on/off of the next trial
        # finish of this sectiom
        self.GeneFinish=1

    def _InitiateATrial(self,rig):
        # Determine if the current lick port should be baited. self.B_Baited can only be updated after receiving response of the animal, so this part cannot appear in the _GenerateATrial section
        self.CurrentBait=self.B_CurrentRewardProb>np.random.random(2)
        if (self.TP_Task in ['Coupled Baiting','Uncoupled Baiting']):
             self.CurrentBait= self.CurrentBait | self.B_Baited
        self.B_Baited=  self.CurrentBait.copy()
        self.B_BaitHistory=np.append(self.B_BaitHistory, self.CurrentBait.reshape(2,1),axis=1)

        rig.Left_Bait(int(self.CurrentBait[0]))
        rig.Right_Bait(int(self.CurrentBait[1]))
        rig.ITI(float(self.CurrentITI))
        rig.DelayTime(float(self.CurrentDelay))
        rig.ResponseTime(float(self.ResponseTime()))
        rig.start(1)
  
    def _GetAnimalResponse(self,rig,rig3):
        '''
        # random forager
        self.B_AnimalCurrentResponse=random.choice(range(2))
        # win stay, lose switch forager
        if self.B_CurrentTrialN>=2:
            if any(self.B_RewardedHistory[:,-1]==1):# win
                self.B_AnimalCurrentResponse=self.B_AnimalResponseHistory[-1]
            elif any(self.B_RewardedHistory[:,-1]==0) and self.B_AnimalResponseHistory[-1]!=2:# lose
                self.B_AnimalCurrentResponse=1-self.B_AnimalResponseHistory[-1]
            else: # no response
                self.B_AnimalCurrentResponse=random.choice(range(2))

        if np.random.random(1)<0.1: # no response
            self.B_AnimalCurrentResponse=2
        '''
        # get the trial start time
        TrialStartTime=rig.receive()
        # reset the baited state of chosen side; get the reward state
        a=rig.receive()
        # can not use self.CurrentBait to decide if this current trial is rewarded or not as a new trial was already generated before this
        b=rig.receive()
        # go cue start time
        GoCueTime=rig3.receive()
        self.GoCueTime=np.append(self.GoCueTime,GoCueTime[1])

        if a.address=='/TrialEndTime':
            TrialEndTime=a
        elif a.address=='/TrialEnd':
            TrialOutcome=a
        if b.address=='/TrialEndTime':
            TrialEndTime=b
        elif b.address=='/TrialEnd':
            TrialOutcome=b
        if TrialOutcome[1]=='NoResponse':
            self.B_AnimalCurrentResponse=2
            self.B_CurrentRewarded[0]=False
            self.B_CurrentRewarded[1]=False
        elif TrialOutcome[1]=='RewardLeft':
            self.B_AnimalCurrentResponse=0
            self.B_Baited[0]=False
            self.B_CurrentRewarded[1]=False
            self.B_CurrentRewarded[0]=True  
        elif TrialOutcome[1]=='ErrorLeft':
            self.B_AnimalCurrentResponse=0
            self.B_Baited[0]=False
            self.B_CurrentRewarded[0]=False
            self.B_CurrentRewarded[1]=False
        elif TrialOutcome[1]=='RewardRight':
            self.B_AnimalCurrentResponse=1
            self.B_Baited[1]=False
            self.B_CurrentRewarded[0]=False
            self.B_CurrentRewarded[1]=True
        elif TrialOutcome[1]=='ErrorRight':
            self.B_AnimalCurrentResponse=1
            self.B_Baited[1]=False
            self.B_CurrentRewarded[0]=False
            self.B_CurrentRewarded[1]=False
        self.B_RewardedHistory=np.append(self.B_RewardedHistory,self.B_CurrentRewarded,axis=1)
        self.B_AnimalResponseHistory=np.append(self.B_AnimalResponseHistory,self.B_AnimalCurrentResponse)
        # get the trial end time at the end of the trial
        self.TrialStartTime=np.append(self.TrialStartTime,TrialStartTime[1])
        self.TrialEndTime=np.append(self.TrialEndTime,TrialEndTime[1])
        self.B_CurrentTrialN+=1

    def _GetLicks(self,rig2):
        while ~rig2.msgs.empty():
            QApplication.processEvents()
            Rec=rig2.receive()
            if Rec.address=='/LeftLickTime':
                self.LeftLickTime=np.append(self.LeftLickTime,Rec[1])
            elif Rec.address=='/RightLickTime':
                self.RightLickTime=np.append(self.RightLickTime,Rec[1])

    # get training parameters
    def _GetTrainingParameters(self,win):
        '''Get training parameters'''
        # Iterate over each container to find child widgets and store their values in self
        for container in [win.TrainingParameters, win.centralwidget, win.Opto_dialog]:
            # Iterate over each child of the container that is a QLineEdit or QDoubleSpinBox
            for child in container.findChildren((QtWidgets.QLineEdit, QtWidgets.QDoubleSpinBox)):
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store the child's text value
                setattr(self, 'TP_'+child.objectName(), child.text())
            # Iterate over each child of the container that is a QComboBox
            for child in container.findChildren(QtWidgets.QComboBox):
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store the child's current text value
                setattr(self, 'TP_'+child.objectName(), child.currentText())
            # Iterate over each child of the container that is a QPushButton
            for child in container.findChildren(QtWidgets.QPushButton):
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store whether the child is checked or not
                setattr(self, 'TP_'+child.objectName(), child.isChecked())

    def _SaveParameters(self):
         for attr_name in dir(self):
                if attr_name.startswith('TP_'):
                    # Add the field to the dictionary with the 'TP_' prefix removed
                    # Check if the attribute exists in self.Obj
                    if attr_name in self.Obj:
                        # Check if the attribute value is already a list
                        if isinstance(self.Obj[attr_name], list):
                            self.Obj[attr_name].append(getattr(self, attr_name))
                        else:
                            # If the attribute value is not a list, create a new list and append to it
                            self.Obj[attr_name] = [self.Obj[attr_name], getattr(self, attr_name)]
                    else:
                        # If the attribute does not exist in self.Obj, create a new list and append to it
                        self.Obj[attr_name] = [getattr(self, attr_name)]

class PlotV(FigureCanvas):
    def __init__(self,win,GeneratedTrials=None,parent=None,dpi=100,width=5, height=4):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        gs = GridSpec(10, 30, wspace = 3, hspace = 0.1, bottom = 0.1, top = 0.95, left = 0.04, right = 0.98)
        self.ax1 = self.fig.add_subplot(gs[0:4, 0:20])
        self.ax2 = self.fig.add_subplot(gs[4:10, 0:20])
        self.ax3 = self.fig.add_subplot(gs[1:9, 22:])
        self.ax1.get_shared_x_axes().join(self.ax1, self.ax2)
        FigureCanvas.__init__(self, self.fig)
        self.RunLength=win.RunLength.text
        self.RunLengthSetValue=win.RunLength.setValue
        self.WindowSize=win.WindowSize.text
        self.StepSize=win.StepSize.text
        self.MarkerSize=3

    def _Update(self,GeneratedTrials=None):
        self.B_AnimalResponseHistory=GeneratedTrials.B_AnimalResponseHistory
        self.B_LickPortN=GeneratedTrials.B_LickPortN
        self.B_RewardProHistory=GeneratedTrials.B_RewardProHistory
        self.B_BlockLenHistory=GeneratedTrials.B_BlockLenHistory
        self.B_BaitHistory=GeneratedTrials.B_BaitHistory
        self.B_ITIHistory=GeneratedTrials.B_ITIHistory
        self.B_DelayHistory=GeneratedTrials.B_DelayHistory
        self.B_CurrentRewardProb=GeneratedTrials.B_CurrentRewardProb
        self.B_AnimalCurrentResponse=GeneratedTrials.B_AnimalCurrentResponse
        self.B_CurrentTrialN=GeneratedTrials.B_CurrentTrialN
        self.B_RewardedHistory=GeneratedTrials.B_RewardedHistory
        self.B_CurrentTrialN=GeneratedTrials.B_CurrentTrialN
        self.B_RightLickTime=GeneratedTrials.RightLickTime
        self.B_LeftLickTime=GeneratedTrials.LeftLickTime
        self.B_TrialStartTime=GeneratedTrials.TrialStartTime
        self.B_TrialEndTime=GeneratedTrials.TrialEndTime

        if self.B_CurrentTrialN>0:
            self.B_Time=self.B_TrialEndTime-GeneratedTrials.TrialStartTime[0]
        else:
            self.B_Time=self.B_TrialEndTime
        self.B_BTime=self.B_Time.copy()
        try:
            Delta=self.B_TrialEndTime[-1]-self.B_TrialStartTime[0]
            self.B_BTime=np.append(self.B_BTime,Delta+0.02*Delta)
        except:
            self.B_BTime=np.append(self.B_BTime,2)

        self.MarchingType=GeneratedTrials.TP_MartchingType
        self._PlotBlockStructure()
        self._PlotChoice()
        self._PlotMatching()
        self._PlotLicks()
    def _PlotBlockStructure(self):
        ax2=self.ax2
        ax2.cla()
        try:
            ax2.plot(self.B_Time, self.B_RewardProHistory[0],color='r', label='p_L',alpha=1)
            ax2.plot(self.B_Time, self.B_RewardProHistory[1],color='b', label='p_R',alpha=1)
            Fraction=self.B_RewardProHistory[1]/self.B_RewardProHistory.sum(axis=0)
            ax2.plot(self.B_Time,Fraction,color='y',label='p_R_frac',alpha=0.5)
        except:
            Len=len(self.B_Time)
            ax2.plot(self.B_Time, self.B_RewardProHistory[0][0:Len],color='r', label='p_L',alpha=1)
            ax2.plot(self.B_Time, self.B_RewardProHistory[1][0:Len],color='b', label='p_R',alpha=1)
            Fraction=self.B_RewardProHistory[1]/self.B_RewardProHistory.sum(axis=0)
            ax2.plot(self.B_Time,Fraction[0:Len],color='y',label='p_R_frac',alpha=0.5)
        self._UpdateAxis()
        self.draw()
    def _PlotChoice(self):
        MarkerSize=self.MarkerSize
        ax1=self.ax1
        ax2=self.ax2
        ax1.cla()
        LeftChoice_Rewarded=np.where(np.logical_and(self.B_AnimalResponseHistory==0,self.B_RewardedHistory[0]==True))
        LeftChoice_UnRewarded=np.where(np.logical_and(self.B_AnimalResponseHistory==0,self.B_RewardedHistory[0]==False))
        RightChoice_Rewarded=np.where(np.logical_and(self.B_AnimalResponseHistory==1,self.B_RewardedHistory[1]==True))
        RightChoice_UnRewarded=np.where(np.logical_and(self.B_AnimalResponseHistory==1, self.B_RewardedHistory[1]==False))

        # running average of choice
        kernel_size = int(self.RunLength())
        if kernel_size==1:
            kernel_size=2
            self.RunLengthSetValue(2)

        ResponseHistoryT=self.B_AnimalResponseHistory.copy()
        ResponseHistoryT[ResponseHistoryT==2]=np.nan
        ResponseHistoryF=ResponseHistoryT.copy()
        # running average of reward and succuss rate
        RewardedHistoryT=self.B_AnimalResponseHistory.copy()
        LeftRewarded=np.logical_and(self.B_RewardedHistory[0]==1,self.B_RewardedHistory[1]==0)  
        RightRewarded=np.logical_and(self.B_RewardedHistory[1]==1,self.B_RewardedHistory[0]==0)
        NoReward=np.logical_and(self.B_RewardedHistory[1]==0,self.B_RewardedHistory[0]==0)
        RewardedHistoryT[LeftRewarded]=0
        RewardedHistoryT[RightRewarded]=1
        RewardedHistoryT[NoReward]=np.nan
        RewardedHistoryF=RewardedHistoryT.copy()

        SuccessHistoryT=self.B_AnimalResponseHistory.copy()
        SuccessHistoryT[np.logical_or(SuccessHistoryT==1, SuccessHistoryT==0)]=1
        SuccessHistoryT[SuccessHistoryT==2]=0
        SuccessHistoryF=SuccessHistoryT.copy()
        # running average of response fraction
        for i in range(len(self.B_AnimalResponseHistory)):
            if i>=kernel_size-1:
                ResponseHistoryF[i+1-kernel_size]=np.nanmean(ResponseHistoryT[i+1-kernel_size:i+1])
                RewardedHistoryF[i+1-kernel_size]=np.nanmean(RewardedHistoryT[i+1-kernel_size:i+1])
                SuccessHistoryF[i+1-kernel_size]=np.nanmean(SuccessHistoryT[i+1-kernel_size:i+1])
                
        LeftChoice=np.where(self.B_AnimalResponseHistory==0)
        RightChoice=np.where(self.B_AnimalResponseHistory==1)
        NoResponse=np.where(self.B_AnimalResponseHistory==2)

        if self.B_BaitHistory.shape[1]>self.B_AnimalResponseHistory.shape[0]:
            LeftBait=np.where(self.B_BaitHistory[0][:-1]==True)
            RightBait=np.where(self.B_BaitHistory[1][:-1]==True)
            
            # plot the upcoming trial start time
            if self.B_CurrentTrialN>0:
                NewTrialStart=np.array(self.B_BTime[-1])
                NewTrialStart2=np.array(self.B_BTime[-1]+self.B_BTime[-1]/40)
            else:
                NewTrialStart=np.array(self.B_BTime[-1]+0.1)
                NewTrialStart2=np.array(self.B_BTime[-1])
            ax1.eventplot(NewTrialStart.reshape((1,)), lineoffsets=.5, linelengths=2, linewidth=2, color='k', label='UpcomingTrial', alpha=0.3)
            ax2.eventplot(NewTrialStart.reshape((1,)), lineoffsets=.5, linelengths=2, linewidth=2, color='k', alpha=0.3)
            if self.B_BaitHistory[0][-1]==True:
                ax1.plot(NewTrialStart2,-0.2, 'kD',label='Bait',markersize=MarkerSize, alpha=0.4)
            if self.B_BaitHistory[1][-1]==True:
                ax1.plot(NewTrialStart2,1.2, 'kD',markersize=MarkerSize, alpha=0.4)
        else:
            LeftBait=np.where(self.B_BaitHistory[0]==True)
            RightBait=np.where(self.B_BaitHistory[1]==True)
        if np.size(LeftBait) !=0:
            ax1.plot(self.B_BTime[LeftBait], np.zeros(len(self.B_BTime[LeftBait]))-0.2, 'kD',markersize=MarkerSize, alpha=0.2)
        if np.size(RightBait) !=0:
            ax1.plot(self.B_BTime[RightBait], np.zeros(len(self.B_BTime[RightBait]))+1.2, 'kD',markersize=MarkerSize, alpha=0.2)
        if np.size(LeftChoice) !=0:
            ax1.plot(self.B_Time[LeftChoice], np.zeros(len(self.B_Time[LeftChoice]))+0, 'go',markerfacecolor = (1, 1, 1, 1),label='Choice',markersize=MarkerSize)
        if np.size(LeftChoice_Rewarded) !=0:
            ax1.plot(self.B_Time[LeftChoice_Rewarded], np.zeros(len(self.B_Time[LeftChoice_Rewarded]))+.2, 'go',markerfacecolor = (0, 1, 0, 1),label='Rewarded',markersize=MarkerSize)
        if np.size(RightChoice) !=0:
            ax1.plot(self.B_Time[RightChoice], np.zeros(len(self.B_Time[RightChoice]))+1, 'go',markerfacecolor = (1, 1, 1, 1),markersize=MarkerSize)
        if np.size(RightChoice_Rewarded) !=0:
            ax1.plot(self.B_Time[RightChoice_Rewarded], np.zeros(len(self.B_Time[RightChoice_Rewarded]))+.8, 'go',markerfacecolor = (0, 1, 0, 1),markersize=MarkerSize)
        if np.size(NoResponse) !=0:
            ax1.plot(self.B_Time[NoResponse], np.zeros(len(self.B_Time[NoResponse]))+.5, 'Xk',label='NoResponse',markersize=MarkerSize,alpha=0.2)
        if self.B_CurrentTrialN>kernel_size:
            ax2.plot(self.B_Time[kernel_size-1:],ResponseHistoryF[:-kernel_size+1],'k',label='Choice_frac')
            ax2.plot(self.B_Time[kernel_size-1:],RewardedHistoryF[:-kernel_size+1],'g',label='reward_frac')
            ax2.plot(self.B_Time[kernel_size-1:],SuccessHistoryF[:-kernel_size+1],'c',label='succuss_frac', alpha=0.2)
        self._UpdateAxis()
        self.draw()

    def _PlotMatching(self):
        ax=self.ax3
        ax.cla()
        WindowSize=int(self.WindowSize())
        StepSize=int(self.StepSize())
        if self.B_CurrentTrialN<1:
            return
        NumberOfDots = int((np.ptp(self.B_Time)-WindowSize)/StepSize)
        if NumberOfDots<1:
            return
        #WindowStart=np.linspace(np.min(self.B_Time),np.max(self.B_Time)-WindowSize,num=NumberOfDots)
        choice_R_frac = np.empty(NumberOfDots)
        choice_R_frac[:]=np.nan
        reward_R_frac = choice_R_frac.copy()
        choice_log_ratio = choice_R_frac.copy()
        reward_log_ratio = choice_R_frac.copy()
        WinStartN=np.min(self.B_Time)
        for idx in range(NumberOfDots):
            CuI=np.logical_and(self.B_Time>=WinStartN,self.B_Time<WinStartN+WindowSize)
            LeftChoiceN=sum(self.B_AnimalResponseHistory[CuI]==0)
            RightChoiceN=sum(self.B_AnimalResponseHistory[CuI]==1)
            LeftRewardN=sum(self.B_RewardedHistory[0,CuI]==1)
            RightRewardN=sum(self.B_RewardedHistory[1,CuI]==1)    
            choice_R_frac[idx]=LeftChoiceN/(LeftChoiceN+RightChoiceN)
            reward_R_frac[idx]=LeftRewardN/(LeftRewardN+RightRewardN)
            choice_log_ratio[idx]=np.log(RightChoiceN / LeftChoiceN)
            reward_log_ratio[idx]=np.log(RightRewardN / LeftRewardN)
            WinStartN=WinStartN+StepSize
        if self.MarchingType=='log ratio':
            x=reward_log_ratio
            y=choice_log_ratio
            ax.set(xlabel='Log Reward_R/L',ylabel='Log Choice_R/L')
            ax.plot(x, y, 'ko')
            max_range = max(np.abs(ax.get_xlim()).max(), np.abs(ax.get_ylim()).max())
            ax.plot([-max_range, max_range], [-max_range, max_range], 'k--', lw=1)
        else:
            x=reward_R_frac
            y=choice_R_frac
            ax.set(xlabel='frac Reward_R',ylabel='frac Choice_R')
            ax.plot(x, y, 'ko')
            ax.plot([0, 1], [0, 1], 'k--', lw=1)

        # linear fitting
        try: 
            SeInd=~np.logical_or(np.logical_or(np.isinf(x),np.isinf(y)), np.logical_or(np.isnan(x),np.isnan(y)))
            x=x[SeInd]
            y=y[SeInd]
            slope, intercept, r_value, p_value, _ = stats.linregress(x, y)
            fit_x = x
            fit_y = x * slope + intercept
            ax.plot(fit_x, fit_y, 'r', label=f'r = {r_value:.3f}\np = {p_value:.2e}')
            ax.set_title(f'Matching slope = {slope:.2f}, bias_R = {intercept:.2f}', fontsize=10)
            ax.legend(loc='upper left', fontsize=8)
            ax.axis('equal')
        except:
            pass
        self.draw()
        #range(np.min(self.B_Time),np.max(self.B_Time),periods = numberofpoints * int(self.DotsPerWindow()))
        #win_centers = pd.date_range(start = np.min(self.B_Time), end = np.max(self.B_Time),periods = numberofpoints * int(self.DotsPerWindow()))
    def _PlotLicks(self):
        if self.B_CurrentTrialN<1:
            return
        ax=self.ax1
        ax.plot(self.B_LeftLickTime-self.B_TrialStartTime[0], np.zeros(len(self.B_LeftLickTime))-0.4, 'k|')
        ax.plot(self.B_RightLickTime-self.B_TrialStartTime[0], np.zeros(len(self.B_RightLickTime))+1.4, 'k|')
        self.draw()

    def _UpdateAxis(self):
        self.ax1.set_xticks([])
        self.ax1.set_yticks([0,1])
        self.ax1.set_yticklabels(['L', 'R'])
        self.ax1.set_ylim(-0.6, 1.6)
        self.ax1.legend(loc='lower left', fontsize=8)
        #self.ax1.axis('off')
        self.ax2.set_yticks([0,1])
        self.ax2.set_yticklabels(['L', 'R'])
        self.ax2.set_ylim(-0.15, 1.15)
        self.ax2.legend(loc='lower left', fontsize=8)

class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        #self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    # Run your application's event loop and stop after closing all windows
    sys.exit(app.exec())
