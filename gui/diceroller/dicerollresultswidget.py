import app
import common
import diceroller
import gui
import math
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

class _SnakeEyesWidget(QtWidgets.QWidget):
    _DisplayText = 'Snake Eyes!'
    _TextOutlineWidth = 1.5

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget]):
        super().__init__(parent)
        self._textSize = QtCore.QSize()
        self._handleResize()

    def paintEvent(self, event):
        textAngle = math.degrees(self._calculateTextAngle())

        font = self.font()

        path = QtGui.QPainterPath()
        path.addText(0, 0, font, _SnakeEyesWidget._DisplayText)

        interfaceScale = app.Config.instance().interfaceScale()

        pen = QtGui.QPen()
        pen.setWidthF(_SnakeEyesWidget._TextOutlineWidth * interfaceScale)
        pen.setColor(QtCore.Qt.black)

        brush = QtGui.QBrush()
        brush.setStyle(QtCore.Qt.BrushStyle.SolidPattern)
        brush.setColor(QtCore.Qt.red)

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.translate(
            self.width() / 2,
            self.height() / 2)
        painter.rotate(textAngle)
        painter.translate(
            -self._textSize.width() / 2,
            self._textSize.height() / 4)
        painter.drawPath(path)
        painter.end()

    def resizeEvent(self, event: typing.Optional[QtGui.QResizeEvent]) -> None:
        super().resizeEvent(event)
        self._handleResize()

    def _handleResize(self) -> None:
        textAngle = self._calculateTextAngle()

        availableRect = self._calculateUsableRect()

        # Calculate the OBB for the required text at an arbitrary font size
        # given "infinite" space. The font size is unimportant as long as
        # it's big enough to render and small enough the size of 65535 is
        # big enough to render the text without wrapping or cropping
        font = self.font()
        font.setPixelSize(10)
        fontMetrics = QtGui.QFontMetrics(font)
        textRect = fontMetrics.boundingRect(
            QtCore.QRect(0, 0, 65535, 65535),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            _SnakeEyesWidget._DisplayText)

        cosTextAngle = math.cos(textAngle)
        sinTextAngle = math.sin(textAngle)

        # Calculate the x/y size of the AABB that contains the text OBB once
        # it's been rotated along with the ratio of how much of the width of the
        # box comes from the width of the text compared to the height of the
        # text and how much of the height of the box comes from the height of
        # the text compared to the width of the text.
        boxWidthFromTextWidth = abs(cosTextAngle * textRect.width())
        boxWidthFromTextHeight = abs(sinTextAngle * textRect.height())
        boxHeightFromTextHeight = abs(cosTextAngle * textRect.height())
        boxHeightFromTextWidth = abs(sinTextAngle * textRect.width())
        rotatedTextBounds = QtCore.QSizeF(
            boxWidthFromTextWidth + boxWidthFromTextHeight,
            boxHeightFromTextHeight + boxHeightFromTextWidth)
        textWidthRatio = boxWidthFromTextWidth / rotatedTextBounds.width()
        textHeightRatio = boxHeightFromTextHeight / rotatedTextBounds.height()

        # Calculate the value required to scale the text AABB so that it best
        # fits inside the available space while maintaining aspect ratio
        scale = min(availableRect.width() / rotatedTextBounds.width(),
                    availableRect.height() / rotatedTextBounds.height())

        # Calculate the size of the scaled text AABB
        rotatedTextBounds = QtCore.QSizeF(
            rotatedTextBounds.width() * scale,
            rotatedTextBounds.height() * scale)

        # Calculate the portions of the scaled text AABB width and height that
        # can be attributed to the width and height of the text OBB
        # can be attributed to the width and height of the rotated text
        # respectively
        boxWidthFromTextWidth = rotatedTextBounds.width() * textWidthRatio
        boxHeightFromTextHeight = rotatedTextBounds.height() * textHeightRatio

        # Calculate the width and heigh of the OBB that contains the scaled text
        scaledTextSize = QtCore.QSizeF(
            boxWidthFromTextWidth / cosTextAngle,
            boxHeightFromTextHeight / cosTextAngle)

        # Calculate the font size that will best fill the text rect
        font = gui.sizeFontToFit(
            orig=self.font(),
            text=_SnakeEyesWidget._DisplayText,
            rect=QtCore.QRect(
                0,
                0,
                math.floor(scaledTextSize.width()),
                math.floor(scaledTextSize.height())),
            align=QtCore.Qt.AlignmentFlag.AlignCenter)
        if font != None:
            self.setFont(font)

        # Get the size of the text when rendered with the selected font size
        fontMetrics = QtGui.QFontMetrics(self.font())
        textRect = fontMetrics.boundingRect(
            textRect,
            QtCore.Qt.AlignmentFlag.AlignCenter,
            _SnakeEyesWidget._DisplayText)
        self._textSize = textRect.size()

    def _calculateTextAngle(self) -> float:
        width = self.width()
        if width == 0:
            return 0
        height = self.height()
        return -math.atan(height / width)

    def _calculateUsableRect(self) -> QtCore.QRect:
        width = self.width()
        height = self.height()
        horzPadding = int(width * 0.1)
        vertPadding = int(height * 0.1)
        horzPadding = vertPadding = 0
        return QtCore.QRect(
            horzPadding,
            vertPadding,
            width - (horzPadding * 2),
            height - (vertPadding * 2))

    @staticmethod
    def _normaliseSize(size: typing.Union[QtCore.QSizeF, QtCore.QSize]) -> QtCore.QSizeF:
        length = math.sqrt((size.width() * size.width()) + (size.height() * size.height()))
        if length == 0:
            return QtCore.QSizeF(0, 0)
        return QtCore.QSizeF(size.width() / length, size.height() / length)

