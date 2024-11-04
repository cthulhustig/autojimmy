import app
import common
import diceroller
import gui
import typing
from PyQt5 import QtWidgets, QtCore

class DiceModifierWidget(QtWidgets.QWidget):
    modifierChanged = QtCore.pyqtSignal()

    _EditModificationDelayMs = 1000

    def __init__(
            self,
            modifier: diceroller.DiceModifier,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._modifier = modifier

        self._noWheelFilter = gui.NoWheelEventUnlessFocusedFilter()

        self._nameLineEdit = gui.LineEditEx()
        self._nameLineEdit.setText(self._modifier.name())
        # Set the cursor position to 0 so that, when the dialog is first
        # displayed, if the text is longer than size of the edit box, it
        # shows the start of the string rather than the end of the string
        self._nameLineEdit.setCursorPosition(0)
        self._nameLineEdit.enableDelayedTextEdited(
            msecs=DiceModifierWidget._EditModificationDelayMs)
        self._nameLineEdit.delayedTextEdited.connect(self._nameChanged)

        self._enabledCheckBox = gui.CheckBoxEx()
        self._enabledCheckBox.setChecked(self._modifier.enabled())
        self._enabledCheckBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._enabledCheckBox.stateChanged.connect(self._enabledChanged)

        self._modifierSpinBox = gui.SpinBoxEx()
        self._modifierSpinBox.enableAlwaysShowSign(True)
        self._modifierSpinBox.setRange(-100, 100)
        self._modifierSpinBox.setValue(self._modifier.value())
        self._modifierSpinBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        # NOTE: Change focus policy and install event filter to prevent
        # accidental changes to the value if, while scrolling the list the
        # widget is contained in, the spin box happens to move under the
        # cursor
        self._modifierSpinBox.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self._modifierSpinBox.installEventFilter(self._noWheelFilter)
        self._modifierSpinBox.valueChanged.connect(self._modifierChanged)

        widgetLayout = QtWidgets.QHBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._enabledCheckBox)
        widgetLayout.addWidget(self._nameLineEdit)
        widgetLayout.addWidget(self._modifierSpinBox)

        self.setLayout(widgetLayout)

    def _nameChanged(self) -> None:
        self._modifier.setName(self._nameLineEdit.text())
        self.modifierChanged.emit()

    def _enabledChanged(self) -> None:
        self._modifier.setEnabled(self._enabledCheckBox.isChecked())
        self.modifierChanged.emit()

    def _modifierChanged(self) -> None:
        self._modifier.setValue(self._modifierSpinBox.value())
        self.modifierChanged.emit()

