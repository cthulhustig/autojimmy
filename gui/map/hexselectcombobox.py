import app
import gui
import html
import logging
import math
import traveller
import travellermap
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

def _formatWorldName(world: traveller.World) -> str:
    return world.name(includeSubsector=True)

def _formatHexName(hex: travellermap.HexPosition) -> str:
    milieu = app.Config.instance().asEnum(
        option=app.ConfigOption.Milieu,
        enumType=travellermap.Milieu)

    world = traveller.WorldManager.instance().worldByPosition(
        milieu=milieu,
        hex=hex)
    if world:
        return _formatWorldName(world=world)

    try:
        sectorHex = traveller.WorldManager.instance().positionToSectorHex(milieu=milieu, hex=hex)
        subsector = traveller.WorldManager.instance().subsectorByPosition(milieu=milieu, hex=hex)
        return f'{sectorHex} ({subsector.name()})' if subsector else sectorHex
    except:
        return f'{hex.absoluteX()},{hex.absoluteY()}'

def _formatWorldHtml(world: traveller.World) -> str:
    return '{worldName}<br><i>{sectorHex} - {uwp}</i>'.format(
        worldName=html.escape(_formatWorldName(world=world)),
        sectorHex=html.escape(world.sectorHex()),
        uwp=html.escape(world.uwp().string()))

def _formatHexHtml(hex: travellermap.HexPosition) -> str:
    world = traveller.WorldManager.instance().worldByPosition(
        milieu=app.Config.instance().asEnum(
            option=app.ConfigOption.Milieu,
            enumType=travellermap.Milieu),
        hex=hex)
    if world:
        return _formatWorldHtml(world=world)
    return html.escape(_formatHexName(hex=hex))

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

        hex = index.data(QtCore.Qt.ItemDataRole.UserRole)
        if hex:
            self._document.setHtml(_formatHexHtml(hex=hex))
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
        hex = index.data(QtCore.Qt.ItemDataRole.UserRole)
        if not hex:
            return super().sizeHint(option, index)
        self._document.setHtml(_formatHexHtml(hex=hex))
        return QtCore.QSize(int(self._document.idealWidth()),
                            int(self._document.size().height()))

