from qtpy.QtCore import Signal, Slot, QTimer
from qtpy.QtGui import QIntValidator, QDoubleValidator
from qtpy.QtWidgets import (
    QWidget,
    QLabel,
    QComboBox,
    QHBoxLayout,
    QVBoxLayout,
    QMainWindow,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QSlider,
    QCheckBox
)
from inspect import currentframe
from importlib import import_module
import enum
import types
import re
import logging
import inflection
from view.widgets.miscellaneous_widgets.q_scrollable_line_edit import QScrollableLineEdit
from view.widgets.miscellaneous_widgets.q_scrollable_float_slider import QScrollableFloatSlider
import inspect
from pydantic import BaseModel
from typing import Literal
from aind_behavior_dynamic_foraging.DataSchemas.task_logic import \
    AindBehaviorTaskLogicModel, AindDynamicForagingTaskParameters

class TaskParameterWidget(QMainWindow):

    def __init__(self, schema: AindBehaviorTaskLogicModel):

        self.log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        super().__init__()
        self.schema = schema
        self.schema_module = import_module(self.schema.__module__)
        widget = self.create_field_widgets(schema.model_dump())
        self.setCentralWidget(create_widget("V", widget))
        self.ValueChangedOutside[str].connect(self.update_field_widget)  # Trigger update when property value changes

    def create_field_widgets(self, fields: dict):
        """Create input widgets based on properties
        :param properties: dictionary containing properties within a class and mapping to values
        :param widget_group: attribute name for dictionary of widgets"""

        widgets = {}
        for name, value in fields.items():
            arg_type = type(value)
            search_name = arg_type.__name__ if arg_type.__name__ in dir(self.schema_module ) else name.split(".")[-1]
            boxes = {"label": QLabel(label_maker(name.split(".")[-1]))}
            if dict not in type(value).__mro__ and list not in type(value).__mro__ or type(arg_type) == enum.EnumMeta:
                # Create combo boxes if there are preset options
                if input_specs := self.check_driver_variables(search_name):
                    boxes[name] = self.create_attribute_widget(name, "combo", input_specs)
                # If no found options, create an editable text box or checkbox
                else:
                    box_type = 'text' if bool not in type(value).__mro__ else 'check'
                    boxes[name] = self.create_attribute_widget(name, box_type, value)

            elif dict in type(value).__mro__:  # deal with dict like variables
                boxes[name] = create_widget(
                    "V", **self.create_field_widgets({f"{name}.{k}": v for k, v in value.items()})
                )
            elif list in type(value).__mro__:  # deal with list like variables
                boxes[name] = create_widget(
                    "H", **self.create_field_widgets({f"{name}.{i}": v for i, v in enumerate(value)})
                )
            orientation = "H"
            if "." in name:  # see if parent list and format index label and input vertically
                parent = pathGet(self.__dict__, name.split(".")[0:-1])
                if list in type(parent).__mro__:
                    orientation = "V"
            widgets[name] = create_widget(orientation, **boxes)

        return widgets

    def check_driver_variables(self, name: str):
        """Check if there is variable in device driver that has name of
        property to inform input widget type and values
        :param name: name of property to search for"""

        driver_vars = self.schema_module.__dict__
        for variable in driver_vars:
            search_name = inflection.pluralize(name.replace(".", "_"))
            x = re.search(variable, rf"\b{search_name}?\b", re.IGNORECASE)
            if x is not None:
                if type(driver_vars[variable]) in [dict, list]:
                    return driver_vars[variable]
                elif type(driver_vars[variable]) == enum.EnumMeta:  # if enum
                    enum_class = driver_vars[variable]
                    return {i.name: i.value for i in enum_class}

    def create_attribute_widget(self, name, widget_type: Literal["combo", "text", "check"], values):
        """Create a widget and create corresponding attribute
                :param name: name of property
                :param widget_type: widget type ('combo', 'text', 'check')
                :param values: input into widget"""

        # options = values.keys() if widget_type == 'combo' else values
        box = getattr(self, f"create_{widget_type}_box")(name, values)
        setattr(self, f"{name}_widget", box)  # add attribute for widget input for easy access

        return box

    def create_text_box(self, name, value) -> QLineEdit or QDoubleSpinBox or QSpinBox:
        """Convenience function to build editable text boxes and add initial value and validator
        :param name: name to emit when text is edited is changed
        :param value: initial value to add to box"""
        value_type = type(value)
        if value_type == int:
            textbox = QSpinBox(value)
            textbox.editingFinished
        else:
            textbox = QLineEdit(str(value))
            textbox.editingFinished.connect(lambda: self.textbox_edited(name))
        return textbox

    def textbox_edited(self, name):
        """
        Correctly set attribute after textbox has been edited
        :param name: name of property that was edited
        :return:
        """

        name_lst = name.split(".")
        value = getattr(self, name + "_widget").text()
        path_set(self.schema, name, value)
        self.ValueChangedInside.emit(name)

    def create_check_box(self, name, value: bool) -> QCheckBox:
        """Convenience function to build checkboxes
        :param name: name to emit when text is edited is changed
        :param value: initial value to add to box
        """

        checkbox = QCheckBox()
        checkbox.setChecked(value)
        checkbox.toggled.connect(lambda state: self.check_box_toggled(name, state))
        return checkbox

    def check_box_toggled(self, name: str, state: bool):
        """
        Correctly set attribute after combobox has been toggles
        :param name: name of property that was edited
        :param state: state of checkbox
        :return:
        """

        name_lst = name.split(".")
        parent_attr = pathGet(self.__dict__, name_lst[0:-1])
        if dict in type(parent_attr).__mro__:  # name is a dictionary
            parent_attr[name_lst[-1]] = state
        elif list in type(parent_attr).__mro__:
            parent_attr[int(name_lst[-1])] = state
        setattr(self, name, state)
        self.ValueChangedInside.emit(name)

    def create_combo_box(self, name, items):
        """Convenience function to build combo boxes and add items
        :param name: name to emit when combobox index is changed
        :param items: items to add to combobox"""

        options = items.keys() if hasattr(items, "keys") else items
        box = QComboBox()
        box.addItems([str(x) for x in options])
        box.currentTextChanged.connect(lambda value: self.combo_box_changed(value, name))
        box.setCurrentText(str(getattr(self, name)))

        return box

    def combo_box_changed(self, value, name):
        """
        Correctly set attribute after combobox index has been changed
        :param value: new value combobox has been changed to
        :param name: name of property that was edited
        :return:
        """

        name_lst = name.split(".")

        parent_attr = pathGet(self.__dict__, name_lst[0:-1])
        if dict in type(parent_attr).__mro__:  # name is a dict
            parent_attr[str(name_lst[-1])] = value_type(value)
        elif list in type(parent_attr).__mro__:  # name is a list

            parent_attr[int(name_lst[-1])] = value_type(value)
        setattr(self, name, value_type(value))
        self.ValueChangedInside.emit(name)

    @Slot(str)
    def update_field_widget(self, name):
        """Update property widget. Triggers when attribute has been changed outside of widget
        :param name: name of attribute and widget"""

        value = getattr(self, name, None)
        if dict not in type(value).__mro__ and list not in type(value).__mro__:  # not a dictionary or list like value
            self._set_widget_text(name, value)
        elif dict in type(value).__mro__:
            for k, v in value.items():  # multiple widgets to set values for
                setattr(self, f"{name}.{k}", v)
                self.update_field_widget(f"{name}.{k}")
        else:
            for i, item in enumerate(value):
                if hasattr(self, f"{name}.{i}"):  # can't handle added indexes yet
                    setattr(self, f"{name}.{i}", item)
                    self.update_field_widget(f"{name}.{i}")

    def _set_widget_text(self, name, value):
        """Set widget text if widget is QLineEdit or QCombobox
        :param name: widget name to set text to
        :param value: value of text"""

        if hasattr(self, f"{name}_widget"):
            widget = getattr(self, f"{name}_widget")
            widget.blockSignals(True)  # block signal indicating change since changing internally
            if hasattr(widget, "setText") and hasattr(widget, "validator"):
                if widget.validator() is None:
                    widget.setText(str(value))
                elif type(widget.validator()) == QIntValidator:
                    widget.setValue(round(value))
                elif type(widget.validator()) == QDoubleValidator:
                    widget.setValue(str(round(value, widget.validator().decimals())))
            elif type(widget) in [QSpinBox, QDoubleSpinBox, QSlider, QScrollableFloatSlider]:
                widget.setValue(value)
            elif type(widget) == QComboBox:
                widget.setCurrentText(str(value))
            elif hasattr(widget, 'setChecked'):
                widget.setChecked(value)
            widget.blockSignals(False)
        else:
            self.log.warning(f"{name} doesn't correspond to a widget")

    def __setattr__(self, name, value):
        """Overwrite __setattr__ to trigger update if property is changed"""
        if name == "schema":    # if schema has been updated, update widgets
            self.__dict__[name] = value
            if currentframe().f_back.f_locals.get("self", None) != self:  # call from outside so update widgets
                self.ValueChangedOutside.emit(name)


