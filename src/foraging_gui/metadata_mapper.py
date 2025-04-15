import ast
from datetime import datetime
from aind_behavior_dynamic_foraging.DataSchemas.task_logic import (
    AindDynamicForagingTaskParameters,
    AindDynamicForagingTaskLogic,
    BlockParameters,
    RewardProbability,
    DelayPeriod,
    AutoWater,
    InterTrialInterval,
    ResponseTime,
    AutoBlock,
    RewardSize,
    Warmup,
    RewardN
)
from aind_behavior_services.session import AindBehaviorSessionModel

from aind_behavior_dynamic_foraging.DataSchemas.optogenetics import (
    Optogenetics,
    LaserColorOne,
    LaserColorTwo,
    LaserColorThree,
    LaserColorFour,
    LaserColorFive,
    LaserColorSix,
    LocationOne,
    LocationTwo,
    IntervalConditions,
    SineProtocol,
    PulseProtocol,
    ConstantProtocol,
    SessionControl
)

from aind_behavior_dynamic_foraging.DataSchemas.fiber_photometry import FiberPhotometry
from aind_behavior_dynamic_foraging.DataSchemas.operation_control import OperationalControl, AutoStop, StageSpecs


def task_parameters_to_tp_conversion(task_parameters: AindDynamicForagingTaskParameters) -> dict:
    """
    Map the AindDynamicForagingTaskParameters to previously foraging gui TP_ parameters
    :param task_parameters: task_parameters to map
    """

    return {
        'AddOneTrialForNoresponse': task_parameters.no_response_trial_addition,
        'AdvancedBlockAuto': task_parameters.auto_block if task_parameters.auto_block is not None else "off",
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
        'TP_AdvancedBlockAuto': task_parameters.auto_block if task_parameters.auto_block is not None else "off",
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
        'TP_warm_max_choice_ratio_bias': None if task_parameters.warmup is None else task_parameters.warmup.max_choice_ratio_bias,
        'TP_warm_min_finish_ratio': None if task_parameters.warmup is None else task_parameters.warmup.min_finish_ratio,
        'TP_warm_min_trial': None if task_parameters.warmup is None else task_parameters.warmup.min_trial,
        'TP_warm_windowsize': None if task_parameters.warmup is None else task_parameters.warmup.windowsize,
        'TP_warmup': True if task_parameters.warmup is not None else False,
        'UncoupledReward': task_parameters.uncoupled_reward,
        'Unrewarded': None if task_parameters.auto_water is None else task_parameters.auto_water.unrewarded,
        'warm_max_choice_ratio_bias': None if task_parameters.warmup is None else task_parameters.warmup.max_choice_ratio_bias,
        'warm_min_finish_ratio': None if task_parameters.warmup is None else task_parameters.warmup.min_trial,
        'warm_min_trial': None if task_parameters.warmup is None else task_parameters.warmup.min_trial,
        'warm_windowsize': None if task_parameters.warmup is None else task_parameters.warmup.windowsize,
        'warmup': True if task_parameters.warmup is not None else False
    }


