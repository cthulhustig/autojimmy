import app
import cartographer
import gui
import logic
import multiverse
import traveller
import typing

class HexTooltipProvider(object):
    def __init__(
            self,
            milieu: multiverse.Milieu,
            rules: traveller.Rules,
            mapStyle: cartographer.MapStyle,
            mapOptions: typing.Collection[app.MapOption],
            worldTagging: typing.Optional[logic.WorldTagging] = None,
            taggingColours: typing.Optional[app.TaggingColours] = None
            ) -> None:
        super().__init__()

        self._milieu = milieu
        self._rules = traveller.Rules(rules)
        self._mapStyle = mapStyle
        self._mapOptions = set(mapOptions)
        self._worldTagging = logic.WorldTagging(worldTagging) if worldTagging else None
        self._taggingColours = app.TaggingColours(taggingColours) if taggingColours else None

    def milieu(self) -> multiverse.Milieu:
        return self._milieu

    def setMilieu(self, milieu: multiverse.Milieu) -> None:
        self._milieu = milieu

    def rules(self) -> traveller.Rules:
        return traveller.Rules(self._rules)

    def setRules(self, rules: traveller.Rules) -> None:
        self._rules = traveller.Rules(rules)

    def mapStyle(self) -> cartographer.MapStyle:
        return self._mapStyle

    def setMapStyle(self, style: cartographer.MapStyle) -> None:
        self._mapStyle = style

    def mapOptions(self) -> typing.Iterable[app.MapOption]:
        return list(self._mapOptions)

    def setMapOptions(self, options: typing.Collection[app.MapOption]) -> None:
        self._mapOptions = set(options)

    def worldTagging(self) -> typing.Optional[logic.WorldTagging]:
        return logic.WorldTagging(self._worldTagging) if self._worldTagging else None

    def setWorldTagging(self, tagging: typing.Optional[logic.WorldTagging]) -> None:
        self._worldTagging = logic.WorldTagging(tagging) if tagging else None

    def taggingColours(self) -> typing.Optional[app.TaggingColours]:
        return app.TaggingColours(self._taggingColours) if self._taggingColours else None

    def setTaggingColours(self, colours: typing.Optional[app.TaggingColours]) -> None:
        self._taggingColours = app.TaggingColours(colours) if colours else None

    def tooltip(self, hex: multiverse.HexPosition) -> str:
        return gui.createHexToolTip(
            universe=multiverse.WorldManager.instance().universe(),
            milieu=self._milieu,
            hex=hex,
            rules=self._rules,
            includeHexImage=True, # Always show hex images
            hexImageStyle=self._mapStyle,
            hexImageOptions=self._mapOptions,
            worldTagging=self._worldTagging,
            taggingColours=self._taggingColours)
