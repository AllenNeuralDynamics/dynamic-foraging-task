from aind_behavior_dynamic_foraging.DataSchemas.task_logic import AindDynamicForagingTaskParameters
from aind_behavior_services.session import AindBehaviorSessionModel

from aind_behavior_dynamic_foraging.DataSchemas.optogenetics import (
    Optogenetics,
    IntervalConditions,
    LaserColorOne,
    LaserColorTwo,
    LaserColorThree,
    LaserColorFour,
    LaserColorFive,
    LaserColorSix,
    SessionControl
)

from aind_behavior_dynamic_foraging.DataSchemas.fiber_photometry import FiberPhotometry



def task_parameters_to_tp_conversion(task_parameters: AindDynamicForagingTaskParameters) -> dict:
    """
    Map the AindDynamicForagingTaskParameters to previously foraging gui TP_ parameters
    :param task_parameters: task_parameters to map
    """

    return {
        'AddOneTrialForNoresponse': task_parameters.no_response_trial_addition,
        'AdvancedBlockAuto': True if task_parameters.auto_block is not None else False,
        'AutoReward': True if task_parameters.auto_water is not None else False,
        'AutoWaterType': None if task_parameters.auto_water is None else task_parameters.auto_water.auto_water_type,
        'BaseRewardSum': task_parameters.reward_probability.base_reward_sum,
        'BlockBeta': task_parameters.block_parameters.beta,
        'BlockMax': task_parameters.block_parameters.max,
        'BlockMin': task_parameters.block_parameters.min,
        'BlockMinReward': task_parameters.block_parameters.min_reward,
        'DelayBeta': task_parameters.delay_period.beta,
        'DelayMax': task_parameters.delay_period.max,
        'DelayMin': task_parameters.delay_period.min,
        'ITIBeta': task_parameters.inter_trial_interval.beta,
        'ITIIncrease': task_parameters.inter_trial_interval.increase,
        'ITIMax': task_parameters.inter_trial_interval.max,
        'ITIMin': task_parameters.inter_trial_interval.min,
        'Ignored': None if task_parameters.auto_water is None else task_parameters.auto_water.ignored,
        'IncludeAutoReward': None if task_parameters.auto_water is None else task_parameters.auto_water.include_reward,
        'InitiallyInactiveN': None if task_parameters.reward_n is None else task_parameters.reward_n.initial_inactive_trials,
        'LeftValue_volume': task_parameters.reward_size.left_value_volume,
        'MaxTime': task_parameters.auto_stop.max_time,
        'MaxTrial': task_parameters.auto_stop.max_trial,
        'Multiplier': None if task_parameters.auto_water is None else task_parameters.auto_water.multiplier,
        'PointsInARow': None if task_parameters.auto_block is None else task_parameters.auto_block.points_in_a_row,
        'Randomness': task_parameters.randomness,
        'ResponseTime': task_parameters.response_time.response_time,
        'RewardConsumeTime': task_parameters.response_time.reward_consume_time,
        'RewardDelay': task_parameters.reward_delay,
        'RewardFamily': task_parameters.reward_probability.family,
        'RewardPairsN': task_parameters.reward_probability.pairs_n,
        'RightValue_volume': task_parameters.reward_size.right_value_volume,
        'SwitchThr': None if task_parameters.auto_block is None else task_parameters.auto_block.switch_thr,
        'TP_AddOneTrialForNoresponse': task_parameters.no_response_trial_addition,
        'TP_AdvancedBlockAuto': True if task_parameters.auto_block is not None else False,
        'TP_AutoReward': True if task_parameters.auto_water is not None else False,
        'TP_AutoWaterType': None if task_parameters.auto_water is None else task_parameters.auto_water.auto_water_type,
        'TP_BaseRewardSum': task_parameters.reward_probability.base_reward_sum,
        'TP_BlockBeta': task_parameters.block_parameters.beta,
        'TP_BlockMax': task_parameters.block_parameters.max,
        'TP_BlockMin': task_parameters.block_parameters.min,
        'TP_BlockMinReward': task_parameters.block_parameters.min,
        'TP_DelayBeta': task_parameters.delay_period.beta,
        'TP_DelayMax': task_parameters.delay_period.max,
        'TP_DelayMin': task_parameters.delay_period.min,
        'TP_ITIBeta': task_parameters.inter_trial_interval.beta,
        'TP_ITIIncrease': task_parameters.inter_trial_interval.increase,
        'TP_ITIMax': task_parameters.inter_trial_interval.max,
        'TP_ITIMin': task_parameters.inter_trial_interval.min,
        'TP_Ignored': None if task_parameters.auto_water is None else task_parameters.auto_water.ignored,
        'TP_IncludeAutoReward': None if task_parameters.auto_water is None else task_parameters.auto_water.include_reward,
        'TP_InitiallyInactiveN': None if task_parameters.reward_n is None else task_parameters.reward_n.initial_inactive_trials,
        'TP_LeftValue_volume': task_parameters.reward_size.left_value_volume,
        'TP_MaxTime': task_parameters.auto_stop.max_time,
        'TP_MaxTrial': task_parameters.auto_stop.max_trial,
        'TP_Multiplier': None if task_parameters.auto_water is None else task_parameters.auto_water.multiplier,
        'TP_PointsInARow': None if task_parameters.auto_block is None else task_parameters.auto_block.points_in_a_row,
        'TP_Randomness': task_parameters.randomness,
        'TP_ResponseTime': task_parameters.response_time.response_time,
        'TP_RewardConsumeTime': task_parameters.response_time.reward_consume_time,
        'TP_RewardDelay': task_parameters.reward_delay,
        'TP_RewardFamily': task_parameters.reward_probability.family,
        'TP_RewardPairsN': task_parameters.reward_probability.pairs_n,
        'TP_RightValue_volume': task_parameters.reward_size.right_value_volume,
        'TP_SwitchThr': None if task_parameters.auto_block is None else task_parameters.auto_block.switch_thr,
        'TP_UncoupledReward': task_parameters.uncoupled_reward,
        'TP_Unrewarded': None if task_parameters.auto_water is None else task_parameters.auto_water.unrewarded,
        'TP_WindowSize': task_parameters.auto_stop.ignore_win,
        'TP_warm_max_choice_ratio_bias': None if task_parameters.warmup is None else task_parameters.warmup.max_choice_ratio_bias,
        'TP_warm_min_finish_ratio': None if task_parameters.warmup is None else task_parameters.warmup.min_finish_ratio,
        'TP_warm_min_trial': None if task_parameters.warmup is None else task_parameters.warmup.min_trial,
        'TP_warm_windowsize': None if task_parameters.warmup is None else task_parameters.warmup.windowsize,
        'TP_warmup': task_parameters.warmup,
        'UncoupledReward': task_parameters.uncoupled_reward,
        'Unrewarded': None if task_parameters.auto_water is None else task_parameters.auto_water.unrewarded,
        'WindowSize': task_parameters.auto_stop.ignore_win,
        'warm_max_choice_ratio_bias': None if task_parameters.warmup is None else task_parameters.warmup.max_choice_ratio_bias,
        'warm_min_finish_ratio': None if task_parameters.warmup is None else task_parameters.warmup.min_trial,
        'warm_min_trial': None if task_parameters.warmup is None else task_parameters.warmup.min_trial,
        'warm_windowsize': None if task_parameters.warmup is None else task_parameters.warmup.windowsize,
        'warmup': task_parameters.warmup
    }

