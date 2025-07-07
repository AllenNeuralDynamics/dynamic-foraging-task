import json
import logging
import os
import re
import subprocess
from datetime import datetime

import numpy as np
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_data_schema.components.coordinates import (
    Axis,
    AxisName,
    RelativePosition,
    Rotation3dTransform,
    Translation3dTransform,
)
from aind_data_schema.components.devices import Calibration, SpoutSide
from aind_data_schema.components.stimulus import AuditoryStimulation
from aind_data_schema.core.session import (
    Coordinates3d,
    DetectorConfig,
    DomeModule,
    FiberConnectionConfig,
    LaserConfig,
    LightEmittingDiodeConfig,
    ManipulatorModule,
    RewardDeliveryConfig,
    RewardSolution,
    RewardSpoutConfig,
    Session,
    Software,
    SpeakerConfig,
    StimulusEpoch,
    StimulusModality,
    Stream,
    TriggerType,
)
from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform
from aind_data_schema_models.units import (
    FrequencyUnit,
    PowerUnit,
    SizeUnit,
    SoundIntensityUnit,
    TimeUnit
)

import foraging_gui
from foraging_gui.TransferToNWB import _get_field
from foraging_gui.Visualization import PlotWaterCalibration


class generate_metadata:
    """
    Parse the behavior json file and generate session and rig metadata

    Parameters:
    Obj: dict
        dictionary containing the json file.
    json_file: str
        path to the json file. If provided, the json file will be loaded to the Obj.
    dialog_metadata: dict
        dictionary containing the dialog metadata. If provided, it will override the meta_data_dialog key in the json file.
    output_folder: str
        path to the output folder where the metadata will be saved. If not provided, the metadata will be saved in the MetadataFolder extracted from the behavior json file/object.

    Output:
    session metadata: json file
        json file to the metadata folder
    rig metadata: json file
        json file to the metadata folder

    """

    def __init__(
        self,
        json_file=None,
        Obj=None,
        dialog_metadata_file=None,
        dialog_metadata=None,
        output_folder=None,
    ):
        self.session_metadata_success = False
        self.rig_metadata_success = False

        if Obj is None:
            self._set_metadata_logging()

        if json_file is None and Obj is None:
            logging.info("json file or Obj is not provided")
            return

        if json_file is not None:
            with open(json_file) as f:
                self.Obj = json.load(f)
            self.session_folder = os.path.dirname(os.path.dirname(json_file))
        else:
            self.Obj = Obj
            if "TrainingFolder" in self.Obj:
                self.session_folder = os.path.dirname(
                    self.Obj["TrainingFolder"]
                )
            else:
                self.session_folder = "session folder is unknown"
        logging.info("processing:" + self.session_folder)

        if dialog_metadata_file is not None:
            with open(dialog_metadata_file) as f:
                self.Obj["meta_data_dialog"] = json.load(f)
        elif dialog_metadata is not None:
            self.Obj["meta_data_dialog"] = dialog_metadata

        if output_folder is not None:
            self.output_folder = output_folder
        elif json_file is not None:
            self._get_metadata_folder(json_file)
        elif "MetadataFolder" in self.Obj:
            self.output_folder = self.Obj["MetadataFolder"]
        else:
            logging.info("MetadataFolder is not determined")

        return_tag = self._handle_edge_cases()
        if return_tag == 1:
            return
        self._save_rig_metadata()
        self.Obj["session_metadata"] = {}
        self._mapper()
        self._get_box_type()
        self._session()

        logging.info(
            "Session metadata generated successfully: "
            + str(self.session_metadata_success)
        )
        logging.info(
            "Rig metadata generated successfully: "
            + str(self.rig_metadata_success)
        )

    def _mapper(self):
        """
        Name mapping
        """
        if "settings" in self.Obj:
            if "name_mapper_file" in self.Obj["settings"]:
                if os.path.exists(self.Obj["settings"]["name_mapper_file"]):
                    with open(self.Obj["settings"]["name_mapper_file"]) as f:
                        self.name_mapper_external = json.load(f)

        self.name_mapper = {
            "laser_name_mapper": {
                "Oxxius Laser 473-1": {"color": "Blue", "laser_tag": 1},
                "Oxxius Laser 473-2": {"color": "Blue", "laser_tag": 2},
                "Oxxius Laser 561-1": {"color": "Yellow", "laser_tag": 1},
                "Oxxius Laser 561-2": {"color": "Yellow", "laser_tag": 2},
                "Oxxius Laser 638-1": {"color": "Red", "laser_tag": 1},
                "Oxxius Laser 638-2": {"color": "Red", "laser_tag": 2},
            },  # laser name in the rig metadata and the corresponding color used in the behavior GUI
            "led_name_mapper": {
                "LED 460-1": {"color": "Blue", "laser_tag": 1},
                "LED 460-2": {"color": "Blue", "laser_tag": 2},
            },  # led name in the rig metadata and the corresponding color used in the behavior GUI
            "laser_tags": [
                1,
                2,
            ],  # laser tags corresponding to Laser_1 and Laser_2
            "sides": ["Left", "Right"],  # lick spouts
            "camera_list": [
                "SideCameraLeft",
                "SideCameraRight",
                "BottomCamera",
                "BodyCamera",
            ],  # camera names in the settings_box.csv
            "camera_name_mapper": {
                "SideCameraLeft": "Face Side Left",
                "SideCameraRight": "Face Side Right",
                "BottomCamera": "Face Bottom",
                "BodyCamera": "Body",
            },  # camera names in the settings_box.csv and the corresponding names in the rig metadata
            "institute": {
                "Allen Institute": "AI",
                "NINDS": "NINDS",
                "Simons Foundation": "SIMONS",
            },
            "rig_daq_names_janelia_lick_detector": [
                "harp behavior board",
                "harp sound card",
                "harp clock synchronization board",
                "harp sound amplifier",
            ],
            "rig_daq_names_aind_lick_detector": [
                "harp behavior board",
                "harp sound card",
                "harp clock synchronization board",
                "harp sound amplifier",
                "harp lickety split left",
                "harp lickety split right",
            ],
            "fiber_photometry_daq_names": [""],
            "ephys_daq_names": ["neuropixel basestation"],
            "optogenetics_daq_names": ["optogenetics nidaq"],
        }

        # replacing fileds with the external name mapper
        if hasattr(self, "name_mapper_external"):
            for key in self.name_mapper_external:
                self.name_mapper[key] = self.name_mapper_external[key]

    def _set_metadata_logging(self):
        """
        Set the logging for the metadata generation. Don't use the behavior GUI logger.
        """
        # Check if the log folder exists, if it doesn't make it
        logging_folder = os.path.join(
            os.path.expanduser("~"), "Documents", "foraging_metadata_logs"
        )
        if not os.path.exists(logging_folder):
            os.makedirs(logging_folder)

        # Determine name of this log file
        # Get current time. Generate one log file per day.
        current_time = datetime.now()
        formatted_datetime = current_time.strftime("%Y-%m-%d")

        # Build logfile name
        filename = "{}_metadata_log.txt".format(formatted_datetime)
        logging_filename = os.path.join(logging_folder, filename)

        # Format the log file:
        log_format = "%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(funcName)s:line %(lineno)d:%(message)s"
        log_datefmt = "%I:%M:%S %p"

        # Start the log file
        print("Starting a GUI log file at: ")
        print(logging_filename)
        logging.basicConfig(
            format=log_format,
            level=logging.INFO,
            datefmt=log_datefmt,
            handlers=[
                logging.FileHandler(logging_filename),
            ],
        )
        logging.info("Starting logfile!")
        logging.captureWarnings(True)

    def _get_metadata_folder(self, json_file):
        """
        Get the metadata folder
        """
        session_folder = os.path.dirname(os.path.dirname(json_file))
        metadata_folder = os.path.join(session_folder, "metadata-dir")
        self.output_folder = metadata_folder
        if not os.path.exists(metadata_folder):
            os.makedirs(metadata_folder)

    def _get_lick_spouts_distance(self):
        """
        get the distance between the two lick spouts in um
        """
        self.lick_spouts_distance = 5000

    def _get_box_type(self):
        """
        To judge the box type (ephys or behavior) based on the rig_id. This should be improved in the future.
        """

        if "rig_id" not in self.Obj["meta_data_dialog"]["rig_metadata"]:
            self.box_type = "Unknown"
            logging.info("rig id is not found in the rig metadata!")
            return

        if "EPHYS" in self.Obj["meta_data_dialog"]["rig_metadata"]["rig_id"]:
            self.box_type = "Ephys"
        else:
            self.box_type = "Behavior"

    def _get_platform(self):
        """
        Get the platform name. This should be improved in the future.
        """
        if self.box_type == "Ephys":
            self.platform = Platform.ECEPHYS
        elif self.box_type == "Behavior":
            self.platform = Platform.BEHAVIOR
        else:
            self.platform = ""

    def _get_session_time(self):
        """
        Get the session start and session end time
        """
        # Initialize empty lists to store start and end times
        start_times = []
        end_times = []

        # List of all stream lists
        all_streams = [
            self.behavior_streams,
            self.high_speed_camera_streams,
            self.ephys_streams,
            self.ophys_streams,
        ]

        # Iterate over each stream list and collect times
        for stream_list in all_streams:
            for stream in stream_list:
                start_times.append(stream.stream_start_time)
                end_times.append(stream.stream_end_time)

        # Determine the session start and end times
        if start_times and end_times:
            self.session_start_time = min(start_times)
            self.session_end_time = max(end_times)
        else:
            self.session_start_time = ""
            self.session_end_time = ""

    def _save_rig_metadata(self):
        """
        Save the rig metadata to the MetadataFolder
        """
        if (
            self.Obj["meta_data_dialog"]["rig_metadata_file"] == ""
            or self.output_folder == ""
        ):
            logging.info("rig_metadata_file or the out_put folder is emtpy!")
            return

        # save copy as rig.json
        rig_metadata_full_path = os.path.join(self.output_folder, "rig.json")
        with open(rig_metadata_full_path, "w") as f:
            json.dump(
                self.Obj["meta_data_dialog"]["rig_metadata"], f, indent=4
            )
            self.rig_metadata_success = True

    def _handle_edge_cases(self):
        """
        handle edge cases (e.g. missing keys in the json file)
        """

        # Missing filed version in the json file.
        # Possible reason: 1) Old version of the software.
        if "version" not in self.Obj:
            self.Obj["version"] = "Not recorded"

        # Missing field 'meta_data_dialog' in the json file.
        # Possible reason: 1) Old version of the software.
        if "meta_data_dialog" not in self.Obj:
            self.Obj["meta_data_dialog"] = {}
            logging.info("Missing metadata dialog for session metadata")
            return 1

        # Missing fields camera_start_time and camera_stop_time in the Camera_dialog.
        # Possible reason: 1) the camera is not used in the session. 2 ) the camera is used but the start and end time are not recorded for old version of the software.
        self._initialize_fields(
            dic=self.Obj["Camera_dialog"],
            keys=["camera_start_time", "camera_stop_time"],
            default_value="",
        )

        # Missing Behavior data streams in the json file.
        # Possible reason: 1) the behavior data is not started in the session.
        if "B_AnimalResponseHistory" not in self.Obj:
            self.has_behavior_data = False
            logging.info(
                "No animal response history to log in session metadata"
            )
        else:
            self.has_behavior_data = True

        # Missing fields B_StagePositions, LickSpoutReferenceArea, LickSpoutReferenceX, LickSpoutReferenceY, LickSpoutReferenceZ in the json file.
        # Possible reason: 1) the NewScale stage is not connected to the behavior GUI. 2) the session is not started.
        if (
            ("B_StagePositions" not in self.Obj)
            or (
                self.Obj["meta_data_dialog"]["session_metadata"][
                    "LickSpoutReferenceArea"
                ]
                == ""
            )
            or (
                self.Obj["meta_data_dialog"]["session_metadata"][
                    "LickSpoutReferenceX"
                ]
                == ""
            )
            or (
                self.Obj["meta_data_dialog"]["session_metadata"][
                    "LickSpoutReferenceY"
                ]
                == ""
            )
            or (
                self.Obj["meta_data_dialog"]["session_metadata"][
                    "LickSpoutReferenceZ"
                ]
                == ""
            )
        ):
            self.has_reward_delivery = False
            logging.info(
                "Cannot log reward delivery in session metadata - missing fields"
            )
        elif self.Obj["B_StagePositions"] == []:
            self.has_reward_delivery = False
            logging.info(
                "Cannot log reward delivery in session metadata - missing newscale positions"
            )
        else:
            self.has_reward_delivery = True

        # Missing field WaterCalibrationResults in the json file.
        # Possible reason: 1) the water calibration file is not included in the ForagingSettings folder. 2) the water calibration is not saved in the json file.
        if "WaterCalibrationResults" not in self.Obj:
            self.Obj["WaterCalibrationResults"] = {}
            logging.info("No water calibration file for session metadata")

        # Missing field LaserCalibrationResults in the json file.
        # Possible reason: 1) the optogenetic calibration file is not included in the ForagingSettings folder. 2) the optogenetic calibration is not saved in the json file. 3) no optogenetics calibration for this rig.
        if "LaserCalibrationResults" not in self.Obj:
            self.Obj["LaserCalibrationResults"] = {}
            logging.info("No laser calibration file for session metadata")

        # Missing field open_ephys in the json file.
        # Possible reason: 1) The ephys data is recorded but the open ephys is not controlled by the behavior GUI in the old version.
        if "open_ephys" not in self.Obj:
            self.Obj["open_ephys"] = []
            logging.info("no open ephys data for session metadata")

        # Missing field Camera_dialog in the json file.
        # Possible reason: 1) Old version of the software.
        if "Camera_dialog" not in self.Obj:
            self.Obj["Camera_dialog"] = {}
            logging.info("no camera data for session metadata")

        # Missing field 'settings_box' in the json file.
        # Possible reason: 1) Old version of the software.
        if "settings_box" not in self.Obj:
            self.Obj["settings_box"] = {}
            logging.info("Missing settings_box.csv file for session metadata")

        # Missing field 'rig_metadata' in the json file.
        # Possible reason: 1) Old version of the software. 2) the rig metadata is not provided.
        if "rig_metadata" not in self.Obj["meta_data_dialog"]:
            self.Obj["meta_data_dialog"]["rig_metadata"] = {}
            logging.info("Missing rig metadata for session metadata")
            return 1
        elif self.Obj["meta_data_dialog"]["rig_metadata"] == {}:
            logging.info("Missing rig metadata for session metadata")
            return 1

        # Missing field 'rig_metadata_file' and 'MetadataFolder' in the json file.
        # Possible reason: 1) Old version of the software. 2) the rig metadata is not provided.
        self._initialize_fields(
            dic=self.Obj["meta_data_dialog"],
            keys=["rig_metadata_file"],
            default_value="",
        )
        self._initialize_fields(
            dic=self.Obj, keys=["MetadataFolder"], default_value=""
        )

        # Missing field Other_go_cue_decibel is not recorded in the behavior json file.
        # Possible reason: 1) the go cue decibel is not set in the foraging settings file. 2) old version of the software.
        if self.Obj.get("Other_go_cue_decibel", "") == "":
            self.Obj["Other_go_cue_decibel"] = 74
            logging.error(
                "No go cue decibel recorded in the ForagingSettings.json file. Using default value of 74 dB"
            )

        # Missing field 'fiber_photometry_start_time' and 'fiber_photometry_end_time' in the json file.
        # Possible reason: 1) the fiber photometry data is not recorded in the session. 2) the fiber photometry data is recorded but the start and end time are not recorded in the old version of the software.
        self._initialize_fields(
            dic=self.Obj,
            keys=["fiber_photometry_start_time", "fiber_photometry_end_time"],
            default_value="",
        )

        # Missing field 'FIPMode' in the json file.
        # Possible reason: 1) old version of the software.
        if "FIPMode" not in self.Obj:
            self.Obj["fiber_mode"] = ""
        else:
            self.Obj["fiber_mode"] = self.Obj["FIPMode"]

        # Missing field 'commit_ID', 'repo_url', 'current_branch' in the json file.
        # Possible reason: 1) old version of the software.
        if "commit_ID" not in self.Obj:
            self._initialize_fields(
                dic=self.Obj,
                keys=["commit_ID", "repo_url", "current_branch"],
                default_value="",
            )

        # Missing field or empty 'Other_lick_spout_distance' in the json file.
        # Possible reason: 1) old version of the software.
        if "Other_lick_spout_distance" not in self.Obj:
            self.Obj["Other_lick_spout_distance"] = 5000
        if self.Obj["Other_lick_spout_distance"] == "":
            self.Obj["Other_lick_spout_distance"] = 5000

        # Missing ProjectName
        # Possible reason: 1) old version of the software. 2) the "Project Name and Funding Source v2.csv" is not provided.
        self._initialize_fields(
            dic=self.Obj["meta_data_dialog"]["session_metadata"],
            keys=["ProjectName"],
            default_value="",
        )

        # Missing field 'B_AnimalResponseHistory' in the json file.
        # Possible reason: 1) the behavior data is not started in the session.
        # total_reward_consumed_in_session is the reward animal consumed in the session, not including the supplementary water.
        if "B_AnimalResponseHistory" not in self.Obj:
            self.trials_total = 0
            self.trials_finished = 0
            self.trials_rewarded = 0
            self.total_reward_consumed_in_session = 0
        else:
            self.Obj["B_AnimalResponseHistory"] = np.array(
                self.Obj["B_AnimalResponseHistory"]
            )
            self.trials_total = len(self.Obj["B_AnimalResponseHistory"])
            self.trials_finished = np.count_nonzero(
                self.Obj["B_AnimalResponseHistory"] != 2
            )
            self.trials_rewarded = np.count_nonzero(
                np.logical_or(
                    self.Obj["B_RewardedHistory"][0],
                    self.Obj["B_RewardedHistory"][1],
                )
            )
            self.total_reward_consumed_in_session = float(
                self.Obj.get("BS_TotalReward", 0)
            )

        # Wrong format of WeightAfter
        # Remove all the non-numeric characters except the dot in the WeightAfter
        if self.Obj["WeightAfter"] != "":
            self.Obj["WeightAfter"] = self.Obj["WeightAfter"].replace(
                "..", "."
            )
            self.Obj["WeightAfter"] = re.sub(
                r"[^\.\d]", "", self.Obj["WeightAfter"]
            )

        # Typo
        if "PtotocolID" in self.Obj["meta_data_dialog"]["session_metadata"]:
            self.Obj["meta_data_dialog"]["session_metadata"]["ProtocolID"] = (
                self.Obj["meta_data_dialog"]["session_metadata"]["PtotocolID"]
            )

        # Get the lick detector
        if "AINDLickDetector" not in self.Obj["settings_box"]:
            self.Obj["settings_box"]["AINDLickDetector"] = 0
        else:
            self.Obj["settings_box"]["AINDLickDetector"] = int(
                self.Obj["settings_box"]["AINDLickDetector"]
            )

    def _initialize_fields(self, dic, keys, default_value=""):
        """
        Initialize fields
            If dic has the key, do nothing
            If dic does not have the key, add the key with the default value

        Parameters:
        dic: dict
            dictionary to be initialized
        keys: list
            key to be initialized
        default_value: any
        """
        for key in keys:
            if key not in dic:
                dic[key] = default_value

    def _session(self):
        """
        Create metadata related to Session class in the aind_data_schema
        """
        # session_start_time and session_end_time are required fields
        if self.Obj["meta_data_dialog"]["rig_metadata"] == {}:
            logging.info("rig metadata is empty!")
            return
        self._get_reward_delivery()
        self._get_water_calibration()
        self._get_opto_calibration()
        self.calibration = self.water_calibration + self.opto_calibration
        self._get_behavior_software()
        self._get_behavior_stream()
        self._get_ephys_stream()
        self._get_ophys_stream()
        self._get_high_speed_camera_stream()
        self._get_session_time()
        if self.session_start_time == "" or self.session_end_time == "":
            logging.info("session start time or session end time is empty!")
            return

        self._get_stimulus()
        self._combine_data_streams()
        # self.data_streams = self.ephys_streams+self.ophys_streams+self.high_speed_camera_streams

        session_params = {
            "experimenter_full_name": [self.Obj["Experimenter"]],
            "subject_id": self.Obj["ID"],
            "session_start_time": self.session_start_time,
            "session_end_time": self.session_end_time,
            "session_type": self.Obj["Task"],
            "iacuc_protocol": self.Obj["meta_data_dialog"]["session_metadata"][
                "IACUCProtocol"
            ],
            "rig_id": self.Obj["meta_data_dialog"]["rig_metadata"]["rig_id"],
            "notes": self.Obj["ShowNotes"],
            "weight_unit": "gram",
            "reward_consumed_total": self.total_reward_consumed_in_session,
            "reward_consumed_unit": "microliter",
            "calibrations": self.calibration,
            "data_streams": self.data_streams,
            "mouse_platform_name": self.Obj["meta_data_dialog"][
                "rig_metadata"
            ]["mouse_platform"]["name"],
            "active_mouse_platform": False,
            "protocol_id": [
                self.Obj["meta_data_dialog"]["session_metadata"]["ProtocolID"]
            ],
        }

        if self.reward_delivery != []:
            session_params["reward_delivery"] = self.reward_delivery

        # adding go cue and opto parameters to the stimulus_epochs
        if self.stimulus != []:
            session_params["stimulus_epochs"] = self.stimulus

        if self.Obj["WeightAfter"] != "":
            session_params["animal_weight_post"] = float(
                self.Obj["WeightAfter"]
            )
        if self.Obj["BaseWeight"] != "":
            session_params["animal_weight_prior"] = float(
                self.Obj["BaseWeight"]
            )
        session = Session(**session_params)
        session.write_standard_file(output_directory=self.output_folder)
        self.session_metadata_success = True
        return session

    def _combine_data_streams(self):
        """
        Combine the data streams
        """

        self.data_streams = self.high_speed_camera_streams
        if self.data_streams == []:
            self.data_streams = self.ophys_streams
        elif self.ophys_streams != []:
            # add the ophys streams to the high speed camera streams
            self.data_streams[0].stream_modalities = (
                self.data_streams[0].stream_modalities
                + self.ophys_streams[0].stream_modalities
            )
            self.data_streams[0].stream_start_time = min(
                self.data_streams[0].stream_start_time,
                self.ophys_streams[0].stream_start_time,
            )
            self.data_streams[0].stream_end_time = max(
                self.data_streams[0].stream_end_time,
                self.ophys_streams[0].stream_end_time,
            )
            self.data_streams[0].daq_names = (
                self.data_streams[0].daq_names
                + self.ophys_streams[0].daq_names
            )
            self.data_streams[0].light_sources = (
                self.data_streams[0].light_sources
                + self.ophys_streams[0].light_sources
            )
            self.data_streams[0].detectors = (
                self.data_streams[0].detectors
                + self.ophys_streams[0].detectors
            )
            self.data_streams[0].fiber_connections = (
                self.data_streams[0].fiber_connections
                + self.ophys_streams[0].fiber_connections
            )
            self.data_streams[0].notes = (
                str(self.data_streams[0].notes)
                + ";"
                + str(self.ophys_streams[0].notes)
            )
            self.data_streams[0].software = self.ophys_streams[0].software

        if self.data_streams == []:
            self.data_streams = self.ephys_streams
        elif self.ephys_streams != []:
            # add the first ephys streams (associated with the behavior) to the high speed camera streams
            self.data_streams[0].stream_modalities = (
                self.data_streams[0].stream_modalities
                + self.ephys_streams[0].stream_modalities
            )
            self.data_streams[0].stream_start_time = min(
                self.data_streams[0].stream_start_time,
                self.ephys_streams[0].stream_start_time,
            )
            self.data_streams[0].stream_end_time = max(
                self.data_streams[0].stream_end_time,
                self.ephys_streams[0].stream_end_time,
            )
            self.data_streams[0].daq_names = (
                self.data_streams[0].daq_names
                + self.ephys_streams[0].daq_names
            )
            self.data_streams[0].ephys_modules = (
                self.data_streams[0].ephys_modules
                + self.ephys_streams[0].ephys_modules
            )
            self.data_streams[0].stick_microscopes = (
                self.data_streams[0].stick_microscopes
                + self.ephys_streams[0].stick_microscopes
            )
            self.data_streams[0].notes = (
                str(self.data_streams[0].notes)
                + ";"
                + str(self.ephys_streams[0].notes)
            )

        # combine other ephys streams
        self.data_streams2 = []
        if len(self.ephys_streams) > 2:
            self.data_streams2 = self.ephys_streams[1]
            for ephys_stream in self.ephys_streams[2:]:
                self.data_streams2.stream_start_time = min(
                    self.data_streams2.stream_start_time,
                    ephys_stream.stream_start_time,
                )
                self.data_streams2.stream_end_time = max(
                    self.data_streams2.stream_end_time,
                    ephys_stream.stream_end_time,
                )
                self.data_streams2.notes = (
                    str(self.data_streams2.notes)
                    + ";"
                    + str(ephys_stream.notes)
                )
        if self.data_streams2 != []:
            self.data_streams.append(self.data_streams2)

    def _get_high_speed_camera_stream(self):
        """
        Make the high speed camera stream metadata
        """
        self.high_speed_camera_streams = []
        self._get_camera_names()
        if (
            self.Obj["Camera_dialog"]["camera_start_time"] != ""
            and self.camera_names != []
        ):
            if self.Obj["Camera_dialog"]["camera_stop_time"] == "":
                camera_stop_time = datetime.now()
            else:
                camera_stop_time = datetime.strptime(
                    self.Obj["Camera_dialog"]["camera_stop_time"],
                    "%Y-%m-%d %H:%M:%S.%f",
                )
            self.high_speed_camera_streams.append(
                Stream(
                    stream_modalities=[Modality.BEHAVIOR_VIDEOS],
                    camera_names=self.camera_names,
                    stream_start_time=datetime.strptime(
                        self.Obj["Camera_dialog"]["camera_start_time"],
                        "%Y-%m-%d %H:%M:%S.%f",
                    ),
                    stream_end_time=camera_stop_time,
                    software=self.behavior_software,
                )
            )
        else:
            logging.info("No camera data stream detected!")

    def _get_camera_names(self):
        """
        get cameras used in this session
        """
        if "settings_box" not in self.Obj:
            self.camera_names = []
            logging.info(
                "Settings box is not provided and camera names can not be extracted!"
            )
            return

        self.camera_names = []
        for camera in self.name_mapper["camera_list"]:
            if "Has" + camera in self.Obj["settings_box"]:
                if self.Obj["settings_box"]["Has" + camera] == "1":
                    self.camera_names.append(
                        self.name_mapper["camera_name_mapper"][camera]
                    )

    def _get_ophys_stream(self):
        """
        Make the ophys stream metadata
        """
        self.ophys_streams = []
        if self.Obj["fiber_photometry_start_time"] == "":
            logging.info("No photometry data stream detected!")
            return
        if self.Obj["fiber_photometry_end_time"] == "":
            self.Obj["fiber_photometry_end_time"] = str(datetime.now())
        self._get_photometry_light_sources_config()
        self._get_photometry_detectors()
        self._get_fiber_connections()
        self.ophys_streams.append(
            Stream(
                stream_modalities=[Modality.FIB],
                stream_start_time=datetime.strptime(
                    self.Obj["fiber_photometry_start_time"],
                    "%Y-%m-%d %H:%M:%S.%f",
                ),
                stream_end_time=datetime.strptime(
                    self.Obj["fiber_photometry_end_time"],
                    "%Y-%m-%d %H:%M:%S.%f",
                ),
                daq_names=self.name_mapper["fiber_photometry_daq_names"],
                light_sources=self.fib_light_sources_config,
                detectors=self.fib_detectors,
                fiber_connections=self.fiber_connections,
                software=self.behavior_software,
                notes=f"Fib modality: fib mode: {self.Obj['fiber_mode']}",
            )
        )

    def _get_fiber_connections(self):
        """
        get the fiber connections
        """
        # hard coded for now
        self.fiber_connections = [
            FiberConnectionConfig(
                patch_cord_name="Patch Cord A",
                patch_cord_output_power=20,
                output_power_unit="microwatt",
                fiber_name="Fiber 0",
            )
        ]
        self.fiber_connections.append(
            FiberConnectionConfig(
                patch_cord_name="Patch Cord B",
                patch_cord_output_power=20,
                output_power_unit="microwatt",
                fiber_name="Fiber 1",
            )
        )
        self.fiber_connections.append(
            FiberConnectionConfig(
                patch_cord_name="Patch Cord C",
                patch_cord_output_power=20,
                output_power_unit="microwatt",
                fiber_name="Fiber 2",
            )
        )
        self.fiber_connections.append(
            FiberConnectionConfig(
                patch_cord_name="Patch Cord D",
                patch_cord_output_power=20,
                output_power_unit="microwatt",
                fiber_name="Fiber 3",
            )
        )
        return

        # this is not complete.
        self.fiber_connections = []
        for patch_cord in self.Obj["meta_data_dialog"]["rig_metadata"][
            "patch_cords"
        ]:
            self.fiber_connections.append(
                FiberConnectionConfig(
                    patch_cord_name=patch_cord["name"],
                    patch_cord_output_power=0,
                    output_power_unit=PowerUnit.MW,
                    fiber_name="NA",
                )
            )

    def _get_photometry_detectors(self):
        """
        get the photometry detectors
        """
        self.fib_detectors = []
        exposure_time = datetime.strptime(
            self.Obj["fiber_photometry_end_time"], "%Y-%m-%d %H:%M:%S.%f"
        ) - datetime.strptime(
            self.Obj["fiber_photometry_start_time"], "%Y-%m-%d %H:%M:%S.%f"
        )
        exposure_time = float(exposure_time.total_seconds())

        for current_detector in self.Obj["meta_data_dialog"]["rig_metadata"][
            "detectors"
        ]:
            if current_detector["device_type"] == "Detector":
                self.fib_detectors.append(
                    DetectorConfig(
                        name=current_detector["name"],
                        exposure_time=exposure_time,
                        exposure_time_unit=TimeUnit.US,
                        trigger_type=TriggerType.EXTERNAL,
                    )
                )

    def _get_photometry_light_sources_config(self):
        """
        get the light sources config for fiber photometry
        """
        self.fib_light_sources_config = []
        for current_light_source in self.Obj["meta_data_dialog"][
            "rig_metadata"
        ]["light_sources"]:
            # caution: the light sources for the photometry are selected based on the device type, and excludes LED with camera included in the notes (LED for camera illumination). This may be wrong for some rigs.
            if current_light_source["device_type"] in [
                "LightEmittingDiode",
                "Light emitting diode",
            ]:
                if current_light_source["notes"] is not None:
                    if "camera" in current_light_source["notes"]:
                        continue
                self.fib_light_sources_config.append(
                    LightEmittingDiodeConfig(
                        name=current_light_source["name"],
                    )
                )

    def _get_stimulus(self):
        """
        make the stimulus metadata (e.g. audio and optogenetics)
        """
        self.stimulus = []
        self._get_behavior_stimulus()
        self._get_optogenetics_stimulus()
        self.stimulus = self.behavior_stimulus + self.optogenetics_stimulus

    def _get_behavior_stimulus(self):
        """
        Make the audio stimulus metadata
        """
        self.behavior_stimulus = []
        if self.has_behavior_data == False:
            logging.info("No behavior data stream detected!")
            return

        self.behavior_stimulus.append(
            StimulusEpoch(
                software=self.behavior_software,
                stimulus_device_names=self._get_speaker_names(),
                stimulus_name="The behavior auditory go cue",
                stimulus_modalities=[StimulusModality.AUDITORY],
                stimulus_start_time=self.behavior_streams[0].stream_start_time,
                stimulus_end_time=self.behavior_streams[0].stream_end_time,
                stimulus_parameters=[
                    AuditoryStimulation(
                        sitmulus_name="auditory go cue",
                        sample_frequency=96000,
                        frequency_unit=FrequencyUnit.HZ,
                        amplitude_modulation_frequency=7500,
                    )
                ],
                speaker_config=SpeakerConfig(
                    name="Stimulus Speaker",
                    volume=self.Obj["Other_go_cue_decibel"],
                    volume_unit=SoundIntensityUnit.DB,
                ),
                output_parameters=self._get_output_parameters(),
                reward_consumed_during_epoch=self.total_reward_consumed_in_session,
                reward_consumed_unit="microliter",
                trials_total=self.trials_total,
                trials_finished=self.trials_finished,
                trials_rewarded=self.trials_rewarded,
                notes=f"The duration of go cue is 100 ms. The frequency is 7500 Hz. Amplitude is {self.Obj['Other_go_cue_decibel']}dB. The total reward consumed in the session is {self.total_reward_consumed_in_session} microliters. The total reward including consumed in the session and supplementary water is {self.Obj['TotalWater']} milliliters.",
            )
        )

    def _get_speaker_names(self):
        """
        get the speaker names
        """
        speaker_names = []
        self.Obj["meta_data_dialog"]["rig_metadata"]
        for current_device in self.Obj["meta_data_dialog"]["rig_metadata"][
            "stimulus_devices"
        ]:
            if current_device["device_type"] == "Speaker":
                speaker_names.append(current_device["name"])
        return speaker_names

    def _get_output_parameters(self):
        """Get the output parameters"""

        # Handle water info (with better names)
        BS_TotalReward = _get_field(self.Obj, "BS_TotalReward")
        # Turn uL to mL if the value is too large
        water_in_session_foraging = (
            BS_TotalReward / 1000 if BS_TotalReward > 5.0 else BS_TotalReward
        )
        # Old name "ExtraWater" goes first because old json has a wrong Suggested Water
        water_after_session = float(
            _get_field(
                self.Obj,
                field_list=["ExtraWater", "SuggestedWater"],
                default=np.nan,
            )
        )
        water_day_total = float(_get_field(self.Obj, "TotalWater"))
        water_in_session_total = water_day_total - water_after_session
        water_in_session_manual = (
            water_in_session_total - water_in_session_foraging
        )

        output_parameters = {
            "meta": {
                "box": _get_field(self.Obj, ["box", "Tower"]),
                "session_run_time_in_min": _get_field(
                    self.Obj, "Other_RunningTime"
                ),
            },
            "water": {
                "water_in_session_foraging": water_in_session_foraging,
                "water_in_session_manual": water_in_session_manual,
                "water_in_session_total": water_in_session_total,
                "water_after_session": water_after_session,
                "water_day_total": water_day_total,
            },
            "performance": {
                "foraging_efficiency": _get_field(
                    self.Obj, "B_for_eff_optimal"
                ),
                "foraging_efficiency_with_actual_random_seed": _get_field(
                    self.Obj, "B_for_eff_optimal_random_seed"
                ),
            },
            "task_parameters": self._get_task_parameters(),
        }

        return output_parameters

    def _get_task_parameters(self):
        """Get task parameters"""
        # excluding parameters starting with B_, TP_,  BS_, meta_data_dialog, LaserCalibrationResults, WaterCalibrationResults
        # task_parameters = {key: value for key, value in self.Obj.items() if not key.startswith(('B_', 'TP_', 'BS_','meta_data_dialog','LaserCalibrationResults','WaterCalibrationResults'))}
        # only keep key task parameters
        keys = [
            "Task",
            "BlockBeta",
            "BlockMin",
            "BlockMax",
            "ITIBeta",
            "ITIMin",
            "ITIMax",
            "DelayBeta",
            "DelayMin",
            "DelayMax",
            "LeftValue_volume",
            "RightValue_volume",
            "stage_in_use",
            "curriculum_in_use"

        ]
        reward_probability = self._get_reward_probability()
        task_parameters = {
            key: value for key, value in self.Obj.items() if key in keys
        }
        task_parameters["reward_probability"] = reward_probability

        return task_parameters

    def _get_reward_probability(self):
        """
        Get the reward probability
        """
        if self.Obj["Task"] in [
            "Uncoupled Baiting",
            "Uncoupled Without Baiting",
        ]:
            # Get reward prob pool from the input string (e.g., ["0.1", "0.5", "0.9"])
            return self.Obj["UncoupledReward"]
        elif self.Obj["Task"] in [
            "Coupled Baiting",
            "Coupled Without Baiting",
            "RewardN",
        ]:
            RewardPairs = self.Obj["B_RewardFamilies"][
                int(self.Obj["RewardFamily"]) - 1
            ][: int(self.Obj["RewardPairsN"])]
            RewardProb = (
                np.array(RewardPairs)
                / np.expand_dims(np.sum(RewardPairs, axis=1), axis=1)
                * float(self.Obj["BaseRewardSum"])
            )
            return str(RewardProb.tolist())
        else:
            logging.info("Task is not recognized!")
            return ""

    def _get_optogenetics_stimulus(self):
        """
        Make the optogenetics stimulus metadata
        """
        self.optogenetics_stimulus = []
        if "B_SelectedCondition" not in self.Obj:
            logging.info(
                "B_SelectedCondition is not included in the self.Obj!"
            )
            return
        a = np.array(self.Obj["B_SelectedCondition"])
        self.Obj["B_SelectedCondition"] = a.astype(int)
        if sum(self.Obj["B_SelectedCondition"]) == 0:
            return
        self._get_light_source_config()
        self.optogenetics_stimulus.append(
            StimulusEpoch(
                software=self.behavior_software,
                stimulus_device_names=self.light_names_used_in_session,
                stimulus_name="Optogenetics",
                stimulus_modalities=[StimulusModality.OPTOGENETICS],
                notes="Please see NWB files for more details (stimulus epoch and stimulus protocol etc.).",
                stimulus_start_time=self.session_start_time,
                stimulus_end_time=self.session_end_time,
                light_source_config=self.light_source_config,
            )
        )

    def _get_light_source_config(self):
        """
        get the optogenetics stimulus light source config
        """
        self.light_source_config = []
        self._get_light_names_used_in_session()
        if self.box_type == "Ephys":
            for light_source in self.light_names_used_in_session:
                wavelength = self._get_light_pars(light_source)
                self.light_source_config.append(
                    LaserConfig(
                        name=light_source,
                        wavelength=wavelength,
                    )
                )
        elif self.box_type == "Behavior":
            for light_source in self.light_names_used_in_session:
                self.light_source_config.append(
                    LightEmittingDiodeConfig(
                        name=light_source,
                    )
                )

    def _get_light_pars(self, light_source):
        """
        Get the wavelength and wavelength unit for the light source
        """
        for current_stimulus_device in self.Obj["meta_data_dialog"][
            "rig_metadata"
        ]["light_sources"]:
            if current_stimulus_device["name"] == light_source:
                return current_stimulus_device["wavelength"]

    def _get_light_names_used_in_session(self):
        """
        Get the optogenetics laser names used in the session
        """
        self.light_names_used_in_session = []
        light_sources = []
        index = np.where(np.array(self.Obj["B_SelectedCondition"]) == 1)[0]
        for i in index:
            current_condition = self.Obj["B_SelectedCondition"][i]
            if f"TP_LaserColor_{current_condition}" not in self.Obj:
                # old format
                current_color = self.Obj[f"TP_Laser_{current_condition}"][i]
            else:
                # new format
                current_color = self.Obj[f"TP_LaserColor_{current_condition}"][
                    i
                ]
            current_location = self.Obj[f"TP_Location_{current_condition}"][i]
            if current_location == "Both":
                light_sources.append({"color": current_color, "laser_tag": 1})
                light_sources.append({"color": current_color, "laser_tag": 2})
            elif current_location == "Left":
                light_sources.append({"color": current_color, "laser_tag": 1})
            elif current_location == "Right":
                light_sources.append({"color": current_color, "laser_tag": 2})

        if self.box_type == "Ephys":
            for light_source in light_sources:
                self.light_names_used_in_session.append(
                    [
                        key
                        for key, value in self.name_mapper[
                            "laser_name_mapper"
                        ].items()
                        if value == light_source
                    ][0]
                )
        elif self.box_type == "Behavior":
            for light_source in light_sources:
                self.light_names_used_in_session.append(
                    [
                        key
                        for key, value in self.name_mapper[
                            "led_name_mapper"
                        ].items()
                        if value == light_source
                    ][0]
                )

        self.light_names_used_in_session = list(
            set(self.light_names_used_in_session)
        )

    def _get_ephys_stream(self):
        """
        Make the ephys stream metadata
        """

        if self.Obj["open_ephys"] == []:
            self.ephys_streams = []
            logging.info("No ephys data stream detected!")
            return

        # find daq names for Neuropixels
        daq_names = self.name_mapper["ephys_daq_names"]

        self.ephys_streams = []
        self._get_ephys_modules()
        if self.ephys_modules == []:
            logging.info("Ephys modules are empty!")
            return
        self._get_stick_microscope()
        for current_recording in self.Obj["open_ephys"]:
            if (
                "openephys_start_recording_time"
                not in current_recording.keys()
            ):
                start_time = self.Obj["Other_SessionStartTime"]
                end_time = self.Obj["Other_CurrentTime"]
            else:
                start_time = current_recording[
                    "openephys_start_recording_time"
                ]
                end_time = current_recording["openephys_stop_recording_time"]
            self.ephys_streams.append(
                Stream(
                    stream_modalities=[Modality.ECEPHYS],
                    stream_start_time=datetime.strptime(
                        start_time, "%Y-%m-%d %H:%M:%S.%f"
                    ),
                    stream_end_time=datetime.strptime(
                        end_time, "%Y-%m-%d %H:%M:%S.%f"
                    ),
                    daq_names=daq_names,
                    ephys_modules=self.ephys_modules,
                    stick_microscopes=self.stick_microscopes,
                    notes=f"Ephys modality: recording type: {current_recording['recording_type']}; file name:{current_recording['prepend_text']}{current_recording['base_text']};  experiment number:{current_recording['record_nodes'][0]['experiment_number']};  recording number:{current_recording['record_nodes'][0]['recording_number']}",
                )
            )

    def _get_stick_microscope(self):
        """
        Make the stick microscope metadata
        """
        self.stick_microscopes = []
        self._find_stick_microscope_names()
        for stick_microscope in self.stick_microscope_names:
            self.stick_microscopes.append(
                DomeModule(
                    assembly_name=stick_microscope,
                    rotation_angle=self.Obj["meta_data_dialog"][
                        "session_metadata"
                    ]["microscopes"][stick_microscope]["Stick_RotationAngle"],
                    arc_angle=self.Obj["meta_data_dialog"]["session_metadata"][
                        "microscopes"
                    ][stick_microscope]["Stick_ArcAngle"],
                    module_angle=self.Obj["meta_data_dialog"][
                        "session_metadata"
                    ]["microscopes"][stick_microscope]["Stick_ModuleAngle"],
                    notes="Did not calibrate.",
                )
            )

    def _get_ephys_modules(self):
        """
        Make the ephys module metadata
        """
        self._get_probe_names()
        self.ephys_modules = []
        self.stmulus_device_names = []
        for ind_probe, probe in enumerate(self.probe_names):
            if (
                probe
                in self.Obj["meta_data_dialog"]["session_metadata"]["probes"]
            ):
                self.ephys_modules.append(
                    ManipulatorModule(
                        rotation_angle=self.Obj["meta_data_dialog"][
                            "session_metadata"
                        ]["probes"][probe]["RotationAngle"],
                        arc_angle=self.Obj["meta_data_dialog"][
                            "session_metadata"
                        ]["probes"][probe]["ArcAngle"],
                        module_angle=self.Obj["meta_data_dialog"][
                            "session_metadata"
                        ]["probes"][probe]["ModuleAngle"],
                        assembly_name=self._find_assembly_names(probe),
                        primary_targeted_structure=self.Obj[
                            "meta_data_dialog"
                        ]["session_metadata"]["probes"][probe]["ProbeTarget"],
                        manipulator_coordinates=Coordinates3d(
                            x=self.Obj["meta_data_dialog"]["session_metadata"][
                                "probes"
                            ][probe]["ManipulatorX"],
                            y=self.Obj["meta_data_dialog"]["session_metadata"][
                                "probes"
                            ][probe]["ManipulatorY"],
                            z=self.Obj["meta_data_dialog"]["session_metadata"][
                                "probes"
                            ][probe]["ManipulatorZ"],
                            unit=SizeUnit.UM,
                        ),
                    )
                )
                self.stmulus_device_names.extend(self._find_laser_names(probe))

    def _find_stick_microscope_names(self):
        """
        Find the stick microscope names
        """
        self.stick_microscope_names = []
        for stick_microscope in self.Obj["meta_data_dialog"]["rig_metadata"][
            "stick_microscopes"
        ]:
            self.stick_microscope_names.append(stick_microscope["name"])

    def _find_laser_names(self, probe_name):
        """
        Find the laser name for the probe
        """
        for assembly in self.Obj["meta_data_dialog"]["rig_metadata"][
            "ephys_assemblies"
        ]:
            for probe in assembly["probes"]:
                if probe["name"] == probe_name:
                    return probe["lasers"]
        logging.info("No lasers found!")
        return None

    def _find_assembly_names(self, probe_name):
        """
        Find the assembly name for the probe
        """
        for assembly in self.Obj["meta_data_dialog"]["rig_metadata"][
            "ephys_assemblies"
        ]:
            if probe_name in [probe["name"] for probe in assembly["probes"]]:
                return assembly["name"]
        logging.info("No ephys assembly found!")
        return None

    def _get_probe_names(self):
        """
        Get the probe names from the rig metadata
        """
        self.probe_names = []
        for assembly in self.Obj["meta_data_dialog"]["rig_metadata"][
            "ephys_assemblies"
        ]:
            for probe in assembly["probes"]:
                self.probe_names.append(probe["name"])

    def _get_behavior_stream(self):
        """
        Make the behavior stream metadata
        """

        if self.has_behavior_data == False:
            self.behavior_streams = []
            logging.info("No behavior data detected!")
            return

        if self.Obj["settings_box"]["AINDLickDetector"] == 1:
            daq_names = self.name_mapper["rig_daq_names_aind_lick_detector"]
        else:
            daq_names = self.name_mapper["rig_daq_names_janelia_lick_detector"]

        self.behavior_streams = []
        self.behavior_streams.append(
            Stream(
                stream_modalities=[Modality.BEHAVIOR],
                stream_start_time=datetime.strptime(
                    self.Obj["Other_SessionStartTime"], "%Y-%m-%d %H:%M:%S.%f"
                ),
                stream_end_time=datetime.strptime(
                    self.Obj["Other_CurrentTime"], "%Y-%m-%d %H:%M:%S.%f"
                ),
                daq_names=daq_names,
                software=self.behavior_software,
            )
        )

    def _get_behavior_software(self):
        """
        get the behavior software version information
        """
        self.behavior_software = []
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            os.chdir(script_dir)  # Change to the directory of the current script
            # Get information about task repository
            commit_ID = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()
            current_branch = subprocess.check_output(['git','branch','--show-current']).decode('ascii').strip()
            version=foraging_gui.__version__
        except Exception as e:
            logging.error(
                "Could not get git branch and hash during generating session metadata: {}".format(
                    str(e)
                )
            )
            commit_ID = None
            current_branch = None
            version = None
        self.behavior_software.append(
            Software(
                name="dynamic-foraging-task",
                version=f"behavior branch:{self.Obj['current_branch']}   commit ID:{self.Obj['commit_ID']}    version:{self.Obj['version']}; metadata branch: {current_branch}   commit ID:{commit_ID}   version:{version}",
                url=self.Obj["repo_url"],
            )
        )

    def _get_opto_calibration(self):
        """
        Make the optogenetic (Laser or LED) calibration metadata
        """
        if self.Obj["LaserCalibrationResults"] == {}:
            self.opto_calibration = []
            logging.info("No opto calibration results detected!")
            return
        self._parse_opto_calibration()
        self.opto_calibration = []
        for current_calibration in self.parsed_optocalibration:
            description = f"Optogenetic calibration for {current_calibration['laser name']} {current_calibration['Color']} Laser_{current_calibration['Laser tag']}. Protocol: {current_calibration['Protocol']}. Frequency: {current_calibration['Frequency']}."
            self.opto_calibration.append(
                Calibration(
                    calibration_date=datetime.strptime(
                        current_calibration["latest_calibration_date"],
                        "%Y-%m-%d",
                    ).date(),
                    device_name=current_calibration["laser name"],
                    description=description,
                    input={
                        "input voltage (v)": current_calibration["Voltage"]
                    },
                    output={"laser power (mw)": current_calibration["Power"]},
                )
            )

    def _parse_opto_calibration(self):
        """
        Parse the optogenetic calibration information from the behavior json file
        """
        self.parsed_optocalibration = []
        self.OptoCalibrationResults = self.Obj["LaserCalibrationResults"]
        self._get_laser_names_from_rig_metadata()
        for laser in self.laser_names:
            if laser not in self.name_mapper["laser_name_mapper"]:
                continue
            color = self.name_mapper["laser_name_mapper"][laser]["color"]
            laser_tag = self.name_mapper["laser_name_mapper"][laser][
                "laser_tag"
            ]
            latest_calibration_date = self._FindLatestCalibrationDate(color)
            if latest_calibration_date == "NA":
                RecentLaserCalibration = {}
            else:
                RecentLaserCalibration = self.Obj["LaserCalibrationResults"][
                    latest_calibration_date
                ]
            if not RecentLaserCalibration == {}:
                if color in RecentLaserCalibration.keys():
                    for Protocol in RecentLaserCalibration[color]:
                        if Protocol == "Sine":
                            for Frequency in RecentLaserCalibration[color][
                                Protocol
                            ]:
                                voltage = []
                                power = []
                                if (
                                    f"Laser_{laser_tag}"
                                    in RecentLaserCalibration[color][Protocol][
                                        Frequency
                                    ]
                                ):
                                    current_calibration = (
                                        RecentLaserCalibration[color][
                                            Protocol
                                        ][Frequency][f"Laser_{laser_tag}"][
                                            "LaserPowerVoltage"
                                        ]
                                    )
                                else:
                                    if laser_tag == 1:
                                        current_calibration = (
                                            RecentLaserCalibration[color][
                                                Protocol
                                            ][Frequency]["Left"][
                                                "LaserPowerVoltage"
                                            ]
                                        )
                                    elif laser_tag == 2:
                                        current_calibration = (
                                            RecentLaserCalibration[color][
                                                Protocol
                                            ][Frequency]["Right"][
                                                "LaserPowerVoltage"
                                            ]
                                        )
                                if current_calibration == []:
                                    continue
                                for i in range(len(current_calibration)):
                                    laser_voltage_power = eval(
                                        str(current_calibration[i])
                                    )
                                    voltage.append(laser_voltage_power[0])
                                    power.append(laser_voltage_power[1])
                                voltage, power = zip(
                                    *sorted(
                                        zip(voltage, power), key=lambda x: x[0]
                                    )
                                )
                                self.parsed_optocalibration.append(
                                    {
                                        "laser name": laser,
                                        "latest_calibration_date": latest_calibration_date,
                                        "Color": color,
                                        "Protocol": Protocol,
                                        "Frequency": Frequency,
                                        "Laser tag": laser_tag,
                                        "Voltage": voltage,
                                        "Power": power,
                                    }
                                )
                        elif Protocol == "Constant":
                            voltage = []
                            power = []
                            if (
                                f"Laser_{laser_tag}"
                                in RecentLaserCalibration[color][Protocol]
                            ):
                                current_calibration = RecentLaserCalibration[
                                    color
                                ][Protocol][f"Laser_{laser_tag}"][
                                    "LaserPowerVoltage"
                                ]
                            else:
                                if laser_tag == 1:
                                    current_calibration = (
                                        RecentLaserCalibration[color][
                                            Protocol
                                        ]["Left"]["LaserPowerVoltage"]
                                    )
                                elif laser_tag == 2:
                                    current_calibration = (
                                        RecentLaserCalibration[color][
                                            Protocol
                                        ]["Right"]["LaserPowerVoltage"]
                                    )
                            if current_calibration == []:
                                continue
                            for i in range(len(current_calibration)):
                                laser_voltage_power = eval(
                                    str(current_calibration[i])
                                )
                                voltage.append(laser_voltage_power[0])
                                power.append(laser_voltage_power[1])
                            voltage, power = zip(
                                *sorted(
                                    zip(voltage, power), key=lambda x: x[0]
                                )
                            )
                            self.parsed_optocalibration.append(
                                {
                                    "laser name": laser,
                                    "latest_calibration_date": latest_calibration_date,
                                    "Color": color,
                                    "Protocol": Protocol,
                                    "Frequency": "None",
                                    "Laser tag": laser_tag,
                                    "Voltage": voltage,
                                    "Power": power,
                                }
                            )

    def _get_laser_names_from_rig_metadata(self, Obj=None):
        """
        Get the Laser/LED names from the rig metadata
        """
        self.laser_names = []
        if Obj is None:
            Obj = self.Obj
        for light_source in Obj["meta_data_dialog"]["rig_metadata"][
            "light_sources"
        ]:
            if light_source["device_type"] in ["Laser", "LightEmittingDiode"]:
                self.laser_names.append(light_source["name"])
        return self.laser_names

    def _FindLatestCalibrationDate(self, Laser):
        """find the latest calibration date for the selected laser"""
        if "LaserCalibrationResults" not in self.Obj:
            logging.info(
                "LaserCalibrationResults is not included in self.Obj."
            )
            return "NA"
        Dates = []
        for Date in self.Obj["LaserCalibrationResults"]:
            if Laser in self.Obj["LaserCalibrationResults"][Date].keys():
                Dates.append(Date)
        sorted_dates = sorted(Dates)
        if sorted_dates == []:
            logging.info("No dates found in the LaserCalibrationResults.")
            return "NA"
        else:
            return sorted_dates[-1]

    def _get_water_calibration(self):
        """
        Make water calibration metadata
        """
        self.water_calibration = []
        return

        # removing the water calibration as it is contained in the rig metadata
        if self.Obj["WaterCalibrationResults"] == {}:
            self.water_calibration = []
            return

        self.water_calibration = []
        self._parse_water_calibration()
        for side in self.parsed_watercalibration.keys():
            if side == "Left":
                device_name = "Left lick spout"
            elif side == "Right":
                device_name = "Right lick spout"
            description = f"Water calibration for {device_name}. The input is the valve open time in second and the output is the volume of water delivered in microliters."
            self.water_calibration.append(
                Calibration(
                    calibration_date=datetime.strptime(
                        self.RecentWaterCalibrationDate, "%Y-%m-%d"
                    ).date(),
                    device_name=device_name,
                    description=description,
                    input={
                        "valve open time (s)": self.parsed_watercalibration[
                            side
                        ]["X"]
                    },
                    output={
                        "water volume (ul)": self.parsed_watercalibration[
                            side
                        ]["Y"]
                    },
                )
            )

    def _parse_water_calibration(self):
        """
        Parse the water calibration information from the json file
        """
        self.WaterCalibrationResults = self.Obj["WaterCalibrationResults"]
        sorted_dates = sorted(
            self.WaterCalibrationResults.keys(), key=self._custom_sort_key
        )
        self.RecentWaterCalibration = self.WaterCalibrationResults[
            sorted_dates[-1]
        ]
        self.RecentWaterCalibrationDate = sorted_dates[-1]

        sides = self.name_mapper["sides"]
        self.parsed_watercalibration = {}
        for side in sides:
            self.parsed_watercalibration[side] = {}
            sorted_X, sorted_Y = PlotWaterCalibration._GetWaterCalibration(
                self,
                self.WaterCalibrationResults,
                self.RecentWaterCalibrationDate,
                side,
            )
            self.parsed_watercalibration[side]["X"] = sorted_X
            self.parsed_watercalibration[side]["Y"] = sorted_Y

    def _custom_sort_key(self, key):
        if "_" in key:
            date_part, number_part = key.rsplit("_", 1)
            return (date_part, int(number_part))
        else:
            return (key, 0)

    def _get_reward_delivery(self):
        """
        Make the RewardDelivery metadata
        """
        if not self.has_reward_delivery:
            self.reward_delivery = []
            logging.info("No reward delivery metadata found!")
            return

        device_oringin = self.Obj["meta_data_dialog"]["session_metadata"][
            "LickSpoutReferenceArea"
        ]
        lick_spouts_distance = float(self.Obj["Other_lick_spout_distance"])
        # using the last position of the stage
        if "B_StagePositions" in self.Obj.keys():
            start_position = [
                self.Obj["B_StagePositions"][-1]["x"],
                self.Obj["B_StagePositions"][-1].get(
                    "y", None
                ),  # newscale stage
                self.Obj["B_StagePositions"][-1].get("y1", None),  # aind-stage
                self.Obj["B_StagePositions"][-1].get("y2", None),  # aind-stage
                self.Obj["B_StagePositions"][-1]["z"],
            ]
            start_position = [
                pos for pos in start_position if pos is not None
            ]  # filter out None values

            reference_spout_position = [
                float(
                    self.Obj["meta_data_dialog"]["session_metadata"][
                        "LickSpoutReferenceX"
                    ]
                ),
                float(
                    self.Obj["meta_data_dialog"]["session_metadata"].get(
                        "LickSpoutReferenceY", None
                    )
                ),
                float(
                    self.Obj["meta_data_dialog"]["session_metadata"].get(
                        "LickSpoutReferenceY1", None
                    )
                ),
                float(
                    self.Obj["meta_data_dialog"]["session_metadata"].get(
                        "LickSpoutReferenceY2", None
                    )
                ),
                float(
                    self.Obj["meta_data_dialog"]["session_metadata"][
                        "LickSpoutReferenceZ"
                    ]
                ),
            ]
            reference_spout_position = [
                pos for pos in reference_spout_position if pos is not None
            ]  # filter out None value

        elif "B_NewscalePositions" in self.Obj.keys():  # older version of code
            start_position = [
                self.Obj["B_NewscalePositions"][-1][0],
                self.Obj["B_NewscalePositions"][-1][1],
                self.Obj["B_NewscalePositions"][-1][2],
            ]
            # assuming refering to the left lick spout
            reference_spout_position = [
                float(
                    self.Obj["meta_data_dialog"]["session_metadata"][
                        "LickSpoutReferenceX"
                    ]
                ),
                float(
                    self.Obj["meta_data_dialog"]["session_metadata"][
                        "LickSpoutReferenceY"
                    ]
                ),
                float(
                    self.Obj["meta_data_dialog"]["session_metadata"][
                        "LickSpoutReferenceZ"
                    ]
                ),
            ]
        else:
            logging.error(
                "Object does not have stage positions to create metadata."
            )
            return

        if len(reference_spout_position) == 3:  # newscale stage
            left_lick_spout_reference_position = np.array(
                reference_spout_position
            ) - np.array(start_position)
            right_lick_spout_reference_position = (
                left_lick_spout_reference_position
                + np.array([-lick_spouts_distance, 0, 0])
            )
        else:  # aind stage
            left_lick_spout_reference_position = [
                reference_spout_position[i] - start_position[i]
                for i in [0, 1, 3]
            ]
            right_lick_spout_reference_position = [
                reference_spout_position[i] - start_position[i]
                for i in [0, 2, 3]
            ]

        self.reward_delivery = RewardDeliveryConfig(
            reward_solution=RewardSolution.WATER,
            reward_spouts=[
                RewardSpoutConfig(
                    side=SpoutSide.LEFT,
                    starting_position=RelativePosition(
                        device_position_transformations=[
                            Translation3dTransform(
                                translation=left_lick_spout_reference_position.tolist()
                            ),
                            Rotation3dTransform(
                                rotation=[1, 0, 0, 0, 1, 0, 0, 0, 1]
                            ),
                        ],
                        device_origin=device_oringin,
                        device_axes=[
                            Axis(name=AxisName.X, direction="Left"),
                            Axis(name=AxisName.Y, direction="Forward"),
                            Axis(name=AxisName.Z, direction="Down"),
                        ],
                        notes="X positive is left, Y positive is forward, and Z positive is down.",
                    ),
                    variable_position=True,
                ),
                RewardSpoutConfig(
                    side=SpoutSide.RIGHT,
                    starting_position=RelativePosition(
                        device_position_transformations=[
                            Translation3dTransform(
                                translation=right_lick_spout_reference_position.tolist()
                            ),
                            Rotation3dTransform(
                                rotation=[1, 0, 0, 0, 1, 0, 0, 0, 1]
                            ),
                        ],
                        device_origin=device_oringin,
                        device_axes=[
                            Axis(name=AxisName.X, direction="Left"),
                            Axis(name=AxisName.Y, direction="Forward"),
                            Axis(name=AxisName.Z, direction="Down"),
                        ],
                        notes="X positive is left, Y positive is forward, and Z positive is down.",
                    ),
                    variable_position=True,
                ),
            ],
            notes="Lick spout positions and reward size can be varied and the data is saved in the NWB file",
        )


if __name__ == "__main__":
    generate_metadata(
        json_file=r"Y:\753126\behavior_753126_2024-10-07_10-14-07\behavior\753126_2024-10-07_10-14-07.json",
        output_folder=r"H:\test",
    )
    # generate_metadata(json_file=r'Y:\753126\behavior_753126_2024-10-15_12-20-35\behavior\753126_2024-10-15_12-20-35.json',output_folder=r'H:\test')
    # generate_metadata(json_file=r'F:\Test\Metadata\715083_2024-04-22_14-32-07.json', dialog_metadata_file=r'C:\Users\xinxin.yin\Documents\ForagingSettings\metadata_dialog\323_EPHYS3_2024-05-09_12-42-30_metadata_dialog.json', output_folder=r'F:\Test\Metadata')
