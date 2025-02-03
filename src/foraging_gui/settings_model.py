from pydantic import BaseModel
from pydantic import Field
from typing import Literal, Optional

class BonsaiSettingsModel(BaseModel):
    '''
        Defines a model for the Settings_box.csv file
    '''
    Behavior: str = Field(pattern=r"^COM[0-9]+$")
    Soundcard: str = Field(pattern=r"^COM[0-9]+$")
    BonsaiOsc1: str = Field(pattern=r"^40[0-9][0-9]$")
    BonsaiOsc2: str = Field(pattern=r"^40[0-9][0-9]$")
    BonsaiOsc3: str = Field(pattern=r"^40[0-9][0-9]$")
    BonsaiOsc4: str = Field(pattern=r"^40[0-9][0-9]$")
    AttenuationLeft: int
    AttenuationRight: int
    current_box: str = Field(pattern=r"^[0-9][0-9][0-9]-[0-9]+-[ABCD]$")
    RunningWheel: Literal["0","1"]
    AINDLickDetector: Literal["0","1"]
    LeftLickDetector: Optional[str] = Field(default="COM0",pattern=r"^COM[0-9]+$")
    RightLickDetector: Optional[str] = Field(default="COM0",pattern=r"^COM[0-9]+$")
    HighSpeedCamera: Literal["0","1"] 
    HasSideCameraLeft: Literal["0","1"] = Field(default=0)
    HasSideCameraRight: Literal["0","1"] = Field(default=0)
    HasBottomCamera: Literal["0","1"] = Field(default=0)
    HasBodyCamera: Literal["0","1"] = Field(default=0)
    SideCameraLeft: int = Field(default=0)
    SideCameraRight: int= Field(default=0)
    BottomCamera: int= Field(default=0)
    BodyCamera: int= Field(default=0)
    codec: Optional[str] = Field(default='')
    HasOpto: Literal["0","1"] = Field(default=0)
    # TODO OptoLaser<x>Manufacturer 
    # TODO OptoLaser<x>Wavelength
    # TODO OptoLaser<x>Model
    # TODO OptoLaser<x>SerialNumber
    FipObjectiveCMOSSerialNumber: Optional[str] = Field(default=0)  

class DFTSettingsModel(BaseModel):
    '''
        Defines a model for the ForagingSettings.json file
    '''
    default_saveFolder: str
    current_box:str
    temporary_video_folder:str
    Teensy_COM_box1:str
    Teensy_COM_box2:str
    Teensy_COM_box3:str
    Teensy_COM_box4:str
    FIP_workflow_path:str
    FIP_settings:str
    bonsai_path:str
    bonsai_config_path:str
    bonsaiworkflow_path:str
    newscale_serial_num_box1:str
    newscale_serial_num_box2:str
    newscale_serial_num_box3:str
    newscale_serial_num_box4:str
    show_log_info_in_console:bool
    default_ui:str
    open_ephys_machine_ip_address:str
    metadata_dialog_folder:str
    rig_metadata_folder:str
    project_info_file:str
    schedule_path: str
    go_cue_decibel_box1:float
    go_cue_decibel_box2:float
    go_cue_decibel_box3:float
    go_cue_decibel_box4:float
    lick_spout_distance_box1:float
    lick_spout_distance_box2:float
    lick_spout_distance_box3:float
    lick_spout_distance_box4:float
    name_mapper_file:str
    create_rig_metadata:bool
    save_each_trial:bool
    AutomaticUpload:bool
    manifest_flag_dir:str
    auto_engage:bool
    clear_figure_after_save:bool
    add_default_project_name:bool
