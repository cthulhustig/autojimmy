import app
import datetime
import gui
import jobs
import logging
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

# This intentionally doesn't inherit from DialogEx. We don't want it saving its size as it
# can cause incorrect sizing if the font scaling is increased then decreased
class DownloadProgressDialog(QtWidgets.QDialog):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._downloadJob = None

        self._sectorNameLabel = QtWidgets.QLabel()
        self._remainingTimeLabel = QtWidgets.QLabel()
        self._progressBar = QtWidgets.QProgressBar()
        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self._cancelDownload)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._sectorNameLabel)
        windowLayout.addWidget(self._remainingTimeLabel)
        windowLayout.addWidget(self._progressBar)
        windowLayout.addWidget(self._cancelButton)

        self.setWindowTitle('Downloading')
        self.setLayout(windowLayout)
        self.setWindowFlags(
            ((self.windowFlags() | QtCore.Qt.WindowType.CustomizeWindowHint | QtCore.Qt.WindowType.FramelessWindowHint) & ~QtCore.Qt.WindowType.WindowCloseButtonHint))
        self.setFixedWidth(400)
        self.setSizeGripEnabled(False)

        # Setting up the title bar needs to be done before the window is show to take effect. It
        # needs to be done every time the window is shown as the setting is lost if the window is
        # closed then reshown
        gui.configureWindowTitleBar(widget=self)

    def exec(self) -> int:
        try:
            self._downloadJob = jobs.DataDownloadJob(
                parent=self,
                travellerMapUrl=app.Config.instance().travellerMapUrl(),
                progressCallback=self._updateProgress,
                finishedCallback=self._downloadFinished)
        except Exception as ex:
            message = 'Failed to start download job'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            # Closing a dialog from showEvent doesn't work so schedule it to happen immediately after
            # the window is shown
            QtCore.QTimer.singleShot(0, self.close)

        return super().exec()

    def showEvent(self, e: QtGui.QShowEvent) -> None:
        if not e.spontaneous():
            # Setting up the title bar needs to be done before the window is show to take effect. It
            # needs to be done every time the window is shown as the setting is lost if the window is
            # closed then reshown
            gui.configureWindowTitleBar(widget=self)

        return super().showEvent(e)

    def _cancelDownload(self) -> None:
        if self._downloadJob:
            self._downloadJob.cancel()

    def _updateProgress(
            self,
            item: str,
            current: int,
            total: int,
            remainingTime: typing.Optional[datetime.timedelta] = None
            ) -> None:
        self._sectorNameLabel.setText(f'Downloading: {current}/{total} - {item}')

        if remainingTime:
            # Convert remaining time to a string without microseconds
            remainingTime = str(remainingTime).split(".")[0]
        else:
            remainingTime = 'Unknown'
        self._remainingTimeLabel.setText(f'Estimated Time: {remainingTime}')

        self._progressBar.setMaximum(int(total))
        self._progressBar.setValue(int(current))

    def _downloadFinished(
            self,
            result: typing.Union[str, Exception]
            ) -> None:
        if isinstance(result, Exception):
            message = 'Failed to download data'
            logging.error(message, exc_info=result)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=result)
            self.close()
        elif self._downloadJob and self._downloadJob.isCancelled():
            self.close()
        else:
            self.accept()

        self._downloadJob = None
