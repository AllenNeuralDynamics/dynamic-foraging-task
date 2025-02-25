from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QWidget
from PyQt5.QtCore import Qt

class QFieldVBoxLayout(QVBoxLayout):
    """
    QVBoxLayout that will set widgets as attributes when added
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__annotations__ = {}

    def addWidget(self, widget: QWidget, attr_name: str = None, *args, **kwargs) -> None:
        """
        Add widget to layout and set as attribute if a name is provided
        :param widget: widget to add
        :param attr_name: optional name of attribute
        """

        super().addWidget(widget, *args, **kwargs)

        if attr_name:
            setattr(self, attr_name, widget)
            self.__annotations__[attr_name] = type(widget)

class QFieldHBoxLayout(QHBoxLayout):
    """
    QHBoxLayout that will set widgets as attributes when added
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__annotations__ = {}

    def addWidget(self, widget: QWidget, attr_name: str = None, *args, **kwargs) -> None:
        """
        Add widget to layout and set as attribute if a name is provided
        :param widget: widget to add
        :param attr_name: optional name of attribute
        """
        super().addWidget(widget, *args, **kwargs)

        if attr_name:
            setattr(self, attr_name, widget)
            self.__annotations__[attr_name] = type(widget)

class QFieldGridLayout(QGridLayout):
    """
    QHBoxLayout that will set widgets as attributes when added
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__annotations__ = {}

    def addWidget(self, widget: QWidget,
                  row: int,
                  column: int,
                  row_span: int = 1,
                  column_span: int = 1,
                  alignment: Qt.Alignment = Qt.Alignment(),
                  attr_name: str = None,
                  *args, **kwargs) -> None:
        """
        Add widget to layout and set as attribute if a name is provided
        :param widget: widget to add
        :param row: row of widget
        :param column: column of widget
        :param row_span: row span of widget
        :param column_span: column span of widget
        :param alignment: alignment of widget
        :param attr_name: optional name of attribute
        """
        super().addWidget(widget, row, column, row_span, column_span, alignment, *args, **kwargs)

        if attr_name:
            setattr(self, attr_name, widget)
            self.__annotations__[attr_name] = type(widget)