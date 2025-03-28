from foraging_gui.schema_widgets.schema_widget_base import SchemaWidgetBase, create_widget
from aind_behavior_dynamic_foraging.DataSchemas.fiber_photometry import (
    FiberPhotometry
)
from PyQt5.QtWidgets import QCheckBox, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QSlider, QComboBox
from PyQt5.QtCore import pyqtSignal
import enum

class FIBParametersWidget(SchemaWidgetBase):

    """
    Widget to expose task logic for fiber photometry sessions
    """


    def __init__(self, schema: FiberPhotometry):

        super().__init__(schema)
        self.schema_fields_widgets["name"].hide()
        self.enabled_widget.toggled.connect(self.toggle_enabled)
        self.toggle_enabled(self.schema.enabled)

    def toggle_enabled(self, enabled):
        """
            Disable widgets if enabled is False
        """

        for key, widget in self.schema_fields_widgets.items():
            if key == "enabled":
                continue
            widget.setEnabled(enabled)
        self.schemaToggled.emit()

    def _set_widget_text(self, name, value):
        """Set widget text if widget is QLineEdit or QCombobox
        :param name: widget name to set text to
        :param value: value of text"""
        if hasattr(self, f"{name}_widget"):
            widget = getattr(self, f"{name}_widget")
            widget.blockSignals(True)  # block signal indicating change since changing internally
            if type(widget) in [QLineEdit]:
                widget.setText(str(value))
            elif type(widget) in [QSpinBox, QDoubleSpinBox, QSlider]:
                widget.setValue(value)
            elif type(widget) == QComboBox:
                value_type = type(self.path_get(self.schema, name.split("."))) if name != "mode" else str
                value = value.name if type(value_type) == enum.EnumMeta else value_type(value)
                widget.setCurrentText(str(value))
            elif hasattr(widget, 'setChecked'):
                widget.setChecked(value)
            widget.blockSignals(False)
        else:
            self.log.warning(f"{name} doesn't correspond to a widget")

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

    task_model.mode = "Axon"
    task_model.baseline_time = 7
    task_widget.apply_schema(task_model)

    sys.exit(app.exec_())