import app
import common
import gui
import typing
from PyQt5 import QtWidgets, QtGui, QtCore

def _blendColor(
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

class _ListItemDelegate(QtWidgets.QStyledItemDelegate):
    _ListItemScale = 0.90

    def __init__(
            self,
            height: int,
            colours: app.TaggingColours,
            parent: typing.Optional[QtCore.QObject] = None
            ) -> None:
        super().__init__(parent)
        self._height = height
        self._colours = app.TaggingColours(colours)

    def height(self) -> int:
        return self._height

    def setHeight(self, height: int) -> None:
        if height == self._height:
            return
        self._height = height

    def colours(self) -> app.TaggingColours:
        return app.TaggingColours(self._colours)

    def setColours(self, colours: app.TaggingColours) -> None:
        if colours == self._colours:
            return

        self._colours = app.TaggingColours(colours)

    def sizeHint(
            self,
            option: 'QtWidgets.QStyleOptionViewItem',
            index: QtCore.QModelIndex
            ) -> QtCore.QSize:
        hint = super().sizeHint(option, index)
        hint.setHeight(int(self._height * _ListItemDelegate._ListItemScale))
        return hint

    def paint(
            self,
            painter: QtGui.QPainter,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
            ) -> None:
        options = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        if isinstance(option.widget, QtWidgets.QWidget):
            colour = option.widget.palette().color(QtGui.QPalette.ColorRole.Background)
            tagLevel = index.data(QtCore.Qt.ItemDataRole.UserRole)
            if tagLevel:
                taggingColour = QtGui.QColor(self._colours.colour(level=tagLevel))
                colour = _blendColor(
                    baseColour=colour,
                    topColour=taggingColour)

            painter.save()
            try:
                painter.fillRect(option.rect, colour)
            finally:
                painter.restore()

        super().paint(painter, option, index)

class TagLevelComboBox(QtWidgets.QComboBox):
    _ComboOptions = {
        'None': None,
        'Desirable': app.TagLevel.Desirable,
        'Warning': app.TagLevel.Warning,
        'Danger': app.TagLevel.Danger
    }

    def __init__(
            self,
            colours: app.TaggingColours,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            value: typing.Optional[app.TagLevel] = None
            ) -> None:
        super().__init__(parent=parent)

        self._colours = app.TaggingColours(colours)
        self._itemDelegate = _ListItemDelegate(
            height=self.height(),
            colours=colours)

        self.setItemDelegate(self._itemDelegate)
        self.currentIndexChanged.connect(self._selectedItemChanged)

        for text, tagLevel in TagLevelComboBox._ComboOptions.items():
            itemIndex = self.count()
            self.addItem(text)
            self.setItemData(itemIndex, tagLevel, QtCore.Qt.ItemDataRole.UserRole)

        if value:
            self.setCurrentTagLevel(value)

    def colours(self) -> app.TaggingColours:
        return app.TaggingColours(self._colours)

    def setColours(self, colours: app.TaggingColours) -> None:
        if colours == self._colours:
            return

        self._colours = app.TaggingColours(colours)
        self._itemDelegate.setColours(colours)
        self.update() # Force redraw

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        # HACK: For reasons I don't understand the size hint for the delegate
        # isn't respected if I just update the existing delegate here. It might
        # be the call to setItemDelegate that is actually fixing it but just
        # updating the existing delegate and calling setItemDelegate with the
        # delegate it's already using results in a crash inside Qt
        self._itemDelegate = _ListItemDelegate(
            height=self.height(),
            colours=self._colours)
        self.setItemDelegate(self._itemDelegate)
        super().resizeEvent(e)

    def currentTagLevel(self) -> app.TagLevel:
        index = self.currentIndex()
        return self.itemData(index, QtCore.Qt.ItemDataRole.UserRole)

    def setCurrentTagLevel(self, tagLevel: app.TagLevel) -> None:
        for index in range(self.count()):
            itemTagLevel = self.itemData(index, QtCore.Qt.ItemDataRole.UserRole)
            if tagLevel == itemTagLevel:
                self.setCurrentIndex(index)
                return

    def _selectedItemChanged(self, index: int):
        tagLevel = self.itemData(index, QtCore.Qt.ItemDataRole.UserRole)
        colour = \
            QtGui.QColor(self._colours.colour(level=tagLevel)) \
            if tagLevel else \
            self._defaultBackgroundColour()
        self._updateBackgroundColour(colour=colour)

    def _defaultBackgroundColour(self) -> QtGui.QColor:
        colour = self.palette().color(self.backgroundRole())
        if not colour:
            colour = self.palette().color(QtGui.QPalette.ColorRole.Background)
        return colour

    def _updateBackgroundColour(
            self,
            colour: QtGui.QColor
            ) -> None:
        if gui.isDarkModeEnabled():
            colour = _blendColor(
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
