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
        if world:
            self._document.setHtml(_formatWorldHtml(world))
        else:
            self._document.clear()

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
        if not world:
            return super().sizeHint(option, index)
        self._document.setHtml(_formatWorldHtml(world))
        return QtCore.QSize(int(self._document.idealWidth()),
                            int(self._document.size().height()))

class WorldSelectComboBox(gui.ComboBoxEx):
    worldChanged = QtCore.pyqtSignal(object)

    # NOTE: This controls the max number of results added to the completer
    # model. The complete its self also has a max number it will display
    # in the popup, with any remaining being accessible by scrolling the
    # popup view
    _MaxCompleterResults = 50

    _StateVersion = '_WorldSearchComboBox_v1'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._selectedWorld = None

        self._completer = None
        self._completerModel = None
        self._completerPopupDelegate = None

        self._enableWorldToolTips = False

        self._document = QtGui.QTextDocument(self)

        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        self.setCompleter(self._completer)
        self.setItemDelegate(_ListItemDelegate())
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.installEventFilter(self)
        self.editTextChanged.connect(self._updateCompleter)
        self.activated.connect(self._dropDownSelected)
        self.customContextMenuRequested.connect(self._showContextMenu)

    def currentWorld(self) -> typing.Optional[traveller.World]:
        return self._selectedWorld

    def setCurrentWorld(
            self,
            world: typing.Optional[traveller.World],
            updateRecentWorlds: bool = True
            ) -> None:
        self.setCurrentText(
            world.name(includeSubsector=True) if world else '')
        self._updateSelectedWorld(
            world=world,
            updateRecentWorlds=updateRecentWorlds)

    def enableAutoComplete(self, enable: bool) -> None:
        if enable == (self._completer != None):
            return # Nothing to do

        if enable:
            self._completerModel = QtGui.QStandardItemModel()
            self._completerPopupDelegate = _ListItemDelegate()

            self._completer = QtWidgets.QCompleter()
            self._completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
            # I don't completely understand what unfiltered does compared to the standard popup but
            # using it fixed an issue I was seeing where in some cases the completer would automatically
            # select the first entry in the list when scrolling through with the cursor keys but wouldn't
            # call activate.
            self._completer.setCompletionMode(
                QtWidgets.QCompleter.CompletionMode.UnfilteredPopupCompletion)
            self._completer.setCompletionRole(QtCore.Qt.ItemDataRole.DisplayRole)
            self._completer.setModel(self._completerModel)
            self._completer.activated[QtCore.QModelIndex].connect(self._completerActivated)
            self.setCompleter(self._completer)
        else:
            self.setCompleter(None)
            self._completer = None
            self._completerModel = None
            self._completerPopupDelegate = None

    def enableWorldToolTips(self, enabled: bool) -> None:
        self._enableWorldToolTips = enabled

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if object == self:
            if event.type() == QtCore.QEvent.Type.FocusIn:
                # The widget has received focus. Prime a call to select all text
                # as long as it's not being passed focus from the completer
                # popup. This is done so the user can just start typing to enter
                # the new search when they click on the widget or tab to it. The
                # call to select the text can't be made now as it doesn't work
                # reliably.
                assert(isinstance(event, QtGui.QFocusEvent))
                if event.reason() != QtCore.Qt.FocusReason.PopupFocusReason:
                    QtCore.QTimer.singleShot(0, self.selectAll)
            elif event.type() == QtCore.QEvent.Type.FocusOut:
                # The widget has lost focus. Sync the selected world and current
                # text as long as focus isn't being lost to the widgets completer
                # popup. If there is a currently selected world then force the
                # text to be the full canonical name for that world. If there is
                # no selected world then get the list of the matches for the
                # current text, if there are matches then select the first one.
                # This should effectively be as if the user had selected the first
                # completer option. This is a usability thing as, if a user gets
                # it down to the point the world they want is the first in the
                # completer list, it might not be obvious to them that they need
                # select it. It should be obvious if it's not the first in the
                # list but it's less obvious if it was the first.
                assert(isinstance(event, QtGui.QFocusEvent))
                if event.reason() != QtCore.Qt.FocusReason.PopupFocusReason:
                    world = self.currentWorld()
                    if world:
                        worldName = world.name(includeSubsector=True)
                        if worldName != self.currentText():
                            self.setCurrentText(worldName)
                    else:
                        worlds = self._matchedWorlds()
                        self.setCurrentWorld(world=worlds[0] if worlds else None)
            elif event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.matches(QtGui.QKeySequence.StandardKey.Paste):
                    self._pasteText()
                    event.accept()
                    return True
            if event.type() == QtCore.QEvent.Type.ToolTip:
                assert(isinstance(event, QtGui.QHelpEvent))
                toolTip = ''
                if self._enableWorldToolTips and self._selectedWorld:
                    toolTip =  gui.createWorldToolTip(self._selectedWorld)
                if toolTip != self.toolTip():
                    self.setToolTip(toolTip)

        return super().eventFilter(object, event)

    def showPopup(self) -> None:
        self._loadHistory()
        return super().showPopup()

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(WorldSelectComboBox._StateVersion)

        world = self.currentWorld()
        stream.writeBool(world != None)
        if world:
            stream.writeInt32(world.absoluteX())
            stream.writeInt32(world.absoluteY())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != WorldSelectComboBox._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore WorldSearchComboBox state (Incorrect version)')
            return False

        if stream.readBool():
            absoluteX = stream.readInt32()
            absoluteY = stream.readInt32()
            try:
                world = traveller.WorldManager.instance().worldByAbsolutePosition(
                    absoluteX=absoluteX,
                    absoluteY=absoluteY)
            except Exception as ex:
                logging.error(
                    'Failed to restore WorldSearchComboBox selected world',
                    exc_info=ex)
                return False
            self.setCurrentWorld(
                world=world,
                updateRecentWorlds=False)

        return True

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
        if not self._completer:
            return

        # Clear the selected world when the user starts typing
        self._updateSelectedWorld(None)

        worlds = self._matchedWorlds()
        self._completerModel.clear()
        if not worlds:
            return
        worlds = worlds[:WorldSelectComboBox._MaxCompleterResults]

        self._completerModel.setColumnCount(1)
        self._completerModel.setRowCount(len(worlds))
        contentWidth = 0
        for index, world in enumerate(worlds):
            modelIndex = self._completerModel.index(index, 0)
            self._completerModel.setData(
                modelIndex,
                world.name(includeSubsector=True),
                QtCore.Qt.ItemDataRole.DisplayRole)
            self._completerModel.setData(
                modelIndex,
                world,
                QtCore.Qt.ItemDataRole.UserRole)

            worldHtml = _formatWorldHtml(world)
            idealWidth = self._calculateIdealHtmlWidth(worldHtml)
            if idealWidth > contentWidth:
                contentWidth = idealWidth

        # Clear the completer prefix as we don't want it doing any filtering.
        # It's really just being used to display the drop down.
        self._completer.setCompletionPrefix('')

        # Set the widget completion is being performed on to the comboboxes
        # line edit. This needs to be done to avoid weird issues where
        # activate isn't called in some cases, an example being just typing
        # z then using the mouse to select the first item in the list. It
        # would fill in the text for the world in the comboboxes edit box
        # but it wouldn't call activate so the selected world would be set
        # and the world changed notification wouldn't be emitted. It needs
        # to be set each time the search changes as something keeps resetting
        # so it's set back to target the actual combobox
        self._completer.setWidget(self.lineEdit())

        popup = self._completer.popup()
        if popup:
            margins = popup.contentsMargins()
            contentWidth += margins.left() + margins.right()
            popup.setFixedWidth(self._calculateListWidth(contentWidth))

            popup.setItemDelegate(self._completerPopupDelegate)

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
            world: typing.Optional[traveller.World],
            updateRecentWorlds: bool = True
            ) -> None:
        if world == self._selectedWorld:
            return

        self._selectedWorld = world
        if world and updateRecentWorlds:
            app.RecentWorlds.instance().addWorld(world)

        # Notify observers that the selected world has changed. This is done even
        # if it's actually the same world to allow for the case where the user
        # reselects the same world to cause the map to jump back to it's location
        self.worldChanged.emit(self._selectedWorld)

    # https://forum.qt.io/topic/123909/how-to-override-paste-or-catch-the-moment-before-paste-happens-in-qlineedit/10
    # NOTE: I suspect this might not work with RTL languages
    def _showContextMenu(self, pos: QtCore.QPoint) -> None:
        menu = self.lineEdit().createStandardContextMenu()

        try:
            translatedText = QtWidgets.QApplication.translate('QComboBox', '&Paste')
            foundActions = [action for action in menu.actions() if action.text().startswith(translatedText)]
            if len(foundActions) == 1:
                action = foundActions[0]
                action.triggered.disconnect()
                action.triggered.connect(self._pasteText)
        except Exception as ex:
            logging.error(
                'An exception occurred while overriding the world search paste action',
                exc_info=ex)
            # Continue so menu is still displayed

        menu.exec(self.mapToGlobal(pos))

    def _pasteText(self) -> None:
        lineEdit = self.lineEdit()
        lineEdit.paste()
        if self._completer:
            # Force display of the completer after pasting text into the line
            # edit as QT doesn't seem to do it it's self. Setting the completer
            # widget to the line edit used by the combo box is needed otherwise
            # the world changed event isn't trigged if the user selects an entry
            # from the completer. This happens as for some reason activated
            # isn't called even though the completer does still set the text
            self._completer.setWidget(lineEdit)
            self._completer.complete()

    def _matchedWorlds(self) -> typing.Optional[typing.List[traveller.World]]:
        searchString = self.currentText().strip()
        worlds = None
        if searchString:
            try:
                # NOTE: For sorting to make sense it's important that the world
                # search returns ALL worlds that match the search string so they
                # can be sorted. The limiting of the number of results added to
                # the completer should be done on the sorted list.
                worlds = traveller.WorldManager.instance().searchForWorlds(
                    searchString=searchString)
            except Exception as ex:
                logging.error(
                    f'World search for "{searchString}" failed setting up completer',
                    exc_info=ex)

            worlds.sort(
                key=lambda world: world.name(includeSubsector=True).casefold())
        return worlds
