import app
import common
import enum
import gui
import jobs
import logging
import os
import travellermap
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

    <p>How custom sectors are drawn in windows displaying the map differs
    depending on if you're using the default local rendering, where {name}
    draws the map, or if you're using one of the legacy web based rendering,
    where the Traveller Map server draws it.</p>
    <p>If local rendering is used, {name} will draw custom sectors at the
    same time as it's drawing the rest of the map. Custom sectors will be
    indistinguishable from other sectors and will update if the map style or
    draw options are changed.</p>
    <p>If one of the web based rendering methods is used, {name} will use
    Traveller Map to draw the stock map, then composites the custom sectors
    on top of that. This uses images of the custom sectors that are
    automatically generated using the Traveller Map Poster API at the point
    the sector is added to {name}. This approach to drawing custom sectors
    has a few of significant drawbacks. Most significant of those are, there
    can be graphical artifacts where a custom sector borders another sector
    or at high zoom levels, and, the map style and draw options are set at
    the point the custom sector is created, so custom sectors will not
    update if they're changed later.<p>

    <p>Web based rendering is now considered a legacy feature and will most
    likely be removed in a future version of {name}. If you do choose to use
    when also using custom sectors, there are a few additional things to be
    aware of:
    <ul style="margin-left:15px; -qt-list-indent:0;">
    <li>The eye candy style isn't supported.</li>
    <li>{name} support 3 modes of composition with web based rendering. Which
    is used is dependent on configuration and if CairoSVG is installed. The
    composition modes are:</li>
    <ul style="margin-left:15px; -qt-list-indent:0;">
    <li><i>Bitmap</i> - This is the fallback mode if CairoSVG is not installed.
    {name} uses Traveller Map to generate bitmap posters for composition. This
    method suffers from the most visual artifacts.</li>
    <li><i>Hybrid</i> - This is the default mode if CairoSVG is installed.
    {name} uses Traveller Map to generate SVG posters, these posters are
    pre-processed and converted to bitmap layers prior to composition. This
    method prevents some of the visual artifacts around the borders of custom
    sectors.</li>
    <li><i>SVG</i> - This method of composition can be enabled from the
    configuration dialog if CairoSVG is installed. {name} uses Traveller Map to
    generate SVG posters, these SVG posters are only converted to bitmaps at the
    point tile composition occurs. This method prevents blockiness at high zoom
    levels and some of the visual artifacts around the borders, however it's
    <b>significantly</b> more CPU intensive than other methods and only suitable
    for systems with high core counts.</ul>
    </ul></p>
    </html>
""".format(name=app.AppName)

_JsonMetadataWarning = """
    <html>
    <p>You're using JSON metadata which isn't officially supported by the
    Traveller Map Poster API that's used to generate images of custom sectors.
    The metadata will be automatically converted to XML format before uploading
    it to Traveller Map. This is mostly a transparent process, however any
    parsing errors returned by Traveller Map will refer to the XML
    representation of the data.</p>
    </html>
