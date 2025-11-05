import app
import astronomer
import cartographer
import common
import enum
import gui
import jobs
import logging
import os
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_WelcomeMessage = """
    <html>
    <p>The Custom Sectors dialog allows you to add your own sectors to {name}.
    These sectors will be merged with the stock data from Traveller Map to
    create your own custom version of the Traveller universe. This allows
    {name} to display the sectors in windows that show the map and for
    features such as jump route planning and trade calculations to take your
    sectors into account.</p>

    <p>Each custom sector must have a sector file and a metadata file. The
    metadata file must, at a minimum, specify the name and position of the
    sector. Supported data formats are:
    <ul style="margin-left:15px; -qt-list-indent:0;">
    <li><a href='https://travellermap.com/doc/fileformats#t5-column-delimited-format'>T5 Column Delimited Sector Format</a> (aka Second Survey format)</li>
    <li><a href='https://travellermap.com/doc/fileformats#t5tab'>T5 Tab Delimited Sector Format</a></li>
    <li><a href='https://travellermap.com/doc/metadata#xml-metadata-file-structure'>XML Metadata Format</a></li>
    <li>JSON Metadata Format (sorry, I can't find any documentation for this format)</li>
    </ul>
    </p>
""".format(name=app.AppName)

_JsonMetadataWarning = """
    <html>
    <p>You're using JSON metadata which isn't officially supported by the
    Traveller Map Linter API. The metadata will be automatically converted to
    XML format before uploading it to Traveller Map. Due to this conversion
    line numbers reported in linter results may be inaccurate.</p>
    </html>
""".format(name=app.AppName)
_JsonMetadataWarningNoShowStateKey = 'JsonMetadataConversionWarning'

_TravellerMapBaseUrl = 'https://travellermap.com'

# This intentionally doesn't inherit from DialogEx. We don't want it saving its size as it
# can cause incorrect sizing if the font scaling is increased then decreased
class _LintJobDialog(QtWidgets.QDialog):
    _GeneratingProgressDotCount = 5

    def __init__(
            self,
            title: str,
            job: jobs.LintJobAsync,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._job = job
        self._job.complete.connect(self._jobComplete)
        self._job.progress.connect(self._jobEvent)
        self._results = None
        self._lintingTimer = QtCore.QTimer()
        self._lintingTimer.timeout.connect(self._lintingTimerFired)
        self._lintingTimer.setInterval(500)
        self._lintingTimer.setSingleShot(False)

        self._fileLabel = gui.PrefixLabel(prefix='File: ')
        self._uploadingLabel = gui.PrefixLabel(prefix='Uploading: ')
        self._lintingLabel = gui.PrefixLabel(prefix='Linting: ')
        self._downloadingLabel = gui.PrefixLabel(prefix='Downloading: ')

        progressLayout = QtWidgets.QVBoxLayout()
        progressLayout.addWidget(self._fileLabel)
        progressLayout.addWidget(self._uploadingLabel)
        progressLayout.addWidget(self._lintingLabel)
        progressLayout.addWidget(self._downloadingLabel)

        progressGroupBox = QtWidgets.QGroupBox()
        progressGroupBox.setLayout(progressLayout)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self._cancelJob)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(progressGroupBox)
        windowLayout.addWidget(self._cancelButton)

        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)
        self.setSizeGripEnabled(False)
        self.setLayout(windowLayout)

        # Setting up the title bar needs to be done before the window is show to take effect. It
        # needs to be done every time the window is shown as the setting is lost if the window is
        # closed then reshown
        gui.configureWindowTitleBar(widget=self)

    def results(self) -> typing.Optional[typing.Mapping[jobs.LintJobAsync.Stage, jobs.LintJobAsync.LinterResult]]:
        return self._results

    def exec(self) -> int:
        try:
            self._job.run()
        except Exception as ex:
            message = 'Failed to start lint job'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            # Closing a dialog from showEvent doesn't work so schedule it to happen immediately after
            # the window is shown
            QtCore.QTimer.singleShot(0, self.close)

        return super().exec()

    def showEvent(self, e: QtGui.QShowEvent) -> None:
        if not e.spontaneous():
            # Setting up the title bar needs to be done before the window is show to take effect. It
            # needs to be done every time the window is shown as the setting is lost if the window is
            # closed then reshown
            gui.configureWindowTitleBar(widget=self)

        return super().showEvent(e)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self._job:
            self._job.cancel()
        return super().closeEvent(a0)

    def _cancelJob(self) -> None:
        if self._job:
            self._job.cancel()
        self.close()

    def _jobComplete(
            self,
            result: typing.Union[typing.Mapping[jobs.LintJobAsync.Stage, jobs.LintJobAsync.LinterResult], Exception]
            ) -> None:
        self._lintingTimer.stop()

        if isinstance(result, Exception):
            message = 'Linter job failed'
            logging.critical(message, exc_info=result)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=result)
            self.close()
        else:
            self._results = result
            self.accept()

    def _jobEvent(
            self,
            event: jobs.LintJobAsync.ProgressEvent,
            stage: jobs.LintJobAsync.Stage,
            currentBytes: int,
            totalBytes: int
            ) -> None:
        self._fileLabel.setText(stage.name)

        if totalBytes > 0:
            progressText = common.humanFriendlyByteSizes(currentBytes) + ' / ' + \
                common.humanFriendlyByteSizes(totalBytes)
        else:
            progressText = common.humanFriendlyByteSizes(currentBytes)

        if event == jobs.LintJobAsync.ProgressEvent.Uploading:
            if currentBytes == 0:
                self._lintingLabel.setText('')
                self._downloadingLabel.setText('')

            self._uploadingLabel.setText(progressText)

            if currentBytes == totalBytes:
                self._lintingTimer.start()
        elif event == jobs.LintJobAsync.ProgressEvent.Downloading:
            if currentBytes == 0:
                self._lintingTimer.stop()
                self._lintingLabel.setText('Complete')

            self._downloadingLabel.setText(progressText)

    def _lintingTimerFired(self) -> None:
        text = self._lintingLabel.text()
        if (len(text) % _LintJobDialog._GeneratingProgressDotCount) == 0:
            text = ''
        text += '.'
        self._lintingLabel.setText(text)

