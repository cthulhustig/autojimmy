import app
import common
import construction
import gui
import gunsmith
import jobs
import logging
import os
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_WelcomeMessage = """
    <html>
    <p>The Gunsmith window allows you to generate weapons using the rules from the Mongoose 2e
    Field Catalogue. It's aimed to aid in the creation of weapons and is not intended to be a
    substitute for the rules book.</p>
    <p>I have to mention the number of contradictions and ambiguities that the Field Catalogue
    contains. I'm not taking a pop at Mongoose, the Field Catalogue is by far my favourite of their
    books, however, it directly affects how the Gunsmith tool is used. Efforts have been made to add
    options so users can choose how they interpret the rules in cases where it wasn't possible to
    clearly determine the intent of the rules. However, in some cases the holes are so fundamental
    to the construction process that it's not feasible to do this (notably RF/VRF weapons and multi
    barrel/receiver weapons). In these cases, it was necessary to choose what seemed like the most
    logical interpretation and go with that, it's not ideal, but it was the only real option.</p>
    <p>{name} comes with pre-configured example weapons based on the examples from the rule book.
    This is another area the book seems to fall a little short. Almost none of the examples in the
    book appear to follow the rules to the letter. The amount they differ varies, but out of 40
    weapons only 1 seems to actually follow the rules (Squadmate for the win). Some of these
    differences may come down to the aforementioned ambiguities, but the majority of them seem to be
    simple errors (e.g. the wrong cost/weight for a part) or missed rules (e.g. not having quickdraw
    -2 for having a scope). In order to verify the {name} implementation, time has been spent to
    determine where the examples in the book differed from the rules as written. A copy of these
    findings are included in the User Notes for each of the weapons.</p>
    </html>
""".format(name=app.AppName)

