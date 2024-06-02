from PyQt5 import QtCore, QtWidgets

class NoWheelEventFilter(QtCore.QObject):
    def eventFilter(self, object: object, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.Wheel:
                return True
        return super().eventFilter(object, event)

# For this have any real effect the widget(s) it's used should NOT
# have the WheelFocus focus policy. Widgets seem to have this by
# default so it needs to be explicitly removed. If this isn't done
# then using the wheel over the cursor will cause it to gain focus
# at which point this filter will have no effect. This is at least
# the case for QComboBox or QSpinBox where the scroll wheel changes
# the value
class NoWheelEventUnlessFocusedFilter(QtCore.QObject):
    def eventFilter(self, object: object, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.Wheel:
            if isinstance(object, QtWidgets.QWidget) and not object.hasFocus():
                return True
        return super().eventFilter(object, event)