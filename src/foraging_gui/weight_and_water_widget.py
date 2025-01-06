from view.widgets.base_device_widget import BaseDeviceWidget, create_widget
from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtGui import QDoubleValidator
from widget_schemas.weight_and_water_schema import WeightAndWater
from pydantic_core import PydanticUndefined
import typing

class QWithinRangeValidator(QDoubleValidator):
    """
    QDouble validator that will set value within range if fixup is called
    """

    def fixup(self, value: typing.Optional[str]) -> str:
        self.parent().setValue(min(self.top(), max(float(value), self.bottom())))
        return str(min(self.top(), max(float(value), self.bottom())))


class WeightAndWaterWidget(BaseDeviceWidget):
    """
    Widget for weight and water info for mouse
    """

    def __init__(self):

        widget_dict = {k: v.default if v.default is not PydanticUndefined else v.annotation()
                       for k, v in WeightAndWater.model_fields.items()}
        super().__init__(WeightAndWater, widget_dict)

        # add warning label
        self.total_water_warning_widget = QLabel()

        # reorganize layout
        widgets = list(self.property_widgets.values())
        if len(widgets) % 2 != 0:   # add dummy widget so all rows/columns can be created
            widgets.append(QWidget())
        self.setCentralWidget(create_widget('HV', *widgets, self.total_water_warning_widget))

        # add validators so no value can go below 0
        self.base_weight_g_widget.validator().setBottom(0.0)
        self.supplemental_mL_widget.validator().setBottom(0.0)
        self.target_weight_g_widget.validator().setBottom(0.0)
        self.total_water_mL_widget.validator().setBottom(0.0)
        self.post_weight_g_widget.validator().setBottom(0.0)

        # add validator and fixup method if target_ratio value is above 1
        self.target_ratio_widget.setValidator(QWithinRangeValidator(self.target_ratio_widget))
        self.target_ratio_widget.validator().setRange(0.0, 1.0)

        self.base_weight_g_widget.editingFinished.connect(self.update_target_weight)
        self.target_ratio_widget.editingFinished.connect(self.update_target_weight)

        # make target_weight_g and total water uneditable
        self.target_weight_g_widget.setReadOnly(True)
        self.total_water_mL_widget.setReadOnly(True)

    def update_target_weight(self):
        """
        Update the suggested water from the manually given water
        """


        self.target_weight_g = self.target_ratio * self.base_weight_g
        self.target_weight_g_widget.setValue(round(self.target_weight_g, 3))


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication
    import sys
    from aind_behavior_services.task_logic import AindBehaviorTaskLogicModel
    from aind_auto_train.schema.task import DynamicForagingParas
    import traceback
    import logging


    def error_handler(etype, value, tb):
        error_msg = ''.join(traceback.format_exception(etype, value, tb))
        print(error_msg)


    sys.excepthook = error_handler  # redirect std error

    app = QApplication(sys.argv)

    weight_water_widget = WeightAndWaterWidget()
    weight_water_widget.show()
    sys.exit(app.exec_())