class _WeaponPDFExportDialog(gui.DialogEx):
    def __init__(
            self,
            hasMagazineQuantities: bool,
            hasAmmoQuantities: bool,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Weapon PDF Export',
            configSection='WeaponPDFExportDialog',
            parent=parent)

        self._includeEditableFieldsCheckBox = gui.CheckBoxEx('Include editable fields')
        self._includeEditableFieldsCheckBox.setChecked(True)

        self._includeManifestTableCheckBox = gui.CheckBoxEx('Include manifest table')
        self._includeManifestTableCheckBox.setChecked(True)

        self._includeAmmoTableCheckBox = gui.CheckBoxEx(
            'Include magazine && ammo table(s)') # Double & for escaping to prevent interpretation as hotkey char
        self._includeAmmoTableCheckBox.setChecked(True)
        self._includeAmmoTableCheckBox.stateChanged.connect(self._includeAmmoTableChanged)

        self._usePurchasedMagazinesCheckBox = None
        if hasMagazineQuantities:
            self._usePurchasedMagazinesCheckBox = gui.CheckBoxEx('Use purchased magazine types')
            self._usePurchasedMagazinesCheckBox.setEnabled(hasMagazineQuantities)
            self._usePurchasedMagazinesCheckBox.setChecked(hasMagazineQuantities)

        self._usePurchasedAmmoCheckBox = None
        if hasAmmoQuantities:
            self._usePurchasedAmmoCheckBox = gui.CheckBoxEx('Use purchased ammunition types')
            self._usePurchasedAmmoCheckBox.setEnabled(hasAmmoQuantities)
            self._usePurchasedAmmoCheckBox.setChecked(hasAmmoQuantities)

        self._blackAndWhiteCheckBox = gui.CheckBoxEx('Black && White')
        self._blackAndWhiteCheckBox.setChecked(False)

        self._okButton = QtWidgets.QPushButton('OK')
        self._okButton.setDefault(True)
        self._okButton.clicked.connect(self.accept)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._okButton)
        buttonLayout.addWidget(self._cancelButton)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._includeEditableFieldsCheckBox)
        windowLayout.addWidget(self._includeManifestTableCheckBox)
        windowLayout.addWidget(self._includeAmmoTableCheckBox)
        if self._usePurchasedMagazinesCheckBox:
            windowLayout.addWidget(self._usePurchasedMagazinesCheckBox)
        if self._usePurchasedAmmoCheckBox:
            windowLayout.addWidget(self._usePurchasedAmmoCheckBox)
        windowLayout.addWidget(self._blackAndWhiteCheckBox)
        windowLayout.addLayout(buttonLayout)

        self.setLayout(windowLayout)

        # Prevent the dialog being resized
        windowLayout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)
        self.setSizeGripEnabled(False)

    def isIncludeEditableFieldsChecked(self) -> bool:
        return self._includeEditableFieldsCheckBox.isChecked()

    def isIncludeManifestTableChecked(self) -> bool:
        return self._includeManifestTableCheckBox.isChecked()

    def isIncludeAmmoTableChecked(self) -> bool:
        return self._includeAmmoTableCheckBox.isChecked()

    def isUsePurchasedMagazinesChecked(self) -> bool:
        if not self._usePurchasedMagazinesCheckBox or \
                not self._usePurchasedMagazinesCheckBox.isEnabled():
            return False
        return self._usePurchasedMagazinesCheckBox.isChecked()

    def isUsePurchasedAmmoChecked(self) -> bool:
        if not self._usePurchasedAmmoCheckBox or \
                not self._usePurchasedAmmoCheckBox.isEnabled():
            return False
        return self._usePurchasedAmmoCheckBox.isChecked()

    def isBlackAndWhiteChecked(self) -> bool:
        return self._blackAndWhiteCheckBox.isChecked()

    # There is intentionally no saveSettings implementation as saving is only done if the user clicks ok
    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='IncludeEditableFields',
            type=QtCore.QByteArray)
        if storedValue:
            self._includeEditableFieldsCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='IncludeManifestTable',
            type=QtCore.QByteArray)
        if storedValue:
            self._includeManifestTableCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='IncludeAmmoTable',
            type=QtCore.QByteArray)
        if storedValue:
            self._includeAmmoTableCheckBox.restoreState(storedValue)

        if self._usePurchasedMagazinesCheckBox:
            storedValue = gui.safeLoadSetting(
                settings=self._settings,
                key='UsePurchasedMagazines',
                type=QtCore.QByteArray)
            if storedValue:
                self._usePurchasedMagazinesCheckBox.restoreState(storedValue)

        if self._usePurchasedAmmoCheckBox:
            storedValue = gui.safeLoadSetting(
                settings=self._settings,
                key='UsePurchasedAmmo',
                type=QtCore.QByteArray)
            if storedValue:
                self._usePurchasedAmmoCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='BlackAndWhite',
            type=QtCore.QByteArray)
        if storedValue:
            self._blackAndWhiteCheckBox.restoreState(storedValue)

        self._settings.endGroup()

    def accept(self) -> None:
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('IncludeEditableFields', self._includeEditableFieldsCheckBox.saveState())
        self._settings.setValue('IncludeManifestTable', self._includeManifestTableCheckBox.saveState())
        self._settings.setValue('IncludeAmmoTable', self._includeAmmoTableCheckBox.saveState())
        if self._usePurchasedMagazinesCheckBox:
            self._settings.setValue('UsePurchasedMagazines', self._usePurchasedMagazinesCheckBox.saveState())
        if self._usePurchasedAmmoCheckBox:
            self._settings.setValue('UsePurchasedAmmo', self._usePurchasedAmmoCheckBox.saveState())
        self._settings.setValue('BlackAndWhite', self._blackAndWhiteCheckBox.saveState())
        self._settings.endGroup()

        super().accept()

    def _includeAmmoTableChanged(self) -> None:
        checked = self._includeAmmoTableCheckBox.isChecked()
        if self._usePurchasedMagazinesCheckBox:
            self._usePurchasedMagazinesCheckBox.setEnabled(checked)
            self._usePurchasedMagazinesCheckBox.setChecked(checked)
        if self._usePurchasedAmmoCheckBox:
            self._usePurchasedAmmoCheckBox.setEnabled(checked)
            self._usePurchasedAmmoCheckBox.setChecked(checked)

