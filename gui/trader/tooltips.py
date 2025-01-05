import app
import base64
import common
import html
import logging
import logic
import travellermap
import traveller
import typing

# Details of what HTML subset is supported for tooltips
# https://doc.qt.io/qt-5/richtext-html-subset.html

# Over time this has become a little pointless. Its being kept in case I need to add a style sheet to all
# tool tips
def createStringToolTip(
        string: str,
        escape: bool = True
        ) -> str:
    if escape:
        string = html.escape(string)
    return f'<html>{string}</html>'


_IndentListStyle = 'margin-left:15px; -qt-list-indent:0;'

ShipTonnageToolTip = createStringToolTip(
    '<p>Ship total tonnage</p>',
    escape=False)
ShipJumpRatingToolTip = createStringToolTip(
    '<p>Ship jump rating</p>',
    escape=False)
ShipFuelCapacityToolTip = createStringToolTip(
    '<p>Total ship capacity usable for jump fuel.</p>'
    '<p>Jump route calculations only take the fuel required for jumping into account. Fuel '
    'required to run reaction drives and power other ships systems must be calculated manually. '
    'It\'s recommended to set the this value to less than the actual max capacity to allow for '
    'this.</p>',
    escape=False)
ShipCurrentFuelToolTip = createStringToolTip(
    '<p>Amount of jump fuel currently in the ship.</p>'
    '<p>Jump route calculations only take the fuel required for jumping into account. Fuel '
    'required to run reaction drives and power other ships systems must be calculated manually. '
    'It\'s recommended to set this value to less than the actual current fuel level to allow for'
    'this.</p>',
    escape=False)
ShipFuelPerParsecToolTip = createStringToolTip(
    '<p>Tons of fuel consumed for each parsec jumped.</p>'
    '<p>Enabling this option allows the specified value to be used instead of the default of 10% '
    'of total ship tonnage.</p>',
    escape=False)
FreeCargoSpaceToolTip = createStringToolTip(
    '<p>Free cargo space available for purchased trade cargo</p>',
    escape=False)
RouteOptimisationToolTip = createStringToolTip(
    '<p>Type of optimisation to apply when calculating a jump route</p>'
    '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0;">'
    '<li><b>Shortest Distance</b> - A search that finds the route that has the '
    'shortest travel distance and therefore uses the least fuel.</li>'
    '<li><b>Shortest Time</b> - A search that finds the route that has the '
    'lowest number of jumps and therefore requires the shortest time spent in '
    'jump space.</li>'
    '<li><b>Lowest Cost</b> - A search that attempts to find the route with '
    'the lowest logistics costs. It\'s not guaranteed to find the absolute '
    'lowest cost route but it\'s generally pretty good.</li>'
    '</ul>',
    escape=False)
# TODO: This should be reworked as a RoutingType tool tip
FuelBasedRoutingToolTip = createStringToolTip(
    '<p>Turn fuel based route calculation on/off</p>'
    '<p>When fuel based route calculation is enabled, the jump route calculator will use ship '
    'jump/fuel details and world information to generate a route that can be completed using the '
    'type of refuelling specified by the refuelling strategy. Fuel based routing allows for the '
    'generation of a refuelling plan that details where along the route to take on fuel and how '
    'much to take on in order to complete the route with the minimum cost. It also allows the '
    'route calculator to generate more optimised routes for ships that can travel more parsecs '
    'than their jump rating without refuelling.</p>'
    '<p>When fuel based route calculation is disabled, the jump route calculator only uses the '
    'ships jump rating to calculate the route. This method of route calculation can be significantly '
    'faster than fuel based routing, however it\'s not guaranteed that it would be possible to take '
    'on enough fuel along the route to complete it. If you have specific refuelling requirements, '
    'avoid world filters can be used to exclude worlds that don\'t allow the refuelling you need.</p>'
    '<p>The primary reason to disable fuel based route calculation is when you need to create a '
    'route in a sector such as Foreven where world information isn\'t know.</p>',
    escape=False)
