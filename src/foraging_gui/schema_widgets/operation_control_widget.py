from aind_behavior_dynamic_foraging.DataSchemas.operation_control import (
    OperationalControl,
)
from PyQt5.QtCore import pyqtSignal
from foraging_gui.schema_widgets.schema_widget_base import SchemaWidgetBase, add_border
from threading import Lock

class OperationControlWidget(SchemaWidgetBase):
    """
    Widget to expose fields from operation_control models
    """

    upper_bias_changed = pyqtSignal(float)  # signal emiting new bias value
    lower_bias_changed = pyqtSignal(float)  # signal emiting new bias value

    def __init__(self, schema: OperationalControl, trial_lock: Lock, unsaved_color: str = "purple"):

        super().__init__(schema, trial_lock, unsaved_color)

        # add range for auto stop widgets
        getattr(self, "auto_stop.ignore_ratio_threshold_widget").setRange(0, 1)
        getattr(self, "auto_stop.ignore_win_widget").setMinimum(0)
        getattr(self, "auto_stop.max_trial_widget").setMinimum(0)
        getattr(self, "auto_stop.max_time_widget").setMinimum(0)
        getattr(self, "auto_stop.min_time_widget").setMinimum(0)

        # delete unneeded widgets
        del self.schema_fields_widgets["stage_specs"]
        del self.schema_fields_widgets["name"]

        add_border(self)

        # add ranges for bias thresholds
        up_bias = getattr(self, "lick_spout_bias_movement.bias_upper_threshold_widget")
        low_bias = getattr(self, "lick_spout_bias_movement.bias_lower_threshold_widget")
        up_bias.setRange(0, 1)
        up_bias. setSingleStep(.1)
        up_bias.returnPressed.connect(low_bias.setMaximum)   # lower threshold must be lower that upper threshold
        getattr(self, "lick_spout_bias_movement.bias_upper_threshold_widget").setMinimum(0)

        # add signal emit when thresholds are changed
        up_bias.returnPressed.connect(self.upper_bias_changed.emit)
        low_bias.returnPressed.connect(self.lower_bias_changed.emit)



if __name__ == "__main__":
    import sys
    import traceback

    from PyQt5.QtWidgets import QApplication

    def error_handler(etype, value, tb):
        error_msg = "".join(traceback.format_exception(etype, value, tb))
        print(error_msg)

    sys.excepthook = error_handler  # redirect std error
    app = QApplication(sys.argv)
    task_model = OperationalControl()
    task_widget = OperationControlWidget(task_model)
    task_widget.ValueChangedInside.connect(lambda name: print(task_model))
    task_widget.show()

    sys.exit(app.exec_())
