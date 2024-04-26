import json
import logging

from aind_data_schema.core.session import (
    CcfCoords,
    Coordinates3d,
    DomeModule,
    EphysModule,
    EphysProbeConfig,
    Session,
    Stream,
)

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

    Output:
    session metadata: json file
        json file to the metadata folder
    rig metadata: json file
        json file to the metadata folder

    '''
    def __init__(self, json_file=None, Obj=None, dialog_metadata_file=None,dialog_metadata=None, output_folder=None):
        if json_file is None and Obj is None and dialog_metadata is None:
            logging.info("json file or Obj is not provided")
            return
        
        if json_file is not None:
            with open(json_file) as f:
                self.Obj = json.load(f)
        else:
            self.Obj = Obj

        if dialog_metadata_file is not None:
            with open(dialog_metadata_file) as f:
                self.Obj['meta_data_dialog'] = json.load(f)
        elif dialog_metadata is not None:
            self.Obj['meta_data_dialog'] = dialog_metadata
        
        if output_folder is not None:
            self.Obj['MetadataFolder'] = output_folder

        self.Obj['session_metadata']= {}
        self.ephys_metadata()
        self.behavior_metadata()
        self.ophys_metadata()
        self.high_speed_camera_metadata()
        self._session()
    
    def _session(self):
        '''
        Create metadata related to Session class in the aind_data_schema
        '''
        session = Session(
            experimenter_full_name = [self.Obj['Experimenter']],
            subject_id=self.Obj['ID'],
            session_start_time=self.Obj['Other_SessionStartTime'],
            session_end_time=self.Obj['Other_CurrentTime'],
            session_type=self.Obj['Task'],
            iacuc_protocol=self.Obj['meta_data_dialog']['session_metadata']['IACUCProtocol'],
            rig_id=self.Obj['meta_data_dialog']['rig_metadata']['rig_id'],
            notes=self.Obj['ShowNotes'],
            animal_weight_post=float(self.Obj['WeightAfter']),
            weight_unit="gram",
            stimulus_epochs=[],
            reward_consumed_total=float(self.Obj['TotalWater']),
            reward_consumed_unit= "microliter",
            data_streams=[],
        )

        session.write_standard_file(output_directory=self.Obj['MetadataFolder'])

    def ephys_metadata(self):
        pass
    
    def behavior_metadata(self):
        pass

    def ophys_metadata(self):
        pass

    def high_speed_camera_metadata(self):
        pass

if __name__ == '__main__':
    generate_metadata(json_file=r'Y:\715083\behavior_715083_2024-04-22_14-32-07\behavior\715083_2024-04-22_14-32-07.json', dialog_metadata_file=r'C:\Users\xinxin.yin\Documents\ForagingSettings\metadata_dialog\323_EPHYS3_2024-04-25_22-24-01_metadata_dialog.json', output_folder=r'F:\Test\Metadata')