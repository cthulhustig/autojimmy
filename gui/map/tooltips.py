import app
import astronomer
import cartographer
import base64
import common
import gui
import html
import logging
import logic
import traveller
import typing

def createHexToolTip(
        universe: astronomer.Universe,
        milieu: astronomer.Milieu,
        hex: astronomer.HexPosition,
        rules: traveller.Rules,
        width: int = 512, # 0 means no fixed width
        worldTagging: typing.Optional[logic.WorldTagging] = None,
        taggingColours: typing.Optional[app.TaggingColours] = None,
        includeHexImage: bool = False,
        # hexImageStyle & hexImageOptions must be supplied if includeHexImage is True
        hexImageStyle: typing.Optional[cartographer.MapStyle] = None,
        hexImageOptions: typing.Optional[typing.Collection[app.MapOption]] = None
        ) -> str:
    world = universe.worldByPosition(
        milieu=milieu,
        hex=hex)
    uwp = world.uwp() if world else None

    formatTaggingStyle = lambda level: '' if not level or not taggingColours else f'background-color:{taggingColours.colour(level=level)}'

    toolTip = '<html>'

    toolTip += '<table>'
    toolTip += '<tr>'

    #
    # Image
    #
    if includeHexImage:
        try:
            tileBytes = gui.generateThumbnail(
                universe=universe,
                milieu=milieu,
                hex=hex,
                width=256,
                height=256,
                linearScale=64,
                style=hexImageStyle,
                options=hexImageOptions)
            if tileBytes:
                tileString = base64.b64encode(tileBytes).decode()
                toolTip += '<td width="256">'
                # https://travellermap.com/doc/api#tile-render-an-arbitrary-rectangle-of-space
                toolTip += f'<p style="vertical-align:middle"><img src=data:image/png;base64,{tileString} width="256" height="256"></p>'
                toolTip += '</td>'
        except Exception as ex:
            logging.error(f'Failed to generate tool tip image for hex {hex}', exc_info=ex)

    widthString = '' if not width else f'width="{width}"'
    toolTip += f'<td style="padding-left:10" {widthString}>'

    #
    # World
    #

    canonicalName = universe.canonicalHexName(
        milieu=milieu,
        hex=hex)
    toolTip += f'<h1>{html.escape(canonicalName)}</h1>'

    if world:
        sectorHex = world.sectorHex()
        subsectorName = world.subsectorName()
    else:
        sectorHex = universe.positionToSectorHex(
            milieu=milieu,
            hex=hex)
        subsector = universe.subsectorByPosition(
            milieu=milieu,
            hex=hex)
        subsectorName = subsector.name() if subsector else 'Unknown'
    toolTip += '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0">'
    toolTip += f'<li>Subsector: {html.escape(subsectorName)}</li>'
    toolTip += f'<li>Sector Hex: {html.escape(sectorHex)}</li>'
    toolTip += f'<li>Sector Position: ({hex.sectorX()}, {hex.sectorY()})</li>'

    if world:
        zone = world.zone()
        if zone:
            tagLevel = worldTagging.calculateZoneTagLevel(world=world) if worldTagging else None
            toolTip += '<li><span style="{style}">Zone: {zone}</span></li>'.format(
                style=formatTaggingStyle(level=tagLevel),
                zone=html.escape(astronomer.zoneTypeName(zone)))

    refuellingTypes = []
    if world:
        if traveller.worldHasStarPortRefuelling(world=world, rules=rules):
            refuellingTypes.append('Star Port ({code})'.format(
                code=uwp.code(astronomer.UWP.Element.StarPort)))
        if traveller.worldHasGasGiantRefuelling(world=world):
            refuellingTypes.append('Gas Giant(s)')
        if traveller.worldHasWaterRefuelling(world=world):
            refuellingTypes.append('Water')
        if world.isFuelCache():
            refuellingTypes.append('Fuel Cache')
        if world.isAnomaly():
            refuellingTypes.append('Anomaly')

        if not refuellingTypes:
            refuellingTypes.append('None')
    else:
        refuellingTypes.append('None (Dead Space)')
    toolTip += '<li><span style="{style}">Refuelling: {types}</span></li>'.format(
        style=formatTaggingStyle(level=None if refuellingTypes else logic.TagLevel.Danger),
        types=html.escape(common.humanFriendlyListString(refuellingTypes)) if refuellingTypes else 'None')

    if world:
        toolTip += '<li><span>Total Worlds: {count}</span></li>'.format(
            count=world.numberOfSystemWorlds() if world.numberOfSystemWorlds() is not None else 'Unknown/Unspecified')

    if world:
        allegiance = world.allegiance()
        allegianceString = 'Unknown'
        if allegiance:
            allegianceCode = allegiance.code()
            allegianceName = allegiance.name()
            allegianceString = '{code} - {name}'.format(
                code=allegianceCode,
                name=allegianceName if allegianceName else 'Unknown')

        tagLevel = worldTagging.calculateAllegianceTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Allegiance: {html.escape(allegianceString)}</span><li>'

        population = world.population()
        toolTip += f'<li><span>Population: {common.formatNumber(population) if population >= 0 else "Unknown"}</span><li>'

        if world.hasOwner():
            try:
                ownerWorld = universe.worldBySectorHex(
                    milieu=milieu,
                    sectorHex=world.ownerSectorHex())
            except Exception:
                ownerWorld = None

            if ownerWorld:
                ownerText = ownerWorld.name(includeSubsector=True)
                tagLevel = worldTagging.calculateWorldTagLevel(world=ownerWorld) if worldTagging else None
            else:
                # We don't know about this world so just display the sector hex and tag it as danger
                ownerText = f'Unknown world at {world.ownerSectorHex()}'
                tagLevel = logic.TagLevel.Danger

            style = formatTaggingStyle(level=tagLevel)
            toolTip += f'<li><span style="{style}">Owner: {html.escape(ownerText)}</span><li>'

        #
        # UWP
        #
        toolTip += f'<li>UWP: {html.escape(uwp.string())}<li>'
        toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'

        tagLevel = worldTagging.calculateStarPortTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Star Port: {uwp.code(astronomer.UWP.Element.StarPort)} - {html.escape(uwp.description(astronomer.UWP.Element.StarPort))}</span></li>'

        tagLevel = worldTagging.calculateWorldSizeTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">World Size: {uwp.code(astronomer.UWP.Element.WorldSize)} - {html.escape(uwp.description(astronomer.UWP.Element.WorldSize))}</span></li>'

        tagLevel = worldTagging.calculateAtmosphereTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Atmosphere: {uwp.code(astronomer.UWP.Element.Atmosphere)} - {html.escape(uwp.description(astronomer.UWP.Element.Atmosphere))}</span></li>'

        tagLevel = worldTagging.calculateHydrographicsTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Hydrographics: {uwp.code(astronomer.UWP.Element.Hydrographics)} - {html.escape(uwp.description(astronomer.UWP.Element.Hydrographics))}</span></li>'

        tagLevel = worldTagging.calculatePopulationTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Population: {uwp.code(astronomer.UWP.Element.Population)} - {html.escape(uwp.description(astronomer.UWP.Element.Population))}</span></li>'

        tagLevel = worldTagging.calculateGovernmentTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Government: {uwp.code(astronomer.UWP.Element.Government)} - {html.escape(uwp.description(astronomer.UWP.Element.Government))}</span></li>'

        tagLevel = worldTagging.calculateLawLevelTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Law Level: {uwp.code(astronomer.UWP.Element.LawLevel)} - {html.escape(uwp.description(astronomer.UWP.Element.LawLevel))}</span></li>'

        tagLevel = worldTagging.calculateTechLevelTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Tech Level: {uwp.code(astronomer.UWP.Element.TechLevel)} ({astronomer.ehexToInteger(value=uwp.code(astronomer.UWP.Element.TechLevel), default="?")}) - {html.escape(uwp.description(astronomer.UWP.Element.TechLevel))}</span></li>'

        toolTip += '</ul>'

        #
        # Economics
        #
        economics = world.economics()
        toolTip += f'<li>Economics: {html.escape(economics.string())}</li>'
        toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'

        tagLevel = worldTagging.calculateResourcesTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Resources: {economics.code(astronomer.Economics.Element.Resources)} - {html.escape(economics.description(astronomer.Economics.Element.Resources))}</span></li>'

        tagLevel = worldTagging.calculateLabourTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Labour: {economics.code(astronomer.Economics.Element.Labour)} - {html.escape(economics.description(astronomer.Economics.Element.Labour))}</span></li>'

        tagLevel = worldTagging.calculateInfrastructureTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Infrastructure: {economics.code(astronomer.Economics.Element.Infrastructure)} - {html.escape(economics.description(astronomer.Economics.Element.Infrastructure))}</span></li>'

        tagLevel = worldTagging.calculateEfficiencyTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Efficiency: {economics.code(astronomer.Economics.Element.Efficiency)} - {html.escape(economics.description(astronomer.Economics.Element.Efficiency))}</span></li>'

        toolTip += '</ul>'

        #
        # Culture
        #
        culture = world.culture()
        toolTip += f'<li>Culture: {html.escape(culture.string())}</li>'
        toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'

        tagLevel = worldTagging.calculateHeterogeneityTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Heterogeneity: {culture.code(astronomer.Culture.Element.Heterogeneity)} - {html.escape(culture.description(astronomer.Culture.Element.Heterogeneity))}</span></li>'

        tagLevel = worldTagging.calculateAcceptanceTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Acceptance: {culture.code(astronomer.Culture.Element.Acceptance)} - {html.escape(culture.description(astronomer.Culture.Element.Acceptance))}</span></li>'

        tagLevel = worldTagging.calculateStrangenessTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Strangeness: {culture.code(astronomer.Culture.Element.Strangeness)} - {html.escape(culture.description(astronomer.Culture.Element.Strangeness))}</span></li>'

        tagLevel = worldTagging.calculateSymbolsTagLevel(world=world) if worldTagging else None
        style = formatTaggingStyle(level=tagLevel)
        toolTip += f'<li><span style="{style}">Symbols: {html.escape(culture.code(astronomer.Culture.Element.Symbols))} - {html.escape(culture.description(astronomer.Culture.Element.Symbols))}</span></li>'

        toolTip += '</ul>'

        #
        # Nobilities
        #
        nobilities = world.nobilities()
        if not nobilities.isEmpty():
            toolTip += f'<li>Nobilities: {html.escape(nobilities.string())}</li>'
            toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
            for nobilityType in nobilities:
                tagLevel = worldTagging.calculateNobilityTagLevel(nobilityType) if worldTagging else None
                style = formatTaggingStyle(level=tagLevel)
                toolTip += f'<li><span style="{style}">{astronomer.Nobilities.code(nobilityType)} - {html.escape(astronomer.Nobilities.description(nobilityType))}</span></li>'
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
                    tagLevel = worldTagging.calculateTradeCodeTagLevel(tradeCode) if worldTagging else None
                    style = formatTaggingStyle(level=tagLevel)
                    toolTip += f'<li><span style="{style}">{html.escape(astronomer.tradeCodeName(tradeCode))} - {html.escape(astronomer.tradeCodeDescription(tradeCode))}</span></li>'
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
        toolTip += f'<li><span>Population Multiplier: {pbg.code(astronomer.PBG.Element.PopulationMultiplier)} ({astronomer.ehexToInteger(value=pbg.code(astronomer.PBG.Element.PopulationMultiplier), default="?")})</span></li>'
        toolTip += f'<li><span>Planetoid Belts: {pbg.code(astronomer.PBG.Element.PlanetoidBelts)} ({astronomer.ehexToInteger(value=pbg.code(astronomer.PBG.Element.PlanetoidBelts), default="?")})</span></li>'
        toolTip += f'<li><span>Gas Giants: {pbg.code(astronomer.PBG.Element.GasGiants)} ({astronomer.ehexToInteger(value=pbg.code(astronomer.PBG.Element.GasGiants), default="?")})</span></li>'
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

                tagLevel = worldTagging.calculateSpectralTagLevel(star) if worldTagging else None
                style = formatTaggingStyle(level=tagLevel)
                toolTip += f'<li><span style="{style}">Spectral Class: {star.code(astronomer.Star.Element.SpectralClass)} - {html.escape(star.description(astronomer.Star.Element.SpectralClass))}</span></li>'
                toolTip += f'<li><span style="{style}">Spectral Scale: {star.code(astronomer.Star.Element.SpectralScale)} - {html.escape(star.description(astronomer.Star.Element.SpectralScale))}</span></li>'

                tagLevel = worldTagging.calculateLuminosityTagLevel(star) if worldTagging else None
                style = formatTaggingStyle(level=tagLevel)
                toolTip += f'<li><span style="{style}">Luminosity Class: {star.code(astronomer.Star.Element.LuminosityClass)} - {html.escape(star.description(astronomer.Star.Element.LuminosityClass))}</span></li>'
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
                tagLevel = worldTagging.calculateBaseTypeTagLevel(base) if worldTagging else None
                style = formatTaggingStyle(level=tagLevel)
                toolTip += f'<li><span style="{style}">{html.escape(astronomer.Bases.description(base))}</span></li>'
            toolTip += '</ul>'

        #
        # Colonies
        #
        if world.hasColony():
            toolTip += '<li>Colonies</li>'
            toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
            for colonySectorHex in world.colonySectorHexes():
                try:
                    colonyWorld = universe.worldBySectorHex(
                        milieu=milieu,
                        sectorHex=colonySectorHex)
                except Exception:
                    colonyWorld = None

                if colonyWorld:
                    worldText = colonyWorld.name(includeSubsector=True)
                    tagLevel = worldTagging.calculateWorldTagLevel(colonyWorld) if worldTagging else None
                else:
                    # We don't know about this world so just display the sector hex and tag it as danger
                    worldText = f'Unknown World at {colonySectorHex}'
                    tagLevel = logic.TagLevel.Danger

                style = formatTaggingStyle(level=tagLevel)
                toolTip += f'<li><span style="{style}">{html.escape(worldText)}</span></li>'
            toolTip += '</ul>'
    toolTip += '</ul>'

    sector = universe.sectorBySectorIndex(
        milieu=milieu,
        index=hex.sectorIndex())
    if sector and sector.sources():
        sources = sector.sources()

        toolTip += '<br>'

        if sources.credits():
            toolTip += '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0">'

            toolTip += '<li><i><u>Sector Credits</u></i></li>'
            toolTip += '<li>'
            # NOTE: Credits are expected to be preformatted html so no escaping
            toolTip += sources.credits()
            toolTip += '</li>'
            toolTip += '</ul>'

        primary = sources.primary()
        if primary:
            toolTip += '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0">'

            toolTip += '<li><i><u>Sector Data</u></i></li>'
            text = ', '.join([s for s in [primary.publication(), primary.author(), primary.publisher()] if s])

            if text or primary.reference():
                toolTip += '<li>'
                if text:
                    toolTip += html.escape(text)
                if primary.reference():
                    if text:
                        toolTip += ' - '
                    toolTip += '<a href="{url}">Source</a>'.format(
                        url=html.escape(primary.reference()))
                toolTip += '</li>'

            toolTip += '</ul>'

        if sources.products():
            toolTip += '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0">'

            toolTip += '<li><i><u>Reference Products</u></i></li>'
            isFirst = True
            for product in sources.products():
                if not product.publication():
                    continue # No publication so no product to mention

                if not isFirst:
                    toolTip += '<li>&nbsp;</li>'
                isFirst = False

                toolTip += '<li>'
                if product.reference():
                    toolTip += '<a href="{url}">{text}</a>'.format(
                        url=html.escape(product.reference()),
                        text=html.escape(product.publication()))
                else:
                    toolTip += html.escape(product.publication())
                toolTip += '</li>'

                if product.author():
                    toolTip += '<li>'
                    toolTip += html.escape(product.author())
                    toolTip += '</li>'

                toolTip += '<li>'
                toolTip += html.escape(product.publisher())
                toolTip += '</li>'

            toolTip += '</ul>'

    toolTip += '</td>'
    toolTip += '</tr>'
    toolTip += '</table>'

    toolTip += '</html>'

    return toolTip
