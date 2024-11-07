import sys
import os
import traceback
import json
import time
import subprocess
import math
import logging
import socket
import harp
import threading
from random import randint
import yaml
import copy
import shutil
from pathlib import Path
from datetime import date, datetime, timezone
import csv
from aind_slims_api import SlimsClient
from aind_slims_api import models
import serial
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from scipy.io import savemat, loadmat
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QSizePolicy
from PyQt5.QtWidgets import QFileDialog,QVBoxLayout, QGridLayout, QLabel
from PyQt5 import QtWidgets,QtGui,QtCore, uic
from PyQt5.QtCore import QThreadPool,Qt,QThread
from pyOSC3.OSC3 import OSCStreamingClient
import webbrowser

from StageWidget.main import get_stage_widget

import foraging_gui
import foraging_gui.rigcontrol as rigcontrol
from foraging_gui.Visualization import PlotV,PlotLickDistribution,PlotTimeDistribution
from foraging_gui.Dialogs import OptogeneticsDialog,WaterCalibrationDialog,CameraDialog,MetadataDialog
from foraging_gui.Dialogs import LaserCalibrationDialog
from foraging_gui.Dialogs import LickStaDialog,TimeDistributionDialog
from foraging_gui.Dialogs import AutoTrainDialog, MouseSelectorDialog
from foraging_gui.MyFunctions import GenerateTrials, Worker,TimerWorker, NewScaleSerialY, EphysRecording
from foraging_gui.stage import Stage
from foraging_gui.bias_indicator import BiasIndicator
from foraging_gui.warning_widget import WarningWidget
from foraging_gui.GenerateMetadata import generate_metadata
from foraging_gui.RigJsonBuilder import build_rig_json
from aind_data_schema.core.session import Session
from aind_data_schema_models.modalities import Modality

logger = logging.getLogger(__name__)
logger.root.handlers.clear() # clear handlers so console output can be configured

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()  # Convert NumPy array to a list
        if isinstance(obj, np.integer):
            return int(obj)  # Convert np.int32 to a regular int
        if isinstance(obj, np.float64) and np.isnan(obj):
            return 'NaN'  # Represent NaN as a string
        return super(NumpyEncoder, self).default(obj)

