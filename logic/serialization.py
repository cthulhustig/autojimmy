import common
import enum
import logic
import json
import packaging
import packaging.version
import traveller
import travellermap
import typing

def serialiseEnum(
        enumValue: enum.Enum
        ) -> typing.Mapping[str, typing.Any]:
    return {'enum': enumValue.name}

def deserialiseEnum(
        type: typing.Type[enum.Enum],
        data: typing.Mapping[str, typing.Any]
        ) -> enum.Enum:
    name = data.get('enum')
    if name == None:
        raise RuntimeError('Enum is missing the name element')

    if name not in type.__members__:
        raise RuntimeError(f'Unknown enum name "{name}"')
    return type.__members__[name]

def serialiseEnumList(
        enumList: typing.Iterable[enum.Enum]
        ) -> typing.Mapping[str, typing.Any]:
    items = []
    for enumValue in enumList:
        items.append(serialiseEnum(enumValue=enumValue))
    return {'enums': items}

def deserialiseEnumList(
        type: typing.Type[enum.Enum],
        data: typing.Mapping[str, typing.Any]
        ) -> typing.Iterable[enum.Enum]:
    items = data.get('enums')
    if items == None:
        raise RuntimeError('Enum list is missing the enums element')

    enumList = []
    for item in items:
        enumList.append(deserialiseEnum(type=type, data=item))
    return enumList

def serialiseWorldFilter(
        worldFilter: logic.WorldFilter
        ) -> typing.Mapping[str, typing.Any]:
    if isinstance(worldFilter, logic.NameFiler):
        return {
            'filterType': 'name',
            'type': serialiseEnum(enumValue=worldFilter.type()),
            'operation': serialiseEnum(enumValue=worldFilter.operation()),
            'value': worldFilter.value()}
    elif isinstance(worldFilter, logic.TagLevelFiler):
        return {
            'filterType': 'tagLevel',
            'operation': serialiseEnum(enumValue=worldFilter.operation()),
            'value': serialiseEnum(enumValue=worldFilter.value())}
    elif isinstance(worldFilter, logic.ZoneFiler):
        return {
            'filterType': 'zone',
            'operation': serialiseEnum(enumValue=worldFilter.operation()),
            'value': serialiseEnum(worldFilter.value())}
    elif isinstance(worldFilter, logic.UWPFilter):
        return {
            'filterType': 'uwp',
            'element': serialiseEnum(enumValue=worldFilter.element()),
            'operation': serialiseEnum(enumValue=worldFilter.operation()),
            'value': worldFilter.value()}
    elif isinstance(worldFilter, logic.EconomicsFilter):
        return {
            'filterType': 'economics',
            'element': serialiseEnum(enumValue=worldFilter.element()),
            'operation': serialiseEnum(enumValue=worldFilter.operation()),
            'value': worldFilter.value()}
    elif isinstance(worldFilter, logic.CultureFilter):
        return {
            'filterType': 'culture',
            'element': serialiseEnum(enumValue=worldFilter.element()),
            'operation': serialiseEnum(enumValue=worldFilter.operation()),
            'value': worldFilter.value()}
    elif isinstance(worldFilter, logic.RefuellingFilter):
        return {
            'filterType': 'refuelling',
            'operation': serialiseEnum(enumValue=worldFilter.operation()),
            'value': serialiseEnumList(enumList=worldFilter.value())}
    elif isinstance(worldFilter, logic.AllegianceFilter):
        return {
            'filterType': 'allegiance',
            'operation': serialiseEnum(enumValue=worldFilter.operation()),
            'value': worldFilter.value()}
    elif isinstance(worldFilter, logic.SophontFilter):
        return {
            'filterType': 'sophont',
            'operation': serialiseEnum(enumValue=worldFilter.operation()),
            'value': worldFilter.value()}
    elif isinstance(worldFilter, logic.BaseFilter):
        return {
            'filterType': 'base',
            'operation': serialiseEnum(enumValue=worldFilter.operation()),
            'value': serialiseEnumList(enumList=worldFilter.value())}
    elif isinstance(worldFilter, logic.NobilityFilter):
        return {
            'filterType': 'nobility',
            'operation': serialiseEnum(enumValue=worldFilter.operation()),
            'value': serialiseEnumList(enumList=worldFilter.value())}
    elif isinstance(worldFilter, logic.RemarksFilter):
        return {
            'filterType': 'remarks',
            'operation': serialiseEnum(enumValue=worldFilter.operation()),
            'value': worldFilter.value()}
    elif isinstance(worldFilter, logic.TradeCodeFilter):
        return {
            'filterType': 'tradeCode',
            'operation': serialiseEnum(enumValue=worldFilter.operation()),
            'value': serialiseEnumList(enumList=worldFilter.value())}
    elif isinstance(worldFilter, logic.PBGFilter):
        return {
            'filterType': 'pbg',
            'element': serialiseEnum(enumValue=worldFilter.element()),
            'operation': serialiseEnum(enumValue=worldFilter.operation()),
            'value': worldFilter.value()}

    raise RuntimeError('Unknown world filter type')

