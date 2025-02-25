from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
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
    QCheckBox,
    QGroupBox,
    QLayout,
    QRadioButton
)
from q_field_box_layout import QFieldVBoxLayout, QFieldHBoxLayout, QFieldGridLayout
from inspect import currentframe
from importlib import import_module
import enum
import re
import inflection
from pydantic import BaseModel
from typing import Literal
import logging
import typing

from hypothesis import given

from hypothesis_jsonschema import from_schema

TYPE_MAP = {'string': str, "number": float, "integer": int, "boolean": bool, "array": list, "null": None}


class SchemaWidgetBase(QMainWindow):
    ValueChangedOutside = pyqtSignal((str,))
    ValueChangedInside = pyqtSignal((str,))

    def __init__(self, schema: BaseModel):

        self.log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.__annotations__ = {}

        super().__init__()
        self.schema = schema
        self.schema_module = import_module(self.schema.__module__)
        self.model_json_schema = self.schema.model_json_schema()
        layout = QFieldGridLayout()
        self.create_field_widgets(self.model_json_schema["properties"], layout)
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.ValueChangedOutside[str].connect(self.update_field_widget)  # Trigger update when property value changes

    def create_field_widgets(self, fields: dict, layout: QFieldGridLayout) -> None:
        """
        Create input widgets based on properties
        :param fields: dictionary containing properties within a class and mapping to values
        :param layout: layout to put widgets
        :return dictionary of widget with keys corresponding to attribute name
        """

        for name, json_schema in fields.items():
            name_lst = name.split(".")
            value = self.get_value(name_lst, json_schema)
            arg_type = TYPE_MAP[json_schema.get("type", "null")]

            # create groupbox and corresponding layout to use if json schema outline an object or list
            groupbox = QGroupBox()
            groupbox.setTitle(label_maker(name_lst[-1]))
            field_layout = QFieldGridLayout()
            row = layout.rowCount() + 1

            if arg_type is not None:
                label = QLabel(label_maker(name_lst[-1])) if not name_lst[-1].isdigit() else QLabel()
                # Create combo boxes if there are preset options
                if "enum" in json_schema.keys():
                    layout.addWidget(label, row, 0, alignment=Qt.AlignRight, attr_name=f"{name_lst[-1]}_label")
                    layout.addWidget(self.create_attribute_widget(name, "combo", json_schema["enum"]),
                                     row, 1, attr_name=name_lst[-1])

                elif json_schema["type"] == "array":  # deal with list like variables
                    setattr(self, name, field_layout)
                    self.__annotations__[name] = QFieldGridLayout  # add to class annotations
                    self.create_field_widgets({f"{name}.{i}": json_schema["items"] for i, v in
                                               enumerate(value)}, field_layout)

                else:  # If no found options, create an editable text box or checkbox
                    layout.addWidget(label, row, 0, alignment=Qt.AlignRight, attr_name=f"{name_lst[-1]}_label")
                    box_type = 'text' if bool not in type(value).__mro__ else 'check'
                    layout.addWidget(self.create_attribute_widget(name, box_type, value), row, 1,
                                     attr_name=name_lst[-1])

            elif "$ref" in json_schema.keys():  # deal with dict like variables
                ref = self.path_get(self.model_json_schema, json_schema["$ref"].split("/")[1:])
                if "properties" in ref.keys():
                    # create vertical layout
                    setattr(self, name, field_layout)
                    self.__annotations__[name] = QFieldGridLayout  # add to class annotations
                    self.create_field_widgets({f"{name}.{k}": v for k, v in ref["properties"].items()}, field_layout)
                else:
                    self.create_field_widgets({name: ref}, layout)

            elif "anyOf" in json_schema.keys():
                # handle optional types
                if len(json_schema["anyOf"]) == 2 and {'type': 'null'} in json_schema["anyOf"]:
                    radio_button = QRadioButton()
                    radio_button.setAutoExclusive(False)
                    radio_button.toggled.connect(lambda toggle, json=json_schema, n=name:
                                                 self.toggle_optional_field(n, json, toggle))
                    self.create_field_widgets({f"{name}": json_schema["anyOf"][0]}, layout)
                    layout.addWidget(radio_button, row, 0, attr_name=f"{name_lst[-1]}_radio")
                else:
                    setattr(self, name, field_layout)
                    for types in json_schema["anyOf"]:
                        if types != {'type': 'null'}:
                            radio_button = QRadioButton()
                            field_layout.addWidget(radio_button, row, 0)
                            self.create_field_widgets({f"{name}": types}, field_layout)

            if field_layout.count() != 0:
                groupbox.setLayout(field_layout)
                layout.addWidget(groupbox, row, 0, 1, 2)

        return layout

    def get_value(self, name_lst: list, json_schema: dict):
        """
        Create a value for schema input
        """

        return self.path_get(self.schema, name_lst)

    def toggle_optional_field(self, name: str, json_schema: dict, enabled: bool) -> None:
        """
        Add or remove optional field
        :param name: name of field
        :param json_schema: schema of parameter
        :param enabled: whether to add or remove field
        """

        name_lst = name.split(".")

        # disable widget
        layout = getattr(self, name_lst[0])
        for n in name_lst:
            layout = getattr(self, n)
        for i in range(layout.count()):
            layout.itemAt(i).widget().setEnabled(enabled)

        if enabled:
            value = from_schema(json_schema)
            print(value)
            # if "default" in json_schema.keys():
            #     value = json_schema["default"]
            # else:
            #     value = from_schema(json_schema)

        # for widget in widgets.values():
        #     widget.setEnabled(enabled)
        # name_lst = name.split(".")
        # if enabled:
        #     self.path_set(self.schema, name_lst, value)
        # else:
        #     self.path_set(self.schema, name_lst, None)
        # self.ValueChangedInside.emit(name)

    def create_attribute_widget(self, name, widget_type: Literal["combo", "text", "check"], values):
        """Create a widget and create corresponding attribute
                :param name: name of property
                :param widget_type: widget type ('combo', 'text', 'check')
                :param values: input into widget"""

        box = getattr(self, f"create_{widget_type}_box")(name, values)
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
        value = value if value else self.path_get(self, name_lst).text()
        self.path_set(self.schema, name_lst, value)
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
        self.path_set(self.schema, name_lst, state)
        self.ValueChangedInside.emit(name)

    def create_combo_box(self, name: str, items: dict or list):
        """Convenience function to build combo boxes and add items
        :param name: name to emit when combobox index is changed
        :param items: items to add to combobox"""

        options = items.keys() if hasattr(items, "keys") else items
        box = QComboBox()
        box.addItems([str(x) for x in options])
        box.currentTextChanged.connect(lambda value: self.combo_box_changed(value, name))
        box.setCurrentText(str(self.path_get(self.schema, name.split("."))))

        return box

    def combo_box_changed(self, value, name):
        """
        Correctly set attribute after combobox index has been changed
        :param value: new value combobox has been changed to
        :param name: name of property that was edited
        :return:
        """

        name_lst = name.split(".")
        value_type = type(self.path_get(self.schema, name_lst))
        value = value_type[value] if enum in value_type.__mro__ else value_type(value)
        self.path_set(self.schema, name_lst, value)
        self.ValueChangedInside.emit(name)

    def update_field_widget(self, name):
        """Update property widget. Triggers when attribute has been changed outside of widget
        :param name: name of attribute and widget"""
        value = self.path_get(self.schema, name.split("."))
        if dict not in type(value).__mro__ and list not in type(value).__mro__ and BaseModel not in type(
                value).__mro__:  # not a dictionary or list like value
            self._set_widget_text(name, value)
        elif dict in type(value).__mro__ or BaseModel in type(value).__mro__:
            value = value.model_dump() if BaseModel in type(value).__mro__ else value
            for k, v in value.items():  # multiple widgets to set values for
                self.update_field_widget(f"{name}.{k}")
        else:  # update list
            for i, item in enumerate(value):
                self.update_field_widget(f"{name}.{i}")

    def _set_widget_text(self, name, value):
        """Set widget text if widget is QLineEdit or QCombobox
        :param name: widget name to set text to
        :param value: value of text"""

        try:
            widget = self.path_get(self, name.split("."))
            widget.blockSignals(True)  # block signal indicating change since changing internally
            if type(widget) in [QLineEdit]:
                widget.setText(str(value))
            elif type(widget) in [QSpinBox, QDoubleSpinBox, QSlider]:
                widget.setValue(value)
            elif type(widget) == QComboBox:
                value_type = type(self.path_get(self.schema, name.split(".")))
                value = value.name if type(value_type) == enum.EnumMeta else value_type(value)
                widget.setCurrentText(str(value))
            elif hasattr(widget, 'setChecked'):
                widget.setChecked(value)
            widget.blockSignals(False)
        except:
            self.log.warning(f"{name} doesn't correspond to a widget")

    def apply_schema(self, schema: BaseModel = None):
        """
        Convenience function to apply new schema
        """
        self.schema = schema if not schema else self.schema
        for name in self.schema.model_dump().keys():
            try:
                self.update_field_widget(name)
            except RuntimeError as e:
                if "has been deleted" not in str(e):  # catch errors not related to deleted widgets
                    raise RuntimeError(e)

    def __setattr__(self, name, value):
        """Overwrite __setattr__ to trigger update if property is changed"""
        super().__setattr__(name, value)
        self.__dict__[name] = value
        if currentframe().f_back.f_locals.get("self", None) != self:  # call from outside so update widgets
            self.ValueChangedOutside.emit(name)

    @staticmethod
    def path_set(iterable: BaseModel, path: list[str], value) -> None:
        """
        Set value in a nested dictionary or list
        :param iterable: dictionary or list to set value
        :param path: list of strings that point towards value to set.
        """

        for i, k in enumerate(path):
            if i != len(path) - 1:
                iterable = iterable[int(k)] if type(iterable) == list else getattr(iterable, k)
            else:
                if type(iterable) == list:
                    iterable[int(k)] = value
                else:
                    setattr(iterable, k, value)

    @staticmethod
    def path_get(iterable: BaseModel, path: list[str]):
        """
        Get value in a nested dictionary or listt
        :param iterable: dictionary or list to set value
        :param path: list of strings that point towards value to set.
        :return value found at end of path
        """

        for i, k in enumerate(path):
            k = int(k) if type(iterable) == list else k
            iterable = iterable[k] if type(iterable) in [list, dict] else getattr(iterable, k)
        return iterable


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


