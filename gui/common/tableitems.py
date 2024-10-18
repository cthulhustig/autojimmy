import common
import typing
from PyQt5 import QtWidgets, QtCore

class TableWidgetItemEx(QtWidgets.QTableWidgetItem):
    def setBold(self, enable: bool = True) -> None:
        font = self.font()
        font.setBold(enable)
        self.setFont(font)

    def setStrikeOut(self, enable: bool = True) -> None:
        font = self.font()
        font.setStrikeOut(enable)
        self.setFont(font)

class FormattedNumberTableWidgetItem(TableWidgetItemEx):
    def __init__(
            self,
            value: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            thousandsSeparator: bool = True,
            alwaysIncludeSign: bool = False,
            decimalPlaces: int = 2, # Only applies for float values
            removeTrailingZeros: bool = True, # Only applies for float values,
            prefix: str = '',
            infix: str = '', # Infix (my own term) goes before number but after any sign
            suffix: str = '',
            other: typing.Optional['FormattedNumberTableWidgetItem'] = None
            ) -> None:
        super().__init__(other)
        self.setTextAlignment(int(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter))
        self.setConfig(
            value=other._value if other else value,
            thousandsSeparator=other._thousandsSeparator if other else thousandsSeparator,
            alwaysIncludeSign=other._alwaysIncludeSign if other else alwaysIncludeSign,
            decimalPlaces=other._decimalPlaces if other else decimalPlaces,
            removeTrailingZeros=other._removeTrailingZeros if other else removeTrailingZeros,
            prefix=other._prefix if other else prefix,
            infix=other._infix if other else infix,
            suffix=other._suffix if other else suffix)

    def value(self) -> None:
        return self._value

    def numericValue(self) -> typing.Union[int, float]:
        if self._value == None:
            return None

        if isinstance(self._value, common.ScalarCalculation):
            return self._value.value()

        return self._value

    def setValue(
            self,
            value: typing.Optional[typing.Union[int, float, common.ScalarCalculation]]
            ) -> None:
        numericValue = None
        if value != None:
            if isinstance(value, common.ScalarCalculation):
                # Convert calculations to their raw value for easier displaying
                numericValue = value.value()
            else:
                assert(isinstance(value, int) or isinstance(value, float))
                numericValue = value
        self._value = value

        stringValue = ''
        if numericValue != None:
            stringValue = common.formatNumber(
                number=numericValue,
                thousandsSeparator=self._thousandsSeparator,
                alwaysIncludeSign=self._alwaysIncludeSign,
                decimalPlaces=self._decimalPlaces,
                removeTrailingZeros=self._removeTrailingZeros,
                prefix=self._prefix,
                infix=self._infix,
                suffix=self._suffix,
                infinityString='∞')
        self.setText(stringValue)

    def setConfig(
            self,
            value: typing.Optional[typing.Union[int, float, common.ScalarCalculation]],
            thousandsSeparator: bool = True,
            alwaysIncludeSign: bool = False,
            decimalPlaces: int = 2, # Only applies for float values
            removeTrailingZeros: bool = True, # Only applies for float values
            prefix: str = '',
            infix: str = '', # Infix (my own term) goes before number but after any sign
            suffix: str = '',
            ) -> None:
        self._thousandsSeparator = thousandsSeparator
        self._alwaysIncludeSign = alwaysIncludeSign
        self._decimalPlaces = decimalPlaces
        self._removeTrailingZeros = removeTrailingZeros
        self._prefix = prefix
        self._infix = infix
        self._suffix = suffix
        self.setValue(value=value)

    def clone(self) -> 'FormattedNumberTableWidgetItem':
        return FormattedNumberTableWidgetItem(other=self)

    def __lt__(
            self,
            other: 'FormattedNumberTableWidgetItem'
            ) -> bool:
        selfValue = self.numericValue()
        otherValue = other.numericValue()
        if selfValue != None and otherValue != None:
            return selfValue < otherValue
        elif selfValue == None and otherValue != None:
            # This value is None and the other value isn't so this value is
            # considered less than the other
            return True

        assert(otherValue == None)
        # Either this value is not None and the other is _or_ they're both
        # None, either way this value is not considered less than the other
        # (at best they're equal if both None)
        return False
