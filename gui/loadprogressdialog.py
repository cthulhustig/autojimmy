import gui
import jobs
import logging
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

# This intentionally doesn't inherit from DialogEx. We don't want it saving its size as it
# can cause incorrect sizing if the font scaling is increased then decreased
class LoadProgressDialog(QtWidgets.QDialog):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._loadJob = None

        self._textLabel = QtWidgets.QLabel()
        self._progressBar = QtWidgets.QProgressBar()

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._textLabel)
        windowLayout.addWidget(self._progressBar)

        self.setWindowTitle('Loading')
        self.setLayout(windowLayout)
        self.setWindowFlags(
            ((self.windowFlags() | QtCore.Qt.WindowType.CustomizeWindowHint | QtCore.Qt.WindowType.FramelessWindowHint) & ~QtCore.Qt.WindowType.WindowCloseButtonHint))
        self.setFixedWidth(300)
        self.setSizeGripEnabled(False)

        # Setting up the title bar needs to be done before the window is show to take effect. It
        # needs to be done every time the window is shown as the setting is lost if the window is
        # closed then reshown
        gui.configureWindowTitleBar(widget=self)

    def exec(self) -> int:
        try:
            self._loadJob = jobs.DataLoadJob(
                parent=self,
                progressCallback=self._updateProgress,
                finishedCallback=self._loadingFinished)
        except Exception as ex:
            message = 'Failed to start data load job'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            self.close()

        return super().exec()

    def showEvent(self, e: QtGui.QShowEvent) -> None:
        if not e.spontaneous():
            # Setting up the title bar needs to be done before the window is show to take effect. It
            # needs to be done every time the window is shown as the setting is lost if the window is
            # closed then reshown
            gui.configureWindowTitleBar(widget=self)

        return super().showEvent(e)

    def _updateProgress(
            self,
            item: str,
            current: int,
            total: int
            ) -> None:
        self._textLabel.setText(f'Loading: {item}')
        self._progressBar.setMaximum(int(total))
        self._progressBar.setValue(int(current))

    def _loadingFinished(
            self,
            result: typing.Union[str, Exception]
            ) -> None:
        if isinstance(result, Exception):
            message = 'Failed to load data'
            logging.error(message, exc_info=result)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=result)
            self.close()
        else:
            self.accept()

        self._loadJob = None