def deserialiseWorldFilter(
        data: typing.Mapping[str, typing.Any]
        ) -> logic.WorldFilter:
    filterType = data.get('filterType')
    if filterType == None:
        raise RuntimeError('World filter is missing the filterType element')

    if filterType == 'name':
        type = data.get('type')
        if not type:
            raise RuntimeError('Name filter is missing the type element')

        operation = data.get('operation')
        if not operation:
            raise RuntimeError('Name filter is missing the operation element')

        value = data.get('value')
        if not value:
            raise RuntimeError('Name filter is missing the value element')

        return logic.NameFiler(
            type=deserialiseEnum(type=logic.NameFiler.Type, data=type),
            operation=deserialiseEnum(type=logic.StringFilterOperation, data=operation),
            value=value)
    elif filterType == 'tagLevel':
        operation = data.get('operation')
        if not operation:
            raise RuntimeError('Tag level filter is missing the operation element')

        value = data.get('value')
        if not value:
            raise RuntimeError('Tag level filter is missing the value element')

        return logic.TagLevelFiler(
            operation=deserialiseEnum(type=logic.ComparisonFilterOperation, data=operation),
            value=deserialiseEnum(type=logic.TagLevel, data=value))
    elif filterType == 'zone':
        operation = data.get('operation')
        if not operation:
            raise RuntimeError('Zone filter is missing the operation element')

        value = data.get('value')
        if not value:
            raise RuntimeError('Zone filter is missing the value element')

        return logic.ZoneFiler(
            operation=deserialiseEnum(type=logic.ComparisonFilterOperation, data=operation),
            value=deserialiseEnum(type=traveller.ZoneType, data=value))
    elif filterType == 'uwp':
        element = data.get('element')
        if not element:
            raise RuntimeError('UWP filter is missing the element element')

        operation = data.get('operation')
        if not operation:
            raise RuntimeError('UWP filter is missing the operation element')

        value = data.get('value')
        if not value:
            raise RuntimeError('UWP filter is missing the value element')

        return logic.UWPFilter(
            element=deserialiseEnum(type=traveller.UWP.Element, data=element),
            operation=deserialiseEnum(type=logic.ComparisonFilterOperation, data=operation),
            value=value)
    elif filterType == 'economics':
        element = data.get('element')
        if not element:
            raise RuntimeError('Economics filter is missing the element element')

        operation = data.get('operation')
        if not operation:
            raise RuntimeError('Economics filter is missing the operation element')

        value = data.get('value')
        if not value:
            raise RuntimeError('Economics filter is missing the value element')

        return logic.EconomicsFilter(
            element=deserialiseEnum(type=traveller.Economics.Element, data=element),
            operation=deserialiseEnum(type=logic.ComparisonFilterOperation, data=operation),
            value=value)
    elif filterType == 'culture':
        element = data.get('element')
        if not element:
            raise RuntimeError('Culture filter is missing the element element')

        operation = data.get('operation')
        if not operation:
            raise RuntimeError('Culture filter is missing the operation element')

        value = data.get('value')
        if not value:
            raise RuntimeError('Culture filter is missing the value element')

        return logic.CultureFilter(
            element=deserialiseEnum(type=traveller.Culture.Element, data=element),
            operation=deserialiseEnum(type=logic.ComparisonFilterOperation, data=operation),
            value=value)
    elif filterType == 'refuelling':
        operation = data.get('operation')
        if not operation:
            raise RuntimeError('Refuelling filter is missing the operation element')

        value = data.get('value')
        if not value:
            raise RuntimeError('Refuelling filter is missing the value element')

        return logic.RefuellingFilter(
            operation=deserialiseEnum(type=logic.ListFilterOperation, data=operation),
            value=deserialiseEnumList(type=logic.RefuellingFilter.Type, data=value))
    elif filterType == 'allegiance':
        operation = data.get('operation')
        if not operation:
            raise RuntimeError('Allegiance filter is missing the operation element')

        value = data.get('value')
        if not value:
            raise RuntimeError('Allegiance filter is missing the value element')

        return logic.AllegianceFilter(
            operation=deserialiseEnum(type=logic.StringFilterOperation, data=operation),
            value=value)
    elif filterType == 'sophont':
        operation = data.get('operation')
        if not operation:
            raise RuntimeError('Sophont filter is missing the operation element')

        value = data.get('value')
        if not value:
            raise RuntimeError('Sophont filter is missing the value element')

        return logic.SophontFilter(
            operation=deserialiseEnum(type=logic.StringFilterOperation, data=operation),
            value=value)
    elif filterType == 'base':
        operation = data.get('operation')
        if not operation:
            raise RuntimeError('Base filter is missing the operation element')

        value = data.get('value')
        if not value:
            raise RuntimeError('Base filter is missing the value element')

        return logic.BaseFilter(
            operation=deserialiseEnum(type=logic.ListFilterOperation, data=operation),
            value=deserialiseEnumList(type=traveller.BaseType, data=value))
    elif filterType == 'nobility':
        operation = data.get('operation')
        if not operation:
            raise RuntimeError('Nobility filter is missing the operation element')

        value = data.get('value')
        if not value:
            raise RuntimeError('Nobility filter is missing the value element')

        return logic.NobilityFilter(
            operation=deserialiseEnum(type=logic.ListFilterOperation, data=operation),
            value=deserialiseEnumList(type=traveller.NobilityType, data=value))
    elif filterType == 'remarks':
        operation = data.get('operation')
        if not operation:
            raise RuntimeError('Remarks filter is missing the operation element')

        value = data.get('value')
        if not value:
            raise RuntimeError('Remarks filter is missing the value element')

        return logic.RemarksFilter(
            operation=deserialiseEnum(type=logic.StringFilterOperation, data=operation),
            value=value)
    elif filterType == 'tradeCode':
        operation = data.get('operation')
        if not operation:
            raise RuntimeError('Trade code filter is missing the operation element')

        value = data.get('value')
        if not value:
            raise RuntimeError('Trade code filter is missing the value element')

        return logic.TradeCodeFilter(
            operation=deserialiseEnum(type=logic.ListFilterOperation, data=operation),
            value=deserialiseEnumList(type=traveller.TradeCode, data=value))
    elif filterType == 'pbg':
        element = data.get('element')
        if not element:
            raise RuntimeError('PBG filter is missing the element element')

        operation = data.get('operation')
        if not operation:
            raise RuntimeError('PBG filter is missing the operation element')

        value = data.get('value')
        if not value:
            raise RuntimeError('PBG filter is missing the value element')

        return logic.PBGFilter(
            element=deserialiseEnum(type=traveller.PBG.Element, data=element),
            operation=deserialiseEnum(type=logic.ComparisonFilterOperation, data=operation),
            value=value)

    raise RuntimeError('Unknown world filter type')