class DiceModifierListWidget(gui.ListWidgetEx):
    modifierChanged = QtCore.pyqtSignal(diceroller.DiceModifier)
    modifierDeleted = QtCore.pyqtSignal(diceroller.DiceModifier)
    modifierMoved = QtCore.pyqtSignal([int, diceroller.DiceModifier])

    _ItemSpacing = 10

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        palette = self.palette()
        brush = palette.window()
        self.setStyleSheet('QListWidget{{background: {colour}; border: none;}}'.format(
            colour=gui.colourToString(brush.color())))
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)

        self._modifierItemMap: typing.Dict[
            str,
            typing.Tuple[
                diceroller.DiceModifier,
                QtWidgets.QListWidgetItem]] = {}

    # Return modifiers in list order
    def modifiers(self) -> None:
        modifiers = []
        for index in range(self.count()):
            item = self.item(index)
            modifiers.append(item.data(QtCore.Qt.ItemDataRole.UserRole))
        return modifiers

    def addModifier(self, modifier: diceroller.DiceModifier) -> None:
        self.insertModifier(
            row=self.count(),
            modifier=modifier)

    def insertModifier(self, row: int, modifier: diceroller.DiceModifier) -> None:
        modifierWidget = DiceModifierWidget(modifier=modifier)
        modifierWidget.modifierChanged.connect(lambda: self._modifierChanged(modifier))

        deleteButton = gui.IconButton(icon=gui.loadIcon(id=gui.Icon.CloseTab))
        deleteButton.clicked.connect(lambda: self._deleteClicked(modifier))

        moveUpButton = QtWidgets.QToolButton()
        moveUpButton.setArrowType(QtCore.Qt.ArrowType.UpArrow)
        moveUpButton.clicked.connect(lambda: self._moveUpClicked(modifier))

        moveDownButton = QtWidgets.QToolButton()
        moveDownButton.setArrowType(QtCore.Qt.ArrowType.DownArrow)
        moveDownButton.clicked.connect(lambda: self._moveDownClicked(modifier))

        itemSpacing = int(DiceModifierListWidget._ItemSpacing * \
                          app.Config.instance().interfaceScale())

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, itemSpacing)
        layout.addWidget(modifierWidget)
        layout.addWidget(moveUpButton)
        layout.addWidget(moveDownButton)
        layout.addWidget(deleteButton)

        itemWidget = gui.LayoutWrapperWidget(layout)
        itemWidget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.Fixed)

        item = QtWidgets.QListWidgetItem()
        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
        item.setSizeHint(itemWidget.sizeHint())
        item.setData(QtCore.Qt.ItemDataRole.UserRole, modifier)
        self.insertItem(row, item)
        self.setItemWidget(item, itemWidget)
        self._modifierItemMap[modifier.id()] = (modifier, item)
        self._updateDimensions()

    def removeModifier(self, modifier: diceroller.DiceModifier) -> None:
        _, item = self._modifierItemMap.get(modifier.id(), (None, None))
        if not item:
            return
        del self._modifierItemMap[modifier.id()]
        row = self.row(item)
        widget = self.itemWidget(item)
        if row >= 0:
            self.takeItem(row)
        if widget:
            widget.hide()
            widget.deleteLater()
        self._updateDimensions()
        self.modifierDeleted.emit(modifier)

    def clear(self) -> None:
        super().clear()
        for modifier, _ in self._modifierItemMap.values():
            self.modifierDeleted.emit(modifier)
        self._modifierItemMap.clear()
        self._updateDimensions()

    def _modifierChanged(self, modifier: diceroller.DiceModifier) -> None:
        self.modifierChanged.emit(modifier)

    def _deleteClicked(self, modifier: diceroller.DiceModifier) -> None:
        # Don't emit modifierDeleted as removeModifier will do that
        self.removeModifier(modifier=modifier)

    def _moveUpClicked(self, modifier: diceroller.DiceModifier) -> None:
        modifier, item = self._modifierItemMap[modifier.id()]
        index = self.indexFromItem(item)
        if index.row() <= 0:
            return # Nothing to do

        self.takeItem(index.row())

        self.insertModifier(
            row=index.row() - 1,
            modifier=modifier)

        self.modifierMoved[int, diceroller.DiceModifier].emit(
            index.row() - 1,
            modifier)

    def _moveDownClicked(self, modifier: diceroller.DiceModifier) -> None:
        _, item = self._modifierItemMap[modifier.id()]
        index = self.indexFromItem(item)
        if index.row() >= (self.count() - 1):
            return # Nothing to do

        self.takeItem(index.row())

        self.insertModifier(
            row=index.row() + 1,
            modifier=modifier)

        self.modifierMoved[int, diceroller.DiceModifier].emit(
            index.row() + 1,
            modifier)

    def _updateDimensions(self) -> None:
        self.updateGeometry()
        height = width = 0
        if self.count() > 0:
            height = self.sizeHintForRow(0) * self.count() + \
                (self.frameWidth() * 2)
            width = self.sizeHintForColumn(0) + \
                (self.frameWidth() * 2)
        if not self.horizontalScrollBar().isHidden():
            height += self.horizontalScrollBar().height()
        if not self.verticalScrollBar().isHidden():
            width += self.verticalScrollBar().width()
        self.setFixedHeight(height)
        self.setMinimumWidth(width)

