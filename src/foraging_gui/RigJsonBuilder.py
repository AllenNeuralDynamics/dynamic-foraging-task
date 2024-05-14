import logging
from datetime import date, datetime, timezone

import aind_data_schema.core.rig as r
import aind_data_schema.components.devices as d
from aind_data_schema_models.modalities import Modality

def build_rig_json(settings, water_calibration, laser_calibration):    
    logging.info('building rig json')
    rig = r.Rig(
        rig_id="447_FIP/Behavior/Opt_FullModalityTemplate", ## TODO
        modification_date=date(2000, 1, 1), # TODO
        modalities=[Modality.FIB, Modality.BEHAVIOR], # TODO
        cameras=[
            d.CameraAssembly(
                name="BehaviorVideography_FaceSide",
                #camera_assembly_name="BehaviorVideography_FaceBottom",
                camera_target=d.CameraTarget.FACE_SIDE_RIGHT,
                camera=d.Camera(
                    name="Side face camera",
                    detector_type="Camera",
                    serial_number="TBD",
                    manufacturer=d.Organization.AILIPU,
                    model="ELP-USBFHD05MT-KL170IR",
                    notes="The light intensity sensor was removed; IR illumination is constantly on",
                    data_interface="USB",
                    computer_name="W10DTJK7N0M3",
                    max_frame_rate=120,
                    sensor_width=640,
                    sensor_height=480,
                    chroma="Color",
                    cooling="Air",
                    bin_mode="Additive",
                    recording_software=d.Software(name="Bonsai", version="2.5"),
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
                #camera_assembly_name="BehaviorVideography_FaceBottom",
                camera_target=d.CameraTarget.FACE_BOTTOM,
                camera=d.Camera(
                    name="Bottom face Camera",
                    detector_type="Camera",
                    serial_number="TBD",
                    manufacturer=d.Organization.AILIPU,
                    model="ELP-USBFHD05MT-KL170IR",
                    notes="The light intensity sensor was removed; IR illumination is constantly on",
                    data_interface="USB",
                    computer_name="W10DTJK7N0M3",
                    max_frame_rate=120,
                    sensor_width=640,
                    sensor_height=480,
                    chroma="Color",
                    cooling="Air",
                    bin_mode="Additive",
                    recording_software=d.Software(name="Bonsai", version="2.5"),
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
        ],
        
        daqs=[
            d.HarpDevice(
                name="Harp Behavior",
                harp_device_type=d.HarpDeviceType.BEHAVIOR,
                core_version="2.1",
                firmware_version="FTDI version:",
                computer_name="behavior_computer", # TODO should this be hostname?
                is_clock_generator=False,
                channels=[
                    d.DAQChannel(channel_name="DO0", device_name="Solenoid Left", channel_type="Digital Output"),
                    d.DAQChannel(channel_name="DO1", device_name="Solenoid Right", channel_type="Digital Output"),
                    d.DAQChannel(channel_name="DI0", device_name="Janelia_Lick_Detector Left", channel_type="Digital Input"), # TODO, need to check this
                    d.DAQChannel(channel_name="DI1", device_name="Janelia_Lick_Detector Right", channel_type="Digital Input"), # TODO, need to check this
                    d.DAQChannel(channel_name="DI3", device_name="Photometry Clock", channel_type="Digital Input"),
                ],
            )
        ],
        mouse_platform=d.Tube(name="mouse_tube_foraging", diameter=4.0),
        stimulus_devices=[
            d.RewardDelivery(
                reward_spouts=[
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
                ],
                stage_type=d.MotorizedStage(
                        name="NewScaleMotor for LickSpouts",
                        serial_number="xxxx", #grabing from GUI/SettingFiles # TODO
                        manufacturer=d.Organization.NEW_SCALE_TECHNOLOGIES,
                        travel=15.0,  #unit is mm
                        firmware="https://github.com/AllenNeuralDynamics/python-newscale, branch: axes-on-target, commit #7c17497",
                ),
                
            ),
        ],
        
        
        ## Common
        #######################################################################################################
        ##FIB Specific
        
        # TODO, need to toggle whether to include this       
 
        patch_cords=[
            d.Patch(
                name="Bundle Branching Fiber-optic Patch Cord",
                manufacturer=d.Organization.DORIC,
                model="BBP(4)_200/220/900-0.37_Custom_FCM-4xMF1.25",
                core_diameter=200,
                numerical_aperture=0.37,
            )
        ],
        light_sources=[
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
        ],
        detectors=[
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
        ],
        objectives=[
            d.Objective(
                name="Objective",
                serial_number="128022336",
                manufacturer=d.Organization.NIKON,
                model="CFI Plan Apochromat Lambda D 10x",
                numerical_aperture=0.45,
                magnification=10,
                immersion="air",
            )
        ],
        filters=[
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
        ],
        lenses=[
            d.Lens(
                manufacturer=d.Organization.THORLABS,
                model="AC254-080-A-ML",
                name="Image focusing lens",
                focal_length=80,
                size=1,
            )
        ],
        
        additional_devices=[d.Device(device_type="Photometry Clock", name="Photometry Clock")],
        
        ##FIB Specific
        #######################################################################################################
        ##Optogenetics Specific   ##Xinxin to fill in
        # TODO, need to toggle whether to include this, and fill it in       
 
        #light_sources=[
        #    d.LightEmittingDiode(
        #        name="LED for photostimulation",
        #        manufacturer=d.Organization.PRIZMATIX,
        #        model="xxx",
        #        wavelength=470,
        #    ),
        #],
        
        #daqs=[
        #    d.DAQDevice(
        #        name="NIDAQ for opto",
        #        device_type="DAQ Device",
        #        data_interface="USB2.0",
        #        manufacturer=d.Organization.NATIONAL_INSTRUMENTS,
        #        computer_name="behavior_computer",
        #        channels=[
        #        ],
        #    )
        #],
        
        ##Optogenetics Specific
        #######################################################################################################
    
        # TODO, need to merge in laser and water calibration things
        ##Calibrations
        calibrations=[
            d.Calibration(
                calibration_date=datetime(2023, 10, 2, 3, 15, 22, tzinfo=timezone.utc),
                device_name="470nm LED",
                description="LED calibration",
                input={"Power setting": [0]},
                output={"Power mW": [0.02]},
            ),
            d.Calibration(
                calibration_date=datetime(2023, 10, 2, 3, 15, 22, tzinfo=timezone.utc),
                device_name="415nm LED",
                description="LED calibration",
                input={"Power setting": [0]},
                output={"Power mW": [0.02]},
            ),
            d.Calibration(
                calibration_date=datetime(2023, 10, 2, 3, 15, 22, tzinfo=timezone.utc),
                device_name="560nm LED",
                description="LED calibration",
                input={"Power setting": [0]},
                output={"Power mW": [0.02]},
            ),
    
            ##Water calibration comes here##
        ],
    )
   
    # Write to file 
    suffix = '_{}_{}.json'.format(settings['rig_name'], datetime.now().strftime('%Y-%m-%d_%H_%M_%S'))
    rig.write_standard_file(suffix=suffix, output_directory=settings['rig_metadata_folder']) 
    logging.info('built rig json: rig{}'.format(suffix))

