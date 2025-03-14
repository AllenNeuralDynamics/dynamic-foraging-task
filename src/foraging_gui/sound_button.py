from PyQt5.QtWidgets import QAction, QWidget, QSlider, QGridLayout, QLabel, QToolButton, QWidgetAction, QMenu
from PyQt5.QtGui import QIcon
from PyQt5.Qt import pyqtSignal, Qt, QMouseEvent

class SoundButton(QToolButton):
    """Button to allow user to play go cue and change volume"""

    leftAttenuationChanged = pyqtSignal(int)
    rightAttenuationChanged = pyqtSignal(int)

    def __init__(self,
                 left_attenuation_db: int = 0,
                 right_attenuation_db: int = 0):

        super().__init__()

        self.setIcon(QIcon(r"resources/speaker.png"))
        self.setCheckable(True)

        self.volume_widget = QWidget()
        self.volume_widget_layout = QGridLayout()
        self.volume_widget.setLayout(self.volume_widget_layout)

        # configure right slider
        self.right_slider = QSlider()
        self.right_slider.setValue(right_attenuation_db)
        self.right_slider.setMaximum(500)
        self.right_slider.setStyleSheet("""
                                        QSlider::groove:horizontal {
                                            border: 1px solid #5c5c5c;
                                            height: 8px;
                                            background: qlineargradient(x1:0, y1:0.5, x2:1, y2:0.5,
                                                                        stop:0 #FFFFFF, stop:1 #0066CC);
                                            border-radius: 4px;
                                        }
                                    
                                        QSlider::handle:horizontal {
                                            background: #007AFF;
                                            border: 2px solid #005BBB;
                                            width: 10px;
                                            height: 10px;
                                            margin: -5px 0;
                                            border-radius: 9px;
                                        }
                                    
                                        QSlider::handle:horizontal:hover {
                                            background: #339AFF;
                                        }
                                    
                                        QSlider::handle:horizontal:pressed {
                                            background: #005BBB;
                                        }
                                    """)
        self.right_slider.setOrientation(Qt.Horizontal)
        self.right_label = QLabel(f"right: {right_attenuation_db} db")
        self.right_slider.valueChanged.connect(lambda value: self.right_label.setText(f"right: {value} db"))
        self.right_slider.valueChanged.connect(self.rightAttenuationChanged.emit)
        self.volume_widget_layout.addWidget(self.right_slider, 0, 0)
        self.volume_widget_layout.addWidget(self.right_label, 0, 1)

        # configure left slider
        self.left_slider = QSlider()
        self.left_slider.setValue(left_attenuation_db)
        self.left_slider.setMaximum(500)
        self.left_slider.setStyleSheet("""
                                        QSlider::groove:horizontal {
                                            border: 1px solid #5c5c5c;
                                            height: 8px;
                                            background: qlineargradient(x1:0, y1:0.5, x2:1, y2:0.5,
                                                                        stop:0 #FFFFFF, stop:1 #CC0000); 
                                            border-radius: 4px;
                                        }
                            
                                        QSlider::handle:horizontal {
                                            background: #FF3333;
                                            border: 2px solid #990000;
                                            width: 10px;
                                            height: 10px;
                                            margin: -5px 0;
                                            border-radius: 9px;
                                        }
                            
                                        QSlider::handle:horizontal:hover {
                                            background: #FF6666;
                                        }
                            
                                        QSlider::handle:horizontal:pressed {
                                            background: #990000;
                                        }
                                    """)
        self.left_slider.setOrientation(Qt.Horizontal)
        self.left_label = QLabel(f"left: {left_attenuation_db} db")
        self.left_slider.valueChanged.connect(lambda value: self.left_label.setText(f"left: {value} db"))
        self.left_slider.valueChanged.connect(self.leftAttenuationChanged.emit)
        self.volume_widget_layout.addWidget(self.left_slider, 1, 0)
        self.volume_widget_layout.addWidget(self.left_label, 1, 1)

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
    from PyQt5.QtWidgets import QApplication, QMainWindow, QToolBar, QToolButton

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