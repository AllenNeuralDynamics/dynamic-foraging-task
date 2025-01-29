"""
Transfer current Json/mat format from Bonsai behavior control to NWB format
"""
from uuid import uuid4
import numpy as np
import json
import os
import datetime
import logging
import pandas as pd
from dateutil.tz import tzlocal

from pynwb import NWBHDF5IO, NWBFile, TimeSeries
from pynwb.file import Subject
from scipy.io import loadmat

save_folder=R'F:\Data_for_ingestion\Foraging_behavior\Bonsai\nwb'

logger = logging.getLogger(__name__)

def _get_field(obj, field_list, reject_list=[None, np.nan,'',[]], index=None, default=np.nan):
    """get field from obj, if not found, return default

    Parameters
    ----------
    obj : the object to get the field from
    field : str or list
            if is a list, try one by one until one is found in the obj (for back-compatibility)
    reject_list: list, optional
            if the value is in the reject_list, reject this value and continue to search the next field name in the field_list
    index: int, optional
            if index is not None and the field is a list, return the index-th element of the field
            otherwise, return default
    default : _type_, optional
        _description_, by default np.nan
    """
    if type(field_list) is not list:
        field_list = [field_list]
        
    for f in field_list:
            has_field=0
            if type(obj) is type:
                if hasattr(obj, f):
                    value = getattr(obj, f)
                    has_field=1
            # the obj.Opto_dialog is a dictionary
            elif type(obj) is dict:
                if f in obj:
                    value = obj[f]
                    has_field=1
            if has_field==0:
                continue
            if value in reject_list:
                continue
            if index is None:
                return value
            # If index is int, try to get the index-th element of the field
            try:
                if value[index] in reject_list:
                    continue
                return value[index]
            except:
                logger.debug(f"Field {field_list} is iterable or index {index} is out of range")
                return default
    else:
        logger.debug(f"Field {field_list} not found in the object")
        return default
    

