import app
import astronomer
import azathoth
import common
import gui
import logging
import multiverse
import os
import survey
import traveller
import typing
from PyQt5 import QtCore, QtWidgets, QtGui

class ImportSectorDialog(gui.DialogEx):
    _SectorFileFilter = 'Sector (*.sec *.tab *.tsv *.t5 *.t5col *.t5tab)'
    _MetadataFileFilter = 'Metadata (*.xml *.json)'
    _AllFileFilter = 'All Files (*.*)'

    def __init__(
            self,
            milieu: astronomer.Milieu,
            sectorPos: astronomer.SectorPosition,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Import Sector',
            configSection='ImportSectorDialog',
            parent=parent)

        self._milieu = milieu
        self._sectorPos = sectorPos

        self._recentDirectoryPath = None
        self._sector = None

        self._setupFileSelectControls()
        self._setupOptionControls()
        self._setupDialogButtons()

        dialogLayout = QtWidgets.QVBoxLayout()
        dialogLayout.addWidget(self._filesGroupBox)
        dialogLayout.addWidget(self._optionsGroupBox)
        dialogLayout.addLayout(self._buttonLayout)

        self.setLayout(dialogLayout)
        self.setFixedHeight(self.sizeHint().height())

    def sector(self) -> typing.Optional[azathoth.EditableSector]:
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
        if storedValue is not None:
            self._recentDirectoryPath = storedValue

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SectorFilePath',
            type=str)
        if storedValue is not None:
            self._sectorFileLineEdit.setText(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='MetadataFilePath',
            type=str)
        if storedValue is not None:
            self._metadataFileLineEdit.setText(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='RegenerateTradeCodes',
            type=bool)
        if storedValue is not None:
            self._regenerateTradeCodesCheckBox.setChecked(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='TradeCodeRules',
            type=QtCore.QByteArray)
        if storedValue is not None:
            self._tradeCodeRulesComboBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ShowImportReport',
            type=bool)
        if storedValue is not None:
            self._showConversionReportCheckBox.setChecked(storedValue)

        self._settings.endGroup()

    def accept(self) -> None:
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('RecentDirectory', self._recentDirectoryPath)
        self._settings.setValue('SectorFilePath', self._sectorFileLineEdit.text())
        self._settings.setValue('MetadataFilePath', self._metadataFileLineEdit.text())
        self._settings.setValue('RegenerateTradeCodes', self._regenerateTradeCodesCheckBox.isChecked())
        self._settings.setValue('TradeCodeRules', self._tradeCodeRulesComboBox.saveState())
        self._settings.setValue('ShowImportReport', self._showConversionReportCheckBox.isChecked())
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

    def _setupOptionControls(self) -> None:
        self._tradeCodeRulesComboBox = gui.EnumComboBox(
            type=traveller.TradeCodeRules)

        self._regenerateTradeCodesCheckBox = gui.TogglableWidget(
            widget=self._tradeCodeRulesComboBox)
        self._regenerateTradeCodesCheckBox.setChecked(False)

        self._showConversionReportCheckBox = gui.CheckBoxEx()
        self._showConversionReportCheckBox.setChecked(True)

        groupLayout = gui.FormLayoutEx()
        groupLayout.addRow('Regenerate Trade Codes: ', self._regenerateTradeCodesCheckBox)
        groupLayout.addRow('Show Conversion Report: ', self._showConversionReportCheckBox)

        self._optionsGroupBox = QtWidgets.QGroupBox('Options')
        self._optionsGroupBox.setLayout(groupLayout)

    def _setupDialogButtons(self) -> None:
        self._importButton = QtWidgets.QPushButton('Import')
        self._importButton.setDefault(True)
        self._importButton.clicked.connect(self._importClicked)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        self._buttonLayout = QtWidgets.QHBoxLayout()
        self._buttonLayout.addStretch()
        self._buttonLayout.addWidget(self._importButton)
        self._buttonLayout.addWidget(self._cancelButton)

    def _sectorFileBrowseClicked(self) -> None:
        path = self._showFileSelect(
            caption='Sector File',
            filter=f'{ImportSectorDialog._SectorFileFilter};;{ImportSectorDialog._AllFileFilter}')
        if not path:
            return # User cancelled
        self._sectorFileLineEdit.setText(path)

    def _metadataFileBrowseClicked(self) -> None:
        path = self._showFileSelect(
            caption='Metadata File',
            filter=f'{ImportSectorDialog._MetadataFileFilter};;{ImportSectorDialog._AllFileFilter}')
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

    def _importClicked(self) -> None:
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

        # TODO: Need to display any messages that are reported to the user
        reporter = None

        if self._showConversionReportCheckBox.isChecked():
            reporter = common.LoggingReporter(logLevel=logging.WARNING)

        if reporter:
            _, metadataFileName = os.path.split(metadataFilePath)
            reporter.pushPrefix(f'{metadataFileName} - ')
        try:
            with open(metadataFilePath, 'r', encoding='utf-8-sig') as file:
                sectorMetadata = file.read()
            rawMetadata = survey.parseMetadata(
                content=sectorMetadata,
                reporter=reporter)

            rawMetadata = self._overrideSectorPosition(
                sectorPos=self._sectorPos,
                rawMetadata=rawMetadata)
        except Exception as ex:
            message = 'An error occurred when loading sector metadata.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return
        finally:
            if reporter:
                reporter.popPrefix()

        # Try to parse the sector format now to prevent it failing after the user has waited
        # to create the posters. This is only really needed for cases where Traveller Map is
        # happy with the format but my parser isn't
        if reporter:
            _, sectorFileName = os.path.split(sectorFilePath)
            reporter.pushPrefix(f'{sectorFileName} - ')
        try:
            with open(sectorFilePath, 'r', encoding='utf-8-sig') as file:
                sectorData = file.read()
            rawWorlds = survey.parseSector(
                content=sectorData,
                reporter=reporter)

            if self._regenerateTradeCodesCheckBox.isChecked():
                tradeCodeRules = self._tradeCodeRulesComboBox.currentEnum()
                for index, rawWorld in enumerate(rawWorlds):
                    rawWorlds[index] = self._regenerateTradeCodes(
                        ruleSystem=tradeCodeRules,
                        rawWorld=rawWorld)
        except Exception as ex:
            message = 'An error occurred when loading sector world data.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return
        finally:
            if reporter:
                reporter.popPrefix()

        if reporter:
            reporter.pushPrefix('Stock Allegiances: ')
        try:
            rawStockAllegiances = multiverse.loadSnapshotStockAllegiances(reporter=reporter)
        except:
            message = 'An error occurred when loading stock allegiances.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return
        finally:
            if reporter:
                reporter.popPrefix()

        if reporter:
            reporter.pushPrefix('Stock Sophonts: ')
        try:
            rawStockSophonts = multiverse.loadSnapshotStockSophonts(reporter=reporter)
        except:
            message = 'An error occurred when loading stock sophonts.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return
        finally:
            if reporter:
                reporter.popPrefix()

        if reporter:
            reporter.pushPrefix('Stock Style Sheet: ')
        try:
            rawStyleSheet = multiverse.loadSnapshotStyleSheet(reporter=reporter)
        except:
            message = 'An error occurred when loading stock style sheet.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return
        finally:
            if reporter:
                reporter.popPrefix()

        try:
            sector: azathoth.EditableSector = astronomer.convertRawSectorToAstronomerSector(
                milieu=self._milieu,
                rawMetadata=rawMetadata,
                rawSystems=rawWorlds,
                rawStockAllegiances=rawStockAllegiances,
                rawStockSophonts=rawStockSophonts,
                rawStockStyleSheet=rawStyleSheet,
                entityFactory=azathoth.UniverseEditor.instance().entityFactory())
        except Exception as ex:
            message = 'An error occurred when converting the sector.'
            logging.critical(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        if reporter:
            text = '\n'.join(reporter.messages())
            if not text:
                text = 'No issues when converting sector'

            reportWindow = gui.TextWindow(
                title=f'Sector Conversion Report - {rawMetadata.canonicalName()}',
                text=text,
                readOnly=True,
                configSection='SectorConversionReport')
            gui.WindowManager.instance().manageWindow(window=reportWindow)

            # NOTE: This is a hack to bring the report window to the front
            # after the dialog has closed. This is needed as, when the dialog
            # closes, the window that displayed the dialog will become active
            # and be brought in front of the report window
            # TODO: Need to check this works on Linux & MacOS
            QtCore.QTimer.singleShot(0, reportWindow.bringToFront)

        self._sector = sector
        self.accept()

    def _overrideSectorPosition(
            self,
            sectorPos: astronomer.SectorPosition,
            rawMetadata: survey.RawMetadata
            ) -> survey.RawMetadata:
        return survey.RawMetadata(
            x=sectorPos.sectorX(), # Override position
            y=sectorPos.sectorY(),
            canonicalName=rawMetadata.canonicalName(),
            alternateNames=rawMetadata.alternateNames(),
            nameLanguages=rawMetadata.nameLanguages(),
            abbreviation=rawMetadata.abbreviation(),
            sectorLabel=rawMetadata.sectorLabel(),
            subsectorNames=rawMetadata.subsectorNames(),
            selected=rawMetadata.selected(),
            tags=rawMetadata.tags(),
            allegiances=rawMetadata.allegiances(),
            routes=rawMetadata.routes(),
            borders=rawMetadata.borders(),
            labels=rawMetadata.labels(),
            regions=rawMetadata.regions(),
            sources=rawMetadata.sources(),
            styleSheet=rawMetadata.styleSheet())

    def _regenerateTradeCodes(
            self,
            ruleSystem: traveller.TradeCodeRules,
            rawWorld: survey.RawWorld
            ) -> survey.RawWorld:
        rawUWP = rawWorld.uwp()
        if not rawUWP:
            return rawWorld

        rawRemarks = rawWorld.remarks()
        rawTradeCodes = rawRemarks.tradeCodes() if rawRemarks else None

        rawTradeCodes = traveller.tradeCodeStrings(traveller.calculateTradeCodes(
            uwp=survey.formatSystemUWPString(
                starport=rawUWP.starport(),
                worldSize=rawUWP.worldSize(),
                atmosphere=rawUWP.atmosphere(),
                hydrographics=rawUWP.hydrographics(),
                population=rawUWP.population(),
                government=rawUWP.government(),
                lawLevel=rawUWP.lawLevel(),
                techLevel=rawUWP.techLevel()),
            ruleSystem=ruleSystem,
            mergeTradeCodes=traveller.tradeCodes(rawTradeCodes) if rawTradeCodes else None))

        if rawRemarks:
            rawRemarks = survey.RawRemarks(
                tradeCodes=rawTradeCodes, # Replace the trade codes
                majorRaceHomeWorlds=rawRemarks.majorRaceHomeWorlds(),
                minorRaceHomeWorlds=rawRemarks.minorRaceHomeWorlds(),
                sophontPopulations=rawRemarks.sophontPopulations(),
                dieBackSophonts=rawRemarks.dieBackSophonts(),
                owningSystems=rawRemarks.owningSystems(),
                colonySystems=rawRemarks.colonySystems(),
                rulingAllegiances=rawRemarks.rulingAllegiances(),
                researchStations=rawRemarks.researchStations(),
                customRemarks=rawRemarks.customRemarks())
        else:
            rawRemarks = survey.RawRemarks(tradeCodes=rawTradeCodes)

        return survey.RawWorld(
            x=rawWorld.x(),
            y=rawWorld.y(),
            name=rawWorld.name(),
            allegianceCode=rawWorld.allegianceCode(),
            zone=rawWorld.zone(),
            uwp=rawWorld.uwp(),
            economics=rawWorld.economics(),
            culture=rawWorld.culture(),
            nobilities=rawWorld.nobilities(),
            bases=rawWorld.bases(),
            remarks=rawRemarks, # Replace the remarks
            importance=rawWorld.importance(),
            pbg=rawWorld.pbg(),
            systemWorlds=rawWorld.systemWorlds(),
            stars=rawWorld.stars())
