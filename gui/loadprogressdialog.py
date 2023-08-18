import gui
import jobs
import logging
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

class LoadProgressDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Loading',
            configSection='LoadProgressDialog',
            parent=parent)

        self._loadJob = None

        self._textLabel = QtWidgets.QLabel()
        self._progressBar = QtWidgets.QProgressBar()

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._textLabel)
        windowLayout.addWidget(self._progressBar)

        self.setLayout(windowLayout)
        self.setWindowFlags(
            ((self.windowFlags() | QtCore.Qt.WindowType.CustomizeWindowHint | QtCore.Qt.WindowType.FramelessWindowHint) & ~QtCore.Qt.WindowType.WindowCloseButtonHint))
        self.setFixedWidth(300)
        self.setSizeGripEnabled(False)

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
