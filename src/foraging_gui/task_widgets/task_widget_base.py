from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import (
    QFrame,
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
import re
import inflection
from view.widgets.miscellaneous_widgets.q_scrollable_float_slider import QScrollableFloatSlider
from pydantic import BaseModel
from typing import Literal
import logging
import typing

class TaskWidgetBase(QMainWindow):
    ValueChangedOutside = Signal((str,))
    ValueChangedInside = Signal((str,))

    def __init__(self, schema: BaseModel):

        self.log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        super().__init__()
        self.schema = schema
        self.schema_module = import_module(self.schema.__module__)
        widget = self.create_field_widgets(self.schema.model_dump(),
                                           "task_parameters")
        self.setCentralWidget(create_widget("V", **widget))
        #add_border(self)
        self.ValueChangedOutside[str].connect(self.update_field_widget)  # Trigger update when property value changes

    def create_field_widgets(self, fields: dict,  widget_field: str) -> dict:
        """
        Create input widgets based on properties
        :param fields: dictionary containing properties within a class and mapping to values
        :param model: schema model corresponding to the fields dict
        :param widget_field: attribute name for dictionary of widgets
        :return dictionary of widget with keys corresponding to attribute name
        """
        widgets = {}
        for name, value in fields.items():
            name_lst = name.split(".")
            arg_type = type(value)
            search_name = arg_type.__name__ if arg_type.__name__ in dir(self.schema_module) else name_lst[-1]
            boxes = {"label": QLabel(label_maker(name_lst[-1]))} if not name_lst[-1].isdigit() else {}
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
                    "V", **self.create_field_widgets({f"{name}.{k}": v for k, v in value.items()},
                                                     name)
                )
                setattr(self, name+"_widget", boxes[name])
            elif list in type(value).__mro__:  # deal with list like variables
                boxes[name] = create_widget(
                    "H", **self.create_field_widgets({f"{name}.{i}": v for i, v in enumerate(value)},
                                                     name)
                )
                setattr(self, name+"_widget", boxes[name])
            orientation = "H"
            if "." in name:  # see if parent list and format index label and input vertically
                parent = path_get(self.schema.model_dump(), name_lst[0:-1])
                if list in type(parent).__mro__:
                    orientation = "V"
            widgets[name_lst[-1]] = create_widget(orientation, **boxes)

        # Add attribute of grouped widgets for easy access
        setattr(self, f"{widget_field}_widgets", widgets)
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
                elif type(driver_vars[variable]) == typing._LiteralGenericAlias:
                    return list(typing.get_args(driver_vars[variable]))
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
        if value_type in [int, float]:
            textbox = QSpinBox() if value_type == int else QDoubleSpinBox()
            textbox.setRange(0, 1000000)
            textbox.setValue(value)
            textbox.valueChanged.connect(lambda v: self.textbox_edited(name, v))
        else:
            textbox = QLineEdit(str(value))
            textbox.editingFinished.connect(lambda: self.textbox_edited(name))
        return textbox

    def textbox_edited(self, name, value=None):
        """
        Correctly set attribute after textbox has been edited
        :param name: name of property that was edited
        :param value: new value
        :return:
        """

        name_lst = name.split(".")
        value = value if value else getattr(self, name + "_widget").text()
        path_set(self.schema, name_lst, value)
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
        path_set(self.schema, name_lst, state)
        self.ValueChangedInside.emit(name)

    def create_combo_box(self, name: str, items: dict or list):
        """Convenience function to build combo boxes and add items
        :param name: name to emit when combobox index is changed
        :param items: items to add to combobox"""

        options = items.keys() if hasattr(items, "keys") else items
        box = QComboBox()
        box.addItems([str(x) for x in options])
        box.currentTextChanged.connect(lambda value: self.combo_box_changed(value, name))
        box.setCurrentText(str(path_get(self.schema.model_dump(), name.split("."))))

        return box

    def combo_box_changed(self, value, name):
        """
        Correctly set attribute after combobox index has been changed
        :param value: new value combobox has been changed to
        :param name: name of property that was edited
        :return:
        """

        name_lst = name.split(".")
        value_type = type(path_get(self.schema.model_dump(), name_lst))
        value = value_type[value] if type(value_type) == enum.EnumMeta else value_type(value)
        path_set(self.schema, name_lst, value)
        self.ValueChangedInside.emit(name)

    @Slot(str)
    def update_field_widget(self, name):
        """Update property widget. Triggers when attribute has been changed outside of widget
        :param name: name of attribute and widget"""
        value = path_get(self.schema.model_dump(), name.split("."))
        if dict not in type(value).__mro__ and list not in type(value).__mro__:  # not a dictionary or list like value
            self._set_widget_text(name, value)
        elif dict in type(value).__mro__:
            for k, v in value.items():  # multiple widgets to set values for
                self.update_field_widget(f"{name}.{k}")
        else:  # update list
            for i, item in enumerate(value):
                if hasattr(self, f"{name}.{i}_widget"):  # can't handle added indexes yet
                    self.update_field_widget(f"{name}.{i}")

    def _set_widget_text(self, name, value):
        """Set widget text if widget is QLineEdit or QCombobox
        :param name: widget name to set text to
        :param value: value of text"""
        if hasattr(self, f"{name}_widget"):
            widget = getattr(self, f"{name}_widget")
            widget.blockSignals(True)  # block signal indicating change since changing internally
            if type(widget) in [QLineEdit]:
                widget.setText(str(value))
            elif type(widget) in [QSpinBox, QDoubleSpinBox, QSlider, QScrollableFloatSlider]:
                widget.setValue(value)
            elif type(widget) == QComboBox:
                value_type = type(path_get(self.schema.model_dump(), name.split(".")))
                value = value.name if type(value_type) == enum.EnumMeta else value_type(value)
                widget.setCurrentText(str(value))
            elif hasattr(widget, 'setChecked'):
                widget.setChecked(value)
            widget.blockSignals(False)
        else:
            self.log.warning(f"{name} doesn't correspond to a widget")

    def apply_schema(self, schema: BaseModel):
        """
        Convenience function to apply new schema
        """
        self.schema = schema
        for name in self.schema.model_dump().keys():
            self.update_field_widget(name)

    def __setattr__(self, name, value):
        """Overwrite __setattr__ to trigger update if property is changed"""
        super().__setattr__(name, value)
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

    possible_units = ["mm", "um", "px", "mW", "W", "ms", "C", "V", "us", "s", "ms", "uL", "g", "mL"]
    label = string.split("_")
    label = [words.capitalize() for words in label]

    for i, word in enumerate(label):
        for unit in possible_units:
            if unit.lower() == word.lower():  # TODO: Consider using regular expression here for better results?
                label[i] = f"[{unit}]"

    label = " ".join(label)
    return label