# TODO: Ideally this class would update if the milieu changes to show
# the name of the world in the new milieu. It would also need to handle
# the case there is no world at the selected hex in the new milieu. If
# dead space routing is not enabled then it should clear the current
# selected hex
class HexSelectComboBox(gui.ComboBoxEx):
    hexChanged = QtCore.pyqtSignal(object)

    # NOTE: This controls the max number of results added to the completer
    # model. The complete its self also has a max number it will display
    # in the popup, with any remaining being accessible by scrolling the
    # popup view
    _MaxCompleterResults = 50

    # NOTE: This state string doesn't match the class name so the user doesn't
    # lose the last selected history due to the updates made to add dead space
    # support. It was already writing a sector hex so previous data should load
    # correctly
    _StateVersion = '_WorldSearchComboBox_v1'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._enableDeadSpaceSelection = False
        self._selectedHex = None

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

    def currentHex(self) -> typing.Optional[travellermap.HexPosition]:
        return self._selectedHex

    def setCurrentHex(
            self,
            hex: typing.Optional[travellermap.HexPosition],
            updateHistory: bool = True
            ) -> None:
        self.setCurrentText(_formatHexName(hex=hex) if hex else '')
        self._updateSelectedHex(
            hex=hex,
            updateHistory=updateHistory)

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

    def enableDeadSpaceSelection(self, enable: bool) -> None:
        self._enableDeadSpaceSelection = enable

        if not self._enableDeadSpaceSelection:
            # Dead space selection has been disabled so clear the current selection
            # if it's a dead space hex
            hex = self.currentHex()
            if hex:
                world = traveller.WorldManager.instance().worldByPosition(
                    milieu=app.Config.instance().asEnum(
                        option=app.ConfigOption.Milieu,
                        enumType=travellermap.Milieu),
                    hex=hex)
                if not world:
                    self.setCurrentHex(hex=None)

    def isDeadSpaceSelectionEnabled(self) -> bool:
        return self._enableDeadSpaceSelection

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
                # The widget has lost focus. If the completer is enabled sync
                # the selected hex and current text as long as focus isn't
                # being lost to the widgets completer popup. If there is a
                # currently selected hex then force the text to be the full
                # canonical name for that hex. If there is no selected hex then
                # get the list of the matches for the current text, if there are
                # matches then select the first one. This should effectively be
                # as if the user had selected the first completer option. This
                # is a usability thing as, if a user gets it down to the point
                # the hex they want is the first in the completer list, it might
                # not be obvious to them that they need select it. It should be
                # obvious if it's not the first in the list but it's less
                # obvious if it was the first.
                assert(isinstance(event, QtGui.QFocusEvent))
                if self._completer and event.reason() != QtCore.Qt.FocusReason.PopupFocusReason:
                    hex = self.currentHex()
                    if hex:
                        newText = _formatHexName(hex)
                        if newText != self.currentText():
                            self.setCurrentText(newText)
                    else:
                        matches = self._findCompletionMatches()
                        self.setCurrentHex(hex=matches[0] if matches else None)
            elif event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.matches(QtGui.QKeySequence.StandardKey.Paste):
                    self._pasteText()
                    event.accept()
                    return True
            if event.type() == QtCore.QEvent.Type.ToolTip:
                assert(isinstance(event, QtGui.QHelpEvent))
                toolTip = ''
                if self._enableWorldToolTips and self._selectedHex:
                    toolTip = gui.createHexToolTip(hex=self._selectedHex)
                if toolTip != self.toolTip():
                    self.setToolTip(toolTip)

        return super().eventFilter(object, event)

    def showPopup(self) -> None:
        self._loadHistory()
        return super().showPopup()

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(HexSelectComboBox._StateVersion)

        current = self.currentHex()
        stream.writeBool(current != None)
        if current:
            stream.writeInt32(current.absoluteX())
            stream.writeInt32(current.absoluteY())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != HexSelectComboBox._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore HexSearchComboBox state (Incorrect version)')
            return False

        if stream.readBool():
            hex = travellermap.HexPosition(
                absoluteX=stream.readInt32(),
                absoluteY=stream.readInt32())
            self.setCurrentHex(
                hex=hex,
                updateHistory=False)

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

            milieu = app.Config.instance().asEnum(
                option=app.ConfigOption.Milieu,
                enumType=travellermap.Milieu)
            for hex in app.HexHistory.instance().hexes():
                if not self._enableDeadSpaceSelection:
                    world = traveller.WorldManager.instance().worldByPosition(
                        milieu=milieu,
                        hex=hex)
                    if not world:
                        # Ignore dead space in history
                        continue

                self.addItem(_formatHexName(hex=hex), hex)

                html = _formatHexHtml(hex=hex)
                itemWidth = self._calculateIdealHtmlWidth(html)
                if itemWidth > contentWidth:
                    contentWidth = itemWidth

        # Force clearing the current text selection. This works around a bug where the first item
        # of the list is automatically selected but I don't get a notification that the text has
        # changed. It's most likely because I'm blocking signals above but it doesn't seem worth
        # the effort to do anything better. The only downside of this approach is any text the user
        # has typed is cleared but that doesn't seem like an issue as they're using the drop down to
        # select a previously used hex
        self.setCurrentIndex(-1)

        margins = self.view().contentsMargins()
        contentWidth += margins.left() + margins.right()

        self.view().setFixedWidth(self._calculateListWidth(contentWidth))

    def _updateCompleter(self) -> None:
        if not self._completer:
            return

        matches = self._findCompletionMatches()

        # Clear the selected hex when the user starts typing
        # Update: I disabled this 11/01/25 as it meant if you cancel the
        # completer the previously selected world is lost. If the selection
        # was to be enabled it important it's done after the matches are
        # generated so the current selection can be taken into account when
        # ordering new matches
        # self._updateSelectedHex(hex=None)

        self._completerModel.clear()
        if not matches:
            return

        self._completerModel.setColumnCount(1)
        self._completerModel.setRowCount(len(matches))
        contentWidth = 0
        for index, hex in enumerate(matches):
            modelIndex = self._completerModel.index(index, 0)
            self._completerModel.setData(
                modelIndex,
                _formatHexName(hex=hex),
                QtCore.Qt.ItemDataRole.DisplayRole)
            self._completerModel.setData(
                modelIndex,
                hex,
                QtCore.Qt.ItemDataRole.UserRole)

            html = _formatHexHtml(hex=hex)
            idealWidth = self._calculateIdealHtmlWidth(html)
            if idealWidth > contentWidth:
                contentWidth = idealWidth

        # Clear the completer prefix as we don't want it doing any filtering.
        # It's really just being used to display the drop down.
        self._completer.setCompletionPrefix('')

        # Set the widget completion is being performed on to the comboboxes
        # line edit. This needs to be done to avoid weird issues where
        # activate isn't called in some cases, an example being just typing
        # z then using the mouse to select the first item in the list. It
        # would fill in the text for the hex in the comboboxes edit box
        # but it wouldn't call activate so the selected hex would be set
        # and the hex changed notification wouldn't be emitted. It needs
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
        hex = index.data(QtCore.Qt.ItemDataRole.UserRole)

        # The completer hasn't actually set the combo box text yet so defer
        # handling the hex update until after that's done. This is done to make
        # sure the state is always consistent when the hex changed event is
        # generated
        QtCore.QTimer.singleShot(0, lambda: self._delayedCompleterHandler(hex=hex))

    def _delayedCompleterHandler(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        self._updateSelectedHex(hex=hex)
        self.selectAll()

    def _dropDownSelected(
            self,
            index: int
            ) -> None:
        hex = self.itemData(index, QtCore.Qt.ItemDataRole.UserRole)
        self._updateSelectedHex(hex=hex)

        # Select all the current text so the control is ready for the user to search for something
        # else without them having to delete the current search text
        self.selectAll()

    def _updateSelectedHex(
            self,
            hex: typing.Optional[travellermap.HexPosition],
            updateHistory: bool = True
            ) -> None:
        if hex and updateHistory:
            app.HexHistory.instance().addHex(hex=hex)

        if hex != self._selectedHex:
            self._selectedHex = hex
            self.hexChanged.emit(self._selectedHex)

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
                'An exception occurred while overriding the hex search paste action',
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
            # the hex changed event isn't trigged if the user selects an entry
            # from the completer. This happens as for some reason activated
            # isn't called even though the completer does still set the text
            self._completer.setWidget(lineEdit)
            self._completer.complete()

    def _findCompletionMatches(self) -> typing.Collection[travellermap.HexPosition]:
        milieu = app.Config.instance().asEnum(
            option=app.ConfigOption.Milieu,
            enumType=travellermap.Milieu)
        searchString = self.currentText().strip()
        matches: typing.List[travellermap.HexPosition] = []

        if searchString:
            # NOTE: For sorting to make sense it's important that the world
            # search returns ALL worlds that match the search string so they
            # can be sorted. The limiting of the number of results added to
            # the completer should be done on the sorted list.
            try:
                worlds = traveller.WorldManager.instance().searchForWorlds(
                    milieu=milieu,
                    searchString=searchString)
                for world in worlds:
                    matches.append(world.hex())
            except Exception as ex:
                # Log this at debug as it could get very spammy as the user types
                logging.debug(
                    f'Search for "{searchString}" failed',
                    exc_info=ex)

            if self._enableDeadSpaceSelection:
                try:
                    hex = traveller.WorldManager.instance().stringToPosition(
                        milieu=milieu,
                        string=searchString)
                    isDuplicate = False
                    for other in matches:
                        if hex == other:
                            isDuplicate = True
                            break
                    if not isDuplicate:
                        matches.append(hex)
                except KeyError:
                    pass # The search string isn't a a sector hex so ignore it
                except Exception as ex:
                    # Log this at debug as it could get very spammy as the user types
                    logging.debug(
                        f'Search for sector hex "{searchString}" failed',
                        exc_info=ex)

            # If the currently selected hex is in the list of matched hexes, make sure
            # it's the first option in the list
            if self._selectedHex and self._selectedHex in matches:
                matches.remove(self._selectedHex)
                matches.insert(0, self._selectedHex)

        if len(matches) > HexSelectComboBox._MaxCompleterResults:
            matches = matches[:HexSelectComboBox._MaxCompleterResults]
        return matches
