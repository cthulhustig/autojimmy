import app
import common
import gui
import logging
import math
import re
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class TabWidgetEx(QtWidgets.QTabWidget):
    _StateVersion = 'TabWidgetEx_v1'

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        isMacOS = common.isMacOS()
        self.tabBar().setDocumentMode(not isMacOS)
        self.tabBar().setExpanding(not isMacOS)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(TabWidgetEx._StateVersion)
        stream.writeInt32(self.currentIndex())
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != TabWidgetEx._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore TabWidgetEx state (Incorrect version)')
            return False

        self.setCurrentIndex(stream.readInt32())
        return True

class ItemCountTabWidget(TabWidgetEx):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._itemCountMap: typing.Dict[QtWidgets.QWidget, int] = {}
        self._originalTextMap: typing.Dict[QtWidgets.QWidget, str] = {}

    def setTabItemCount(self, index: int, count: int) -> None:
        widget = self.widget(index)
        if not widget:
            return

        self._itemCountMap[widget] = count
        if widget not in self._originalTextMap:
            self._originalTextMap[widget] = self.tabText(index)

        # NOTE: Call base setTabText to avoid having the item count added twice
        super().setTabText(
            index,
            self._formatItemCountText(widget))

    def setWidgetItemCount(self, widget: QtWidgets.QWidget, count: int) -> None:
        index = self.indexOf(widget)
        if index >= 0:
            self.setTabItemCount(index, count)

    def removeTabItemCount(self, index: int) -> None:
        widget = self.widget(index)
        if not widget:
            return

        if widget in self._itemCountMap:
            del self._itemCountMap[widget]
        if widget in self._originalTextMap:
            # NOTE: Call base setTabText to avoid having the item count added twice
            super().setTabText(
                index,
                self._originalTextMap[widget])
            del self._originalTextMap[widget]

    def removeWidgetItemCount(self, widget: QtWidgets.QWidget) -> None:
        index = self.indexOf(widget)
        if index >= 0:
            self.removeTabItemCount(index)

    def setTabText(self, index: int, text: str) -> None:
        widget = self.widget(index)
        if widget in self._originalTextMap:
            self._originalTextMap[widget] = text
            text = self._formatItemCountText(widget)

        return super().setTabText(index, text)

    def tabText(self, index: int) -> str:
        widget = self.widget(index)
        if not widget:
            return ''

        origText = self._originalTextMap.get(widget)
        if origText != None:
            return origText

        return super().tabText(index)

    def removeTab(self, index: int) -> None:
        widget = self.widget(index)
        if widget in self._itemCountMap:
            del self._itemCountMap[widget]
        if widget in self._originalTextMap:
            del self._originalTextMap[widget]

        return super().removeTab(index)

    def clear(self):
        self._itemCountMap.clear()
        self._originalTextMap.clear()
        return super().clear()

    def _formatItemCountText(self, widget: QtWidgets.QWidget) -> str:
        itemCount = self._itemCountMap[widget]
        origText = self._originalTextMap[widget]
        return f'{origText} ({itemCount})'


class TabBarEx(QtWidgets.QTabBar):
    _StateVersion = 'TabBarEx_v1'

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        isMacOS = common.isMacOS()
        self.setDocumentMode(not isMacOS)
        self.setExpanding(not isMacOS)

    # Override paintEvent and clear widget background to window colour before calling base drawing
    # code. The base class doesn't do this so if the tab bar is drawn on top of another widget you
    # can see the other widget in the small gap caused by the fact the unselected tabs are a few
    # pixels shorter than the selected tab. This was causing issues when the tab bar was part of
    # the stack widget on the jump route window as you could see the Traveller Map widget through
    # this gap. This was caused by an interaction with another hack that's been put in place where
    # Traveller Map is forcibly shown when not selected to allow scripts to be run before the map
    # has been shown in the stack
    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        palette = self.palette()
        colour = palette.color(QtGui.QPalette.ColorRole.Window)
        size = self.size()
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QPen(colour, 1, QtCore.Qt.PenStyle.SolidLine))
        painter.setBrush(QtGui.QBrush(colour, QtCore.Qt.BrushStyle.SolidPattern))
        painter.drawRect(0, 0, size.width(), size.height())

        super().paintEvent(event)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(TabBarEx._StateVersion)
        stream.writeInt32(self.currentIndex())
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != TabBarEx._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore TabBarEx state (Incorrect version)')
            return False

        self.setCurrentIndex(stream.readInt32())
        return True

class CheckBoxEx(QtWidgets.QCheckBox):
    _StateVersion = 'CheckBoxEx_v1'

    def setTextOnLeft(self, enable: bool) -> None:
        self.setLayoutDirection(
            QtCore.Qt.LayoutDirection.RightToLeft
            if enable else
            QtCore.Qt.LayoutDirection.LeftToRight)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(CheckBoxEx._StateVersion)
        stream.writeBool(self.isChecked())
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != CheckBoxEx._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore CheckBoxEx state (Incorrect version)')
            return False

        self.setChecked(stream.readBool())
        return True