def behavior_json_to_task_logic_model(behavior_json: dict) -> AindDynamicForagingTaskLogic:
    """
        Map behavior.json to task_logic model.

        :param behavior_json: dictionary of behavior json
    """

    # parse through json and grab last value
    behavior = {k: v[-1] for k, v in behavior_json.items() if type(v) == list and len(v) != 0}

    return AindDynamicForagingTaskLogic(
        block_parameters=BlockParameters(
            min=0 if behavior["TP_BlockMinReward"] == "" else float(behavior["TP_BlockMinReward"]),
            max=0 if behavior["TP_BlockMaxReward"] else float(behavior["TP_BlockMaxReward"]),
            beta=0 if behavior["TP_BlockBetaReward"] else float(behavior["TP_BlockBetaReward"])),
        reward_probability=RewardProbability(
            base_reward_sum=0 if behavior["TP_BaseRewardSum"] else float(behavior["TP_BaseRewardSum"]),
            family=0 if behavior["TP_RewardFamily"] else float(behavior["TP_RewardFamily"]),
            pairs_n=0 if behavior["TP_RewardPairsN"] else float(behavior["TP_RewardPairsN"])),
        uncoupled_reward=None if behavior["TP_UncoupledReward"][-1] == "" else ast.literal_eval(
            behavior["TP_UncoupledReward"]),
        randomness=0 if behavior["TP_Randomness"] else float(behavior["TP_Randomness"]),
        delay_period=DelayPeriod(
            min=0 if behavior["TP_DelayMin"] else float(behavior["TP_DelayMin"]),
            max=0 if behavior["TP_DelayMax"] else float(behavior["TP_DelayMax"]),
            beta=0 if behavior["TP_DelayBeta"] else float(behavior["TP_DelayBeta"])
        ),
        reward_delay=0 if behavior["TP_RewardDelay"] == "" else float(behavior["TP_RewardDelay"]),
        auto_water=None if not behavior["TP_AutoReward"] else AutoWater(
            auto_water_type=behavior["TP_AutoWaterType"],
            multiplier=0 if behavior["TP_Multiplier"] == "" else float(behavior["TP_Multiplier"]),
            unrewarded=0 if behavior["TP_Unrewarded"] == "" else float(behavior["TP_Unrewarded"]),
            ignored=0 if behavior["TP_Ignored"] == "" else float(behavior["TP_Ignored"]),
            include_reward=0 if behavior["TP_IncludeAutoReward"] == "" else float(behavior["TP_IncludeAutoReward"])
        ),
        inter_trial_interval=InterTrialInterval(min=0 if behavior["TP_ITIMin"] == "" else float(behavior["TP_ITIMin"]),
                                                max=0 if behavior["TP_ITIMax"] == "" else float(behavior["TP_ITIMax"]),
                                                beta=0 if behavior["TP_ITIBeta"] == "" else float(
                                                    behavior["TP_ITIBeta"]),
                                                increase=0 if behavior["TP_ITIIncrease"] == "" else float(
                                                    behavior["TP_ITIIncrease"])),
        response_time=ResponseTime(
            response_time=0 if behavior["TP_ResponseTime"] == "" else float(behavior["TP_ResponseTime"]),
            reward_consume_time=0 if behavior["TP_RewardConsumeTime"] == "" else float(behavior["TP_RewardConsumeTime"])

        ),
        auto_block=None if behavior["TP_AdvancedBlockAuto"] else AutoBlock(
            advanced_block_auto=behavior["TP_AdvancedBlockAuto"],
            switch_thr=0 if behavior["TP_SwitchThr"] == "" else float(behavior["TP_SwitchThr"]),
            points_in_a_row=0 if behavior["TP_PointsInARow"] == "" else float(behavior["TP_PointsInARow"])
        ),
        warmup=None if not behavior["TP_warmup"] else Warmup(
            min_trial=0 if behavior["TP_warm_min_trial"] == "" else float(behavior["TP_warm_min_trial"]),
            max_choice_ratio_bias=0 if behavior["warm_max_choice_ratio_bias"] == "" else float(
                behavior["warm_max_choice_ratio_bias"]),
            min_finish_ratio=0 if behavior["TP_warm_min_finish_ratio"] == "" else float(
                behavior["TP_warm_min_finish_ratio"]),
            windowsize=0 if behavior["TP_warm_windowsize"] == "" else float(behavior["TP_warm_windowsize"])
        ),
        reward_size=RewardSize(
            right_value_volume=0 if behavior["TP_RightValue_volume"] == "" else float(behavior["TP_RightValue_volume"]),
            left_value_volume=0 if behavior["TP_LeftValue_volume"] == "" else float(behavior["TP_LeftValue_volume"])
        ),

        no_response_trial_addition=behavior["TP_AddOneTrialForNoresponse"],
        reward_n=None if behavior["TP_Task"] != "RewardN" else RewardN(
            initial_inactive_trials=0 if behavior["TP_InitiallyInactiveN"] == "" else float(
                behavior["TP_InitiallyInactiveN"])
        )
    )


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


def behavior_json_to_session_model(behavior_json: dict) -> AindBehaviorSessionModel:
    """
        Map behavior.json to session model.

        :param behavior_json: dictionary of behavior json
    """

    # parse through json and grab last value
    behavior = {k: v[-1] for k, v in behavior_json.items() if type(v) == list and len(v) != 0}

    return AindBehaviorSessionModel(
        experiment=behavior["TP_Task"],
        experimenter=[behavior["TP_Experimenter"]],
        date=datetime.strptime(behavior_json["Other_SessionStartTime"], "%Y-%m-%d %H:%M:%S.%f"),
        root_path=behavior_json["SessionFolder"],
        session_name=behavior_json["SessionFolder"].split("\\")[-1],
        subject=behavior["TP_ID"],
        experiment_version=behavior_json["version"],
        notes=behavior_json["ShowNotes"],
        commit_hash=behavior_json["commit_ID"],
        allow_dirty_repo=not behavior_json["repo_dirty_flag"],
        skip_hardware_validation=True
    )