""".format(name=app.AppName)
_JsonMetadataWarningNoShowStateKey = 'JsonMetadataConversionWarning'

# This defines the scales of the different map images that will be generated. The values
# are specifically chosen to match up with the scales that the Traveller Map rendering
# code makes significant changes to how it renders the sector (e.g. transitioning from
# full world info -> no names -> no worlds)
# It's important that this is defined from largest to smallest as this will be the
# order the maps are generated in and the generating the largest is the most likely to
# fail so best to do it first.
# Once you get to a scale lower than 4 the poster API stops generating posters that really
# look like what is rendered by the tile API. You don't get the red sector overlay and
# the background colour can be noticeably different.
# NOTE: SVGs put less load on Traveller Map so I've added an extra scale to make the
# compositing more seamless
_BitmapCustomMapScales = [128, 64, 32, 16, 4]

# TODO: This should go away as part of these changes
_TravellerMapUrl = 'https://www.travellermap.com'

# This intentionally doesn't inherit from DialogEx. We don't want it saving its size as it
# can cause incorrect sizing if the font scaling is increased then decreased
class _PosterJobDialog(QtWidgets.QDialog):
    _GeneratingProgressDotCount = 5

    def __init__(
            self,
            title: str,
            job: jobs.PosterJobAsync,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._job = job
        self._job.complete.connect(self._jobComplete)
        self._job.progress.connect(self._jobEvent)
        self._posters = None
        self._generatingTimer = QtCore.QTimer()
        self._generatingTimer.timeout.connect(self._generatingTimerFired)
        self._generatingTimer.setInterval(500)
        self._generatingTimer.setSingleShot(False)

        self._mapLabel = gui.PrefixLabel(prefix='Map: ')
        self._uploadingLabel = gui.PrefixLabel(prefix='Uploading: ')
        self._generatingLabel = gui.PrefixLabel(prefix='Generating: ')
        self._downloadingLabel = gui.PrefixLabel(prefix='Downloading: ')

        progressLayout = QtWidgets.QVBoxLayout()
        progressLayout.addWidget(self._mapLabel)
        progressLayout.addWidget(self._uploadingLabel)
        progressLayout.addWidget(self._generatingLabel)
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

    def posters(self) -> typing.Optional[typing.Mapping[int, travellermap.MapImage]]:
        return self._posters

    def exec(self) -> int:
        try:
            self._job.run()
        except Exception as ex:
            message = 'Failed to start poster job'
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
            result: typing.Union[typing.Mapping[int, travellermap.MapImage], Exception]
            ) -> None:
        self._generatingTimer.stop()

        if isinstance(result, Exception):
            message = 'Map creation job failed'
            logging.critical(message, exc_info=result)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=result)
            self.close()
        else:
            self._posters = result
            self.accept()

    def _jobEvent(
            self,
            event: jobs.PosterJobAsync.ProgressEvent,
            scale: int,
            stageIndex: int,
            totalStages: int,
            currentBytes: int,
            totalBytes: int
            ) -> None:
        self._mapLabel.setText(f'{scale} pixels per parsec ({stageIndex + 1}/{totalStages})')

        if totalBytes > 0:
            progressText = common.humanFriendlyByteSizes(currentBytes) + ' / ' + \
                common.humanFriendlyByteSizes(totalBytes)
        else:
            progressText = common.humanFriendlyByteSizes(currentBytes)

        if event == jobs.PosterJobAsync.ProgressEvent.Uploading:
            if currentBytes == 0:
                self._generatingLabel.setText('')
                self._downloadingLabel.setText('')

            self._uploadingLabel.setText(progressText)

            if currentBytes == totalBytes:
                self._generatingTimer.start()
        elif event == jobs.PosterJobAsync.ProgressEvent.Downloading:
            if currentBytes == 0:
                self._generatingTimer.stop()
                self._generatingLabel.setText('Complete')

            self._downloadingLabel.setText(progressText)

    def _generatingTimerFired(self) -> None:
        text = self._generatingLabel.text()
        if (len(text) % _PosterJobDialog._GeneratingProgressDotCount) == 0:
            text = ''
        text += '.'
        self._generatingLabel.setText(text)

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

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='StyleComboBoxState',
            type=QtCore.QByteArray)
        if storedValue:
            self._renderStyleComboBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SectorGridCheckBoxState',
            type=QtCore.QByteArray)
        if storedValue:
            self._renderSectorGridCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SectorNamesComboBoxState',
            type=QtCore.QByteArray)
        if storedValue:
            self._renderSectorNamesComboBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='RegionNamesCheckBoxState',
            type=QtCore.QByteArray)
        if storedValue:
            self._renderRegionNamesCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='BordersCheckBoxState',
            type=QtCore.QByteArray)
        if storedValue:
            self._renderBordersCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='FilledBordersCheckBoxState',
            type=QtCore.QByteArray)
        if storedValue:
            self._renderFilledBordersCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='RoutesCheckBoxState',
            type=QtCore.QByteArray)
        if storedValue:
            self._renderRoutesCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='WorldColoursCheckBoxState',
            type=QtCore.QByteArray)
        if storedValue:
            self._renderWorldColoursCheckBox.restoreState(storedValue)

        self._settings.endGroup()

    def accept(self) -> None:
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('RecentDirectory', self._recentDirectoryPath)
        self._settings.setValue('SectorFilePath', self._sectorFileLineEdit.text())
        self._settings.setValue('MetadataFilePath', self._metadataFileLineEdit.text())
        self._settings.setValue('StyleComboBoxState', self._renderStyleComboBox.saveState())
        self._settings.setValue('SectorGridCheckBoxState', self._renderSectorGridCheckBox.saveState())
        self._settings.setValue('SectorNamesComboBoxState', self._renderSectorNamesComboBox.saveState())
        self._settings.setValue('RegionNamesCheckBoxState', self._renderRegionNamesCheckBox.saveState())
        self._settings.setValue('BordersCheckBoxState', self._renderBordersCheckBox.saveState())
        self._settings.setValue('FilledBordersCheckBoxState', self._renderFilledBordersCheckBox.saveState())
        self._settings.setValue('RoutesCheckBoxState', self._renderRoutesCheckBox.saveState())
        self._settings.setValue('WorldColoursCheckBoxState', self._renderWorldColoursCheckBox.saveState())
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

    # NOTE: This only allows setting a subset of options that are available. In some cases I don't
    # thing anyone would ever want their custom sectors to always display the info (all overlays
    # fall into this category). Other options are client side so don't need to be included (i.e.
    # mains)
    def _setupRenderOptionControls(self) -> None:
        style = app.Config.instance().value(option=app.ConfigOption.MapStyle)
        options = app.Config.instance().value(option=app.ConfigOption.MapOptions)

        supportedStyles = [s for s in travellermap.Style if s is not travellermap.Style.Candy]
        self._renderStyleComboBox = gui.EnumComboBox(
            type=travellermap.Style,
            value=style,
            options=supportedStyles)

        self._renderSectorGridCheckBox = gui.CheckBoxEx()
        self._renderSectorGridCheckBox.setChecked(
            travellermap.Option.SectorGrid in options)

        renderSectorNames = None
        if travellermap.Option.SectorNames in options:
            renderSectorNames = travellermap.Option.SectorNames
        elif travellermap.Option.SelectedSectorNames in options:
            renderSectorNames = travellermap.Option.SelectedSectorNames
        self._renderSectorNamesComboBox = gui.EnumComboBox(
            type=travellermap.Option,
            value=renderSectorNames,
            isOptional=True,
            options=[
                travellermap.Option.SelectedSectorNames,
                travellermap.Option.SectorNames],
            textMap={
                travellermap.Option.SelectedSectorNames: 'Selected',
                travellermap.Option.SectorNames: 'All'})

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
        leftLayout.addRow('Sector Names:', self._renderSectorNamesComboBox)
        leftLayout.addRow('Region Names:', self._renderRegionNamesCheckBox)

        rightLayout = gui.FormLayoutEx()
        rightLayout.setContentsMargins(0, 0, 0, 0)
        rightLayout.addRow('Borders:', self._renderBordersCheckBox)
        rightLayout.addRow('Filled Borders:', self._renderFilledBordersCheckBox)
        rightLayout.addRow('Routes:', self._renderRoutesCheckBox)
        rightLayout.addRow('More World Colours:', self._renderWorldColoursCheckBox)

        optionsLayout = QtWidgets.QHBoxLayout()
        optionsLayout.setContentsMargins(0, 0, 0, 0)
        optionsLayout.addLayout(leftLayout)
        optionsLayout.addLayout(rightLayout)
        optionsLayout.addStretch()

        infoLabel = QtWidgets.QLabel(
            '* These options only apply to custom sectors if you switch to legacy web based rendering. When using local rendering, custom sectors will be drawn using the same options as the rest of the map and will update dynamically as you change those options.')
        infoLabel.setWordWrap(True)
        infoLabel.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Minimum)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addLayout(optionsLayout)
        groupLayout.addSpacing(int(10 * gui.interfaceScale()))
        groupLayout.addWidget(infoLabel)

        self._renderOptionsGroupBox = QtWidgets.QGroupBox('Web Rendering Options*')
        self._renderOptionsGroupBox.setLayout(groupLayout)

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

        renderStyle = self._renderStyleComboBox.currentEnum()
        renderOptions = self._renderOptionList()

        xmlMetadata = None
        try:
            with open(metadataFilePath, 'r', encoding='utf-8-sig') as file:
                sectorMetadata = file.read()

            metadataFormat = travellermap.metadataFileFormatDetect(
                content=sectorMetadata)
            if not metadataFormat:
                raise RuntimeError('Unknown metadata file format')

            rawMetadata = travellermap.readMetadata(
                content=sectorMetadata,
                format=metadataFormat,
                identifier=metadataFilePath)

            if metadataFormat == travellermap.MetadataFormat.XML:
                xmlMetadata = sectorMetadata
                travellermap.DataStore.instance().validateSectorMetadataXML(xmlMetadata)
            else:
                gui.AutoSelectMessageBox.information(
                    parent=self,
                    text=_JsonMetadataWarning,
                    stateKey=_JsonMetadataWarningNoShowStateKey)

                xmlMetadata = travellermap.writeXMLMetadata(
                    metadata=rawMetadata,
                    identifier='Generated XML metadata')

            # This will throw if there is a conflict with an existing sector
            travellermap.DataStore.instance().customSectorConflictCheck(
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

            sectorFormat = travellermap.sectorFileFormatDetect(content=sectorData)
            if not sectorFormat:
                raise RuntimeError('Unknown sector file format')
            travellermap.readSector(
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
            posterJob = jobs.PosterJobAsync(
                parent=self,
                mapUrl=_TravellerMapUrl,
                sectorData=sectorData,
                xmlMetadata=xmlMetadata, # Poster API always uses XML metadata
                style=renderStyle,
                options=renderOptions,
                scales=_BitmapCustomMapScales,
                compositing=True)
            progressDlg = _PosterJobDialog(
                parent=self,
                title='Map Creation',
                job=posterJob)
            if progressDlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                return
            posters = posterJob.posters()
        except Exception as ex:
            message = 'Failed to generate sector maps'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        try:
            self._sector = travellermap.DataStore.instance().createCustomSector(
                milieu=app.Config.instance().value(option=app.ConfigOption.Milieu),
                sectorContent=sectorData,
                metadataContent=sectorMetadata, # Write the users metadata, not the xml metadata if it was converted
                customMapStyle=renderStyle,
                customMapOptions=renderOptions,
                customMapImages=posters)
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

                metadataFormat = travellermap.metadataFileFormatDetect(
                    content=sectorMetadata)
                if not metadataFormat:
                    raise RuntimeError('Unknown metadata file format')

                if metadataFormat == travellermap.MetadataFormat.XML:
                    xmlMetadata = sectorMetadata
                    travellermap.DataStore.instance().validateSectorMetadataXML(xmlMetadata)
                else:
                    gui.AutoSelectMessageBox.information(
                        parent=self,
                        text=_JsonMetadataWarning,
                        stateKey=_JsonMetadataWarningNoShowStateKey)

                    rawMetadata = travellermap.readMetadata(
                        content=sectorMetadata,
                        format=metadataFormat,
                        identifier=metadataFilePath)
                    xmlMetadata = travellermap.writeXMLMetadata(
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
                mapUrl=_TravellerMapUrl,
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

    def _renderOptionList(self) -> typing.Iterable[travellermap.Option]:
        renderOptions = []

        if self._renderSectorGridCheckBox.isChecked():
            renderOptions.append(travellermap.Option.SectorGrid)

        if self._renderSectorNamesComboBox.currentEnum():
            renderOptions.append(self._renderSectorNamesComboBox.currentEnum())

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
        Style = 'Style'
        Options = 'Options'

    AllColumns = [
        ColumnType.Name,
        ColumnType.Location,
        ColumnType.Style,
        ColumnType.Options
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

    def setCurrentSector(
            self,
            sector: typing.Optional[travellermap.SectorInfo]
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
        sectors = travellermap.DataStore.instance().sectors(
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
            self.selectRow(0)

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
                elif columnType == self.ColumnType.Style:
                    style = sector.customMapStyle()
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, style.value if style else 'Unknown')
                elif columnType == self.ColumnType.Options:
                    options = sector.customMapOptions()
                    if options:
                        optionsString = common.humanFriendlyListString(
                            [option.value for option in options])
                    else:
                        optionsString = ''
                    tableItem = QtWidgets.QTableWidgetItem()
                    tableItem.setData(QtCore.Qt.ItemDataRole.DisplayRole, optionsString)

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
    _StateVersion = 'MapComboBox_v1'

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
                for scale in sectorInfo.customMapLevels().keys():
                    self.addItem(f'{scale} Pixels Per Parsec', scale)
        self.currentIndexChanged.emit(self.currentIndex())

    def currentScale(self) -> typing.Optional[int]:
        currentIndex = self.currentIndex()
        if currentIndex < 0:
            return None
        return self.itemData(currentIndex, QtCore.Qt.ItemDataRole.UserRole)

    def setCurrentScale(self, scale: typing.Optional[int]) -> None:
        if scale != None:
            for index in range(self.count()):
                if scale == self.itemData(index, QtCore.Qt.ItemDataRole.UserRole):
                    self.setCurrentIndex(index)
                    return
        else:
            self.setCurrentIndex(-1)

    def saveState(self) -> QtCore.QByteArray:
        value = self.currentScale()
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(_MapComboBox._StateVersion)
        stream.writeDouble(value if value != None else 0)
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != _MapComboBox._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore MapComboBox state (Incorrect version)')
            return False

        value = stream.readDouble()
        self.setCurrentScale(value if value > 0 else None)
        return True

class _MapImageView(gui.ImageView):
    def __init__(
            self,
            sectorInfo: typing.Optional[travellermap.SectorInfo] = None,
            scale: typing.Optional[int] = None,
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
            scale: typing.Optional[int],
            ) -> bool:
        self.clear()

        self._sectorInfo = sectorInfo
        if not self._sectorInfo:
            return True # Nothing more to do

        mapImage = travellermap.DataStore.instance().sectorMapImage(
            sectorName=self._sectorInfo.canonicalName(),
            milieu=app.Config.instance().value(option=app.ConfigOption.Milieu),
            scale=scale)
        if not mapImage:
            return False
        return self.imageFromBytes(data=mapImage.bytes(), type=mapImage.format().value)

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
            key='MapSelectState',
            type=QtCore.QByteArray)
        if storedValue:
            self._mapSelectComboBox.restoreState(storedValue)

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
        self._settings.setValue('MapSelectState', self._mapSelectComboBox.saveState())
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

        self._mapGraphicsView = _MapImageView()

        self._mapSelectComboBox = _MapComboBox()
        self._mapSelectComboBox.currentIndexChanged.connect(self._mapSelectionChanged)

        iconSize = self._mapSelectComboBox.sizeHint().height()
        self._mapToolbar = QtWidgets.QToolBar("Map Toolbar")
        self._mapToolbar.setIconSize(QtCore.QSize(iconSize, iconSize))
        self._mapToolbar.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self._mapToolbar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._mapToolbar.addWidget(self._mapSelectComboBox)
        self._mapToolbar.addActions(self._mapGraphicsView.actions())

        mapLayout = QtWidgets.QVBoxLayout()
        mapLayout.setContentsMargins(0, 0, 0, 0)
        mapLayout.setSpacing(0)
        mapLayout.addWidget(self._mapToolbar)
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
            sectorInfo=self._mapSelectComboBox.sectorInfo(),
            scale=self._mapSelectComboBox.currentScale())
        self._mapGraphicsView.zoomToFit()

    def _syncSectorDataControls(
            self,
            sectorInfo: typing.Optional[travellermap.SectorInfo]
            ) -> None:
        if not sectorInfo:
            self._sectorFileTextEdit.clear()
            self._sectorMetadataTextEdit.clear()
            self._mapSelectComboBox.setSectorInfo(None)
            return

        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)

        try:
            fileData = travellermap.DataStore.instance().sectorFileData(
                sectorName=sectorInfo.canonicalName(),
                milieu=milieu)
            self._sectorFileTextEdit.setPlainText(fileData)
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
            metaData = travellermap.DataStore.instance().sectorMetaData(
                sectorName=sectorInfo.canonicalName(),
                milieu=milieu)
            self._sectorMetadataTextEdit.setPlainText(metaData)
        except Exception as ex:
            self._sectorMetadataTextEdit.clear()

            message = 'Failed to retrieve sector metadata.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            # Continue to try and sync other controls

        # This will trigger an update of the map graphics view
        self._mapSelectComboBox.setSectorInfo(sectorInfo=sectorInfo)

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

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            # v1 = Initial custom sector release
            # v2 = Update for local rendering
            noShowAgainId='CustomSectorsWelcome_v2')
        message.exec()
