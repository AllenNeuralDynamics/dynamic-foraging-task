from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QWidget

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