def serialiseWorldFilterList(
        worldFilters: typing.Iterable[logic.WorldFilter]
        ) -> typing.Iterable[typing.Mapping[str, typing.Any]]:
    items = []
    for worldFilter in worldFilters:
        items.append(serialiseWorldFilter(worldFilter=worldFilter))
    return {'worldFilters': items}

def deserialiseWorldFiltersList(
        data: typing.Mapping[str, typing.Any]
        ) -> typing.Iterable[logic.WorldFilter]:
    items = data.get('worldFilters')
    if items == None:
        raise RuntimeError('World filter list is missing the worldFilters element')

    worldFilters = []
    for item in items:
        worldFilters.append(deserialiseWorldFilter(data=item))
    return worldFilters

#
# Jump Route
#
# v1.0 - Initial version that used sector hexes. Support for this
# format was dropped as it's milieu specific so was incompatible
# with recent changes
# v2.0 - Switched from world based to hex based jump routes as part of
# the work for dead space routing. Support for waypoints and berthing
# was added later as part of improvements to jump route import/export.
# They're optional though so didn't require an up tick of the version.
# Calculations are stored using Calculation v1.0 format

_JumpRouteVersion = packaging.version.Version('2.0')

_MilieuToString = {
    travellermap.Milieu.IW: 'IW',
    travellermap.Milieu.M0: 'M0',
    travellermap.Milieu.M990: 'M990',
    travellermap.Milieu.M1105: 'M1105',
    travellermap.Milieu.M1120: 'M1120',
    travellermap.Milieu.M1201: 'M1201',
    travellermap.Milieu.M1248: 'M1248',
    travellermap.Milieu.M1900: 'M1900'}
