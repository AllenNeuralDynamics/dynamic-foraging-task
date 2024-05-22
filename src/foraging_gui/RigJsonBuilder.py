import os
import json
import logging
import numpy as np
from deepdiff import DeepDiff
from datetime import date, datetime, timezone

import aind_data_schema.core.rig as r
import aind_data_schema.components.devices as d
from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.units import SizeUnit

from foraging_gui.Visualization import GetWaterCalibration


def build_rig_json(existing_rig_json, settings, water_calibration, laser_calibration):    

    # Build the new rig schema
    rig = build_rig_json_core(settings, water_calibration, laser_calibration)

    # Compare with existing rig schema
    # Write the new rig schema to a json file and load it back 
    # I do this to ignore serialization issues when comparing the rig.jsons 
    suffix = '_temp.json'
    rig.write_standard_file(suffix=suffix, output_directory=settings['rig_metadata_folder']) 
    new_rig_json_path = os.path.join(settings['rig_metadata_folder'],'rig_temp.json')
    with open(new_rig_json_path, 'r') as f:
        new_rig_json = json.load(f)

    # Compare the two rig.jsons
    differences = DeepDiff(existing_rig_json, new_rig_json,ignore_order=True)

    # Remove the modification date, since that doesnt matter for comparison purposes
    values_to_ignore = ['modification_date','rig_id']
    for value in values_to_ignore:
        if ('values_changed' in differences) and ("root['{}']".format(value) in differences['values_changed']):
            differences['values_changed'].pop("root['{}']".format(value))
            if len(differences['values_changed']) == 0:
                differences.pop('values_changed')

    # Determine which schema to use
    if len(differences) > 0:
        # If any differences remain, rename the temp file
        logging.info('differences with existing rig json: {}'.format(differences))
        # Write to file 
        time_str = datetime.now().strftime('%Y-%m-%d_%H_%M_%S')
        filename = 'rig_{}_{}.json'.format(settings['rig_name'],time_str )
        final_path = os.path.join(settings['rig_metadata_folder'],filename)
        os.rename(new_rig_json_path, final_path)
        logging.info('Saving new rig json: {}'.format(filename))
    else:
        # Delete temp file
        os.remove(new_rig_json_path)
        logging.info('Using existing rig json')