def fip_to_tp_conversion(fip_model: FiberPhotometry) -> dict:
    """
    Map the FiberPhotometry to previously foraging gui TP_ parameters
    :param fip_model: fip model to map
    """

    return {
        'PhotometryB': fip_model.enabled,
        'TP_FIPMode': fip_model.mode,
        'TP_PhotometryB': fip_model.enabled,
        'TP_baselinetime': fip_model.baseline_time,
        'baselinetime': fip_model.baseline_time,
        'fiber_mode': fip_model.mode,
        "FIPMode": fip_model.mode
    }


def behavior_json_to_fip_model(behavior_json: dict) -> FiberPhotometry:
    """
        Map behavior.json to fip model.

        :param behavior_json: dictionary of behavior json
    """

    # parse through json and grab last value
    behavior = {k: v[-1] for k, v in behavior_json.items() if type(v) == list and len(v) != 0}

    return FiberPhotometry(
        enabled=behavior["TP_PhotometryB"],
        mode=behavior["TP_FIPMode"],
        baseline_time=behavior["TP_baselinetime"]
    )


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
        'TP_SessionWideControl': False if opto_model.session_control is None else True,
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
            dictionary[f'TP_ConditionP_{i + 1}'] = lasers[laser_name].condition_probability
            dictionary[f'TP_Condition_{i + 1}'] = getattr(lasers[laser_name], 'pulse_condition', None)
            dictionary[f'TP_Duration_{i + 1}'] = lasers[laser_name].duration
            dictionary[f'TP_Frequency_{i + 1}'] = getattr(lasers[laser_name].protocol, 'frequency', None)
            dictionary[f'TP_LaserColor_{i + 1}'] = lasers[laser_name].color
            dictionary[f'TP_LaserEnd_{i + 1}'] = getattr(lasers[laser_name].end, 'interval_condition', None) is None
            dictionary[f'TP_LaserStart_{i + 1}'] = getattr(lasers[laser_name].start, 'interval_condition', None) is None
            dictionary[f'TP_OffsetEnd_{i + 1}'] = getattr(lasers[laser_name].end, 'offset', None) is None
            dictionary[f'TP_OffsetStart_{i + 1}'] = getattr(lasers[laser_name].start, 'offset', None) is None
            dictionary[f'TP_Probability_{i + 1}'] = lasers[laser_name].probability
            dictionary[f'TP_Protocol_{i + 1}'] = lasers[laser_name].protocol.name
            dictionary[f'TP_PulseDur_{i + 1}'] = getattr(lasers[laser_name].protocol, 'duration', None)
            dictionary[f'TP_RD_{i + 1}'] = getattr(lasers[laser_name].protocol, 'ramp_down', None)

            # map laser locations
            loc_map = ["LocationOne", "LocationTwo"]
            locs = {k: None for k in loc_map}
            locs.update({loc.name: loc for loc in lasers[laser_name].location})
            dictionary[f'TP_Laser1_power_{i + 1}'] = None if locs["LocationOne"] is None else locs["LocationOne"].power
            dictionary[f'TP_Laser2_power_{i + 1}'] = None if locs["LocationTwo"] is None else locs["LocationTwo"].power
            if locs["LocationOne"] is None:
                dictionary[f'TP_Location_{i + 1}'] = "laser2"
            elif locs["LocationTwo"] is None:
                dictionary[f'TP_Location_{i + 1}'] = "laser1"
            else:
                dictionary[f'TP_Location_{i + 1}'] = "both"
        else:
            dictionary[f'TP_ConditionP_{i + 1}'] = None
            dictionary[f'TP_Condition_{i + 1}'] = None
            dictionary[f'TP_Duration_{i + 1}'] = None
            dictionary[f'TP_Frequency_{i + 1}'] = None
            dictionary[f'TP_LaserColor_{i + 1}'] = None
            dictionary[f'TP_LaserEnd_{i + 1}'] = None
            dictionary[f'TP_LaserStart_{i + 1}'] = None
            dictionary[f'TP_OffsetEnd_{i + 1}'] = None
            dictionary[f'TP_OffsetStart_{i + 1}'] = None
            dictionary[f'TP_Probability_{i + 1}'] = None
            dictionary[f'TP_Protocol_{i + 1}'] = None
            dictionary[f'TP_PulseDur_{i + 1}'] = None
            dictionary[f'TP_RD_{i + 1}'] = None
            dictionary[f'TP_Laser1_power_{i + 1}'] = None
            dictionary[f'TP_Laser2_power_{i + 1}'] = None
            dictionary[f'TP_Location_{i + 1}'] = None

    return dictionary


