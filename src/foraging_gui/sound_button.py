from PyQt5.Qt import QMouseEvent, Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QGridLayout,
    QLabel,
    QMenu,
    QSpinBox,
    QToolButton,
    QWidget,
    QWidgetAction,
)


class SoundButton(QToolButton):
    """Button to allow user to play go cue and change volume"""

    attenuationChanged = pyqtSignal(int)

    def __init__(self, attenuation: int = 0):

        super().__init__()

        self.setIcon(QIcon(r"resources/speaker.png"))
        self.setCheckable(True)

        self.volume_widget = QWidget()
        self.volume_widget_layout = QGridLayout()
        self.volume_widget.setLayout(self.volume_widget_layout)

        # configure label
        self.label = QLabel("Attenuation: ")
        self.volume_widget_layout.addWidget(self.label, 0, 0)

        # configure spinbox
        self.attenuation_box = QSpinBox()
        self.attenuation_box.setRange(0, 500)
        self.attenuation_box.setValue(attenuation)
        self.attenuation_box.valueChanged.connect(self.attenuationChanged.emit)
        self.volume_widget_layout.addWidget(self.attenuation_box, 0, 1)

        # configure popup window
        self.menu = QMenu()
        self.action = QWidgetAction(self.menu)
        self.action.setDefaultWidget(self.volume_widget)
        self.menu.addAction(self.action)

        # set menu
        self.setMenu(self.menu)
        self.setPopupMode(QToolButton.MenuButtonPopup)


if __name__ == "__main__":
    import sys

    from PyQt5.QtWidgets import (
        QApplication,
        QMainWindow,
        QToolBar,
        QToolButton,
    )

    # Initialize the application
    app = QApplication(sys.argv)

    # Create the main window
    window = QMainWindow()
    window.setWindowTitle("QToolButton in QToolBar Example")

    # Create a toolbar
    toolbar = QToolBar("Main Toolbar")
    window.addToolBar(toolbar)

    # Create a tool button and assign the action
    tool_button = SoundButton()

    # Add the tool button to the toolbar
    toolbar.addWidget(tool_button)

    # Show the main window
    window.show()

    # Run the application
    sys.exit(app.exec())
