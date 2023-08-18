import typing
from PyQt5 import QtWidgets, QtNetwork

class SingletonApplication(QtWidgets.QApplication):
    def __init__(self, appId: str, argv: typing.List[str]) -> None:
        super().__init__(argv)
        self._appId = appId

        self._sendSocket = QtNetwork.QLocalSocket()
        self._sendSocket.connectToServer(self._appId)
        self._alreadyRunning = self._sendSocket.waitForConnected()

        # There's a race condition here where, in theory, another instance could start between this
        # instance finding there are no other instances running and it starting the server. It
        # shouldn't be an issue as the window of opportunity is tiny.

        if not self._alreadyRunning:
            self._server = QtNetwork.QLocalServer()
            self._server.listen(self._appId)
            self._server.newConnection.connect(self._handleConnect)

    def _handleConnect(self) -> None:
        # Another instance of the app was run so bring this instance to the front
        for widget in self.topLevelWidgets():
            if not isinstance(widget, QtWidgets.QMainWindow):
                continue
            windowWidget = widget.window()
            if not windowWidget:
                continue
            window = windowWidget.windowHandle()
            if not window:
                continue
            window.show()
            window.raise_()
            window.requestActivate()

    def isAlreadyRunning(self) -> bool:
        return self._alreadyRunning
