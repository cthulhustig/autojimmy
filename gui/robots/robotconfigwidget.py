import construction
import gui
import logging
import robots
import typing
from PyQt5 import QtWidgets, QtCore

class RobotConfigWidget(QtWidgets.QWidget):
    robotChanged = QtCore.pyqtSignal(robots.Robot)

    _StateVersion = 'RobotConfigWidget_v1'

    def __init__(
            self,
            robot: robots.Robot,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._robot = None
        self._phaseWidgets: typing.Dict[robots.RobotPhase, gui.SinglePhaseStageWidget] = {}
        self._stageExpansionMap: typing.Dict[str, bool] = {}

        self._techLevelSpinBox = gui.SpinBoxEx()
        self._techLevelSpinBox.setMinimum(0)
        self._techLevelSpinBox.setValue(robot.techLevel())
        self._techLevelSpinBox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._techLevelSpinBox.valueChanged.connect(self._techLevelChanged)

        globalLayout = gui.VBoxLayoutEx()
        globalLayout.addLabelledWidget(
            label='Tech Level:',
            widget=self._techLevelSpinBox,
            alignment=QtCore.Qt.AlignmentFlag.AlignLeft)

        self._configurationWidget = gui.ExpanderGroupWidgetEx()
        self._configurationWidget.setPersistExpanderStates(True)
        self._configurationWidget.addExpandingContent(
            label='Global',
            content=globalLayout,
            expanded=True)

        self.setRobot(robot=robot)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._configurationWidget)
        widgetLayout.addStretch(1)

        self.setLayout(widgetLayout)

    def techLevel(self) -> None:
        return self._robot.techLevel()

    def robot(self) -> robots.Robot:
        return self._robot

    def setRobot(
            self,
            robot: robots.Robot
            ) -> None:
        self._robot = robot

        with gui.SignalBlocker(widget=self._techLevelSpinBox):
            self._techLevelSpinBox.setValue(self._robot.techLevel())

        self._configureDynamicWidgets()

        self.robotChanged.emit(self._robot)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(RobotConfigWidget._StateVersion)

        expanderState = self._configurationWidget.saveState()
        stream.writeUInt32(expanderState.count() if expanderState else 0)
        if expanderState:
            stream.writeRawData(expanderState.data())

        stream.writeUInt32(len(self._stageExpansionMap))
        for label, isExpanded in self._stageExpansionMap.items():
            stream.writeQString(label)
            stream.writeBool(isExpanded)

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != RobotConfigWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore RobotConfigWidget state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count > 0:
            expanderState = QtCore.QByteArray(stream.readRawData(count))
            if not self._configurationWidget.restoreState(state=expanderState):
                return False

        count = stream.readUInt32()
        if count > 0:
            self._stageExpansionMap.clear()
            for _ in range(count):
                label = stream.readQString()
                isExpanded = stream.readBool()
                self._stageExpansionMap[label] = isExpanded

            for phaseWidget in self._phaseWidgets.values():
                with gui.SignalBlocker(phaseWidget):
                    phaseWidget.expandStages(
                        expansionMap=self._stageExpansionMap,
                        animated=False)

        return True

    def _techLevelChanged(self, techLevel: int) -> None:
        self._robot.setTechLevel(techLevel=techLevel)
        self._synchroniseStages()
        self.robotChanged.emit(self._robot)

    def _configureDynamicWidgets(self) -> None:
        self._removeWidgets()

        if not self._robot:
            return # No more to do

        for phase in robots.RobotPhase:
            if phase == robots.RobotPhase.Finalisation:
                continue # Don't create widgets for finalisation

            phaseWidget = gui.SinglePhaseStageWidget(
                context=self._robot.context(),
                phase=phase)
            phaseWidget.expandStages(expansionMap=self._stageExpansionMap, animated=False)
            phaseWidget.stageChanged.connect(self._stageChanged)
            phaseWidget.expansionChanged.connect(self._expansionChanged)
            self._configurationWidget.addExpandingContent(
                label=phase.value,
                content=phaseWidget,
                expanded=True)
            self._phaseWidgets[phase] = phaseWidget

    def _removeWidgets(self) -> None:
        for phaseWidget in self._phaseWidgets.values():
            phaseWidget.stageChanged.disconnect(self._stageChanged)
            phaseWidget.expansionChanged.disconnect(self._expansionChanged)
            # TODO: Check this ordering is correct, shouldn't teardown come after removal from the config widget?
            # This would also apply to the gunsmith as this ordering was copied (and then flattened) from the
            # equivalent implementation there
            phaseWidget.teardown()
            self._configurationWidget.removeContent(content=phaseWidget)
            phaseWidget.setParent(None)
            phaseWidget.setHidden(True)
            phaseWidget.deleteLater()
        self._phaseWidgets.clear()

    def _stageChanged(
            self,
            stage: construction.ConstructionStage
            ) -> None:
        self._synchroniseStages()
        self.robotChanged.emit(self._robot)

    def _expansionChanged(
            self,
            label: str,
            expanded: bool
            ) -> None:
        self._stageExpansionMap[label] = expanded

    def _synchroniseStages(self) -> None:
        for phase in robots.RobotPhase:
            phaseWidget = self._phaseWidgets.get(phase)
            if not phaseWidget:
                continue
            phaseWidget.synchronise()
