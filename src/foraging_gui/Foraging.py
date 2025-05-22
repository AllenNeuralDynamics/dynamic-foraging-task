import json
import logging
import math
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
import traceback
import webbrowser
from datetime import date, datetime, timedelta
from hashlib import md5
from importlib import import_module
from pathlib import Path
from threading import Lock, Thread, Event
from typing import Literal, Optional, Union, get_args

import harp
import logging_loki
import numpy as np
import pandas as pd
import requests
import serial
import yaml
from aind_behavior_dynamic_foraging.CurriculumManager.curriculum_schedule_mapper import (
    CURRICULUM_SCHEDULE_NAME_MAPPER,
)
from aind_behavior_dynamic_foraging.CurriculumManager.trainer import (
    DynamicForagingMetrics,
    DynamicForagingTrainerState,
    TrainerState,
)
from aind_behavior_dynamic_foraging.DataSchemas.fiber_photometry import (
    STAGE_STARTS,
    FiberPhotometry,
)
from aind_behavior_dynamic_foraging.DataSchemas.operation_control import (
    OperationalControl,
    StageSpecs,
)
from aind_behavior_dynamic_foraging.DataSchemas.optogenetics import (
    IntervalConditions,
    LaserColorFive,
    LaserColorFour,
    LaserColorOne,
    LaserColorSix,
    LaserColorThree,
    LaserColorTwo,
    Optogenetics,
    SessionControl,
)
from aind_behavior_dynamic_foraging.DataSchemas.task_logic import (
    AindDynamicForagingTaskLogic,
    AindDynamicForagingTaskParameters,
    AutoBlock,
    AutoWater,
    Warmup,
)
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_slims_api.models.behavior_session import SlimsBehaviorSession
from matplotlib.backends.backend_qt5agg import (
    NavigationToolbar2QT as NavigationToolbar,
)
from pydantic import BaseModel, ValidationError
from pykeepass import PyKeePass
from pyOSC3.OSC3 import OSCStreamingClient
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import Qt, QThread, QThreadPool, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
)
from scipy.io import loadmat, savemat
from StageWidget.main import get_stage_widget

import foraging_gui
import foraging_gui.rigcontrol as rigcontrol
from foraging_gui.bias_indicator import BiasIndicator
from foraging_gui.Dialogs import (
    CameraDialog,
    LaserCalibrationDialog,
    LickStaDialog,
    MetadataDialog,
    MouseSelectorDialog,
    OptogeneticsDialog,
    TimeDistributionDialog,
    WaterCalibrationDialog,
)
from foraging_gui.GenerateMetadata import generate_metadata
from foraging_gui.loaded_mouse_slims_handler import LoadedMouseSlimsHandler
from foraging_gui.metadata_mapper import (
    behavior_json_to_fip_model,
    behavior_json_to_operational_control_model,
    behavior_json_to_opto_model,
    behavior_json_to_session_model,
    behavior_json_to_task_logic_model,
)
from foraging_gui.MyFunctions import (
    EphysRecording,
    GenerateTrials,
    NewScaleSerialY,
    TimerWorker,
    Worker,
)
from foraging_gui.RigJsonBuilder import build_rig_json
from foraging_gui.schema_widgets.behavior_parameters_widget import (
    BehaviorParametersWidget,
)
from foraging_gui.schema_widgets.fib_parameters_widget import (
    FIBParametersWidget,
)
from foraging_gui.schema_widgets.operation_control_widget import (
    OperationControlWidget,
)
from foraging_gui.schema_widgets.session_parameters_widget import (
    SessionParametersWidget,
)
from foraging_gui.settings_model import BonsaiSettingsModel, DFTSettingsModel
from foraging_gui.sound_button import SoundButton
from foraging_gui.stage import Stage
from foraging_gui.Visualization import (
    PlotLickDistribution,
    PlotTimeDistribution,
    PlotV,
)
from foraging_gui.warning_widget import WarningWidget

logger = logging.getLogger(__name__)
logger.root.handlers.clear()  # clear handlers so console output can be configured
logging.raiseExceptions = os.getenv("FORAGING_DEV_MODE", False)


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()  # Convert NumPy array to a list
        if isinstance(obj, np.integer):
            return int(obj)  # Convert np.int32 to a regular int
        if isinstance(obj, np.float64) and np.isnan(obj):
            return "NaN"  # Represent NaN as a string
        return super(NumpyEncoder, self).default(obj)


