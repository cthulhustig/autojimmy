import common
import datetime
import typing
from PyQt5 import QtWidgets, QtCore

class TableWidgetItemEx(QtWidgets.QTableWidgetItem):
    def setBold(self, enable: bool = True) -> None:
        font = self.font()
        font.setBold(enable)
        self.setFont(font)

    def setItalic(self, enable: bool = True) -> None:
        font = self.font()
        font.setItalic(enable)
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
        if isinstance(other, FormattedNumberTableWidgetItem):
            selfValue = self.numericValue()
            otherValue = other.numericValue()
            if selfValue != None and otherValue != None:
                return selfValue < otherValue

            # This covers 3 cases
            # - If this object has no value and the other object has
            #   a value, then this object is considered less than the
            #   other object
            # - If this object has a value and the other doesn't,
            #   then this object is not considered less than the other
            #   object
            # - If this and the other object have no value, then this
            #   instance is not considered less than the other
            return selfValue == None and otherValue != None
        return super().__lt__(other)

class LocalTimestampTableWidgetItem(TableWidgetItemEx):
    def __init__(
            self,
            timestamp: typing.Optional[datetime.datetime] = None,
            other: typing.Optional['LocalTimestampTableWidgetItem'] = None
            ) -> None:
        super().__init__(other)
        self._timestamp = None
        self.setTimestamp(other.timestamp() if other else timestamp)

    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    def setTimestamp(
            self,
            timestamp: typing.Optional[datetime.datetime] = None
            ):
        self._timestamp = timestamp if timestamp else common.utcnow()
        self.setText(timestamp.astimezone().strftime('%c'))

    def clone(self) -> 'LocalTimestampTableWidgetItem':
        return LocalTimestampTableWidgetItem(other=self)

    def __lt__(
            self,
            other: 'LocalTimestampTableWidgetItem'
            ) -> bool:
        if isinstance(other, LocalTimestampTableWidgetItem):
            return self._timestamp < other._timestamp
        return super().__lt__(other)
