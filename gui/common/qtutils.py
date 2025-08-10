import html
import logging
import packaging.version
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

def minPyQtVersionCheck(minVersion: str) -> bool:
    minVersion = packaging.version.Version(minVersion)
    currentVersion = packaging.version.Version(QtCore.PYQT_VERSION_STR)
    return currentVersion >= minVersion

def createLabelledWidgetLayout(
        text: str,
        widget: QtWidgets.QWidget
        ) -> QtWidgets.QHBoxLayout:
    layout = QtWidgets.QHBoxLayout()
    layout.addWidget(QtWidgets.QLabel(text))
    layout.addWidget(widget)
    layout.addStretch()
    return layout

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
    def __init__(self, widget: QtWidgets.QWidget) -> None:
        self._widget = widget

    def __enter__(self) -> 'SignalBlocker':
        self._old = self._widget.blockSignals(True)
        return self

    def __exit__(self, type, value, traceback) -> None:
        self._widget.blockSignals(self._old)

class UpdateBlocker():
    def __init__(self, widget: QtWidgets.QWidget) -> None:
        self._widget = widget

    def __enter__(self) -> 'UpdateBlocker':
        self._old = self._widget.updatesEnabled()
        self._widget.setUpdatesEnabled(False)
        return self

    def __exit__(self, type, value, traceback) -> None:
        self._widget.setUpdatesEnabled(self._old)

class PainterDrawGuard():
    def __init__(
            self,
            painter: QtGui.QPainter,
            device: typing.Optional[QtGui.QPaintDevice] = None
            ) -> None:
        self._painter = painter
        self._device = device

    def __enter__(self) -> 'PainterDrawGuard':
        self._painter.begin(self._device)
        return self

    def __exit__(self, type, value, traceback) -> None:
        self._painter.end()

class PainterStateGuard():
    def __init__(
            self,
            painter: QtGui.QPainter
            ) -> None:
        self._painter = painter

    def __enter__(self) -> 'PainterStateGuard':
        self._painter.save()
        return self

    def __exit__(self, type, value, traceback) -> None:
        self._painter.restore()

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


# This will attempt to retrieve the system monospace font. If it's unable to do
# that it will try to create a monospace font. It falls back to creating a font
# because there are reports of using the font database not working on some Linux
# distros
# https://stackoverflow.com/questions/1468022/how-to-specify-monospace-fonts-for-cross-platform-qt-applications)
# NOTE: that creating the monospace font causes an ugly warning to be dumped to
# the terminal on macOS but not other platforms form what I've seen.
_cachedMonospaceFont = None
def getMonospaceFont() -> QtGui.QFont:
    global _cachedMonospaceFont
    if _cachedMonospaceFont is not None:
        return _cachedMonospaceFont

    font = None
    try:
        font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
    except Exception as ex:
        logging.error(
            'An exception occurred while querying the system fixed font',
            exc_info=ex)
        # Continue to try and create a font

    if not font:
        font = QtGui.QFont()
        font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        font.setFamily('monospace')

    _cachedMonospaceFont = font
    return font

def tabWidgetSearch(
        widget: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
        tabWidgets: typing.List[QtWidgets.QWidget]
        ) -> None:
    if not widget.isEnabled():
        return
    if isinstance(widget, QtWidgets.QWidget):
        focusPolicy = widget.focusPolicy()
        if focusPolicy & QtCore.Qt.FocusPolicy.TabFocus:
            tabWidgets.append(widget)
            return
    for child in widget.children():
        tabWidgetSearch(widget=child, tabWidgets=tabWidgets)

def alignmentToHtmlStyle(alignment: typing.Optional[int]) -> str:
    if not alignment:
        return ''
    styles = []
    if alignment & QtCore.Qt.AlignmentFlag.AlignLeft:
        styles.append('text-align: left;')
    elif alignment & QtCore.Qt.AlignmentFlag.AlignRight:
        styles.append('text-align: right;')
    elif alignment & QtCore.Qt.AlignmentFlag.AlignHCenter:
        styles.append('text-align: center;')
    elif alignment & QtCore.Qt.AlignmentFlag.AlignJustify:
        styles.append('text-align: justify;')

    if alignment & QtCore.Qt.AlignmentFlag.AlignTop:
        styles.append('vertical-align: top;')
    elif alignment & QtCore.Qt.AlignmentFlag.AlignBottom:
        styles.append('vertical-align: bottom;')
    elif alignment & QtCore.Qt.AlignmentFlag.AlignVCenter:
        styles.append('vertical-align: middle;')
    return ' '.join(styles)

def textToHtmlContent(text: str, font: typing.Optional[QtGui.QFont]) -> str:
    text = html.escape(text)
    text = text.replace('\n', '<br>')
    if font:
        if font.bold():
            text = f'<b>{text}</b>'
        if font.italic():
            text = f'<i>{text}</i>'
    return text

def sizeFontToFit(
        orig: QtGui.QFont,
        text: str,
        rect: QtCore.QRect,
        align: typing.Union[QtCore.Qt.Alignment, QtCore.Qt.AlignmentFlag] = QtCore.Qt.AlignmentFlag.AlignCenter
        ) -> typing.Optional[QtGui.QFont]:
    # Remove any non-alignment flags
    align &= int(QtCore.Qt.AlignmentFlag.AlignHorizontal_Mask | QtCore.Qt.AlignmentFlag.AlignVertical_Mask)

    # Force align to an int as older versions of QtGui.QFontMetrics.boundingRect
    # will throw an exception if they're passed a QtCore.Qt.Alignment
    align = int(align)

    font = QtGui.QFont(orig)
    low = 1
    high = rect.height()
    best = None

    while low <= high:
        mid = int(low + ((high - low) // 2))
        font.setPixelSize(mid)
        fontMetrics = QtGui.QFontMetrics(font)
        contentRect = fontMetrics.boundingRect(rect, align, text)
        contentRect.moveTo(0, 0)

        contained = rect.contains(contentRect)
        if (best == None or mid > best) and contained:
            best = mid

        if contained:
            low = mid + 1
        else:
            high = mid - 1

    if best == None:
        return None

    font.setPixelSize(best)
    return font

def setClipboardContent(
        content: typing.Union[str, QtGui.QPixmap, QtGui.QImage]
        ) -> None:
    clipboard = QtWidgets.QApplication.clipboard()
    if not clipboard:
        raise RuntimeError('Unable to retrieve application clipboard')

    if isinstance(content, str):
        clipboard.setText(content)
    elif isinstance(content, QtGui.QPixmap):
        clipboard.setImage(content.toImage())
    elif isinstance(content, QtGui.QImage):
        clipboard.setImage(content)
    else:
        raise ValueError(f'Clipboard object is unsupported type {type(content)}')
