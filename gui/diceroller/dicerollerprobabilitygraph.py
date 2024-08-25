import common
import diceroller
import gui
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
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            ) -> None:
        super().__init__(parent)
        self._roller = None
        self._bars = None
        self._highlightRoll = None

        self._graph = _CustomPlotWidget()
        self._graph.mouseMoveSignal.connect(self._moveCursor)

        self._graph.setBackground(QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.Base))

        font = QtWidgets.QApplication.font()
        styles = {'color': gui.colourToString(QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.Text))}
        self._graph.setLabel('left', 'Probability (%)', **styles)
        self._graph.setLabel('bottom', 'Dice Roll', **styles)

        # Prevent the mouse from panning/scaling the graph
        self._graph.setMouseEnabled(x=False, y=False)

        # Hide auto scale button
        self._graph.hideButtons()

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._graph)

        self.setLayout(layout)

    def setRoller(
            self,
            roller: typing.Optional[diceroller.DiceRoller] = None
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

    def _updateGraph(self):
        if not self._roller:
            self._bars.hide()
            return # No weapon set so nothing to do

        probabilities = self._roller.calculateProbabilities()
        xValues = list(probabilities.keys())
        yValues = [value.value() * 100 for value in probabilities.values()]

        defaultColour = 'w' if gui.isDarkModeEnabled() else 'k'
        colours = []
        for roll in xValues:
            colours.append('b' if roll == self._highlightRoll else defaultColour)

        xMin = min(xValues)
        xMax = max(xValues)
        xRange = (xMax - xMin) + 1
        barWidth = (xRange / len(xValues)) * 0.8

        if self._bars == None:
            self._bars = pyqtgraph.BarGraphItem(
                x=xValues,
                height=yValues,
                width=barWidth,
                brushes=colours)
            self._graph.addItem(self._bars)
        else:
            self._bars.setOpts(
                x=xValues,
                height=yValues,
                width=barWidth,
                brushes=colours)
        self._bars.show()

    def _moveCursor(
            self,
            cursorWidgetPos: QtCore.QPointF
            ) -> None:
        pass