def build_rig_json_core(settings, water_calibration, laser_calibration):

    # Set up
    ###########################################################################
    logging.info('building rig json')

    # Build dictionary of components
    components = {}

    # Determine what extra components are present using settings files
    FIB = settings['Teensy_COM_box{}'.format(settings['box_number'])] != ''
    OPTO = ('HasOpto' in settings['box_settings']) and (settings['box_settings']['HasOpto'] == "1")
    HIGH_SPEED_CAMERA = ('HighSpeedCamera' in settings['box_settings']) and (settings['box_settings']['HighSpeedCamera'] == "1")
    RIGHT_CAMERA = ('HasSideCameraRight' in settings['box_settings']) and (settings['box_settings']['HasSideCameraRight'] == "1")
    BOTTOM_CAMERA = ('HasBottomCamera' in settings['box_settings']) and (settings['box_settings']['HasBottomCamera'] == "1")


    # Modalities
    ###########################################################################
    # Opto is not a modality, its a stimulus
    components['modalities'] = [Modality.BEHAVIOR, Modality.BEHAVIOR_VIDEOS]
    if FIB:
        components['modalities'].append(Modality.FIB)


    # Cameras 
    ###########################################################################
    if HIGH_SPEED_CAMERA:
        components['cameras']=[]
        if RIGHT_CAMERA:
            components['cameras'].append(
                d.CameraAssembly(
                    name="Right Camera assembly",
                    camera_target=d.CameraTarget.FACE_SIDE_RIGHT,
                    lens=d.Lens( 
                        name="Behavior Video Lens Right Side",
                        manufacturer=d.Organization.FUJINON,
                        focal_length=16,
                        focal_length_unit=SizeUnit.MM,
                        model="CF16ZA-1S",
                        ),
                    camera=d.Camera(
                        name = "Right size of face camera",
                        detector_type="Camera",
                        manufacturer=d.Organization.FLIR,
                        data_interface="USB",
                        computer_name=settings['computer_name'],
                        chroma="Monochrome",
                        cooling="Air", 
                        sensor_format="1/2.9",
                        sensor_format_unit=SizeUnit.IN,
                        sensor_width=720,
                        sensor_height=540,
                        max_frame_rate=522,
                        model="Blackfly S BFS-U3-04S2M",
                        serial_number=settings['box_settings']['SideCameraRight'],
                    )
                )
            )
        if BOTTOM_CAMERA:
            components['cameras'].append(
                d.CameraAssembly(
                    name="Bottom Camera assembly",
                    camera_target=d.CameraTarget.FACE_BOTTOM,
                    lens=d.Lens(
                        name="Behavior Video Lens Bottom of face", 
                        manufacturer=d.Organization.OTHER,
                        focal_length=25,
                        focal_length_unit=SizeUnit.MM,
                        model="LM25HC",
                        notes='Manufacturer is Kowa'
                        ), 
                    camera=d.Camera(
                        name="bottom of face camera",
                        computer_name=settings['computer_name'],
                        detector_type="Camera",
                        manufacturer=d.Organization.FLIR,
                        data_interface="USB",
                        chroma="Monochrome",
                        cooling="Air", 
                        sensor_format="1/2.9",
                        sensor_format_unit=SizeUnit.IN,
                        sensor_width=720,
                        sensor_height=540,
                        max_frame_rate=522,
                        model="Blackfly S BFS-U3-04S2M",
                        serial_number=settings['box_settings']['BottomCamera'],
                    )
                )
            )
    else:
        components['cameras']=[
            d.CameraAssembly(
                name="BehaviorVideography_FaceSide",
                camera_target=d.CameraTarget.FACE_SIDE_RIGHT,
                camera=d.Camera(
                    name="Side face camera",
                    detector_type="Camera",
                    manufacturer=d.Organization.AILIPU,
                    model="ELP-USBFHD05MT-KL170IR",
                    notes="The light intensity sensor was removed; IR illumination is constantly on",
                    data_interface="USB",
                    computer_name=settings['computer_name'],
                    max_frame_rate=120,
                    sensor_width=640,
                    sensor_height=480,
                    chroma="Color",
                    cooling="Air",
                    bin_mode="Additive",
                    recording_software=d.Software(name="Bonsai", version=settings['bonsai_version']),
                ),
                lens=d.Lens(
                    name="Xenocam 1",
                    model="XC0922LENS",
                    manufacturer=d.Organization.OTHER,
                    max_aperture="f/1.4",
                    notes='Focal Length 9-22mm 1/3" IR F1.4',
                ),
            ),
            d.CameraAssembly(
                name="BehaviorVideography_FaceBottom",
                camera_target=d.CameraTarget.FACE_BOTTOM,
                camera=d.Camera(
                    name="Bottom face Camera",
                    detector_type="Camera",
                    manufacturer=d.Organization.AILIPU,
                    model="ELP-USBFHD05MT-KL170IR",
                    notes="The light intensity sensor was removed; IR illumination is constantly on",
                    data_interface="USB",
                    computer_name=settings['computer_name'],
                    max_frame_rate=120,
                    sensor_width=640,
                    sensor_height=480,
                    chroma="Color",
                    cooling="Air",
                    bin_mode="Additive",
                    recording_software=d.Software(name="Bonsai", version=settings['bonsai_version']),
                ),
                lens=d.Lens(
                    name="Xenocam 2",
                    model="XC0922LENS",
                    manufacturer=d.Organization.OTHER,
                    max_aperture="f/1.4",
                    notes='Focal Length 9-22mm 1/3" IR F1.4',
                ),
            ),
        ]

    components['light_sources'] = [
             d.LightEmittingDiode(
                name="IR LED",
                manufacturer=d.Organization.THORLABS,
                model="M810L5",
                wavelength=810,
            )
        ]


    # Mouse Platform
    ###########################################################################
    components['mouse_platform']=d.Tube(
        name="mouse_tube_foraging", 
        diameter=3.0,
        diameter_unit=SizeUnit.CM
        )


    # Stimulus devices
    ###########################################################################
    if settings['newscale_serial_num_box{}'.format(settings['box_number'])] != '':
        stage = d.MotorizedStage(
                    name="NewScaleMotor for LickSpouts",
                    serial_number=settings['newscale_serial_num_box{}'.format(settings['box_number'])], 
                    manufacturer=d.Organization.NEW_SCALE_TECHNOLOGIES,
                    travel=15.0,
                    travel_unit=SizeUnit.MM,
                    firmware="https://github.com/AllenNeuralDynamics/python-newscale, branch: axes-on-target, commit #7c17497",
                    )
    else:
        stage = d.MotorizedStage(
                    name="AIND lick spout stage",
                    manufacturer=d.Organization.AIND,
                    travel=30, 
                    travel_unit=SizeUnit.MM
                    )      

    if ('AINDLickDetector' in settings['box_settings']) and (settings['box_settings']['AINDLickDetector'] == "1"):
        lick_spout_name = 'AIND_Lick_Detector'
    else:
        lick_spout_name = 'Janelia_Lick_Detector'
    lick_spouts=[
        d.RewardSpout(
            name="{} Left".format(lick_spout_name),
            side=d.SpoutSide.LEFT,
            spout_diameter=1.2,
            solenoid_valve=d.Device(device_type="Solenoid", name="Solenoid Left"),
            lick_sensor_type=d.LickSensorType("Capacitive")
        ),
        d.RewardSpout(
            name="{} Right".format(lick_spout_name),
            side=d.SpoutSide.RIGHT,
            spout_diameter=1.2,
            spout_diameter_unit=SizeUnit.MM,
            solenoid_valve=d.Device(device_type="Solenoid", name="Solenoid Right"),
            lick_sensor_type=d.LickSensorType("Capacitive")
        ),
        ]   

    components['stimulus_devices']=[
        d.RewardDelivery(
            reward_spouts=lick_spouts,
            stage_type = stage,
        ),
        d.Speaker(
            name="Stimulus speaker",
            manufacturer=d.Organization.OTHER,
        )
        ]


    # DAQS
    ###########################################################################

    components['daqs']=[
        d.HarpDevice(
            name="Harp Behavior",
            harp_device_type=d.HarpDeviceType.BEHAVIOR,
            manufacturer=d.Organization.CHAMPALIMAUD,
            computer_name=settings['computer_name'], 
            is_clock_generator=False,
            channels=[
                d.DAQChannel(channel_name="DO0", device_name="Solenoid Left", channel_type="Digital Output"),
                d.DAQChannel(channel_name="DO1", device_name="Solenoid Right", channel_type="Digital Output"),
                d.DAQChannel(channel_name="DI0", device_name=lick_spouts[0].name, channel_type="Digital Input"),
                d.DAQChannel(channel_name="DI1", device_name=lick_spouts[1].name, channel_type="Digital Input") 
            ],
        ),
        d.HarpDevice(
            name="Harp Sound",
            harp_device_type=d.HarpDeviceType.SOUND_CARD,
            manufacturer=d.Organization.CHAMPALIMAUD,
            computer_name=settings['computer_name'], 
            is_clock_generator=False,
            data_interface=d.DataInterface.USB
        ),
        d.HarpDevice(
            name="Harp clock synchronization board",
            harp_device_type=d.HarpDeviceType.CLOCK_SYNCHRONIZER,
            manufacturer=d.Organization.CHAMPALIMAUD,
            computer_name=settings['computer_name'], 
            is_clock_generator=True,
            data_interface=d.DataInterface.USB
        ),       
        d.HarpDevice(
            name="Harp sound amplifier",
            harp_device_type=d.HarpDeviceType.INPUT_EXPANDER,
            manufacturer=d.Organization.CHAMPALIMAUD,
            computer_name=settings['computer_name'], 
            is_clock_generator=False,
            data_interface=d.DataInterface.USB
        )
    ]


    # Water Calibration
    ###########################################################################

    components['calibrations']=[]

    # Water calibration
    if water_calibration != {}:
        left, right = parse_water_calibration(water_calibration)
        components['calibrations'].append(left)
        components['calibrations'].append(right)


    # FIB specific information
    ###########################################################################
    if FIB:
        # TODO FIB calibration needs to be recorded and incorporated here
        # This is waiting for the FIB calibration to be tracked after upcoming
        # hardware/firmware changes

        components['patch_cords']=[
            d.Patch(
                name="Bundle Branching Fiber-optic Patch Cord",
                manufacturer=d.Organization.DORIC,
                model="BBP(4)_200/220/900-0.37_Custom_FCM-4xMF1.25",
                core_diameter=200,
                numerical_aperture=0.37,
            )
        ]

        components['light_sources'].append(
            d.LightEmittingDiode(
                name="470nm LED",
                manufacturer=d.Organization.THORLABS,
                model="M470F3",
                wavelength=470,
            ))
        components['light_sources'].append(
            d.LightEmittingDiode(
                name="415nm LED",
                manufacturer=d.Organization.THORLABS,
                model="M415F3",
                wavelength=415,
            ))
        components['light_sources'].append(
            d.LightEmittingDiode(
                name="565nm LED",
                manufacturer=d.Organization.THORLABS,
                model="M565F3",
                wavelength=565,
            ))

        components['detectors']=[
            d.Detector(
                name="Green CMOS",
                serial_number=settings["box_settings"]["FipGreenCMOSSerialNumber"],
                manufacturer=d.Organization.FLIR,
                model="BFS-U3-20S40M",
                detector_type="Camera",
                data_interface="USB",
                cooling="Air",
                immersion="air",
                bin_width=4,
                bin_height=4,
                bin_mode="Additive",
                crop_width=200,
                crop_height=200,
                gain=2,
                chroma="Monochrome",
                bit_depth=16,
            ),
            d.Detector(
                name="Red CMOS",
                serial_number=settings["box_settings"]["FipRedCMOSSerialNumber"],
                manufacturer=d.Organization.FLIR,
                model="BFS-U3-20S40M",
                detector_type="Camera",
                data_interface="USB",
                cooling="Air",
                immersion="air",
                bin_width=4,
                bin_height=4,
                bin_mode="Additive",
                crop_width=200,
                crop_height=200,
                gain=2,
                chroma="Monochrome",
                bit_depth=16,
            ),
        ]

        components['objectives']=[
            d.Objective(
                name="Objective",
                serial_number=settings['box_settings']['FipObjectiveSerialNumber'],
                manufacturer=d.Organization.NIKON,
                model="CFI Plan Apochromat Lambda D 10x",
                numerical_aperture=0.45,
                magnification=10,
                immersion="air",
            )
        ]

        components['filters']=[
            d.Filter(
                name="Green emission filter",
                manufacturer=d.Organization.SEMROCK,
                model="FF01-520/35-25",
                filter_type="Band pass",
                center_wavelength=520,
                diameter=25,
            ),
            d.Filter(
                name="Red emission filter",
                manufacturer=d.Organization.SEMROCK,
                model="FF01-600/37-25",
                filter_type="Band pass",
                center_wavelength=600,
                diameter=25,
            ),
            d.Filter(
                name="Emission Dichroic",
                model="FF562-Di03-25x36",
                manufacturer=d.Organization.SEMROCK,
                filter_type="Dichroic",
                height=25,
                width=36,
                cut_off_wavelength=562,
            ),
            d.Filter(
                name="dual-edge standard epi-fluorescence dichroic beamsplitter",
                model="FF493/574-Di01-25x36",
                manufacturer=d.Organization.SEMROCK,
                notes="493/574 nm BrightLine dual-edge standard epi-fluorescence dichroic beamsplitter",
                filter_type="Multiband",
                width=36,
                height=24,
            ),
            d.Filter(
                name="Excitation filter 410nm",
                manufacturer=d.Organization.THORLABS,
                model="FB410-10",
                filter_type="Band pass",
                diameter=25,
                center_wavelength=410,
            ),
            d.Filter(
                name="Excitation filter 470nm",
                manufacturer=d.Organization.THORLABS,
                model="FB470-10",
                filter_type="Band pass",
                center_wavelength=470,
                diameter=25,
            ),
            d.Filter(
                name="Excitation filter 560nm",
                manufacturer=d.Organization.THORLABS,
                model="FB560-10",
                filter_type="Band pass",
                diameter=25,
                center_wavelength=560,
            ),
            d.Filter(
                name="450 Dichroic Longpass Filter",
                manufacturer=d.Organization.EDMUND_OPTICS,
                model="#69-898",
                filter_type="Dichroic",
                cut_off_wavelength=450,
                width=35.6,
                height=25.2,
            ),
            d.Filter(
                name="500 Dichroic Longpass Filter",
                manufacturer=d.Organization.EDMUND_OPTICS,
                model="#69-899",
                filter_type="Dichroic",
                cut_off_wavelength=500,
                width=35.6,
                height=23.2,
            ),
        ]
        components['lenses']=[
            d.Lens(
                manufacturer=d.Organization.THORLABS,
                model="AC254-080-A-ML",
                name="Image focusing lens",
                focal_length=80,
                size=1,
            )
        ]
        
        components['additional_devices']=[d.Device(device_type="Photometry Clock", name="Photometry Clock")]
        components['daqs'][0].channels.append(d.DAQChannel(channel_name="DI3", device_name="Photometry Clock", channel_type="Digital Input"))


    # Optogenetics specific
    ###########################################################################
    if OPTO:
        components['daqs'].append(
            d.DAQDevice(
                name="optogenetics nidaq",
                device_type="DAQ Device",
                data_interface=d.DataInterface.USB,
                manufacturer=d.Organization.NATIONAL_INSTRUMENTS,
                model="USB-6002",
                computer_name=settings['computer_name'],
            )
        )
        components['light_sources'].append(
            d.LightEmittingDiode(
                name="Optogenetics LED",
                manufacturer=d.Organization.PRIZMATIX,
                model="Dual-Optogenetics-LED-Blue",
                wavelength=460,
                wavelength_unit=SizeUnit.NM,
                notes="This LED is used for optogenetics"
            ))

        components['patch_cords'].append(
            d.Patch(
                name="Optogenetics Fiber to FC",
                manufacturer=d.Organization.PRIZMATIX,
                model="Optogenetics-Fiber-1000",
                core_diameter=1000,
                numerical_aperture=0.63,
                notes="SMA to FC"
            )
        )
        components['patch_cords'].append(
            d.Patch(
                name="Optogenetics Fiber to ferrule",
                manufacturer=d.Organization.PRIZMATIX,
                model="Optogenetics-Fiber-500",
                core_diameter=500,
                numerical_aperture=0.63,
                notes="FC to ferrule; ferrule size 1.25mm"
            )
        )

        # laser calibration
        components['calibrations'].extend(parse_laser_calibration(laser_calibration))


    # Generate Rig Schema
    ###########################################################################
    # Assemble rig schema
    rig = r.Rig(
        rig_id="{}_{}".format(settings['rig_name'],datetime.now().strftime('%Y-%m-%d')), 
        modification_date=date.today(),
        **components 
        )
    logging.info('finished building rig json')
    return rig