######## load the Json/Mat file #######
def bonsai_to_nwb(fname, save_folder=save_folder):
    if fname.endswith('.mat'):
        Obj = loadmat(fname)
        for key in Obj.keys():
            Value=Obj[key]
            if key=='B_SuggestedWater':
                pass
            if isinstance(Value, np.ndarray):
                if Value.shape[0]==1:
                    try:
                        Value=Value.reshape(Value.shape[1],)
                    except:
                        pass
                if Value.shape==(1,):
                    Obj[key]=Value.tolist()[0]
                else:
                    Obj[key]=Value.tolist()
    elif fname.endswith('.json'):
        f = open (fname, "r")
        Obj = json.loads(f.read())
        f.close()
        
    # transfer dictionary to class
    class obj:
        pass
    for attr_name in Obj.keys():
        setattr(obj, attr_name, Obj[attr_name])
     
    # Early return if missing some key fields
    if any([not hasattr(obj, field) for field in ['B_TrialEndTime', 'TP_BaseRewardSum']]):
        logger.warning(f"Missing key fields! Skipping {fname}")
        return 'incomplete_json'
    
    if not hasattr(obj, 'Other_SessionStartTime'):
        session_start_timeC=datetime.datetime.strptime('2023-04-26', "%Y-%m-%d") # specific for LA30_2023-04-27.json
    else:
        session_start_timeC=datetime.datetime.strptime(obj.Other_SessionStartTime, '%Y-%m-%d %H:%M:%S.%f')
    
    # add local time zone explicitly
    session_start_timeC = session_start_timeC.replace(tzinfo=tzlocal())

    ### session related information ###
    nwbfile = NWBFile(
        session_description='Session end time:'+_get_field(obj, 'Other_CurrentTime', default='None'),  
        identifier=str(uuid4()),  # required
        session_start_time= session_start_timeC,  # required
        session_id=os.path.basename(fname),  # optional
        experimenter=[
            _get_field(obj, 'Experimenter', default='None'),
        ],  # optional
        lab="",  # optional
        institution="Allen Institute for Neural Dynamics",  # optional
        ### add optogenetics description (the target brain areas). 
        experiment_description="",  # optional
        related_publications="",  # optional
        notes=obj.ShowNotes,
        protocol=obj.Task
    )

    #######  Animal information #######
    # need to get more subject information through subject_id
    nwbfile.subject = Subject(
        subject_id=obj.ID,
        description='Animal name:'+obj.ID,
        species="Mus musculus",
        weight=_get_field(obj, 'WeightAfter',default=np.nan),
    )
    # print(nwbfile)
    
    ### Add some meta data to the scratch (rather than the session description) ###
    # Handle water info (with better names)
    BS_TotalReward = _get_field(obj, 'BS_TotalReward')
    # Turn uL to mL if the value is too large
    water_in_session_foraging = BS_TotalReward / 1000 if BS_TotalReward > 5.0 else BS_TotalReward 
    # Old name "ExtraWater" goes first because old json has a wrong Suggested Water
    water_after_session = float(_get_field(obj, 
                                           field_list=['ExtraWater', 'SuggestedWater'], default=np.nan
                                           ))
    water_day_total = float(_get_field(obj, 'TotalWater'))
    water_in_session_total = water_day_total - water_after_session
    water_in_session_manual = water_in_session_total - water_in_session_foraging
    Opto_dialog=_get_field(obj, 'Opto_dialog',default='None')
    metadata = {
        # Meta
        'box': _get_field(obj, ['box', 'Tower']),
        'session_end_time': _get_field(obj, 'Other_CurrentTime'),
        'session_run_time_in_min': _get_field(obj, 'Other_RunningTime'),
        
        # Water (all in mL)
        'water_in_session_foraging': water_in_session_foraging, 
        'water_in_session_manual': water_in_session_manual,
        'water_in_session_total':  water_in_session_total,
        'water_after_session': water_after_session,
        'water_day_total': water_day_total,

        # Weight
        'base_weight': float(_get_field(obj, 'BaseWeight')),
        'target_weight': float(_get_field(obj, 'TargetWeight')),
        'target_weight_ratio': float(_get_field(obj, 'TargetRatio')),
        'weight_after': float(_get_field(obj, 'WeightAfter')),
        
        # Performance
        'foraging_efficiency': _get_field(obj, 'B_for_eff_optimal'),
        'foraging_efficiency_with_actual_random_seed': _get_field(obj, 'B_for_eff_optimal_random_seed'),

        # Optogenetics
        'laser_1_calibration_power': float(_get_field(Opto_dialog, 'laser_1_calibration_power')),
        'laser_2_calibration_power': float(_get_field(Opto_dialog, 'laser_2_calibration_power')),
        'laser_1_target_areas': _get_field(Opto_dialog, 'laser_1_target',default='None'),
        'laser_2_target_areas': _get_field(Opto_dialog, 'laser_2_target',default='None'),

        # Behavior control software version
        'commit_ID':_get_field(obj, 'commit_ID',default='None'),
        'repo_url':_get_field(obj, 'repo_url',default='None'),
        'current_branch':_get_field(obj, 'current_branch',default='None'),
    }

    # Turn the metadata into a DataFrame in order to add it to the scratch
    df_metadata = pd.DataFrame(metadata, index=[0])

    # Are there any better places to add arbitrary meta data in nwb?
    # I don't bother creating an nwb "extension"...
    # To retrieve the metadata, use:
    # nwbfile.scratch['metadata'].to_dataframe()
    nwbfile.add_scratch(df_metadata, 
                        name="metadata",
                        description="Some important session-wise meta data")


    #######       Add trial     #######
    ## behavior events (including trial start/end time; left/right lick time; give left/right reward time) ##
    nwbfile.add_trial_column(name='animal_response', description=f'The response of the animal. 0, left choice; 1, right choice; 2, no response')
    nwbfile.add_trial_column(name='rewarded_historyL', description=f'The reward history of left lick port')
    nwbfile.add_trial_column(name='rewarded_historyR', description=f'The reward history of right lick port')
    nwbfile.add_trial_column(name='delay_start_time', description=f'The delay start time')
    nwbfile.add_trial_column(name='goCue_start_time', description=f'The go cue start time')
    nwbfile.add_trial_column(name='reward_outcome_time', description=f'The reward outcome time (reward/no reward/no response) Note: This is in fact time when choice is registered.')
    ## training paramters ##
    # behavior structure
    nwbfile.add_trial_column(name='bait_left', description=f'Whether the current left lickport has a bait or not')
    nwbfile.add_trial_column(name='bait_right', description=f'Whether the current right lickport has a bait or not')
    nwbfile.add_trial_column(name='base_reward_probability_sum', description=f'The summation of left and right reward probability')
    nwbfile.add_trial_column(name='reward_probabilityL', description=f'The reward probability of left lick port')
    nwbfile.add_trial_column(name='reward_probabilityR', description=f'The reward probability of right lick port')
    nwbfile.add_trial_column(name='reward_random_number_left', description=f'The random number used to determine the reward of left lick port')
    nwbfile.add_trial_column(name='reward_random_number_right', description=f'The random number used to determine the reward of right lick port')
    nwbfile.add_trial_column(name='left_valve_open_time', description=f'The left valve open time')
    nwbfile.add_trial_column(name='right_valve_open_time', description=f'The right valve open time')
    # block
    nwbfile.add_trial_column(name='block_beta', description=f'The beta of exponential distribution to generate the block length')
    nwbfile.add_trial_column(name='block_min', description=f'The minimum length allowed for each block')
    nwbfile.add_trial_column(name='block_max', description=f'The maxmum length allowed for each block')
    nwbfile.add_trial_column(name='min_reward_each_block', description=f'The minimum reward allowed for each block')
    # delay duration
    nwbfile.add_trial_column(name='delay_beta', description=f'The beta of exponential distribution to generate the delay duration(s)')
    nwbfile.add_trial_column(name='delay_min', description=f'The minimum duration(s) allowed for each delay')
    nwbfile.add_trial_column(name='delay_max', description=f'The maxmum duration(s) allowed for each delay')
    nwbfile.add_trial_column(name='delay_duration', description=f'The expected time duration between delay start and go cue start')
    # ITI duration
    nwbfile.add_trial_column(name='ITI_beta', description=f'The beta of exponential distribution to generate the ITI duration(s)')
    nwbfile.add_trial_column(name='ITI_min', description=f'The minimum duration(s) allowed for each ITI')
    nwbfile.add_trial_column(name='ITI_max', description=f'The maxmum duration(s) allowed for each ITI')
    nwbfile.add_trial_column(name='ITI_duration', description=f'The expected time duration between trial start and ITI start')
    # response duration
    nwbfile.add_trial_column(name='response_duration', description=f'The maximum time that the animal must make a choce in order to get a reward')
    # reward consumption duration
    nwbfile.add_trial_column(name='reward_consumption_duration', description=f'The duration for the animal to consume the reward')
    # reward delay
    nwbfile.add_trial_column(name='reward_delay', description=f'The delay between choice and reward delivery')
    # auto water
    nwbfile.add_trial_column(name='auto_waterL', description=f'Autowater given at Left')
    nwbfile.add_trial_column(name='auto_waterR', description=f'Autowater given at Right')
    # optogenetics
    nwbfile.add_trial_column(name='laser_on_trial', description=f'Trials with laser stimulation')
    nwbfile.add_trial_column(name='laser_wavelength', description=f'The wavelength of laser or LED')
    nwbfile.add_trial_column(name='laser_location', description=f'The target brain areas')
    nwbfile.add_trial_column(name='laser_1_power', description=f'The laser power of the laser 1(mw)')
    nwbfile.add_trial_column(name='laser_2_power', description=f'The laser power of the laser 2(mw)')
    nwbfile.add_trial_column(name='laser_on_probability', description=f'The laser on probability')
    nwbfile.add_trial_column(name='laser_duration', description=f'The laser duration')
    nwbfile.add_trial_column(name='laser_condition', description=f'The laser on is conditioned on LaserCondition')
    nwbfile.add_trial_column(name='laser_condition_probability', description=f'The laser on is conditioned on LaserCondition with a probability LaserConditionPro')
    nwbfile.add_trial_column(name='laser_start', description=f'Laser start is aligned to an event')
    nwbfile.add_trial_column(name='laser_start_offset', description=f'Laser start is aligned to an event with an offset')
    nwbfile.add_trial_column(name='laser_end', description=f'Laser end is aligned to an event')
    nwbfile.add_trial_column(name='laser_end_offset', description=f'Laser end is aligned to an event with an offset')
    nwbfile.add_trial_column(name='laser_protocol', description=f'The laser waveform')
    nwbfile.add_trial_column(name='laser_frequency', description=f'The laser waveform frequency')
    nwbfile.add_trial_column(name='laser_rampingdown', description=f'The ramping down time of the laser')
    nwbfile.add_trial_column(name='laser_pulse_duration', description=f'The pulse duration for Pulse protocol')
    nwbfile.add_trial_column(name='session_wide_control', description=f'Control the optogenetics session wide (e.g. only turn on opto in half of the session)')
    nwbfile.add_trial_column(name='fraction_of_session', description=f'Turn on/off opto in a fraction of the session (related to session_wide_control)')
    nwbfile.add_trial_column(name='session_start_with', description=f'The session start with opto on or off (related to session_wide_control)')
    nwbfile.add_trial_column(name='session_alternation', description=f'Turn on/off opto in every other session (related to session_wide_control)')
    nwbfile.add_trial_column(name='minimum_opto_interval', description=f'Minimum interval between two optogenetics trials (number of trials)')

    # auto training parameters
    nwbfile.add_trial_column(name='auto_train_engaged', description=f'Whether the auto training is engaged')
    nwbfile.add_trial_column(name='auto_train_curriculum_name', description=f'The name of the auto training curriculum')
    nwbfile.add_trial_column(name='auto_train_curriculum_version', description=f'The version of the auto training curriculum')
    nwbfile.add_trial_column(name='auto_train_curriculum_schema_version', description=f'The schema version of the auto training curriculum')
    nwbfile.add_trial_column(name='auto_train_stage', description=f'The current stage of auto training')
    nwbfile.add_trial_column(name='auto_train_stage_overridden', description=f'Whether the auto training stage is overridden')

    # determine lickspout keys based on stage position keys
    stage_positions = getattr(obj, 'B_StagePositions', [{}])
    nwbfile.add_trial_column(name='lickspout_position_x', description=f'x position (um) of the lickspout position (left-right)')
    nwbfile.add_trial_column(name='lickspout_position_z', description=f'z position (um) of the lickspout position (up-down)')
    if len(stage_positions) > 0 and list(stage_positions[0].keys()) == ['x', 'y1', 'y2', 'z']:   # aind stage
        nwbfile.add_trial_column(name='lickspout_position_y1',
                                 description=f'y position (um) of the left lickspout position (forward-backward)')
        nwbfile.add_trial_column(name='lickspout_position_y2',
                                 description=f'y position (um) of the right lickspout position (forward-backward)')
    else:
        nwbfile.add_trial_column(name='lickspout_position_y',
                                 description=f'y position (um) of the lickspout position (forward-backward)')
    # add reward size
    nwbfile.add_trial_column(name='reward_size_left', description=f'Left reward size (uL)')
    nwbfile.add_trial_column(name='reward_size_right', description=f'Right reward size (uL)')

    ## start adding trials ##
    # to see if we have harp timestamps
    if not hasattr(obj, 'B_TrialEndTimeHarp'):
        Harp = ''
    elif obj.B_TrialEndTimeHarp == []: # for json file transferred from mat data
        Harp = ''
    else:
        Harp = 'Harp'
    for i in range(len(obj.B_TrialEndTime)):
        Sc = obj.B_SelectedCondition[i] # the optogenetics conditions
        if Sc == 0:
            LaserWavelengthC = np.nan
            LaserLocationC = 'None'
            Laser1Power = np.nan
            Laser2Power = np.nan
            LaserOnProbablityC = np.nan
            LaserDurationC = np.nan
            LaserConditionC = 'None'
            LaserConditionProC = np.nan
            LaserStartC = 'None'
            LaserStartOffsetC = np.nan
            LaserEndC = 'None'
            LaserEndOffsetC = np.nan
            LaserProtocolC = 'None'
            LaserFrequencyC = np.nan
            LaserRampingDownC = np.nan
            LaserPulseDurC = np.nan

        else:
            laser_color=_get_field(obj, field_list=[f'TP_Laser_{Sc}',f'TP_LaserColor_{Sc}'],index=i)
            if laser_color == 'Blue':
                LaserWavelengthC = float(473)
            elif laser_color == 'Red':
                LaserWavelengthC = float(647)
            elif laser_color == 'Green':
                LaserWavelengthC = float(547)
            LaserLocationC = str(getattr(obj, f'TP_Location_{Sc}')[i])
            Laser1Power=float(eval(_get_field(obj, field_list=[f'TP_Laser1_power_{Sc}',f'TP_LaserPowerLeft_{Sc}'],index=i,default='[np.nan,np.nan]'))[1])
            Laser2Power=float(eval(_get_field(obj, field_list=[f'TP_Laser2_power_{Sc}',f'TP_LaserPowerRight_{Sc}'],index=i,default='[np.nan,np.nan]'))[1]) 
            LaserOnProbablityC = float(getattr(obj, f'TP_Probability_{Sc}')[i])
            LaserDurationC = float(getattr(obj, f'TP_Duration_{Sc}')[i])
            LaserConditionC = str(getattr(obj, f'TP_Condition_{Sc}')[i])
            LaserConditionProC = float(getattr(obj, f'TP_ConditionP_{Sc}')[i])
            LaserStartC = str(getattr(obj, f'TP_LaserStart_{Sc}')[i])
            LaserStartOffsetC = float(getattr(obj, f'TP_OffsetStart_{Sc}')[i])
            LaserEndC = str(getattr(obj, f'TP_LaserEnd_{Sc}')[i])
            LaserEndOffsetC = float(getattr(obj, f'TP_OffsetEnd_{Sc}')[i])
            LaserProtocolC = str(getattr(obj, f'TP_Protocol_{Sc}')[i])
            LaserFrequencyC = float(getattr(obj, f'TP_Frequency_{Sc}')[i])
            LaserRampingDownC = float(getattr(obj, f'TP_RD_{Sc}')[i])
            LaserPulseDurC = float(getattr(obj, f'TP_PulseDur_{Sc}')[i])
         
        if Harp == '':
            goCue_start_time_t = getattr(obj, f'B_GoCueTime')[i]  # Use CPU time
        else:
            if hasattr(obj, f'B_GoCueTimeHarp'):
                goCue_start_time_t = getattr(obj, f'B_GoCueTimeHarp')[i]  # Use Harp time, old format
            else:
                goCue_start_time_t = getattr(obj, f'B_GoCueTimeSoundCard')[i]  # Use Harp time, new format

        trial_kwargs = {
        'start_time' : getattr(obj, f'B_TrialStartTime{Harp}')[i],
        'stop_time' : getattr(obj, f'B_TrialEndTime{Harp}')[i],
        'animal_response' : obj.B_AnimalResponseHistory[i],
        'rewarded_historyL' : obj.B_RewardedHistory[0][i],
        'rewarded_historyR' : obj.B_RewardedHistory[1][i],
        'reward_outcome_time' : obj.B_RewardOutcomeTime[i],
        'delay_start_time' : _get_field(obj, f'B_DelayStartTime{Harp}', index=i, default=np.nan),
        'goCue_start_time' : goCue_start_time_t,
        'bait_left' : obj.B_BaitHistory[0][i],
        'bait_right' : obj.B_BaitHistory[1][i],
        'base_reward_probability_sum' : float(obj.TP_BaseRewardSum[i]),
        'reward_probabilityL' : float(obj.B_RewardProHistory[0][i]),
        'reward_probabilityR' : float(obj.B_RewardProHistory[1][i]),
        'reward_random_number_left' : _get_field(obj, 'B_CurrentRewardProbRandomNumber', index=i, default=[np.nan] * 2)[
                                        0],
        'reward_random_number_right' : _get_field(obj, 'B_CurrentRewardProbRandomNumber', index=i, default=[np.nan] * 2)[
                                         1],
        'left_valve_open_time' : float(obj.TP_LeftValue[i]),
        'right_valve_open_time' : float(obj.TP_RightValue[i]),
        'block_beta' : float(obj.TP_BlockBeta[i]),
        'block_min' : float(obj.TP_BlockMin[i]),
        'block_max' : float(obj.TP_BlockMax[i]),
        'min_reward_each_block' : float(obj.TP_BlockMinReward[i]),
        'delay_beta' : float(obj.TP_DelayBeta[i]),
        'delay_min' : float(obj.TP_DelayMin[i]),
        'delay_max' : float(obj.TP_DelayMax[i]),
        'delay_duration' : obj.B_DelayHistory[i],
        'ITI_beta' : float(obj.TP_ITIBeta[i]),
        'ITI_min' : float(obj.TP_ITIMin[i]),
        'ITI_max' : float(obj.TP_ITIMax[i]),
        'ITI_duration' : obj.B_ITIHistory[i],
        'response_duration' : float(obj.TP_ResponseTime[i]),
        'reward_consumption_duration' : float(obj.TP_RewardConsumeTime[i]),
        'reward_delay' : float(_get_field(obj, 'TP_RewardDelay', index=i, default=0)),
        'auto_waterL' : obj.B_AutoWaterTrial[0][i] if type(obj.B_AutoWaterTrial[0]) is list else obj.B_AutoWaterTrial[
            i],  # Back-compatible with old autowater format
        'auto_waterR' : obj.B_AutoWaterTrial[1][i] if type(obj.B_AutoWaterTrial[0]) is list else obj.B_AutoWaterTrial[i],
        # optogenetics
        'laser_on_trial' : obj.B_LaserOnTrial[i],
        'laser_wavelength' : LaserWavelengthC,
        'laser_location' : LaserLocationC,
        'laser_1_power' : Laser1Power,
        'laser_2_power' : Laser2Power,
        'laser_on_probability' : LaserOnProbablityC,
        'laser_duration' : LaserDurationC,
        'laser_condition' : LaserConditionC,
        'laser_condition_probability' : LaserConditionProC,
        'laser_start' : LaserStartC,
        'laser_start_offset' : LaserStartOffsetC,
        'laser_end' : LaserEndC,
        'laser_end_offset' : LaserEndOffsetC,
        'laser_protocol' : LaserProtocolC,
        'laser_frequency' : LaserFrequencyC,
        'laser_rampingdown' : LaserRampingDownC,
        'laser_pulse_duration' : LaserPulseDurC,

        'session_wide_control' : _get_field(obj, 'TP_SessionWideControl', index=i, default='None'),
        'fraction_of_session' : float(_get_field(obj, 'TP_FractionOfSession', index=i, default=np.nan)),
        'session_start_with' : _get_field(obj, 'TP_SessionStartWith', index=i, default='None'),
        'session_alternation' : _get_field(obj, 'TP_SessionAlternating', index=i, default='None'),
        'minimum_opto_interval' : float(_get_field(obj, 'TP_MinOptoInterval', index=i, default=0)),

        # add all auto training parameters (eventually should be in session.json)
        'auto_train_engaged' : _get_field(obj, 'TP_auto_train_engaged', index=i, default='None'),
        'auto_train_curriculum_name' : _get_field(obj, 'TP_auto_train_curriculum_name', index=i, default='None'),
        'auto_train_curriculum_version' : _get_field(obj, 'TP_auto_train_curriculum_version', index=i, default='None'),
        'auto_train_curriculum_schema_version' : _get_field(obj, 'TP_auto_train_curriculum_schema_version', index=i,
                                                          default='None'),
        'auto_train_stage' : _get_field(obj, 'TP_auto_train_stage', index=i, default='None'),
        'auto_train_stage_overridden' : _get_field(obj, 'TP_auto_train_stage_overridden', index=i, default=np.nan),

        # reward size
        'reward_size_left' : float(_get_field(obj, 'TP_LeftValue_volume', index=i)),
        'reward_size_right' : float(_get_field(obj, 'TP_RightValue_volume', index=i))
        }

        # populate lick spouts with correct format depending if using newscale or aind stage
        stage_positions = getattr(obj, 'B_StagePositions', [])  # If obj doesn't have attr, skip if since i !< len([])
        if i < len(stage_positions):    # index is valid for stage position lengths
            trial_kwargs['lickspout_position_x'] = stage_positions[i].get('x', np.nan)  # nan default if keys are wrong
            trial_kwargs['lickspout_position_z'] = stage_positions[i].get('z', np.nan)  # nan default if keys are wrong
            if list(stage_positions[i].keys()) == ['x', 'y1', 'y2', 'z']:    # aind stage
                trial_kwargs['lickspout_position_y1'] = stage_positions[i]['y1']
                trial_kwargs['lickspout_position_y2'] = stage_positions[i]['y2']
            else:       # newscale stage
                trial_kwargs['lickspout_position_y'] = stage_positions[i].get('y', np.nan) # nan default if keys are wrong
        else:   # if i not valid index, populate values with nan for x, y, z
            trial_kwargs['lickspout_position_x'] = np.nan
            trial_kwargs['lickspout_position_y'] = np.nan
            trial_kwargs['lickspout_position_z'] = np.nan

        nwbfile.add_trial(**trial_kwargs)


    #######  Other time series  #######
    #left/right lick time; give left/right reward time
    B_LeftRewardDeliveryTime=_get_field(obj, f'B_LeftRewardDeliveryTime{Harp}',default=[np.nan])
    B_RightRewardDeliveryTime=_get_field(obj, f'B_RightRewardDeliveryTime{Harp}',default=[np.nan])
    B_LeftLickTime=_get_field(obj, 'B_LeftLickTime',default=[np.nan])
    B_RightLickTime=_get_field(obj, 'B_RightLickTime',default=[np.nan])
    B_PhotometryFallingTimeHarp=_get_field(obj, 'B_PhotometryFallingTimeHarp',default=[np.nan])
    B_PhotometryRisingTimeHarp=_get_field(obj, 'B_PhotometryRisingTimeHarp',default=[np.nan])

    LeftRewardDeliveryTime = TimeSeries(
        name="left_reward_delivery_time",
        unit="second",
        timestamps=B_LeftRewardDeliveryTime,
        data=np.ones(len(B_LeftRewardDeliveryTime)).tolist(),
        description='The reward delivery time of the left lick port'
    )
    nwbfile.add_acquisition(LeftRewardDeliveryTime)

    RightRewardDeliveryTime = TimeSeries(
        name="right_reward_delivery_time",
        unit="second",
        timestamps=B_RightRewardDeliveryTime,
        data=np.ones(len(B_RightRewardDeliveryTime)).tolist(),
        description='The reward delivery time of the right lick port'
    )
    nwbfile.add_acquisition(RightRewardDeliveryTime)

    LeftLickTime = TimeSeries(
        name="left_lick_time",
        unit="second",
        timestamps=B_LeftLickTime,
        data=np.ones(len(B_LeftLickTime)).tolist(),
        description='The time of left licks'
    )
    nwbfile.add_acquisition(LeftLickTime)

    RightLickTime = TimeSeries(
        name="right_lick_time",
        unit="second",
        timestamps=B_RightLickTime,
        data=np.ones(len(B_RightLickTime)).tolist(),
        description='The time of left licks'
    )
    nwbfile.add_acquisition(RightLickTime)

    # Add photometry time stamps
    PhotometryFallingTimeHarp = TimeSeries(
        name="FIP_falling_time",
        unit="second",
        timestamps=B_PhotometryFallingTimeHarp,
        data=np.ones(len(B_PhotometryFallingTimeHarp)).tolist(),
        description='The time of photometry falling edge (from Harp)'
    )
    nwbfile.add_acquisition(PhotometryFallingTimeHarp)

    PhotometryRisingTimeHarp = TimeSeries(
        name="FIP_rising_time",
        unit="second",
        timestamps=B_PhotometryRisingTimeHarp,
        data=np.ones(len(B_PhotometryRisingTimeHarp)).tolist(),
        description='The time of photometry rising edge (from Harp)'
    )
    nwbfile.add_acquisition(PhotometryRisingTimeHarp)
    
    # Add optogenetics time stamps
    ''' 
    There are two sources of optogenetics time stamps depending on which event it is aligned to. 
    The first source is the optogenetics time stamps aligned to the trial start time (from the 
    DO0 stored in B_TrialStartTimeHarp), and the second source is the optogenetics time stamps aligned to other events 
    (e.g go cue and reward outcome; from the DO3 stored in B_OptogeneticsTimeHarp).
    '''
    start_time=np.array(_get_field(obj, f'B_TrialStartTime{Harp}', default=[np.nan]))
    LaserStart=[]
    for i in range(len(obj.B_TrialEndTime)):
        Sc = obj.B_SelectedCondition[i] # the optogenetics conditions
        if Sc == 0:
            LaserStart.append('None')
            continue
        LaserStart.append(str(getattr(obj, f'TP_LaserStart_{Sc}')[i]))
    OptogeneticsTimeHarp_ITI_Stimulation=start_time[np.array(LaserStart) == 'Trial start'].tolist()
    OptogeneticsTimeHarp_other=_get_field(obj, 'B_OptogeneticsTimeHarp',default=[np.nan])
    B_OptogeneticsTimeHarp=OptogeneticsTimeHarp_ITI_Stimulation+OptogeneticsTimeHarp_other
    B_OptogeneticsTimeHarp.sort()
    OptogeneticsTimeHarp = TimeSeries(
        name="optogenetics_time",
        unit="second",
        timestamps=B_OptogeneticsTimeHarp,
        data=np.ones(len(B_OptogeneticsTimeHarp)).tolist(),
        description='Optogenetics start time (from Harp)'
    )
    nwbfile.add_acquisition(OptogeneticsTimeHarp)

    # save NWB file
    base_filename = os.path.splitext(os.path.basename(fname))[0] + '.nwb'
    if len(nwbfile.trials) > 0:
        NWBName = os.path.join(save_folder, base_filename)
        io = NWBHDF5IO(NWBName, mode="w")
        io.write(nwbfile)
        io.close()
        logger.info(f'Successfully converted: {NWBName}')
        return 'success'
    else:
        logger.warning(f"No trials found! Skipping {fname}")
        return 'empty_trials'


