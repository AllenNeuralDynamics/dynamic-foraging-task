import json
import os
import logging
from datetime import datetime

import numpy as np

from foraging_gui.Visualization import PlotWaterCalibration
from aind_data_schema.components.stimulus import AuditoryStimulation
from aind_data_schema.components.devices import SpoutSide,Calibration
from aind_data_schema_models.units import SizeUnit,FrequencyUnit,SoundIntensityUnit,PowerUnit
from aind_data_schema_models.modalities import Modality

from aind_data_schema.core.data_description import DataLevel, Funding, RawDataDescription
from aind_data_schema_models.organizations import Organization
from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform
from aind_data_schema_models.pid_names import PIDName, BaseName
from aind_data_schema.components.coordinates import RelativePosition, Translation3dTransform, Rotation3dTransform,Axis,AxisName


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
    StimulusEpoch,
    StimulusModality,
    SpeakerConfig,
    LaserConfig,
    LightEmittingDiodeConfig,
    DetectorConfig,
    TriggerType,
    FiberConnectionConfig,
    Software
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
        self._save_rig_metadata()
        self.Obj['session_metadata']= {}
        self._mapper()
        self._get_box_type()
        self._session()
        self._session_description()

    def _mapper(self):
        '''
        Name mapping
        '''
        if 'settings' in self.Obj:
            if 'name_mapper_file' in self.Obj['settings']:
                if os.path.exists(self.Obj['settings']['name_mapper_file']):
                    with open(self.Obj['settings']['name_mapper_file']) as f:
                        self.name_mapper_external = json.load(f)

        self.name_mapper = {
            'laser_name_mapper':{
                'Oxxius Laser 473-1': {'color':'Blue','laser_tag':1}, 
                'Oxxius Laser 473-2': {'color':'Blue','laser_tag':2}, 
                'Oxxius Laser 561-1': {'color':'Yellow','laser_tag':1}, 
                'Oxxius Laser 561-2': {'color':'Yellow','laser_tag':2}, 
                'Oxxius Laser 638-1': {'color':'Red','laser_tag':1}, 
                'Oxxius Laser 638-2': {'color':'Red','laser_tag':2}, 
            },# laser name in the rig metadata and the corresponding color used in the behavior GUI
            'led_name_mapper':{
                'LED 460-1': {'color':'Blue','laser_tag':1},
                'LED 460-2': {'color':'Blue','laser_tag':2},
            }, # led name in the rig metadata and the corresponding color used in the behavior GUI

            'laser_tags':[1,2], # laser tags corresponding to Laser_1 and Laser_2
            'sides':['Left','Right'], # lick spouts
            'camera_list':['SideCameraLeft','SideCameraRight','BottomCamera','BodyCamera'], # camera names in the settings_box.csv
            'camera_name_mapper':{
                'SideCameraLeft': "Face side left",
                'SideCameraRight': "Face side right",
                'BottomCamera': "Bottom",
                'BodyCamera': "Body"
            }, # camera names in the settings_box.csv and the corresponding names in the rig metadata
            'institute':{
                'Allen Institute': 'AI',
                'NINDS': 'NINDS',
                'Simons Foundation': 'SIMONS',
            },
            'ephys_rig_behavior_daq_names':["harp behavior board","harp sound card","harp clock synchronization board","harp lickety split left","harp lickety split right"],
            'behavior_rig_behavior_daq_names':["harp behavior board","harp sound card","harp clock synchronization board",'Janelia lick detector'],
            'fiber_photometry_daq_names':[''],
            'ephys_daq_names':['neuropixel basestation'],
            'optogenetics_daq_names':['optogenetics nidaq'],
        }

        # replacing fileds with the external name mapper
        if hasattr(self,'name_mapper_external'):
            for key in self.name_mapper_external:
                self.name_mapper[key] = self.name_mapper_external[key]

    def _get_lick_spouts_distance(self):
        ''' 
        get the distance between the two lick spouts in um
        '''
        self.lick_spouts_distance=5000

    def _get_box_type(self):
        '''
        To judge the box type (ephys or behavior) based on the rig_id. This should be improved in the future.
        '''

        if 'rig_id' not in self.Obj['meta_data_dialog']['rig_metadata']:
            self.box_type = 'Unknown'
            return
        
        if 'EPHYS' in self.Obj['meta_data_dialog']['rig_metadata']['rig_id']:
            self.box_type = 'Ephys'
        else:
            self.box_type = 'Behavior'
    
    def _session_description(self):
        '''
        Generate the session description to the MetadataFolder
        '''
        if self.Obj['meta_data_dialog']['rig_metadata']=={}:
            return
        self._get_session_time()
        if self.session_start_time == '' or self.session_end_time == '':
            return
        
        self.orcid = BaseName(name="Open Researcher and Contributor ID", abbreviation="ORCID")
        self._get_modality()
        self._get_investigators()
        self._get_funding_source()
        self._get_platform()

        description= RawDataDescription(
            data_level=DataLevel.RAW,
            funding_source=self.funding_source,
            investigators=self.investigators,
            modality=self.modality,
            project_name=self.Obj['meta_data_dialog']['session_metadata']['ProjectName'],
            data_summary=self.Obj['meta_data_dialog']['session_metadata']['DataSummary'],
            institution=Organization.AIND,
            creation_time=self.session_start_time,
            platform= self.platform,
            subject_id=self.Obj['ID'],
        )
        description.write_standard_file(output_directory=self.Obj['MetadataFolder'])

    def _get_funding_source(self):
        '''
        Get the funding source
        '''
        self.funding_source=[Funding(
            funder=getattr(Organization,self.name_mapper['institute'][self.Obj['meta_data_dialog']['session_metadata']['FundingSource']]),
            grant_number=self.Obj['meta_data_dialog']['session_metadata']['GrantNumber'],
            fundee=self.Obj['meta_data_dialog']['session_metadata']['Fundee'],
        )]
                
    def _get_platform(self):
        '''
        Get the platform name. This should be improved in the future.
        '''
        if self.box_type == 'Ephys':
            self.platform = Platform.ECEPHYS
        elif self.box_type == 'Behavior':
            self.platform = Platform.BEHAVIOR
        else:
            self.platform = ''

    def _get_session_time(self):
        '''
        Get the session start and session end time
        '''
        # priority behavior_streams>high_speed_camera_streams>ephys_streams>ophys_streams
        if self.behavior_streams!=[]:
            self.session_start_time = self.behavior_streams[0].stream_start_time
            self.session_end_time = self.behavior_streams[0].stream_end_time
        elif self.high_speed_camera_streams!=[]:
            self.session_start_time = self.high_speed_camera_streams[0].stream_start_time
            self.session_end_time = self.high_speed_camera_streams[0].stream_end_time
        elif self.ephys_streams!=[]:
            self.session_start_time = self.ephys_streams[0].stream_start_time
            self.session_end_time = self.ephys_streams[0].stream_end_time
        elif self.ophys_streams!=[]:
            self.session_start_time = self.ophys_streams[0].stream_start_time
            self.session_end_time = self.ophys_streams[0].stream_end_time
        else:
            self.session_start_time = ''
            self.session_end_time = ''

    def _get_modality(self):
        '''
        Get all the modalities used in the session
        '''
        self.modality = []
        if self.behavior_streams!=[]:
            self.modality.append(Modality.BEHAVIOR)
        if self.ephys_streams!=[]:
            self.modality.append(Modality.ECEPHYS)
        if self.ophys_streams!=[]:
            self.modality.append(Modality.FIB)
        if self.high_speed_camera_streams!=[]:
            self.modality.append(Modality.BEHAVIOR_VIDEOS)
        
    def _get_investigators(self):
        '''
        Get investigators
        '''
        self.investigators=[]
        investigators=self.Obj['meta_data_dialog']['session_metadata']['Investigators'].split(',')
        for investigator in investigators:
            if investigator != '':
                self.investigators.append(PIDName(name=investigator, registry=self.orcid))

    def _save_rig_metadata(self):
        '''
        Save the rig metadata to the MetadataFolder
        '''
        if self.Obj['meta_data_dialog']['rig_metadata_file']=='' or self.Obj['MetadataFolder']=='':
            return
        
        rig_metadata_full_path=os.path.join(self.Obj['MetadataFolder'],self.Obj['meta_data_dialog']['rig_metadata_file'])
        with open(rig_metadata_full_path, 'w') as f:
            json.dump(self.Obj['meta_data_dialog']['rig_metadata'], f, indent=4)

    def _handle_edge_cases(self):
        '''
        handle edge cases (e.g. missing keys in the json file)
        '''
        # Missing fields camera_start_time and camera_stop_time in the Camera_dialog. 
        # Possible reason: 1) the camera is not used in the session. 2 ) the camera is used but the start and end time are not recorded for old version of the software.
        self._initialize_fields(dic=self.Obj['Camera_dialog'],keys=['camera_start_time','camera_stop_time'],default_value='')
        
        # Missing Behavior data streams in the json file.
        # Possible reason: 1) the behavior data is not started in the session. 
        if 'B_AnimalResponseHistory' not in self.Obj:
            self.has_behavior_data = False
        else:
            self.has_behavior_data = True
        
        # Missing fields B_NewscalePositions, LickSpoutReferenceArea, LickSpoutReferenceX, LickSpoutReferenceY, LickSpoutReferenceZ in the json file.
        # Possible reason: 1) the NewScale stage is not connected to the behavior GUI. 2) the session is not started.
        if ('B_NewscalePositions' not in self.Obj) or (self.Obj['meta_data_dialog']['session_metadata']['LickSpoutReferenceArea']=='') or (self.Obj['meta_data_dialog']['session_metadata']['LickSpoutReferenceX']=='') or (self.Obj['meta_data_dialog']['session_metadata']['LickSpoutReferenceY']=='') or (self.Obj['meta_data_dialog']['session_metadata']['LickSpoutReferenceZ']==''):
            self.has_reward_delivery = False
        elif self.Obj['B_NewscalePositions']==[]:
            self.has_reward_delivery = False
        else:
            self.has_reward_delivery = True

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

        # Missing field 'settings_box' in the json file.
        # Possible reason: 1) Old version of the software.
        if 'settings_box' not in self.Obj:
            self.Obj['settings_box'] = {}

        # Missing field 'meta_data_dialog' in the json file.
        # Possible reason: 1) Old version of the software.
        if 'meta_data_dialog' not in self.Obj:
            self.Obj['meta_data_dialog'] = {}

        # Missing field 'rig_metadata' in the json file.
        # Possible reason: 1) Old version of the software. 2) the rig metadata is not provided.
        if 'rig_metadata' not in self.Obj['meta_data_dialog']:
            self.Obj['meta_data_dialog']['rig_metadata'] = {}

        # Missing field 'rig_metadata_file' and 'MetadataFolder' in the json file.
        # Possible reason: 1) Old version of the software. 2) the rig metadata is not provided.
        self._initialize_fields(dic=self.Obj['meta_data_dialog'],keys=['rig_metadata_file'],default_value='')
        self._initialize_fields(dic=self.Obj,keys=['MetadataFolder'],default_value='')
    
        # Missing field Other_go_cue_decibel is not recorded in the behavior json file.
        # Possible reason: 1) the go cue decibel is not set in the foraging settings file. 2) old version of the software.
        if 'Other_go_cue_decibel' not in self.Obj:
            self.Obj['Other_go_cue_decibel'] = 60

        # Missing field 'fiber_photometry_start_time' and 'fiber_photometry_end_time' in the json file.
        # Possible reason: 1) the fiber photometry data is not recorded in the session. 2) the fiber photometry data is recorded but the start and end time are not recorded in the old version of the software.
        self._initialize_fields(dic=self.Obj,keys=['fiber_photometry_start_time','fiber_photometry_end_time'],default_value='')

        # Missing field 'FIPMode' in the json file.
        # Possible reason: 1) old version of the software.
        if 'FIPMode' not in self.Obj:
            self.Obj['fiber_mode'] = ''
        else:
            self.Obj['fiber_mode'] = self.Obj['FIPMode']

        # Missing field 'commit_ID', 'repo_url', 'current_branch' in the json file.
        # Possible reason: 1) old version of the software.
        if 'commit_ID' not in self.Obj:
            self._initialize_fields(dic=self.Obj,keys=['commit_ID','repo_url','current_branch'],default_value='')

        # Missing field 'Other_lick_spout_distance' in the json file.
        # Possible reason: 1) old version of the software.
        if 'Other_lick_spout_distance' not in self.Obj:
            self.Obj['Other_lick_spout_distance']=5000

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
        if self.Obj['meta_data_dialog']['rig_metadata']=={}:
            return
        
        self._get_reward_delivery()
        self._get_water_calibration()
        self._get_opto_calibration()
        self.calibration=self.water_calibration+self.opto_calibration

        self._get_behavior_stream()
        self._get_ephys_stream()
        self._get_ophys_stream()
        self._get_high_speed_camera_stream()
        self._get_session_time()
        if self.session_start_time == '' or self.session_end_time == '':
            return

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
            "weight_unit": "gram",
            "reward_consumed_total": float(self.Obj['BS_TotalReward']),
            "reward_consumed_unit": "microliter",
            "calibrations": self.calibration,
            "data_streams": self.data_streams,
            "mouse_platform_name": self.Obj['meta_data_dialog']['rig_metadata']['mouse_platform']['name'],
            "active_mouse_platform": False,
            "protocol_id":[self.Obj['meta_data_dialog']['session_metadata']['ProtocolID']],
        }

        if self.reward_delivery!=[]:
            session_params["reward_delivery"] = self.reward_delivery

        #adding go cue and opto parameters to the stimulus_epochs
        if self.stimulus!=[]:
            session_params["stimulus_epochs"] = self.stimulus

        if self.Obj['WeightAfter']!='':
            session_params["animal_weight_post"]=float(self.Obj['WeightAfter'])

        session = Session(**session_params)
        session.write_standard_file(output_directory=self.Obj['MetadataFolder'])

    def _get_high_speed_camera_stream(self):
        '''
        Make the high speed camera stream metadata
        '''
        self.high_speed_camera_streams=[]
        self._get_camera_names()
        if self.Obj['Camera_dialog']['camera_start_time'] != '' and self.Obj['Camera_dialog']['camera_stop_time'] != '' and self.camera_names != []:
            self.high_speed_camera_streams.append(Stream(
                        stream_modalities=[Modality.BEHAVIOR_VIDEOS],
                        camera_names=self.camera_names,
                        stream_start_time=datetime.strptime(self.Obj['Camera_dialog']['camera_start_time'], '%Y-%m-%d %H:%M:%S.%f'),
                        stream_end_time=datetime.strptime(self.Obj['Camera_dialog']['camera_stop_time'], '%Y-%m-%d %H:%M:%S.%f'),
                ))

    def _get_camera_names(self):
        '''
        get cameras used in this session    
        '''
        if 'settings_box' not in self.Obj:
            self.camera_names=[]
            return
        
        self.camera_names=[]
        for camera in self.name_mapper['camera_list']:
            if 'Has'+camera in self.Obj['settings_box']:
                if self.Obj['settings_box']['Has'+camera] == '1':
                    self.camera_names.append(self.name_mapper['camera_name_mapper'][camera])

    def _get_ophys_stream(self):
        '''
        Make the ophys stream metadata
        '''
        self.ophys_streams=[]
        if self.Obj['fiber_photometry_start_time']=='':
            return
        self._get_photometry_light_sources_config()
        self._get_photometry_detectors()
        self._get_fiber_connections()
        self.ophys_streams.append(Stream(
                stream_modalities=[Modality.FIB],
                stream_start_time=datetime.strptime(self.Obj['fiber_photometry_start_time'], '%Y-%m-%d %H:%M:%S.%f'),
                stream_end_time=datetime.strptime(self.Obj['fiber_photometry_end_time'], '%Y-%m-%d %H:%M:%S.%f'),
                daq_names=self.name_mapper['fiber_photometry_daq_names'],
                light_sources=self.fib_light_sources_config,
                detectors=self.fib_detectors,
                fiber_connections=self.fiber_connections,
                notes=f'fib mode: {self.Obj['fiber_mode']}',
        ))

    def _get_fiber_connections(self):
        '''
        get the fiber connections
        '''
        # hard coded for now
        self.fiber_connections=[
                FiberConnectionConfig(
                    patch_cord_name="Patch Cord A",
                    patch_cord_output_power=20,
                    output_power_unit="microwatt",
                    fiber_name="Fiber 0",
                )]
        self.fiber_connections.append(
                FiberConnectionConfig(
                    patch_cord_name="Patch Cord B",
                    patch_cord_output_power=20,
                    output_power_unit="microwatt",
                    fiber_name="Fiber 1",
                ))
        self.fiber_connections.append(
                FiberConnectionConfig(
                    patch_cord_name="Patch Cord C",
                    patch_cord_output_power=20,
                    output_power_unit="microwatt",
                    fiber_name="Fiber 2",
                ))
        self.fiber_connections.append(
                 FiberConnectionConfig(
                    patch_cord_name="Patch Cord D",
                    patch_cord_output_power=20,
                    output_power_unit="microwatt",
                    fiber_name="Fiber 3",
                 ))
        return
        
        # this is not complete. 
        self.fiber_connections=[]
        for patch_cord in self.Obj['meta_data_dialog']['rig_metadata']['patch_cords']:
            self.fiber_connections.append(FiberConnectionConfig(
                patch_cord_name=patch_cord['name'],
                patch_cord_output_power=0,
                output_power_unit=PowerUnit.MW,
                fiber_name='NA',
            ))


    def _get_photometry_detectors(self):
        '''
        get the photometry detectors
        '''
        self.fib_detectors=[]
        exposure_time=datetime.strptime(self.Obj['fiber_photometry_end_time'], '%Y-%m-%d %H:%M:%S.%f')-datetime.strptime(self.Obj['fiber_photometry_start_time'], '%Y-%m-%d %H:%M:%S.%f')
        exposure_time=float(exposure_time.total_seconds())

        for current_detector in self.Obj['meta_data_dialog']['rig_metadata']['detectors'] :
            if current_detector['device_type']=='Detector':
                self.fib_detectors.append(DetectorConfig(
                    name=current_detector['name'],
                    exposure_time=exposure_time,
                    trigger_type=TriggerType.INTERNAL,
                ))    
                    

    def _get_photometry_light_sources_config(self):
        '''
        get the light sources config for fiber photometry
        '''
        self.fib_light_sources_config=[]
        for current_light_source in self.Obj['meta_data_dialog']['rig_metadata']['light_sources']:
            # caution: the light sources for the photometry are selected based on the device type, and excludes LED with camera included in the notes (LED for camera illumination). This may be wrong for some rigs.
            if (current_light_source['device_type'] in ['LightEmittingDiode','Light emitting diode']):
                if current_light_source['notes'] !=None:
                    if 'camera' in current_light_source['notes']:
                        continue
                self.fib_light_sources_config.append(LightEmittingDiodeConfig(
                    name=current_light_source['name'],
                ))

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
        if self.behavior_streams==[]:
            return
        
        self.audio_stimulus.append(StimulusEpoch(
            stimulus_name='auditory go cue',
            notes=f"The duration of go cue is 100ms. The frequency is 7500Hz. Decibel is {self.Obj['Other_go_cue_decibel']}dB.",
            stimulus_modalities=[StimulusModality.AUDITORY],
            stimulus_start_time=self.session_start_time,
            stimulus_end_time=self.session_end_time,
            stimulus_parameters=[AuditoryStimulation(
                sitmulus_name='auditory go cue',
                sample_frequency=96000,
                frequency_unit=FrequencyUnit.HZ,
                amplitude_modulation_frequency=7500,
            )],
            speaker_config=SpeakerConfig(
                name='Speaker',
                volume=self.Obj['Other_go_cue_decibel'],
                volume_unit=SoundIntensityUnit.DB,
            )
        ))
    def _get_optogenetics_stimulus(self):
        '''
        Make the optogenetics stimulus metadata
        '''
        self.optogenetics_stimulus=[]
        a=np.array(self.Obj['B_SelectedCondition'])
        self.Obj['B_SelectedCondition']=a.astype(int)
        if sum( self.Obj['B_SelectedCondition'])==0:
            return  
        self._get_light_source_config()
        self.optogenetics_stimulus.append(StimulusEpoch(    
                stimulus_name='Optogenetics',
                stimulus_modalities=[StimulusModality.OPTOGENETICS],
                notes='Please see NWB files for more details (stimulus epoch and stimulus protocol etc.).',
                stimulus_start_time=self.session_start_time,
                stimulus_end_time=self.session_end_time,
                light_source_config=self.light_source_config,
        ))


    def _get_light_source_config(self):
        '''
        get the optogenetics stimulus light source config
        '''
        self.light_source_config=[]
        self._get_light_names_used_in_session()
        if self.box_type=='Ephys':
            for light_source in self.light_names_used_in_session:
                wavelength=self._get_light_pars(light_source)
                self.light_source_config.append(LaserConfig(
                    name=light_source,
                    wavelength=wavelength,
                ))
        elif self.box_type=='Behavior':
            for light_source in self.light_names_used_in_session:
                self.light_source_config.append(LightEmittingDiodeConfig(
                    name=light_source,
                ))

    def _get_light_pars(self,light_source):
        '''
        Get the wavelength and wavelength unit for the light source
        '''
        for current_stimulus_device in self.Obj['meta_data_dialog']['rig_metadata']['light_sources']:
            if current_stimulus_device['name']==light_source:
                return current_stimulus_device['wavelength']


    def _get_light_names_used_in_session(self):
        '''
        Get the optogenetics laser names used in the session
        '''
        self.light_names_used_in_session=[]
        light_sources=[]
        index=np.where(np.array(self.Obj['B_SelectedCondition'])==1)[0]
        for i in index:
            current_condition=self.Obj['B_SelectedCondition'][i]
            current_color=self.Obj[f'TP_LaserColor_{current_condition}'][i]
            current_location=self.Obj[f'TP_Location_{current_condition}'][i]
            if current_location=='Both':
                light_sources.append({'color':current_color,'laser_tag':1})
                light_sources.append({'color':current_color,'laser_tag':2})
            elif current_location=='Left':
                light_sources.append({'color':current_color,'laser_tag':1})
            elif current_location=='Right':
                light_sources.append({'color':current_color,'laser_tag':2})

        if self.box_type=='Ephys':
            for light_source in light_sources:
                self.light_names_used_in_session.append([key for key, value in self.name_mapper['laser_name_mapper'].items() if value == light_source][0])
        elif self.box_type=='Behavior':
            for light_source in light_sources:
                self.light_names_used_in_session.append([key for key, value in self.name_mapper['led_name_mapper'].items() if value == light_source][0])

        self.light_names_used_in_session = list(set(self.light_names_used_in_session))

        

    def _get_ephys_stream(self):
        '''
        Make the ephys stream metadata
        '''

        if self.Obj['open_ephys']==[]:
            self.ephys_streams=[]
            return
        
        # find daq names for Neuropixels
        daq_names = self.name_mapper['ephys_daq_names']

        self.ephys_streams=[]
        self._get_ephys_modules()
        if self.ephys_modules==[]:
            return
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
            daq_names=self.name_mapper['ephys_rig_behavior_daq_names']
        else:
            daq_names=self.name_mapper['behavior_rig_behavior_daq_names']

        self.behavior_streams=[]
        self._get_behavior_software()
        self.behavior_streams.append(Stream(
                stream_modalities=[Modality.BEHAVIOR],
                stream_start_time=datetime.strptime(self.Obj['Other_SessionStartTime'], '%Y-%m-%d %H:%M:%S.%f'),
                stream_end_time=datetime.strptime(self.Obj['Other_CurrentTime'], '%Y-%m-%d %H:%M:%S.%f'),
                daq_names=daq_names,
                software=self.behavior_software,
        ))
    def _get_behavior_software(self):
        '''
        get the behavior software version information
        '''
        self.behavior_software=[]
        self.behavior_software.append(Software(
            name='dynamic-foraging-task',
            version=f'branch:{self.Obj["current_branch"]}   commit ID:{self.Obj["commit_ID"]}',
            url=self.Obj["repo_url"],
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
                if laser not in self.name_mapper['laser_name_mapper']:
                    continue
                color=self.name_mapper['laser_name_mapper'][laser]['color']
                laser_tag=self.name_mapper['laser_name_mapper'][laser]['laser_tag']
                latest_calibration_date=self._FindLatestCalibrationDate(color)
                if latest_calibration_date=='NA':
                    RecentLaserCalibration={}
                else:
                    RecentLaserCalibration=self.Obj['LaserCalibrationResults'][latest_calibration_date]
                no_calibration=False
                if not RecentLaserCalibration=={}:
                    if color in RecentLaserCalibration.keys():
                        for Protocol in RecentLaserCalibration[color]:
                            if Protocol=='Sine': 
                                for Frequency in RecentLaserCalibration[color][Protocol]:
                                    voltage=[]
                                    power=[]
                                    for i in range(len(RecentLaserCalibration[color][Protocol][Frequency][f"Laser_{laser_tag}"]['LaserPowerVoltage'])):
                                        laser_voltage_power=eval(str(RecentLaserCalibration[color][Protocol][Frequency][f"Laser_{laser_tag}"]['LaserPowerVoltage'][i]))
                                        voltage.append(laser_voltage_power[0])
                                        power.append(laser_voltage_power[1])
                                    voltage, power = zip(*sorted(zip(voltage, power), key=lambda x: x[0]))
                                    self.parsed_optocalibration.append({'laser name':laser,'latest_calibration_date':latest_calibration_date,'Color':color, 'Protocol':Protocol, 'Frequency':Frequency, 'Laser tag':laser_tag, 'Voltage':voltage, 'Power':power})
                            elif Protocol=='Constant':
                                voltage=[]
                                power=[]
                                for i in range(len(RecentLaserCalibration[color][Protocol][f"Laser_{laser_tag}"]['LaserPowerVoltage'])):
                                    laser_voltage_power=eval(str(RecentLaserCalibration[color][Protocol][f"Laser_{laser_tag}"]['LaserPowerVoltage'][i]))
                                    voltage.append(laser_voltage_power[0])
                                    power.append(laser_voltage_power[1])
                                voltage, power = zip(*sorted(zip(voltage, power), key=lambda x: x[0]))
                                self.parsed_optocalibration.append({'laser name':laser,'latest_calibration_date':latest_calibration_date,'Color':color, 'Protocol':Protocol, 'Frequency':'None', 'Laser tag':laser_tag, 'Voltage':voltage, 'Power':power})
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
            if light_source['device_type'] in ['Laser','LightEmittingDiode']:
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
        if not self.has_reward_delivery:
            self.reward_delivery=[]
            return

        device_oringin=self.Obj['meta_data_dialog']['session_metadata']['LickSpoutReferenceArea']
        lick_spouts_distance=self.Obj['Other_lick_spout_distance']
        # using the last position of the stage
        start_position=[self.Obj['B_NewscalePositions'][-1][0], self.Obj['B_NewscalePositions'][-1][1], self.Obj['B_NewscalePositions'][-1][2]]

        # assuming refering to the left lick spout
        reference_spout_position=[float(self.Obj['meta_data_dialog']['session_metadata']['LickSpoutReferenceX']),float(self.Obj['meta_data_dialog']['session_metadata']['LickSpoutReferenceY']),float(self.Obj['meta_data_dialog']['session_metadata']['LickSpoutReferenceZ'])]
        left_lick_spout_reference_position=np.array(reference_spout_position)-np.array(start_position)
        right_lick_spout_reference_position=left_lick_spout_reference_position+np.array([-lick_spouts_distance,0,0])

        self.reward_delivery=RewardDeliveryConfig(
            reward_solution= RewardSolution.WATER,
            reward_spouts=[RewardSpoutConfig(
                side=SpoutSide.LEFT,
                starting_position=RelativePosition(
                    device_position_transformations=[
                        Translation3dTransform(translation=left_lick_spout_reference_position.tolist()),
                        Rotation3dTransform(rotation=[1, 0, 0, 0, 1, 0, 0, 0, 1])
                    ],
                    device_origin=device_oringin,  
                    device_axes=[
                        Axis(name=AxisName.X, direction="Left"),
                        Axis(name=AxisName.Y, direction="Forward"),
                        Axis(name=AxisName.Z, direction="Down")
                    ],
                    notes="X positive is left, Y positive is forward, and Z positive is down."
                ),
                variable_position=True
            ),RewardSpoutConfig(
                side=SpoutSide.RIGHT,
                starting_position=RelativePosition(
                    device_position_transformations=[
                        Translation3dTransform(translation=right_lick_spout_reference_position.tolist()),
                        Rotation3dTransform(rotation=[1, 0, 0, 0, 1, 0, 0, 0, 1])
                    ],
                    device_origin=device_oringin,  
                    device_axes=[
                        Axis(name=AxisName.X, direction="Left"),
                        Axis(name=AxisName.Y, direction="Forward"),
                        Axis(name=AxisName.Z, direction="Down")
                    ],
                    notes="X positive is left, Y positive is forward, and Z positive is down."
                ),
                variable_position=True
            )],
            notes="Lick spout positions and reward size can be varied and the data is saved in the NWB file"
        )


if __name__ == '__main__':
    
    generate_metadata(json_file=r'Y:\715083\behavior_715083_2024-04-26_17-12-15\behavior\715083_2024-04-26_17-12-15.json', dialog_metadata_file=r'C:\Users\xinxin.yin\Documents\ForagingSettings\metadata_dialog\323_EPHYS3_2024-05-13_12-38-51_metadata_dialog.json', output_folder=r'F:\Test\Metadata')
    #generate_metadata(json_file=r'F:\Test\Metadata\715083_2024-04-22_14-32-07.json', dialog_metadata_file=r'C:\Users\xinxin.yin\Documents\ForagingSettings\metadata_dialog\323_EPHYS3_2024-05-09_12-42-30_metadata_dialog.json', output_folder=r'F:\Test\Metadata')