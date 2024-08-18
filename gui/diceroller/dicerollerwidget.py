import app
import common
import enum
import diceroller
import gui
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class DiceModifierWidget(QtWidgets.QWidget):
    deleteClicked = QtCore.pyqtSignal()

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
        widgetLayout.addWidget(self._enabledCheckBox)
        widgetLayout.addWidget(QtWidgets.QLabel('Name: '))
        widgetLayout.addWidget(self._nameLineEdit)
        widgetLayout.addWidget(QtWidgets.QLabel('DM: '))
        widgetLayout.addWidget(self._modifierSpinBox)

        self.setLayout(widgetLayout)

    def _nameChanged(self) -> None:
        self._modifier.setName(self._nameLineEdit.text())

    def _enabledChanged(self) -> None:
        self._modifier.setEnabled(self._enabledCheckBox.isChecked())

    def _modifierChanged(self) -> None:
        self._modifier.setValue(self._modifierSpinBox.value())

    def _deleteClicked(self) -> None:
        self.deleteClicked.emit()

class DiceModifierListWidget(gui.ListWidgetEx):
    modifierDeleted = QtCore.pyqtSignal(diceroller.DiceModifier)

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

        deleteButton = gui.IconButton(icon=gui.loadIcon(id=gui.Icon.CloseTab))
        deleteButton.clicked.connect(lambda: self._deleteClicked(modifier))

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(modifierWidget)
        layout.addWidget(deleteButton)

        itemWidget = gui.LayoutWrapperWidget(layout)

        item = QtWidgets.QListWidgetItem()
        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
        item.setSizeHint(itemWidget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, itemWidget)
        self._modifierItemMap[modifier] = item

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

    def _deleteClicked(self, modifier: diceroller.DiceModifier) -> None:
        self.removeModifier(modifier=modifier)
        self.modifierDeleted.emit(modifier)

class DiceRollerWidget(QtWidgets.QWidget):
    def __init__(
            self,
            roller: diceroller.DiceRoller,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._roller = roller
        self._dieCountSpinBox = gui.SpinBoxEx()
        self._dieCountSpinBox.setRange(0, 100)
        self._dieCountSpinBox.setValue(self._roller.dieCount())
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
        self._constantDMSpinBox.setValue(self._roller.constantDM())
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

        self._boonCountSpinBox = gui.SpinBoxEx()
        self._boonCountSpinBox.setRange(0, 10)
        self._boonCountSpinBox.setValue(self._roller.boonCount())
        self._boonCountSpinBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._boonCountSpinBox.valueChanged.connect(self._boonCountChanged)

        self._baneCountSpinBox = gui.SpinBoxEx()
        self._baneCountSpinBox.setRange(0, 10)
        self._baneCountSpinBox.setValue(self._roller.baneCount())
        self._baneCountSpinBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._baneCountSpinBox.valueChanged.connect(self._baneCountChanged)

        boonBaneLayout = QtWidgets.QHBoxLayout()
        boonBaneLayout.setContentsMargins(0, 0, 0, 0)
        boonBaneLayout.addLayout(gui.createLabelledWidgetLayout(
            text='Boons:',
            widget=self._boonCountSpinBox))
        boonBaneLayout.addLayout(gui.createLabelledWidgetLayout(
            text='Banes:',
            widget=self._baneCountSpinBox))

        self._addModifierButton = QtWidgets.QPushButton('Add Modifier')
        self._addModifierButton.clicked.connect(self._addModifierClicked)

        self._clearModifiersButton = QtWidgets.QPushButton('Clear Modifiers')
        self._clearModifiersButton.clicked.connect(self._clearModifiersClicked)

        self._modifierList = DiceModifierListWidget()
        self._modifierList.setHidden(True) # Will be shown if modifiers added
        self._modifierList.modifierDeleted.connect(self._modifierDeleted)
        for modifier in self._roller.yieldDynamicDMs():
            self._modifierList.addModifier(modifier)

        modifierControlLayout = QtWidgets.QHBoxLayout()
        modifierControlLayout.setContentsMargins(0, 0, 0, 0)
        modifierControlLayout.addWidget(self._addModifierButton)
        modifierControlLayout.addWidget(self._clearModifiersButton)

        modifiersLayout = QtWidgets.QVBoxLayout()
        modifiersLayout.addLayout(modifierControlLayout)
        modifiersLayout.addWidget(self._modifierList)

        self._rollButton = QtWidgets.QPushButton('Roll')
        self._rollButton.clicked.connect(self._rollDice)

        self._resultsLabel = QtWidgets.QLabel()

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addLayout(diceRollLayout)
        widgetLayout.addLayout(boonBaneLayout)
        widgetLayout.addLayout(modifiersLayout)
        widgetLayout.addWidget(self._rollButton)
        widgetLayout.addWidget(self._resultsLabel)

        self.setLayout(widgetLayout)

    def _dieCountChanged(self) -> None:
        self._roller.setDieCount(
            self._dieCountSpinBox.value())

    def _dieTypeChanged(self) -> None:
        self._roller.setDieType(
            self._dieTypeComboBox.currentEnum())

    def _constantDMChanged(self) -> None:
        self._roller.setConstantDM(
            self._constantDMSpinBox.value())

    def _boonCountChanged(self) -> None:
        self._roller.setBoonCount(
            count=self._boonCountSpinBox.value())

    def _baneCountChanged(self) -> None:
        self._roller.setBaneCount(
            count=self._baneCountSpinBox.value())

    def _addModifierClicked(self) -> None:
        modifier = diceroller.DiceModifier()
        self._roller.addDynamicDM(modifier=modifier)
        self._modifierList.addModifier(modifier)
        self._modifierList.setHidden(False)

    def _clearModifiersClicked(self) -> None:
        modifiers = list(self._roller.yieldDynamicDMs())
        for modifier in modifiers:
            self._roller.removeDynamicDM(modifier)
            self._modifierList.removeModifier(modifier)
        self._modifierList.setHidden(True)

    def _modifierDeleted(self, modifier: diceroller.DiceModifier) -> None:
        self._roller.removeDynamicDM(modifier)
        if self._modifierList.isEmpty():
            self._modifierList.setHidden(True)

    def _rollDice(self) -> None:
        result = self._roller.roll()
        total=result.total()
        self._resultsLabel.setText(f'You rolled {total.value()}')