class DiceRollResultsWidget(QtWidgets.QWidget):
    rollComplete = QtCore.pyqtSignal()

    _DiceDisplayPercent = 70
    _RollDurationMs = 3000
    _FadeDurationMs = 400

    _StandardDieColour = QtGui.QColor('#003366')
    _FirstFluxDieColour = QtGui.QColor('#FFFFFF')
    _SecondFluxDieColour = QtGui.QColor('#FF0000')

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._results = None
        self._animations: typing.List[gui.DieAnimationWidget] = []
        self._pendingRollCount = 0
        self._labelsWidget = QtWidgets.QLabel(self)
        self._labelsWidget.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self._labelsWidget.hide()
        self._valuesWidget = QtWidgets.QLabel(self)
        self._valuesWidget.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self._valuesWidget.hide()
        self._snakeEyesWidget = _SnakeEyesWidget(self)
        self._snakeEyesWidget.hide()

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding)

    def setResults(
            self,
            results: typing.Optional[diceroller.DiceRollResult],
            animate: bool = True
            ) -> None:
        self._results = results
        if results != None:
            for animation in self._animations:
                animation.cancelSpin()

            dieCount = results.rollCount()
            fluxRolls = results.fluxRolls()
            if fluxRolls:
                dieCount += len(fluxRolls)

            while len(self._animations) > dieCount:
                animation = self._animations.pop()
                self._deleteAnimation(widget=animation)
            while len(self._animations) < dieCount:
                self._animations.append(self._createAnimation())

            animationConfig: typing.List[typing.Tuple[
                int, # Rolled value
                bool, # Ignored boon/bane roll
                int # Flux (0 = not flux, 1 = first flux, 2 = second flux)
            ]] = []
            for roll, ignored in results.rolls():
                animationConfig.append((roll, ignored, 0))
            if fluxRolls:
                for index, roll in enumerate(fluxRolls):
                    animationConfig.append((roll, False, index + 1))

            assert(len(self._animations) == dieCount)
            self._pendingRollCount = len(self._animations) if animate else 0
            for index, (roll, ignored, flux) in enumerate(animationConfig):
                animation = self._animations[index]
                animation.setDieType(results.dieType())

                if flux:
                    animation.setDieFillColour(
                        DiceRollResultsWidget._FirstFluxDieColour
                        if flux == 1 else
                        DiceRollResultsWidget._SecondFluxDieColour)
                else:
                    # Reset standard colour as animation may have
                    # previously been a flux die
                    animation.setDieFillColour(
                        DiceRollResultsWidget._StandardDieColour)

                if animate:
                    animation.startSpin(
                        result=roll,
                        strike=ignored)
                else:
                    animation.setValue(
                        result=roll,
                        strike=ignored)

            labelsText = ''
            valuesText = ''
            resultType = results.resultType()
            # Don't display any results text if the result is snake eyes as
            # it's all meaningless
            if resultType != diceroller.DiceRollResultType.SnakeEyesFailure:
                # NOTE: The odd way strings are formatted (with ': ' being part
                # of the value) is down to an issue I was seeing where something
                # in the Qt text rendering strips white space immediately before
                # a \n. This is a problem because it's needed as spacing between
                # the colon and the value. To work around this I've moved the
                # ': ' to the start of the value.
                labelsText = 'Rolled'
                valuesText = common.formatNumber(
                    number=results.rolledTotal(),
                    prefix=': ')

                if fluxRolls:
                    labelsText += '\nFlux'
                    valuesText += common.formatNumber(
                        number=results.fluxTotal(),
                        alwaysIncludeSign=True,
                        prefix='\n: ')

                if results.modifierCount() > 0:
                    labelsText += '\nModifiers'
                    valuesText += common.formatNumber(
                        number=results.modifiersTotal(),
                        alwaysIncludeSign=True,
                        prefix='\n: ')

                labelsText += '\nTotal'
                valuesText += common.formatNumber(
                    number=results.total(),
                    prefix='\n: ')

                if resultType != None:
                    labelsText += '\nResult'
                    valuesText += '\n: {result}'.format(
                        result=resultType.value)
                elif results.hasTarget():
                    labelsText += '\nTarget'
                    valuesText += '\n: {result}'.format(
                        result='Pass' if results.isSuccess() else 'Fail')

                effectValue = results.effectValue()
                if effectValue != None:
                    labelsText += '\nEffect'
                    valuesText += '\n: {effect}'.format(
                        effect=common.formatNumber(
                            number=effectValue,
                            alwaysIncludeSign=True),
                        effectType=resultType.value)

            self._labelsWidget.setText(labelsText)
            self._valuesWidget.setText(valuesText)

            if animate:
                self._labelsWidget.hide()
                self._valuesWidget.hide()
                self._snakeEyesWidget.hide()
            else:
                self._labelsWidget.show()
                self._valuesWidget.show()
                if results.isSnakeEyes():
                    self._snakeEyesWidget.show()
        else:
            for animation in self._animations:
                self._deleteAnimation(widget=animation)
            self._animations.clear()
            self._labelsWidget.setText('')
            self._valuesWidget.setText('')
            self._labelsWidget.hide()
            self._valuesWidget.hide()
            self._snakeEyesWidget.hide()

        self._layoutWidget()

    def skipAnimation(self) -> None:
        for animation in self._animations:
            animation.skipSpin()

    def resizeEvent(self, event: typing.Optional[QtGui.QResizeEvent]) -> None:
        super().resizeEvent(event)
        self._layoutWidget()

    def mouseDoubleClickEvent(self, event: typing.Optional[QtGui.QMouseEvent]) -> None:
        if event and self._pendingRollCount > 0:
            self.skipAnimation()
            event.accept()
            return

        return super().mouseDoubleClickEvent(event)

    def _createAnimation(self) -> gui.DieAnimationWidget:
        widget = gui.DieAnimationWidget(self)
        widget.setSpinDuration(durationMs=DiceRollResultsWidget._RollDurationMs)
        widget.setFadeDuration(durationMs=DiceRollResultsWidget._FadeDurationMs)
        widget.stackUnder(self._snakeEyesWidget)
        widget.animationComplete.connect(self._rollComplete)
        return widget

    def _deleteAnimation(
            self,
            widget: gui.DieAnimationWidget
            ) -> None:
        widget.animationComplete.disconnect(self._rollComplete)
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

        self._updateSnakeEyesLayout(
            availableWidth=availableWidth,
            availableHeight=usedHeight, # Should overlay dice layout
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
            ) -> int: # Used height
        if not availableWidth or not availableHeight:
            return 0 # No space used

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

    def _updateSnakeEyesLayout(
            self,
            availableWidth: int,
            availableHeight: int,
            offsetX: int,
            offsetY: int
            ) -> None:
        self._snakeEyesWidget.move(offsetX, offsetY)
        self._snakeEyesWidget.resize(availableWidth, availableHeight)

    def _updateTextLayout(
            self,
            availableWidth: int,
            availableHeight: int,
            offsetX: int,
            offsetY: int
            ) -> None:
        if availableWidth == 0 or availableHeight == 0:
            return

        defaultFont = self.font()

        fontMetrics = QtGui.QFontMetrics(defaultFont)
        testLabelRect = fontMetrics.boundingRect(
            QtCore.QRect(0, 0, 65535, 65535),
            int(self._labelsWidget.alignment()), # Convert Alignment object to flags
            self._labelsWidget.text())
        testValueRect = fontMetrics.boundingRect(
            QtCore.QRect(0, 0, 65535, 65535),
            int(self._valuesWidget.alignment()), # Convert Alignment object to flags
            self._valuesWidget.text())

        labelScale = valueScale = 0.5
        if testLabelRect.width() != 0 and testValueRect.width() != 0:
            testWidth = testLabelRect.width() + testValueRect.width()
            labelScale = testLabelRect.width() / testWidth
            valueScale = testValueRect.width() / testWidth

        labelAvailableRect = QtCore.QRect(
            0, 0, int(availableWidth * labelScale), availableHeight)
        labelFont = gui.sizeFontToFit(
            orig=defaultFont,
            text=self._labelsWidget.text(),
            rect=labelAvailableRect,
            align=self._labelsWidget.alignment())

        valueAvailableRect = QtCore.QRect(
            0, 0, int(availableWidth * valueScale), availableHeight)
        valueFont = gui.sizeFontToFit(
            orig=defaultFont,
            text=self._valuesWidget.text(),
            rect=valueAvailableRect,
            align=self._valuesWidget.alignment())

        if not labelFont or not valueFont:
            fallbackFont = QtGui.QFont(defaultFont)
            fallbackFont.setPixelSize(1)
            labelFont = valueFont = fallbackFont
        elif labelFont.pixelSize() > valueFont.pixelSize():
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
            int(self._labelsWidget.alignment()), # Convert Alignment object to flags
            self._labelsWidget.text())
        self._valuesWidget.move(
            offsetX + labelRect.width(),
            offsetY)

    def _rollComplete(self) -> None:
        assert(self._pendingRollCount > 0)
        self._pendingRollCount -= 1

        if self._pendingRollCount > 0:
            return

        # All the animations have completed
        self._labelsWidget.show()
        self._valuesWidget.show()

        if self._results != None and self._results.isSnakeEyes():
            self._snakeEyesWidget.show()

        self.rollComplete.emit()

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

        if not bestLayout:
            # The available area isn't big enough for the dice. This is
            # known to occur if width or height are 0. Position all dice
            # in a line with a size of 0
            return (1, dieCount, 0) if width < height else (dieCount, 1, 0)

        return (bestLayout[0], bestLayout[1], int(bestSize))
