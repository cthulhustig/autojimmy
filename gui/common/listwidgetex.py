
import typing
from PyQt5 import QtCore, QtWidgets

class ListWidgetEx(QtWidgets.QListWidget):
    def currentData(self, role: QtCore.Qt.ItemDataRole) -> typing.Any:
        currentItem = self.currentItem()
        return currentItem.data(role) if currentItem else None

