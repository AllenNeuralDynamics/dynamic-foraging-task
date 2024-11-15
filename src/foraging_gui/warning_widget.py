import logging
from queue import Queue
from logging.handlers import QueueHandler
from random import randint
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QScrollArea
import sys
from time import sleep

class WarningWidget(QWidget):
    """Widget that uses a logging QueueHandler to display log errors and warning"""

    def __init__(self, log_tag: str = 'warning_widget',
                 log_level: str = logging.INFO,
                 warning_color: str = 'purple',
                 info_color: str = 'green',
                 error_color: str = 'chocolate',
                 *args, **kwargs):
        """
        :param log_tag: log_tag to pass into filter
        :param log_level: level for QueueHandler
        :param warning_color: color of warning messages
        :param info_color: color of info messages
        :param error_color: color of error messages
        """

        super().__init__(*args, **kwargs)

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # set color for labels
        self._warning_color = warning_color
        self._info_color = info_color
        self._error_color = error_color

        # create vertical layout
        self.setLayout(QVBoxLayout())

        # configure queue handler to write to queue
        self.queue = Queue()
        queue_handler = QueueHandler(self.queue)
        queue_handler.setLevel(log_level)
        queue_handler.addFilter(WarningFilter(log_tag))     # add filter
        queue_handler.setFormatter(logging.Formatter(fmt='%(asctime)s: %(message)s', datefmt='%I:%M:%S %p'))
        self.logger.root.addHandler(queue_handler)

        # create QTimer to periodically check queue
        self.check_timer = QTimer(timeout=self.check_warning_queue, interval=1000)
        self.check_timer.start()

    def check_warning_queue(self) -> None:
        """
        Check queue and update layout with the latest warnings
        """

        while not self.queue.empty():
            log = self.queue.get()

            if log.getMessage()[12:].strip():   # skip empty messages
                label = QLabel(log.getMessage())
                label.setWordWrap(True)
                if log.levelno == logging.WARNING:
                    label.setStyleSheet(f'color: {self._warning_color};')
                elif log.levelno == logging.ERROR:
                    label.setStyleSheet(f'color: {self._error_color};')
                elif log.levelno == logging.INFO:
                    label.setStyleSheet(f'color: {self._info_color};')
                self.layout().insertWidget(0, label)

                # prune layout if too many warnings
                if self.layout().count() == 30:
                    widget = self.layout().itemAt(29).widget()
                    self.layout().removeWidget(widget)

    def setWarningColor(self, color: str) -> None:
        """
        Set color of warning labels
        :param color: color to set text to
        """

        self._warning_color = color
    def warningColor(self) -> str:
        """
        return color of warning labels
        """

        return self._warning_color

    def setInfoColor(self, color: str) -> None:
        """
        Set color of info labels
        :param color: color to set text to
        """

        self._info_color = color

    def infoColor(self) -> str:
        """
        return color of info labels
        """

        return self._info_color

    def setErrorColor(self, color: str) -> None:
        """
        Set color of error labels
        :param color: color to set text to
        """

        self._error_color = color

    def errorColor(self) -> str:
        """
        return color of error labels
        """

        return self._error_color

class WarningFilter(logging.Filter):
    """ Log filter which logs messages with tags that contain keyword"""

    def __init__(self, keyword: str, *args, **kwargs):
        """
        :param keyword: word that filter will look for in tags
        """

        self.keyword = keyword
        super().__init__(*args, **kwargs)

    def filter(self, record):
        """Returns True for a record that matches a log we want to keep."""
        return self.keyword in record.__dict__.get('tags', [])


if __name__ == '__main__':
    app = QApplication(sys.argv)

    logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger()
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel('INFO')
    log_format = '%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(funcName)s:line %(lineno)d:%(message)s'
    log_datefmt = '%I:%M:%S %p'
    stream_handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=log_datefmt))
    logger.root.addHandler(stream_handler)

    scroll = QScrollArea()
    warn_widget = WarningWidget(parent=scroll)
    scroll.setWidget(warn_widget)
    scroll.setWidgetResizable(True)
    scroll.show()


    warnings = ['this is a warning', 'this is also a warning', 'this is a warning too', 'Warn warn warn',
                'are you warned yet?', '']
    infos = ['info dump', 'inspo info', 'too much information']
    errors = ['error 7', 'error 8', 'error 9']

    warning_timer = QTimer(timeout=lambda: logger.warning(warnings[randint(0, 5)],
                                                          extra={'tags': 'warning_widget'}), interval=1000)

    info_timer = QTimer(timeout=lambda: logger.info(infos[randint(0, 2)],
                                                          extra={'tags': 'warning_widget'}), interval=1500)
    error_timer = QTimer(timeout=lambda: logger.error(errors[randint(0, 2)],
                                                    extra={'tags': 'warning_widget'}), interval=1750)

    warning_timer.start()
    sleep(.5)
    info_timer.start()
    sleep(1)
    error_timer.start()
    sleep(1)

    sys.exit(app.exec_())
