import logging
from queue import Queue
from logging.handlers import QueueHandler
from random import randint
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QScrollArea
import sys


class WarningWidget(QWidget):
    """Widget that uses a logging QueueHandler to display log errors and warning"""

    def __init__(self, log_tag: str = 'warning_widget', log_level: str = 'INFO', *args, **kwargs):
        """
        :param log_tag: log_tag to pass into filter
        :param log_level: level for QueueHandler
        """

        super().__init__(*args, **kwargs)

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # create vertical layout
        self.setLayout(QVBoxLayout())

        # configure queue handler to write to queue
        self.queue = Queue()
        queue_handler = QueueHandler(self.queue)
        queue_handler.setLevel(log_level)
        queue_handler.addFilter(WarningFilter(log_tag))     # add filter
        self.logger.root.addHandler(queue_handler)

        # create QTimer to periodically check queue
        self.check_timer = QTimer(timeout=self.check_warning_queue, interval=1000)
        self.check_timer.start()

    def check_warning_queue(self):
        """
        Check queue and update layout with the latest warnings
        """

        while not self.queue.empty():
            log = self.queue.get()
            label = QLabel(str(log.getMessage()))
            self.layout().insertWidget(0, label)

            # prune layout if too many warnings
            if self.layout().count() == 30:
                widget = self.layout().itemAt(29).widget()
                self.layout().removeWidget(widget)


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

    logger = logging.getLogger()
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logger.root.level)
    logger.root.addHandler(stream_handler)

    warn_widget = WarningWidget()
    warn_widget.show()

    warnings = ['this is a warning', 'this is also a warning', 'this is a warning too', 'Warn warn warn',
                'are you warned yet?']

    warning_timer = QTimer(timeout=lambda: logger.warning(warnings[randint(0, 4)]), interval=1000)
    warning_timer.start()

    sys.exit(app.exec_())