RefuellingStrategyToolTip = createStringToolTip(
    '<p>Type of refuelling that\'s desired</p>'
    '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0;">'
    '<li><b>Refined Fuel Only</b> - Only refuel at star ports with refined '
    'fuel.</li>'
    '<li><b>Unrefined Fuel Only</b> - Only refuel at star ports with '
    'unrefined fuel.</li>'
    '<li><b>Gas Giant Only</b> - Only refuel by skimming gas giants.</li>'
    '<li><b>Water Only</b> - Only refuel by extracting hydrogen from water'
    'or ice.</li>'
    '<li><b>Wilderness Only</b> - Only refuel by skimming gas giants or '
    'extracting hydrogen from water or ice.</li>'
    '<li><b>Refined Fuel Preferred</b> - Ideally refuel at star ports with '
    'refined fuel, but allow star ports with only unrefined fuel to be used '
    'if it results in a more optimal jump route.</li>'
    '<li><b>Unrefined Fuel Preferred</b> - Ideally refuel at star ports with '
    'unrefined fuel, but allow star ports with only refined fuel to be used '
    'if it results in a more optimal jump route.</li>'
    '<li><b>Gas Giant Preferred</b> - Ideally refuel by skimming gas giants, '
    'but allow refuelling at star ports if it results in a more optimal jump '
    'route. If refuelling at a star port with refined and unrefined fuel, '
    'unrefined fuel costs will be used for logistics calculations.</li>'
    '<li><b>Water Preferred</b> - Ideally refuel by extracting hydrogen from '
    'water or ice, but allow refuelling at star ports if it results in a more '
    'optimal jump route. If refuelling at a star port with refined and '
    'unrefined fuel, unrefined fuel costs will be used for logistics '
    'calculations.</li>'
    '<li><b>Wilderness Preferred</b> - Ideally refuel by skimming gas giants '
    'or extracting hydrogen from water or ice, but allow refuelling at star '
    'ports if it results in a more optimal jump route. If refuelling at a '
    'star port with refined and unrefined fuel, unrefined fuel costs will be '
    'used for logistics calculations.</li>'
    '</ul>',
    escape=False)
UseFuelCachesToolTip = createStringToolTip(
    '<p>Specify if fuel caches can be used when calculating a jump route.</p>'
    '<p>Fuel Caches are systems that have the {Fuel} remark. These tend '
    'to be unmanned platforms in otherwise dead space. Fuel is free, assuming '
    'you can find them.</p>'
    '<p>At the time of writing, the only fuel caches in the stock Traveller '
    'Map data are the VoidBridges located in Thaku Fung and the Pirian Domain '
    'Fuel Factories located in Datsatl and Gakghang.</p>'
    '<p><i>Note that, if using fuel caches is disabled, a multi-jump route may '
    'still have a stop in a hex containing a fuel cache if the ship can hold '
    'enough fuel to then jump on to the next stop in the route without '
    'refuelling. If you want to completely avoid fuel cache hexes in your jump '
    'route, you can add them to the avoid worlds.</i></p>',
    escape=False)
AnomalyRefuellingToolTip = createStringToolTip(
    '<p>Specify if anomalies can be used for refuelling when calculating a '
    'jump route.</p>'
    '<p>Anomalies are systems that have the {Anomaly} remark. How this '
    'remark is used in the Traveller Map data is a little inconsistent. In '
    'some places (e.g. Chandler Station in Reft) it\'s used for a star port '
    'in dead space where fuel can be purchased for exorbitant prices. '
    'However, in other places (e.g. The Big Wreck in Corridor) it\'s used '
    'for points of interest where it might be possible to scavenge some fuel '
    'but you probably shouldn\'t rely on it.</p>'
    '<p><i>Note that, if using anomalies for refuelling is disabled, a '
    'multi-jump route may still have a stop in a hex containing a fuel cache '
    'if the ship can hold enough fuel to then jump on to the next stop in the '
    'route without refuelling. If you want to completely avoid fuel cache '
    'hexes in your jump route, you can add them to the avoid worlds.</i></p>'
    '<p><i>This setting doesn\'t apply to systems that have the {Anomaly} '
    'and {Fuel} remarks as they are treated as fuel caches.</i></p>',
    escape=False)
