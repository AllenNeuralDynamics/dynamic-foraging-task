import sys, os,traceback,json
import numpy as np
from datetime import date,timedelta,datetime
from PyQt5.QtWidgets import QApplication, QDialog, QMainWindow, QMessageBox,QFileDialog,QVBoxLayout,QLineEdit,QWidget,QSizePolicy
from PyQt5 import QtWidgets,QtGui,QtCore
from PyQt5.QtCore import QThreadPool,Qt,QMetaObject
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from scipy.io import savemat, loadmat
from ForagingGUI import Ui_ForagingGUI
import rigcontrol
from pyOSC3.OSC3 import OSCStreamingClient
from Visualization import PlotV
from Dialogs import OptogeneticsDialog,WaterCalibrationDialog,CameraDialog,ManipulatorDialog,MotorStageDialog,LaserCalibrationDialog
from MyFunctions import GenerateTrials, Worker
import warnings
import json 
#warnings.filterwarnings("ignore")
#import subprocess
#import h5py
#from scipy import stats
#from PyQt5.uic import loadUi
#from threading import Event

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)

def dump_single_line(obj, fp):
    for key, value in obj.items():
        fp.write(json.dumps({key: value}, indent=None, cls=NumpyEncoder, separators=(',', ':')))
        fp.write('\n')