class Window(QMainWindow):
    Time = QtCore.pyqtSignal(int)  # Photometry timer signal
    sessionEnded = QtCore.pyqtSignal()

    def __init__(self, parent=None, box_number=1, start_bonsai_ide=True):
        logging.info("Creating Window")

        # create warning widget
        self.warning_log_tag = (
            "warning_widget"  # TODO: How to set this or does it matter?
        )

        super().__init__(parent)

        # Process inputs
        self.box_number = box_number
        mapper = {
            1: "A",
            2: "B",
            3: "C",
            4: "D",
        }
        self.box_letter = mapper[box_number]
        self.start_bonsai_ide = start_bonsai_ide

        # Load Settings that are specific to this computer
        self.SettingFolder = os.path.join(
            os.path.expanduser("~"), "Documents", "ForagingSettings"
        )
        self.SettingFile = os.path.join(
            self.SettingFolder, "ForagingSettings.json"
        )
        self.SettingsBoxFile = os.path.join(
            self.SettingFolder, "Settings_box" + str(self.box_number) + ".csv"
        )
        self._GetSettings()
        self._LoadSchedule()

        # Load Settings that are specific to this box
        self.LaserCalibrationFiles = os.path.join(
            self.SettingFolder, "LaserCalibration_{}.json".format(box_number)
        )
        self.WaterCalibrationFiles = os.path.join(
            self.SettingFolder, "WaterCalibration_{}.json".format(box_number)
        )
        self.WaterCalibrationParFiles = os.path.join(
            self.SettingFolder,
            "WaterCalibrationPar_{}.json".format(box_number),
        )

        # Load Laser and Water Calibration Files
        self._GetLaserCalibration()
        self._GetWaterCalibration()

        # Load Rig Json
        self._LoadRigJson()

        # Load User interface
        self._LoadUI()

        # create AINDBehaviorSession model and widget to be used and referenced for session info
        self.session_model = AindBehaviorSessionModel(
            experiment="Coupled Baiting",
            experimenter=["the ghost in the shell"],
            date=datetime.now(),  # update when folders are created
            root_path="",  # update when created
            session_name="",  # update when date and subject are filled in
            subject="0",
            experiment_version=foraging_gui.__version__,
            notes="",
            commit_hash=subprocess.check_output(["git", "rev-parse", "HEAD"])
            .decode("ascii")
            .strip(),
            allow_dirty_repo=subprocess.check_output(
                ["git", "diff-index", "--name-only", "HEAD"]
            )
            .decode("ascii")
            .strip()
            != "",
            skip_hardware_validation=True,
        )
        self.session_widget = SessionParametersWidget(self.session_model)
        for i, widget in enumerate(
            self.session_widget.schema_fields_widgets.values()
        ):
            self.session_param_layout.insertWidget(i, widget)
        self.notes_layout.insertWidget(
            0, self.session_widget.schema_fields_widgets["notes"]
        )

        # create AindDynamicForagingTaskLogic model and widget to be used and referenced for session info
        self.task_logic = AindDynamicForagingTaskLogic(
            task_parameters=AindDynamicForagingTaskParameters(
                auto_water=AutoWater(), auto_block=AutoBlock(), warmup=Warmup()
            )
        )
        self.RewardFamilies = [
            [[8, 1], [6, 1], [3, 1], [1, 1]],
            [[8, 1], [1, 1]],
            [
                [1, 0],
                [0.9, 0.1],
                [0.8, 0.2],
                [0.7, 0.3],
                [0.6, 0.4],
                [0.5, 0.5],
            ],
            [[6, 1], [3, 1], [1, 1]],
        ]
        self.task_widget = BehaviorParametersWidget(
            self.task_logic.task_parameters,
            reward_families=self.RewardFamilies,
        )
        self.task_widget.taskUpdated.connect(self.update_session_task)
        self.update_session_task("coupled")  # initialize to coupled
        # update reward pairs when task has changed
        self.task_widget.taskUpdated.connect(
            lambda task: self._ShowRewardPairs()
        )
        self.task_widget.ValueChangedInside.connect(
            lambda name: self._ShowRewardPairs()
        )
        # initialize valve times and update valve times when reward volumes change
        self.left_valve_open_time = 0.03
        self.right_valve_open_time = 0.03
        self.task_widget.volumeChanged.connect(self.update_valve_open_time)

        # create OperationControl model and widget to be used and referenced for session info
        self.operation_control_model = OperationalControl(
            stage_specs=StageSpecs(
                stage_name=(
                    "AIND"
                    if self.Settings[
                        f"newscale_serial_num_box{self.box_number}"
                    ]
                    == ""
                    else "newscale"
                ),
                rig_name=self.current_box,
            )
        )
        self.operation_control_widget = OperationControlWidget(
            self.operation_control_model
        )

        # create layout for task and operation widget
        layout = QVBoxLayout()
        layout.addWidget(self.operation_control_widget)
        layout.addWidget(self.task_widget)
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.task_parameter_scroll_area.setWidget(widget)

        # add fip schema widget
        self.fip_model = FiberPhotometry(enabled=False)
        self.fip_widget = FIBParametersWidget(self.fip_model)
        for i, widget in enumerate(
            list(self.fip_widget.schema_fields_widgets.values())
        ):
            self.fip_layout.insertWidget(i, widget)
            self.fip_layout.insertWidget(i, widget)

        # when session is ended, save relevant models
        self.sessionEnded.connect(self.save_task_models)

        # add warning_widget to layout and set color
        self.warning_widget = WarningWidget(
            log_tag=self.warning_log_tag,
            warning_color=self.default_warning_color,
        )
        self.scrollArea_6.setWidget(self.warning_widget)

        # set window title
        self.setWindowTitle(self.rig_name)
        logging.info("Setting Window title: {}".format(self.rig_name))

        # Set up parameters
        self.StartANewSession = 1  # to decide if should start a new session
        self.ToInitializeVisual = 1  # Should we visualize performance
        self.FigureUpdateTooSlow = 0  # if the FigureUpdateTooSlow is true, using different process to update figures
        self.ANewTrial = 1  # permission to start a new trial
        self.UpdateParameters = 1  # permission to update parameters
        # -1, logging is not started; 0, formal logging; 1, temporary logging
        self.logging_type = -1
        self.previous_backup_completed = 1  # permission to save backup data; 0, the previous saving has not finished, and it will not trigger the next saving; 1, it is allowed to save backup data
        self.unsaved_data = False  # Setting unsaved data to False
        self.to_check_drop_frames = 1  # 1, to check drop frames during saving data; 0, not to check drop frames
        self.session_run = (
            False  # flag to indicate if session has been run or not
        )

        # Stage Widget
        self.stage_widget = None
        # initialize empty timers
        self.left_retract_timer = QTimer(timeout=lambda: None)
        self.left_retract_timer.setSingleShot(True)
        self.right_retract_timer = QTimer(timeout=lambda: None)
        self.right_retract_timer.setSingleShot(True)
        try:
            self._load_stage()
        except IOError as e:
            msg = (
                "ERROR...<br>"
                "Dear scientist, please perform the following to document this issue:<br>"
                "    1) Create comment here: <a href=https://github.com/AllenNeuralDynamics/dynamic-foraging-task/issues/925>Github Link</a><br>"
                "    2) In the comment list the following information:<br> "
                "            - Date and time of error<br>"
                "            - Box info (ex. 6D)<br>"
                "            - Attach logs (found in  C:\\Users\\svc_aind_behavior\\Documents\\foraging_gui_logs). Please add the two most recent files<br>"
                "            - Short description of the last thing done on the GUI before the error. (ex. overnight bleaching, closed gui, opened gui - error)<br>"
                "Thank you, with your efforts hopefully we can vanquish this error and never see it again...<br>"
            )
            show_msg_box(
                "Stage Widget Error", "Stage Widget Error Diagnostic Help", msg
            )
            raise e

        # Connect to Bonsai
        self._InitializeBonsai()

        # Set up threads
        self.threadpool = QThreadPool()  # get animal response
        self.threadpool2 = QThreadPool()  # get animal lick
        self.threadpool3 = QThreadPool()  # visualization
        self.threadpool4 = QThreadPool()  # for generating a new trial
        self.threadpool5 = QThreadPool()  # for starting the trial loop
        self.threadpool6 = QThreadPool()  # for saving data
        self.threadpool_workertimer = QThreadPool()  # for timing
        self.load_mouse_worker = None  # initialized when mouse loaded
        self.load_mouse_thread = (
            QThreadPool()
        )  # threadpool for loading in mouse

        # initialize thread lock
        self.data_lock = Lock()

        # intialize behavior baseline time flag
        self.behavior_baseline_period = Event()
        self.baseline_min_elapsed = 0

        # create bias indicator
        self.bias_n_size = 200
        self.bias_indicator = BiasIndicator(
            x_range=self.bias_n_size, data_lock=self.data_lock
        )
        self.bias_indicator.biasValue.connect(
            self.bias_calculated
        )  # update dashboard value
        self.bias_indicator.setSizePolicy(
            QSizePolicy.Maximum, QSizePolicy.Maximum
        )
        self.bias_thread = Thread()  # dummy thread

        # create sound button
        self.sound_button = SoundButton(
            attenuation=int(self.SettingsBox["AttenuationLeft"])
        )
        self.toolBar_3.addWidget(self.sound_button)

        # Set up more parameters
        self.FIP_started = False
        self.OpenOptogenetics = 0
        self.OpenWaterCalibration = 0
        self.OpenLaserCalibration = 0
        self.OpenCamera = 0
        self.OpenMetadata = 0
        self.NewTrialRewardOrder = 0
        self.LickSta = 0
        self.LickSta_ToInitializeVisual = 1
        self.TimeDistribution = 0
        self.TimeDistribution_ToInitializeVisual = 1
        self.finish_Timer = 1  # for photometry baseline recordings
        self.PhotometryRun = 0  # 1. Photometry has been run; 0. Photometry has not been carried out.
        self.ignore_timer = (
            False  # Used for canceling the photometry baseline timer
        )
        self.give_left_volume_reserved = 0  # the reserved volume of the left valve (usually given after go cue)
        self.give_right_volume_reserved = 0  # the reserved volume of the right valve (usually given after go cue)
        self.give_left_time_reserved = 0  # the reserved open time of the left valve (usually given after go cue)
        self.give_right_time_reserved = 0  # the reserved open time of the right valve (usually given after go cue)
        self.load_tag = (
            0  # 1, a session has been loaded; 0, no session has been loaded
        )
        self.Other_manual_water_left_volume = (
            []
        )  # the volume of manual water given by the left valve each time
        self.Other_manual_water_left_time = (
            []
        )  # the valve open time of manual water given by the left valve each time
        self.Other_manual_water_right_volume = (
            []
        )  # the volume of manual water given by the right valve each time
        self.Other_manual_water_right_time = (
            []
        )  # the valve open time of manual water given by the right valve each time

        # create slims handler to handle waterlog and curriculum management
        self.slims_handler = LoadedMouseSlimsHandler()
        if (
            self.slims_handler.slims_client is None
        ):  # error connecting to slims
            logging.warning(
                "Cannot connect to slims. If mouse needs to be run, load in parameters locally.",
                extra={"tags": [self.warning_log_tag]},
            )

        # initialize mouse selector
        slims_mice = self.slims_handler.get_added_mice()
        self.mouse_selector_dialog = MouseSelectorDialog(
            [mouse.barcode for mouse in slims_mice], self.box_letter
        )

        # create label giff to indicate mouse is being loaded
        movie = QtGui.QMovie("resources/mouse_loading.gif")
        movie.setScaledSize(QtCore.QSize(200, 200))
        movie.start()
        self.load_slims_progress = QLabel()
        self.load_slims_progress.setWindowFlag(Qt.FramelessWindowHint)
        self.load_slims_progress.setMovie(movie)

        self._Optogenetics()  # open the optogenetics panel and initialize opto model
        self._LaserCalibration()  # to open the laser calibration panel
        self._WaterCalibration()  # to open the water calibration panel
        self._Camera()
        self._InitializeMotorStage()
        self._Metadata()
        self.WaterPerRewardedTrial = 0.005
        self._ShowRewardPairs()  # show reward pairs
        self._GetTrainingParameters()  # get initial training parameters
        self.connectSignalsSlots()
        self.update_valve_open_time("Left")
        self.update_valve_open_time("Right")
        self._LickSta()
        self.CreateNewFolder = (
            1  # to create new folder structure (a new session)
        )
        self.ManualWaterVolume = [0, 0]
        self._StopPhotometry()  # Make sure photoexcitation is stopped

        # update operational control positions once stage is loaded
        self.update_operational_control_stage_positions()

        # create QTimer to flash start button color
        self.start_flash = QTimer(timeout=self.toggle_save_color, interval=500)
        self.is_purple = False

        # Initialize open ephys saving dictionary
        self.open_ephys = []

        # load the rig metadata
        self._load_rig_metadata()

        # Initializes session log handler as None
        self.session_log_handler = None

        # show disk space
        self._show_disk_space()
        if not self.start_bonsai_ide:
            """
            When starting bonsai without the IDE the connection is always unstable.
            Reconnecting solves the issue
            """
            self._ReconnectBonsai()
        logging.info("Start up complete")

    def update_session_task(
        self, task_type: Literal["coupled", "uncoupled", "rewardN"]
    ):
        """
        Configure session task based on task parameters configured
        :param task_type: task type currently configured
        """

        if task_type == "coupled":
            for i in range(2, 5):
                self.session_widget.experiment_widget.model().item(
                    i
                ).setEnabled(False)
            for i in range(2):
                self.session_widget.experiment_widget.model().item(
                    i
                ).setEnabled(True)
            self.session_widget.experiment_widget.setCurrentIndex(0)

        elif task_type == "uncoupled":
            for i in range(5):
                if i in [0, 1, 4]:
                    self.session_widget.experiment_widget.model().item(
                        i
                    ).setEnabled(False)
                else:
                    self.session_widget.experiment_widget.model().item(
                        i
                    ).setEnabled(True)
                self.session_widget.experiment_widget.setCurrentIndex(2)
        else:
            for i in range(4):
                self.session_widget.experiment_widget.model().item(
                    i
                ).setEnabled(False)

            self.session_widget.experiment_widget.model().item(4).setEnabled(
                True
            )
            self.session_widget.experiment_widget.setCurrentIndex(4)
        logging.info("Start up complete")

    def _load_rig_metadata(self):
        """Load the latest rig metadata"""

        rig_json, rig_json_file = self._load_most_recent_rig_json()
        self.latest_rig_metadata_file = rig_json_file
        self.Metadata_dialog._SelectRigMetadata(self.latest_rig_metadata_file)

    def _show_disk_space(self):
        """Show the disk space of the current computer"""
        total, used, free = shutil.disk_usage(self.default_saveFolder)
        self.diskspace.setText(
            f"Used space: {used / 1024**3:.2f}GB    Free space: {free / 1024**3:.2f}GB"
        )
        self.DiskSpaceProgreeBar.setValue(int(used / total * 100))
        if free / 1024**3 < 100 or used / total > 0.9:
            self.DiskSpaceProgreeBar.setStyleSheet(
                f"QProgressBar::chunk {{background-color: {self.default_warning_color};}}"
            )
            logging.warning(
                f"Low disk space  Used space: {used / 1024**3:.2f}GB    Free space: {free / 1024**3:.2f}GB"
            )
        else:
            self.DiskSpaceProgreeBar.setStyleSheet(
                "QProgressBar::chunk {background-color: green;}"
            )

    def _load_stage(self) -> None:
        """
        Check whether newscale stage is defined in the config. If not, initialize and inject stage widget.
        """
        if (
            self.Settings["newscale_serial_num_box{}".format(self.box_number)]
            == ""
        ):
            widget_to_replace = (
                "motor_stage_widget"
                if self.default_ui == "ForagingGUI_Ephys.ui"
                else "widget_2"
            )
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

    def retract_lick_spout(self, lick_spout_licked: Literal["Left", "Right"], pos: float = 0) -> None:
        """
        Fast retract lick spout based on lick spout licked

        :param lick_spout_licked: lick spout that was licked. Opposite lickspout will be retracted
        :param pos: pos to move lick spout to. Default is 0

        """
        # disconnect so it's only triggered once
        self.GeneratedTrials.mouseLicked.disconnect(self.retract_lick_spout)

        lick_spout_retract = "right" if lick_spout_licked == "Left" else "left"
        timer = getattr(self, f"{lick_spout_retract}_retract_timer")
        tp = self.task_logic.task_parameters
        if tp.lick_spout_retraction and self.stage_widget is not None:
            logger.info("Retracting lick spout.")
            motor = 1 if lick_spout_licked == "Left" else 2                             # TODO: is this the correct mapping
            curr_pos = self.stage_widget.stage_model.get_current_positions_mm(motor)    # TODO: Do I need to set rel_to_monument to True?
            self.stage_widget.stage_model.quick_move(motor=motor, distance=pos-curr_pos, skip_if_busy=True)

            # configure timer to un-retract lick spout
            timer.timeout.disconnect()
            timer.timeout.connect(lambda: self.un_retract_lick_spout(lick_spout_licked, curr_pos))
            timer.setInterval(self.operation_control_model.lick_spout_retraction_specs.wait_time*1000)
            timer.setSingleShot(True)
            timer.start()

        elif self.stage_widget is None:
            logger.info("Can't fast retract stage because AIND stage is not being used.",
                        extra={"tags": [self.warning_log_tag]})

        elif tp.lick_spout_retraction:
            self.GeneratedTrials.mouseLicked.connect(self.retract_lick_spout)
            logger.info(f"Retraction turned off.",
                        extra={"tags": [self.warning_log_tag]})

    def un_retract_lick_spout(self, lick_spout_licked: Literal["Left", "Right"], pos: float = 0) -> None:
        """
        Un-retract specified lick spout

        :param lick_spout_licked: lick spout that was licked. Opposite licks pout will be un-retracted
        :param pos: pos to move lick spout to. Default is 0

        """
        if self.stage_widget is not None:
            logger.info("Un-retracting lick spout.")
            speed = self.operation_control_model.lick_spout_retraction_specs.un_retract_speed.value
            motor = 1 if lick_spout_licked == "Left" else 2
            logger.info("Setting speed and pos")
            self.stage_widget.stage_model.update_speed(value=speed)
            self.stage_widget.stage_model.update_position(positions={motor:pos})
            self.stage_widget.stage_model.update_speed(value=1)
        else:
            logger.info("Can't un retract lick spout because no AIND stage connected")

        self.GeneratedTrials.mouseLicked.connect(self.retract_lick_spout)

    # def set_stage_speed_to_normal(self):
    #     """"
    #     Sets AIND stage to normal speed
    #     """
    #
    #     if self.stage_widget is not None:
    #         logger.info("Setting stage to normal speed.")
    #         self.stage_widget.stage_model.update_speed(value=1)
    #
    #     else:
    #         logger.info("Can't set stage speed because no AIND stage connected")

    def _LoadUI(self):
        """
        Determine which user interface to use
        """
        uic.loadUi(self.default_ui, self)
        if self.default_ui == "ForagingGUI.ui":
            logging.info("Using ForagingGUI.ui interface")
            self.default_warning_color = "purple"
            self.default_text_color = "purple"
            self.default_text_background_color = "purple"
        elif self.default_ui == "ForagingGUI_Ephys.ui":
            logging.info("Using ForagingGUI_Ephys.ui interface")
            self.Visualization.setTitle(str(date.today()))
            self.default_warning_color = "red"
            self.default_text_color = "red"
            self.default_text_background_color = "red"
        else:
            logging.info("Using ForagingGUI.ui interface")
            self.default_warning_color = "red"
            self.default_text_color = "red"
            self.default_text_background_color = "red"

    def connectSignalsSlots(self):
        """Define callbacks"""
        self.action_About.triggered.connect(self._about)
        self.action_Camera.triggered.connect(self._Camera)

        # create QTimer to deliver constant tone
        self.beep_loop = QtCore.QTimer(timeout=self.play_beep, interval=10)
        self.sound_button.toggled.connect(
            lambda checked: (
                self.beep_loop.start() if checked else self.beep_loop.stop()
            )
        )
        self.sound_button.attenuationChanged.connect(self.change_attenuation)

        self.actionMeta_Data.triggered.connect(self._Metadata)
        self.action_Optogenetics.triggered.connect(self._Optogenetics)
        self.actionLicks_sta.triggered.connect(self._LickSta)
        self.actionTime_distribution.triggered.connect(self._TimeDistribution)
        self.action_Calibration.triggered.connect(self._WaterCalibration)
        self.actionLaser_Calibration.triggered.connect(self._LaserCalibration)
        self.action_create_from_local_session.triggered.connect(
            self.load_local_session
        )
        self.action_Save.triggered.connect(self._Save)
        self.actionForce_save.triggered.connect(self._ForceSave)
        self.SaveAs.triggered.connect(self._SaveAs)
        self.Save_continue.triggered.connect(self._Save_continue)
        self.action_Exit.triggered.connect(self._Exit)
        self.action_New.triggered.connect(self._NewSession)
        self.action_Start.triggered.connect(self.Start.click)
        self.action_NewSession.triggered.connect(self.NewSession.click)
        self.actionConnectBonsai.triggered.connect(self._ConnectBonsai)
        self.actionReconnect_bonsai.triggered.connect(self._ReconnectBonsai)
        self.Load.clicked.connect(self.mouse_selector_dialog.show)
        self.Save.setCheckable(True)
        self.Save.clicked.connect(self._Save)
        self.Start.clicked.connect(self._Start)
        self.GiveLeft.clicked.connect(lambda: self.give_manual_water("Left"))
        self.GiveRight.clicked.connect(lambda: self.give_manual_water("Right"))
        self.NewSession.clicked.connect(self._NewSession)
        self.StartFIP.clicked.connect(self._StartFIP)
        self.StartExcitation.clicked.connect(self._StartExcitation)
        self.StartBleaching.clicked.connect(self._StartBleaching)
        self.OptogeneticsB.activated.connect(
            self._OptogeneticsB
        )  # turn on/off optogenetics
        self.OptogeneticsB.currentIndexChanged.connect(
            lambda: self._QComboBoxUpdate(
                "Optogenetics", self.OptogeneticsB.currentText()
            )
        )
        self.TargetRatio.textChanged.connect(self._UpdateSuggestedWater)
        self.WeightAfter.textChanged.connect(self._PostWeightChange)
        self.BaseWeight.textChanged.connect(self._UpdateSuggestedWater)
        self.actionTemporary_Logging.triggered.connect(
            self._startTemporaryLogging
        )
        self.actionFormal_logging.triggered.connect(self._startFormalLogging)
        self.actionOpen_logging_folder.triggered.connect(
            self._OpenLoggingFolder
        )
        self.actionOpen_behavior_folder.triggered.connect(
            self._OpenBehaviorFolder
        )
        self.actionOpenSettingFolder.triggered.connect(self._OpenSettingFolder)
        self.actionOpen_rig_metadata_folder.triggered.connect(
            self._OpenRigMetadataFolder
        )
        self.actionOpen_metadata_dialog_folder.triggered.connect(
            self._OpenMetadataDialogFolder
        )
        self.actionOpen_video_folder.triggered.connect(self._OpenVideoFolder)
        self.MoveXP.clicked.connect(self._MoveXP)
        self.MoveYP.clicked.connect(self._MoveYP)
        self.MoveZP.clicked.connect(self._MoveZP)
        self.MoveXN.clicked.connect(self._MoveXN)
        self.MoveYN.clicked.connect(self._MoveYN)
        self.MoveZN.clicked.connect(self._MoveZN)
        self.StageStop.clicked.connect(self._StageStop)
        self.GetPositions.clicked.connect(self._GetPositions)
        self.StartEphysRecording.clicked.connect(self._StartEphysRecording)
        self.SetReference.clicked.connect(self._set_reference)
        self.Opto_dialog.laser_1_calibration_voltage.textChanged.connect(
            self._toggle_save_color
        )
        self.Opto_dialog.laser_2_calibration_voltage.textChanged.connect(
            self._toggle_save_color
        )
        self.Opto_dialog.laser_1_calibration_power.textChanged.connect(
            self._toggle_save_color
        )
        self.Opto_dialog.laser_2_calibration_power.textChanged.connect(
            self._toggle_save_color
        )
        self.pushButton_streamlit.clicked.connect(
            self._open_mouse_on_streamlit
        )
        self.on_curriculum.clicked.connect(self.off_curriculum)

        # hook up mouse selector signals
        self.mouse_selector_dialog.acceptedMouseID.connect(
            lambda: self.geometry().center()
        )
        self.mouse_selector_dialog.acceptedMouseID.connect(
            lambda: self.Load.setEnabled(False)
        )
        self.mouse_selector_dialog.acceptedMouseID.connect(
            self.load_slims_progress.show
        )
        self.mouse_selector_dialog.acceptedMouseID.connect(
            self.create_load_mouse_worker
        )

        # add validator for weight and water fields
        double_validator = QtGui.QDoubleValidator()
        self.BaseWeight.setValidator(double_validator)
        self.TargetWeight.setValidator(double_validator)
        self.TargetRatio.setValidator(double_validator)
        self.TotalWater.setValidator(double_validator)
        self.WeightAfter.setValidator(double_validator)
        self.SuggestedWater.setValidator(double_validator)

        if hasattr(
            self, "current_stage"
        ):  # Connect newscale button to update operational control model
            self.MoveXP.clicked.connect(
                self.update_operational_control_stage_positions
            )
            self.MoveYP.clicked.connect(
                self.update_operational_control_stage_positions
            )
            self.MoveZP.clicked.connect(
                self.update_operational_control_stage_positions
            )
            self.MoveXN.clicked.connect(
                self.update_operational_control_stage_positions
            )
            self.MoveYN.clicked.connect(
                self.update_operational_control_stage_positions
            )
            self.MoveZN.clicked.connect(
                self.update_operational_control_stage_positions
            )

        elif self.stage_widget is not None:
            view = self.stage_widget.movement_page_view

            # connect aind stage widgets to update loaded mouse offset if text has been changed by user or button press
            view.lineEdit_z.textChanged.connect(
                lambda v: Thread(
                    target=self.update_loaded_mouse_offset
                ).start()
            )
            view.lineEdit_x.textChanged.connect(
                lambda v: Thread(
                    target=self.update_loaded_mouse_offset
                ).start()
            )
            view.lineEdit_y1.textChanged.connect(
                lambda v: Thread(
                    target=self.update_loaded_mouse_offset
                ).start()
            )
            view.lineEdit_y2.textChanged.connect(
                lambda v: Thread(
                    target=self.update_loaded_mouse_offset
                ).start()
            )

            # Connect aind stage widgets to update operational control model
            view.lineEdit_z.textChanged.connect(
                self.update_operational_control_stage_positions
            )
            view.lineEdit_x.textChanged.connect(
                self.update_operational_control_stage_positions
            )
            view.lineEdit_y1.textChanged.connect(
                self.update_operational_control_stage_positions
            )
            view.lineEdit_y2.textChanged.connect(
                self.update_operational_control_stage_positions
            )
            view.lineEdit_step_size.textEdited.connect(
                lambda v: setattr(
                    self.operation_control_model.stage_specs,
                    "step_size",
                    float(v),
                )
            )

    def create_load_mouse_worker(self) -> None:
        """
        Creates worker for slims handler to load in mouse. Since loading in mouse requires updating widgets,
        put loading from slims in thread and then update ui once finished.
        """

        continue_load = self._NewSession()

        if not continue_load:
            return

        self.load_mouse_worker = Worker(
            fn=self.slims_handler.load_mouse_curriculum,
            mouse_id=self.mouse_selector_dialog.combo.currentText(),
        )
        self.load_mouse_worker.signals.result.connect(
            lambda args: self.load_curriculum(*args)
        )
        self.load_mouse_worker.signals.finished.connect(
            self.load_slims_progress.hide
        )
        self.load_mouse_thread.start(self.load_mouse_worker)

    def update_loaded_mouse_offset(self):
        """
        Update the stage offset associated with mouse model from slims with aind stage coordinates
        """
        current_positions = self._GetPositions()
        if current_positions is None:
            logging.info(
                "Can't update loaded mouse position because no stage is connected."
            )
            return

        elif list(current_positions.keys()) == ["x", "y", "z"]:
            logging.debug(
                "Can't update loaded mouse offset with non AIND stage coordinates."
            )
        else:
            x = self.stage_widget.movement_page_view.lineEdit_x.text()
            y = self.stage_widget.movement_page_view.lineEdit_y1.text()
            z = self.stage_widget.movement_page_view.lineEdit_z.text()
            # use widget values since current position isn't updated yet
            self.slims_handler.set_loaded_mouse_offset(
                None if x == "" else float(x),
                None if y == "" else float(y),
                None if z == "" else float(z),
            )

    def update_operational_control_stage_positions(self, *args) -> None:
        """
        Update operational control model with the latest stage coordinates

        :params args: catchall for signal emit values
        """

        current_positions = self._GetPositions()
        if current_positions is None:
            logging.info(
                "Can't update loaded mouse position because no stage is connected."
            )
            return

        self.operation_control_model.stage_specs.x = current_positions["x"]
        self.operation_control_model.stage_specs.z = current_positions["z"]
        # use y key and default to y1 key if not in dict
        self.operation_control_model.stage_specs.y = current_positions.get(
            "y"
        ) or current_positions.get("y1")

    def update_stage_positions_from_operational_control(
        self, oc: OperationalControl = None
    ) -> None:
        """
        Update stage position based on operational control model

        :param oc: optional model to use for stage position. If None, use operational_control attribute.
        """

        oc = oc if oc is not None else self.operation_control_model

        if oc.stage_specs is None:
            logging.info(
                "Cannot move stage as stage specs are not defined in operational control model."
            )
            return
        # determine how stage should be moved.
        last_positions = {
            "x": oc.stage_specs.x,
            "y": oc.stage_specs.y,
            "z": oc.stage_specs.z,
        }
        positions = self._GetPositions()
        none_pos = {"x": None, "y": None, "z": None}

        # check aind stage
        if self.stage_widget is not None and last_positions != none_pos:
            if (
                oc.stage_specs.stage_name == "AIND"
            ):  # coordinates in oc model also come from aind stage
                logging.info(
                    "Using coordinates in loaded operational control model."
                )
                last_positions = {
                    "x": oc.stage_specs.x,
                    "y": oc.stage_specs.y,
                    "z": oc.stage_specs.z,
                }

            else:  # coordinates in oc model also come from newscale stage and can't be applied
                logging.info(
                    "Coordinates in loaded operational control model come from newscale stage which does "
                    "not match current stage. Checking slims for location."
                )
                last_positions = (
                    self.slims_handler.get_loaded_mouse_offset()
                )  # check if slims has offset
                if last_positions == none_pos:
                    logging.info(
                        "No offset coordinates found in Slims. Not moving stage.",
                        extra={"tags": [self.warning_log_tag]},
                    )

            positions = {
                0: (
                    positions["x"]
                    if last_positions["x"] is None
                    else float(last_positions["x"])
                ),
                1: (
                    positions["y1"]
                    if last_positions["y"] is None
                    else float(last_positions["y"])
                ),
                2: (
                    positions["y2"]
                    if last_positions["y"] is None
                    else float(last_positions["y"])
                ),
                3: (
                    positions["z"]
                    if last_positions["z"] is None
                    else float(last_positions["z"])
                ),
            }
            self.stage_widget.blockSignals(True)
            self.stage_widget.stage_model.update_position(positions)
            if oc.stage_specs.step_size:  # update step size
                self.stage_widget.stage_model.update_step_size(
                    oc.stage_specs.step_size
                )
                self.stage_widget.movement_page_view.lineEdit_step_size.setText(
                    str(oc.stage_specs.step_size)
                )
            self.stage_widget.blockSignals(False)

        # check newscale stage
        elif (
            hasattr(self, "current_stage") and last_positions != none_pos
        ):  # newscale stage
            # coordinates in oc model come from same newscale stage and can be used
            if (
                oc.stage_specs.stage_name == "newscale"
                and oc.stage_specs.rig_name == self.current_box
            ):
                logging.info(
                    "Using coordinates in loaded operational control model."
                )
                last_positions = {
                    k: v if v is not None else positions[k]
                    for k, v in last_positions.items()
                }
                last_positions_lst = list(last_positions.values())

                self.current_stage.move_absolute_3d(*last_positions_lst)
                self._UpdatePosition(last_positions_lst, (0, 0, 0))
            else:
                # don't do anything if oc model stage isn't newscal and not from box being used
                logging.info(
                    f"Cannot move stage since last session was run using {oc.stage_specs.stage_name} and"
                    f" on {oc.stage_specs.rig_name}",
                    extra={"tags": [self.warning_log_tag]},
                )
        else:
            logging.info(
                f"Cannot move stage with last position {last_positions}.",
                extra={"tags": [self.warning_log_tag]},
            )

    def load_curriculum(
        self,
        trainer_state: Optional[DynamicForagingTrainerState],
        slims_session: Optional[SlimsBehaviorSession],
        task: Optional[AindDynamicForagingTaskLogic],
        sess: Optional[AindBehaviorSessionModel],
        opto: Optional[Optogenetics],
        fip: Optional[FiberPhotometry],
        oc: Optional[OperationalControl],
        mouse_id: str,
    ) -> None:
        """
        Load curriculum based on models

        :param trainer_state: trainer state loaded from slims. None if nothing on slims found.
        :param slims_session: slims model of session loaded from slims. None if nothing on slims found.
        :param task: task model found as an attachment from slims. None if nothing on slims found.
        :param sess: session model found as an attachment from slims. None if nothing on slims found.
        :param opto: optogenetic model found as an attachment from slims. None if nothing on slims found.
        :param fip: fiber photometery model found as an attachment from slims. None if nothing on slims found.
        :param oc: operational control model found as an attachment from slims. None if nothing on slims found.
        :param mouse_id: mouse id to loaded
        """

        try:
            if trainer_state is None:  # no curriculum in slims for this mouse
                logging.info(
                    f"Attempting to create curriculum for mouse {mouse_id} from schedule."
                )
                trainer_state, slims_session, task, sess, opto, fip, oc = (
                    self.create_curriculum(mouse_id)
                )

            # update models
            self.task_logic = task
            self.opto_model = opto if opto else self.opto_model

            self.fip_model = fip if fip else self.fip_model
            mode = self._GetInfoFromSchedule(mouse_id, "FIP Mode")
            if (
                not (isinstance(mode, float) and math.isnan(mode))
                and mode is not None
            ):  # schedule has input for fip
                stage_list = get_args(STAGE_STARTS)
                stage_mapping = [
                    "1.1",
                    "1.2",
                    "2",
                    "3",
                    "4",
                    "FINAL",
                    "GRADUATED",
                ]
                start = self._GetInfoFromSchedule(mouse_id, "First FP Stage")
                first = (
                    "stage_1_warmup"
                    if (isinstance(start, float) and math.isnan(start))
                    else stage_list[stage_mapping.index(start)]
                )
                # check if current stage is past stage_start and enable if so
                self.fip_model = FiberPhotometry(
                    mode=mode,
                    stage_start=first,
                    enabled=stage_list.index(trainer_state.stage.name)
                    >= stage_list.index(self.fip_model.stage_start),
                )

            # update session model only partially
            self.session_model.experiment = sess.experiment
            self.session_model.experimenter = sess.experimenter
            self.session_model.subject = sess.subject
            self.session_model.notes = self.session_model.notes

            # enable or disable widget based on if session is on curriculum
            self.task_widget.setEnabled(
                not slims_session.is_curriculum_suggestion
            )

            # set state of on_curriculum check
            self.on_curriculum.setChecked(
                slims_session.is_curriculum_suggestion
            )
            self.on_curriculum.setEnabled(
                slims_session.is_curriculum_suggestion
            )
            self.update_stage_positions_from_operational_control(oc)

            # update operational control model with latest stage coords
            self.update_operational_control_stage_positions()

            logging.info(
                f"Successfully loaded mouse {mouse_id} on {trainer_state.stage.name} ",
                extra={"tags": [self.warning_log_tag]},
            )

            # update gui
            self.update_model_widgets()
            self.on_curriculum.setVisible(True)
            self.label_curriculum_stage.setText(trainer_state.stage.name)
            self.label_curriculum_stage.setStyleSheet(
                "color: rgb(0, 214, 103);"
            )
            self.BaseWeight.setText(
                str(self.slims_handler.loaded_slims_mouse.baseline_weight_g)
            )

        except Exception as e:
            logging.error(str(e), extra={"tags": [self.warning_log_tag]})
            self.Load.setEnabled(True)

    def create_curriculum(self, mouse_id) -> tuple[
        DynamicForagingTrainerState or None,
        SlimsBehaviorSession or None,
        AindDynamicForagingTaskLogic or None,
        AindBehaviorSessionModel or None,
        Optogenetics or None,
        FiberPhotometry or None,
        OperationalControl or None,
    ]:
        """
        Create curriculum based on schedule
        :params mouse_id: mouse id string to load from slims
        """

        # define mapping between schedule and curriculums
        curriculum_mapping = CURRICULUM_SCHEDULE_NAME_MAPPER

        # gather keys from schedule
        logging.info("Gathering curriculum keys from schedule.")
        autotrain_curriculum_name = self._GetInfoFromSchedule(
            mouse_id, "Autotrain Curriculum Name"
        )
        curriculum_version = self._GetInfoFromSchedule(
            mouse_id, "Curriculum Version"
        )

        key = f"{autotrain_curriculum_name} {curriculum_version}"
        if key not in curriculum_mapping.keys():
            raise KeyError(
                f"Curriculum {key} as defined in the schedule is not a valid curriculum. "
                f"Valid curriculums are {curriculum_mapping.keys()}"
            )

        # import and instantiate curriculum
        logging.info("Importing and instantiating curriculum")
        module = curriculum_mapping[key]
        creation_factory_name = f"construct_{module}_curriculum"
        curriculum = getattr(
            import_module(
                f"aind_behavior_dynamic_foraging.CurriculumManager.curriculums.{module}"
            ),
            creation_factory_name,
        )()

        # create trainer state
        stages = curriculum.see_stages()
        stage_mapping = {
            "nan": 0,
            "1.1": 0,
            "1.2": 1,
            "FINAL": -1,
            "GRADUATED": -2,
        }
        stage = self._GetInfoFromSchedule(mouse_id, "Current Stage")
        index = (
            0
            if isinstance(stage, float) and math.isnan(stage)
            else stage_mapping.get(stage, int(stage))
        )
        logging.info("Creating trainer state")
        ts = TrainerState(
            stage=stages[index], curriculum=curriculum, is_on_curriculum=True
        )

        # create metrics from docdb
        sessions = (
            self.slims_handler.trainer.docdb_client.retrieve_docdb_records(
                filter_query={
                    "name": {
                        "$regex": f"^behavior_{mouse_id}(?!.*processed).*"
                    }
                }
            )
        )
        session_total = len(sessions)
        sessions = [
            session for session in sessions if session["session"] is not None
        ]  # sort out none types
        sessions.sort(
            key=lambda session: session["session"]["session_start_time"]
        )  # sort based on time
        epochs = [
            session["session"]["stimulus_epochs"][0] for session in sessions
        ]
        finished_trials = [epoch["trials_finished"] for epoch in epochs]
        foraging_efficiency = [
            epoch["output_parameters"]["performance"]["foraging_efficiency"]
            for epoch in epochs
        ]
        logging.info("Creating metrics.")
        metrics = DynamicForagingMetrics(
            foraging_efficiency=foraging_efficiency,
            finished_trials=finished_trials,
            session_total=session_total,
            session_at_current_stage=0,
        )

        # set loaded mouse in slims handler to be able to write after session
        logging.info("Creating metrics.")
        self.slims_handler.set_loaded_mouse(mouse_id, metrics, ts, curriculum)

        # update session model
        self.session_model.experiment = autotrain_curriculum_name
        self.session_model.experimenter = [
            str(self._GetInfoFromSchedule(mouse_id, "Trainer"))
        ]
        self.session_model.subject = mouse_id
        self.session_model.notes = (
            ""
            if math.isnan(self._GetInfoFromSchedule(mouse_id, "RA Notes"))
            else str(self._GetInfoFromSchedule(mouse_id, "RA Notes"))
        )

        # update fip model
        mode = self._GetInfoFromSchedule(mouse_id, "FIP Mode")
        if not (
            isinstance(mode, float) and math.isnan(mode)
        ):  # schedule has input for fip
            stage_list = get_args(STAGE_STARTS)
            stage_mapping = ["1.1", "1.2", "2", "3", "4", "FINAL", "GRADUATED"]
            start = self._GetInfoFromSchedule(mouse_id, "First FP Stage")
            first = (
                "stage_1_warmup"
                if math.isnan(start)
                else stage_list[stage_mapping.index(start)]
            )
            # check if current stage is past stage_start and enable if so
            self.fip_model = FiberPhotometry(
                mode=mode,
                stage_start=first,
                enabled=stage_list.index(ts.stage.name)
                >= stage_list.index(self.fip_model.stage_start),
            )

        else:  # set fip model to clear
            self.fip_model.enabled = False

        # clear opto info
        self.opto_model.laser_colors = []

        # create slims session model
        sbs = SlimsBehaviorSession(
            task_stage=ts.stage.name,
            task=curriculum.name,
            task_schema_version=curriculum.version,
            is_curriculum_suggestion=True,
        )

        return (
            ts,
            sbs,
            ts.stage.task,
            self.session_model,
            self.opto_model,
            self.fip_model,
            self.operation_control_model,
        )

    def load_local_session(self) -> None:
        """
        Load session from local drive.

        """

        # stop current session first
        self._StopCurrentSession()

        # check if user wants to load new session
        new_session = self._NewSession()

        if not new_session:
            return

        # Open dialog box
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            self.default_openFolder + "\\" + self.current_box,
        )
        logging.info("User selected: {}".format(folder_path))

        if not folder_path:
            return

        # dict to easily access model class and function to translate behavior json into model
        schema_map = {
            "task_logic": {
                "model": AindDynamicForagingTaskLogic,
                "map": behavior_json_to_task_logic_model,
            },
            "session": {
                "model": AindBehaviorSessionModel,
                "map": behavior_json_to_session_model,
            },
            "optogenetics": {
                "model": Optogenetics,
                "map": behavior_json_to_opto_model,
            },
            "fiber_photometry": {
                "model": FiberPhotometry,
                "map": behavior_json_to_fip_model,
            },
            "operational_control": {
                "model": OperationalControl,
                "map": behavior_json_to_operational_control_model,
            },
        }

        # dict to keep track if all models are in folder
        loaded = {
            **{k: False for k in schema_map.keys()},
            "behavior_json": False,
        }
        # regex to check filename starts against schema_map key
        pattern = re.compile(
            rf"^behavior_({'|'.join(re.escape(k) for k in schema_map.keys())})_model"
        )

        # iterate through files
        for filename in os.listdir(folder_path):
            joined = os.path.join(folder_path, filename)

            # check if file is serialized model based on regex
            match = pattern.match(filename)
            if match:
                key = match.group(1)
                model = schema_map[key]["model"]
                with open(joined, "r") as f:
                    loaded[key] = model(**json.load(f))

            # check and load behavior json
            elif re.fullmatch(
                r"^\d+_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.json$", filename
            ):
                loaded["behavior_json"] = True
                with open(joined, "r") as f:
                    Obj = json.load(f)
            elif re.fullmatch(
                r"^\d+_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.mat$", filename
            ):
                loaded["behavior_json"] = True
                Obj = loadmat(joined)
                # this is a bug to use the scipy.io.loadmat or savemat (it will change the dimension of the nparray)
                Obj.B_AnimalResponseHistory = Obj.B_AnimalResponseHistory[0]
                Obj.B_TrialStartTime = Obj.B_TrialStartTime[0]
                Obj.B_DelayStartTime = Obj.B_DelayStartTime[0]
                Obj.B_TrialEndTime = Obj.B_TrialEndTime[0]
                Obj.B_GoCueTime = Obj.B_GoCueTime[0]
                Obj.B_RewardOutcomeTime = Obj.B_RewardOutcomeTime[0]

        if any(
            not value for value in loaded.values()
        ):  # if any of the required files are missing
            not_loaded = [key for key, value in loaded.items() if not value]
            try:
                if "behavior_json" not in not_loaded:
                    logger.info(
                        f"Models {not_loaded} are not found. Trying to create models from behavior json."
                    )
                    for key in not_loaded:
                        loaded[key] = schema_map[key]["map"](Obj)
                else:
                    raise ValueError(
                        "behavior json not found so models cannot be reconstructed."
                    )

            except Exception as e:
                logger.warning(
                    f"Can't load mouse in folder {folder_path}: {str(e)}"
                )
                return

        try:  # check slims for curriculum and go off curriculum if user would like
            ts, slims_session, *args = (
                self.slims_handler.load_mouse_curriculum(
                    loaded["session"].subject
                )
            )
            if (
                ts is not None and slims_session.is_curriculum_suggestion
            ):  # mouse has next session set in slims
                reply = self.off_curriculum(
                    False
                )  # check if user wants to go off curriculum for this mouse
                if reply == QMessageBox.No:  # return before updating models
                    return
        except Exception as e:
            if "No record found" not in str(
                e
            ):  # mouse may exist but another error occured
                logging.error(
                    f"Error loading mouse {loaded['session'].subject} curriculum loaded from Slims. {e}"
                )

        # update models
        self.task_logic = loaded["task_logic"]
        # TODO: Should I update the path and the date for the session model?
        self.session_model.experiment = loaded["session"].experiment
        self.session_model.experimenter = loaded["session"].experimenter
        self.session_model.subject = loaded["session"].subject
        self.session_model.notes = loaded["session"].notes
        self.operation_control_model = loaded["operational_control"]
        self.opto_model = loaded["optogenetics"]
        self.fip_model = loaded["fiber_photometry"]


        self.Obj = Obj
        self._LoadVisualization()
        # check dropping frames
        self.to_check_drop_frames = 1
        self._check_drop_frames(save_tag=0)
        self.StartExcitation.setChecked(False)

        # Set stage position to last position
        self.update_stage_positions_from_operational_control()

        self.update_model_widgets()

        logging.info(
            f"Successfully opened mouse {self.session_model.subject}.",
            extra={"tags": [self.warning_log_tag]},
        )
        self.load_tag = 1

    def write_curriculum(self):
        """
        Write curriculum to slims for next session
        """
        # add session to slims if there are trials and mouse loaded
        if (
            hasattr(self, "GeneratedTrials")
            and self.slims_handler.loaded_slims_mouse is not None
        ):
            try:
                trainer_state = self.slims_handler.write_loaded_mouse(
                    self.GeneratedTrials.B_for_eff_optimal,
                    self.GeneratedTrials.B_CurrentTrialN,
                    self.task_logic,
                    self.session_model,
                    self.opto_model,
                    self.fip_model,
                    self.operation_control_model,
                )
                logging.info(
                    f"Writing next session to Slims successful. Mouse {self.session_model.subject} will run"
                    f" on {trainer_state.stage.name} next session.",
                    extra={"tags": [self.warning_log_tag]},
                )
                # save trainer_state
                id_name = self.session_model.session_name.split("behavior_")[
                    -1
                ]
                with open(
                    os.path.join(
                        self.session_model.root_path,
                        f"trainer_state_{id_name}.json",
                    ),
                    "w",
                ) as outfile:
                    outfile.write(trainer_state.model_dump_json(indent=1))

                self.on_curriculum.setChecked(False)
                self.on_curriculum.setVisible(False)
                self.label_curriculum_stage.setText("")

            except Exception as e:
                logging.error(str(e), extra={"tags": [self.warning_log_tag]})

        else:
            logging.info("No mouse loaded.")

    def update_curriculum_attachments(self) -> None:
        """
        Update attachments with model attributes
        """

        try:
            self.slims_handler.update_loaded_session_attachments(
                AindBehaviorSessionModel.__name__,
                self.session_model.model_dump_json(),
            )
            self.slims_handler.update_loaded_session_attachments(
                self.operation_control_model.name,
                self.operation_control_model.model_dump_json(),
            )
            self.slims_handler.update_loaded_session_attachments(
                self.fip_model.name, self.fip_model.model_dump_json()
            )
            self.slims_handler.update_loaded_session_attachments(
                self.opto_model.name, self.opto_model.model_dump_json()
            )
            # Update with curriculum that actually ran
            if (
                not self.slims_handler.loaded_slims_session.is_curriculum_suggestion
            ):
                ts, *args = self.slims_handler.load_mouse_curriculum(
                    self.session_model.subject
                )
                ts.stage.task = self.task_logic
                self.slims_handler.update_loaded_session_attachments(
                    "TrainerState", ts.model_dump_json()
                )

            logging.info("Successfully updated attachments")

        except KeyError as e:
            logging.error(
                f"Error updating mouse {self.session_model.subject} session in slims: {e}"
            )

    def _set_reference(self):
        """
        set the reference point for lick spout position in the metadata dialog
        """
        # get the current position of the stage
        current_positions = self._GetPositions()
        # set the reference point for lick spout position in the metadata dialog
        if current_positions is not None:
            self.Metadata_dialog._set_reference(current_positions)

    def _StartEphysRecording(self):
        """
        Start/stop ephys recording

        """
        if self.open_ephys_machine_ip_address == "":
            QMessageBox.warning(
                self,
                "Connection Error",
                "Empty ip address for Open Ephys Computer. Please check the settings file.",
            )
            self.StartEphysRecording.setChecked(False)
            self._toggle_color(self.StartEphysRecording)
            return

        if (
            self.Start.isChecked() or self.ANewTrial == 0
        ) and self.StartEphysRecording.isChecked():
            reply = QMessageBox.question(
                self,
                "",
                "Behavior has started! Do you want to start ephys recording?",
                QMessageBox.No | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                pass
            elif reply == QMessageBox.No:
                self.StartEphysRecording.setChecked(False)
                self._toggle_color(self.StartEphysRecording)
                return

        EphysControl = EphysRecording(
            open_ephys_machine_ip_address=self.open_ephys_machine_ip_address,
            mouse_id=self.session_model.subject,
        )
        if self.StartEphysRecording.isChecked():
            try:
                if EphysControl.get_status()["mode"] == "RECORD":
                    QMessageBox.warning(
                        self,
                        "",
                        "Open Ephys is already recording! Please stop the recording first.",
                    )
                    self.StartEphysRecording.setChecked(False)
                    self._toggle_color(self.StartEphysRecording)
                    return
                EphysControl.start_open_ephys_recording()
                self.openephys_start_recording_time = str(datetime.now())
                QMessageBox.warning(
                    self,
                    "",
                    f"Open Ephys has started recording!\n Recording type: {self.OpenEphysRecordingType.currentText()}",
                )
            except Exception:
                logging.error(traceback.format_exc())
                self.StartEphysRecording.setChecked(False)
                QMessageBox.warning(
                    self,
                    "Connection Error",
                    "Failed to connect to Open Ephys. Please check: \n1) the correct ip address is "
                    "included in the settings json file. \n2) the Open Ephys software is open.",
                )
        else:
            try:
                if EphysControl.get_status()["mode"] != "RECORD":
                    QMessageBox.warning(
                        self,
                        "",
                        "Open Ephys is not recording! Please start the recording first.",
                    )
                    self.StartEphysRecording.setChecked(False)
                    self._toggle_color(self.StartEphysRecording)
                    return

                if self.Start.isChecked() or self.ANewTrial == 0:
                    reply = QMessageBox.question(
                        self,
                        "",
                        "The behavior hasn’t stopped yet! Do you want to stop ephys recording?",
                        QMessageBox.No | QMessageBox.No,
                        QMessageBox.Yes,
                    )
                    if reply == QMessageBox.Yes:
                        pass
                    elif reply == QMessageBox.No:
                        self.StartEphysRecording.setChecked(True)
                        self._toggle_color(self.StartEphysRecording)
                        return

                self.openephys_stop_recording_time = str(datetime.now())
                response = (
                    EphysControl.get_open_ephys_recording_configuration()
                )
                response["openephys_start_recording_time"] = (
                    self.openephys_start_recording_time
                )
                response["openephys_stop_recording_time"] = (
                    self.openephys_stop_recording_time
                )
                response["recording_type"] = (
                    self.OpenEphysRecordingType.currentText()
                )
                self.open_ephys.append(response)
                self.unsaved_data = True
                # self.Save.setStyleSheet("color: white;background-color : mediumorchid;")
                self.start_flash.start()
                EphysControl.stop_open_ephys_recording()
                QMessageBox.warning(
                    self,
                    "",
                    "Open Ephys has stopped recording! Please save the data again!",
                )
            except Exception:
                logging.error(traceback.format_exc())
                QMessageBox.warning(
                    self,
                    "Connection Error",
                    "Failed to stop Open Ephys recording. Please check: \n1) the open ephys software is still running",
                )
        self._toggle_color(self.StartEphysRecording)

    def _toggle_color(
        self,
        widget,
        check_color="background-color : green;",
        unchecked_color="background-color : none",
    ):
        """
        Toggle the color of the widget.

        Parameters
        ----------
        widget : QtWidgets.QWidget

            If Checked, sets the color to green. If unchecked, sets the color to None.

        Returns
        -------
        None
        """

        if widget.isChecked():
            widget.setStyleSheet(check_color)
        else:
            widget.setStyleSheet(unchecked_color)

    def off_curriculum(
        self, checked
    ) -> Union[QMessageBox.StandardButton, None]:
        """
        Function to handle going off curriculum.
        :param checked: if on_curriculum checkbox is checked or not
        """

        if not checked:  # user wants to go off curriculum
            msg = QMessageBox()
            msg.setWindowTitle("Off Curriculum")
            msg.setText(
                "You are going off curriculum. Are you absolutely sure you would like to do this? "
                "<span style='color: mediumorchid;'>Once you do this, there is no going back. </span><br>"
                "This could be really annoying."
            )
            msg.setStyleSheet(
                "QLabel{font-size: 25px; font-weight: bold;}"
            )  # Apply to text
            msg.setIcon(QMessageBox.Question)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            reply = msg.exec_()

            if reply == QMessageBox.No:
                self.on_curriculum.setChecked(True)
            else:
                self.task_widget.setEnabled(True)
                self.session_widget.setEnabled(True)
                self.fip_widget.setEnabled(True)
                self.Opto_dialog.opto_widget.setEnabled(True)
                self.on_curriculum.setEnabled(False)
                self.slims_handler.go_off_curriculum()  # update slims model to be off curriculum

            return reply

    def _check_drop_frames(self, save_tag=1):
        """check if there are any drop frames in the video"""
        if self.to_check_drop_frames == 1:
            return_tag = 0
            if save_tag == 0:
                if "drop_frames_warning_text" in self.Obj:
                    self.drop_frames_warning_text = self.Obj[
                        "drop_frames_warning_text"
                    ]
                    self.drop_frames_tag = self.Obj["drop_frames_tag"]
                    self.trigger_length = self.Obj["trigger_length"]
                    self.frame_num = self.Obj["frame_num"]
                    return_tag = 1
            if return_tag == 0:
                self.drop_frames_tag = 0
                self.trigger_length = 0
                self.drop_frames_warning_text = ""
                self.frame_num = {}
                use_default_folder_structure = 0
                if save_tag == 1:
                    # check the drop frames of the current session
                    if hasattr(self, "HarpFolder"):
                        HarpFolder = self.HarpFolder
                        video_folder = self.VideoFolder
                    else:
                        use_default_folder_structure = 1
                elif save_tag == 0:
                    if "HarpFolder" in self.Obj:
                        # check the drop frames of the loaded session
                        HarpFolder = self.Obj["HarpFolder"]
                        video_folder = self.Obj["VideoFolder"]
                    else:
                        use_default_folder_structure = 1
                if use_default_folder_structure:
                    # use the default folder structure
                    HarpFolder = os.path.join(
                        os.path.dirname(os.path.dirname(self.fname)),
                        "HarpFolder",
                    )  # old folder structure
                    video_folder = os.path.join(
                        os.path.dirname(os.path.dirname(self.fname)),
                        "VideoFolder",
                    )  # old folder structure
                    if not os.path.exists(HarpFolder):
                        HarpFolder = os.path.join(
                            os.path.dirname(self.fname), "raw.harp"
                        )  # new folder structure
                        video_folder = os.path.join(
                            os.path.dirname(os.path.dirname(self.fname)),
                            "behavior-videos",
                        )  # new folder structure

                camera_trigger_file = os.path.join(
                    HarpFolder, "BehaviorEvents", "Event_94.bin"
                )
                if os.path.exists(camera_trigger_file):
                    # sleep some time to wait for the finish of saving video
                    time.sleep(5)
                    triggers = harp.read(camera_trigger_file)
                    self.trigger_length = len(triggers)
                elif len(os.listdir(video_folder)) == 0:
                    # no video data saved.
                    self.trigger_length = 0
                    self.to_check_drop_frames = 0
                    return
                elif ("HighSpeedCamera" in self.SettingsBox) and (
                    self.SettingsBox["HighSpeedCamera"] == 1
                ):
                    self.trigger_length = 0
                    logging.error(
                        "Saved video data, but no camera trigger file found"
                    )
                    logging.info(
                        "No camera trigger file found!",
                        extra={"tags": [self.warning_log_tag]},
                    )
                    return
                else:
                    logging.info(
                        "Saved video data, but not using high speed camera - skipping drop frame check"
                    )
                    self.trigger_length = 0
                    self.to_check_drop_frames = 0
                    return
                csv_files = [
                    file
                    for file in os.listdir(video_folder)
                    if file.endswith(".csv")
                ]
                avi_files = [
                    file
                    for file in os.listdir(video_folder)
                    if file.endswith(".avi")
                ]

                for avi_file in avi_files:
                    csv_file = avi_file.replace(".avi", ".csv")
                    camera_name = avi_file.replace(".avi", "")
                    if csv_file not in csv_files:
                        self.drop_frames_warning_text += (
                            f"No csv file found for {avi_file}"
                        )
                    else:
                        current_frames = pd.read_csv(
                            os.path.join(video_folder, csv_file), header=None
                        )
                        num_frames = len(current_frames)
                        if num_frames != self.trigger_length:
                            this_text = f"Error: {avi_file} has {num_frames} frames, but {self.trigger_length} triggers. "
                            self.drop_frames_warning_text += this_text
                            logging.error(
                                this_text,
                                extra={"tags": [self.warning_log_tag]},
                            )
                            self.drop_frames_tag = 1
                        else:
                            this_text = f"Correct: {avi_file} has {num_frames} frames and {self.trigger_length} triggers. "
                            self.drop_frames_warning_text += this_text
                            logging.info(
                                this_text,
                                extra={"tags": [self.warning_log_tag]},
                            )
                        self.frame_num[camera_name] = num_frames

            # only check drop frames once each session
            self.to_check_drop_frames = 0

    def _CheckStageConnection(self):
        """get the current position of the stage"""
        if hasattr(self, "current_stage") and self.current_stage.connected:
            logging.info("Checking stage connection")
            current_stage = self.current_stage
            current_stage.get_position()
            if not current_stage.connected:
                logging.error("lost stage connection")
                self._no_stage()

    def _GetPositions(self):
        """get the current position of the stage"""
        self._CheckStageConnection()

        if (
            hasattr(self, "current_stage") and self.current_stage.connected
        ):  # newscale stage
            logging.info("Grabbing current stage position")
            current_stage = self.current_stage
            current_position = current_stage.get_position()
            self._UpdatePosition(current_position, (0, 0, 0))
            return {
                axis: float(pos)
                for axis, pos in zip(["x", "y", "z"], current_position)
            }
        elif self.stage_widget is not None:  # aind stage
            # Get absolute position of motors in AIND stage
            positions = (
                self.stage_widget.stage_model.get_current_positions_mm()
            )
            return {
                "x": positions[0],
                "y1": positions[1],
                "y2": positions[2],
                "z": positions[3],
            }
        else:  # no stage
            logging.info("GetPositions called, but no current stage")
            return None

    def _StageStop(self):
        """Halt the stage"""
        self._CheckStageConnection()
        if hasattr(self, "current_stage") and self.current_stage.connected:
            logging.info("Stopping stage movement")
            current_stage = self.current_stage
            current_stage.halt()
        else:
            logging.info("StageStop pressed, but no current stage")

    def _Move(self, axis, step):
        """Move stage"""
        self._CheckStageConnection()
        try:
            if (not hasattr(self, "current_stage")) or (
                not self.current_stage.connected
            ):
                logging.info("Move Stage pressed, but no current stage")
                return
            logging.info("Moving stage")
            current_stage = self.current_stage
            current_position = current_stage.get_position()
            current_stage.set_speed(3000)
            current_stage.move_relative_1d(axis, step)
            if axis == "x":
                relative_postition = (step, 0, 0)
            elif axis == "y":
                relative_postition = (0, step, 0)
            elif axis == "z":
                relative_postition = (0, 0, step)
            self._UpdatePosition(current_position, relative_postition)
        except Exception:
            logging.error(traceback.format_exc())

    def _MoveXP(self):
        """Move X positively"""
        axis = "x"
        step = float(self.Step.text())
        self._Move(axis, step)

    def _MoveXN(self):
        """Move X negatively"""
        axis = "x"
        step = float(self.Step.text())
        self._Move(axis, -step)

    def _MoveYP(self):
        """Move Y positively"""
        axis = "y"
        step = float(self.Step.text())
        self._Move(axis, step)

    def _MoveYN(self):
        """Move Y negatively"""
        axis = "y"
        step = float(self.Step.text())
        self._Move(axis, -step)

    def _MoveZP(self):
        """Move Z positively"""
        axis = "z"
        step = float(self.Step.text())
        self._Move(axis, step)

    def _MoveZN(self):
        """Move Z negatively"""
        axis = "z"
        step = float(self.Step.text())
        self._Move(axis, -step)

    def _UpdatePosition(self, current_position, relative_postition):
        """Update the NewScale position"""
        NewPositions = [0, 0, 0]
        for i in range(len(current_position)):
            NewPositions[i] = current_position[i] + relative_postition[i]
            if NewPositions[i] < 0:
                NewPositions[i] = 0
            elif NewPositions[i] > 15000:
                NewPositions[i] = 15000
        self.PositionX.setText(str(NewPositions[0]))
        self.PositionY.setText(str(NewPositions[1]))
        self.PositionZ.setText(str(NewPositions[2]))

    def _InitializeMotorStage(self):
        """
        Scans for available newscale stages. Attempts to connect to the newscale stage
        defined by the serial number in the settings file. If it cannot connect for any reason
        it displays a warning in the motor stage box, and returns.

        Failure modes include: an error in scanning for stages, no stages found, no stage defined
        in the settings file, the defined stage not found, an error in connecting to the stage
        """

        # find available newscale stages
        logging.info("Scanning for newscale stages")
        try:
            self.instances = NewScaleSerialY.get_instances()
        except Exception as e:
            logging.error(
                "Could not find instances of NewScale Stage: {}".format(str(e))
            )
            self._no_stage()
            return

        # If we can't find any stages, return
        if len(self.instances) == 0:
            logging.info(
                "Could not find any instances of NewScale Stage",
                extra={"tags": [self.warning_log_tag]},
            )
            self._no_stage()
            return

        logging.info("found {} newscale stages".format(len(self.instances)))

        # Get the serial num from settings
        if not hasattr(
            self, "newscale_serial_num_box{}".format(self.box_number)
        ):
            logging.error("Cannot determine newscale serial num")
            self._no_stage()
            return
        self.newscale_serial_num = eval(
            "self.newscale_serial_num_box" + str(self.box_number)
        )
        if self.newscale_serial_num == "":
            logging.warning("No newscale serial number in settings file")
            self._no_stage()
            return

        # See if the serial num from settings is in the instances we found
        stage_index = 0
        stage_names = np.array(
            [str(instance.sn) for instance in self.instances]
        )
        index = np.where(stage_names == str(self.newscale_serial_num))[0]
        if len(index) == 0:
            self._no_stage()
            msg = "Could not find newscale with serial number: {}"
            logging.error(msg.format(self.newscale_serial_num))
            return
        else:
            stage_index = index[0]
            logging.info("Found the newscale stage from the settings file")

        # Setup connection
        newscale_stage_instance = self.instances[stage_index]
        self._connect_stage(newscale_stage_instance)

    def _no_stage(self):
        """
        Display a warrning message that the newscale stage is not connected
        """
        if hasattr(self, "current_stage"):
            self.Warning_Newscale.setText("Lost newscale stage connection")
        else:
            self.Warning_Newscale.setText("Newscale stage not connected")
        self.Warning_Newscale.setStyleSheet(
            f"color: {self.default_warning_color};"
        )

    def _connect_stage(self, instance):
        """connect to a stage"""
        try:
            instance.io.open()
            instance.set_timeout(1)
            instance.set_baudrate(250000)
            self.current_stage = Stage(serial=instance)
        except Exception:
            logging.error(traceback.format_exc())
            self._no_stage()
        else:
            logging.info(
                "Successfully connected to newscale stage: {}".format(
                    instance.sn
                )
            )

    def _ConnectBonsai(self):
        """
        Connect to already running bonsai instance

        Will only attempt to connect if InitializeBonsaiSuccessfully=0

        If successfully connects, sets InitializeBonsaiSuccessfully=1
        """
        if self.InitializeBonsaiSuccessfully == 0:
            try:
                self._ConnectOSC()
                self.InitializeBonsaiSuccessfully = 1
                logging.info("Connected to Bonsai")
                subprocess.Popen(
                    "title Box{}".format(self.box_letter), shell=True
                )
            except Exception:
                logging.error(traceback.format_exc())
                logging.warning(
                    "Please open bonsai!",
                    extra={"tags": [self.warning_log_tag]},
                )
                self.InitializeBonsaiSuccessfully = 0

    def _ReconnectBonsai(self):
        """
        Reconnect bonsai

        First, it closes the connections with the clients.
        Then, it restarts the Bonsai workflow. If a bonsai instance is already running,
        then it will connect. Otherwise it will start a new bonsai instance
        """
        try:
            logging.info("attempting to close bonsai connection")
            self.client.close()
            self.client2.close()
            self.client3.close()
            self.client4.close()
        except Exception as e:
            logging.info(
                "could not close bonsai connection: {}".format(str(e))
            )
        else:
            logging.info("bonsai connection closed")

        logging.info("attempting to restart bonsai")
        self.InitializeBonsaiSuccessfully = 0
        self._InitializeBonsai()

        """
            If trials have already been generated, then after reconnection to bonsai
            trial generation loops indefinitiely. See issue #166. I cannot understand
            the root cause, so I am warning users to start a new session.
        """
        if self.InitializeBonsaiSuccessfully == 1 and hasattr(
            self, "GeneratedTrials"
        ):
            msg = "Reconnected to Bonsai. Start a new session before running more trials"
            QMessageBox.information(
                self,
                "Box {}, Reconnect Bonsai".format(self.box_letter),
                msg,
                QMessageBox.Ok,
            )

    def _restartlogging(self, log_folder=None,start_from_camera=False):
        """Restarting logging"""
        logging.info("Restarting logging")
        # stop the current session except it is a new session
        if self.StartANewSession == 1 and self.ANewTrial == 1:
            pass
        else:
            self._StopCurrentSession()

        # We don't need to stop the recording when the start_from_camera is True as the logging is from the camera
        if start_from_camera == False:
            # Turn off the camera recording if it it on
            if self.Camera_dialog.StartRecording.isChecked():
                self.Camera_dialog.StartRecording.setChecked(False)
                self.Camera_dialog.StartRecording()

        # Turn off the preview if it is on and the autocontrol is on, which can make sure the trigger is off before starting the logging.
        if (
            self.Camera_dialog.AutoControl.currentText() == "Yes"
            and self.Camera_dialog.StartPreview.isChecked()
        ):
            self.Camera_dialog.StartPreview.setChecked(False)
            # sleep for 1 second to make sure the trigger is off
            time.sleep(1)

        if log_folder is None:
            # formal logging
            loggingtype = 0
            self.load_tag = 0
            self._GetSaveFolder()
            self.CreateNewFolder = 0
            log_folder = self.HarpFolder
            self.unsaved_data = True
            self.start_flash.start()
        else:
            # temporary logging
            loggingtype = 1
            current_time = datetime.now()
            formatted_datetime = current_time.strftime("%Y-%m-%d_%H-%M-%S")
            log_folder = os.path.join(
                log_folder, formatted_datetime, "behavior", "raw.harp"
            )
            # create video folder
            video_folder = os.path.join(
                log_folder, "..", "..", "behavior-videos"
            )
            if not os.path.exists(video_folder):
                os.makedirs(video_folder)
        # stop the logging first
        self._stop_logging()
        self.Channel.StartLogging(log_folder)
        Rec = self.Channel.receive()
        if Rec[0].address == "/loggerstarted":
            pass

        self.logging_type = (
            loggingtype  # 0 for formal logging, 1 for temporary logging
        )

        # if we are starting a new logging, we should initialize/empty some fields
        self._empty_initialize_fields()

        return log_folder

    def _GetLaserCalibration(self):
        """
        Load the laser calibration file.

        If it exists, populate:
            self.LaserCalibrationResults with the calibration json

        """
        if os.path.exists(self.LaserCalibrationFiles):
            with open(self.LaserCalibrationFiles, "r") as f:
                self.LaserCalibrationResults = json.load(f)

    def _GetWaterCalibration(self):
        """
        Load the water calibration file.

        If it exists, populate:
            self.WaterCalibrationResults with the calibration json
            self.RecentWaterCalibration with the last calibration
            self.RecentCalibrationDate with the date of the last calibration

        If it does not exist, populate
            self.WaterCalibrationResults with an empty dictionary
            self.RecentCalibrationDate with 'None'
        """

        if os.path.exists(self.WaterCalibrationFiles):
            with open(self.WaterCalibrationFiles, "r") as f:
                self.WaterCalibrationResults = json.load(f)
                sorted_dates = sorted(
                    self.WaterCalibrationResults.keys(),
                    key=self._custom_sort_key,
                )
                self.RecentWaterCalibration = self.WaterCalibrationResults[
                    sorted_dates[-1]
                ]
                self.RecentWaterCalibrationDate = sorted_dates[-1]
            logging.info("Loaded Water Calibration")
        else:
            self.WaterCalibrationResults = {}
            self.RecentWaterCalibrationDate = "None"
            logging.warning("Did not find a recent water calibration file")

    def _custom_sort_key(self, key):
        if "_" in key:
            date_part, number_part = key.rsplit("_", 1)
            return (date_part, int(number_part))
        else:
            return (key, 0)

    def _check_line_terminator(self, file_path):
        # Open the file in binary mode to read raw bytes. Check that last line has a \n terminator.
        with open(file_path, "rb") as file:
            # Move the cursor to the end of the file
            file.seek(0, 2)
            # Start from the end and move backwards to find the start of the last line
            file.seek(file.tell() - 1, 0)
            # Read the last line
            last_line = file.readline()
            # Detect line terminator
            if b"\r\n" in last_line:  # Windows
                return True
            elif b"\n" in last_line:  # Unix
                return True
            elif b"\r" in last_line:  # Old Mac
                return True
            else:
                return False

    def _LoadSchedule(self):
        if os.path.exists(self.Settings["schedule_path"]):
            schedule = pd.read_csv(self.Settings["schedule_path"])
            self.schedule_mice = [
                x
                for x in schedule["Mouse ID"].unique()
                if isinstance(x, str) and (len(x) > 3) and ("/" not in x)
            ]
            self.schedule = schedule.dropna(subset=["Mouse ID", "Box"]).copy()
            logging.info("Loaded behavior schedule")
        else:
            self.schedule_mice = None
            logging.info(
                "Could not find schedule at {}".format(
                    self.Settings["schedule_path"]
                )
            )
            logging.error(
                "Could not find schedule",
                extra={"tags": [self.warning_log_tag]},
            )
            return

    def _GetInfoFromSchedule(self, mouse_id, column):
        mouse_id = str(mouse_id)
        if not hasattr(self, "schedule"):
            logging.info("No schedule loaded.")
            return None
        if mouse_id not in self.schedule["Mouse ID"].values:
            logging.info(
                f"Mouse id {mouse_id} not in schedule values: {self.schedule['Mouse ID'].values}"
            )
            return None
        return self.schedule.query("`Mouse ID` == @mouse_id").iloc[0][column]

    def _GetProtocol(self, mouse_id):
        if not self.Settings["check_schedule"]:
            logging.info("not setting protocol because check_schedule=False")
            return
        logging.info("Getting protocol")
        protocol = self._GetInfoFromSchedule(mouse_id, "Protocol")
        if (protocol is None) or (protocol == "") or (np.isnan(protocol)):
            if not self.Settings["add_default_project_name"]:
                logging.info(
                    "Protocol not on schedule, not using default because add_default_project_name=False"
                )
                return
            else:
                logging.info("Protocol not on schedule, using default: 2414")
                protocol = 2414

        self.Metadata_dialog.meta_data["session_metadata"]["IACUCProtocol"] = (
            str(int(protocol))
        )
        self.Metadata_dialog._update_metadata(
            update_rig_metadata=False, update_session_metadata=True
        )
        logging.info("Setting IACUC Protocol: {}".format(protocol))

    def _GetProjectName(self, mouse_id):
        if not self.Settings["check_schedule"]:
            logging.info(
                "not setting project name because check_schedule=False"
            )
            return
        logging.info("Getting Project name")
        project_name = self._GetInfoFromSchedule(mouse_id, "Project Name")
        add_default = True

        # Check if this is a valid project name
        if project_name is None:
            logging.info("Project name not on schedule, using default")
        elif project_name not in self._GetApprovedAINDProjectNames():
            logging.error(
                "Project name {} is not valid, using default, please correct schedule".format(
                    project_name
                )
            )
            project_name = None

        # If we have a valid name update the metadata dialog
        if project_name is not None:
            if self.Metadata_dialog.ProjectName.findText(project_name) != -1:
                # If project name is valid, update metadata
                self.Metadata_dialog.meta_data["session_metadata"][
                    "ProjectName"
                ] = project_name
                self.Metadata_dialog._update_metadata(
                    update_rig_metadata=False, update_session_metadata=True
                )
                logging.info("Setting project name: {}".format(project_name))
                add_default = False

        # Users can opt out of setting the default project name
        # In this case they must set the project name manually
        if self.Settings["add_default_project_name"] and add_default:
            project_name = self._set_default_project()

    def _GetApprovedAINDProjectNames(self):
        end_point = "http://aind-metadata-service/project_names"
        timeout = 30
        try:
            response = requests.get(end_point, timeout=timeout)
        except Exception as e:
            logging.error(f"Failed to fetch project names from endpoint. {e}")
            return []
        if response.ok:
            return json.loads(response.content)["data"]
        else:
            logging.error(
                f"Failed to fetch project names from endpoint. {response.content}"
            )
            return []

    def _GetSettings(self):
        """
        Load the settings that are specific to this computer
        """

        # Try to load Settings_box#.csv
        self.SettingsBox = {}
        if not os.path.exists(self.SettingsBoxFile):
            logging.error(
                "Could not find settings_box file at: {}".format(
                    self.SettingsBoxFile
                )
            )
            raise Exception(
                "Could not find settings_box file at: {}".format(
                    self.SettingsBoxFile
                )
            )
        try:
            # Open the csv settings file
            df = pd.read_csv(self.SettingsBoxFile, index_col=None, header=None)
            self.SettingsBox = {row[0]: row[1] for _, row in df.iterrows()}
            logging.info("Loaded settings_box file")
        except Exception as e:
            logging.error(
                "Could not load settings_box file at: {}, {}".format(
                    self.SettingsBoxFile, str(e)
                )
            )
            e.args = (
                "Could not load settings box file at: {}".format(
                    self.SettingsBoxFile
                ),
                *e.args,
            )
            raise e

        # check that there is a newline for final entry of csv files
        if not self._check_line_terminator(self.SettingsBoxFile):
            logging.error(
                "Settings box file does not have a newline at the end"
            )
            raise Exception(
                "Settings box file does not have a newline at the end"
            )

        # Validate Bonsai Settings file
        BonsaiSettingsModel(**self.SettingsBox)
        logging.info("Settings_box.csv file validated")

        # Get default settings for ForagingSettings.JSON
        defaults = {
            "default_saveFolder": os.path.join(
                os.path.expanduser("~"), "Documents"
            )
            + "\\",
            "current_box": "",
            "temporary_video_folder": os.path.join(
                os.path.expanduser("~"), "Documents", "temporaryvideo"
            ),
            "Teensy_COM_box1": "",
            "Teensy_COM_box2": "",
            "Teensy_COM_box3": "",
            "Teensy_COM_box4": "",
            "FIP_workflow_path": "",
            "FIP_settings": os.path.join(
                os.path.expanduser("~"), "Documents", "FIPSettings"
            ),
            "bonsai_path": os.path.join(
                os.path.expanduser("~"),
                "Documents",
                "Github",
                "dynamic-foraging-task",
                "bonsai",
                "Bonsai.exe",
            ),
            "bonsai_config_path": os.path.join(
                os.path.expanduser("~"),
                "Documents",
                "Github",
                "dynamic-foraging-task",
                "bonsai",
                "Bonsai.config",
            ),
            "bonsaiworkflow_path": os.path.join(
                os.path.expanduser("~"),
                "Documents",
                "Github",
                "dynamic-foraging-task",
                "src",
                "workflows",
                "foraging.bonsai",
            ),
            "newscale_serial_num_box1": "",
            "newscale_serial_num_box2": "",
            "newscale_serial_num_box3": "",
            "newscale_serial_num_box4": "",
            "show_log_info_in_console": False,
            "default_ui": "ForagingGUI.ui",
            "open_ephys_machine_ip_address": "",
            "metadata_dialog_folder": os.path.join(
                self.SettingFolder, "metadata_dialog"
            )
            + "\\",
            "rig_metadata_folder": os.path.join(
                self.SettingFolder, "rig_metadata"
            )
            + "\\",
            "schedule_path": os.path.join(
                "Z:\\", "dynamic_foraging", "DynamicForagingSchedule.csv"
            ),
            "go_cue_decibel_box1": 60,
            "go_cue_decibel_box2": 60,
            "go_cue_decibel_box3": 60,
            "go_cue_decibel_box4": 60,
            "lick_spout_distance_box1": 5000,
            "lick_spout_distance_box2": 5000,
            "lick_spout_distance_box3": 5000,
            "lick_spout_distance_box4": 5000,
            "name_mapper_file": os.path.join(
                self.SettingFolder, "name_mapper.json"
            ),
            "create_rig_metadata": True,
            "save_each_trial": True,
            "AutomaticUpload": True,
            "manifest_flag_dir": os.path.join(
                os.path.expanduser("~"),
                "Documents",
                "aind_watchdog_service",
                "manifest",
            ),
            "auto_engage": True,
            "clear_figure_after_save": True,
            "add_default_project_name": True,
            "check_schedule": False,
        }

        # Try to load the ForagingSettings.json file
        self.Settings = {}
        if not os.path.exists(self.SettingFile):
            logging.error(
                "Could not find settings file at: {}".format(self.SettingFile)
            )
            raise Exception(
                "Could not find settings file at: {}".format(self.SettingFile)
            )
        try:
            # Open the JSON settings file
            with open(self.SettingFile, "r") as f:
                self.Settings = json.load(f)
            logging.info("Loaded settings file")
        except Exception as e:
            logging.error(
                "Could not load settings file at: {}, {}".format(
                    self.SettingFile, str(e)
                )
            )
            e.args = (
                "Could not load settings file at: {}".format(self.SettingFile),
                *e.args,
            )
            raise e

        # If any settings are missing, use the default values
        for key in defaults:
            if key not in self.Settings:
                self.Settings[key] = defaults[key]
                logging.warning(
                    "Missing setting ({}), using default: {}".format(
                        key, self.Settings[key]
                    )
                )
                if key in ["default_saveFolder", "current_box"]:
                    logging.error(
                        "Missing setting ({}), is required".format(key)
                    )
                    raise Exception(
                        "Missing setting ({}), is required".format(key)
                    )

        # Check that settings are valid
        DFTSettingsModel(**self.Settings)
        logging.info("ForagingSettings.json validated")

        if "default_openFolder" not in self.Settings:
            self.Settings["default_openFolder"] = self.Settings[
                "default_saveFolder"
            ]

        # Save all settings
        # TODO, should always use the values in self.Settings[x], not self.x
        self.default_saveFolder = self.Settings["default_saveFolder"]
        self.default_openFolder = self.Settings["default_openFolder"]
        self.current_box = self.Settings["current_box"]
        self.temporary_video_folder = self.Settings["temporary_video_folder"]
        self.Teensy_COM = self.Settings[
            "Teensy_COM_box" + str(self.box_number)
        ]
        self.FIP_workflow_path = self.Settings["FIP_workflow_path"]
        self.bonsai_path = self.Settings["bonsai_path"]
        self.bonsaiworkflow_path = self.Settings["bonsaiworkflow_path"]
        self.newscale_serial_num_box1 = self.Settings[
            "newscale_serial_num_box1"
        ]
        self.newscale_serial_num_box2 = self.Settings[
            "newscale_serial_num_box2"
        ]
        self.newscale_serial_num_box3 = self.Settings[
            "newscale_serial_num_box3"
        ]
        self.newscale_serial_num_box4 = self.Settings[
            "newscale_serial_num_box4"
        ]
        self.default_ui = self.Settings["default_ui"]
        self.open_ephys_machine_ip_address = self.Settings[
            "open_ephys_machine_ip_address"
        ]
        self.metadata_dialog_folder = self.Settings["metadata_dialog_folder"]
        self.rig_metadata_folder = self.Settings["rig_metadata_folder"]
        self.go_cue_decibel_box1 = self.Settings["go_cue_decibel_box1"]
        self.go_cue_decibel_box2 = self.Settings["go_cue_decibel_box2"]
        self.go_cue_decibel_box3 = self.Settings["go_cue_decibel_box3"]
        self.go_cue_decibel_box4 = self.Settings["go_cue_decibel_box4"]
        self.lick_spout_distance_box1 = self.Settings[
            "lick_spout_distance_box1"
        ]
        self.lick_spout_distance_box2 = self.Settings[
            "lick_spout_distance_box2"
        ]
        self.lick_spout_distance_box3 = self.Settings[
            "lick_spout_distance_box3"
        ]
        self.lick_spout_distance_box4 = self.Settings[
            "lick_spout_distance_box4"
        ]
        self.name_mapper_file = self.Settings["name_mapper_file"]
        self.save_each_trial = self.Settings["save_each_trial"]
        self.auto_engage = self.Settings["auto_engage"]
        self.clear_figure_after_save = self.Settings["clear_figure_after_save"]
        self.add_default_project_name = self.Settings[
            "add_default_project_name"
        ]

        # Also stream log info to the console if enabled
        if self.Settings["show_log_info_in_console"]:
            handler = logging.StreamHandler()
            # Using the same format and level as the root logger
            handler.setFormatter(logger.root.handlers[0].formatter)
            handler.setLevel(logger.root.level)
            logger.root.addHandler(handler)

        # Determine box
        if self.current_box in ["447-1", "447-2", "447-3"]:
            mapper = {1: "A", 2: "B", 3: "C", 4: "D"}
            self.current_box = "{}-{}".format(
                self.current_box, mapper[self.box_number]
            )
        self.Other_current_box = self.current_box
        self.Other_go_cue_decibel = self.Settings[
            "go_cue_decibel_box" + str(self.box_number)
        ]
        self.Other_lick_spout_distance = self.Settings[
            "lick_spout_distance_box" + str(self.box_number)
        ]
        self.rig_name = "{}".format(self.current_box)

    def _InitializeBonsai(self):
        """
        Connect to Bonsai using OSC messages to establish a connection.

        We first attempt to connect, to see if Bonsai is already running.
        If not, we start Bonsai and check the connection every 500ms.
        If we wait more than 6 seconds without Bonsai connection we set
        InitializeBonsaiSuccessfully=0 and return

        """

        # Try to connect, to see if Bonsai is already running
        self.InitializeBonsaiSuccessfully = 0
        try:
            logging.info("Trying to connect to already running Bonsai")
            self._ConnectOSC()
        except Exception as e:
            # We couldn't connect, log as info, and move on
            logging.info("Could not connect: " + str(e))
        else:
            # We could connect, set the indicator flag and return
            logging.info("Connected to already running Bonsai")
            logging.info("Bonsai started successfully")
            self.InitializeBonsaiSuccessfully = 1
            return

        # Start Bonsai
        logging.info("Starting Bonsai")
        self._OpenBonsaiWorkflow()

        # Test the connection until it completes or we time out
        wait = 0
        max_wait = 6
        check_every = 0.5
        while wait < max_wait:
            time.sleep(check_every)
            wait += check_every
            try:
                self._ConnectOSC()
            except Exception as e:
                # We could not connect
                logging.info(
                    "Could not connect, total waiting time {} seconds: ".format(
                        wait
                    )
                    + str(e)
                )
            else:
                # We could connect
                logging.info(
                    "Connected to Bonsai after {} seconds".format(wait)
                )
                logging.info("Bonsai started successfully")
                self.InitializeBonsaiSuccessfully = 1
                subprocess.Popen(
                    "title Box{}".format(self.box_letter), shell=True
                )
                return

        # Could not connect and we timed out
        logging.info(
            "Could not connect to bonsai with max wait time {} seconds".format(
                max_wait
            )
        )
        logging.warning(
            "Started without bonsai connected!",
            extra={"tags": [self.warning_log_tag]},
        )

    def _ConnectOSC(self):
        """
        Connect the GUI and Bonsai through OSC messages
        Uses self.box_number to determine ports
        """

        # connect the bonsai workflow with the python GUI
        logging.info("connecting to GUI and Bonsai through OSC")
        self.ip = "127.0.0.1"

        if self.box_number == 1:
            self.request_port = 4002
            self.request_port2 = 4003
            self.request_port3 = 4004
            self.request_port4 = 4005
        elif self.box_number == 2:
            self.request_port = 4012
            self.request_port2 = 4013
            self.request_port3 = 4014
            self.request_port4 = 4015
        elif self.box_number == 3:
            self.request_port = 4022
            self.request_port2 = 4023
            self.request_port3 = 4024
            self.request_port4 = 4025
        elif self.box_number == 4:
            self.request_port = 4032
            self.request_port2 = 4033
            self.request_port3 = 4034
            self.request_port4 = 4035
        else:
            logging.error("bad bonsai tag {}".format(self.box_number))
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
        self.InitializeBonsaiSuccessfully = 1

    def _OpenBonsaiWorkflow(self, runworkflow=1):
        """Open the bonsai workflow and run it"""

        SettingsBox = "Settings_box{}.csv".format(self.box_number)
        CWD = os.path.join(os.path.dirname(os.getcwd()), "workflows")
        if self.start_bonsai_ide:
            process = subprocess.Popen(
                self.bonsai_path
                + " "
                + self.bonsaiworkflow_path
                + " -p "
                + "SettingsPath="
                + self.SettingFolder
                + "\\"
                + SettingsBox
                + " --start",
                cwd=CWD,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        else:
            process = subprocess.Popen(
                self.bonsai_path
                + " "
                + self.bonsaiworkflow_path
                + " -p "
                + "SettingsPath="
                + self.SettingFolder
                + "\\"
                + SettingsBox
                + " --start --no-editor",
                cwd=CWD,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

        # Log stdout and stderr from bonsai in a separate thread
        Thread(
            target=log_subprocess_output,
            args=(
                process,
                "BONSAI",
            ),
        ).start()

    def _OpenVideoFolder(self):
        """Open the video folder"""
        try:
            subprocess.Popen(["explorer", self.VideoFolder])
        except Exception:
            logging.error(traceback.format_exc())

    def _OpenMetadataDialogFolder(self):
        """Open the metadata dialog folder"""
        try:
            subprocess.Popen(["explorer", self.metadata_dialog_folder])
        except Exception:
            logging.error(traceback.format_exc())

    def _OpenRigMetadataFolder(self):
        """Open the rig metadata folder"""
        try:
            subprocess.Popen(["explorer", self.rig_metadata_folder])
        except Exception:
            logging.error(traceback.format_exc())

    def _load_most_recent_rig_json(self, error_if_none=True):
        # See if rig metadata folder exists
        if not os.path.exists(self.Settings["rig_metadata_folder"]):
            print(
                "making directory: {}".format(
                    self.Settings["rig_metadata_folder"]
                )
            )
            os.makedirs(self.Settings["rig_metadata_folder"])

        # Load most recent rig_json
        files = sorted(
            Path(self.Settings["rig_metadata_folder"]).iterdir(),
            key=os.path.getmtime,
        )
        files = [f.__str__().split("\\")[-1] for f in files]
        files = [
            f
            for f in files
            if (f.startswith("rig_" + self.rig_name) and f.endswith(".json"))
        ]

        if len(files) == 0:
            # No rig.jsons found
            rig_json = {}
            rig_json_path = ""
            if error_if_none:
                logging.error("Did not find any existing rig.json files")
                logging.warning(
                    "No rig metadata found!",
                    extra={"tags": self.warning_log_tag},
                )
            else:
                logging.info(
                    "Did not find any existing rig.json files"
                )  # FIXME: is this really the right message
        else:
            rig_json_path = os.path.join(
                self.Settings["rig_metadata_folder"], files[-1]
            )
            logging.info("Found existing rig.json: {}".format(files[-1]))
            with open(rig_json_path, "r") as f:
                rig_json = json.load(f)

        return rig_json, rig_json_path

    def _LoadRigJson(self):
        # User can skip this step if they make rig metadata themselves
        if not self.Settings["create_rig_metadata"]:
            logging.info(
                "Skipping rig metadata creation because create_rig_metadata=False"
            )
            return

        existing_rig_json, rig_json_path = self._load_most_recent_rig_json(
            error_if_none=False
        )

        # Builds a new rig.json, and saves if there are changes with the most recent
        rig_settings = self.Settings.copy()
        rig_settings["rig_name"] = self.rig_name
        rig_settings["box_number"] = self.box_number
        df = pd.read_csv(self.SettingsBoxFile, index_col=None, header=None)
        rig_settings["box_settings"] = {
            row[0]: row[1] for index, row in df.iterrows()
        }
        rig_settings["computer_name"] = socket.gethostname()
        rig_settings["bonsai_version"] = self._get_bonsai_version(
            rig_settings["bonsai_config_path"]
        )

        if hasattr(self, "LaserCalibrationResults"):
            LaserCalibrationResults = self.LaserCalibrationResults
        else:
            LaserCalibrationResults = {}
        if hasattr(self, "WaterCalibrationResults"):
            WaterCalibrationResults = self.WaterCalibrationResults
        else:
            WaterCalibrationResults = {}

        # Load CMOS serial numbers for FIP if they exist
        green_cmos = os.path.join(
            self.Settings["FIP_settings"], "CameraSerial_Green.csv"
        )
        red_cmos = os.path.join(
            self.Settings["FIP_settings"], "CameraSerial_Red.csv"
        )
        if os.path.isfile(green_cmos):
            with open(green_cmos, "r") as f:
                green_cmos_sn = f.read()
            rig_settings["box_settings"]["FipGreenCMOSSerialNumber"] = (
                green_cmos_sn.strip("\n")
            )
        if os.path.isfile(red_cmos):
            with open(red_cmos, "r") as f:
                red_cmos_sn = f.read()
            rig_settings["box_settings"]["FipRedCMOSSerialNumber"] = (
                red_cmos_sn.strip("\n")
            )

        build_rig_json(
            existing_rig_json,
            rig_settings,
            WaterCalibrationResults,
            LaserCalibrationResults,
        )

    def _get_bonsai_version(self, config_path):
        with open(config_path, "r") as f:
            for line in f:
                if 'Package id="Bonsai"' in line:
                    return line.split('version="')[1].split('"')[0]
        return "0.0.0"

    def _OpenSettingFolder(self):
        """Open the setting folder"""
        try:
            subprocess.Popen(["explorer", self.SettingFolder])
        except Exception:
            logging.error(traceback.format_exc())

    def _ForceSave(self):
        """Save whether the current trial is complete or not"""
        self._Save(ForceSave=1)

    def _SaveAs(self):
        """Do not restart a session after saving"""
        self._Save(SaveAs=1)

    def update_valve_open_time(self, valve: Literal["Left", "Right"]):
        """
        Change the valve open time based on the water volume
        :param valve: valve to update
        """

        # use the latest calibration result
        if hasattr(self, "WaterCalibration_dialog"):
            if hasattr(self.WaterCalibration_dialog, "PlotM"):
                if hasattr(
                    self.WaterCalibration_dialog.PlotM, "FittingResults"
                ):
                    self.set_water_calibration_latest_fitting(
                        self.WaterCalibration_dialog.PlotM.FittingResults
                    )
                    volume = getattr(
                        self.task_logic.task_parameters.reward_size,
                        f"{valve.lower()}_value_volume",
                    )
                    valve_time = (
                        volume - self.latest_fitting[valve][1]
                    ) / self.latest_fitting[valve][0]
                    setattr(self, f"{valve.lower()}_open_time", valve_time)
                    getattr(self, f"GiveWater{valve[0]}").setValue(valve_time)
                    getattr(self, f"GiveWater{valve[0]}_volume").setValue(
                        volume
                    )

    def set_water_calibration_latest_fitting(self, fitting_results: dict):
        """
        Set the latest fitting results from water calibration
        :param fitting_results: dictionary containing the water calibration values
        """
        latest_fitting = {}
        sorted_dates = sorted(
            fitting_results.keys(), key=self._custom_sort_key
        )
        sorted_dates = sorted_dates[::-1]
        for current_date in sorted_dates:
            if "Left" in fitting_results[current_date]:
                latest_fitting["Left"] = fitting_results[current_date]["Left"]
                break
        for current_date in sorted_dates:
            if "Right" in fitting_results[current_date]:
                latest_fitting["Right"] = fitting_results[current_date][
                    "Right"
                ]
                break
        self.latest_fitting = latest_fitting

    def _OpenBehaviorFolder(self):
        """Open the the current behavior folder"""

        if hasattr(self, "SaveFileJson"):
            folder_name = os.path.dirname(self.SaveFileJson)
            subprocess.Popen(["explorer", folder_name])
        elif hasattr(self, "default_saveFolder"):
            AnimalFolder = os.path.join(
                self.default_saveFolder,
                self.current_box,
                self.session_model.subject,
            )
            logging.warning(
                f"Save folder unspecified, so opening {AnimalFolder}"
            )
            subprocess.Popen(["explorer", AnimalFolder])
        else:
            logging.warning(
                "Save folder unspecified", extra={"tags": self.warning_log_tag}
            )

    def _OpenLoggingFolder(self):
        """Open the logging folder"""
        try:
            subprocess.Popen(["explorer", self.Ot_log_folder])
        except Exception:
            logging.error(traceback.format_exc())

    def _startTemporaryLogging(self):
        """Restart the temporary logging"""
        self.Ot_log_folder = self._restartlogging(self.temporary_video_folder)

    def _startFormalLogging(self):
        """Restart the formal logging"""
        self.Ot_log_folder = self._restartlogging()

    def _QComboBoxUpdate(self, parameter, value):
        logging.info("Field updated: {}:{}".format(parameter, value))

    def _GetTrainingParameters(self, prefix="TP_"):
        """Get training parameters"""
        # Iterate over each container to find child widgets and store their values in self
        for container in [
            self.centralwidget,
            self.Opto_dialog,
            self.Metadata_dialog,
        ]:
            # Iterate over each child of the container that is a QLineEdit or QDoubleSpinBox
            for child in container.findChildren(
                (
                    QtWidgets.QLineEdit,
                    QtWidgets.QDoubleSpinBox,
                    QtWidgets.QSpinBox,
                )
            ):
                if child.objectName() == "qt_spinbox_lineedit":
                    continue
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store the child's text value
                setattr(self, prefix + child.objectName(), child.text())
            # Iterate over each child of the container that is a QComboBox
            for child in container.findChildren(QtWidgets.QComboBox):
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store the child's current text value
                setattr(self, prefix + child.objectName(), child.currentText())
            # Iterate over each child of the container that is a QPushButton
            for child in container.findChildren(QtWidgets.QPushButton):
                # Set an attribute in self with the name 'TP_' followed by the child's object name
                # and store whether the child is checked or not
                setattr(self, prefix + child.objectName(), child.isChecked())

    def _ShowRewardPairs(self):
        """Show reward pairs"""
        tp = self.task_logic.task_parameters
        try:
            if self.session_model.experiment in [
                "Coupled Baiting",
                "Coupled Without Baiting",
                "RewardN",
            ]:
                self.RewardPairs = self.RewardFamilies[
                    tp.reward_probability.family - 1
                ][: tp.reward_probability.pairs_n]
                self.RewardProb = (
                    np.array(self.RewardPairs)
                    / np.expand_dims(np.sum(self.RewardPairs, axis=1), axis=1)
                    * tp.reward_probability.base_reward_sum
                )
            elif self.session_model.experiment in [
                "Uncoupled Baiting",
                "Uncoupled Without Baiting",
            ]:
                self.RewardProb = np.array(tp.uncoupled_reward)
            str_reward = (
                str(self.RewardProb)
                if type(self.RewardProb) != float
                else str(np.round(self.RewardProb, 2))
            )
            reward_str = (
                "Reward pairs:\n"
                + str_reward.replace("\n", ",")
                + "\n\n"
                + "Current pair:\n"
            )
            if hasattr(self, "GeneratedTrials"):
                history = np.round(
                    self.GeneratedTrials.B_RewardProHistory[
                        :, self.GeneratedTrials.B_CurrentTrialN
                    ],
                    2,
                )
                self.ShowRewardPairs.setText(f"{reward_str}{history}")
            else:
                self.ShowRewardPairs.setText(reward_str)

        except Exception:
            # Catch the exception and log error information
            logging.warning(traceback.format_exc())

    def closeEvent(self, event):
        # stop the current session first
        self._StopCurrentSession()

        if self.unsaved_data:
            reply = QMessageBox.critical(
                self,
                "Box {}, Foraging Close".format(self.box_letter),
                "Exit without saving?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
        # post weight not entered and session ran
        elif (
            self.WeightAfter.text() == ""
            and self.session_run
            and not self.unsaved_data
        ):
            reply = QMessageBox.critical(
                self,
                "Box {}, Foraging Close".format(self.box_letter),
                "Post weight appears to not be entered. Do you want to close gui?",
                QMessageBox.Yes,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
        else:
            reply = QMessageBox.question(
                self,
                "Box {}, Foraging Close".format(self.box_letter),
                "Close the GUI?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.No:
                event.ignore()
                return

        event.accept()
        self.Start.setChecked(False)
        if self.InitializeBonsaiSuccessfully == 1:
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
        self._StopPhotometry(
            closing=True
        )  # Make sure photo excitation is stopped

        print("GUI Window closed")
        logging.info("GUI Window closed")

    def _Exit(self):
        """Close the GUI"""
        logging.info("closing the GUI")
        self.close()

    def _Optogenetics(self):
        """will be triggered when the optogenetics icon is pressed"""
        if self.OpenOptogenetics == 0:
            # initialize opto schema
            self.opto_model = Optogenetics(
                sample_frequency=5000,
                laser_colors=[
                    LaserColorOne(
                        color="Blue",
                        pulse_condition="Right choice",
                        start=IntervalConditions(
                            interval_condition="Trial start", offset=0
                        ),
                        end=IntervalConditions(
                            interval_condition="Right reward", offset=0
                        ),
                    ),
                    LaserColorTwo(
                        color="Red",
                        pulse_condition="Right choice",
                        start=IntervalConditions(
                            interval_condition="Trial start", offset=0
                        ),
                        end=IntervalConditions(
                            interval_condition="Right reward", offset=0
                        ),
                    ),
                    LaserColorThree(
                        color="Green",
                        pulse_condition="Right choice",
                        start=IntervalConditions(
                            interval_condition="Trial start", offset=0
                        ),
                        end=IntervalConditions(
                            interval_condition="Right reward", offset=0
                        ),
                    ),
                    LaserColorFour(
                        color="Orange",
                        pulse_condition="Right choice",
                        start=IntervalConditions(
                            interval_condition="Trial start", offset=0
                        ),
                        end=IntervalConditions(
                            interval_condition="Right reward", offset=0
                        ),
                    ),
                    LaserColorFive(
                        color="Orange",
                        pulse_condition="Right choice",
                        start=IntervalConditions(
                            interval_condition="Trial start", offset=0
                        ),
                        end=IntervalConditions(
                            interval_condition="Right reward", offset=0
                        ),
                    ),
                    LaserColorSix(
                        color="Orange",
                        pulse_condition="Right choice",
                        start=IntervalConditions(
                            interval_condition="Trial start", offset=0
                        ),
                        end=IntervalConditions(
                            interval_condition="Right reward", offset=0
                        ),
                    ),
                ],
                session_control=SessionControl(),
            )
            self.Opto_dialog = OptogeneticsDialog(
                MainWindow=self, opto_model=self.opto_model
            )
            self.OpenOptogenetics = 1
        if self.action_Optogenetics.isChecked() == True:
            self.Opto_dialog.show()
        else:
            self.Opto_dialog.hide()

    def _Camera(self):
        """Open the camera. It's not available now"""
        if self.OpenCamera == 0:
            self.Camera_dialog = CameraDialog(MainWindow=self)
            self.OpenCamera = 1
        if self.action_Camera.isChecked() == True:
            self.Camera_dialog.show()
        else:
            self.Camera_dialog.hide()

    def play_beep(self):
        """
        Convenience function to play tone
        """

        self.Channel3.TriggerGoCue(1)
        # clear messages
        self.Channel.receive()

    def change_attenuation(self, value: int) -> None:
        """
        Change attenuation of for both right and left channels
        :param value: value to set attenuation
        """

        beeping = self.beep_loop.isActive()

        if beeping:
            self.beep_loop.stop()

        self.Channel3.set_attenuation_right(value)
        self.Channel3.set_attenuation_left(value)

        self.SettingsBox["AttenuationLeft"] = value
        self.SettingsBox["AttenuationRight"] = value
        # Writing to CSV
        with open(self.SettingsBoxFile, "w", newline="") as file:
            writer = csv.writer(file)
            # Write each key-value pair as a row
            for key, value in self.SettingsBox.items():
                writer.writerow([key, value])

        if beeping:
            self.beep_loop.start()

        # else:
        #     self.Channel.receive()

    def _Metadata(self):
        """Open the metadata dialog"""
        if self.OpenMetadata == 0:
            self.Metadata_dialog = MetadataDialog(MainWindow=self)
            self.OpenMetadata = 1
        if self.actionMeta_Data.isChecked() == True:
            self.Metadata_dialog.show()
        else:
            self.Metadata_dialog.hide()

    def _WaterCalibration(self):
        if self.OpenWaterCalibration == 0:
            self.WaterCalibration_dialog = WaterCalibrationDialog(
                MainWindow=self
            )
            self.OpenWaterCalibration = 1
        if self.action_Calibration.isChecked() == True:
            self.WaterCalibration_dialog.show()
        else:
            self.WaterCalibration_dialog.hide()

    def _LaserCalibration(self):
        if self.OpenLaserCalibration == 0:
            self.LaserCalibration_dialog = LaserCalibrationDialog(
                MainWindow=self
            )
            self.OpenLaserCalibration = 1
        if self.actionLaser_Calibration.isChecked() == True:
            self.LaserCalibration_dialog.show()
        else:
            self.LaserCalibration_dialog.hide()

    def _TimeDistribution(self):
        """Plot simulated ITI/delay/block distribution"""
        if self.TimeDistribution == 0:
            self.TimeDistribution_dialog = TimeDistributionDialog(
                MainWindow=self
            )
            self.TimeDistribution = 1
            self.TimeDistribution_dialog.setWindowTitle(
                "Simulated time distribution"
            )
        if self.actionTime_distribution.isChecked() == True:
            self.TimeDistribution_dialog.show()
        else:
            self.TimeDistribution_dialog.hide()
        if self.TimeDistribution_ToInitializeVisual == 1:  # only run once
            PlotTime = PlotTimeDistribution()
            self.PlotTime = PlotTime
            layout = self.TimeDistribution_dialog.VisualizeTimeDist.layout()
            if layout is not None:
                for i in reversed(range(layout.count())):
                    layout.itemAt(i).widget().setParent(None)
                layout.invalidate()
            if layout is None:
                layout = QVBoxLayout(
                    self.TimeDistribution_dialog.VisualizeTimeDist
                )
            toolbar = NavigationToolbar(PlotTime, self)
            toolbar.setMaximumHeight(20)
            toolbar.setMaximumWidth(300)
            layout.addWidget(toolbar)
            layout.addWidget(PlotTime)
            self.TimeDistribution_ToInitializeVisual = 0
        try:
            self.PlotTime._Update(self)
        except Exception:
            logging.error(traceback.format_exc())

    def _LickSta(self):
        """Licks statistics"""
        if self.LickSta == 0:
            self.LickSta_dialog = LickStaDialog(MainWindow=self)
            self.LickSta = 1
            self.LickSta_dialog.setWindowTitle("Licks statistics")
        if self.actionLicks_sta.isChecked() == True:
            self.LickSta_dialog.show()
        else:
            self.LickSta_dialog.hide()
        if self.LickSta_ToInitializeVisual == 1:  # only run once
            PlotLick = PlotLickDistribution()
            self.PlotLick = PlotLick
            layout = self.LickSta_dialog.VisuLicksStatistics.layout()
            if layout is not None:
                for i in reversed(range(layout.count())):
                    layout.itemAt(i).widget().setParent(None)
                layout.invalidate()
            if layout is None:
                layout = QVBoxLayout(self.LickSta_dialog.VisuLicksStatistics)
            toolbar = NavigationToolbar(PlotLick, self)
            toolbar.setMaximumHeight(20)
            toolbar.setMaximumWidth(300)
            layout.addWidget(toolbar)
            layout.addWidget(PlotLick)
            # add text labels to indicate lick interval percentages
            self.same_side_lick_interval = QtWidgets.QLabel()
            self.cross_side_lick_interval = QtWidgets.QLabel()
            layout.addWidget(self.same_side_lick_interval)
            layout.addWidget(self.cross_side_lick_interval)

            self.LickSta_ToInitializeVisual = 0
        try:
            if hasattr(self, "GeneratedTrials"):
                self.PlotLick._Update(GeneratedTrials=self.GeneratedTrials)
        except Exception:
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
        """Save the current session witout restarting the logging"""
        self._Save(SaveContinue=1)

    def _Save(self, ForceSave=0, SaveAs=0, SaveContinue=0, BackupSave=0):
        """
        Save the current session

        parameters:
            ForceSave (int): 0, save after finishing the current trial, 1, save without waiting for the current trial to finish
            SaveAs (int): 0 if the user should be prompted to select a save file, 1 if the file should be saved as the current SaveFileJson
            SaveContinue (int): 0, force to start a new session, 1 if the current session should be saved without restarting the logging
            BackupSave (int): 1, save the current session without stopping the current session and without prompting the user for a save file, 0, save the current session and prompt the user for a save file
        """

        save_clicked = (
            self.Save.isChecked()
        )  # save if function was called by save button press

        if BackupSave == 1:
            ForceSave = 1
            SaveAs = 0
            SaveContinue = 1
            saving_type_label = "backup saving"
            behavior_data_field = "GeneratedTrials"
        elif ForceSave == 1:
            saving_type_label = "force saving"
            behavior_data_field = "GeneratedTrials"
        else:
            saving_type_label = "normal saving"
            behavior_data_field = "GeneratedTrials"

        logging.info("Saving current session, ForceSave={}".format(ForceSave))
        if ForceSave == 0:
            self._StopCurrentSession()  # stop the current session first
        if (
            self.BaseWeight.text() == ""
            or self.WeightAfter.text() == ""
            or self.TargetRatio.text() == ""
        ) and BackupSave == 0:
            response = QMessageBox.question(
                self,
                "Box {}, Save without weight or extra water:".format(
                    self.box_letter
                ),
                "Do you want to save without weight or extra water information provided?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )
            if response == QMessageBox.Yes:
                logging.warning(
                    "Saving without weight or extra water!",
                    extra={"tags": [self.warning_log_tag]},
                )
                pass
            elif response == QMessageBox.No:
                logging.info("saving declined by user")
                self.Save.setChecked(False)  # uncheck button
                return
            elif response == QMessageBox.Cancel:
                logging.info("saving canceled by user")
                self.Save.setChecked(False)  # uncheck button
                return
        # check if the laser power and target are entered
        if (
            BackupSave == 0
            and self.OptogeneticsB.currentText() == "on"
            and (
                self.Opto_dialog.laser_1_target.text() == ""
                or self.Opto_dialog.laser_1_calibration_power.text() == ""
                or self.Opto_dialog.laser_2_target.text() == ""
                or self.Opto_dialog.laser_2_calibration_power.text() == ""
                or self.Opto_dialog.laser_1_calibration_voltage.text() == ""
                or self.Opto_dialog.laser_2_calibration_voltage.text() == ""
            )
        ):
            response = QMessageBox.question(
                self,
                "Box {}, Save without laser target or laser power:".format(
                    self.box_letter
                ),
                "Do you want to save without complete laser target or laser power calibration information provided?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )
            if response == QMessageBox.Yes:
                logging.warning(
                    "Saving without laser target or laser power!",
                    extra={"tags": [self.warning_log_tag]},
                )
                pass
            elif response == QMessageBox.No:
                logging.info("saving declined by user")
                self.Save.setChecked(False)  # uncheck button
                return
            elif response == QMessageBox.Cancel:
                logging.info("saving canceled by user")
                self.Save.setChecked(False)  # uncheck button
                return

        # Stop Excitation if its running
        if self.StartExcitation.isChecked() and BackupSave == 0:
            self.StartExcitation.setChecked(False)
            self._StartExcitation()
            logging.info("Stopping excitation before saving")

        # get iregular timestamp
        if (
            hasattr(self, "GeneratedTrials")
            and self.InitializeBonsaiSuccessfully == 1
            and BackupSave == 0
        ):
            self.GeneratedTrials._get_irregular_timestamp(self.Channel2)

        # Create new folders.
        if self.CreateNewFolder == 1:
            self._GetSaveFolder()
            self.CreateNewFolder = 0

        if not os.path.exists(os.path.dirname(self.SaveFileJson)):
            os.makedirs(os.path.dirname(self.SaveFileJson))
            logging.info(
                f"Created new folder: {os.path.dirname(self.SaveFileJson)}"
            )

        # Save in the standard location
        if SaveAs == 0:
            self.SaveFile = self.SaveFileJson
        else:
            Names = QFileDialog.getSaveFileName(
                self,
                "Save File",
                self.SaveFileJson,
                "JSON files (*.json);;MAT files (*.mat);;JSON parameters (*_par.json)",
            )
            if Names[1] == "JSON parameters (*_par.json)":
                self.SaveFile = Names[0].replace(".json", "_par.json")
            else:
                self.SaveFile = Names[0]
            if self.SaveFile == "":
                logging.info("empty file name")
                self.Save.setChecked(False)  # uncheck button
                return

        # Do we have trials to save?
        if self.load_tag == 1:
            Obj = self.Obj
        elif hasattr(self, behavior_data_field):
            if hasattr(getattr(self, behavior_data_field), "Obj"):
                Obj = getattr(self, behavior_data_field).Obj
            else:
                Obj = {}
        else:
            Obj = {}

        if self.load_tag == 0:
            widget_dict = {
                w.objectName(): w
                for w in self.centralwidget.findChildren(
                    (
                        QtWidgets.QPushButton,
                        QtWidgets.QLineEdit,
                        QtWidgets.QTextEdit,
                        QtWidgets.QComboBox,
                        QtWidgets.QDoubleSpinBox,
                        QtWidgets.QSpinBox,
                    )
                )
            }
            self._Concat(widget_dict, Obj, "None")
            dialogs = [
                "LaserCalibration_dialog",
                "Opto_dialog",
                "Camera_dialog",
                "Metadata_dialog",
            ]
            for dialog_name in dialogs:
                if hasattr(self, dialog_name):
                    widget_dict = {
                        w.objectName(): w
                        for w in getattr(self, dialog_name).findChildren(
                            (
                                QtWidgets.QPushButton,
                                QtWidgets.QLineEdit,
                                QtWidgets.QTextEdit,
                                QtWidgets.QComboBox,
                                QtWidgets.QDoubleSpinBox,
                                QtWidgets.QSpinBox,
                            )
                        )
                    }
                    self._Concat(widget_dict, Obj, dialog_name)
            Obj2 = Obj.copy()
            # save behavor events
            if hasattr(self, behavior_data_field):
                # Do something if self has the GeneratedTrials attribute
                # Iterate over all attributes of the GeneratedTrials object
                for attr_name in dir(getattr(self, behavior_data_field)):
                    if attr_name.startswith("B_") or attr_name.startswith(
                        "BS_"
                    ):
                        if (
                            attr_name == "B_RewardFamilies"
                            and self.SaveFile.endswith(".mat")
                        ):
                            pass
                        elif attr_name == "B_SelectedCondition":
                            B_SelectedCondition = getattr(
                                getattr(self, behavior_data_field), attr_name
                            )
                            Obj["B_SelectedCondition"] = [
                                (
                                    laser.model_dump_json()
                                    if BaseModel in type(laser).__mro__
                                    else laser
                                )
                                for laser in B_SelectedCondition
                            ]
                        else:
                            Value = getattr(
                                getattr(self, behavior_data_field), attr_name
                            )
                            try:
                                if isinstance(Value, float) or isinstance(
                                    Value, int
                                ):
                                    if math.isnan(Value):
                                        Obj[attr_name] = "nan"
                                    else:
                                        Obj[attr_name] = Value
                                else:
                                    Obj[attr_name] = Value
                            except Exception:
                                logging.info(
                                    f"{attr_name} is not a real scalar, save it as it is."
                                )
                                Obj[attr_name] = Value

            # save other events, e.g. session start time
            for attr_name in dir(self):
                if attr_name.startswith("Other_") or attr_name.startswith(
                    "info_"
                ):
                    Obj[attr_name] = getattr(self, attr_name)
            # save laser calibration results (only for the calibration session)
            if hasattr(self, "LaserCalibration_dialog"):
                for attr_name in dir(self.LaserCalibration_dialog):
                    if attr_name.startswith("LCM_"):
                        Obj[attr_name] = getattr(
                            self.LaserCalibration_dialog, attr_name
                        )

            # save laser calibration results from the json file
            if hasattr(self, "LaserCalibrationResults"):
                self._GetLaserCalibration()
                Obj["LaserCalibrationResults"] = self.LaserCalibrationResults

            # save water calibration results
            if hasattr(self, "WaterCalibrationResults"):
                self._GetWaterCalibration()
                Obj["WaterCalibrationResults"] = self.WaterCalibrationResults

            # save other fields start with Ot_
            for attr_name in dir(self):
                if attr_name.startswith("Ot_"):
                    Obj[attr_name] = getattr(self, attr_name)

            if hasattr(self, "fiber_photometry_start_time"):
                Obj["fiber_photometry_start_time"] = (
                    self.fiber_photometry_start_time
                )
                if hasattr(self, "fiber_photometry_end_time"):
                    end_time = self.fiber_photometry_end_time
                else:
                    end_time = str(datetime.now())
                Obj["fiber_photometry_end_time"] = end_time

            # Save the current box
            Obj["box"] = self.current_box

            # save settings
            Obj["settings"] = self.Settings
            Obj["settings_box"] = self.SettingsBox

            # save the commit hash
            Obj["commit_ID"] = self.session_model.commit_hash
            Obj["repo_url"] = self.repo_url
            Obj["current_branch"] = self.current_branch
            Obj["repo_dirty_flag"] = self.session_model.allow_dirty_repo
            Obj["dirty_files"] = self.dirty_files
            Obj["version"] = self.session_model.experiment_version

            # save the open ephys recording information
            Obj["open_ephys"] = self.open_ephys

            if SaveContinue == 0:
                # force to start a new session; Logging will stop and users cannot run new behaviors, but can still modify GUI parameters and save them.
                self.unsaved_data = False
                self._NewSession()
                self.unsaved_data = True
                # do not create a new folder
                self.CreateNewFolder = 0

            if BackupSave == 0:
                self._check_drop_frames(save_tag=1)

                # save drop frames information
                Obj["drop_frames_tag"] = self.drop_frames_tag
                Obj["trigger_length"] = self.trigger_length
                Obj["drop_frames_warning_text"] = self.drop_frames_warning_text
                Obj["frame_num"] = self.frame_num

            # save manual water
            Obj["ManualWaterVolume"] = self.ManualWaterVolume

            # save camera start/stop time
            Obj["Camera_dialog"][
                "camera_start_time"
            ] = self.Camera_dialog.camera_start_time
            Obj["Camera_dialog"][
                "camera_stop_time"
            ] = self.Camera_dialog.camera_stop_time

            # save the saving type (normal saving, backup saving or force saving)
            Obj["saving_type_label"] = saving_type_label

        # save folders
        Obj["SessionFolder"] = self.SessionFolder
        Obj["TrainingFolder"] = self.session_model.root_path
        Obj["HarpFolder"] = self.HarpFolder
        Obj["VideoFolder"] = self.VideoFolder
        Obj["PhotometryFolder"] = self.PhotometryFolder
        Obj["MetadataFolder"] = self.MetadataFolder
        Obj["SaveFile"] = self.SaveFile

        # generate the metadata file and update slims
        try:
            # save the metadata collected in the metadata dialogue
            self.Metadata_dialog._save_metadata_dialog_parameters()
            Obj["meta_data_dialog"] = self.Metadata_dialog.meta_data
            # generate the metadata file
            generated_metadata = generate_metadata(
                Obj=Obj,
                session_model=self.session_model,
                task_logic=self.task_logic,
                opto_model=self.opto_model,
                fip_model=self.fip_model,
            )
            session = generated_metadata._session()

            if BackupSave == 0:
                text = (
                    "Session metadata generated successfully: "
                    + str(generated_metadata.session_metadata_success)
                    + "\n"
                    + "Rig metadata generated successfully: "
                    + str(generated_metadata.rig_metadata_success)
                )
                logging.warning(text, extra={"tags": [self.warning_log_tag]})
            Obj["generate_session_metadata_success"] = (
                generated_metadata.session_metadata_success
            )
            Obj["generate_rig_metadata_success"] = (
                generated_metadata.rig_metadata_success
            )

            if (
                save_clicked
            ):  # create water log result if weight after filled and uncheck save
                if (
                    self.BaseWeight.text() != ""
                    and self.WeightAfter.text() != ""
                    and self.session_model.subject
                    not in [
                        "0",
                        "1",
                        "2",
                        "3",
                        "4",
                        "5",
                        "6",
                        "7",
                        "8",
                        "9",
                        "10",
                    ]
                ):
                    self.slims_handler.add_waterlog_result(session)
                self.bias_indicator.clear()  # prepare for new session

        except Exception as e:
            logging.warning(
                "Meta data is not saved!",
                extra={"tags": {self.warning_log_tag}},
            )
            logging.error("Error generating session metadata: " + str(e))
            logging.error(traceback.format_exc())
            # set to False if error occurs
            Obj["generate_session_metadata_success"] = False
            Obj["generate_rig_metadata_success"] = False

        # don't save the data if the load tag is 1
        if self.load_tag == 0:
            with self.data_lock:
                # save Json or mat
                if self.SaveFile.endswith(".mat"):
                    # Save data to a .mat file
                    savemat(self.SaveFile, Obj)
                elif self.SaveFile.endswith("par.json") and self.load_tag == 0:
                    with open(self.SaveFile, "w") as outfile:
                        json.dump(Obj2, outfile, indent=4, cls=NumpyEncoder)
                elif self.SaveFile.endswith(".json"):
                    with open(self.SaveFile, "w") as outfile:
                        json.dump(Obj, outfile, indent=4, cls=NumpyEncoder)
        if self.load_tag == 0:
            # save Json or mat
            if self.SaveFile.endswith(".mat"):
                # Save data to a .mat file
                savemat(self.SaveFile, Obj)
            elif self.SaveFile.endswith("par.json") and self.load_tag == 0:
                with open(self.SaveFile, "w") as outfile:
                    json.dump(Obj2, outfile, indent=4, cls=NumpyEncoder)
            elif self.SaveFile.endswith(".json"):
                with open(self.SaveFile, "w") as outfile:
                    json.dump(Obj, outfile, indent=4, cls=NumpyEncoder)

        # Toggle unsaved data to False
        if BackupSave == 0:
            self.unsaved_data = False
            self.start_flash.stop()
            self.Save.setStyleSheet("background-color : None;")
            self.Save.setStyleSheet("color: black;")

            short_file = self.SaveFile.split("\\")[-1]
            if self.load_tag == 0:
                logging.warning(
                    "Saved: {}".format(short_file),
                    extra={"tags": [self.warning_log_tag]},
                )
            else:
                logging.warning(
                    "Saving of loaded files is not allowed!",
                    extra={"tags": [self.warning_log_tag]},
                )

            if self.StartEphysRecording.isChecked():
                QMessageBox.warning(
                    self,
                    "",
                    "Data saved successfully! However, the ephys recording is still running. Make sure to stop ephys recording and save the data again!",
                )
                self.unsaved_data = True
                self.start_flash.start()

            self.Save.setChecked(False)  # uncheck button

    def _GetSaveFolder(self):
        """
        Create folders with structure requested by Sci.Comp.
        Each session forms an independent folder, with subfolders:
            Training data
                Harp register events
            video data
            photometry data
            ephys data

        """

        if self.load_tag == 0:
            self.session_model.date = (
                datetime.now()
            )  # update session model with correct date
            self._get_folder_structure_new()
            self.session_model.session_name = (
                f"behavior_{self.session_model.subject}_"
                f'{self.session_model.date.strftime("%Y-%m-%d_%H-%M-%S")}'
            )
        else:
            self._parse_folder_structure()

        # update session model with correct date

        # create folders
        if not os.path.exists(self.SessionFolder):
            os.makedirs(self.SessionFolder)
            logging.info(f"Created new folder: {self.SessionFolder}")
        if not os.path.exists(self.MetadataFolder):
            os.makedirs(self.MetadataFolder)
            logging.info(f"Created new folder: {self.MetadataFolder}")
        if not os.path.exists(self.session_model.root_path):
            os.makedirs(self.session_model.root_path)
            logging.info(f"Created new folder: {self.session_model.root_path}")
        if not os.path.exists(self.HarpFolder):
            os.makedirs(self.HarpFolder)
            logging.info(f"Created new folder: {self.HarpFolder}")
        if not os.path.exists(self.VideoFolder):
            os.makedirs(self.VideoFolder)
            logging.info(f"Created new folder: {self.VideoFolder}")
        if not os.path.exists(self.PhotometryFolder):
            os.makedirs(self.PhotometryFolder)
            logging.info(f"Created new folder: {self.PhotometryFolder}")

    def _parse_folder_structure(self) -> str:
        """
        parse the folder structure from the loaded json file
        :return string of the date used to name folders
        """
        formatted_datetime = (
            os.path.basename(self.fname).split("_")[1]
            + "_"
            + os.path.basename(self.fname).split("_")[-1].split(".")[0]
        )
        self.behavior_session_model.date = datetime.strptime(
            formatted_datetime, "%Y-%m-%d_%H-%M-%S"
        )
        if os.path.basename(os.path.dirname(self.fname)) == "TrainingFolder":
            # old data format
            self._get_folder_structure_old()
        else:
            # new data format
            self._get_folder_structure_new()

    def _get_folder_structure_old(self):
        """get the folder structure for the old data format"""
        # includes subject and date of session
        session_name = self.session_model.session_name = (
            f"behavior_{self.session_model.subject}_"
            f'{self.session_model.date.strftime("%Y-%m-%d_%H-%M-%S")}'
        )
        id_name = session_name.split("behavior_")[-1]
        self.SessionFolder = os.path.join(
            self.default_saveFolder,
            self.current_box,
            self.session_model.subject,
            session_name,
        )
        self.MetadataFolder = os.path.join(self.SessionFolder, "metadata-dir")
        self.session_model.root_path = os.path.join(
            self.SessionFolder, "TrainingFolder"
        )
        self.HarpFolder = os.path.join(self.SessionFolder, "HarpFolder")
        self.VideoFolder = os.path.join(self.SessionFolder, "VideoFolder")
        self.PhotometryFolder = os.path.join(
            self.SessionFolder, "PhotometryFolder"
        )
        self.SaveFileMat = os.path.join(
            self.session_model.root_path, f"{id_name}.mat"
        )
        self.SaveFileJson = os.path.join(
            self.session_model.root_path, f"{id_name}.json"
        )
        self.SaveFileParJson = os.path.join(
            self.session_model.root_path, f"{id_name}.json"
        )

    def _get_folder_structure_new(self):
        """get the folder structure for the new data format"""
        # Determine folders
        # session_name includes subject and date of session
        session_name = self.session_model.session_name = (
            f"behavior_{self.session_model.subject}_"
            f'{self.session_model.date.strftime("%Y-%m-%d_%H-%M-%S")}'
        )
        id_name = session_name.split("behavior_")[-1]
        self.SessionFolder = os.path.join(
            self.default_saveFolder,
            self.current_box,
            self.session_model.subject,
            session_name,
        )
        self.session_model.root_path = os.path.join(
            self.SessionFolder, "behavior"
        )
        self.SaveFileMat = os.path.join(
            self.session_model.root_path, f"{id_name}.mat"
        )
        self.SaveFileJson = os.path.join(
            self.session_model.root_path, f"{id_name}.json"
        )
        self.SaveFileParJson = os.path.join(
            self.session_model.root_path, f"{id_name}_par.json"
        )
        self.HarpFolder = os.path.join(
            self.session_model.root_path, "raw.harp"
        )
        self.VideoFolder = os.path.join(self.SessionFolder, "behavior-videos")
        self.PhotometryFolder = os.path.join(self.SessionFolder, "fib")
        self.MetadataFolder = os.path.join(self.SessionFolder, "metadata-dir")

    def update_model_widgets(self):
        """
        Method to update all widget based on pydantic models
        """

        logging.info("Applying models to widgets")
        self.session_widget.apply_schema(self.session_model)
        self.task_widget.apply_schema(self.task_logic.task_parameters)
        self.Opto_dialog.opto_widget.apply_schema(self.opto_model)
        self.fip_widget.apply_schema(self.fip_model)
        self.operation_control_widget.apply_schema(
            self.operation_control_model
        )

    def save_task_models(self):
        """
        Save session and task model as well as opto and fip if applicable
        """

        id_name = self.session_model.session_name.split("behavior_")[-1]

        # validate behavior session model and document validation errors if any
        session_model_path = os.path.join(
            self.session_model.root_path,
            f"behavior_session_model_{id_name}.json",
        )
        self.validate_and_save_model(
            AindBehaviorSessionModel, self.session_model, session_model_path
        )

        # validate behavior task logic model and document validation errors if any
        task_model_path = os.path.join(
            self.session_model.root_path,
            f"behavior_task_logic_model_{id_name}.json",
        )
        self.validate_and_save_model(
            AindDynamicForagingTaskLogic, self.task_logic, task_model_path
        )

        # validate operation_control_model and document validation errors if any
        oc_path = os.path.join(
            self.session_model.root_path,
            f"behavior_operational_control_model_{id_name}.json",
        )
        self.validate_and_save_model(
            OperationalControl, self.operation_control_model, oc_path
        )

        # validate opto_model and document validation errors if any
        opto_model_path = os.path.join(
            self.session_model.root_path,
            f"behavior_optogenetics_model_{id_name}.json",
        )
        self.validate_and_save_model(
            Optogenetics, self.opto_model, opto_model_path
        )

        # validate fip_model and document validation errors if any
        fip_model_path = os.path.join(
            self.session_model.root_path,
            f"behavior_fiber_photometry_model_{id_name}.json",
        )
        self.validate_and_save_model(
            FiberPhotometry, self.fip_model, fip_model_path
        )

    def validate_and_save_model(self, schema: BaseModel, model, path: str):
        """
        Validate a model against schema and log any errors. Save schema regardless.
        :param schema: BaseModel class to validate against
        :param model: model object to validate and save
        :param path: path of where to save model
        """

        # validate model and document validation errors if any
        try:
            schema(**model.model_dump())
        except ValidationError as e:
            logging.error(str(e), extra={"tags": [self.warning_log_tag]})
        # save behavior session model
        with open(path, "w") as outfile:
            outfile.write(model.model_dump_json(indent=1))

    def _Concat(self, widget_dict, Obj, keyname):
        """Help manage save different dialogs"""
        if keyname == "None":
            for key in widget_dict.keys():
                widget = widget_dict[key]
                if isinstance(widget, QtWidgets.QPushButton):
                    Obj[widget.objectName()] = widget.isChecked()
                elif isinstance(widget, QtWidgets.QTextEdit):
                    Obj[widget.objectName()] = widget.toPlainText()
                elif (
                    isinstance(widget, QtWidgets.QDoubleSpinBox)
                    or isinstance(widget, QtWidgets.QLineEdit)
                    or isinstance(widget, QtWidgets.QSpinBox)
                ):
                    Obj[widget.objectName()] = widget.text()
                elif isinstance(widget, QtWidgets.QComboBox):
                    Obj[widget.objectName()] = widget.currentText()
        else:
            if keyname not in Obj.keys():
                Obj[keyname] = {}
            for key in widget_dict.keys():
                widget = widget_dict[key]
                if key == "Frequency_1":
                    pass
                if isinstance(widget, QtWidgets.QPushButton):
                    Obj[keyname][widget.objectName()] = widget.isChecked()
                elif isinstance(widget, QtWidgets.QTextEdit):
                    Obj[keyname][widget.objectName()] = widget.toPlainText()
                elif (
                    isinstance(widget, QtWidgets.QDoubleSpinBox)
                    or isinstance(widget, QtWidgets.QLineEdit)
                    or isinstance(widget, QtWidgets.QSpinBox)
                ):
                    Obj[keyname][widget.objectName()] = widget.text()
                elif isinstance(widget, QtWidgets.QComboBox):
                    Obj[keyname][widget.objectName()] = widget.currentText()
        return Obj

    def _LoadVisualization(self):
        """To visulize the training when loading a session"""
        self.ToInitializeVisual = 1
        Obj = self.Obj
        self.GeneratedTrials = GenerateTrials(
            self,
            self.task_logic,
            self.session_model,
            self.opto_model,
            self.fip_model,
            self.operation_control_model,
        )
        self.GeneratedTrials.mouseLicked.connect(self.retract_lick_spout)
        # Iterate over all attributes of the GeneratedTrials object
        for attr_name in dir(self.GeneratedTrials):
            if attr_name in Obj.keys():
                try:
                    # Get the value of the attribute from Obj
                    if attr_name.startswith("TP_"):
                        value = Obj[attr_name][-1]
                    else:
                        value = Obj[attr_name]
                    # transfer list to numpy array
                    if isinstance(
                        getattr(self.GeneratedTrials, attr_name), np.ndarray
                    ):
                        value = np.array(value)
                    # Set the attribute in the GeneratedTrials object
                    setattr(self.GeneratedTrials, attr_name, value)
                except Exception:
                    logging.error(traceback.format_exc())
        if self.GeneratedTrials.B_AnimalResponseHistory.size == 0:
            del self.GeneratedTrials
            return

        self.PlotM = PlotV(
            win=self, GeneratedTrials=self.GeneratedTrials, width=5, height=4
        )
        self.PlotM.setSizePolicy(
            QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding
        )
        layout = self.Visualization.layout()
        if layout is not None:
            for i in reversed(range(layout.count())):
                layout.itemAt(i).widget().setParent(None)
            layout.invalidate()
        layout = self.Visualization.layout()
        if layout is None:
            layout = QGridLayout(self.Visualization)
        toolbar = NavigationToolbar(self.PlotM, self)
        toolbar.setMaximumHeight(20)
        toolbar.setMaximumWidth(300)
        layout.addWidget(toolbar, 0, 0, 1, 2)
        layout.addWidget(self.PlotM, 1, 0)
        layout.addWidget(self.bias_indicator, 1, 1)
        self.bias_indicator.clear()
        self.PlotM._Update(GeneratedTrials=self.GeneratedTrials)
        self.PlotLick._Update(GeneratedTrials=self.GeneratedTrials)

    def _StartFIP(self):
        self.StartFIP.setChecked(False)

        if self.Teensy_COM == "":
            logging.warning(
                "No Teensy COM configured for this box, cannot start FIP workflow",
                extra={"tags": [self.warning_log_tag]},
            )
            msg = "No Teensy COM configured for this box, cannot start FIP workflow"
            reply = QMessageBox.information(
                self,
                "Box {}, StartFIP".format(self.box_letter),
                msg,
                QMessageBox.Ok,
            )
            return

        if self.FIP_workflow_path == "":
            logging.warning(
                "No FIP workflow path defined in ForagingSettings.json"
            )
            msg = "FIP workflow path not defined, cannot start FIP workflow"
            reply = QMessageBox.information(
                self,
                "Box {}, StartFIP".format(self.box_letter),
                msg,
                QMessageBox.Ok,
            )
            return

        if self.FIP_started:
            reply = QMessageBox.question(
                self,
                "Box {}, Start FIP workflow:".format(self.box_letter),
                "FIP workflow has already been started. Start again?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                logging.warning(
                    "FIP workflow already started, user declines to restart"
                )
                return
            else:
                logging.warning(
                    "FIP workflow already started, user restarts",
                    extra={"tags": [self.warning_log_tag]},
                )

        # Start logging
        if self.logging_type != 0:
            self.Ot_log_folder = self._restartlogging()

        # Start the FIP workflow
        try:
            CWD = os.path.dirname(self.FIP_workflow_path)
            logging.info("Starting FIP workflow in directory: {}".format(CWD))
            folder_path = ' -p session="{}"'.format(self.SessionFolder)
            camera = ' -p RunCamera="{}"'.format(
                not self.Camera_dialog.StartRecording.isChecked()
            )
            process = subprocess.Popen(
                self.bonsai_path
                + " "
                + self.FIP_workflow_path
                + folder_path
                + camera
                + " --start",
                cwd=CWD,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            Thread(
                target=log_subprocess_output,
                args=(
                    process,
                    "FIP",
                ),
            ).start()
            self.FIP_started = True
        except Exception as e:
            logging.error(e)
            reply = QMessageBox.information(
                self,
                "Box {}, Start FIP workflow:".format(self.box_letter),
                "Could not start FIP workflow: {}".format(e),
                QMessageBox.Ok,
            )

    def _StartExcitation(self):

        if self.Teensy_COM == "":
            logging.warning(
                "No Teensy COM configured for this box, cannot start excitation",
                extra={"tags": [self.warning_log_tag]},
            )
            msg = "No Teensy COM configured for this box, cannot start excitation"
            reply = QMessageBox.information(
                self,
                "Box {}, StartExcitation".format(self.box_letter),
                msg,
                QMessageBox.Ok,
            )
            self.StartExcitation.setChecked(False)
            self.StartExcitation.setStyleSheet("background-color : none")
            return 0

        if self.StartExcitation.isChecked():
            logging.info(
                "StartExcitation is checked, photometry mode: {}".format(
                    self.fip_model.mode
                )
            )
            self.StartExcitation.setStyleSheet("background-color : green;")
            try:
                ser = serial.Serial(self.Teensy_COM, 9600, timeout=1)
                # Trigger Teensy with the above specified exp mode
                if self.fip_model.mode == "Normal":
                    ser.write(b"c")
                elif self.fip_model.mode == "Axon":
                    ser.write(b"e")
                ser.close()
                logging.info(
                    "Started FIP excitation",
                    extra={"tags": [self.warning_log_tag]},
                )
            except Exception as e:
                logging.error(traceback.format_exc())
                logging.warning(
                    "Error: starting excitation!",
                    extra={"tags": [self.warning_log_tag]},
                )
                QMessageBox.critical(
                    self,
                    "Box {}, Start excitation:".format(self.box_letter),
                    "error when starting excitation: {}".format(e),
                    QMessageBox.Ok,
                )
                self.StartExcitation.setChecked(False)
                self.StartExcitation.setStyleSheet("background-color : none")
                return 0
            else:
                self.fiber_photometry_start_time = str(datetime.now())

        else:
            logging.info("StartExcitation is unchecked")
            self.StartExcitation.setStyleSheet("background-color : none")
            try:
                ser = serial.Serial(self.Teensy_COM, 9600, timeout=1)
                # Trigger Teensy with the above specified exp mode
                ser.write(b"s")
                ser.close()
                logging.info(
                    "Stopped FIP excitation",
                    extra={"tags": [self.warning_log_tag]},
                )
            except Exception as e:
                logging.error(traceback.format_exc())
                logging.warning(
                    "Error stopping excitation!",
                    extra={"tags": [self.warning_log_tag]},
                )
                QMessageBox.critical(
                    self,
                    "Box {}, Start excitation:".format(self.box_letter),
                    "error when stopping excitation: {}".format(e),
                    QMessageBox.Ok,
                )
                return 0
            else:
                self.fiber_photometry_end_time = str(datetime.now())

        return 1

    def _StartBleaching(self):

        if self.Teensy_COM == "":
            logging.warning(
                "No Teensy COM configured for this box, cannot start bleaching",
                extra={"tags": [self.warning_log_tag]},
            )
            msg = (
                "No Teensy COM configured for this box, cannot start bleaching"
            )
            reply = QMessageBox.information(
                self,
                "Box {}, StartBleaching".format(self.box_letter),
                msg,
                QMessageBox.Ok,
            )
            self.StartBleaching.setChecked(False)
            self.StartBleaching.setStyleSheet("background-color : none")
            return

        if self.StartBleaching.isChecked():
            # Check if trials have stopped
            if self.ANewTrial == 0:
                # Alert User
                reply = QMessageBox.critical(
                    self,
                    "Box {}, Start bleaching:".format(self.box_letter),
                    "Cannot start photobleaching, because trials are in progress",
                    QMessageBox.Ok,
                )

                # reset GUI button
                self.StartBleaching.setChecked(False)
                return

            # Verify mouse is disconnected
            reply = QMessageBox.question(
                self,
                "Box {}, Start bleaching:".format(self.box_letter),
                "Starting photobleaching, have the cables been disconnected from the mouse?",
                QMessageBox.Yes,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                # reset GUI button
                self.StartBleaching.setChecked(False)
                return

            # Start bleaching
            self.StartBleaching.setStyleSheet("background-color : green;")
            try:
                ser = serial.Serial(self.Teensy_COM, 9600, timeout=1)
                # Trigger Teensy with the above specified exp mode
                ser.write(b"d")
                ser.close()
                logging.info(
                    "Start bleaching!", extra={"tags": [self.warning_log_tag]}
                )
            except Exception as e:
                logging.error(traceback.format_exc())

                # Alert user
                logging.warning(
                    "Error: start bleaching!",
                    extra={"tags": [self.warning_log_tag]},
                )
                reply = QMessageBox.critical(
                    self,
                    "Box {}, Start bleaching:".format(self.box_letter),
                    "Cannot start photobleaching: {}".format(str(e)),
                    QMessageBox.Ok,
                )

                # Reset GUI button
                self.StartBleaching.setStyleSheet("background-color : none")
                self.StartBleaching.setChecked(False)
            else:
                # Bleaching continues until user stops
                msgbox = QMessageBox()
                msgbox.setWindowTitle(
                    "Box {}, bleaching:".format(self.box_letter)
                )
                msgbox.setText(
                    "Photobleaching in progress, do not close the GUI."
                )
                msgbox.setStandardButtons(QMessageBox.Ok)
                button = msgbox.button(QMessageBox.Ok)
                button.setText("Stop bleaching")
                msgbox.exec_()

                # Stop Bleaching
                self.StartBleaching.setChecked(False)
                self._StartBleaching()
        else:
            self.StartBleaching.setStyleSheet("background-color : none")
            try:
                ser = serial.Serial(self.Teensy_COM, 9600, timeout=1)
                # Trigger Teensy with the above specified exp mode
                ser.write(b"s")
                ser.close()
            except Exception:
                logging.error(traceback.format_exc())
                logging.warning("Error: stop bleaching!")

    def _StopPhotometry(self, closing=False):
        """
        Stop either bleaching or photometry
        """
        if self.Teensy_COM == "":
            return
        logging.info("Checking that photometry is not running")
        FIP_was_running = self.FIP_started
        try:
            ser = serial.Serial(self.Teensy_COM, 9600, timeout=1)
            # Trigger Teensy with the above specified exp mode
            ser.write(b"s")
            ser.close()
        except Exception as e:
            logging.info(
                "Could not stop photometry, most likely this means photometry is not running: "
                + str(e)
            )
        else:
            logging.info("Photometry excitation stopped")
        finally:
            # Reset all GUI buttons
            self.StartBleaching.setStyleSheet("background-color : none")
            self.StartExcitation.setStyleSheet("background-color : none")
            self.StartBleaching.setChecked(False)
            self.StartExcitation.setChecked(False)
            self.FIP_started = False

        if (FIP_was_running) & (not closing):
            self.FIP_msgbox = QMessageBox()
            self.FIP_msgbox.setWindowTitle(
                "Box {}, New Session:".format(self.box_letter)
            )
            self.FIP_msgbox.setText("Please restart the FIP workflow")
            self.FIP_msgbox.setStandardButtons(QMessageBox.Ok)
            self.FIP_msgbox.setModal(False)
            self.FIP_msgbox.show()

    def _stop_camera(self):
        """Stop the camera if it is running"""
        if self.Camera_dialog.StartRecording.isChecked():
            self.Camera_dialog.StartRecording.setChecked(False)

    def _stop_logging(self):
        """Stop the logging"""
        self.Camera_dialog.StartPreview.setEnabled(True)
        self.session_widget.subject_widget.setEnabled(True)

        try:
            self.Channel.StopLogging("s")
            self.logging_type = -1  # logging has stopped
        except Exception:
            logging.warning("Bonsai connection is closed")
            logging.warning(
                "Lost bonsai connection",
                extra={"tags": [self.warning_log_tag]},
            )
            self.InitializeBonsaiSuccessfully = 0

    def _NewSession(self):

        logging.info("New Session pressed")
        # If we have unsaved data, prompt to save
        if (self.ToInitializeVisual == 0) and (self.unsaved_data):
            reply = QMessageBox.critical(
                self,
                "Box {}, New Session:".format(self.box_letter),
                "Start new session without saving?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                self.NewSession.setStyleSheet("background-color : none")
                self.NewSession.setChecked(False)
                logging.info("New Session declined")
                return False
        # post weight not entered and session ran and new session button was clicked
        elif (
            self.WeightAfter.text() == ""
            and self.session_run
            and not self.unsaved_data
            and self.NewSession.isChecked()
        ):
            reply = QMessageBox.critical(
                self,
                "Box {}, Foraging Close".format(self.box_letter),
                "Post weight appears to not be entered. Start new session without entering and saving?",
                QMessageBox.Yes,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                self.NewSession.setStyleSheet("background-color : none")
                self.NewSession.setChecked(False)
                logging.info("New Session declined")
                return False

        # stop the camera
        self._stop_camera()

        # Reset logging
        self._stop_logging()

        # reset if session has been run
        if self.NewSession.isChecked():
            logging.info("Resetting session run flag")
            self.session_run = False
            self.BaseWeight.setText("")
            self.WeightAfter.setText("")

        # Reset GUI visuals
        self.start_flash.stop()
        self.Save.setStyleSheet("color:black;background-color:None;")
        self.NewSession.setStyleSheet("background-color : green;")
        self.NewSession.setChecked(False)
        self.Start.setStyleSheet("background-color : none")
        self.Start.setChecked(False)
        self.Start.setDisabled(False)
        self.Load.setEnabled(True)
        self.TotalWaterWarning.setText("")
        self._set_metadata_enabled(True)

        # enable task model widgets
        self.task_widget.setEnabled(True)
        self.session_widget.setEnabled(True)
        self.Opto_dialog.opto_widget.setEnabled(True)
        self.fip_widget.setEnabled(True)
        self.on_curriculum.setEnabled(True)

        # add session to slims and clear loaded mouse
        self.write_curriculum()
        self.slims_handler.clear_loaded_mouse()

        self._ConnectBonsai()
        if self.InitializeBonsaiSuccessfully == 0:
            logging.warning(
                "Lost bonsai connection",
                extra={"tags": [self.warning_log_tag]},
            )

        # Reset state variables
        self._StopPhotometry()  # Make sure photoexcitation is stopped
        self.StartANewSession = 1
        self.CreateNewFolder = 1
        self.PhotometryRun = 0

        self.unsaved_data = False
        self.ManualWaterVolume = [0, 0]
        self.baseline_min_elapsed = 0   # variable to track baseline time elapsed before session for start/stop

        # Clear Plots
        if hasattr(self, "PlotM") and self.clear_figure_after_save:
            self.bias_indicator.clear()
            self.PlotM._Update(GeneratedTrials=None, Channel=None)

        # Add note to log
        logging.info("New Session complete")

        # if session log handler is not none, stop logging for previous session
        if self.session_log_handler is not None:
            self.end_session_log()

        return True

    def _AskSave(self):
        reply = QMessageBox.question(
            self,
            "Box {}, New Session:".format(self.box_letter),
            "Do you want to save the current result?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self._Save()
            logging.info("The current session was saved")
        elif reply == QMessageBox.No:
            pass
        else:
            pass

    def _StopCurrentSession(self):
        logging.info("Stopping current trials")

        # stop the current session
        self.Start.setStyleSheet("background-color : none")
        self.Start.setChecked(False)

        # waiting for the finish of the last trial
        start_time = time.time()
        stall_iteration = 1
        stall_duration = 5 * 60
        if self.ANewTrial == 0:
            logging.warning(
                "Waiting for the finish of the last trial!",
                extra={"tags": [self.warning_log_tag]},
            )
            while 1:
                QApplication.processEvents()
                if self.ANewTrial == 1:
                    break
                elif (
                    time.time() - start_time
                ) > stall_duration * stall_iteration:
                    elapsed_time = int(
                        np.floor(stall_duration * stall_iteration / 60)
                    )
                    message = "{} minutes have elapsed since trial stopped was initiated. Force stop?".format(
                        elapsed_time
                    )
                    reply = QMessageBox.question(
                        self,
                        "Box {}, StopCurrentSession".format(self.box_letter),
                        message,
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes,
                    )
                    if reply == QMessageBox.Yes:
                        logging.error(
                            "trial stalled {} minutes, user force stopped trials".format(
                                elapsed_time
                            )
                        )
                        self.ANewTrial = 1
                        break
                    else:
                        stall_iteration += 1
                        logging.info(
                            "trial stalled {} minutes, user did not force stopped trials".format(
                                elapsed_time
                            )
                        )

    def _thread_complete(self):
        """complete of a trial"""
        if self.NewTrialRewardOrder == 0:
            self.GeneratedTrials._GenerateATrial()
        self.ANewTrial = 1

    def _thread_complete2(self):
        """complete of receive licks"""
        self.ToReceiveLicks = 1

    def _thread_complete3(self):
        """complete of update figures"""
        self.ToUpdateFigure = 1

    def _thread_complete4(self):
        """complete of generating a trial"""
        self.ToGenerateATrial = 1

    def _thread_complete6(self):
        """complete of save data"""
        self.previous_backup_completed = 1

    def _thread_complete_timer(self):
        """complete of _Timer"""
        if not self.ignore_timer:
            self.finish_Timer = 1
            logging.info("Finished photometry baseline timer")

    def _update_photometery_timer(self, time):
        """
        Updates photometry baseline timer
        """
        minutes = int(np.floor(time / 60))
        seconds = np.remainder(time, 60)
        if len(str(seconds)) == 1:
            seconds = "0{}".format(seconds)
        if not self.ignore_timer:
            self.photometry_timer_label.setText(
                "Running photometry baseline: {}:{}".format(minutes, seconds)
            )

    def _set_metadata_enabled(self, enable: bool):
        """Enable or disable metadata fields"""
        self.session_widget.experimenter_widget.setEnabled(enable)
        self.session_widget.subject_widget.setEnabled(enable)

    def _set_default_project(self):
        """Set default project information"""
        project_name = "Behavior Platform"
        logging.error(
            "Setting default project name for mouse {}: {}".format(
                self.session_model.subject, project_name
            )
        )

        # Check if Behavior Platform is in project list
        if self.Metadata_dialog.ProjectName.findText(project_name) == -1:
            self.Metadata_dialog.ProjectName.addItem(project_name)

        # Set project name
        self.Metadata_dialog.meta_data["session_metadata"][
            "ProjectName"
        ] = project_name
        self.Metadata_dialog._update_metadata(
            update_rig_metadata=False, update_session_metadata=True
        )

        return project_name

    def _empty_initialize_fields(self):
        """empty fields from the previous session"""
        # empty the manual water volume
        self.ManualWaterVolume = [0, 0]
        # delete open ephys data
        self.open_ephys = []
        # set the flag to check drop frames
        self.to_check_drop_frames = 1
        # empty the laser calibration
        self.Opto_dialog.laser_1_calibration_voltage.setText("")
        self.Opto_dialog.laser_2_calibration_voltage.setText("")
        self.Opto_dialog.laser_1_calibration_power.setText("")
        self.Opto_dialog.laser_2_calibration_power.setText("")

        # clear camera start and end time
        self.Camera_dialog.camera_start_time = ""
        self.Camera_dialog.camera_stop_time = ""

        # clear fiber start and end time (this could be simplified after refactoring the photometry code)
        if hasattr(self, "fiber_photometry_end_time"):
            self.fiber_photometry_end_time = ""
        if not self.StartExcitation.isChecked():
            self.fiber_photometry_start_time = ""

        # delete generate trials
        if hasattr(self, "GeneratedTrials"):
            # delete GeneratedTrials
            del self.GeneratedTrials

        # delete the random reward
        if hasattr(self, "RandomReward_dialog"):
            self.RandomReward_dialog.random_reward_par = {}
            self.RandomReward_dialog.random_reward_par["RandomWaterVolume"] = [
                0,
                0,
            ]

        # delete the optical tagging
        if hasattr(self, "OpticalTagging_dialog"):
            self.OpticalTagging_dialog.optical_tagging_par = {}

    def _Start(self):
        """start trial loop"""

        # post weight not entered and session ran
        if (
            self.WeightAfter.text() == ""
            and self.session_run
            and not self.unsaved_data
        ):
            reply = QMessageBox.critical(
                self,
                "Box {}, Foraging Close".format(self.box_letter),
                "Post weight appears to not be entered. Do you want to start a new session?",
                QMessageBox.Yes,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return

        # Check for Bonsai connection
        self._ConnectBonsai()
        if self.InitializeBonsaiSuccessfully == 0:
            logging.info("Start button pressed, but bonsai not connected")
            self.Start.setChecked(False)
            self.Start.setStyleSheet("background-color:none;")
            return

        # Clear warnings
        self.NewSession.setDisabled(False)
        # Toggle button colors
        if self.Start.isChecked():
            logging.info("Start button pressed: starting trial loop")
            mouse_id = self.session_model.subject
            if self.StartANewSession == 0:
                reply = QMessageBox.question(
                    self,
                    "Box {}, Start".format(self.box_letter),
                    "Continue current session?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    self.Start.setChecked(False)
                    logging.info("User declines continuation of session")
                    return
                self.GeneratedTrials.lick_interval_time.start()  # restart lick interval calculation

            # check experimenter name
            reply = QMessageBox.critical(
                self,
                "Box {}, Start".format(self.box_letter),
                f'The experimenter is <span style="color: {self.default_text_color};">'
                f"{self.session_model.experimenter[0]}</span>. Is this correct?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                self.Start.setChecked(False)
                logging.info("User declines using default name")
                return
            logging.info(
                "Starting session, with experimenter: {}".format(
                    self.session_model.experimenter[0]
                )
            )

            # check repo status
            if (self.current_branch not in ["main", "production_testing"]) & (
                self.session_model.subject
                not in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
            ):
                # Prompt user over off-pipeline branch
                reply = QMessageBox.critical(
                    self,
                    "Box {}, Start".format(self.box_letter),
                    'Running on branch <span style="color:purple;font-weight:bold">{}</span>, continue anyways?'.format(
                        self.current_branch
                    ),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    # Stop session
                    self.Start.setChecked(False)
                    logging.info(
                        "User declines starting session on branch: {}".format(
                            self.current_branch
                        )
                    )
                    return
                else:
                    # Allow the session to continue, but log error
                    logging.error(
                        "Starting session on branch: {}".format(
                            self.current_branch
                        ),
                        extra={"tags": [self.warning_log_tag]},
                    )

            # Check for untracked local changes
            if self.session_model.allow_dirty_repo & (
                self.session_model.subject
                not in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
            ):
                # prompt user over untracked local changes
                reply = QMessageBox.critical(
                    self,
                    "Box {}, Start".format(self.box_letter),
                    "Local repository has untracked changes, continue anyways?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    # Stop session
                    self.Start.setChecked(False)
                    logging.info(
                        "User declines starting session with untracked changes"
                    )
                    return
                else:
                    # Allow the session to continue, but log error
                    logging.error(
                        "Starting session with untracked local changes: {}".format(
                            self.dirty_files
                        ),
                        extra={"tags": [self.warning_log_tag]},
                    )
            elif self.session_model.allow_dirty_repo is None:
                logging.error("Could not check for untracked local changes")

            # disable sound button
            self.sound_button.setEnabled(False)

            #   if mouse is loaded, update attachments with what actually ran
            if self.slims_handler.loaded_slims_session:
                Thread(target=self.update_curriculum_attachments).start()

            # set the load tag to zero
            self.load_tag = 0

            # empty post weight after pass through checks in case user cancels run
            self.WeightAfter.setText("")

            # change button color and mark the state change
            self.Start.setStyleSheet("background-color : green;")
            self.NewSession.setStyleSheet("background-color : none")
            self.NewSession.setChecked(False)

            # disable metadata fields
            self._set_metadata_enabled(False)

            # update slims with latest stage offset value for loaded mouse
            self.update_loaded_mouse_offset()

            # disable task model widgets
            self.task_widget.setEnabled(False)
            self.session_widget.setEnabled(False)
            self.Opto_dialog.opto_widget.setEnabled(False)
            self.fip_widget.setEnabled(False)
            self.on_curriculum.setEnabled(False)

            # set flag to perform habituation period
            self.behavior_baseline_period.set()

            self.session_run = True  # session has been started
        else:
            # Prompt user to confirm stopping trials
            reply = QMessageBox.question(
                self,
                "Box {}, Start".format(self.box_letter),
                "Stop current session?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                # End trials
                logging.info("Start button pressed: ending trial loop")
                self.Start.setStyleSheet("background-color : none")
            else:
                # Continue trials
                logging.info("Start button pressed: user continued session")
                self.Start.setChecked(True)
                return

            # enable task model widgets
            self.task_widget.setEnabled(
                not self.on_curriculum.isVisible()
                or not self.on_curriculum.isChecked()
            )
            self.session_widget.setEnabled(
                not self.on_curriculum.isVisible()
                or not self.on_curriculum.isChecked()
            )
            self.Opto_dialog.opto_widget.setEnabled(
                not self.on_curriculum.isVisible()
                or not self.on_curriculum.isChecked()
            )
            self.fip_widget.setEnabled(
                not self.on_curriculum.isVisible()
                or not self.on_curriculum.isChecked()
            )
            self.on_curriculum.setEnabled(True)

            # If the photometry timer is running, stop it
            if self.finish_Timer == 0:
                self.ignore_timer = True
                self.PhotometryRun = 0
                logging.info("canceling photometry baseline timer")
                if hasattr(self, "workertimer"):
                    # Stop the worker, this has a 1 second delay before taking effect
                    # so we set the text to get ignored as well
                    self.workertimer._stop()

            self.session_end_tasks()
            self.sound_button.setEnabled(True)
            self.behavior_baseline_period.clear()   # set flag to break out of habituation period

        if (self.StartANewSession == 1) and (self.ANewTrial == 0):
            # If we are starting a new session, we should wait for the last trial to finish
            self._StopCurrentSession()
        # to see if we should start a new session
        if self.StartANewSession == 1 and self.ANewTrial == 1:
            # start a new logging
            try:
                # Start logging if the formal logging is not started
                if self.logging_type != 0:
                    self.Ot_log_folder = self._restartlogging()
            except Exception as e:
                if "ConnectionAbortedError" in str(e):
                    logging.info("lost bonsai connection: restartlogging()")
                    logging.warning(
                        "Lost bonsai connection",
                        extra={"tags": [self.warning_log_tag]},
                    )
                    self.Start.setChecked(False)
                    self.Start.setStyleSheet("background-color : none")
                    self.InitializeBonsaiSuccessfully = 0
                    reply = QMessageBox.question(
                        self,
                        "Box {}, Start".format(self.box_letter),
                        "Cannot connect to Bonsai. Attempt reconnection?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes,
                    )
                    if reply == QMessageBox.Yes:
                        self._ReconnectBonsai()
                        logging.info("User selected reconnect bonsai")
                    else:
                        logging.info("User selected not to reconnect bonsai")
                    return
                else:
                    print("type: {}, text:{}".format(type(e), e))
                    raise
            # start the camera during the begginning of each session
            if self.Camera_dialog.AutoControl.currentText() == "Yes":
                # camera will start recording
                self.Camera_dialog.StartRecording.setChecked(True)
            self.SessionStartTime = datetime.now()
            self.Other_SessionStartTime = str(
                self.SessionStartTime
            )  # for saving
            GeneratedTrials = GenerateTrials(
                self,
                self.task_logic,
                self.session_model,
                self.opto_model,
                self.fip_model,
                self.operation_control_model,
            )
            self.GeneratedTrials = GeneratedTrials
            self.GeneratedTrials.mouseLicked.connect(self.retract_lick_spout)
            self.StartANewSession = 0
            PlotM = PlotV(
                win=self, GeneratedTrials=GeneratedTrials, width=5, height=4
            )
            # PlotM.finish=1
            self.PlotM = PlotM
            # generate the first trial outside the loop, only for new session
            self.ToReceiveLicks = 1
            self.ToUpdateFigure = 1
            self.ToGenerateATrial = 1
            self.ToInitializeVisual = 1
            GeneratedTrials._GenerateATrial()
            # delete licks from the previous session
            GeneratedTrials._DeletePreviousLicks(self.Channel2)
            GeneratedTrials.lick_interval_time.start()  # start lick interval calculation

            if self.Start.isChecked():
                # if session log handler is not none, stop logging for previous session
                if self.session_log_handler is not None:
                    self.end_session_log()
                self.log_session()  # start log for new session

        else:
            GeneratedTrials = self.GeneratedTrials

        if self.ToInitializeVisual == 1:  # only run once
            self.PlotM = PlotM
            self.PlotM.setSizePolicy(
                QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding
            )
            layout = self.Visualization.layout()
            if layout is not None:
                for i in reversed(range(layout.count())):
                    layout.itemAt(i).widget().setParent(None)
                layout.invalidate()
            if layout is None:
                layout = QGridLayout(self.Visualization)
            toolbar = NavigationToolbar(PlotM, self)
            toolbar.setMaximumHeight(20)
            toolbar.setMaximumWidth(300)
            layout.addWidget(toolbar, 0, 0, 1, 2)
            layout.addWidget(PlotM, 1, 0)
            layout.addWidget(self.bias_indicator, 1, 1)
            self.ToInitializeVisual = 0
            # clear bias indicator graph
            self.bias_indicator.clear()
            # create workers
            worker1 = Worker(
                self.GeneratedTrials._GetAnimalResponse,
                self.Channel,
                self.Channel3,
                self.data_lock,
            )
            worker1.signals.finished.connect(self._thread_complete)
            workerLick = Worker(
                GeneratedTrials._get_irregular_timestamp, self.Channel2
            )
            workerLick.signals.finished.connect(self._thread_complete2)
            workerPlot = Worker(
                PlotM._Update,
                GeneratedTrials=GeneratedTrials,
                Channel=self.Channel2,
            )
            workerPlot.signals.finished.connect(self._thread_complete3)
            workerGenerateAtrial = Worker(GeneratedTrials._GenerateATrial)
            workerGenerateAtrial.signals.finished.connect(
                self._thread_complete4
            )
            workerStartTrialLoop = Worker(
                self._StartTrialLoop,
                GeneratedTrials,
                worker1,
                workerPlot,
                workerGenerateAtrial,
            )
            workerStartTrialLoop1 = Worker(
                self._StartTrialLoop1, GeneratedTrials
            )
            worker_save = Worker(self._perform_backup, BackupSave=1)
            worker_save.signals.finished.connect(self._thread_complete6)
            self.worker1 = worker1
            self.workerLick = workerLick
            self.workerPlot = workerPlot
            self.workerGenerateAtrial = workerGenerateAtrial
            self.workerStartTrialLoop = workerStartTrialLoop
            self.workerStartTrialLoop1 = workerStartTrialLoop1
            self.worker_save = worker_save
            self.data_lock = Lock()
        else:
            PlotM = self.PlotM
            worker1 = self.worker1
            workerLick = self.workerLick
            workerPlot = self.workerPlot
            workerGenerateAtrial = self.workerGenerateAtrial
            workerStartTrialLoop = self.workerStartTrialLoop
            workerStartTrialLoop1 = self.workerStartTrialLoop1
            worker_save = self.worker_save

        # pause for specified habituation time
        if self.baseline_min_elapsed <= self.hab_time_box.value():
            self.wait_for_baseline()

        # collecting the base signal for photometry. Only run once
        if (
                self.Start.isChecked()
                and self.fip_model.enabled
                and self.PhotometryRun == 0
        ):
            # check if workflow is running and start photometry timer
            if not self.photometry_workflow_running():
                self.Start.setChecked(False)
                return

            logging.info("Starting photometry baseline timer")
            self.finish_Timer = 0
            self.PhotometryRun = 1
            self.ignore_timer = False

            # create label to display time remaining on photometry label and add to warning widget
            self.photometry_timer_label = QLabel()
            self.photometry_timer_label.setStyleSheet(
                f"color: {self.default_warning_color};"
            )
            self.warning_widget.layout().insertWidget(
                0, self.photometry_timer_label
            )

            # If we already created a workertimer and thread we can reuse them
            if not hasattr(self, "workertimer"):
                self.workertimer = TimerWorker()
                self.workertimer_thread = QThread()
                self.workertimer.progress.connect(
                    self._update_photometery_timer
                )
                self.workertimer.finished.connect(self._thread_complete_timer)
                self.Time.connect(self.workertimer._Timer)
                self.workertimer.moveToThread(self.workertimer_thread)
                self.workertimer_thread.start()

            self.Time.emit(int(np.floor(self.fip_model.baseline_time * 60)))
            logging.info(
                "Running photometry baseline",
                extra={"tags": [self.warning_log_tag]},
            )

        self._StartTrialLoop(GeneratedTrials, worker1, worker_save)

        if self.actionDrawing_after_stopping.isChecked() == True:
            try:
                self.PlotM._Update(
                    GeneratedTrials=GeneratedTrials, Channel=self.Channel2
                )
            except Exception:
                logging.error(traceback.format_exc())

    def photometry_workflow_running(self) -> bool or None:
        """
        If fiber photometery is configured for session, check if work flow is running

        :returns: boolean indicating if workflow is running or not. If None, fip is not configured
        """

        if self.fib_model.enabled and (
                not self.FIP_started
        ):
            QMessageBox.critical(
                self,
                "Box {}, Start".format(self.box_letter),
                'Photometry is set to "on", but the FIP workflow has not been started',
                QMessageBox.Ok,
            )

            logging.info(
                "Cannot start session without starting FIP workflow"
            )
            return False

        # Check if photometry excitation is running or not
        if self.fib_model.enabled and not self.StartExcitation.isChecked():
            logging.warning('photometry is set to "on", but excitation is not running')

            reply = QMessageBox.question(
                self,
                "Box {}, Start".format(self.box_letter),
                'Photometry is set to "on", but excitation is not running. Start excitation now?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                self.StartExcitation.setChecked(True)
                logging.info("User selected to start excitation")
                started = self._StartExcitation()
                if started == 0:
                    QMessageBox.critical(
                        self,
                        "Box {}, Start".format(self.box_letter),
                        "Could not start excitation, therefore cannot start the session",
                        QMessageBox.Ok,
                    )
                    logging.info(
                        "could not start session, due to failure to start excitation"
                    )
                    self.Start.setChecked(False)
                    return False
            else:
                logging.info("User selected not to start excitation")
                self.Start.setChecked(False)
                return False

        return True

    def session_end_tasks(self):
        """
        Data cleanup and saving that needs to be done at end of session.
        """
        if hasattr(self, "GeneratedTrials"):
            # If the session never generated any trials, then we don't need to perform these tasks

            # fill out GenerateTrials B_Bias
            last_bias = self.GeneratedTrials.B_Bias[-1]
            b_bias_len = len(self.GeneratedTrials.B_Bias)
            bias_filler = [last_bias] * (
                (self.GeneratedTrials.B_CurrentTrialN + 1) - b_bias_len
            )
            self.GeneratedTrials.B_Bias = np.concatenate(
                (self.GeneratedTrials.B_Bias, bias_filler), axis=0
            )

            # fill out GenerateTrials B_Bias_CI
            last_ci = self.GeneratedTrials.B_Bias_CI[-1]
            b_ci_len = len(self.GeneratedTrials.B_Bias_CI)
            ci_filler = [last_ci] * (
                (self.GeneratedTrials.B_CurrentTrialN + 1) - b_ci_len
            )
            if ci_filler != []:
                self.GeneratedTrials.B_Bias_CI = np.concatenate(
                    (self.GeneratedTrials.B_Bias_CI, ci_filler), axis=0
                )

            # stop lick interval calculation
            self.GeneratedTrials.lick_interval_time.stop()

    def log_session(self) -> None:
        """
        Setup a log handler to write logs during session to TrainingFolder
        """

        logging_filename = os.path.join(
            self.session_model.root_path, "python_gui_log.txt"
        )

        # Format the log file:
        log_format = "%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(funcName)s:line %(lineno)d:%(message)s"
        log_datefmt = "%I:%M:%S %p"

        log_formatter = logging.Formatter(fmt=log_format, datefmt=log_datefmt)
        self.session_log_handler = logging.FileHandler(logging_filename)
        self.session_log_handler.setFormatter(log_formatter)
        self.session_log_handler.setLevel(logging.INFO)
        logger.root.addHandler(self.session_log_handler)

        logging.info(f"Starting log file at {self.session_model.root_path}")

    def end_session_log(self) -> None:
        """
        Dismantle the session log handler when gui is closed or new session is started
        """

        if self.session_log_handler is not None:
            logging.info(
                f"Closing log file at {self.session_log_handler.baseFilename}"
            )
            self.session_log_handler.close()
            logger.root.removeHandler(self.session_log_handler)
            self.session_log_handler = None
        else:
            logging.info("No active session logger")

    def wait_for_baseline(self) -> None:
        """
            Function to wait for a baseline time before behavior
        """

        # pause for specified habituation time
        start_time = time.time()

        # create habituation timer label and update every minute
        hab_lab = QLabel()
        hab_lab.setStyleSheet(f"color: {self.default_warning_color};")
        self.warning_widget.layout().insertWidget(0, hab_lab)
        update_hab_timer = QtCore.QTimer(
            timeout=lambda: hab_lab.setText(f"Time elapsed: "
                                            f"{round((self.baseline_min_elapsed * 60) // 60)} minutes"
                                            f" {round((self.baseline_min_elapsed * 60) % 60)} seconds"),
            interval=1000)
        update_hab_timer.start()

        logging.info(f"Waiting {round(self.hab_time_box.value() - self.baseline_min_elapsed)} min before starting "
                     f"session.")

        elapsed = self.baseline_min_elapsed
        while self.baseline_min_elapsed < self.hab_time_box.value() and self.behavior_baseline_period.is_set():
            QApplication.processEvents()
            # update baseline time elapsed before session for start/stop logic
            self.baseline_min_elapsed = ((time.time() - start_time) / 60) + elapsed

        update_hab_timer.stop()
        self.behavior_baseline_period.clear()


    def _StartTrialLoop(self, GeneratedTrials, worker1, worker_save):

        if not self.Start.isChecked():
            logging.info("ending trial loop")
            return

        logging.info("starting trial loop")

        # Track elapsed time in case Bonsai Stalls
        last_trial_start = time.time()
        stall_iteration = 1
        stall_duration = 5 * 60

        logging.info(f"Starting session.")

        while self.Start.isChecked():
            QApplication.processEvents()
            if (
                self.ANewTrial == 1
                and self.Start.isChecked()
                and self.finish_Timer == 1
            ):
                # Reset stall timer
                last_trial_start = time.time()
                stall_iteration = 1

                # can start a new trial when we receive the trial end signal from Bonsai
                self.ANewTrial = 0
                GeneratedTrials.B_CurrentTrialN += 1
                print(
                    "Current trial: "
                    + str(GeneratedTrials.B_CurrentTrialN + 1)
                )
                logging.info(
                    "Current trial: "
                    + str(GeneratedTrials.B_CurrentTrialN + 1)
                )
                if (
                    (
                        self.task_logic.task_parameters.auto_water is not None
                        or self.task_logic.task_parameters.block_parameters.min_reward
                        > 0
                        or self.session_model.experiment
                        in ["Uncoupled Baiting", "Uncoupled Without Baiting"]
                    )
                    or self.task_logic.task_parameters.no_response_trial_addition
                ):
                    # The next trial parameters must be dependent on the current trial's choice
                    # get animal response and then generate a new trial
                    self.NewTrialRewardOrder = 0
                else:
                    # By default, to save time, generate a new trial as early as possible
                    # generate a new trial and then get animal response
                    self.NewTrialRewardOrder = 1

                # initiate the generated trial
                try:
                    GeneratedTrials._InitiateATrial(
                        self.Channel, self.Channel4
                    )
                except Exception as e:
                    if "ConnectionAbortedError" in str(e):
                        logging.info("lost bonsai connection: InitiateATrial")
                        logging.warning(
                            "Lost bonsai connection",
                            extra={"tags": [self.warning_log_tag]},
                        )
                        self.Start.setChecked(False)
                        self.Start.setStyleSheet("background-color : none")
                        self.InitializeBonsaiSuccessfully = 0
                        reply = QMessageBox.question(
                            self,
                            "Box {}, Start".format(self.box_letter),
                            "Cannot connect to Bonsai. Attempt reconnection?",
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.Yes,
                        )
                        if reply == QMessageBox.Yes:
                            self._ReconnectBonsai()
                            logging.info("User selected reconnect bonsai")
                        else:
                            logging.info(
                                "User selected not to reconnect bonsai"
                            )
                        self.ANewTrial = 1

                        break
                    else:
                        reply = QMessageBox.critical(
                            self,
                            "Box {}, Error".format(self.box_letter),
                            "Encountered the following error: {}".format(e),
                            QMessageBox.Ok,
                        )
                        logging.error("Caught this error: {}".format(e))
                        self.ANewTrial = 1
                        self.Start.setChecked(False)
                        self.Start.setStyleSheet("background-color : none")
                        break
                # receive licks and update figures
                if self.actionDrawing_after_stopping.isChecked() == False:
                    self.PlotM._Update(
                        GeneratedTrials=GeneratedTrials, Channel=self.Channel2
                    )
                # update licks statistics
                if self.actionLicks_sta.isChecked():
                    self.PlotLick._Update(GeneratedTrials=GeneratedTrials)

                # Generate upload manifest when we generate the second trial
                # counter starts at 0
                if GeneratedTrials.B_CurrentTrialN == 1:
                    self._generate_upload_manifest()

                # calculate bias every 10 trials
                if (
                    GeneratedTrials.B_CurrentTrialN + 1
                ) % 10 == 0 and GeneratedTrials.B_CurrentTrialN + 1 > 20:
                    # correctly format data for bias indicator

                    formatted_history = [
                        np.nan if x == 2 else int(x)
                        for x in self.GeneratedTrials.B_AnimalResponseHistory
                    ]
                    formatted_reward = [
                        any(x)
                        for x in np.column_stack(
                            self.GeneratedTrials.B_RewardedHistory
                        )
                    ]

                    # only take last 200 trials if enough trials have happened
                    choice_history = (
                        formatted_history[-200:]
                        if len(formatted_history) > 200
                        else formatted_history
                    )
                    any_reward = (
                        formatted_reward[-200:]
                        if len(formatted_reward) > 200
                        else formatted_reward
                    )

                    # add data to bias_indicator
                    if not self.bias_thread.is_alive():
                        logger.debug("Starting bias thread.")
                        self.bias_thread = Thread(
                            target=self.bias_indicator.calculate_bias,
                            kwargs={
                                "trial_num": len(formatted_history),
                                "choice_history": choice_history,
                                "reward_history": np.array(any_reward).astype(
                                    int
                                ),
                                "n_trial_back": 5,
                                "cv": 1,
                            },
                        )
                        self.bias_thread.start()
                    else:
                        logger.debug(
                            "Skipping bias calculation as previous is still in progress. "
                        )

                # save the data everytrial
                if GeneratedTrials.CurrentSimulation == True:
                    GeneratedTrials._GetAnimalResponse(
                        self.Channel, self.Channel3, self.data_lock
                    )
                    self.ANewTrial = 1
                    self.NewTrialRewardOrder = 1
                else:
                    # get the response of the animal using a different thread
                    self.threadpool.start(worker1)
                # generate a new trial
                if self.NewTrialRewardOrder == 1:
                    GeneratedTrials._GenerateATrial()

                # Save data in a separate thread
                if (
                    GeneratedTrials.B_CurrentTrialN > 0
                    and self.previous_backup_completed == 1
                    and self.save_each_trial
                    and GeneratedTrials.CurrentSimulation == False
                ):
                    self.previous_backup_completed = 0
                    self.threadpool6.start(worker_save)

                # show disk space
                self._show_disk_space()

            elif (
                (time.time() - last_trial_start)
                > stall_duration * stall_iteration
            ) and (
                (time.time() - self.Channel.last_message_time)
                > stall_duration * stall_iteration
            ):
                # Elapsed time since last trial is more than tolerance
                # and elapsed time since last harp message is more than tolerance

                # Check if we are in the photometry baseline period.
                if (self.finish_Timer == 0) & (
                    (time.time() - last_trial_start)
                    < (self.fip_model.baseline_time * 60 + 10)
                ):
                    # Extra 10 seconds is to avoid any race conditions
                    # We are in the photometry baseline period
                    continue

                # Prompt user to stop trials
                elapsed_time = int(
                    np.floor(stall_duration * stall_iteration / 60)
                )
                message = "{} minutes have elapsed since the last trial started. Bonsai may have stopped. Stop trials?".format(
                    elapsed_time
                )
                reply = QMessageBox.question(
                    self,
                    "Box {}, Trial Generator".format(self.box_letter),
                    message,
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if reply == QMessageBox.Yes:
                    # User stops trials
                    err_msg = "trial stalled {} minutes, user stopped trials. ANewTrial:{},Start:{},finish_Timer:{}"
                    logging.error(
                        err_msg.format(
                            elapsed_time,
                            self.ANewTrial,
                            self.Start.isChecked(),
                            self.finish_Timer,
                        )
                    )

                    # Set that the current trial ended, so we can save
                    self.ANewTrial = 1

                    # Flag Bonsai connection
                    self.InitializeBonsaiSuccessfully = 0

                    # Reset Start button
                    self.Start.setChecked(False)
                    self.Start.setStyleSheet("background-color : none")

                    # Give warning to user
                    logging.warning(
                        "Trials stalled, recheck bonsai connection.",
                        extra={"tags": [self.warning_log_tag]},
                    )
                    break
                else:
                    # User continues, wait another stall_duration and prompt again
                    logging.error(
                        "trial stalled {} minutes, user continued trials".format(
                            elapsed_time
                        )
                    )
                    stall_iteration += 1

    def _perform_backup(self, BackupSave):
        # Backup save logic
        try:
            self._Save(BackupSave=BackupSave)
        except Exception as e:
            logging.error("backup save failed: {}".format(e))

    def bias_calculated(
        self,
        bias: float,
        confidence_interval: list[float, float],
        trial_number: int,
    ) -> None:
        """
        Function to update GeneratedTrials.B_Bias and Bias attribute when new bias value is calculated
        :param bias: bias value
        :param confidence_interval: confidence interval of bias
        :param trial_number: trial number at which bias value was calculated
        """
        self.B_Bias_R = bias
        # back-fill bias list with previous bias
        last_bias_filler = [self.GeneratedTrials.B_Bias[-1]] * (
            self.GeneratedTrials.B_CurrentTrialN
            - len(self.GeneratedTrials.B_Bias)
        )
        self.GeneratedTrials.B_Bias = np.concatenate(
            (self.GeneratedTrials.B_Bias, last_bias_filler), axis=0
        )
        self.GeneratedTrials.B_Bias[trial_number - 1 :] = (
            bias  # set last value to newest bias
        )

        # back-fill bias confidence interval list with previous bias CI
        last_ci_filler = [self.GeneratedTrials.B_Bias_CI[-1]] * (
            self.GeneratedTrials.B_CurrentTrialN
            - len(self.GeneratedTrials.B_Bias_CI)
        )
        if last_ci_filler != []:
            self.GeneratedTrials.B_Bias_CI = np.concatenate(
                (self.GeneratedTrials.B_Bias_CI, last_ci_filler), axis=0
            )
            self.GeneratedTrials.B_Bias_CI[trial_number - 1 :] = (
                confidence_interval  # set last value to newest bias CI
            )

        self.GeneratedTrials.B_Bias[trial_number - 1 :] = bias

    def _StartTrialLoop1(
        self, GeneratedTrials, worker1, workerPlot, workerGenerateAtrial
    ):
        logging.info("starting trial loop 1")
        while self.Start.isChecked():
            QApplication.processEvents()
            if (
                self.ANewTrial == 1
                and self.ToGenerateATrial == 1
                and self.Start.isChecked()
            ):
                self.ANewTrial = 0  # can start a new trial when we receive the trial end signal from Bonsai
                GeneratedTrials.B_CurrentTrialN += 1
                print(
                    "Current trial: "
                    + str(GeneratedTrials.B_CurrentTrialN + 1)
                )
                logging.info(
                    "Current trial: "
                    + str(GeneratedTrials.B_CurrentTrialN + 1)
                )
                if not (
                    self.task_logic.task_parameters.auto_water is not None
                    or self.task_logic.task_parameters.block_parameters.min_reward
                    > 0
                ):
                    # generate new trial and get reward
                    self.NewTrialRewardOrder = 1
                else:
                    # get reward and generate new trial
                    self.NewTrialRewardOrder = 0
                # initiate the generated trial
                GeneratedTrials._InitiateATrial(self.Channel, self.Channel4)
                # receive licks and update figures
                if self.test == 1:
                    self.PlotM._Update(
                        GeneratedTrials=GeneratedTrials, Channel=self.Channel2
                    )
                else:
                    if self.ToUpdateFigure == 1:
                        self.ToUpdateFigure = 0
                        self.threadpool3.start(workerPlot)
                # get the response of the animal using a different thread
                self.threadpool.start(worker1)
                """
                if self.test==1:
                    self.ANewTrial=1
                    GeneratedTrials.GetResponseFinish=0
                    GeneratedTrials._GetAnimalResponse(self.Channel,self.Channel3)
                else:
                    GeneratedTrials.GetResponseFinish=0
                    self.threadpool.start(worker1)
                """
                # generate a new trial
                if self.test == 1:
                    self.ToGenerateATrial = 1
                    GeneratedTrials._GenerateATrial()
                else:
                    self.ToGenerateATrial = 0
                    self.threadpool4.start(workerGenerateAtrial)

    def _OptogeneticsB(self):
        """optogenetics control in the main window"""
        if self.OptogeneticsB.currentText() == "on":
            self._Optogenetics()  # press the optogenetics icon
            self.action_Optogenetics.setChecked(True)
            self.Opto_dialog.show()

        else:
            self.action_Optogenetics.setChecked(False)
            self.Opto_dialog.hide()

    def give_manual_water(self, valve: Literal["Right", "Left"]):
        """
        Give manual water
        :param valve: valve to give manual water
        """

        volume = getattr(
            self.task_logic.task_parameters.reward_size,
            f"{valve.lower()}_value_volume",
        )
        open_time_s = getattr(self, f"{valve.lower()}_valve_open_time")
        self._ConnectBonsai()
        if self.InitializeBonsaiSuccessfully == 0:
            return
        if self.AlignToGoCue.currentText() == "yes":
            # Reserving the water after the go cue.Each click will add the water to the reserved water
            reserve_volume = (
                getattr(self, f"give_{valve.lower()}_volume_reserved") + volume
            )
            setattr(
                self, f"give_{valve.lower()}_volume_reserved", reserve_volume
            )
            if self.latest_fitting != {}:
                time_reserve = (
                    (reserve_volume - self.latest_fitting[valve][1])
                    / self.latest_fitting[valve][0]
                ) * 1000
            else:
                time_reserve = (
                    getattr(self, f"give_{valve.lower()}_time_reserved")
                    + open_time_s * 1000
                )

            setattr(self, f"give_{valve.lower()}_time_reserved", time_reserve)
        else:
            getattr(self, f"Other_manual_water_{valve.lower()}_volume").append(
                volume
            )
            getattr(self, f"Other_manual_water_{valve.lower()}_time").append(
                open_time_s * 1000
            )

            getattr(self.Channel, f"{valve}Value")(float(open_time_s * 1000))
            time.sleep(0.01)
            getattr(self.Channel3, f"ManualWater_{valve}")(int(1))
            time.sleep(0.01 + open_time_s)
            getattr(self.Channel, f"{valve}Value")(float(open_time_s * 1000))
            index = 0 if valve == "Left" else 1
            self.ManualWaterVolume[index] = (
                self.ManualWaterVolume[index] + volume / 1000
            )
            self._UpdateSuggestedWater()
            logger.info(
                f"Give {valve.lower()} manual water (ul): {round(volume, 3)}",
                extra={"tags": [self.warning_log_tag]},
            )

    def _give_reserved_water(self, valve=Literal["Right", "Left"]):
        """
        Give reserved water usually after the go cue
        :param valve: valve to give water from
        """

        reserve = getattr(self, f"give_{valve}_volume_reserved")
        open_time_s = getattr(self, f"{valve.lower()}_valve_open_time")
        volume = getattr(
            self.task_logic.task_parameters.reward_size,
            f"{valve.lower()}_value_volume",
        )

        if reserve == 0:
            return
        getattr(self.Channel, f"{valve.title()}Value")(float(reserve))
        time.sleep(0.01)
        getattr(self.Channel3, f"ManualWater_{valve.title()}")(int(1))
        time.sleep(0.01 + reserve / 1000)
        getattr(self.Channel, f"{valve.title()}Value")(
            float(open_time_s * 1000)
        )
        index = 0 if valve == "Left" else 1
        self.ManualWaterVolume[index] = (
            self.ManualWaterVolume[index] + volume / 1000
        )
        getattr(self, f"Other_manual_water_{valve.lower()}_volume").append(
            volume
        )
        getattr(self, f"Other_manual_water_{valve.lower()}_time").append(
            open_time_s * 1000
        )
        setattr(self, f"give_{valve}_volume_reserved", 0)
        setattr(self, f"give_{valve}_time_reserved", 0)

    def _toggle_save_color(self):
        """toggle the color of the save button to mediumorchid"""
        self.unsaved_data = True
        self.start_flash.start()
        # self.Save.setStyleSheet("color: white;background-color : mediumorchid;")

    def _PostWeightChange(self):
        self.unsaved_data = True
        # self.Save.setStyleSheet("color: white;background-color : mediumorchid;")
        self.start_flash.start()
        self._UpdateSuggestedWater()

    def toggle_save_color(self):
        """
        Function to emulate flashing of color for button
        """

        """Switch button background color"""
        if self.is_purple:
            self.Save.setStyleSheet("color:black;background-color:None;")
        else:
            self.Save.setStyleSheet(
                "color: white;background-color : mediumorchid;"
            )
        self.is_purple = not self.is_purple

    def _UpdateSuggestedWater(self, ManualWater=0):
        """Update the suggested water from the manually give water"""
        try:
            if self.BaseWeight.text() != "":
                float(self.BaseWeight.text())
        except Exception as e:
            logging.warning(str(e))
            return
        try:
            if self.WeightAfter.text() != "":
                float(self.WeightAfter.text())
        except Exception as e:
            logging.warning(str(e))
            return
        try:
            if self.BaseWeight.text() != "" and self.TargetRatio.text() != "":
                # set the target weight
                target_weight = float(self.TargetRatio.text()) * float(
                    self.BaseWeight.text()
                )
                self.TargetWeight.setText(str(np.round(target_weight, 3)))

            if hasattr(self, "GeneratedTrials"):
                if hasattr(self.GeneratedTrials, "BS_TotalReward"):
                    BS_TotalReward = (
                        float(self.GeneratedTrials.BS_TotalReward) / 1000
                    )
                else:
                    BS_TotalReward = 0
            else:
                BS_TotalReward = 0

            if hasattr(self, "ManualWaterVolume"):
                ManualWaterVolume = np.sum(self.ManualWaterVolume)
            else:
                ManualWaterVolume = 0
            water_in_session = BS_TotalReward + ManualWaterVolume
            self.water_in_session = water_in_session
            if (
                self.WeightAfter.text() != ""
                and self.BaseWeight.text() != ""
                and self.TargetRatio.text() != ""
            ):
                # calculate the suggested water
                suggested_water = target_weight - float(
                    self.WeightAfter.text()
                )
                # give at lease 1ml
                if suggested_water < 1 - water_in_session:
                    suggested_water = 1 - water_in_session
                if suggested_water < 0:
                    suggested_water = 0
                # maximum 3.5ml
                if suggested_water > 3.5:
                    suggested_water = 3.5
                    if self.default_ui == "ForagingGUI.ui":
                        self.TotalWaterWarning.setText(
                            "Supplemental water is >3.5! Health issue and LAS should be alerted!"
                        )
                    elif self.default_ui == "ForagingGUI_Ephys.ui":
                        self.TotalWaterWarning.setText(
                            "Supplemental water is >3.5! Health issue and \n LAS should be alerted!"
                        )
                    self.TotalWaterWarning.setStyleSheet(
                        f"color: {self.default_warning_color};"
                    )
                else:
                    self.TotalWaterWarning.setText("")
                self.SuggestedWater.setText(str(np.round(suggested_water, 3)))
            else:
                self.SuggestedWater.setText("")
                self.TotalWaterWarning.setText("")
            # update total water
            if self.SuggestedWater.text() == "":
                ExtraWater = 0
            else:
                ExtraWater = float(self.SuggestedWater.text())
            TotalWater = ExtraWater + water_in_session
            self.TotalWater.setText(str(np.round(TotalWater, 3)))
        except Exception:
            logging.error(traceback.format_exc())

    def _open_mouse_on_streamlit(self):
        """open the training history of the current mouse on the streamlit app"""
        # See this PR: https://github.com/AllenNeuralDynamics/foraging-behavior-browser/pull/25
        webbrowser.open(
            f"https://foraging-behavior-browser.allenneuraldynamics-test.org/?filter_subject_id={self.session_model.subject}"
            "&tab_id=tab_session_inspector"
            "&session_plot_mode=all+sessions+filtered+from+sidebar"
            "&session_plot_selected_draw_types=1.+Choice+history"
        )

    def _generate_upload_manifest(self):
        """
        Generates a manifest.yml file for triggering data copy to VAST and upload to aws
        """

        # skip manifest generation for test mouse
        if self.session_model.subject in [
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "10",
        ]:
            logging.info(
                "Skipping upload manifest, because this is the test mouse"
            )
            return
        # skip manifest generation if automatic upload is disabled
        if not self.Settings["AutomaticUpload"]:
            logging.info(
                "Skipping Automatic Upload based on ForagingSettings.json"
            )
            return
        # skip manifest generation if this is an ephys session
        if self.open_ephys != [] or self.StartEphysRecording.isChecked():
            logging.info(
                "Skipping upload manifest, because this is an ephys session"
            )
            return

        logging.info("Generating upload manifest")
        try:
            date_format = "%Y-%m-%d_%H-%M-%S"
            if (
                self.session_model.date.strftime("%H-%M-%S")
                < "17-30-00"
            ):
                # Session started before 5:30
                # Upload time is 8:30 tonight, plus a random offset over a 30 minute period
                # Random offset reduces strain on downstream servers getting many requests at once
                schedule = (
                    self.session_model.date.strftime(
                        date_format
                    ).split("_")[0]
                    + "_20-30-00"
                )
                schedule_time = datetime.strptime(
                    schedule, date_format
                ) + timedelta(seconds=np.random.randint(30 * 60))
            else:
                # Session started after 5:30
                # upload time is current time plus 3 hours plus a random offset
                schedule_time = self.behavior_session_model.date + timedelta(
                    hours=3, seconds=np.random.randint(30 * 60)
                )
            capsule_id = "0ae9703f-9012-4d0b-ad8d-b6a00858b80d"
            mount = "FIP"

            modalities = {}
            modalities["behavior"] = [
                self.session_model.root_path.replace("\\", "/")
            ]
            if self.Camera_dialog.camera_start_time != "":
                modalities["behavior-videos"] = [
                    self.VideoFolder.replace("\\", "/")
                ]
            if hasattr(self, "fiber_photometry_start_time") and (
                self.fiber_photometry_start_time != ""
            ):
                modalities["fib"] = [self.PhotometryFolder.replace("\\", "/")]
                modalities["behavior-videos"] = [
                    self.VideoFolder.replace("\\", "/")
                ]

            # Define contents of manifest file
            contents = {
                "acquisition_datetime": self.session_model.date,
                "name": self.session_model.session_name,
                "platform": "behavior",
                "subject_id": int(self.session_model.subject),
                "capsule_id": capsule_id,
                "mount": mount,
                "destination": "//allen/aind/scratch/dynamic_foraging_rig_transfer",
                "s3_bucket": "open",
                "processor_full_name": "AIND Behavior Team",
                "modalities": modalities,
                "schemas": [
                    os.path.join(self.MetadataFolder, "session.json").replace(
                        "\\", "/"
                    ),
                    os.path.join(self.MetadataFolder, "rig.json").replace(
                        "\\", "/"
                    ),
                ],
                "schedule_time": schedule_time,
                "project_name": self.Metadata_dialog.ProjectName.currentText(),
                "script": {},
            }

            # Define filename of manifest
            if not os.path.exists(self.Settings["manifest_flag_dir"]):
                os.makedirs(self.Settings["manifest_flag_dir"])
            filename = os.path.join(
                self.Settings["manifest_flag_dir"],
                "manifest_{}.yml".format(contents["name"]),
            )

            # Write the manifest file
            with open(filename, "w") as yaml_file:
                yaml.dump(contents, yaml_file, default_flow_style=False)
            logging.info("Finished generating manifest")
        except Exception as e:
            logging.error(
                "Could not generate upload manifest: {}".format(str(e))
            )
            QMessageBox.critical(
                self,
                "Upload manifest",
                "Could not generate upload manifest. "
                + "Please alert the mouse owner, and report on github.",
            )


def setup_loki_logging(box_number):
    db_file = os.getenv(
        "SIPE_DB_FILE", r"//allen/aibs/mpe/keepass/sipe_sw_passwords.kdbx"
    )
    key_file = os.getenv(
        "SIPE_KEY_FILE",
        r"c:\ProgramData\AIBS_MPE\.secrets\sipe_sw_passwords.keyx",
    )
    kp = PyKeePass(db_file, keyfile=key_file)
    entry = kp.find_entries(title="Loki Credentials", first=True)
    session = md5(
        (
            "".join([str(datetime.now()), platform.node(), str(os.getpid())])
        ).encode("utf-8")
    ).hexdigest()[:7]

    handler = logging_loki.LokiHandler(
        url="http://eng-tools/loki/api/v1/push",
        tags={
            "hostname": socket.gethostname(),
            "process_name": __name__,
            "user_name": os.getlogin(),
            "log_session": session,
            "box_name": chr(box_number + 64),  # they use A=1, B=2, ...
        },
        auth=(entry.username, entry.password),
        version="1",
    )

    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s\n%(name)s\n%(levelname)s\n%(funcName)s (%(filename)s:%(lineno)d)\n%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.setLevel(logging.INFO)
    logger.root.addHandler(handler)


def start_gui_log_file(box_number):
    """
    Starts a log file for the gui.
    The log file is located at C:/Users/<username>/Documents/foraging_gui_logs
    One log file is created for each time the GUI is started
    The name of the gui file is <hostname>-<box letter A/B/C/D>_gui_log_<date and time>.txt
    """
    # Check if the log folder exists, if it doesn't make it
    logging_folder = os.path.join(
        os.path.expanduser("~"), "Documents", "foraging_gui_logs"
    )
    if not os.path.exists(logging_folder):
        os.makedirs(logging_folder)

    # Determine name of this log file
    # Get current time
    current_time = datetime.now()
    formatted_datetime = current_time.strftime("%Y-%m-%d_%H-%M-%S")

    # Build logfile name
    hostname = socket.gethostname()
    box_mapping = {1: "A", 2: "B", 3: "C", 4: "D"}
    box_name = hostname + "-" + box_mapping[box_number]
    filename = "{}_gui_log_{}.txt".format(box_name, formatted_datetime)
    logging_filename = os.path.join(logging_folder, filename)

    # Format the log file:
    log_format = "%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(funcName)s:line %(lineno)d:%(message)s"
    log_datefmt = "%I:%M:%S %p"

    # Start the log file
    print("Starting a GUI log file at: ")
    print(logging_filename)

    log_formatter = logging.Formatter(fmt=log_format, datefmt=log_datefmt)
    file_handler = logging.FileHandler(logging_filename)
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
    logger.root.addHandler(file_handler)

    logging.info("Starting logfile!")
    logging.captureWarnings(True)


def log_git_hash():
    """
    Add a note to the GUI log about the current branch and hash. Assumes the local repo is clean
    """

    # Get information about python
    py_version = sys.version
    py_version_parse = ".".join(py_version.split(".")[0:2])
    logging.info("Python version: {}".format(py_version))
    print("Python version: {}".format(py_version))
    if py_version_parse != "3.11":
        logging.error(
            "Incorrect version of python! Should be 3.11, got {}".format(
                py_version_parse
            )
        )

    try:
        # Get information about task repository
        git_hash = (
            subprocess.check_output(["git", "rev-parse", "HEAD"])
            .decode("ascii")
            .strip()
        )
        git_branch = (
            subprocess.check_output(["git", "branch", "--show-current"])
            .decode("ascii")
            .strip()
        )
        repo_url = (
            subprocess.check_output(["git", "remote", "get-url", "origin"])
            .decode("ascii")
            .strip()
        )
        dirty_files = (
            subprocess.check_output(
                ["git", "diff-index", "--name-only", "HEAD"]
            )
            .decode("ascii")
            .strip()
        )
        version = foraging_gui.__version__
    except Exception as e:
        logging.error("Could not log git branch and hash: {}".format(str(e)))
        return None, None, None, None, None, None

    # Log branch and commit hash
    logging.info(
        "Current git commit branch, hash: {}, {}".format(git_branch, git_hash)
    )
    print(
        "Current git commit branch, hash: {}, {}".format(git_branch, git_hash)
    )

    # Log gui version:
    logging.info(
        "Current foraging_gui version: {}".format(foraging_gui.__version__)
    )
    print("Current foraging_gui version: {}".format(foraging_gui.__version__))

    # Check for untracked local changes
    repo_dirty_flag = dirty_files != ""
    if repo_dirty_flag:
        dirty_files = dirty_files.replace("\n", ", ")
        logging.warning(
            "local repository has untracked changes to the following files: {}".format(
                dirty_files
            )
        )
        print(
            "local repository has untracked changes to the following files: {}".format(
                dirty_files
            )
        )
    else:
        logging.warning("local repository is clean")
        print("local repository is clean")

    return (
        git_hash,
        git_branch,
        repo_url,
        repo_dirty_flag,
        dirty_files,
        version,
    )


def show_msg_box(window_title, title, msg):
    """
    Display a Qwindow alert to the user. This is originally implemented to debug the stagewidget connection issues.
    This can be removed after the issue is resolved.
    """
    if QtWidgets.QApplication.instance() is not None:
        msg_box = QtWidgets.QMessageBox()
        msg_box.setWindowTitle(window_title)
        msg_box.setText(
            '<span style="color:purple;font-weight:bold"> {} </span> <br><br> {}'.format(
                title, msg
            )
        )
        msg_box.exec_()
    else:
        logging.error("could not launch custom message box")


def show_exception_box(log_msg):
    """
    Displays a Qwindow alert to the user that an uncontrolled error has occured, and the error message
    if no QApplication instance is available, logs a note in the GUI log
    """
    # Check if a QApplication instance is running
    if QtWidgets.QApplication.instance() is not None:
        box = log_msg[0]  # Grab the box letter
        log_msg = log_msg[1:]  # Grab the error messages

        # Make a QWindow, wait for user response
        errorbox = QtWidgets.QMessageBox()
        errorbox.setWindowTitle("Box {}, Error".format(box))
        msg = '<span style="color:purple;font-weight:bold">An uncontrolled error occurred. Save any data and restart the GUI. </span> <br><br>{}'.format(
            log_msg
        )
        errorbox.setText(msg)
        errorbox.exec_()
    else:
        logging.error("could not launch exception box")


def is_absolute_path(path):
    # Check if the path starts with a root directory identifier or drive letter (for Windows)
    return path.startswith("/") or (
        len(path) > 2 and path[1] == ":" and path[2] == "\\"
    )


class UncaughtHook(QtCore.QObject):
    """
    This class handles uncaught exceptions and hooks into the sys.excepthook
    """

    _exception_caught = QtCore.Signal(object)

    def __init__(self, box_number, *args, **kwargs):
        super(UncaughtHook, self).__init__(*args, **kwargs)

        # Determine what Box we are in
        mapper = {1: "A", 2: "B", 3: "C", 4: "D"}
        self.box = mapper[box_number]

        # Hook into the system except hook
        sys.excepthook = self.exception_hook

        # Call our custom function to display an alert
        self._exception_caught.connect(show_exception_box)

    def exception_hook(self, exc_type, exc_value, exc_traceback):
        """
        Log the error in the log, and display in the console
        then call our custom hook function to display an alert
        """

        # Display in console
        tb = "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )
        print("Encountered a fatal error: ")
        print(tb)

        # Add to log
        logging.error("FATAL ERROR: \n{}".format(tb))

        # Display alert box
        tb = "<br><br>".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )
        self._exception_caught.emit(self.box + tb)


def log_subprocess_output(process, prefix):
    logging.info("{} logging starting".format(prefix))
    while process.poll() is None:
        output = process.stdout.readline()
        if "Exception" in output:
            logging.error(prefix + ": " + output.strip())
        else:
            logging.info(prefix + ": " + output.strip())

    logging.info("{} logging terminating".format(prefix))


if __name__ == "__main__":
    # Determine which box we are using, and whether to start bonsai IDE
    start_bonsai_ide = True
    if len(sys.argv) == 1:
        box_number = 1
    elif len(sys.argv) == 2:
        box_number = int(sys.argv[1])
    else:
        box_number = int(sys.argv[1])
        if sys.argv[2] == "--no-bonsai-ide":
            start_bonsai_ide = False

    # Start logging
    start_gui_log_file(box_number)
    try:
        setup_loki_logging(box_number)
    except Exception as e:  # noqa
        logging.warning(f"Failed to setup LOKI Handler: {e}")

    (
        commit_ID,
        current_branch,
        repo_url,
        repo_dirty_flag,
        dirty_files,
        version,
    ) = log_git_hash()

    # Formating GUI graphics
    logging.info("Setting QApplication attributes")
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, 1)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QApplication.setAttribute(Qt.AA_DisableHighDpiScaling, False)
    QApplication.setAttribute(Qt.AA_Use96Dpi, False)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Start QApplication
    logging.info("Starting QApplication and Window")
    app = QApplication(sys.argv)

    # Create global instance of uncaught exception handler
    qt_exception_hook = UncaughtHook(box_number)

    # Start GUI window
    win = Window(box_number=box_number, start_bonsai_ide=start_bonsai_ide)
    # Get the commit hash of the current version of this Python file
    win.current_branch = current_branch
    win.repo_url = repo_url
    win.dirty_files = dirty_files
    win.show()

    # Run your application's event loop and stop after closing all windows
    sys.exit(app.exec())
