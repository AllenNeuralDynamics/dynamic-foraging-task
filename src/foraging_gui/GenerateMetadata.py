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
        path to the output folder where the metadata will be saved. If not provided, the metadata will be saved in the MetadataFolder extracted from the behavior json file/object. 

    Returns:
    Obj: dict
        dictionary containing the original dictionary and the updated dictionary with complete metadata
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
    def __init__(self, json_file=None, Obj=None, dialog_metadata=None, output_folder=None):
        if json_file is None and Obj is None and dialog_metadata is None:
            logging.info("json file or Obj is not provided")
            return
        
        if json_file is not None:
            with open(json_file) as f:
                self.Obj = json.load(f)
        else:
            self.Obj = Obj

        if dialog_metadata is not None:
            self.Obj['meta_data_dialog'] = dialog_metadata
        
        if output_folder is not None:
            self.Obj['MetadataFolder'] = output_folder

        self.Obj['metadata'] = {}
        self.Obj['metadata']['session_metadata'] = {}
        self.Obj['metadata']['rig_metadata'] = self.Obj['meta_data_dialog']['rig_metadata']
        self.ephys_metadata()
        self.behavior_metadata()
        self.ophys_metadata()
        self.high_speed_camera_metadata()
        return self.Obj, self.Obj['metadata']['session_metadata'], self.Obj['metadata']['rig_metadata']
    
    def ephys_metadata(self):
        pass
    
    def behavior_metadata(self):
        pass

    def ophys_metadata(self):
        pass

    def high_speed_camera_metadata(self):
        pass

