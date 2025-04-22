from foraging_gui.schema_widgets.schema_widget_base import SchemaWidgetBase, add_border, create_widget
from aind_behavior_dynamic_foraging.DataSchemas.operation_control import OperationalControl
from PyQt5.QtWidgets import QVBoxLayout


class OperationControlWidget(SchemaWidgetBase):
    """
    Widget to expose fields from operation_control models
    """

    def __init__(self, schema: OperationalControl):
        super().__init__(schema)

        # hide unnecessary widgets
        self.schema_fields_widgets["stage_specs"].hide()
        self.schema_fields_widgets["name"].hide()

        # add range for auto stop widgets
        getattr(self, "auto_stop.ignore_ratio_threshold_widget").setRange(0, 1)
        getattr(self, "auto_stop.ignore_win_widget").setMinimum(0)
        getattr(self, "auto_stop.max_trial_widget").setMinimum(0)
        getattr(self, "auto_stop.max_time_widget").setMinimum(0)
        getattr(self, "auto_stop.min_time_widget").setMinimum(0)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    import traceback

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
