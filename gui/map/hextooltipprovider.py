import app
import gui
import logic
import traveller
import travellermap
import typing

class HexTooltipProvider(object):
    def __init__(
            self,
            milieu: travellermap.Milieu,
            rules: traveller.Rules,
            showImages: bool,
            mapStyle: travellermap.Style,
            mapOptions: typing.Collection[travellermap.Option],
            worldTagging: typing.Optional[logic.WorldTagging] = None,
            taggingColours: typing.Optional[app.TaggingColours] = None
            ) -> None:
        super().__init__()

        self._milieu = milieu
        self._rules = traveller.Rules(rules)
        self._showImages = showImages
        self._mapStyle = mapStyle
        self._mapOptions = set(mapOptions)
        self._worldTagging = logic.WorldTagging(worldTagging) if worldTagging else None
        self._taggingColours = app.TaggingColours(taggingColours) if taggingColours else None

    def milieu(self) -> travellermap.Milieu:
        return self._milieu

    def setMilieu(self, milieu: travellermap.Milieu) -> None:
        self._milieu = milieu

    def rules(self) -> traveller.Rules:
        return traveller.Rules(self._rules)

    def setRules(self, rules: traveller.Rules) -> None:
        self._rules = traveller.Rules(rules)

    def showImages(self) -> bool:
        return self._showImages

    def setShowImages(self, show: bool) -> None:
        self._showImages = show

    def mapStyle(self) -> travellermap.Style:
        return self._mapStyle

    def setMapStyle(self, style: travellermap.Style) -> None:
        self._mapStyle = style

    def mapOptions(self) -> typing.Iterable[travellermap.Option]:
        return list(self._mapOptions)

    def setMapOptions(self, options: typing.Collection[travellermap.Option]) -> None:
        self._mapOptions = set(options)

    def setWorldTagging(self, tagging: typing.Optional[logic.WorldTagging]) -> None:
        self._worldTagging = logic.WorldTagging(tagging) if tagging else None

    def setTaggingColours(self, colours: app.TaggingColours) -> None:
        self._taggingColours = app.TaggingColours(colours) if colours else None

    def tooltip(self, hex: travellermap.HexPosition) -> str:
        return gui.createHexToolTip(
            hex=hex,
            milieu=self._milieu,
            rules=self._rules,
            hexImage=self._showImages,
            hexImageStyle=self._mapStyle,
            hexImageOptions=self._mapOptions,
            worldTagging=self._worldTagging,
            taggingColours=self._taggingColours)