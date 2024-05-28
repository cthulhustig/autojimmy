import app
import construction
import common
import enum
import gui
import logging
import robots
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
            action = QtWidgets.QAction('Show Calculation...')
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
                decimalPlaces=robots.ConstructionDecimalPlaces)
        except Exception as ex:
            message = 'Failed to show calculations'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

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

class RobotInfoWidget(QtWidgets.QWidget):
    # TODO: Need to add something to display skills and weapons

    _StateVersion = 'RobotInfoWidget_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._robot = None

        self._basicFormLayout = gui.FormLayoutEx()
        self._basicFormLayout.setContentsMargins(0, 0, 0, 0)

        self._traitFormLayout = gui.FormLayoutEx()
        self._traitFormLayout.setContentsMargins(0, 0, 0, 0)        

        self._attributeLayout = QtWidgets.QHBoxLayout()
        self._attributeLayout.setContentsMargins(0, 0, 0, 0)
        self._attributeLayout.addLayout(self._basicFormLayout)
        self._attributeLayout.addLayout(self._traitFormLayout)
        self._attributeLayout.addStretch(1)

        self._notesTextEdit = gui.ContentSizedTextEdit()
        self._notesTextEdit.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred, # Width can vary
            QtWidgets.QSizePolicy.Policy.Minimum) # Height fits to content
        self._notesTextEdit.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.WidgetWidth)
        self._notesTextEdit.setReadOnly(True)

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

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._expanderWidget)
        widgetLayout.addStretch(1)

        self.setLayout(widgetLayout)

    def setRobot(
            self,
            robot: typing.Optional[robots.Robot]
            ) -> None:
        self._robot = robot
        self._configureControls()

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(self._StateVersion)

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
            logging.debug('Failed to restore RobotInfoWidget state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count <= 0:
            return True
        expanderState = QtCore.QByteArray(stream.readRawData(count))
        if not self._expanderWidget.restoreState(expanderState):
            return False

        return True

    def _configureControls(self) -> None:
        self._updateAttributeLayout(
            layout=self._basicFormLayout,
            attributeIds=robots.StandardAttributeIds,
            isTraitAttributes=False)
        self._updateAttributeLayout(
            layout=self._traitFormLayout,
            attributeIds=robots.TraitAttributesIds,
            isTraitAttributes=True)        
        self._expanderWidget.setContentHidden(
            content=self._attributeLayout,
            hidden=self._basicFormLayout.isEmpty())

        self._notesTextEdit.clear()
        seenNotes = set()
        for step in self._robot.steps():
            for note in step.notes():
                note = f'{step.type()}: {step.name()} - {note}'
                if note not in seenNotes:
                    self._notesTextEdit.append(note)
                    seenNotes.add(note)

        self._expanderWidget.setContentHidden(
            content=self._notesTextEdit,
            hidden=self._notesTextEdit.isEmpty())

    def _updateAttributeLayout(
            self,
            layout: gui.FormLayoutEx,
            attributeIds: typing.Optional[typing.Iterable[robots.RobotAttributeId]],
            isTraitAttributes: bool,
            startRow: int = 0
            ) -> None:
        row = startRow
        for attributeId in attributeIds:
            attribute = self._robot.attribute(
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
        self._notesTextEdit.clear()

        self._expanderWidget.setContentHidden(
            content=self._attributeLayout,
            hidden=True)
        self._expanderWidget.setContentHidden(
            content=self._notesTextEdit,
            hidden=True)

