from foraging_gui.schema_widgets.schema_widget_base import SchemaWidgetBase, add_border
from aind_behavior_dynamic_foraging.DataSchemas.fiber_photometry import (
    FiberPhotometry
)

class FIBParametersWidget(SchemaWidgetBase):

    """
    Widget to expose task logic for fiber photometry sessions
    """

    def __init__(self, schema: FiberPhotometry):

        super().__init__(schema)
        self.schema_fields_widgets["experiment_type"].hide()


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
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