AnomalyFuelCostToolTip = createStringToolTip(
    '<p>Specify the per-ton cost of fuel at anomalies.</p>',
    escape=False)
AnomalyBerthingCostToolTip = createStringToolTip(
    '<p>Specify the cost of berthing at anomalies.</p>',
    escape=False)
IncludeStartBerthingToolTip = createStringToolTip(
    '<p>Include start world berthing cost in logistics calculations</p>',
    escape=False)
IncludeFinishBerthingToolTip = createStringToolTip(
    '<p>Include finish world berthing cost in logistics calculations</p>',
    escape=False)
IncludeLogisticsCostsToolTip = createStringToolTip(
    '<p>Include logistics costs in trade option calculations</p>'
    '<p>The logistics costs of a trade only really come into play in cases where the only reason '
    'to go to the sale world is to sell the trade goods. If you\'re going to the world anyway '
    'and just want some cargo to make some extra profit then logistics costs don\'t make a '
    'difference to the trade profitability and this option can be disabled.<br>'
    'The logistics costs will still be taken into account when calculating the refuelling plan for '
    'the route.</p>',
    escape=False)
IncludeUnprofitableTradesToolTip = createStringToolTip(
    '<p>Include trade options where average dice rolls will result in no profit or a loss</p>',
    escape=False)
PerJumpOverheadsToolTip = createStringToolTip(
    '<p>The overheads accrued each jump</p>' \
    '<p>Used when calculating logistics costs and performing lowest cost route optimisation. '
    'This can be used to allow the jump route calculation to take things like ship mortgage, '
    'ship maintenance and crew salary into account.</p>',
    escape=False)
AvailableFundsToolTip = createStringToolTip(
    'Funds available for trading (including logistics costs if applied).',
    escape=False)
PlayerBrokerDmToolTip = createStringToolTip('<p>Player\'s broker skill with all modifiers</p>',
                                            escape=False)
PlayerAdminDmToolTip = createStringToolTip('<p>Player\'s admin skill with all modifiers</p>',
                                           escape=False)
PlayerStreetWiseDmToolTip = createStringToolTip(
    '<p>Player\'s street wise skill with all modifiers</p>',
    escape=False)
SellerDmToolTip = createStringToolTip(
    '<p>Seller DM bonus range to use when calculating purchase price ranges</p>',
    escape=False)
BuyerDmToolTip = createStringToolTip(
    '<p>Buyer DM bonus range to use when calculating sale price ranges</p>',
    escape=False)
MgtLocalBrokerToolTip = createStringToolTip(
    '<p>A local broker can be hired to try and get a better price when trading.</p>'
    '<p>The player can choose to hire a local broker with a Broker skill of 1-6. The higher their '
    'skill, the higher the cut of the final trade value they must be paid.<br>'
    '<table border="1" cellpadding="5">' \
    '<tr><th>Broker Skill</th><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td></tr>'
    '<tr><th>Broker Cut</th><td>1%</td><td>2%</td><td>5%</td><td>7%</td><td>10%</td><td>15%</td></tr>'
    '</table></p>',
    escape=False)
Mgt2LocalBrokerToolTip = createStringToolTip(
    '<p>A local broker can be hired to try and get a better price when trading.</p>'
    '<p>The base Broker skill of a local broker is 1D-2. The trader hiring the broker adds to '
    'this by increasing the percentage of the final trade value that they pay them. Each '
    'DM+1 costs 5% of the trade value or 10% for black market brokers.</p>'
    '<p>The player must pay a standard broker at least 5% for a DM+1 bonus and can pay up '
    'to 20% for a DM+4. A black market broker must be paid at least 10% for DM+1 and can '
    'be paid up to 40% for DM+4. This means, depending on your dice roll and how much of '
    'a cut you\'re willing to give the broker, their skill level can range from 0 to 8.<br>'
    '<table border="1" cellpadding="5">'
    '<tr><th>DM Increase</th><th>Broker Cut<br>(Standard/Black Market)</th><th>Broker Skill Range</th></tr>'
    '<tr><td>+1</td><td>5%/10%</td><td>0-5</td></tr>'
    '<tr><td>+2</td><td>10%/20%</td><td>1-6</td></tr>'
    '<tr><td>+3</td><td>15%/30%</td><td>2-7</td></tr>'
    '<tr><td>+4</td><td>20%/40%</td><td>3-8</td></tr>'
    '</table></p>',
    escape=False)
