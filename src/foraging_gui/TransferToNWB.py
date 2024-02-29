"""
Transfer current Json/mat format from Bonsai behavior control to NWB format
"""
from uuid import uuid4
import numpy as np, json,os,datetime
from pynwb import NWBHDF5IO, NWBFile, TimeSeries
from pynwb.file import Subject
from scipy.io import loadmat

save_folder=R'F:\Data_for_ingestion\Foraging_behavior\Bonsai\nwb'

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
    # Some fields are not provided in some cases
    if  not hasattr(obj, 'Experimenter'):
        setattr(obj, 'Experimenter', '')
    if  not hasattr(obj, 'ExtraWater'):
        setattr(obj, 'ExtraWater', '')
    if  not hasattr(obj, 'Other_CurrentTime'):
        setattr(obj, 'Other_CurrentTime', '')
    if  not hasattr(obj, 'WeightAfter'):
        setattr(obj, 'WeightAfter', '')
    if  not hasattr(obj, 'WeightBefore'):
        setattr(obj, 'WeightBefore', '')
    if  not hasattr(obj, 'Other_SessionStartTime'):
        session_start_timeC=datetime.datetime.strptime('2023-04-26', "%Y-%m-%d") # specific for LA30_2023-04-27.json
    else:
        session_start_timeC=datetime.datetime.strptime(obj.Other_SessionStartTime, '%Y-%m-%d %H:%M:%S.%f')

    ### session related information ###
    nwbfile = NWBFile(
        session_description='Session end time:'+obj.Other_CurrentTime+'  Give extra water(ml):'+obj.ExtraWater+'  box:'+obj.box,  
        identifier=str(uuid4()),  # required
        session_start_time= session_start_timeC,  # required
        session_id=os.path.basename(fname),  # optional
        experimenter=[
            obj.Experimenter,
        ],  # optional
        lab="",  # optional
        institution="Allen Institute for Neural Dynamics",  # optional
        ### add optogenetics description (the target brain areas). 
        experiment_description="Optogenetics target brain areas:",  # optional
        related_publications="",  # optional
        notes=obj.ShowNotes,
        protocol=obj.Task
    )

    #######  Animal information #######
    # need to get more subject information through subject_id
    nwbfile.subject = Subject(
        subject_id=obj.ID,
        description='Animal name:'+obj.ID+'  Weight after(g):'+obj.WeightAfter,
        species="Mus musculus",
        weight=obj.WeightBefore,
    )
    # print(nwbfile)

    #######       Add trial     #######
    ## behavior events (including trial start/end time; left/right lick time; give left/right reward time) ##
    nwbfile.add_trial_column(name='animal_response', description=f'The response of the animal. 0, left choice; 1, right choice; 2, no response')
    nwbfile.add_trial_column(name='rewarded_historyL', description=f'The reward history of left lick port')
    nwbfile.add_trial_column(name='rewarded_historyR', description=f'The reward history of right lick port')
    nwbfile.add_trial_column(name='delay_start_time', description=f'The delay start time')
    nwbfile.add_trial_column(name='goCue_start_time', description=f'The go cue start time')
    nwbfile.add_trial_column(name='reward_outcome_time', description=f'The reward outcome time (reward/no reward/no response)')
    ## training paramters ##
    # behavior structure
    nwbfile.add_trial_column(name='bait_left', description=f'Whether the current left lickport has a bait or not')
    nwbfile.add_trial_column(name='bait_right', description=f'Whether the current right lickport has a bait or not')
    nwbfile.add_trial_column(name='base_reward_probability_sum', description=f'The summation of left and right reward probability')
    nwbfile.add_trial_column(name='reward_probabilityL', description=f'The reward probability of left lick port')
    nwbfile.add_trial_column(name='reward_probabilityR', description=f'The reward probability of right lick port')
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
    # auto water
    nwbfile.add_trial_column(name='auto_waterL', description=f'Autowater given at Left')
    nwbfile.add_trial_column(name='auto_waterR', description=f'Autowater given at Right')
    # optogenetics
    nwbfile.add_trial_column(name='laser_on_trial', description=f'Trials with laser stimulation')
    nwbfile.add_trial_column(name='laser_wavelength', description=f'The wavelength of laser or LED')
    nwbfile.add_trial_column(name='laser_location', description=f'The target brain areas')
    nwbfile.add_trial_column(name='laser_power', description=f'The laser power(mw)')
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
    
    # auto training parameters
    nwbfile.add_trial_column(name='auto_train_engaged', description=f'Whether the auto training is engaged')
    nwbfile.add_trial_column(name='auto_train_curriculum_name', description=f'The name of the auto training curriculum')
    nwbfile.add_trial_column(name='auto_train_curriculum_version', description=f'The version of the auto training curriculum')
    nwbfile.add_trial_column(name='auto_train_curriculum_schema_version', description=f'The schema version of the auto training curriculum')
    nwbfile.add_trial_column(name='auto_train_stage', description=f'The current stage of auto training')
    nwbfile.add_trial_column(name='auto_train_stage_overridden', description=f'Whether the auto training stage is overridden')
    
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
            LaserWavelengthC = 0
            LaserLocationC = 0
            LaserPowerC = 0
            LaserDurationC = 0
            LaserConditionC = 0
            LaserConditionProC = 0
            LaserStartC = 0
            LaserStartOffsetC = 0
            LaserEndC = 0
            LaserEndOffsetC = 0
            LaserProtocolC = 0
            LaserFrequencyC = 0
            LaserRampingDownC = 0
            LaserPulseDurC = 0
        else:
            # if there is no training paramters history stored (for old Bonsai behavior control)
            if not hasattr(obj, 'TP_Laser_1'):
                if getattr(obj, f'TP_Laser_{Sc}')[i] == 'Blue':
                    LaserWavelengthC = 473
                elif getattr(obj, f'TP_Laser_{Sc}')[i] == 'Red':
                    LaserWavelengthC = 647
                elif getattr(obj, f'TP_Laser_{Sc}')[i] == 'Green':
                    LaserWavelengthC = 547
                LaserLocationC = getattr(obj, f'TP_Location_{Sc}')[i]
                LaserPowerC = getattr(obj, f'TP_LaserPower_{Sc}')[i]
                LaserDurationC = getattr(obj, f'TP_Duration_{Sc}')[i]
                LaserConditionC = getattr(obj, f'TP_Condition_{Sc}')[i]
                LaserConditionProC = getattr(obj, f'TP_ConditionP_{Sc}')[i]
                LaserStartC = getattr(obj, f'TP_LaserStart_{Sc}')[i]
                LaserStartOffsetC = getattr(obj, f'TP_OffsetStart_{Sc}')[i]
                LaserEndC = getattr(obj, f'TP_LaserEnd_{Sc}')[i]
                LaserEndOffsetC = getattr(obj, f'TP_OffsetEnd_{Sc}')[i]
                LaserProtocolC = getattr(obj, f'TP_Protocol_{Sc}')[i]
                LaserFrequencyC = getattr(obj, f'TP_Frequency_{Sc}')[i]
                LaserRampingDownC = getattr(obj, f'TP_RD_{Sc}')[i]
                LaserPulseDurC = getattr(obj, f'TP_PulseDur_{Sc}')[i]
         
        if Harp == '':
            goCue_start_time_t = getattr(obj, f'B_GoCueTime')[i]  # Use CPU time
        else:
            if hasattr(obj, f'B_GoCueTimeHarp'):
                goCue_start_time_t = getattr(obj, f'B_GoCueTimeHarp')[i]  # Use Harp time, old format
            else:
                goCue_start_time_t = getattr(obj, f'B_GoCueTimeSoundCard')[i]  # Use Harp time, new format
            
        nwbfile.add_trial(start_time=getattr(obj, f'B_TrialStartTime{Harp}')[i], 
                          stop_time=getattr(obj, f'B_TrialEndTime{Harp}')[i],
                          animal_response=obj.B_AnimalResponseHistory[i],
                          rewarded_historyL=obj.B_RewardedHistory[0][i],
                          rewarded_historyR=obj.B_RewardedHistory[1][i],
                          reward_outcome_time=obj.B_RewardOutcomeTime[i],
                          delay_start_time=getattr(obj, f'B_DelayStartTime{Harp}')[i],
                          goCue_start_time=goCue_start_time_t,
                          bait_left=obj.B_BaitHistory[0][i],
                          bait_right=obj.B_BaitHistory[1][i],
                          base_reward_probability_sum=float(obj.TP_BaseRewardSum[i]),
                          reward_probabilityL=float(obj.B_RewardProHistory[0][i]),
                          reward_probabilityR=float(obj.B_RewardProHistory[1][i]),
                          left_valve_open_time=float(obj.TP_LeftValue[i]),
                          right_valve_open_time=float(obj.TP_RightValue[i]),
                          block_beta=float(obj.TP_BlockBeta[i]),
                          block_min=float(obj.TP_BlockMin[i]),
                          block_max=float(obj.TP_BlockMax[i]),
                          min_reward_each_block=float(obj.TP_BlockMinReward[i]),
                          delay_beta=float(obj.TP_DelayBeta[i]),
                          delay_min=float(obj.TP_DelayMin[i]),
                          delay_max=float(obj.TP_DelayMax[i]),
                          delay_duration=obj.B_DelayHistory[i],
                          ITI_beta=float(obj.TP_ITIBeta[i]),
                          ITI_min=float(obj.TP_ITIMin[i]),
                          ITI_max=float(obj.TP_ITIMax[i]),
                          ITI_duration=obj.B_ITIHistory[i],
                          response_duration=float(obj.TP_ResponseTime[i]),
                          reward_consumption_duration=float(obj.TP_RewardConsumeTime[i]),
                          auto_waterL=obj.B_AutoWaterTrial[0][i] if type(obj.B_AutoWaterTrial[0]) is list else obj.B_AutoWaterTrial[i],   # Back-compatible with old autowater format
                          auto_waterR=obj.B_AutoWaterTrial[1][i] if type(obj.B_AutoWaterTrial[0]) is list else obj.B_AutoWaterTrial[i],
                          laser_on_trial=obj.B_LaserOnTrial[i],
                          laser_wavelength=LaserWavelengthC,
                          laser_location=LaserLocationC,
                          laser_power=LaserPowerC,
                          laser_duration=LaserDurationC,
                          laser_condition=LaserConditionC,
                          laser_condition_probability=LaserConditionProC,
                          laser_start=LaserStartC,
                          laser_start_offset=LaserStartOffsetC,
                          laser_end=LaserEndC,
                          laser_end_offset=LaserEndOffsetC,
                          laser_protocol=LaserProtocolC,
                          laser_frequency=LaserFrequencyC,
                          laser_rampingdown=LaserRampingDownC,
                          laser_pulse_duration=LaserPulseDurC,

                          # add all auto training parameters (eventually should be in session.json)
                          auto_train_engaged=obj.TP_auto_train_engaged[i],
                          auto_train_curriculum_name=obj.TP_auto_train_curriculum_name[i] or 'none',
                          auto_train_curriculum_version=obj.TP_auto_train_curriculum_version[i] or 'none',
                          auto_train_curriculum_schema_version=obj.TP_auto_train_curriculum_schema_version[i] or 'none',
                          auto_train_stage=obj.TP_auto_train_stage[i] or 'none',
                          auto_train_stage_overridden=obj.TP_auto_train_stage_overridden[i] or np.nan,
                        )


    #######  Other time series  #######
    #left/right lick time; give left/right reward time
    if getattr(obj, f'B_LeftRewardDeliveryTime{Harp}') == []:
        B_LeftRewardDeliveryTime = [np.nan]
    else:
        B_LeftRewardDeliveryTime = getattr(obj, f'B_LeftRewardDeliveryTime{Harp}')
    if getattr(obj, f'B_RightRewardDeliveryTime{Harp}') == []:
        B_RightRewardDeliveryTime = [np.nan]
    else:
        B_RightRewardDeliveryTime = getattr(obj, f'B_RightRewardDeliveryTime{Harp}')
    if obj.B_LeftLickTime == []:
        B_LeftLickTime = [np.nan]
    else:
        B_LeftLickTime = obj.B_LeftLickTime
    if obj.B_RightLickTime == []:
        B_RightLickTime = [np.nan]
    else:
        B_RightLickTime = obj.B_RightLickTime

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
    if not hasattr(obj, 'B_PhotometryFallingTimeHarp') or obj.B_PhotometryFallingTimeHarp == []:
        B_PhotometryFallingTimeHarp = [np.nan]
    else:
        B_PhotometryFallingTimeHarp = obj.B_PhotometryFallingTimeHarp
    PhotometryFallingTimeHarp = TimeSeries(
        name="FIP_falling_time",
        unit="second",
        timestamps=B_PhotometryFallingTimeHarp,
        data=np.ones(len(B_PhotometryFallingTimeHarp)).tolist(),
        description='The time of photometry falling edge (from Harp)'
    )
    nwbfile.add_acquisition(PhotometryFallingTimeHarp)

    if not hasattr(obj, 'B_PhotometryRisingTimeHarp') or obj.B_PhotometryRisingTimeHarp == []:
        B_PhotometryRisingTimeHarp = [np.nan]
    else:
        B_PhotometryRisingTimeHarp = obj.B_PhotometryRisingTimeHarp
    PhotometryRisingTimeHarp = TimeSeries(
        name="FIP_rising_time",
        unit="second",
        timestamps=B_PhotometryRisingTimeHarp,
        data=np.ones(len(B_PhotometryRisingTimeHarp)).tolist(),
        description='The time of photometry rising edge (from Harp)'
    )
    nwbfile.add_acquisition(PhotometryRisingTimeHarp)


    # save NWB file
    base_filename = os.path.splitext(os.path.basename(fname))[0] + '.nwb'
    NWBName = os.path.join(save_folder, base_filename)
    io = NWBHDF5IO(NWBName, mode="w")
    io.write(nwbfile)
    io.close()


if __name__ == '__main__':
    bonsai_to_nwb(R'F:\Data_for_ingestion\Foraging_behavior\Bonsai\AIND-447-3-A\704151\704151_2024-02-27_09-59-17\TrainingFolder\704151_2024-02-27_09-59-17.json')
