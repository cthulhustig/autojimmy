import astronomer
import common
import enum
import survey
import typing

class LabelLayer(enum.Enum):
    Mega = 0
    Minor = 1
    World = 2
    Border = 3
    Rift = 4
    Route = 5

class LabelSize(enum.Enum):
    Small = 0
    Large = 1

class TextAlignment(enum.Enum):
    Baseline = 0
    Center = 1
    TopLeft = 2
    TopCenter = 3
    TopRight = 4
    CenterLeft = 5
    CenterRight = 6
    BottomLeft = 7
    BottomCenter = 8
    BottomRight = 9

class SectorLabel(astronomer.Entity):
    def __init__(
            self,
            entityId: str,
            text: str,
            worldX: float,
            worldY: float,
            colour: typing.Optional[str] = None,
            size: typing.Optional[LabelSize] = None,
            wrap: bool = False
            ) -> None:
        super().__init__(entityId=entityId)

        common.validateStr(name='text', value=text, allowEmpty=False)
        common.validateFloat(name='worldX', value=worldX)
        common.validateFloat(name='worldY', value=worldY)
        survey.validateHtmlColour(name='colour', value=colour, allowNone=True)
        common.validateObject(name='size', value=size, objectType=LabelSize, allowNone=True)
        common.validateBool(name='wrap', value=wrap)

        self._text = text
        self._worldX = worldX
        self._worldY = worldY
        self._colour = colour
        self._size = size
        self._wrap = wrap

    def text(self) -> str:
        return self._text

    # Offset from top left of sector in world coordinates
    def worldX(self) -> float:
        return self._worldX

    def worldY(self) -> float:
        return self._worldY

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def size(self) -> typing.Optional[LabelSize]:
        return self._size

    def wrap(self) -> bool:
        return self._wrap

class MapLabel(astronomer.Entity):
    def __init__(
            self,
            entityId: str,
            text: str,
            worldX: float,
            worldY: float,
            layer: LabelLayer,
            alignment: typing.Optional[TextAlignment] = None,
            colour: typing.Optional[str] = None,
            size: typing.Optional[LabelSize] = None,
            rotation: typing.Optional[float] = None
            ) -> None:
        super().__init__(entityId=entityId)

        common.validateStr(name='text', value=text)
        common.validateFloat(name='worldX', value=worldX)
        common.validateFloat(name='worldY', value=worldY)
        common.validateObject(name='layer', value=layer, objectType=LabelLayer)
        common.validateObject(name='alignment', value=alignment, objectType=TextAlignment, allowNone=True)
        survey.validateHtmlColour(name='colour', value=colour, allowNone=True)
        common.validateObject(name='size', value=size, objectType=LabelSize, allowNone=True)
        common.validateFloat(name='rotation', value=rotation, allowNone=True)

        self._text = text
        self._worldX = worldX
        self._worldY = worldY
        self._layer = layer
        self._alignment = alignment
        self._colour = colour
        self._size = size
        self._rotation = rotation

    def text(self) -> str:
        return self._text

    def worldX(self) -> float:
        return self._worldX

    def worldY(self) -> float:
        return self._worldY

    def layer(self) -> LabelLayer:
        return self._layer

    def alignment(self) -> typing.Optional[TextAlignment]:
        return self._alignment

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def size(self) -> typing.Optional[LabelSize]:
        return self._size

    def rotation(self) -> typing.Optional[float]:
        return self._rotation