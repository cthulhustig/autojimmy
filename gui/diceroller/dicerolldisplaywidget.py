import diceroller
import gui
import logging
import typing
from PyQt5 import QtCore, QtWidgets

class DiceRollDisplayWidget(QtWidgets.QWidget):
    animationComplete = QtCore.pyqtSignal()

    _StateVersion = 'DiceRollDisplayWidget_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._roller = None
        self._results = None

        self._animatedResultsWidget = gui.DiceRollResultsWidget()
        self._animatedResultsWidget.animationComplete.connect(self._animationComplete)
        self._detailedResultsWidget = gui.DiceRollResultsTable()
        self._probabilityGraph = gui.DiceRollerProbabilityGraph()

        self._displayModeTabView = gui.TabWidgetEx()
        self._displayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.East)
        self._displayModeTabView.addTab(self._animatedResultsWidget, 'Results')
        self._displayModeTabView.addTab(self._detailedResultsWidget, 'Breakdown')
        self._displayModeTabView.addTab(self._probabilityGraph, 'Probabilities')

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._displayModeTabView)
        self.setLayout(layout)

    def setRoller(self, roller: typing.Optional[diceroller.DiceRollerDatabaseObject]) -> None:
        self._clearResults()
        self._roller = roller
        self._probabilityGraph.setRoller(roller=roller)
        self._probabilityGraph.setHighlightRoll(roll=None)

    def setResults(
            self,
            results: typing.Optional[diceroller.DiceRollResult],
            animate: bool = True) -> None:
        self._clearResults()
        self._results = results
        self._animatedResultsWidget.setResults(results=results, animate=animate)

        if animate:
            # If we're animating, may as well show it
            self._displayModeTabView.setCurrentWidget(self._animatedResultsWidget)
        else:
            self._detailedResultsWidget.setResults(results=results)
            self._probabilityGraph.setHighlightRoll(results.total() if results else None)

    def skipAnimation(self) -> None:
        self._animatedResultsWidget.skipAnimation()

    def syncToRoller(self) -> None:
        self._probabilityGraph.syncToRoller()

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(DiceRollDisplayWidget._StateVersion)

        childState = self._probabilityGraph.saveState()
        stream.writeUInt32(childState.count() if childState else 0)
        if childState:
            stream.writeRawData(childState.data())

        childState = self._displayModeTabView.saveState()
        stream.writeUInt32(childState.count() if childState else 0)
        if childState:
            stream.writeRawData(childState.data())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != DiceRollDisplayWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore DiceRollDisplayWidget state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count > 0:
            childState = QtCore.QByteArray(stream.readRawData(count))
            if not self._probabilityGraph.restoreState(childState):
                return False

        count = stream.readUInt32()
        if count > 0:
            childState = QtCore.QByteArray(stream.readRawData(count))
            if not self._displayModeTabView.restoreState(childState):
                return False

        return True

    def _clearResults(self) -> None:
        self._results = None
        self._animatedResultsWidget.setResults(results=None)
        self._detailedResultsWidget.setResults(results=None)
        self._probabilityGraph.setHighlightRoll(roll=None)

    def _animationComplete(self) -> None:
        self._detailedResultsWidget.setResults(results=self._results)
        self._probabilityGraph.setHighlightRoll(self._results.total() if self._results else None)
        self.animationComplete.emit()
