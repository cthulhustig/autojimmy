import app
import common
import gui
import html
import logic
import traveller
import travellermap
import typing

ShipTonnageToolTip = gui.createStringToolTip(
    '<p>Ship total tonnage</p>',
    escape=False)
ShipJumpRatingToolTip = gui.createStringToolTip(
    '<p>Ship jump rating</p>',
    escape=False)
ShipFuelCapacityToolTip = gui.createStringToolTip(
    '<p>Total ship capacity usable for jump fuel.</p>'
    '<p>Jump route calculations only take the fuel required for jumping into account. Fuel '
    'required to run reaction drives and power other ships systems must be calculated manually. '
    'It\'s recommended to set the this value to less than the actual max capacity to allow for '
    'this.</p>',
    escape=False)
ShipCurrentFuelToolTip = gui.createStringToolTip(
    '<p>Amount of jump fuel currently in the ship.</p>'
    '<p>Jump route calculations only take the fuel required for jumping into account. Fuel '
    'required to run reaction drives and power other ships systems must be calculated manually. '
    'It\'s recommended to set this value to less than the actual current fuel level to allow for'
    'this.</p>',
    escape=False)
ShipFuelPerParsecToolTip = gui.createStringToolTip(
    '<p>Tons of fuel consumed for each parsec jumped.</p>'
    '<p>Enabling this option allows the specified value to be used instead of the default of 10% '
    'of total ship tonnage.</p>',
    escape=False)
RoutingTypeToolTip = gui.createStringToolTip(
    '<p>Type of routing algorithm to use</p>'
    '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0;">'
    '<li><b>Basic</b> - Basic routing is the fastest type of routing, however '
    'it is also the most primitive. It\'s similar to the routing algorithm '
    'used by Traveller Map, with routes just using the ship jump rating to '
    'determine possible routes. Although the algorithm its self is not fuel '
    'aware, simple fuelling requirements (e.g. only jumping to worlds that '
    'allow wilderness refuelling) can be achieved by adding filters to the '
    'avoid locations list. The main downsides to basic routing are the lack '
    'of control over what type of refuelling you would like to use and the '
    'fact it can\'t generate optimal routes for ships with a fuel capacity '
    'that allows them to make multiple jumps without refuelling.'
    '</li>'
    '<li><b>Fuel Based</b> - Fuel Based routing is a more advanced but slower '
    'algorithm that also takes the ship\'s fuel capacity along with other '
    'refuelling requirements into account in order to generate jump routes '
    'more optimized for the ship and how want to refuel it. As well as this, '
    'it has the added benefit of allowing for the automatic creation of a '
    'refuelling plan that lets you know where along the route to take on fuel '
    'and how much to take on in order to complete the route at the lost cost.'
    '</li>'
    '<li><b>Dead Space</b> - Dead Space routing uses the same algorithm as Fuel '
    'Based routing but with the additional advantage that, if it will result in '
    'a more optimal jump route, it will plot a route using dead space (i.e. '
    'empty hexes on the map). This type of routing generally only makes sense if '
    'your ship has the fuel capacity to make multiple jumps without refuelling.'
    '</li>'
    '</ul>',
    escape=False)
