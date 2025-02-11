from task_widget_base import TaskWidgetBase, add_border, path_get, path_set, create_widget
from aind_behavior_dynamic_foraging.DataSchemas.optogenetics import (
    Optogenetics,
    LaserColors,
    SessionControl,
    IntervalConditions,
    LaserOne,
    LaserTwo,
    SineProtocol,
    PulseProtocol,
    ConstantProtocol
)
import logging
from qtpy.QtWidgets import QCheckBox, QComboBox


class OptoParametersWidget(TaskWidgetBase):
    """
    Widget to expose task logic for behavior sessions
    """

    def __init__(self, schema):
        super().__init__(schema)
        print(self.__dict__)
        # delete widgets unrelated to session
        del self.task_parameters_widgets["experiment_type"]

        # add or remove laser colors
        for laser, widget in self.laser_colors_widgets.items():
            check_box = QCheckBox(f"Color {laser}")
            check_box.setChecked(True)
            check_box.toggled.connect(lambda s, laser_i=laser: self.toggle_laser_field(f"laser_colors.{laser_i}",
                                                                        s,
                                                                       LaserColors(
                                                                           color="Blue",
                                                                           pulse_condition="Right choice",
                                                                           start=IntervalConditions(
                                                                               interval_condition="Trial start",
                                                                               offset=0
                                                                           ),
                                                                           end=IntervalConditions(
                                                                               interval_condition="Right reward",
                                                                               offset=0
                                                                           ),
                                                                       )))
            widget.layout().insertWidget(0, check_box)
            setattr(self, f"laser_colors.{laser}_checkbox", check_box)

            # add/remove lasers
            for location, location_widget in getattr(self, f"laser_colors.{laser}.location_widgets").items():
                location_widget_dict = getattr(self, f"laser_colors.{laser}.location.{location}_widgets")
                location_widget_dict["name"].hide()
                del location_widget_dict["name"]
                check_box = QCheckBox(f"laser {location}")
                check_box.setChecked(True)
                check_box.toggled.connect(lambda s, laser_i=laser, loc_i=location:
                                          self.toggle_location_field(f"laser_colors.{laser_i}.location.{loc_i}", s))
                location_widget.layout().insertWidget(0, check_box)
                setattr(self, f"laser_colors.{laser}.location.{location}_checkbox", check_box)

            # change protocol
            protocol_widget = QComboBox()
            protocol_widget.addItems(["Sine", "Pulse", "Constant"])
            protocol_widget.currentTextChanged.connect(lambda text, laser_i=laser:
                                                       self.change_protocol(f"laser_colors.{laser_i}.protocol", text))
            getattr(self, f"laser_colors.{laser}.protocol_widget").layout().insertWidget(0, protocol_widget)
            self.change_protocol(f"laser_colors.{laser}.protocol", "Sine")

        add_border(self)

    def toggle_laser_field(self, name: str, enabled: bool, value) -> None:
        """
        Add or remove optional field
        :param name: name of field
        :param enabled: whether to add or remove field
        :param value: value to set field to
        """

        for widget in getattr(self, name+"_widgets").values():
            if enabled:
                widget.show()
            else:
                widget.hide()
        name_lst = name.split(".")
        laser_list = path_get(self.schema.model_dump(), name_lst[:-1])

        laser_list[int(name_lst[-1])] = value if enabled else None
        path_set(self.schema, name_lst[:-1], laser_list)
        self.ValueChangedOutside.emit(name)

    def toggle_location_field(self, name: str, enabled: bool) -> None:
        """
        Add or remove optional field
        :param name: name of field
        :param enabled: whether to add or remove field
        """
        for widget in getattr(self, name+"_widgets").values():
            if enabled:
                widget.show()
            else:
                widget.hide()
        name_lst = name.split(".")
        index = int(name_lst[-1])
        laser_type = LaserOne() if index == 0 else LaserTwo()
        name_lst = name.split(".")
        location_list = path_get(self.schema.model_dump(), name_lst[:-1])

        location_list[int(name_lst[-1])] = laser_type if enabled else None
        path_set(self.schema, name_lst[:-1], location_list)
        self.ValueChangedOutside.emit(name)

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
        path_set(self.schema, name_lst, protocol_type)

        for widget in getattr(self, name + "_widgets").values():
            widget.deleteLater()
        fields = {f"{name}.{key}": value for key, value in path_get(self.schema.model_dump(), name_lst).items()}
        new_widget = create_widget(**self.create_field_widgets(fields, name),
                                   struct="V")
        getattr(self, f"{name}_widget").layout().insertWidget(1, new_widget)
        getattr(self, f"{name}_widgets")["name"].hide()
        self.ValueChangedOutside.emit(name)

if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication
    import sys
    import traceback


    def error_handler(etype, value, tb):
        error_msg = ''.join(traceback.format_exception(etype, value, tb))
        print(error_msg)


    sys.excepthook = error_handler  # redirect std error
    app = QApplication(sys.argv)
    task_model = Optogenetics(
        laser_colors=[
            LaserColors(
                color="Blue",
                pulse_condition="Right choice",
                start=IntervalConditions(
                    interval_condition="Trial start",
                    offset=0
                ),
                end=IntervalConditions(
                    interval_condition="Right reward",
                    offset=0
                ),
            ),
            LaserColors(
                color="Red",
                pulse_condition="Right choice",
                start=IntervalConditions(
                    interval_condition="Trial start",
                    offset=0
                ),
                end=IntervalConditions(
                    interval_condition="Right reward",
                    offset=0
                ),
            ),
            LaserColors(
                color="Green",
                pulse_condition="Right choice",
                start=IntervalConditions(
                    interval_condition="Trial start",
                    offset=0
                ),
                end=IntervalConditions(
                    interval_condition="Right reward",
                    offset=0
                ),
            ),
            LaserColors(
                color="Orange",
                pulse_condition="Right choice",
                start=IntervalConditions(
                    interval_condition="Trial start",
                    offset=0
                ),
                end=IntervalConditions(
                    interval_condition="Right reward",
                    offset=0
                ),
            ),
        ],
        session_control=SessionControl(),
    )
    task_widget = OptoParametersWidget(task_model)
    task_widget.ValueChangedInside.connect(lambda name: print(task_model))
    task_widget.show()

    # task_model.task_parameters.block_parameters.min = 10
    # task_model.task_parameters.auto_water = None
    # task_widget.apply_schema(task_model.task_parameters)

    sys.exit(app.exec_())
