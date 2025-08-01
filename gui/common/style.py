import app
import common
import darkdetect
import gui
import logging
import typing
from PyQt5 import QtCore, QtWidgets, QtGui

if common.isWindows():
    import ctypes
    try:
        _SetWindowAttribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
    except Exception as ex:
        logging.warning('Failed to initialise Windows DwmSetWindowAttribute', exc_info=ex)
        _SetWindowAttribute = None


# This is INCREDIBLY hacky but I can't find a better way to do it
def _defaultWidgetSize(type: typing.Type[QtWidgets.QWidget]) -> QtCore.QSize:
    tempWidget = type()
    sizeHint = tempWidget.sizeHint()
    tempWidget.destroy()
    return sizeHint


_InterfaceTheme = app.ColourTheme.DarkMode
_CachedDarkDetectResult = None
def isDarkModeEnabled() -> bool:
    global _InterfaceTheme

    if _InterfaceTheme is app.ColourTheme.DarkMode:
        return True
    elif _InterfaceTheme is app.ColourTheme.LightMode:
        return False
    elif _InterfaceTheme is app.ColourTheme.UseOSSetting:
        global _CachedDarkDetectResult
        if _CachedDarkDetectResult == None:
            _CachedDarkDetectResult = darkdetect.isDark()
        return _CachedDarkDetectResult

    return True # In case of error default to dark mode

_InterfaceScale = 1.0
def interfaceScale() -> float:
    global _InterfaceScale
    return _InterfaceScale

# This function can be called on any platform but only has an effect on Windows
# This MUST be called before the a window is shown. It has no effect if the window is already displayed.
# If the window is closed then reshown it must be called again before it's reshown
def configureWindowTitleBar(widget: QtWidgets.QWidget) -> bool:
    if not common.isWindows():
        return True # Successfully did nothing

    if not _SetWindowAttribute:
        return False

    # For some mad reason Microsoft change this attribute for Windows 10 20h1. We try to set it
    # using the new value, if that doesn't work the older value is tried. This is what the Qt
    # implementation does internally
    # https://github.com/qt/qtbase/blob/dev/src/plugins/platforms/windows/qwindowswindow.cpp#L3082
    DwmwaUseImmersiveDarkMode = 20
    DwmwaUseImmersiveDarkModeBefore20h1 = 19

    value = ctypes.c_int(1 if isDarkModeEnabled() else 0)

    hwnd = ctypes.c_void_p(widget.winId().__int__())
    SetImmersiveDarkMode = lambda attribute: bool(_SetWindowAttribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)))

    try:
        return SetImmersiveDarkMode(DwmwaUseImmersiveDarkMode) or SetImmersiveDarkMode(DwmwaUseImmersiveDarkModeBefore20h1)
    except Exception as ex:
        logging.warning('Failed to set Windows ImmersionDarkMode attribute', exc_info=ex)
        return False

def configureAppStyle(
        application: QtWidgets.QApplication,
        interfaceTheme: app.ColourTheme = app.ColourTheme.DarkMode,
        interfaceScale: float = 1.0
        ) -> None:
    global _InterfaceTheme, _InterfaceScale
    _InterfaceTheme = interfaceTheme
    _InterfaceScale = interfaceScale

    darkModeEnabled = isDarkModeEnabled()

    # Enable Fusion no mater what for a consistent look
    application.setStyle(QtWidgets.QStyleFactory.create('Fusion'))

    palette = application.palette()
    if darkModeEnabled:
        textColour = QtGui.QColor(190, 190, 190)

        # Dark mode colour scheme taken from this stack overflow post then tweaked a fair bit
        # https://stackoverflow.com/questions/48256772/dark-theme-for-qt-widgets
        # Some pretty limited information on where the various roles are used can be found here
        # https://doc.qt.io/qt-6/qpalette.html#ColorRole-enum
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(53, 53, 53))
        palette.setColor(QtGui.QPalette.ColorRole.WindowText, textColour)
        palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(127, 127, 127))
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(20, 20, 20))
        palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor(66, 66, 66))
        palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor(42, 42, 42))
        palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, textColour)
        palette.setColor(QtGui.QPalette.ColorRole.Text, textColour)
        palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Text, QtGui.QColor(127, 127, 127))
        palette.setColor(QtGui.QPalette.ColorRole.Light, QtGui.QColor(99, 99, 99))
        palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Light, QtGui.QColor(80, 80, 80))
        palette.setColor(QtGui.QPalette.ColorRole.Dark, QtGui.QColor(35, 35, 35))
        palette.setColor(QtGui.QPalette.ColorRole.Shadow, QtGui.QColor(20, 20, 20))
        palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(53, 53, 53))
        palette.setColor(QtGui.QPalette.ColorRole.ButtonText, textColour)
        palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor(127, 127, 127))
        # I don't know of anything 'official' that uses BrightText but I'm
        # miss-using it as an error colour for things like highlighting an
        # invalid regex
        palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor(100, 0, 0))
        palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor(42, 130, 218))
        palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(12, 106, 210, 127)) # Use transparency for highlight
        palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(80, 80, 80))
        palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(235, 235, 235))
        palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(127, 127, 127))
    else:
        # Use default colours for most things but force tool tip colours as Windows (or possibly Qt)
        # uses a horrible yellowish colour by default
        palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtCore.Qt.GlobalColor.white)
        palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtCore.Qt.GlobalColor.black)
        # I don't know of anything 'official' that uses BrightText but I'm
        # miss-using it as an error colour for things like highlighting an
        # invalid regex
        palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtCore.Qt.GlobalColor.red)
    application.setPalette(palette)

    style = ''

    if interfaceScale != 1.0:
        # Scale radio buttons and check boxes as they don't auto scale with the font
        size = _defaultWidgetSize(QtWidgets.QRadioButton)
        style += 'QRadioButton::indicator {{width: {width}px; height: {height}px;}}\n'.format(
            width=int(round(size.width() * interfaceScale)),
            height=int(round(size.height() * interfaceScale)))

        size = _defaultWidgetSize(QtWidgets.QCheckBox)
        style += 'QCheckBox::indicator {{width: {width}px; height: {height}px;}}\n'.format(
            width=int(round(size.width() * interfaceScale)),
            height=int(round(size.height() * interfaceScale)))

    # For some reason tool tip text and background colours need set as a style sheet in order to work.
    # Most likely because I'm using html tool tips.
    textColour = gui.colourToString(QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.ToolTipText))
    bkColour = gui.colourToString(QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.ToolTipBase))
    style += f'QToolTip {{color: {textColour}; background-color: {bkColour}; padding: 1px; border-width:2px; border-style:solid;}}\n'

    darkTabStyle = ''
    if darkModeEnabled:
        # Highlight selected tab in dark mode to make it easier to see
        highlightColour = palette.color(QtGui.QPalette.ColorRole.Highlight)
        darkTabStyle = f'background: {gui.colourToString(highlightColour)}'
    style += f'QTabBar::tab:selected {{font-weight: bold; {darkTabStyle}}}\n'

    application.setStyleSheet(style)

    # For reasons I don't understand, this needs to be done AFTER the style sheet is set. If it's
    # not, then menus, tables (and possibly more) don't automatically pick up the application font
    if interfaceScale != 1.0:
        font = application.font()
        font.setPointSizeF(font.pointSizeF() * interfaceScale)
        application.setFont(font)
