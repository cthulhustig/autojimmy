import app
import enum
import gui
import jobs
import logging
import os
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

# TODO: Welcome message

# This defines the scales of the different map images that will be generated. The values
# are specifically chosen to match up with the scales that the Traveller Map rendering 
# code makes significant changes to how it renders the sector (e.g. transitioning from
# full world info -> no names -> no worlds)
# It's important that this is defined from largest to smallest as this will be the
# order the maps are generated in and the generating the largest is the most likely to
# fail so best to do it first
# TODO: Need to check with Joshua that generating 5 maps is cool
_CustomMapScales = [128, 64, 32, 16, 3]

class _NewSectorDialog(gui.DialogEx):
    _XmlFileFilter = 'XML Files(*.xml)'
    _AllFileFilter = 'All Files(*.*)'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='New Custom Sector',
            configSection='NewCustomSectorDialog',
            parent=parent)
        
        self._recentDirectoryPath = None
        self._posterJob = None
        self._sectorData = None
        self._sectorMetadata = None
        self._sector = None
        
        self._setupFileSelectControls()
        self._setupRenderOptionControls()
        self._setupDialogButtons()

        dialogLayout = QtWidgets.QVBoxLayout()
        dialogLayout.addWidget(self._filesGroupBox)
        dialogLayout.addWidget(self._renderOptionsGroupBox)
        dialogLayout.addLayout(self._buttonLayout)

        self.setLayout(dialogLayout)
        self.setFixedHeight(self.sizeHint().height())

    def sector(self) -> typing.Optional[travellermap.SectorInfo]:
        return self._sector

    def loadSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='RecentDirectory',
            type=str)
        if storedValue:
            self._recentDirectoryPath = storedValue

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('RecentDirectory', self._recentDirectoryPath)
        self._settings.endGroup()    
    
    def _setupFileSelectControls(self) -> None:
        self._sectorFileLineEdit = gui.LineEditEx()
        self._sectorFileBrowseButton = QtWidgets.QPushButton('Browse...')
        self._sectorFileBrowseButton.clicked.connect(self._sectorFileBrowseClicked)
        sectorLayout = QtWidgets.QHBoxLayout()
        sectorLayout.setContentsMargins(0, 0, 0, 0)
        sectorLayout.addWidget(self._sectorFileLineEdit)
        sectorLayout.addWidget(self._sectorFileBrowseButton)
        
        self._metadataFileLineEdit = gui.LineEditEx()
        self._metadataFileBrowseButton = QtWidgets.QPushButton('Browse...')
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

    # NOTE: This only allows setting a subset of options that are available. In some cases I don't
    # thing anyone would ever want their custom sectors to always display the info (all overlays
    # fall into this category). Other options are client side so don't need to be included (i.e. 
    # mains)
    def _setupRenderOptionControls(self) -> None:
        style = app.Config.instance().mapStyle()
        options = app.Config.instance().mapOptions()

        self._renderStyleComboBox = gui.EnumComboBox(
            type=travellermap.Style,
            value=style)
                
        self._renderSectorGridCheckBox = gui.CheckBoxEx()
        self._renderSectorGridCheckBox.setChecked(
            travellermap.Option.SectorGrid in options)
        
        self._renderSectorNamesCheckBox = gui.CheckBoxEx()
        self._renderSectorNamesCheckBox.setChecked(
            travellermap.Option.SectorNames in options)

        self._renderRegionNamesCheckBox = gui.CheckBoxEx()
        self._renderRegionNamesCheckBox.setChecked(
            travellermap.Option.RegionNames in options)           

        self._renderBordersCheckBox = gui.CheckBoxEx()
        self._renderBordersCheckBox.setChecked(
            travellermap.Option.Borders in options)

        self._renderFilledBordersCheckBox = gui.CheckBoxEx()
        self._renderFilledBordersCheckBox.setChecked(
            travellermap.Option.FilledBorders in options)

        self._renderRoutesCheckBox = gui.CheckBoxEx()
        self._renderRoutesCheckBox.setChecked(
            travellermap.Option.Routes in options)         

        self._renderWorldColoursCheckBox = gui.CheckBoxEx()
        self._renderWorldColoursCheckBox.setChecked(
            travellermap.Option.WorldColours in options)        
        
        leftLayout = gui.FormLayoutEx()
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.addRow('Style:', self._renderStyleComboBox)
        leftLayout.addRow('Sector Grid:', self._renderSectorGridCheckBox)
        leftLayout.addRow('Sector Names:', self._renderSectorNamesCheckBox)
        leftLayout.addRow('Region Names:', self._renderRegionNamesCheckBox)

        rightLayout = gui.FormLayoutEx()
        rightLayout.setContentsMargins(0, 0, 0, 0)        
        rightLayout.addRow('Borders:', self._renderBordersCheckBox)
        rightLayout.addRow('Filled Borders:', self._renderFilledBordersCheckBox)
        rightLayout.addRow('Routes:', self._renderRoutesCheckBox)
        rightLayout.addRow('More World Colours:', self._renderWorldColoursCheckBox)

        groupLayout = QtWidgets.QHBoxLayout()
        groupLayout.addLayout(leftLayout)
        groupLayout.addLayout(rightLayout)
        groupLayout.addStretch()

        self._renderOptionsGroupBox = QtWidgets.QGroupBox('Render Options')
        self._renderOptionsGroupBox.setLayout(groupLayout)

    def _setupDialogButtons(self):
        self._createButton = QtWidgets.QPushButton('Create')
        self._createButton.setDefault(True)
        self._createButton.clicked.connect(self._createClicked)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        self._buttonLayout = QtWidgets.QHBoxLayout()
        self._buttonLayout.addStretch()
        self._buttonLayout.addWidget(self._createButton)
        self._buttonLayout.addWidget(self._cancelButton)

    def _syncControls(self) -> None:
        disable = self._posterJob != None
        self._filesGroupBox.setDisabled(disable)
        self._renderOptionsGroupBox.setDisabled(disable)
        self._createButton.setDisabled(disable)
        self._cancelButton.setDisabled(disable)

    def _sectorFileBrowseClicked(self) -> None:
        path = self._showFileSelect(
            caption='Sector File',
            filter=_NewSectorDialog._AllFileFilter)
        if not path:
            return # User cancelled
        self._sectorFileLineEdit.setText(path)

    def _metadataFileBrowseClicked(self) -> None:
        path = self._showFileSelect(
            caption='Metadata File',
            filter=f'{_NewSectorDialog._XmlFileFilter};;{_NewSectorDialog._AllFileFilter}')
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
        # TODO: This logic is duplicated in a few places, should consolidate. I don't think
        # this actually needs both, could just have the required base url (proxy or direct)
        # passed in from a higher level
        try:
            mapProxyPort = app.Config.instance().mapProxyPort()
            if mapProxyPort:
                mapUrl = f'http://127.0.0.1:{mapProxyPort}'
            else:
                mapUrl = app.Config.instance().travellerMapUrl()

            # TODO: Some sector file types use specific character encodings, need to make sure this
            # doesn't mess with them
            with open(self._sectorFileLineEdit.text(), 'r') as file:
                self._sectorData = file.read()

            # TODO: Validate sector file with my parsers

            with open(self._metadataFileLineEdit.text(), 'r') as file:
                self._sectorMetadata = file.read()

            # TODO: Validate metadata against XSD

            self._posterJob = jobs.PosterJob(
                parent=self,
                mapUrl=mapUrl,
                sectorData=self._sectorData,
                sectorMetadata=self._sectorMetadata,
                style=self._renderStyleComboBox.currentEnum(),
                options=self._renderOptionList(),
                scales=_CustomMapScales,
                compositing=True,
                finishedCallback=self._posterCreationFinished)
            self._syncControls()
        except Exception as ex:
            message = 'Failed to generate sector maps'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
        
    def _posterCreationFinished(
            self,
            result: typing.Union[typing.Dict[float, bytes], Exception]
            ) -> None:
        self._posterJob = None
        self._syncControls()

        if isinstance(result, Exception):
            message = 'Failed to generate posters'
            logging.error(message, exc_info=result)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=result)
            return
        
        assert(isinstance(result, dict))

        try:
            self._sector = travellermap.DataStore.instance().createCustomSector(
                sectorData=self._sectorData,
                sectorMetadata=self._sectorMetadata,
                sectorMaps=result,
                milieu=app.Config.instance().milieu())
        except Exception as ex:
            message = 'Failed to add custom sector to data store'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return
            
        self.accept()

    def _renderOptionList(self) -> typing.Iterable[travellermap.Option]:
        renderOptions = []

        if self._renderSectorGridCheckBox.isChecked():
            renderOptions.append(travellermap.Option.SectorGrid)

        if self._renderSectorNamesCheckBox.isChecked():
            renderOptions.append(travellermap.Option.SectorNames)
    
        if self._renderRegionNamesCheckBox.isChecked():
            renderOptions.append(travellermap.Option.RegionNames)

        if self._renderBordersCheckBox.isChecked():
            renderOptions.append(travellermap.Option.Borders)

        if self._renderFilledBordersCheckBox.isChecked():
            renderOptions.append(travellermap.Option.FilledBorders)

        if self._renderRoutesCheckBox.isChecked():
            renderOptions.append(travellermap.Option.Routes)

        if self._renderWorldColoursCheckBox.isChecked():
            renderOptions.append(travellermap.Option.WorldColours)            

        return renderOptions            

