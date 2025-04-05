import app
import base64
import common
import gui
import html
import logging
import travellermap
import traveller
import typing

_DisableWorldToolTipImages = False
def createHexToolTip(
        hex: typing.Union[travellermap.HexPosition, traveller.World],
        noThumbnail: bool = False,
        width: int = 512 # 0 means no fixed width
        ) -> str:
    global _DisableWorldToolTipImages

    worldManager = traveller.WorldManager.instance()

    if isinstance(hex, traveller.World):
        world = hex
        hex = world.hex()
    else:
        world = worldManager.worldByPosition(hex=hex)
    uwp = world.uwp() if world else None

    formatStyle = lambda tagColour: \
        '' if not tagColour \
        else f'background-color:{tagColour}'

    toolTip = '<html>'

    toolTip += '<table>'
    toolTip += '<tr>'

    #
    # Image
    #
    if not noThumbnail and \
            app.Config.instance().showToolTipImages() and \
            not _DisableWorldToolTipImages:
        try:
            tileBytes, tileFormat = gui.generateThumbnail(hex=hex, width=256, height=256)
            if tileBytes:
                mineType = travellermap.mapFormatToMimeType(tileFormat)
                tileString = base64.b64encode(tileBytes).decode()
                toolTip += '<td width="256">'
                # https://travellermap.com/doc/api#tile-render-an-arbitrary-rectangle-of-space
                toolTip += f'<p style="vertical-align:middle"><img src=data:{mineType};base64,{tileString} width="256" height="256"></p>'
                toolTip += '</td>'
        except Exception as ex:
            logging.error(f'Failed to retrieve tool tip image for hex {hex}', exc_info=ex)
            if isinstance(ex, TimeoutError):
                logging.warning(f'Showing world images in tool tips has been temporarily disabled')
                _DisableWorldToolTipImages = True

    widthString = '' if not width else f'width="{width}"'
    toolTip += f'<td style="padding-left:10" {widthString}>'

    #
    # World
    #

    canonicalName = traveller.WorldManager.instance().canonicalHexName(hex=hex)
    toolTip += f'<h1>{html.escape(canonicalName)}</h1>'

    if world:
        sectorHex = world.sectorHex()
        subsectorName = world.subsectorName()
    else:
        try:
            sectorHex = worldManager.positionToSectorHex(hex=hex)
        except:
            sectorHex = 'Unknown'
        subsector = worldManager.subsectorByPosition(hex=hex)
        subsectorName = subsector.name() if subsector else 'Unknown'
    toolTip += '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0">'
    toolTip += f'<li>Subsector: {html.escape(subsectorName)}</li>'
    toolTip += f'<li>Sector Hex: {html.escape(sectorHex)}</li>'
    toolTip += f'<li>Sector Position: ({hex.sectorX()}, {hex.sectorY()})</li>'

    zone = world.zone()
    if zone:
        zoneTag = None
        if zone is traveller.ZoneType.RedZone or zone is traveller.ZoneType.Forbidden:
            zoneTag = app.TagLevel.Danger
        elif zone is traveller.ZoneType.AmberZone or zone is traveller.ZoneType.Unabsorbed:
            zoneTag = app.TagLevel.Warning

        toolTip += '<li><span style="{style}">Zone: {zone}</span></li>'.format(
            style='' if not zoneTag else formatStyle(app.tagColour(zoneTag)),
            zone=html.escape(traveller.zoneTypeName(zone)))

    refuellingTypes = []
    if world:
        if world.hasStarPortRefuelling(rules=app.Config.instance().rules()):
            refuellingTypes.append('Star Port ({code})'.format(
                code=uwp.code(traveller.UWP.Element.StarPort)))
        if world.hasGasGiantRefuelling():
            refuellingTypes.append('Gas Giant(s)')
        if world.hasWaterRefuelling():
            refuellingTypes.append('Water')
        if world.isFuelCache():
            refuellingTypes.append('Fuel Cache')
        if world.isAnomaly():
            refuellingTypes.append('Anomaly')
    toolTip += '<li><span style="{style}">Refuelling: {types}</span></li>'.format(
        style='' if refuellingTypes else formatStyle(app.tagColour(app.TagLevel.Warning)),
        types=html.escape(common.humanFriendlyListString(refuellingTypes)) if refuellingTypes else 'None')
    toolTip += '<li><span>Total Worlds: {count}</span></li>'.format(
        count=world.numberOfSystemWorlds() if world else 0)

    if world:
        allegianceString = traveller.AllegianceManager.instance().formatAllegianceString(
            allegianceCode=world.allegiance(),
            sectorName=world.sectorName())
        tagLevel = app.calculateAllegianceTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Allegiance: {html.escape(allegianceString)}</span><li>'

        population = world.population()
        toolTip += f'<li><span>Population: {common.formatNumber(population) if population >= 0 else "Unknown"}</span><li>'

        if world.hasOwner():
            try:
                ownerWorld = traveller.WorldManager.instance().worldBySectorHex(sectorHex=world.ownerSectorHex())
            except Exception:
                ownerWorld = None

            if ownerWorld:
                ownerText = ownerWorld.name(includeSubsector=True)
                tagLevel = app.calculateWorldTagLevel(world=ownerWorld)
            else:
                # We don't know about this world so just display the sector hex and tag it as danger
                ownerText = f'Unknown world at {world.ownerSectorHex()}'
                tagLevel = app.TagLevel.Danger

            style = formatStyle(app.tagColour(tagLevel))
            toolTip += f'<li><span style="{style}">Owner: {html.escape(ownerText)}</span><li>'

        #
        # UWP
        #
        toolTip += f'<li>UWP: {html.escape(uwp.string())}<li>'
        toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'

        tagLevel = app.calculateStarPortTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Star Port: {uwp.code(traveller.UWP.Element.StarPort)} - {html.escape(uwp.description(traveller.UWP.Element.StarPort))}</span></li>'

        tagLevel = app.calculateWorldSizeTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">World Size: {uwp.code(traveller.UWP.Element.WorldSize)} - {html.escape(uwp.description(traveller.UWP.Element.WorldSize))}</span></li>'

        tagLevel = app.calculateAtmosphereTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Atmosphere: {uwp.code(traveller.UWP.Element.Atmosphere)} - {html.escape(uwp.description(traveller.UWP.Element.Atmosphere))}</span></li>'

        tagLevel = app.calculateHydrographicsTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Hydrographics: {uwp.code(traveller.UWP.Element.Hydrographics)} - {html.escape(uwp.description(traveller.UWP.Element.Hydrographics))}</span></li>'

        tagLevel = app.calculatePopulationTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Population: {uwp.code(traveller.UWP.Element.Population)} - {html.escape(uwp.description(traveller.UWP.Element.Population))}</span></li>'

        tagLevel = app.calculateGovernmentTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Government: {uwp.code(traveller.UWP.Element.Government)} - {html.escape(uwp.description(traveller.UWP.Element.Government))}</span></li>'

        tagLevel = app.calculateLawLevelTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Law Level: {uwp.code(traveller.UWP.Element.LawLevel)} - {html.escape(uwp.description(traveller.UWP.Element.LawLevel))}</span></li>'

        tagLevel = app.calculateTechLevelTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Tech Level: {uwp.code(traveller.UWP.Element.TechLevel)} ({traveller.ehexToInteger(value=uwp.code(traveller.UWP.Element.TechLevel), default="?")}) - {html.escape(uwp.description(traveller.UWP.Element.TechLevel))}</span></li>'

        toolTip += '</ul>'

        #
        # Economics
        #
        economics = world.economics()
        toolTip += f'<li>Economics: {html.escape(economics.string())}</li>'
        toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'

        tagLevel = app.calculateResourcesTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Resources: {economics.code(traveller.Economics.Element.Resources)} - {html.escape(economics.description(traveller.Economics.Element.Resources))}</span></li>'

        tagLevel = app.calculateLabourTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Labour: {economics.code(traveller.Economics.Element.Labour)} - {html.escape(economics.description(traveller.Economics.Element.Labour))}</span></li>'

        tagLevel = app.calculateInfrastructureTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Infrastructure: {economics.code(traveller.Economics.Element.Infrastructure)} - {html.escape(economics.description(traveller.Economics.Element.Infrastructure))}</span></li>'

        tagLevel = app.calculateEfficiencyTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Efficiency: {economics.code(traveller.Economics.Element.Efficiency)} - {html.escape(economics.description(traveller.Economics.Element.Efficiency))}</span></li>'

        toolTip += '</ul>'

        #
        # Culture
        #
        culture = world.culture()
        toolTip += f'<li>Culture: {html.escape(culture.string())}</li>'
        toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'

        tagLevel = app.calculateHeterogeneityTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Heterogeneity: {culture.code(traveller.Culture.Element.Heterogeneity)} - {html.escape(culture.description(traveller.Culture.Element.Heterogeneity))}</span></li>'

        tagLevel = app.calculateAcceptanceTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Acceptance: {culture.code(traveller.Culture.Element.Acceptance)} - {html.escape(culture.description(traveller.Culture.Element.Acceptance))}</span></li>'

        tagLevel = app.calculateStrangenessTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Strangeness: {culture.code(traveller.Culture.Element.Strangeness)} - {html.escape(culture.description(traveller.Culture.Element.Strangeness))}</span></li>'

        tagLevel = app.calculateSymbolsTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Symbols: {html.escape(culture.code(traveller.Culture.Element.Symbols))} - {html.escape(culture.description(traveller.Culture.Element.Symbols))}</span></li>'

        toolTip += '</ul>'

        #
        # Nobilities
        #
        nobilities = world.nobilities()
        if not nobilities.isEmpty():
            toolTip += f'<li>Nobilities: {html.escape(nobilities.string())}</li>'
            toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
            for nobilityType in nobilities:
                tagLevel = app.calculateNobilityTagLevel(nobilityType)
                style = formatStyle(app.tagColour(tagLevel))
                toolTip += f'<li><span style="{style}">{traveller.Nobilities.code(nobilityType)} - {html.escape(traveller.Nobilities.description(nobilityType))}</span></li>'
            toolTip += '</ul>'

        #
        # Remarks
        #
        remarks = world.remarks()
        if not remarks.isEmpty():
            toolTip += f'<li>Remarks: {html.escape(remarks.string())}</li>'

            tradeCodes = remarks.tradeCodes()
            if tradeCodes:
                toolTip += '<li>Trade Codes:</li>'
                toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
                for tradeCode in tradeCodes:
                    tagLevel = app.calculateTradeCodeTagLevel(tradeCode)
                    style = formatStyle(app.tagColour(tagLevel))
                    toolTip += f'<li><span style="{style}">{html.escape(traveller.tradeCodeName(tradeCode))} - {html.escape(traveller.tradeCodeDescription(tradeCode))}</span></li>'
                toolTip += '</ul>'

            sophonts = remarks.sophonts()
            if sophonts:
                toolTip += '<li>Sophonts:</li>'
                toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
                for sophont in sophonts:
                    percentage = remarks.sophontPercentage(sophont=sophont)
                    toolTip += f'<li><span>{html.escape(sophont)} - {percentage}%</span></li>'
                toolTip += '</ul>'

        #
        # PBG
        #
        pbg = world.pbg()
        toolTip += f'<li><span>PBG: {html.escape(pbg.string())}</span></li>'
        toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
        toolTip += f'<li><span>Population Multiplier: {pbg.code(traveller.PBG.Element.PopulationMultiplier)} ({traveller.ehexToInteger(value=pbg.code(traveller.PBG.Element.PopulationMultiplier), default="?")})</span></li>'
        toolTip += f'<li><span>Planetoid Belts: {pbg.code(traveller.PBG.Element.PlanetoidBelts)} ({traveller.ehexToInteger(value=pbg.code(traveller.PBG.Element.PlanetoidBelts), default="?")})</span></li>'
        toolTip += f'<li><span>Gas Giants: {pbg.code(traveller.PBG.Element.GasGiants)} ({traveller.ehexToInteger(value=pbg.code(traveller.PBG.Element.GasGiants), default="?")})</span></li>'
        toolTip += '</ul>'

        #
        # Stellar
        #
        stellar = world.stellar()
        if not stellar.isEmpty():
            toolTip += f'<li><span>Stars: {html.escape(stellar.string())}</span></li>'

            toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
            for star in stellar:
                toolTip += f'<li><span">Classification: {html.escape(star.string())}</span></li>'
                toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'

                tagLevel = app.calculateSpectralTagLevel(star)
                style = formatStyle(app.tagColour(tagLevel))
                toolTip += f'<li><span style="{style}">Spectral Class: {star.code(traveller.Star.Element.SpectralClass)} - {html.escape(star.description(traveller.Star.Element.SpectralClass))}</span></li>'
                toolTip += f'<li><span style="{style}">Spectral Scale: {star.code(traveller.Star.Element.SpectralScale)} - {html.escape(star.description(traveller.Star.Element.SpectralScale))}</span></li>'

                tagLevel = app.calculateLuminosityTagLevel(star)
                style = formatStyle(app.tagColour(tagLevel))
                toolTip += f'<li><span style="{style}">Luminosity Class: {star.code(traveller.Star.Element.LuminosityClass)} - {html.escape(star.description(traveller.Star.Element.LuminosityClass))}</span></li>'
                toolTip += '</ul>'
            toolTip += '</ul>'

        #
        # Bases
        #
        bases = world.bases()
        if not bases.isEmpty():
            toolTip += f'<li>Bases: {html.escape(bases.string())}</li>'
            toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
            for base in bases:
                tagLevel = app.calculateBaseTypeTagLevel(base)
                style = formatStyle(app.tagColour(tagLevel))
                toolTip += f'<li><span style="{style}">{html.escape(traveller.Bases.description(base))}</span></li>'
            toolTip += '</ul>'

        #
        # Colonies
        #
        if world.hasColony():
            toolTip += '<li>Colonies</li>'
            toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
            for colonySectorHex in world.colonySectorHexes():
                try:
                    colonyWorld = traveller.WorldManager.instance().worldBySectorHex(sectorHex=colonySectorHex)
                except Exception:
                    colonyWorld = None

                if colonyWorld:
                    worldText = colonyWorld.name(includeSubsector=True)
                    tagLevel = app.calculateWorldTagLevel(colonyWorld)
                else:
                    # We don't know about this world so just display the sector hex and tag it as danger
                    worldText = f'Unknown World at {colonySectorHex}'
                    tagLevel = app.TagLevel.Danger

                style = formatStyle(app.tagColour(tagLevel))
                toolTip += f'<li><span style="{style}">{html.escape(worldText)}</span></li>'
            toolTip += '</ul>'

    toolTip += '</ul>'

    toolTip += '</td>'
    toolTip += '</tr>'
    toolTip += '</table>'
    toolTip += '</html>'

    return toolTip