# Convenience Functions

def create_widget(struct: str, *args, **kwargs):
    """Creates either a horizontal or vertical layout populated with widgets
    :param struct: specifies whether the layout will be horizontal, vertical, or combo
    :param kwargs: all widgets contained in layout
    :return QWidget()"""

    layouts = {"H": QHBoxLayout(), "V": QVBoxLayout()}
    widget = QWidget()
    if struct == "V" or struct == "H":
        layout = layouts[struct]
        for arg in [*kwargs.values(), *args]:
            try:
                layout.addWidget(arg)
            except TypeError:
                layout.addLayout(arg)

    elif struct == "VH" or "HV":
        bin0 = {}
        bin1 = {}
        j = 0
        for v in [*kwargs.values(), *args]:
            bin0[str(v)] = v
            j += 1
            if j == 2:
                j = 0
                bin1[str(v)] = create_widget(struct=struct[0], **bin0)
                bin0 = {}
        return create_widget(struct=struct[1], **bin1)

    layout.setContentsMargins(0, 0, 0, 0)
    widget.setLayout(layout)
    return widget


def label_maker(string):
    """Removes underscores from variable names and capitalizes words
    :param string: string to make label out of
    """

    possible_units = ["mm", "um", "px", "mW", "W", "ms", "C", "V", "us", "s", "ms", "uL", "min", "g", "mL"]
    label = string.split("_")
    label = [words.capitalize() for words in label]

    for i, word in enumerate(label):
        for unit in possible_units:
            if unit.lower() == word.lower():  # TODO: Consider using regular expression here for better results?
                label[i] = f"[{unit}]"

    label = " ".join(label)
    return label

