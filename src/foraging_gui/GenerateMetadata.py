import json
import logging


class generate_metadata:
    '''
    Parse the behavior json file and generate session and rig metadata

    Parameters:
    json_file: str
        path to the json file
    Obj: dict
        dictionary containing the json file
    dialog_metadata: dict
        dictionary containing the dialog metadata. If provided, it will override the meta_data_dialog key in the json file
    output_folder: str
        path to the output folder where the metadata will be saved. If not provided, the metadata will be saved in the . 

    Returns:
    session_metadata: dict
        dictionary containing the session metadata
    rig_metadata: dict
        dictionary containing the rig metadata

    Output:
    session metadata: json file
        json file to the metadata folder
    rig metadata: json file
        json file to the metadata folder

    '''
    def __init__(self,json_file=None,Obj=None,dialog_metadata=None,output_folder=None):
        if (json_file is None) and (Obj is None) and (dialog_metadata is None):
            logging.info("json file or Obj is not provided")
            return
        pass

    def ephys_metadata(self):
        pass
    
    def behavior_metadata(self):
        pass

    def ophys_metadata(self):
        pass

    def high_speed_camera_metadata(self):
        pass

    def combined_metadata(self):
        pass

generate_metadata(json_file=f"metadata.json")