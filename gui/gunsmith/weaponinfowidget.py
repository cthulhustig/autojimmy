import app
import construction
import common
import enum
import gui
import gunsmith
import logging
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class _CalculationLineEdit(gui.ContentSizedLineEdit):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self.setReadOnly(True)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._showContextMenu)

    def _calculations(self) -> typing.Iterable[common.ScalarCalculation]:
        raise RuntimeError('The _calculations method must be implemented by classes derived from _CustomLineEdit')

    def _showContextMenu(
            self,
            position: QtCore.QPoint
            ) -> None:
        menu = self.createStandardContextMenu()

        calculations = self._calculations()
        if calculations:
            action = QtWidgets.QAction('Show calculation...')
            action.triggered.connect(lambda: self._showCalculations(calculations))

            existingActions = menu.actions()
            firstAction = existingActions[0] if existingActions else None
            menu.insertAction(firstAction, action)

        menu.exec(self.mapToGlobal(position))

    def _showCalculations(
            self,
            calculations: typing.Iterable[common.ScalarCalculation]):
        try:
            calculationWindow = gui.WindowManager.instance().showCalculationWindow()
            calculationWindow.showCalculations(
                calculations=calculations,
                decimalPlaces=gunsmith.ConstructionDecimalPlaces)
        except Exception as ex:
            message = 'Failed to show calculations'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

class _WeightLineEdit(_CalculationLineEdit):
    def __init__(
            self,
            weapon: gunsmith.Weapon,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)
        self._weapon = None
        self.setWeapon(weapon=weapon)

    def setWeapon(
            self,
            weapon: gunsmith.Weapon,
            ) -> None:
        self._weapon = weapon

        weight = self._weapon.combatWeight()
        self.setText(common.formatNumber(number=weight.value()))

    def _calculations(self) -> typing.Iterable[common.ScalarCalculation]:
        return [self._weapon.combatWeight()]

class _AttributeLineEdit(_CalculationLineEdit):
    def __init__(
            self,
            attribute: construction.AttributeInterface,
            isTrait: bool,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)
        self._attribute = None
        self.setAttribute(attribute=attribute, isTrait=isTrait)

    def setAttribute(
            self,
            attribute: construction.AttributeInterface,
            isTrait: bool
            ) -> None:
        self._attribute = attribute

        value = attribute.value()
        if not value:
            content = ''
        elif isinstance(value, common.ScalarCalculation):
            content = common.formatNumber(number=value.value())
        elif isinstance(value, common.DiceRoll):
            content = str(value)
        elif isinstance(value, enum.Enum):
            content = str(value.value)
        else:
            content = '?'

        if isTrait:
            content = f'{attribute.name()} ({content})' if content else attribute.name()

        self.setText(content)

    def _calculations(self) -> typing.Iterable[common.ScalarCalculation]:
        return self._attribute.calculations()

