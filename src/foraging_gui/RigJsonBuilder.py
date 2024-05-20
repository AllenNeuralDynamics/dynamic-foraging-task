import os
import json
import logging
from deepdiff import DeepDiff
from datetime import date, datetime, timezone

import aind_data_schema.core.rig as r
import aind_data_schema.components.devices as d
from aind_data_schema_models.modalities import Modality

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
    LEFT_CAMERA = ('HasSideCameraLeft' in settings['box_settings']) and (settings['box_settings']['HasSideCameraLeft'] == "1")
    RIGHT_CAMERA = ('HasSideCameraRight' in settings['box_settings']) and (settings['box_settings']['HasSideCameraRight'] == "1")
    BODY_CAMERA = ('HasBodyCamera' in settings['box_settings']) and (settings['box_settings']['HasBodyCamera'] == "1")
    BOTTOM_CAMERA = ('HasBottomCamera' in settings['box_settings']) and (settings['box_settings']['HasBottomCamera'] == "1")
    AIND_LICK_DETECTOR = ('AINDLickDetector' in settings['box_settings']) and (settings['box_settings']['AINDLickDetector'] == "1")

    # Modalities
    ###########################################################################
    # Opto is not a modality, its a stimulus
    components['modalities'] = [Modality.BEHAVIOR, Modality.BEHAVIOR_VIDEOS]
    if FIB:
        components['modalities'].append(Modality.FIB)

    # Cameras
    ###########################################################################
    components['cameras']=[
        d.CameraAssembly(
            name="BehaviorVideography_FaceSide",
            camera_target=d.CameraTarget.FACE_SIDE_RIGHT,
            camera=d.Camera(
                name="Side face camera",
                detector_type="Camera",
                serial_number="TBD",
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
                serial_number="unknown",
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
                serial_number="TBD",
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
                serial_number="unknown",
                manufacturer=d.Organization.OTHER,
                max_aperture="f/1.4",
                notes='Focal Length 9-22mm 1/3" IR F1.4',
            ),
        ),
    ]

    # Mouse Platform
    ###########################################################################
    components['mouse_platform']=d.Tube(name="mouse_tube_foraging", diameter=4.0)

    # Stimulus devices
    ###########################################################################
    if settings['newscale_serial_num_box{}'.format(settings['box_number'])] != '':
        stage = d.MotorizedStage(
                    name="NewScaleMotor for LickSpouts",
                    serial_number=settings['newscale_serial_num_box{}'.format(settings['box_number'])], 
                    manufacturer=d.Organization.NEW_SCALE_TECHNOLOGIES,
                    travel=15.0,  #unit is mm
                    firmware="https://github.com/AllenNeuralDynamics/python-newscale, branch: axes-on-target, commit #7c17497",
                    )
    else:
        stage = d.MotorizedStage(
                    name="AIND lick spout stage",
                    manufacturer=d.Organization.AIND,
                    travel=15.0,
                    )      
    if ('AINDLickDetector' in settings['box_settings']) and (settings['box_settings']['AINDLickDetector'] == "1"):
        lick_spouts=[
            d.RewardSpout(
                name="AIND_Lick_Detector Left",
                side=d.SpoutSide.LEFT,
                spout_diameter=1.2,
                solenoid_valve=d.Device(device_type="Solenoid", name="Solenoid Left"),
                lick_sensor_type=d.LickSensorType("Capacitive")
            ),
            d.RewardSpout(
                name="AIND_Lick_Detector Right",
                side=d.SpoutSide.RIGHT,
                spout_diameter=1.2,
                solenoid_valve=d.Device(device_type="Solenoid", name="Solenoid Right"),
                lick_sensor_type=d.LickSensorType("Capacitive")
            ),
            ]   
    else:
        lick_spouts=[
            d.RewardSpout(
                name="Janelia_Lick_Detector Left",
                side=d.SpoutSide.LEFT,
                spout_diameter=1.2,
                solenoid_valve=d.Device(device_type="Solenoid", name="Solenoid Left"),
                lick_sensor_type=d.LickSensorType("Capacitive")
            ),
            d.RewardSpout(
                name="Janelia_Lick_Detector Right",
                side=d.SpoutSide.RIGHT,
                spout_diameter=1.2,
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
            core_version="2.1",
            firmware_version="FTDI version:",
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
            core_version="2.1",
            firmware_version="FTDI version:",
            computer_name=settings['computer_name'], 
            is_clock_generator=False,
            data_interface=d.DataInterface.USB
        ),
        d.HarpDevice(
            name="Harp clock synchronization board",
            harp_device_type=d.HarpDeviceType.CLOCK_SYNCHRONIZER,
            manufacturer=d.Organization.CHAMPALIMAUD,
            core_version="2.1",
            firmware_version="FTDI version:",
            computer_name=settings['computer_name'], 
            is_clock_generator=True,
            data_interface=d.DataInterface.USB
        ),       
        d.HarpDevice(
            name="Harp sound amplifier",
            harp_device_type=d.HarpDeviceType.INPUT_EXPANDER,
            manufacturer=d.Organization.CHAMPALIMAUD,
            core_version="2.1",
            firmware_version="FTDI version:",
            computer_name=settings['computer_name'], 
            is_clock_generator=False,
            data_interface=d.DataInterface.USB
        )
    ]

    # Calibrations
    ###########################################################################

    components['calibrations']=[]

    # Water calibration
    left, right = parse_water_calibration(water_calibration)
    components['calibrations'].append(left)
    components['calibrations'].append(right)

    # Laser Calibration     # TODO, its unclear if these are for FIP, OPTO, or both?
    # Its unclear how to include the laser calibration file
    #components['calibrations'].append(
    #    d.Calibration(
    #        calibration_date=datetime(2023, 10, 2, 3, 15, 22, tzinfo=timezone.utc),
    #        device_name="470nm LED",
    #        description="LED calibration",
    #        input={"Power setting": [0]},
    #        output={"Power mW": [0.02]},
    #    ))
    #components['calibrations'].append(
    #    d.Calibration(
    #        calibration_date=datetime(2023, 10, 2, 3, 15, 22, tzinfo=timezone.utc),
    #        device_name="415nm LED",
    #        description="LED calibration",
    #        input={"Power setting": [0]},
    #        output={"Power mW": [0.02]},
    #    ))
    #components['calibrations'].append(
    #    d.Calibration(
    #        calibration_date=datetime(2023, 10, 2, 3, 15, 22, tzinfo=timezone.utc),
    #        device_name="560nm LED",
    #        description="LED calibration",
    #        input={"Power setting": [0]},
    #        output={"Power mW": [0.02]},
    #    )

    # FIB specific information
    ###########################################################################
    if FIB:
        components['patch_cords']=[
            d.Patch(
                name="Bundle Branching Fiber-optic Patch Cord",
                manufacturer=d.Organization.DORIC,
                model="BBP(4)_200/220/900-0.37_Custom_FCM-4xMF1.25",
                core_diameter=200,
                numerical_aperture=0.37,
            )
        ]

        components['light_sources']=[
            d.LightEmittingDiode(
                name="470nm LED",
                manufacturer=d.Organization.THORLABS,
                model="M470F3",
                wavelength=470,
            ),
            d.LightEmittingDiode(
                name="415nm LED",
                manufacturer=d.Organization.THORLABS,
                model="M415F3",
                wavelength=415,
            ),
            d.LightEmittingDiode(
                name="565nm LED",
                manufacturer=d.Organization.THORLABS,
                model="M565F3",
                wavelength=565,
            ),
        ]

        components['detectors']=[
            d.Detector(
                name="Green CMOS",
                serial_number="21396991",
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
                serial_number="21396991",
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
                serial_number="128022336",
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
        ##Optogenetics Specific   ## TODO Xinxin to fill in
        print('need to implement') 
        #components['light_sources'].append(
        #    d.LightEmittingDiode(
        #        name="LED for photostimulation",
        #        manufacturer=d.Organization.PRIZMATIX,
        #        model="xxx",
        #        wavelength=470,
        #    )
        #    )
        
        #daqs.append(
        #    d.DAQDevice(
        #        name="NIDAQ for opto",
        #        device_type="DAQ Device",
        #        data_interface="USB2.0",
        #        manufacturer=d.Organization.NATIONAL_INSTRUMENTS,
        #        computer_name=settings['computer_name'],
        #        channels=[
        #        ],
        #    )
        #    )

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

    # TODO
    # Cameras
    # Platforms
    # FIP
    # OPTO
    # Reward/lick spouts
    # Lick detector
    # Harp boards
    # Parse laser calibration
    #
    # TODO, later
    # Lick spout stages - Need to add details for AIND stages
    # Speaker - needs manufactor, any details
    # What if water calibration is null?

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


