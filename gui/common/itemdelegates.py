import typing
from PyQt5 import QtCore, QtGui, QtWidgets

class StyledItemDelegateEx(QtWidgets.QStyledItemDelegate):
    def __init__(
            self,
            parent: typing.Optional[QtCore.QObject] = None
            ) -> None:
        super().__init__(parent)
        self._highlightCurrentItem = True

    def highlightCurrentItem(self) -> bool:
        return self._highlightCurrentItem

    def setHighlightCurrentItem(
            self,
            enabled: bool
            ) -> None:
        self._highlightCurrentItem = enabled

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        itemOption = QtWidgets.QStyleOptionViewItem(option)
        if not self._highlightCurrentItem and option.state & QtWidgets.QStyle.StateFlag.State_HasFocus:
            itemOption.state = itemOption.state ^ QtWidgets.QStyle.StateFlag.State_HasFocus
        super().paint(painter, itemOption, index)

class HtmlItemDelegate(StyledItemDelegateEx):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._document = QtGui.QTextDocument(self)

    def paint(
            self,
            painter: QtGui.QPainter,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
            ) -> None:
        options = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        if isinstance(options.widget, QtWidgets.QWidget):
            style = options.widget.style()
        else:
            style = QtWidgets.QApplication.style()

        text = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        if text:
            self._document.setHtml(text)
        else:
            self._document.clear()

        options.text = ''
        style.drawControl(QtWidgets.QStyle.ControlElement.CE_ItemViewItem, options, painter)
        context = QtGui.QAbstractTextDocumentLayout.PaintContext()
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
        text = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        if text:
            self._document.setHtml(text)
        else:
            self._document.clear()
        return QtCore.QSize(int(self._document.idealWidth()),
                            int(self._document.size().height()))


# This delegate is a fix for the fact QTableWidget (and possibly QTableView)
# don't seem to properly support word wrapping text in spanned rows. The issue
# appears to be, when you have a column span and call resizeRowsToContent, it
# uses the width of the item containing the text rather than the width of the
# span to calculate how tall the word wrapped text will be.
# NOTE: Currently only supports spans covering multiple columns, not multiple
# rows
class TableViewSpannedWordWrapFixDelegate(StyledItemDelegateEx):
    def sizeHint(
            self,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
            ) -> QtCore.QSize:
        itemOptions = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(itemOptions, index)

        model = index.model()
        table = model.parent()
        assert(isinstance(table, QtWidgets.QTableView))
        itemSpan = table.columnSpan(index.row(), index.column())
        if itemSpan <= 1:
            # No span so just return base size hint
            return super().sizeHint(option, index)

        column = 0
        while column < index.column():
            span = table.columnSpan(index.row(), column)
            column += span
        if column != index.column():
            # Not the first item in the span so just return the base
            # size hint
            return super().sizeHint(option, index)

        availableWidth = 0
        for column in range(index.column(), index.column() + itemSpan):
            availableWidth += table.horizontalHeader().sectionSize(column)
        availableRect = QtCore.QRect(
            itemOptions.rect.left(),
            itemOptions.rect.top(),
            availableWidth,
            option.rect.height())

        fontMetrics = QtGui.QFontMetrics(itemOptions.font)
        textRect = fontMetrics.boundingRect(
            availableRect,
            QtCore.Qt.TextFlag.TextWordWrap,
            itemOptions.text)
        return textRect.size()