Mgt2022LocalBrokerToolTip = createStringToolTip(
    '<p>A local broker can be hired to try and get a better price when trading.</p>'
    '<p>The base Broker skill of the local broker is 2D/3, they also get a DM+2 for local knowledge '
    'making their effective Broker skill (2D/3) + 2. This means they have a skill range of 2-6. Hiring '
    'a broker costs 10% of the trade value or 20% if hiring a black market fixer.</p>'
    '<p>When hiring a black market fixer, if you roll snake eyes on the 2D before any modifiers, the '
    'broker you hired is some kind of informant and hilarity ensues.</p>',
    escape=False)

def createListToolTip(
        title: str,
        strings: typing.Iterable[str],
        stringColours: typing.Optional[typing.Dict[str, str]] = None,
        stringIndents: typing.Optional[typing.Dict[str, int]] = None
        ) -> str:
    # This is a hack. Create a list with a single item for the title then have a sub list containing
    # the supplied list entries. This is done as I couldn't figure out another way to prevent a big
    # gap between the title and the list
    toolTip = '<html>'
    toolTip += '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0">'
    toolTip += f'<li>{html.escape(title)}</li>'
    toolTip += f'<ul style="{_IndentListStyle}">'

    for string in strings:
        indent = 0
        if stringIndents and string in stringIndents:
            indent = stringIndents[string]
        if indent:
            for _ in range(indent):
                toolTip += f'<ul style="{_IndentListStyle}">'

        style = None
        if stringColours and string in stringColours:
            style = f'style="background-color:{stringColours[string]}"'
        toolTip += f'<li><span {style}><nobr>{html.escape(string)}</nobr></span></li>'

        if indent:
            for _ in range(indent):
                toolTip += '</ul>'

    toolTip += '</ul>'
    toolTip += '</ul>'
    toolTip += '</html>'

    return toolTip


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
            tileBytes, tileFormat = travellermap.TileClient.instance().tile(
                milieu=app.Config.instance().milieu(),
                style=app.Config.instance().mapStyle(),
                options=app.Config.instance().mapOptions(),
                hex=hex,
                width=256,
                height=256,
                timeout=3)
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
    toolTip += f'<li>Subsector: {html.escape(subsectorName)}<li>'
    toolTip += f'<li>Sector Hex: {html.escape(sectorHex)}<li>'
    toolTip += f'<li>Sector Position: ({hex.sectorX()}, {hex.sectorY()})<li>'

    if world:
        allegianceString = traveller.AllegianceManager.instance().formatAllegianceString(world=world)
        tagLevel = app.calculateAllegianceTagLevel(world=world)
        style = formatStyle(app.tagColour(tagLevel))
        toolTip += f'<li><span style="{style}">Allegiance: {html.escape(allegianceString)}</span><li>'

        population = world.population()
        toolTip += f'<li><span>Population: {common.formatNumber(population) if population >= 0 else "Unknown"}</span><li>'
        toolTip += f'<li><span>Total Worlds: {world.numberOfSystemWorlds()}</span></li>'
        toolTip += f'<li><span>Water Present: {"Yes" if world.waterPresent() else "No"}</span></li>'
        if world.isFuelCache():
            toolTip += '<li><span>Fuel Cache: Yes</span></li>'
        if world.isAnomaly():
            style = formatStyle(app.tagColour(app.TagLevel.Warning))
            toolTip += f'<li><span style="{style}">Anomaly: Yes</span></li>'

        if world.hasOwner():
            try:
                ownerWorld = traveller.WorldManager.instance().world(sectorHex=world.ownerSectorHex())
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
        uwp = world.uwp()
        toolTip += f'<li>UWP: {html.escape(uwp.string())}<li>'
        toolTip += f'<ul style="{_IndentListStyle}">'

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
        toolTip += f'<ul style="{_IndentListStyle}">'

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
        toolTip += f'<ul style="{_IndentListStyle}">'

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
            toolTip += f'<ul style="{_IndentListStyle}">'
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
                toolTip += f'<ul style="{_IndentListStyle}">'
                for tradeCode in tradeCodes:
                    tagLevel = app.calculateTradeCodeTagLevel(tradeCode)
                    style = formatStyle(app.tagColour(tagLevel))
                    toolTip += f'<li><span style="{style}">{html.escape(traveller.tradeCodeName(tradeCode))} - {html.escape(traveller.tradeCodeDescription(tradeCode))}</span></li>'
                toolTip += '</ul>'

            sophonts = remarks.sophonts()
            if sophonts:
                toolTip += '<li>Sophonts:</li>'
                toolTip += f'<ul style="{_IndentListStyle}">'
                for sophont in sophonts:
                    percentage = remarks.sophontPercentage(sophont=sophont)
                    toolTip += f'<li><span>{html.escape(sophont)} - {percentage}%</span></li>'
                toolTip += '</ul>'

        #
        # PBG
        #
        pbg = world.pbg()
        toolTip += f'<li><span>PBG: {html.escape(pbg.string())}</span></li>'
        toolTip += f'<ul style="{_IndentListStyle}">'
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

            toolTip += f'<ul style="{_IndentListStyle}">'
            for star in stellar:
                toolTip += f'<li><span">Classification: {html.escape(star.string())}</span></li>'
                toolTip += f'<ul style="{_IndentListStyle}">'

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
            toolTip += f'<ul style="{_IndentListStyle}">'
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
            toolTip += f'<ul style="{_IndentListStyle}">'
            for colonySectorHex in world.colonySectorHexes():
                try:
                    colonyWorld = traveller.WorldManager.instance().world(sectorHex=colonySectorHex)
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

