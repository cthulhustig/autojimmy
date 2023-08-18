import app
import logic
import traveller

def calculateWorldTagLevel(world: traveller.World) -> app.TagLevel:
    # Always tag Anomalies at danger level
    if world.isAnomaly():
        return app.TagLevel.Danger

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

    for world in jumpRoute:
        worldTagLevel = calculateWorldTagLevel(world)
        if not routeTagLevel or (worldTagLevel > routeTagLevel):
            routeTagLevel = worldTagLevel

    return routeTagLevel

def calculateZoneTagLevel(world: traveller.World) -> app.TagLevel:
    return app.Config.instance().zoneTagLevel(world.zone())

def calculateStarPortTagLevel(world: traveller.World) -> app.TagLevel:
    startPortCode = world.uwp().code(traveller.UWP.Element.StarPort)
    return app.Config.instance().starPortTagLevel(startPortCode)

def calculateWorldSizeTagLevel(world: traveller.World) -> app.TagLevel:
    worldSizeCode = world.uwp().code(traveller.UWP.Element.WorldSize)
    return app.Config.instance().worldSizeTagLevel(worldSizeCode)

def calculateAtmosphereTagLevel(world: traveller.World) -> app.TagLevel:
    atmosphereCode = world.uwp().code(traveller.UWP.Element.Atmosphere)
    return app.Config.instance().atmosphereTagLevel(atmosphereCode)

def calculateHydrographicsTagLevel(world: traveller.World) -> app.TagLevel:
    hydrographicCode = world.uwp().code(traveller.UWP.Element.Hydrographics)
    return app.Config.instance().hydrographicsTagLevel(hydrographicCode)

def calculatePopulationTagLevel(world: traveller.World) -> app.TagLevel:
    populationCode = world.uwp().code(traveller.UWP.Element.Population)
    return app.Config.instance().populationTagLevel(populationCode)

def calculateGovernmentTagLevel(world: traveller.World) -> app.TagLevel:
    governmentCode = world.uwp().code(traveller.UWP.Element.Government)
    return app.Config.instance().governmentTagLevel(governmentCode)

def calculateLawLevelTagLevel(world: traveller.World) -> app.TagLevel:
    lawLevelCode = world.uwp().code(traveller.UWP.Element.LawLevel)
    return app.Config.instance().lawLevelTagLevel(lawLevelCode)

def calculateTechLevelTagLevel(world: traveller.World) -> app.TagLevel:
    techLevelCode = world.uwp().code(traveller.UWP.Element.TechLevel)
    return app.Config.instance().techLevelTagLevel(techLevelCode)

def calculateBaseTypeTagLevel(baseType: traveller.BaseType) -> app.TagLevel:
    return app.Config.instance().baseTypeTagLevel(baseType)

def calculateTradeCodeTagLevel(tradeCode: traveller.TradeCode) -> app.TagLevel:
    return app.Config.instance().tradeCodeTagLevel(tradeCode)

def calculateResourcesTagLevel(world: traveller.World) -> app.TagLevel:
    resourcesCode = world.economics().code(traveller.Economics.Element.Resources)
    return app.Config.instance().resourcesTagLevel(resourcesCode)

def calculateLabourTagLevel(world: traveller.World) -> app.TagLevel:
    labourCode = world.economics().code(traveller.Economics.Element.Labour)
    return app.Config.instance().labourTagLevel(labourCode)

def calculateInfrastructureTagLevel(world: traveller.World) -> app.TagLevel:
    infrastructureCode = world.economics().code(traveller.Economics.Element.Infrastructure)
    return app.Config.instance().infrastructureTagLevel(infrastructureCode)

def calculateEfficiencyTagLevel(world: traveller.World) -> app.TagLevel:
    efficiencyCode = world.economics().code(traveller.Economics.Element.Efficiency)
    return app.Config.instance().efficiencyTagLevel(efficiencyCode)

def calculateHeterogeneityTagLevel(world: traveller.World) -> app.TagLevel:
    heterogeneityCode = world.culture().code(traveller.Culture.Element.Heterogeneity)
    return app.Config.instance().heterogeneityTagLevel(heterogeneityCode)

def calculateAcceptanceTagLevel(world: traveller.World) -> app.TagLevel:
    acceptanceCode = world.culture().code(traveller.Culture.Element.Acceptance)
    return app.Config.instance().acceptanceTagLevel(acceptanceCode)

def calculateStrangenessTagLevel(world: traveller.World) -> app.TagLevel:
    strangenessCode = world.culture().code(traveller.Culture.Element.Strangeness)
    return app.Config.instance().strangenessTagLevel(strangenessCode)

def calculateSymbolsTagLevel(world: traveller.World) -> app.TagLevel:
    symbolsCode = world.culture().code(traveller.Culture.Element.Symbols)
    return app.Config.instance().symbolsTagLevel(symbolsCode)

def calculateNobilityTagLevel(nobilityType: traveller.NobilityType) -> app.TagLevel:
    return app.Config.instance().nobilityTagLevel(nobilityType)

def calculateAllegianceTagLevel(world: traveller.World) -> app.TagLevel:
    allegianceCode = traveller.AllegianceManager.instance().uniqueAllegianceCode(world)
    return app.Config.instance().allegianceTagLevel(allegianceCode)

def calculateSpectralTagLevel(star: traveller.Star) -> app.TagLevel:
    spectralCode = star.code(traveller.Star.Element.SpectralClass)
    return app.Config.instance().spectralTagLevel(spectralCode)

def calculateLuminosityTagLevel(star: traveller.Star) -> app.TagLevel:
    luminosityCode = star.code(traveller.Star.Element.LuminosityClass)
    return app.Config.instance().luminosityTagLevel(luminosityCode)

def tagColour(tagLevel: app.TagLevel) -> str:
    return app.Config.instance().tagColour(tagLevel)
