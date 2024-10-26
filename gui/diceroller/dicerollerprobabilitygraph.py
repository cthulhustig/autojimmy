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
            type=common.ComparisonType)
        self._typeComboBox.setCurrentEnum(
            value=common.ComparisonType.EqualTo)
        self._typeComboBox.currentIndexChanged.connect(
            self._updateGraph)

        self._graph = _CustomPlotWidget()
        self._graph.mouseMoveSignal.connect(self._moveCursor)

        self._graph.setBackground(QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.Base))

        styles = {'color': gui.colourToString(QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.Text))}
        self._graph.setLabel('left', 'Probability (%)', **styles)
        self._graph.setLabel('bottom', 'Dice Roll', **styles)

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

        probabilities = diceroller.calculateProbabilities(
            roller=self._roller,
            probability=self._typeComboBox.currentEnum())
        xValues = list(probabilities.keys())
        yValues = [value.value() * 100 for value in probabilities.values()]

        defaultColour = 'w' if gui.isDarkModeEnabled() else 'k'
        colours = []
        for roll in xValues:
            colour = defaultColour
            if roll == self._highlightRoll:
                colour = 'b'
            elif self._roller.hasTarget():
                isSuccess = common.ComparisonType.compareValues(
                    lhs=roll,
                    rhs=self._roller.targetNumber(),
                    comparison=self._roller.targetType())
                colour = 'g' if isSuccess else 'r'
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
        matched = None

        # NOTE: This is hokey as hell. The pyqtgraph api doesn't make the rects
        # of the bars available over a public API but it does store them in an
        # internal _rectarray
        if self._bars and self._bars._rectarray:
            pos = self._graph.getPlotItem().vb.mapSceneToView(cursorWidgetPos)
            for index, rect in enumerate(self._bars._rectarray.instances()):
                assert(isinstance(rect, QtCore.QRectF))
                x = pos.x()
                if x >= rect.left() and x <= rect.right():
                    matched = index
                    break

        if matched != None:
            values, probabilities = self._bars.getData()
            graphType = self._typeComboBox.currentEnum()
            assert(isinstance(graphType, common.ComparisonType))
            # NOTE: A high decimal place count is used to avoid cases where
            # rounding can make the tool tip look wrong. For example, with just
            # 2-3 decimal places it would say there was a 100% probability of
            # rolling >= 8 with 7 D20 which just seems wrong
            toolTip = '{probability}% chance of rolling {type} {value}'.format(
                probability=common.formatNumber(
                    number=probabilities[matched],
                    decimalPlaces=10),
                type=graphType.value.lower(),
                value=values[matched])

            self.setToolTip(toolTip)
            QtWidgets.QToolTip.showText(
                self._graph.mapToGlobal(cursorWidgetPos.toPoint()),
                toolTip)
        else:
            self.setToolTip(None)
            QtWidgets.QToolTip.hideText()
