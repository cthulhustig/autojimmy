import pyqtgraph
from PyQt5 import QtCore, QtGui

class PlotWidgetEx(pyqtgraph.PlotWidget):
    mouseMoveSignal = QtCore.pyqtSignal([QtCore.QPointF])

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        self.mouseMoveSignal.emit(event.localPos())
        return super().mouseMoveEvent(event)