def createLogisticsToolTip(routeLogistics: logic.RouteLogistics) -> str:
    jumpRoute = routeLogistics.jumpRoute()
    startHex, _ = jumpRoute.startNode()
    finishHex, _ = jumpRoute.finishNode()
    startString = html.escape(traveller.WorldManager.instance().canonicalHexName(hex=startHex))
    finishString = html.escape(traveller.WorldManager.instance().canonicalHexName(hex=finishHex))

    toolTip = '<html>'

    if startHex != finishHex:
        toolTip += f'<b>{startString} to {finishString})</b>'
    else:
        toolTip += f'<b>{startString})</b>'
    toolTip += '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0;">'

    toolTip += '<li>Distance:</li>'
    toolTip += f'<ul style="{_IndentListStyle}">'
    toolTip += f'<li><span>Jumps: {jumpRoute.jumpCount()}</span></li>'
    toolTip += f'<li><span>Parsecs: {jumpRoute.totalParsecs()}</span></li>'
    toolTip += '</ul>'

    toolTip += '<li>Costs:</li>'
    toolTip += f'<ul style="{_IndentListStyle}">'

    refuellingPlan = routeLogistics.refuellingPlan()
    if refuellingPlan:
        fuelTons = refuellingPlan.totalTonsOfFuel()
        fuelCost = refuellingPlan.totalFuelCost()
        toolTip += f'<li><span>Fuel:</span></li>'
        toolTip += f'<ul style="{_IndentListStyle}">'
        toolTip += f'<li><span>Tonnage: {fuelTons.value()} tons</span></li>'
        toolTip += f'<li><span>Cost: Cr{fuelCost.value()}</span></li>'
        toolTip += '</ul>'

        berthingCosts = refuellingPlan.totalBerthingCosts()
        toolTip += f'<li><span>Berthing:</span></li>'
        toolTip += f'<ul style="{_IndentListStyle}">'
        toolTip += f'<li><span>Range: Cr{berthingCosts.worstCaseValue()} - Cr{berthingCosts.bestCaseValue()}</span></li>'
        toolTip += f'<li><span>Average: Cr{berthingCosts.averageCaseValue()}</span></li>'
        toolTip += '</ul>'

    overheads = routeLogistics.totalOverheads()
    if overheads:
        toolTip += '<li><span>Overheads:</span></li>'
        toolTip += f'<ul style="{_IndentListStyle}">'
        toolTip += f'<li><span>Range: Cr{overheads.worstCaseValue()} - Cr{overheads.bestCaseValue()}</span></li>'
        toolTip += f'<li><span>Average: Cr{overheads.averageCaseValue()}</span></li>'
        toolTip += '</ul>'

    totalCosts = routeLogistics.totalCosts()
    toolTip += '<li><span>Total:</span></li>'
    toolTip += f'<ul style="{_IndentListStyle}">'
    toolTip += f'<li><span>Range: Cr{totalCosts.worstCaseValue()} - Cr{totalCosts.bestCaseValue()}</span></li>'
    toolTip += f'<li><span>Average: Cr{totalCosts.averageCaseValue()}</span></li>'
    toolTip += '</ul>'

    toolTip += '</ul>'

    toolTip += '<li>Route:</li>'
    toolTip += f'<ul style="{_IndentListStyle}">'

    pitStopMap = {}
    if refuellingPlan:
        for pitStop in refuellingPlan:
            pitStopMap[pitStop.jumpIndex()] = pitStop

    for index, (nodeHex, world) in enumerate(jumpRoute):
        hexString = html.escape('{type}: {name}'.format(
            type='World' if world else 'Dead Space',
            name=traveller.WorldManager.instance().canonicalHexName(hex=nodeHex)))
        tagColour = app.tagColour(
            app.calculateWorldTagLevel(world)
            if world else
            app.TagLevel.Danger) # Dead space is tagged as danger
        style = ""
        if tagColour:
            style = f'background-color:#{tagColour}'
        toolTip += f'<li><span style="{style}">{hexString}<span></li>'

        if index in pitStopMap:
            pitStop: logic.PitStop = pitStopMap[index]
            toolTip += f'<ul style="list-style-type:none; {_IndentListStyle}">'

            tonsOfFuel = pitStop.tonsOfFuel()
            if tonsOfFuel:
                toolTip += f'<li><span>Refuelling:<span></li>'
                toolTip += f'<ul style="{_IndentListStyle}">'
                if pitStop.refuellingType() == logic.RefuellingType.Refined:
                    toolTip += f'<li><span>Type: Star Port (Refined)<span></li>'
                elif pitStop.refuellingType() == logic.RefuellingType.Unrefined:
                    toolTip += f'<li><span>Type: Star Port (Unrefined)<span></li>'
                elif pitStop.refuellingType() == logic.RefuellingType.Wilderness:
                    toolTip += '<li><span>Type: Wilderness<span></li>'
                elif pitStop.refuellingType() == logic.RefuellingType.FuelCache:
                    toolTip += '<li><span>Type: Fuel Cache<span></li>'
                elif pitStop.refuellingType() == logic.RefuellingType.Anomaly:
                    toolTip += '<li><span>Type: Anomaly<span></li>'
                else:
                    toolTip += '<li><span>Type: Unknown<span></li>'
                toolTip += f'<li><span>Tonnage: {tonsOfFuel.value()} tons<span></li>'
                fuelCost = pitStop.fuelCost()
                if fuelCost:
                    toolTip += f'<li><span>Cost: Cr{fuelCost.value()}<span></li>'
                toolTip += '</ul>'

            berthingCosts = pitStop.berthingCost()
            if berthingCosts:
                toolTip += f'<li><span>Berthing:</span></li>'
                toolTip += f'<ul style="{_IndentListStyle}">'
                toolTip += f'<li><span>Range: Cr{berthingCosts.worstCaseValue()} - Cr{berthingCosts.bestCaseValue()}</span></li>'
                toolTip += f'<li><span>Average: Cr{berthingCosts.averageCaseValue()}</span></li>'
                toolTip += '</ul>'

            toolTip += '</ul>'

    toolTip += '</ul>'

    toolTip += '</ul>'
    toolTip += '</html>'

    return toolTip

