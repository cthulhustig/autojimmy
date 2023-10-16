import common
import typing
from PyQt5 import QtWidgets

class PrefixLabel(QtWidgets.QLabel):
    def __init__(
            self,
            prefix: str,
            text: typing.Optional[str] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self._prefix = prefix
        self._text = None
        self.setText(text)

    def text(self) -> str:
        text = super().text()
        if text.startswith(self._prefix):
            return text[len(self._prefix):]
        return text

    def setText(self, text: str) -> None:
        self._text = text
        return super().setText(self._prefix + self._text if self._text else self._prefix)

    def setNum(self, number: typing.Union[int, float]) -> None:
        self.setText(common.formatNumber(number))

    def setPrefix(
            self,
            prefix: typing.Optional[str] = None
            ) -> None:
        self._prefix = prefix
        self.setText(self._text)

    def clear(self) -> None:
        self._text = None
        super().setText(self._prefix)
