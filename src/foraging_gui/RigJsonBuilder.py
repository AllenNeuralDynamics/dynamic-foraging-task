import json
import logging
import re
from datetime import date, datetime

import aind_data_schema.components.coordinates as c
import aind_data_schema.components.devices as d
import aind_data_schema.core.rig as r
import numpy as np
from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.organizations import Organization
from aind_data_schema_models.units import SizeUnit
from deepdiff import DeepDiff

from foraging_gui.Visualization import GetWaterCalibration


def build_rig_json(
    existing_rig_json, settings, water_calibration, laser_calibration
):

    # Build the new rig schema
    rig = build_rig_json_core(settings, water_calibration, laser_calibration)
    if rig is None:
        logging.error("Could not generate Rig json")
        return
    # Serialize, and then deserialize to compare with existing rig schema
    new_rig_json = json.loads(rig.model_dump_json())

    # Compare the two rig.jsons
    differences = DeepDiff(existing_rig_json, new_rig_json, ignore_order=True)

    # Remove the modification date, since that doesnt matter for comparison purposes
    values_to_ignore = ["modification_date", "rig_id"]
    for value in values_to_ignore:
        if ("values_changed" in differences) and (
            "root['{}']".format(value) in differences["values_changed"]
        ):
            differences["values_changed"].pop("root['{}']".format(value))
            if len(differences["values_changed"]) == 0:
                differences.pop("values_changed")

    # Determine which schema to use
    if len(differences) > 0:
        # If any differences remain save a new rig.json
        logging.info(
            "differences with existing rig json: {}".format(differences)
        )
        # Write to file
        time_str = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        filename = "_{}_{}.json".format(settings["rig_name"], time_str)
        rig.write_standard_file(
            suffix=filename, output_directory=settings["rig_metadata_folder"]
        )
        filename = "rig" + filename
        logging.info("Saving new rig json: {}".format(filename))
    else:
        logging.info("Using existing rig json")


