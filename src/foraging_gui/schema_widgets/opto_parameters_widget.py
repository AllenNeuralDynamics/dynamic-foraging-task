from aind_behavior_dynamic_foraging.DataSchemas.optogenetics import (
    LaserColors,
    ConstantProtocol,
    IntervalConditions,
    LaserColorFive,
    LaserColorFour,
    LaserColorOne,
    LaserColorSix,
    LaserColorThree,
    LaserColorTwo,
    LocationOne,
    LocationTwo,
    Optogenetics,
    PulseProtocol,
    SessionControl,
    SineProtocol,
)
from pydantic import BaseModel
from PyQt5.QtWidgets import QCheckBox, QComboBox, QSizePolicy
from PyQt5.QtCore import pyqtSignal
from threading import Lock

from foraging_gui.schema_widgets.schema_widget_base import (
    SchemaWidgetBase,
    add_border,
    create_widget,
)


class OptoParametersWidget(SchemaWidgetBase):
    """
    Widget to expose task logic for behavior sessions
    """

    protocolChanged = pyqtSignal(dict)  # emit when protocol is changed and emit serialized condition
    laserColorChanged = pyqtSignal(dict)  # emit when laser color is changed and emit serialized condition

    def __init__(self, schema, trial_lock: Lock):
        super().__init__(schema, trial_lock)

        # delete widgets unrelated to session
        self.schema_fields_widgets["name"].hide()
        self.schema_fields_widgets["sample_frequency"].setEnabled(False)

        # add or remove laser colors
        for laser, widget in self.laser_colors_widgets.items():
            check_box = QCheckBox(f"Color {int(laser) + 1}")
            check_box.setChecked(True)
            check_box.toggled.connect(
                lambda s, laser_i=laser: self.toggle_laser_field(
                    f"laser_colors.{laser_i}", s
                )
            )
            widget.layout().insertWidget(0, check_box)
            setattr(self, f"laser_colors.{laser}_check_box", check_box)
            # hide laser color name widget
            getattr(self, f"laser_colors.{laser}_widgets")["name"].hide()
            del getattr(self, f"laser_colors.{laser}_widgets")["name"]

            # add signal for changing colors
            getattr(self, f"laser_colors.{laser}.color_widget").currentTextChanged.connect(lambda text, laser_i=laser:
                                                                                           self.laserColorChanged.emit(self.path_get(self.schema, ["laser_colors", str(laser_i)]).model_dump()))

            # add/remove locations
            for location, location_widget in getattr(
                self, f"laser_colors.{laser}.location_widgets"
            ).items():
                location_widget_dict = getattr(
                    self, f"laser_colors.{laser}.location.{location}_widgets"
                )
                # hide location name widget
                location_widget_dict["name"].hide()
                del location_widget_dict["name"]

                # create checkbox
                check_box = QCheckBox(f"laser {int(location) + 1}")
                check_box.setChecked(True)
                check_box.toggled.connect(
                    lambda s, laser_i=laser, loc_i=location: self.toggle_location_field(
                        f"laser_colors.{laser_i}.location.{loc_i}", s
                    )
                )
                location_widget.layout().insertWidget(0, check_box)
                setattr(
                    self,
                    f"laser_colors.{laser}.location.{location}_check_box",
                    check_box,
                )

            # add/remove start and end
            for interval in ["start", "end"]:
                check_box = QCheckBox(interval.title())
                check_box.setChecked(True)
                check_box.toggled.connect(
                    lambda s, laser_i=laser, name=interval: self.toggle_optional_field(
                        f"laser_colors.{laser_i}.{name}",
                        s,
                        IntervalConditions(),
                    )
                )
                layout = (
                    getattr(self, f"laser_colors.{laser}.{interval}_widget")
                    .parent()
                    .layout()
                )
                label = layout.itemAt(0).widget()
                layout.replaceWidget(label, check_box)
                setattr(
                    self,
                    f"laser_colors.{laser}.{interval}_check_box",
                    check_box,
                )
            # set 0 minimum for start
            getattr(
                self, f"laser_colors.{laser}.start.offset_widget"
            ).setMinimum(0)

            # set range on probability widget
            getattr(self, f"laser_colors.{laser}.probability_widget").setRange(
                0, 1
            )

            # change protocol
            protocol_widget = QComboBox()
            protocol_widget.addItems(["Sine", "Pulse", "Constant"])
            protocol_widget.currentTextChanged.connect(
                lambda text, laser_i=laser: self.change_protocol(
                    f"laser_colors.{laser_i}.protocol", text
                )
            )
            protocol_widget.currentTextChanged.connect(lambda text, laser_i=laser: self.protocolChanged.emit(self.path_get(self.schema, ["laser_colors", str(laser_i)]).model_dump()))
            getattr(
                self, f"laser_colors.{laser}.protocol_widget"
            ).layout().insertWidget(0, protocol_widget)
            setattr(
                self,
                f"laser_colors.{laser}.protocol_combo_box_widget",
                protocol_widget,
            )
            # hide protocol name widget
            getattr(self, f"laser_colors.{laser}.protocol_widgets")[
                "name"
            ].hide()

        # add/remove session control
        widget = self.session_control_widget
        self.session_control_check_box = QCheckBox("Enable Session Control")
        self.session_control_check_box.setChecked(True)
        self.session_control_check_box.toggled.connect(
            lambda s: self.toggle_optional_field(
                "session_control", s, SessionControl()
            )
        )
        widget.layout().insertWidget(0, self.session_control_check_box)

        add_border(self, orientation="V")

    def toggle_optional_field(self, name: str, enabled: bool, value) -> None:
        """
        Add or remove optional field
        :param name: name of field
        :param enabled: whether to add or remove field
        :param value: value to set field to
        """
        for widget in getattr(self, name + "_widgets").values():
            widget.setEnabled(enabled)
        name_lst = name.split(".")
        if enabled:
            self.path_set(self.schema, name_lst, value)
        else:
            self.path_set(self.schema, name_lst, None)
        self.ValueChangedInside.emit(name)

    def toggle_laser_field(self, name: str, enabled: bool) -> None:
        """
        Add or remove optional field
        :param name: name of field
        :param enabled: whether to add or remove field
        :param value: value to set field to
        """

        widget_dict = getattr(self, name + "_widgets")
        for widget in widget_dict.values():
            if enabled:
                widget.show()
                widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            else:
                widget.hide()
                widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.adjustSize()

        name_lst = name.split(".")

        possible_lasers = [
            LaserColorOne,
            LaserColorTwo,
            LaserColorThree,
            LaserColorFour,
            LaserColorFive,
            LaserColorSix,
        ]
        laser_color = possible_lasers[int(name_lst[-1])](
            color="Blue",
            pulse_condition="Right choice",
            start=IntervalConditions(
                interval_condition="Trial start", offset=0
            ),
            end=IntervalConditions(
                interval_condition="Right reward", offset=0
            ),
        )
        active_lasers = self.path_get(self.schema, name_lst[:-1])
        if enabled and laser_color.name not in [
            laser.name for laser in active_lasers
        ]:  # checkbox was clicked
            active_lasers.append(laser_color)
        elif not enabled and laser_color.name in [
            laser.name for laser in active_lasers
        ]:  # checkbox was unclicked
            remove_index = [
                i
                for i, laser in enumerate(active_lasers)
                if laser.name == laser_color.name
            ]
            if len(remove_index) == 1:
                del active_lasers[remove_index[0]]
        self.path_set(self.schema, name_lst[:-1], active_lasers)
        self.ValueChangedInside.emit(".".join(name_lst[:-1]))

    def toggle_location_field(self, name: str, enabled: bool) -> None:
        """
        Add or remove optional field
        :param name: name of field
        :param enabled: whether to add or remove field
        """
        widget_dict = getattr(self, name + "_widgets")
        [
            widget.show() if enabled else widget.hide()
            for widget in widget_dict.values()
        ]

        name_lst = name.split(".")
        index = int(name_lst[-1])
        location_type = LocationTwo() if index == 1 else LocationOne()
        active_locations = self.path_get(self.schema, name_lst[:-1])
        if enabled:
            active_locations.append(location_type)
        else:
            remove_index = [
                i
                for i, location in enumerate(active_locations)
                if location.name == location_type.name
            ]
            if len(remove_index) == 1:
                del active_locations[remove_index[0]]
        self.path_set(self.schema, name_lst[:-1], active_locations)
        self.ValueChangedInside.emit(".".join(name_lst[:-1]))

    def change_protocol(self, name: str, protocol: str):
        """
        Change protocol class in schema and update widget
        :param name: name of protocol changes
        :param protocol: name of new protocol
        """

        if protocol == "Sine":
            protocol_type = SineProtocol()
        elif protocol == "Pulse":
            protocol_type = PulseProtocol()
        else:
            protocol_type = ConstantProtocol()
        name_lst = name.split(".")

        self.path_set(self.schema, name_lst, protocol_type)

        for widget in getattr(self, name + "_widgets").values():
            widget.deleteLater()
        fields = {
            f"{name}.{key}": value
            for key, value in self.path_get(self.schema, name_lst)
            .model_dump()
            .items()
        }
        new_widget = create_widget(
            **self.create_field_widgets(fields, name), struct="V"
        )
        getattr(self, f"{name}_widget").layout().insertWidget(1, new_widget)
        getattr(self, f"{name}_widgets")["name"].hide()
        self.ValueChangedInside.emit(name)

    def update_laser_power(self, condition: LaserColors, location: "LocationOne" or "LocationTwo", powers: list[float]):
        """
            Update power selection for location combo boxes

            :param condition: condition location is associated with
            :param location: location powers to update
            :param powers: list of powers to update

        """
        # map condition to schema
        possible_conditions = [
            "LaserColorOne",
            "LaserColorTwo",
            "LaserColorThree",
            "LaserColorFour",
            "LaserColorFive",
            "LaserColorSix",
        ]
        condition_index = possible_conditions.index(condition.name)

        # map laser location to schema
        possible_locations = ["LocationOne", "LocationTwo"]
        location_index = possible_locations.index(location)

        # find widget
        widget = getattr(self, f"laser_colors.{condition_index}.location.{location_index}.power_widget")
        widget.blockSignals(True)
        widget.clear()
        widget.blockSignals(False)
        widget.addItems([str(p) for p in powers])

    def update_laser_protocol(self, condition: LaserColors, location: LocationOne or LocationTwo, protocols: list[str]):
        """
            Update power selection for location combo boxes

            :param condition: condition location is associated with
            :param location: location powers to update
            :param protocols: list of protocols available

        """
        # map condition to schema
        possible_conditions = [
            "LaserColorOne",
            "LaserColorTwo",
            "LaserColorThree",
            "LaserColorFour",
            "LaserColorFive",
            "LaserColorSix",
        ]
        condition_index = possible_conditions.index(condition.name)

        # find widget
        widget = getattr(self, f"laser_colors.{condition_index}.protocol_combo_box_widget")
        widget.blockSignals(True)
        widget.clear()
        widget.blockSignals(False)
        widget.addItems(protocols)
        widget.currentTextChanged.emit(widget.currentText())  # emit signal to trigger power update

    def update_laser_colors(self, colors: list[str]):
        """
            Update available laser colors based on what is in calibration file

            :param colors: list of available colors to choose from
        """

        for i in range(6):
            # find widget
            widget = getattr(self, f"laser_colors.{i}.color_widget")
            widget.blockSignals(True)
            widget.clear()
            widget.blockSignals(False)
            widget.addItems(colors)


    def update_field_widget(self, name):
        """
        Overwrite to apply optional None value
        """

        name_lst = name.split(".")
        value = self.path_get(self.schema, name_lst)
        if hasattr(self, name + "_check_box"):  # optional type
            getattr(self, name + "_check_box").setChecked(value is not None)

        if value is not None:
            if "protocol" == name_lst[-1]:
                getattr(self, f"{name}_combo_box_widget").blockSignals(True)
                getattr(self, f"{name}_combo_box_widget").setCurrentText(
                    value.name
                )
                getattr(self, f"{name}_combo_box_widget").blockSignals(False)
                self._set_widget_text(name, value)
                for widget in getattr(self, name + "_widgets").values():
                    widget.deleteLater()
                fields = {
                    f"{name}.{k}": v
                    for k, v in self.path_get(self.schema, name_lst)
                    .model_dump()
                    .items()
                }
                new_widget = create_widget(
                    **self.create_field_widgets(fields, name), struct="V"
                )
                getattr(self, f"{name}_widget").layout().insertWidget(
                    1, new_widget
                )
                getattr(self, f"{name}_widgets")["name"].hide()
            elif (
                dict not in type(value).__mro__
                and list not in type(value).__mro__
                and BaseModel not in type(value).__mro__
            ):  # not a dictionary or list like value
                self._set_widget_text(name, value)
            elif (
                dict in type(value).__mro__ or BaseModel in type(value).__mro__
            ):
                value = (
                    value.model_dump()
                    if BaseModel in type(value).__mro__
                    else value
                )
                for (
                    k,
                    v,
                ) in value.items():  # multiple widgets to set values for
                    self.update_field_widget(f"{name}.{k}")
            else:  # update list
                for i, item in enumerate(value):
                    if hasattr(
                        self, f"{name}.{i}_widget"
                    ):  # can't handle added indexes yet
                        self.update_field_widget(f"{name}.{i}")

    def apply_schema(self, schema: Optogenetics):
        """Overwrite to handle laser color and location"""

        with self.trial_lock:
            self.schema = schema
            for name in self.schema.model_dump().keys():
                if name == "laser_colors":
                    for color_i in range(6):
                        self.update_field_widget(f"{name}.{color_i}")
                        if self.path_get(self.schema, [name, color_i]) is not None:
                            for loc_i in range(2):
                                self.update_field_widget(
                                    f"{name}.{color_i}.location.{loc_i}"
                                )
                else:
                    self.update_field_widget(name)

    @staticmethod
    def path_set(iterable: Optogenetics, path: list[str], value) -> None:
        """
        Set value in a nested dictionary or list
        :param iterable: dictionary or list to set value
        :param path: list of strings that point towards value to set.
        """

        for i, k in enumerate(path):
            if k == "laser_colors" and i != len(path) - 1:
                sort_map = [
                    "LaserColorOne",
                    "LaserColorTwo",
                    "LaserColorThree",
                    "LaserColorFour",
                    "LaserColorFive",
                    "LaserColorSix",
                ]
                laser_dict = {k: None for k in sort_map}
                # fill gaps in laser dict
                laser_dict.update(
                    {laser.name: laser for laser in iterable.laser_colors}
                )
                iterable = [laser_dict[mapping] for mapping in sort_map]
            elif k == "location" and i != len(path) - 1:
                sort_map = ["LocationOne", "LocationTwo"]
                location_dict = {k: None for k in sort_map}
                # fill gaps
                location_dict.update(
                    {loc.name: loc for loc in iterable.location}
                )
                iterable = [location_dict[mapping] for mapping in sort_map]

            else:
                if i != len(path) - 1:
                    iterable = (
                        iterable[int(k)]
                        if type(iterable) == list
                        else getattr(iterable, k)
                    )
                else:
                    if type(iterable) == list:
                        iterable[int(k)] = value
                    else:
                        setattr(iterable, k, value)

    @staticmethod
    def path_get(iterable: Optogenetics, path: list[str]):
        """
        Get value in a nested dictionary or listt
        :param iterable: dictionary or list to set value
        :param path: list of strings that point towards value to set.
        :return value found at end of path
        """

        for i, k in enumerate(path):
            if k == "laser_colors" and i != len(path) - 1:
                sort_map = [
                    "LaserColorOne",
                    "LaserColorTwo",
                    "LaserColorThree",
                    "LaserColorFour",
                    "LaserColorFive",
                    "LaserColorSix",
                ]
                laser_dict = {k: None for k in sort_map}
                # fill gaps in laser dict
                laser_dict.update(
                    {laser.name: laser for laser in iterable.laser_colors}
                )
                iterable = [laser_dict[mapping] for mapping in sort_map]
            elif k == "location" and i != len(path) - 1:
                sort_map = ["LocationOne", "LocationTwo"]
                location_dict = {k: None for k in sort_map}
                # fill gaps
                location_dict.update(
                    {loc.name: loc for loc in iterable.location}
                )
                iterable = [location_dict[mapping] for mapping in sort_map]
            else:
                k = int(k) if type(iterable) == list else k
                iterable = (
                    iterable[int(k)]
                    if type(iterable) == list
                    else getattr(iterable, k)
                )
        return iterable


