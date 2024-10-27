import pyqtgraph
from PyQt5 import QtCore, QtGui

# TODO: This is a duplicate of the one from the malfunction graph
class PlotWidgetEx(pyqtgraph.PlotWidget):
    mouseMoveSignal = QtCore.pyqtSignal([QtCore.QPointF])

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        self.mouseMoveSignal.emit(event.localPos())
        return super().mouseMoveEvent(event)