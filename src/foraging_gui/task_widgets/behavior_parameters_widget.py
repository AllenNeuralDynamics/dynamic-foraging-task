from foraging_gui.task_widgets.task_widget_base import TaskWidgetBase, add_border
from aind_behavior_dynamic_foraging.DataSchemas.task_logic import (
    AindDynamicForagingTaskLogic,
    AindDynamicForagingTaskParameters,
    AutoWater,
    AutoStop,
    AutoBlock,
    Warmup
)
import logging
from PyQt5.QtWidgets import QCheckBox

class BehaviorParametersWidget(TaskWidgetBase):
    """
    Widget to expose task logic for behavior sessions
    """

    def __init__(self, schema: AindDynamicForagingTaskParameters):

        super().__init__(schema)
        #print(self.__dict__)

        # delete widgets unrelated to session
        del self.task_parameters_widgets["rng_seed"]
        del self.task_parameters_widgets["aind_behavior_services_pkg_version"]

        # set range on certain widgets
        getattr(self, "auto_water.multiplier_widget").setRange(0, 1)
        getattr(self, "auto_block.switch_thr_widget").setRange(0, 1)
        getattr(self, "warmup.max_choice_ratio_bias_widget").setRange(0, 1)
        getattr(self, "warmup.min_finish_ratio_widget").setRange(0, 1)
        getattr(self, "auto_stop.ignore_ratio_threshold_widget").setRange(0, 1)

        # hide or show auto_water
        widget = self.auto_water_widget
        self.auto_water_check_box = QCheckBox()
        self.auto_water_check_box.setChecked(True)
        self.auto_water_check_box.toggled.connect(lambda s: self.toggle_optional_field("auto_water", s, AutoWater()))
        widget.layout().insertWidget(0, self.auto_water_check_box)

        # hide or show auto_block
        widget = self.auto_block_widget
        self.auto_block_check_box = QCheckBox()
        self.auto_block_check_box.setChecked(True)
        self.auto_block_check_box.toggled.connect(lambda s: self.toggle_optional_field("auto_block", s, AutoBlock()))
        widget.layout().insertWidget(0, self.auto_block_check_box)

        # hide or show uncoupled_reward
        widget = self.uncoupled_reward_widget
        self.uncoupled_reward_check_box = QCheckBox()
        self.uncoupled_reward_check_box.setChecked(True)
        self.uncoupled_reward_check_box.toggled.connect(lambda s: self.toggle_optional_field("uncoupled_reward",
                                                                                             s,
                                                                                             [0.1, 0.3, 0.7]))
        widget.layout().insertWidget(0, self.uncoupled_reward_check_box)

        # hide or show warmuo
        widget = self.warmup_widget
        self.warmup_check_box = QCheckBox()
        self.warmup_check_box.setChecked(True)
        self.warmup_check_box.toggled.connect(lambda state: self.toggle_optional_field("warmup", state, Warmup()))
        widget.layout().insertWidget(0, self.warmup_check_box)

        add_border(self)

    def toggle_optional_field(self, name: str, enabled: bool, value) -> None:
        """
        Add or remove optional field
        :param name: name of field
        :param enabled: whether to add or remove field
        :param value: value to set field to
        """
        for widget in getattr(self, name+"_widgets").values():
            widget.setEnabled(enabled)
        name_lst = name.split(".")
        if enabled:
            self.path_set(self.schema, name_lst, value)
        else:
            self.path_set(self.schema, name_lst, None)
        self.ValueChangedInside.emit(name)

    def update_field_widget(self, name):
        """
        Overwrite to apply optional None value
        """

        value = self.path_get(self.schema, name.split("."))
        if dict not in type(value).__mro__ and list not in type(value).__mro__:  # not a dictionary or list like value
            if value is None and hasattr(self, name+"_check_box"):   # optional type so uncheck widget
               getattr(self, name+"_check_box").setChecked(False)
            else:
                self._set_widget_text(name, value)
        elif dict in type(value).__mro__:
            for k, v in value.items():  # multiple widgets to set values for
                self.update_field_widget(f"{name}.{k}")
        else:  # update list
            for i, item in enumerate(value):
                if hasattr(self, f"{name}.{i}_widget"):  # can't handle added indexes yet
                    self.update_field_widget(f"{name}.{i}")

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    import traceback


    def error_handler(etype, value, tb):
        error_msg = ''.join(traceback.format_exception(etype, value, tb))
        print(error_msg)


    sys.excepthook = error_handler  # redirect std error
    app = QApplication(sys.argv)
    task_model = AindDynamicForagingTaskLogic(
        task_parameters=AindDynamicForagingTaskParameters(
            auto_water=AutoWater(),
            auto_stop=AutoStop(),
            auto_block=AutoBlock(),
            warmup=Warmup()
        ),
    )
    task_widget = BehaviorParametersWidget(task_model.task_parameters)
    task_widget.ValueChangedInside.connect(lambda name: print(task_model))
    task_widget.show()

    task_model.task_parameters.block_parameters.min = 10
    task_model.task_parameters.auto_water = None
    task_widget.apply_schema(task_model.task_parameters)

    sys.exit(app.exec_())
