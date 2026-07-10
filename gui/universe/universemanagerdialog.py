import app
import astronomer
import common
import gui
import jobs
import logging
import multiverse
import os
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class UniverseManagerDialog(gui.DialogEx):
    _IconSize = 24

    _ImportExportLastDirKey = 'UniverseManagerDialogImportExportDir'
    _UniverseFileFilter = 'Universe (*.db)'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Universe Manager',
            configSection='UniverseManagerDialog',
            parent=parent)

        self._setupUniverseList()
        self._setupDialogButtons()

        dialogLayout = QtWidgets.QVBoxLayout()
        dialogLayout.addWidget(self._universeListGroupBox)
        dialogLayout.addLayout(self._buttonLayout)

        self.setLayout(dialogLayout)

        self._syncUniverseList()

    def _setupUniverseList(self) -> None:
        self._universeList = gui.ListWidgetEx()
        self._universeList.currentRowChanged.connect(self._selectedUniverseChanged)
        self._universeList.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)
        itemDelegate = gui.StyledItemDelegateEx()
        itemDelegate.setHighlightCurrentItem(enabled=False)
        self._universeList.setItemDelegate(itemDelegate)

        iconSize = int(UniverseManagerDialog._IconSize * gui.interfaceScale())
        self._toolbar = QtWidgets.QToolBar()
        self._toolbar.setIconSize(QtCore.QSize(iconSize, iconSize))
        self._toolbar.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self._toolbar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        self._newUniverseAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DatabaseNew), 'New...', self)
        self._newUniverseAction.triggered.connect(self._newUniverse)
        self._universeList.addAction(self._newUniverseAction)
        self._toolbar.addAction(self._newUniverseAction)

        self._deleteUniverseAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DatabaseDelete), 'Delete...', self)
        self._deleteUniverseAction.triggered.connect(self._deleteUniverse)
        self._universeList.addAction(self._deleteUniverseAction)
        self._toolbar.addAction(self._deleteUniverseAction)

        self._renameUniverseAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DatabaseRename), 'Rename...', self)
        self._renameUniverseAction.triggered.connect(self._renameUniverse)
        self._universeList.addAction(self._renameUniverseAction)
        self._toolbar.addAction(self._renameUniverseAction)

        self._makeActiveUniverseAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DatabaseStar), 'Make Active', self)
        self._makeActiveUniverseAction.triggered.connect(self._makeActiveUniverse)
        self._universeList.addAction(self._makeActiveUniverseAction)
        self._toolbar.addAction(self._makeActiveUniverseAction)

        self._importUniverseAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DatabaseImport), 'Import...', self)
        self._importUniverseAction.triggered.connect(self._importUniverse)
        self._universeList.addAction(self._importUniverseAction)
        self._toolbar.addAction(self._importUniverseAction)

        self._exportUniverseAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DatabaseExport), 'Export...', self)
        self._exportUniverseAction.triggered.connect(self._exportUniverse)
        self._universeList.addAction(self._exportUniverseAction)
        self._toolbar.addAction(self._exportUniverseAction)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._toolbar)
        layout.addWidget(self._universeList)

        self._universeListGroupBox = QtWidgets.QGroupBox('Universe')
        self._universeListGroupBox.setLayout(layout)

    def _setupDialogButtons(self) -> None:
        self._closeButton = QtWidgets.QPushButton('Close')
        self._closeButton.clicked.connect(self.accept)

        self._buttonLayout = QtWidgets.QHBoxLayout()
        self._buttonLayout.addStretch()
        self._buttonLayout.addWidget(self._closeButton)

    def _syncUniverseList(self) -> None:
        activeUniverseId = app.Config.instance().value(option=app.ConfigOption.Universe)

        oldSelectedUniverse: typing.Optional[multiverse.UniverseInfo] = self._universeList.currentData(
            QtCore.Qt.ItemDataRole.UserRole)

        newCurrentItem = None
        with gui.SignalBlocker(self._universeList):
            self._universeList.clear()

            universes = multiverse.UniverseManager.instance().universeInfos()
            for universe in universes:
                name = universe.name()
                if activeUniverseId and universe.id() == activeUniverseId:
                    # TODO: Do this better, maybe an icon and separate column
                    name += ' (Active)'

                item = QtWidgets.QListWidgetItem(name)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, universe)
                self._universeList.addItem(item)

                if oldSelectedUniverse and oldSelectedUniverse.id() == universe.id():
                    newCurrentItem = item

        if newCurrentItem:
            self._universeList.setCurrentItem(newCurrentItem)

        self._syncActionStates()

    def _selectedUniverseChanged(self) -> None:
        item = self._universeList.currentItem()
        if item:
            item.setSelected(True)
        self._syncActionStates()

    def _newUniverse(self) -> None:
        dlg = gui.CreateUniverseDialog()
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        self._syncUniverseList()
        self._selectUniverse(dlg.universeId())

    def _deleteUniverse(self) -> None:
        selectedUniverse: typing.Optional[multiverse.UniverseInfo] = self._universeList.currentData(
            QtCore.Qt.ItemDataRole.UserRole)
        if not selectedUniverse:
            return

        answer = gui.MessageBoxEx.question(
            parent=self,
            text=f'Are you sure you want to delete universe {selectedUniverse.name()!r}?\nThis cannot be undone!')
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        try:
            multiverse.UniverseManager.instance().deleteUniverse(universeId=selectedUniverse.id())
        except Exception as ex:
            message = f'An error occurred while deleting universe {selectedUniverse.name()!r}.'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(parent=self, text=message, exception=ex)

        self._syncUniverseList()

    def _renameUniverse(self) -> None:
        # TODO: Implement me
        pass

    def _makeActiveUniverse(self) -> None:
        selectedUniverse: typing.Optional[multiverse.UniverseInfo] = self._universeList.currentData(
            QtCore.Qt.ItemDataRole.UserRole)
        if not selectedUniverse:
            return

        app.Config.instance().setValue(
            option=app.ConfigOption.Universe,
            value=selectedUniverse.id())

        self._syncUniverseList()

    def _importUniverse(self) -> None:
        path, filter = gui.FileDialogEx.getOpenFileName(
            parent=self,
            caption='Import Universe',
            filter=f'{UniverseManagerDialog._UniverseFileFilter};;{gui.AllFileFilter}',
            lastDirKey=UniverseManagerDialog._ImportExportLastDirKey)
        if not path:
            return # User cancelled

        try:
            # Use filename without extension as the universe name
            universeName = os.path.splitext(os.path.basename(path))[0]
            universeId = multiverse.UniverseManager.instance().importUniverse(
                name=universeName,
                importPath=path)
        except Exception as ex:
            message = f'An error occurred while importing the universe from {path!r}.'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(parent=self, text=message, exception=ex)

        # Make the imported universe the active universe
        app.Config.instance().setValue(
            option=app.ConfigOption.Universe,
            value=universeId)

        self._syncUniverseList()
        self._selectUniverse(universeId)

    def _exportUniverse(self) -> None:
        selectedUniverse: typing.Optional[multiverse.UniverseInfo] = self._universeList.currentData(
            QtCore.Qt.ItemDataRole.UserRole)
        if not selectedUniverse:
            return

        path, filter = gui.FileDialogEx.getSaveFileName(
            parent=self,
            caption='Export Universe',
            filter=f'{UniverseManagerDialog._UniverseFileFilter};;{gui.AllFileFilter}',
            lastDirKey=UniverseManagerDialog._ImportExportLastDirKey,
            defaultFileName=f'{common.sanitiseFileName(selectedUniverse.name())}.db')
        if not path:
            return # User cancelled

        try:
            multiverse.UniverseManager.instance().exportUniverse(
                universeId=selectedUniverse.id(),
                exportPath=path)
        except Exception as ex:
            message = f'An error occurred while exporting the universe to {path!r}.'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(parent=self, text=message, exception=ex)

    def _selectUniverse(self, universeId: str) -> None:
        for row in range(self._universeList.count()):
            universe: typing.Optional[multiverse.UniverseInfo] = self._universeList.rowData(
                row,
                QtCore.Qt.ItemDataRole.UserRole)
            if universe and universe.id() == universeId:
                self._universeList.setCurrentRow(row)
                return

    def _syncActionStates(self) -> None:
        activeUniverseId = app.Config.instance().value(option=app.ConfigOption.Universe)
        selectedUniverse: typing.Optional[multiverse.UniverseInfo] = self._universeList.currentData(
            QtCore.Qt.ItemDataRole.UserRole)
        hasSelection = selectedUniverse is not None
        selectedUniverseId = selectedUniverse.id() if hasSelection else None
        selectedIsActive = \
            selectedUniverseId is not None and \
            activeUniverseId is not None and \
            selectedUniverseId == activeUniverseId

        self._deleteUniverseAction.setEnabled(hasSelection)
        self._renameUniverseAction.setEnabled(hasSelection)
        self._makeActiveUniverseAction.setEnabled(hasSelection and not selectedIsActive)
        self._exportUniverseAction.setEnabled(hasSelection)