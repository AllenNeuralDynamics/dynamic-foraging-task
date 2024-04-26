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
    RewardDeliveryConfig,
    RewardSpoutConfig,
    RewardSolution,
)

from aind_data_schema.models.devices import (
    
    RelativePosition, 
    SpoutSide,
    Calibration,

)

from aind_data_schema.models.units import (

    SizeUnit,

)

from foraging_gui.Visualization import PlotWaterCalibration


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

        self._get_RewardDelivery()
        self._get_WaterCalibration()
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
            reward_consumed_total=float(self.Obj['BS_TotalReward']),
            reward_consumed_unit= "microliter",
            reward_delivery=self.lick_spouts,
            data_streams=[],
        )

        session.write_standard_file(output_directory=self.Obj['MetadataFolder'])

    def _get_WaterCalibration(self):
        '''
        Make water calibration metadata
        '''
        self._parse_water_calibration()
        Calibration(

            calibration_date='',
            device_name='',
            description='' ,
            input= '',
            output='' ,
            notes='' ,
        )

    def _parse_water_calibration(self):
        '''
        Parse the water calibration information from the json file
        '''
        self.WaterCalibrationResults=self.Obj['WaterCalibrationResults']
        sorted_dates = sorted(self.WaterCalibrationResults.keys(), key=self._custom_sort_key)
        self.RecentWaterCalibration=self.WaterCalibrationResults[sorted_dates[-1]]
        self.RecentWaterCalibrationDate=sorted_dates[-1]
        sides=['Left','Right']
        self.parsed_watercalibration={}
        for side in sides:
            self.parsed_watercalibration[side]={}
            sorted_X,sorted_Y=PlotWaterCalibration._GetWaterCalibration(self,self.WaterCalibrationResults,self.RecentWaterCalibrationDate,side)
            self.parsed_watercalibration[side]['X']=sorted_X
            self.parsed_watercalibration[side]['Y']=sorted_Y

    def _custom_sort_key(self,key):
        if '_' in key:
            date_part, number_part = key.rsplit('_', 1)
            return (date_part, int(number_part))
        else:
            return (key, 0)
        
    def  _get_RewardDelivery(self):
        '''
        Make the RewardDelivery metadata
        '''
        lick_spouts_distance=5000 # distance between the two lick spouts in um

        self.lick_spouts=RewardDeliveryConfig(
            reward_solution= RewardSolution.WATER,
            reward_spouts=[RewardSpoutConfig(
                side=SpoutSide.LEFT,
                starting_position=RelativePosition(
                    coordinate_system='Stage. x: left (+) and right (-); y: forward (+) and backward (-); z: down (+) and up (-). Both left and right lick spouts are fixed on the same stage.',
                    x=self.Obj['B_NewscalePositions'][0][0], y=self.Obj['B_NewscalePositions'][0][1], z=self.Obj['B_NewscalePositions'][0][2],
                    position_unit=SizeUnit.UM
                ),
                variable_position=True
            ),RewardSpoutConfig(
                side=SpoutSide.RIGHT,
                starting_position=RelativePosition(
                    coordinate_system='Relative to the left lick spout.',
                    x=self.Obj['B_NewscalePositions'][0][0]-lick_spouts_distance, y=self.Obj['B_NewscalePositions'][0][1], z=self.Obj['B_NewscalePositions'][0][2],
                    position_unit=SizeUnit.UM
                ),
                variable_position=True
            )],
            notes="Lick spout positions and reward size can be varied and the data is saved in the NWB file"
        )

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