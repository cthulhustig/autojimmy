import gui
import logging
import robots
import typing
from PyQt5 import QtWidgets, QtCore

# TODO: There is an ugly bug where sometimes while typing, the notes
# table jumps up massively for a few seconds then goes back down again.
# To reproduce type a long string of garbage so nothing matches then
# hold the delete key, they jump happens at the point it gets short
# enough to start matching stuff
class RobotInfoWidget(QtWidgets.QWidget):
    _StateVersion = 'RobotInfoWidget_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._robot = None

        self._statsSheetWidget = gui.RobotSheetWidget()
        self._notesWidget = gui.NotesWidget()

        self._expanderWidget = gui.ExpanderGroupWidgetEx()
        self._expanderWidget.setPersistExpanderStates(True)
        self._expanderWidget.addExpandingContent(
            label='Stats',
            content=self._statsSheetWidget,
            expanded=True)        
        self._expanderWidget.addExpandingContent(
            label='Notes',
            content=self._notesWidget,
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

        statsState = self._statsSheetWidget.saveState()
        stream.writeUInt32(statsState.count() if statsState else 0)
        if statsState:
            stream.writeRawData(statsState.data())

        notesState = self._notesWidget.saveState()
        stream.writeUInt32(notesState.count() if notesState else 0)
        if notesState:
            stream.writeRawData(notesState.data())            

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
        statsState = QtCore.QByteArray(stream.readRawData(count))
        if not self._statsSheetWidget.restoreState(statsState):
            return False
        
        count = stream.readUInt32()
        if count <= 0:
            return True
        notesState = QtCore.QByteArray(stream.readRawData(count))
        if not self._notesWidget.restoreState(notesState):
            return False        

        count = stream.readUInt32()
        if count <= 0:
            return True
        expanderState = QtCore.QByteArray(stream.readRawData(count))
        if not self._expanderWidget.restoreState(expanderState):
            return False

        return True

    def _configureControls(self) -> None:       
        self._statsSheetWidget.setRobot(robot=self._robot)
        self._expanderWidget.setContentHidden(
            content=self._statsSheetWidget,
            hidden=self._robot == None)

        self._notesWidget.setSteps(self._robot.steps())
        self._expanderWidget.setContentHidden(
            content=self._notesWidget,
            hidden=self._notesWidget.isEmpty())

    def _resetControls(self) -> None:
        self._statsSheetWidget.clear()
        self._notesWidget.clear()

        # Hide expanders (and the controls they contain). They will be
        # shown again if/when they have something to display
        self._expanderWidget.setContentHidden(
            content=self._statsSheetWidget,
            hidden=True)
        self._expanderWidget.setContentHidden(
            content=self._notesWidget,
            hidden=True)        