def createPurchaseTradeScoreToolTip(tradeScore: logic.TradeScore) -> str:
    return _createTradeScoreToolTip(
        tradeScores=tradeScore.purchaseScores(),
        quantityModifiers=tradeScore.quantityModifiers(),
        totalScore=tradeScore.totalPurchaseScore())

def createSaleTradeScoreToolTip(tradeScore: logic.TradeScore) -> str:
    return _createTradeScoreToolTip(
        tradeScores=tradeScore.saleScores(),
        quantityModifiers=tradeScore.quantityModifiers(),
        totalScore=tradeScore.totalSaleScore())

def _createTradeScoreToolTip(
        tradeScores: typing.Mapping[traveller.TradeGood, common.ScalarCalculation],
        quantityModifiers: typing.Iterable[common.ScalarCalculation],
        totalScore: common.ScalarCalculation
        ) -> str:
    posScores = []
    negScores = []
    for tradeGood, tradeScore in tradeScores.items():
        score = tradeScore.value()
        string = '{name}: {value}'.format(
            name=tradeGood.name(),
            value=common.formatNumber(number=score, alwaysIncludeSign=True))
        if score > 0:
            posScores.append(string)
        elif score < 0:
            negScores.append(string)

    toolTip = '<html>'
    toolTip += '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0">'

    if posScores:
        posScores.sort(key=str.casefold)

        toolTip += '<li>Positive Trade Good Scores:</li>'
        toolTip += f'<ul style="{_IndentListStyle}">'

        for string in posScores:
            toolTip += f'<li><span><nobr>{string}</nobr></span></li>'

        toolTip += '</ul>'

    if negScores:
        negScores.sort(key=str.casefold)

        toolTip += '<li>Negative Trade Good Scores:</li>'
        toolTip += f'<ul style="{_IndentListStyle}">'

        for string in negScores:
            toolTip += f'<li><span><nobr>{string}</nobr></span></li>'

        toolTip += '</ul>'

    if quantityModifiers:
        toolTip += '<li>Quantity Modifiers:</li>'
        toolTip += f'<ul style="{_IndentListStyle}">'

        for modifier in quantityModifiers:
            toolTip += '<li><span><nobr>{name}: {value}</nobr></span></li>'.format(
                name=modifier.name(),
                value=common.formatNumber(number=modifier.value(), alwaysIncludeSign=True))

        toolTip += '</ul>'

    toolTip += '<li>Total Score: {value}</li>'.format(
        value=common.formatNumber(number=totalScore.value(), alwaysIncludeSign=True))

    toolTip += '</ul>'

    return toolTip

def createBasesToolTip(
        world: traveller.World,
        includeBaseTypes: typing.Optional[typing.Iterable[traveller.BaseType]] = None
        ) -> str:
    baseStrings = []
    baseColours = {}
    for baseType in includeBaseTypes if includeBaseTypes else world.bases():
        if includeBaseTypes and not world.hasBase(baseType=baseType):
            # An include list is being used and the world doesn't have the base type
            continue
        baseString = traveller.Bases.description(baseType=baseType)
        baseStrings.append(baseString)

        tagLevel = app.calculateBaseTypeTagLevel(baseType=baseType)
        if tagLevel:
            baseColours[baseString] = app.tagColour(tagLevel=tagLevel)
    if not baseStrings:
        return ''

    return createListToolTip(
        title='Bases',
        strings=baseStrings,
        stringColours=baseColours)
