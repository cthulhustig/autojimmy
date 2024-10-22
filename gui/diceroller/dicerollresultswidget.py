import common
import diceroller
import gui
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

class DiceRollResultsWidget(QtWidgets.QWidget):
    animationComplete = QtCore.pyqtSignal()

    _DiceDisplayPercent = 70
    _RollDurationMs = 3000
    _FadeDurationMs = 700

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._animations: typing.List[gui.DieAnimationWidget] = []
        self._pendingAnimationCount = 0
        self._labelsWidget = QtWidgets.QLabel(self)
        self._labelsWidget.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self._labelsWidget.hide()
        self._valuesWidget = QtWidgets.QLabel(self)
        self._valuesWidget.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self._valuesWidget.hide()

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding)

    def setResults(
            self,
            results: typing.Optional[diceroller.DiceRollResult],
            animate: bool = True
            ) -> None:
        if results != None:
            for animation in self._animations:
                animation.cancelSpin()

            dieCount = results.rollCount()
            while len(self._animations) > dieCount:
                animation = self._animations.pop()
                self._deleteAnimation(widget=animation)
            while len(self._animations) < dieCount:
                self._animations.append(self._createAnimation())

            self._layoutWidget()

            assert(len(self._animations) == dieCount)
            self._pendingAnimationCount = len(self._animations) if animate else 0
            for index, diceRoll in enumerate(results.yieldRolls()):
                value = diceRoll[0]
                ignored = diceRoll[1]
                animation = self._animations[index]
                animation.setDieType(results.die())
                if animate:
                    animation.startSpin(
                        result=value.value(),
                        strike=ignored)
                else:
                    animation.setValue(
                        result=value.value(),
                        strike=ignored)

            # All the animations have completed
            # NOTE: The odd way strings are formatted (with ': ' being part
            # of the value) is down to an issue I was seeing where something
            # in the Qt text rendering strips white space immediately before
            # a \n. This is a problem because it's needed as spacing between
            # the colon and the value. To work around this I've moved the
            # ': ' to the start of the value.
            labelsText = 'Rolled'
            valuesText = common.formatNumber(
                number=results.rolledTotal().value(),
                prefix=': ')

            if results.modifierCount() > 0:
                labelsText += '\nModifiers'
                valuesText += common.formatNumber(
                    number=results.modifiersTotal().value(),
                    alwaysIncludeSign=True,
                    prefix='\n: ')

            labelsText += '\nTotal'
            valuesText += common.formatNumber(
                number=results.total().value(),
                prefix='\n: ')

            effectType = results.effectType()
            if effectType != None:
                labelsText += '\nEffect'
                valuesText += '\n: {effectValue} ({effectType})'.format(
                    effectValue=common.formatNumber(
                        number=results.effectValue().value(),
                        alwaysIncludeSign=True),
                    effectType=effectType.value)

            self._labelsWidget.setText(labelsText)
            self._valuesWidget.setText(valuesText)

            if animate:
                self._labelsWidget.hide()
                self._valuesWidget.hide()
            else:
                self._labelsWidget.show()
                self._valuesWidget.show()
        else:
            for animation in self._animations:
                self._deleteAnimation(widget=animation)
            self._animations.clear()
            self._labelsWidget.setText('')
            self._valuesWidget.setText('')
            self._labelsWidget.hide()
            self._valuesWidget.hide()

        self._layoutWidget()

    def skipAnimation(self) -> None:
        for animation in self._animations:
            animation.skipSpin()

    def resizeEvent(self, event: typing.Optional[QtGui.QResizeEvent]) -> None:
        super().resizeEvent(event)
        self._layoutWidget()

    def mouseDoubleClickEvent(self, event: typing.Optional[QtGui.QMouseEvent]) -> None:
        if event and self._pendingAnimationCount > 0:
            self.skipAnimation()
            event.accept()
            return

        return super().mouseDoubleClickEvent(event)

    def _createAnimation(self) -> gui.DieAnimationWidget:
        widget = gui.DieAnimationWidget(self)
        widget.setSpinDuration(durationMs=DiceRollResultsWidget._RollDurationMs)
        widget.setFadeDuration(durationMs=DiceRollResultsWidget._FadeDurationMs)
        widget.animationComplete.connect(self._animationComplete)
        return widget

    def _deleteAnimation(
            self,
            widget: gui.DieAnimationWidget
            ) -> None:
        widget.animationComplete.disconnect(self._animationComplete)
        widget.hide()
        widget.deleteLater()

    def _layoutWidget(self) -> QtCore.QSize:
        if not self._animations:
            return

        availableWidth = self.width()
        availableHeight = self.height()
        usedHeight = self._updateDiceLayout(
            availableWidth=availableWidth,
            availableHeight=availableHeight * (DiceRollResultsWidget._DiceDisplayPercent / 100),
            offsetX=0,
            offsetY=0)

        self._updateTextLayout(
            availableWidth=availableWidth,
            availableHeight=availableHeight - usedHeight,
            offsetX=0,
            offsetY=usedHeight)

        self.update()

    def _updateDiceLayout(
            self,
            availableWidth: int,
            availableHeight: int,
            offsetX: int,
            offsetY: int
            ) -> int:
        animationCount = len(self._animations)
        xCount, yCount, size = DiceRollResultsWidget._calculateMaxDieSize(
            width=availableWidth,
            height=availableHeight * (DiceRollResultsWidget._DiceDisplayPercent / 100),
            dieCount=animationCount)
        usedWidth = xCount * size
        usedHeight = yCount * size

        indentX = (availableWidth - usedWidth) // 2

        lastRowDelta = (xCount * yCount) - len(self._animations)
        lastRowIndentX = indentX
        if lastRowDelta > 0:
            # If the last row is not a full row, what dice there are
            # should be centred in horizontally
            lastRowIndentX += (lastRowDelta * size) // 2

        for index, animation in enumerate(self._animations):
            x = index % xCount
            y = index // xCount

            xPos = (x * size) + offsetX
            yPos = (y * size) + offsetY

            xPos += indentX if y < (yCount - 1) else lastRowIndentX

            animation.move(xPos, yPos)
            animation.resize(size, size)
            animation.show()

        return usedHeight

    def _updateTextLayout(
            self,
            availableWidth: int,
            availableHeight: int,
            offsetX: int,
            offsetY: int
            ) -> int:
        fontMetrics = QtGui.QFontMetrics(self.font())
        testLabelRect = fontMetrics.boundingRect(
            QtCore.QRect(0, 0, 65535, 65535),
            self._labelsWidget.alignment(),
            self._labelsWidget.text())
        testValueRect = fontMetrics.boundingRect(
            QtCore.QRect(0, 0, 65535, 65535),
            self._valuesWidget.alignment(),
            self._valuesWidget.text())

        labelScale = valueScale = 0.5
        if testLabelRect.width() != 0 and testValueRect.width() != 0:
            testWidth = testLabelRect.width() + testValueRect.width()
            labelScale = testLabelRect.width() / testWidth
            valueScale = testValueRect.width() / testWidth

        labelAvailableRect = QtCore.QRect(
            0, 0, int(availableWidth * labelScale), availableHeight)
        labelFont = gui.sizeFontToFit(
            orig=self.font(),
            text=self._labelsWidget.text(),
            rect=labelAvailableRect,
            align=self._labelsWidget.alignment())

        valueAvailableRect = QtCore.QRect(
            0, 0, int(availableWidth * valueScale), availableHeight)
        valueFont = gui.sizeFontToFit(
            orig=self.font(),
            text=self._valuesWidget.text(),
            rect=valueAvailableRect,
            align=self._valuesWidget.alignment())

        if not labelFont or not valueFont:
            self._labelsWidget.hide()
            self._valuesWidget.hide()
            return

        if labelFont.pixelSize() > valueFont.pixelSize():
            labelFont = valueFont
        else:
            valueFont = labelFont
        self._labelsWidget.setFont(labelFont)
        self._valuesWidget.setFont(valueFont)

        self._labelsWidget.adjustSize()
        self._valuesWidget.adjustSize()

        self._labelsWidget.move(offsetX, offsetY)

        fontMetrics = QtGui.QFontMetrics(labelFont)
        labelRect = fontMetrics.boundingRect(
            labelAvailableRect,
            self._labelsWidget.alignment(),
            self._labelsWidget.text())
        self._valuesWidget.move(
            offsetX + labelRect.width(),
            offsetY)

    def _animationComplete(self) -> None:
        assert(self._pendingAnimationCount > 0)
        self._pendingAnimationCount -= 1

        if self._pendingAnimationCount > 0:
            return

        # All the animations have completed
        self._labelsWidget.show()
        self._valuesWidget.show()

        self.animationComplete.emit()

    @staticmethod
    def _calculateMaxDieSize(
            width: int,
            height: int,
            dieCount: int
            ) -> typing.Tuple[
                int, # x count
                int, # y count
                int]: # size
        """Calculate the maximum size of squares that can fit into the rectangle."""
        bestSize = 0
        bestLayout = []

        for xCount in range(1, dieCount + 1):
            yCount = (dieCount + xCount - 1) // xCount  # Compute number of rows needed to fit `x` squares

            # Ensure the configuration fits within the rectangle
            if xCount * yCount >= dieCount:
                # Calculate square size
                s = min(width // xCount, height // yCount)

                if s > bestSize:
                    bestSize = s
                    bestLayout = (xCount, yCount)

        return (bestLayout[0], bestLayout[1], int(bestSize))
