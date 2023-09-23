import logging
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

def createLabelledWidgetLayout(
        text: str,
        widget: QtWidgets.QWidget
        ) -> QtWidgets.QHBoxLayout:
    layout = QtWidgets.QHBoxLayout()
    layout.addWidget(QtWidgets.QLabel(text))
    layout.addWidget(widget)
    layout.addStretch()
    return layout

class MenuItem(object):
    def __init__(
            self,
            text: str,
            callback: typing.Callable[[], typing.Any],
            enabled: bool = True,
            displayed: bool = True
            ) -> None:
        self.text = text
        self.callback = callback
        self.enabled = enabled
        self.displayed = displayed

def displayMenu(
        parent: QtWidgets.QWidget,
        items: typing.Iterable[typing.Union[MenuItem, QtWidgets.QAction, QtWidgets.QMenu, None]],
        globalPosition: QtCore.QPoint
        ) -> None:
    menu = QtWidgets.QMenu(parent)

    for item in items:
        if isinstance(item, MenuItem):
            if not item.displayed:
                continue
            action = menu.addAction(item.text)
            action.triggered.connect(item.callback)
            action.setEnabled(item.enabled)
        elif isinstance(item, QtWidgets.QAction):
            menu.addAction(item)
        elif isinstance(item, QtWidgets.QMenu):
            menu.addMenu(item)
        else:
            menu.addSeparator()

    menu.exec(globalPosition)

def safeLoadSetting(
        settings: QtCore.QSettings,
        key: str,
        type: typing.Optional[typing.Type],
        default: typing.Optional[typing.Any] = None,
        ) -> typing.Optional[typing.Any]:
    if not settings.contains(key):
        return default
    try:
        return settings.value(key, type=type)
    except Exception as ex:
        logging.error(f'Exception occurred while reading "{key}" from "{settings.group()}" in "{settings.fileName()}"', exc_info=ex)
        return default

def colourToString(
        colour: QtGui.QColor,
        includeAlpha: bool = True
        ) -> str:
    if includeAlpha:
        return f'#{colour.alpha():02X}{colour.red():02X}{colour.green():02X}{colour.blue():02X}'
    else:
        return f'#{colour.red():02X}{colour.green():02X}{colour.blue():02X}'

def isShiftKeyDown():
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier

def isCtrlKeyDown():
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == QtCore.Qt.KeyboardModifier.ControlModifier

def isAltKeyDown():
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == QtCore.Qt.KeyboardModifier.AltModifier

class SignalBlocker():
    def __init__(self, widget: QtWidgets.QWidget):
        self._widget = widget

    def __enter__(self) -> 'SignalBlocker':
        self._old = self._widget.blockSignals(True)
        return self

    def __exit__(self, type, value, traceback):
        self._widget.blockSignals(self._old)

# This generates a list of values for a PyQt enum. For example, to get all values for
# QtWidgets.QMessageBox.StandardButton:
# pyQtEnumValues(QtWidgets.QMessageBox, QtWidgets.QMessageBox.StandardButton)
def pyQtEnumValues(
        cls: typing.Type,
        enum: typing.Type
        ) -> typing.Collection[int]:
    values = []
    for key in dir(cls):
        value = getattr(cls, key)
        if isinstance(value, enum):
            values.append(value)
    return values

# This generates a mapping for a PyQt enum that maps to/from the string name of the enum and the int
# it represents. For example, to get a mapping for QtWidgets.QMessageBox.StandardButton:
# pyQtEnumMapping(QtWidgets.QMessageBox, QtWidgets.QMessageBox.StandardButton)
def pyQtEnumMapping(
        cls: typing.Type,
        enum: typing.Type
        ) -> typing.Mapping[typing.Union[str, int], typing.Union[str, int]]:
    mapping = {}
    for key in dir(cls):
        value = getattr(cls, key)
        if isinstance(value, enum):
            mapping[key] = value
            mapping[value] = key
    return mapping