#
def add_border(widget: SchemaWidgetBase,
               widget_group: dict = None,
               orientation: Literal['H', 'V', 'VH', 'HV'] = 'HV') \
        -> SchemaWidgetBase:
    """
    Add border dividing property widgets in BaseDeviceWidget
    :param widget: widget to add dividers
    :param widget_group: dictionary of widgets to add border to. If None, default is schema_fields_widgets
    :param: schema: schema used to create widget
    :param orientation: orientation to order widgets. H for horizontal, V for vertical, HV or VH for combo
    """

    widgets = []
    widget_group = widget_group if widget_group else widget.schema_fields_widgets
    for name, field_widget in widget_group.items():
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
    from PyQt5.QtWidgets import QApplication
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
    from pprint import pprint

    # pprint(AindDynamicForagingTaskParameters.model_json_schema())
    task_model = AindDynamicForagingTaskLogic(
        task_parameters=AindDynamicForagingTaskParameters(
            # uncoupled_reward = None,
            auto_water=AutoWater(),
            auto_stop=AutoStop(),
            auto_block=AutoBlock(),
            warmup=Warmup()
        ),
    )
    task_widget = SchemaWidgetBase(task_model.task_parameters)
    task_widget.ValueChangedInside.connect(lambda name: print(task_model))
    task_widget.show()
    sys.exit(app.exec_())