def behavior_json_to_opto_model(behavior_json: dict) -> Optogenetics:
    """
        Map behavior.json to opto model.

        :param behavior_json: dictionary of behavior json
    """

    # parse through json and grab last value
    behavior = {k: v[-1] for k, v in behavior_json.items() if type(v) == list and len(v) != 0}

    sort_map = [LaserColorOne,
                LaserColorTwo,
                LaserColorThree,
                LaserColorFour,
                LaserColorFive,
                LaserColorSix]

    lasers = []

    for i in range(0, 6):
        if behavior[f"TP_LaserColor_{i + 1}"] != "NA":

            location = [LocationOne(), LocationTwo()]
            if behavior[f"TP_Location_{i + 1}"] == "Laser_1":
                location = location[:1]
            elif behavior[f"TP_Location_{i + 1}"] == "Laser_2":
                location = location[1:]

            if behavior[f"TP_Protocol_{i + 1}"] == "Sine":
                protocol = SineProtocol(
                    frequency=behavior[f"TP_Frequency_{i + 1}"],
                    ramp_down=behavior[f"TP_RD_{i + 1}"]
                )
            elif behavior[f"TP_Protocol_{i + 1}"] == "Pulse":
                protocol = PulseProtocol(
                    frequency=behavior[f"TP_Frequency_{i + 1}"],
                    duration=behavior[f'TP_PulseDur_{i + 1}']
                )
            else:
                protocol = ConstantProtocol(
                    ramp_down=behavior[f"TP_RD_{i + 1}"]
                )

            lasers.append(sort_map[i](
                color=behavior[f"TP_LaserColor_{i + 1}"],
                location=location,
                probability=float(behavior[f"TP_Probability_{i + 1}"]),
                duration=float(behavior[f"TP_Duration_{i + 1}"]),
                pulse_condition=behavior[f"TP_Condition_{i + 1}"],
                condition_probability=behavior[f"TP_ConditionP_{i + 1}"],
                start=IntervalConditions(
                    interval_condition=behavior[f"TP_LaserStart_{i + 1}"],
                    offset=behavior[f"TP_OffsetStart_{i + 1}"]
                ),
                end=IntervalConditions(
                    interval_condition=behavior[f"TP_LaserEnd_{i + 1}"],
                    offset=behavior[f"TP_OffsetEnd_{i + 1}"]
                ),
                protocol=protocol
            ))

    return Optogenetics(
        laser_colors=lasers,
        session_control=None if not behavior["TP_SessionWideControl"] else SessionControl(
            session_fraction=behavior["TP_FractionOfSession"],
            optogenetic_start=behavior["TP_SessionStartWith"],
            alternating_sessions=behavior["TP_SessionAlternating"],
        ),
        minimum_trial_interval=behavior["TP_MinOptoInterval"],
        sample_frequency=behavior["TP_SampleFrequency"]
    )


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


def behavior_json_to_operational_control_model(behavior_json: dict) -> OperationalControl:
    """
        Map behavior.json to operational control model.

        :param behavior_json: dictionary of behavior json
    """

    # parse through json and grab last value
    behavior = {k: v[-1] for k, v in behavior_json.items() if type(v) == list and len(v) != 0}

    return OperationalControl(
        auto_stop=AutoStop(
            ignore_win=behavior["TP_auto_stop_ignore_win"],
            ignore_ratio_threshold=behavior["TP_auto_stop_ignore_ratio_threshold"],
            max_trial=behavior["TP_MaxTrial"],
            max_time=behavior["TP_MaxTime"],
            min_time=behavior["TP_min_time"],
        ),
        stage_specs=None if behavior["B_StagePositions"] is None else StageSpecs(
            stage_name="newscale" if list(behavior["B_StagePositions"].keys()) == ["x", "y", "z"] else "AIND",
            rig_name=behavior_json["Other_current_box"],
            x=behavior["B_StagePositions"]["x"],
            y=behavior["B_StagePositions"]["y"] or behavior["B_StagePositions"]["y1"],
            z=behavior["B_StagePositions"]["z"],
        )
    )
