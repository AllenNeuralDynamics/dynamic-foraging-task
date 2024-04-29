import json
import os
import logging
from datetime import datetime

import numpy as np

from aind_data_schema.models.stimulus import OptoStimulation, StimulusEpoch
from aind_data_schema.models.devices import RelativePosition,SpoutSide,Calibration
from aind_data_schema.models.units import SizeUnit
from aind_data_schema.models.modalities import Modality
from foraging_gui.Visualization import PlotWaterCalibration

from aind_data_schema.core.session import (
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
        
        self._handle_edge_cases()

        # save rig metadata
        rig_metadata_full_path=os.path.join(self.Obj['MetadataFolder'],self.Obj['meta_data_dialog']['rig_metadata_file'])
        with open(rig_metadata_full_path, 'w') as f:
            json.dump(self.Obj['meta_data_dialog']['rig_metadata'], f, indent=4)

        self.Obj['session_metadata']= {}
        self._mapper()
        self._get_box_type()
        self._session()
    

    def _mapper(self):
        '''
        Name mapping
        '''
        self.name_mapper = {
            'laser_name_mapper':{
                'Oxxius Lasers 473': 'Blue', 
                'Oxxius Lasers 561': 'Yellow',
                'Oxxius Lasers 638': 'Red',
            },# laser name in the rig metadata and the corresponding color used in the behavior GUI
            'laser_tags':[1,2], # laser tags corresponding to Laser_1 and Laser_2
            'sides':['Left','Right'], # lick spouts
            'lick_spouts_distance':5000, # distance between the two lick spouts in um; this value shoud be directly extracted from the rig metadata
            'camera_list':['SideCameraLeft','SideCameraRight','BottomCamera','BodyCamera'], # camera names in the settings_box.csv
            'camera_name_mapper':{
                'SideCameraLeft': "Face side left",
                'SideCameraRight': "Face side right",
                'BottomCamera': "Bottom",
                'BodyCamera': "Body"
            }, # camera names in the settings_box.csv and the corresponding names in the rig metadata
        }

    def _get_box_type(self):
        '''
        To judge the box type (ephys or behavior) based on the rig_id.
        '''
        if 'EPHYS' in self.Obj['meta_data_dialog']['rig_metadata']['rig_id']:
            self.box_type = 'Ephys'
        else:
            self.box_type = 'Behavior'
    
    def _handle_edge_cases(self):
        '''
        handle edge cases (e.g. missing keys in the json file)
        '''
        # Missing fields camera_start_time and camera_end_time in the Camera_dialog. 
        # Possible reason: 1) the camera is not used in the session. 2 ) the camera is used but the start and end time are not recorded for old version of the software.
        self._initialize_fields(dic=self.Obj['Camera_dialog'],keys=['camera_start_time','camera_end_time'],default_value='')
        
        # Missing Behavior data streams in the json file.
        # Possible reason: 1) the behavior data is not started in the session. 
        if 'B_AnimalResponseHistory' not in self.Obj:
            self.has_behavior_data = False
        else:
            self.has_behavior_data = True
        
        # Missing fields B_NewscalePositions in the json file.
        # Possible reason: 1) the NewScale stage is not connected to the behavior GUI. 2) the session is not started.
        if 'B_NewscalePositions' not in self.Obj:
            self.has_newscale_position = False
        else:
            self.has_newscale_position = True

        # Missing field WaterCalibrationResults in the json file.
        # Possible reason: 1) the water calibration file is not included in the ForagingSettings folder. 2) the water calibration is not saved in the json file.
        if 'WaterCalibrationResults' not in self.Obj:
            self.Obj['WaterCalibrationResults'] = {} 

        # Missing field LaserCalibrationResults in the json file.
        # Possible reason: 1) the optogenetic calibration file is not included in the ForagingSettings folder. 2) the optogenetic calibration is not saved in the json file. 3) no optogenetics calibration for this rig.
        if 'LaserCalibrationResults' not in self.Obj:
            self.Obj['LaserCalibrationResults'] = {}

        # Missing field open_ephys in the json file.
        # Possible reason: 1) The ephys data is recorded but the open ephys is not controlled by the behavior GUI in the old version.
        if 'open_ephys' not in self.Obj:
            self.Obj['open_ephys'] = []
        
        # Missing field Camera_dialog in the json file.
        # Possible reason: 1) Old version of the software.
        if 'Camera_dialog' not in self.Obj:
            self.Obj['Camera_dialog'] = {}

        # Missing field camera_start_time and camera_end_time in the Camera_dialog.
        # Possible reason: 1) the camera is not used in the session. 2 ) the camera is used but the start and end time are not recorded for old version of the software.
        if 'camera_start_time' not in self.Obj['Camera_dialog']:
            self.Obj['Camera_dialog']['camera_start_time'] = ''
        if 'camera_end_time' not in self.Obj['Camera_dialog']:
            self.Obj['Camera_dialog']['camera_end_time'] = ''

        # Missing fields 'Other_SessionStartTime' and 'Other_CurrentTime' in the json file.
        # Possible reason: 1) the behavior session is not started.
        if 'Other_SessionStartTime' not in self.Obj:
            self.session_start_time = ''
            self.session_end_time = '' 
        else:
            self.session_start_time = self.Obj['Other_SessionStartTime']
            self.session_end_time= self.Obj['Other_CurrentTime']

    def _initialize_fields(self,dic,keys,default_value=''):
        '''
        Initialize fields
            If dic has the key, do nothing
            If dic does not have the key, add the key with the default value
            
        Parameters:
        dic: dict
            dictionary to be initialized
        keys: list
            key to be initialized
        default_value: any
        '''
        for key in keys:
            if key not in dic:
                dic[key] = default_value


    def _session(self):
        '''
        Create metadata related to Session class in the aind_data_schema
        '''
        # session_start_time and session_end_time are required fields
        if self.session_start_time == '' or self.session_end_time == '':
            return
        
        self._get_reward_delivery()
        self._get_water_calibration()
        self._get_opto_calibration()
        self.calibration=self.water_calibration+self.opto_calibration

        self._get_behavior_stream()
        self._get_ephys_stream()
        self._get_ophys_stream()
        self._get_high_speed_camera_stream()
        self._get_stimulus()
        self.data_streams = self.behavior_streams+self.ephys_streams+self.ophys_streams+self.high_speed_camera_streams

        session_params = {
            "experimenter_full_name": [self.Obj['Experimenter']],
            "subject_id": self.Obj['ID'],
            "session_start_time": self.session_start_time,
            "session_end_time": self.session_end_time,
            "session_type": self.Obj['Task'],
            "iacuc_protocol": self.Obj['meta_data_dialog']['session_metadata']['IACUCProtocol'],
            "rig_id": self.Obj['meta_data_dialog']['rig_metadata']['rig_id'],
            "notes": self.Obj['ShowNotes'],
            "animal_weight_post": float(self.Obj['WeightAfter']),
            "weight_unit": "gram",
            "reward_consumed_total": float(self.Obj['BS_TotalReward']),
            "reward_consumed_unit": "microliter",
            "calibrations": self.calibration,
            "data_streams": self.data_streams,
        }

        if self.has_newscale_position:
            session_params["reward_delivery"] = self.lick_spouts

        session = Session(**session_params)
        session.write_standard_file(output_directory=self.Obj['MetadataFolder'])

    def _get_high_speed_camera_stream(self):
        '''
        Make the high speed camera stream metadata
        '''
        self.high_speed_camera_streams=[]
        self._get_camera_names()
        if self.Obj['Camera_dialog']['camera_start_time'] != '' and self.Obj['Camera_dialog']['camera_end_time'] != '':
            self.high_speed_camera_streams.append(Stream(
                        stream_modalities=[Modality.BEHAVIOR_VIDEOS],
                        camera_names=self.camera_names,
                        stream_start_time=datetime.strptime(self.Obj['Camera_dialog']['camera_start_time'], '%Y-%m-%d %H:%M:%S.%f'),
                        stream_end_time=datetime.strptime(self.Obj['Camera_dialog']['camera_end_time'], '%Y-%m-%d %H:%M:%S.%f'),
                        mouse_platform_name=self.Obj['meta_data_dialog']['rig_metadata']['mouse_platform']['name'],
                        active_mouse_platform=False,
                ))

    def _get_camera_names(self):
        '''
        get cameras used in this session    
        '''
        self.camera_names=[]
        for camera in self.name_mapper['camera_list']:
            if self.Obj['settings_box']['Has'+camera] == '1':
                self.camera_names.append(self.name_mapper['camera_name_mapper'][camera])

    def _get_ophys_stream(self):
        '''
        Make the ophys stream metadata
        '''
        self.ophys_streams=[]

    def _get_stimulus(self):
        '''
        make the stimulus metadata (e.g. audio and optogenetics)
        '''
        self.stimulus=[]
        self._get_audio_stimulus()
        self._get_optogenetics_stimulus()
        self.stimulus=self.audio_stimulus+self.optogenetics_stimulus

    def _get_audio_stimulus(self):
        '''
        Make the audio stimulus metadata
        '''
        self.audio_stimulus=[]

    def _get_optogenetics_stimulus(self):
        '''
        Make the optogenetics stimulus metadata
        '''
        self.optogenetics_stimulus=[]
        '''
        self.optogenetics_stimulus.append(StimulusEpoch(    
            stimulus= OptoStimulation(
                stimulus_name='Optogenetics',
                notes='Please see NWB files for more details (stimulus epoch and stimulus protocol etc.).',
                pulse_shape='',
                pulse_frequency='',
                number_pulse_trains='',
                pulse_width='',
                pulse_train_duration='',
                fixed_pulse_train_interval='',
                baseline_duration='',
            )
        ))
        '''


    def _get_ephys_stream(self):
        '''
        Make the ephys stream metadata
        '''

        if self.Obj['open_ephys']==[]:
            self.ephys_streams=[]
            return
        
        # find daq names for Neuropixels
        daq_names = [daq['name'] for daq in self.Obj['meta_data_dialog']['rig_metadata']["daqs"] if 'Neuropixels' in daq['name']]

        self.ephys_streams=[]
        self._get_ephys_modules()
        self._get_stick_microscope()
        for current_recording in self.Obj['open_ephys']:
            if 'openephys_stat_recording_time' not in current_recording:
                start_time = self.Obj['Other_SessionStartTime']
                end_time = self.Obj['Other_CurrentTime']
            else:
                start_time = current_recording['openephys_stat_recording_time']
                end_time = current_recording['openephys_stop_recording_time']
            self.ephys_streams.append(Stream(
                    stream_modalities=[Modality.ECEPHYS],
                    stream_start_time=datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S.%f'),
                    stream_end_time=datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S.%f'),
                    daq_names=daq_names,
                    stimulus_device_names=self.stmulus_device_names,
                    mouse_platform_name=self.Obj['meta_data_dialog']['rig_metadata']['mouse_platform']['name'],
                    active_mouse_platform=False,
                    ephys_modules=self.ephys_modules,
                    stick_microscopes=self.stick_microscopes,
                    notes=f"recording type: {current_recording['recording_type']}; file name:{current_recording['prepend_text']}{current_recording['base_text']};  experiment number:{current_recording['record_nodes'][0]['experiment_number']};  recording number:{current_recording['record_nodes'][0]['recording_number']}",
            ))


    def _get_stick_microscope(self):
        '''
        Make the stick microscope metadata
        '''
        self.stick_microscopes=[]
        self._find_stick_microscope_names()
        for stick_microscope in self.stick_microscope_names:
            self.stick_microscopes.append(DomeModule(
                assembly_name=stick_microscope,
                rotation_angle=self.Obj['meta_data_dialog']['session_metadata']['microscopes'][stick_microscope]['Stick_RotationAngle'],
                arc_angle=self.Obj['meta_data_dialog']['session_metadata']['microscopes'][stick_microscope]['Stick_ArcAngle'],
                module_angle=self.Obj['meta_data_dialog']['session_metadata']['microscopes'][stick_microscope]['Stick_ModuleAngle'],
                notes='Did not calibrate.',
            ))

    def _get_ephys_modules(self):
        '''
        Make the ephys module metadata
        '''
        self._get_probe_names()
        self.ephys_modules=[]
        self.stmulus_device_names=[]
        for ind_probe, probe in enumerate(self.probe_names):
            if probe in self.Obj['meta_data_dialog']['session_metadata']['probes']:
                self.ephys_modules.append(EphysModule(
                    rotation_angle=self.Obj['meta_data_dialog']['session_metadata']['probes'][probe]['RotationAngle'],
                    arc_angle=self.Obj['meta_data_dialog']['session_metadata']['probes'][probe]['ArcAngle'],
                    module_angle=self.Obj['meta_data_dialog']['session_metadata']['probes'][probe]['ModuleAngle'],
                    ephys_probes=[EphysProbeConfig(name=probe)],
                    assembly_name=self._find_assembly_names(probe),
                    primary_targeted_structure=self.Obj['meta_data_dialog']['session_metadata']['probes'][probe]['ProbeTarget'],
                    manipulator_coordinates=Coordinates3d(
                        x=self.Obj['meta_data_dialog']['session_metadata']['probes'][probe]['ManipulatorX'],
                        y=self.Obj['meta_data_dialog']['session_metadata']['probes'][probe]['ManipulatorY'],
                        z=self.Obj['meta_data_dialog']['session_metadata']['probes'][probe]['ManipulatorZ'],
                        unit=SizeUnit.UM,
                    ),
                ))
                self.stmulus_device_names.extend(self._find_laser_names(probe))
    

    def _find_stick_microscope_names(self):
        '''
        Find the stick microscope names
        '''
        self.stick_microscope_names=[]
        for stick_microscope in self.Obj['meta_data_dialog']['rig_metadata']['stick_microscopes']:
                self.stick_microscope_names.append(stick_microscope['name'])


    def _find_laser_names(self, probe_name):
        '''
        Find the laser name for the probe
        '''
        for assembly in self.Obj['meta_data_dialog']['rig_metadata']['ephys_assemblies']:
            for probe in assembly['probes']:
                if probe['name'] == probe_name:
                   return probe['lasers']
        return None
    
    def _find_assembly_names(self, probe_name):
        '''
        Find the assembly name for the probe
        '''
        for assembly in self.Obj['meta_data_dialog']['rig_metadata']['ephys_assemblies']:
            if probe_name in [probe['name'] for probe in assembly['probes']]:
               return assembly['name']
        return None
    
    def _get_probe_names(self):
        '''
        Get the probe names from the rig metadata
        '''
        self.probe_names=[]
        for assembly in self.Obj['meta_data_dialog']['rig_metadata']['ephys_assemblies']:
            for probe in assembly['probes']:
                self.probe_names.append(probe['name'])
       
    def _get_behavior_stream(self):
        '''
        Make the behavior stream metadata
        '''

        if self.has_behavior_data==False:
            self.behavior_streams=[]
            return

        if self.box_type == 'Ephys':
            daq_names=["Behavior board","Sound card","Synchronizer","Lickety Split Left","Lickety Split Right"]
        else:
            daq_names=["Behavior board","Sound card","Synchronizer","Janelia lick detector"]

        self.behavior_streams=[]
        self.behavior_streams.append(Stream(
                stream_modalities=[Modality.TRAINED_BEHAVIOR],
                stream_start_time=datetime.strptime(self.Obj['Other_SessionStartTime'], '%Y-%m-%d %H:%M:%S.%f'),
                stream_end_time=datetime.strptime(self.Obj['Other_CurrentTime'], '%Y-%m-%d %H:%M:%S.%f'),
                daq_names=daq_names,
                stimulus_device_names=[''],
                mouse_platform_name=self.Obj['meta_data_dialog']['rig_metadata']['mouse_platform']['name'],
                active_mouse_platform=False,
        ))

    def _get_opto_calibration(self):
        '''
        Make the optogenetic (Laser or LED) calibration metadata
        '''
        if self.Obj['LaserCalibrationResults']=={}:
            self.opto_calibration =[]
            return
        self._parse_opto_calibration() 
        self.opto_calibration=[]
        for current_calibration in self.parsed_optocalibration:
                description= f'Optogenetic calibration for {current_calibration["laser name"]} {current_calibration["Color"]} Laser_{current_calibration["Laser tag"]}. Protocol: {current_calibration["Protocol"]}. Frequency: {current_calibration["Frequency"]}.'
                self.opto_calibration.append(Calibration(
                calibration_date=datetime.strptime(current_calibration['latest_calibration_date'], '%Y-%m-%d').date(),
                device_name=current_calibration['laser name'],
                description=description,
                input= {'input voltage (v)':current_calibration['Voltage']},
                output={'laser power (mw)':current_calibration['Power']} ,
                ))

    def _parse_opto_calibration(self):
        '''
        Parse the optogenetic calibration information from the behavior json file
        '''
        self.parsed_optocalibration=[]
        self.OptoCalibrationResults=self.Obj['LaserCalibrationResults']
        self._get_laser_names_from_rig_metadata()
        for laser in self.laser_names:
                Color=self.name_mapper['laser_name_mapper'][laser]
                latest_calibration_date=self._FindLatestCalibrationDate(Color)
                if latest_calibration_date=='NA':
                    RecentLaserCalibration={}
                else:
                    RecentLaserCalibration=self.Obj['LaserCalibrationResults'][latest_calibration_date]
                no_calibration=False
                if not RecentLaserCalibration=={}:
                    if Color in RecentLaserCalibration.keys():
                        for Protocol in RecentLaserCalibration[Color]:
                            if Protocol=='Sine': 
                                for Frequency in RecentLaserCalibration[Color][Protocol]:
                                    for laser_tag in self.name_mapper['laser_tags']:
                                        voltage=[]
                                        power=[]
                                        for i in range(len(RecentLaserCalibration[Color][Protocol][Frequency][f"Laser_{laser_tag}"]['LaserPowerVoltage'])):
                                            laser_voltage_power=eval(str(RecentLaserCalibration[Color][Protocol][Frequency][f"Laser_{laser_tag}"]['LaserPowerVoltage'][i]))
                                            voltage.append(laser_voltage_power[0])
                                            power.append(laser_voltage_power[1])
                                        voltage, power = zip(*sorted(zip(voltage, power), key=lambda x: x[0]))
                                        self.parsed_optocalibration.append({'laser name':laser,'latest_calibration_date':latest_calibration_date,'Color':Color, 'Protocol':Protocol, 'Frequency':Frequency, 'Laser tag':laser_tag, 'Voltage':voltage, 'Power':power})
                            elif Protocol=='Constant' or Protocol=='Pulse':
                                for laser_tag in self.name_mapper['laser_tags']:
                                    voltage=[]
                                    power=[]
                                    for i in range(len(RecentLaserCalibration[Color][Protocol][f"Laser_{laser_tag}"]['LaserPowerVoltage'])):
                                        laser_voltage_power=eval(str(RecentLaserCalibration[Color][Protocol][f"Laser_{laser_tag}"]['LaserPowerVoltage'][i]))
                                        voltage.append(laser_voltage_power[0])
                                        power.append(laser_voltage_power[1])
                                    voltage, power = zip(*sorted(zip(voltage, power), key=lambda x: x[0]))
                                    self.parsed_optocalibration.append({'laser name':laser,'latest_calibration_date':latest_calibration_date,'Color':Color, 'Protocol':Protocol, 'Frequency':'None', 'Laser tag':laser_tag, 'Voltage':voltage, 'Power':power})
                        else:
                            no_calibration=True
                    else:
                        no_calibration=True
                else:
                    no_calibration=True

    def _get_laser_names_from_rig_metadata(self,Obj=None):
        '''
        Get the Laser/LED names from the rig metadata
        '''
        self.laser_names=[]
        if Obj is None:
            Obj=self.Obj
        for light_source in Obj['meta_data_dialog']['rig_metadata']['light_sources']:
            if light_source['device_type']=='Laser':
                self.laser_names.append(light_source['name'])
        return self.laser_names
    
    def _FindLatestCalibrationDate(self,Laser):
        '''find the latest calibration date for the selected laser'''
        if not ('LaserCalibrationResults' in self.Obj):
            return 'NA'
        Dates=[]
        for Date in self.Obj['LaserCalibrationResults']:
            if Laser in self.Obj['LaserCalibrationResults'][Date].keys():
                Dates.append(Date)
        sorted_dates = sorted(Dates)
        if sorted_dates==[]:
            return 'NA'
        else:
            return sorted_dates[-1]
        
    def _get_water_calibration(self):
        '''
        Make water calibration metadata
        '''

        if self.Obj['WaterCalibrationResults']=={}:
            self.water_calibration =[]
            return
        
        self.water_calibration =[]
        self._parse_water_calibration()
        for side in self.parsed_watercalibration.keys():
            if side == 'Left':
                device_name = 'Left lick spout'
            elif side == 'Right':
                device_name = 'Right lick spout'
            description= f'Water calibration for {device_name}. The input is the valve open time in second and the output is the volume of water delivered in microliters.'
            self.water_calibration.append(Calibration(
                calibration_date=datetime.strptime(self.RecentWaterCalibrationDate, '%Y-%m-%d').date(),
                device_name=device_name,
                description=description ,
                input= {'valve open time (s)':self.parsed_watercalibration[side]['X']},
                output={'water volume (ul)':self.parsed_watercalibration[side]['Y']} ,
            ))

    def _parse_water_calibration(self):
        '''
        Parse the water calibration information from the json file
        '''
        self.WaterCalibrationResults=self.Obj['WaterCalibrationResults']
        sorted_dates = sorted(self.WaterCalibrationResults.keys(), key=self._custom_sort_key)
        self.RecentWaterCalibration=self.WaterCalibrationResults[sorted_dates[-1]]
        self.RecentWaterCalibrationDate=sorted_dates[-1]

        sides=self.name_mapper['sides']
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
        
    def  _get_reward_delivery(self):
        '''
        Make the RewardDelivery metadata
        '''
        if not self.has_newscale_position:
            return
        lick_spouts_distance=self.name_mapper['lick_spouts_distance'] 
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


if __name__ == '__main__':
    generate_metadata(json_file=r'F:\Test\Metadata\715083_2024-04-22_14-32-07.json', dialog_metadata_file=r'C:\Users\xinxin.yin\Documents\ForagingSettings\metadata_dialog\323_EPHYS3_2024-04-27_14-57-06_metadata_dialog.json', output_folder=r'F:\Test\Metadata')