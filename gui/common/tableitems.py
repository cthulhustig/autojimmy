import common
import typing
from PyQt5 import QtWidgets, QtCore

class FormattedNumberTableWidgetItem(QtWidgets.QTableWidgetItem):
    def __init__(
            self,
            value: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            thousandsSeparator: bool = True,
            alwaysIncludeSign: bool = False,
            decimalPlaces: int = 2, # Only applies for float values
            removeTrailingZeros: bool = True, # Only applies for float values,
            other: typing.Optional['FormattedNumberTableWidgetItem'] = None
            ) -> None:
        super().__init__(other)
        self.setTextAlignment(int(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter))
        self.setValue(
            value=other._value if other else value,
            thousandsSeparator=other._thousandsSeparator if other else thousandsSeparator,
            alwaysIncludeSign=other._alwaysIncludeSign if other else alwaysIncludeSign,
            decimalPlaces=other._decimalPlaces if other else decimalPlaces,
            removeTrailingZeros=other._removeTrailingZeros if other else removeTrailingZeros)

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
            value: typing.Optional[typing.Union[int, float, common.ScalarCalculation]],
            thousandsSeparator: bool = True,
            alwaysIncludeSign: bool = False,
            decimalPlaces: int = 2, # Only applies for float values
            removeTrailingZeros: bool = True, # Only applies for float values
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
        self._thousandsSeparator = thousandsSeparator
        self._alwaysIncludeSign = alwaysIncludeSign
        self._decimalPlaces = decimalPlaces
        self._removeTrailingZeros = removeTrailingZeros

        stringValue = None
        if numericValue != None:
            stringValue = common.formatNumber(
                number=numericValue,
                thousandsSeparator=thousandsSeparator,
                alwaysIncludeSign=alwaysIncludeSign,
                decimalPlaces=decimalPlaces,
                removeTrailingZeros=removeTrailingZeros,
                infinityString='∞')
        self.setText(stringValue)

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