class _ExportProgressDialog(gui.DialogEx):
    def __init__(
            self,
            weapon: gunsmith.Weapon,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._textLabel = QtWidgets.QLabel(f'Exporting {weapon.name()}...')
        self._progressBar = QtWidgets.QProgressBar()

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._textLabel)
        windowLayout.addWidget(self._progressBar)

        self.setLayout(windowLayout)
        self.setWindowFlags(
            ((self.windowFlags() | QtCore.Qt.WindowType.CustomizeWindowHint | QtCore.Qt.WindowType.FramelessWindowHint) & ~QtCore.Qt.WindowType.WindowCloseButtonHint))
        self.setSizeGripEnabled(False)
        self.show()

    def update(
            self,
            current: int,
            total: int
            ) -> None:
        self._progressBar.setMaximum(int(total))
        self._progressBar.setValue(int(current))

class _WeaponManagerWidget(gui.ConstructableManagerWidget):
    _DefaultTechLevel = 12
    _DefaultWeaponType = gunsmith.WeaponType.ConventionalWeapon

    _StateVersion = '_WeaponManagerWidget_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            constructableStore=gunsmith.WeaponStore.instance().constructableStore(),
            parent=parent)
        self._exportJob = None
        self._importExportPath = None

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(_WeaponManagerWidget._StateVersion)

        stream.writeQString(self._importExportPath)

        baseState = super().saveState()
        stream.writeUInt32(baseState.count() if baseState else 0)
        if baseState:
            stream.writeRawData(baseState.data())

        return state
    
    def restoreState(self, state: QtCore.QByteArray) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != _WeaponManagerWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore _WeaponManagementWidget state (Incorrect version)')
            return False

        self._importExportPath = stream.readQString()

        count = stream.readUInt32()
        if count <= 0:
            return True
        baseState = QtCore.QByteArray(stream.readRawData(count))
        if not super().restoreState(baseState):
            return False

        return True
        
    def createConstructable(
            self,
            name: str
            ) -> construction.ConstructableInterface:
        return gunsmith.Weapon(
            name=name,
            techLevel=_WeaponManagerWidget._DefaultTechLevel,
            weaponType=_WeaponManagerWidget._DefaultWeaponType)
    
    def importConstructable(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            directory=self._importExportPath if self._importExportPath else QtCore.QDir.homePath(),
            filter=gui.JSONFileFilter)
        if not path:
            return # User cancelled

        self._importExportPath = os.path.dirname(path)

        try:
            weapon = gunsmith.readWeapon(filePath=path)
        except Exception as ex:
            message = f'Failed to load weapon from {path}'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        weaponName = weapon.name()
        while self._constructableStore.exists(name=weaponName):
            weaponName, result = gui.InputDialogEx.getText(
                parent=self,
                title='Weapon Name',
                label=f'A weapon named \'{weaponName}\' already exists.\nEnter a new name for the imported weapon',
                text=weaponName)
            if not result:
                return # User cancelled
        if weaponName != weapon.name():
            weapon.setName(weaponName)

        try:
            # No need to update buttons or results as import will trigger a selection change
            self._internalAdd(
                constructable=weapon,
                unnamed=False,
                writeToDisk=True,
                makeCurrent=True,
                sortList=True)
        except Exception as ex:
            message = 'Failed to import weapon'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

    def exportConstructable(self) -> None:
        if self._exportJob:
            gui.MessageBoxEx.information(
                parent=self,
                text='Unable to export while another export is in progress')
            return

        weapon = self.current()
        if not  isinstance(weapon, gunsmith.Weapon):
            gui.MessageBoxEx.information(
                parent=self,
                text='No weapon to export')
            return

        defaultPath = os.path.join(
            self._importExportPath if self._importExportPath else QtCore.QDir.homePath(),
            common.sanitiseFileName(fileName=weapon.name()) + '.pdf')

        path, filter = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption='Export File',
            directory=defaultPath,
            filter=f'{gui.PDFFileFilter};;{gui.JSONFileFilter};;{gui.CSVFileFilter}')
        if not path:
            return # User cancelled

        self._importExportPath = os.path.dirname(path)

        try:
            if filter == gui.PDFFileFilter:
                dlg = _WeaponPDFExportDialog(
                    parent=self,
                    hasMagazineQuantities=weapon.hasComponent(componentType=gunsmith.MagazineQuantity),
                    hasAmmoQuantities=weapon.hasComponent(componentType=gunsmith.AmmoQuantity))
                if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                    return # User cancelled

                self._progressDlg = _ExportProgressDialog(weapon=weapon, parent=self)

                self._exportJob = jobs.ExportWeaponJob(
                    parent=self,
                    weapon=weapon,
                    filePath=path,
                    includeEditableFields=dlg.isIncludeEditableFieldsChecked(),
                    includeManifestTable=dlg.isIncludeManifestTableChecked(),
                    includeAmmoTable=dlg.isIncludeAmmoTableChecked(),
                    usePurchasedMagazines=dlg.isUsePurchasedMagazinesChecked(),
                    usePurchasedAmmo=dlg.isUsePurchasedAmmoChecked(),
                    colour=not dlg.isBlackAndWhiteChecked(),
                    progressCallback=self._progressDlg.update,
                    finishedCallback=lambda result: self._exportFinished(filePath=path, result=result))

                self.setDisabled(True)
            elif filter == gui.JSONFileFilter:
                gunsmith.writeWeapon(weapon=weapon, filePath=path)
            elif filter == gui.CSVFileFilter:
                gunsmith.exportToCsv(weapon=weapon, filePath=path)
            else:
                raise ValueError(f'Unexpected filter {filter}')
        except Exception as ex:
            message = f'Failed to export weapon to {path}'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            
    def _exportFinished(
            self,
            filePath: str,
            result: typing.Union[str, Exception]
            ) -> None:
        self._progressDlg.close()
        self.setEnabled(True)

        if isinstance(result, Exception):
            message = f'Failed to export weapon to {filePath}'
            logging.error(message, exc_info=result)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=result)

        self._exportJob = None
        self._progressDlg = None
         