assert(len(_MilieuToString) == len(travellermap.Milieu))
_StringToMilieu = {v: k for k, v in _MilieuToString.items()}

_RefuellingTypeToString = {
    logic.RefuellingType.Refined: 'refined',
    logic.RefuellingType.Unrefined: 'unrefined',
    logic.RefuellingType.Wilderness: 'wilderness',
    logic.RefuellingType.FuelCache: 'cache',
    logic.RefuellingType.Anomaly: 'anomaly'}
assert(len(_RefuellingTypeToString) == len(logic.RefuellingType))
_StringToRefuellingType = {v: k for k, v in _RefuellingTypeToString.items()}

def _serialiseLogistics(
        logistics: logic.RouteLogistics,
        includeCalculations: bool
        ) -> typing.Dict[str, typing.Any]:
    jsonData = {'milieu': _MilieuToString[logistics.milieu()]}

    if logistics.perJumpOverheads():
        jsonData['overheads'] = common.serialiseCalculation(
            calculation=logistics.perJumpOverheads(),
            includeVersion=False, # Don't include version to avoid bloat, v1.0 is currently assumed
            includeSubcalculations=includeCalculations)

    refuelling = logistics.refuellingPlan()
    if refuelling:
        jsonPitStops = []
        for pitStop in refuelling:
            jsonPitStop = {'index': pitStop.routeIndex()}

            if pitStop.refuellingType():
                jsonPitStop['refuelling'] = _RefuellingTypeToString[pitStop.refuellingType()]

            if pitStop.tonsOfFuel():
                jsonPitStop['fuelAmount'] = common.serialiseCalculation(
                    calculation=pitStop.tonsOfFuel(),
                    includeVersion=False, # Don't include version to avoid bloat, v1.0 is currently assumed
                    includeSubcalculations=includeCalculations)

            if pitStop.fuelCost():
                jsonPitStop['fuelCost'] = common.serialiseCalculation(
                    calculation=pitStop.fuelCost(),
                    includeVersion=False, # Don't include version to avoid bloat, v1.0 is currently assumed
                    includeSubcalculations=includeCalculations)

            if pitStop.berthingCost():
                jsonPitStop['berthingCost'] = common.serialiseCalculation(
                    calculation=pitStop.berthingCost(),
                    includeVersion=False, # Don't include version to avoid bloat, v1.0 is currently assumed
                    includeSubcalculations=includeCalculations)

            jsonPitStops.append(jsonPitStop)

        jsonData['stops'] = jsonPitStops

    return jsonData

