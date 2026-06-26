import app
import astronomer
import azathoth
import cartographer
import common
import enum
import gui
import logging
import multiverse
import os
import survey
import typing
from PyQt5 import QtCore, QtWidgets, QtGui

# TODO: Welcome message
# TODO: Check if current universe is custom when window first opens and, if it's not, prompt to create a new one
# - Should close window if user chooses not to create one. Not sure how best to do this it should really be destroyed rather than just hidden like other windows
# - Needs to have the option to create one from the traveller map data or an empty universe
# - Need the option to regenerate trade codes for a rule system
#   - It might be worth having this option when creating a universe from traveller map data _and_ when importing a sector file into a universe
# TODO: Ability to select the sector to import the new sector to
# - Not sure if I still need a way to have it use the position specified in the metadata file
# TODO: When creating first universe need to make sure it explains that it won't auto update from traveller map
# TODO: Something that causes other windows to update when new sectors are imported
# TODO: A list of which sectors have been modified so the user can jump between them
# TODO: If you delete a custom sector it could give the user the option to restore the equivalent sector from the stock database
# TODO: Option to update unmodified sectors to the versions from the stock database
# TODO: When creating a custom universe, give the option to not include sectors with the Faraway tag
# - This will mean not using a DB file copy to create the new sector

class CustomUniverseWindow(gui.WindowWidget):
    class Actions(enum.StrEnum):
        Undo = 'undo'
        Redo = 'redo'

        ImportSector = 'import'
        ExportSector = 'export'

    def __init__(self) -> None:
        super().__init__(
            title='Custom Universe',
            configSection='CustomUniverseWindow')

        universe = astronomer.WorldManager.instance().universe()
        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        mapStyle = app.Config.instance().value(option=app.ConfigOption.MapStyle)
        mapOptions = app.Config.instance().value(option=app.ConfigOption.MapOptions)
        mapRendering = app.Config.instance().value(option=app.ConfigOption.MapRendering)
        mapAnimations = app.Config.instance().value(option=app.ConfigOption.MapAnimations)
        worldTagging = app.Config.instance().value(option=app.ConfigOption.WorldTagging)
        taggingColours = app.Config.instance().value(option=app.ConfigOption.TaggingColours)
        app.Config.instance().configChanged.connect(self._appConfigChanged)

        self._sectorTable = gui.SectorTable(
            universe=universe,
            milieu=milieu)
        self._sectorTable.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._sectorTable.itemSelectionChanged.connect(self._sectorSelectionChanged)

        self._mapWidget = gui.MapWidgetEx(
            universe=universe,
            milieu=milieu,
            rules=rules,
            style=mapStyle,
            options=mapOptions,
            rendering=mapRendering,
            animated=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours)
        self._mapWidget.setSelectionMode(gui.MapWidgetEx.SelectionMode.SingleSelection)
        self._mapWidget.setSelectionCategory(gui.MapWidgetEx.SelectionCategory.SectorSelection)
        self._mapWidget.enableDeadSpaceSelection(True)
        self._mapWidget.mapStyleChanged.connect(self._mapStyleChanged)
        self._mapWidget.mapOptionsChanged.connect(self._mapOptionsChanged)
        self._mapWidget.mapRenderingChanged.connect(self._mapRenderingChanged)
        self._mapWidget.mapAnimationChanged.connect(self._mapAnimationChanged)
        self._mapWidget.selectionChanged.connect(self._mapSelectionChanged)
        self._mapWidget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._mapWidget.customContextMenuRequested.connect(self._mapShowContextMenu)

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._sectorTable)
        self._splitter.addWidget(self._mapWidget)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 100)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._splitter)

        self._actions: typing.Dict[CustomUniverseWindow.Actions, QtWidgets.QAction] = {}
        self._createActions()

        self.resize(640, 480)
        self.setLayout(windowLayout)

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        super().firstShowEvent(e)

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SectorTableState',
            type=QtCore.QByteArray)
        if storedValue:
            self._sectorTable.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='MapWidgetState',
            type=QtCore.QByteArray)
        if storedValue:
            self._mapWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._splitter.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('SectorTableState', self._sectorTable.saveState())
        self._settings.setValue('MapWidgetState', self._mapWidget.saveState())
        self._settings.setValue('SplitterState', self._splitter.saveState())
        self._settings.endGroup()

        super().saveSettings()

    def _createActions(self) -> None:
        action = QtWidgets.QAction('Undo', self)
        action.triggered.connect(self._undo)
        action.setShortcut(QtGui.QKeySequence.StandardKey.Undo)
        self._actions[CustomUniverseWindow.Actions.Undo] = action
        self.addAction(action)

        action = QtWidgets.QAction('Redo', self)
        action.triggered.connect(self._redo)
        action.setShortcut(QtGui.QKeySequence.StandardKey.Redo)
        self._actions[CustomUniverseWindow.Actions.Redo] = action
        self.addAction(action)

        action = QtWidgets.QAction('Import Sector', self)
        action.triggered.connect(self._importSector)
        # TODO: Use proper shortcut when I get passed hacky debug import
        #action.setShortcut(QtGui.QKeySequence('Ctrl+I'))
        action.setShortcut(QtGui.QKeySequence('Ctrl+V'))
        self._actions[CustomUniverseWindow.Actions.ImportSector] = action
        self.addAction(action)

        action = QtWidgets.QAction('Export Sector', self)
        action.triggered.connect(self._exportSector)
        # TODO: Is there a more standard shortcut for export (import as well)
        action.setShortcut(QtGui.QKeySequence('Ctrl+E'))
        self._actions[CustomUniverseWindow.Actions.ExportSector] = action
        self.addAction(action)

        self._syncActionState()

    def _syncActionState(self) -> None:
        hasSelection = self._mapWidget.hasSelection()
        hasSelectedSector = hasSelection and self._mapWidget.selectionCategory() is gui.MapWidgetEx.SelectionCategory.SectorSelection

        self._actions[CustomUniverseWindow.Actions.Undo].setEnabled(azathoth.UniverseEditor.instance().canUndo())
        self._actions[CustomUniverseWindow.Actions.Redo].setEnabled(azathoth.UniverseEditor.instance().canRedo())

        self._actions[CustomUniverseWindow.Actions.ImportSector].setEnabled(hasSelectedSector)
        self._actions[CustomUniverseWindow.Actions.ExportSector].setEnabled(hasSelectedSector)

    def _appConfigChanged(
            self,
            option: app.ConfigOption,
            oldValue: typing.Any,
            newValue: typing.Any
            ) -> None:
        if option is app.ConfigOption.Universe:
            universe = astronomer.WorldManager.instance().universe()
            self._sectorTable.setUniverse(universe=universe)
            self._mapWidget.setUniverse(universe=universe)
        elif option is app.ConfigOption.Milieu:
            self._sectorTable.setMilieu(milieu=newValue)
            self._mapWidget.setMilieu(milieu=newValue)
        elif option is app.ConfigOption.Rules:
            self._mapWidget.setRules(rules=newValue)
        elif option is app.ConfigOption.MapStyle:
            self._mapWidget.setMapStyle(style=newValue)
        elif option is app.ConfigOption.MapOptions:
            self._mapWidget.setMapOptions(options=newValue)
        elif option is app.ConfigOption.MapRendering:
            self._mapWidget.setRendering(rendering=newValue)
        elif option is app.ConfigOption.MapAnimations:
            self._mapWidget.setAnimated(animated=newValue)
        elif option is app.ConfigOption.WorldTagging:
            self._mapWidget.setWorldTagging(tagging=newValue)
        elif option is app.ConfigOption.TaggingColours:
            self._mapWidget.setTaggingColours(colours=newValue)

    def _sectorSelectionChanged(self) -> None:
        newSector = self._sectorTable.currentSector()
        newPos = newSector.position() if newSector else None
        if newPos:
            currentSelection = self._mapWidget.selectedSectors()
            currentPos = currentSelection[0] if currentSelection else None
            if currentPos != newPos:
                self._mapWidget.selectSector(newPos)
                self._mapWidget.centerOnSector(newPos)
        else:
            self._mapWidget.clearSelection()

    def _mapStyleChanged(
            self,
            style: cartographer.MapStyle
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MapStyle,
            value=style)

    def _mapOptionsChanged(
            self,
            options: typing.Iterable[app.MapOption]
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MapOptions,
            value=options)

    def _mapRenderingChanged(
            self,
            renderingType: app.MapRendering,
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MapRendering,
            value=renderingType)

    def _mapAnimationChanged(
            self,
            animations: bool
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MapAnimations,
            value=animations)

    def _mapSelectionChanged(self) -> None:
        newSelection = self._mapWidget.selectedSectors()
        newPos = newSelection[0] if newSelection else None
        if newPos:
            currentSector = self._sectorTable.currentSector()
            currentPos = currentSector.position() if currentSector else None
            if currentPos != newPos:
                self._sectorTable.setCurrentSectorByPosition(newPos)
                self._sectorTable.scrollToPosition(newPos)
        else:
            self._sectorTable.clearSelection()

        self._syncActionState()

    def _mapShowContextMenu(
            self,
            pos: QtCore.QPoint
            ) -> None:
        sectorPos = self._mapWidget.sectorAt(pos=pos)
        universe = azathoth.UniverseEditor.instance().universe()
        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)

        sector = universe.sectorByPosition(
            milieu=milieu,
            position=sectorPos)
        if not sector:
            return

        actions: typing.List[QtWidgets.QAction] = []

        action = QtWidgets.QAction('Export Sector....', self)
        action.triggered.connect(lambda: self._exportSector(sectorPos))
        actions.append(action)

        menu = QtWidgets.QMenu()
        menu.addActions(actions)
        menu.exec(QtGui.QCursor.pos())

    def _importSector(self) -> None:
        selection = self._mapWidget.selectedSectors()
        sectorPos = None
        if selection:
            sectorPos = selection[0]
        if not sectorPos:
            return

        universe = azathoth.UniverseEditor.instance().universe()
        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)

        oldSector = universe.sectorByPosition(
            milieu=milieu,
            position=sectorPos)
        if oldSector is not None and not isinstance(oldSector, azathoth.EditableSector):
            message = 'Old sector is not editable.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        importDlg = gui.ImportSectorDialog(sectorPos=sectorPos, parent=self)
        if importDlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        newSector = importDlg.sector()
        if not newSector:
            message = 'Invalid sector.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        try:
            azathoth.UniverseEditor.instance().executeCommand(
                command=azathoth.ReplaceSectorCommand(
                    oldSector=oldSector,
                    newSector=newSector))
            self._syncActionState()
        except Exception as ex:
            message = 'An error occurred when importing sector.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

    def _exportSector(
            self,
            sectorPos: astronomer.SectorPosition
            ) -> None:
        universe = azathoth.UniverseEditor.instance().universe()
        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)

        try:
            sector = universe.sectorByPosition(
                milieu=milieu,
                position=sectorPos)
        except Exception as ex:
            message = 'An error occurred when finding sector data'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        try:
            rawMetadata, rawWorlds = astronomer.convertAstronomerSectorToRawSector(
                astroSector=sector)
        except Exception as ex:
            message = f'An error occurred when converting sector'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        # TODO: Prompt user for file names and file formats
        # TODO: If file names are generated from sector name, need to sanitize it for invalid
        # characters
        encodedSectorName = common.encodeFileName(sector.name())
        metadataFilePath = f'c:\\temp\\{encodedSectorName}.xml'
        metadataFileFormat = survey.MetadataFormat.XML
        sectorFilePath = f'c:\\temp\\{encodedSectorName}.sec'
        sectorFileFormat = survey.SectorFormat.T5Column

        # TODO: Need to display reported messages to the user
        reporter = common.LoggingReporter(logLevel=logging.WARNING)

        try:
            content = survey.formatMetadata(
                metadata=rawMetadata,
                format=metadataFileFormat,
                reporter=reporter)
            with open(metadataFilePath, 'w', encoding='utf-8-sig') as file:
                file.write(content)
        except Exception as ex:
            message = f'An error occurred when writing the sector metadata file'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        try:
            content = survey.formatSector(
                worlds=rawWorlds,
                format=sectorFileFormat,
                reporter=reporter)
            with open(sectorFilePath, 'w', encoding='utf-8-sig') as file:
                file.write(content)
        except Exception as ex:
            message = f'An error occurred when writing the sector file'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

    def _undo(self) -> None:
        if not azathoth.UniverseEditor.instance().canUndo():
            return

        try:
            azathoth.UniverseEditor.instance().undo()
            self._syncActionState()
        except Exception as ex:
            message = 'An error occurred while performing undo.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

    def _redo(self) -> None:
        if not azathoth.UniverseEditor.instance().canRedo():
            return

        try:
            azathoth.UniverseEditor.instance().redo()
            self._syncActionState()
        except Exception as ex:
            message = 'An error occurred while performing redo.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return