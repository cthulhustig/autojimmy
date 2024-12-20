import common
from PyQt5 import QtCore, QtWidgets, QtGui

# Based on the QStyleHelper code from the Qt source. The class doesn't seem to
# be available in PyQt
# https://codebrowser.dev/qt5/qtbase/src/widgets/styles/qstylehelper.cpp.html#QStyleHelper
class QStyleHelper():
    @staticmethod
    def dpi(option: QtWidgets.QStyleOption) -> float:
        if not common.isMacOS() and QtWidgets.QApplication.testAttribute(QtCore.Qt.ApplicationAttribute.AA_Use96Dpi):
            return 96

        if option:
            fontMetrics: QtGui.QFontMetrics = option.fontMetrics
            return fontMetrics.fontDpi()

        return QStyleHelper._baseDpi()

    @staticmethod
    def dpiScaled(value: float, dpi: float) -> float:
        return value * dpi / QStyleHelper._baseDpi()

    @staticmethod
    def _baseDpi() -> float:
        return 72 if common.isMacOS() else 96
