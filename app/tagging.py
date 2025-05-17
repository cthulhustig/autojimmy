import app
import enum
import logic
import traveller
import typing

def calculateWorldTagLevel(world: traveller.World) -> app.TagLevel:
    # Always tag Anomalies at warning level as they're not necessarily a danger
    if world.isAnomaly():
        return app.TagLevel.Warning

    worldTagLevel = None

    tempTagLevel = calculateZoneTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    tempTagLevel = calculateStarPortTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    tempTagLevel = calculateWorldSizeTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    tempTagLevel = calculateAtmosphereTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    tempTagLevel = calculateHydrographicsTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    tempTagLevel = calculatePopulationTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    tempTagLevel = calculateGovernmentTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    tempTagLevel = calculateLawLevelTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    tempTagLevel = calculateTechLevelTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    for baseType in world.bases():
        tempTagLevel = calculateBaseTypeTagLevel(baseType)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

    for tradeCode in world.tradeCodes():
        tempTagLevel = calculateTradeCodeTagLevel(tradeCode)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

    tempTagLevel = calculateResourcesTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    tempTagLevel = calculateLabourTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    tempTagLevel = calculateInfrastructureTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    tempTagLevel = calculateEfficiencyTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    tempTagLevel = calculateHeterogeneityTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    tempTagLevel = calculateAcceptanceTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    tempTagLevel = calculateStrangenessTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    tempTagLevel = calculateSymbolsTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    for nobilityType in world.nobilities():
        tempTagLevel = calculateNobilityTagLevel(nobilityType)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

    tempTagLevel = calculateAllegianceTagLevel(world)
    if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
        worldTagLevel = tempTagLevel

    for star in world.stellar():
        tempTagLevel = calculateSpectralTagLevel(star)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

        tempTagLevel = calculateLuminosityTagLevel(star)
        if tempTagLevel and (not worldTagLevel or (tempTagLevel > worldTagLevel)):
            worldTagLevel = tempTagLevel

    return worldTagLevel

def calculateJumpRouteTagLevel(jumpRoute: logic.JumpRoute) -> app.TagLevel:
    routeTagLevel = None

    for _, world in jumpRoute:
        if world:
            worldTagLevel = calculateWorldTagLevel(world)
            if not routeTagLevel or (worldTagLevel > routeTagLevel):
                routeTagLevel = worldTagLevel
        else:
            # Routes going through dead space are always considered dangerous
            routeTagLevel = app.TagLevel.Danger
            break

    return routeTagLevel

def calculateZoneTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.ZoneTagging,
        code=world.zone())

def calculateStarPortTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.StarPortTagging,
        code=world.uwp().code(traveller.UWP.Element.StarPort))

def calculateWorldSizeTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.WorldSizeTagging,
        code=world.uwp().code(traveller.UWP.Element.WorldSize))

def calculateAtmosphereTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.AtmosphereTagging,
        code=world.uwp().code(traveller.UWP.Element.Atmosphere))

def calculateHydrographicsTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.HydrographicsTagging,
        code=world.uwp().code(traveller.UWP.Element.Hydrographics))

def calculatePopulationTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.PopulationTagging,
        code=world.uwp().code(traveller.UWP.Element.Population))

def calculateGovernmentTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.GovernmentTagging,
        code=world.uwp().code(traveller.UWP.Element.Government))

def calculateLawLevelTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.LawLevelTagging,
        code=world.uwp().code(traveller.UWP.Element.LawLevel))

def calculateTechLevelTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.TechLevelTagging,
        code=world.uwp().code(traveller.UWP.Element.TechLevel))

def calculateBaseTypeTagLevel(
        baseType: traveller.BaseType
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.BaseTypeTagging,
        code=baseType)

def calculateTradeCodeTagLevel(
        tradeCode: traveller.TradeCode
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.TradeCodeTagging,
        code=tradeCode)

def calculateResourcesTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.ResourcesTagging,
        code=world.economics().code(traveller.Economics.Element.Resources))

def calculateLabourTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.LabourTagging,
        code=world.economics().code(traveller.Economics.Element.Labour))

def calculateInfrastructureTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.InfrastructureTagging,
        code=world.economics().code(traveller.Economics.Element.Infrastructure))

def calculateEfficiencyTagLevel(world: traveller.World) -> app.TagLevel:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.EfficiencyTagging,
        code=world.economics().code(traveller.Economics.Element.Efficiency))

def calculateHeterogeneityTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.HeterogeneityTagging,
        code=world.culture().code(traveller.Culture.Element.Heterogeneity))

def calculateAcceptanceTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.AcceptanceTagging,
        code=world.culture().code(traveller.Culture.Element.Acceptance))

def calculateStrangenessTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.StrangenessTagging,
        code=world.culture().code(traveller.Culture.Element.Strangeness))

def calculateSymbolsTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.SymbolsTagging,
        code=world.culture().code(traveller.Culture.Element.Symbols))

def calculateNobilityTagLevel(
        nobilityType: traveller.NobilityType
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.NobilityTagging,
        code=nobilityType)

def calculateAllegianceTagLevel(
        world: traveller.World
        ) -> typing.Optional[app.TagLevel]:
    allegianceCode = traveller.AllegianceManager.instance().uniqueAllegianceCode(
        milieu=world.milieu(),
        code=world.allegiance(),
        sectorName=world.sectorName())
    if not allegianceCode:
        return None
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.AllegianceTagging,
        code=allegianceCode)

def calculateSpectralTagLevel(
        star: traveller.Star
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.SpectralTagging,
        code=star.code(traveller.Star.Element.SpectralClass))

def calculateLuminosityTagLevel(
        star: traveller.Star
        ) -> typing.Optional[app.TagLevel]:
    return _checkConfigTagLevel(
        configOption=app.ConfigOption.LuminosityTagging,
        code=star.code(traveller.Star.Element.LuminosityClass))

def tagColour(tagLevel: app.TagLevel) -> typing.Optional[str]:
    if tagLevel is app.TagLevel.Desirable:
        return app.Config.instance().asStr(
            option=app.ConfigOption.DesirableTagColour)
    elif tagLevel is app.TagLevel.Warning:
        return app.Config.instance().asStr(
            option=app.ConfigOption.WarningTagColour)
    elif tagLevel is app.TagLevel.Danger:
        return app.Config.instance().asStr(
            option=app.ConfigOption.DangerTagColour)
    return None

def _checkConfigTagLevel(
        configOption: app.ConfigOption,
        code: typing.Union[str, enum.Enum]
        ) -> typing.Optional[app.TagLevel]:
    tagMap = app.Config.instance().asTagMap(option=configOption)
    if not tagMap:
        return None
    return tagMap.get(code)