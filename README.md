# Dynamic Foraging Task
- [Dynamic Foraging Task](#dynamic-foraging-task)
- [Prerequisites](#prerequisites)
  - [Software](#software)
  - [Hardware](#hardware)
- [Deployment](#deployment)
  - [Bonsai](#bonsai)
  - [Python GUI](#python-gui)
- [Output JSON Format](#output-json-format)
- [Information Flow](#information-flow)
- [Usage of Python GUI](#usage-of-python-gui)
  - [Menu](#menu)
  - [Toolbars](#toolbars)
  - [Training Parameters](#training-parameters)
  - [Water Calibration](#water-calibration)
  - [Laser Calibration](#laser-calibration)
  - [Optogenetics](#optogenetics)
  - [Camera](#camera)
  - [Motor Stage](#motor-stage)

## Prerequisites
### Software
- Windows 10 or 11
- [ftdi driver](https://ftdichip.com/drivers/) (serial port drivers for HARP devices)
- [NI-DAQmax 19.0](https://www.ni.com/en/support/downloads/drivers/download.ni-daq-mx.html#484356) (for running optogenetics through NI-daq)
- [Spinnaker SDK version 1.29.0.5](https://www.flir.com/products/spinnaker-sdk/) (driver for FLIR camera)
- Python package:
  - numpy
  - scipy
  - matplotlib
  - PyQt5
  - pandas
  - [pyosc3](https://github.com/glopesdev/pyosc3.git@master)

### Hardware
- Harp behavior board
- Harp sound card
- Sound amplifier
- Harp synchronization board
  
## Deployment

### Bonsai

- Run **setup.cmd** in the **dynamic-foraging-task\bonsai** folder to install the bonsai and related packages (you only need to do it once).
- Run the foraging bonsai workflow in the folder **dynamic-foraging-task\src\workflows** to start Bonsai.

### Python GUI

- Run the **Foraging.py** in the folder **dynamic-foraging-task\src\foraging_gui** to start the GUI

## Information Flow

![image](https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/109394934/8b669d0d-c6aa-4abc-a41a-309ce6200fc0)


## Usage of Python GUI

### Menu

(Your content here)

### Toolbars

(Your content here)

### Training Parameters

(Your content here)

### Water Calibration

(Your content here)

### Laser Calibration

(Your content here)

### Optogenetics

(Your content here)

### Camera

(Your content here)

### Motor Stage

(Your content here)

## Output NWB Format
### Task structure
- **animal_response**:'The response of the animal. 0, left choice; 1, right choice; 2, no response'
- **rewarded_historyL**:'The reward history of left lick port'
- **rewarded_historyR**: 'The reward history of right lick port'
- **delay_start_time**: 'The delay start time'
- **goCue_start_time**: 'The go cue start time'
- **reward_outcome_time**: 'The reward outcome time (reward/no reward/no response)'
### Training paramters 
#### Behavior structure
- **bait_left**:'Whether the current left lickport has a bait or not'
- **bait_right**:'Whether the current right lickport has a bait or not'
- **base_reward_probability_sum**:'The summation of left and right reward probability'
- **reward_probabilityL**:'The reward probability of left lick port'
- **reward_probabilityR**:'The reward probability of right lick port'
- **left_valve_open_time**:'The left valve open time'
- **right_valve_open_time**:'The right valve open time'
#### Block
- **block_beta**:'The beta of exponential distribution to generate the block length'
- **block_min**:'The minimum length allowed for each block'
- **block_max**:'The maxmum length allowed for each block'
- **min_reward_each_block**:'The minimum reward allowed for each block'
#### Delay duration
- **delay_beta**:'The beta of exponential distribution to generate the delay duration(s)'
- **delay_min**:'The minimum duration(s) allowed for each delay'
- **delay_max**:'The maxmum duration(s) allowed for each delay'
- **delay_duration**:'The expected time duration between delay start and go cue start'
#### ITI duration
- **ITI_beta**:'The beta of exponential distribution to generate the ITI duration(s)'
- **ITI_min**:'The minimum duration(s) allowed for each ITI'
- **ITI_max**:'The maxmum duration(s) allowed for each ITI'
- **ITI_duration**:'The expected time duration between trial start and ITI start'
#### Response duration
- **response_duration**:'The maximum time that the animal must make a choce in order to get a reward'
#### Reward consumption duration
- **reward_consumption_duration**:'The duration for the animal to consume the reward'
#### Auto water
- **auto_water**:'Whether the current trial was a auto water trial or not'
#### Optogenetics
- **laser_on_trial**:'Trials with laser stimulation'
- **laser_wavelength**:'The wavelength of laser or LED'
- **laser_location**:'The target brain areas'
- **laser_power**:'The laser power(mw)'
- **laser_duration**:'The laser duration'
- **laser_condition**:'The laser on is conditioned on LaserCondition'
- **laser_condition_probability**:'The laser on is conditioned on LaserCondition with a probability LaserConditionPro'
- **laser_start**:'Laser start is aligned to an event'
- **laser_start_offset**:'Laser start is aligned to an event with an offset'
- **laser_end**:'Laser end is aligned to an event'
- **laser_end_offset**:'Laser end is aligned to an event with an offset'
- **laser_protocol**:'The laser waveform'
- **laser_frequency**:'The laser waveform frequency'
- **laser_rampingdown**:'The ramping down time of the laser'
- **laser_pulse_duration**:'The pulse duration for Pulse protocol'
#### Left/right lick time; give left/right reward time
- **B_LeftRewardDeliveryTime**:'The reward delivery time of the left lick port'
- **B_RightRewardDeliveryTime**:'The reward delivery time of the right lick port'
- **B_LeftLickTime**:'The time of left licks'
- **B_RightLickTime**:'The time of left licks'
