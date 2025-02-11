from task_widget_base import TaskWidgetBase, add_border
from aind_behavior_dynamic_foraging.DataSchemas.fiber_photometry import (
    FiberPhotometry
)
import logging
from qtpy.QtWidgets import QCheckBox

class FIBParametersWidget(TaskWidgetBase):

    """
    Widget to expose task logic for fiber photometry sessions
    """

    def __init__(self, schema: FiberPhotometry):

        super().__init__(schema)
        self.task_parameters_widgets["experiment_type"].hide()


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication
    import sys
    import traceback


    def error_handler(etype, value, tb):
        error_msg = ''.join(traceback.format_exception(etype, value, tb))
        print(error_msg)


    sys.excepthook = error_handler  # redirect std error
    app = QApplication(sys.argv)
    task_model = FiberPhotometry()
    task_widget = FIBParametersWidget(task_model)
    task_widget.ValueChangedInside.connect(lambda name: print(task_model))
    task_widget.show()

    sys.exit(app.exec_())