def parse_water_calibration(water_calibration):
    
    date = sorted(water_calibration.keys())[-1]
    left_times, left_volumes = GetWaterCalibration(water_calibration, date, 'Left')
    right_times, right_volumes = GetWaterCalibration(water_calibration, date, 'Right')

    left = d.Calibration(
        calibration_date=datetime.strptime(date, "%Y-%m-%d").date(),
        device_name = 'Lick spout Left',
        description = 'Water calibration for Lick spout Left. The input is the valve open time in seconds and the output is the volume of water delievered in microliters.',
        input = {'valve open time (s):':left_times},
        output = {'water volume (ul):':left_volumes}
        )

    right = d.Calibration(
        calibration_date=datetime.strptime(date, "%Y-%m-%d").date(),
        device_name = 'Lick spout Right',
        description = 'Water calibration for Lick spout Left. The input is the valve open time in seconds and the output is the volume of water delievered in microliters.',
        input = {'valve open time (s):':right_times},
        output = {'water volume (ul):':right_volumes}
        )

    return left, right


def parse_laser_calibration(laser_calibration):
    calibrations = []

    # Iterate through laser colors
    laser_colors = get_laser_names(laser_calibration) 
    for laser in laser_colors:
        # find the last calibration for this laser color        
        latest_calibration_date = FindLatestCalibrationDate(laser, laser_calibration)
        if latest_calibration_date == 'NA':
            continue

        # Iterate through calibration protocols for this laser color
        this_calibration = laser_calibration[latest_calibration_date][laser]
        for protocol in this_calibration.keys():
            if protocol == 'Sine':
                for freq in this_calibration[protocol]:
                    for laser_name in this_calibration[protocol][freq].keys():
                        voltage = [x[0] for x in 
                            this_calibration[protocol][freq][laser_name]['LaserPowerVoltage']]
                        power = [x[1] for x in 
                            this_calibration[protocol][freq][laser_name]['LaserPowerVoltage']]
                        voltage, power = zip(*sorted(zip(voltage, power), key=lambda x: x[0]))
                        
                        datestr = datetime.strptime(latest_calibration_date,'%Y-%m-%d').date()
                        description= f'Optogenetic calibration for {laser} {laser_name}, protocol: {protocol}, frequency: {freq}.'
                        calibrations.append(
                            d.Calibration(
                                calibration_date = datestr,
                                device_name = laser_name, 
                                description = description, 
                                input = {'input voltage (v)':voltage},
                                output = {'laser power (mw)':power},
                            ))
            elif protocol in ['Constant', 'Pulse']:
                for laser_name in this_calibration[protocol].keys():
                    voltage = [x[0] for x in 
                        this_calibration[protocol][laser_name]['LaserPowerVoltage']]
                    power = [x[1] for x in 
                        this_calibration[protocol][laser_name]['LaserPowerVoltage']]
                    voltage, power = zip(*sorted(zip(voltage, power), key=lambda x: x[0]))
                    
                    datestr = datetime.strptime(latest_calibration_date,'%Y-%m-%d').date()
                    description= f'Optogenetic calibration for {laser} {laser_name}, protocol: {protocol}'
                    calibrations.append(
                        d.Calibration(
                            calibration_date = datestr,
                            device_name = laser_name, 
                            description = description, 
                            input = {'input voltage (v)':voltage},
                            output = {'laser power (mw)':power},
                        ))

    return calibrations


def get_laser_names(laser_calibration):
    names = []
    for date in laser_calibration:
        names.extend(list(laser_calibration[date].keys()))
    return np.unique(names)


def FindLatestCalibrationDate(laser, laser_calibration):
        '''find the latest calibration date for the selected laser'''
        dates=[]
        for date in laser_calibration:
            if laser in laser_calibration[date].keys():
                dates.append(date)
        sorted_dates = sorted(dates)
        if sorted_dates==[]:
            return 'NA'
        else:
            return sorted_dates[-1]

