from pydantic import Field, BaseModel, field_validator
from typing import Dict
import logging
from enum import Enum
from typing_extensions import TypedDict


RANDOMNESSES = ['Exponential', 'Even']

class AdvancedBlockMode(str, Enum):
    """ Modes for advanced block """
    OFF = "off"
    NOW = "now"
    ONCE = "once"

class AutoWaterModes(str, Enum):
    """ Modes for auto water """
    NATURAL = "Natural"
    BOTH = "Both"
    HIGH_PRO = "High pro"

class RewardProbability(BaseModel):
    sum: float = Field(default=.8, ge=0, le=1, title="Sum of p_reward")
    family: int = Field(default=1, title="Reward family")
    pairs: int = Field(default=1, title="Number of pairs")

class Block(BaseModel):
    min: int = Field(default=20, title="Block length (min)")
    max: int = Field(default=60, title="Block length (max)")
    beta: int = Field(default=20, title="Block length (beta)")
    min_reward: int = Field(default=1, title="Minimal rewards in a block to switch")

class Delay(BaseModel):
    min_s: float = Field(default=1, title="Delay period (min) ")
    max_s: float = Field(default=8, title="Delay period (max) ")
    beta_s:  float = Field(default=1, title="Delay period (beta)")
    reward_s: int = Field(default=0, title="Reward delay (sec)")

class AutoWater(BaseModel):
    autoReward: bool = Field(default=False, title="Auto reward switch")
    autoWaterType: AutoWaterModes = Field(default=AutoWaterModes.NATURAL, title="Auto water mode")
    multiplier: float = Field(default=0.8, title="Multiplier for auto reward")
    unrewarded: int = Field(default=200, title="Number of unrewarded trials before auto water")
    ignored: int = Field(default=100, title="Number of ignored trials before auto water")

class ITI_Parameters(BaseModel):
    min: float = Field(default=0.0, title="ITI (min)")
    max: float = Field(default=0.0, title="ITI (max)")
    beta: float = Field(default=0.0, title="ITI (beta)")
    increase: float = Field(default=0.0, title="ITI increase")

class AutoStop(BaseModel):
    ignore_window: int = Field(default=30, description="Trial window in which to monitor ignored trials")
    ignore_ratio: float = Field(default=0.8, description="Percent of ignored licks in window to trigger auto-stop")
    max_time: float = Field(default=120, title="Maximal session time (min)")
    min_time: float = Field(default=30, title="Minimum session time (min)")
    max_trial: int = Field(..., title="Maximal number of trials")

class AutoBlock(BaseModel):
    advanced_block_auto: AdvancedBlockMode = Field(default=AdvancedBlockMode.OFF, title="Auto block mode")
    switch_thr: float = Field(default=0.5, title="Switch threshold for auto block")
    points_in_a_row: int = Field(default=5, title="Points in a row for auto block")

class RewardSize(BaseModel):
    right_volume: float = Field(default=3.00, title="Right reward size (uL)")
    left_volume: float = Field(default=3.00, title="Left reward size (uL)")

class Warmup(BaseModel):
    warmup: bool = Field(default=False, title="Warmup master switch")
    min_trial: int = Field(default=50, title="Warmup finish criteria: minimal trials")
    max_choice_ratio_bias: float = Field(default=0.1, title="Warmup finish criteria: maximal choice ratio bias from 0.5")
    min_finish_ratio: float = Field(default=0.8, title="Warmup finish criteria: minimal finish ratio")
    window_size: int = Field(default=20, title="Warmup finish criteria: window size to compute the bias and ratio")

class Coupled(BaseModel):
    """
    Training schema for the dynamic foraging
    """

    reward_probability: RewardProbability = Field(default=RewardProbability().dict())
    randomness: str = Field('Exponential', title="Randomness mode")  # Exponential by default
    block: Block = Field(default=Block().dict())
    delay: Delay = Field(default=Delay().dict())
    auto_water: AutoWater = Field(default=AutoWater().dict())
    ITI: ITI_Parameters = Field(default=ITI_Parameters().dict())
    response_time_s: float = Field(default=1, title="Response time")
    reward_consume_time_s: float = Field(default=3, title="Reward consume time", description="Time of the no-lick period before trial end")
    auto_block: AutoBlock = Field(default=AutoBlock().dict())
    reward_size: RewardSize = Field(default=RewardSize().dict())
    warmup: Warmup = Field(default=Warmup().dict())
    # UncoupledReward: str = Field("0.1,0.3,0.7", title="Uncoupled reward")  # For uncoupled tasks only



