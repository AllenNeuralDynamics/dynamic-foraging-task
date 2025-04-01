from aind_behavior_dynamic_foraging.DataSchemas.task_logic import AindDynamicForagingTaskParameters
from aind_behavior_services.session import AindBehaviorSessionModel

from aind_behavior_dynamic_foraging.DataSchemas.optogenetics import (
    Optogenetics,
)

from aind_behavior_dynamic_foraging.DataSchemas.fiber_photometry import FiberPhotometry
from aind_behavior_dynamic_foraging.DataSchemas.operation_control import OperationalControl


def task_parameters_to_tp_conversion(task_parameters: AindDynamicForagingTaskParameters) -> dict:
    """
    Map the AindDynamicForagingTaskParameters to previously foraging gui TP_ parameters
    :param task_parameters: task_parameters to map
    """

    return {
        'AddOneTrialForNoresponse': task_parameters.no_response_trial_addition,
        'AdvancedBlockAuto': True if task_parameters.auto_block is not None else False,
        'AutoReward': True if task_parameters.auto_water is not None else False,
        'auto_stop_ignore_ratio_threshold': task_parameters.auto_stop.ignore_ratio_threshold,
        'auto_stop_ignore_win': task_parameters.auto_stop.ignore_win,
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
        'min_time': task_parameters.auto_stop.min_time,
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
        'TP_auto_stop_ignore_ratio_threshold': task_parameters.auto_stop.ignore_ratio_threshold,
        'TP_auto_stop_ignore_win': task_parameters.auto_stop.ignore_win,
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
        'TP_min_time': task_parameters.auto_stop.min_time,
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
        'TP_warmup': True if task_parameters.warmup is not None else False,
        'UncoupledReward': task_parameters.uncoupled_reward,
        'Unrewarded': None if task_parameters.auto_water is None else task_parameters.auto_water.unrewarded,
        'WindowSize': task_parameters.auto_stop.ignore_win,
        'warm_max_choice_ratio_bias': None if task_parameters.warmup is None else task_parameters.warmup.max_choice_ratio_bias,
        'warm_min_finish_ratio': None if task_parameters.warmup is None else task_parameters.warmup.min_trial,
        'warm_min_trial': None if task_parameters.warmup is None else task_parameters.warmup.min_trial,
        'warm_windowsize': None if task_parameters.warmup is None else task_parameters.warmup.windowsize,
        'warmup': True if task_parameters.warmup is not None else False
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
        "FIPMode": fip_model.mode
    }


