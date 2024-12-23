from view.widgets.base_device_widget import BaseDeviceWidget, create_widget
from PyQt5.QtWidgets import QMainWindow, QComboBox, QFrame, QVBoxLayout
from task_schemas import Coupled
from aind_auto_train.schema.task import DynamicForagingParas

class TaskWidget(BaseDeviceWidget):
    """Widget to edit task"""
    def __init__(self):
        super().__init__(Coupled, {k:v.default for k, v in Coupled.model_fields.items()})

        # Add in line spacer between properties
        widgets = []
        for widget in self.property_widgets.values():
            line = QFrame()
            line.setStyleSheet('QFrame {border: 2px solid grey;}')
            #line.setFixedHeight(100)
            line.setFrameShape(QFrame.VLine)
            widgets.append(widget)
            widgets.append(line)
        # self.widget = create_widget('V', *frames)
        self.setCentralWidget(create_widget('H', *widgets))
        self.layout().setContentsMargins(1, 1, 1, 1)

if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    base = TaskWidget()


    base.show()

    sys.exit(app.exec_())