class _LintJobResultsDialog(gui.DialogEx):
    def __init__(
            self,
            results: typing.Mapping[jobs.LintJobAsync.Stage, jobs.LintJobAsync.LinterResult],
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Linter Results',
            configSection='LinterResultsDialog',
            parent=parent)

        self._tabWidget = gui.TabWidgetEx()
        for stage, result in results.items():
            textWidget = gui.TextEditEx()
            if result.mimeType().lower().startswith('text/html'):
                textWidget.setHtml(result.content())
            else:
                textWidget.setPlainText(result.content())
            textWidget.setReadOnly(True)
            self._tabWidget.addTab(textWidget, stage.name)

        self._closeButton = QtWidgets.QPushButton('Close')
        self._closeButton.clicked.connect(self.close)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._closeButton)

        dialogLayout = QtWidgets.QVBoxLayout()
        dialogLayout.addWidget(self._tabWidget)
        dialogLayout.addLayout(buttonLayout)

        self.setLayout(dialogLayout)
        self.showMaximizeButton(True)

class _NewSectorDialog(gui.DialogEx):
    _SectorFileFilter = 'Sector (*.sec *.tab *.t5 *.t5col *.t5tab)'
    _MetadataFileFilter = 'Metadata (*.xml *.json)'
    _AllFileFilter = 'All Files (*.*)'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='New Custom Sector',
            configSection='NewCustomSectorDialog',
            parent=parent)

        self._recentDirectoryPath = None
        self._sector = None

        self._setupFileSelectControls()
        self._setupDialogButtons()

        dialogLayout = QtWidgets.QVBoxLayout()
        dialogLayout.addWidget(self._filesGroupBox)
        dialogLayout.addLayout(self._buttonLayout)

        self.setLayout(dialogLayout)
        self.setFixedHeight(self.sizeHint().height())

    def sector(self) -> typing.Optional[astronomer.SectorInfo]:
        return self._sector

    # NOTE: There is no saveSettings as settings are only saved when accept is triggered (i.e. not
    # if the user cancels the dialog)
    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='RecentDirectory',
            type=str)
        if storedValue:
            self._recentDirectoryPath = storedValue

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SectorFilePath',
            type=str)
        if storedValue:
            self._sectorFileLineEdit.setText(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='MetadataFilePath',
            type=str)
        if storedValue:
            self._metadataFileLineEdit.setText(storedValue)

        self._settings.endGroup()

    def accept(self) -> None:
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('RecentDirectory', self._recentDirectoryPath)
        self._settings.setValue('SectorFilePath', self._sectorFileLineEdit.text())
        self._settings.setValue('MetadataFilePath', self._metadataFileLineEdit.text())
        self._settings.endGroup()

        return super().accept()

    def _setupFileSelectControls(self) -> None:
        sectorFileTooltip = gui.createStringToolTip(
            '<p>Specify the T5 Column (aka Second Survey) or T5 Row sector data file to use to create the custom sector</p>',
            escape=False)
        metadataFileTooltip = gui.createStringToolTip(
            '<p>Specify the XML sector or JSON metadata file to use to create the custom sector</p>',
            escape=False)

        self._sectorFileLineEdit = gui.LineEditEx()
        self._sectorFileLineEdit.setToolTip(sectorFileTooltip)
        self._sectorFileBrowseButton = QtWidgets.QPushButton('Browse...')
        self._sectorFileBrowseButton.setToolTip(sectorFileTooltip)
        self._sectorFileBrowseButton.clicked.connect(self._sectorFileBrowseClicked)
        sectorLayout = QtWidgets.QHBoxLayout()
        sectorLayout.setContentsMargins(0, 0, 0, 0)
        sectorLayout.addWidget(self._sectorFileLineEdit)
        sectorLayout.addWidget(self._sectorFileBrowseButton)

        self._metadataFileLineEdit = gui.LineEditEx()
        self._metadataFileLineEdit.setToolTip(metadataFileTooltip)
        self._metadataFileBrowseButton = QtWidgets.QPushButton('Browse...')
        self._metadataFileBrowseButton.setToolTip(metadataFileTooltip)
        self._metadataFileBrowseButton.clicked.connect(self._metadataFileBrowseClicked)
        metadataLayout = QtWidgets.QHBoxLayout()
        metadataLayout.setContentsMargins(0, 0, 0, 0)
        metadataLayout.addWidget(self._metadataFileLineEdit)
        metadataLayout.addWidget(self._metadataFileBrowseButton)

        groupLayout = gui.FormLayoutEx()
        groupLayout.addRow('Sector File:', gui.LayoutWrapperWidget(sectorLayout))
        groupLayout.addRow('Metadata File:', gui.LayoutWrapperWidget(metadataLayout))

        self._filesGroupBox = QtWidgets.QGroupBox('Files')
        self._filesGroupBox.setLayout(groupLayout)

    def _setupDialogButtons(self):
        metadataFileTooltip = gui.createStringToolTip(
            '<p>Linting uploads your sector and metadata files to Traveller Map so it can check them for problems.</p>' +
            '<p>It\'s advisable to do this before trying to create a custom sector as, when creating the map ' +
            'images, Traveller Map will ignore most errors resulting in worlds with errors not being rendered ' +
            'correctly.</p>',
            escape=False)

        self._lintButton = QtWidgets.QPushButton('Lint...')
        self._lintButton.setToolTip(metadataFileTooltip)
        self._lintButton.clicked.connect(self._lintClicked)

        self._createButton = QtWidgets.QPushButton('Create')
        self._createButton.setDefault(True)
        self._createButton.clicked.connect(self._createClicked)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        self._buttonLayout = QtWidgets.QHBoxLayout()
        self._buttonLayout.addWidget(self._lintButton)
        self._buttonLayout.addStretch()
        self._buttonLayout.addWidget(self._createButton)
        self._buttonLayout.addWidget(self._cancelButton)

    def _sectorFileBrowseClicked(self) -> None:
        path = self._showFileSelect(
            caption='Sector File',
            filter=f'{_NewSectorDialog._SectorFileFilter};;{_NewSectorDialog._AllFileFilter}')
        if not path:
            return # User cancelled
        self._sectorFileLineEdit.setText(path)

    def _metadataFileBrowseClicked(self) -> None:
        path = self._showFileSelect(
            caption='Metadata File',
            filter=f'{_NewSectorDialog._MetadataFileFilter};;{_NewSectorDialog._AllFileFilter}')
        if not path:
            return # User cancelled
        self._metadataFileLineEdit.setText(path)

    def _showFileSelect(
            self,
            caption: str,
            filter: str
            ) -> typing.Optional[str]:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            caption=caption,
            directory=self._recentDirectoryPath if self._recentDirectoryPath else QtCore.QDir.homePath(),
            filter=filter)
        if not path:
            return None # User cancelled

        self._recentDirectoryPath = os.path.dirname(path)
        return path

    def _createClicked(self) -> None:
        sectorFilePath = self._sectorFileLineEdit.text()
        if not sectorFilePath:
            gui.MessageBoxEx.critical(
                parent=self,
                text='No sector file selected')
            return
        if not os.path.exists(sectorFilePath):
            gui.MessageBoxEx.critical(
                parent=self,
                text='Sector file doesn\'t exist')
            return

        metadataFilePath = self._metadataFileLineEdit.text()
        if not metadataFilePath:
            gui.MessageBoxEx.critical(
                parent=self,
                text='No sector metadata file selected')
            return
        if not os.path.exists(metadataFilePath):
            gui.MessageBoxEx.critical(
                parent=self,
                text=f'Sector metadata file doesn\'t exist')
            return

        try:
            with open(metadataFilePath, 'r', encoding='utf-8-sig') as file:
                sectorMetadata = file.read()

            metadataFormat = astronomer.metadataFileFormatDetect(
                content=sectorMetadata)
            if not metadataFormat:
                raise RuntimeError('Unknown metadata file format')

            rawMetadata = astronomer.readMetadata(
                content=sectorMetadata,
                format=metadataFormat,
                identifier=metadataFilePath)

            # This will throw if there is a conflict with an existing sector
            astronomer.DataStore.instance().customSectorConflictCheck(
                sectorName=rawMetadata.canonicalName(),
                sectorX=rawMetadata.x(),
                sectorY=rawMetadata.y(),
                milieu=app.Config.instance().value(option=app.ConfigOption.Milieu))
        except Exception as ex:
            message = 'Metadata validation failed.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        # Try to parse the sector format now to prevent it failing after the user has waited
        # to create the posters. This is only really needed for cases where Traveller Map is
        # happy with the format but my parser isn't
        try:
            with open(sectorFilePath, 'r', encoding='utf-8-sig') as file:
                sectorData = file.read()

            sectorFormat = astronomer.sectorFileFormatDetect(content=sectorData)
            if not sectorFormat:
                raise RuntimeError('Unknown sector file format')
            astronomer.readSector(
                content=sectorData,
                format=sectorFormat,
                identifier=sectorFilePath)
        except Exception as ex:
            message = 'Sector validation failed.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        try:
            self._sector = astronomer.DataStore.instance().createCustomSector(
                milieu=app.Config.instance().value(option=app.ConfigOption.Milieu),
                sectorContent=sectorData,
                metadataContent=sectorMetadata) # Write the users metadata, not the xml metadata if it was converted
        except Exception as ex:
            message = 'Failed to add custom sector to data store'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self.accept()

    def _lintClicked(self) -> None:
        try:
            try:
                sectorFilePath = self._sectorFileLineEdit.text()
                with open(sectorFilePath, 'r', encoding='utf-8-sig') as file:
                    sectorData = file.read()
            except Exception as ex:
                message = 'Failed to load sector file.'
                logging.critical(message, exc_info=ex)
                gui.MessageBoxEx.critical(
                    parent=self,
                    text=message,
                    exception=ex)
                return

            try:
                metadataFilePath = self._metadataFileLineEdit.text()
                with open(metadataFilePath, 'r', encoding='utf-8-sig') as file:
                    sectorMetadata = file.read()

                metadataFormat = astronomer.metadataFileFormatDetect(
                    content=sectorMetadata)
                if not metadataFormat:
                    raise RuntimeError('Unknown metadata file format')

                if metadataFormat == astronomer.MetadataFormat.XML:
                    xmlMetadata = sectorMetadata
                    astronomer.DataStore.instance().validateSectorMetadataXML(xmlMetadata)
                else:
                    gui.AutoSelectMessageBox.information(
                        parent=self,
                        text=_JsonMetadataWarning,
                        stateKey=_JsonMetadataWarningNoShowStateKey)

                    rawMetadata = astronomer.readMetadata(
                        content=sectorMetadata,
                        format=metadataFormat,
                        identifier=metadataFilePath)
                    xmlMetadata = astronomer.writeXMLMetadata(
                        metadata=rawMetadata,
                        identifier='Generated XML metadata')
            except Exception as ex:
                message = 'Failed to load metadata file.'
                logging.critical(message, exc_info=ex)
                gui.MessageBoxEx.critical(
                    parent=self,
                    text=message,
                    exception=ex)
                return

            lintJob = jobs.LintJobAsync(
                parent=self,
                mapUrl=_TravellerMapBaseUrl,
                sectorData=sectorData,
                xmlMetadata=xmlMetadata)
            progressDlg = _LintJobDialog(
                parent=self,
                title='Linting',
                job=lintJob)
            if progressDlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                return
            results = lintJob.results()
        except Exception as ex:
            message = 'Failed to lint data.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        if not results:
            gui.MessageBoxEx.information(
                parent=self,
                text='The Traveller Map linter reported no errors or warnings in your sector or metadata files')
        else:
            dlg = _LintJobResultsDialog(
                parent=self,
                results=results)
            dlg.exec()

