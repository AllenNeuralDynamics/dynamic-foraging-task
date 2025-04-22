from datetime import datetime

from aind_behavior_services.session import AindBehaviorSessionModel
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QLabel, QTextEdit

from foraging_gui.schema_widgets.schema_widget_base import (
    SchemaWidgetBase,
    create_widget,
)


class SessionParametersWidget(SchemaWidgetBase):
    """
    Widget to expose fields from session models
    """

    def __init__(self, schema: AindBehaviorSessionModel):
        super().__init__(schema)

        # hide unnecessary widgets
        self.schema_fields_widgets["version"].hide()
        self.schema_fields_widgets["root_path"].hide()
        self.schema_fields_widgets["date"].hide()
        self.schema_fields_widgets["session_name"].hide()
        self.schema_fields_widgets["experiment_version"].hide()
        self.schema_fields_widgets["commit_hash"].hide()
        self.schema_fields_widgets["allow_dirty_repo"].hide()
        self.schema_fields_widgets["skip_hardware_validation"].hide()
        self.schema_fields_widgets["aind_behavior_services_pkg_version"].hide()

        # change notes to QTextEdit
        self.notes_widget = QTextEdit()
        self.notes_widget.textChanged.connect(
            lambda: self.text_edit_changed("notes")
        )
        self.schema_fields_widgets["notes"].deleteLater()
        self.schema_fields_widgets["notes"] = create_widget(
            "V", QLabel("Notes:"), self.notes_widget
        )
        self.centralWidget().layout().insertWidget(
            -1, self.schema_fields_widgets["notes"]
        )

        # change experiment to combo box
        self.create_attribute_widget(
            "experiment",
            "combo",
            [
                "Coupled Baiting",
                "Coupled Without Baiting",
                "Uncoupled Baiting",
                "Uncoupled Without Baiting",
                "RewardN",
            ],
        )
        self.schema_fields_widgets["experiment"].deleteLater()
        self.schema_fields_widgets["experiment"] = create_widget(
            "H", QLabel("Experiment"), self.experiment_widget
        )
        self.centralWidget().layout().insertWidget(
            0, self.schema_fields_widgets["experiment"]
        )

        # add validation for subject id
        self.subject_widget.setValidator(QIntValidator())

    def text_edit_changed(self, name):
        """
        Update schema when text edit is changed
        :param name: name of parameter
        """

        name_lst = name.split(".")
        value = getattr(self, f"{name}_widget").toPlainText()
        self.path_set(self.schema, name_lst, value)
        self.ValueChangedInside.emit(name)


if __name__ == "__main__":
    import subprocess
    import sys
    import traceback

    from PyQt5.QtWidgets import QApplication

    import foraging_gui

    def error_handler(etype, value, tb):
        error_msg = "".join(traceback.format_exception(etype, value, tb))
        print(error_msg)

    sys.excepthook = error_handler  # redirect std error
    app = QApplication(sys.argv)
    task_model = schema = AindBehaviorSessionModel(
        experiment="Coupled Baiting",
        experimenter=["Chris P. Bacon"],
        date=datetime.now(),  # update when folders are created
        root_path="",  # update when created
        session_name="",  # update when date and subject are filled in
        subject="",
        experiment_version=foraging_gui.__version__,
        notes="",
        commit_hash=subprocess.check_output(["git", "rev-parse", "HEAD"])
        .decode("ascii")
        .strip(),
        allow_dirty_repo=subprocess.check_output(
            ["git", "diff-index", "--name-only", "HEAD"]
        )
        .decode("ascii")
        .strip()
        != "",
        skip_hardware_validation=True,
    )
    task_widget = SessionParametersWidget(task_model)
    task_widget.ValueChangedInside.connect(lambda name: print(task_model))
    task_widget.show()

    sys.exit(app.exec_())
