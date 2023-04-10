import sys, os,traceback
import numpy as np
from datetime import date,timedelta,datetime
from PyQt5.QtWidgets import QApplication, QDialog, QMainWindow, QMessageBox,QFileDialog,QVBoxLayout
from PyQt5 import QtWidgets
from PyQt5.QtCore import QThreadPool,Qt
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from scipy.io import savemat, loadmat
from ForagingGUI import Ui_ForagingGUI
import rigcontrol
from pyOSC3.OSC3 import OSCStreamingClient
from Visualization import PlotV
from Dialogs import OptogeneticsDialog,WaterCalibrationDialog,CameraDialog,ManipulatorDialog,MotorStageDialog,LaserCalibrationDialog
from MyFunctions import GenerateTrials, Worker
import warnings
warnings.filterwarnings("ignore")
#import subprocess
#import h5py
#from scipy import stats
#from PyQt5.uic import loadUi
#from threading import Event

class Window(QMainWindow, Ui_ForagingGUI):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.connectSignalsSlots()
        self.default_saveFolder='E:\\DynamicForagingGUI\\Behavior\\'
        self.StartANewSession=1 # to decide if should start a new session
        self.ToInitializeVisual=1
        self.FigureUpdateTooSlow=0 # if the FigureUpdateTooSlow is true, using different process to update figures
        self.ANewTrial=1
        self.Visualization.setTitle(str(date.today()))
        self._InitializeBonsai()
        self.threadpool=QThreadPool() # get animal response
        self.threadpool2=QThreadPool() # get animal lick
        self.threadpool3=QThreadPool() # visualization
        self.threadpool4=QThreadPool() # for generating a new trial
        self.threadpool5=QThreadPool() # for starting the trial loop
        self.OpenOptogenetics=0
        self.WaterCalibration=0
        self.LaserCalibration=0
        self.Camera=0
        self.MotorStage=0
        self.Manipulator=0
        self._Optogenetics() # open the optogenetics panel
        self._LaserCalibration() # to open the laser calibration panel

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
        self.Channel = rigcontrol.RigClient(self.client)
        self.request_port2 = 4003
        self.client2 = OSCStreamingClient()  # Create client
        self.client2.connect((self.ip, self.request_port2))
        self.Channel2 = rigcontrol.RigClient(self.client2)
        self.request_port3 = 4004
        self.client3 = OSCStreamingClient()  # Create client
        self.client3.connect((self.ip, self.request_port3))
        self.Channel3 = rigcontrol.RigClient(self.client3)
        # specific for transfering optogenetics waveform
        self.request_port4 = 4005
        self.client4 = OSCStreamingClient()  # Create client
        self.client4.connect((self.ip, self.request_port4))
        self.Channel4 = rigcontrol.RigClient(self.client4)
    def connectSignalsSlots(self):
        self.action_About.triggered.connect(self._about)
        self.action_Camera.triggered.connect(self._Camera)
        self.action_Optogenetics.triggered.connect(self._Optogenetics)
        self.action_Manipulator.triggered.connect(self._Manipulator)
        self.action_MotorStage.triggered.connect(self._MotorStage)
        self.action_Calibration.triggered.connect(self._WaterCalibration)
        self.actionLaser_Calibration.triggered.connect(self._LaserCalibration)
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
        self.GiveLeft.clicked.connect(self._GiveLeft)
        self.GiveRight.clicked.connect(self._GiveRight)
        self.NewSession.clicked.connect(self._NewSession)
        self.OptogeneticsB.activated.connect(self._OptogeneticsB) # turn on/off optogenetics

    def closeEvent(self, event):
        self._StopCurrentSession() # stop the current session first
        reply = QMessageBox.question(self, 'Foraging Close', 'Do you want to save the result?',QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self._Save()
            event.accept()
            self.Start.setChecked(False)
            self.client.close()
            self.client2.close()
            self.client3.close()
            self.client4.close()
            self.threadpool.cancel()
            self.threadpool2.cancel()
            self.threadpool3.cancel()
            self.threadpool4.cancel()
            print('Window closed')
        elif reply == QMessageBox.No:
            event.accept()
            self.Start.setChecked(False)
            self.client.close()
            self.client2.close()
            self.client3.close()
            self.client4.close()
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
            self.Opto_dialog = OptogeneticsDialog(MainWindow=self)
            self.OpenOptogenetics=1
        if self.action_Optogenetics.isChecked()==True:
            self.Opto_dialog.show()
        else:
            self.Opto_dialog.hide()
    def _Camera(self):
        if self.Camera==0:
            self.Camera_dialog = CameraDialog(MainWindow=self)
            self.Camera=1
        if self.action_Camera.isChecked()==True:
            self.Camera_dialog.show()
        else:
            self.Camera_dialog.hide()
    def _Manipulator(self):
        if self.Manipulator==0:
            self.ManipulatoB_dialog = ManipulatorDialog(MainWindow=self)
            self.Manipulator=1
        if self.action_Manipulator.isChecked()==True:
            self.ManipulatoB_dialog.show()
        else:
            self.ManipulatoB_dialog.hide()
    def _WaterCalibration(self):
        if self.WaterCalibration==0:
            self.WaterCalibration_dialog = WaterCalibrationDialog(MainWindow=self)
            self.WaterCalibration=1
        if self.action_Calibration.isChecked()==True:
            self.WaterCalibration_dialog.show()
        else:
            self.WaterCalibration_dialog.hide()
    def _LaserCalibration(self):
        if self.LaserCalibration==0:
            self.LaserCalibration_dialog = LaserCalibrationDialog(MainWindow=self)
            self.LaserCalibration=1
        if self.actionLaser_Calibration.isChecked()==True:
            self.LaserCalibration_dialog.show()
        else:
            self.LaserCalibration_dialog.hide()
    def _MotorStage(self):
        if self.MotorStage==0:
            self.MotorStage_dialog = MotorStageDialog(MainWindow=self)
            self.MotorStage=1
        if self.action_MotorStage.isChecked()==True:
            self.MotorStage_dialog.show()
        else:
            self.MotorStage_dialog.hide()
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
        self._StopCurrentSession() # stop the current session first
        SaveFile=self.default_saveFolder+self.AnimalName.text()+'\\'+self.AnimalName.text()+'_'+str(date.today())+'.mat'
        SaveFolder=self.default_saveFolder+self.AnimalName.text()+'\\'
        if not os.path.exists(SaveFolder):
            os.makedirs(SaveFolder)
            print(f"Created new folder: {SaveFolder}")
        N=0
        while 1:
            if os.path.isfile(SaveFile):
                N=N+1
                SaveFile=self.default_saveFolder+self.AnimalName.text()+'\\'+self.AnimalName.text()+'_'+str(date.today())+'_'+str(N)+'.mat'
            else:
                break
        self.SaveFile = QFileDialog.getSaveFileName(self, 'Save File',SaveFile)[0]
        if self.SaveFile != '':
            if hasattr(self, 'GeneratedTrials'):
                if hasattr(self.GeneratedTrials, 'Obj'):
                    Obj=self.GeneratedTrials.Obj
            else:
                Obj={}
            # save training parameters
            for child in self.TrainingParameters.findChildren(QtWidgets.QDoubleSpinBox)+self.centralwidget.findChildren(QtWidgets.QLineEdit)+self.centralwidget.findChildren(QtWidgets.QSpinBox):
                Obj[child.objectName()]=child.text()
            for child in self.centralwidget.findChildren(QtWidgets.QComboBox):
                Obj[child.objectName()]=child.currentText()
            
            # save optogenetics parameters
            if 'Opto_dialog' in self.__dict__:
                for child in self.Opto_dialog.findChildren(QtWidgets.QDoubleSpinBox)+self.Opto_dialog.findChildren(QtWidgets.QLineEdit):
                    Obj[child.objectName()]=child.text()
                for child in self.Opto_dialog.findChildren(QtWidgets.QComboBox):
                    Obj[child.objectName()]=child.currentText()
            # save optogenetics calibration parameters
            if 'LaserCalibration_dialog' in self.__dict__:
                for child in self.LaserCalibration_dialog.findChildren(QtWidgets.QDoubleSpinBox)+self.LaserCalibration_dialog.findChildren(QtWidgets.QLineEdit):
                    Obj[child.objectName()]=child.text()
                for child in self.LaserCalibration_dialog.findChildren(QtWidgets.QComboBox):
                    Obj[child.objectName()]=child.currentText()
            # save behavor events
            if hasattr(self, 'GeneratedTrials'):
                # Do something if self has the GeneratedTrials attribute
                # Iterate over all attributes of the GeneratedTrials object
                for attr_name in dir(self.GeneratedTrials):
                    if attr_name.startswith('B_'):
                        if attr_name=='B_RewardFamilies':
                            pass
                        else:
                            Obj[attr_name] = getattr(self.GeneratedTrials, attr_name)
            # save laser calibration results 
            if hasattr(self, 'LaserCalibration_dialog'):
                # Do something if self has the GeneratedTrials attribute
                # Iterate over all attributes of the GeneratedTrials object
                for attr_name in dir(self.LaserCalibration_dialog):
                    if attr_name.startswith('LCM_'):
                        Obj[attr_name] = getattr(self.LaserCalibration_dialog, attr_name)
            savemat(self.SaveFile, Obj)           

    def _Open(self):
        self._StopCurrentSession() # stop current session first
        SaveFolder=self.default_saveFolder+self.AnimalName.text()+'\\'
        if not os.path.exists(SaveFolder):
            fname, _ = QFileDialog.getOpenFileName(self, 'Open file', self.default_saveFolder, "Behavior files (*.mat)")
        else:
            fname, _ = QFileDialog.getOpenFileName(self, 'Open file', self.default_saveFolder+'\\'+self.AnimalName.text()+'\\', "Behavior files (*.mat)")
        if fname:
            Obj = loadmat(fname)
            self.Obj = Obj
            self.NewSession.setDisabled(False)
            self.NewSession.setChecked(False)
            self.NewSession.click() # click the NewSession button to trigger the save dialog
            self.NewSession.setDisabled(True) # You must start a NewSession after loading a new file, and you can't continue that session
            widget_dict = {w.objectName(): w for w in self.centralwidget.findChildren((QtWidgets.QLineEdit, QtWidgets.QComboBox,QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox))}
            widget_dict.update({w.objectName(): w for w in self.TrainingParameters.findChildren(QtWidgets.QDoubleSpinBox)})
            widget_dict.update({w.objectName(): w for w in self.Opto_dialog.findChildren((QtWidgets.QLineEdit, QtWidgets.QComboBox,QtWidgets.QDoubleSpinBox))})  # update optogenetics parameters from the loaded file
            if hasattr(self, 'LaserCalibration_dialog'):
                widget_dict.update({w.objectName(): w for w in self.LaserCalibration_dialog.findChildren((QtWidgets.QLineEdit, QtWidgets.QComboBox,QtWidgets.QDoubleSpinBox))})  # update laser calibration parameters from the loaded file
            try:
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
                        elif isinstance(widget, QtWidgets.QSpinBox):
                            widget.setValue(int(value[-1]))
                    else:
                        widget = widget_dict[key]
                        if not isinstance(widget, QtWidgets.QComboBox):
                            widget.clear()
            except Exception as e:
                # Catch the exception and print error information
                print("An error occurred:")
                print(traceback.format_exc())
            try:
                # visualization when loading the data
                self._LoadVisualization()
            except Exception as e:
                # Catch the exception and print error information
                print("An error occurred:")
                print(traceback.format_exc())

    def _LoadVisualization(self):
        '''To visulize the training when loading a session'''
        self.ToInitializeVisual=1
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
        if self.GeneratedTrials.B_AnimalResponseHistory.size==0:
            return
        # this is a bug to use the scipy.io.loadmat or savemat (it will change the dimension of the nparray)
        self.GeneratedTrials.B_AnimalResponseHistory=self.GeneratedTrials.B_AnimalResponseHistory[0]
        self.GeneratedTrials.B_TrialStartTime=self.GeneratedTrials.B_TrialStartTime[0]
        self.GeneratedTrials.B_DelayStartTime=self.GeneratedTrials.B_DelayStartTime[0]
        self.GeneratedTrials.B_TrialEndTime=self.GeneratedTrials.B_TrialEndTime[0]
        self.GeneratedTrials.B_GoCueTime=self.GeneratedTrials.B_GoCueTime[0]

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

    def _AskSave(self):
        reply = QMessageBox.question(self, 'New Session:', 'Do you want to save the result?',QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self._Save()
            print('Saved')
        elif reply == QMessageBox.No:
            pass
        else:
            pass
        
    def _StopCurrentSession(self):
        # stop the current session
        self.Start.setStyleSheet("background-color : green;")
        self.Start.setStyleSheet("background-color : none")
        self.Start.setChecked(False)
        # waiting for the finish of the last trial
        if self.ANewTrial==0:
            self.WarningLabel.setText('Waiting for the finish of the last trial!')
            self.WarningLabel.setStyleSheet("color: red;")
            while 1:
                QApplication.processEvents()
                if self.ANewTrial==1:
                    self.WarningLabel.setText('')
                    self.WarningLabel.setStyleSheet("color: red;")
                    break
    def _thread_complete(self):
        '''complete of a trial'''
        self.ANewTrial=1
    def _thread_complete2(self):
        '''complete of receive licks'''
        self.ToReceiveLicks=1
    def _thread_complete3(self):
        '''complete of update figures'''
        self.ToUpdateFigure=1
    def _thread_complete4(self):
        '''complete of generating a trial'''
        self.ToGenerateATrial=1
    def _Start(self):
        self.NewSession.setDisabled(False)
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
        # waiting for the finish of the last trial
        if self.StartANewSession==1 and self.ANewTrial==0:
            self.WarningLabel.setText('Waiting for the finish of the last trial!')
            self.WarningLabel.setStyleSheet("color: red;")
            while 1:
                QApplication.processEvents()
                if self.ANewTrial==1:
                    self.WarningLabel.setText('')
                    self.WarningLabel.setStyleSheet("color: red;")
                    break

        # to see if we should start a new session
        if self.StartANewSession==1 and self.ANewTrial==1:
            GeneratedTrials=GenerateTrials(self)
            self.GeneratedTrials=GeneratedTrials
            self.StartANewSession=0
            PlotM=PlotV(win=self,GeneratedTrials=GeneratedTrials,width=5, height=4)
            PlotM.finish=1
            #generate the first trial outside the loop, only for new session
            self.ToReceiveLicks=1
            self.ToUpdateFigure=1
            self.ToGenerateATrial=1
            self.ToInitializeVisual=1
            GeneratedTrials._GenerateATrial(self.Channel4)
        else:
            GeneratedTrials=self.GeneratedTrials
        if self.ToInitializeVisual==1: # only run once
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
            self.ToInitializeVisual=0
            # create workers
            worker1 = Worker(GeneratedTrials._GetAnimalResponse,self.Channel,self.Channel3)
            worker1.signals.finished.connect(self._thread_complete)
            workerLick = Worker(GeneratedTrials._GetLicks,self.Channel2)
            workerLick.signals.finished.connect(self._thread_complete2)
            workerPlot = Worker(PlotM._Update,GeneratedTrials=GeneratedTrials,Channel=self.Channel2)
            workerPlot.signals.finished.connect(self._thread_complete3)
            workerGenerateAtrial = Worker(GeneratedTrials._GenerateATrial,self.Channel4)
            workerGenerateAtrial.signals.finished.connect(self._thread_complete4)
            workerStartTrialLoop = Worker(self._StartTrialLoop,GeneratedTrials,worker1,workerPlot,workerGenerateAtrial)
            self.worker1=worker1
            self.workerLick=workerLick
            self.workerPlot=workerPlot
            self.workerGenerateAtrial=workerGenerateAtrial
            self.workerStartTrialLoop=workerStartTrialLoop
        else:
            PlotM=self.PlotM
            worker1=self.worker1
            workerLick=self.workerLick
            workerPlot=self.workerPlot
            workerGenerateAtrial=self.workerGenerateAtrial
            workerStartTrialLoop=self.workerStartTrialLoop
        
        self.threadpool5.start(workerStartTrialLoop) # I just found the QApplication.processEvents() was better to reduce delay time between trial end the the next trial start
        # _GetLicks also receive LeftRewardDeliveryTime, RightRewardDeliveryTime and RewardOutcomeTime. 
        GeneratedTrials._GetLicks(self.Channel2)

    def _StartTrialLoop(self,GeneratedTrials,worker1,workerPlot,workerGenerateAtrial):
        while self.Start.isChecked():
            QApplication.processEvents()
            if self.ANewTrial==1 and self.ToGenerateATrial==1 and self.Start.isChecked(): #and GeneratedTrials.GeneFinish==1: \
                self.ANewTrial=0 # can start a new trial when we receive the trial end signal from Bonsai
                print(GeneratedTrials.B_CurrentTrialN)     
                #initiate the generated trial
                GeneratedTrials._InitiateATrial(self.Channel,self.Channel4)
                #get the response of the animal using a different thread
                self.threadpool.start(worker1)
                #receive licks and update figures
                if self.ToUpdateFigure==1:
                    self.ToUpdateFigure=0
                    self.threadpool3.start(workerPlot)
                #generate a new trial
                GeneratedTrials.GeneFinish=0
                self.ToGenerateATrial=0
                self.threadpool4.start(workerGenerateAtrial)
            
    def _OptogeneticsB(self):
        ''' optogenetics control in the main window'''
        if self.OptogeneticsB.currentText()=='on':
            self._Optogenetics() # press the optogenetics icon
            self.action_Optogenetics.setChecked(True)
            self.Opto_dialog.show()
        else:
            self.action_Optogenetics.setChecked(False)
            self.Opto_dialog.hide()
    def _GiveLeft(self):
        self.Channel.LeftValue(float(self.GiveWaterL.text())*1000) 
        self.Channel3.ManualWater_Left(int(1))
        self.Channel.LeftValue(float(self.LeftValue.text())*1000)
    def _GiveRight(self):
        self.Channel.RightValue(float(self.GiveWaterR.text())*1000)
        self.Channel3.ManualWater_Right(int(1))
        self.Channel.RightValue(float(self.RightValue.text())*1000)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    # Run your application's event loop and stop after closing all windows
    sys.exit(app.exec())
