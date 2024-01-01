import app
import enum
import gui
import os
import typing
from PyQt5 import QtGui, QtCore, QtWidgets, QtSvg, QtXml

class Icon(enum.Enum):
    FrozenColumn = 'frozen_column.svg'
    UnfrozenColumn = 'unfrozen_column.svg'
    CloseTab = 'close_tab.svg'
    NewFile = 'new_file.svg'
    SaveFile = 'save_file.svg'
    DeleteFile = 'delete_file.svg'
    CopyFile = 'copy_file.svg'
    RenameFile = 'rename_file.svg'
    RevertFile = 'revert_file.svg'
    ImportFile = 'import_file.svg'
    ExportFile = 'export_file.svg'
    Search = 'search.svg'
    Info = 'info.svg'
    ZoomIn = 'zoom_in.svg'
    ZoomOut = 'zoom_out.svg'
    ZoomToFit = 'zoom_to_fit.svg'
    Settings = 'settings.svg'


# Mapping to override colour used for Normal mode variant of the icon. If no override
# is specified, WindowText colour is used
_IconColourMap: typing.Dict[Icon, QtGui.QColor] = {
    Icon.FrozenColumn: QtGui.QColor('#1084FE')
}

_IconMap: typing.Dict[str, QtGui.QIcon] = {}

class IconTheme(enum.Enum):
    DarkMode = 0
    LightMode = 1

def setSvgColour(
        svgData: QtCore.QByteArray,
        colour: QtGui.QColor
        ) -> QtCore.QByteArray:
    doc = QtXml.QDomDocument()
    doc.setContent(svgData)
    root = doc.firstChildElement()
    if root:
        root.setAttribute(
            'stroke',
            gui.colourToString(colour, includeAlpha=False))
    return doc.toByteArray() if doc else None

# https://falsinsoft.blogspot.com/2016/04/qt-snippet-render-svg-to-qpixmap-for.html
def svgToPixmap(
        svgData: QtCore.QByteArray,
        pixmapSize: QtCore.QSize) -> QtGui.QPixmap:
    pixelRatio = QtWidgets.QApplication.instance().devicePixelRatio()
    svgRenderer = QtSvg.QSvgRenderer(svgData)

    pixmap = QtGui.QPixmap(pixmapSize * pixelRatio)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)

    painter = QtGui.QPainter()
    painter.begin(pixmap)
    svgRenderer.render(painter)
    painter.end()

    pixmap.setDevicePixelRatio(pixelRatio)

    return pixmap

def svgToIcon(
        svgPath: str,
        colour: typing.Optional[QtGui.QColor] = None
        ) -> QtGui.QIcon:
    file = QtCore.QFile(svgPath)
    try:
        file.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text)
        doc = QtXml.QDomDocument()
        doc.setContent(file)
    finally:
        file.close()
    svgData = doc.toByteArray()

    iconSizes = [16, 24, 32, 48, 64]
    icon = QtGui.QIcon()

    if not colour:
        colour = QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.WindowText)
    disabledColour = QtWidgets.QApplication.palette().color(
        QtGui.QPalette.ColorGroup.Disabled,
        QtGui.QPalette.ColorRole.WindowText)

    for size in iconSizes:
        pixmapSize = QtCore.QSize(size, size)
        svgData = setSvgColour(svgData=svgData, colour=colour)
        pixmap = svgToPixmap(
            svgData=svgData,
            pixmapSize=pixmapSize)
        icon.addPixmap(pixmap, mode=QtGui.QIcon.Mode.Normal)

        svgData = setSvgColour(
            svgData=svgData,
            colour=disabledColour)
        pixmap = svgToPixmap(
            svgData=svgData,
            pixmapSize=pixmapSize)
        icon.addPixmap(pixmap, mode=QtGui.QIcon.Mode.Disabled)

    return icon

def loadIcon(id: Icon) -> QtGui.QIcon:
    iconPath = os.path.join(
        app.Config.instance().installDir(),
        'icons',
        id.value)
    icon = _IconMap.get(iconPath)
    if not icon:
        icon = svgToIcon(
            svgPath=iconPath,
            colour=_IconColourMap.get(id))
        _IconMap[iconPath] = icon
    return icon
