import gui
import typing
from PyQt5 import QtGui, QtWidgets, QtCore

class InfoDialog(gui.DialogEx):
    # Use a separate config section for the no show again flag as it makes it easier to
    # reset it if needed
    _NoShowAgainConfigSection = 'NoShowAgain'

    def __init__(
            self,
            title: typing.Optional[str] = None,
            configSection: typing.Optional[str] = None,
            text: typing.Optional[str] = None,
            html: typing.Optional[str] = None,
            noShowAgainId: typing.Optional[str] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title=title,
            configSection=configSection,
            parent=parent)

        self._noShowAgainId = noShowAgainId

        self._textEdit = gui.ContentSizedTextEdit()
        self._textEdit.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Preferred)
        self._textEdit.setReadOnly(True)

        self._noShowAgain = gui.CheckBoxEx('Don\'t show again')
        if self._noShowAgainId:
            self._noShowAgain.hide()

        self._closeButton = QtWidgets.QPushButton('Close')
        self._closeButton.clicked.connect(self.accept)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.addWidget(self._noShowAgain)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._closeButton)

        dialogLayout = QtWidgets.QVBoxLayout()
        dialogLayout.addWidget(self._textEdit, 1)
        dialogLayout.addLayout(buttonLayout, 0)

        self.setLayout(dialogLayout)

        if text != None:
            self.setText(text)
        elif html != None:
            self.setHtml(html)

        self.enableNoShowAgain(noShowAgainId)

        # Set base size, height doesn't mater as the adjustSize will be called when the dialog is
        # displayed causing it to change height to fit the content
        self.resize(450, 600)

    def text(self) -> str:
        return self._textEdit.toPlainText()

    def setText(
            self,
            text: str
            ) -> None:
        self._textEdit.setText(text)

    def html(self) -> str:
        return self._textEdit.toHtml()

    def setHtml(
            self,
            html: str
            ) -> None:
        self._textEdit.setHtml(html)

    def enableNoShowAgain(
            self,
            enable: bool
            ) -> None:
        if enable:
            self._noShowAgain.show()
        else:
            self._noShowAgain.hide()

    def noShowAgain(self) -> bool:
        return self._noShowAgain.isChecked()

    def setNoShowAgain(self, checked: bool) -> None:
        self._noShowAgain.setChecked(checked)

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        # Adjust size to make dialog height change to better fit content. This can't be done until
        # the dialog is shown
        self.updateGeometry()
        self.adjustSize()
        return super().firstShowEvent(e)

    def exec(self) -> int:
        if self._shouldAutoClose():
            return QtWidgets.QDialog.DialogCode.Accepted

        return super().exec()

    def accept(self) -> None:
        if self._noShowAgainId:
            self._settings.beginGroup(InfoDialog._NoShowAgainConfigSection)
            self._settings.setValue(self._noShowAgainId, self._noShowAgain.isChecked())
            self._settings.endGroup()

        return super().accept()

    def _shouldAutoClose(self) -> bool:
        if not self._noShowAgainId:
            return False

        # Can't use self._settings as this is called before the dialog is shown
        settings = gui.globalWindowSettings()
        settings.beginGroup(InfoDialog._NoShowAgainConfigSection)
        autoClose = gui.safeLoadSetting(
            settings=settings,
            key=self._noShowAgainId,
            type=bool)
        settings.endGroup()
        return autoClose