def build_rig_json_core(settings, water_calibration, laser_calibration):
    # Set up
    ###########################################################################
    logging.info("building rig json")

    # Build dictionary of components
    components = {}

    # Determine what extra components are present using settings files
    FIB = settings["Teensy_COM_box{}".format(settings["box_number"])] != ""
    OPTO = ("HasOpto" in settings["box_settings"]) and (
        settings["box_settings"]["HasOpto"] == "1"
    )
    HIGH_SPEED_CAMERA = ("HighSpeedCamera" in settings["box_settings"]) and (
        settings["box_settings"]["HighSpeedCamera"] == "1"
    )
    RIGHT_CAMERA = ("HasSideCameraRight" in settings["box_settings"]) and (
        settings["box_settings"]["HasSideCameraRight"] == "1"
    )
    BOTTOM_CAMERA = ("HasBottomCamera" in settings["box_settings"]) and (
        settings["box_settings"]["HasBottomCamera"] == "1"
    )

    # Modalities
    ###########################################################################
    # Opto is not a modality, its a stimulus
    components["modalities"] = [Modality.BEHAVIOR, Modality.BEHAVIOR_VIDEOS]
    if FIB:
        components["modalities"].append(Modality.FIB)

    if OPTO or FIB:
        components["patch_cords"] = []

    # Cameras
    ###########################################################################
    if HIGH_SPEED_CAMERA:
        components["cameras"] = []
        if RIGHT_CAMERA:
            components["cameras"].append(
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
                        name="Right size of face camera",
                        detector_type="Camera",
                        manufacturer=d.Organization.FLIR,
                        data_interface="USB",
                        computer_name=settings["computer_name"],
                        chroma="Monochrome",
                        cooling="Air",
                        sensor_format="1/2.9",
                        sensor_format_unit=SizeUnit.IN,
                        sensor_width=720,
                        sensor_height=540,
                        model="Blackfly S BFS-U3-04S2M",
                        serial_number=settings["box_settings"][
                            "SideCameraRight"
                        ],
                    ),
                )
            )
        if BOTTOM_CAMERA:
            components["cameras"].append(
                d.CameraAssembly(
                    name="Bottom Camera assembly",
                    camera_target=d.CameraTarget.FACE_BOTTOM,
                    lens=d.Lens(
                        name="Behavior Video Lens Bottom of face",
                        manufacturer=d.Organization.OTHER,
                        focal_length=25,
                        focal_length_unit=SizeUnit.MM,
                        model="LM25HC",
                        notes="Manufacturer is Kowa",
                    ),
                    camera=d.Camera(
                        name="bottom of face camera",
                        computer_name=settings["computer_name"],
                        detector_type="Camera",
                        manufacturer=d.Organization.FLIR,
                        data_interface="USB",
                        chroma="Monochrome",
                        cooling="Air",
                        sensor_format="1/2.9",
                        sensor_format_unit=SizeUnit.IN,
                        sensor_width=720,
                        sensor_height=540,
                        model="Blackfly S BFS-U3-04S2M",
                        serial_number=settings["box_settings"]["BottomCamera"],
                    ),
                )
            )
    else:
        components["cameras"] = [
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
                    computer_name=settings["computer_name"],
                    sensor_width=640,
                    sensor_height=480,
                    chroma="Color",
                    cooling="Air",
                    bin_mode="Additive",
                    recording_software=d.Software(
                        name="Bonsai", version=settings["bonsai_version"]
                    ),
                ),
                lens=d.Lens(
                    name="Xenocam 1",
                    model="XC0922LENS",
                    manufacturer=d.Organization.OTHER,
                    max_aperture="f/1.4",
                    focal_length=9,
                    focal_length_unit=SizeUnit.MM,
                    notes="Manufacturer is Xenocam",
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
                    computer_name=settings["computer_name"],
                    sensor_width=640,
                    sensor_height=480,
                    chroma="Color",
                    cooling="Air",
                    bin_mode="Additive",
                    recording_software=d.Software(
                        name="Bonsai", version=settings["bonsai_version"]
                    ),
                ),
                lens=d.Lens(
                    name="Xenocam 2",
                    model="XC0922LENS",
                    manufacturer=d.Organization.OTHER,
                    max_aperture="f/1.4",
                    focal_length=9,
                    focal_length_unit=SizeUnit.MM,
                    notes="Manufacturer is Xenocam",
                ),
            ),
        ]

    components["light_sources"] = [
        d.LightEmittingDiode(
            name="IR LED",
            manufacturer=d.Organization.THORLABS,
            model="M810L5",
            wavelength=810,
        )
    ]

    # Mouse Platform
    ###########################################################################
    components["mouse_platform"] = d.Tube(
        name="mouse_tube_foraging",
        diameter=3.0,
        diameter_unit=SizeUnit.CM,
        manufacturer=d.Organization.CUSTOM,
    )

    components["enclosure"] = d.Enclosure(
        name="Behavior enclosure",
        size=c.Size3d(
            width=54,  # TODO, 54cm is my quick measurement of one box
            length=54,  # TODO
            height=54,  # TODO
            unit=SizeUnit.CM,
        ),
        manufacturer=d.Organization.AIND,  # TODO
        internal_material="",
        external_material="",
        grounded=False,  # TODO
        laser_interlock=False,
        air_filtration=False,  # TODO
    )

    # Stimulus devices
    ###########################################################################
    if (
        settings["newscale_serial_num_box{}".format(settings["box_number"])]
        != ""
    ):
        stage = d.MotorizedStage(
            name="NewScaleMotor for LickSpouts",
            serial_number=settings[
                "newscale_serial_num_box{}".format(settings["box_number"])
            ],
            manufacturer=d.Organization.NEW_SCALE_TECHNOLOGIES,
            model="XYZ Stage with M30LS-3.4-15 linear stages",
            travel=15.0,
            travel_unit=SizeUnit.MM,
            firmware="https://github.com/AllenNeuralDynamics/python-newscale, branch: axes-on-target, commit #7c17497",
        )
    else:
        stage = d.MotorizedStage(
            name="AIND lick spout stage",
            manufacturer=d.Organization.AIND,
            travel=30,
            travel_unit=SizeUnit.MM,
            notes="https://allenneuraldynamics.github.io/Bonsai.AllenNeuralDynamics/articles/aind-manipulator.html",
        )

    if ("AINDLickDetector" in settings["box_settings"]) and (
        settings["box_settings"]["AINDLickDetector"] == "1"
    ):
        lick_spout_manufacturer = d.Organization.AIND
    else:
        lick_spout_manufacturer = d.Organization.JANELIA
    lick_spouts = [
        d.RewardSpout(
            name="Left lick spout",
            side=d.SpoutSide.LEFT,
            spout_diameter=1.2,
            solenoid_valve=d.Device(
                device_type="Solenoid",
                name="Solenoid Left",
                model="LHDA1233415H",
                manufacturer=Organization.from_name("The Lee Company"),
            ),
            lick_sensor_type=d.LickSensorType("Capacitive"),
            lick_sensor=d.Device(
                device_type="Lick Sensor",
                name="Lick Sensor Left",
                manufacturer=lick_spout_manufacturer,
            ),
        ),
        d.RewardSpout(
            name="Right lick spout",
            side=d.SpoutSide.RIGHT,
            spout_diameter=1.2,
            spout_diameter_unit=SizeUnit.MM,
            solenoid_valve=d.Device(
                device_type="Solenoid",
                name="Solenoid Right",
                model="LHDA1233415H",
                manufacturer=Organization.from_name("The Lee Company"),
            ),
            lick_sensor_type=d.LickSensorType("Capacitive"),
            lick_sensor=d.Device(
                device_type="Lick Sensor",
                name="Lick Sensor Right",
                manufacturer=lick_spout_manufacturer,
            ),
        ),
    ]

    components["stimulus_devices"] = [
        d.RewardDelivery(
            reward_spouts=lick_spouts,
            stage_type=stage,
        ),
        d.Speaker(
            name="Stimulus Speaker",
            manufacturer=d.Organization.TYMPHANY,
            model="XT25SC90-04",
        ),
    ]

    # DAQS
    ###########################################################################

    components["daqs"] = [
        d.HarpDevice(
            name="harp behavior board",
            harp_device_type=d.HarpDeviceType.BEHAVIOR,
            manufacturer=d.Organization.CHAMPALIMAUD,
            computer_name=settings["computer_name"],
            is_clock_generator=False,
            data_interface=d.DataInterface.ETH,
            core_version="1.11",  # TODO
            notes="{} and {}, as well as reward delivery solenoids are connected via ethernet cables".format(
                lick_spouts[0].name, lick_spouts[1].name
            ),
        ),
        d.HarpDevice(
            name="harp sound card",
            harp_device_type=d.HarpDeviceType.SOUND_CARD,
            manufacturer=d.Organization.CHAMPALIMAUD,
            computer_name=settings["computer_name"],
            is_clock_generator=False,
            data_interface=d.DataInterface.USB,
            core_version="1.4",  # TODO
        ),
        d.HarpDevice(
            name="harp clock synchronization board",
            harp_device_type=d.HarpDeviceType.CLOCK_SYNCHRONIZER,
            manufacturer=d.Organization.CHAMPALIMAUD,
            computer_name=settings["computer_name"],
            is_clock_generator=True,
            data_interface=d.DataInterface.USB,
            core_version="",  # TODO
        ),
        d.HarpDevice(
            name="harp sound amplifier",
            harp_device_type=d.HarpDeviceType.INPUT_EXPANDER,
            manufacturer=d.Organization.CHAMPALIMAUD,
            computer_name=settings["computer_name"],
            is_clock_generator=False,
            data_interface=d.DataInterface.USB,
            core_version="",  # TODO
        ),
    ]

    # Water Calibration
    ###########################################################################

    components["calibrations"] = []

    # Water calibration
    if water_calibration != {}:
        calibrations = parse_water_calibration(water_calibration)
        components["calibrations"].extend(calibrations)

    # FIB specific information
    ###########################################################################
    if FIB:
        # TODO FIB calibration needs to be recorded and incorporated here
        # This is waiting for the FIB calibration to be tracked after upcoming
        # hardware/firmware changes

        components["patch_cords"].append(
            d.Patch(
                name="Bundle Branching Fiber-optic Patch Cord",
                manufacturer=d.Organization.DORIC,
                model="BBP(4)_200/220/900-0.37_Custom_FCM-4xMF1.25",
                core_diameter=200,
                numerical_aperture=0.37,
            )
        )

        components["light_sources"].append(
            d.LightEmittingDiode(
                name="470nm LED",
                manufacturer=d.Organization.THORLABS,
                model="M470F3",
                wavelength=470,
            )
        )
        components["light_sources"].append(
            d.LightEmittingDiode(
                name="415nm LED",
                manufacturer=d.Organization.THORLABS,
                model="M415F3",
                wavelength=415,
            )
        )
        components["light_sources"].append(
            d.LightEmittingDiode(
                name="565nm LED",
                manufacturer=d.Organization.THORLABS,
                model="M565F3",
                wavelength=565,
            )
        )

        components["detectors"] = [
            d.Detector(
                name="Green CMOS",
                serial_number=settings["box_settings"][
                    "FipGreenCMOSSerialNumber"
                ],
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
                serial_number=settings["box_settings"][
                    "FipRedCMOSSerialNumber"
                ],
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

        components["objectives"] = [
            d.Objective(
                name="Objective",
                serial_number=settings["box_settings"][
                    "FipObjectiveSerialNumber"
                ],
                manufacturer=d.Organization.NIKON,
                model="CFI Plan Apochromat Lambda D 10x",
                numerical_aperture=0.45,
                magnification=10,
                immersion="air",
            )
        ]

        components["filters"] = [
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
                name="beamsplitter",
                model="FF493/574-Di01-25x36",
                manufacturer=d.Organization.SEMROCK,
                notes="493/574 nm BrightLine dual-edge standard epi-fluorescence dichroic beamsplitter",
                filter_type="Multiband",
                width=36,
                height=25,
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
        components["lenses"] = [
            d.Lens(
                manufacturer=d.Organization.THORLABS,
                model="AC254-080-A-ML",
                name="Image focusing lens",
                focal_length=80,
                size=1,
            )
        ]

        components["additional_devices"] = [
            d.Device(device_type="Photometry Clock", name="Photometry Clock")
        ]
        components["daqs"][0].channels.append(
            d.DAQChannel(
                channel_name="DI3",
                device_name="Photometry Clock",
                channel_type="Digital Input",
            )
        )

    # Optogenetics specific
    ###########################################################################
    if OPTO:
        components["daqs"].append(
            d.DAQDevice(
                name="optogenetics nidaq",
                device_type="DAQ Device",
                data_interface=d.DataInterface.USB,
                manufacturer=d.Organization.NATIONAL_INSTRUMENTS,
                model="USB-6002",
                computer_name=settings["computer_name"],
            )
        )
        components["light_sources"].append(
            d.LightEmittingDiode(
                name="Optogenetics LED",
                manufacturer=d.Organization.PRIZMATIX,
                model="Dual-Optogenetics-LED-Blue",
                wavelength=460,
                wavelength_unit=SizeUnit.NM,
                notes="This LED is used for optogenetics",
            )
        )

        components["patch_cords"].append(
            d.Patch(
                name="Optogenetics Fiber to FC",
                manufacturer=d.Organization.PRIZMATIX,
                model="Optogenetics-Fiber-1000",
                core_diameter=1000,
                numerical_aperture=0.63,
                notes="SMA to FC",
            )
        )
        components["patch_cords"].append(
            d.Patch(
                name="Optogenetics Fiber to ferrule",
                manufacturer=d.Organization.PRIZMATIX,
                model="Optogenetics-Fiber-500",
                core_diameter=500,
                numerical_aperture=0.63,
                notes="FC to ferrule; ferrule size 1.25mm",
            )
        )

        # laser calibration
        components["calibrations"].extend(
            parse_laser_calibration(laser_calibration)
        )

    # Generate Rig Schema
    ###########################################################################
    # Assemble rig schema
    rig_id = "{}_{}".format(
        settings["rig_name"], datetime.now().strftime("%Y%m%d")
    )
    if (
        re.match(r.RIG_ID_PATTERN, rig_id) is None
    ):  # rig_id does not match regex pattern reqs
        try:  # assuming rigs are named in room-box-letter fashion
            room, box, letter = settings["rig_name"].split("-")
            rig_name = room + "_" + box + letter
            rig_id = "{}_{}".format(
                rig_name, datetime.now().strftime("%Y%m%d")
            )
            if (
                re.match(r.RIG_ID_PATTERN, rig_id) is None
            ):  # rig_id still does not match regex pattern reqs
                raise ValueError
        except ValueError:
            logging.error(
                f"Cannot generate rig because rig_id cannot be configured to match {r.RIG_ID_PATTERN}"
            )
            return

    rig = r.Rig(rig_id=rig_id, modification_date=date.today(), **components)
    logging.info("finished building rig json")
    return rig


def parse_water_calibration(water_calibration):
    calibrations = []
    dates = sorted(water_calibration.keys())
    for this_date in dates[::-1]:
        if "Left" in water_calibration[this_date]:
            left_times, left_volumes = GetWaterCalibration(
                water_calibration, this_date, "Left"
            )
            left = d.Calibration(
                calibration_date=datetime.strptime(
                    this_date, "%Y-%m-%d"
                ).date(),
                device_name="Lick spout Left",
                description="Water calibration for Lick spout Left. The input is the valve open time in seconds and the output is the volume of water delivered in microliters.",
                input={"valve open time (s):": left_times},
                output={"water volume (ul):": left_volumes},
            )
            calibrations.append(left)
            break
        elif "SpotLeft" in water_calibration[this_date]:
            times, volumes = GetWaterCalibration(
                water_calibration, this_date, "SpotLeft"
            )
            left = d.Calibration(
                calibration_date=datetime.strptime(
                    this_date, "%Y-%m-%d"
                ).date(),
                device_name="Lick spout Left",
                description="Spot check of water calibration for Lick spout Left. "
                + "The input is the valve open time in seconds and the output is the "
                + "volume of water delievered in microliters. The valve open time was "
                + "selected to produce 2ul of water. This measurement was used "
                + "to check the previous calibration, and was not used to set the calibration.",
                input={"valve open time (s):": times},
                output={"water volume (ul):": volumes},
            )
            calibrations.append(left)

    for this_date in dates[::-1]:
        if "Right" in water_calibration[this_date]:
            right_times, right_volumes = GetWaterCalibration(
                water_calibration, this_date, "Right"
            )
            right = d.Calibration(
                calibration_date=datetime.strptime(
                    this_date, "%Y-%m-%d"
                ).date(),
                device_name="Lick spout Right",
                description="Water calibration for Lick spout Right. The input is the valve open time in seconds and the output is the volume of water delivered in microliters.",
                input={"valve open time (s):": right_times},
                output={"water volume (ul):": right_volumes},
            )
            calibrations.append(right)
            break
        elif "SpotRight" in water_calibration[this_date]:
            times, volumes = GetWaterCalibration(
                water_calibration, this_date, "SpotRight"
            )
            right = d.Calibration(
                calibration_date=datetime.strptime(
                    this_date, "%Y-%m-%d"
                ).date(),
                device_name="Lick spout Right",
                description="Spot check of water calibration for Lick spout Right. "
                + "The input is the valve open time in seconds and the output is the "
                + "volume of water delievered in microliters. The valve open time was "
                + "selected to produce 2ul of water. This measurement was used "
                + "to check the previous calibration, and was not used to set the calibration.",
                input={"valve open time (s):": times},
                output={"water volume (ul):": volumes},
            )
            calibrations.append(right)

    return calibrations


def parse_laser_calibration(laser_calibration):
    calibrations = []

    # Iterate through laser colors
    laser_colors = get_laser_names(laser_calibration)
    for laser in laser_colors:
        # find the last calibration for this laser color
        latest_calibration_date = FindLatestCalibrationDate(
            laser, laser_calibration
        )
        if latest_calibration_date == "NA":
            continue

        # Iterate through calibration protocols for this laser color
        this_calibration = laser_calibration[latest_calibration_date][laser]
        for protocol in this_calibration.keys():
            if protocol == "Sine":
                for freq in this_calibration[protocol]:
                    for laser_name in this_calibration[protocol][freq].keys():
                        voltage = [
                            x[0]
                            for x in this_calibration[protocol][freq][
                                laser_name
                            ]["LaserPowerVoltage"]
                        ]
                        power = [
                            x[1]
                            for x in this_calibration[protocol][freq][
                                laser_name
                            ]["LaserPowerVoltage"]
                        ]
                        voltage, power = zip(
                            *sorted(zip(voltage, power), key=lambda x: x[0])
                        )

                        datestr = datetime.strptime(
                            latest_calibration_date, "%Y-%m-%d"
                        ).date()
                        description = f"Optogenetic calibration for {laser} {laser_name}, protocol: {protocol}, frequency: {freq}."
                        calibrations.append(
                            d.Calibration(
                                calibration_date=datestr,
                                device_name=laser_name,
                                description=description,
                                input={"input voltage (v)": voltage},
                                output={"laser power (mw)": power},
                            )
                        )
            elif protocol in ["Constant", "Pulse"]:
                for laser_name in this_calibration[protocol].keys():
                    voltage = [
                        x[0]
                        for x in this_calibration[protocol][laser_name][
                            "LaserPowerVoltage"
                        ]
                    ]
                    power = [
                        x[1]
                        for x in this_calibration[protocol][laser_name][
                            "LaserPowerVoltage"
                        ]
                    ]
                    voltage, power = zip(
                        *sorted(zip(voltage, power), key=lambda x: x[0])
                    )

                    datestr = datetime.strptime(
                        latest_calibration_date, "%Y-%m-%d"
                    ).date()
                    description = f"Optogenetic calibration for {laser} {laser_name}, protocol: {protocol}"
                    calibrations.append(
                        d.Calibration(
                            calibration_date=datestr,
                            device_name=laser_name,
                            description=description,
                            input={"input voltage (v)": voltage},
                            output={"laser power (mw)": power},
                        )
                    )

    return calibrations


def get_laser_names(laser_calibration):
    names = []
    for this_date in laser_calibration:
        names.extend(list(laser_calibration[this_date].keys()))
    return np.unique(names)


def FindLatestCalibrationDate(laser, laser_calibration):
    """find the latest calibration date for the selected laser"""
    dates = []
    for this_date in laser_calibration:
        if laser in laser_calibration[this_date].keys():
            dates.append(this_date)
    sorted_dates = sorted(dates)
    if sorted_dates == []:
        return "NA"
    else:
        return sorted_dates[-1]
