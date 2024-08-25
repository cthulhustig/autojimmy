import app
import common
import enum
import diceroller
import gui
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class DiceModifierWidget(QtWidgets.QWidget):
    modifierChanged = QtCore.pyqtSignal()

    def __init__(
            self,
            modifier: diceroller.DiceModifier,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._modifier = modifier

        self._nameLineEdit = gui.LineEditEx()
        self._nameLineEdit.setText(self._modifier.name())
        self._nameLineEdit.textChanged.connect(self._nameChanged)

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
        self._modifierSpinBox.valueChanged.connect(self._modifierChanged)

        widgetLayout = QtWidgets.QHBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._enabledCheckBox)
        widgetLayout.addWidget(QtWidgets.QLabel('Name: '))
        widgetLayout.addWidget(self._nameLineEdit)
        widgetLayout.addWidget(QtWidgets.QLabel('DM: '))
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
            diceroller.DiceModifier,
            QtWidgets.QListWidgetItem] = {}

    def addModifier(self, modifier: diceroller.DiceModifier) -> None:
        modifierWidget = DiceModifierWidget(modifier=modifier)
        modifierWidget.modifierChanged.connect(lambda: self._modifierChanged(modifier))

        deleteButton = gui.IconButton(icon=gui.loadIcon(id=gui.Icon.CloseTab))
        deleteButton.clicked.connect(lambda: self._deleteClicked(modifier))

        itemSpacing = int(DiceModifierListWidget._ItemSpacing * \
            app.Config.instance().interfaceScale())

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, itemSpacing)
        layout.addWidget(modifierWidget)
        layout.addWidget(deleteButton)

        itemWidget = gui.LayoutWrapperWidget(layout)
        itemWidget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.Fixed)

        item = QtWidgets.QListWidgetItem()
        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
        item.setSizeHint(itemWidget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, itemWidget)
        self._modifierItemMap[modifier] = item
        self._updateDimensions()

    def removeModifier(self, modifier: diceroller.DiceModifier) -> None:
        item = self._modifierItemMap.get(modifier)
        if not item:
            return
        del self._modifierItemMap[modifier]
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
        for modifier in self._modifierItemMap.keys():
            self.modifierDeleted.emit(modifier)
        self._modifierItemMap.clear()
        self._updateDimensions()

    def _modifierChanged(self, modifier: diceroller.DiceModifier) -> None:
        self.modifierChanged.emit(modifier)

    def _deleteClicked(self, modifier: diceroller.DiceModifier) -> None:
        # Don't emit modifierDeleted as removeModifier will do that
        self.removeModifier(modifier=modifier)

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
            roller: diceroller.DiceRoller,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._roller = roller
        self._dieCountSpinBox = gui.SpinBoxEx()
        self._dieCountSpinBox.setRange(0, 100)
        self._dieCountSpinBox.valueChanged.connect(self._dieCountChanged)

        self._dieTypeComboBox = gui.EnumComboBox(
            type=common.DieType,
            value=self._roller.dieType())
        self._dieTypeComboBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._dieTypeComboBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._dieTypeComboBox.currentIndexChanged.connect(self._dieTypeChanged)

        self._constantDMSpinBox = gui.SpinBoxEx()
        self._constantDMSpinBox.enableAlwaysShowSign(True)
        self._constantDMSpinBox.setRange(-100, 100)
        self._constantDMSpinBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._constantDMSpinBox.valueChanged.connect(self._constantDMChanged)

        diceRollLayout = QtWidgets.QHBoxLayout()
        diceRollLayout.setContentsMargins(0, 0, 0, 0)
        diceRollLayout.addWidget(self._dieCountSpinBox)
        diceRollLayout.addWidget(self._dieTypeComboBox)
        diceRollLayout.addWidget(self._constantDMSpinBox)
        diceRollLayout.addStretch()

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

        modifierControlLayout = QtWidgets.QHBoxLayout()
        modifierControlLayout.setContentsMargins(0, 0, 0, 0)
        modifierControlLayout.addWidget(self._addModifierButton)
        modifierControlLayout.addWidget(self._removeModifiersButton)
        modifierControlLayout.addStretch()

        modifiersLayout = QtWidgets.QVBoxLayout()
        modifiersLayout.addLayout(modifierControlLayout)
        modifiersLayout.addWidget(self._modifierList)

        self._targetNumberSpinBox = gui.OptionalSpinBox()
        self._targetNumberSpinBox.setMinimum(0)
        self._targetNumberSpinBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._targetNumberSpinBox.valueChanged.connect(self._targetNumberChanged)

        controlLayout = gui.FormLayoutEx()
        controlLayout.addRow('Dice Roll:', diceRollLayout)
        controlLayout.addRow('Boon:', self._hasBoonCheckBox)
        controlLayout.addRow('Bane:', self._hasBaneCheckBox)
        controlLayout.addRow('Modifiers:', modifiersLayout)
        controlLayout.addRow('Target Number:', self._targetNumberSpinBox)
        controlLayout.addStretch()

        wrapperWidget = QtWidgets.QWidget()
        wrapperWidget.setLayout(controlLayout)
        wrapperWidget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding)

        scrollArea = gui.ScrollAreaEx()
        scrollArea.setWidgetResizable(True)
        scrollArea.setWidget(wrapperWidget)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(scrollArea)

        self.setLayout(widgetLayout)
        self._syncToRoller()

    def roller(self) -> diceroller.DiceRoller:
        return self._roller

    def setRoller(
            self,
            roller: diceroller.DiceRoller
            ) -> None:
        self._roller = roller

    def _syncToRoller(self) -> None:
        with gui.SignalBlocker(self._dieCountSpinBox):
            self._dieCountSpinBox.setValue(self._roller.dieCount())

        with gui.SignalBlocker(self._dieTypeComboBox):
            self._dieTypeComboBox.setCurrentEnum(self._roller.dieType())

        with gui.SignalBlocker(self._constantDMSpinBox):
            self._constantDMSpinBox.setValue(self._roller.constantDM())

        with gui.SignalBlocker(self._hasBoonCheckBox):
            self._hasBoonCheckBox.setChecked(self._roller.hasBoon())

        with gui.SignalBlocker(self._hasBaneCheckBox):
            self._hasBaneCheckBox.setChecked(self._roller.hasBane())

        with gui.SignalBlocker(self._modifierList):
            self._modifierList.clear()
            for modifier in self._roller.yieldDynamicDMs():
                self._modifierList.addModifier(modifier)
            self._modifierList.setHidden(self._modifierList.isEmpty())

        with gui.SignalBlocker(self._targetNumberSpinBox):
            targetNumber = self._roller.targetNumber()
            self._targetNumberSpinBox.setValue(targetNumber)
            if targetNumber == None:
                self._targetNumberSpinBox.setSpinBoxValue(8)

    def _dieCountChanged(self) -> None:
        self._roller.setDieCount(
            self._dieCountSpinBox.value())
        self.configChanged.emit()

    def _dieTypeChanged(self) -> None:
        self._roller.setDieType(
            self._dieTypeComboBox.currentEnum())
        self.configChanged.emit()

    def _constantDMChanged(self) -> None:
        self._roller.setConstantDM(
            self._constantDMSpinBox.value())
        self.configChanged.emit()

    def _hasBoonChanged(self) -> None:
        self._roller.setHasBoon(
            self._hasBoonCheckBox.isChecked())
        self.configChanged.emit()

    def _hasBaneChanged(self) -> None:
        self._roller.setHasBane(
            self._hasBaneCheckBox.isChecked())
        self.configChanged.emit()

    def _addModifierClicked(self) -> None:
        modifier = diceroller.DiceModifier()
        self._roller.addDynamicDM(modifier=modifier)
        self._modifierList.addModifier(modifier)
        self._modifierList.setHidden(False)
        self.configChanged.emit()

    # TODO: This should probably have an 'are you sure' prompt
    def _removeAllModifiersClicked(self) -> None:
        modifiers = list(self._roller.yieldDynamicDMs())
        for modifier in modifiers:
            self._roller.removeDynamicDM(modifier)

        # Block signals to prevent multiple config update
        # notifications as modifiers are deleted
        with gui.SignalBlocker(self._modifierList):
            self._modifierList.clear()

        self._modifierList.setHidden()
        self.configChanged.emit()

    def _modifierChanged(self) -> None:
        self.configChanged.emit()

    def _modifierDeleted(self, modifier: diceroller.DiceModifier) -> None:
        self._roller.removeDynamicDM(modifier)
        self._modifierList.setHidden(self._modifierList.isEmpty())
        self.configChanged.emit()

    def _targetNumberChanged(self) -> None:
        self._roller.setTargetNumber(self._targetNumberSpinBox.value())
        self.configChanged.emit()
