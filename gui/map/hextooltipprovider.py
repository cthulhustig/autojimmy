import gui
import travellermap
import typing

class HexTooltipProvider(object):
    def __init__(
            self,
            mapStyle: travellermap.Style,
            mapOptions: typing.Collection[travellermap.Option]
            ) -> None:
        super().__init__()

        self._mapStyle = mapStyle
        self._mapOptions = set(mapOptions)

    def mapStyle(self) -> travellermap.Style:
        return self._mapStyle

    def setMapStyle(self, style: travellermap.Style) -> None:
        self._mapStyle = style

    def mapOptions(self) -> typing.Iterable[travellermap.Option]:
        return list(self._mapOptions)

    def setMapOptions(self, options: typing.Collection[travellermap.Option]) -> None:
        self._mapOptions = set(options)

    def tooltip(
            self,
            milieu: travellermap.Milieu,
            hex: travellermap.HexPosition
            ) -> str:
        return gui.createHexToolTip(
            hex=hex,
            milieu=milieu,
            thumbnail=True,
            thumbnailStyle=self._mapStyle,
            thumbnailOptions=self._mapOptions)