def _deserialiseLogistics(
        jsonData: typing.Mapping[str, typing.Any],
        route: logic.JumpRoute
        ) -> logic.RouteLogistics:
    milieu = jsonData.get('milieu')
    if milieu is None:
        raise RuntimeError('Jump route logistics are missing milieu property')
    if not isinstance(milieu, str):
        raise RuntimeError('Jump route logistics milieu property is not a string')
    if milieu not in _StringToMilieu:
        raise RuntimeError(f'Jump route logistics milieu property has invalid value {milieu}')
    milieu = _StringToMilieu[milieu]

    jsonOverheads = jsonData.get('overheads')
    overheads = None
    if jsonOverheads is not None:
        overheads = common.deserialiseCalculation(jsonData=jsonOverheads)

    jsonPitStops = jsonData.get('stops')
    refuelling = None
    if jsonPitStops is not None:
        if not isinstance(jsonPitStops, list):
            raise RuntimeError('Jump route logistics stops property is not a list')

        pitStops = []
        for index, jsonStop in enumerate(jsonPitStops):
            if not isinstance(jsonStop, dict):
                raise RuntimeError(f'Jump route logistics stop {index} is not a dictionary')

            routeIndex = jsonStop.get('index')
            if routeIndex is None:
                raise RuntimeError(f'Jump route logistics stop {index} is missing index property')
            if not isinstance(routeIndex, int):
                raise RuntimeError(f'Jump route logistics stop {index} index property is not an integer')
            if (routeIndex < 0) or (routeIndex > (route.nodeCount() - 1)):
                raise RuntimeError(f'Jump route logistics stop {index} index property is out of range')

            refuellingType = jsonStop.get('refuelling')
            if refuellingType is not None:
                if not isinstance(refuellingType, str):
                    raise RuntimeError(f'Jump route logistics stop {index} refuelling property is not a string')
                if refuellingType not in _StringToRefuellingType:
                    raise RuntimeError(f'Jump route logistics stop {index} refuelling property has invalid value {refuellingType}')
                refuellingType = _StringToRefuellingType[refuellingType]

            fuelAmount = jsonStop.get('fuelAmount')
            if fuelAmount is not None:
                fuelAmount = common.deserialiseCalculation(jsonData=fuelAmount)

            fuelCost = jsonStop.get('fuelCost')
            if fuelCost is not None:
                fuelCost = common.deserialiseCalculation(jsonData=fuelCost)

            berthingCost = jsonStop.get('berthingCost')
            if berthingCost is not None:
                berthingCost = common.deserialiseCalculation(jsonData=berthingCost)

            world = traveller.WorldManager.instance().worldByPosition(
                milieu=milieu,
                hex=route.nodeAt(routeIndex))

            pitStops.append(logic.PitStop(
                routeIndex=routeIndex,
                world=world,
                refuellingType=refuellingType,
                tonsOfFuel=fuelAmount,
                fuelCost=fuelCost,
                berthingCost=berthingCost))

        refuelling = logic.RefuellingPlan(milieu=milieu, pitStops=pitStops)

    return logic.RouteLogistics(
        milieu=milieu,
        jumpRoute=route,
        refuellingPlan=refuelling,
        perJumpOverheads=overheads)

def serialiseJumpRoute(
        route: typing.Union[logic.JumpRoute, logic.RouteLogistics],
        includeCalculations: bool = True
        ) -> typing.Mapping[str, typing.Any]:
    logistics = None
    if isinstance(route, logic.RouteLogistics):
        logistics = route
        route = logistics.jumpRoute()

    jsonRoute = []
    for index, node in enumerate(route.nodes()):
        jsonNode = {
            'absoluteX': node.absoluteX(),
            'absoluteY': node.absoluteY()}

        if route.isWaypoint(index=index):
            jsonNode['waypoint'] = 'true'

        if route.mandatoryBerthing(index=index):
            jsonNode['berthing'] = 'true'

        jsonRoute.append(jsonNode)

    jsonData = {
        'version': str(_JumpRouteVersion),
        'route': jsonRoute}

    jsonLogistics = None
    if logistics:
        jsonLogistics = _serialiseLogistics(
            logistics=logistics,
            includeCalculations=includeCalculations)

    if jsonLogistics:
        jsonData['logistics'] = jsonLogistics

    return jsonData