RouteOptimisationToolTip = gui.createStringToolTip(
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
RefuellingStrategyToolTip = gui.createStringToolTip(
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
    'route. If refuelling at a star port that has refined and unrefined fuel, '
    'unrefined fuel costs will be used for logistics calculations.</li>'
    '<li><b>Water Preferred</b> - Ideally refuel by extracting hydrogen from '
    'water or ice, but allow refuelling at star ports if it results in a more '
    'optimal jump route. If refuelling at a star port that has refined and '
    'unrefined fuel, unrefined fuel costs will be used for logistics '
    'calculations.</li>'
    '<li><b>Wilderness Preferred</b> - Ideally refuel by skimming gas giants '
    'or extracting hydrogen from water or ice, but allow refuelling at star '
    'ports if it results in a more optimal jump route. If refuelling at a '
    'star port that has refined and unrefined fuel, unrefined fuel costs will '
    'be used for logistics calculations.</li>'
    '</ul>',
    escape=False)
UseFuelCachesToolTip = gui.createStringToolTip(
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
AnomalyRefuellingToolTip = gui.createStringToolTip(
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
AnomalyFuelCostToolTip = gui.createStringToolTip(
    '<p>Specify the per-ton cost of fuel at anomalies.</p>',
    escape=False)
AnomalyBerthingCostToolTip = gui.createStringToolTip(
    '<p>Specify the cost of berthing at anomalies.</p>',
    escape=False)
IncludeStartBerthingToolTip = gui.createStringToolTip(
    '<p>Include start world berthing cost in logistics calculations</p>',
    escape=False)
IncludeFinishBerthingToolTip = gui.createStringToolTip(
    '<p>Include finish world berthing cost in logistics calculations</p>',
    escape=False)
IncludeLogisticsCostsToolTip = gui.createStringToolTip(
    '<p>Include logistics costs in trade option calculations</p>'
    '<p>The logistics costs of a trade only really come into play in cases where the only reason '
    'to go to the sale world is to sell the trade goods. If you\'re going to the world anyway '
    'and just want some cargo to make some extra profit then logistics costs don\'t make a '
    'difference to the trade profitability and this option can be disabled.<br>'
    'The logistics costs will still be taken into account when calculating the refuelling plan for '
    'the route.</p>',
    escape=False)
IncludeUnprofitableTradesToolTip = gui.createStringToolTip(
    '<p>Include trade options where average dice rolls will result in no profit or a loss</p>',
    escape=False)
PerJumpOverheadsToolTip = gui.createStringToolTip(
    '<p>The overheads accrued each jump</p>' \
    '<p>Used when calculating logistics costs and performing lowest cost route optimisation. '
    'This can be used to allow the jump route calculation to take things like ship mortgage, '
    'ship maintenance and crew salary into account.</p>',
    escape=False)
AvailableFundsToolTip = gui.createStringToolTip(
    'Funds available for trading (including logistics costs if applied).',
    escape=False)
MaxCargoTonnageToolTip = gui.createStringToolTip(
    '<p>The max tonnage of cargo you want to purchase.</p>',
    escape=False)
PlayerBrokerDmToolTip = gui.createStringToolTip('<p>Player\'s broker skill with all modifiers</p>',
                                                escape=False)
PlayerAdminDmToolTip = gui.createStringToolTip('<p>Player\'s admin skill with all modifiers</p>',
                                               escape=False)
PlayerStreetWiseDmToolTip = gui.createStringToolTip(
    '<p>Player\'s street wise skill with all modifiers</p>',
    escape=False)
SellerDmToolTip = gui.createStringToolTip(
    '<p>Seller DM bonus range to use when calculating purchase price ranges</p>',
    escape=False)
BuyerDmToolTip = gui.createStringToolTip(
    '<p>Buyer DM bonus range to use when calculating sale price ranges</p>',
    escape=False)
MgtLocalBrokerToolTip = gui.createStringToolTip(
    '<p>A local broker can be hired to try and get a better price when trading.</p>'
    '<p>The player can choose to hire a local broker with a Broker skill of 1-6. The higher their '
    'skill, the higher the cut of the final trade value they must be paid.<br>'
    '<table border="1" cellpadding="5">' \
    '<tr><th>Broker Skill</th><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td></tr>'
    '<tr><th>Broker Cut</th><td>1%</td><td>2%</td><td>5%</td><td>7%</td><td>10%</td><td>15%</td></tr>'
    '</table></p>',
    escape=False)
Mgt2LocalBrokerToolTip = gui.createStringToolTip(
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
Mgt2022LocalBrokerToolTip = gui.createStringToolTip(
    '<p>A local broker can be hired to try and get a better price when trading.</p>'
    '<p>The base Broker skill of the local broker is 2D/3, they also get a DM+2 for local knowledge '
    'making their effective Broker skill (2D/3) + 2. This means they have a skill range of 2-6. Hiring '
    'a broker costs 10% of the trade value or 20% if hiring a black market fixer.</p>'
    '<p>When hiring a black market fixer, if you roll snake eyes on the 2D before any modifiers, the '
    'broker you hired is some kind of informant and hilarity ensues.</p>',
    escape=False)

def createLogisticsToolTip(
        routeLogistics: logic.RouteLogistics,
        worldTagging: typing.Optional[logic.WorldTagging] = None,
        taggingColours: typing.Optional[app.TaggingColours] = None
        ) -> str:
    jumpRoute = routeLogistics.jumpRoute()
    startHex, _ = jumpRoute.startNode()
    finishHex, _ = jumpRoute.finishNode()
    startString = html.escape(traveller.WorldManager.instance().canonicalHexName(
        milieu=jumpRoute.milieu(),
        hex=startHex))
    finishString = html.escape(traveller.WorldManager.instance().canonicalHexName(
        milieu=jumpRoute.milieu(),
        hex=finishHex))

    toolTip = '<html>'

    if startHex != finishHex:
        toolTip += f'<b>{startString} to {finishString})</b>'
    else:
        toolTip += f'<b>{startString})</b>'
    toolTip += '<ul style="list-style-type:none; margin-left:0px; -qt-list-indent:0;">'

    toolTip += '<li>Distance:</li>'
    toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
    toolTip += f'<li><span>Jumps: {jumpRoute.jumpCount()}</span></li>'
    toolTip += f'<li><span>Parsecs: {jumpRoute.totalParsecs()}</span></li>'
    toolTip += '</ul>'

    toolTip += '<li>Costs:</li>'
    toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'

    refuellingPlan = routeLogistics.refuellingPlan()
    if refuellingPlan:
        fuelTons = refuellingPlan.totalTonsOfFuel()
        fuelCost = refuellingPlan.totalFuelCost()
        toolTip += f'<li><span>Fuel:</span></li>'
        toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
        toolTip += f'<li><span>Tonnage: {fuelTons.value()} tons</span></li>'
        toolTip += f'<li><span>Cost: Cr{fuelCost.value()}</span></li>'
        toolTip += '</ul>'

        berthingCosts = refuellingPlan.totalBerthingCosts()
        toolTip += f'<li><span>Berthing:</span></li>'
        toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
        toolTip += f'<li><span>Range: Cr{berthingCosts.bestCaseValue()} - Cr{berthingCosts.worstCaseValue()}</span></li>'
        toolTip += f'<li><span>Average: Cr{berthingCosts.averageCaseValue()}</span></li>'
        toolTip += '</ul>'

    overheads = routeLogistics.totalOverheads()
    if overheads:
        toolTip += '<li><span>Overheads:</span></li>'
        toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
        toolTip += f'<li><span>Range: Cr{overheads.bestCaseValue()} - Cr{overheads.worstCaseValue()}</span></li>'
        toolTip += f'<li><span>Average: Cr{overheads.averageCaseValue()}</span></li>'
        toolTip += '</ul>'

    totalCosts = routeLogistics.totalCosts()
    toolTip += '<li><span>Total:</span></li>'
    toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
    toolTip += f'<li><span>Range: Cr{totalCosts.bestCaseValue()} - Cr{totalCosts.worstCaseValue()}</span></li>'
    toolTip += f'<li><span>Average: Cr{totalCosts.averageCaseValue()}</span></li>'
    toolTip += '</ul>'

    toolTip += '</ul>'

    toolTip += '<li>Route:</li>'
    toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'

    pitStopMap = {}
    if refuellingPlan:
        for pitStop in refuellingPlan:
            pitStopMap[pitStop.jumpIndex()] = pitStop

    for index, (nodeHex, world) in enumerate(jumpRoute):
        hexString = html.escape('{type}: {name}'.format(
            type='World' if world else 'Dead Space',
            name=traveller.WorldManager.instance().canonicalHexName(milieu=jumpRoute.milieu(), hex=nodeHex)))

        tagLevel = app.TagLevel.Danger # Dead space is tagged as danger
        if world and worldTagging:
            tagLevel = worldTagging.calculateWorldTagLevel(world)
        tagColour = taggingColours.colour(level=tagLevel) if tagLevel and taggingColours else None

        style = f'background-color:#{tagColour}' if tagColour else ''
        toolTip += f'<li><span style="{style}">{hexString}<span></li>'

        if index in pitStopMap:
            pitStop: logic.PitStop = pitStopMap[index]
            toolTip += f'<ul style="list-style-type:none; {gui.TooltipIndentListStyle}">'

            tonsOfFuel = pitStop.tonsOfFuel()
            if tonsOfFuel:
                toolTip += f'<li><span>Refuelling:<span></li>'
                toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
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
                toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'
                toolTip += f'<li><span>Range: Cr{berthingCosts.bestCaseValue()} - Cr{berthingCosts.worstCaseValue()}</span></li>'
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
        toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'

        for string in posScores:
            toolTip += f'<li><span><nobr>{string}</nobr></span></li>'

        toolTip += '</ul>'

    if negScores:
        negScores.sort(key=str.casefold)

        toolTip += '<li>Negative Trade Good Scores:</li>'
        toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'

        for string in negScores:
            toolTip += f'<li><span><nobr>{string}</nobr></span></li>'

        toolTip += '</ul>'

    if quantityModifiers:
        toolTip += '<li>Quantity Modifiers:</li>'
        toolTip += f'<ul style="{gui.TooltipIndentListStyle}">'

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
        includeBaseTypes: typing.Optional[typing.Iterable[traveller.BaseType]] = None,
        worldTagging: typing.Optional[logic.WorldTagging] = None,
        taggingColours: typing.Optional[app.TaggingColours] = None
        ) -> str:
    baseStrings = []
    baseColours = {}
    for baseType in includeBaseTypes if includeBaseTypes else world.bases():
        if includeBaseTypes and not world.hasBase(baseType=baseType):
            # An include list is being used and the world doesn't have the base type
            continue
        baseString = traveller.Bases.description(baseType=baseType)
        baseStrings.append(baseString)

        tagLevel = worldTagging.calculateBaseTypeTagLevel(baseType=baseType) if worldTagging else None
        if tagLevel and taggingColours:
            baseColours[baseString] = taggingColours.colour(level=tagLevel)
    if not baseStrings:
        return ''

    return gui.createListToolTip(
        title='Bases',
        strings=baseStrings,
        stringColours=baseColours)
