import astronomer
import enum
import logic
import typing

class TaggingProperty(enum.Enum):
    Zone = 'Zone'
    StarPort = 'Starport'
    WorldSize = 'World Size'
    Atmosphere = 'Atmosphere'
    Hydrographics = 'Hydrographics'
    Population = 'Population'
    Government = 'Government'
    LawLevel = 'Law Level'
    TechLevel = 'Tech Level'
    BaseType = 'Base Type'
    TradeCode = 'Trade Code'
    Resources = 'Resources'
    Labour = 'Labour'
    Infrastructure = 'Infrastructure'
    Efficiency = 'Efficiency'
    Heterogeneity = 'Heterogeneity'
    Acceptance = 'Acceptance'
    Strangeness = 'Strangeness'
    Symbols = 'Symbols'
    Nobility = 'Nobility'
    Allegiance = 'Allegiance'
    Spectral = 'Spectral'
    Luminosity = 'Luminosity'

class WorldTagging(object):
    @typing.overload
    def __init__(
        self,
        config: typing.Optional[typing.Dict[
            TaggingProperty,
            typing.Dict[
                typing.Any, # Type varies by tagging property
                logic.TagLevel
                ]]] = None
        ) -> None: ...

    @typing.overload
    def __init__(self, other: 'WorldTagging' ) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        config = None
        if args:
            arg = args[0]
            config: typing.Dict = arg._taggingMap if isinstance(arg, WorldTagging) else arg
        elif 'config' in kwargs:
            config = kwargs['config']
        elif 'other' in kwargs:
            other = kwargs['other']
            if not isinstance(other, WorldTagging):
                raise RuntimeError('The other parameter must be an WorldTagging')
            config = other._taggingMap

        self._taggingMap = WorldTagging._copyConfig(source=config)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorldTagging):
            return False
        return self._taggingMap == other._taggingMap

    def config(self) -> typing.Dict[
        TaggingProperty,
        typing.Dict[
            typing.Any, # Type varies by tagging property
            logic.TagLevel
            ]]:
        return WorldTagging._copyConfig(self._taggingMap)

    def setConfig(
            self,
            config: typing.Mapping[
                TaggingProperty,
                typing.Mapping[
                    typing.Any, # Type varies by tagging property
                    logic.TagLevel
                    ]]
            ) -> None:
        self._taggingMap.clear()
        for property, tagging in config.items():
            self._taggingMap[property] = dict(tagging)

    def propertyConfig(
        self,
        property: TaggingProperty
        ) -> typing.Dict[
            typing.Any, # Type varies by tagging property
            logic.TagLevel
            ]:
        config = self._taggingMap.get(property)
        return dict(config) if config else {}

    def setPropertyConfig(
            self,
            property: TaggingProperty,
            config: typing.Mapping[
                typing.Any, # Type varies by tagging property
                logic.TagLevel
                ]) -> None:
        self._taggingMap[property] = dict(config)

    def calculateWorldTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        # Always tag Anomalies at warning level as they're not necessarily a danger
        if world.isAnomaly():
            return logic.TagLevel.Warning

        worldTagLevel = None

        tempTagLevel = self.calculateZoneTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateStarPortTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateWorldSizeTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateAtmosphereTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateHydrographicsTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = self.calculatePopulationTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateGovernmentTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateLawLevelTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateTechLevelTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        for baseType in world.bases():
            tempTagLevel = self.calculateBaseTypeTagLevel(baseType)
            if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
                worldTagLevel = tempTagLevel

        for tradeCode in world.tradeCodes():
            tempTagLevel = self.calculateTradeCodeTagLevel(tradeCode)
            if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
                worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateResourcesTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateLabourTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateInfrastructureTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateEfficiencyTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateHeterogeneityTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateAcceptanceTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateStrangenessTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateSymbolsTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        for nobilityType in world.nobilities():
            tempTagLevel = self.calculateNobilityTagLevel(nobilityType)
            if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
                worldTagLevel = tempTagLevel

        tempTagLevel = self.calculateAllegianceTagLevel(world)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        for star in world.stellar():
            tempTagLevel = self.calculateSpectralTagLevel(star)
            if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
                worldTagLevel = tempTagLevel

            tempTagLevel = self.calculateLuminosityTagLevel(star)
            if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
                worldTagLevel = tempTagLevel

        return worldTagLevel

    def calculateZoneTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.Zone,
            code=world.zone())

    def calculateStarPortTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.StarPort,
            code=world.uwp().code(astronomer.UWP.Element.StarPort))

    def calculateWorldSizeTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.WorldSize,
            code=world.uwp().code(astronomer.UWP.Element.WorldSize))

    def calculateAtmosphereTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.Atmosphere,
            code=world.uwp().code(astronomer.UWP.Element.Atmosphere))

    def calculateHydrographicsTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.Hydrographics,
            code=world.uwp().code(astronomer.UWP.Element.Hydrographics))

    def calculatePopulationTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.Population,
            code=world.uwp().code(astronomer.UWP.Element.Population))

    def calculateGovernmentTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.Government,
            code=world.uwp().code(astronomer.UWP.Element.Government))

    def calculateLawLevelTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.LawLevel,
            code=world.uwp().code(astronomer.UWP.Element.LawLevel))

    def calculateTechLevelTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.TechLevel,
            code=world.uwp().code(astronomer.UWP.Element.TechLevel))

    def calculateBaseTypeTagLevel(
            self,
            baseType: astronomer.BaseType
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.BaseType,
            code=baseType)

    def calculateTradeCodeTagLevel(
            self,
            tradeCode: astronomer.TradeCode
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.TradeCode,
            code=tradeCode)

    def calculateResourcesTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.Resources,
            code=world.economics().code(astronomer.Economics.Element.Resources))

    def calculateLabourTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.Labour,
            code=world.economics().code(astronomer.Economics.Element.Labour))

    def calculateInfrastructureTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.Infrastructure,
            code=world.economics().code(astronomer.Economics.Element.Infrastructure))

    def calculateEfficiencyTagLevel(
            self,
            world: astronomer.World
            ) -> logic.TagLevel:
        return self._propertyTagLevel(
            property=TaggingProperty.Efficiency,
            code=world.economics().code(astronomer.Economics.Element.Efficiency))

    def calculateHeterogeneityTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.Heterogeneity,
            code=world.culture().code(astronomer.Culture.Element.Heterogeneity))

    def calculateAcceptanceTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.Acceptance,
            code=world.culture().code(astronomer.Culture.Element.Acceptance))

    def calculateStrangenessTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.Strangeness,
            code=world.culture().code(astronomer.Culture.Element.Strangeness))

    def calculateSymbolsTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.Symbols,
            code=world.culture().code(astronomer.Culture.Element.Symbols))

    def calculateNobilityTagLevel(
            self,
            nobilityType: astronomer.NobilityType
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.Nobility,
            code=nobilityType)

    def calculateAllegianceTagLevel(
            self,
            world: astronomer.World
            ) -> typing.Optional[logic.TagLevel]:
        allegiance = world.allegiance()
        if not allegiance:
            return None
        return self._propertyTagLevel(
            property=TaggingProperty.Allegiance,
            code=allegiance.uniqueCode())

    def calculateSpectralTagLevel(
            self,
            star: astronomer.Star
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.Spectral,
            code=star.code(astronomer.Star.Element.SpectralClass))

    def calculateLuminosityTagLevel(
            self,
            star: astronomer.Star
            ) -> typing.Optional[logic.TagLevel]:
        return self._propertyTagLevel(
            property=TaggingProperty.Luminosity,
            code=star.code(astronomer.Star.Element.LuminosityClass))

    def _propertyTagLevel(
            self,
            property: TaggingProperty,
            code: typing.Union[str, enum.Enum]
            ) -> typing.Optional[logic.TagLevel]:
        propertyTagMap = self._taggingMap.get(property)
        if not propertyTagMap:
            return None
        return propertyTagMap.get(code)

    @staticmethod
    def _copyConfig(
            source: typing.Optional[typing.Dict[
                TaggingProperty,
                typing.Dict[
                    typing.Any,
                    logic.TagLevel
                    ]]] = None
            ) -> typing.Dict[
        TaggingProperty,
        typing.Dict[
            typing.Any,
            logic.TagLevel
            ]]:
        copy = {}
        if source:
            for property, tagging in source.items():
                copy[property] = dict(tagging)
        return copy