class GunsmithWindow(gui.WindowWidget):
    _ConfigurationBottomSpacing = 300

    def __init__(self) -> None:
        super().__init__(
            title='Gunsmith',
            configSection='Gunsmith')

        self._weaponInfoWidgets: typing.Dict[str, gui.WeaponInfoWidget] = {}
        self._unnamedIndex = 1

        self._setupWeaponListControls()
        self._setupCurrentWeaponControls()
        self._setupResultsControls()

        self._verticalSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._verticalSplitter.addWidget(self._weaponsGroupBox)
        self._verticalSplitter.addWidget(self._currentWeaponGroupBox)

        self._horizontalSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._horizontalSplitter.addWidget(self._verticalSplitter)
        self._horizontalSplitter.addWidget(self._manifestGroupBox)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._horizontalSplitter)

        self.setLayout(windowLayout)

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        QtCore.QTimer.singleShot(0, self._showWelcomeMessage)
        super().firstShowEvent(e)

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='VerticalSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._verticalSplitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='HorizontalSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._horizontalSplitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='WeaponManagementWidgetState',
            type=QtCore.QByteArray)
        if storedValue:
            self._weaponManagementWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='CurrentWeaponDisplayModeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._currentWeaponDisplayModeTabView.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='WeaponConfigurationState',
            type=QtCore.QByteArray)
        if storedValue:
            self._configurationWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ResultsDisplayModeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._resultsDisplayModeTabView.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='WeaponInfoState',
            type=QtCore.QByteArray)
        if storedValue:
            self._weaponInfoWidget.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('VerticalSplitterState', self._verticalSplitter.saveState())
        self._settings.setValue('HorizontalSplitterState', self._horizontalSplitter.saveState())
        self._settings.setValue('WeaponManagementWidgetState', self._weaponManagementWidget.saveState())
        self._settings.setValue('CurrentWeaponDisplayModeState', self._currentWeaponDisplayModeTabView.saveState())
        self._settings.setValue('WeaponConfigurationState', self._configurationWidget.saveState())
        self._settings.setValue('ResultsDisplayModeState', self._resultsDisplayModeTabView.saveState())
        self._settings.setValue('WeaponInfoState', self._weaponInfoWidget.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def closeEvent(self, e: QtGui.QCloseEvent):
        if not self._weaponManagementWidget.promptSaveModified(revertUnsaved=True):
            e.ignore()
            return # User cancelled so don't close the window

        return super().closeEvent(e)

    def _setupWeaponListControls(self) -> None:
        self._weaponManagementWidget = _WeaponManagerWidget()
        self._weaponManagementWidget.currentChanged.connect(self._selectedWeaponChanged)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._weaponManagementWidget)

        self._weaponsGroupBox = QtWidgets.QGroupBox('Weapons')
        self._weaponsGroupBox.setLayout(layout)

    def _setupCurrentWeaponControls(self) -> None:
        weapon = self._weaponManagementWidget.current()
        assert(isinstance(weapon, gunsmith.Weapon))

        self._configurationWidget = gui.WeaponConfigWidget(weapon=weapon)
        self._configurationWidget.weaponModified.connect(self._weaponModified)

        # Wrap the configuration widget in a layout with a spacing at the bottom. This is an effort to avoid
        # the usability issue where adding items at the bottom of the configuration widget would appear of
        # the bottom of the control and require scrolling. This isn't a great solution but it does make it a
        # bit better.
        spacerLayout = QtWidgets.QVBoxLayout()
        spacerLayout.setContentsMargins(0, 0, 0, 0)
        spacerLayout.addWidget(self._configurationWidget)
        spacerLayout.addSpacing(GunsmithWindow._ConfigurationBottomSpacing)
        wrapperWidget = QtWidgets.QWidget()
        wrapperWidget.setLayout(spacerLayout)

        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setWidget(wrapperWidget)

        # Use a plain text edit for the notes as we don't want the advanced stuff (tables etc)
        # supported by QTextEdit. This text could end up in the notes section of a pdf so
        # advanced formatting is out
        self._userNotesTextEdit = QtWidgets.QPlainTextEdit()
        self._userNotesTextEdit.setPlainText(weapon.userNotes() if weapon else '')
        self._userNotesTextEdit.textChanged.connect(self._userNotesChanged)

        self._currentWeaponDisplayModeTabView = gui.TabWidgetEx()
        self._currentWeaponDisplayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self._currentWeaponDisplayModeTabView.addTab(scrollArea, 'Configuration')
        self._currentWeaponDisplayModeTabView.addTab(self._userNotesTextEdit, 'User Notes')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._currentWeaponDisplayModeTabView)

        self._currentWeaponGroupBox = QtWidgets.QGroupBox('Current Weapon')
        self._currentWeaponGroupBox.setLayout(layout)

    def _setupResultsControls(self) -> None:
        self._manifestTable = gui.WeaponManifestTable()

        self._weaponInfoWidget = gui.WeaponInfoTabWidget()

        self._resultsDisplayModeTabView = gui.TabWidgetEx()
        self._resultsDisplayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.East)
        self._resultsDisplayModeTabView.addTab(self._manifestTable, 'Manifest')
        self._resultsDisplayModeTabView.addTab(self._weaponInfoWidget, 'Attributes')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._resultsDisplayModeTabView)

        self._manifestGroupBox = QtWidgets.QGroupBox('Results')
        self._manifestGroupBox.setLayout(layout)

        self._updateResults()

    def _weaponModified(self, value: int) -> None:
        self._weaponManagementWidget.markCurrentModified()
        self._updateResults()

    def _updateResults(self) -> None:
        weapon = self._configurationWidget.weapon()
        self._manifestTable.setManifest(manifest=weapon.manifest())
        self._weaponInfoWidget.setWeapon(weapon=weapon)

    def _selectedWeaponChanged(self) -> None:
        weapon = self._weaponManagementWidget.current()
        isWeapon = isinstance(weapon, gunsmith.Weapon)

        if isWeapon:
            isReadOnly = self._weaponManagementWidget.isReadOnly(
                constructable=weapon)

            # Block signals from configuration widget while configuration widget
            # is updated as the generated change notification would cause the
            # weapon to be marked as dirty. Doing this means we need to manually
            # update the result widgets
            with gui.SignalBlocker(widget=self._configurationWidget):
                self._configurationWidget.setWeapon(weapon=weapon)

            with gui.SignalBlocker(widget=self._userNotesTextEdit):
                # Use setPLainText to reset undo/redo history
                self._userNotesTextEdit.setPlainText(weapon.userNotes())
                self._userNotesTextEdit.setReadOnly(isReadOnly)

        self._currentWeaponDisplayModeTabView.setHidden(not isWeapon)

        self._updateResults()

    def _userNotesChanged(self) -> None:
        weapon = self._weaponManagementWidget.current()
        if not isinstance(weapon, gunsmith.Weapon):
            return
        weapon.setUserNotes(notes=self._userNotesTextEdit.toPlainText())
        self._weaponManagementWidget.markCurrentModified()

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='GunsmithWelcome')
        message.exec()
