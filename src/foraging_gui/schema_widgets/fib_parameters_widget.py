from foraging_gui.schema_widgets.schema_widget_base import SchemaWidgetBase, create_widget
from aind_behavior_dynamic_foraging.DataSchemas.fiber_photometry import (
    FiberPhotometry
)
from PyQt5.QtWidgets import QCheckBox, QLabel
from PyQt5.QtCore import pyqtSignal

class FIBParametersWidget(SchemaWidgetBase):

    """
    Widget to expose task logic for fiber photometry sessions
    """

    schemaToggled = pyqtSignal()

    def __init__(self, schema: FiberPhotometry):

        super().__init__(schema)
        self.schema_fields_widgets["experiment_type"].hide()

        # make entire fip schema optional
        # hide or show auto_water
        widget = self.centralWidget()
        label = QLabel("FIP Enabled")
        self.fip_schema_check_box = QCheckBox()
        self.fip_schema_check_box.toggled.connect(self.toggle_schema)
        self.fip_schema_check_box.setChecked(False)
        self.toggle_schema(False)
        widget.layout().insertWidget(0, create_widget("H", label, self.fip_schema_check_box))

    def toggle_schema(self, enabled):
        """
        Allow schema to be None type to indicate if session is run with FIP or not
        """

        if enabled:
            self.schema.mode = "Normal"
            self.apply_schema(self.schema)
        else:
            self.schema.mode = None

        for widget in self.schema_fields_widgets.values():
            widget.setEnabled(enabled)
        self.schemaToggled.emit()

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
    task_widget.schemaToggled.connect(lambda: print(task_model))
    task_widget.show()

    print(task_model)

    sys.exit(app.exec_())