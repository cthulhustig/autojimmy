import app
import common
import copy
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

class _PDFExportSettingsDialog(gui.DialogEx):
    def __init__(
            self,
            hasMagazineQuantities: bool,
            hasAmmoQuantities: bool,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='PDF Export Settings',
            configSection='PDFExportSettingsDialog',
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

        self._textLabel = QtWidgets.QLabel(f'Exporting {weapon.weaponName()}...')
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

class GunsmithWindow(gui.WindowWidget):
    _DefaultWeaponType = gunsmith.WeaponType.ConventionalWeapon
    _DefaultTechLevel = 12

    _PDFFilter = 'PDF (*.pdf)'
    _JSONFilter = 'JSON (*.json)'
    _CSVFilter = 'CSV (*.csv)'

    _ConfigurationBottomSpacing = 300

    def __init__(self) -> None:
        super().__init__(
            title='Gunsmith',
            configSection='Gunsmith')

        self._weaponInfoWidgets: typing.Dict[str, gui.WeaponInfoWidget] = {}
        self._exportJob = None
        self._importExportPath = None

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

        self._forceUserWeapon()
        self._updateButtons()

        self.setLayout(windowLayout)

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        QtCore.QTimer.singleShot(0, self._showWelcomeMessage)
        super().firstShowEvent(e)

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ImportExportPath',
            type=str)
        if storedValue:
            self._importExportPath = storedValue

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
            key='WeaponStoreListState',
            type=QtCore.QByteArray)
        if storedValue:
            self._weaponsListBox.restoreState(storedValue)

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

        self._settings.setValue('ImportExportPath', self._importExportPath)
        self._settings.setValue('VerticalSplitterState', self._verticalSplitter.saveState())
        self._settings.setValue('HorizontalSplitterState', self._horizontalSplitter.saveState())
        self._settings.setValue('WeaponStoreListState', self._weaponsListBox.saveState())
        self._settings.setValue('CurrentWeaponDisplayModeState', self._currentWeaponDisplayModeTabView.saveState())
        self._settings.setValue('WeaponConfigurationState', self._configurationWidget.saveState())
        self._settings.setValue('ResultsDisplayModeState', self._resultsDisplayModeTabView.saveState())
        self._settings.setValue('WeaponInfoState', self._weaponInfoWidget.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def closeEvent(self, e: QtGui.QCloseEvent):
        if not self._promptSaveModified():
            e.ignore()
            return # User cancelled so don't close the window

        return super().closeEvent(e)

    def _setupWeaponListControls(self) -> None:
        self._weaponsListBox = gui.WeaponStoreList()
        self._weaponsListBox.currentChanged.connect(self._selectedWeaponChanged)
        self._weaponsListBox.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)

        self._weaponsListToolbar = QtWidgets.QToolBar("Weapons Toolbar")
        self._weaponsListToolbar.setIconSize(QtCore.QSize(32, 32))
        self._weaponsListToolbar.setOrientation(QtCore.Qt.Orientation.Vertical)
        self._weaponsListToolbar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        self._newWeaponAction = QtWidgets.QAction(gui.loadIcon(gui.Icon.NewFile), 'New', self)
        self._newWeaponAction.triggered.connect(self._newWeaponClicked)
        self._weaponsListBox.addAction(self._newWeaponAction)
        self._weaponsListToolbar.addAction(self._newWeaponAction)

        self._saveWeaponAction = QtWidgets.QAction(gui.loadIcon(gui.Icon.SaveFile), 'Save...', self)
        self._saveWeaponAction.triggered.connect(self._saveWeaponClicked)
        self._weaponsListBox.addAction(self._saveWeaponAction)
        self._weaponsListToolbar.addAction(self._saveWeaponAction)

        self._renameWeaponAction = QtWidgets.QAction(gui.loadIcon(gui.Icon.RenameFile), 'Rename...', self)
        self._renameWeaponAction.triggered.connect(self._renameWeaponClicked)
        self._weaponsListBox.addAction(self._renameWeaponAction)
        self._weaponsListToolbar.addAction(self._renameWeaponAction)

        self._revertWeaponAction = QtWidgets.QAction(gui.loadIcon(gui.Icon.Reload), 'Revert...', self)
        self._revertWeaponAction.triggered.connect(self._revertWeaponClicked)
        self._weaponsListBox.addAction(self._revertWeaponAction)
        self._weaponsListToolbar.addAction(self._revertWeaponAction)

        self._copyWeaponAction = QtWidgets.QAction(gui.loadIcon(gui.Icon.CopyFile), 'Copy', self)
        self._copyWeaponAction.triggered.connect(self._copyWeaponClicked)
        self._weaponsListBox.addAction(self._copyWeaponAction)
        self._weaponsListToolbar.addAction(self._copyWeaponAction)

        self._deleteWeaponAction = QtWidgets.QAction(gui.loadIcon(gui.Icon.DeleteFile), 'Delete...', self)
        self._deleteWeaponAction.triggered.connect(self._deleteWeaponClicked)
        self._weaponsListBox.addAction(self._deleteWeaponAction)
        self._weaponsListToolbar.addAction(self._deleteWeaponAction)

        self._importWeaponAction = QtWidgets.QAction(gui.loadIcon(gui.Icon.ImportFile), 'Import...', self)
        self._importWeaponAction.triggered.connect(self._importWeaponClicked)
        self._weaponsListBox.addAction(self._importWeaponAction)
        self._weaponsListToolbar.addAction(self._importWeaponAction)

        self._exportWeaponAction = QtWidgets.QAction(gui.loadIcon(gui.Icon.ExportFile), 'Export...', self)
        self._exportWeaponAction.triggered.connect(self._exportWeaponClicked)
        self._weaponsListBox.addAction(self._exportWeaponAction)
        self._weaponsListToolbar.addAction(self._exportWeaponAction)

        layout = QtWidgets.QHBoxLayout()
        layout.setSpacing(0)
        layout.addWidget(self._weaponsListToolbar)
        layout.addWidget(self._weaponsListBox)

        self._weaponsGroupBox = QtWidgets.QGroupBox('Weapons')
        self._weaponsGroupBox.setLayout(layout)

    def _setupCurrentWeaponControls(self) -> None:
        weapon = self._weaponsListBox.currentWeapon()

        self._configurationWidget = gui.WeaponConfigWidget(weapon=self._weaponsListBox.currentWeapon())
        self._configurationWidget.weaponChanged.connect(self._weaponModified)

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
        self._userNotesTextEdit.textChanged.connect(self._weaponNotesChanged)

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

    # Create a user weapon if there isn't one. This is done to make it more obvious to the user
    # what is going on. Without this, out the box, the configuration would show one of the example
    # weapons which the user might start editing.
    def _forceUserWeapon(self):
        if self._weaponsListBox.isEmpty(section=gui.WeaponStoreList.Section.UserWeapons):
            self._weaponsListBox.newWeapon(
                weaponType=GunsmithWindow._DefaultWeaponType,
                techLevel=GunsmithWindow._DefaultTechLevel,
                makeCurrent=True)

    def _weaponModified(self, value: int) -> None:
        self._weaponsListBox.markCurrentWeaponModified()
        self._updateButtons()
        self._updateResults()

    def _updateButtons(self) -> None:
        isUserWeapon = self._weaponsListBox.currentSection() == gui.WeaponStoreList.Section.UserWeapons
        isModified = self._weaponsListBox.isCurrentWeaponModified()
        isStored = self._weaponsListBox.isCurrentWeaponStored()
        self._saveWeaponAction.setEnabled(isModified)
        self._renameWeaponAction.setEnabled(isUserWeapon)
        self._revertWeaponAction.setEnabled(isModified and isStored)
        self._deleteWeaponAction.setEnabled(isUserWeapon)

    def _updateResults(self) -> None:
        weapon = self._configurationWidget.weapon()
        self._manifestTable.setManifest(manifest=weapon.manifest())
        self._weaponInfoWidget.setWeapon(weapon=weapon)

    def _selectedWeaponChanged(self) -> None:
        weapon = self._weaponsListBox.currentWeapon()
        isUserWeapon = self._weaponsListBox.currentSection() == gui.WeaponStoreList.Section.UserWeapons
        if weapon:
            # Block signals from configuration widget while weapon is set as we don't want to be
            # notified that the weapon has changed as that would cause the weapon to be marked as dirty.
            # Doing this means we need to manually update the weapon name and manifest displays
            with gui.SignalBlocker(widget=self._configurationWidget):
                self._configurationWidget.setWeapon(weapon=weapon)

        with gui.SignalBlocker(widget=self._userNotesTextEdit):
            # Use setPLainText to reset undo/redo history
            self._userNotesTextEdit.setPlainText(weapon.userNotes() if weapon else '')
            self._userNotesTextEdit.setReadOnly(not isUserWeapon)

        self._updateButtons()
        self._updateResults()

    def _weaponNotesChanged(self) -> None:
        weapon = self._weaponsListBox.currentWeapon()
        if not weapon:
            return
        weapon.setUserNotes(notes=self._userNotesTextEdit.toPlainText())
        self._weaponsListBox.markCurrentWeaponModified()
        self._updateButtons()

    def _newWeaponClicked(self) -> None:
        # No need to update buttons or results as weapon creation will trigger a selection change
        self._weaponsListBox.newWeapon(
            weaponType=self._DefaultWeaponType,
            techLevel=self._configurationWidget.techLevel(),
            makeCurrent=True)

    def _saveWeaponClicked(self) -> None:
        weapon = self._weaponsListBox.currentWeapon()
        if not  weapon:
            gui.MessageBoxEx.information(
                parent=self,
                text='No weapon to save')
            return
        self._promptSaveWeapon(weapon=weapon)

    def _renameWeaponClicked(self) -> None:
        weapon = self._weaponsListBox.currentWeapon()
        if not  weapon:
            gui.MessageBoxEx.information(
                parent=self,
                text='No weapon to rename')
            return

        oldWeaponName = None if self._weaponsListBox.isCurrentWeaponUnnamed() else weapon.weaponName()
        newWeaponName = None
        while not newWeaponName:
            newWeaponName, result = gui.InputDialogEx.getText(
                parent=self,
                title='Weapon Name',
                label='Enter a name for the weapon',
                text=oldWeaponName)
            if not result:
                return False

            if not newWeaponName:
                gui.MessageBoxEx.information(
                    parent=self,
                    text='The weapon name can\'t be empty')
            elif gunsmith.WeaponStore.instance().hasWeapon(weaponName=newWeaponName):
                # A weapon with that name already exists (and it's not a simple case change of the weapon name)
                gui.MessageBoxEx.critical(
                    parent=self,
                    text=f'A weapon named \'{newWeaponName}\' already exists')

                # Trigger prompt for a new name but show what he use previously types
                oldWeaponName = newWeaponName
                newWeaponName = None

        try:
            self._weaponsListBox.renameCurrentWeapon(newName=newWeaponName)
        except Exception as ex:
            message = 'Failed to rename weapon(s)'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

        self._updateButtons()

    def _revertWeaponClicked(self) -> None:
        selectionCount = self._weaponsListBox.selectionCount()
        if not selectionCount:
            gui.MessageBoxEx.information(
                parent=self,
                text='Select the weapon(s) to revert')
            return

        if selectionCount == 1:
            weapon = self._weaponsListBox.currentWeapon()
            prompt = f'Are you sure you want to revert \'{weapon.weaponName()}\'?'
        else:
            prompt = f'Are you sure you want to revert {selectionCount} weapons?'

        answer = gui.MessageBoxEx.question(parent=self, text=prompt)
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        try:
            self._weaponsListBox.revertSelectedWeapons()
        except Exception as ex:
            message = 'Failed to revert weapon'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

        # Sync the weapon configuration, buttons and results
        self._selectedWeaponChanged()

    def _copyWeaponClicked(self) -> None:
        if not self._weaponsListBox.hasSelection():
            gui.MessageBoxEx.information(
                parent=self,
                text='Select the weapon(s) to copy')
            return

        try:
            self._weaponsListBox.copySelectedWeapons(makeSelected=True)
        except Exception as ex:
            message = 'Failed to copy weapon(s)'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

        # Sync the weapon configuration, buttons and results
        self._selectedWeaponChanged()

    def _deleteWeaponClicked(self) -> None:
        selectionCount = self._weaponsListBox.selectionCount()
        if not selectionCount:
            gui.MessageBoxEx.information(
                parent=self,
                text='Select the weapon(s) to delete')
            return

        if selectionCount == 1:
            weapon = self._weaponsListBox.currentWeapon()
            prompt = f'Are you sure you want to delete \'{weapon.weaponName()}\'?'
        else:
            prompt = f'Are you sure you want to delete {selectionCount} weapons?'

        answer = gui.MessageBoxEx.question(parent=self, text=prompt)
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        try:
            # No need to update buttons or results as delete will trigger a selection change
            self._weaponsListBox.deleteSelectedWeapons()
        except Exception as ex:
            message = 'Failed to delete weapon(s)'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

        self._forceUserWeapon()

    def _exportWeaponClicked(self) -> None:
        if self._exportJob:
            gui.MessageBoxEx.information(
                parent=self,
                text='Unable to export while another export is in progress')
            return

        weapon = self._weaponsListBox.currentWeapon()
        if not  weapon:
            gui.MessageBoxEx.information(
                parent=self,
                text='No weapon to export')
            return

        currentWeapon = self._weaponsListBox.currentWeapon()
        defaultPath = os.path.join(
            self._importExportPath if self._importExportPath else QtCore.QDir.homePath(),
            common.sanitiseFileName(fileName=currentWeapon.weaponName()) + '.pdf')

        path, filter = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption='Export File',
            directory=defaultPath,
            filter=f'{GunsmithWindow._PDFFilter};;{GunsmithWindow._JSONFilter};;{GunsmithWindow._CSVFilter}')
        if not path:
            return # User cancelled

        self._importExportPath = os.path.dirname(path)

        try:
            if filter == GunsmithWindow._PDFFilter:
                dlg = _PDFExportSettingsDialog(
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

                self._exportWeaponAction.setDisabled(True)
            elif filter == GunsmithWindow._JSONFilter:
                gunsmith.writeWeapon(weapon=weapon, filePath=path)
            elif filter == GunsmithWindow._CSVFilter:
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

        if isinstance(result, Exception):
            message = f'Failed to export weapon to {filePath}'
            logging.error(message, exc_info=result)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=result)

        self._exportJob = None
        self._progressDlg = None
        self._exportWeaponAction.setDisabled(False)

    def _importWeaponClicked(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            directory=self._importExportPath if self._importExportPath else QtCore.QDir.homePath(),
            filter=GunsmithWindow._JSONFilter)
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

        weaponName = weapon.weaponName()
        while self._weaponsListBox.hasWeaponWithName(weaponName):
            weaponName, result = gui.InputDialogEx.getText(
                parent=self,
                title='Weapon Name',
                label=f'A weapon named \'{weaponName}\' already exists.\nEnter a new name for the imported weapon',
                text=weaponName)
            if not result:
                return # User cancelled
        if weaponName != weapon.weaponName():
            weapon.setWeaponName(weaponName)

        try:
            # No need to update buttons or results as import will trigger a selection change
            self._weaponsListBox.importWeapon(
                weapon=weapon,
                makeCurrent=True)
        except Exception as ex:
            message = 'Failed to import weapon'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

    def _promptSaveWeapon(
            self,
            weapon: gunsmith.Weapon
            ) -> bool: # False if user cancelled, otherwise True
        readOnly = self._weaponsListBox.isWeaponReadOnly(weapon=weapon)
        unnamed = self._weaponsListBox.isWeaponUnnamed(weapon=weapon)

        oldWeaponName = weapon.weaponName()
        newWeaponName = None
        if readOnly or unnamed:
            prompt = f'The weapon \'{weapon.weaponName()}\' is {"read only" if readOnly else "unsaved"}, enter a name to save it as.'
            while not newWeaponName:
                newWeaponName, result = gui.InputDialogEx.getText(
                    parent=self,
                    title='Weapon Name',
                    label=prompt,
                    text=oldWeaponName)
                if not result:
                    return False # User cancelled

                if not newWeaponName:
                    gui.MessageBoxEx.information(
                        parent=self,
                        text='The weapon name can\'t be empty')
                elif gunsmith.WeaponStore.instance().hasWeapon(weaponName=newWeaponName):
                    gui.MessageBoxEx.critical(
                        parent=self,
                        text=f'A weapon named \'{newWeaponName}\' already exists')

                    # Trigger prompt for a new name but show what he use previously types
                    oldWeaponName = newWeaponName
                    newWeaponName = None

        try:
            originalWeapon = None
            if readOnly:
                # The weapon is readonly so to save it needs to copied and saved as a new user weapon
                assert(newWeaponName)
                originalWeapon = weapon
                weapon = copy.deepcopy(weapon)
                weapon.setWeaponName(name=newWeaponName)
                self._weaponsListBox.addWeapon(
                    weapon=weapon,
                    makeCurrent=True) # Select the copy
            elif unnamed:
                # The weapon is unnamed so rename it before saving
                assert(newWeaponName)
                self._weaponsListBox.renameWeapon(
                    weapon=weapon,
                    newName=newWeaponName)

            self._weaponsListBox.saveWeapon(weapon=weapon)

            if originalWeapon:
                # The modified weapon has been saved as something else so revert the
                # original version
                self._weaponsListBox.revertWeapon(weapon=originalWeapon)
        except Exception as ex:
            message = 'Failed to save weapon(s)'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

        self._updateButtons()

        return True # User didn't cancel

    def _promptSaveModified(self) -> bool: # False if the user cancelled, otherwise True
        modifiedWeapons: typing.List[gunsmith.Weapon] = []
        for weapon in self._weaponsListBox.weapons():
            if self._weaponsListBox.isWeaponModified(weapon=weapon):
                modifiedWeapons.append(weapon)
        if not modifiedWeapons:
            return True # Nothing to do

        if len(modifiedWeapons) == 1:
            weapon = modifiedWeapons[0]
            answer = gui.MessageBoxEx.question(
                parent=self,
                text=f'The weapon \'{weapon.weaponName()}\' has been modified, do you want to save it?',
                buttons=QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No | QtWidgets.QMessageBox.StandardButton.Cancel)
            if answer == QtWidgets.QMessageBox.StandardButton.Cancel:
                return False # User cancelled

            weaponToSave = []
            if answer == QtWidgets.QMessageBox.StandardButton.Yes:
                weaponToSave.append(weapon)
        else:
            dlg = gui.WeaponSelectDialog(
                parent=self,
                title='Unsaved Weapons',
                text='Do you want to save these modified weapons?',
                weapons=modifiedWeapons,
                showYesNoCancel=True,
                defaultState=QtCore.Qt.CheckState.Checked)
            if dlg.exec() == QtWidgets.QDialog.DialogCode.Rejected:
                return False # The use cancelled
            weaponToSave = dlg.selectedWeapons()

        for weapon in weaponToSave:
            if not self._promptSaveWeapon(weapon=weapon):
                return False # The use cancelled

        # Revert all weapons. Updating the list box and selected weapon when the window is being closed seems
        # counter intuitive but, due to the way the app handles windows, this same window may be redisplayed if
        # the user opens the Gunsmith again. We don't want them to see the modified weapons that they said not
        # to save so best to reset everything
        currentWeapon = self._weaponsListBox.currentWeapon()
        for weapon in self._weaponsListBox.weapons():
            if self._weaponsListBox.isWeaponModified(weapon=weapon):
                self._weaponsListBox.revertWeapon(weapon=weapon)
            if weapon == currentWeapon:
                # The current weapon was reverted so force an update of the configuration and results controls
                self._selectedWeaponChanged()

        # Remove any unsaved weapons for the same reason the modified weapons were removed
        self._weaponsListBox.removeUnsavedWeapons()
        self._forceUserWeapon()

        return True # The user didn't cancel

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='GunsmithWelcome')
        message.exec()