def path_set(iterable: BaseModel, path: list[str], value) -> None:
    """
    Set value in a nested dictionary or list
    :param iterable: dictionary or list to set value
    :param path: list of strings that point towards value to set.
    """

    for i, k in enumerate(path):
        if i != len(path)-1:
            iterable = iterable[int(k)] if type(iterable) == list else getattr(iterable, k)
        else:
            if type(iterable) == list:
                iterable[int(k)] = value
            else:
                setattr(iterable, k, value)

def path_get(iterable: dict or list, path: list[str]):
    """
    Get value in a nested dictionary or listt
    :param iterable: dictionary or list to set value
    :param path: list of strings that point towards value to set.
    :return value found at end of path
    """

    for i, k in enumerate(path):
        k = int(k) if type(iterable) == list else k
        iterable = iterable.__getitem__(k)
    return iterable


#
def add_border(widget: QMainWindow,
               orientation: Literal['H', 'V', 'VH', 'HV'] = 'HV') \
        -> QMainWindow:
    """
    Add border dividing property widgets in BaseDeviceWidget
    :param widget: widget to add dividers
    :param: schema: schema used to create widget
    :param orientation: orientation to order widgets. H for horizontal, V for vertical, HV or VH for combo
    """

    widgets = []
    for name, field_widget in getattr(widget, "task_parameters_widgets").items():
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.addWidget(field_widget)
        frame.setStyleSheet(f".QFrame {{ border:1px solid grey }} ")
        widgets.append(frame)
    if len(widgets) % 2 != 0 and orientation in ['VH', 'HV']:  # add dummy widget so all rows/colums can be created
        widgets.append(QWidget())
    widget.setCentralWidget(create_widget(orientation, *widgets))

    return widget


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication
    import sys
    import traceback
    from aind_behavior_dynamic_foraging.DataSchemas.task_logic import (
        AindDynamicForagingTaskLogic,
        AindDynamicForagingTaskParameters,
        AutoWater,
        AutoStop,
        AutoBlock,
        Warmup
    )


    def error_handler(etype, value, tb):
        error_msg = ''.join(traceback.format_exception(etype, value, tb))
        print(error_msg)


    sys.excepthook = error_handler  # redirect std error
    app = QApplication(sys.argv)
    task_model = AindDynamicForagingTaskLogic(
        task_parameters=AindDynamicForagingTaskParameters(
            auto_water=AutoWater(),
            auto_stop=AutoStop(),
            auto_block=AutoBlock(),
            warmup=Warmup()
        ),
    )
    task_widget = TaskWidgetBase(task_model.task_parameters)
    task_widget.ValueChangedInside.connect(lambda name: print(task_model))
    task_widget.show()

    sys.exit(app.exec_())
