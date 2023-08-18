from PyQt5.QtWidgets import QStyleOptionViewItem
import app
import gui
import html
import logging
import math
import traveller
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

def _formatWorldHtml(world: traveller.World) -> str:
    return f'{html.escape(world.name(includeSubsector=True))}<br><i>{html.escape(world.sectorHex())} - {html.escape(world.uwp().string())}</i>'

# Based on code from here
# https://stackoverflow.com/questions/21141757/pyqt-different-colors-in-a-single-row-in-a-combobox
class _ListItemDelegate(QtWidgets.QStyledItemDelegate):
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
        if options.widget:
            style = options.widget.style()
        else:
            style = QtWidgets.QApplication.style()

        world = index.data(QtCore.Qt.ItemDataRole.UserRole)
        self._document.setHtml(_formatWorldHtml(world))
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
        world = index.data(QtCore.Qt.ItemDataRole.UserRole)
        self._document.setHtml(_formatWorldHtml(world))
        return QtCore.QSize(int(self._document.idealWidth()),
                            int(self._document.size().height()))

class WorldSearchComboBox(gui.ComboBoxEx):
    worldChanged = QtCore.pyqtSignal(object)

    _MaxCompleterResults = 50

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._selectedWorld = None

        self._autoComplete = False
        self._completer = None
        self._completerDelegate = None

        self._document = QtGui.QTextDocument(self)

        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        self.setCompleter(self._completer)
        self.setItemDelegate(_ListItemDelegate())
        self.installEventFilter(self)
        self.editTextChanged.connect(self._updateCompleter)
        self.activated.connect(self._dropDownSelected)

    def selectedWorld(self) -> typing.Optional[traveller.World]:
        return self._selectedWorld

    def setSelectedWorld(self, world: typing.Optional[traveller.World]) -> None:
        self.setCurrentText(world.name(includeSubsector=True) if world else '')
        self._updateSelectedWorld(world)

    def enableAutoComplete(self, enable: bool) -> None:
        self._autoComplete = enable
        self._updateCompleter()

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if object == self:
            if event.type() == QtCore.QEvent.Type.FocusIn:
                # The widget has received focus. Prime a call to select all text as long as
                # it's not being passed focus from the completer popup. This is done so the
                # user can just start typing to enter the new search when they click on the
                # widget or tag to it. The call to select the text can't be made now as it
                # doesn't work reliably.
                assert(isinstance(event, QtGui.QFocusEvent))
                if event.reason() != QtCore.Qt.FocusReason.PopupFocusReason:
                    QtCore.QTimer.singleShot(0, self.selectAll)
        return super().eventFilter(object, event)

    def showPopup(self) -> None:
        self._loadHistory()
        return super().showPopup()

    def _calculateIdealHtmlWidth(self, html: str) -> int:
        self._document.setHtml(html)
        self._document.setTextWidth(100000)
        return math.ceil(self._document.idealWidth())

    def _calculateListWidth(
            self,
            contentWidth: int
            ) -> int:
        width = contentWidth
        if not self.view().verticalScrollBar().isHidden():
            width += self.view().verticalScrollBar().sizeHint().width()

        return max(width, self.width())

    def _loadHistory(self) -> None:
        contentWidth = 0
        with gui.SignalBlocker(widget=self):
            self.clear()

            for world in app.RecentWorlds.instance().worlds():
                self.addItem(world.name(includeSubsector=True), world)

                displayHtml = _formatWorldHtml(world)
                itemWidth = self._calculateIdealHtmlWidth(displayHtml)
                if itemWidth > contentWidth:
                    contentWidth = itemWidth

        # Force clearing the current text selection. This works around a bug where the first item
        # of the list is automatically selected but I don't get a notification that the text has
        # changed. It's most likely because I'm blocking signals above but it doesn't seem worth
        # the effort to do anything better. The only downside of this approach is any text the user
        # has typed is cleared but that doesn't seem like an issue as they're using the drop down to
        # select a previously used world
        self.setCurrentIndex(-1)

        margins = self.view().contentsMargins()
        contentWidth += margins.left() + margins.right()

        self.view().setFixedWidth(self._calculateListWidth(contentWidth))

    def _updateCompleter(self) -> None:
        if self._selectedWorld:
            # Clear the selected world when the user starts typing
            self._updateSelectedWorld(None)

        if not self._autoComplete:
            if self._completer == self.completer():
                self.setCompleter(None)
            self._completer = None
            self._completerDelegate = None
            return

        searchString = self.currentText()
        if not searchString:
            return # Nothing to do
        searchString = searchString.strip()

        if not self._completer:
            self._completer = QtWidgets.QCompleter()
            self._completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
            # I don't completely understand what unfiltered does compared to the standard popup but
            # using it fixed an issue I was seeing where in some cases the completer would automatically
            # select the first entry in the list when scrolling through with the cursor keys but wouldn't
            # call activate.
            self._completer.setCompletionMode(
                QtWidgets.QCompleter.CompletionMode.UnfilteredPopupCompletion)
            self._completer.setCompletionRole(QtCore.Qt.ItemDataRole.DisplayRole)
            self._completer.activated[QtCore.QModelIndex].connect(self._completerActivated)
            self.setCompleter(self._completer)

        worlds = None
        try:
            worlds = traveller.WorldManager.instance().searchForWorlds(
                searchString=searchString,
                maxResults=WorldSearchComboBox._MaxCompleterResults)
        except Exception as ex:
            logging.error(
                f'World search for "{searchString}" failed setting up completer',
                exc_info=ex)

        model = QtGui.QStandardItemModel()
        if not worlds:
            self._completer.setModel(model)
            return

        model.insertColumn(0)
        model.insertRows(0, len(worlds))
        contentWidth = 0
        for index, world in enumerate(worlds):
            modelIndex = model.index(index, 0)
            model.setData(
                modelIndex,
                world.name(includeSubsector=True),
                QtCore.Qt.ItemDataRole.DisplayRole)
            model.setData(
                modelIndex,
                world,
                QtCore.Qt.ItemDataRole.UserRole)

            worldHtml = _formatWorldHtml(world)
            idealWidth = self._calculateIdealHtmlWidth(worldHtml)
            if idealWidth > contentWidth:
                contentWidth = idealWidth

        model.sort(0, QtCore.Qt.SortOrder.AscendingOrder)
        self._completer.setModel(model)

        popup = self._completer.popup()
        if popup:
            margins = popup.contentsMargins()
            contentWidth += margins.left() + margins.right()
            popup.setFixedWidth(self._calculateListWidth(contentWidth))

            if not self._completerDelegate:
                self._completerDelegate = _ListItemDelegate()
            popup.setItemDelegate(self._completerDelegate)

    def _completerActivated(
            self,
            index: QtCore.QModelIndex
            ) -> None:
        world = index.data(QtCore.Qt.ItemDataRole.UserRole)

        # The completer hasn't actually set the combo box text yet so defer handling the world
        # update until after that's done. This is done to make sure the state is always consistent
        # when the world changed event is generated
        QtCore.QTimer.singleShot(0, lambda: self._delayedCompleterHandler(world))

    def _delayedCompleterHandler(
            self,
            world: typing.Optional[traveller.World]
            ) -> None:
        self._updateSelectedWorld(world)
        self.selectAll()

    def _dropDownSelected(
            self,
            index: int
            ) -> None:
        world = self.itemData(index, QtCore.Qt.ItemDataRole.UserRole)
        self._updateSelectedWorld(world)

        # Select all the current text so the control is ready for the user to search for something
        # else without them having to delete the current search text
        self.selectAll()

    def _updateSelectedWorld(
            self,
            world: typing.Optional[traveller.World]
            ) -> None:
        self._selectedWorld = world

        # Notify observers that the selected world has changed. This is done even
        # if it's actually the same world to allow for the case where the user
        # reselects the same world to cause the map to jump back to it's location
        self.worldChanged.emit(self._selectedWorld)
