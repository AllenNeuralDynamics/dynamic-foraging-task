# Dynamic Foraging Task

A [Bonsai](https://bonsai-rx.org/) workflow for lick-based foraging experiments, with a [PyQt](https://wiki.python.org/moin/PyQt) frontend for visualizing performance and modifying task parameters.

## Table of contents
- [Prerequisites](#prerequisites)
  - [Operating System](#operating-system)
  - [Software](#software)
  - [Hardware](#hardware)
- [Deployment](#deployment)
- [Block Diagram](#block-diagram)
- [User Manual](#user-manual)
  - [Menu](#menu)
  - [Toolbars](#toolbars)
  - [Training Parameters](#training-parameters)
    - [Automatic training](#automatic-training)
  - [Water Calibration](#water-calibration)
  - [Laser Calibration](#laser-calibration)
  - [Optogenetics](#optogenetics)
  - [Camera](#camera)
  - [Visualization](#visualization)
  - [Motor Stage](#motor-stage)
- [Data Format](#data-format)
- [Developer Instructions](#developer-instructions)
  - [Add a widget](#add-a-widget)
  - [Create a dialogue](#create-a-dialogue)
  - [Add a new task](#add-a-new-task)

## Prerequisites
### Operating system
- Windows 10 or 11
### Software
> [!IMPORTANT]
> The exact versions of the NI-DAQ and Spinnaker libraries are needed for Bonsai package compatibility
- [FTDI driver](https://ftdichip.com/drivers/) (for Harp devices)
- [NI-DAQmax **version 19.0**](https://www.ni.com/en/support/downloads/drivers/download.ni-daq-mx.html#484356) (for optogenetic stimulation via NI-DAQ cards)
- [Spinnaker SDK **version 1.29.0.5**](https://www.flir.com/products/spinnaker-sdk/) (driver for FLIR cameras)
   - [download the driver here](https://alleninstitute-my.sharepoint.com/:u:/g/personal/xinxin_yin_alleninstitute_org/Ef8zZAeZymFFjuz_5T70xs8BV8Qmdd3zVCZ6gvdYAismYQ?e=9WvLlQ)
   - Install FULL, x64
- USBXpress SDK (for newscale python API)
  - [get installation .exe here](https://www.silabs.com/documents/public/software/install_USBXpress_SDK.exe) (for newscale python API)
  - Click install, accept terms of agreement, hit next and accept default settings for everything. 
- Python packages:
  - `numpy`
  - `scipy`
  - `matplotlib`
  - `PyQt5`
  - `pandas`
  - `pyserial`
  - [`pyosc3`](https://github.com/glopesdev/pyosc3.git@master)
  - [`newscale`](https://github.com/AllenNeuralDynamics/python-newscale@axes-on-target)
- [Qt designer](https://build-system.fman.io/qt-designer-download) (For GUI development only)
### Hardware
- [Harp Behavior Board](https://github.com/harp-tech/device.behavior)
- [Harp Sound Card](https://github.com/harp-tech/device.soundcard)
- [Harp Audio Amplifier](https://github.com/harp-tech/peripheral.audioamp)
- [Harp Synchronizer](https://github.com/harp-tech/device.synchronizer)
  
## Deployment

#### For initial installation:
- Clone repository onto your computer
  - The installation directory should be `C:\Users\svc_aind_behavior\Documents\GitHub\`
  - In the console: `git clone https://github.com/AllenNeuralDynamics/dynamic-foraging-task.git`
      - If you do not have git installed, use: https://gitforwindows.org
  - You can alternatively use the Github Desktop App to clone the repo
- Install Bonsai on your computer
  - In the console, change to the directory `C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task\bonsai`
  - install bonsai with: `./setup.cmd`
- Update the firmware of the Harp Behavior Board by following the instructions [here](https://harp-tech.org/articles/firmware.html).
- Install the USBXpress software, for the newscale motor stage
- Install the Spinnaker SDK, if a FLIR camera is being used
- Install the NI-DAQ max driver if a NiDAQ is present (for optogenetics)
- Create a `conda` environment, with python version 3.8
  - install `conda` [instructions here](https://docs.conda.io/projects/conda/en/latest/user-guide/install/windows.html)
  - Run `miniconda prompt`, and type `where conda`
  - Add conda to the path variable
    - [instructions from here](https://stackoverflow.com/questions/44515769/conda-is-not-recognized-as-internal-or-external-command)
    - Open Advanced System Settings
    - Click on "Environment Variables", then "Edit Path", then add the following paths:
      - C:\Users\svc_aind_behavior\AppData\Local\miniconda3
      - C:\Users\svc_aind_behavior\AppData\Local\miniconda3\Scripts
      - C:\Users\svc_aind_behavior\AppData\Local\miniconda3\Library\bin
      - C:\Users\svc_aind_behavior\AppData\Local\miniconda3\condabin
  - Create an environment: `conda create -n Foraging python=3.8`
  - Activate the environment: `conda activate Foraging`
- Use `pip` to install this repository:
  - From the `C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task` directory run `pip install -e .`
  - This should install all the required python packages. 
- Copy `Settings_box<box num>.csv` to `Users\svc_aind_behavior\Documents\ForagingSettings`
  - Copy `<box num>` 1-4 depending on the computer
  - Configure the Behavior/Soundcard COM ports for each computer
     - Unplug the USB cables for the Behavior and Soundcard boards for one of the two behavior boxes connected to each computer.
     - In a file browser, navigated to `C:\Users\svc_aind_behavior\Documents\GitHub\dynamic-foraging-task\bonsai`
     - Click on `Bonsai`, then `New Project`
     - In the Toolbox window type `Device (Harp)`
     - Select the Node, then in the properties window, iterate through the COM Ports and look in the console window, which will tell you which board is connected to which COM port.
     - Plug in the other behavior box's boards and repeat the steps. 
  - The BonsaiOsc ports are determined by the box number, and should not be modified. 
- Copy `Foraging<box num>.bat` to the Desktop
  - Copy `<box num>` 1-4 depending on the computer
- Configure `ForagingSettings.json`
  - Copy the template from `src\foraging_gui\ForagingSettings.json` to `Users\svc_aind_behavior\Documents\ForagingSettings\ForagingSettings.json`
  - You should not have to modify these settings:
    - "bonsai_path":"C:\\Users\\svc_aind_behavior\\Documents\\Github\\dynamic-foraging-task\\bonsai\\Bonsai.exe",
    - "bonsaiworkflow_path":"C:\\Users\\svc_aind_behavior\\Documents\\Github\\dynamic-foraging-task\\src\\workflows\\foraging.bonsai"
    - "default_saveFolder": "C:\\Documents\\"
    - "temporary_video_folder":"C:\\Users\\svc_aind_behavior\\Documents\\temporaryvideo\\",
    - "show_log_info_in_console":false (only used for debugging)
  - This field is mandatory and must be configured for each computer:
    - "current_box": For example "Tower_EphysRig3", "Blue"
  - These settings need to be configured for each computer:
    - "Teensy_COM": For example "COM10",
        - This is only for fiber-photometry  
        - Follow instructions on the [wiki](https://github.com/AllenNeuralDynamics/aind-behavior-blog/wiki/Computer-Configuration) to install Arduino IDE (1.8x) and TeensyDuino
        - Once both are installed open ArduinoIDE, go to Tools>Port, select COMport cooresponding to Teensy4.1, and this value to the ForagingSettings.json
    - "newscale_serial_num_tower1": For example 46103
    - "newscale_serial_num_tower2": For example 46104
    - "newscale_serial_num_tower3": For example 46105
    - "newscale_serial_num_tower4": For example 46106
        - Determine the serial numbers of the Newscale Stages
            - Unplug the stages for one of the two boxes
            - Open Miniconda Prompt
            - type `conda activate Foraging`
            - navigate to `dynamic-foraging-task/src/foraging)gui`
            - `python`
            - `from MyFunctions import NewScaleSerialY `
            - `serial_num = NewScaleSerialY.get_instances()[0]`
        - Edit `ForagingSettings.json` to add a line `"newscale_port_tower1":<serial number for rig 1>`
   - Create shortcut to the camera workflows 
- Create a log file folder at `~\Documents\foraging_gui_logs`

#### To launch the software:
- Run `foraging.bonsai` in `dynamic-foraging-task\src\workflows` to start Bonsai.
- Activate the `conda` environment created above
- Run `python dynamic-foraging-task\src\foraging_gui\Foraging.py` to start the GUI.
- The GUI will leave a log file at `~\Documents\foraging_gui_logs\` named by the tower and date/time. 

#### Automatic Updates
To configure automatic updates consistent with the [update protocol](https://github.com/AllenNeuralDynamics/aind-behavior-blog/wiki/Software-Update-Procedures),please use TaskScheduler to automatically run three batch files at specified times of the week ([instructions](https://github.com/AllenNeuralDynamics/aind-behavior-blog/wiki/Configure-Automatic-Updates))
- On every computer:
   - `\src\foraging_gui\update_from_github_to_main.bat` everyday at 6am
- On the testing computer:
   - `\src\foraging_gui\update_from_github_to_production_testing.bat` every monday at 6am
   - `\src\foraging_gui\check_github_status.bat` every tuesday at 6am
   - `\src\foraging_gui\update_from_github_to_main.bat` every W,Th,F,S,Su at 6am
- These batch files will leave a log file at `~\Documents\foraging_gui_logs\github_log.txt`

## Block Diagram
![image](https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/109394934/b8549072-5648-4afd-a508-8d38d7bf6549)

## User Manual
![GUI-screenshot](https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/e7b0dcc4-288c-4bf7-8fe2-80bfafa4d2a5)

### Menu

#### File
- **New**: Clear the training parameters 
- **Open**: Open an existing session and visualization
- **Save**: Save the current session as a JSON file (or optionally a .mat file)
- **Exit**: Close the GUI
- **Clear**: Clear the training parameters
- **Force Save**: Save the current session whether completed or not
#### Tools
- **Water calibration**: Open the water calibration dialogue
- **Laser calibration**: Open the laser calibration dialogue
- **Snipping**: Open the snipping tools
- **Simulation**: When one of the simulation methods is selected, it will run the simulation when the **Start** button is pressed.
  - **Win-stay lose-switch**: Foragers employ a win-stay-lose-switch strategy.
  - **Random**: Foragers randomly select a choice. 
#### Visualization
- **Lick distribution**: Open the lick analysis dialogue to display lick-related statistics.
- **Time distribution**: Display the simulated distribution of block length/ITI time/Delay time.
#### Control
- **Optogenetics**: Open the optogenetics dialogue
- **Camera**: Open the camera dialogue
- **Motor stage**: Open the New Scale stage dialogue to control the movement of lick spouts
- **Manipulator**: Open the New Scale stage to control the movement of probe
- **Connect bonsai**: Connect to Bonsai via OSC message
- **Start**: Start the GUI
- **New session**: Restart a session
- **Restart logging**:
  - **Temporary logging**: Logging to a temporary folder (determined by the **temporary_video_folder** in the **ForagingSettings.json** )
  - **Formal logging**: Logging to a standard folder structure (determined by the **default_saveFolder** in the **ForagingSettings.json** )
- **Open logging folder**: Open the current logging folder
- **Open behavior folder**: Open the folder to save the current behavior JSON file
#### Settings
- **Open setting folder**: Open the default settings folder. It is in `Documents\ForagingSettings` by default. There are different JSON files to save different default parameters.
  - **ForagingSettings.json**: General settings. 
    - **default_saveFolder**: The default save location. The folder structure is `default_saveFolder\Rig\Animal\Animal_year-month-day_hour-minute-second\`. There are five additional folders: `EphysFolder`, `HarpFolder`, `PhotometryFolder`, `TrainingFolder`, and `VideoFolder` for saving different data sources. Default location: `Documents`
    - **current_box**: To define the rig name.
    - **show_log_info_in_console**: If exists and equals `True`, a copy of log info is sent to the console.
  - **WaterCalibration.json**: The water calibration results.
  - **LaserCalibration.json**: The laser calibration results.
  - **TrainingStagePar.json**: The training stage parameters in a task-dependent manner.
#### Help

### Toolbars
(copy of some of the useful functions from the menu)
- **New**
- **Open**
- **Save**
- **Snipping**
- **Camera**
- **Motor stage**
- **Manipulator**
- **Water calibration**
- **Optogenetics**
- **Laser calibration**

### Training Parameters
#### Animal/task/tower information
- **Name**: The animal name used by individual users.
- **ID**: The animal ID.
- **Experimenter**: The experimenter running this session.
- **Task**: There are currently five tasks supported (**Coupled Baiting**;**Uncoupled Baiting**;**Coupled Without Baiting**;**Uncoupled Without Baiting**;**RewardN**).
- **Tower**: The current tower (can be set by **current_box** in **ForagingSettings.json**).
- **Auto Train**: Click the button to open the [Automatic Training](#automatic-training) dialog, see below
  
#### Automatic training
1. In the main dialog, press `Auto Train` button  <img src="https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/9ef26192-044b-4c22-928f-b328b7ab36ab" width="90"> or `Ctrl + Alt + A` to open the Automatic Training dialog.
2. For the first session of a new mouse:
   - Confirm that this is a new mouse<br>
   <img src="https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/bcaafe89-3330-4704-81f9-ab30c259512b" width="400"><br>
   - On the right side, select a desired curriculum for the new mouse. Double-check `curriculum_name`, `curriculum_version`, and the diagrams<br>.
   <img src="https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/2e3c030f-f91e-4917-9fa9-7e27af115171" width="700"><br>
   - Click buttons to see interative diagrams in browser <br><img src="https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/bb845129-a12b-445a-8639-0e981a60deb9" height="30">
   - Click `Set curriculum` button <img src="https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/f1fac3e0-1c84-42e9-9f12-ba11896845b8" width="60"> to confirm
   - Now a new entry with `session = 0` is added in `Training history`, and `STAGE_1` of the selected curriculum is suggested by default. <br>
   <img src="https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/90a054ab-71c1-4fa2-b13b-ab06f7895080" width="700"><br>
3. For a mouse that already started training
   - Its training history and curriculum is automatically loaded
   <br><img src="https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/58a9e583-09a4-4295-84eb-db5ef873df5d" width="900">
   - Uncheck `show this mouse only` to see training history from all mice
   <br><img src="https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/97c05425-7dac-426b-9ba2-aadcfc1868ed" height="30">
   - Press `Show all training history` <img src="https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/ff1354b6-4b78-4740-a317-b5ec1b83686e" height="30"> to open an interactive plotly chart that visualize all training history in browser
   <br><img src="https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/af541948-94ab-4f13-b599-ca188be77324" width="700">
4. Apply and lock training parameters
   - Check the curriculum name and stage name shown on the huge green button<br>
   <img src="https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/c46cd82e-76e7-4d7c-914e-41752937fee8" width="200"><br>
   - Press the button to apply and lock all curriculum-controlled training parameters in the main GUI (including the "Task").
   <br><img src="https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/27e72b0d-5317-47ba-ac16-7b22e7374cd7" width="900">
   - Note that you can still modify some items in `Training parameters`, such as `Valve open time`, `Give left/right`, and `Next block`.
   - You could now close the Auto Training dialog.
   - Start the training as usual.
     
6. Override parameters (not recommended)
   - Once `Apply and lock` is pressed, you can press it again to unlock the parameters and override any of them. But in this case, the automatic training mode is disengaged, and this session is considered "off-curriculum".
     
8. Override stage (not recommended)
   - Check `Override stage` to override the suggested stage. In the example below, `STAGE_FINAL` is suggested, but `STAGE_3` will be actually used (see the green button).
   <br><img src="https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/92fb9df7-3e54-4bf2-a86a-02c3808c554e" width="700">

10. Override curriculum (not recommended)
   - If you somehow decide to change the curriculum during training, press `Override curriculum` and set a new curriculum.
   - In this case, since all stages from the old curriculum now become "irrelevant", you should always manually select a stage in the ***new*** curriculum to override.
   <br><img src="https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/802e5208-dc5f-45f5-8ece-b9241157bf88" width="300">
   <br><img src="https://github.com/AllenNeuralDynamics/dynamic-foraging-task/assets/24734299/fba62a4b-acdb-49e9-a401-3a382607b0f3" width="700">


#### Trial-related parameters
- **training stage**: Select the training stage parameters. These parameters can be saved in **TrainingStagePar.json** through "**Save training**" button. They are task dependent. 
- **randomness**: There are **exponential** and **even distribution** available. This random generator will be applied to generate **Block length**/**ITI**/**Delay period**.
- **L(s)**: The left valve open time. The **L(s)** and **L(ul)** are dependent on each other, and the relationship is determined by the water calibration.
- **L(ul)**: The estimated water volume given by the left valve under the **L(s)**.
- **R(s)**: Similar to **L(s)**, but for right valve.
- **R(ul)**: Similar to **L(ul)**, but for left valve.
- **Give left**: Manually give water to the left valve
- **Give right**: Manually give water to the right valve
- **sum (base reward probability)**: The total reward probability.
- **family**: Currently, we use four reward families [[[8,1],[6, 1],[3, 1],[1, 1]],[[8, 1], [1, 1]],[[1,0],[.9,.1],[.8,.2],[.7,.3],[.6,.4],[.5,.5]],[[6, 1],[3, 1],[1, 1]]].
- **#of pairs**: Number of reward pairs you want to show under that family.
- **uncoupled reward**: Reward probabilities used by **Uncoupled Without Baiting** and **Uncoupled Baiting**. The reward probability of 0.1 cannot occur on both sides at the same time.
- **beta (Block)**: The beta used in the exponential distribution.
- **min (Block)**: Minimum block length permitted.
- **max (Block)**: Maximum block length permitted.
- **min reward each block**: Minimum reward allowed to transfer to the next block (The left and right blocks are independent under the uncoupled tasks).
- **include auto reward**: Include/exclude the auto reward when calculating the **min reward each block**.
- **RewardN**: The minimum reward amount to enter the next block under the **RewardN** task.
- **Initially inactive N**: A reward is available only when the animal chooses the side with the higher reward probability consecutively for **N** times (specific for **RewardN** task).
- **beta (delay)**: The beta used in the exponential distribution in the delay epoch. If the animal licks during the delay epoch, the delay will begin again.
- **min (delay)**: The minimum delay epoch time.
- **max (delay)**: The maximum delay epoch time.
- **beta (ITI)**: The beta used in the exponential distribution in the inter trial interval (ITI).
- **min (ITI)**: The minimum ITI time.
- **max (ITI)**: The maximum ITI time.
- **On (Auto water)**: If the auto water button is clicked, auto water will be given based on **type**, **multiplier**, and conditions (**unrewarded** and **ignored**).
- **type**: **Natural** - water will be given to sides with baited reward in the auto water trial. **High pro** - water will be given to the side with the higher probability. **Both** - water will be given to both sides.
- **multiplier**: Auto water volume is scaled by **multiplier**.
- **unrewarded**: It will be an auto water trial if unreward trials exceed **unrewarded**.
- **ignored**: It will be an auto water trial if ignored trials exceed **ignored**.
- **RT**: Response time. The animal can receive a reward only if it responds within the response time.
- **Reward consume time**: The extra time for the animal to consume the reward. If there is no reward, it will pause for the same duration once the outcome is determined.
- **stop ignores>**: The session will stop if the number of ignored trials surpasses the limit.
- **max trial**: The session will stop if the number of trials surpasses the limit.
- **max time (min)**: The session will stop if the running time of the session surpasses the limit.
- **auto (Advanced block)**: The block change will also be dependent on the choice of the animal when it is turned on. It's allowed to go to the next block only when there are consecutive points (**points in a row**) that cross the threshold (**switch thr**). 
- **switch thr**: The block switch threshold (only active after the auto is turned on). 
- **points in a row**: Consecutive points that cross the threshold (only active after the auto is turned on). 
- **Next block**: It will jump to the next block when it is clicked.
#### Weight and water
- **Weight before (g)**: Enter the mouse weight before starting training.
- **Weight after (g)**: Enter the mouse weight after training is completed.
- **Total water (ml)**: Total volume of water you plan to give the mouse (manually given reward and automatic reward are also included).
- **Suggested (ml)**: Suggested water to give the mouse after training (Based on **total water** and estimated water consumption from all sources in the session).
- **Extra water (ml)**: Enter the water given to the mouse after training.
#### Information
- **Current left block**: current trial number of the current left block/length of current left block.
- **Current right block**: current trial number of the current right block/length of current right block.
- **Responded trial**: number of responded trial/number of total trial. A trial is regarded as a responded trial if the animal licks one of the lick sprouts within the response time (**RT**).
- **Reward trial**: number of reward trials/number of total trial.
- **Total Reward**: Estimated total reward (excluding the manually given reward). 
- **Left choice rewarded**:
- **Right choice rewarded**:
- **Early licking**: Statistics of early licking rate in different behavior epochs.
- **Double dipping**: Double dipping statistics in different behavior epochs and conditions. 
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

## Data Format

Data for each session is saved as a JSON file with the following files:

### Task structure
- **animal_response**:'The response of the animal. 0, left choice; 1, right choice; 2, no response'
- **rewarded_historyL**:'The reward history of left lick sprout'
- **rewarded_historyR**: 'The reward history of right lick sprout'
- **delay_start_time**: 'The delay start time'
- **goCue_start_time**: 'The go cue start time'
- **reward_outcome_time**: 'The reward outcome time (reward/no reward/no response)'
### Training paramters 
#### Behavior structure
- **bait_left**:'Whether the current left licksprout has a bait or not'
- **bait_right**:'Whether the current right licksprout has a bait or not'
- **base_reward_probability_sum**:'The summation of left and right reward probability'
- **reward_probabilityL**:'The reward probability of left lick spout'
- **reward_probabilityR**:'The reward probability of right lick spout'
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
- **auto_water**:'Whether the current trial was an auto water trial or not'
#### Optogenetics
- **laser_on_trial**:'Trials with laser stimulation'
- **laser_wavelength**:'The wavelength of laser or LED'
- **laser_location**:'The target brain areas'
- **laser_power**:'The laser power (mW)'
- **laser_duration**:'The laser duration'
- **laser_condition**:'The laser on is conditioned on `LaserCondition`'
- **laser_condition_probability**:'The laser on is conditioned on `LaserCondition` with a probability `LaserConditionPro`'
- **laser_start**:'Laser start is aligned to an event'
- **laser_start_offset**:'Laser start is aligned to an event with an offset'
- **laser_end**:'Laser end is aligned to an event'
- **laser_end_offset**:'Laser end is aligned to an event with an offset'
- **laser_protocol**:'The laser waveform'
- **laser_frequency**:'The laser waveform frequency'
- **laser_rampingdown**:'The ramping down time of the laser'
- **laser_pulse_duration**:'The pulse duration for Pulse protocol'
#### Left/right lick time; give left/right reward time
- **B_LeftRewardDeliveryTime**:'The reward delivery time of the left lick spout'
- **B_RightRewardDeliveryTime**:'The reward delivery time of the right lick spout'
- **B_LeftLickTime**:'The time of left licks'
- **B_RightLickTime**:'The time of left licks'
  
## Developer Instructions
The user interface of the GUI was designed based on Qt-designer (introduction available [here](https://realpython.com/qt-designer-python/)).

### Update Protocol
- Please follow the update protocol [here](https://github.com/AllenNeuralDynamics/dynamic-foraging-task/wiki/Update-Procedures)

### Add a widget
- Widgets can be dragged directly into a window or dialog.
- Qt-designer will create a UI file, and then change the UI file to Python through the command **pyuic5 -o test.py test.ui**. Some useful commands can be found in `dynamic-foraging-task\src\foraging_gui\UI2Python.sh`.
- Define callbacks in Python to interact with the widget.

### Create a dialogue
- Create a dialogue window.
- Add widgets to the new dialogue.
- Transfer UI files to Python.
- Import the Python class generated from the UI file and then define callbacks to interact with the dialogue.

### Add a new task
If the new task structure is similar to the current foraging workflow, we can change the `dynamic-foraging-task\src\foraging_gui\MyFunctions\GenerateTrials` to add a new task. Otherwise, the Bonsai workflow will need to be updated as well.