class _CustomSectorTable(gui.ListTable):
    class ColumnType(enum.Enum):
        Name = 'Name'
        Location = 'Location'

    AllColumns = [
        ColumnType.Name,
        ColumnType.Location
    ]

    def __init__(
            self,
            columns: typing.Iterable[ColumnType] = AllColumns
            ) -> None:
        super().__init__()

        self.setColumnHeaders(columns)
        self.resizeColumnsToContents() # Size columns to header text
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)

        self.synchronise()

    def sector(self, row: int) -> typing.Optional[travellermap.SectorInfo]:
        tableItem = self.item(row, 0)
        if not tableItem:
            return None
        return tableItem.data(QtCore.Qt.ItemDataRole.UserRole)
    
    def sectorRow(self, sector: travellermap.SectorInfo) -> int:
        for row in range(self.rowCount()):
            if sector == self.sector(row):
                return row
        return -1

    def currentSector(self) -> typing.Optional[travellermap.SectorInfo]:
        row = self.currentRow()
        if row < 0:
            return None
        return self.sector(row)     

    def synchronise(self) -> None:
        sectors = travellermap.DataStore.instance().sectors(
            milieu=app.Config.instance().milieu())

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
            self.selectRow(0)

    def _fillRow(
            self,
            row: int,
            sector: travellermap.SectorInfo
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

class _MapComboBox(gui.ComboBoxEx):
    def __init__(
            self,
            sectorInfo: typing.Optional[travellermap.SectorInfo] = None,
            *args,
            **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._sectorInfo = None
        if sectorInfo:
            self.setSectorInfo(sectorInfo)

    def sectorInfo(self) -> typing.Optional[travellermap.SectorInfo]:
        return self._sectorInfo

    def setSectorInfo(
            self,
            sectorInfo: typing.Optional[travellermap.SectorInfo]
            ) -> None:
        if sectorInfo == self._sectorInfo:
            return # Nothing to do

        self._sectorInfo = sectorInfo
        with gui.SignalBlocker(widget=self):
            self.clear()
            if sectorInfo:
                for scale in sectorInfo.mapLevels().keys():
                    self.addItem(f'{scale} Pixels Per Parsec', scale)
        self.currentIndexChanged.emit(self.currentIndex())

    def currentScale(self) -> typing.Optional[float]:
        currentIndex = self.currentIndex()
        if currentIndex < 0:
            return None
        return self.itemData(currentIndex, QtCore.Qt.ItemDataRole.UserRole)

class _MapImageView(gui.ImageView):
    def __init__(
            self,
            sectorInfo: typing.Optional[travellermap.SectorInfo] = None,
            scale: typing.Optional[float] = None,
            *args,
            **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._sectorInfo = None
        if sectorInfo != None and scale != None:
            self.setMapImage(
                sectorInfo=sectorInfo,
                scale=scale)

    def setMapImage(
            self,
            sectorInfo: typing.Optional[travellermap.SectorInfo],
            scale: typing.Optional[float],
            ) -> bool:
        self.clear()

        self._sectorInfo = sectorInfo
        mapImage = travellermap.DataStore.instance().sectorMapImage(
            sectorName=self._sectorInfo.canonicalName(),
            milieu=app.Config.instance().milieu(),
            scale=scale)
        if mapImage == None:
            return False
        return self.imageFromBytes(data=mapImage, type='PNG')

class CustomSectorDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Custom Sectors',
            configSection='CustomSectorDialog',
            parent=parent)
        
        self._modified = False

        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowMaximizeButtonHint)

        self._setupSectorListControls()
        self._setupSectorDataControls()

        self._horizontalSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._horizontalSplitter.addWidget(self._sectorListGroupBox)
        self._horizontalSplitter.addWidget(self._sectorDataGroupBox)

        dialogLayout = QtWidgets.QHBoxLayout()
        dialogLayout.addWidget(self._horizontalSplitter)

        self.setLayout(dialogLayout)

    def modified(self) -> bool:
        return self._modified

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
        monospaceFont = QtGui.QFont('unknown')
        monospaceFont.setStyleHint(QtGui.QFont.StyleHint.Monospace)

        self._sectorFileTextEdit = QtWidgets.QPlainTextEdit()
        self._sectorFileTextEdit.setFont(monospaceFont)
        self._sectorFileTextEdit.setReadOnly(True)

        self._sectorMetadataTextEdit = QtWidgets.QPlainTextEdit()
        self._sectorMetadataTextEdit.setFont(monospaceFont)
        self._sectorMetadataTextEdit.setReadOnly(True)

        self._mapSelectionComboBox = _MapComboBox()
        self._mapSelectionComboBox.currentIndexChanged.connect(self._mapSelectionChanged)

        self._mapGraphicsView = _MapImageView()

        mapLayout = QtWidgets.QVBoxLayout()
        mapLayout.setContentsMargins(0, 0, 0, 0)
        mapLayout.addWidget(self._mapSelectionComboBox)
        mapLayout.addWidget(self._mapGraphicsView)
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

    def _mapSelectionChanged(self) -> None:
        self._mapGraphicsView.setMapImage(
            sectorInfo=self._mapSelectionComboBox.sectorInfo(),
            scale=self._mapSelectionComboBox.currentScale())
        
    def _syncSectorDataControls(
            self,
            sectorInfo: typing.Optional[travellermap.SectorInfo]
            ) -> None:
        if not sectorInfo:
            self._sectorFileTextEdit.clear()
            self._sectorMetadataTextEdit.clear()
            self._mapSelectionComboBox.setSectorInfo(None)
            return
        
        milieu = app.Config.instance().milieu()
        
        try:
            fileData = travellermap.DataStore.instance().sectorFileData(
                sectorName=sectorInfo.canonicalName(),
                milieu=milieu)
            self._sectorFileTextEdit.setPlainText(fileData)
        except Exception as ex:
            self._sectorFileTextEdit.clear()
            # TODO: Log something
            gui.MessageBoxEx.critical(
                parent=self,
                text='Failed to retrieve sector file data.',
                exception=ex)
            # Continue to try and sync other controls

        try:
            metaData = travellermap.DataStore.instance().sectorMetaData(
                sectorName=sectorInfo.canonicalName(),
                milieu=milieu)
            self._sectorMetadataTextEdit.setPlainText(metaData)
        except Exception as ex:
            self._sectorMetadataTextEdit.clear()
            # TODO: Log something
            gui.MessageBoxEx.critical(
                parent=self,
                text='Failed to retrieve sector file data.',
                exception=ex)
            # Continue to try and sync other controls

        # This will trigger an update of the map graphics view
        self._mapSelectionComboBox.setSectorInfo(sectorInfo=sectorInfo)

    def _newSectorClicked(self) -> None:
        dialog = _NewSectorDialog()
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        
        newSector = dialog.sector()
        assert(newSector != None)

        self._modified = True
        self._sectorTable.synchronise()

        # Select the sector that was just added
        row = self._sectorTable.sectorRow(newSector)
        if row >= 0:
            self._sectorTable.selectRow(row)

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
            travellermap.DataStore.instance().deleteCustomSector(
                sectorName=sector.canonicalName(),
                milieu=app.Config.instance().milieu())
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
