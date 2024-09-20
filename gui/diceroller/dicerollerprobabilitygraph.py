import common
import diceroller
import gui
import logging
import pyqtgraph
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

# TODO: This is a duplicate of the one from the malfunction graph
class _CustomPlotWidget(pyqtgraph.PlotWidget):
    mouseMoveSignal = QtCore.pyqtSignal([QtCore.QPointF])

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        self.mouseMoveSignal.emit(event.localPos())
        return super().mouseMoveEvent(event)

class DiceRollerProbabilityGraph(QtWidgets.QWidget):
    _StateVersion = 'DiceRollerProbabilityGraph_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            ) -> None:
        super().__init__(parent)
        self._roller = None
        self._bars = None
        self._highlightRoll = None

        self._typeComboBox = gui.EnumComboBox(
            type=common.ProbabilityType)
        self._typeComboBox.setCurrentEnum(
            value=common.ProbabilityType.EqualTo)
        self._typeComboBox.currentIndexChanged.connect(
            self._updateGraph)

        self._graph = _CustomPlotWidget()
        self._graph.mouseMoveSignal.connect(self._moveCursor)

        self._graph.setBackground(QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.Base))

        styles = {'color': gui.colourToString(QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.Text))}
        self._graph.setLabel('left', 'Probability (%)', **styles)
        self._graph.setLabel('bottom', 'Dice Roll', **styles)

        # TODO: I'm not sure about forcing the Y range. It means the graph
        # can be pretty low if you have a large number of dice
        self._graph.setYRange(0, 100)

        # Prevent the mouse from panning/scaling the graph
        self._graph.setMouseEnabled(x=False, y=False)

        # Hide auto scale button
        self._graph.hideButtons()

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(gui.createLabelledWidgetLayout('Probability Type', self._typeComboBox))
        layout.addWidget(self._graph)

        self.setLayout(layout)

    def setRoller(
            self,
            roller: typing.Optional[diceroller.DiceRollerDatabaseObject] = None
            ) -> None:
        self._roller = roller
        self._updateGraph()

    def setHighlightRoll(
            self,
            roll: typing.Optional[typing.Union[int, common.ScalarCalculation]]
            ):
        self._highlightRoll = int(roll.value()) if isinstance(roll, common.ScalarCalculation) else roll
        self._updateGraph()

    def syncToRoller(self) -> None:
        self._updateGraph()

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(self._StateVersion)

        statsState = self._typeComboBox.saveState()
        stream.writeUInt32(statsState.count() if statsState else 0)
        if statsState:
            stream.writeRawData(statsState.data())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != self._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug('Failed to restore DiceRollerProbabilityGraph state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count <= 0:
            return True
        statsState = QtCore.QByteArray(stream.readRawData(count))
        if not self._typeComboBox.restoreState(statsState):
            return False

        return True

    def _updateGraph(self):
        if not self._roller:
            if self._bars != None:
                self._bars.hide()
            return # No weapon set so nothing to do

        modifiers = []
        for modifier in self._roller.dynamicDMs():
            assert(isinstance(modifier, diceroller.DiceModifierDatabaseObject))
            if modifier.enabled():
                modifiers.append((modifier.name(), modifier.value()))
        probabilities = diceroller.calculateProbabilities(
            dieCount=self._roller.dieCount(),
            dieType=self._roller.dieCount(),
            constantDM=self._roller.constantDM(),
            hasBoon=self._roller.hasBoon(),
            hasBane=self._roller.hasBane(),
            dynamicDMs=modifiers,
            probability=self._typeComboBox.currentEnum())
        xValues = list(probabilities.keys())
        yValues = [value.value() * 100 for value in probabilities.values()]

        defaultColour = 'w' if gui.isDarkModeEnabled() else 'k'
        colours = []
        for roll in xValues:
            colour = defaultColour
            if roll == self._highlightRoll:
                colour = 'b'
            elif self._roller.targetNumber() != None:
                colour = 'g' if roll >= self._roller.targetNumber() else 'r'
            colours.append(colour)

        xMin = min(xValues)
        xMax = max(xValues)
        xRange = (xMax - xMin) + 1
        barWidth = (xRange / len(xValues)) * 0.8

        if self._bars == None:
            self._bars = pyqtgraph.BarGraphItem(
                x=xValues,
                height=yValues,
                width=barWidth,
                brushes=colours,
                pen=defaultColour)
            self._graph.addItem(self._bars)
        else:
            self._bars.setOpts(
                x=xValues,
                height=yValues,
                width=barWidth,
                brushes=colours,
                pen=defaultColour)
        self._bars.show()

    def _moveCursor(
            self,
            cursorWidgetPos: QtCore.QPointF
            ) -> None:
        pass
