import gui
import cartographer
import multiverse
import typing
from PyQt5 import QtCore, QtGui

_thumbnailRenderInitialised = False
_thumbnailGraphics: typing.Optional[gui.MapGraphics] = None
_thumbnailImageCache: typing.Optional[cartographer.ImageStore] = None
_thumbnailVectorCache: typing.Optional[cartographer.VectorStore] = None
_thumbnailLabelCache: typing.Optional[cartographer.LabelStore] = None
_thumbnailStyleCache: typing.Optional[cartographer.StyleStore] = None

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
    _thumbnailImageCache = cartographer.ImageStore(graphics=_thumbnailGraphics)
    _thumbnailVectorCache = cartographer.VectorStore(graphics=_thumbnailGraphics)
    _thumbnailLabelCache = cartographer.LabelStore(universe=multiverse.WorldManager.instance().universe())
    _thumbnailStyleCache = cartographer.StyleStore()
    _thumbnailRenderInitialised = True

def generateThumbnail(
        universe: multiverse.Universe,
        milieu: multiverse.Milieu,
        hex: multiverse.HexPosition,
        width: int,
        height: int,
        linearScale: float,
        style: multiverse.MapStyle,
        options: typing.Collection[multiverse.MapOption]
        ) -> typing.Optional[bytes]:
    _initThumbnailRenderer()

    centerX, centerY = hex.worldCenter()
    renderer = cartographer.RenderContext(
        universe=gui.MapUniverse(universe=universe),
        graphics=_thumbnailGraphics,
        worldCenterX=centerX,
        worldCenterY=centerY,
        scale=linearScale,
        outputPixelX=width,
        outputPixelY=height,
        milieu=milieu,
        style=style,
        options=cartographer.mapOptionsToRenderOptions(options),
        imageStore=_thumbnailImageCache,
        styleStore=_thumbnailStyleCache,
        vectorStore=_thumbnailVectorCache,
        labelStore=_thumbnailLabelCache)

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

    return byteArray.data()
