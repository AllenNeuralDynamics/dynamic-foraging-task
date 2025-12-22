from typing import Literal, Optional

from pydantic import BaseModel, Field


class BonsaiSettingsModel(BaseModel):
    """
    Defines a model for the Settings_box.csv file
    """

    Behavior: str = Field(
        pattern=r"^COM[0-9]+$", description="COM port for Harp Behavior Board"
    )
    Soundcard: str = Field(
        pattern=r"^COM[0-9]+$", description="COM port for Harp Behavior Board"
    )
    BonsaiOsc1: str = Field(
        pattern=r"^40[0-9][0-9]$",
        description="OSC channel for python/bonsai communication",
    )
    BonsaiOsc2: str = Field(
        pattern=r"^40[0-9][0-9]$",
        description="OSC channel for python/bonsai communication",
    )
    BonsaiOsc3: str = Field(
        pattern=r"^40[0-9][0-9]$",
        description="OSC channel for python/bonsai communication",
    )
    BonsaiOsc4: str = Field(
        pattern=r"^40[0-9][0-9]$",
        description="OSC channel for python/bonsai communication",
    )
    AttenuationLeft: int = Field(
        description="Calibration parameter for the left channel sound stimulus"
    )
    AttenuationRight: int = Field(
        description="Calibration parameter for the left channel sound stimulus"
    )
    current_box: str = Field(
        pattern=r"^[0-9][0-9][0-9](-[0-9]+-[ABCD]|_EPHYS[0-9]+|_Ephys[0-9]+)$",
        description="Box name in ROOM-TOWER-BOX format, or ROOM-EphysNUM",
    )
    RunningWheel: Literal["0", "1"] = Field(
        default="0", description="Using AIND running wheel"
    )
    AINDLickDetector: Literal["0", "1"] = Field(
        default="0", description="Using AIND Lick Detector"
    )
    LeftLickDetector: Optional[str] = Field(
        default="COM0",
        pattern=r"^COM[0-9]+$",
        description="COM port for AIND Lick Detector",
    )
    RightLickDetector: Optional[str] = Field(
        default="COM0",
        pattern=r"^COM[0-9]+$",
        description="COM port for AIND Lick Detector",
    )
    HighSpeedCamera: Literal["0", "1"] = Field(
        default=0, description="Using High Speed cameras"
    )
    HasSideCameraLeft: Literal["0", "1"] = Field(
        default=0,
        description="Using high speed camera on the left side of the mouse",
    )
    HasSideCameraRight: Literal["0", "1"] = Field(
        default=0,
        description="Using high speed camera on the right side of the mouse",
    )
    HasBottomCamera: Literal["0", "1"] = Field(
        default=0,
        description="Using high speed camera on the bottom the mouse",
    )
    HasBodyCamera: Literal["0", "1"] = Field(
        default=0,
        description="Using high speed camera on the body of the mouse",
    )
    SideCameraLeft: int = Field(
        default=0, description="Serial number for side camera left"
    )
    SideCameraRight: int = Field(
        default=0, description="Serial number for side camera right"
    )
    BottomCamera: int = Field(
        default=0, description="Serial number for bottom camera"
    )
    BodyCamera: int = Field(
        default=0, description="Serial number for body camera"
    )
    codec: Optional[str] = Field(default="", description="Video codec")
    HasOpto: Literal["0", "1"] = Field(
        default=0, description="Using Optogenetics"
    )
    
    # TODO: Add optogenetic parameters as needed
    # OptoLaser<x>Manufacturer
    # OptoLaser<x>Wavelength
    # OptoLaser<x>Model
    # OptoLaser<x>SerialNumber

    FipObjectiveCMOSSerialNumber: Optional[str] = Field(
        default=0, description="Serial number for FIP CMOS Objective"
    )

    # NEW FIELDS FOR CAMERA EXPOSURE & GAIN
    BottomCamera_ExposureTime: float = Field(
        default=1000,
        description="Exposure time for the bottom camera"
    )
    SideCameraLeft_ExposureTime: float = Field(
        default=1000,
        description="Exposure time for the left side camera"
    )
    SideCameraRight_ExposureTime: float = Field(
        default=1000,
        description="Exposure time for the right side camera"
    )
    BodyCamera_ExposureTime: float = Field(
        default=1000,
        description="Exposure time for the body camera"
    )
    BottomCamera_Gain: float = Field(
        default=8,
        description="Gain for the bottom camera"
    )
    SideCameraLeft_Gain: float = Field(
        default=8,
        description="Gain for the left side camera"
    )
    SideCameraRight_Gain: float = Field(
        default=8,
        description="Gain for the right side camera"
    )
    BodyCamera_Gain: float = Field(
        default=8,
        description="Gain for the body camera"
    )
    ffmpeg_output_args: str = Field()   # required field so no default
    ffmpeg_input_args: str = Field()    # required field so no default

class DFTSettingsModel(BaseModel):
    """
    Defines a model for the ForagingSettings.json file
    """

    # TODO, should check that the path fields are valid fields
    default_saveFolder: str
    current_box: str
    temporary_video_folder: str
    Teensy_COM_box1: str
    Teensy_COM_box2: str
    Teensy_COM_box3: str
    Teensy_COM_box4: str
    FIP_workflow_path: str
    FIP_settings: str
    bonsai_path: str
    bonsai_config_path: str
    bonsaiworkflow_path: str
    newscale_serial_num_box1: str
    newscale_serial_num_box2: str
    newscale_serial_num_box3: str
    newscale_serial_num_box4: str
    show_log_info_in_console: bool
    default_ui: str
    open_ephys_machine_ip_address: str
    metadata_dialog_folder: str
    rig_metadata_folder: str
    schedule_path: str
    go_cue_decibel_box1: float
    go_cue_decibel_box2: float
    go_cue_decibel_box3: float
    go_cue_decibel_box4: float
    lick_spout_distance_box1: float
    lick_spout_distance_box2: float
    lick_spout_distance_box3: float
    lick_spout_distance_box4: float
    name_mapper_file: str
    create_rig_metadata: bool
    save_each_trial: bool
    AutomaticUpload: bool
    manifest_flag_dir: str
    transfer_service_job_type: str
    auto_engage: bool
    clear_figure_after_save: bool
    add_default_project_name: bool
    check_schedule: bool
