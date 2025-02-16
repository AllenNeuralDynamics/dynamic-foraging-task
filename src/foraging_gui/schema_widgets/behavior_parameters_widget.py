from foraging_gui.schema_widgets.schema_widget_base import SchemaWidgetBase, add_border
from aind_behavior_dynamic_foraging.DataSchemas.task_logic import (
    AindDynamicForagingTaskLogic,
    AindDynamicForagingTaskParameters,
    AutoWater,
    AutoStop,
    AutoBlock,
    Warmup,
    RewardN
)
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtCore import pyqtSignal
from pydantic import BaseModel

class BehaviorParametersWidget(SchemaWidgetBase):
    """
    Widget to expose task logic for behavior sessions
    """

    taskUpdated = pyqtSignal(str)
    volumeChanged = pyqtSignal(str)

    def __init__(self, schema: AindDynamicForagingTaskParameters,
                 reward_families: list):

        super().__init__(schema)

        self.reward_families = reward_families

        # set range on certain widgets
        getattr(self, "auto_water.multiplier_widget").setRange(0, 1)
        getattr(self, "auto_block.switch_thr_widget").setRange(0, 1)
        getattr(self, "warmup.max_choice_ratio_bias_widget").setRange(0, 1)
        getattr(self, "warmup.min_finish_ratio_widget").setRange(0, 1)
        getattr(self, "auto_stop.ignore_ratio_threshold_widget").setRange(0, 1)
        getattr(self, "reward_probability.family_widget").setRange(1, len(self.reward_families[:]))
        getattr(self, "reward_probability.pairs_n_widget").setMinimum(1)

        # connect reward family signal to update pair_n if needed
        getattr(self, "reward_probability.family_widget").valueChanged.connect(self.update_reward_family)
        getattr(self, "reward_probability.pairs_n_widget").valueChanged.connect(self.update_reward_family)

        # emit signal if reward volume changes
        getattr(self, "reward_size.right_value_volume_widget").valueChanged.connect(
            lambda: self.volumeChanged.emit('Right'))
        getattr(self, "reward_size.left_value_volume_widget").valueChanged.connect(
            lambda: self.volumeChanged.emit('Left'))

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
        self.uncoupled_reward_check_box.toggled.connect(lambda s: self.toggle_optional_field("uncoupled_reward",
                                                                                             s,
                                                                                             [0.1, 0.3, 0.7]))
        self.uncoupled_reward_check_box.setChecked(False)
        self.uncoupled_reward_check_box.toggled.emit(False)

        widget.layout().insertWidget(0, self.uncoupled_reward_check_box)

        # hide or show warmup
        widget = self.warmup_widget
        self.warmup_check_box = QCheckBox()
        self.warmup_check_box.setChecked(True)
        self.warmup_check_box.toggled.connect(lambda state: self.toggle_optional_field("warmup", state, Warmup()))
        widget.layout().insertWidget(0, self.warmup_check_box)

        # hide or show reward n
        widget = self.reward_n_widget
        self.reward_n_check_box = QCheckBox()
        self.reward_n_check_box.toggled.connect(lambda state: self.toggle_optional_field("reward_n", state, RewardN()))
        widget.parent().layout().insertWidget(0, self.reward_n_check_box)
        self.reward_n_check_box.setChecked(False)
        self.reward_n_check_box.toggled.emit(False)

        # delete widgets unrelated to session
        self.schema_fields_widgets["rng_seed"].hide()
        self.schema_fields_widgets["aind_behavior_services_pkg_version"].hide()

        add_border(self, {k: v for k, v in self.schema_fields_widgets.items() if
                          k not in ["rng_seed", "aind_behavior_services_pkg_version"]})

        self.ValueChangedInside.connect(self.update_task_option)

    def update_task_option(self, name):
        """
        Emit task type change and correctly configure parameters
        :param name of field changed
        """

        if name == "uncoupled_reward":
            if self.uncoupled_reward_check_box.isChecked():
                self.taskUpdated.emit("uncoupled")
                if self.reward_n_check_box.isChecked():
                    self.reward_n_check_box.setChecked(False)
            else:
                if not self.reward_n_check_box.isChecked():
                    self.taskUpdated.emit("coupled")

        if name == "reward_n":
            if self.reward_n_check_box.isChecked():
                self.taskUpdated.emit("reward_n")
                self.schema.block_parameters.min = 1
                self.schema.block_parameters.max = 1
                self.apply_schema(self.schema)
                if self.uncoupled_reward_check_box.isChecked():
                    self.uncoupled_reward_check_box.setChecked(False)
            else:
                if not self.uncoupled_reward_check_box.isChecked():
                    self.taskUpdated.emit("coupled")

    def update_reward_family(self):
        """
        Ensure that reward_probability pairs_n is larger than available reward pairs in family
        """

        family = self.schema.reward_probability.family
        pairs_n = self.schema.reward_probability.pairs_n
        if pairs_n > len(self.reward_families[family-1]):
            self.schema.reward_probability.pairs_n = len(self.reward_families[family-1])
            self.apply_schema(self.schema)

    def toggle_optional_field(self, name: str, enabled: bool, value) -> None:
        """
        Add or remove optional field
        :param name: name of field
        :param enabled: whether to add or remove field
        :param value: value to set field to
        """
        widgets = getattr(self, name+"_widgets") if hasattr(self, name+"_widgets") \
            else {"k": getattr(self, name+"_widget")}  # disable all sub widgets
        for widget in widgets.values():
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
        if dict not in type(value).__mro__ and list not in type(value).__mro__ and BaseModel not in type(value).__mro__:  # not a dictionary or list like value
            if value is None and hasattr(self, name+"_check_box"):   # optional type so uncheck widget
               getattr(self, name+"_check_box").setChecked(False)
            else:
                self._set_widget_text(name, value)
        elif dict in type(value).__mro__ or BaseModel in type(value).__mro__:
            value = value.model_dump() if BaseModel in type(value).__mro__ else value
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
    reward_families = [[[8, 1], [6, 1], [3, 1], [1, 1]], [[8, 1], [1, 1]],
                           [[1, 0], [.9, .1], [.8, .2], [.7, .3], [.6, .4], [.5, .5]], [[6, 1], [3, 1], [1, 1]]]

    task_widget = BehaviorParametersWidget(task_model.task_parameters, reward_families)
    task_widget.ValueChangedInside.connect(lambda name: print(task_model))
    task_widget.taskUpdated.connect(print)
    task_widget.show()

    task_model.task_parameters.block_parameters.min = 10
    task_model.task_parameters.auto_water = None
    task_widget.apply_schema(task_model.task_parameters)

    sys.exit(app.exec_())