class Window(QMainWindow, Ui_ForagingGUI):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.SettingFile=os.path.join(os.path.expanduser("~"), "Documents")+'\\'+'ForagingSettings\\ForagingSettings.json'
        try:
            # Open the JSON settings file
            with open(self.SettingFile, 'r') as f:
                Settings = json.load(f)
            self.default_saveFolder=Settings['default_saveFolder']
        except:
            self.default_saveFolder=os.path.join(os.path.expanduser("~"), "Documents")+'\\'
        self.StartANewSession=1 # to decide if should start a new session
        self.ToInitializeVisual=1
        self.FigureUpdateTooSlow=0 # if the FigureUpdateTooSlow is true, using different process to update figures
        self.ANewTrial=1 # permission to start a new trial
        self.UpdateParameters=1 # permission to update parameters
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
        self.RewardFamilies=[[[8,1],[6, 1],[3, 1],[1, 1]],[[8, 1], [1, 1]],[[1,0],[.9,.1],[.8,.2],[.7,.3],[.6,.4],[.5,.5]],[[6, 1],[3, 1],[1, 1]]]
        self.WaterPerRewardedTrial=0.005 
        self._ShowRewardPairs() # show reward pairs
        self._GetTrainingParameters() # get initial training parameters
        self.connectSignalsSlots()
    def _InitializeBonsai(self):
        #os.system(" E:\\GitHub\\dynamic-foraging-task\\bonsai\\Bonsai.exe E:\\GitHub\\dynamic-foraging-task\\src\\workflows\\foraging.bonsai  --start") 
        #workflow_file = "E:\\GitHub\\dynamic-foraging-task\\src\\workflows\\foraging.bonsai"
        #result=subprocess.run(["E:\\GitHub\\dynamic-foraging-task\\bonsai\\Bonsai.exe", "workflows", "--start", workflow_file], check=True)
        #output = result.stdout.decode()
        #workflow_id = re.search(r"Workflow started with ID: (.+)", output).group(1)
        #print(f"Workflow started with ID {workflow_id}")

        # normal behavior events
        self.ip = "127.0.0.1"
        self.request_port = 4002
        self.client = OSCStreamingClient()  # Create client 
        self.client.connect((self.ip, self.request_port))
        self.Channel = rigcontrol.RigClient(self.client)
        # licks, LeftRewardDeliveryTime and RightRewardDeliveryTime 
        self.request_port2 = 4003
        self.client2 = OSCStreamingClient()  
        self.client2.connect((self.ip, self.request_port2))
        self.Channel2 = rigcontrol.RigClient(self.client2)
        # manually give water
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
        self.AutoReward.clicked.connect(self._AutoReward)
        self.NextBlock.clicked.connect(self._NextBlock)
        self.OptogeneticsB.activated.connect(self._OptogeneticsB) # turn on/off optogenetics
        self.UncoupledReward.textChanged.connect(self._ShowRewardPairs)
        self.UncoupledReward.returnPressed.connect(self._ShowRewardPairs)
        self.Task.currentIndexChanged.connect(self._ShowRewardPairs)
        self.TotalWater.textChanged.connect(self._SuggestedWater)
        self.ShowNotes.setStyleSheet("background-color: #F0F0F0;")
        # check the change of all of the QLineEdit, QDoubleSpinBox and QSpinBox
        for container in [self.TrainingParameters, self.centralwidget, self.Opto_dialog]:
            # Iterate over each child of the container that is a QLineEdit or QDoubleSpinBox
            for child in container.findChildren((QtWidgets.QLineEdit,QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox)):        
                child.textChanged.connect(self._CheckTextChange)
        # Opto_dialog can not detect natural enter press, so returnPressed is used here. 
        for container in [self.Opto_dialog]:
            # Iterate over each child of the container that is a QLineEdit or QDoubleSpinBox
            for child in container.findChildren((QtWidgets.QLineEdit)):        
                child.returnPressed.connect(self.keyPressEvent)

    def keyPressEvent(self, event=None):
        '''Enter press to allow change of parameters'''
        # Get the parameters before change
        if hasattr(self, 'GeneratedTrials') and self.ToInitializeVisual==0: # use the current GUI paramters when no session starts running
            Parameters=self.GeneratedTrials
        else:
            Parameters=self
        if event==None:
            event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, Qt.Key_Return, Qt.KeyboardModifiers())
        if (event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter):
            # handle the return key press event here
            print("Parameter changes confirmed!")
            # prevent the default behavior of the return key press event
            event.accept()
            self.UpdateParameters=1 # Changes are allowed
            # change color to black
            for container in [self.TrainingParameters, self.centralwidget, self.Opto_dialog]:
                # Iterate over each child of the container that is a QLineEdit or QDoubleSpinBox
                for child in container.findChildren((QtWidgets.QLineEdit,QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox)):
                    if child.objectName()=='qt_spinbox_lineedit':
                        continue
                    if child.isEnabled()==False:
                        continue
                    child.setStyleSheet('color: black;')
                    child.setStyleSheet('background-color: white;')
                    if child.objectName()=='AnimalName' and child.text()=='':
                        child.setText(getattr(Parameters, 'TP_'+child.objectName()))
                        continue
                    if child.objectName()=='TotalWater' or child.objectName()=='AnimalName' or child.objectName()=='WeightBefore'  or child.objectName()=='WeightAfter' or child.objectName()=='ExtraWater':
                        continue
                    if child.objectName()=='UncoupledReward':
                        Correct=self._CheckFormat(child)
                        if Correct ==0: # incorrect format; don't change
                            child.setText(getattr(Parameters, 'TP_'+child.objectName()))
                        continue
                    # check valid for empty condition
                    try:
                        # it's valid float
                        float(child.text())
                    except ValueError:
                        if isinstance(child, QtWidgets.QDoubleSpinBox):
                            child.setValue(float(getattr(Parameters, 'TP_'+child.objectName())))
                        elif isinstance(child, QtWidgets.QSpinBox):
                            child.setValue(int(getattr(Parameters, 'TP_'+child.objectName())))
                        else:
                            # Invalid float. Do not change the parameter
                            child.setText(getattr(Parameters, 'TP_'+child.objectName()))
            # update the current training parameters
            self._GetTrainingParameters()
    
    def _CheckTextChange(self):
        '''Check if the text change is reasonable'''
        # Get the parameters before change
        if hasattr(self, 'GeneratedTrials'):
            Parameters=self.GeneratedTrials
        else:
            Parameters=self
        for container in [self.TrainingParameters, self.centralwidget, self.Opto_dialog]:
            # Iterate over each child of the container that is a QLineEdit or QDoubleSpinBox
            for child in container.findChildren((QtWidgets.QLineEdit,QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox)):
                if child.objectName()=='qt_spinbox_lineedit' or child.isEnabled()==False: # I don't understand where the qt_spinbox_lineedit comes from. 
                    continue
                if getattr(Parameters, 'TP_'+child.objectName())!=child.text() :
                    self.Continue=0
                    if child.objectName()=='AnimalName' or child.objectName()=='UncoupledReward' or child.objectName()=='WeightBefore'  or child.objectName()=='WeightAfter' or child.objectName()=='ExtraWater':
                        child.setStyleSheet('color: red;')
                        self.Continue=1
                    if child.text()=='': # If it's empty, changing the background color and waiting for the confirming
                        self.UpdateParameters=0
                        child.setStyleSheet('background-color: red;')
                        self.Continue=1
                    if child.objectName()=='RunLength' or child.objectName()=='WindowSize' or child.objectName()=='StepSize':
                        if child.text()=='':
                            child.setValue(int(getattr(Parameters, 'TP_'+child.objectName())))
                            child.setStyleSheet('color: black;')
                            child.setStyleSheet('background-color: white;')
                    if (child.objectName()=='RewardFamily' or child.objectName()=='RewardPairsN' or child.objectName()=='BaseRewardSum') and (child.text()!=''):
                        Correct=self._CheckFormat(child)
                        if Correct ==0: # incorrect format; don't change
                            child.setText(getattr(Parameters, 'TP_'+child.objectName()))
                        self._ShowRewardPairs()
                    if self.Continue==1:
                        continue
                    child.setStyleSheet('color: red;')
                    try:
                        # it's valid float
                        float(child.text())
                        self.UpdateParameters=0 # Changes are not allowed until press is typed
                    except ValueError:
                        # Invalid float. Do not change the parameter
                        if isinstance(child, QtWidgets.QDoubleSpinBox):
                            child.setValue(float(getattr(Parameters, 'TP_'+child.objectName())))
                        elif isinstance(child, QtWidgets.QSpinBox):
                            child.setValue(int(getattr(Parameters, 'TP_'+child.objectName())))
                        else:
                            child.setText(getattr(Parameters, 'TP_'+child.objectName()))
                        child.setText(getattr(Parameters, 'TP_'+child.objectName()))
                        child.setStyleSheet('color: black;')
                        self.UpdateParameters=1
                else:
                    child.setStyleSheet('color: black;')
                    child.setStyleSheet('background-color: white;')
    def _CheckFormat(self,child):
        '''Check if the input format is correct'''
        if child.objectName()=='RewardFamily': # When we change the RewardFamily, sometimes the RewardPairsN is larger than available reward pairs in this family. 
            try:
                self.RewardFamilies[int(self.RewardFamily.text())-1]
                if int(self.RewardPairsN.text())>len(self.RewardFamilies[int(self.RewardFamily.text())-1]):
                    self.RewardPairsN.setText(str(len(self.RewardFamilies[int(self.RewardFamily.text())-1])))
                return 1
            except:
                return 0
        if child.objectName()=='RewardFamily' or child.objectName()=='RewardPairsN' or child.objectName()=='BaseRewardSum':
            try:
                self.RewardPairs=self.RewardFamilies[int(self.RewardFamily.text())-1][:int(self.RewardPairsN.text())]
                if int(self.RewardPairsN.text())>len(self.RewardFamilies[int(self.RewardFamily.text())-1]):
                    return 0
                else:
                    return 1
            except Exception as e: 
                return 0
        if child.objectName()=='UncoupledReward':
            try:
                input_string=self.UncoupledReward.text()
                if input_string=='': # do not permit empty uncoupled reward
                    return 0
                # remove any square brackets and spaces from the string
                input_string = input_string.replace('[','').replace(']','').replace(',', ' ')
                # split the remaining string into a list of individual numbers
                num_list = input_string.split()
                # convert each number in the list to a float
                num_list = [float(num) for num in num_list]
                # create a numpy array from the list of numbers
                self.RewardProb=np.array(num_list)
                return 1
            except Exception as e: 
                return 0
        else:
            return 1
        
    def _SuggestedWater(self):
        '''Change suggested water based on total water'''
        try:
            self.T_SuggestedWater=float(self.TotalWater.text())-float(self.GeneratedTrials.BS_TotalReward)
            self.SuggestedWater.setText(str(np.round(self.T_SuggestedWater,3)))
        except:
            self.SuggestedWater.setText(self.TotalWater.text())

    def _GetTrainingParameters(self):
        '''Get training parameters'''
        # Iterate over each container to find child widgets and store their values in self
        for container in [self.TrainingParameters, self.centralwidget, self.Opto_dialog]:
            # Iterate over each child of the container that is a QLineEdit or QDoubleSpinBox
            for child in container.findChildren((QtWidgets.QLineEdit, QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox)):
                if child.objectName()=='qt_spinbox_lineedit':
                    continue
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

    def _ShowRewardPairs(self):
        '''Show reward pairs'''
        if self.Task.currentText() in ['Coupled Baiting','Coupled Without Baiting']:
            self.label_6.setEnabled(True)
            self.label_7.setEnabled(True)
            self.label_8.setEnabled(True)
            self.BaseRewardSum.setEnabled(True)
            self.RewardPairsN.setEnabled(True)
            self.RewardFamily.setEnabled(True)
            self.label_20.setEnabled(False)
            self.UncoupledReward.setEnabled(False)
        elif self.Task.currentText() in ['Uncoupled Baiting','Uncoupled Without Baiting']:
            self.label_6.setEnabled(False)
            self.label_7.setEnabled(False)
            self.label_8.setEnabled(False)
            self.BaseRewardSum.setEnabled(False)
            self.RewardPairsN.setEnabled(False)
            self.RewardFamily.setEnabled(False)
            self.label_20.setEnabled(True)
            self.UncoupledReward.setEnabled(True)
        try:
            if self.Task.currentText() in ['Coupled Baiting','Coupled Without Baiting']:
                self.RewardPairs=self.RewardFamilies[int(self.RewardFamily.text())-1][:int(self.RewardPairsN.text())]
                self.RewardProb=np.array(self.RewardPairs)/np.expand_dims(np.sum(self.RewardPairs,axis=1),axis=1)*float(self.BaseRewardSum.text())
                if hasattr(self, 'GeneratedTrials'):
                    self.ShowRewardPairs.setText('Reward pairs: '+str(np.round(self.RewardProb,2))+'\n\n'+'Current pair: '+str(np.round(self.GeneratedTrials.B_RewardProHistory[:,self.GeneratedTrials.B_CurrentTrialN],2))) 
                else:
                    self.ShowRewardPairs.setText('Reward pairs: '+str(np.round(self.RewardProb,2))+'\n\n'+'Current pair: ') 
            elif self.Task.currentText() in ['Uncoupled Baiting','Uncoupled Without Baiting']:
                input_string=self.UncoupledReward.text()
                # remove any square brackets and spaces from the string
                input_string = input_string.replace('[','').replace(']','').replace(',', ' ')
                # split the remaining string into a list of individual numbers
                num_list = input_string.split()
                # convert each number in the list to a float
                num_list = [float(num) for num in num_list]
                # create a numpy array from the list of numbers
                self.RewardProb=np.array(num_list)
                if hasattr(self, 'GeneratedTrials'):
                    self.ShowRewardPairs.setText('Reward pairs: '+str(np.round(self.RewardProb,2))+'\n\n'+'Current pair: '+str(np.round(self.GeneratedTrials.B_RewardProHistory[:,self.GeneratedTrials.B_CurrentTrialN],2))) 
                else:
                    self.ShowRewardPairs.setText('Reward pairs: '+str(np.round(self.RewardProb,2))+'\n\n'+'Current pair: ') 
        except Exception as e:
            # Catch the exception and print error information
            print("An error occurred:")
            print(traceback.format_exc())
    def closeEvent(self, event):
        self._StopCurrentSession() # stop the current session first
        reply = QMessageBox.question(self, 'Foraging Close', 'Do you want to save the current result?',QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)
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
        response = QMessageBox.question(self,'Save and Exit:', "Do you want to save the current result?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,QMessageBox.Yes)
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
        if self.WeightBefore.text()=='' or self.WeightAfter.text()=='' or self.ExtraWater.text()=='':
            response = QMessageBox.question(self,'Save without weight or extra water:', "Do you want to save without weight or extra water information provided?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,QMessageBox.Yes)
            if response==QMessageBox.Yes:
                pass
                self.WarningLabel.setText('Saving without weight or extra water!')
                self.WarningLabel.setStyleSheet("color: red;")
            elif response==QMessageBox.No:
                return
            elif response==QMessageBox.Cancel:
                return
        # this should be improved in the future. Need to get the last LeftRewardDeliveryTime and RightRewardDeliveryTime
        if hasattr(self, 'GeneratedTrials'):
            self.GeneratedTrials._GetLicks(self.Channel2)
        
        #ParamsFile = os.path.join(self.default_saveFolder, self.AnimalName.text(), f'{self.AnimalName.text()}_{date.today()}.json')
        SaveFileMat = os.path.join(self.default_saveFolder, self.AnimalName.text(), f'{self.AnimalName.text()}_{date.today()}.mat')
        SaveFileJson= os.path.join(self.default_saveFolder, self.AnimalName.text(), f'{self.AnimalName.text()}_{date.today()}.json')
        SaveFileParJson= os.path.join(self.default_saveFolder, self.AnimalName.text(), f'{self.AnimalName.text()}_{date.today()}_par.json')
        if not os.path.exists(os.path.dirname(SaveFileJson)):
            os.makedirs(os.path.dirname(SaveFileJson))
            print(f"Created new folder: {os.path.dirname(SaveFileJson)}")
        N=0
        while 1:
            if os.path.isfile(SaveFileMat) or os.path.isfile(SaveFileJson)or os.path.isfile(SaveFileParJson):
                N=N+1
                SaveFileMat=os.path.join(self.default_saveFolder, self.AnimalName.text(), f'{self.AnimalName.text()}_{date.today()}_{N}.mat')
                SaveFileJson=os.path.join(self.default_saveFolder, self.AnimalName.text(), f'{self.AnimalName.text()}_{date.today()}_{N}.json')
                SaveFileParJson=os.path.join(self.default_saveFolder, self.AnimalName.text(), f'{self.AnimalName.text()}_{date.today()}_{N}_par.json')
            else:
                break
        Names = QFileDialog.getSaveFileName(self, 'Save File',SaveFileJson,"JSON files (*.json);;MAT files (*.mat);;JSON parameters (*_par.json)")
        if Names[1]=='JSON parameters (*_par.json)':
            self.SaveFile=Names[0].replace('.json', '_par.json')
        else:
            self.SaveFile=Names[0]
        if self.SaveFile == '':
            self.WarningLabel.setText('Discard saving!')
            self.WarningLabel.setStyleSheet("color: red;")
        if self.SaveFile != '':
            if hasattr(self, 'GeneratedTrials'):
                if hasattr(self.GeneratedTrials, 'Obj'):
                    Obj=self.GeneratedTrials.Obj
            else:
                Obj={}
            # save training parameters
            for child in self.centralwidget.findChildren(QtWidgets.QTextEdit):
                Obj[child.objectName()]=child.toPlainText()
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
            Obj2=Obj.copy()
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
            # save other events, e.g. session start time
            for attr_name in dir(self):
                if attr_name.startswith('Other_'):
                    Obj[attr_name] = getattr(self, attr_name)
            # save laser calibration results 
            if hasattr(self, 'LaserCalibration_dialog'):
                # Do something if self has the GeneratedTrials attribute
                # Iterate over all attributes of the GeneratedTrials object
                for attr_name in dir(self.LaserCalibration_dialog):
                    if attr_name.startswith('LCM_'):
                        Obj[attr_name] = getattr(self.LaserCalibration_dialog, attr_name)
            # save Json or mat
            if self.SaveFile.endswith('.mat'):
            # Save data to a .mat file
                savemat(self.SaveFile, Obj) 
            elif self.SaveFile.endswith('par.json'):
                with open(self.SaveFile, "w") as outfile:
                    json.dump(Obj2, outfile, indent=4, cls=NumpyEncoder)
            elif self.SaveFile.endswith('.json'):
                with open(self.SaveFile, "w") as outfile:
                    json.dump(Obj, outfile, indent=4, cls=NumpyEncoder)
                      
    def _Open(self):
        self._StopCurrentSession() # stop current session first
        self.NewSession.setChecked(True)
        Reply=self._NewSession()
        if Reply == QMessageBox.Yes or Reply == QMessageBox.No:
            self.NewSession.setDisabled(True) # You must start a NewSession after loading a new file, and you can't continue that session
        elif Reply == QMessageBox.Cancel:
            return

        fname, _ = QFileDialog.getOpenFileName(self, 'Open file', self.default_saveFolder, "Behavior JSON files (*.json);;Behavior MAT files (*.mat);;JSON parameters (*_par.json)")
        self.fname=fname
        if fname:
            if fname.endswith('.mat'):
                Obj = loadmat(fname)
            elif fname.endswith('.json'):
                f = open (fname, "r")
                Obj = json.loads(f.read())
                f.close()
            self.Obj = Obj
            widget_dict = {w.objectName(): w for w in self.centralwidget.findChildren((QtWidgets.QLineEdit,QtWidgets.QTextEdit, QtWidgets.QComboBox,QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox))}
            widget_dict.update({w.objectName(): w for w in self.TrainingParameters.findChildren(QtWidgets.QDoubleSpinBox)})
            widget_dict.update({w.objectName(): w for w in self.Opto_dialog.findChildren((QtWidgets.QLineEdit, QtWidgets.QComboBox,QtWidgets.QDoubleSpinBox))})  # update optogenetics parameters from the loaded file
            
            if hasattr(self, 'LaserCalibration_dialog'):
                widget_dict.update({w.objectName(): w for w in self.LaserCalibration_dialog.findChildren((QtWidgets.QLineEdit, QtWidgets.QComboBox,QtWidgets.QDoubleSpinBox))})  # update laser calibration parameters from the loaded file
            try:
                for key in widget_dict.keys():
                    if key in Obj:
                        # skip some keys
                        if key=='ExtraWater':
                            self.ExtraWater.setText('')
                            continue
                        widget = widget_dict[key]
                        try: # load the paramter used by last trial
                            value=np.array([Obj['TP_'+key][-2]])
                            Tag=0
                        except: # sometimes we only have training parameters, no behavior parameters
                            value=Obj[key]
                            Tag=1
                        if len(value)==0:
                            value=np.array([''], dtype='<U1')
                            Tag=0
                        if type(value)==np.ndarray:
                            Tag=0
                        if isinstance(widget, QtWidgets.QLineEdit):
                            if Tag==0:
                                widget.setText(value[-1])
                            elif Tag==1:
                                widget.setText(value)
                        elif isinstance(widget, QtWidgets.QComboBox):
                            if Tag==0:
                                index = widget.findText(value[-1])
                            elif Tag==1:
                                index = widget.findText(value)
                            if index != -1:
                                widget.setCurrentIndex(index)
                        elif isinstance(widget, QtWidgets.QDoubleSpinBox):
                            if Tag==0:
                                widget.setValue(float(value[-1]))
                            elif Tag==1:
                                widget.setValue(float(value))
                        elif isinstance(widget, QtWidgets.QSpinBox):
                            if Tag==0:
                                widget.setValue(int(value[-1]))
                            elif Tag==1:
                                widget.setValue(int(value))
                        elif isinstance(widget, QtWidgets.QTextEdit):
                            if Tag==0:
                                widget.setText(value[-1])
                            elif Tag==1:
                                widget.setText(value)
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
                # delete GeneratedTrials
                del self.GeneratedTrials
        else:
            self.NewSession.setDisabled(False)

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
                    # transfer list to numpy array
                    if type(getattr(self.GeneratedTrials,attr_name))== np.ndarray:
                        value=np.array(value)
                    # Set the attribute in the GeneratedTrials object
                    setattr(self.GeneratedTrials, attr_name, value)
                except:
                    pass
        if self.GeneratedTrials.B_AnimalResponseHistory.size==0:
            del self.GeneratedTrials
            return
        # for mat file
        if self.fname.endswith('.mat'):
            # this is a bug to use the scipy.io.loadmat or savemat (it will change the dimension of the nparray)
            self.GeneratedTrials.B_AnimalResponseHistory=self.GeneratedTrials.B_AnimalResponseHistory[0]
            self.GeneratedTrials.B_TrialStartTime=self.GeneratedTrials.B_TrialStartTime[0]
            self.GeneratedTrials.B_DelayStartTime=self.GeneratedTrials.B_DelayStartTime[0]
            self.GeneratedTrials.B_TrialEndTime=self.GeneratedTrials.B_TrialEndTime[0]
            self.GeneratedTrials.B_GoCueTime=self.GeneratedTrials.B_GoCueTime[0]
            self.GeneratedTrials.B_RewardOutcomeTime=self.GeneratedTrials.B_RewardOutcomeTime[0]
            #self.GeneratedTrials._GenerateATrial(self.Channel4)
            
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
        reply = QMessageBox.question(self, 'Clear parameters:', 'Do you want to clear training parameters?',QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            for child in self.TrainingParameters.findChildren(QtWidgets.QLineEdit)+ self.centralwidget.findChildren(QtWidgets.QLineEdit):
                if child.isEnabled():
                    child.clear()
        else:
            pass

    def _New(self):
        self._Clear()

    def _AutoReward(self):
        if self.AutoReward.isChecked():
            self.AutoReward.setStyleSheet("background-color : green;")
        else:
            self.AutoReward.setStyleSheet("background-color : none")
    def _NextBlock(self):
        if self.NextBlock.isChecked():
            self.NextBlock.setStyleSheet("background-color : green;")
        else:
            self.NextBlock.setStyleSheet("background-color : none")
    def _NewSession(self):
        if self.NewSession.isChecked():
            if self.ToInitializeVisual==0: # Do not ask to save when no session starts running
                reply = QMessageBox.question(self, 'New Session:', 'Do you want to save the current result?',QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)
            else:
                reply=QMessageBox.No
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
            reply=QMessageBox.Cancel
        return reply

    def _AskSave(self):
        reply = QMessageBox.question(self, 'New Session:', 'Do you want to save the current result?',QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)
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
            self.keyPressEvent()
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
            self.WarningLabel.setText('')
            self.WarningLabel.setStyleSheet("color: gray;")
            self.SessionStartTime=datetime.now()
            self.Other_SessionStartTime=str(self.SessionStartTime) # for saving
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
            # delete licks from the previous session
            GeneratedTrials._DeletePreviousLicks(self.Channel2)
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
        
        self.test=1
        if self.test==1:
            self._StartTrialLoop(GeneratedTrials,worker1,workerPlot,workerGenerateAtrial)
        else:
            self.threadpool5.start(workerStartTrialLoop) # I just found the QApplication.processEvents() was better to reduce delay time between trial end the the next trial start

    def _StartTrialLoop(self,GeneratedTrials,worker1,workerPlot,workerGenerateAtrial):
        while self.Start.isChecked():
            QApplication.processEvents()
            if self.ANewTrial==1 and self.ToGenerateATrial==1 and self.Start.isChecked(): #and GeneratedTrials.GeneFinish==1: \
                self.ANewTrial=0 # can start a new trial when we receive the trial end signal from Bonsai
                GeneratedTrials.B_CurrentTrialN+=1
                print('Current trial: '+str(GeneratedTrials.B_CurrentTrialN+1))     
                #initiate the generated trial
                GeneratedTrials._InitiateATrial(self.Channel,self.Channel4)
                #get the response of the animal using a different thread
                self.threadpool.start(worker1)
                #receive licks and update figures
                #if self.ToUpdateFigure==1:
                #    self.ToUpdateFigure=0
                 #   self.threadpool3.start(workerPlot)
                self.PlotM._Update(GeneratedTrials=GeneratedTrials,Channel=self.Channel2)
                #generate a new trial
                GeneratedTrials.GeneFinish=0
                self.ToGenerateATrial=0
                if self.test==1:
                    self.ToGenerateATrial=1
                    GeneratedTrials._GenerateATrial(self.Channel4)
                else:
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
        '''manually give left water'''
        self.Channel.LeftValue(float(self.GiveWaterL.text())*1000) 
        self.Channel3.ManualWater_Left(int(1))
        self.Channel.LeftValue(float(self.LeftValue.text())*1000)
    def _GiveRight(self):
        '''manually give right water'''
        self.Channel.RightValue(float(self.GiveWaterR.text())*1000)
        self.Channel3.ManualWater_Right(int(1))
        self.Channel.RightValue(float(self.RightValue.text())*1000)

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling,1)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps,True)
    QApplication.setAttribute(Qt.AA_DisableHighDpiScaling,False)
    QApplication.setAttribute(Qt.AA_Use96Dpi,False)
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    # Run your application's event loop and stop after closing all windows
    sys.exit(app.exec())
