import app
import common
import gui
import typing
from PyQt5 import QtWidgets, QtGui, QtCore

class TagLevelComboBox(QtWidgets.QComboBox):
    class _ItemStyleDelegate(QtWidgets.QStyledItemDelegate):
        def __init__(
                self,
                height: int
                ) -> None:
            super().__init__()
            self._height = height

        def sizeHint(
                self,
                option: 'QtWidgets.QStyleOptionViewItem',
                index: QtCore.QModelIndex
                ) -> QtCore.QSize:
            hint = super().sizeHint(option, index)
            hint.setHeight(self._height)
            return hint

    _ComboOptions = {
        'None': None,
        'Desirable': app.TagLevel.Desirable,
        'Warning': app.TagLevel.Warning,
        'Danger': app.TagLevel.Danger
    }

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            value: typing.Optional[app.TagLevel] = None
            ) -> None:
        super().__init__(parent=parent)

        self.setAutoFillBackground(True)
        self.currentIndexChanged.connect(self._selectedItemChanged)

        for text, tagLevel in TagLevelComboBox._ComboOptions.items():
            itemIndex = self.count()
            self.addItem(text)
            self.setItemData(itemIndex, tagLevel, QtCore.Qt.ItemDataRole.UserRole)

            if tagLevel is app.TagLevel.Desirable:
                colour = app.ConfigEx.instance().asObject(
                    option=app.ConfigOption.DesirableTagColour,
                    objectType=QtGui.QColor)
            elif tagLevel is app.TagLevel.Warning:
                colour = app.ConfigEx.instance().asObject(
                    option=app.ConfigOption.WarningTagColour,
                    objectType=QtGui.QColor)
            elif tagLevel is app.TagLevel.Danger:
                colour = app.ConfigEx.instance().asObject(
                    option=app.ConfigOption.DangerTagColour,
                    objectType=QtGui.QColor)
            else:
                colour = QtWidgets.QApplication.palette().color(self.backgroundRole())

            self.setItemData(itemIndex, colour, QtCore.Qt.ItemDataRole.BackgroundRole)

        if value:
            self.setCurrentTagLevel(value)

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        self.setItemDelegate(TagLevelComboBox._ItemStyleDelegate(self.size().height()))
        return super().resizeEvent(e)

    def currentTagLevel(self) -> app.TagLevel:
        index = self.currentIndex()
        return self.itemData(index, QtCore.Qt.ItemDataRole.UserRole)

    def setCurrentTagLevel(self, tagLevel: app.TagLevel) -> None:
        for index in range(self.count()):
            itemTagLevel = self.itemData(index, QtCore.Qt.ItemDataRole.UserRole)
            if tagLevel == itemTagLevel:
                self.setCurrentIndex(index)
                return

    def setBackgroundRole(self, role: QtGui.QPalette.ColorRole) -> None:
        result = super().setBackgroundRole(role)

        for itemIndex in range(self.count()):
            tagLevel = self.itemData(itemIndex, QtCore.Qt.ItemDataRole.UserRole)
            if not tagLevel:
                colour = QtWidgets.QApplication.palette().color(role)
                self.setItemData(itemIndex, colour, QtCore.Qt.ItemDataRole.BackgroundRole)

        colour = self.itemData(self.currentIndex(), QtCore.Qt.ItemDataRole.BackgroundRole)
        if not colour:
            colour = self._defaultBackgroundColour()
        self._updateBackgroundColour(colour=colour)

        return result

    def _selectedItemChanged(self, index: int):
        colour = self.itemData(index, QtCore.Qt.ItemDataRole.BackgroundRole)
        if not colour:
            colour = self._defaultBackgroundColour()
        self._updateBackgroundColour(colour=colour)

    def _defaultBackgroundColour(self) -> QtGui.QColor:
        colour = QtWidgets.QApplication.palette().color(self.backgroundRole())
        if not colour:
            colour = QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.Base)
        return colour

    def _updateBackgroundColour(
            self,
            colour: QtGui.QColor
            ) -> None:
        if gui.isDarkModeEnabled():
            colour = TagLevelComboBox.blendColor(
                baseColour=self._defaultBackgroundColour(),
                topColour=colour)

        palette = self.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Button, colour)
        self.setPalette(palette)

    @staticmethod
    def blendColor(
            baseColour: QtGui.QColor,
            topColour: QtGui.QColor
            ) -> QtGui.QColor:
        alpha = topColour.alpha() / 255
        clampToByte = lambda value: common.clamp(round(value), 0, 255)
        blended = QtGui.QColor(
            clampToByte(baseColour.red() * (1.0 - alpha) + (topColour.red() * alpha)),
            clampToByte(baseColour.green() * (1.0 - alpha) + (topColour.green() * alpha)),
            clampToByte(baseColour.blue() * (1.0 - alpha) + (topColour.blue() * alpha)),
            255)
        return blended
