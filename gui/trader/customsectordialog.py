import app
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
        
        self._setupFileSelectControls()
        self._setupRenderOptionControls()
        self._setupDialogButtons()

        dialogLayout = QtWidgets.QVBoxLayout()
        dialogLayout.addWidget(self._filesGroupBox)
        dialogLayout.addWidget(self._renderOptionsGroupBox)
        dialogLayout.addLayout(self._buttonLayout)

        self.setLayout(dialogLayout)
        self.setFixedHeight(self.sizeHint().height())

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
            gui.MessageBoxEx.critical(message, exception=ex)
        
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
            travellermap.DataStore.instance().createCustomSector(
                sectorData=self._sectorData,
                sectorMetadata=self._sectorMetadata,
                sectorMaps=result,
                milieu=app.Config.instance().milieu())
        except Exception as ex:
            message = 'Failed to add custom sector to data store'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(message, exception=ex)
            
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

class _SectorListWidget(gui.ListWidgetEx):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._synchronise()

    def _synchronise(self) -> None:
        sectors = travellermap.DataStore.instance().sectors(
            milieu=app.Config.instance().milieu())
        self.clear()
        for sector in sectors:
            if not sector.isCustomSector():
                continue
            item = gui.NaturalSortListWidgetItem(sector.canonicalName())
            item.setData(QtCore.Qt.ItemDataRole.UserRole, sector)
            self.addItem(item)
        if self.count() > 0:
            self.setCurrentRow(0)

    def selectedSector(self) -> typing.Optional[travellermap.SectorInfo]:
        items = self.selectedItems()
        if not items or len(items) != 1:
            return None
        item = items[0]
        return item.data(QtCore.Qt.ItemDataRole.UserRole)

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

        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowMaximizeButtonHint)

        self._setupSectorListControls()
        self._setupSectorDataControls()

        self._horizontalSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._horizontalSplitter.addWidget(self._sectorListGroupBox)
        self._horizontalSplitter.addWidget(self._sectorDataGroupBox)

        dialogLayout = QtWidgets.QHBoxLayout()
        dialogLayout.addWidget(self._horizontalSplitter)

        self.setLayout(dialogLayout)

    def _setupSectorListControls(self) -> None:
        self._sectorList = _SectorListWidget()
        self._sectorList.selectionModel().selectionChanged.connect(self._sectorSelectionChanged)

        self._sectorListToolbar = QtWidgets.QToolBar("Sector Toolbar")
        self._sectorListToolbar.setIconSize(QtCore.QSize(32, 32))
        self._sectorListToolbar.setOrientation(QtCore.Qt.Orientation.Vertical)
        self._sectorListToolbar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        self._newSectorAction = QtWidgets.QAction(gui.loadIcon(gui.Icon.NewFile), 'New', self)
        self._newSectorAction.triggered.connect(self._newSectorClicked)
        self._sectorList.addAction(self._newSectorAction)
        self._sectorListToolbar.addAction(self._newSectorAction)

        self._renameSectorAction = QtWidgets.QAction(gui.loadIcon(gui.Icon.RenameFile), 'Rename...', self)
        self._renameSectorAction.triggered.connect(self._renameSectorClicked)
        self._sectorList.addAction(self._renameSectorAction)
        self._sectorListToolbar.addAction(self._renameSectorAction)

        self._deleteSectorAction = QtWidgets.QAction(gui.loadIcon(gui.Icon.DeleteFile), 'Delete...', self)
        self._deleteSectorAction.triggered.connect(self._deleteSectorClicked)
        self._sectorList.addAction(self._deleteSectorAction)
        self._sectorListToolbar.addAction(self._deleteSectorAction)               

        groupLayout = QtWidgets.QHBoxLayout()
        groupLayout.addWidget(self._sectorListToolbar)
        groupLayout.addWidget(self._sectorList)

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
        self._syncSectorDataControls(sectorInfo=self._sectorList.selectedSector())

    def _sectorSelectionChanged(self) -> None:
        self._syncSectorDataControls(sectorInfo=self._sectorList.selectedSector())

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
            gui.MessageBoxEx.critical('Failed to retrieve sector file data.', exception=ex)

        try:
            metaData = travellermap.DataStore.instance().sectorMetaData(
                sectorName=sectorInfo.canonicalName(),
                milieu=milieu)
            self._sectorMetadataTextEdit.setPlainText(metaData)
        except Exception as ex:
            self._sectorMetadataTextEdit.clear()
            # TODO: Log something
            gui.MessageBoxEx.critical('Failed to retrieve sector file data.', exception=ex)

        # This will trigger an update of the map graphics view
        self._mapSelectionComboBox.setSectorInfo(sectorInfo=sectorInfo)

    def _newSectorClicked(self) -> None:
        dialog = _NewSectorDialog()
        dialog.exec()

    def _renameSectorClicked(self) -> None:
        # TODO: Rename sector
        pass

    def _deleteSectorClicked(self) -> None:
        # TODO: delete sector
        pass