class _CustomSectorTable(gui.ListTable):
    class ColumnType(enum.Enum):
        Name = 'Name'
        Location = 'Location'

    AllColumns = [
        ColumnType.Name,
        ColumnType.Location
    ]

    _StateVersion = 'CustomSectorTable_v1'

    def __init__(
            self,
            columns: typing.Iterable[ColumnType] = AllColumns
            ) -> None:
        super().__init__()

        self.setColumnHeaders(columns)
        self.resizeColumnsToContents() # Size columns to header text
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)

        self.synchronise()

    def sector(self, row: int) -> typing.Optional[astronomer.SectorInfo]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)

    def sectorRow(self, sector: astronomer.SectorInfo) -> int:
        for row in range(self.rowCount()):
            if sector == self.sector(row):
                return row
        return -1

    def currentSector(self) -> typing.Optional[astronomer.SectorInfo]:
        row = self.currentRow()
        if row < 0:
            return None
        return self.sector(row)

    def setCurrentSector(
            self,
            sector: typing.Optional[astronomer.SectorInfo]
            ) -> None:
        if sector:
            row = self.sectorRow(sector)
            if row < 0:
                return
            item = self.item(row, 0)
            self.setCurrentItem(item)
        else:
            self.setCurrentItem(None)

    def synchronise(self) -> None:
        sectors = astronomer.DataStore.instance().sectors(
            milieu=app.Config.instance().value(option=app.ConfigOption.Milieu))

        # Disable sorting while inserting multiple rows then sort once after they've
        # all been added
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            currentSectors = set()
            for row in range(self.rowCount() - 1, -1, -1):
                sector = self.sector(row)
                if sector not in sectors:
                    self.removeRow(row)
                else:
                    currentSectors.add(sector)

            for sector in sectors:
                if not sector.isCustomSector():
                    continue # Ignore standard sectors
                if sector in currentSectors:
                    continue # Table already has an entry for the sector

                row = self.rowCount()
                self.insertRow(row)
                self._fillRow(row, sector)
        finally:
            self.setSortingEnabled(sortingEnabled)

        # Force a selection if there isn't one
        if not self.hasSelection() and self.rowCount() > 0:
            self.setCurrentRow(0)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(_CustomSectorTable._StateVersion)

        currentSector = self.currentSector()
        stream.writeQString(currentSector.canonicalName() if currentSector else '')

        baseState = super().saveState()
        stream.writeUInt32(baseState.count() if baseState else 0)
        if baseState:
            stream.writeRawData(baseState.data())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != _CustomSectorTable._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore CustomSectorTable state (Incorrect version)')
            return False

        sectorName = stream.readQString()
        currentSector = None
        if sectorName:
            for row in range(self.rowCount()):
                sector = self.sector(row)
                if not sector:
                    continue
                if sector.canonicalName() == sectorName:
                    currentSector = sector
                    break
        if currentSector:
            self.setCurrentSector(currentSector)

        count = stream.readUInt32()
        if count <= 0:
            return True
        baseState = QtCore.QByteArray(stream.readRawData(count))
        if not super().restoreState(baseState):
            return False

        return True

    def _fillRow(
            self,
            row: int,
            sector: astronomer.SectorInfo
            ) -> int:
        # Workaround for the issue covered here, re-enabled after setting items
        # https://stackoverflow.com/questions/7960505/strange-qtablewidget-behavior-not-all-cells-populated-after-sorting-followed-b
        sortingEnabled = self.isSortingEnabled()
        self.setSortingEnabled(False)

        try:
            for column in range(self.columnCount()):
                columnType = self.columnHeader(column)
                tableItem = None
                if columnType == self.ColumnType.Name:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, sector.canonicalName())
                elif columnType == self.ColumnType.Location:
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, f'({sector.x()}, {sector.y()})')

                if tableItem:
                    self.setItem(row, column, tableItem)
                    tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, sector)

            # Take note of the sort column item so we can determine which row index after the table
            # has been sorted
            sortItem = self.item(row, self.horizontalHeader().sortIndicatorSection())
        finally:
            self.setSortingEnabled(sortingEnabled)

        # If we don't have a sort item we assume a derived class has overridden _fillRow to add custom
        # columns and the table is currently sorted by one of those columns. In this the expectation is
        # the derived class will be handling working out the post sort row index.
        return sortItem.row() if sortItem else row

