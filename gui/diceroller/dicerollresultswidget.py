import diceroller
import gui
import typing
from PyQt5 import QtWidgets

class DiceRollResultsWidget(QtWidgets.QWidget):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._results = None

        self._totalWidget = gui.FullSizeTextWidget()

        self._targetWidget = gui.FullSizeTextWidget()
        self._targetWidget.setHidden(True)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._totalWidget, 5)
        widgetLayout.addWidget(self._targetWidget, 1)

        self.setLayout(widgetLayout)

    def setResults(
            self,
            results: typing.Optional[diceroller.DiceRollResult]
            ) -> None:
        if results:
            total = results.total()
            effectType = results.effectType()
            self._totalWidget.setText(str(total.value()))
            if effectType:
                targetText = effectType.value
                effectValue = results.effectValue()
                targetText += f' (Effect: {effectValue.value()})'
                self._targetWidget.setText(targetText)
            self._targetWidget.setHidden(effectType == None)
        else:
            self._totalWidget.setText('')
            self._targetWidget.setText('')
            self._targetWidget.setHidden(True)
