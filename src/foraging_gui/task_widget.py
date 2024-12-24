from view.widgets.base_device_widget import BaseDeviceWidget, create_widget
from PyQt5.QtWidgets import QWidget, QComboBox, QFrame, QStackedWidget, QVBoxLayout
from task_schemas import Coupled, Uncoupled, RewardN
from pydantic import BaseModel
from typing import Literal
from PyQt5.QtCore import pyqtSignal

def add_border(widget: BaseDeviceWidget, orientation: Literal['H', 'V', 'VH', 'HV'] = 'VH') \
        -> BaseDeviceWidget:
    """
    Add border dividing property widgets in BaseDeviceWidget
    :param widget: widget to add dividers
    :param orientation: orientation to order widgets. H for horizontal, V for vertical, HV or VH for combo
    """

    widgets = []
    for input in widget.property_widgets.values():
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.addWidget(input)
        #frame.setLayout(layout)
        frame.setStyleSheet(f".QFrame {{ border:1px solid grey }} ")
        widgets.append(frame)
    widget.setCentralWidget(create_widget(orientation, *widgets))

    return widget

class TaskWidget(QWidget):
    """Widget to edit task"""

    taskTypeChanged = pyqtSignal(str)
    taskValueChanged = pyqtSignal(str)
    def __init__(self, task_types: dict[str, BaseModel]):
        super().__init__()

        self.setLayout(QVBoxLayout())

        self.task_combobox = QComboBox()
        self.task_combobox.addItems(task_types.keys())
        self.layout().addWidget(self.task_combobox)

        self.stacked_task_widget = QStackedWidget()
        self.layout().addWidget(self.stacked_task_widget)

        for schema in task_types.values():
            widget = BaseDeviceWidget(schema, schema().dict())
            widget.ValueChangedInside.connect(self.taskValueChanged.emit)  # emit when a widget is changed
            self.stacked_task_widget.addWidget(add_border(widget))

        self.task_combobox.currentIndexChanged.connect(lambda i: self.stacked_task_widget.setCurrentIndex(i))
        self.task_combobox.currentTextChanged.connect(self.taskTypeChanged.emit)


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication
    import sys
    from aind_behavior_services.task_logic import AindBehaviorTaskLogicModel
    from aind_auto_train.schema.task import DynamicForagingParas


    def widget_property_changed(name, widget):
        """Slot to signal when widget has been changed
        :param name: name of attribute and widget"""

        name_lst = name.split('.')
        value = getattr(widget, name_lst[0])
        setattr(behavior_task_logic_model.task_parameters, name_lst[0], value)
        print(behavior_task_logic_model.task_parameters)

    app = QApplication(sys.argv)
    task_widget = TaskWidget(task_types={'Coupled Baiting': Coupled,
                                  'Coupled Without Baiting': Coupled,
                                  'Uncoupled': Uncoupled,
                                  'Uncoupled Without Baiting': Uncoupled,
                                  'RewardN': RewardN})

    task_widget.show()
    task_widget.taskTypeChanged.connect(lambda task: print(task))
    task_widget.taskValueChanged.connect(lambda task: widget_property_changed(task, task_widget.stacked_task_widget.currentWidget()))

    behavior_task_logic_model = AindBehaviorTaskLogicModel(
        name=task_widget.task_combobox.currentText(),
        task_parameters=Coupled().dict(),
        version='1.6.11'
    )

    sys.exit(app.exec_())
