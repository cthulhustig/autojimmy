import common
import gunsmith
import gui
import logging
import pyqtgraph
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class _CustomPlotWidget(pyqtgraph.PlotWidget):
    mouseMoveSignal = QtCore.pyqtSignal([QtCore.QPointF])

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        self.mouseMoveSignal.emit(event.localPos())
        return super().mouseMoveEvent(event)

class WeaponMalfunctionGraph(QtWidgets.QWidget):
    _LightMalfunctionTypeColourMap = {
        gunsmith.MalfunctionType.MalfunctionType1: QtGui.QColor(255, 0, 0),
        gunsmith.MalfunctionType.MalfunctionType2: QtGui.QColor(255, 0, 255),
        gunsmith.MalfunctionType.MalfunctionType3: QtGui.QColor(128, 0, 128),
        gunsmith.MalfunctionType.MalfunctionType4: QtGui.QColor(0, 255, 255),
        gunsmith.MalfunctionType.MalfunctionType5: QtGui.QColor(0, 255, 0),
    }
    _DarkMalfunctionTypeColourMap = {
        gunsmith.MalfunctionType.MalfunctionType1: QtGui.QColor(255, 0, 0),
        gunsmith.MalfunctionType.MalfunctionType2: QtGui.QColor(255, 0, 255),
        gunsmith.MalfunctionType.MalfunctionType3: QtGui.QColor(255, 255, 0),
        gunsmith.MalfunctionType.MalfunctionType4: QtGui.QColor(0, 255, 255),
        gunsmith.MalfunctionType.MalfunctionType5: QtGui.QColor(0, 255, 0),
    }

    _ToolTipOffset = QtCore.QPoint(5, 5)
    _TemperatureAxisPaddingPercentage = 0.1
    _TemperatureAxisMinPadding = 2

    def __init__(
            self,
            skill: int = 0,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            ) -> None:
        super().__init__(parent)
        self._weapon = None
        self._sequence = None
        self._skill = skill
        self._plots: typing.List[pyqtgraph.PlotDataItem] = []

        self._graph = _CustomPlotWidget()
        self._graph.mouseMoveSignal.connect(self._moveCursor)

        self._graph.setBackground(QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.Base))

        font = QtWidgets.QApplication.font()
        styles = {'color': gui.colourToString(QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.Text))}
        self._graph.setLabel('left', 'Malfunction Probability (%)', **styles)
        self._graph.setLabel('bottom', 'Current Heat', **styles)
        self._graph.setYRange(0, 100)

        # Prevent the mouse from panning/scaling the graph
        self._graph.setMouseEnabled(x=False, y=False)

        # Hide auto scale button
        self._graph.hideButtons()

        self._legend: pyqtgraph.LegendItem = self._graph.addLegend()
        self._legend.setLabelTextSize(str(font.pointSizeF()))

        self._highlightLine = pyqtgraph.InfiniteLine(
            angle=90,
            movable=False,
            pen=QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.Highlight))
        self._graph.addItem(self._highlightLine, ignoreBounds=True)

        # Create a label that gives the descriptions of the different malfunction types.
        # The seemingly pointless font tags on the first line of text are needed otherwise
        # the QLabel doesn't interpret the string as html
        descriptionText = '<font>Malfunction Types:</font>'
        for malfunctionType in gunsmith.MalfunctionType:
            if len(descriptionText) > 0:
                descriptionText += '<br>'
            malfunctionColour = gui.colourToString(WeaponMalfunctionGraph._malfunctionColour(malfunctionType))
            descriptionText += f' <font color="{malfunctionColour}"><b>Type {malfunctionType.value}</b></font>: '
            descriptionText += gunsmith.malfunctionDescription(
                malfunctionType=malfunctionType)
        self._descriptionLabel = QtWidgets.QLabel(descriptionText)
        self._descriptionLabel.setWordWrap(True)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._graph)
        layout.addWidget(self._descriptionLabel)

        self.setLayout(layout)

        if self._weapon:
            self._updateGraph()

    def setWeapon(
            self,
            weapon: typing.Optional[gunsmith.Weapon] = None,
            sequence: typing.Optional[str] = None
            ) -> None:
        self._weapon = weapon if weapon and sequence else None
        self._sequence = sequence if weapon and sequence else None
        self._updateGraph()

    def setGunCombatSkill(
            self,
            skill: int
            ) -> None:
        self._skill = skill
        self._updateGraph()

    def hasPlots(self) -> bool:
        return len(self._plots) > 0

    def _updateGraph(self):
        for plot in self._plots:
            self._graph.removeItem(plot)
        self._plots.clear()
        if not self._weapon:
            return # No weapon set so nothing to do

        overheatThreshold = self._weapon.attributeValue(
            sequence=self._sequence,
            attributeId=gunsmith.WeaponAttributeId.OverheatThreshold)
        if not isinstance(overheatThreshold, common.ScalarCalculation):
            return

        dangerThreshold = self._weapon.attributeValue(
            sequence=self._sequence,
            attributeId=gunsmith.WeaponAttributeId.DangerHeatThreshold)
        if not isinstance(overheatThreshold, common.ScalarCalculation):
            return

        disasterThreshold = self._weapon.attributeValue(
            sequence=self._sequence,
            attributeId=gunsmith.WeaponAttributeId.DisasterHeatThreshold)
        if not isinstance(disasterThreshold, common.ScalarCalculation):
            return

        malfunctionDM = self._weapon.attributeValue(
            sequence=self._sequence,
            attributeId=gunsmith.WeaponAttributeId.MalfunctionDM)
        if not isinstance(malfunctionDM, common.ScalarCalculation):
            return

        if not (overheatThreshold.value() < dangerThreshold.value() < disasterThreshold.value()):
            return

        temperatureRange = disasterThreshold.value() - overheatThreshold.value()
        temperatureAxisPadding = max(
            round(temperatureRange * self._TemperatureAxisPaddingPercentage),
            self._TemperatureAxisMinPadding)
        temperatures: typing.List[int] = list(range(
            overheatThreshold.value() - temperatureAxisPadding,
            disasterThreshold.value() + temperatureAxisPadding + 1))
        malfunctionTypeValues: typing.Dict[gunsmith.MalfunctionType, typing.List[float]] = \
            {type: [] for type in gunsmith.MalfunctionType}
        totalValues: typing.List[float] = []
        for temperature in temperatures:
            try:
                malfunctionMap = gunsmith.calculateMalfunctionProbability(
                    weapon=self._weapon,
                    sequence=self._sequence,
                    weaponSkill=self._skill,
                    currentHeat=temperature)
            except Exception as ex:
                logging.error('WeaponMalfunctionGraph failed to calculate malfunction probability', exc_info=ex)
                return # Return without adding any plots

            total = 0
            for malfunctionType in gunsmith.MalfunctionType:
                probability = malfunctionMap.get(malfunctionType)
                probability = probability.value() if probability else 0
                probability *= 100 # Convert from normalised percentage to percentage
                malfunctionTypeValues[malfunctionType].append(probability)
                total += probability

            totalValues.append(total)

        for malfunctionType, values in malfunctionTypeValues.items():
            malfunctionColour = pyqtgraph.mkPen(WeaponMalfunctionGraph._malfunctionColour(malfunctionType))
            self._addPlot(
                temperatures=temperatures,
                probabilities=values,
                name=f'Type {malfunctionType.value}',
                colour=malfunctionColour)

        self._addPlot(
            temperatures=temperatures,
            probabilities=totalValues,
            name='Total',
            colour='w' if gui.isDarkModeEnabled() else 'k')

    def _addPlot(
            self,
            temperatures: typing.Iterable[int],
            probabilities: typing.Iterable[float],
            name: str,
            colour: typing.Union[str, QtGui.QColor]
            ) -> None:
        plot = self._graph.plot(
            x=temperatures,
            y=probabilities,
            name=name,
            pen=colour)
        self._plots.append(plot)

    def _moveCursor(
            self,
            cursorWidgetPos: QtCore.QPointF
            ) -> None:
        if self._graph.sceneBoundingRect().contains(cursorWidgetPos):
            cursorGraphPos: QtCore.QPoint = self._graph.getPlotItem().vb.mapSceneToView(cursorWidgetPos)
            cursorTemperature = round(cursorGraphPos.x())
            self._highlightLine.setPos(cursorTemperature)

            for plot in self._plots:
                legendLabel: pyqtgraph.LabelItem = self._legend.getLabel(plotItem=plot)
                if not legendLabel:
                    continue

                temperatureData, probabilityData = plot.getData()
                legendText = plot.name() + ':'
                if cursorTemperature >= temperatureData.min() and cursorTemperature <= temperatureData.max():
                    probability = probabilityData[cursorTemperature - temperatureData.min()]
                    legendText += f' Heat {cursorTemperature} = {common.formatNumber(number=probability)}% chance'
                legendLabel.setText(legendText)
            self._legend.updateSize()

    @staticmethod
    def _malfunctionColour(malfunctionType: gunsmith.MalfunctionType):
        colourMap = \
            WeaponMalfunctionGraph._DarkMalfunctionTypeColourMap \
            if gui.isDarkModeEnabled() else \
            WeaponMalfunctionGraph._LightMalfunctionTypeColourMap
        return colourMap[malfunctionType]
