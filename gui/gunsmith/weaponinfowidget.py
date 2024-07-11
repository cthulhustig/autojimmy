import app
import construction
import common
import enum
import gui
import gunsmith
import logging
import typing
from PyQt5 import QtWidgets, QtCore

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
            action = QtWidgets.QAction('Show Calculation...')
            action.triggered.connect(lambda: self._showCalculations(calculations))

            existingActions = menu.actions()
            firstAction = existingActions[0] if existingActions else None
            menu.insertAction(firstAction, action)

        menu.exec(self.mapToGlobal(position))

    def _showCalculations(
            self,
            calculations: typing.Iterable[common.ScalarCalculation]
            ) -> None:
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
    _StateVersion = 'WeaponInfoWidget_v2'

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

        statsLayout = QtWidgets.QHBoxLayout()
        statsLayout.addLayout(self._basicFormLayout)
        statsLayout.addLayout(self._reliabilityFormLayout)
        statsLayout.addLayout(self._traitFormLayout)
        statsLayout.addStretch(1)
        self._statsGroupBox = QtWidgets.QGroupBox('Stats')
        self._statsGroupBox.setLayout(statsLayout)

        self._notesWidget = gui.NotesWidget()

        notesLayout = QtWidgets.QVBoxLayout()
        notesLayout.addWidget(self._notesWidget)
        self._notesGroupBox = QtWidgets.QGroupBox('Notes')
        self._notesGroupBox.setLayout(notesLayout)

        self._gunCombatSkillSpinBox = gui.SpinBoxEx()
        self._gunCombatSkillSpinBox.setRange(app.MinPossibleDm, app.MaxPossibleDm)
        self._gunCombatSkillSpinBox.valueChanged.connect(self._gunCombatSkillChanged)
        gunCombatLayout = gui.FormLayoutEx()
        gunCombatLayout.addRow('Gun Combat Skill:', self._gunCombatSkillSpinBox)

        self._malfunctionGraph = gui.WeaponMalfunctionGraph()

        malfunctionLayout = QtWidgets.QVBoxLayout()
        malfunctionLayout.addLayout(gunCombatLayout, 0)
        malfunctionLayout.addWidget(self._malfunctionGraph, 1)
        self._malfunctionGroupBox = QtWidgets.QGroupBox('Malfunction Probabilities')
        self._malfunctionGroupBox.setLayout(malfunctionLayout)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._statsGroupBox)
        widgetLayout.addWidget(self._notesGroupBox)
        widgetLayout.addWidget(self._malfunctionGroupBox)
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

        return True

    def _configureControls(
            self,
            typeAttributeIds: typing.Optional[typing.Iterable[gunsmith.WeaponAttributeId]]
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
        self._statsGroupBox.setHidden(
            self._basicFormLayout.isEmpty() and self._reliabilityFormLayout.isEmpty() and self._traitFormLayout.isEmpty())

        self._notesWidget.setSteps(
            self._weapon.steps(sequence=self._sequence))
        self._notesGroupBox.setHidden(
            self._notesWidget.isEmpty())

        self._malfunctionGraph.setWeapon(
            weapon=self._weapon,
            sequence=self._sequence)
        self._malfunctionGroupBox.setHidden(
            not self._malfunctionGraph.hasPlots())

    def _updateAttributeLayout(
            self,
            layout: gui.FormLayoutEx,
            attributeIds: typing.Optional[typing.Iterable[gunsmith.WeaponAttributeId]],
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
        self._statsGroupBox.setHidden(True)
        self._notesGroupBox.setHidden(True)
        self._malfunctionGroupBox.setHidden(True)

        self._basicFormLayout.clear()
        self._reliabilityFormLayout.clear()
        self._traitFormLayout.clear()
        self._notesWidget.clear()

    def _gunCombatSkillChanged(self) -> None:
        self._malfunctionGraph.setGunCombatSkill(
            skill=self._gunCombatSkillSpinBox.value())