def test_bonsai_json_to_nwb(test_json_urls):
    """Test preloaded json files from GitHub that cover many versions of our json files
    
    See this issue https://github.com/AllenNeuralDynamics/dynamic-foraging-task/issues/377
    Add new example json files to the issue and test_json_urls here to include them in the test.
    """
    import requests
    
    results = []
    os.makedirs('test_nwb', exist_ok=True)
    for json_url in test_json_urls:
        # Get json from GitHub link
        file_name = json_url.split('/')[-1].replace('.json', '')
        temp_json_name = f'test_nwb/test_{file_name}.json'
        r = requests.get(json_url, allow_redirects=True)
        open(temp_json_name, 'wb').write(r.content)
        
        # Try convert nwb and round-trip test
        try:
            result = bonsai_to_nwb(temp_json_name, 'test_nwb/')
            results.append(f'Converting {file_name} to nwb: {result}')
            
            # Try read the nwb file and show number of trials
            if result != 'empty_trials':
                temp_nwb_name = temp_json_name.replace("json", "nwb")
                io = NWBHDF5IO(temp_nwb_name, mode='r')
                nwbfile = io.read()
                results.append(f'   Reload nwb and get {len(nwbfile.trials)} trials!\n')
                io.close()
                print(temp_nwb_name)
                os.remove(temp_nwb_name)
        except Exception as e:
            results.append(f'{file_name} failed!!\n    {e}\n')
            
        os.remove(temp_json_name)
               
    # Clean up
    os.rmdir('test_nwb')
    logger.info('\n\n================= Test Results =================')
    logger.info('\n'.join(results))
    if 'failed' not in ''.join(results):
        logger.info('======= All tests passed! =======')
    else:
        logger.error('======= Some tests failed!! =======')


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    
    test_json_urls = [
        'https://github.com/AllenNeuralDynamics/dynamic-foraging-task/files/14936281/668551_2023-06-16.json',
        'https://github.com/AllenNeuralDynamics/dynamic-foraging-task/files/14936313/662914_2023-09-22.json',
        'https://github.com/AllenNeuralDynamics/dynamic-foraging-task/files/14936315/684039_2023-12-01_08-22-32.json',
        'https://github.com/AllenNeuralDynamics/dynamic-foraging-task/files/14936331/704151_2024-02-27_09-59-17.json',
        'https://github.com/AllenNeuralDynamics/dynamic-foraging-task/files/14936356/1_2024-04-06_16-31-06.json',
        'https://github.com/AllenNeuralDynamics/dynamic-foraging-task/files/14936359/706893_2024-04-09_14-27-56_ephys.json',
        r'https://github.com/user-attachments/files/18304002/746346_2025-01-02_10-16-10.json',  # https://github.com/AllenNeuralDynamics/dynamic-foraging-task/pull/1274
        r'https://github.com/user-attachments/files/18304087/746346_2024-12-02_13-16-12.json'  # Empty trials
    ]

    test_bonsai_json_to_nwb(test_json_urls)