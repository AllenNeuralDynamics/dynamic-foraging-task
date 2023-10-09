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

## Output JSON Format

(Your content here)
