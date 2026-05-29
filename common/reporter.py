import common
import logging
import typing

class Reporter(object):
    def __init__(self):
        self._messageList = []
        self._prefixStack = []

    def messages(self) -> typing.Sequence[str]:
        return common.ConstSequenceRef(self._messageList)

    def addMessage(self, string: str) -> None:
        prefix = self._formatPrefix()
        self._internalAddMessage(prefix + string)

    def pushPrefix(self, prefix: typing.Optional[str]) -> None:
        self._prefixStack.append(prefix)

    def popPrefix(self) -> None:
        self._prefixStack.pop()

    def _formatPrefix(self) -> str:
        return ''.join(self._prefixStack)

    def _internalAddMessage(self, prefixedString) -> None:
        self._messageList.append(prefixedString)

class LoggingReporter(Reporter):
    def __init__(self, logLevel: int) -> None:
        super().__init__()
        self._logLevel = logLevel

    def _internalAddMessage(self, prefixedString):
        super()._internalAddMessage(prefixedString)
        logging.log(self._logLevel, prefixedString)