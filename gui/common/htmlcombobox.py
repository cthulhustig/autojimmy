import gui
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

# Based on code from here
# https://stackoverflow.com/questions/21141757/pyqt-different-colors-in-a-single-row-in-a-combobox
class _HtmlItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._document = QtGui.QTextDocument(self)
        self._displayMap: typing.Dict[str, str] = {}

    def addDisplayMapping(self, key: str, display: str) -> None:
        self._displayMap[key] = display

    def removeDisplayMapping(self, key: str) -> None:
        if key in self._displayMap:
            del self._displayMap[key]

    def clearDisplayMappings(self) -> None:
        self._displayMap.clear()

    def paint(
            self,
            painter: QtGui.QPainter,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
            ) -> None:
        options = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        if options.widget is not None:
            style = options.widget.style()
        else:
            style = QtWidgets.QApplication.style()

        self._document.setHtml(self._displayMap.get(options.text, options.text))
        options.text = ''
        style.drawControl(QtWidgets.QStyle.ControlElement.CE_ItemViewItem, options, painter)
        context = QtGui.QAbstractTextDocumentLayout.PaintContext()
        if options.state & QtWidgets.QStyle.StateFlag.State_Selected:
            context.palette.setColor(
                QtGui.QPalette.ColorRole.Text, options.palette.color(
                    QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.HighlightedText))
        textRect = style.subElementRect(
            QtWidgets.QStyle.SubElement.SE_ItemViewItemText, options)
        painter.save()
        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        self._document.documentLayout().draw(painter, context)
        painter.restore()

    def sizeHint(
            self,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
            ) -> QtCore.QSize:
        options = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        self._document.setHtml(self._displayMap.get(options.text, options.text))
        self._document.setTextWidth(options.rect.width())
        return QtCore.QSize(int(self._document.idealWidth()),
                            int(self._document.size().height()))

class HtmlComboBox(gui.ComboBoxEx):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._document = QtGui.QTextDocument(self)
        self._delegate = _HtmlItemDelegate(self)
        self.setItemDelegate(self._delegate)
        self.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLength)

    def addHtmlItem(
            self,
            text: str,
            displayHtml: str,
            userData: typing.Any = None
            ) -> None:
        self._delegate.addDisplayMapping(key=text, display=displayHtml)
        self.addItem(text, userData)

    def insertHtmlItem(
            self,
            index: int,
            text: str,
            displayHtml: str,
            userData: typing.Any = None
            ) -> None:
        self._delegate.addDisplayMapping(key=text, display=displayHtml)
        self.insertItem(index, text, userData)

    def removeItem(self, index: int) -> None:
        if index < self.count():
            itemText = self.itemText(index)
            self._delegate.removeDisplayMapping(itemText)
        super().removeItem(index)

    def clear(self) -> None:
        self._delegate.clearDisplayMappings()
        super().clear()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtWidgets.QStylePainter(self)
        painter.setPen(self.palette().color(QtGui.QPalette.ColorRole.Text))
        options = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(options)
        self._document.setHtml(options.currentText)
        options.currentText = self._document.toPlainText()
        painter.drawComplexControl(QtWidgets.QStyle.ComplexControl.CC_ComboBox, options)
        painter.drawControl(QtWidgets.QStyle.ControlElement.CE_ComboBoxLabel, options)
