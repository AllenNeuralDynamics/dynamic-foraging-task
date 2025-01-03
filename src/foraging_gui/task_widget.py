from view.widgets.base_device_widget import BaseDeviceWidget, create_widget
from PyQt5.QtWidgets import QWidget, QComboBox, QFrame, QStackedWidget, QVBoxLayout
from task_schemas import Coupled, Uncoupled, RewardN
from pydantic import BaseModel
from typing import Literal
from PyQt5.QtCore import pyqtSignal

def add_border(widget: BaseDeviceWidget, orientation: Literal['H', 'V', 'VH', 'HV'] = 'HV') \
        -> BaseDeviceWidget:
    """
    Add border dividing property widgets in BaseDeviceWidget
    :param widget: widget to add dividers
    :param orientation: orientation to order widgets. H for horizontal, V for vertical, HV or VH for combo
    """

    widgets = []
    for prop_widget in widget.property_widgets.values():
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.addWidget(prop_widget)
        frame.setStyleSheet(f".QFrame {{ border:1px solid grey }} ")
        widgets.append(frame)
    if len(widgets) % 2 != 0 and orientation in ['VH', 'HV']: # add dummy widget so all rows/colums can be created
        widgets.append(QWidget())
    widget.setCentralWidget(create_widget(orientation, *widgets))

    return widget


class TaskWidget(QWidget):
    """Widget to edit task"""

    taskTypeChanged = pyqtSignal(str)
    taskValueChanged = pyqtSignal(str)

    def __init__(self, task_types: dict[str, BaseModel]):
        """
        :param task_types: dictionary where the keys are the names of the tasks and values are the schemas
        """
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

    def currentTask(self) -> BaseDeviceWidget:
        """
        Convenience function to return current widget of stacked_task_widget
        :return current widget of stacked_task_widget
        """

        return self.stacked_task_widget.currentWidget()

    def setTask(self, task_name: str) -> None:
        """
        Set current task programmatically
        :param task_name: name of task to change to
        """

        if task_name not in [self.task_combobox.itemText(i) for i in range(self.task_combobox.count())]:
            raise ValueError(f'{task_name} not a valid task selection.')
        self.task_combobox.setCurrentText(task_name)

if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication
    import sys
    from aind_behavior_services.task_logic import AindBehaviorTaskLogicModel
    from aind_auto_train.schema.task import DynamicForagingParas
    import traceback
    import logging

    behavior_task_logic_model = None

    def widget_property_changed(name, widget):
        """Slot to signal when widget has been changed
        :param name: name of attribute and widget"""

        name_lst = name.split('.')
        value = getattr(widget, name_lst[0])
        setattr(behavior_task_logic_model.task_parameters, name_lst[0], value)
        print(behavior_task_logic_model.task_parameters)

    def widget_task_change(name, ):
        """Slot to signal when task type has been changed
        :param name: name of task
        """

        behavior_task_logic_model = AindBehaviorTaskLogicModel(
        name=name,
        task_parameters=task_types[name]().dict(),
        version='1.6.11')
        for name, widget in task_widget.currentTask().property_widgets.items():
            task_widget.taskValueChanged.emit(name)
        print(behavior_task_logic_model)

    def error_handler(etype, value, tb):
        error_msg = ''.join(traceback.format_exception(etype, value, tb))
        print(error_msg)

    sys.excepthook = error_handler  # redirect std error
    app = QApplication(sys.argv)
    task_types = {'Coupled Baiting': Coupled,
                  'Coupled Without Baiting': Coupled,
                  'Uncoupled': Uncoupled,
                  'Uncoupled Without Baiting': Uncoupled,
                  'RewardN': RewardN}
    task_widget = TaskWidget(task_types=task_types)
    task_widget.show()

    task_widget.taskValueChanged.connect(
        lambda task: widget_property_changed(task, task_widget.currentTask()))
    task_widget.taskTypeChanged.connect(widget_task_change)


    behavior_task_logic_model = AindBehaviorTaskLogicModel(
        name=task_widget.task_combobox.currentText(),
        task_parameters=Coupled().dict(),
        version='1.6.11'
    )

    sys.exit(app.exec_())