if __name__ == "__main__":
    import sys
    import traceback

    from PyQt5.QtWidgets import QApplication

    def error_handler(etype, value, tb):
        error_msg = "".join(traceback.format_exception(etype, value, tb))
        print(error_msg)

    sys.excepthook = error_handler  # redirect std error
    app = QApplication(sys.argv)
    task_model = Optogenetics(
        sample_frequency=5000,
        laser_colors=[
            LaserColorOne(
                color="Blue",
                pulse_condition="Right choice",
                start=IntervalConditions(
                    interval_condition="Trial start", offset=0
                ),
                end=IntervalConditions(
                    interval_condition="Right reward", offset=0
                ),
            ),
            LaserColorTwo(
                color="Red",
                pulse_condition="Right choice",
                start=IntervalConditions(
                    interval_condition="Trial start", offset=0
                ),
                end=IntervalConditions(
                    interval_condition="Right reward", offset=0
                ),
            ),
            LaserColorThree(
                color="Green",
                pulse_condition="Right choice",
                start=IntervalConditions(
                    interval_condition="Trial start", offset=0
                ),
                end=IntervalConditions(
                    interval_condition="Right reward", offset=0
                ),
            ),
            LaserColorFour(
                color="Orange",
                pulse_condition="Right choice",
                start=IntervalConditions(
                    interval_condition="Trial start", offset=0
                ),
                end=IntervalConditions(
                    interval_condition="Right reward", offset=0
                ),
            ),
            LaserColorFive(
                color="Orange",
                pulse_condition="Right choice",
                start=IntervalConditions(
                    interval_condition="Trial start", offset=0
                ),
                end=IntervalConditions(
                    interval_condition="Right reward", offset=0
                ),
            ),
            LaserColorSix(
                color="Orange",
                pulse_condition="Right choice",
                start=IntervalConditions(
                    interval_condition="Trial start", offset=0
                ),
                end=IntervalConditions(
                    interval_condition="Right reward", offset=0
                ),
            ),
        ],
        session_control=SessionControl(),
    )
    task_widget = OptoParametersWidget(task_model, Lock())
    #task_widget.ValueChangedInside.connect(lambda name: print(task_model))
    task_widget.show()

    task_model.laser_colors = []
    task_widget.apply_schema(task_model)

    task_model.laser_colors.append(
        LaserColorFive(
            color="Blue",
            pulse_condition="Right choice",
            start=IntervalConditions(
                interval_condition="Trial start", offset=0
            ),
            end=IntervalConditions(
                interval_condition="Right reward", offset=0
            ),
        )
    )
    task_model.laser_colors[0].location = [LocationOne()]
    # task_model.laser_colors[1].location = [LocationTwo()]
    # task_model.laser_colors[0].protocol = PulseProtocol()

    task_widget.apply_schema(task_model)
    new_model = Optogenetics(
        sample_frequency=5000,
        laser_colors=[
            LaserColorOne(
                color="Blue",
                pulse_condition="Right choice",
                start=IntervalConditions(
                    interval_condition="Trial start", offset=0
                ),
                end=IntervalConditions(
                    interval_condition="Right reward", offset=0
                ),
            ),
            LaserColorThree(
                color="Blue",
                pulse_condition="Right choice",
                start=IntervalConditions(
                    interval_condition="Trial start", offset=0
                ),
                end=IntervalConditions(
                    interval_condition="Right reward", offset=0
                ),
            ),
            LaserColorFour(
                color="Blue",
                pulse_condition="Right choice",
                start=IntervalConditions(
                    interval_condition="Trial start", offset=0
                ),
                end=IntervalConditions(
                    interval_condition="Right reward", offset=0
                ),
            ),
            LaserColorFive(
                color="Blue",
                pulse_condition="Right choice",
                start=IntervalConditions(
                    interval_condition="Trial start", offset=0
                ),
                end=IntervalConditions(
                    interval_condition="Right reward", offset=0
                ),
            ),
        ],
        session_control=SessionControl(),
    ).model_dump()
    task_model = Optogenetics(**new_model)
    task_model.laser_colors[0].location = [LocationOne()]
    task_model.laser_colors[0].probability = 0.75
    task_model.laser_colors[0].duration = 6
    task_model.laser_colors[0].pulse_condition = "Left reward"
    task_model.laser_colors[0].start = None
    task_model.laser_colors[0].end.interval_condition = "Reward outcome"
    task_model.laser_colors[0].end.offset = 1
    task_model.laser_colors[0].protocol.frequency = 40
    task_model.laser_colors[0].protocol.ramp_down = 4
    task_model.laser_colors[1].protocol = ConstantProtocol(ramp_down=4)

    task_widget.apply_schema(task_model)

    #task_widget.update_laser_power(task_model.laser_colors[0], task_model.laser_colors[0].location[0], [3, 4] )
    #print(task_model.laser_colors[0].location[0].power)
    sys.exit(app.exec_())