def opto_to_tp_conversion(opto_model: Optogenetics) -> dict:
    """
    Map the Optogenetics to previously foraging gui TP_ parameters
    :param opto_model: opto model to map
    """

    dictionary = {
        'TP_FractionOfSession': getattr(opto_model.session_control, "session_fraction", None),
        'TP_MinOptoInterval': opto_model.minimum_trial_interval,
        'TP_SampleFrequency': opto_model.sample_frequency,
        'TP_SessionAlternating': getattr(opto_model.session_control, "alternating_sessions", None),
        'TP_SessionStartWith': getattr(opto_model.session_control, "optogenetic_start", None),
        'TP_SessionWideControl': opto_model.session_control,
    }

    sort_map = ["LaserColorOne",
                "LaserColorTwo",
                "LaserColorThree",
                "LaserColorFour",
                "LaserColorFive",
                "LaserColorSix"]
    lasers = {k: None for k in sort_map}
    # fill gaps in laser dict
    lasers.update({laser.name: laser for laser in opto_model.laser_colors})

    for i in range(0, 6):
        laser_name = sort_map[i]
        if lasers[laser_name] is not None:
            dictionary[f'TP_ConditionP_{i+1}'] = lasers[laser_name].condition_probability
            dictionary[f'TP_Condition_{i+1}'] = getattr(lasers[laser_name], 'pulse_condition', None)
            dictionary[f'TP_Duration_{i+1}'] = lasers[laser_name].duration
            dictionary[f'TP_Frequency_{i+1}'] = getattr(lasers[laser_name].protocol, 'frequency', None)
            dictionary[f'TP_LaserColor_{i+1}'] = lasers[laser_name].color
            dictionary[f'TP_LaserEnd_{i+1}'] = getattr(lasers[laser_name].end, 'interval_condition', None) is None
            dictionary[f'TP_LaserStart_{i+1}'] = getattr(lasers[laser_name].start, 'interval_condition', None) is None
            dictionary[f'TP_OffsetEnd_{i+1}'] = getattr(lasers[laser_name].end, 'offset', None) is None
            dictionary[f'TP_OffsetStart_{i+1}'] = getattr(lasers[laser_name].start, 'offset', None) is None
            dictionary[f'TP_Probability_{i+1}'] = lasers[laser_name].probability
            dictionary[f'TP_Protocol_{i+1}'] = lasers[laser_name].protocol.name
            dictionary[f'TP_PulseDur_{i+1}'] = getattr(lasers[laser_name].protocol, 'duration', None)
            dictionary[f'TP_RD_{i+1}'] = getattr(lasers[laser_name].protocol, 'ramp_down', None)

            # map laser locations
            loc_map = ["LocationOne", "LocationTwo"]
            locs = {k: None for k in loc_map}
            locs.update({loc.name: loc for loc in lasers[laser_name].location})
            dictionary[f'TP_Laser1_power_{i+1}'] = None if locs["LocationOne"] is None else locs["LocationOne"].power
            dictionary[f'TP_Laser2_power_{i+1}'] = None if locs["LocationTwo"] is None else locs["LocationTwo"].power
            if locs["LocationOne"] is None:
                dictionary[f'TP_Location_{i+1}'] = "laser2"
            elif locs["LocationTwo"] is None:
                dictionary[f'TP_Location_{i+1}'] = "laser1"
            else:
                dictionary[f'TP_Location_{i+1}'] = "both"
        else:
            dictionary[f'TP_ConditionP_{i+1}'] = None
            dictionary[f'TP_Condition_{i+1}'] = None
            dictionary[f'TP_Duration_{i+1}'] = None
            dictionary[f'TP_Frequency_{i+1}'] = None
            dictionary[f'TP_LaserColor_{i+1}'] = None
            dictionary[f'TP_LaserEnd_{i+1}'] = None
            dictionary[f'TP_LaserStart_{i+1}'] = None
            dictionary[f'TP_OffsetEnd_{i+1}'] = None
            dictionary[f'TP_OffsetStart_{i+1}'] = None
            dictionary[f'TP_Probability_{i+1}'] = None
            dictionary[f'TP_Protocol_{i+1}'] = None
            dictionary[f'TP_PulseDur_{i+1}'] = None
            dictionary[f'TP_RD_{i+1}'] = None
            dictionary[f'TP_Laser1_power_{i+1}'] = None
            dictionary[f'TP_Laser2_power_{i+1}'] = None
            dictionary[f'TP_Location_{i+1}'] = None

    return dictionary

def operational_control_to_tp_conversion(operational_control: OperationalControl) -> dict:
    """
    Map the OperationalControl to previously foraging gui TP_ parameters
    :param operational_control: operational_control to map
    """

    return {
        'auto_stop_ignore_ratio_threshold': operational_control.auto_stop.ignore_ratio_threshold,
        'auto_stop_ignore_win': operational_control.auto_stop.ignore_win,
        'TP_auto_stop_ignore_ratio_threshold': operational_control.auto_stop.ignore_ratio_threshold,
        'TP_auto_stop_ignore_win': operational_control.auto_stop.ignore_win,
        'TP_MaxTime': operational_control.auto_stop.max_time,
        'TP_MaxTrial': operational_control.auto_stop.max_trial,
        'TP_min_time': operational_control.auto_stop.min_time,
        'TP_WindowSize': operational_control.auto_stop.ignore_win,
        'WindowSize': operational_control.auto_stop.ignore_win,
    }