def session_to_tp_conversion(session_model: AindBehaviorSessionModel) -> dict:
    """
    Map the AindBehaviorSessionModel to previously foraging gui TP_ parameters
    :param session_model: session model to map
    """

    return {
     'Experimenter': session_model.experimenter[0],
     'ID': session_model.subject,
     'ShowNotes': session_model.notes,
     'TP_Experimenter': session_model.experimenter[0],
     'TP_ID': session_model.subject,
     'TP_Task': session_model.experiment,
     'Task': session_model.experiment,
     }

def fip_to_tp_conversion(fip_model: FiberPhotometry) -> dict:
    """
    Map the FiberPhotometry to previously foraging gui TP_ parameters
    :param fip_model: fip model to map
    """

    return {
     'PhotometryB': False if fip_model.mode is None else True,
     'TP_FIPMode': fip_model.mode,
     'TP_PhotometryB': False if fip_model.mode is None else True,
     'TP_baselinetime': fip_model.baseline_time,
     'baselinetime': fip_model.baseline_time,
     'fiber_mode': fip_model.mode,
     }

def opto_to_tp_conversion(opto_model: Optogenetics) -> dict:
    """
    Map the Optogenetics to previously foraging gui TP_ parameters
    :param opto_model: opto model to map
    """

    sort_map = ["LaserColorOne",
                "LaserColorTwo",
                "LaserColorThree",
                "LaserColorFour",
                "LaserColorFive",
                "LaserColorSix"]
    lasers = {k: None for k in sort_map}
    # fill gaps in laser dict
    lasers.update({laser.name: laser for laser in opto_model.laser_colors})

    dictionary = {}

    for i in range(1, 6):
        laser_name = sort_map[i]
        dictionary[f'TP_ConditionP_{i}'] = lasers[laser_name]

    {
     'TP_ConditionP_1':,
     'TP_ConditionP_2',
     'TP_ConditionP_3',
     'TP_ConditionP_4',
     'TP_ConditionP_5',
     'TP_ConditionP_6',
     'TP_Condition_1',
     'TP_Condition_2',
     'TP_Condition_3',
     'TP_Condition_4',
     'TP_Condition_5',
     'TP_Condition_6',
     'TP_Duration_1',
     'TP_Duration_2',
     'TP_Duration_3',
     'TP_Duration_4',
     'TP_Duration_5',
     'TP_Duration_6',
     'TP_FractionOfSession',
     'TP_Frequency_1',
     'TP_Frequency_2',
     'TP_Frequency_3',
     'TP_Frequency_4',
     'TP_Frequency_5',
     'TP_Frequency_6',
     'TP_Laser1_power_1',
     'TP_Laser1_power_2',
     'TP_Laser1_power_3',
     'TP_Laser1_power_4',
     'TP_Laser1_power_5',
     'TP_Laser1_power_6',
     'TP_Laser2_power_1',
     'TP_Laser2_power_2',
     'TP_Laser2_power_3',
     'TP_Laser2_power_4',
     'TP_Laser2_power_5',
     'TP_Laser2_power_6',
     'TP_LaserColor_1',
     'TP_LaserColor_2',
     'TP_LaserColor_3',
     'TP_LaserColor_4',
     'TP_LaserColor_5',
     'TP_LaserColor_6',
     'TP_LaserEnd_1',
     'TP_LaserEnd_2',
     'TP_LaserEnd_3',
     'TP_LaserEnd_4',
     'TP_LaserEnd_5',
     'TP_LaserEnd_6',
     'TP_LaserStart_1',
     'TP_LaserStart_2',
     'TP_LaserStart_3',
     'TP_LaserStart_4',
     'TP_LaserStart_5',
     'TP_LaserStart_6',
     'TP_Laser_calibration',
     'TP_LatestCalibrationDate',
     'TP_Location_1',
     'TP_Location_2',
     'TP_Location_3',
     'TP_Location_4',
     'TP_Location_5',
     'TP_Location_6',
     'TP_MinOptoInterval',
     'TP_OffsetEnd_1',
     'TP_OffsetEnd_2',
     'TP_OffsetEnd_3',
     'TP_OffsetEnd_4',
     'TP_OffsetEnd_5',
     'TP_OffsetEnd_6',
     'TP_OffsetStart_1',
     'TP_OffsetStart_2',
     'TP_OffsetStart_3',
     'TP_OffsetStart_4',
     'TP_OffsetStart_5',
     'TP_OffsetStart_6',
     'TP_Probability_1',
     'TP_Probability_2',
     'TP_Probability_3',
     'TP_Probability_4',
     'TP_Probability_5',
     'TP_Probability_6',
     'TP_Protocol_1',
     'TP_Protocol_2',
     'TP_Protocol_3',
     'TP_Protocol_4',
     'TP_Protocol_5',
     'TP_Protocol_6',
     'TP_PulseDur_1',
     'TP_PulseDur_2',
     'TP_PulseDur_3',
     'TP_PulseDur_4',
     'TP_PulseDur_5',
     'TP_PulseDur_6',
     'TP_RD_1',
     'TP_RD_2',
     'TP_RD_3',
     'TP_RD_4',
     'TP_RD_5',
     'TP_RD_6',
     'TP_SampleFrequency',
     'TP_SessionAlternating',
     'TP_SessionStartWith',
     'TP_SessionWideControl',
     'TP_laser_1_calibration_power',
     'TP_laser_1_calibration_voltage',
     'TP_laser_1_target',
     'TP_laser_2_calibration_power',
     'TP_laser_2_calibration_voltage',
     'TP_laser_2_target',
     }