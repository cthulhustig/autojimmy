import app
import gui
import cartographer
import travellermap
import typing
from PyQt5 import QtCore, QtGui

_thumbnailRenderInitialised = False
_thumbnailGraphics: typing.Optional[gui.MapGraphics] = None
_thumbnailImageCache: typing.Optional[cartographer.ImageCache] = None
_thumbnailVectorCache: typing.Optional[cartographer.VectorObjectCache] = None
_thumbnailLabelCache: typing.Optional[cartographer.LabelCache] = None
_thumbnailStyleCache: typing.Optional[cartographer.StyleCache] = None

def _initThumbnailRenderer():
    global _thumbnailRenderInitialised
    global _thumbnailGraphics
    global _thumbnailImageCache
    global _thumbnailVectorCache
    global _thumbnailLabelCache
    global _thumbnailStyleCache

    if _thumbnailRenderInitialised:
        return
    _thumbnailGraphics = gui.MapGraphics()
    _thumbnailImageCache = cartographer.ImageCache(graphics=_thumbnailGraphics)
    _thumbnailVectorCache = cartographer.VectorObjectCache(graphics=_thumbnailGraphics)
    _thumbnailLabelCache = cartographer.LabelCache()
    _thumbnailStyleCache = cartographer.StyleCache()
    _thumbnailRenderInitialised = True

def generateThumbnail(
        hex: travellermap.HexPosition,
        width: int = 256,
        height: int = 256,
        linearScale: float = 64
        ) -> typing.Tuple[
            typing.Optional[bytes],
            typing.Optional[travellermap.MapFormat]]:
    milieu = app.Config.instance().asEnum(
        option=app.ConfigOption.Milieu,
        enumType=travellermap.Milieu)
    mapEngine = app.Config.instance().asEnum(
        option=app.ConfigOption.MapEngine,
        enumType=app.MapEngine)
    mapStyle = app.Config.instance().asEnum(
        option=app.ConfigOption.MapStyle,
        enumType=travellermap.Style)
    mapOptions = app.Config.instance().asObject(
        option=app.ConfigOption.MapOptions,
        objectType=list)

    if mapEngine is app.MapEngine.InApp:
        _initThumbnailRenderer()

        centerX, centerY = hex.worldCenter()
        renderer = cartographer.RenderContext(
            graphics=_thumbnailGraphics,
            worldCenterX=centerX,
            worldCenterY=centerY,
            scale=linearScale,
            outputPixelX=width,
            outputPixelY=height,
            milieu=milieu,
            style=mapStyle,
            options=cartographer.mapOptionsToRenderOptions(mapOptions),
            imageCache=_thumbnailImageCache,
            vectorCache=_thumbnailVectorCache,
            labelCache=_thumbnailLabelCache,
            styleCache=_thumbnailStyleCache)

        image = QtGui.QImage(width, height, QtGui.QImage.Format.Format_ARGB32)
        painter = QtGui.QPainter()
        painter.begin(image)
        try:
            _thumbnailGraphics.setPainter(painter)
            renderer.render()
        finally:
            painter.end()
            _thumbnailGraphics.setPainter(None)

        byteArray = QtCore.QByteArray()
        buffer = QtCore.QBuffer(byteArray)
        buffer.open(QtCore.QBuffer.OpenModeFlag.WriteOnly)
        try:
            image.save(buffer, 'PNG')
        finally:
            buffer.close()

        return (byteArray.data(), travellermap.MapFormat.PNG)
    else:
        return travellermap.TileClient.instance().tile(
            milieu=milieu,
            style=mapStyle,
            options=mapOptions,
            hex=hex,
            width=width,
            height=height,
            linearScale=linearScale,
            timeout=3)