class WeaponInfoWidget(QtWidgets.QWidget):
    _StateVersion = 'WeaponInfoWidget_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._weapon = None
        self._sequence = None

        self._basicFormLayout = gui.FormLayoutEx()
        self._basicFormLayout.setContentsMargins(0, 0, 0, 0)

        self._reliabilityFormLayout = gui.FormLayoutEx()
        self._reliabilityFormLayout.setContentsMargins(0, 0, 0, 0)

        self._traitFormLayout = gui.FormLayoutEx()
        self._traitFormLayout.setContentsMargins(0, 0, 0, 0)

        self._attributeLayout = QtWidgets.QHBoxLayout()
        self._attributeLayout.setContentsMargins(0, 0, 0, 0)
        self._attributeLayout.addLayout(self._basicFormLayout)
        self._attributeLayout.addLayout(self._reliabilityFormLayout)
        self._attributeLayout.addLayout(self._traitFormLayout)
        self._attributeLayout.addStretch(1)

        self._notesTextEdit = gui.ContentSizedTextEdit()
        self._notesTextEdit.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred, # Width can vary
            QtWidgets.QSizePolicy.Policy.Minimum) # Height fits to content
        self._notesTextEdit.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.WidgetWidth)
        self._notesTextEdit.setReadOnly(True)

        self._gunCombatSkillSpinBox = gui.SpinBoxEx()
        self._gunCombatSkillSpinBox.setRange(app.MinPossibleDm, app.MaxPossibleDm)
        self._gunCombatSkillSpinBox.valueChanged.connect(self._gunCombatSkillChanged)
        gunCombatLayout = gui.FormLayoutEx()
        gunCombatLayout.addRow('Gun Combat Skill:', self._gunCombatSkillSpinBox)

        self._malfunctionGraph = gui.WeaponMalfunctionGraph()

        self._malfunctionGraphLayout = QtWidgets.QVBoxLayout()
        self._malfunctionGraphLayout.addLayout(gunCombatLayout, 0)
        self._malfunctionGraphLayout.addWidget(self._malfunctionGraph, 1)

        self._expanderWidget = gui.ExpanderGroupWidgetEx()
        self._expanderWidget.setPersistExpanderStates(True)
        self._expanderWidget.addExpandingContent(
            label='Stats',
            content=self._attributeLayout,
            expanded=True)
        self._expanderWidget.addExpandingContent(
            label='Notes',
            content=self._notesTextEdit,
            expanded=True)
        self._expanderWidget.addExpandingContent(
            label='Malfunction Probabilities',
            content=self._malfunctionGraphLayout,
            expanded=True)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._expanderWidget)
        widgetLayout.addStretch(1)

        self.setLayout(widgetLayout)

    def setWeapon(
            self,
            weapon: typing.Optional[gunsmith.Weapon],
            sequence: typing.Optional[str]
            ) -> None:
        self._weapon = weapon
        self._sequence = sequence

        if not self._weapon:
            self._configureControls(typeAttributeIds=None)
        elif self._weapon.weaponType(sequence=self._sequence) == gunsmith.WeaponType.ConventionalWeapon:
            self._configureControls(typeAttributeIds=gunsmith.ConventionalWeaponAttributeIds)
        elif self._weapon.weaponType(sequence=self._sequence) == gunsmith.WeaponType.GrenadeLauncherWeapon:
            self._configureControls(typeAttributeIds=gunsmith.LauncherWeaponAttributeIds)
        elif self._weapon.weaponType(sequence=self._sequence) == gunsmith.WeaponType.PowerPackWeapon:
            self._configureControls(typeAttributeIds=gunsmith.PowerPackEnergyWeaponAttributeIds)
        elif self._weapon.weaponType(sequence=self._sequence) == gunsmith.WeaponType.EnergyCartridgeWeapon:
            self._configureControls(typeAttributeIds=gunsmith.CartridgeEnergyWeaponAttributeIds)
        elif self._weapon.weaponType(sequence=self._sequence) == gunsmith.WeaponType.ProjectorWeapon:
            self._configureControls(typeAttributeIds=gunsmith.ProjectorWeaponAttributeIds)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(self._StateVersion)

        stream.writeInt32(self._gunCombatSkillSpinBox.value())

        expanderState = self._expanderWidget.saveState()
        stream.writeUInt32(expanderState.count() if expanderState else 0)
        if expanderState:
            stream.writeRawData(expanderState.data())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != self._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug('Failed to restore WeaponInfoWidget state (Incorrect version)')
            return False

        self._gunCombatSkillSpinBox.setValue(stream.readInt32())

        count = stream.readUInt32()
        if count <= 0:
            return True
        expanderState = QtCore.QByteArray(stream.readRawData(count))
        if not self._expanderWidget.restoreState(expanderState):
            return False

        return True

    def _configureControls(
            self,
            typeAttributeIds: typing.Optional[typing.Iterable[gunsmith.WeaponAttribute]]
            ) -> None:
        if not typeAttributeIds:
            # No (or unrecognised) weapon, nothing to display
            self._resetControls()
            return

        # Add Weapon weight at the top of basic attribute layout
        if self._basicFormLayout.isEmpty():
            self._basicFormLayout.addRow(
                'Weight',
                _WeightLineEdit(weapon=self._weapon))
        else:
            weightWidget = self._basicFormLayout.widgetAt(0)
            assert(isinstance(weightWidget, _WeightLineEdit))
            weightWidget.setWeapon(weapon=self._weapon)

        self._updateAttributeLayout(
            layout=self._basicFormLayout,
            attributeIds=typeAttributeIds,
            isTraitAttributes=False,
            startRow=1) # Account for weapon weight widget
        self._updateAttributeLayout(
            layout=self._reliabilityFormLayout,
            attributeIds=gunsmith.ReliabilityAttributeIds,
            isTraitAttributes=False)
        self._updateAttributeLayout(
            layout=self._traitFormLayout,
            attributeIds=gunsmith.TraitAttributeIds,
            isTraitAttributes=True)
        self._expanderWidget.setContentHidden(
            content=self._attributeLayout,
            hidden=self._basicFormLayout.isEmpty() and self._reliabilityFormLayout.isEmpty() and self._traitFormLayout.isEmpty())

        self._notesTextEdit.clear()
        for step in self._weapon.steps(sequence=self._sequence):
            for note in step.notes():
                self._notesTextEdit.append(f'{step.type()}: {step.name()} - {note}')

        self._expanderWidget.setContentHidden(
            content=self._notesTextEdit,
            hidden=self._notesTextEdit.isEmpty())

        self._malfunctionGraph.setWeapon(
            weapon=self._weapon,
            sequence=self._sequence)
        self._expanderWidget.setContentHidden(
            content=self._malfunctionGraphLayout,
            hidden=not self._malfunctionGraph.hasPlots())

    def _updateAttributeLayout(
            self,
            layout: gui.FormLayoutEx,
            attributeIds: typing.Optional[typing.Iterable[gunsmith.WeaponAttribute]],
            isTraitAttributes: bool,
            startRow: int = 0
            ) -> None:
        row = startRow
        for attributeId in attributeIds:
            attribute = self._weapon.attribute(
                sequence=self._sequence,
                attributeId=attributeId)
            if not attribute:
                continue

            label = 'Trait:' if isTraitAttributes else attribute.name() + ':'
            if row >= layout.rowCount():
                attributeEditBox = _AttributeLineEdit(
                    attribute=attribute,
                    isTrait=isTraitAttributes)
                layout.addRow(label, attributeEditBox)
            else:
                attributeEditBox = layout.widgetAt(row)
                attributeEditBox.setAttribute(
                    attribute=attribute,
                    isTrait=isTraitAttributes)
                layout.setLabelText(row, label)

            row += 1

        while layout.rowCount() > row:
            layout.removeRow(layout.rowCount() - 1)

    def _resetControls(self) -> None:
        self._basicFormLayout.clear()
        self._reliabilityFormLayout.clear()
        self._traitFormLayout.clear()
        self._notesTextEdit.clear()

        self._expanderWidget.setContentHidden(
            content=self._attributeLayout,
            hidden=True)
        self._expanderWidget.setContentHidden(
            content=self._notesTextEdit,
            hidden=True)
        self._expanderWidget.setContentHidden(
            content=self._malfunctionGraphLayout,
            hidden=True)

    def _gunCombatSkillChanged(self) -> None:
        self._malfunctionGraph.setGunCombatSkill(
            skill=self._gunCombatSkillSpinBox.value())