def path_set(dictionary: dict, path: list[str], value) -> None:
    """
    Set value in a nested dictionary
    :param dictionary: dictionary to set value
    :param path: list of strings that point towards value to set.
    """

    for k in path[:-1]:
        dictionary = dictionary[k]
    dictionary[-1] = value


# def pathGet(iterable: dict or list, path: list):
#     """Based on list of nested dictionary keys or list indices, return inner dictionary"""
#
#     for k in path:
#         k = int(k) if type(iterable) == list else k
#         iterable = iterable.__getitem__(k)
#     return iterable

#
# def add_border(widget: BaseDeviceWidget, orientation: Literal['H', 'V', 'VH', 'HV'] = 'HV') \
#         -> BaseDeviceWidget:
#     """
#     Add border dividing property widgets in BaseDeviceWidget
#     :param widget: widget to add dividers
#     :param orientation: orientation to order widgets. H for horizontal, V for vertical, HV or VH for combo
#     """
#
#     widgets = []
#     for prop_widget in widget.property_widgets.values():
#         frame = QFrame()
#         layout = QVBoxLayout(frame)
#         layout.addWidget(prop_widget)
#         frame.setStyleSheet(f".QFrame {{ border:1px solid grey }} ")
#         widgets.append(frame)
#     if len(widgets) % 2 != 0 and orientation in ['VH', 'HV']:  # add dummy widget so all rows/colums can be created
#         widgets.append(QWidget())
#     widget.setCentralWidget(create_widget(orientation, *widgets))
#
#     return widget
#
#
# class TaskWidget(QWidget):
#     """Widget to edit task"""
#
#     taskTypeChanged = pyqtSignal(str)
#     taskValueChanged = pyqtSignal(str)
#
#     def __init__(self, task_types: dict[str, BaseModel]):
#         """
#         :param task_types: dictionary where the keys are the names of the tasks and values are the schemas
#         """
#         super().__init__()
#
#         self.setLayout(QVBoxLayout())
#
#         self.task_combobox = QComboBox()
#         self.task_combobox.addItems(task_types.keys())
#         self.layout().addWidget(self.task_combobox)
#
#         self.stacked_task_widget = QStackedWidget()
#         self.layout().addWidget(self.stacked_task_widget)
#         for schema in task_types.values():
#             widget = BaseDeviceWidget(schema, schema().dict())
#             # emit signal when widget is changed
#             widget.ValueChangedInside.connect(self.taskValueChanged.emit)
#             widget.ValueChangedOutside.connect(self.taskValueChanged.emit)
#             self.stacked_task_widget.addWidget(add_border(widget))
#
#         self.task_combobox.currentIndexChanged.connect(lambda i: self.stacked_task_widget.setCurrentIndex(i))
#         self.task_combobox.currentTextChanged.connect(self.taskTypeChanged.emit)
#
#     def currentTask(self) -> BaseDeviceWidget:
#         """
#         Convenience function to return current widget of stacked_task_widget
#         :return current widget of stacked_task_widget
#         """
#
#         return self.stacked_task_widget.currentWidget()
#
#     def setTask(self, task_name: str) -> None:
#         """
#         Set current task programmatically
#         :param task_name: name of task to change to
#         """
#
#         if task_name not in [self.task_combobox.itemText(i) for i in range(self.task_combobox.count())]:
#             raise ValueError(f'{task_name} not a valid task selection.')
#        self.task_combobox.setCurrentText(task_name)

if __name__ == "__main__":

    from qtpy.QtWidgets import QApplication
    import sys
    import traceback
    import logging

    behavior_task_logic_model = None

    def error_handler(etype, value, tb):
        error_msg = ''.join(traceback.format_exception(etype, value, tb))
        print(error_msg)


    sys.excepthook = error_handler  # redirect std error
    app = QApplication(sys.argv)
    task_model = AindBehaviorTaskLogicModel(name="coupled",
        task_parameters=AindDynamicForagingTaskParameters(),
        version='1.6.11')
    task_widget = TaskParameterWidget(task_model)
    task_widget.show()

    sys.exit(app.exec_())