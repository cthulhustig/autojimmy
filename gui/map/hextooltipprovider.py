import gui
import traveller
import travellermap
import typing

class HexTooltipProvider(object):
    def __init__(
            self,
            milieu: travellermap.Milieu,
            rules: traveller.Rules,
            mapStyle: travellermap.Style,
            mapOptions: typing.Collection[travellermap.Option]
            ) -> None:
        super().__init__()

        self._milieu = milieu
        self._rules = traveller.Rules(rules)
        self._mapStyle = mapStyle
        self._mapOptions = set(mapOptions)

    def milieu(self) -> travellermap.Milieu:
        return self._milieu

    def setMilieu(self, milieu: travellermap.Milieu) -> None:
        self._milieu = milieu

    def rules(self) -> traveller.Rules:
        return traveller.Rules(self._rules)

    def setRules(self, rules: traveller.Rules) -> None:
        self._rules = traveller.Rules(rules)

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
            hex: travellermap.HexPosition,
            thumbnail: bool = True
            ) -> str:
        return gui.createHexToolTip(
            hex=hex,
            milieu=self._milieu,
            rules=self._rules,
            thumbnail=thumbnail,
            thumbnailStyle=self._mapStyle,
            thumbnailOptions=self._mapOptions)