def deserialiseJumpRoute(
        jsonData: typing.Mapping[str, typing.Any]
        ) -> typing.Union[logic.JumpRoute, logic.RouteLogistics]:
    jsonVersion = jsonData.get('version')
    if jsonVersion is None:
        raise RuntimeError('Jump route is missing the version property')
    if not isinstance(jsonVersion, str):
        raise RuntimeError('Jump route version property is not a string')
    try:
        version = packaging.version.Version(jsonVersion)
    except Exception:
        raise RuntimeError(f'Jump route version property "{jsonVersion}" could not be parsed')

    if version.major != _JumpRouteVersion.major:
        raise RuntimeError(f'Jump route has unsupported file format {version}')

    jsonRoute = jsonData.get('route')
    if jsonRoute is None:
        raise RuntimeError('Jump route is missing the route property')
    if not isinstance(jsonRoute, list):
        raise RuntimeError('Jump route route property is not a list')

    nodes = []
    for index, jsonNode in enumerate(jsonRoute):
        if not isinstance(jsonNode, dict):
            raise RuntimeError(f'Jump route node {index} is not a dictionary')

        absoluteX = jsonNode.get('absoluteX')
        if absoluteX is None:
            raise RuntimeError(f'Jump route node {index} is missing absoluteX property')
        if not isinstance(absoluteX, int):
            raise RuntimeError(f'Jump route node {index} absoluteX property is not a integer')

        absoluteY = jsonNode.get('absoluteY')
        if absoluteY is None:
            raise RuntimeError(f'Jump route node {index} is missing absoluteY property')
        if not isinstance(absoluteY, int):
            raise RuntimeError(f'Jump route node {index} absoluteY property is not a integer')

        nodeHex = travellermap.HexPosition(absoluteX, absoluteY)
        nodeFlags = 0

        waypoint = jsonNode.get('waypoint')
        if waypoint is not None:
            if not isinstance(waypoint, str):
                raise RuntimeError(f'Jump route node {index} waypoint property is not a string')
            try:
                if common.stringToBool(string=waypoint, strict=True):
                    nodeFlags |= logic.JumpRoute.NodeFlags.Waypoint
            except Exception:
                raise RuntimeError(f'Jump route node {index} waypoint property can\'t be converted to a boolean')

        # This indicates if berthing is required for the route that was
        # exported. This is either because required start/finish world
        # berthing was enabled when the jump route was created or it was
        # a waypoint with berthing specified
        berthing = jsonNode.get('berthing')
        if berthing is not None:
            if not isinstance(berthing, str):
                raise RuntimeError(f'Jump route node {index} berthing property is not a string')
            try:
                if common.stringToBool(string=berthing, strict=True):
                    nodeFlags |= logic.JumpRoute.NodeFlags.MandatoryBerthing
            except Exception:
                raise RuntimeError(f'Jump route node {index} berthing property can\'t be converted to a boolean')

        nodes.append((nodeHex, nodeFlags))

    if not nodes:
        raise RuntimeError('Jump route is empty')

    route = logic.JumpRoute(nodes)

    jsonLogistics: typing.Mapping[str, typing.Any] = jsonData.get('logistics')
    logistics = None
    if jsonLogistics:
        logistics = _deserialiseLogistics(jsonData=jsonLogistics, route=route)

    return logistics if logistics else route

def writeJumpRoute(
        route: typing.Union[logic.JumpRoute, logic.RouteLogistics],
        path: str,
        includeCalculations: bool = True
        ) -> None:
    with open(path, 'w', encoding='UTF8') as file:
        json.dump(serialiseJumpRoute(route=route, includeCalculations=includeCalculations), file, indent=4)

def readJumpRoute(path: str) -> typing.Union[logic.JumpRoute, logic.RouteLogistics]:
    with open(path, 'r') as file:
        return deserialiseJumpRoute(jsonData=json.load(file))