from aind_behavior_dynamic_foraging.DataSchemas.task_logic import AindDynamicForagingTaskParameters
from aind_behavior_services.session import AindBehaviorSessionModel

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

    {
     'Experimenter',
     'ID',
     'ShowNotes',
     'TP_Experimenter',
     'TP_ID',
     'TP_Task',
     'Task',
     }