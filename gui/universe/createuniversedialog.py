import astronomer
import common
import gui
import jobs
import multiverse
import typing
from PyQt5 import QtWidgets, QtCore

# TODO: Load/save previous settings (not name or description)
# TODO: Test description works

class CreateUniverseDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Create Universe',
            configSection='CreateUniverseDialog',
            parent=parent)

        self._universeId = None

        self._setupConfigControls()
        self._setupDialogButtons()

        dialogLayout = QtWidgets.QVBoxLayout()
        dialogLayout.addLayout(self._buttonLayout)

        self.setLayout(dialogLayout)

    def universeId(self) -> typing.Optional[str]:
        return self._universeId

    def _setupConfigControls(self) -> None:
        self._nameEditBox = gui.LineEditEx()
        self._nameEditBox.textChanged.connect(self._nameChanged)

        self._emptyRadioButton = gui.RadioButtonEx('Empty')
        self._travellerMapRadioButton = gui.RadioButtonEx('Traveller Map')

        typeButtonsLayout = gui.VBoxLayoutEx()
        typeButtonsLayout.addWidget(self._emptyRadioButton)
        typeButtonsLayout.addWidget(self._travellerMapRadioButton)

        self._milieuComboBox = gui.EnumComboBox(
            type=astronomer.Milieu,
            value=astronomer.Milieu.M1105)

        self._descriptionEditBox = gui.TextEditEx()

        self._showReportCheckBox = gui.CheckBoxEx()
        self._showReportCheckBox.setChecked(True)

        layout = gui.FormLayoutEx()
        layout.addRow('Content:', typeButtonsLayout)
        layout.addRow('Milieu:', self._milieuComboBox)
        layout.addRow('Description:', self._descriptionEditBox)
        layout.addRow('Show Report:', self._showReportCheckBox)

        self._configGroupBox = QtWidgets.QGroupBox('Universe Configuration')
        self._configGroupBox.setLayout(layout)

    def _setupDialogButtons(self) -> None:
        self._createButton = QtWidgets.QPushButton('Create')
        self._createButton.setDefault(True)
        self._createButton.clicked.connect(self._createClicked)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        self._buttonLayout = QtWidgets.QHBoxLayout()
        self._buttonLayout.addStretch()
        self._buttonLayout.addWidget(self._createButton)
        self._buttonLayout.addWidget(self._cancelButton)

    def _nameChanged(self, text: str) -> None:
        self._createButton.setEnabled(len(text) > 0)

    def _createClicked(self) -> None:
        universeName = self._nameEditBox.text()
        if not universeName:
            gui.MessageBoxEx.critical('The universe must have a name.')
            return

        if multiverse.UniverseManager.instance().universeInfoByName(universeName) is not None:
            gui.MessageBoxEx.critical(f'A universe named {universeName!r} already exists.')
            return

        milieu = self._milieuComboBox.currentEnum()
        description = self._descriptionEditBox.toPlainText()
        importTravellerMap = self._travellerMapRadioButton.isChecked()

        reporter = None
        if self._showReportCheckBox.isChecked():
            reporter = common.Reporter()

        createJob = jobs.CreateUniverseJob(
            name=universeName,
            milieu=milieu.value,
            description=description,
            importTravellerMap=importTravellerMap,
            reporter=reporter)
        progressDlg = gui.ProgressJobDialog()
        progressDlg.addJob(createJob)

        result = progressDlg.exec()
        if result != QtWidgets.QDialog.DialogCode.Accepted:
            return

        self._universeId = createJob.universeId()

        if reporter:
            text = '\n'.join(reporter.messages())
            if not text:
                text = 'No issues when creating universe'

            reportWindow = gui.TextWindow(
                title=f'Universe Creation Report - {universeName}',
                text=text,
                readOnly=True,
                configSection='UniverseCreationReport')
            gui.WindowManager.instance().manageWindow(window=reportWindow)

            # NOTE: This is a hack to bring the report window to the front
            # after the dialog has closed. This is needed as, when the dialog
            # closes, the window that displayed the dialog will become active
            # and be brought in front of the report window
            # TODO: Need to check this works on Linux & MacOS
            QtCore.QTimer.singleShot(0, reportWindow.bringToFront)

        self.accept()