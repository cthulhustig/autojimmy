import common
import gui
import logging
import math
import re
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class FormLayoutEx(QtWidgets.QFormLayout):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)

    def labelAt(self, row: int) -> typing.Optional[QtWidgets.QLabel]:
        item = self.itemAt(row, gui.FormLayoutEx.ItemRole.LabelRole)
        return item.widget() if item else None

    def fieldAt(self, row: int) -> typing.Optional[typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]]:
        item = self.itemAt(row, gui.FormLayoutEx.ItemRole.FieldRole)
        if item:
            if item.widget():
                return item.widget()
            if item.layout():
                return item.layout()
        return None

    def widgetAt(self, row: int) -> typing.Optional[QtWidgets.QWidget]:
        item = self.itemAt(row, gui.FormLayoutEx.ItemRole.FieldRole)
        return item.widget() if item else None

    def layoutAt(self, row: int) -> typing.Optional[QtWidgets.QLayout]:
        item = self.itemAt(row, gui.FormLayoutEx.ItemRole.FieldRole)
        return item.layout() if item else None

    def clear(self) -> None:
        while self.rowCount() > 0:
            self.removeRow(self.rowCount() - 1)

    def setLabelText(
            self,
            row: int,
            text: str
            ) -> None:
        label = self.labelAt(row)
        if label:
            label.setText(text)

    def setRowHidden(
            self,
            row: int,
            hidden: bool
            ) -> None:
        rowItems = [
            self.itemAt(row, FormLayoutEx.ItemRole.LabelRole),
            self.itemAt(row, FormLayoutEx.ItemRole.FieldRole)
        ]

        for item in rowItems:
            if not item:
                continue

            widget = item.widget()
            widget.setHidden(hidden)

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

class RadioButtonEx(QtWidgets.QRadioButton):
    _StateVersion = 'RadioButtonEx_v1'

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
            logging.debug(f'Failed to restore RadioButtonEx state (Incorrect version)')
            return False

        self.setChecked(stream.readBool())
        return True

class SpinBoxEx(QtWidgets.QSpinBox):
    _StateVersion = 'SpinBoxEx_v1'

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

    # Update the number of decimal places the spin box allows so they accommodate
    # the max and min values
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
        stream.writeQString(SpinBoxEx._StateVersion)
        stream.writeDouble(self.value())
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != SpinBoxEx._StateVersion:
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
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._checkBox = CheckBoxEx()
        self._checkBox.stateChanged.connect(self._checkBoxChanged)

        self._spinBox = spinBox
        self._spinBox.setEnabled(self._checkBox.isChecked())
        self._spinBox.valueChanged.connect(self._spinBoxChanged)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._checkBox)
        layout.addWidget(self._spinBox)

        self.setLayout(layout)

    def value(self) -> typing.Optional[typing.Union[int, float]]:
        return self._spinBox.value() if self._checkBox.isChecked() else None

    def setValue(self, value: typing.Optional[typing.Union[int, float]]) -> None:
        if value != None:
            # Order is important here to prevent double notifications without disabling signals.
            # The spin box is updated first, this will only trigger this classes valueChanged event
            # if the check box is currently ticked and the value has changed. The check box is then
            # checked if it's not already, this will cause this classes valueChanged event to be
            # triggered if the spin widget is going from disabled to enabled (regardless of if the
            # value stored in the spin box has actually changed)
            self._spinBox.setValue(value)

            if not self._checkBox.isChecked():
                self._checkBox.setChecked(False)
        else:
            if self._checkBox.isChecked():
                self._checkBox.setChecked(False)

    def isEnabled(self) -> bool:
        return self._checkBox.isChecked()

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
        self._spinBox.setEnabled(self.isEnabled())
        self._emitValueChanged()

    def _spinBoxChanged(self) -> None:
        if self.isEnabled():
            self._emitValueChanged()

    def _emitValueChanged(self) -> None:
        self.valueChanged.emit(self.value())

class OptionalSpinBox(_BaseOptionalSpinBox):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            spinBox=SpinBoxEx(),
            parent=parent)

    # The following overrides are pretty pointless. They're only there so intellisense
    # will only show the numeric type used by this derived instance rather than the
    # union of int & float that the base classes implementation takes
    def value(self) -> typing.Optional[int]:
        return super().value()

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
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
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

    _darkModeInvalidRegexHighlight = QtGui.QColor(100, 0, 0)

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

        colour = self._cachedBaseColour
        if not self._regexPattern:
            colour = self._darkModeInvalidRegexHighlight if gui.isDarkModeEnabled() else QtCore.Qt.GlobalColor.red

        palette = self.palette()
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

class ScrollAreaEx(QtWidgets.QScrollArea):
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
            stretch: int = 0
            ) -> None:
        self._insertLabelledObject(
            index=self.count(),
            object=layout,
            label=label,
            stretch=stretch)

    def addLabelledWidget(
            self,
            label: str,
            widget: QtWidgets.QWidget,
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> None:
        self._insertLabelledObject(
            index=self.count(),
            object=widget,
            label=label,
            stretch=stretch,
            alignment=alignment)

    def insertLabelledLayout(
            self,
            index: int,
            label: str,
            layout: QtWidgets.QLayout,
            stretch: int = 0
            ) -> None:
        self._insertLabelledObject(
            index=index,
            object=layout,
            label=label,
            stretch=stretch)

    def insertLabelledWidget(
            self,
            index: int,
            label: str,
            widget: QtWidgets.QWidget,
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> None:
        self._insertLabelledObject(
            index=index,
            object=widget,
            label=label,
            stretch=stretch,
            alignment=alignment)

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
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> None:
        # When adding this wrapper layout a stretch isn't added. Instead the alignment should be
        # used. I've done this as I was finding the stretch meant line edits that were set to
        # expand to use as much space as is available weren't doing so.
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QtWidgets.QLabel(label))
        if isinstance(object, QtWidgets.QWidget):
            layout.addWidget(object)
        elif isinstance(object, QtWidgets.QLayout):
            layout.addLayout(object)
        else:
            raise TypeError("Labelled object must be a QWidget or QLayout")

        widget = QtWidgets.QWidget()
        widget.setLayout(layout)

        super().insertWidget(index, widget, stretch, alignment)
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
