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

# TODO: Need to make this user configurable
_LocalRendering = True

def generateThumbnail(
        hex: travellermap.HexPosition,
        width: int = 256,
        height: int = 256,
        linearScale: float = 64
        ) -> typing.Tuple[
            typing.Optional[bytes],
            typing.Optional[travellermap.MapFormat]]:
    if _LocalRendering:
        _initThumbnailRenderer()

        centerX, centerY = hex.absoluteCenter()
        renderer = cartographer.RenderContext(
            graphics=_thumbnailGraphics,
            absoluteCenterX=centerX,
            absoluteCenterY=centerY,
            scale=linearScale,
            outputPixelX=width,
            outputPixelY=height,
            style=app.Config.instance().mapStyle(),
            options=cartographer.mapOptionsToRenderOptions(
                app.Config.instance().mapOptions()),
            imageCache=_thumbnailImageCache,
            vectorCache=_thumbnailVectorCache,
            labelCache=_thumbnailLabelCache,
            styleCache=_thumbnailStyleCache)

        image = QtGui.QImage(width, height, QtGui.QImage.Format.Format_ARGB32)
        painter = QtGui.QPainter()
        _thumbnailGraphics.setPainter(painter)
        painter.begin(image)
        try:
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
            milieu=app.Config.instance().milieu(),
            style=app.Config.instance().mapStyle(),
            options=app.Config.instance().mapOptions(),
            hex=hex,
            width=width,
            height=height,
            linearScale=linearScale,
            timeout=3)