class CustomSectorDialog(gui.DialogEx):
    _MinMapScale = gui.MapScale(log=5)
    _MaxMapScale = gui.MapScale(log=10)

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Custom Sectors',
            configSection='CustomSectorDialog',
            parent=parent)

        self._modified = False

        self.showMaximizeButton()

        self._setupSectorListControls()
        self._setupSectorDataControls()

        self._horizontalSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._horizontalSplitter.addWidget(self._sectorListGroupBox)
        self._horizontalSplitter.addWidget(self._sectorDataGroupBox)
        self._horizontalSplitter.setStretchFactor(0, 1)
        self._horizontalSplitter.setStretchFactor(1, 2)

        dialogLayout = QtWidgets.QHBoxLayout()
        dialogLayout.addWidget(self._horizontalSplitter)

        self.setLayout(dialogLayout)

        app.Config.instance().configChanged.connect(self._appConfigChanged)

    def modified(self) -> bool:
        return self._modified

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
            key='SectorDataDisplayModeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._sectorDataTabView.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._horizontalSplitter.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('SectorTableState', self._sectorTable.saveState())
        self._settings.setValue('SectorDataDisplayModeState', self._sectorDataTabView.saveState())
        self._settings.setValue('SplitterState', self._horizontalSplitter.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        QtCore.QTimer.singleShot(0, self._showWelcomeMessage)
        super().firstShowEvent(e)

    def _setupSectorListControls(self) -> None:
        self._sectorTable = _CustomSectorTable()
        self._sectorTable.selectionModel().selectionChanged.connect(self._sectorSelectionChanged)

        self._newSectorButton = QtWidgets.QPushButton('New...')
        self._newSectorButton.clicked.connect(self._newSectorClicked)

        self._deleteSectorButton = QtWidgets.QPushButton('Delete...')
        self._deleteSectorButton.clicked.connect(self._deleteSectorClicked)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addWidget(self._newSectorButton)
        buttonLayout.addWidget(self._deleteSectorButton)
        buttonLayout.addStretch()

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addLayout(buttonLayout)
        groupLayout.addWidget(self._sectorTable)

        self._sectorListGroupBox = QtWidgets.QGroupBox('Sectors')
        self._sectorListGroupBox.setLayout(groupLayout)

    def _setupSectorDataControls(self) -> None:
        monospaceFont = gui.getMonospaceFont()

        self._sectorFileTextEdit = QtWidgets.QPlainTextEdit()
        self._sectorFileTextEdit.setFont(monospaceFont)
        self._sectorFileTextEdit.setReadOnly(True)

        self._sectorMetadataTextEdit = QtWidgets.QPlainTextEdit()
        self._sectorMetadataTextEdit.setFont(monospaceFont)
        self._sectorMetadataTextEdit.setReadOnly(True)

        self._sectorMapWidget = gui.MapWidgetEx(
            universe=astronomer.Universe(sectors=[]),
            milieu=app.Config.instance().value(option=app.ConfigOption.Milieu),
            rules=app.Config.instance().value(option=app.ConfigOption.Rules),
            style=app.Config.instance().value(option=app.ConfigOption.MapStyle),
            options=app.Config.instance().value(option=app.ConfigOption.MapOptions),
            rendering=app.Config.instance().value(option=app.ConfigOption.MapRendering),
            animated=app.Config.instance().value(option=app.ConfigOption.MapAnimations),
            worldTagging=app.Config.instance().value(option=app.ConfigOption.WorldTagging),
            taggingColours=app.Config.instance().value(option=app.ConfigOption.TaggingColours))
        self._sectorMapWidget.setViewScaleLimits(
            minScale=CustomSectorDialog._MinMapScale,
            maxScale=CustomSectorDialog._MaxMapScale)
        self._sectorMapWidget.mapStyleChanged.connect(self._mapStyleChanged)
        self._sectorMapWidget.mapOptionsChanged.connect(self._mapOptionsChanged)
        self._sectorMapWidget.mapRenderingChanged.connect(self._mapRenderingChanged)
        self._sectorMapWidget.mapAnimationChanged.connect(self._mapAnimationChanged)

        mapLayout = QtWidgets.QVBoxLayout()
        mapLayout.setContentsMargins(0, 0, 0, 0)
        mapLayout.setSpacing(0)
        mapLayout.addWidget(self._sectorMapWidget)
        mapLayoutWidget = QtWidgets.QWidget()
        mapLayoutWidget.setLayout(mapLayout)

        self._sectorDataTabView = gui.TabWidgetEx()
        self._sectorDataTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self._sectorDataTabView.addTab(self._sectorFileTextEdit, 'Sector')
        self._sectorDataTabView.addTab(self._sectorMetadataTextEdit, 'Metadata')
        self._sectorDataTabView.addTab(mapLayoutWidget, 'Maps')

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._sectorDataTabView)

        self._sectorDataGroupBox = QtWidgets.QGroupBox('Map Images')
        self._sectorDataGroupBox.setLayout(groupLayout)

        # Sync the controls to the currently selected sector
        self._syncSectorDataControls(sectorInfo=self._sectorTable.currentSector())

    def _sectorSelectionChanged(self) -> None:
        self._syncSectorDataControls(sectorInfo=self._sectorTable.currentSector())

    def _syncSectorDataControls(
            self,
            sectorInfo: typing.Optional[astronomer.SectorInfo]
            ) -> None:
        if not sectorInfo:
            self._sectorFileTextEdit.clear()
            self._sectorMetadataTextEdit.clear()
            self._sectorMapWidget.setUniverse(universe=astronomer.Universe(sectors=[]))
            return

        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)

        try:
            sectorContent = astronomer.DataStore.instance().sectorFileData(
                sectorName=sectorInfo.canonicalName(),
                milieu=milieu)
            self._sectorFileTextEdit.setPlainText(sectorContent)
        except Exception as ex:
            self._sectorFileTextEdit.clear()

            message = 'Failed to retrieve sector file data.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            # Continue to try and sync other controls

        try:
            metadataContent = astronomer.DataStore.instance().sectorMetaData(
                sectorName=sectorInfo.canonicalName(),
                milieu=milieu)
            self._sectorMetadataTextEdit.setPlainText(metadataContent)
        except Exception as ex:
            self._sectorMetadataTextEdit.clear()

            message = 'Failed to retrieve sector metadata.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            # Continue to try and sync other controls

        universe, sector = astronomer.WorldManager.instance().createSectorUniverse(
            milieu=milieu,
            sectorContent=sectorContent,
            metadataContent=metadataContent)

        self._sectorMapWidget.setUniverse(universe=universe)

        sectorIndex = sector.index()
        left, top, width, height = sectorIndex.worldBounds()
        sectorCenter = QtCore.QPointF(left + (width / 2), top + (height / 2))
        self._sectorMapWidget.setViewAreaLimits(
            upperLeft=QtCore.QPointF(left, top),
            lowerRight=QtCore.QPointF(left + width, top + height))
        self._sectorMapWidget.setView(
            center=sectorCenter,
            scale=CustomSectorDialog._MinMapScale,
            immediate=True)
        self._sectorMapWidget.setHomePosition(
            center=sectorCenter,
            scale=CustomSectorDialog._MinMapScale)
        self._sectorMapWidget.setInfoHex(hex=None)

    def _newSectorClicked(self) -> None:
        dialog = _NewSectorDialog(parent=self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        newSector = dialog.sector()
        assert(newSector != None)

        self._modified = True
        self._sectorTable.synchronise()

        # Select the sector that was just added
        row = self._sectorTable.sectorRow(newSector)
        if row >= 0:
            self._sectorTable.setCurrentRow(row)

    def _deleteSectorClicked(self) -> None:
        sector = self._sectorTable.currentSector()
        if not sector:
            gui.MessageBoxEx.information(
                parent=self,
                text='No sector selected for deletion')

        answer = gui.MessageBoxEx.question(
            parent=self,
            text=f'Are you sure you want to delete {sector.canonicalName()}')
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return # User cancelled

        try:
            astronomer.DataStore.instance().deleteCustomSector(
                sectorName=sector.canonicalName(),
                milieu=app.Config.instance().value(option=app.ConfigOption.Milieu))
        except Exception as ex:
            message = f'Failed to delete {sector.canonicalName()}'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            # Continue in order to sync the table if an error occurs as we don't know what state
            # the data store was left in after the error

        self._modified = True
        self._sectorTable.synchronise()

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

    def _appConfigChanged(
            self,
            option: app.ConfigOption,
            oldValue: typing.Any,
            newValue: typing.Any
            ) -> None:
        if option is app.ConfigOption.Milieu:
            self._sectorMapWidget.setMilieu(milieu=newValue)
        elif option is app.ConfigOption.Rules:
            self._sectorMapWidget.setRules(rules=newValue)
        elif option is app.ConfigOption.MapStyle:
            self._sectorMapWidget.setMapStyle(style=newValue)
        elif option is app.ConfigOption.MapOptions:
            self._sectorMapWidget.setMapOptions(options=newValue)
        elif option is app.ConfigOption.MapRendering:
            self._sectorMapWidget.setRendering(rendering=newValue)
        elif option is app.ConfigOption.MapAnimations:
            self._sectorMapWidget.setAnimated(animated=newValue)
        elif option is app.ConfigOption.WorldTagging:
            self._sectorMapWidget.setWorldTagging(tagging=newValue)
        elif option is app.ConfigOption.TaggingColours:
            self._sectorMapWidget.setTaggingColours(colours=newValue)

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            # v1 = Initial custom sector release
            # v2 = Update for local rendering
            noShowAgainId='CustomSectorsWelcome_v2')
        message.exec()