class Window(QMainWindow):
    Time = QtCore.pyqtSignal(int) # Photometry timer signal
    sessionGenerated = QtCore.pyqtSignal(Session)  # signal to indicate Session has been generated

    def __init__(self, parent=None,box_number=1,start_bonsai_ide=True):
        logging.info('Creating Window')

        # create warning widget
        self.warning_log_tag = 'warning_widget'  # TODO: How to set this or does it matter?

        super().__init__(parent)

        # Process inputs        
        self.box_number=box_number
        mapper = {
            1:'A',
            2:'B',
            3:'C',
            4:'D',
        }
        self.box_letter = mapper[box_number]
        self.start_bonsai_ide = start_bonsai_ide

        # Load Settings that are specific to this computer  
        self.SettingFolder=os.path.join(os.path.expanduser("~"), "Documents","ForagingSettings")
        self.SettingFile=os.path.join(self.SettingFolder,'ForagingSettings.json')
        self.SettingsBoxFile=os.path.join(self.SettingFolder,'Settings_box'+str(self.box_number)+'.csv')
        self._GetSettings()
        self._LoadSchedule()

        # Load Settings that are specific to this box 
        self.LaserCalibrationFiles=os.path.join(self.SettingFolder,'LaserCalibration_{}.json'.format(box_number))
        self.WaterCalibrationFiles=os.path.join(self.SettingFolder,'WaterCalibration_{}.json'.format(box_number))
        self.WaterCalibrationParFiles=os.path.join(self.SettingFolder,'WaterCalibrationPar_{}.json'.format(box_number))

        # Load Laser and Water Calibration Files
        self._GetLaserCalibration()
        self._GetWaterCalibration()

        # Load Rig Json
        self._LoadRigJson()

        # Stage Widget
        self.stage_widget = None

        # Load User interface
        self._LoadUI()

        # add warning_widget to layout and set color
        self.warning_widget = WarningWidget(log_tag=self.warning_log_tag,
                                            text_color=self.default_warning_color)
        self.scrollArea_6.setWidget(self.warning_widget)

        # set window title
        self.setWindowTitle(self.rig_name)
        logging.info('Setting Window title: {}'.format(self.rig_name))

        # Set up parameters
        self.StartANewSession = 1   # to decide if should start a new session
        self.ToInitializeVisual = 1 # Should we visualize performance
        self.FigureUpdateTooSlow = 0# if the FigureUpdateTooSlow is true, using different process to update figures
        self.ANewTrial = 1          # permission to start a new trial
        self.previous_backup_completed = 1   # permission to save backup data; 0, the previous saving has not finished, and it will not trigger the next saving; 1, it is allowed to save backup data
        self.UpdateParameters = 1   # permission to update parameters
        self.logging_type = -1    # -1, logging is not started; 0, temporary logging; 1, formal logging
        self.unsaved_data = False   # Setting unsaved data to False
        self.to_check_drop_frames = 1 # 1, to check drop frames during saving data; 0, not to check drop frames
        self.session_run = False    # flag to indicate if session has been run or not

        # Connect to Bonsai
        self._InitializeBonsai()

        # connect to Slims
        self._ConnectSlims()

        # Set up threads 
        self.threadpool=QThreadPool() # get animal response
        self.threadpool2=QThreadPool() # get animal lick
        self.threadpool3=QThreadPool() # visualization
        self.threadpool4=QThreadPool() # for generating a new trial
        self.threadpool5=QThreadPool() # for starting the trial loop
        self.threadpool6=QThreadPool() # for saving data
        self.threadpool_workertimer=QThreadPool() # for timing

        # create bias indicator
        self.bias_n_size = 500
        self.bias_indicator = BiasIndicator(x_range=self.bias_n_size)  # TODO: Where to store bias_threshold parameter? self.Settings?
        self.bias_indicator.biasValue.connect(self.bias_calculated)  # update dashboard value
        self.bias_indicator.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

        # Set up more parameters
        self.FIP_started=False
        self.OpenOptogenetics=0
        self.OpenWaterCalibration=0
        self.OpenLaserCalibration=0
        self.OpenCamera=0
        self.OpenMetadata=0
        self.NewTrialRewardOrder=0
        self.LickSta=0
        self.LickSta_ToInitializeVisual=1
        self.TimeDistribution=0
        self.TimeDistribution_ToInitializeVisual=1
        self.finish_Timer=1     # for photometry baseline recordings
        self.PhotometryRun=0    # 1. Photometry has been run; 0. Photometry has not been carried out.
        self.ignore_timer=False # Used for canceling the photometry baseline timer
        self.give_left_volume_reserved=0 # the reserved volume of the left valve (usually given after go cue)
        self.give_right_volume_reserved=0 # the reserved volume of the right valve (usually given after go cue)
        self.give_left_time_reserved=0 # the reserved open time of the left valve (usually given after go cue)
        self.give_right_time_reserved=0 # the reserved open time of the right valve (usually given after go cue)
        self.load_tag=0 # 1, a session has been loaded; 0, no session has been loaded
        self.Other_manual_water_left_volume=[] # the volume of manual water given by the left valve each time
        self.Other_manual_water_left_time=[] # the valve open time of manual water given by the left valve each time
        self.Other_manual_water_right_volume=[] # the volume of manual water given by the right valve each time
        self.Other_manual_water_right_time=[] # the valve open time of manual water given by the right valve each time
        self._Optogenetics()    # open the optogenetics panel
        self._LaserCalibration()# to open the laser calibration panel
        self._WaterCalibration()# to open the water calibration panel
        self._Camera()
        self._Metadata()
        self.RewardFamilies=[[[8,1],[6, 1],[3, 1],[1, 1]],[[8, 1], [1, 1]],[[1,0],[.9,.1],[.8,.2],[.7,.3],[.6,.4],[.5,.5]],[[6, 1],[3, 1],[1, 1]]]
        self.WaterPerRewardedTrial=0.005
        self._ShowRewardPairs() # show reward pairs
        self._GetTrainingParameters() # get initial training parameters
        self.connectSignalsSlots()
        self._Task()
        self.keyPressEvent()
        self._WaterVolumnManage2()
        self._LickSta()
        self._InitializeMotorStage()
        self._load_stage()
        self._warmup()
        self.CreateNewFolder=1 # to create new folder structure (a new session)
        self.ManualWaterVolume=[0,0]
        self._StopPhotometry() # Make sure photoexcitation is stopped
        # Initialize open ephys saving dictionary
        self.open_ephys=[]

        # load the rig metadata
        self._load_rig_metadata()

        # Initializes session log handler as None
        self.session_log_handler = None

        # generate an upload manifest when a session has been produced
        self.upload_manifest_slot = self.sessionGenerated.connect(self._generate_upload_manifest)

        # show disk space
        self._show_disk_space()
        if not self.start_bonsai_ide:
            '''
                When starting bonsai without the IDE the connection is always unstable.
                Reconnecting solves the issue
            '''
            self._ReconnectBonsai()
        logging.info('Start up complete')

    def _load_rig_metadata(self):
        '''Load the latest rig metadata'''

        rig_json, rig_json_file= self._load_most_recent_rig_json()
        self.latest_rig_metadata_file = rig_json_file
        self.Metadata_dialog._SelectRigMetadata(self.latest_rig_metadata_file)

    def _show_disk_space(self):
        '''Show the disk space of the current computer'''
        total, used, free = shutil.disk_usage(self.default_saveFolder)
        self.diskspace.setText(f"Used space: {used/1024**3:.2f}GB    Free space: {free/1024**3:.2f}GB")
        self.DiskSpaceProgreeBar.setValue(int(used/total*100))
        if free/1024**3 < 100 or used/total > 0.9:
            self.DiskSpaceProgreeBar.setStyleSheet("QProgressBar::chunk {background-"+self.default_warning_color+"}")
            logging.warning(f"Low disk space  Used space: {used/1024**3:.2f}GB    Free space: {free/1024**3:.2f}GB")
        else:
            self.DiskSpaceProgreeBar.setStyleSheet("QProgressBar::chunk {background-color: green;}")

    def _load_stage(self) -> None:
        """
        Check whether newscale stage is defined in the config. If not, initialize and inject stage widget.
        """
        if self.Settings['newscale_serial_num_box{}'.format(self.box_number)] == '':
            widget_to_replace = "motor_stage_widget" if self.default_ui == "ForagingGUI_Ephys.ui" else "widget_2"
            self._insert_stage_widget(widget_to_replace)
        else:
            self._GetPositions()

    def _insert_stage_widget(self, widget_to_replace: str) -> None:
        """
        Given a widget name, replace all contents of that widget with the stage widget
        Note: The UI file must be loaded or else it can't find the widget to replace
              Also the widget to replace must contain a layout so it can hide all child widgets properly.
        """
        logging.info("Inserting Stage Widget")

        # Get QWidget object
        widget = getattr(self, widget_to_replace, None)

        if widget is not None:
            layout = widget.layout()
            # Hide all current items within widget being replaced
            for i in reversed(range(layout.count())):
                layout.itemAt(i).widget().setVisible(False)
            # Insert new stage_widget
            self.stage_widget = get_stage_widget()
            layout.addWidget(self.stage_widget)

    def _LoadUI(self):
        '''
            Determine which user interface to use
        '''
        uic.loadUi(self.default_ui, self)
        if self.default_ui=='ForagingGUI.ui':
            logging.info('Using ForagingGUI.ui interface')
            self.label_date.setText(str(date.today()))
            self.default_warning_color="purple"
            self.default_text_color="color: purple;"
            self.default_text_background_color='background-color: purple;'
        elif self.default_ui=='ForagingGUI_Ephys.ui':
            logging.info('Using ForagingGUI_Ephys.ui interface')
            self.Visualization.setTitle(str(date.today()))
            self.default_warning_color="red"
            self.default_text_color="color: red;"
            self.default_text_background_color='background-color: red;'
        else:
            logging.info('Using ForagingGUI.ui interface')
            self.default_warning_color="color: red;"
            self.default_text_color='color: red;'
            self.default_text_background_color='background-color: red;'

    def connectSignalsSlots(self):
        '''Define callbacks'''
        self.action_About.triggered.connect(self._about)
        self.action_Camera.triggered.connect(self._Camera)
        self.actionMeta_Data.triggered.connect(self._Metadata)
        self.action_Optogenetics.triggered.connect(self._Optogenetics)
        self.actionLicks_sta.triggered.connect(self._LickSta)
        self.actionTime_distribution.triggered.connect(self._TimeDistribution)
        self.action_Calibration.triggered.connect(self._WaterCalibration)
        self.actionLaser_Calibration.triggered.connect(self._LaserCalibration)
        self.action_Open.triggered.connect(self._Open)
        self.action_Save.triggered.connect(self._Save)
        self.actionForce_save.triggered.connect(self._ForceSave)
        self.SaveAs.triggered.connect(self._SaveAs)
        self.Save_continue.triggered.connect(self._Save_continue)
        self.action_Exit.triggered.connect(self._Exit)
        self.action_New.triggered.connect(self._NewSession)
        self.action_Clear.triggered.connect(self._Clear)
        self.action_Start.triggered.connect(self.Start.click)
        self.action_NewSession.triggered.connect(self.NewSession.click)
        self.actionConnectBonsai.triggered.connect(self._ConnectBonsai)
        self.actionReconnect_bonsai.triggered.connect(self._ReconnectBonsai)
        self.Load.clicked.connect(self._OpenLast)
        self.Save.setCheckable(True)
        self.Save.clicked.connect(self._Save)
        self.Clear.clicked.connect(self._Clear)
        self.Start.clicked.connect(self._Start)
        self.GiveLeft.clicked.connect(self._GiveLeft)
        self.GiveRight.clicked.connect(self._GiveRight)
        self.NewSession.clicked.connect(self._NewSession)
        self.AutoReward.clicked.connect(self._AutoReward)
        self.StartFIP.clicked.connect(self._StartFIP)
        self.StartExcitation.clicked.connect(self._StartExcitation)
        self.StartBleaching.clicked.connect(self._StartBleaching)
        self.NextBlock.clicked.connect(self._NextBlock)
        self.OptogeneticsB.activated.connect(self._OptogeneticsB) # turn on/off optogenetics
        self.OptogeneticsB.currentIndexChanged.connect(lambda: self._QComboBoxUpdate('Optogenetics',self.OptogeneticsB.currentText()))
        self.PhotometryB.currentIndexChanged.connect(lambda: self._QComboBoxUpdate('Photometry',self.PhotometryB.currentText()))
        self.FIPMode.currentIndexChanged.connect(lambda: self._QComboBoxUpdate('FIPMode', self.FIPMode.currentText()))
        self.AdvancedBlockAuto.currentIndexChanged.connect(self._keyPressEvent)
        self.AutoWaterType.currentIndexChanged.connect(self._keyPressEvent)
        self.UncoupledReward.textChanged.connect(self._ShowRewardPairs)
        self.UncoupledReward.returnPressed.connect(self._ShowRewardPairs)
        # Connect to ID change in the mainwindow
        self.ID.returnPressed.connect(
            lambda: self.AutoTrain_dialog.update_auto_train_lock(engaged=False)
        )
        self.ID.returnPressed.connect(
            lambda: self.AutoTrain_dialog.update_auto_train_fields(
                subject_id=self.ID.text(),
                auto_engage=self.auto_engage,
                )
            )
        self.AutoTrain.clicked.connect(self._auto_train_clicked)
        self.pushButton_streamlit.clicked.connect(self._open_mouse_on_streamlit)
        self.Task.currentIndexChanged.connect(self._ShowRewardPairs)
        self.Task.currentIndexChanged.connect(self._Task)
        self.AdvancedBlockAuto.currentIndexChanged.connect(self._AdvancedBlockAuto)
        self.TargetRatio.textChanged.connect(self._UpdateSuggestedWater)
        self.WeightAfter.textChanged.connect(self._PostWeightChange)
        self.BaseWeight.textChanged.connect(self._UpdateSuggestedWater)
        self.Randomness.currentIndexChanged.connect(self._Randomness)
        self.actionTemporary_Logging.triggered.connect(self._startTemporaryLogging)
        self.actionFormal_logging.triggered.connect(self._startFormalLogging)
        self.actionOpen_logging_folder.triggered.connect(self._OpenLoggingFolder)
        self.actionOpen_behavior_folder.triggered.connect(self._OpenBehaviorFolder)
        self.actionOpenSettingFolder.triggered.connect(self._OpenSettingFolder)
        self.actionOpen_rig_metadata_folder.triggered.connect(self._OpenRigMetadataFolder)
        self.actionOpen_metadata_dialog_folder.triggered.connect(self._OpenMetadataDialogFolder)
        self.actionOpen_video_folder.triggered.connect(self._OpenVideoFolder)
        self.LeftValue.textChanged.connect(self._WaterVolumnManage1)
        self.RightValue.textChanged.connect(self._WaterVolumnManage1)
        self.GiveWaterL.textChanged.connect(self._WaterVolumnManage1)
        self.GiveWaterR.textChanged.connect(self._WaterVolumnManage1)
        self.LeftValue_volume.textChanged.connect(self._WaterVolumnManage2)
        self.RightValue_volume.textChanged.connect(self._WaterVolumnManage2)
        self.GiveWaterL_volume.textChanged.connect(self._WaterVolumnManage2)
        self.GiveWaterR_volume.textChanged.connect(self._WaterVolumnManage2)
        self.MoveXP.clicked.connect(self._MoveXP)
        self.MoveYP.clicked.connect(self._MoveYP)
        self.MoveZP.clicked.connect(self._MoveZP)
        self.MoveXN.clicked.connect(self._MoveXN)
        self.MoveYN.clicked.connect(self._MoveYN)
        self.MoveZN.clicked.connect(self._MoveZN)
        self.StageStop.clicked.connect(self._StageStop)
        self.GetPositions.clicked.connect(self._GetPositions)
        self.ShowNotes.setStyleSheet("background-color: #F0F0F0;")
        self.warmup.currentIndexChanged.connect(self._warmup)
        self.Sessionlist.currentIndexChanged.connect(self._session_list)
        self.SessionlistSpin.textChanged.connect(self._session_list_spin)
        self.StartEphysRecording.clicked.connect(self._StartEphysRecording)
        self.SetReference.clicked.connect(self._set_reference)
        self.Opto_dialog.laser_1_calibration_voltage.textChanged.connect(self._toggle_save_color)
        self.Opto_dialog.laser_2_calibration_voltage.textChanged.connect(self._toggle_save_color)
        self.Opto_dialog.laser_1_calibration_power.textChanged.connect(self._toggle_save_color)
        self.Opto_dialog.laser_2_calibration_power.textChanged.connect(self._toggle_save_color)

        # check the change of all of the QLineEdit, QDoubleSpinBox and QSpinBox
        for container in [self.TrainingParameters, self.centralwidget, self.Opto_dialog,self.Metadata_dialog]:
            # Iterate over each child of the container that is a QLineEdit or QDoubleSpinBox
            for child in container.findChildren((QtWidgets.QLineEdit,QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox)):
                child.textChanged.connect(self._CheckTextChange)
            for child in container.findChildren((QtWidgets.QComboBox)):
                child.currentIndexChanged.connect(self.keyPressEvent)
        # Opto_dialog can not detect natural enter press, so returnPressed is used here. 
        for container in [self.Opto_dialog,self.Metadata_dialog]:
            # Iterate over each child of the container that is a QLineEdit or QDoubleSpinBox
            for child in container.findChildren((QtWidgets.QLineEdit)):
                child.returnPressed.connect(self.keyPressEvent)

    def _set_reference(self):
        '''
        set the reference point for lick spout position in the metadata dialog
        '''
        # get the current position of the stage
        current_positions=self._GetPositions()
        # set the reference point for lick spout position in the metadata dialog
        if current_positions is not None:
            self.Metadata_dialog._set_reference(current_positions)

    def _StartEphysRecording(self):
        '''
            Start/stop ephys recording

        '''
        if self.open_ephys_machine_ip_address=='':
            QMessageBox.warning(self, 'Connection Error', 'Empty ip address for Open Ephys Computer. Please check the settings file.')
            self.StartEphysRecording.setChecked(False)
            self._toggle_color(self.StartEphysRecording)
            return

        if  (self.Start.isChecked() or self.ANewTrial==0) and self.StartEphysRecording.isChecked():
            reply = QMessageBox.question(self, '', 'Behavior has started! Do you want to start ephys recording?', QMessageBox.No | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                pass
            elif reply == QMessageBox.No:
                self.StartEphysRecording.setChecked(False)
                self._toggle_color(self.StartEphysRecording)
                return

        EphysControl=EphysRecording(open_ephys_machine_ip_address=self.open_ephys_machine_ip_address,mouse_id=self.ID.text())
        if self.StartEphysRecording.isChecked():
            try:
                if EphysControl.get_status()['mode']=='RECORD':
                    QMessageBox.warning(self, '', 'Open Ephys is already recording! Please stop the recording first.')
                    self.StartEphysRecording.setChecked(False)
                    self._toggle_color(self.StartEphysRecording)
                    return
                EphysControl.start_open_ephys_recording()
                self.openephys_start_recording_time = str(datetime.now())
                QMessageBox.warning(self, '', f'Open Ephys has started recording!\n Recording type: {self.OpenEphysRecordingType.currentText()}')
            except Exception as e:
                logging.error(traceback.format_exc())
                self.StartEphysRecording.setChecked(False)
                QMessageBox.warning(self, 'Connection Error', 'Failed to connect to Open Ephys. Please check: \n1) the correct ip address is included in the settings json file. \n2) the Open Ephys software is open.')
        else:
            try:
                if EphysControl.get_status()['mode']!='RECORD':
                    QMessageBox.warning(self, '', 'Open Ephys is not recording! Please start the recording first.')
                    self.StartEphysRecording.setChecked(False)
                    self._toggle_color(self.StartEphysRecording)
                    return

                if  self.Start.isChecked() or self.ANewTrial==0:
                    reply = QMessageBox.question(self,  '','The behavior hasn’t stopped yet! Do you want to stop ephys recording?', QMessageBox.No | QMessageBox.No, QMessageBox.Yes)
                    if reply == QMessageBox.Yes:
                        pass
                    elif reply == QMessageBox.No:
                        self.StartEphysRecording.setChecked(True)
                        self._toggle_color(self.StartEphysRecording)
                        return

                self.openephys_stop_recording_time = str(datetime.now())
                response=EphysControl.get_open_ephys_recording_configuration()
                response['openephys_start_recording_time']=self.openephys_start_recording_time
                response['openephys_stop_recording_time']=self.openephys_stop_recording_time
                response['recording_type']=self.OpenEphysRecordingType.currentText()
                self.open_ephys.append(response)
                self.unsaved_data=True
                self.Save.setStyleSheet("color: white;background-color : mediumorchid;")
                EphysControl.stop_open_ephys_recording()
                QMessageBox.warning(self, '', 'Open Ephys has stopped recording! Please save the data again!')
            except Exception as e:
                logging.error(traceback.format_exc())
                QMessageBox.warning(self, 'Connection Error', 'Failed to stop Open Ephys recording. Please check: \n1) the open ephys software is still running')
        self._toggle_color(self.StartEphysRecording)

    def _toggle_color(self,widget,check_color="background-color : green;",unchecked_color="background-color : none"):
        '''
        Toggle the color of the widget.

        Parameters
        ----------
        widget : QtWidgets.QWidget

            If Checked, sets the color to green. If unchecked, sets the color to None.

        Returns
        -------
        None
        '''


        if widget.isChecked():
            widget.setStyleSheet(check_color)
        else:
            widget.setStyleSheet(unchecked_color)

    def _manage_warning_labels(self,warning_labels,warning_text=''):
        '''
            Manage the warning labels. 

            If there is a warning, set the color to self.default_warning_color. If there is no warning, set the text to ''. 
        Parameters
        ----------
        warning_label : single QtWidgets.QLabel or list of QtWidgets.QLabel
            The warning label to manage
        warning_text : str
            The warning text to display
        Returns
        -------
        None
        '''
        if not isinstance(warning_labels,list):
            warning_labels = [warning_labels]
        for warning_label in warning_labels:
            warning_label.setText(warning_text)
            warning_label.setStyleSheet(self.default_warning_color)

    def _session_list(self):
        '''show all sessions of the current animal and load the selected session by drop down list'''
        if not hasattr(self,'fname'):
            return 0
        # open the selected session
        if self.Sessionlist.currentText()!='':
            selected_index=self.Sessionlist.currentIndex()
            fname=self.session_full_path_list[self.Sessionlist.currentIndex()]
            self._Open(input_file=fname)
            # set the selected index back to the current session
            self._connect_Sessionlist(connect=False)
            self.Sessionlist.setCurrentIndex(selected_index)
            self.SessionlistSpin.setValue(int(selected_index+1))
            self._connect_Sessionlist(connect=True)

    def _session_list_spin(self):
        '''show all sessions of the current animal and load the selected session by spin box'''
        if not hasattr(self,'fname'):
            return 0
        if self.SessionlistSpin.text()!='':
            self._connect_Sessionlist(connect=False)
            if int(self.SessionlistSpin.text())>self.Sessionlist.count():
                self.SessionlistSpin.setValue(int(self.Sessionlist.count()))
            if int(self.SessionlistSpin.text())<1:
                self.SessionlistSpin.setValue(1)
            fname=self.session_full_path_list[int(self.SessionlistSpin.text())-1]
            self.Sessionlist.setCurrentIndex(int(self.SessionlistSpin.text())-1)
            self._connect_Sessionlist(connect=True)
            self._Open(input_file=fname)

    def _connect_Sessionlist(self,connect=True):
        '''connect or disconnect the Sessionlist and SessionlistSpin'''
        if connect:
            self.Sessionlist.currentIndexChanged.connect(self._session_list)
            self.SessionlistSpin.textChanged.connect(self._session_list_spin)
        else:
            self.Sessionlist.disconnect()
            self.SessionlistSpin.disconnect()

    def _show_sessions(self):
        '''list all sessions of the current animal'''
        if not hasattr(self,'fname'):
            return 0
        animal_folder=os.path.dirname(os.path.dirname(os.path.dirname(self.fname)))
        session_full_path_list=[]
        session_path_list=[]
        for session_folder in os.listdir(animal_folder):
            training_folder_old = os.path.join(animal_folder,session_folder, 'TrainingFolder')
            training_folder_new = os.path.join(animal_folder,session_folder, 'behavior')
            if os.path.exists(training_folder_old):
                for file_name in os.listdir(training_folder_old):
                    if file_name.endswith('.json'):
                        session_full_path_list.append(os.path.join(training_folder_old, file_name))
                        session_path_list.append(session_folder)
            elif os.path.exists(training_folder_new):
                for file_name in os.listdir(training_folder_new):
                    if file_name.endswith('.json'):
                        session_full_path_list.append(os.path.join(training_folder_new, file_name))
                        session_path_list.append(session_folder)

        sorted_indices = sorted(enumerate(session_path_list), key=lambda x: x[1], reverse=True)
        sorted_dates = [date for index, date in sorted_indices]
        # Extract just the indices
        indices = [index for index, date in sorted_indices]
        # Apply sorted index
        self.session_full_path_list = [session_full_path_list[index] for index in indices]
        self.session_path_list=sorted_dates

        self._connect_Sessionlist(connect=False)
        self.Sessionlist.clear()
        self.Sessionlist.addItems(sorted_dates)
        self._connect_Sessionlist(connect=True)

    def _check_drop_frames(self,save_tag=1):
        '''check if there are any drop frames in the video'''
        if self.to_check_drop_frames==1:
            return_tag=0
            if save_tag==0:
                if "drop_frames_warning_text" in self.Obj:
                    self.drop_frames_warning_text=self.Obj['drop_frames_warning_text']
                    self.drop_frames_tag=self.Obj['drop_frames_tag']
                    self.trigger_length=self.Obj['trigger_length']
                    self.frame_num=self.Obj['frame_num']
                    return_tag=1
            if return_tag==0:
                self.drop_frames_tag=0
                self.trigger_length=0
                self.drop_frames_warning_text = ''
                self.frame_num={}
                use_default_folder_structure=0
                if save_tag==1:
                    # check the drop frames of the current session
                    if hasattr(self,'HarpFolder'):
                        HarpFolder=self.HarpFolder
                        video_folder=self.VideoFolder
                    else:
                        use_default_folder_structure=1
                elif save_tag==0:
                    if 'HarpFolder' in self.Obj:
                        # check the drop frames of the loaded session
                        HarpFolder=self.Obj['HarpFolder']
                        video_folder=self.Obj['VideoFolder']
                    else:
                        use_default_folder_structure=1
                if use_default_folder_structure:
                    # use the default folder structure
                    HarpFolder=os.path.join(os.path.dirname(os.path.dirname(self.fname)),'HarpFolder')# old folder structure
                    video_folder=os.path.join(os.path.dirname(os.path.dirname(self.fname)),'VideoFolder') # old folder structure
                    if not os.path.exists(HarpFolder):
                        HarpFolder=os.path.join(os.path.dirname(self.fname),'raw.harp')# new folder structure
                        video_folder=os.path.join(os.path.dirname(os.path.dirname(self.fname)),'behavior-videos') # new folder structure

                camera_trigger_file=os.path.join(HarpFolder,'BehaviorEvents','Event_94.bin')
                if os.path.exists(camera_trigger_file):
                    # sleep some time to wait for the finish of saving video
                    time.sleep(5)
                    triggers = harp.read(camera_trigger_file)
                    self.trigger_length = len(triggers)
                elif len(os.listdir(video_folder)) == 0:
                    # no video data saved.
                    self.trigger_length=0
                    self.to_check_drop_frames=0
                    return
                elif ('HighSpeedCamera' in self.SettingsBox) and (self.SettingsBox['HighSpeedCamera'] ==1):
                    self.trigger_length=0
                    logging.error('Saved video data, but no camera trigger file found')
                    logging.info('No camera trigger file found!', extra={'tags': [self.warning_log_tag]})
                    return
                else:
                    logging.info('Saved video data, but not using high speed camera - skipping drop frame check')
                    self.trigger_length=0
                    self.to_check_drop_frames=0
                    return
                csv_files = [file for file in os.listdir(video_folder) if file.endswith(".csv")]
                avi_files = [file for file in os.listdir(video_folder) if file.endswith(".avi")]

                for avi_file in avi_files:
                    csv_file = avi_file.replace('.avi', '.csv')
                    camera_name = avi_file.replace('.avi','')
                    if csv_file not in csv_files:
                        self.drop_frames_warning_text+=f'No csv file found for {avi_file}\n'
                    else:
                        current_frames = pd.read_csv(os.path.join(video_folder, csv_file), header=None)
                        num_frames = len(current_frames)
                        if num_frames != self.trigger_length:
                            self.drop_frames_warning_text+=f"Error: {avi_file} has {num_frames} frames, but {self.trigger_length} triggers\n"
                            self.drop_frames_tag=1
                        else:
                            self.drop_frames_warning_text+=f"Correct: {avi_file} has {num_frames} frames and {self.trigger_length} triggers\n"
                        self.frame_num[camera_name] = num_frames
            logging.warning(self.drop_frames_warning_text, extra={'tags': [self.warning_log_tag]})
            # only check drop frames once each session
            self.to_check_drop_frames=0

    def _warmup(self):
        '''warm up the session before starting.
            Use warm up with caution. Usually, it is only used for the first time training. 
            Turn on the warm up only when all parameters are set correctly, otherwise it would revert 
            to some incorrect parameters when it was turned off.
        '''
        # set warm up parameters
        if self.warmup.currentText()=='on':
            # get parameters before the warm up is on;WarmupBackup_ stands for Warmup backup, which are parameters before warm-up.
            self._GetTrainingParameters(prefix='WarmupBackup_')
            self.warm_min_trial.setEnabled(True)
            self.warm_min_finish_ratio.setEnabled(True)
            self.warm_max_choice_ratio_bias.setEnabled(True)
            self.warm_windowsize.setEnabled(True)
            self.label_64.setEnabled(True)
            self.label_116.setEnabled(True)
            self.label_117.setEnabled(True)
            self.label_118.setEnabled(True)

            # set warm up default parameters
            self.Task.setCurrentIndex(self.Task.findText('Coupled Baiting'))
            self.BaseRewardSum.setText('1')
            self.RewardFamily.setText('3')
            self.RewardPairsN.setText('1')

            self.BlockBeta.setText('1')
            self.BlockMin.setText('1')
            self.BlockMax.setText('1')
            self.BlockMinReward.setText('1')

            self.AutoReward.setChecked(True)
            self._AutoReward()
            self.AutoWaterType.setCurrentIndex(self.AutoWaterType.findText('Natural'))
            self.Multiplier.setText('0.8')
            self.Unrewarded.setText('0')
            self.Ignored.setText('0')
            # turn advanced block auto off
            self.AdvancedBlockAuto.setCurrentIndex(self.AdvancedBlockAuto.findText('off'))
            self._ShowRewardPairs()
        elif self.warmup.currentText()=='off':
            # set parameters back to the previous parameters before warm up
            self._revert_to_previous_parameters()
            self.warm_min_trial.setEnabled(False)
            self.warm_min_finish_ratio.setEnabled(False)
            self.warm_max_choice_ratio_bias.setEnabled(False)
            self.warm_windowsize.setEnabled(False)
            self.label_64.setEnabled(False)
            self.label_116.setEnabled(False)
            self.label_117.setEnabled(False)
            self.label_118.setEnabled(False)
            self._ShowRewardPairs()

    def _revert_to_previous_parameters(self):
        '''reverse to previous parameters before warm up'''
        # get parameters before the warm up is on
        parameters={}
        for attr_name in dir(self):
            if attr_name.startswith('WarmupBackup_') and attr_name!='WarmupBackup_' and attr_name!='WarmupBackup_warmup':
                parameters[attr_name.replace('WarmupBackup_','')]=getattr(self,attr_name)
        widget_dict = {w.objectName(): w for w in self.TrainingParameters.findChildren((QtWidgets.QPushButton,QtWidgets.QLineEdit,QtWidgets.QTextEdit, QtWidgets.QComboBox,QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox))}
        widget_dict['Task']=self.Task
        try:
            for key in widget_dict.keys():
                self._set_parameters(key,widget_dict,parameters)
        except Exception as e:
            # Catch the exception and log error information
            logging.error(traceback.format_exc())

    def _keyPressEvent(self):
        # press enter to confirm parameters change
        self.keyPressEvent()

    def _CheckStageConnection(self):
        '''get the current position of the stage'''
        if hasattr(self, 'current_stage') and self.current_stage.connected:
            logging.info('Checking stage connection')
            current_stage=self.current_stage
            current_position=current_stage.get_position()
            if not current_stage.connected:
                logging.error('lost stage connection')
                self._no_stage()

    def _GetPositions(self):
        '''get the current position of the stage'''
        self._CheckStageConnection()

        if hasattr(self, 'current_stage') and self.current_stage.connected:
            logging.info('Grabbing current stage position')
            current_stage=self.current_stage
            current_position=current_stage.get_position()
            self._UpdatePosition(current_position,(0,0,0))
            return current_position
        else:
            return None
            logging.info('GetPositions pressed, but no current stage')

    def _StageStop(self):
        '''Halt the stage'''
        self._CheckStageConnection()
        if hasattr(self, 'current_stage') and self.current_stage.connected:
            logging.info('Stopping stage movement')
            current_stage=self.current_stage
            current_stage.halt()
        else:
            logging.info('StageStop pressed, but no current stage')

    def _Move(self,axis,step):
        '''Move stage'''
        self._CheckStageConnection()
        try:
            if (not hasattr(self, 'current_stage')) or (not self.current_stage.connected):
                logging.info('Move Stage pressed, but no current stage')
                return
            logging.info('Moving stage')
            self.StageStop.click
            current_stage=self.current_stage
            current_position=current_stage.get_position()
            current_stage.set_speed(3000)
            current_stage.move_relative_1d(axis,step)
            if axis=='x':
                relative_postition=(step,0,0)
            elif axis=='y':
                relative_postition=(0,step,0)
            elif axis=='z':
                relative_postition=(0,0,step)
            self._UpdatePosition(current_position,relative_postition)
        except Exception as e:
            logging.error(traceback.format_exc())

    def _MoveXP(self):
        '''Move X positively'''
        axis='x'
        step=float(self.Step.text())
        self._Move(axis,step)

    def _MoveXN(self):
        '''Move X negatively'''
        axis='x'
        step=float(self.Step.text())
        self._Move(axis,-step)

    def _MoveYP(self):
        '''Move Y positively'''
        axis='y'
        step=float(self.Step.text())
        self._Move(axis,step)

    def _MoveYN(self):
        '''Move Y negatively'''
        axis='y'
        step=float(self.Step.text())
        self._Move(axis,-step)

    def _MoveZP(self):
        '''Move Z positively'''
        axis='z'
        step=float(self.Step.text())
        self._Move(axis,step)

    def _MoveZN(self):
        '''Move Z negatively'''
        axis='z'
        step=float(self.Step.text())
        self._Move(axis,-step)

    def _UpdatePosition(self,current_position,relative_postition):
        '''Update the NewScale position'''
        NewPositions=[0,0,0]
        for i in range(len(current_position)):
            NewPositions[i]= current_position[i]+relative_postition[i]
            if NewPositions[i]<0:
                NewPositions[i]=0
            elif NewPositions[i]>15000:
                NewPositions[i]=15000
        self.PositionX.setText(str(NewPositions[0]))
        self.PositionY.setText(str(NewPositions[1]))
        self.PositionZ.setText(str(NewPositions[2]))

    def _InitializeMotorStage(self):
        '''
            Scans for available newscale stages. Attempts to connect to the newscale stage
            defined by the serial number in the settings file. If it cannot connect for any reason
            it displays a warning in the motor stage box, and returns. 
            
            Failure modes include: an error in scanning for stages, no stages found, no stage defined
            in the settings file, the defined stage not found, an error in connecting to the stage 
        '''

        # find available newscale stages
        logging.info('Scanning for newscale stages')
        try:
            self.instances = NewScaleSerialY.get_instances()
        except Exception as e:
            logging.error('Could not find instances of NewScale Stage: {}'.format(str(e)))
            self._no_stage()
            return

        # If we can't find any stages, return 
        if len(self.instances) == 0:
            logging.info('Could not find any instances of NewScale Stage',
                         extra={'tags': [self.warning_log_tag]})
            self._no_stage()
            return

        logging.info('found {} newscale stages'.format(len(self.instances)))

        # Get the serial num from settings
        if not hasattr(self, 'newscale_serial_num_box{}'.format(self.box_number)):
            logging.error('Cannot determine newscale serial num')
            self._no_stage()
            return
        self.newscale_serial_num=eval('self.newscale_serial_num_box'+str(self.box_number))
        if self.newscale_serial_num == '':
            logging.warning('No newscale serial number in settings file')
            self._no_stage()
            return

        # See if the serial num from settings is in the instances we found
        stage_index = 0
        stage_names = np.array([str(instance.sn) for instance in self.instances])
        index = np.where(stage_names == str(self.newscale_serial_num))[0]
        if len(index) == 0:
            self._no_stage()
            msg = 'Could not find newscale with serial number: {}'
            logging.error(msg.format(self.newscale_serial_num))
            return
        else:
            stage_index = index[0]
            logging.info('Found the newscale stage from the settings file')

        # Setup connection
        newscale_stage_instance = self.instances[stage_index]
        self._connect_stage(newscale_stage_instance)

    def _no_stage(self):
        '''
            Display a warrning message that the newscale stage is not connected
        '''
        if hasattr(self, 'current_stage'):
            self.Warning_Newscale.setText('Lost newscale stage connection')
        else:
            self.Warning_Newscale.setText('Newscale stage not connected')
        self.Warning_Newscale.setStyleSheet(self.default_warning_color)

    def _connect_stage(self,instance):
        '''connect to a stage'''
        try:
            instance.io.open()
            instance.set_timeout(1)
            instance.set_baudrate(250000)
            self.current_stage=Stage(serial=instance)
        except Exception as e:
            logging.error(traceback.format_exc())
            self._no_stage()
        else:
            logging.info('Successfully connected to newscale stage: {}'.format(instance.sn))

    def _ConnectBonsai(self):
        '''
            Connect to already running bonsai instance
            
            Will only attempt to connect if InitializeBonsaiSuccessfully=0
            
            If successfully connects, sets InitializeBonsaiSuccessfully=1
        '''
        if self.InitializeBonsaiSuccessfully==0:
            try:
                self._ConnectOSC()
                self.InitializeBonsaiSuccessfully=1
                logging.info('Connected to Bonsai')
                subprocess.Popen('title Box{}'.format(self.box_letter),shell=True)
            except Exception as e:
                logging.error(traceback.format_exc())
                logging.warning('Please open bonsai!', extra={'tags': [self.warning_log_tag]})
                self.InitializeBonsaiSuccessfully=0

    def _ReconnectBonsai(self):
        '''
            Reconnect bonsai
            
            First, it closes the connections with the clients. 
            Then, it restarts the Bonsai workflow. If a bonsai instance is already running, 
            then it will connect. Otherwise it will start a new bonsai instance
        '''
        try:
            logging.info('attempting to close bonsai connection')
            self.client.close()
            self.client2.close()
            self.client3.close()
            self.client4.close()
        except Exception as e:
            logging.info('could not close bonsai connection: {}'.format(str(e)))
        else:
            logging.info('bonsai connection closed')

        logging.info('attempting to restart bonsai')
        self.InitializeBonsaiSuccessfully=0
        self._InitializeBonsai()

        '''
            If trials have already been generated, then after reconnection to bonsai
            trial generation loops indefinitiely. See issue #166. I cannot understand
            the root cause, so I am warning users to start a new session. 
        '''
        if self.InitializeBonsaiSuccessfully ==1 and hasattr(self, 'GeneratedTrials'):
            msg = 'Reconnected to Bonsai. Start a new session before running more trials'
            reply = QMessageBox.information(self,
                'Box {}, Reconnect Bonsai'.format(self.box_letter), msg, QMessageBox.Ok )

    def _restartlogging(self,log_folder=None):
        '''Restarting logging'''
        logging.info('Restarting logging')
        # stop the current session except it is a new session
        if self.StartANewSession==1 and self.ANewTrial==1:
            pass
        else:
            self._StopCurrentSession()
        if log_folder is None:
            # formal logging
            loggingtype=0
            self.load_tag=0
            self._GetSaveFolder()
            self.CreateNewFolder=0
            log_folder=self.HarpFolder
            self.unsaved_data=True
            self.Save.setStyleSheet("color: white;background-color : mediumorchid")
        else:
            # temporary logging
            loggingtype=1
            current_time = datetime.now()
            formatted_datetime = current_time.strftime("%Y-%m-%d_%H-%M-%S")
            log_folder=os.path.join(log_folder,formatted_datetime,'behavior','raw.harp')
            # create video folder
            video_folder=os.path.join(log_folder,'..','..','behavior-videos')
            if not os.path.exists(video_folder):
                os.makedirs(video_folder)
        # stop the logging first
        self._stop_logging()
        self.Channel.StartLogging(log_folder)
        Rec=self.Channel.receive()
        if Rec[0].address=='/loggerstarted':
            pass

        self.logging_type=loggingtype # 0 for formal logging, 1 for temporary logging
        return log_folder

    def _GetLaserCalibration(self):
        '''
            Load the laser calibration file. 

            If it exists, populate:
                self.LaserCalibrationResults with the calibration json

        '''
        if os.path.exists(self.LaserCalibrationFiles):
            with open(self.LaserCalibrationFiles, 'r') as f:
                self.LaserCalibrationResults = json.load(f)

    def _GetWaterCalibration(self):
        '''
            Load the water calibration file.
        
            If it exists, populate:
                self.WaterCalibrationResults with the calibration json
                self.RecentWaterCalibration with the last calibration
                self.RecentCalibrationDate with the date of the last calibration
    
            If it does not exist, populate
                self.WaterCalibrationResults with an empty dictionary
                self.RecentCalibrationDate with 'None'
        '''

        if os.path.exists(self.WaterCalibrationFiles):
            with open(self.WaterCalibrationFiles, 'r') as f:
                self.WaterCalibrationResults = json.load(f)
                sorted_dates = sorted(self.WaterCalibrationResults.keys(), key=self._custom_sort_key)
                self.RecentWaterCalibration=self.WaterCalibrationResults[sorted_dates[-1]]
                self.RecentWaterCalibrationDate=sorted_dates[-1]
            logging.info('Loaded Water Calibration')
        else:
            self.WaterCalibrationResults = {}
            self.RecentWaterCalibrationDate='None'
            logging.warning('Did not find a recent water calibration file')

    def _custom_sort_key(self,key):
        if '_' in key:
            date_part, number_part = key.rsplit('_', 1)
            return (date_part, int(number_part))
        else:
            return (key, 0)

    def _check_line_terminator(self, file_path):
        # Open the file in binary mode to read raw bytes. Check that last line has a \n terminator. 
        with open(file_path, 'rb') as file:
            # Move the cursor to the end of the file
            file.seek(0, 2)
            # Start from the end and move backwards to find the start of the last line
            file.seek(file.tell() - 1, 0)
            # Read the last line
            last_line = file.readline()
            # Detect line terminator
            if b'\r\n' in last_line: # Windows
                return True
            elif b'\n' in last_line: # Unix
                return True
            elif b'\r' in last_line: # Old Mac
                return True
            else:
                return False

    def _LoadSchedule(self):
        if os.path.exists(self.Settings['schedule_path']):
            schedule = pd.read_csv(self.Settings['schedule_path'])
            self.schedule = schedule.dropna(subset=['Mouse ID','Box']).copy()
            logging.info('Loaded behavior schedule')
        else:
            logging.error('Could not find schedule at {}'.format(self.Settings['schedule_path']))
            return

    def _GetInfoFromSchedule(self, mouse_id, column):
        mouse_id = str(mouse_id)
        if not hasattr(self, 'schedule'):
            return None
        if mouse_id not in self.schedule['Mouse ID'].values:
            return None
        return self.schedule.query('`Mouse ID` == @mouse_id').iloc[0][column]

    def _GetSettings(self):
        '''
            Load the settings that are specific to this computer
        '''

        # Get default settings
        defaults = {
            'default_saveFolder':os.path.join(os.path.expanduser("~"), "Documents")+'\\',
            'current_box':'',
            'temporary_video_folder':os.path.join(os.path.expanduser("~"), "Documents",'temporaryvideo'),
            'Teensy_COM_box1':'',
            'Teensy_COM_box2':'',
            'Teensy_COM_box3':'',
            'Teensy_COM_box4':'',
            'FIP_workflow_path':'',
            'FIP_settings':os.path.join(os.path.expanduser("~"),"Documents","FIPSettings"),
            'bonsai_path':os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'bonsai','Bonsai.exe'),
            'bonsai_config_path':os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'bonsai','Bonsai.config'),
            'bonsaiworkflow_path':os.path.join(os.path.dirname(os.getcwd()),'workflows','foraging.bonsai'),
            'newscale_serial_num_box1':'',
            'newscale_serial_num_box2':'',
            'newscale_serial_num_box3':'',
            'newscale_serial_num_box4':'',
            'show_log_info_in_console':False,
            'default_ui':'ForagingGUI.ui',
            'open_ephys_machine_ip_address':'',
            'metadata_dialog_folder':os.path.join(self.SettingFolder,"metadata_dialog")+'\\',
            'rig_metadata_folder':os.path.join(self.SettingFolder,"rig_metadata")+'\\',
            'project_info_file':os.path.join(self.SettingFolder,"Project Name and Funding Source v2.csv"),
            'schedule_path': os.path.join('Z:\\','dynamic_foraging','DynamicForagingSchedule.csv'),
            'go_cue_decibel_box1':60,
            'go_cue_decibel_box2':60,
            'go_cue_decibel_box3':60,
            'go_cue_decibel_box4':60,
            'lick_spout_distance_box1':5000,
            'lick_spout_distance_box2':5000,
            'lick_spout_distance_box3':5000,
            'lick_spout_distance_box4':5000,
            'name_mapper_file':os.path.join(self.SettingFolder,"name_mapper.json"),
            'create_rig_metadata':True,
            'save_each_trial':True,
            'AutomaticUpload':True,
            'manifest_flag_dir':os.path.join(
                os.path.expanduser("~"),
                "Documents",
                'aind_watchdog_service',
                'manifest'),
            'auto_engage':True,
            'clear_figure_after_save':True,
            'add_default_project_name':True
        }

        # Try to load Settings_box#.csv
        self.SettingsBox={}
        if not os.path.exists(self.SettingsBoxFile):
            logging.error('Could not find settings_box file at: {}'.format(self.SettingsBoxFile))
            raise Exception('Could not find settings_box file at: {}'.format(self.SettingsBoxFile))
        try:
            # Open the csv settings file
            df = pd.read_csv(self.SettingsBoxFile,index_col=None, header=None)
            self.SettingsBox = {row[0]: row[1] for _, row in df.iterrows()}
            logging.info('Loaded settings_box file')
        except Exception as e:
            logging.error('Could not load settings_box file at: {}, {}'.format(self.SettingsBoxFile,str(e)))
            e.args = ('Could not load settings box file at: {}'.format(self.SettingsBoxFile), *e.args)
            raise e

        # check that there is a newline for final entry of csv files
        if not self._check_line_terminator(self.SettingsBoxFile):
            logging.error('Settings box file does not have a newline at the end')
            raise Exception('Settings box file does not have a newline at the end')

        # check that the SettingsBox has each of the values in mandatory_fields as a key, if not log an error for the missing key

        csv_mandatory_fields = ['Behavior', 'Soundcard', 'BonsaiOsc1', 'BonsaiOsc2', 'BonsaiOsc3', 'BonsaiOsc4','AttenuationLeft','AttenuationRight','current_box']
        for field in csv_mandatory_fields:
            if field not in self.SettingsBox.keys():
                logging.error('Missing key ({}) in settings_box file'.format(field))
                raise Exception('Missing key ({}) in settings_box file'.format(field))

        # Try to load the settings file        
        self.Settings = {}
        if not os.path.exists(self.SettingFile):
            logging.error('Could not find settings file at: {}'.format(self.SettingFile))
            raise Exception('Could not find settings file at: {}'.format(self.SettingFile))
        try:
            # Open the JSON settings file
            with open(self.SettingFile, 'r') as f:
                self.Settings = json.load(f)
            logging.info('Loaded settings file')
        except Exception as e:
            logging.error('Could not load settings file at: {}, {}'.format(self.SettingFile,str(e)))
            e.args = ('Could not load settings file at: {}'.format(self.SettingFile), *e.args)
            raise e

        # If any settings are missing, use the default values
        for key in defaults:
            if key not in self.Settings:
                self.Settings[key] = defaults[key]
                logging.warning('Missing setting ({}), using default: {}'.format(key,self.Settings[key]))
                if key in ['default_saveFolder','current_box']:
                    logging.error('Missing setting ({}), is required'.format(key))
                    raise Exception('Missing setting ({}), is required'.format(key))

        if 'default_openFolder' not in self.Settings:
            self.Settings['default_openFolder'] = self.Settings['default_saveFolder']

        # Save all settings
        self.default_saveFolder=self.Settings['default_saveFolder']
        self.default_openFolder=self.Settings['default_openFolder']
        self.current_box=self.Settings['current_box']
        self.temporary_video_folder=self.Settings['temporary_video_folder']
        self.Teensy_COM = self.Settings['Teensy_COM_box'+str(self.box_number)]
        self.FIP_workflow_path = self.Settings['FIP_workflow_path']
        self.bonsai_path=self.Settings['bonsai_path']
        self.bonsaiworkflow_path=self.Settings['bonsaiworkflow_path']
        self.newscale_serial_num_box1=self.Settings['newscale_serial_num_box1']
        self.newscale_serial_num_box2=self.Settings['newscale_serial_num_box2']
        self.newscale_serial_num_box3=self.Settings['newscale_serial_num_box3']
        self.newscale_serial_num_box4=self.Settings['newscale_serial_num_box4']
        self.default_ui=self.Settings['default_ui']
        self.open_ephys_machine_ip_address=self.Settings['open_ephys_machine_ip_address']
        self.metadata_dialog_folder = self.Settings['metadata_dialog_folder']
        self.rig_metadata_folder = self.Settings['rig_metadata_folder']
        self.project_info_file = self.Settings['project_info_file']
        self.go_cue_decibel_box1 = self.Settings['go_cue_decibel_box1']
        self.go_cue_decibel_box2 = self.Settings['go_cue_decibel_box2']
        self.go_cue_decibel_box3 = self.Settings['go_cue_decibel_box3']
        self.go_cue_decibel_box4 = self.Settings['go_cue_decibel_box4']
        self.lick_spout_distance_box1 = self.Settings['lick_spout_distance_box1']
        self.lick_spout_distance_box2 = self.Settings['lick_spout_distance_box2']
        self.lick_spout_distance_box3 = self.Settings['lick_spout_distance_box3']
        self.lick_spout_distance_box4 = self.Settings['lick_spout_distance_box4']
        self.name_mapper_file = self.Settings['name_mapper_file']
        self.save_each_trial = self.Settings['save_each_trial']
        self.auto_engage = self.Settings['auto_engage']
        self.clear_figure_after_save = self.Settings['clear_figure_after_save']
        self.add_default_project_name = self.Settings['add_default_project_name']
        if not is_absolute_path(self.project_info_file):
            self.project_info_file = os.path.join(self.SettingFolder,self.project_info_file)
        # Also stream log info to the console if enabled
        if self.Settings['show_log_info_in_console']:

            handler = logging.StreamHandler()
            # Using the same format and level as the root logger
            handler.setFormatter(logger.root.handlers[0].formatter)
            handler.setLevel(logger.root.level)
            logger.root.addHandler(handler)

        # Determine box
        if self.current_box in ['447-1','447-2','447-3']:
            mapper={
                1:'A',
                2:'B',
                3:'C',
                4:'D'
            }
            self.current_box='{}-{}'.format(self.current_box,mapper[self.box_number])
        self.Other_current_box=self.current_box
        self.Other_go_cue_decibel=self.Settings['go_cue_decibel_box'+str(self.box_number)]
        self.Other_lick_spout_distance=self.Settings['lick_spout_distance_box'+str(self.box_number)]
        self.rig_name = '{}'.format(self.current_box)

    def _ConnectSlims(self):
        '''
            Connect to Slims
        '''
        try:
            logging.info('Attempting to connect to Slims')
            self.slims_client = SlimsClient(username=os.environ['SLIMS_USERNAME'],
                                            password=os.environ['SLIMS_PASSWORD'])
        except KeyError as e:
            raise KeyError('SLIMS_USERNAME and SLIMS_PASSWORD do not exist as '
                           f'environment variables on machine. Please add. {e}')

        try:
            self.slims_client.fetch_model(models.SlimsMouseContent, barcode='00000000')
        except Exception as e:
            if 'Status 401 – Unauthorized' in str(e):    # catch error if username and password are incorrect
                raise Exception(f'Exception trying to read from Slims: {e}.\n'
                                f' Please check credentials:\n'
                                f'Username: {os.environ["SLIMS_USERNAME"]}\n'
                                f'Password: {os.environ["SLIMS_PASSWORD"]}')
            elif 'No record found' not in str(e):    # bypass if mouse doesn't exist
                raise Exception(f'Exception trying to read from Slims: {e}.\n')
        logging.info('Successfully connected to Slims')

    def _AddWaterLogResult(self, session: Session):
        '''
            Add WaterLogResult to slims based on current state of gui

            :param session: Session object to pull water information from

        '''

        try:    # try and find mouse
            logging.info(f'Attempting to fetch mouse {session.subject_id} from Slims')
            mouse = self.slims_client.fetch_model(models.SlimsMouseContent, barcode=session.subject_id)
        except Exception as e:
            if 'No record found' in str(e):    # if no mouse found or validation errors on mouse
                logging.warning(f'"No record found" error while trying to fetch mouse {session.subject_id}. '
                                f'Will not log water.')
                return
            else:
                logging.error(f'While fetching mouse {session.subject_id} model, unexpected error occurred.')
                raise e

        # extract water information
        logging.info('Extracting water information from first stimulus epoch')
        water_json = session.stimulus_epochs[0].output_parameters.water.items()
        water = {k: v if not (isinstance(v, float) and math.isnan(v)) else None for k, v in water_json}

        # extract software information
        logging.info('Extracting software information from first data stream')
        software = session.data_streams[0].software[0]

        # create model
        logging.info('Creating SlimsWaterlogResult based on session information.')
        model = models.SlimsWaterlogResult(
            mouse_pk=mouse.pk,
            date=session.session_start_time,
            weight_g=session.animal_weight_prior,
            water_earned_ml=water['water_in_session_foraging'],
            water_supplement_delivered_ml=water['water_after_session'],
            water_supplement_recommended_ml=None,
            total_water_ml=water['water_in_session_total'],
            comments=session.notes,
            workstation=session.rig_id,
            sw_source=software.url,
            sw_version=software.version,
            test_pk=self.slims_client.fetch_pk("Test", test_name="test_waterlog"))

        # check if mouse already has waterlog for at session time and if, so update model
        logging.info(f'Fetching previous waterlog for mouse {session.subject_id}')
        waterlog = self.slims_client.fetch_models(models.SlimsWaterlogResult, mouse_pk=mouse.pk, start=0, end=1)
        if waterlog != [] and waterlog[0].date.strftime("%Y-%m-%d %H:%M:%S") == \
                session.session_start_time.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"):
            logging.info(f'Waterlog information already exists for this session. Updating waterlog in Slims.')
            model.pk = waterlog[0].pk
            self.slims_client.update_model(model=model)
        else:
            logging.info(f'Adding waterlog to Slims.')
            self.slims_client.add_model(model)

    def _InitializeBonsai(self):
        '''
            Connect to Bonsai using OSC messages to establish a connection. 
            
            We first attempt to connect, to see if Bonsai is already running. 
            If not, we start Bonsai and check the connection every 500ms.
            If we wait more than 6 seconds without Bonsai connection we set 
            InitializeBonsaiSuccessfully=0 and return
    
        '''

        # Try to connect, to see if Bonsai is already running
        self.InitializeBonsaiSuccessfully=0
        try:
            logging.info('Trying to connect to already running Bonsai')
            self._ConnectOSC()
        except Exception as e:
            # We couldn't connect, log as info, and move on
            logging.info('Could not connect: '+str(e))
        else:
            # We could connect, set the indicator flag and return
            logging.info('Connected to already running Bonsai')
            logging.info('Bonsai started successfully')
            self.InitializeBonsaiSuccessfully=1
            return

        # Start Bonsai
        logging.info('Starting Bonsai')
        self._OpenBonsaiWorkflow()

        # Test the connection until it completes or we time out
        wait = 0
        max_wait = 6
        check_every = .5
        while wait < max_wait:
            time.sleep(check_every)
            wait += check_every
            try:
                self._ConnectOSC()
            except Exception as e:
                # We could not connect
                logging.info('Could not connect, total waiting time {} seconds: '.format(wait)+str(e))
            else:
                # We could connect
                logging.info('Connected to Bonsai after {} seconds'.format(wait))
                logging.info('Bonsai started successfully')
                self.InitializeBonsaiSuccessfully=1
                subprocess.Popen('title Box{}'.format(self.box_letter),shell=True)
                return

        # Could not connect and we timed out
        logging.info('Could not connect to bonsai with max wait time {} seconds'.format(max_wait))
        logging.warning('Started without bonsai connected!', extra={'tags': [self.warning_log_tag]})

    def _ConnectOSC(self):
        '''
            Connect the GUI and Bonsai through OSC messages
            Uses self.box_number to determine ports
        '''

        # connect the bonsai workflow with the python GUI
        logging.info('connecting to GUI and Bonsai through OSC')
        self.ip = "127.0.0.1"

        if self.box_number==1:
            self.request_port = 4002
            self.request_port2 = 4003
            self.request_port3 = 4004
            self.request_port4 = 4005
        elif self.box_number==2:
            self.request_port = 4012
            self.request_port2 = 4013
            self.request_port3 = 4014
            self.request_port4 = 4015
        elif self.box_number==3:
            self.request_port = 4022
            self.request_port2 = 4023
            self.request_port3 = 4024
            self.request_port4 = 4025
        elif self.box_number==4:
            self.request_port = 4032
            self.request_port2 = 4033
            self.request_port3 = 4034
            self.request_port4 = 4035
        else:
            logging.error('bad bonsai tag {}'.format(self.box_number))
            self.request_port = 4002
            self.request_port2 = 4003
            self.request_port3 = 4004
            self.request_port4 = 4005

        # normal behavior events
        self.client = OSCStreamingClient()  # Create client 
        self.client.connect((self.ip, self.request_port))
        self.Channel = rigcontrol.RigClient(self.client)
        # licks, LeftRewardDeliveryTime and RightRewardDeliveryTime 
        self.client2 = OSCStreamingClient()
        self.client2.connect((self.ip, self.request_port2))
        self.Channel2 = rigcontrol.RigClient(self.client2)
        # manually give water
        self.client3 = OSCStreamingClient()  # Create client
        self.client3.connect((self.ip, self.request_port3))
        self.Channel3 = rigcontrol.RigClient(self.client3)
        # specific for transfering optogenetics waveform
        self.client4 = OSCStreamingClient()  # Create client
        self.client4.connect((self.ip, self.request_port4))
        self.Channel4 = rigcontrol.RigClient(self.client4)
        # clear previous events
        while not self.Channel.msgs.empty():
            self.Channel.receive()
        while not self.Channel2.msgs.empty():
            self.Channel2.receive()
        while not self.Channel3.msgs.empty():
            self.Channel3.receive()
        while not self.Channel4.msgs.empty():
            self.Channel4.receive()
        self.InitializeBonsaiSuccessfully=1

    def _OpenBonsaiWorkflow(self,runworkflow=1):
        '''Open the bonsai workflow and run it'''

        SettingsBox = 'Settings_box{}.csv'.format(self.box_number)
        CWD=os.path.join(os.path.dirname(os.getcwd()),'workflows')
        if self.start_bonsai_ide:
            process = subprocess.Popen(self.bonsai_path+' '+self.bonsaiworkflow_path+' -p '+'SettingsPath='+self.SettingFolder+'\\'+SettingsBox+ ' --start',cwd=CWD,shell=True,
                stdout = subprocess.PIPE, stderr = subprocess.STDOUT,text=True)
        else:
            process = subprocess.Popen(self.bonsai_path+' '+self.bonsaiworkflow_path+' -p '+'SettingsPath='+self.SettingFolder+'\\'+SettingsBox+ ' --start --no-editor',cwd=CWD,shell=True,
                stdout = subprocess.PIPE, stderr = subprocess.STDOUT,text=True)

        # Log stdout and stderr from bonsai in a separate thread
        threading.Thread(target=log_subprocess_output, args=(process,'BONSAI',)).start()


    def _OpenVideoFolder(self):
        '''Open the video folder'''
        try:
            subprocess.Popen(['explorer', self.VideoFolder])
        except Exception as e:
            logging.error(traceback.format_exc())

    def _OpenMetadataDialogFolder(self):
        '''Open the metadata dialog folder'''
        try:
            subprocess.Popen(['explorer', self.metadata_dialog_folder])
        except Exception as e:
            logging.error(traceback.format_exc())

    def _OpenRigMetadataFolder(self):
        '''Open the rig metadata folder'''
        try:
            subprocess.Popen(['explorer', self.rig_metadata_folder])
        except Exception as e:
            logging.error(traceback.format_exc())

    def _load_most_recent_rig_json(self,error_if_none=True):
        # See if rig metadata folder exists 
        if not os.path.exists(self.Settings['rig_metadata_folder']):
            print('making directory: {}'.format(self.Settings['rig_metadata_folder']))
            os.makedirs(self.Settings['rig_metadata_folder'])

        # Load most recent rig_json
        files = sorted(Path(self.Settings['rig_metadata_folder']).iterdir(), key=os.path.getmtime)
        files = [f.__str__().split('\\')[-1] for f in files]
        files = [f for f in files if (f.startswith('rig_'+self.rig_name) and f.endswith('.json'))]

        if len(files) ==0:
            # No rig.jsons found
            rig_json = {}
            rig_json_path = ''
            if error_if_none:
                logging.error('Did not find any existing rig.json files')
            else:
                logging.info('Did not find any existing rig.json files')    #FIXME: is this really the right message
        else:
            rig_json_path = os.path.join(self.Settings['rig_metadata_folder'],files[-1])
            logging.info('Found existing rig.json: {}'.format(files[-1]))
            with open(rig_json_path, 'r') as f:
                rig_json = json.load(f)

        return rig_json, rig_json_path

    def _LoadRigJson(self):

        # User can skip this step if they make rig metadata themselves
        if not self.Settings['create_rig_metadata']:
            logging.info('Skipping rig metadata creation because create_rig_metadata=False')
            return

        existing_rig_json, rig_json_path = self._load_most_recent_rig_json(error_if_none=False)

        # Builds a new rig.json, and saves if there are changes with the most recent
        rig_settings = self.Settings.copy()
        rig_settings['rig_name'] = self.rig_name
        rig_settings['box_number'] = self.box_number
        df = pd.read_csv(self.SettingsBoxFile,index_col=None,header=None)
        rig_settings['box_settings'] = {row[0]:row[1] for index, row in df.iterrows()}
        rig_settings['computer_name'] = socket.gethostname()
        rig_settings['bonsai_version'] = self._get_bonsai_version(rig_settings['bonsai_config_path'])

        if hasattr(self, 'LaserCalibrationResults'):
            LaserCalibrationResults = self.LaserCalibrationResults
        else:
            LaserCalibrationResults={}
        if hasattr(self, 'WaterCalibrationResults'):
            WaterCalibrationResults = self.WaterCalibrationResults
        else:
            WaterCalibrationResults={}

        # Load CMOS serial numbers for FIP if they exist 
        green_cmos = os.path.join(self.Settings['FIP_settings'], 'CameraSerial_Green.csv')
        red_cmos = os.path.join(self.Settings['FIP_settings'], 'CameraSerial_Red.csv')
        if os.path.isfile(green_cmos):
            with open(green_cmos, 'r') as f:
                green_cmos_sn = f.read()
            rig_settings['box_settings']["FipGreenCMOSSerialNumber"] = green_cmos_sn.strip('\n')
        if os.path.isfile(red_cmos):
            with open(red_cmos, 'r') as f:
                red_cmos_sn = f.read()
            rig_settings['box_settings']["FipRedCMOSSerialNumber"] = red_cmos_sn.strip('\n')

        build_rig_json(existing_rig_json, rig_settings,
            WaterCalibrationResults,
            LaserCalibrationResults)

    def _get_bonsai_version(self,config_path):
        with open(config_path, "r") as f:
            for line in f:
                if 'Package id="Bonsai"' in line:
                   return line.split('version="')[1].split('"')[0]
        return '0.0.0'

    def _OpenSettingFolder(self):
        '''Open the setting folder'''
        try:
            subprocess.Popen(['explorer', self.SettingFolder])
        except Exception as e:
            logging.error(traceback.format_exc())

    def _ForceSave(self):
        '''Save whether the current trial is complete or not'''
        self._Save(ForceSave=1)

    def _SaveAs(self):
        '''Do not restart a session after saving'''
        self._Save(SaveAs=1)

    def _WaterVolumnManage1(self):
        '''Change the water volume based on the valve open time'''
        self.LeftValue.textChanged.disconnect(self._WaterVolumnManage1)
        self.RightValue.textChanged.disconnect(self._WaterVolumnManage1)
        self.GiveWaterL.textChanged.disconnect(self._WaterVolumnManage1)
        self.GiveWaterR.textChanged.disconnect(self._WaterVolumnManage1)
        self.LeftValue_volume.textChanged.disconnect(self._WaterVolumnManage2)
        self.RightValue_volume.textChanged.disconnect(self._WaterVolumnManage2)
        self.GiveWaterL_volume.textChanged.disconnect(self._WaterVolumnManage2)
        self.GiveWaterR_volume.textChanged.disconnect(self._WaterVolumnManage2)
        # use the latest calibration result
        if hasattr(self, 'WaterCalibration_dialog'):
            if hasattr(self.WaterCalibration_dialog, 'PlotM'):
                if  hasattr(self.WaterCalibration_dialog.PlotM, 'FittingResults'):
                    FittingResults=self.WaterCalibration_dialog.PlotM.FittingResults
                    tag=1
        if tag==1:
            self._GetLatestFitting(FittingResults)
            self._ValvetimeVolumnTransformation(widget2=self.LeftValue_volume,widget1=self.LeftValue,direction=1,valve='Left')
            self._ValvetimeVolumnTransformation(widget2=self.RightValue_volume,widget1=self.RightValue,direction=1,valve='Right')
            self._ValvetimeVolumnTransformation(widget2=self.GiveWaterL_volume,widget1=self.GiveWaterL,direction=1,valve='Left')
            self._ValvetimeVolumnTransformation(widget2=self.GiveWaterR_volume,widget1=self.GiveWaterR,direction=1,valve='Right')
            self.LeftValue_volume.setEnabled(True)
            self.RightValue_volume.setEnabled(True)
            self.GiveWaterL_volume.setEnabled(True)
            self.GiveWaterR_volume.setEnabled(True)
            self.label_28.setEnabled(True)
            self.label_29.setEnabled(True)
        else:
            self.LeftValue_volume.setEnabled(False)
            self.RightValue_volume.setEnabled(False)
            self.GiveWaterL_volume.setEnabled(False)
            self.GiveWaterR_volume.setEnabled(False)
            self.label_28.setEnabled(False)
            self.label_29.setEnabled(False)
        self.LeftValue.textChanged.connect(self._WaterVolumnManage1)
        self.RightValue.textChanged.connect(self._WaterVolumnManage1)
        self.GiveWaterL.textChanged.connect(self._WaterVolumnManage1)
        self.GiveWaterR.textChanged.connect(self._WaterVolumnManage1)
        self.LeftValue_volume.textChanged.connect(self._WaterVolumnManage2)
        self.RightValue_volume.textChanged.connect(self._WaterVolumnManage2)
        self.GiveWaterL_volume.textChanged.connect(self._WaterVolumnManage2)
        self.GiveWaterR_volume.textChanged.connect(self._WaterVolumnManage2)

    def _WaterVolumnManage2(self):
        '''Change the valve open time based on the water volume'''
        self.LeftValue.textChanged.disconnect(self._WaterVolumnManage1)
        self.RightValue.textChanged.disconnect(self._WaterVolumnManage1)
        self.GiveWaterL.textChanged.disconnect(self._WaterVolumnManage1)
        self.GiveWaterR.textChanged.disconnect(self._WaterVolumnManage1)
        self.LeftValue_volume.textChanged.disconnect(self._WaterVolumnManage2)
        self.RightValue_volume.textChanged.disconnect(self._WaterVolumnManage2)
        self.GiveWaterL_volume.textChanged.disconnect(self._WaterVolumnManage2)
        self.GiveWaterR_volume.textChanged.disconnect(self._WaterVolumnManage2)
        # use the latest calibration result
        if hasattr(self, 'WaterCalibration_dialog'):
            if hasattr(self.WaterCalibration_dialog, 'PlotM'):
                if  hasattr(self.WaterCalibration_dialog.PlotM, 'FittingResults'):
                    FittingResults=self.WaterCalibration_dialog.PlotM.FittingResults
                    tag=1
        if tag==1:
            self._GetLatestFitting(FittingResults)
            self._ValvetimeVolumnTransformation(widget1=self.LeftValue_volume,widget2=self.LeftValue,direction=-1,valve='Left')
            self._ValvetimeVolumnTransformation(widget1=self.RightValue_volume,widget2=self.RightValue,direction=-1,valve='Right')
            self._ValvetimeVolumnTransformation(widget1=self.GiveWaterL_volume,widget2=self.GiveWaterL,direction=-1,valve='Left')
            self._ValvetimeVolumnTransformation(widget1=self.GiveWaterR_volume,widget2=self.GiveWaterR,direction=-1,valve='Right')
        else:
            self.LeftValue_volume.setEnabled(False)
            self.RightValue_volume.setEnabled(False)
            self.GiveWaterL_volume.setEnabled(False)
            self.GiveWaterR_volume.setEnabled(False)
            self.label_28.setEnabled(False)
            self.label_29.setEnabled(False)
        self.LeftValue.textChanged.connect(self._WaterVolumnManage1)
        self.RightValue.textChanged.connect(self._WaterVolumnManage1)
        self.GiveWaterL.textChanged.connect(self._WaterVolumnManage1)
        self.GiveWaterR.textChanged.connect(self._WaterVolumnManage1)
        self.LeftValue_volume.textChanged.connect(self._WaterVolumnManage2)
        self.RightValue_volume.textChanged.connect(self._WaterVolumnManage2)
        self.GiveWaterL_volume.textChanged.connect(self._WaterVolumnManage2)
        self.GiveWaterR_volume.textChanged.connect(self._WaterVolumnManage2)

    def _ValvetimeVolumnTransformation(self,widget1,widget2,direction,valve):
        '''Transformation between valve open time the the water volume'''
        # widget1 is the source widget and widget2 is the target widget
        try:
            if valve not in self.latest_fitting:
                # disable the widget
                if direction==1:
                    widget2.setEnabled(False)
                elif direction==-1:
                    widget1.setEnabled(False)
                return
            else:
                widget2.setEnabled(True)
                widget1.setEnabled(True)
            if direction==1:
                widget2.setValue(float(widget1.text())*self.latest_fitting[valve][0]+self.latest_fitting[valve][1])
            elif direction==-1:
                widget2.setValue((float(widget1.text())-self.latest_fitting[valve][1])/self.latest_fitting[valve][0])
        except Exception as e:
            logging.error(traceback.format_exc())

    def _GetLatestFitting(self,FittingResults):
        '''Get the latest fitting results from water calibration'''
        latest_fitting={}
        sorted_dates = sorted(FittingResults.keys(), key=self._custom_sort_key)
        sorted_dates=sorted_dates[::-1]
        for current_date in sorted_dates:
            if 'Left' in FittingResults[current_date]:
                latest_fitting['Left']=FittingResults[current_date]['Left']
                break
        for current_date in sorted_dates:
            if 'Right' in FittingResults[current_date]:
                latest_fitting['Right']=FittingResults[current_date]['Right']
                break
        self.latest_fitting=latest_fitting

    def _OpenBehaviorFolder(self):
        '''Open the the current behavior folder'''
        try:
            folder_name=os.path.dirname(self.SaveFileJson)
            subprocess.Popen(['explorer', folder_name])
        except Exception as e:
            logging.error(traceback.format_exc())
            try:
                AnimalFolder=os.path.join(self.default_saveFolder, self.current_box, self.ID.text())
                subprocess.Popen(['explorer', AnimalFolder])
            except Exception as e:
                logging.error(traceback.format_exc())

    def _OpenLoggingFolder(self):
        '''Open the logging folder'''
        try:
            subprocess.Popen(['explorer', self.Ot_log_folder])
        except Exception as e:
            logging.error(traceback.format_exc())

    def _startTemporaryLogging(self):
        '''Restart the temporary logging'''
        self.Ot_log_folder=self._restartlogging(self.temporary_video_folder)

    def _startFormalLogging(self):
        '''Restart the formal logging'''
        self.Ot_log_folder=self._restartlogging()

    def _set_parameters(self,key,widget_dict,parameters):
        '''Set the parameters in the GUI
            key: the parameter name you want to change
            widget_dict: the dictionary of all the widgets in the GUI
            parameters: the dictionary of all the parameters containing the key you want to change
        '''
        if key in parameters:
            # skip some keys
            if key=='ExtraWater' or key=='WeightAfter' or key=='SuggestedWater':
                self.WeightAfter.setText('')
                return
            widget = widget_dict[key]
            try: # load the paramter used by last trial
                value=np.array([parameters[key]])
                loading_parameters_type=0
            # sometimes we only have training parameters, no behavior parameters
            except Exception as e:
                logging.error(traceback.format_exc())
                value=parameters[key]
                loading_parameters_type=1
            if isinstance(widget, QtWidgets.QPushButton):
                pass
            if type(value)==bool:
                loading_parameters_type=1
            else:
                if len(value)==0:
                    value=np.array([''], dtype='<U1')
                    loading_parameters_type=0
            if type(value)==np.ndarray:
                loading_parameters_type=0
            if isinstance(widget, QtWidgets.QLineEdit):
                if loading_parameters_type==0:
                    widget.setText(value[-1])
                elif loading_parameters_type==1:
                    widget.setText(value)
            elif isinstance(widget, QtWidgets.QComboBox):
                if loading_parameters_type==0:
                    index = widget.findText(value[-1])
                elif loading_parameters_type==1:
                    index = widget.findText(value)
                if index != -1:
                    widget.setCurrentIndex(index)
            elif isinstance(widget, QtWidgets.QDoubleSpinBox):
                if loading_parameters_type==0:
                    widget.setValue(float(value[-1]))
                elif loading_parameters_type==1:
                    widget.setValue(float(value))
            elif isinstance(widget, QtWidgets.QSpinBox):
                if loading_parameters_type==0:
                    widget.setValue(int(value[-1]))
                elif loading_parameters_type==1:
                    widget.setValue(int(value))
            elif isinstance(widget, QtWidgets.QTextEdit):
                if loading_parameters_type==0:
                    widget.setText(value[-1])
                elif loading_parameters_type==1:
                    widget.setText(value)
            elif isinstance(widget, QtWidgets.QPushButton):
                if key=='AutoReward':
                    if loading_parameters_type==0:
                        widget.setChecked(bool(value[-1]))
                    elif loading_parameters_type==1:
                        widget.setChecked(value)
                    self._AutoReward()
        else:
            widget = widget_dict[key]
            if not (isinstance(widget, QtWidgets.QComboBox) or isinstance(widget, QtWidgets.QPushButton)):
                pass
                #widget.clear()

    def _Randomness(self):
        '''enable/disable some fields in the Block/Delay Period/ITI'''
        if self.Randomness.currentText()=='Exponential':
            self.label_14.setEnabled(True)
            self.label_18.setEnabled(True)
            self.label_39.setEnabled(True)
            self.BlockBeta.setEnabled(True)
            self.DelayBeta.setEnabled(True)
            self.ITIBeta.setEnabled(True)
            # if self.Task.currentText()!='RewardN':
            #     self.BlockBeta.setStyleSheet("color: black;border: 1px solid gray;background-color: white;")
        elif self.Randomness.currentText()=='Even':
            self.label_14.setEnabled(False)
            self.label_18.setEnabled(False)
            self.label_39.setEnabled(False)
            self.BlockBeta.setEnabled(False)
            self.DelayBeta.setEnabled(False)
            self.ITIBeta.setEnabled(False)
            # if self.Task.currentText()!='RewardN':
            #     border_color = "rgb(100, 100, 100,80)"
            #     border_style = "1px solid " + border_color
            #     self.BlockBeta.setStyleSheet(f"color: gray;border:{border_style};background-color: rgba(0, 0, 0, 0);")

    def _AdvancedBlockAuto(self):
        '''enable/disable some fields in the AdvancedBlockAuto'''
        if self.AdvancedBlockAuto.currentText()=='off':
            self.label_54.setEnabled(False)
            self.label_60.setEnabled(False)
            self.SwitchThr.setEnabled(False)
            self.PointsInARow.setEnabled(False)
        else:
            self.label_54.setEnabled(True)
            self.label_60.setEnabled(True)
            self.SwitchThr.setEnabled(True)
            self.PointsInARow.setEnabled(True)

    def _QComboBoxUpdate(self, parameter,value):
        logging.info('Field updated: {}:{}'.format(parameter, value))


    def keyPressEvent(self, event=None,allow_reset=False):
        '''
            Enter press to allow change of parameters
            allow_reset (bool) allows the Baseweight etc. parameters to be reset to the empty string
        '''
        try:
            if self.actionTime_distribution.isChecked()==True:
                self.PlotTime._Update(self)
        except Exception as e:
            logging.error(traceback.format_exc())

        # move newscale stage
        if hasattr(self,'current_stage'):
            if (self.PositionX.text() != '')and (self.PositionY.text() != '')and (self.PositionZ.text() != ''):
                try:
                    self.StageStop.click
                    self.current_stage.move_absolute_3d(float(self.PositionX.text()),float(self.PositionY.text()),float(self.PositionZ.text()))
                except Exception as e:
                    logging.error(traceback.format_exc())
        # Get the parameters before change
        if hasattr(self, 'GeneratedTrials') and self.ToInitializeVisual==0: # use the current GUI paramters when no session starts running
            Parameters=self.GeneratedTrials
        else:
            Parameters=self
        if event is None or not isinstance(event, QtGui.QKeyEvent):
            event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, Qt.Key_Return, Qt.KeyboardModifiers())
        if (event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter):
            # handle the return key press event here
            logging.info('processing parameter changes')
            # prevent the default behavior of the return key press event
            event.accept()
            self.UpdateParameters=1 # Changes are allowed
            # change color to black
            for container in [self.TrainingParameters, self.centralwidget, self.Opto_dialog,self.Metadata_dialog]:
                # Iterate over each child of the container that is a QLineEdit or QDoubleSpinBox
                for child in container.findChildren((QtWidgets.QLineEdit,QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox)):
                    if child.objectName()=='qt_spinbox_lineedit':
                        continue

                    if not (hasattr(self, 'AutoTrain_dialog') and self.AutoTrain_dialog.auto_train_engaged):
                        # Only run _Task again if AutoTrain is NOT engaged
                        # To avoid the _Task() function overwriting the AutoTrain UI locks
                        # resolves https://github.com/AllenNeuralDynamics/dynamic-foraging-task/issues/239
                        child.setStyleSheet('color: black;')
                        child.setStyleSheet('background-color: white;')
                        self._Task()

                    if child.objectName() in {'WeightAfter','LickSpoutDistance','ModuleAngle','ArcAngle','ProtocolID','Stick_RotationAngle','LickSpoutReferenceX','LickSpoutReferenceY','LickSpoutReferenceZ','LickSpoutReferenceArea','Fundee','ProjectCode','GrantNumber','FundingSource','Investigators','Stick_ArcAngle','Stick_ModuleAngle','RotationAngle','ManipulatorX','ManipulatorY','ManipulatorZ','ProbeTarget','RigMetadataFile','IACUCProtocol','Experimenter','TotalWater','ExtraWater','laser_1_target','laser_2_target','laser_1_calibration_power','laser_2_calibration_power','laser_1_calibration_voltage','laser_2_calibration_voltage'}:
                        continue
                    if child.objectName()=='UncoupledReward':
                        Correct=self._CheckFormat(child)
                        if Correct ==0: # incorrect format; don't change
                            child.setText(getattr(Parameters, 'TP_'+child.objectName()))
                        continue
                    if ((child.objectName() in ['PositionX','PositionY','PositionZ','SuggestedWater','BaseWeight','TargetWeight','','GoCueDecibel','ConditionP_5','ConditionP_6','Duration_5','Duration_6','OffsetEnd_5','OffsetEnd_6','OffsetStart_5','OffsetStart_6','Probability_5','Probability_6','PulseDur_5','PulseDur_6','RD_5','RD_6']) and
                        (child.text() == '')):
                        # These attributes can have the empty string, but we can't set the value as the empty string, unless we allow resets
                        if allow_reset:
                            continue
                        if hasattr(Parameters, 'TP_'+child.objectName()) and child.objectName()!='':
                            child.setText(getattr(Parameters, 'TP_'+child.objectName()))
                        continue
                    if (child.objectName() in ['LatestCalibrationDate','SessionlistSpin']):
                        continue


                    # check for empty string condition
                    try:
                        float(child.text())
                    except Exception as e:
                        # Invalid float. Do not change the parameter, reset back to previous value
                        logging.error('Cannot convert input to float: {}, \'{}\''.format(child.objectName(),child.text()))
                        if isinstance(child, QtWidgets.QDoubleSpinBox):
                            child.setValue(float(getattr(Parameters, 'TP_'+child.objectName())))
                        elif isinstance(child, QtWidgets.QSpinBox):
                            child.setValue(int(getattr(Parameters, 'TP_'+child.objectName())))
                        else:
                            if hasattr(Parameters, 'TP_'+child.objectName()) and child.objectName()!='':
                                child.setText(getattr(Parameters, 'TP_'+child.objectName()))
                    else:
                        if hasattr(Parameters, 'TP_'+child.objectName()) and child.objectName()!='':
                            # If this parameter changed, add the change to the log
                            old = getattr(Parameters,'TP_'+child.objectName())
                            if old != '':
                                old = float(old)
                            new = float(child.text())
                            if new != old:
                                logging.info('Changing parameter: {}, {} -> {}'.format(child.objectName(), old,new))

            # update the current training parameters
            self._GetTrainingParameters()

    def _CheckTextChange(self):
        '''Check if the text change is reasonable'''
        # Get the parameters before change
        if hasattr(self, 'GeneratedTrials'):
            Parameters=self.GeneratedTrials
        else:
            Parameters=self
        for container in [self.TrainingParameters, self.centralwidget, self.Opto_dialog,self.Metadata_dialog]:
            # Iterate over each child of the container that is a QLineEdit or QDoubleSpinBox
            for child in container.findChildren((QtWidgets.QLineEdit,QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox)):
                if child.objectName()=='qt_spinbox_lineedit' or child.isEnabled()==False: # I don't understand where the qt_spinbox_lineedit comes from.
                    continue
                if (child.objectName()=='RewardFamily' or child.objectName()=='RewardPairsN' or child.objectName()=='BaseRewardSum') and (child.text()!=''):
                    Correct=self._CheckFormat(child)
                    if Correct ==0: # incorrect format; don't change
                        child.setText(getattr(Parameters, 'TP_'+child.objectName()))
                    self._ShowRewardPairs()
                try:
                    if getattr(Parameters, 'TP_'+child.objectName())!=child.text() :
                        # Changes are not allowed until press is typed except for PositionX, PositionY and PositionZ
                        if child.objectName() not in ('PositionX', 'PositionY', 'PositionZ'):
                            self.UpdateParameters = 0

                        self.Continue=0
                        if child.objectName() in {'LickSpoutReferenceArea','Fundee','ProjectCode','GrantNumber','FundingSource','Investigators','ProbeTarget','RigMetadataFile','Experimenter', 'UncoupledReward', 'ExtraWater','laser_1_target','laser_2_target','laser_1_calibration_power','laser_2_calibration_power','laser_1_calibration_voltage','laser_2_calibration_voltage'}:
                            child.setStyleSheet(self.default_text_color)
                            self.Continue=1
                        if child.text()=='': # If empty, change background color and wait for confirmation
                            self.UpdateParameters=0
                            child.setStyleSheet(self.default_text_background_color)
                            self.Continue=1
                        if child.objectName() in {'RunLength','WindowSize','StepSize'}:
                            if child.text()=='':
                                child.setValue(int(getattr(Parameters, 'TP_'+child.objectName())))
                                child.setStyleSheet('color: black;')
                                child.setStyleSheet('background-color: white;')
                        if self.Continue==1:
                            continue
                        child.setStyleSheet(self.default_text_color)
                        try:
                            # it's valid float
                            float(child.text())
                        except Exception as e:
                            #logging.error(traceback.format_exc())
                            # Invalid float. Do not change the parameter
                            if child.objectName() in ['BaseWeight', 'WeightAfter']:
                                # Strip the last character which triggered the invalid float
                                child.setText(child.text()[:-1])
                                continue
                            elif isinstance(child, QtWidgets.QDoubleSpinBox):
                                child.setValue(float(getattr(Parameters, 'TP_'+child.objectName())))
                            elif isinstance(child, QtWidgets.QSpinBox):
                                child.setValue(int(getattr(Parameters, 'TP_'+child.objectName())))
                            else:
                                child.setText(getattr(Parameters, 'TP_'+child.objectName()))
                            child.setText(getattr(Parameters, 'TP_'+child.objectName()))
                            child.setStyleSheet('color: black;')
                            self.UpdateParameters=0
                    else:
                        child.setStyleSheet('color: black;')
                        child.setStyleSheet('background-color: white;')
                except Exception as e:
                    #logging.error(traceback.format_exc())
                    pass

    def _CheckFormat(self,child):
        '''Check if the input format is correct'''
        if child.objectName()=='RewardFamily': # When we change the RewardFamily, sometimes the RewardPairsN is larger than available reward pairs in this family.
            try:
                self.RewardFamilies[int(self.RewardFamily.text())-1]
                if int(self.RewardPairsN.text())>len(self.RewardFamilies[int(self.RewardFamily.text())-1]):
                    self.RewardPairsN.setText(str(len(self.RewardFamilies[int(self.RewardFamily.text())-1])))
                return 1
            except Exception as e:
                logging.error(traceback.format_exc())
                return 0
        if child.objectName()=='RewardFamily' or child.objectName()=='RewardPairsN' or child.objectName()=='BaseRewardSum':
            try:
                self.RewardPairs=self.RewardFamilies[int(self.RewardFamily.text())-1][:int(self.RewardPairsN.text())]
                if int(self.RewardPairsN.text())>len(self.RewardFamilies[int(self.RewardFamily.text())-1]):
                    return 0
                else:
                    return 1
            except Exception as e:
                logging.error(traceback.format_exc())
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
                logging.error(traceback.format_exc())
                return 0
        else:
            return 1

    def _GetTrainingParameters(self,prefix='TP_'):
        '''Get training parameters'''
        # Iterate over each container to find child widgets and store their values in self
        for container in [self.TrainingParameters, self.centralwidget, self.Opto_dialog,self.Metadata_dialog]:
            # Iterate over each child of the container that is a QLineEdit or QDoubleSpinBox
            for child in container.findChildren((QtWidgets.QLineEdit, QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox)):
                if child.objectName()=='qt_spinbox_lineedit':
                    continue
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store the child's text value
                setattr(self, prefix+child.objectName(), child.text())
            # Iterate over each child of the container that is a QComboBox
            for child in container.findChildren(QtWidgets.QComboBox):
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store the child's current text value
                setattr(self, prefix+child.objectName(), child.currentText())
            # Iterate over each child of the container that is a QPushButton
            for child in container.findChildren(QtWidgets.QPushButton):
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store whether the child is checked or not
                setattr(self, prefix+child.objectName(), child.isChecked())


    def _Task(self):
        '''hide and show some fields based on the task type'''
        self.label_43.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: rgba(0, 0, 0, 0);""border: none;")
        self.ITIIncrease.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: rgba(0, 0, 0, 0);""border: none;")
        self._Randomness()

        if self.Task.currentText() in ['Coupled Baiting','Coupled Without Baiting']:
            self.label_6.setEnabled(True)
            self.label_7.setEnabled(True)
            self.label_8.setEnabled(True)
            self.BaseRewardSum.setEnabled(True)
            self.RewardPairsN.setEnabled(True)
            self.RewardFamily.setEnabled(True)
            self.label_20.setEnabled(False)
            self.UncoupledReward.setEnabled(False)
            # block
            self.BlockMinReward.setEnabled(True)
            self.IncludeAutoReward.setEnabled(True)
            self.BlockBeta.setEnabled(True)
            self.BlockMin.setEnabled(True)
            self.BlockMax.setEnabled(True)
            self.label_12.setStyleSheet("color: black;")
            self.label_11.setStyleSheet("color: black;")
            self.label_14.setStyleSheet("color: black;")
            self.BlockBeta.setStyleSheet("color: black;""border: 1px solid gray;")
            self.BlockMin.setStyleSheet("color: black;""border: 1px solid gray;")
            self.BlockMax.setStyleSheet("color: black;""border: 1px solid gray;")

            self.label_27.setEnabled(False)
            self.InitiallyInactiveN.setEnabled(False)
            self.label_27.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: rgba(0, 0, 0, 0);""border: none;")
            self.InitiallyInactiveN.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: rgba(0, 0, 0, 0);""border: none;")
            self.InitiallyInactiveN.setGeometry(QtCore.QRect(1081, 23, 80, 20))
            # change name of min reward each block
            self.label_13.setText('min reward each block=')
            # self.BlockMinReward.setText('0')
            # change the position of RewardN=/min reward each block=
            self.BlockMinReward.setGeometry(QtCore.QRect(863, 128, 80, 20))
            self.label_13.setGeometry(QtCore.QRect(711, 128, 146, 16))
            # move auto-reward
            self.IncludeAutoReward.setGeometry(QtCore.QRect(1080, 128, 80, 20))
            self.label_26.setGeometry(QtCore.QRect(929, 128, 146, 16))

            # Reopen block beta, NextBlock, and AutoBlock panel
            self.BlockBeta.setEnabled(True)
            self.NextBlock.setEnabled(True)

            self.AdvancedBlockAuto.setEnabled(True)
            self._AdvancedBlockAuto() # Update states of SwitchThr and PointsInARow

        elif self.Task.currentText() in ['Uncoupled Baiting','Uncoupled Without Baiting']:
            self.label_6.setEnabled(False)
            self.label_7.setEnabled(False)
            self.label_8.setEnabled(False)
            self.BaseRewardSum.setEnabled(False)
            self.RewardPairsN.setEnabled(False)
            self.RewardFamily.setEnabled(False)
            self.label_20.setEnabled(True)
            self.UncoupledReward.setEnabled(True)
            # block
            self.BlockBeta.setEnabled(True)
            self.BlockMin.setEnabled(True)
            self.BlockMax.setEnabled(True)
            self.label_12.setStyleSheet("color: black;")
            self.label_11.setStyleSheet("color: black;")
            self.label_14.setStyleSheet("color: black;")
            self.BlockBeta.setStyleSheet("color: black;""border: 1px solid gray;")
            self.BlockMin.setStyleSheet("color: black;""border: 1px solid gray;")
            self.BlockMax.setStyleSheet("color: black;""border: 1px solid gray;")

            self.label_27.setEnabled(False)
            self.InitiallyInactiveN.setEnabled(False)
            self.label_27.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: rgba(0, 0, 0, 0);""border: none;")
            self.InitiallyInactiveN.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: rgba(0, 0, 0, 0);""border: none;")
            self.InitiallyInactiveN.setGeometry(QtCore.QRect(1081, 23, 80, 20))
            # change name of min reward each block
            self.label_13.setText('min reward each block=')
            #self.BlockMinReward.setText('0')
            # change the position of RewardN=/min reward each block=
            self.BlockMinReward.setGeometry(QtCore.QRect(863, 128, 80, 20))
            self.label_13.setGeometry(QtCore.QRect(711, 128, 146, 16))
            # move auto-reward
            self.IncludeAutoReward.setGeometry(QtCore.QRect(1080, 128, 80, 20))
            self.label_26.setGeometry(QtCore.QRect(929, 128, 146, 16))
            # Disable block beta, NextBlock, and AutoBlock panel
            self.BlockBeta.setEnabled(False)
            self.NextBlock.setEnabled(False)
            self.AdvancedBlockAuto.setEnabled(False)
            self.SwitchThr.setEnabled(False)
            self.PointsInARow.setEnabled(False)
            self.BlockMinReward.setEnabled(False)
            self.IncludeAutoReward.setEnabled(False)
        elif self.Task.currentText() in ['RewardN']:
            self.label_6.setEnabled(True)
            self.label_7.setEnabled(True)
            self.label_8.setEnabled(True)
            self.BaseRewardSum.setEnabled(True)
            self.RewardPairsN.setEnabled(True)
            self.RewardFamily.setEnabled(True)
            self.label_20.setEnabled(False)
            self.UncoupledReward.setEnabled(False)
            self.label_20.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: rgba(0, 0, 0, 0);""border: none;")
            self.UncoupledReward.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: rgba(0, 0, 0, 0);""border: none;")
            # block
            self.BlockMinReward.setEnabled(True)
            self.IncludeAutoReward.setEnabled(True)
            self.BlockBeta.setEnabled(False)
            self.BlockMin.setEnabled(False)
            self.BlockMax.setEnabled(False)
            self.label_14.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: rgba(0, 0, 0, 0);""border: none;")
            self.label_12.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: rgba(0, 0, 0, 0);""border: none;")
            self.label_11.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: rgba(0, 0, 0, 0);""border: none;")
            self.BlockBeta.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: rgba(0, 0, 0, 0);""border: none;")
            self.BlockMin.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: rgba(0, 0, 0, 0);""border: none;")
            self.BlockMax.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: rgba(0, 0, 0, 0);""border: none;")
            # block; no reward when initially active
            self.label_27.setEnabled(True)
            self.InitiallyInactiveN.setEnabled(True)
            self.label_27.setStyleSheet("color: black;")
            self.InitiallyInactiveN.setStyleSheet("color: black;""border: 1px solid gray;")
            self.InitiallyInactiveN.setGeometry(QtCore.QRect(403, 128, 80, 20))
            # change name of min reward each block
            self.label_13.setText('RewardN=')
            # change the position of RewardN=/min reward each block=
            self.BlockMinReward.setGeometry(QtCore.QRect(191, 128, 80, 20))
            self.label_13.setGeometry(QtCore.QRect(40, 128, 146, 16))
            # move auto-reward
            self.IncludeAutoReward.setGeometry(QtCore.QRect(614, 128, 80, 20))
            self.label_26.setGeometry(QtCore.QRect(460, 128, 146, 16))
            # set block length to be 1
            self.BlockMin.setText('1')
            self.BlockMax.setText('1')

    def _ShowRewardPairs(self):
        '''Show reward pairs'''
        try:
            if self.Task.currentText() in ['Coupled Baiting','Coupled Without Baiting','RewardN']:
                self.RewardPairs=self.RewardFamilies[int(self.RewardFamily.text())-1][:int(self.RewardPairsN.text())]
                self.RewardProb=np.array(self.RewardPairs)/np.expand_dims(np.sum(self.RewardPairs,axis=1),axis=1)*float(self.BaseRewardSum.text())
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
            if self.Task.currentText() in ['Coupled Baiting','Coupled Without Baiting','RewardN','Uncoupled Baiting','Uncoupled Without Baiting']:
                if hasattr(self, 'GeneratedTrials'):
                    self.ShowRewardPairs.setText('Reward pairs:\n'
                                                 + str(np.round(self.RewardProb,2)).replace('\n', ',')
                                                 + '\n\n'
                                                 +'Current pair:\n'
                                                 + str(np.round(self.GeneratedTrials.B_RewardProHistory[:,self.GeneratedTrials.B_CurrentTrialN],2)))
                    if self.default_ui=='ForagingGUI.ui':
                        self.ShowRewardPairs_2.setText(self.ShowRewardPairs.text())
                else:
                    self.ShowRewardPairs.setText('Reward pairs:\n'
                                                 + str(np.round(self.RewardProb,2)).replace('\n', ',')
                                                 + '\n\n'
                                                 +'Current pair:\n ')
                    if self.default_ui=='ForagingGUI.ui':
                        self.ShowRewardPairs_2.setText(self.ShowRewardPairs.text())
        except Exception as e:
            # Catch the exception and log error information
            logging.error(traceback.format_exc())

    def closeEvent(self, event):
        # stop the current session first
        self._StopCurrentSession()

        if self.unsaved_data:
            reply = QMessageBox.critical(self,
                'Box {}, Foraging Close'.format(self.box_letter),
                'Exit without saving?',
                QMessageBox.Yes | QMessageBox.No , QMessageBox.No)
            if reply == QMessageBox.No:
                event.ignore()
                return
        # post weight not entered and session ran
        elif self.WeightAfter.text() == '' and self.session_run and not self.unsaved_data:
            reply = QMessageBox.critical(self,
                                         'Box {}, Foraging Close'.format(self.box_letter),
                                         'Post weight appears to not be entered. Do you want to close gui?',
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                event.ignore()
                return
        else:
            reply = QMessageBox.question(self,
                'Box {}, Foraging Close'.format(self.box_letter),
                'Close the GUI?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.No:
                event.ignore()
                return

        event.accept()
        self.Start.setChecked(False)
        if self.InitializeBonsaiSuccessfully==1:
            # stop the camera 
            self._stop_camera()
            # stop the logging
            self._stop_logging()
            self.client.close()
            self.client2.close()
            self.client3.close()
            self.client4.close()
        self.Opto_dialog.close()

        self.Metadata_dialog.close()
        self.Camera_dialog.close()
        self.LaserCalibration_dialog.close()
        self.WaterCalibration_dialog.close()
        self._StopPhotometry(closing=True)  # Make sure photo excitation is stopped 

        print('GUI Window closed')
        logging.info('GUI Window closed')

    def _Exit(self):
        '''Close the GUI'''
        logging.info('closing the GUI')
        self.close()

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
        '''Open the camera. It's not available now'''
        if self.OpenCamera==0:
            self.Camera_dialog = CameraDialog(MainWindow=self)
            self.OpenCamera=1
        if self.action_Camera.isChecked()==True:
            self.Camera_dialog.show()
        else:
            self.Camera_dialog.hide()

    def _Metadata(self):
        '''Open the metadata dialog'''
        if self.OpenMetadata==0:
            self.Metadata_dialog = MetadataDialog(MainWindow=self)
            self.OpenMetadata=1
        if self.actionMeta_Data.isChecked()==True:
            self.Metadata_dialog.show()
        else:
            self.Metadata_dialog.hide()

    def _WaterCalibration(self):
        if self.OpenWaterCalibration==0:
            self.WaterCalibration_dialog = WaterCalibrationDialog(MainWindow=self)
            self.OpenWaterCalibration=1
        if self.action_Calibration.isChecked()==True:
            self.WaterCalibration_dialog.show()
        else:
            self.WaterCalibration_dialog.hide()

    def _LaserCalibration(self):
        if self.OpenLaserCalibration==0:
            self.LaserCalibration_dialog = LaserCalibrationDialog(MainWindow=self)
            self.OpenLaserCalibration=1
        if self.actionLaser_Calibration.isChecked()==True:
            self.LaserCalibration_dialog.show()
        else:
            self.LaserCalibration_dialog.hide()

    def _TimeDistribution(self):
        '''Plot simulated ITI/delay/block distribution'''
        if self.TimeDistribution==0:
            self.TimeDistribution_dialog = TimeDistributionDialog(MainWindow=self)
            self.TimeDistribution=1
            self.TimeDistribution_dialog.setWindowTitle("Simulated time distribution")
        if self.actionTime_distribution.isChecked()==True:
            self.TimeDistribution_dialog.show()
        else:
            self.TimeDistribution_dialog.hide()
        if self.TimeDistribution_ToInitializeVisual==1: # only run once
            PlotTime=PlotTimeDistribution()
            self.PlotTime=PlotTime
            layout=self.TimeDistribution_dialog.VisualizeTimeDist.layout()
            if layout is not None:
                for i in reversed(range(layout.count())):
                    layout.itemAt(i).widget().setParent(None)
                layout.invalidate()
            if layout is None:
                layout=QVBoxLayout(self.TimeDistribution_dialog.VisualizeTimeDist)
            toolbar = NavigationToolbar(PlotTime, self)
            toolbar.setMaximumHeight(20)
            toolbar.setMaximumWidth(300)
            layout.addWidget(toolbar)
            layout.addWidget(PlotTime)
            self.TimeDistribution_ToInitializeVisual=0
        try:
            self.PlotTime._Update(self)
        except Exception as e:
            logging.error(traceback.format_exc())

    def _LickSta(self):
        '''Licks statistics'''
        if self.LickSta==0:
            self.LickSta_dialog = LickStaDialog(MainWindow=self)
            self.LickSta=1
            self.LickSta_dialog.setWindowTitle("Licks statistics")
        if self.actionLicks_sta.isChecked()==True:
            self.LickSta_dialog.show()
        else:
            self.LickSta_dialog.hide()
        if self.LickSta_ToInitializeVisual==1: # only run once
            PlotLick=PlotLickDistribution()
            self.PlotLick=PlotLick
            layout=self.LickSta_dialog.VisuLicksStatistics.layout()
            if layout is not None:
                for i in reversed(range(layout.count())):
                    layout.itemAt(i).widget().setParent(None)
                layout.invalidate()
            if layout is None:
                layout=QVBoxLayout(self.LickSta_dialog.VisuLicksStatistics)
            toolbar = NavigationToolbar(PlotLick, self)
            toolbar.setMaximumHeight(20)
            toolbar.setMaximumWidth(300)
            layout.addWidget(toolbar)
            layout.addWidget(PlotLick)
            self.LickSta_ToInitializeVisual=0
        try:
            if hasattr(self, 'GeneratedTrials'):
                self.PlotLick._Update(GeneratedTrials=self.GeneratedTrials)
        except Exception as e:
            logging.error(traceback.format_exc())

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
    def _Save_continue(self):
        '''Save the current session witout restarting the logging'''
        self._Save(SaveContinue=1)

    def _Save(self,ForceSave=0,SaveAs=0,SaveContinue=0,BackupSave=0):
        '''
        Save the current session    

        parameters:
            ForceSave (int): 0, save after finishing the current trial, 1, save without waiting for the current trial to finish
            SaveAs (int): 0 if the user should be prompted to select a save file, 1 if the file should be saved as the current SaveFileJson
            SaveContinue (int): 0, force to start a new session, 1 if the current session should be saved without restarting the logging
            BackupSave (int): 1, save the current session without stopping the current session and without prompting the user for a save file, 0, save the current session and prompt the user for a save file
        '''

        save_clicked = self.Save.isChecked()    # save if function was called by save button press

        if BackupSave==1:
            ForceSave=1
            SaveAs=0
            SaveContinue=1
            saving_type_label = 'backup saving'
            behavior_data_field='GeneratedTrials_backup'
        elif ForceSave==1:
            saving_type_label = 'force saving'
            behavior_data_field='GeneratedTrials'
        else:
            saving_type_label = 'normal saving'
            behavior_data_field='GeneratedTrials'


        logging.info('Saving current session, ForceSave={}'.format(ForceSave))
        if ForceSave==0:
            self._StopCurrentSession() # stop the current session first
        if (self.BaseWeight.text()=='' or self.WeightAfter.text()=='' or self.TargetRatio.text()=='') and BackupSave==0:
            response = QMessageBox.question(self,
                'Box {}, Save without weight or extra water:'.format(self.box_letter),
                "Do you want to save without weight or extra water information provided?",
                 QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,QMessageBox.Yes)
            if response==QMessageBox.Yes:
                logging.warning('Saving without weight or extra water!', extra={'tags': [self.warning_log_tag]})
                pass
            elif response==QMessageBox.No:
                logging.info('saving declined by user')
                self.Save.setChecked(False)  # uncheck button
                return
            elif response==QMessageBox.Cancel:
                logging.info('saving canceled by user')
                self.Save.setChecked(False)  # uncheck button
                return
        # check if the laser power and target are entered
        if BackupSave==0 and self.OptogeneticsB.currentText()=='on' and (self.Opto_dialog.laser_1_target.text()=='' or self.Opto_dialog.laser_1_calibration_power.text()=='' or self.Opto_dialog.laser_2_target.text()=='' or self.Opto_dialog.laser_2_calibration_power.text()=='' or self.Opto_dialog.laser_1_calibration_voltage.text()=='' or self.Opto_dialog.laser_2_calibration_voltage.text()==''):
            response = QMessageBox.question(self,
                'Box {}, Save without laser target or laser power:'.format(self.box_letter),
                "Do you want to save without complete laser target or laser power calibration information provided?",
                 QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,QMessageBox.Yes)
            if response==QMessageBox.Yes:
                logging.warning('Saving without laser target or laser power!', extra={'tags': [self.warning_log_tag]})
                pass
            elif response==QMessageBox.No:
                logging.info('saving declined by user')
                self.Save.setChecked(False)  # uncheck button
                return
            elif response==QMessageBox.Cancel:
                logging.info('saving canceled by user')
                self.Save.setChecked(False)  # uncheck button
                return

        # Stop Excitation if its running
        if self.StartExcitation.isChecked() and BackupSave==0:
            self.StartExcitation.setChecked(False)
            self._StartExcitation()
            logging.info('Stopping excitation before saving')

        # get iregular timestamp
        if hasattr(self, 'GeneratedTrials') and self.InitializeBonsaiSuccessfully==1 and BackupSave==0:
            self.GeneratedTrials._get_irregular_timestamp(self.Channel2)

        # Create new folders. 
        if self.CreateNewFolder==1:
            self._GetSaveFolder()
            self.CreateNewFolder=0

        if not os.path.exists(os.path.dirname(self.SaveFileJson)):
            os.makedirs(os.path.dirname(self.SaveFileJson))
            logging.info(f"Created new folder: {os.path.dirname(self.SaveFileJson)}")

        # Save in the standard location
        if SaveAs == 0:
            self.SaveFile = self.SaveFileJson
        else:
            Names = QFileDialog.getSaveFileName(self, 'Save File',self.SaveFileJson,"JSON files (*.json);;MAT files (*.mat);;JSON parameters (*_par.json)")
            if Names[1]=='JSON parameters (*_par.json)':
                self.SaveFile=Names[0].replace('.json', '_par.json')
            else:
                self.SaveFile=Names[0]
            if self.SaveFile == '':
                logging.info('empty file name')
                self.Save.setChecked(False)  # uncheck button
                return

        # Do we have trials to save?
        if self.load_tag==1:
            Obj=self.Obj
        elif hasattr(self, behavior_data_field):
            if hasattr(getattr(self,behavior_data_field), 'Obj'):
                Obj=getattr(self,behavior_data_field).Obj
            else:
                Obj={}
        else:
            Obj={}

        if self.load_tag==0:
            widget_dict = {w.objectName(): w for w in self.centralwidget.findChildren(
                (QtWidgets.QPushButton, QtWidgets.QLineEdit, QtWidgets.QTextEdit,
                QtWidgets.QComboBox,QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox))}
            widget_dict.update({w.objectName(): w for w in self.TrainingParameters.findChildren(QtWidgets.QDoubleSpinBox)})
            self._Concat(widget_dict,Obj,'None')
            dialogs = ['LaserCalibration_dialog', 'Opto_dialog', 'Camera_dialog','Metadata_dialog']
            for dialog_name in dialogs:
                if hasattr(self, dialog_name):
                    widget_dict = {w.objectName(): w for w in getattr(self, dialog_name).findChildren(
                        (QtWidgets.QPushButton, QtWidgets.QLineEdit, QtWidgets.QTextEdit,
                        QtWidgets.QComboBox, QtWidgets.QDoubleSpinBox, QtWidgets.QSpinBox))}
                    self._Concat(widget_dict, Obj, dialog_name)
            Obj2=Obj.copy()
            # save behavor events
            if hasattr(self, behavior_data_field):
                # Do something if self has the GeneratedTrials attribute
                # Iterate over all attributes of the GeneratedTrials object
                for attr_name in dir(getattr(self, behavior_data_field)):
                    if attr_name.startswith('B_') or attr_name.startswith('BS_'):
                        if attr_name=='B_RewardFamilies' and self.SaveFile.endswith('.mat'):
                            pass
                        else:
                            Value=getattr(getattr(self, behavior_data_field), attr_name)
                            try:
                                if isinstance(Value, float) or isinstance(Value, int):
                                    if math.isnan(Value):
                                        Obj[attr_name]='nan'
                                    else:
                                        Obj[attr_name]=Value
                                else:
                                    Obj[attr_name]=Value
                            except Exception as e:
                                logging.info(f'{attr_name} is not a real scalar, save it as it is.')
                                Obj[attr_name]=Value

            # save other events, e.g. session start time
            for attr_name in dir(self):
                if attr_name.startswith('Other_') or attr_name.startswith('info_'):
                    Obj[attr_name] = getattr(self, attr_name)
            # save laser calibration results (only for the calibration session)
            if hasattr(self, 'LaserCalibration_dialog'):
                for attr_name in dir(self.LaserCalibration_dialog):
                    if attr_name.startswith('LCM_'):
                        Obj[attr_name] = getattr(self.LaserCalibration_dialog, attr_name)

            # save laser calibration results from the json file
            if hasattr(self, 'LaserCalibrationResults'):
                self._GetLaserCalibration()
                Obj['LaserCalibrationResults']=self.LaserCalibrationResults

            # save water calibration results
            if hasattr(self, 'WaterCalibrationResults'):
                self._GetWaterCalibration()
                Obj['WaterCalibrationResults']=self.WaterCalibrationResults

            # save other fields start with Ot_
            for attr_name in dir(self):
                if attr_name.startswith('Ot_'):
                    Obj[attr_name]=getattr(self, attr_name)

            if hasattr(self, 'fiber_photometry_start_time'):
                Obj['fiber_photometry_start_time'] = self.fiber_photometry_start_time
                if hasattr(self, 'fiber_photometry_end_time'):
                    end_time = self.fiber_photometry_end_time
                else:
                    end_time = str(datetime.now())
                Obj['fiber_photometry_end_time'] = end_time

            # Save the current box
            Obj['box'] = self.current_box

            # save settings
            Obj['settings'] = self.Settings
            Obj['settings_box']=self.SettingsBox

            # save the commit hash
            Obj['commit_ID']=self.commit_ID
            Obj['repo_url']=self.repo_url
            Obj['current_branch'] =self.current_branch
            Obj['repo_dirty_flag'] =self.repo_dirty_flag
            Obj['dirty_files'] =self.dirty_files
            Obj['version'] = self.version

            # save the open ephys recording information
            Obj['open_ephys'] = self.open_ephys

            if SaveContinue==0:
                # force to start a new session; Logging will stop and users cannot run new behaviors, but can still modify GUI parameters and save them.                 
                self.unsaved_data=False
                self._NewSession()
                self.unsaved_data=True
                # do not create a new folder
                self.CreateNewFolder=0

            if BackupSave==0:
                self._check_drop_frames(save_tag=1)

                # save drop frames information
                Obj['drop_frames_tag']=self.drop_frames_tag
                Obj['trigger_length']=self.trigger_length
                Obj['drop_frames_warning_text']=self.drop_frames_warning_text
                Obj['frame_num']=self.frame_num

            # save manual water 
            Obj['ManualWaterVolume']=self.ManualWaterVolume

            # save camera start/stop time
            Obj['Camera_dialog']['camera_start_time']=self.Camera_dialog.camera_start_time
            Obj['Camera_dialog']['camera_stop_time']=self.Camera_dialog.camera_stop_time

            # save the saving type (normal saving, backup saving or force saving)
            Obj['saving_type_label'] = saving_type_label

        # save folders
        Obj['SessionFolder']=self.SessionFolder
        Obj['TrainingFolder']=self.TrainingFolder
        Obj['HarpFolder']=self.HarpFolder
        Obj['VideoFolder']=self.VideoFolder
        Obj['PhotometryFolder']=self.PhotometryFolder
        Obj['MetadataFolder']=self.MetadataFolder
        Obj['SaveFile']=self.SaveFile

        # generate the metadata file and update slims
        try:
            # save the metadata collected in the metadata dialogue
            self.Metadata_dialog._save_metadata_dialog_parameters()
            Obj['meta_data_dialog'] = self.Metadata_dialog.meta_data
            # generate the metadata file
            generated_metadata=generate_metadata(Obj=Obj)
            session = generated_metadata._session()
            self.sessionGenerated.emit(session)   # emit sessionGenerated

            if BackupSave==0:
                text="Session metadata generated successfully: " + str(generated_metadata.session_metadata_success)+"\n"+\
                "Rig metadata generated successfully: " + str(generated_metadata.rig_metadata_success)
                logging.warning(text, extra={'tags': [self.warning_log_tag]})
            Obj['generate_session_metadata_success']=generated_metadata.session_metadata_success
            Obj['generate_rig_metadata_success']=generated_metadata.rig_metadata_success

            if save_clicked:    # create water log result if weight after filled and uncheck save
                if self.BaseWeight.text() != '' and self.WeightAfter.text() != '' and self.ID.text() not in ['0','1','2','3','4','5','6','7','8','9','10']:
                    self._AddWaterLogResult(session)
                self.bias_indicator.clear()  # prepare for new session


        except Exception as e:
            logging.warning('Meta data is not saved!', extra= {'tags': {self.warning_log_tag}})
            logging.error('Error generating session metadata: '+str(e))
            logging.error(traceback.format_exc())
            # set to False if error occurs
            Obj['generate_session_metadata_success']=False
            Obj['generate_rig_metadata_success']=False

        # don't save the data if the load tag is 1
        if self.load_tag==0:
            # save Json or mat
            if self.SaveFile.endswith('.mat'):
            # Save data to a .mat file
                savemat(self.SaveFile, Obj)
            elif self.SaveFile.endswith('par.json') and self.load_tag==0:
                with open(self.SaveFile, "w") as outfile:
                    json.dump(Obj2, outfile, indent=4, cls=NumpyEncoder)
            elif self.SaveFile.endswith('.json'):
                with open(self.SaveFile, "w") as outfile:
                    json.dump(Obj, outfile, indent=4, cls=NumpyEncoder)

        # Toggle unsaved data to False
        if BackupSave==0:
            self.unsaved_data=False
            self.Save.setStyleSheet("background-color : None;")
            self.Save.setStyleSheet("color: black;")

            short_file = self.SaveFile.split('\\')[-1]
            if self.load_tag==0:
                logging.warning('Saved: {}'.format(short_file), extra={'tags': [self.warning_log_tag]})
            else:
                logging.warning('Saving of loaded files is not allowed!', extra={'tags': [self.warning_log_tag]})

            self.SessionlistSpin.setEnabled(True)
            self.Sessionlist.setEnabled(True)

            if self.StartEphysRecording.isChecked():
                QMessageBox.warning(self, '', 'Data saved successfully! However, the ephys recording is still running. Make sure to stop ephys recording and save the data again!')
                self.unsaved_data=True
                self.Save.setStyleSheet("color: white;background-color : mediumorchid;")

            self.Save.setChecked(False)     # uncheck button

    def _GetSaveFolder(self):
        '''
        Create folders with structure requested by Sci.Comp.
        Each session forms an independent folder, with subfolders:
            Training data
                Harp register events
            video data
            photometry data
            ephys data
        '''

        if self.load_tag==0:
            current_time = datetime.now()
            formatted_datetime = current_time.strftime("%Y-%m-%d_%H-%M-%S")
            self._get_folder_structure_new(formatted_datetime)
            self.acquisition_datetime = formatted_datetime
            self.session_name=f'behavior_{self.ID.text()}_{formatted_datetime}'
        elif self.load_tag==1:
            self._parse_folder_structure()

        # create folders
        if not os.path.exists(self.SessionFolder):
            os.makedirs(self.SessionFolder)
            logging.info(f"Created new folder: {self.SessionFolder}")
        if not os.path.exists(self.MetadataFolder):
            os.makedirs(self.MetadataFolder)
            logging.info(f"Created new folder: {self.MetadataFolder}")
        if not os.path.exists(self.TrainingFolder):
            os.makedirs(self.TrainingFolder)
            logging.info(f"Created new folder: {self.TrainingFolder}")
        if not os.path.exists(self.HarpFolder):
            os.makedirs(self.HarpFolder)
            logging.info(f"Created new folder: {self.HarpFolder}")
        if not os.path.exists(self.VideoFolder):
            os.makedirs(self.VideoFolder)
            logging.info(f"Created new folder: {self.VideoFolder}")
        if not os.path.exists(self.PhotometryFolder):
            os.makedirs(self.PhotometryFolder)
            logging.info(f"Created new folder: {self.PhotometryFolder}")

    def _parse_folder_structure(self):
        '''parse the folder structure from the loaded json file'''
        formatted_datetime = os.path.basename(self.fname).split('_')[1]+'_'+os.path.basename(self.fname).split('_')[-1].split('.')[0]
        if os.path.basename(os.path.dirname(self.fname))=='TrainingFolder':
            # old data format
            self._get_folder_structure_old(formatted_datetime)
        else:
            # new data format
            self._get_folder_structure_new(formatted_datetime)

    def _get_folder_structure_old(self,formatted_datetime):
        '''get the folder structure for the old data format'''
        self.SessionFolder=os.path.join(self.default_saveFolder,
            self.current_box,self.ID.text(), f'{self.ID.text()}_{formatted_datetime}')
        self.MetadataFolder=os.path.join(self.SessionFolder, 'metadata-dir')
        self.TrainingFolder=os.path.join(self.SessionFolder, 'TrainingFolder')
        self.HarpFolder=os.path.join(self.SessionFolder, 'HarpFolder')
        self.VideoFolder=os.path.join(self.SessionFolder, 'VideoFolder')
        self.PhotometryFolder=os.path.join(self.SessionFolder, 'PhotometryFolder')
        self.SaveFileMat=os.path.join(self.TrainingFolder,f'{self.ID.text()}_{formatted_datetime}.mat')
        self.SaveFileJson=os.path.join(self.TrainingFolder,f'{self.ID.text()}_{formatted_datetime}.json')
        self.SaveFileParJson=os.path.join(self.TrainingFolder,f'{self.ID.text()}_{formatted_datetime}_par.json')

    def _get_folder_structure_new(self,formatted_datetime):
        '''get the folder structure for the new data format'''
        # Determine folders
        self.SessionFolder=os.path.join(self.default_saveFolder,
            self.current_box,self.ID.text(), f'behavior_{self.ID.text()}_{formatted_datetime}')
        self.TrainingFolder=os.path.join(self.SessionFolder,'behavior')
        self.SaveFileMat=os.path.join(self.TrainingFolder,f'{self.ID.text()}_{formatted_datetime}.mat')
        self.SaveFileJson=os.path.join(self.TrainingFolder,f'{self.ID.text()}_{formatted_datetime}.json')
        self.SaveFileParJson=os.path.join(self.TrainingFolder,f'{self.ID.text()}_{formatted_datetime}_par.json')
        self.HarpFolder=os.path.join(self.TrainingFolder,'raw.harp')
        self.VideoFolder=os.path.join(self.SessionFolder,'behavior-videos')
        self.PhotometryFolder=os.path.join(self.SessionFolder,'fib')
        self.MetadataFolder=os.path.join(self.SessionFolder, 'metadata-dir')

    def _Concat(self,widget_dict,Obj,keyname):
        '''Help manage save different dialogs'''
        if keyname=='None':
            for key in widget_dict.keys():
                widget = widget_dict[key]
                if isinstance(widget, QtWidgets.QPushButton):
                    Obj[widget.objectName()]=widget.isChecked()
                elif isinstance(widget, QtWidgets.QTextEdit):
                    Obj[widget.objectName()]=widget.toPlainText()
                elif isinstance(widget, QtWidgets.QDoubleSpinBox) or isinstance(widget, QtWidgets.QLineEdit)  or isinstance(widget, QtWidgets.QSpinBox):
                    Obj[widget.objectName()]=widget.text()
                elif isinstance(widget, QtWidgets.QComboBox):
                    Obj[widget.objectName()]=widget.currentText()
        else:
            if keyname not in Obj.keys():
                Obj[keyname]={}
            for key in widget_dict.keys():
                widget = widget_dict[key]
                if key=='Frequency_1':
                    pass
                if isinstance(widget, QtWidgets.QPushButton):
                    Obj[keyname][widget.objectName()]=widget.isChecked()
                elif isinstance(widget, QtWidgets.QTextEdit):
                    Obj[keyname][widget.objectName()]=widget.toPlainText()
                elif isinstance(widget, QtWidgets.QDoubleSpinBox) or isinstance(widget, QtWidgets.QLineEdit)  or isinstance(widget, QtWidgets.QSpinBox):
                    Obj[keyname][widget.objectName()]=widget.text()
                elif isinstance(widget, QtWidgets.QComboBox):
                    Obj[keyname][widget.objectName()]=widget.currentText()
        return Obj

    def _OpenLast(self):
        self._Open(open_last=True)

    def _OpenLast_find_session(self,mouse_id):
        '''
            Returns the filepath of the last available session of this mouse
            Returns a tuple (Bool, str)
            Bool is True is a valid filepath was found, false otherwise
            If a valid filepath was found, then str contains the filepath 
        '''

        # Is this mouse on this computer?
        filepath = os.path.join(self.default_saveFolder,self.current_box)
        mouse_dirs = os.listdir(filepath)
        if mouse_id not in mouse_dirs:
            reply = QMessageBox.critical(self, 'Box {}, Load mouse'.format(self.box_letter),
                'Mouse ID {} does not have any saved sessions on this computer'.format(mouse_id),
                QMessageBox.Ok)
            logging.info('User input mouse id {}, which had no sessions on this computer'.format(mouse_id))
            return False, ''

        # Are there any session from this mouse?
        session_dir = os.path.join(self.default_saveFolder, self.current_box, mouse_id)
        sessions = os.listdir(session_dir)
        if len(sessions) == 0:
            reply = QMessageBox.critical(self, 'Box {}, Load mouse'.format(self.box_letter),
                'Mouse ID {} does not have any saved sessions on this computer'.format(mouse_id),
                QMessageBox.Ok)
            logging.info('User input mouse id {}, which had no sessions on this computer'.format(mouse_id))
            return False, ''

        # do any of the sessions have saved data? Grab the most recent
        for i in range(len(sessions)-1, -1, -1):
            s = sessions[i]
            if 'behavior_' in s:
                json_file = os.path.join(self.default_saveFolder,
                    self.current_box, mouse_id, s,'behavior',s.split('behavior_')[1]+'.json')
                if os.path.isfile(json_file):
                    date = s.split('_')[2]
                    session_date = date.split('-')[1]+'/'+date.split('-')[2]+'/'+date.split('-')[0]
                    reply = QMessageBox.information(self,
                        'Box {}, Please verify'.format(self.box_letter),
                        '<span style="color:purple;font-weight:bold">Mouse ID: {}</span><br>Last session: {}<br>Filename: {}'.format(mouse_id, session_date, s),
                        QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)
                    if reply == QMessageBox.Cancel:
                        logging.info('User hit cancel')
                        return False, ''
                    else:
                        return True, json_file

        # none of the sessions have saved data.  
        reply = QMessageBox.critical(self, 'Box {}, Load mouse'.format(self.box_letter),
            'Mouse ID {} does not have any saved sessions on this computer'.format(mouse_id),
            QMessageBox.Ok)
        logging.info('User input mouse id {}, which had no sessions on this computer'.format(mouse_id))
        return False, ''

    def _OpenNewMouse(self, mouse_id):
        '''
            Queries the user to start a new mouse
        '''
        reply = QMessageBox.question(self,
            'Box {}, Load mouse'.format(self.box_letter),
            'No data for mouse <span style="color:purple;font-weight:bold">{}</span>, start new mouse?'.format(mouse_id),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.No:
            logging.info('User declines to start new mouse: {}'.format(mouse_id))
            return reply

        # Set ID, clear weight information
        logging.info('User starting a new mouse: {}'.format(mouse_id))
        self.ID.setText(mouse_id)
        self.ID.returnPressed.emit()
        self.TargetRatio.setText('0.85')
        self.keyPressEvent(allow_reset=True)

    def _Open_getListOfMice(self):
        '''
            Returns a list of mice with data saved on this computer
        '''
        filepath = os.path.join(self.default_saveFolder,self.current_box)
        mouse_dirs = os.listdir(filepath)
        mice = []
        for m in mouse_dirs:
            session_dir = os.path.join(self.default_saveFolder, self.current_box, str(m))
            sessions = os.listdir(session_dir)
            if len(sessions) == 0 :
                continue
            for s in sessions:
                if 'behavior_' in s:
                    json_file = os.path.join(self.default_saveFolder,
                        self.current_box, str(m), s,'behavior',s.split('behavior_')[1]+'.json')
                    if os.path.isfile(json_file):
                        mice.append(m)
                        break
        return mice

    def _Open(self,open_last = False,input_file = ''):
        if input_file == '':
            # stop current session first
            self._StopCurrentSession()

            if open_last:
                mice = self._Open_getListOfMice()
                W = MouseSelectorDialog(self, mice)

                ok, mouse_id = (
                    W.exec_() == QtWidgets.QDialog.Accepted,
                    W.combo.currentText(),
                )

                if not ok:
                    logging.info('Quick load failed, user hit cancel or X')
                    return

                # Mouse ID not in list of mice:
                if mouse_id not in mice:
                    # figureout out new Mouse
                    logging.info('User entered the ID for a mouse with no data: {}'.format(mouse_id))
                    reply = self._OpenNewMouse(mouse_id)
                    if reply != QMessageBox.No:     # user pressed yes
                        self.NewSession.setChecked(True)
                        self._NewSession()
                    return

                # attempt to load last session from mouse
                good_load, fname = self._OpenLast_find_session(mouse_id)
                if not good_load:
                    logging.info('Quick load failed')
                    return
                logging.info('Quick load success: {}'.format(fname))
            else:
                # Open dialog box
                fname, _ = QFileDialog.getOpenFileName(self, 'Open file',
                    self.default_openFolder+'\\'+self.current_box,
                    "Behavior JSON files (*.json);;Behavior MAT files (*.mat);;JSON parameters (*_par.json)")
                logging.info('User selected: {}'.format(fname))
                if fname != '':
                    self.default_openFolder=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(fname))))

            self.fname=fname
        else:
            fname=input_file
            self.fname=fname
        if fname:
            # Start new session
            self.NewSession.setChecked(True)
            new_session = self._NewSession()
            if not new_session:
                return

            if fname.endswith('.mat'):
                Obj = loadmat(fname)
            elif fname.endswith('.json'):
                f = open (fname, "r")
                Obj = json.loads(f.read())
                f.close()
            self.Obj = Obj

            widget_dict={}
            dialogs = ['LaserCalibration_dialog', 'Opto_dialog', 'Camera_dialog','centralwidget','TrainingParameters']
            for dialog_name in dialogs:
                if hasattr(self, dialog_name):
                    widget_types = (QtWidgets.QPushButton, QtWidgets.QLineEdit, QtWidgets.QTextEdit,
                                    QtWidgets.QComboBox, QtWidgets.QDoubleSpinBox, QtWidgets.QSpinBox)
                    widget_dict.update({w.objectName(): w for w in getattr(self, dialog_name).findChildren(widget_types)})
            # Adding widgets starting with 'Laser1_power' and 'Laser2_power' to widget_keys to allow the second update.
            widget_keys=list(widget_dict.keys())
            for key in widget_dict.keys():
                if key.startswith('Laser1_power') or key.startswith('Laser2_power') or key.startswith('Location_') or key.startswith('Frequency_'):
                    widget_keys.append(key)
            try:
                for key in widget_keys:
                    try:
                        widget = widget_dict[key]
                        if widget.parent().objectName() in ['Optogenetics','Optogenetics_trial_parameters','SessionParameters']:
                            CurrentObj=Obj['Opto_dialog']
                        elif widget.parent().objectName()=='Camera':
                            CurrentObj=Obj['Camera_dialog']
                        elif widget.parent().objectName()=='CalibrationLaser':
                            CurrentObj=Obj['LaserCalibration_dialog']
                        elif widget.parent().objectName()=='MetaData':
                            CurrentObj=Obj['Metadata_dialog']
                        else:
                            CurrentObj=Obj.copy()
                    except Exception as e:
                        logging.error(traceback.format_exc())
                        continue
                    if key in CurrentObj:
                        # skip LeftValue, RightValue, GiveWaterL, GiveWaterR if WaterCalibrationResults is not empty as they will be set by the corresponding volume. 
                        if (key in ['LeftValue','RightValue','GiveWaterL','GiveWaterR']) and self.WaterCalibrationResults!={}:
                            continue
                        # skip some keys
                        if key in ['Start','warmup','SessionlistSpin','StartPreview','StartRecording']:
                            self.WeightAfter.setText('')
                            continue
                        widget = widget_dict[key]

                        # loading_parameters_type=0, get the last value of saved training parameters for each trial; loading_parameters_type=1, get the current value for single value data directly from the window. 
                        if 'TP_{}'.format(key) in CurrentObj:
                            value=np.array([CurrentObj['TP_'+key][-2]])
                            loading_parameters_type=0
                        else:
                            value=CurrentObj[key]
                            loading_parameters_type=1

                        if key in {'BaseWeight','TotalWater','TargetWeight','WeightAfter','SuggestedWater','TargetRatio'}:
                            self.BaseWeight.disconnect()
                            self.TargetRatio.disconnect()
                            self.WeightAfter.disconnect()
                            value=CurrentObj[key]
                            loading_parameters_type=1

                        # tag=0, get the last value for ndarray; tag=1, get the current value for single value data
                        if type(value)==bool:
                            loading_parameters_type=1
                        else:
                            if len(value)==0:
                                value=np.array([''], dtype='<U1')
                                loading_parameters_type=0
                        if type(value)==np.ndarray:
                            loading_parameters_type=0

                        if loading_parameters_type==0:
                            final_value=value[-1]
                        elif loading_parameters_type==1:
                            final_value=value

                        if isinstance(widget, QtWidgets.QLineEdit):
                            widget.setText(final_value)
                            if key in {'BaseWeight','TotalWater','TargetWeight','WeightAfter','SuggestedWater','TargetRatio'}:
                                self.TargetRatio.textChanged.connect(self._UpdateSuggestedWater)
                                self.WeightAfter.textChanged.connect(self._PostWeightChange)
                                self.BaseWeight.textChanged.connect(self._UpdateSuggestedWater)
                        elif isinstance(widget, QtWidgets.QComboBox):
                            index=widget.findText(final_value)
                            if key.startswith('Frequency_'):
                                condition=key.split('_')[1]
                                if CurrentObj['Protocol_'+condition] in ['Pulse']:
                                    widget.setEditable(True)
                                    widget.lineEdit().setText(final_value)
                                    continue

                            if index != -1:
                                # Alternating on/off for SessionStartWith if SessionAlternating is on
                                if key=='SessionStartWith' and 'Opto_dialog' in Obj:
                                    if 'SessionAlternating' in Obj['Opto_dialog'] and 'SessionWideControl' in Obj['Opto_dialog']:
                                        if Obj['Opto_dialog']['SessionAlternating']=='on' and Obj['OptogeneticsB']=='on' and Obj['Opto_dialog']['SessionWideControl']=='on':
                                            index=1-index
                                            widget.setCurrentIndex(index)
                                        else:
                                            widget.setCurrentIndex(index)
                                    else:
                                        widget.setCurrentIndex(index)
                                else:
                                    widget.setCurrentIndex(index)
                        elif isinstance(widget, QtWidgets.QDoubleSpinBox):
                            widget.setValue(float(final_value))
                        elif isinstance(widget, QtWidgets.QSpinBox):
                            widget.setValue(int(final_value))
                        elif isinstance(widget, QtWidgets.QTextEdit):
                            widget.setText(final_value)
                        elif isinstance(widget, QtWidgets.QPushButton):
                            widget.setChecked(bool(final_value))
                            if key=='AutoReward':
                                self._AutoReward()
                            if key=='NextBlock':
                                self._NextBlock()
                    else:
                        widget = widget_dict[key]
                        if not (isinstance(widget, QtWidgets.QComboBox) or isinstance(widget, QtWidgets.QPushButton)):
                            widget.clear()
            except Exception as e:
                # Catch the exception and print error information
                logging.error(traceback.format_exc())
            try:
                # visualization when loading the data
                self._LoadVisualization()
            except Exception as e:
                # Catch the exception and print error information
                logging.error(traceback.format_exc())
                # delete GeneratedTrials
                del self.GeneratedTrials
            # show basic information
            if self.default_ui=='ForagingGUI.ui':
                if 'info_task' in Obj:
                    self.label_info_task.setText(Obj['info_task'])
                if 'info_performance_others' in Obj:
                    self.label_info_performance_others.setText(Obj['info_performance_others'])
                if 'info_performance_essential_1' in Obj:
                    self.label_info_performance_essential_1.setText(Obj['info_performance_essential_1'])
                if 'info_performance_essential_2' in Obj:
                    self.label_info_performance_essential_2.setText(Obj['info_performance_essential_2'])
            elif self.default_ui=='ForagingGUI_Ephys.ui':
                if 'Other_inforTitle' in Obj:
                    self.infor.setTitle(Obj['Other_inforTitle'])
                if 'Other_BasicTitle' in Obj:
                    self.Basic.setTitle(Obj['Other_BasicTitle'])
                if 'Other_BasicText' in Obj:
                    self.ShowBasic.setText(Obj['Other_BasicText'])

            #Set newscale position to last position
            if 'B_NewscalePositions' in Obj:
                try:
                    last_positions=Obj['B_NewscalePositions'][-1]
                except:
                    pass
                if hasattr(self,'current_stage'):
                    try:
                        self.StageStop.click
                        self.current_stage.move_absolute_3d(float(last_positions[0]),float(last_positions[1]),float(last_positions[2]))
                        self._UpdatePosition((float(last_positions[0]),float(last_positions[1]),float(last_positions[2])),(0,0,0))
                    except Exception as e:
                        logging.error(traceback.format_exc())
            else:
                pass

            # load metadata to the metadata dialog
            if 'meta_data_dialog' in Obj:
                if 'session_metadata' in Obj['meta_data_dialog']:
                    self.Metadata_dialog.meta_data['session_metadata'] = Obj['meta_data_dialog']['session_metadata']
                self.Metadata_dialog._update_metadata()

            # show session list related to that animal
            tag=self._show_sessions()
            if tag!=0:
                fname_session_folder=os.path.basename(os.path.dirname(os.path.dirname(fname)))
                Ind=self.Sessionlist.findText(fname_session_folder)
                self._connect_Sessionlist(connect=False)
                self.Sessionlist.setCurrentIndex(Ind)
                self.SessionlistSpin.setValue(Ind+1)
                self._connect_Sessionlist(connect=True)
            # check dropping frames
            self.to_check_drop_frames=1
            self._check_drop_frames(save_tag=0)
        else:
            self.NewSession.setDisabled(False)
        self.StartExcitation.setChecked(False)
        self.keyPressEvent() # Accept all updates
        self.load_tag=1
        self.ID.returnPressed.emit() # Mimic the return press event to auto-engage AutoTrain

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
                except Exception as e:
                    logging.error(traceback.format_exc())
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

        self.PlotM=PlotV(win=self,GeneratedTrials=self.GeneratedTrials,width=5, height=4)
        self.PlotM.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        layout=self.Visualization.layout()
        if layout is not None:
            for i in reversed(range(layout.count())):
                layout.itemAt(i).widget().setParent(None)
            layout.invalidate()
        layout=self.Visualization.layout()
        if layout is None:
            layout=QGridLayout(self.Visualization)
        toolbar = NavigationToolbar(self.PlotM, self)
        toolbar.setMaximumHeight(20)
        toolbar.setMaximumWidth(300)
        layout.addWidget(toolbar, 0, 0, 1, 2)
        layout.addWidget(self.PlotM, 1, 0)
        layout.addWidget(self.bias_indicator, 1, 1)
        self.bias_indicator.clear()
        self.PlotM._Update(GeneratedTrials=self.GeneratedTrials)
        self.PlotLick._Update(GeneratedTrials=self.GeneratedTrials)

    def _Clear(self):
        # Stop current session first
        self._StopCurrentSession()

        # Verify user wants to clear parameters
        if self.unsaved_data:
            reply = QMessageBox.critical(self,
                'Box {}, Clear parameters:'.format(self.box_letter),
                'Unsaved data exists! Do you want to clear training parameters?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        # post weight not entered and session ran and new session button was clicked
        elif self.WeightAfter.text() == '' and self.session_run and not self.unsaved_data:
            reply = QMessageBox.critical(self,
                                         'Box {}, Foraging Close'.format(self.box_letter),
                                         'Post weight appears to not be entered. Do you want to clear training parameters?',
                                         QMessageBox.Yes, QMessageBox.No)
        else:
            reply = QMessageBox.question(self,
                'Box {}, Clear parameters:'.format(self.box_letter),
                'Do you want to clear training parameters?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        # If yes, clear parameters
        if reply == QMessageBox.Yes:
            for child in self.TrainingParameters.findChildren(QtWidgets.QLineEdit)+ self.centralwidget.findChildren(QtWidgets.QLineEdit):
                if child.isEnabled():
                    child.clear()
        else:
            logging.info('Clearing declined')
            return

    def _StartFIP(self):
        self.StartFIP.setChecked(False)

        if self.Teensy_COM == '':
            logging.warning('No Teensy COM configured for this box, cannot start FIP workflow',
                            extra={'tags': [self.warning_log_tag]})
            msg = 'No Teensy COM configured for this box, cannot start FIP workflow'
            reply = QMessageBox.information(self,
                'Box {}, StartFIP'.format(self.box_letter), msg, QMessageBox.Ok )
            return

        if self.FIP_workflow_path == "":
            logging.warning('No FIP workflow path defined in ForagingSettings.json')
            msg = 'FIP workflow path not defined, cannot start FIP workflow'
            reply = QMessageBox.information(self,
                'Box {}, StartFIP'.format(self.box_letter), msg, QMessageBox.Ok )
            return

        if self.FIP_started:
            reply = QMessageBox.question(self,
                'Box {}, Start FIP workflow:'.format(self.box_letter),
                'FIP workflow has already been started. Start again?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No )
            if reply == QMessageBox.No:
                logging.warning('FIP workflow already started, user declines to restart')
                return
            else:
                logging.warning('FIP workflow already started, user restarts')

        # Start logging
        self.Ot_log_folder=self._restartlogging()

        # Start the FIP workflow
        try:
            CWD=os.path.dirname(self.FIP_workflow_path)
            logging.info('Starting FIP workflow in directory: {}'.format(CWD))
            folder_path = ' -p session="{}"'.format(self.SessionFolder)
            camera = ' -p RunCamera="{}"'.format(not self.Camera_dialog.StartRecording.isChecked())
            process = subprocess.Popen(self.bonsai_path+' '+self.FIP_workflow_path+folder_path+camera+' --start',cwd=CWD,shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            threading.Thread(target=log_subprocess_output, args=(process,'FIP',)).start()
            self.FIP_started=True
        except Exception as e:
            logging.error(e)
            reply = QMessageBox.information(self,
               'Box {}, Start FIP workflow:'.format(self.box_letter),
               'Could not start FIP workflow: {}'.format(e),
               QMessageBox.Ok )

    def _StartExcitation(self):

        if self.Teensy_COM == '':
            logging.warning('No Teensy COM configured for this box, cannot start excitation',
                            extra={'tags': [self.warning_log_tag]})
            msg = 'No Teensy COM configured for this box, cannot start excitation'
            reply = QMessageBox.information(self,
                'Box {}, StartExcitation'.format(self.box_letter), msg, QMessageBox.Ok )
            self.StartExcitation.setChecked(False)
            self.StartExcitation.setStyleSheet("background-color : none")
            return 0

        if self.StartExcitation.isChecked():
            logging.info('StartExcitation is checked, photometry mode: {}'.format(self.FIPMode.currentText()))
            self.StartExcitation.setStyleSheet("background-color : green;")
            try:
                ser = serial.Serial(self.Teensy_COM, 9600, timeout=1)
                # Trigger Teensy with the above specified exp mode
                if self.FIPMode.currentText() == "Normal":
                    ser.write(b'c')
                elif self.FIPMode.currentText() == "Axon":
                    ser.write(b'e')
                ser.close()
                logging.info('Started FIP excitation', extra={'tags': [self.warning_log_tag]})
            except Exception as e:
                logging.error(traceback.format_exc())
                logging.warning('Error: starting excitation!', extra={'tags': [self.warning_log_tag]})
                reply = QMessageBox.critical(self, 'Box {}, Start excitation:'.format(self.box_letter), 'error when starting excitation: {}'.format(e), QMessageBox.Ok)
                self.StartExcitation.setChecked(False)
                self.StartExcitation.setStyleSheet("background-color : none")
                return 0
            else:
                self.fiber_photometry_start_time = str(datetime.now())

        else:
            logging.info('StartExcitation is unchecked')
            self.StartExcitation.setStyleSheet("background-color : none")
            try:
                ser = serial.Serial(self.Teensy_COM, 9600, timeout=1)
                # Trigger Teensy with the above specified exp mode
                ser.write(b's')
                ser.close()
                logging.info('Stopped FIP excitation', extra={'tags': [self.warning_log_tag]})
            except Exception as e:
                logging.error(traceback.format_exc())
                logging.warning('Error stopping excitation!', extra={'tags': [self.warning_log_tag]})
                reply = QMessageBox.critical(self, 'Box {}, Start excitation:'.format(self.box_letter), 'error when stopping excitation: {}'.format(e), QMessageBox.Ok)
                return 0
            else:
                self.fiber_photometry_end_time = str(datetime.now())

        return 1

    def _StartBleaching(self):

        if self.Teensy_COM == '':
            logging.warning('No Teensy COM configured for this box, cannot start bleaching',
                            extra={'tags': [self.warning_log_tag]})
            msg = 'No Teensy COM configured for this box, cannot start bleaching'
            reply = QMessageBox.information(self,
                'Box {}, StartBleaching'.format(self.box_letter), msg, QMessageBox.Ok )
            self.StartBleaching.setChecked(False)
            self.StartBleaching.setStyleSheet("background-color : none")
            return

        if self.StartBleaching.isChecked():
            # Check if trials have stopped
            if self.ANewTrial==0:
                # Alert User
                reply = QMessageBox.critical(self, 'Box {}, Start bleaching:'.format(self.box_letter),
                    'Cannot start photobleaching, because trials are in progress', QMessageBox.Ok)

                # reset GUI button
                self.StartBleaching.setChecked(False)
                return

            # Verify mouse is disconnected
            reply = QMessageBox.question(self, 'Box {}, Start bleaching:'.format(self.box_letter),
                    'Starting photobleaching, have the cables been disconnected from the mouse?',QMessageBox.Yes, QMessageBox.No )
            if reply == QMessageBox.No:
                # reset GUI button
                self.StartBleaching.setChecked(False)
                return

            # Start bleaching
            self.StartBleaching.setStyleSheet("background-color : green;")
            try:
                ser = serial.Serial(self.Teensy_COM, 9600, timeout=1)
                # Trigger Teensy with the above specified exp mode
                ser.write(b'd')
                ser.close()
                logging.info('Start bleaching!', extra={'tags': [self.warning_log_tag]})
            except Exception as e:
                logging.error(traceback.format_exc())

                # Alert user
                logging.warning('Error: start bleaching!', extra={'tags': [self.warning_log_tag]})
                reply = QMessageBox.critical(self, 'Box {}, Start bleaching:'.format(self.box_letter),
                    'Cannot start photobleaching: {}'.format(str(e)), QMessageBox.Ok)

                # Reset GUI button
                self.StartBleaching.setStyleSheet("background-color : none")
                self.StartBleaching.setChecked(False)
            else:
                # Bleaching continues until user stops
                msgbox = QMessageBox()
                msgbox.setWindowTitle('Box {}, bleaching:'.format(self.box_letter))
                msgbox.setText('Photobleaching in progress, do not close the GUI.')
                msgbox.setStandardButtons(QMessageBox.Ok)
                button = msgbox.button(QMessageBox.Ok)
                button.setText('Stop bleaching')
                bttn = msgbox.exec_()

                # Stop Bleaching
                self.StartBleaching.setChecked(False)
                self._StartBleaching()
        else:
            self.StartBleaching.setStyleSheet("background-color : none")
            try:
                ser = serial.Serial(self.Teensy_COM, 9600, timeout=1)
                # Trigger Teensy with the above specified exp mode
                ser.write(b's')
                ser.close()
            except Exception as e:
                logging.error(traceback.format_exc())
                logging.warning('Error: stop bleaching!')

    def _StopPhotometry(self,closing=False):
        '''
            Stop either bleaching or photometry
        '''
        if self.Teensy_COM == '':
            return
        logging.info('Checking that photometry is not running')
        FIP_was_running=self.FIP_started
        try:
            ser = serial.Serial(self.Teensy_COM, 9600, timeout=1)
            # Trigger Teensy with the above specified exp mode
            ser.write(b's')
            ser.close()
        except Exception as e:
            logging.info('Could not stop photometry, most likely this means photometry is not running: '+str(e))
        else:
            logging.info('Photometry excitation stopped')
        finally:
            # Reset all GUI buttons
            self.StartBleaching.setStyleSheet("background-color : none")
            self.StartExcitation.setStyleSheet("background-color : none")
            self.StartBleaching.setChecked(False)
            self.StartExcitation.setChecked(False)
            self.FIP_started=False

        if (FIP_was_running)&(not closing):
            reply = QMessageBox.critical(self,
                'Box {}, New Session:'.format(self.box_letter),
                'Please restart the FIP workflow',
                QMessageBox.Ok)

    def _AutoReward(self):
        if self.AutoReward.isChecked():
            self.AutoReward.setStyleSheet("background-color : green;")
            self.AutoReward.setText('Auto water On')
            for widget in ['AutoWaterType', 'Multiplier', 'Unrewarded', 'Ignored']:
                getattr(self, widget).setEnabled(True)
        else:
            self.AutoReward.setStyleSheet("background-color : none")
            self.AutoReward.setText('Auto water Off')
            for widget in ['AutoWaterType', 'Multiplier', 'Unrewarded', 'Ignored']:
                getattr(self, widget).setEnabled(False)

    def _NextBlock(self):
        if self.NextBlock.isChecked():
            self.NextBlock.setStyleSheet("background-color : green;")
        else:
            self.NextBlock.setStyleSheet("background-color : none")

    def _stop_camera(self):
        '''Stop the camera if it is running'''
        if self.Camera_dialog.StartRecording.isChecked():
            self.Camera_dialog.StartRecording.setChecked(False)

    def _stop_logging(self):
        '''Stop the logging'''
        self.Camera_dialog.StartPreview.setEnabled(True)
        self.ID.setEnabled(True)
        self.Load.setEnabled(True)
        try:
            self.Channel.StopLogging('s')
            self.logging_type=-1 # logging has stopped
        except Exception as e:
            logging.warning('Bonsai connection is closed')
            logging.warning('Lost bonsai connection', extra={'tags': [self.warning_log_tag]})
            self.InitializeBonsaiSuccessfully=0

    def _NewSession(self):

        logging.info('New Session pressed')
        # If we have unsaved data, prompt to save
        if (self.ToInitializeVisual==0) and (self.unsaved_data):
            reply = QMessageBox.critical(self,
                'Box {}, New Session:'.format(self.box_letter),
                'Start new session without saving?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                self.NewSession.setStyleSheet("background-color : none")
                self.NewSession.setChecked(False)
                logging.info('New Session declined')
                return False
        # post weight not entered and session ran and new session button was clicked
        elif self.WeightAfter.text() == '' and self.session_run and not self.unsaved_data and self.NewSession.isChecked():
            reply = QMessageBox.critical(self,
                                         'Box {}, Foraging Close'.format(self.box_letter),
                                         'Post weight appears to not be entered. Start new session without entering and saving?',
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                self.NewSession.setStyleSheet("background-color : none")
                self.NewSession.setChecked(False)
                logging.info('New Session declined')
                return False

        # stop the camera 
        self._stop_camera()

        # Reset logging
        self._stop_logging()

        # reset if session has been run
        if self.NewSession.isChecked():
            logging.info('Resetting session run flag')
            self.session_run = False
            self.BaseWeight.setText('')
            self.WeightAfter.setText('')

        # Reset GUI visuals
        self.Save.setStyleSheet("color:black;background-color:None;")
        self.NewSession.setStyleSheet("background-color : green;")
        self.NewSession.setChecked(False)
        self.Start.setStyleSheet("background-color : none")
        self.Start.setChecked(False)
        self.Start.setDisabled(False)
        self.TotalWaterWarning.setText('')
        self._set_metadata_enabled(True)

        self._ConnectBonsai()
        if self.InitializeBonsaiSuccessfully == 0:
            logging.warning('Lost bonsai connection', extra={'tags': [self.warning_log_tag]})

        # Reset state variables
        self._StopPhotometry() # Make sure photoexcitation is stopped
        self.StartANewSession=1
        self.CreateNewFolder=1
        self.PhotometryRun=0

        self.unsaved_data=False
        self.ManualWaterVolume=[0,0]
        if hasattr(self, 'fiber_photometry_start_time'):
            del self.fiber_photometry_start_time
        if hasattr(self, 'fiber_photometry_end_time'):
            del self.fiber_photometry_end_time

        # Clear Plots
        if hasattr(self, 'PlotM') and self.clear_figure_after_save:
            self.bias_indicator.clear()
            self.PlotM._Update(GeneratedTrials=None,Channel=None)

        # Add note to log
        logging.info('New Session complete')

        # if session log handler is not none, stop logging for previous session
        if self.session_log_handler is not None:
            self.end_session_log()

        return True

    def _AskSave(self):
        reply = QMessageBox.question(self, 'Box {}, New Session:'.format(self.box_letter), 'Do you want to save the current result?',QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self._Save()
            logging.info('The current session was saved')
        elif reply == QMessageBox.No:
            pass
        else:
            pass

    def _StopCurrentSession(self):

        logging.info('Stopping current trials')

        # stop the current session
        self.Start.setStyleSheet("background-color : none")
        self.Start.setChecked(False)

        # waiting for the finish of the last trial
        start_time = time.time()
        stall_iteration = 1
        stall_duration = 5*60
        if self.ANewTrial==0:
            logging.warning('Waiting for the finish of the last trial!', extra={'tags': [self.warning_log_tag]})
            while 1:
                QApplication.processEvents()
                if self.ANewTrial==1:
                    break
                elif (time.time() - start_time) > stall_duration*stall_iteration:
                    elapsed_time = int(np.floor(stall_duration*stall_iteration/60))
                    message = '{} minutes have elapsed since trial stopped was initiated. Force stop?'.format(elapsed_time)
                    reply = QMessageBox.question(self,'Box {}, StopCurrentSession'.format(self.box_letter),message,QMessageBox.Yes|QMessageBox.No, QMessageBox.Yes)
                    if reply == QMessageBox.Yes:
                        logging.error('trial stalled {} minutes, user force stopped trials'.format(elapsed_time))
                        self.ANewTrial=1
                        break
                    else:
                        stall_iteration+=1
                        logging.info('trial stalled {} minutes, user did not force stopped trials'.format(elapsed_time))

    def _thread_complete(self):
        '''complete of a trial'''
        if self.NewTrialRewardOrder==0:
            self.GeneratedTrials._GenerateATrial(self.Channel4)
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

    def _thread_complete6(self):
        '''complete of save data'''
        self.previous_backup_completed=1

    def _thread_complete_timer(self):
        '''complete of _Timer'''
        if not self.ignore_timer:
            self.finish_Timer=1
            logging.info('Finished photometry baseline timer')

    def _update_photometery_timer(self,time):
        '''
            Updates photometry baseline timer
        '''
        minutes = int(np.floor(time/60))
        seconds = np.remainder(time,60)
        if len(str(seconds)) == 1:
            seconds = '0{}'.format(seconds)
        if not self.ignore_timer:
            self.photometry_timer_label.setText('Running photometry baseline: {}:{}'.format(minutes,seconds))

    def _set_metadata_enabled(self, enable: bool):
        '''Enable or disable metadata fields'''
        self.ID.setEnabled(enable)
        self.Experimenter.setEnabled(enable)

    def _set_default_project(self):
        '''Set default project information'''
        project_name = 'Behavior Platform'
        logging.info('Setting Project name: {}'.format('Behavior Platform'))
        projects = [self.Metadata_dialog.ProjectName.itemText(i)
                    for i in range(self.Metadata_dialog.ProjectName.count())]
        index = np.where(np.array(projects) == 'Behavior Platform')[0]
        if len(index) > 0:
            index = index[0]
            self.Metadata_dialog.ProjectName.setCurrentIndex(index)
            self.Metadata_dialog._show_project_info()
        else:
            project_info = {
                'Funding Institution': ['Allen Institute'],
                'Grant Number': ['nan'],
                'Investigators': ['Jeremiah Cohen'],
                'Fundee': ['nan'],
            }
            self.Metadata_dialog.project_info = project_info
            self.Metadata_dialog.ProjectName.addItems([project_name])
        return project_name

    def _Start(self):
        '''start trial loop'''

        # set the load tag to zero
        self.load_tag=0

        # post weight not entered and session ran
        if self.WeightAfter.text() == '' and self.session_run and not self.unsaved_data:
            reply = QMessageBox.critical(self,
                                         'Box {}, Foraging Close'.format(self.box_letter),
                                         'Post weight appears to not be entered. Do you want to start a new session?',
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        # empty the laser calibration
        self.Opto_dialog.laser_1_calibration_voltage.setText('')
        self.Opto_dialog.laser_2_calibration_voltage.setText('')
        self.Opto_dialog.laser_1_calibration_power.setText('')
        self.Opto_dialog.laser_2_calibration_power.setText('')

        # Check for Bonsai connection
        self._ConnectBonsai()
        if self.InitializeBonsaiSuccessfully==0:
            logging.info('Start button pressed, but bonsai not connected')
            self.Start.setChecked(False)
            self.Start.setStyleSheet('background-color:none;')
            return

        # set the flag to check drop frames
        self.to_check_drop_frames=1

        # clear the session list
        self._connect_Sessionlist(connect=False)
        self.Sessionlist.clear()
        self.SessionlistSpin.setValue(1)
        self._connect_Sessionlist(connect=True)
        self.SessionlistSpin.setEnabled(False)
        self.Sessionlist.setEnabled(False)

        # Clear warnings
        self.NewSession.setDisabled(False)
        # Toggle button colors
        if self.Start.isChecked():
            logging.info('Start button pressed: starting trial loop')
            self.keyPressEvent()

            # check if FIP setting match schedule
            mouse_id = self.ID.text()
            if hasattr(self, 'schedule') and mouse_id in self.schedule['Mouse ID'].values and mouse_id not in ['0','1','2','3','4','5','6','7','8','9','10'] : # skip if test mouse or mouse isn't in schedule or
                FIP_Mode = self._GetInfoFromSchedule(mouse_id, 'FIP Mode')
                FIP_is_nan = (isinstance(FIP_Mode, float) and math.isnan(FIP_Mode)) or FIP_Mode is None
                if FIP_is_nan and self.PhotometryB.currentText()=='on':
                    reply = QMessageBox.critical(self,
                                                 'Box {}, Start'.format(self.box_letter),
                                                 'Photometry is set to "on", but the FIP Mode is not in schedule. Continue anyways?',
                                                 QMessageBox.Yes | QMessageBox.No,)
                    if reply == QMessageBox.No:
                        self.Start.setChecked(False)
                        logging.info('User declines starting session due to conflicting FIP information')
                        return
                    else:
                        # Allow the session to continue, but log error
                        logging.error('Starting session with conflicting FIP information: mouse {}, FIP on, but not in schedule'.format(mouse_id))
                elif not FIP_is_nan and self.PhotometryB.currentText()=='off':
                    reply = QMessageBox.critical(self,
                                                 'Box {}, Start'.format(self.box_letter),
                                                 f'Photometry is set to "off" but schedule indicate '
                                                 f'FIP Mode is {FIP_Mode}. Continue anyways?',
                                                 QMessageBox.Yes | QMessageBox.No,)
                    if reply == QMessageBox.No:
                        self.Start.setChecked(False)
                        logging.info('User declines starting session due to conflicting FIP information')
                        return
                    else:
                        # Allow the session to continue, but log error
                        logging.error('Starting session with conflicting FIP information: mouse {}, FIP off, but schedule lists FIP {}'.format(mouse_id, FIP_Mode))

                elif not FIP_is_nan and FIP_Mode != self.FIPMode.currentText() and self.PhotometryB.currentText()=='on':
                    reply = QMessageBox.critical(self,
                                                 'Box {}, Start'.format(self.box_letter),
                                                 f'FIP Mode is set to {self.FIPMode.currentText()} but schedule indicate '
                                                 f'FIP Mode is {FIP_Mode}. Continue anyways?',
                                                 QMessageBox.Yes | QMessageBox.No,)
                    if reply == QMessageBox.No:
                        self.Start.setChecked(False)
                        logging.info('User declines starting session due to conflicting FIP information')
                        return
                    else:
                        # Allow the session to continue, but log error
                        logging.error('Starting session with conflicting FIP information: mouse {}, FIP mode {}, schedule lists {}'.format(mouse_id, self.FIPMode.currentText(), FIP_Mode))

            if self.StartANewSession == 0 :
                reply = QMessageBox.question(self,
                    'Box {}, Start'.format(self.box_letter),
                    'Continue current session?',
                    QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.No:
                    self.Start.setChecked(False)
                    logging.info('User declines continuation of session')
                    return

            # check experimenter name
            reply = QMessageBox.critical(self,
                'Box {}, Start'.format(self.box_letter),
                f'The experimenter is <span style="{self.default_text_color}">{self.Experimenter.text()}</span>. Is this correct?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                self.Start.setChecked(False)
                logging.info('User declines using default name')
                return
            logging.info('Starting session, with experimenter: {}'.format(self.Experimenter.text()))

            # check repo status
            if (self.current_branch not in ['main','production_testing']) & (self.ID.text() not in ['0','1','2','3','4','5','6','7','8','9','10']):
                # Prompt user over off-pipeline branch
                reply = QMessageBox.critical(self,
                    'Box {}, Start'.format(self.box_letter),
                    'Running on branch <span style="color:purple;font-weight:bold">{}</span>, continue anyways?'.format(self.current_branch),
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    # Stop session
                    self.Start.setChecked(False)
                    logging.info('User declines starting session on branch: {}'.format(self.current_branch))
                    return
                else:
                    # Allow the session to continue, but log error
                    logging.error('Starting session on branch: {}'.format(self.current_branch))

            # Check for untracked local changes
            if self.repo_dirty_flag & (self.ID.text() not in ['0','1','2','3','4','5','6','7','8','9','10']):
                # prompt user over untracked local changes
                reply = QMessageBox.critical(self,
                    'Box {}, Start'.format(self.box_letter),
                    'Local repository has untracked changes, continue anyways?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    # Stop session
                    self.Start.setChecked(False)
                    logging.info('User declines starting session with untracked changes')
                    return
                else:
                    # Allow the session to continue, but log error
                    logging.error('Starting session with untracked local changes: {}'.format(self.dirty_files))
            elif self.repo_dirty_flag is None:
                logging.error('Could not check for untracked local changes')

            if self.PhotometryB.currentText()=='on' and (not self.FIP_started):
                reply = QMessageBox.critical(self,
                    'Box {}, Start'.format(self.box_letter),
                    'Photometry is set to "on", but the FIP workflow has not been started',
                    QMessageBox.Ok)
                self.Start.setChecked(False)
                logging.info('Cannot start session without starting FIP workflow')
                return

            # Check if photometry excitation is running or not
            if self.PhotometryB.currentText()=='on' and (not self.StartExcitation.isChecked()):
                logging.warning('photometry is set to "on", but excitation is not running')

                reply = QMessageBox.question(self,
                    'Box {}, Start'.format(self.box_letter),
                    'Photometry is set to "on", but excitation is not running. Start excitation now?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes:
                    self.StartExcitation.setChecked(True)
                    logging.info('User selected to start excitation')
                    started = self._StartExcitation()
                    if started == 0:
                        reply = QMessageBox.critical(self,
                            'Box {}, Start'.format(self.box_letter),
                            'Could not start excitation, therefore cannot start the session',
                            QMessageBox.Ok)
                        logging.info('could not start session, due to failure to start excitation')
                        self.Start.setChecked(False)
                        return
                else:
                    logging.info('User selected not to start excitation')
                    self.Start.setChecked(False)
                    return

            # empty post weight after pass through checks in case user cancels run
            self.WeightAfter.setText('')

            # change button color and mark the state change
            self.Start.setStyleSheet("background-color : green;")
            self.NewSession.setStyleSheet("background-color : none")
            self.NewSession.setChecked(False)
            # disable metadata fields
            self._set_metadata_enabled(False)

            # generate an upload manifest when a session has been produced if slot is not already connected
            if self.upload_manifest_slot is None:
                logging.debug('Connecting sessionGenerated to _generate_upload_manifest')
                self.upload_manifest_slot = self.sessionGenerated.connect(self._generate_upload_manifest)

            # Set IACUC protocol in metadata based on schedule
            protocol = self._GetInfoFromSchedule(mouse_id, 'Protocol')
            if protocol is not None:
                self.Metadata_dialog.meta_data['session_metadata']['IACUCProtocol'] = str(int(protocol))
                self.Metadata_dialog._update_metadata(
                    update_rig_metadata=False,
                    update_session_metadata=True
                )
                logging.info('Setting IACUC Protocol: {}'.format(protocol))

            # Set Project Name in metadata based on schedule
            add_default=True
            project_name = self._GetInfoFromSchedule(mouse_id, 'Project Name')
            if project_name is not None:
                projects = [self.Metadata_dialog.ProjectName.itemText(i)
                            for i in range(self.Metadata_dialog.ProjectName.count())]
                index = np.where(np.array(projects) == project_name)[0]
                if len(index) > 0:
                    index = index[0]
                    self.Metadata_dialog.ProjectName.setCurrentIndex(index)
                    self.Metadata_dialog._show_project_info()
                    logging.info('Setting Project name: {}'.format(project_name))
                    add_default = False

            if self.add_default_project_name and add_default:
                project_name=self._set_default_project()

            self.project_name = project_name
            self.session_run = True   # session has been started

            self.keyPressEvent(allow_reset=True)

        else:
            # Prompt user to confirm stopping trials
            reply = QMessageBox.question(self,
                'Box {}, Start'.format(self.box_letter),
                'Stop current session?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                # End trials
                logging.info('Start button pressed: ending trial loop')
                self.Start.setStyleSheet("background-color : none")
            else:
                # Continue trials
                logging.info('Start button pressed: user continued session')
                self.Start.setChecked(True)
                return
            # If the photometry timer is running, stop it
            if self.finish_Timer==0:
                self.ignore_timer=True
                self.PhotometryRun=0
                logging.info('canceling photometry baseline timer')
                if hasattr(self, 'workertimer'):
                    # Stop the worker, this has a 1 second delay before taking effect
                    # so we set the text to get ignored as well
                    self.workertimer._stop()

            # fill out GenerateTrials B_Bias
            last_bias = self.GeneratedTrials.B_Bias[-1]
            b_bias_len = len(self.GeneratedTrials.B_Bias)
            self.GeneratedTrials.B_Bias += [last_bias]*((self.GeneratedTrials.B_CurrentTrialN+1)-b_bias_len)

        if (self.StartANewSession == 1) and (self.ANewTrial == 0):
            # If we are starting a new session, we should wait for the last trial to finish
            self._StopCurrentSession()
        # to see if we should start a new session
        if self.StartANewSession==1 and self.ANewTrial==1:
            # generate a new session id
            self.ManualWaterVolume=[0,0]
            # start a new logging
            try:
                # Do not start a new session if the camera is already open, this means the session log has been started or the existing session has not been completed.
                if (not (self.Camera_dialog.StartRecording.isChecked() and self.Camera_dialog.AutoControl.currentText()=='No')) and (not self.FIP_started):
                    # Turn off the camera recording
                    self.Camera_dialog.StartRecording.setChecked(False)
                    # Turn off the preview if it is on and the autocontrol is on, which can make sure the trigger is off before starting the logging. 
                    if self.Camera_dialog.AutoControl.currentText()=='Yes' and self.Camera_dialog.StartPreview.isChecked():
                        self.Camera_dialog.StartPreview.setChecked(False)
                        # sleep for 1 second to make sure the trigger is off
                        time.sleep(1)
                    self.Ot_log_folder=self._restartlogging()
            except Exception as e:
                if 'ConnectionAbortedError' in str(e):
                    logging.info('lost bonsai connection: restartlogging()')
                    logging.warning('Lost bonsai connection', extra={'tags': [self.warning_log_tag]})
                    self.Start.setChecked(False)
                    self.Start.setStyleSheet("background-color : none")
                    self.InitializeBonsaiSuccessfully=0
                    reply = QMessageBox.question(self, 'Box {}, Start'.format(self.box_letter), 'Cannot connect to Bonsai. Attempt reconnection?',QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                    if reply == QMessageBox.Yes:
                        self._ReconnectBonsai()
                        logging.info('User selected reconnect bonsai')
                    else:
                        logging.info('User selected not to reconnect bonsai')
                    return
                else:
                    print('type: {}, text:{}'.format(type(e),e))
                    raise
            # start the camera during the begginning of each session
            if self.Camera_dialog.AutoControl.currentText()=='Yes':
                # camera will start recording
                self.Camera_dialog.StartRecording.setChecked(True)
            self.SessionStartTime=datetime.now()
            self.Other_SessionStartTime=str(self.SessionStartTime) # for saving
            GeneratedTrials=GenerateTrials(self)
            self.GeneratedTrials=GeneratedTrials
            self.StartANewSession=0
            PlotM=PlotV(win=self,GeneratedTrials=GeneratedTrials,width=5, height=4)
            #PlotM.finish=1
            self.PlotM=PlotM
            #generate the first trial outside the loop, only for new session
            self.ToReceiveLicks=1
            self.ToUpdateFigure=1
            self.ToGenerateATrial=1
            self.ToInitializeVisual=1
            GeneratedTrials._GenerateATrial(self.Channel4)
            # delete licks from the previous session
            GeneratedTrials._DeletePreviousLicks(self.Channel2)

            if self.Start.isChecked():
                # if session log handler is not none, stop logging for previous session
                if self.session_log_handler is not None:
                    self.end_session_log()
                self.log_session()  # start log for new session

        else:
            GeneratedTrials=self.GeneratedTrials

        if self.ToInitializeVisual==1: # only run once
            self.PlotM=PlotM
            self.PlotM.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
            layout=self.Visualization.layout()
            if layout is not None:
                for i in reversed(range(layout.count())):
                    layout.itemAt(i).widget().setParent(None)
                layout.invalidate()
            if layout is None:
                layout=QGridLayout(self.Visualization)
            toolbar = NavigationToolbar(PlotM, self)
            toolbar.setMaximumHeight(20)
            toolbar.setMaximumWidth(300)
            layout.addWidget(toolbar, 0, 0, 1, 2)
            layout.addWidget(PlotM, 1, 0)
            layout.addWidget(self.bias_indicator, 1, 1)
            self.ToInitializeVisual=0
            # clear bias indicator graph
            self.bias_indicator.clear()
            # create workers
            worker1 = Worker(GeneratedTrials._GetAnimalResponse,self.Channel,self.Channel3,self.Channel4)
            worker1.signals.finished.connect(self._thread_complete)
            workerLick = Worker(GeneratedTrials._get_irregular_timestamp,self.Channel2)
            workerLick.signals.finished.connect(self._thread_complete2)
            workerPlot = Worker(PlotM._Update,GeneratedTrials=GeneratedTrials,Channel=self.Channel2)
            workerPlot.signals.finished.connect(self._thread_complete3)
            workerGenerateAtrial = Worker(GeneratedTrials._GenerateATrial,self.Channel4)
            workerGenerateAtrial.signals.finished.connect(self._thread_complete4)
            workerStartTrialLoop = Worker(self._StartTrialLoop,GeneratedTrials,worker1,workerPlot,workerGenerateAtrial)
            workerStartTrialLoop1 = Worker(self._StartTrialLoop1,GeneratedTrials)
            worker_save = Worker(self._Save,BackupSave=1)
            worker_save.signals.finished.connect(self._thread_complete6)
            self.worker1=worker1
            self.workerLick=workerLick
            self.workerPlot=workerPlot
            self.workerGenerateAtrial=workerGenerateAtrial
            self.workerStartTrialLoop=workerStartTrialLoop
            self.workerStartTrialLoop1=workerStartTrialLoop1
            self.worker_save=worker_save
        else:
            PlotM=self.PlotM
            worker1=self.worker1
            workerLick=self.workerLick
            workerPlot=self.workerPlot
            workerGenerateAtrial=self.workerGenerateAtrial
            workerStartTrialLoop=self.workerStartTrialLoop
            workerStartTrialLoop1=self.workerStartTrialLoop1
            worker_save=self.worker_save

        # collecting the base signal for photometry. Only run once
        if self.Start.isChecked() and self.PhotometryB.currentText()=='on' and self.PhotometryRun==0:
            logging.info('Starting photometry baseline timer')
            self.finish_Timer=0
            self.PhotometryRun=1
            self.ignore_timer=False

            # create label to display time remaining on photometry label and add to warning widget
            self.photometry_timer_label = QLabel()
            self.photometry_timer_label.setStyleSheet(f'color: {self.default_warning_color};')
            self.warning_widget.layout().insertWidget(0, self.photometry_timer_label)

            # If we already created a workertimer and thread we can reuse them
            if not hasattr(self, 'workertimer'):
                self.workertimer = TimerWorker()
                self.workertimer_thread = QThread()
                self.workertimer.progress.connect(self._update_photometery_timer)
                self.workertimer.finished.connect(self._thread_complete_timer)
                self.Time.connect(self.workertimer._Timer)
                self.workertimer.moveToThread(self.workertimer_thread)
                self.workertimer_thread.start()

            self.Time.emit(int(np.floor(float(self.baselinetime.text())*60)))
            logging.info('Running photometry baseline', extra={'tags': [self.warning_log_tag]})

        self._StartTrialLoop(GeneratedTrials,worker1,worker_save)

        if self.actionDrawing_after_stopping.isChecked()==True:
            try:
                self.PlotM._Update(GeneratedTrials=GeneratedTrials,Channel=self.Channel2)
            except Exception as e:
                logging.error(traceback.format_exc())

    def log_session(self) -> None:
        """
        Setup a log handler to write logs during session to TrainingFolder
        """

        logging_filename = os.path.join(self.TrainingFolder, 'python_gui_log.txt')

        # Format the log file:
        log_format = '%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(funcName)s:line %(lineno)d:%(message)s'
        log_datefmt = '%I:%M:%S %p'

        log_formatter = logging.Formatter(fmt=log_format, datefmt=log_datefmt)
        self.session_log_handler = logging.FileHandler(logging_filename)
        self.session_log_handler.setFormatter(log_formatter)
        self.session_log_handler.setLevel(logging.INFO)
        logger.root.addHandler(self.session_log_handler)

        logging.info(f'Starting log file at {self.TrainingFolder}')

    def end_session_log(self) -> None:
        """
        Dismantle the session log handler when gui is closed or new session is started
        """

        if self.session_log_handler is not None:
            logging.info(f'Closing log file at {self.session_log_handler.baseFilename}')
            self.session_log_handler.close()
            logger.root.removeHandler(self.session_log_handler)
            self.session_log_handler = None
        else:
            logging.info(f'No active session logger')

    def _StartTrialLoop(self,GeneratedTrials,worker1,worker_save):
        if self.Start.isChecked():
            logging.info('starting trial loop')
        else:
            logging.info('ending trial loop')

        # Track elapsed time in case Bonsai Stalls
        last_trial_start = time.time()
        stall_iteration = 1
        stall_duration = 5*60

        while self.Start.isChecked():
            QApplication.processEvents()
            if self.ANewTrial==1 and self.Start.isChecked() and self.finish_Timer==1:

                # Reset stall timer
                last_trial_start = time.time()
                stall_iteration = 1

                # can start a new trial when we receive the trial end signal from Bonsai
                self.ANewTrial=0
                GeneratedTrials.B_CurrentTrialN+=1
                print('Current trial: '+str(GeneratedTrials.B_CurrentTrialN+1))
                logging.info('Current trial: '+str(GeneratedTrials.B_CurrentTrialN+1))
                if (self.GeneratedTrials.TP_AutoReward  or int(self.GeneratedTrials.TP_BlockMinReward)>0
                    or self.GeneratedTrials.TP_Task in ['Uncoupled Baiting','Uncoupled Without Baiting']) or self.AddOneTrialForNoresponse.currentText()=='Yes':
                    # The next trial parameters must be dependent on the current trial's choice
                    # get animal response and then generate a new trial
                    self.NewTrialRewardOrder=0
                else:
                    # By default, to save time, generate a new trial as early as possible
                    # generate a new trial and then get animal response
                    self.NewTrialRewardOrder=1

                #initiate the generated trial
                try:
                    GeneratedTrials._InitiateATrial(self.Channel,self.Channel4)
                except Exception as e:
                    if 'ConnectionAbortedError' in str(e):
                        logging.info('lost bonsai connection: InitiateATrial')
                        logging.warning('Lost bonsai connection', extra={'tags': [self.warning_log_tag]})
                        self.Start.setChecked(False)
                        self.Start.setStyleSheet("background-color : none")
                        self.InitializeBonsaiSuccessfully=0
                        reply = QMessageBox.question(self,
                            'Box {}, Start'.format(self.box_letter),
                            'Cannot connect to Bonsai. Attempt reconnection?',
                            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                        if reply == QMessageBox.Yes:
                            self._ReconnectBonsai()
                            logging.info('User selected reconnect bonsai')
                        else:
                            logging.info('User selected not to reconnect bonsai')
                        self.ANewTrial=1

                        break
                    else:
                        reply = QMessageBox.critical(self, 'Box {}, Error'.format(self.box_letter), 'Encountered the following error: {}'.format(e),QMessageBox.Ok )
                        logging.error('Caught this error: {}'.format(e))
                        self.ANewTrial=1
                        self.Start.setChecked(False)
                        self.Start.setStyleSheet("background-color : none")
                        break
                #receive licks and update figures
                if self.actionDrawing_after_stopping.isChecked()==False:
                    self.PlotM._Update(GeneratedTrials=GeneratedTrials,Channel=self.Channel2)
                # update licks statistics
                if self.actionLicks_sta.isChecked():
                    self.PlotLick._Update(GeneratedTrials=GeneratedTrials)

                # calculate bias every 10 trials
                if (GeneratedTrials.B_CurrentTrialN+1) % 10 == 0 and GeneratedTrials.B_CurrentTrialN+1 > 20:
                    # correctly format data for bias indicator
                    choice_history = [1 if x == 2 else int(x) for x in self.GeneratedTrials.B_AnimalResponseHistory]
                    any_reward = [any(x) for x in np.column_stack(self.GeneratedTrials.B_RewardedHistory)]

                    # use self.bias_n_size of trials to compute bias over or take n the first 0 to N trials
                    l = len(choice_history)
                    # FIXME: .6  of choice history is a little arbitrary. If the n_trial_back is close to equaling the
                    #  trial count, the logistic regression can't be calculated because of an error saying
                    #  'Cannot have number of splits n_splits=10 greater than the number of samples: 2'
                    n_trial_back = self.bias_n_size if l > self.bias_n_size else \
                        round(len(np.array(choice_history)[~np.isnan(choice_history)])*.6)
                    # add data to bias_indicator
                    bias_thread = threading.Thread(target=self.bias_indicator.calculate_bias,
                                                   kwargs={'time_point': self.GeneratedTrials.B_TrialStartTime[-1],
                                                           'choice_history': choice_history,
                                                           'reward_history': np.array(any_reward).astype(int),
                                                           'n_trial_back': n_trial_back,
                                                           'cv': 2})
                    bias_thread.start()

                # save the data everytrial
                if GeneratedTrials.CurrentSimulation==True:
                    GeneratedTrials._GetAnimalResponse(self.Channel,self.Channel3,self.Channel4)
                    self.ANewTrial=1
                    self.NewTrialRewardOrder=1
                else:
                    #get the response of the animal using a different thread
                    self.threadpool.start(worker1)
                #generate a new trial
                if self.NewTrialRewardOrder==1:
                    GeneratedTrials._GenerateATrial(self.Channel4)
                '''
                ### Save data in the main thread. Keep it temporarily for testing ### 
                start_time = time.time()
                self.previous_backup_completed=1
                if GeneratedTrials.B_CurrentTrialN>0 and self.previous_backup_completed==1 and self.save_each_trial and GeneratedTrials.CurrentSimulation==False:
                    self._Save(BackupSave=1)
                # Record the end time
                end_time = time.time()
                # Calculate the time elapsed and log if it is too long
                if end_time - start_time>1:
                    logging.info(f"Time taken to backup the data is too long: {elapsed_time:.6f} seconds")
                '''
                # Save data in a separate thread
                if GeneratedTrials.B_CurrentTrialN>0 and self.previous_backup_completed==1 and self.save_each_trial and GeneratedTrials.CurrentSimulation==False:
                    self.previous_backup_completed=0
                    self.GeneratedTrials_backup=copy.copy(self.GeneratedTrials)
                    self.threadpool6.start(worker_save)

                # show disk space
                self._show_disk_space()

            elif ((time.time() - last_trial_start) >stall_duration*stall_iteration) and \
                ((time.time() - self.Channel.last_message_time) > stall_duration*stall_iteration):
                # Elapsed time since last trial is more than tolerance
                # and elapsed time since last harp message is more than tolerance

                # Check if we are in the photometry baseline period.
                if (self.finish_Timer==0) & ((time.time() - last_trial_start) < (float(self.baselinetime.text())*60+10)):
                    # Extra 10 seconds is to avoid any race conditions
                    # We are in the photometry baseline period
                    continue

                # Prompt user to stop trials
                elapsed_time = int(np.floor(stall_duration*stall_iteration/60))
                message = '{} minutes have elapsed since the last trial started. Bonsai may have stopped. Stop trials?'.format(elapsed_time)
                reply = QMessageBox.question(self,
                    'Box {}, Trial Generator'.format(self.box_letter),
                    message,QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes:
                    # User stops trials
                    err_msg = 'trial stalled {} minutes, user stopped trials. ANewTrial:{},Start:{},finish_Timer:{}'
                    logging.error(err_msg.format(elapsed_time,self.ANewTrial,self.Start.isChecked(), self.finish_Timer))

                    # Set that the current trial ended, so we can save
                    self.ANewTrial=1

                    # Flag Bonsai connection
                    self.InitializeBonsaiSuccessfully=0

                    # Reset Start button
                    self.Start.setChecked(False)
                    self.Start.setStyleSheet("background-color : none")

                    # Give warning to user
                    logging.warning('Trials stalled, recheck bonsai connection.',
                                    extra={'tags': [self.warning_log_tag]})
                    break
                else:
                    # User continues, wait another stall_duration and prompt again
                    logging.error('trial stalled {} minutes, user continued trials'.format(elapsed_time))
                    stall_iteration +=1

    def bias_calculated(self, bias: float, trial_number: int) -> None:
        """
        Function to update GeneratedTrials.B_Bias and Bias attribute when new bias value is calculated
        :param bias: bias value
        :param trial_number: trial number at which bias value was calculated
        """

        self.B_Bias_R = bias
        last_bias_filler = [self.GeneratedTrials.B_Bias[-1]]*(trial_number-len(self.GeneratedTrials.B_Bias))
        self.GeneratedTrials.B_Bias += last_bias_filler
        self.GeneratedTrials.B_Bias[trial_number-1] = bias

    def _StartTrialLoop1(self,GeneratedTrials,worker1,workerPlot,workerGenerateAtrial):
        logging.info('starting trial loop 1')
        while self.Start.isChecked():
            QApplication.processEvents()
            if self.ANewTrial==1 and self.ToGenerateATrial==1 and self.Start.isChecked():
                self.ANewTrial=0 # can start a new trial when we receive the trial end signal from Bonsai
                GeneratedTrials.B_CurrentTrialN+=1
                print('Current trial: '+str(GeneratedTrials.B_CurrentTrialN+1))
                logging.info('Current trial: '+str(GeneratedTrials.B_CurrentTrialN+1))
                if not (self.GeneratedTrials.TP_AutoReward  or int(self.GeneratedTrials.TP_BlockMinReward)>0):
                    # generate new trial and get reward
                    self.NewTrialRewardOrder=1
                else:
                    # get reward and generate new trial
                    self.NewTrialRewardOrder=0
                #initiate the generated trial
                GeneratedTrials._InitiateATrial(self.Channel,self.Channel4)
                #receive licks and update figures
                if self.test==1:
                    self.PlotM._Update(GeneratedTrials=GeneratedTrials,Channel=self.Channel2)
                else:
                    if self.ToUpdateFigure==1:
                        self.ToUpdateFigure=0
                        self.threadpool3.start(workerPlot)
                #get the response of the animal using a different thread
                self.threadpool.start(worker1)
                '''
                if self.test==1:
                    self.ANewTrial=1
                    GeneratedTrials.GetResponseFinish=0
                    GeneratedTrials._GetAnimalResponse(self.Channel,self.Channel3,self.Channel4)
                else:
                    GeneratedTrials.GetResponseFinish=0
                    self.threadpool.start(worker1)
                '''
                #generate a new trial
                if self.test==1:
                    self.ToGenerateATrial=1
                    GeneratedTrials._GenerateATrial(self.Channel4)
                else:
                    self.ToGenerateATrial=0
                    self.threadpool4.start(workerGenerateAtrial)

    def _OptogeneticsB(self):
        ''' optogenetics control in the main window'''
        if self.OptogeneticsB.currentText()=='on':
            self._Optogenetics() # press the optogenetics icon
            self.action_Optogenetics.setChecked(True)
            self.Opto_dialog.show()
            self.label_18.setEnabled(False)
            self.label_15.setEnabled(False)
            self.label_17.setEnabled(False)
            self.DelayBeta.setEnabled(False)
            self.DelayMin.setEnabled(False)
            self.DelayMax.setEnabled(False)
        else:
            self.action_Optogenetics.setChecked(False)
            self.Opto_dialog.hide()
            self.label_18.setEnabled(True)
            self.label_15.setEnabled(True)
            self.label_17.setEnabled(True)
            self.DelayBeta.setEnabled(True)
            self.DelayMin.setEnabled(True)
            self.DelayMax.setEnabled(True)

    def _GiveLeft(self):
        '''manually give left water'''
        self._ConnectBonsai()
        if self.InitializeBonsaiSuccessfully==0:
            return
        if self.AlignToGoCue.currentText()=='yes':
            # Reserving the water after the go cue.Each click will add the water to the reserved water
            self.give_left_volume_reserved=self.give_left_volume_reserved+float(self.TP_GiveWaterL_volume)
            if self.latest_fitting!={}:
                self.give_left_time_reserved=((float(self.give_left_volume_reserved)-self.latest_fitting['Left'][1])/self.latest_fitting['Left'][0])*1000
            else:
                self.give_left_time_reserved=self.give_left_time_reserved+float(self.TP_GiveWaterL)*1000
        else:
            self.Other_manual_water_left_volume.append(float(self.TP_GiveWaterL_volume))
            self.Other_manual_water_left_time.append(float(self.TP_GiveWaterL)*1000)

            self.Channel.LeftValue(float(self.TP_GiveWaterL)*1000)
            time.sleep(0.01)
            self.Channel3.ManualWater_Left(int(1))
            time.sleep(0.01+float(self.TP_GiveWaterL))
            self.Channel.LeftValue(float(self.TP_LeftValue)*1000)
            self.ManualWaterVolume[0]=self.ManualWaterVolume[0]+float(self.TP_GiveWaterL_volume)/1000
            self._UpdateSuggestedWater()
            logger.info('Give left manual water (ul): '+str(np.round(float(self.TP_GiveWaterL_volume),3)),
                           extra={'tags': [self.warning_log_tag]})


    def _give_reserved_water(self,valve=None):
        '''give reserved water usually after the go cue'''
        if valve=='left':
            if self.give_left_volume_reserved==0:
                return
            self.Channel.LeftValue(float(self.give_left_time_reserved))
            time.sleep(0.01)
            self.Channel3.ManualWater_Left(int(1))
            time.sleep(0.01+float(self.give_left_time_reserved)/1000)
            self.Channel.LeftValue(float(self.TP_LeftValue)*1000)
            self.ManualWaterVolume[0]=self.ManualWaterVolume[0]+self.give_left_volume_reserved/1000
            self.Other_manual_water_left_volume.append(self.give_left_volume_reserved)
            self.Other_manual_water_left_time.append(self.give_left_time_reserved)
            self.give_left_volume_reserved=0
            self.give_left_time_reserved=0
        elif valve=='right':
            if self.give_right_volume_reserved==0:
                return
            self.Channel.RightValue(float(self.give_right_time_reserved))
            time.sleep(0.01)
            self.Channel3.ManualWater_Right(int(1))
            time.sleep(0.01+float(self.give_right_time_reserved)/1000)
            self.Channel.RightValue(float(self.TP_RightValue)*1000)
            self.ManualWaterVolume[1]=self.ManualWaterVolume[1]+self.give_right_volume_reserved/1000
            self.Other_manual_water_right_volume.append(self.give_right_volume_reserved)
            self.Other_manual_water_right_time.append(self.give_right_time_reserved)
            self.give_right_volume_reserved=0
            self.give_right_time_reserved=0

    def _GiveRight(self):
        '''manually give right water'''
        self._ConnectBonsai()
        if self.InitializeBonsaiSuccessfully==0:
            return
        if self.AlignToGoCue.currentText()=='yes':
            # Reserving the water after the go cue.Each click will add the water to the reserved water
            self.give_right_volume_reserved=self.give_right_volume_reserved+float(self.TP_GiveWaterR_volume)
            if self.latest_fitting!={}:
                self.give_right_time_reserved=((float(self.give_right_volume_reserved)-self.latest_fitting['Right'][1])/self.latest_fitting['Right'][0])*1000
            else:
                self.give_right_time_reserved=self.give_right_time_reserved+float(self.TP_GiveWaterR)*1000
        else:
            self.Other_manual_water_right_volume.append(float(self.TP_GiveWaterR_volume))
            self.Other_manual_water_right_time.append(float(self.TP_GiveWaterR)*1000)

            self.Channel.RightValue(float(self.TP_GiveWaterR)*1000)
            time.sleep(0.01)
            self.Channel3.ManualWater_Right(int(1))
            time.sleep(0.01+float(self.TP_GiveWaterR))
            self.Channel.RightValue(float(self.TP_RightValue)*1000)
            self.ManualWaterVolume[1]=self.ManualWaterVolume[1]+float(self.TP_GiveWaterR_volume)/1000
            self._UpdateSuggestedWater()
            logger.info('Give right manual water (ul): '+str(np.round(float(self.TP_GiveWaterR_volume),3)),
                        extra={'tags': [self.warning_log_tag]})

    def _toggle_save_color(self):
        '''toggle the color of the save button to mediumorchid'''
        self.unsaved_data=True
        self.Save.setStyleSheet("color: white;background-color : mediumorchid;")

    def _PostWeightChange(self):
        self.unsaved_data=True
        self.Save.setStyleSheet("color: white;background-color : mediumorchid;")
        self._UpdateSuggestedWater()

    def _UpdateSuggestedWater(self,ManualWater=0):
        '''Update the suggested water from the manually give water'''
        try:
            if self.BaseWeight.text()!='':
                float(self.BaseWeight.text())
        except Exception as e:
            logging.warning(str(e))
            return
        try:
            if self.WeightAfter.text()!='':
                float(self.WeightAfter.text())
        except Exception as e:
            logging.warning(str(e))
            return
        try:
            if self.BaseWeight.text()!='' and self.TargetRatio.text()!='':
                # set the target weight
                target_weight=float(self.TargetRatio.text())*float(self.BaseWeight.text())
                self.TargetWeight.setText(str(np.round(target_weight,3)))

            if hasattr(self,'GeneratedTrials'):
                if hasattr(self.GeneratedTrials,'BS_TotalReward'):
                    BS_TotalReward=float(self.GeneratedTrials.BS_TotalReward)/1000
                else:
                    BS_TotalReward=0
            else:
                BS_TotalReward=0

            if hasattr(self,'ManualWaterVolume'):
                ManualWaterVolume=np.sum(self.ManualWaterVolume)
            else:
                ManualWaterVolume=0
            water_in_session=BS_TotalReward+ManualWaterVolume
            self.water_in_session=water_in_session
            if self.WeightAfter.text()!='' and self.BaseWeight.text()!='' and self.TargetRatio.text()!='':
                # calculate the suggested water
                suggested_water=target_weight-float(self.WeightAfter.text())
                # give at lease 1ml
                if suggested_water<1-water_in_session:
                    suggested_water=1-water_in_session
                if suggested_water<0:
                    suggested_water=0
                # maximum 3.5ml
                if suggested_water>3.5:
                    suggested_water=3.5
                    if self.default_ui=='ForagingGUI.ui':
                        self.TotalWaterWarning.setText('Supplemental water is >3.5! Health issue and LAS should be alerted!')
                    elif self.default_ui=='ForagingGUI_Ephys.ui':
                        self.TotalWaterWarning.setText('Supplemental water is >3.5! Health issue and \n LAS should be alerted!')
                    self.TotalWaterWarning.setStyleSheet(self.default_warning_color)
                else:
                    self.TotalWaterWarning.setText('')
                self.SuggestedWater.setText(str(np.round(suggested_water,3)))
            else:
                self.SuggestedWater.setText('')
                self.TotalWaterWarning.setText('')
            # update total water
            if self.SuggestedWater.text()=='':
                ExtraWater=0
            else:
                ExtraWater=float(self.SuggestedWater.text())
            TotalWater=ExtraWater+water_in_session
            self.TotalWater.setText(str(np.round(TotalWater,3)))
        except Exception as e:
            logging.error(traceback.format_exc())


    def create_auto_train_dialog(self):
        # Note: by only create one AutoTrainDialog, all objects associated with 
        # AutoTrainDialog are now persistent!
        self.AutoTrain_dialog = AutoTrainDialog(MainWindow=self, parent=None)

    def _auto_train_clicked(self):
        """set up auto training"""
        self.AutoTrain_dialog.show()

        # Check subject id each time the dialog is opened
        self.AutoTrain_dialog.update_auto_train_fields(subject_id=self.ID.text())

    def _open_mouse_on_streamlit(self):
        '''open the training history of the current mouse on the streamlit app'''
        # See this PR: https://github.com/AllenNeuralDynamics/foraging-behavior-browser/pull/25
        webbrowser.open(f'https://foraging-behavior-browser.allenneuraldynamics-test.org/?filter_subject_id={self.ID.text()}'
                         '&tab_id=tab_session_inspector'
                         '&session_plot_mode=all+sessions+filtered+from+sidebar'
                         '&session_plot_selected_draw_types=1.+Choice+history'
        )

    def _generate_upload_manifest(self, session: Session):
        '''
            Generates a manifest.yml file for triggering data copy to VAST and upload to aws
            :param session: session to use to create upload manifest
        '''

        if self.ID.text() in ['0','1','2','3','4','5','6','7','8','9','10']:
            logging.info('Skipping upload manifest, because this is the test mouse')
            return

        if not self.Settings['AutomaticUpload']:
            logging.info('Skipping Automatic Upload based on ForagingSettings.json')
            return

        try:
            if not hasattr(self, 'project_name'):
                self.project_name = 'Behavior Platform'

            schedule = self.acquisition_datetime.split('_')[0]+'_20-30-00'
            capsule_id = 'c089614a-347e-4696-b17e-86980bb782c1'
            mount = 'FIP'

            modalities = {}
            for stream in session.data_streams:
                if Modality.BEHAVIOR in stream.stream_modalities:
                    modalities['behavior'] = [self.TrainingFolder.replace('\\', '/')]
                elif Modality.FIB in stream.stream_modalities:
                    modalities['fib'] = [self.PhotometryFolder.replace('\\', '/')]
                elif Modality.BEHAVIOR_VIDEOS in stream.stream_modalities:
                    modalities['behavior-videos'] = [self.VideoFolder.replace('\\', '/')]

            date_format = "%Y-%m-%d_%H-%M-%S"
            # Define contents of manifest file
            contents = {
                'acquisition_datetime': datetime.strptime(self.acquisition_datetime,date_format),
                'name': self.session_name,
                'platform': 'behavior',
                'subject_id': int(self.ID.text()),
                'capsule_id': capsule_id,
                'mount':mount,
                'destination': '//allen/aind/scratch/dynamic_foraging_rig_transfer',
                's3_bucket':'private',
                'processor_full_name': 'AIND Behavior Team',
                'modalities':modalities,
                'schemas':[
                    os.path.join(self.MetadataFolder,'session.json').replace('\\','/'),
                    os.path.join(self.MetadataFolder,'rig.json').replace('\\','/'),
                    ],
                'schedule_time':datetime.strptime(schedule,date_format),
                'project_name':self.project_name,
                'script': {}
                }

            # Define filename of manifest
            if not os.path.exists(self.Settings['manifest_flag_dir']):
                os.makedirs(self.Settings['manifest_flag_dir'])
            filename = os.path.join(
                self.Settings['manifest_flag_dir'],
                'manifest_{}.yml'.format(contents['name']))

            # Write the manifest file
            with open(filename,'w') as yaml_file:
                yaml.dump(contents, yaml_file, default_flow_style=False)

        except Exception as e:
            logging.error('Could not generate upload manifest: {}'.format(str(e)))
            QMessageBox.critical(self, 'Upload manifest',
                'Could not generate upload manifest. '+\
                'Please alert the mouse owner, and report on github.')

        # disconnect slot to only create manifest once
        logging.debug('Disconnecting sessionGenerated from _generate_upload_manifest')
        self.upload_manifest_slot = self.sessionGenerated.disconnect(self.upload_manifest_slot)

def start_gui_log_file(box_number):
    '''
        Starts a log file for the gui.
        The log file is located at C:/Users/<username>/Documents/foraging_gui_logs
        One log file is created for each time the GUI is started
        The name of the gui file is <hostname>-<box letter A/B/C/D>_gui_log_<date and time>.txt
    '''
    # Check if the log folder exists, if it doesn't make it
    logging_folder = os.path.join(os.path.expanduser("~"), "Documents",'foraging_gui_logs')
    if not os.path.exists(logging_folder):
        os.makedirs(logging_folder)

    # Determine name of this log file
    # Get current time
    current_time = datetime.now()
    formatted_datetime = current_time.strftime("%Y-%m-%d_%H-%M-%S")

    # Build logfile name
    hostname = socket.gethostname()
    box_mapping = {
        1:'A',
        2:'B',
        3:'C',
        4:'D'
    }
    box_name =hostname+'-'+box_mapping[box_number]
    filename = '{}_gui_log_{}.txt'.format(box_name,formatted_datetime)
    logging_filename = os.path.join(logging_folder,filename)

    # Format the log file:
    log_format = '%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(funcName)s:line %(lineno)d:%(message)s'
    log_datefmt = '%I:%M:%S %p'

    # Start the log file
    print('Starting a GUI log file at: ')
    print(logging_filename)

    log_formatter = logging.Formatter(fmt=log_format, datefmt=log_datefmt)
    file_handler = logging.FileHandler(logging_filename)
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
    logger.root.addHandler(file_handler)

    logging.info('Starting logfile!')
    logging.captureWarnings(True)

def log_git_hash():
    '''
        Add a note to the GUI log about the current branch and hash. Assumes the local repo is clean
    '''

    # Get information about python
    py_version = sys.version
    py_version_parse = '.'.join(py_version.split('.')[0:2])
    logging.info('Python version: {}'.format(py_version))
    print('Python version: {}'.format(py_version))
    if py_version_parse != '3.11':
        logging.error('Incorrect version of python! Should be 3.11, got {}'.format(py_version_parse))

    try:
        # Get information about task repository
        git_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()
        git_branch = subprocess.check_output(['git','branch','--show-current']).decode('ascii').strip()
        repo_url = subprocess.check_output(['git', 'remote', 'get-url', 'origin']).decode('ascii').strip()
        dirty_files = subprocess.check_output(['git','diff-index','--name-only', 'HEAD']).decode('ascii').strip()
        version=foraging_gui.__version__
    except Exception as e:
        logging.error('Could not log git branch and hash: {}'.format(str(e)))
        return None, None, None, None, None, None

    # Log branch and commit hash
    logging.info('Current git commit branch, hash: {}, {}'.format(git_branch,git_hash))
    print('Current git commit branch, hash: {}, {}'.format(git_branch,git_hash))

    # Log gui version:
    logging.info('Current foraging_gui version: {}'.format(foraging_gui.__version__))
    print('Current foraging_gui version: {}'.format(foraging_gui.__version__))

    # Check for untracked local changes
    repo_dirty_flag = dirty_files != ''
    if repo_dirty_flag:
        dirty_files = dirty_files.replace('\n',', ')
        logging.warning('local repository has untracked changes to the following files: {}'.format(dirty_files))
        print('local repository has untracked changes to the following files: {}'.format(dirty_files))
    else:
        logging.warning('local repository is clean')
        print('local repository is clean')

    return git_hash, git_branch, repo_url, repo_dirty_flag, dirty_files, version


def show_exception_box(log_msg):
    '''
        Displays a Qwindow alert to the user that an uncontrolled error has occured, and the error message
        if no QApplication instance is available, logs a note in the GUI log
    '''
    # Check if a QApplication instance is running
    if QtWidgets.QApplication.instance() is not None:
        box = log_msg[0] # Grab the box letter
        log_msg = log_msg[1:] # Grab the error messages

        # Make a QWindow, wait for user response
        errorbox = QtWidgets.QMessageBox()
        errorbox.setWindowTitle('Box {}, Error'.format(box))
        msg = '<span style="color:purple;font-weight:bold">An uncontrolled error occurred. Save any data and restart the GUI. </span> <br><br>{}'.format(log_msg)
        errorbox.setText(msg)
        errorbox.exec_()
    else:
        logging.error('could not launch exception box')

def is_absolute_path(path):
    # Check if the path starts with a root directory identifier or drive letter (for Windows)
    return path.startswith('/') or (len(path) > 2 and path[1] == ':' and path[2] == '\\')

class UncaughtHook(QtCore.QObject):
    '''
        This class handles uncaught exceptions and hooks into the sys.excepthook
    '''
    _exception_caught = QtCore.Signal(object)

    def __init__(self,box_number, *args, **kwargs):
        super(UncaughtHook, self).__init__(*args, **kwargs)

        # Determine what Box we are in
        mapper = {
            1:'A',
            2:'B',
            3:'C',
            4:'D'
            }
        self.box = mapper[box_number]

        # Hook into the system except hook
        sys.excepthook = self.exception_hook

        # Call our custom function to display an alert
        self._exception_caught.connect(show_exception_box)


    def exception_hook(self, exc_type, exc_value, exc_traceback):
        '''
            Log the error in the log, and display in the console
            then call our custom hook function to display an alert
        '''

        # Display in console
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print('Encountered a fatal error: ')
        print(tb)

        # Add to log
        logging.error('FATAL ERROR: \n{}'.format(tb))

        # Display alert box
        tb = "<br><br>".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        self._exception_caught.emit(self.box+tb)

def log_subprocess_output(process, prefix):
    logging.info('{} logging starting'.format(prefix))
    while process.poll() is None:
        output = process.stdout.readline()
        if 'Exception' in output:
            logging.error(prefix+': '+output.strip())
        else:
            logging.info(prefix+': '+output.strip())

    logging.info('{} logging terminating'.format(prefix))

if __name__ == "__main__":

    # Determine which box we are using, and whether to start bonsai IDE
    start_bonsai_ide=True
    if len(sys.argv) == 1:
        box_number = 1
    elif len(sys.argv) == 2:
        box_number = int(sys.argv[1])
    else:
        box_number = int(sys.argv[1])
        if sys.argv[2] == '--no-bonsai-ide':
            start_bonsai_ide=False

    # Start logging
    start_gui_log_file(box_number)
    commit_ID, current_branch, repo_url, repo_dirty_flag, dirty_files, version = log_git_hash()

    # Formating GUI graphics
    logging.info('Setting QApplication attributes')
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling,1)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps,True)
    QApplication.setAttribute(Qt.AA_DisableHighDpiScaling,False)
    QApplication.setAttribute(Qt.AA_Use96Dpi,False)
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    # Start QApplication
    logging.info('Starting QApplication and Window')
    app = QApplication(sys.argv)

    # Create global instance of uncaught exception handler
    qt_exception_hook = UncaughtHook(box_number)

    # Start GUI window
    win = Window(box_number=box_number,start_bonsai_ide=start_bonsai_ide)
    # Get the commit hash of the current version of this Python file
    win.commit_ID=commit_ID
    win.current_branch=current_branch
    win.repo_url=repo_url
    win.repo_dirty_flag=repo_dirty_flag
    win.dirty_files=dirty_files
    win.version=version
    win.show()

    # Move creating AutoTrain here to catch any AWS errors
    win.create_auto_train_dialog()

    # Run your application's event loop and stop after closing all windows
    sys.exit(app.exec())