class ToolButtonEx(QtWidgets.QToolButton):
    # When replicating the sizing of a QPushButton the calculated size returned
    # by sizeFromContents is 1 pixel larger in height than the default QPushButton
    # sizeHint implementation. This modifier is applied to account for it.
    # Interestingly when I tried the same thing from a QPushButton derived class
    # sizeFromContents also returned a size 1 pixel larger than height than its
    # default sizeHint implementation generated so I'm not sure what is going on.
    _SizeHintHeightModifier = -1

    def __init__(
            self,
            text: typing.Optional[str] = None,
            isPushButton: bool = False,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._isPushButton = isPushButton
        self._disableMenuItem = False
        if text != None:
            self.setText(text)

    def isMenuIconDisabled(self) -> bool:
        return self._disableMenuItem

    def setDisableMenuIcon(self, disable: bool):
        self._disableMenuItem = disable
        self.update()

    # By default a QToolButton will appear significantly smaller than a
    # QPushButton with the same text due to the two controls using different
    # padding. This code modifies sizeHint to replicate the QPushButton sizing
    # behaviour.
    # https://forum.qt.io/topic/84657/qtoolbutton-as-big-as-qpushbutton/5
    def sizeHint(self) -> QtCore.QSize:
        baseHint = super().sizeHint()
        if not self._isPushButton:
            return baseHint

        btnOpt = QtWidgets.QStyleOptionToolButton()
        self.initStyleOption(btnOpt)
        h = max(0, btnOpt.iconSize.height())
        w = btnOpt.iconSize.width() + 4
        fntSize = self.fontMetrics().size(
            QtCore.Qt.TextFlag.TextShowMnemonic,
            btnOpt.text)
        w += fntSize.width()
        h = max(h, fntSize.height())

        opt = QtWidgets.QStyleOptionButton()
        opt.direction = btnOpt.direction
        opt.features = QtWidgets.QStyleOptionButton.ButtonFeature.None_
        if btnOpt.features & QtWidgets.QStyleOptionToolButton.ToolButtonFeature.Menu:
            opt.features |= QtWidgets.QStyleOptionButton.ButtonFeature.HasMenu
        opt.fontMetrics = btnOpt.fontMetrics
        opt.icon = btnOpt.icon
        opt.iconSize = btnOpt.iconSize
        opt.palette = btnOpt.palette
        opt.rect = btnOpt.rect
        opt.state = btnOpt.state
        opt.styleObject = btnOpt.styleObject
        opt.text = btnOpt.text
        pushSize = self.style().sizeFromContents(
            QtWidgets.QStyle.ContentsType.CT_PushButton,
            opt,
            QtCore.QSize(w, max(h + ToolButtonEx._SizeHintHeightModifier, 0)),
            self)
        return baseHint.expandedTo(pushSize)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        if not self._disableMenuItem:
            return super().paintEvent(event)
        option = QtWidgets.QStyleOptionToolButton()
        self.initStyleOption(option)

        option.features &= ~QtWidgets.QStyleOptionToolButton.ToolButtonFeature.HasMenu
        painter = QtWidgets.QStylePainter(self)
        painter.drawComplexControl(
            QtWidgets.QStyle.ComplexControl.CC_ToolButton,
            option)

class IconButton(QtWidgets.QPushButton):
    def __init__(
            self,
            icon: QtGui.QIcon,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self.setIcon(icon)

class RadioButtonEx(QtWidgets.QRadioButton):
    _StateVersion = 'RadioButtonEx_v1'

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(RadioButtonEx._StateVersion)
        stream.writeBool(self.isChecked())
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != RadioButtonEx._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore RadioButtonEx state (Incorrect version)')
            return False

        self.setChecked(stream.readBool())
        return True

class SpinBoxEx(QtWidgets.QSpinBox):
    _StateVersion = 'SpinBoxEx_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self._alwaysShowSign = False

    def alwaysShowSign(self) -> bool:
        return self._alwaysShowSign

    def enableAlwaysShowSign(self, enable: bool) -> None:
        self._alwaysShowSign = enable

    def textFromValue(self, value):
        if value >= 0 and self._alwaysShowSign:
            return f"+{value}"
        else:
            return f"{value}"

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(SpinBoxEx._StateVersion)
        stream.writeInt32(self.value())
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != SpinBoxEx._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore SpinBoxEx state (Incorrect version)')
            return False

        self.setValue(stream.readInt32())
        return True

class DoubleSpinBoxEx(QtWidgets.QDoubleSpinBox):
    _StateVersion = 'DoubleSpinBoxEx_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self._alwaysShowSign = False

    def alwaysShowSign(self) -> bool:
        return self._alwaysShowSign

    def enableAlwaysShowSign(self, enable: bool) -> None:
        self._alwaysShowSign = enable

    def textFromValue(self, value):
        if value >= 0 and self._alwaysShowSign:
            return f"+{value}"
        else:
            return f"{value}"

    # Set the number of decimal places to the minimum number needed to represent
    # the supplied value, with the number of decimal places clamped to the
    # supplied range before it is set.
    def setDecimalsForValue(
            self,
            value: float,
            minPrecision: int = 2,
            maxPrecision: int = 4
            ) -> None:
        if minPrecision > maxPrecision:
            minPrecision, maxPrecision = maxPrecision, minPrecision

        decimals = minPrecision
        while decimals <= maxPrecision:
            converted = float(common.formatNumber(
                number=value,
                decimalPlaces=decimals,
                thousandsSeparator=False))
            if math.isclose(value, converted):
                break
            decimals += 1
        self.setDecimals(decimals)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(DoubleSpinBoxEx._StateVersion)
        stream.writeDouble(self.value())
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != DoubleSpinBoxEx._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore DoubleSpinBoxEx state (Incorrect version)')
            return False

        self.setValue(stream.readDouble())
        return True

class _BaseOptionalSpinBox(QtWidgets.QWidget):
    valueChanged = QtCore.pyqtSignal(object) # Type depends on derived class

    _StateVersion = 'OptionalSpinBoxEx_v1'

    def __init__(
            self,
            spinBox: typing.Union[SpinBoxEx, DoubleSpinBoxEx],
            text: str = "",
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._uncheckedValue = None

        self._checkBox = CheckBoxEx(text)
        self._checkBox.stateChanged.connect(self._checkBoxChanged)

        self._spinBox = spinBox
        self._spinBox.setEnabled(self._checkBox.isChecked())
        self._spinBox.valueChanged.connect(self._spinBoxChanged)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._checkBox)
        layout.addWidget(self._spinBox)

        self.setLayout(layout)

    def isChecked(self) -> bool:
        return self._checkBox.isChecked()

    def setChecked(self, checked: bool) -> None:
        self._checkBox.setChecked(checked)

    def value(self) -> typing.Optional[typing.Union[int, float]]:
        return self._spinBox.value() if self._checkBox.isChecked() else self._uncheckedValue

    def setValue(self, value: typing.Optional[typing.Union[int, float]]) -> None:
        currentValue = self.value()
        if value == currentValue:
            return # Nothing to do

        with gui.SignalBlocker(widget=self._checkBox):
            self._checkBox.setChecked(value != None)

        with gui.SignalBlocker(widget=self._spinBox):
            if value != None:
                self._spinBox.setValue(value)
            self._spinBox.setEnabled(value != None)

        self._emitValueChanged()

    def uncheckedValue(self) -> typing.Optional[typing.Union[int, float]]:
        return self._uncheckedValue

    def setUncheckedValue(self, value: typing.Optional[typing.Union[int, float]]):
        if value == self._uncheckedValue:
            return
        self._uncheckedValue = value
        if not self.isChecked():
            self._emitValueChanged()

    def setRange(self, min: typing.Union[int, float], max: typing.Union[int, float]) -> None:
        self._spinBox.setRange(min, max)

    def setMaximum(self, max: typing.Union[int, float]) -> None:
        self._spinBox.setMaximum(max)

    def maximum(self) -> typing.Union[int, float]:
        return self._spinBox.maximum()

    def setMinimum(self, min: typing.Union[int, float]) -> None:
        self._spinBox.setMinimum(min)

    def minimum(self) -> typing.Union[int, float]:
        return self._spinBox.minimum()

    def setSingleStep(self, val: typing.Union[int, float]) -> None:
        self._spinBox.setSingleStep(val)

    def singleStep(self) -> typing.Union[int, float]:
        return self._spinBox.singleStep()

    def setSuffix(self, s: str) -> None:
        self._spinBox.setSuffix(s)

    def suffix(self) -> str:
        return self._spinBox.suffix()

    def setPrefix(self, p: str) -> None:
        self._spinBox.setPrefix(p)

    def prefix(self) -> str:
        return self._spinBox.prefix()

    def layoutDirection(self) -> QtCore.Qt.LayoutDirection:
        return self._checkBox.layoutDirection()

    def setLayoutDirection(self, direction: QtCore.Qt.LayoutDirection) -> None:
        self._checkBox.setLayoutDirection(direction)

    def setSpinBoxValue(self, value: int) -> None:
        self._spinBox.setValue(value)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(_BaseOptionalSpinBox._StateVersion)

        bytes = self._checkBox.saveState()
        stream.writeUInt32(bytes.count() if bytes else 0)
        if bytes:
            stream.writeRawData(bytes.data())

        bytes = self._spinBox.saveState()
        stream.writeUInt32(bytes.count() if bytes else 0)
        if bytes:
            stream.writeRawData(bytes.data())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != _BaseOptionalSpinBox._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore OptionalSpinBox state (Incorrect version)')
            return False

        # Block signals while restoring sub-widget states to prevent listeners connected
        # to this widgets valueChanged signal from seeing a partially updated state. A
        # manual valueChanged signal will be emitted after both sub-widgets have been
        # updated
        with gui.SignalBlocker(widget=self._checkBox):
            count = stream.readUInt32()
            if count:
                if not self._checkBox.restoreState(
                        QtCore.QByteArray(stream.readRawData(count))):
                    return False

        with gui.SignalBlocker(widget=self._spinBox):
            count = stream.readUInt32()
            if count:
                if not self._spinBox.restoreState(
                        QtCore.QByteArray(stream.readRawData(count))):
                    return False

        self._emitValueChanged()

        return True

    def _checkBoxChanged(self) -> None:
        self._spinBox.setEnabled(self.isChecked())
        self._emitValueChanged()

    def _spinBoxChanged(self) -> None:
        if self.isChecked():
            self._emitValueChanged()

    def _emitValueChanged(self) -> None:
        self.valueChanged.emit(self.value())

class OptionalSpinBox(_BaseOptionalSpinBox):
    def __init__(
            self,
            text: str = "",
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            text=text,
            spinBox=SpinBoxEx(),
            parent=parent)

    # The following overrides are pretty pointless. They're only there so intellisense
    # will only show the numeric type used by this derived instance rather than the
    # union of int & float that the base classes implementation takes
    def value(self) -> typing.Optional[int]:
        return super().value()

    def setValue(self, value: typing.Optional[int]) -> None:
        super().setValue(value)

    def uncheckedValue(self) -> typing.Optional[int]:
        return super().uncheckedValue()

    def setUncheckedValue(self, value: typing.Optional[int]):
        super().setUncheckedValue(value)

    def setRange(self, min: int, max: int) -> None:
        super().setRange(min, max)

    def setMaximum(self, max: int) -> None:
        super().setMaximum(max)

    def maximum(self) -> int:
        return super().maximum()

    def setMinimum(self, min: int) -> None:
        super().setMinimum(min)

    def minimum(self) -> int:
        return super().minimum()

class OptionalDoubleSpinBox(_BaseOptionalSpinBox):
    def __init__(
            self,
            text: str = "",
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            text=text,
            spinBox=DoubleSpinBoxEx(),
            parent=parent)

    def decimals(self) -> int:
        return self._spinBox.decimals()

    def setDecimals(self, decimals: int):
        self._spinBox.setDecimals(decimals)

    def setDecimalsForValue(
            self,
            value: float,
            minPrecision: int = 2,
            maxPrecision: int = 4
            ) -> None:
        return self._spinBox.setDecimalsForValue(
            value=value,
            minPrecision=minPrecision,
            maxPrecision=maxPrecision)

    # The following overrides are pretty pointless. They're only there so intellisense
    # will only show the numeric type used by this derived instance rather than the
    # union of int & float that the base classes implementation takes
    def value(self) -> typing.Optional[float]:
        return super().value()

    def setValue(self, value: typing.Optional[float]) -> None:
        super().setValue(value)

    def uncheckedValue(self) -> typing.Optional[float]:
        return super().uncheckedValue()

    def setUncheckedValue(self, value: typing.Optional[float]):
        super().setUncheckedValue(value)

    def setRange(self, min: float, max: float) -> None:
        super().setRange(min, max)

    def setMaximum(self, max: float) -> None:
        super().setMaximum(max)

    def maximum(self) -> float:
        return super().maximum()

    def setMinimum(self, min: float) -> None:
        super().setMinimum(min)

    def minimum(self) -> float:
        return super().minimum()

class TextEditEx(QtWidgets.QTextEdit):
    def isEmpty(self) -> bool:
        return self.document().isEmpty()

class LineEditEx(QtWidgets.QLineEdit):
    regexValidityChanged = QtCore.pyqtSignal(bool)
    delayedTextEdited = QtCore.pyqtSignal(str)

    _StateVersion = 'LineEditEx_v1'

    @typing.overload
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...
    @typing.overload
    def __init__(self, contents: str, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._regexCheckingEnabled = False
        self._regexPattern = None
        self._cachedBaseColour = None
        self._delayedTextEditedTimer = None

        # Always connect the signal, even though regex checking might not be enabled. This
        # is VERY important as signals are executed in the order they're connected and we
        # want regex checking to be performed before any external consumers are notified of
        # the text being changed (as they may check the regex validity in response to it)
        self.textChanged.connect(self._textChanged)

    def isEmpty(self) -> bool:
        return len(self.text()) <= 0

    def enableRegexChecking(self, enabled) -> bool:
        if enabled == self._regexCheckingEnabled:
            return # Nothing to do
        self._regexCheckingEnabled = enabled
        if self._regexCheckingEnabled:
            self._setupRegexChecking()
        else:
            self._teardownRegexChecking()

    def isRegexCheckingEnabled(self) -> bool:
        return self._regexCheckingEnabled

    def isValidRegex(self) -> bool:
        return self._regexPattern != None

    # Return compiled regex if regex checking is enabled
    def regex(self) -> typing.Optional[re.Pattern]:
        return self._regexPattern

    def setText(self, text: typing.Optional[str]) -> None:
        # The delayed edit timer is cancelled when the text is
        # programmatically set as this overrides any user edit
        # that may have taken place
        if self._delayedTextEditedTimer:
            self._delayedTextEditedTimer.stop()
        return super().setText(text)

    def enableDelayedTextEdited(
            self,
            msecs: int
            ) -> None:
        if not self._delayedTextEditedTimer:
            self._delayedTextEditedTimer = QtCore.QTimer()
            self._delayedTextEditedTimer.setSingleShot(True)
            self._delayedTextEditedTimer.timeout.connect(self._delayedTextEditedFired)
            self.textEdited.connect(self._primeDelayedTextEdited)
        self._delayedTextEditedTimer.setInterval(msecs)

    def disableDelayedTextEdited(self) -> None:
        if self._delayedTextEditedTimer:
            self._delayedTextEditedTimer.stop()
            del self._delayedTextEditedTimer
            self._delayedTextEditedTimer = None
        self.textEdited.disconnect(self._primeDelayedTextEdited)

    def setPalette(self, palette: QtGui.QPalette) -> None:
        if self._regexCheckingEnabled:
            self._cachedBaseColour = palette.color(QtGui.QPalette.ColorRole.Base)
        return super().setPalette(palette)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(LineEditEx._StateVersion)
        stream.writeQString(self.text())
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != LineEditEx._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore LineEditEx state (Incorrect version)')
            return False

        self.setText(stream.readQString())
        return True

    def _setupRegexChecking(self) -> None:
        self._cachedBaseColour = self.palette().color(QtGui.QPalette.ColorRole.Base)
        # Force sending a signal to allow consumers to perform setup based on the initial
        # validity state
        self._checkRegex(forceSignal=True)

    def _teardownRegexChecking(self) -> None:
        assert(self._cachedBaseColour != None)

        palette = self.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Base, self._cachedBaseColour)
        super().setPalette(palette) # Call base to prevent updating valid colour

        self._regexPattern = None
        self._cachedBaseColour = None

    def _textChanged(self, text: str) -> None:
        if self._regexCheckingEnabled:
            self._checkRegex()

    def _primeDelayedTextEdited(self) -> None:
        if self._delayedTextEditedTimer:
            self._delayedTextEditedTimer.start()

    def _delayedTextEditedFired(self) -> None:
        self.delayedTextEdited.emit(self.text())

    def _checkRegex(
            self,
            forceSignal: bool = False
            ) -> None:
        assert(self._regexCheckingEnabled)
        assert(self._cachedBaseColour != None)

        wasValid = self._regexPattern != None

        try:
            self._regexPattern = re.compile(self.text())
        except:
            self._regexPattern = None

        palette = self.palette()

        colour = self._cachedBaseColour
        if not self._regexPattern:
            colour = palette.color(QtGui.QPalette.ColorRole.BrightText)

        palette.setColor(QtGui.QPalette.ColorRole.Base, colour)
        super().setPalette(palette) # Call base to prevent updating valid colour

        isValid = self._regexPattern != None
        if (isValid != wasValid) or forceSignal:
            self.regexValidityChanged.emit(isValid)

class IntegerLineEdit(QtWidgets.QLineEdit):
    _StateVersion = 'IntegerLineEdit_v1'

    _HorizontalPadding = 10

    @typing.overload
    def __init__(self, minValue: int, maxValue: int, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...
    @typing.overload
    def __init__(self, minValue: int, maxValue: int, contents: str, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...

    def __init__(
            self,
            minValue: int,
            maxValue: int,
            *args,
            **kwargs
            ) -> None:
        super().__init__(*args, **kwargs)
        self.setValidator(QtGui.QIntValidator(minValue, maxValue))

        fm = QtGui.QFontMetrics(self.font())
        maxWidth = max(
            fm.boundingRect(str(minValue)).width(),
            fm.boundingRect(str(maxValue)).width())
        maxWidth += IntegerLineEdit._HorizontalPadding
        self.setFixedWidth(maxWidth)
        self.adjustSize()

    def number(self) -> int:
        return int(self.text())

    def setNumber(
            self,
            number: int
            ) -> None:
        self.setText(str(number))

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(IntegerLineEdit._StateVersion)
        stream.writeInt(self.number())
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != IntegerLineEdit._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore IntegerLineEdit state (Incorrect version)')
            return False

        self.setNumber(stream.readInt())
        return True

class FloatLineEdit(QtWidgets.QLineEdit):
    _StateVersion = 'FloatLineEdit_v1'

    _HorizontalPadding = 10

    @typing.overload
    def __init__(self, minValue: float, maxValue: float, decimals: int, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...
    @typing.overload
    def __init__(self, minValue: float, maxValue: float, decimals: int, contents: str, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...

    def __init__(
            self,
            minValue: float,
            maxValue: float,
            decimals: int,
            *args,
            **kwargs
            ) -> None:
        super().__init__(*args, **kwargs)
        self.setValidator(QtGui.QDoubleValidator(minValue, maxValue, decimals))
        self.setMaxLength((len(str(int(maxValue))) + decimals + 1))

        minString = int(minValue) + '.' + ('0' * decimals)
        maxString = int(maxValue) + '.' + ('0' * decimals)

        fm = QtGui.QFontMetrics(self.font())
        maxWidth = max(
            fm.boundingRect(minString).width(),
            fm.boundingRect(maxString).width())
        maxWidth += FloatLineEdit._HorizontalPadding
        self.setFixedWidth(maxWidth)
        self.adjustSize()

    def number(self) -> float:
        return float(self.text())

    def setNumber(
            self,
            number: float
            ) -> None:
        self.setText(str(number))

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(FloatLineEdit._StateVersion)
        stream.writeFloat(self.number())
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != FloatLineEdit._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore FloatLineEdit state (Incorrect version)')
            return False

        self.setNumber(stream.readFloat())
        return True

class ComboBoxEx(QtWidgets.QComboBox):
    userEdited = QtCore.pyqtSignal(str)
    delayedUserEdited = QtCore.pyqtSignal(str)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._delayedUserEditedTimer = None

    def enableDelayedUserEdited(
            self,
            msecs: int
            ) -> None:
        if not self._delayedUserEditedTimer:
            self._delayedUserEditedTimer = QtCore.QTimer()
            self._delayedUserEditedTimer.setSingleShot(True)
            self._delayedUserEditedTimer.timeout.connect(
                self._delayedUserEditedFired)

            # Subscribe to the combo box's activated even to get notification
            # when the user selects a new item from the drop down. Subscribe
            # to the line edit's textEdited event to get notification when the
            # user changes the text in an editable combo box.
            self.activated.connect(self._userEdited)
            lineEdit = self.lineEdit()
            if lineEdit:
                lineEdit.textEdited.connect(self._userEdited)
        self._delayedUserEditedTimer.setInterval(msecs)

    def disableDelayedUserEdited(self) -> None:
        if self._delayedUserEditedTimer:
            self._delayedUserEditedTimer.stop()
            del self._delayedUserEditedTimer
            self._delayedUserEditedTimer = None
        self.activated.disconnect(self._userEdited)
        lineEdit = self.lineEdit()
        if lineEdit:
            lineEdit.textEdited.disconnect(self._userEdited)

    def setEditable(
            self,
            editable: bool
            ) -> None:
        if self._delayedUserEditedTimer:
            lineEdit = self.lineEdit()
            if lineEdit:
                lineEdit.textEdited.disconnect(self._userEdited)

        super().setEditable(editable)

        if self._delayedUserEditedTimer:
            lineEdit = self.lineEdit()
            if lineEdit:
                lineEdit.textEdited.connect(self._userEdited)

    def setLineEdit(
            self,
            edit: QtWidgets.QLineEdit
            ) -> None:
        if self._delayedUserEditedTimer:
            lineEdit = self.lineEdit()
            if lineEdit:
                lineEdit.textEdited.disconnect(self._userEdited)

        super().setLineEdit(edit)

        if self._delayedUserEditedTimer:
            lineEdit = self.lineEdit()
            if lineEdit:
                lineEdit.textEdited.connect(self._userEdited)

    def addItemAlphabetically(
            self,
            text: str,
            userData: typing.Any = None
            ) -> None:
        for index in range(self.count()):
            otherText = self.itemText(index)
            if text < otherText:
                self.insertItem(index, text, userData)
                return
        self.addItem(text, userData)

    def userDataByIndex(
            self,
            index
            ) -> typing.Any:
        return self.itemData(index, QtCore.Qt.ItemDataRole.UserRole)

    def currentUserData(self) -> typing.Any:
        return self.currentData(QtCore.Qt.ItemDataRole.UserRole)

    def setCurrentByUserData(
            self,
            userData: typing.Any = None
            ) -> None:
        for index in range(self.count()):
            itemData = self.itemData(index, QtCore.Qt.ItemDataRole.UserRole)
            if userData == itemData:
                self.setCurrentIndex(index)
                return

    def setSelection(
            self,
            start: int,
            finish: int
            ) -> None:
        self.lineEdit().setSelection(start, finish)

    def selectAll(self) -> None:
        self.lineEdit().selectAll()

    def _userEdited(self) -> None:
        self.userEdited.emit(self.currentText())
        if self._delayedUserEditedTimer:
            self._delayedUserEditedTimer.start()

    def _delayedUserEditedFired(self) -> None:
        self.delayedUserEdited.emit(self.currentText())

class TableWidgetEx(QtWidgets.QTableWidget):
    _FocusRectStyle = 'QTableWidget:focus{{border:{width}px solid {colour};}}'
    _FocusRectRegex = re.compile(r'QTableWidget:focus\s*{.*?}')
    _FocusRectWidth = 4

    @typing.overload
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...
    @typing.overload
    def __init__(self, rows: int, columns: int, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...

    def __init__(
            self,
            *args,
            **kwargs
            ) -> None:
        super().__init__(*args, **kwargs)
        self._showFocusRect = False

    def showFocusRect(self) -> bool:
        return self._showFocusRect

    def setShowFocusRect(self, enabled: bool) -> None:
        self._showFocusRect = enabled
        styleSheet = TableWidgetEx._FocusRectRegex.sub(self.styleSheet(), '')
        styleSheet.strip()
        self.setStyleSheet(styleSheet)

    def setStyleSheet(self, styleSheet: str) -> None:
        if self._showFocusRect and not TableWidgetEx._FocusRectRegex.match(styleSheet):
            palette = self.palette()
            focusColour = palette.color(QtGui.QPalette.ColorRole.Highlight)
            if styleSheet:
                styleSheet += ' '

            interfaceScale = app.Config.instance().asFloat(
                option=app.ConfigOption.InterfaceScale)
            styleSheet += TableWidgetEx._FocusRectStyle.format(
                width=int(TableWidgetEx._FocusRectWidth * interfaceScale),
                colour=gui.colourToString(focusColour, includeAlpha=False))
        super().setStyleSheet(styleSheet)

    def contentToHtml(self) -> str:
        horzHeader = self.horizontalHeader()
        vertHeader = self.verticalHeader()
        hasHorzHeader = horzHeader and not horzHeader.isHidden()
        hasVertHeader = vertHeader and not vertHeader.isHidden()
        model = self.model()

        content = '<html>\n'
        content += '<head>\n'
        content += '<style>\n'
        content += 'table, th, td {\n'
        content += 'border: 1px solid black;\n'
        content += 'border-collapse: collapse;\n'
        content += '}\n'
        content += 'th, td {\n'
        content += 'padding: 2px;\n'
        content += '}\n'
        content += '</style>\n'
        content += '</head>\n'
        content += '<body>\n'
        content += '<table style="border: 1px solid black; border-collapse: collapse;">\n'

        if hasHorzHeader:
            content += '<tr>\n'
            for column in range(model.columnCount()):
                if self.isColumnHidden(column):
                    continue

                tableHeader = TableWidgetEx._formatTableHeader(
                    model=model,
                    index=column,
                    orientation=QtCore.Qt.Orientation.Horizontal)
                content += f'{tableHeader}\n'
            content += '</tr>\n'

        rowSpans = [0] * self.columnCount()
        row = 0
        while row < self.rowCount():
            rowHidden = self.isRowHidden(row)
            column = 0

            if not rowHidden:
                content += '<tr>\n'

            if hasVertHeader and not rowHidden:
                tableHeader = TableWidgetEx._formatTableHeader(
                    model=model,
                    index=column,
                    orientation=QtCore.Qt.Orientation.Vertical)
                content += f'{tableHeader}\n'

            while column < self.columnCount():
                rowSpan = rowSpans[column]
                if rowSpan > 0:
                    rowSpans[column] = rowSpan - 1
                    continue

                columnSpan = self.columnSpan(row, column)
                assert(columnSpan > 0)
                rowSpan = self.rowSpan(row, column)
                assert(rowSpan > 0)
                if not rowHidden and not self.isColumnHidden(column):
                    item = self.item(row, column)
                    itemText = item.text() if item else ''
                    itemAlignment = item.textAlignment() if item else None
                    itemFont = item.font() if item else None

                    itemText = gui.textToHtmlContent(text=itemText, font=itemFont)
                    itemAlignment = gui.alignmentToHtmlStyle(alignment=itemAlignment)

                    content += '<td{style}{columnSpan}{rowSpan}>{itemText}</td>\n'.format(
                        style=f' style="{itemAlignment}"' if itemAlignment else '',
                        columnSpan=f' colspan="{columnSpan}"' if columnSpan > 1 else '',
                        rowSpan=f' rowspan="{rowSpan}"' if rowSpan > 1 else '',
                        itemText=itemText)

                if rowSpan > 1:
                    columnSpanEnd = column + columnSpan
                    while column < columnSpanEnd:
                        rowSpans[column] = rowSpan - 1
                        column += 1
                else:
                    column += columnSpan

            if not rowHidden:
                content += '</tr>\n'
            row += 1

        content += '</table>\n'
        content += '</body>\n'
        content += '</html>\n'

        return content

    @staticmethod
    def _formatTableHeader(
            model: QtCore.QAbstractItemModel,
            index: int,
            orientation: QtCore.Qt.Orientation
            ) -> str:
        headerText = model.headerData(
            index,
            orientation,
            QtCore.Qt.ItemDataRole.DisplayRole)
        headerAlignment = model.headerData(
            index,
            orientation,
            QtCore.Qt.ItemDataRole.TextAlignmentRole)
        headerFont = model.headerData(
            index,
            orientation,
            QtCore.Qt.ItemDataRole.FontRole)

        headerText = gui.textToHtmlContent(text=headerText, font=headerFont)
        headerAlignment = gui.alignmentToHtmlStyle(alignment=headerAlignment)

        return '<th{style}>{headerText}</th>\n'.format(
            style=f' style="{headerAlignment}"' if headerAlignment else '',
            headerText=headerText)

class TreeWidgetEx(QtWidgets.QTreeWidget):
    # https://stackoverflow.com/questions/20203443/right-align-a-button-in-a-qtreeview-column
    def setAlignedIndexWidget(
            self,
            index: QtCore.QModelIndex,
            widget: typing.Optional[QtWidgets.QWidget],
            align=QtCore.Qt.AlignmentFlag.AlignLeft
            ) -> None:
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(align)
        layout.addWidget(widget)
        self.setIndexWidget(index, container)

    def setAlignedItemWidget(
            self,
            item: QtWidgets.QTreeWidgetItem,
            column: int,
            widget: typing.Optional[QtWidgets.QWidget],
            align=QtCore.Qt.AlignmentFlag.AlignLeft
            ) -> None:
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(align)
        layout.addWidget(widget)
        self.setItemWidget(item, column, container)

class ScrollAreaEx(QtWidgets.QScrollArea):
    _StateVersion = 'ScrollAreaEx_v1'

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(ScrollAreaEx._StateVersion)

        scrollBar = self.horizontalScrollBar()
        stream.writeInt(scrollBar.value() if scrollBar else 0)

        scrollBar = self.verticalScrollBar()
        stream.writeInt(scrollBar.value() if scrollBar else 0)

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != ScrollAreaEx._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore ScrollAreaEx state (Incorrect version)')
            return False

        scrollBar = self.horizontalScrollBar()
        if scrollBar:
            scrollBar.setValue(stream.readInt())

        scrollBar = self.verticalScrollBar()
        if scrollBar:
            scrollBar.setValue(stream.readInt())

        return True

class HorizontalSeparator(QtWidgets.QFrame):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed)

class VerticalSeparator(QtWidgets.QFrame):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        self.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Expanding)

# NOTE: This intentionally doesn't inherit from ScrollAreaEx as it
# doesn't make logical sense to save scrollbar state for an auto
# scrolling widget.
class AutoScrollArea(QtWidgets.QScrollArea):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._autoScroll = False
        self._shouldAutoScrollVertically = False
        self._shouldAutoScrollHorizontally = False

        scrollBar = self.verticalScrollBar()
        if scrollBar:
            scrollBar.valueChanged.connect(self._verticalScrollBarValueChanged)
            scrollBar.rangeChanged.connect(self._verticalScrollBarRangeChanged)

        scrollBar = self.horizontalScrollBar()
        if scrollBar:
            scrollBar.valueChanged.connect(self._horizontalScrollBarValueChanged)
            scrollBar.rangeChanged.connect(self._horizontalScrollBarRangeChanged)

    def autoScroll(self) -> bool:
        return self._autoScroll

    def setAutoScroll(self, enable: bool) -> None:
        if self._autoScroll == enable:
            return # Nothing to do
        self._autoScroll = enable
        self._shouldAutoScrollVertically = False
        self._shouldAutoScrollHorizontally = False

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super().resizeEvent(a0)

        self._shouldAutoScrollVertically = self._autoScrollCheck(
            scrollBar=self.verticalScrollBar())
        self._shouldAutoScrollHorizontally = self._autoScrollCheck(
            scrollBar=self.horizontalScrollBar())

    def _verticalScrollBarValueChanged(self, value: int) -> None:
        if not self._autoScroll:
            return
        self._shouldAutoScrollVertically = self._autoScrollCheck(
            scrollBar=self.verticalScrollBar())

    def _verticalScrollBarRangeChanged(self, min: int, max: int) -> None:
        if not self._autoScroll or not self._shouldAutoScrollVertically:
            return

        scrollBar = self.verticalScrollBar()
        scrollBar.setValue(scrollBar.maximum())

    def _horizontalScrollBarValueChanged(self, value: int) -> None:
        if not self._autoScroll:
            return
        self._shouldAutoScrollVertically = self._autoScrollCheck(
            scrollBar=self.horizontalScrollBar())

    def _horizontalScrollBarRangeChanged(self, min: int, max: int) -> None:
        if not self._autoScroll or not self._shouldAutoScrollHorizontally:
            return

        scrollBar = self.horizontalScrollBar()
        scrollBar.setValue(scrollBar.maximum())

    def _autoScrollCheck(
            self,
            scrollBar: QtWidgets.QScrollBar
            ) -> bool:
        if not scrollBar:
            return False
        return scrollBar.value() == scrollBar.maximum()

class NaturalSortListWidgetItem(QtWidgets.QListWidgetItem):
    def __lt__(self, other: QtWidgets.QListWidgetItem) -> bool:
        try:
            lhs = common.naturalSortKey(string=self.text())
            rhs = common.naturalSortKey(string=other.text())
            return lhs < rhs
        except Exception:
            return super().__lt__(other)

class NaturalSortTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    def __lt__(self, other: QtWidgets.QTreeWidgetItem) -> bool:
        try:
            lhs = common.naturalSortKey(string=self.text())
            rhs = common.naturalSortKey(string=other.text())
            return lhs < rhs
        except Exception:
            return super().__lt__(other)

class ListWidgetEx(QtWidgets.QListWidget):
    def isEmpty(self) -> bool:
        return self.count() <= 0

    def removeRow(self, row: int) -> None:
        self.takeItem(row)

    def hasCurrentItem(self) -> bool:
        return self.currentItem() != None

    def hasSelection(self) -> bool:
        return self.selectionModel().hasSelection()

    def selectionCount(self) -> int:
        count = 0
        for row in range(self.count()):
            item = self.item(row)
            if not item:
                continue
            if item.isSelected():
                count += 1
        return count

    def itemFromWidget(
            self,
            widget: QtWidgets.QWidget
            ) -> typing.Optional[QtWidgets.QListWidgetItem]:
        for item in self.items():
            itemWidget = self.itemWidget(item)
            if itemWidget == widget:
                return item
        return None

class VBoxLayoutEx(QtWidgets.QVBoxLayout):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, parent: QtWidgets.QWidget) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._labelledObjectLayoutMap: typing.Dict[typing.Union[QtWidgets.QWidget, QtWidgets.QLayout], QtWidgets.QWidget] = {}

    def addLabelledLayout(
            self,
            label: str,
            layout: QtWidgets.QLayout,
            stretch: int = 0,
            labelAlignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignRight
            ) -> None:
        self._insertLabelledObject(
            index=self.count(),
            object=layout,
            label=label,
            stretch=stretch,
            labelAlignment=labelAlignment)

    def addLabelledWidget(
            self,
            label: str,
            widget: QtWidgets.QWidget,
            stretch: int = 0,
            widgetAlignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0),
            labelAlignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignRight
            ) -> None:
        self._insertLabelledObject(
            index=self.count(),
            object=widget,
            label=label,
            stretch=stretch,
            objectAlignment=widgetAlignment,
            labelAlignment=labelAlignment)

    def insertLabelledLayout(
            self,
            index: int,
            label: str,
            layout: QtWidgets.QLayout,
            stretch: int = 0,
            labelAlignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignRight
            ) -> None:
        self._insertLabelledObject(
            index=index,
            object=layout,
            label=label,
            stretch=stretch,
            labelAlignment=labelAlignment)

    def insertLabelledWidget(
            self,
            index: int,
            label: str,
            widget: QtWidgets.QWidget,
            stretch: int = 0,
            widgetAlignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0),
            labelAlignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignRight
            ) -> None:
        self._insertLabelledObject(
            index=index,
            object=widget,
            label=label,
            stretch=stretch,
            objectAlignment=widgetAlignment,
            labelAlignment=labelAlignment)

    def removeWidget(self, widget: QtWidgets.QWidget) -> None:
        wrapper = self._labelledObjectLayoutMap.get(widget)
        if wrapper:
            widget = wrapper

        super().removeWidget(widget)

        if wrapper:
            wrapper.setParent(None)
            wrapper.setHidden(True)
            wrapper.deleteLater()

    def _insertLabelledObject(
            self,
            index: int,
            object: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            label: str,
            stretch: int,
            objectAlignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0),
            labelAlignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignRight
            ) -> None:
        # When adding this wrapper layout a stretch isn't added. Instead the alignment should be
        # used. I've done this as I was finding the stretch meant line edits that were set to
        # expand to use as much space as is available weren't doing so.
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        label = QtWidgets.QLabel(label)
        label.setAlignment(labelAlignment)
        layout.addWidget(label)
        if isinstance(object, QtWidgets.QWidget):
            layout.addWidget(object)
        elif isinstance(object, QtWidgets.QLayout):
            layout.addLayout(object)
        else:
            raise TypeError("Labelled object must be a QWidget or QLayout")

        widget = QtWidgets.QWidget()
        widget.setLayout(layout)

        super().insertWidget(index, widget, stretch, objectAlignment)
        self._labelledObjectLayoutMap[object] = widget

# Implementation of a TextEdit that automatically resizes to fit its contents
# https://stackoverflow.com/questions/47710329/how-to-adjust-qtextedit-to-fit-its-contents
class ContentSizedTextEdit(TextEditEx):
    @typing.overload
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...
    @typing.overload
    def __init__(self, text: str, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        self.document().contentsChanged.connect(self._contentChanged)

    def sizeHint(self) -> QtCore.QSize:
        docSize = self.document().size().toSize()
        margins = self.contentsMargins()
        return QtCore.QSize(
            docSize.width() + margins.left() + margins.right(),
            docSize.height() + margins.top() + margins.bottom())

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        # If the widget has been resized then the size hint will also have changed.
        # Call updateGeometry to make sure any layouts are notified of the change.
        self.updateGeometry()
        return super().resizeEvent(a0)

    def _contentChanged(self):
        # Force an update of the layout if the content changes
        self.updateGeometry()

class ContentSizedTextBrowser(QtWidgets.QTextBrowser):
    @typing.overload
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...
    @typing.overload
    def __init__(self, text: str, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        self.document().contentsChanged.connect(self._contentChanged)

    def sizeHint(self) -> QtCore.QSize:
        docSize = self.document().size().toSize()
        margins = self.contentsMargins()
        return QtCore.QSize(
            docSize.width() + margins.left() + margins.right(),
            docSize.height() + margins.top() + margins.bottom())

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        # If the widget has been resized then the size hint will also have changed.
        # Call updateGeometry to make sure any layouts are notified of the change.
        self.updateGeometry()
        return super().resizeEvent(a0)

    def _contentChanged(self):
        # Force an update of the layout if the content changes
        self.updateGeometry()

# https://lists.qt-project.org/pipermail/qt-interest-old/2010-May/022744.html
class ContentSizedLineEdit(LineEditEx):
    # For reasons I don't understand, when calculating the content width, the margins
    # are always reported as 0 even though there is clearly spacing between the text
    # and the edge of the widget. Through trial and error it looks like there is an
    # additional 4 pixels of padding on each side (at least on Windows)
    _ContentWidthPaddingHack = 8

    @typing.overload
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...
    @typing.overload
    def __init__(self, contents: str, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.textChanged.connect(self._textChanged)

    def sizeHint(self) -> QtCore.QSize:
        hint = super().sizeHint()
        hint.setWidth(self._calculateContentWidth())
        return hint

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        # If the widget has been resized then the size hint will also have changed.
        # Call updateGeometry to make sure any layouts are notified of the change.
        self.updateGeometry()
        return super().resizeEvent(a0)

    def _textChanged(self):
        # Force an update of the layout if the content changes
        self.updateGeometry()

    def _calculateContentWidth(self) -> int:
        text = self.text()
        margins = self.textMargins()
        fontMetrics = self.fontMetrics()
        width = fontMetrics.boundingRect(text).width() + margins.left() + margins.right() + ContentSizedLineEdit._ContentWidthPaddingHack
        return width

class ResizingListWidget(ListWidgetEx):
    @typing.overload
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...
    @typing.overload
    def __init__(self, text: str, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Minimum)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def sizeHint(self) -> QtCore.QSize:
        sizeHint = super().sizeHint()

        height = 0
        for row in range(self.count()):
            item = self.item(row)
            index = self.indexFromItem(item)
            rect = self.rectForIndex(index)
            height += rect.height()

        contentMargin = self.contentsMargins()
        sizeHint.setHeight(height + contentMargin.top() + contentMargin.bottom())

        return sizeHint

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        # If the widget has been resized then the size hint will also have changed.
        # Call updateGeometry to make sure any layouts are notified of the change.
        self.updateGeometry()
        return super().resizeEvent(a0)

class ProgressDialogEx(QtWidgets.QProgressDialog):
    @typing.overload
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = ..., flags: QtCore.Qt.WindowType = ...) -> None: ...
    @typing.overload
    def __init__(self, labelText: str, cancelButtonText: str, minimum: int, maximum: int, parent: typing.Optional[QtWidgets.QWidget] = ..., flags: QtCore.Qt.WindowType = ...) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        gui.configureWindowTitleBar(widget=self)

class LayoutWrapperWidget(QtWidgets.QWidget):
    def __init__(self, layout, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setLayout(layout)

class GroupBoxEx(QtWidgets.QGroupBox):
    @typing.overload
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...
    @typing.overload
    def __init__(self, title: typing.Optional[str], parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._menuButton = QtWidgets.QToolButton(self)
        self._menuButton.setStyleSheet('QToolButton { border: none; }')
        self._menuButton.setArrowType(QtCore.Qt.ArrowType.DownArrow)
        self._menuButton.setHidden(True)
        self._menuButton.clicked.connect(self._menuRequested)

        self._updateMenuButtonPosition()

    def enableMenuButton(self, enabled: bool) -> None:
        self._menuButton.setHidden(not enabled)

    def setMenuButtonToolTip(self, text: str) -> None:
        self._menuButton.setToolTip(text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._updateMenuButtonPosition()

    def _updateMenuButtonPosition(self) -> None:
        fontMetrics = QtGui.QFontMetrics(self.font())
        titleHeight = fontMetrics.height()
        titleWidth = fontMetrics.width(self.title())

        style = self.style()
        topPadding = style.pixelMetric(
            QtWidgets.QStyle.PixelMetric.PM_LayoutTopMargin,
            None,
            self) // 2

        iconSize = titleHeight + topPadding
        self._menuButton.setFixedSize(iconSize, iconSize)
        self._menuButton.move(titleWidth, 0)

    def _menuRequested(self) -> None:
        actions = self.actions()
        if not actions:
            return

        menu = QtWidgets.QMenu(self)
        for action in actions:
            menu.addAction(action)
        menu.exec(QtGui.QCursor.pos())

class ActionEx(QtWidgets.QAction):
    _StateVersion = 'ActionEx_v1'

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(ActionEx._StateVersion)
        stream.writeBool(self.isChecked())
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != ActionEx._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore ActionEx state (Incorrect version)')
            return False

        self.setChecked(stream.readBool())
        return True

class WidgetActionEx(QtWidgets.QWidgetAction):
    def __init__(self,
                 text: typing.Optional[str] = None,
                 parent: typing.Optional[QtWidgets.QWidget] = None
                 ) -> None:
        super().__init__(parent)
        if text != None:
            self.setText(text)