class DiceRollerConfigWidget(QtWidgets.QWidget):
    configChanged = QtCore.pyqtSignal()

    def __init__(
            self,
            roller: typing.Optional[diceroller.DiceRoller] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._roller = roller

        self._dieCountSpinBox = gui.SpinBoxEx()
        self._dieCountSpinBox.setRange(0, 100)
        self._dieCountSpinBox.valueChanged.connect(self._dieCountChanged)

        self._dieTypeComboBox = gui.EnumComboBox(
            type=common.DieType)
        self._dieTypeComboBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._dieTypeComboBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._dieTypeComboBox.currentIndexChanged.connect(self._dieTypeChanged)

        self._constantSpinBox = gui.SpinBoxEx()
        self._constantSpinBox.enableAlwaysShowSign(True)
        self._constantSpinBox.setRange(-100, 100)
        self._constantSpinBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._constantSpinBox.valueChanged.connect(self._constantChanged)

        diceRollLayout = QtWidgets.QHBoxLayout()
        diceRollLayout.setContentsMargins(0, 0, 0, 0)
        diceRollLayout.addWidget(self._dieCountSpinBox)
        diceRollLayout.addWidget(self._dieTypeComboBox)
        diceRollLayout.addWidget(self._constantSpinBox)
        diceRollLayout.addStretch()

        self._targetTypeComboBox = gui.EnumComboBox(
            type=common.ComparisonType,
            value=None,
            isOptional=True)
        self._targetTypeComboBox.currentIndexChanged.connect(self._targetTypeChanged)

        self._targetNumberSpinBox = gui.SpinBoxEx()
        self._targetNumberSpinBox.setMinimum(0)
        self._targetNumberSpinBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._targetNumberSpinBox.setEnabled(self._targetTypeComboBox.currentEnum() != None)
        self._targetNumberSpinBox.valueChanged.connect(self._targetNumberChanged)

        targetLayout = QtWidgets.QHBoxLayout()
        targetLayout.setContentsMargins(0, 0, 0, 0)
        targetLayout.addWidget(self._targetTypeComboBox)
        targetLayout.addWidget(self._targetNumberSpinBox)
        targetWidget = gui.LayoutWrapperWidget(layout=targetLayout)

        self._hasBoonCheckBox = gui.CheckBoxEx()
        self._hasBoonCheckBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._hasBoonCheckBox.stateChanged.connect(self._hasBoonChanged)

        self._hasBaneCheckBox = gui.CheckBoxEx()
        self._hasBaneCheckBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._hasBaneCheckBox.stateChanged.connect(self._hasBaneChanged)

        self._fluxTypeComboBox = gui.EnumComboBox(
            type=diceroller.FluxType,
            isOptional=True)
        self._fluxTypeComboBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._fluxTypeComboBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._fluxTypeComboBox.currentIndexChanged.connect(self._fluxTypeChanged)

        self._addModifierButton = QtWidgets.QPushButton('Add')
        self._addModifierButton.clicked.connect(self._addModifierClicked)

        self._removeModifiersButton = QtWidgets.QPushButton('Remove All')
        self._removeModifiersButton.clicked.connect(self._removeAllModifiersClicked)

        self._modifierList = DiceModifierListWidget()
        self._modifierList.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self._modifierList.modifierChanged.connect(self._modifierChanged)
        self._modifierList.modifierDeleted.connect(self._modifierDeleted)
        self._modifierList.modifierMoved.connect(self._modifierMoved)

        modifierControlLayout = QtWidgets.QHBoxLayout()
        modifierControlLayout.setContentsMargins(0, 0, 0, 0)
        modifierControlLayout.addWidget(self._addModifierButton)
        modifierControlLayout.addWidget(self._removeModifiersButton)
        modifierControlLayout.addStretch()

        modifiersLayout = QtWidgets.QVBoxLayout()
        modifiersLayout.addLayout(modifierControlLayout)
        modifiersLayout.addWidget(self._modifierList)

        controlLayout = gui.FormLayoutEx()
        controlLayout.addRow('Dice Roll:', diceRollLayout)
        controlLayout.addRow('Target:', targetWidget)
        controlLayout.addRow('Boon:', self._hasBoonCheckBox)
        controlLayout.addRow('Bane:', self._hasBaneCheckBox)
        controlLayout.addRow('Flux:', self._fluxTypeComboBox)
        controlLayout.addRow('Modifiers:', modifiersLayout)
        controlLayout.addStretch()

        wrapperWidget = QtWidgets.QWidget()
        wrapperWidget.setLayout(controlLayout)
        wrapperWidget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding)

        self._scrollArea = gui.ScrollAreaEx()
        self._scrollArea.setWidgetResizable(True)
        self._scrollArea.setWidget(wrapperWidget)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._scrollArea)

        self.setLayout(widgetLayout)
        self._syncToRoller()

    def roller(self) -> diceroller.DiceRoller:
        return self._roller

    def setRoller(
            self,
            roller: typing.Optional[diceroller.DiceRoller]
            ) -> None:
        self._roller = roller
        self._syncToRoller()

    def _syncToRoller(self) -> None:
        if not self._roller:
            self._scrollArea.setHidden(True)
            return

        self._scrollArea.setHidden(False)

        with gui.SignalBlocker(self._dieCountSpinBox):
            self._dieCountSpinBox.setValue(self._roller.dieCount())

        with gui.SignalBlocker(self._dieTypeComboBox):
            self._dieTypeComboBox.setCurrentEnum(self._roller.dieType())

        with gui.SignalBlocker(self._constantSpinBox):
            self._constantSpinBox.setValue(self._roller.constant())

        with gui.SignalBlocker(self._hasBoonCheckBox):
            self._hasBoonCheckBox.setChecked(self._roller.hasBoon())

        with gui.SignalBlocker(self._hasBaneCheckBox):
            self._hasBaneCheckBox.setChecked(self._roller.hasBane())

        with gui.SignalBlocker(self._fluxTypeComboBox):
            self._fluxTypeComboBox.setCurrentEnum(self._roller.fluxType())

        with gui.SignalBlocker(self._modifierList):
            self._modifierList.clear()
            for modifier in self._roller.modifiers():
                self._modifierList.addModifier(modifier)
            self._modifierList.setHidden(self._modifierList.isEmpty())

        with gui.SignalBlocker(self._targetTypeComboBox):
            self._targetTypeComboBox.setCurrentEnum(
                self._roller.targetType())

        with gui.SignalBlocker(self._targetNumberSpinBox):
            targetNumber = self._roller.targetNumber()
            self._targetNumberSpinBox.setValue(
                targetNumber if targetNumber != None else 8)
            self._targetNumberSpinBox.setEnabled(
                self._roller.targetType() != None)

    def _fluxTypeChanged(self) -> None:
        self._roller.setFluxType(
            self._fluxTypeComboBox.currentEnum())
        self.configChanged.emit()

    def _dieCountChanged(self) -> None:
        self._roller.setDieCount(
            self._dieCountSpinBox.value())
        self.configChanged.emit()

    def _dieTypeChanged(self) -> None:
        self._roller.setDieType(
            self._dieTypeComboBox.currentEnum())
        self.configChanged.emit()

    def _constantChanged(self) -> None:
        self._roller.setConstant(
            self._constantSpinBox.value())
        self.configChanged.emit()

    def _hasBoonChanged(self) -> None:
        self._roller.setHasBoon(
            self._hasBoonCheckBox.isChecked())

        self._roller.setHasBane(False)
        with gui.SignalBlocker(self._hasBaneCheckBox):
            self._hasBaneCheckBox.setChecked(False)

        self.configChanged.emit()

    def _hasBaneChanged(self) -> None:
        self._roller.setHasBane(
            self._hasBaneCheckBox.isChecked())

        self._roller.setHasBoon(False)
        with gui.SignalBlocker(self._hasBoonCheckBox):
            self._hasBoonCheckBox.setChecked(False)

        self.configChanged.emit()

    def _addModifierClicked(self) -> None:
        modifier = diceroller.DiceModifier(
            name='Modifier',
            value=0,
            enabled=True)
        self._roller.addModifier(modifier=modifier)
        self._modifierList.addModifier(modifier)
        self._modifierList.setHidden(False)
        self.configChanged.emit()

    # TODO: This should probably have an 'are you sure' prompt
    def _removeAllModifiersClicked(self) -> None:
        self._roller.clearModifiers()

        # Block signals to prevent multiple config update
        # notifications as modifiers are deleted
        with gui.SignalBlocker(self._modifierList):
            self._modifierList.clear()

        self._modifierList.setHidden(True)
        self.configChanged.emit()

    def _modifierChanged(self) -> None:
        self.configChanged.emit()

    def _modifierDeleted(self, modifier: diceroller.DiceModifier) -> None:
        self._roller.removeModifier(id=modifier.id())
        self._modifierList.setHidden(self._modifierList.isEmpty())
        self.configChanged.emit()

    def _modifierMoved(self,
                       index: int,
                       modifier: diceroller.DiceModifier
                       ) -> None:
        self._roller.removeModifier(id=modifier.id())
        self._roller.insertModifier(index=index, modifier=modifier)
        self.configChanged.emit()

    def _targetTypeChanged(self) -> None:
        targetType = self._targetTypeComboBox.currentEnum()
        self._roller.setTargetType(targetType)
        self._roller.setTargetNumber(
            self._targetNumberSpinBox.value() if targetType != None else None)
        self._targetNumberSpinBox.setEnabled(targetType != None)
        self.configChanged.emit()

    def _targetNumberChanged(self) -> None:
        self._roller.setTargetNumber(self._targetNumberSpinBox.value())
        self.configChanged.emit()
