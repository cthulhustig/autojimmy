import astronomer
import common
import enum
import survey
import typing

class LabelBand(enum.Enum):
    Mega = 0
    Minor = 1

class LabelSize(enum.Enum):
    Small = 0
    Large = 1

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

        common.validateMandatoryStr(name='text', value=text, allowEmpty=False)
        common.validateMandatoryFloat(name='worldX', value=worldX)
        common.validateMandatoryFloat(name='worldY', value=worldY)
        survey.validateOptionalHtmlColour(name='colour', value=colour)
        common.validateOptionalObject(name='size', value=size, objectType=LabelSize)
        common.validateMandatoryBool(name='wrap', value=wrap)

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
            band: LabelBand,
            colour: typing.Optional[str] = None,
            # TODO: It feels like this should have a default rather than being nullable
            size: typing.Optional[LabelSize] = None
            ) -> None:
        super().__init__(entityId=entityId)

        common.validateMandatoryStr(name='text', value=text)
        common.validateMandatoryFloat(name='worldX', value=worldX)
        common.validateMandatoryFloat(name='worldY', value=worldY)
        common.validateMandatoryObject(name='band', value=band, objectType=LabelBand)
        survey.validateOptionalHtmlColour(name='colour', value=colour)
        common.validateOptionalObject(name='size', value=size, objectType=LabelSize)

        self._text = text
        self._worldX = worldX
        self._worldY = worldY
        self._band = band
        self._colour = colour
        self._size = size

    def text(self) -> str:
        return self._text

    def worldX(self) -> float:
        return self._worldX

    def worldY(self) -> float:
        return self._worldY

    def band(self) -> LabelBand:
        return self._band

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def size(self) -> typing.Optional[LabelSize]:
        return self._size
