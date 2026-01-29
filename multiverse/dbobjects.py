import common
import typing
import uuid

# TODO: There are some of the uses of string validation that set allow empty to false but
# really it could happen (e.g. if an attribute is specified in the metadata but the value
# is empty). The converter should probably force empty strings to be None for consistency.
# It might also make sense if the survey parsing code replaced empty strings with none
# when generating the raw objects (metadata, sectors and stock sophonts & allegiances)

# TODO: There is a duplicate of each of these in the converter code, the should be shared
_ValidLineStyles = set(['solid', 'dashed', 'dotted'])
_ValidLabelSizes = set(['small', 'large'])

class DbObject(object):
    def __init__(
            self,
            id: typing.Optional[str] = None, # None means allocate an id
            ) -> None:
        common.validateOptionalStr(name='id', value=id, allowEmpty=False)

        super().__init__()
        self._id = id if id is not None else str(uuid.uuid4())

    def id(self) -> str:
        return self._id

class DbUniverseObject(DbObject):
    def __init__(
            self,
            id: typing.Optional[str] = None, # None means allocate an id
            universeId: typing.Optional[str] = None
            ) -> None:
        common.validateOptionalStr(name='universeId', value=universeId, allowEmpty=False)

        super().__init__(id=id)
        self._universeId = universeId

    def universeId(self) -> None:
        return self._universeId

    def setUniverseId(self, universeId: str) -> None:
        common.validateOptionalStr(name='universeId', value=universeId, allowEmpty=False)
        self._universeId = universeId

class DbSectorObject(DbObject):
    def __init__(
            self,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        common.validateOptionalStr(name='sectorId', value=sectorId, allowEmpty=False)

        super().__init__(id=id)
        self._sectorId = sectorId

    def sectorId(self) -> None:
        return self._sectorId

    def setSectorId(self, sectorId: str) -> None:
        common.validateOptionalStr(name='sectorId', value=sectorId, allowEmpty=False)
        self._sectorId = sectorId

class DbSystemObject(DbObject):
    def __init__(
            self,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        common.validateOptionalStr(name='systemId', value=systemId, allowEmpty=False)

        super().__init__(id=id)
        self._systemId = systemId

    def systemId(self) -> None:
        return self._systemId

    def setSystemId(self, systemId: str) -> None:
        common.validateOptionalStr(name='systemId', value=systemId, allowEmpty=False)
        self._systemId = systemId

class DbNobility(DbSystemObject):
    def __init__(
            self,
            code: str,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        # TODO: Should this check it's a valid nobility string
        common.validateMandatoryStr(name='code', value=code, allowEmpty=False)

        super().__init__(id=id, systemId=systemId)
        self._code = code

    def code(self) -> typing.Optional[str]:
        return self._code

class DbTradeCode(DbSystemObject):
    def __init__(
            self,
            code: str,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        # TODO: Should this check it's a valid trade code string
        common.validateMandatoryStr(name='code', value=code, allowEmpty=False)

        super().__init__(id=id, systemId=systemId)
        self._code = code

    def code(self) -> typing.Optional[str]:
        return self._code

class DbAllegiance(DbSectorObject):
    def __init__(
            self,
            code: str,
            name: str,
            legacy: typing.Optional[str] = None,
            base: typing.Optional[str] = None,
            routeColour: typing.Optional[str] = None,
            routeStyle: typing.Optional[str] = None,
            routeWidth: typing.Optional[float] = None,
            borderColour: typing.Optional[str] = None,
            borderStyle: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        common.validateMandatoryStr(name='code', value=code, allowEmpty=False)
        common.validateMandatoryStr(name='name', value=name, allowEmpty=False)
        # TODO: Legacy and base should probably disallow empty but currently it will cause it to barf at convert/load
        common.validateOptionalStr(name='legacy', value=legacy)
        common.validateOptionalStr(name='base', value=base)
        common.validateOptionalHtmlColour(name='routeColour', value=routeColour)
        common.validateOptionalStr(name='routeStyle', value=routeStyle, allowed=_ValidLineStyles)
        common.validateOptionalFloat(name='routeWidth', value=routeWidth) # TODO: Should this enforce a min of 0
        common.validateOptionalHtmlColour(name='borderColour', value=borderColour)
        common.validateOptionalStr(name='borderStyle', value=borderStyle, allowed=_ValidLineStyles)

        super().__init__(id=id, sectorId=sectorId)

        self._code = code
        self._name = name
        self._legacy = legacy
        self._base = base
        self._routeColour = routeColour
        self._routeStyle = routeStyle
        self._routeWidth = routeWidth
        self._borderColour = borderColour
        self._borderStyle = borderStyle

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

    def legacy(self) -> typing.Optional[str]:
        return self._legacy

    def base(self) -> typing.Optional[str]:
        return self._base

    def routeColour(self) -> typing.Optional[str]:
        return self._routeColour

    def routeStyle(self) -> typing.Optional[str]:
        return self._routeStyle

    def routeWidth(self) -> typing.Optional[float]:
        return self._routeWidth

    def borderColour(self) -> typing.Optional[str]:
        return self._borderColour

    def borderStyle(self) -> typing.Optional[str]:
        return self._borderStyle

class DbRulingAllegiance(DbSystemObject):
    def __init__(
            self,
            allegiance: DbAllegiance,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        common.validateMandatoryObject(name='allegiance', value=allegiance, type=DbAllegiance)

        super().__init__(id=id, systemId=systemId)
        self._allegiance = allegiance

    def allegiance(self) -> DbAllegiance:
        return self._allegiance

class DbSophont(DbSectorObject):
    def __init__(
            self,
            code: str,
            name: str,
            isMajor: bool,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        common.validateMandatoryStr(name='code', value=code, allowEmpty=False)
        common.validateMandatoryStr(name='name', value=name, allowEmpty=False)
        common.validateMandatoryBool(name='isMajor', value=isMajor)

        super().__init__(id=id, sectorId=sectorId)

        self._code = code
        self._name = name
        self._isMajor = isMajor

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

    def isMajor(self) -> bool:
        return self._isMajor

class DbSophontPopulation(DbSystemObject):
    def __init__(
            self,
            sophont: DbSophont,
            percentage: typing.Optional[int], # None means it's a die back sophont
            isHomeWorld: bool,
            isDieBack: bool,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        common.validateMandatoryObject(name='sophont', value=sophont, type=DbSophont)
        common.validateOptionalInt(name='percentage', value=percentage) # TODO: Should this enforce min/max values
        common.validateMandatoryBool(name='isHomeWorld', value=isHomeWorld)
        common.validateMandatoryBool(name='isDieBack', value=isDieBack)

        super().__init__(id=id, systemId=systemId)

        self._sophont = sophont
        self._percentage = percentage
        self._isHomeWorld = isHomeWorld
        self._isDieBack = isDieBack

    def sophont(self) -> DbSophont:
        return self._sophont

    def percentage(self) -> typing.Optional[int]:
        return self._percentage

    def isHomeWorld(self) -> bool:
        return self._isHomeWorld

    def isDieBack(self) -> bool:
        return self._isDieBack

class DbOwningSystem(DbSystemObject):
    def __init__(
            self,
            hexX: int,
            hexY: int,
            sectorAbbreviation: typing.Optional[str], # None means current sector
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ):
        common.validateMandatoryInt(name='hexX', value=hexX)
        common.validateMandatoryInt(name='hexY', value=hexY)
        common.validateOptionalStr(name='sectorAbbreviation', value=sectorAbbreviation) # TODO: Should this disallow empty

        super().__init__(id=id, systemId=systemId)

        self._hexX = hexX
        self._hexY = hexY
        self._sectorAbbreviation = sectorAbbreviation

    def hexX(self) -> int:
        return self._hexX

    def hexY(self) -> int:
        return self._hexY

    def sectorAbbreviation(self) -> typing.Optional[str]:
        return self._sectorAbbreviation

class DbColonySystem(DbSystemObject):
    def __init__(
            self,
            hexX: int,
            hexY: int,
            sectorAbbreviation: typing.Optional[str], # None means current sector
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ):
        common.validateMandatoryInt(name='hexX', value=hexX)
        common.validateMandatoryInt(name='hexY', value=hexY)
        common.validateOptionalStr(name='sectorAbbreviation', value=sectorAbbreviation) # TODO: Should this disallow empty

        super().__init__(id=id, systemId=systemId)

        self._hexX = hexX
        self._hexY = hexY
        self._sectorAbbreviation = sectorAbbreviation

    def hexX(self) -> int:
        return self._hexX

    def hexY(self) -> int:
        return self._hexY

    def sectorAbbreviation(self) -> typing.Optional[str]:
        return self._sectorAbbreviation

class DbCustomRemark(DbSystemObject):
    def __init__(
            self,
            remark: str,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ):
        common.validateMandatoryStr(name='remark', value=remark, allowEmpty=False)

        super().__init__(id=id, systemId=systemId)
        self._remark = remark

    def remark(self) -> str:
        return self._remark

class DbBase(DbSystemObject):
    def __init__(
            self,
            code: str,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        # TODO: This could check that it's a valid base code
        common.validateMandatoryStr(name='code', value=code, allowEmpty=False)

        super().__init__(id=id, systemId=systemId)
        self._code = code

    def code(self) -> str:
        return self._code

class DbResearchStation(DbSystemObject):
    def __init__(
            self,
            code: str,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
         # TODO: This could check that it's a valid research station code
        common.validateMandatoryStr(name='code', value=code)

        super().__init__(id=id, systemId=systemId)
        self._code = code

    def code(self) -> str:
        return self._code

class DbStar(DbSystemObject):
    def __init__(
            self,
            luminosityClass: str,
            spectralClass: typing.Optional[str],
            spectralScale: typing.Optional[str],
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
         # TODO: This could check that it's a classes/scale
        common.validateMandatoryStr(name='luminosityClass', value=luminosityClass, allowEmpty=False)
        common.validateOptionalStr(name='spectralClass', value=spectralClass, allowEmpty=False)
        common.validateOptionalStr(name='spectralScale', value=spectralScale, allowEmpty=False)

        super().__init__(id=id, systemId=systemId)

        self._luminosityClass = luminosityClass
        self._spectralClass = spectralClass
        self._spectralScale = spectralScale

    def luminosityClass(self) -> str:
        return self._luminosityClass

    def spectralClass(self) -> typing.Optional[str]:
        return self._spectralClass

    def spectralScale(self) -> typing.Optional[str]:
        return self._spectralScale

class DbSystem(DbSectorObject):
    def __init__(
            self,
            hexX: int,
            hexY: int,
            name: typing.Optional[str] = None,
            # UWP
            starport: typing.Optional[str] = None,
            worldSize: typing.Optional[str] = None,
            atmosphere: typing.Optional[str] = None,
            hydrographics: typing.Optional[str] = None,
            population: typing.Optional[str] = None,
            government: typing.Optional[str] = None,
            lawLevel: typing.Optional[str] = None,
            techLevel: typing.Optional[str] = None,
            # Economics
            resources: typing.Optional[str] = None,
            labour: typing.Optional[str] = None,
            infrastructure: typing.Optional[str] = None,
            efficiency: typing.Optional[str] = None,
            # Culture
            heterogeneity: typing.Optional[str] = None,
            acceptance: typing.Optional[str] = None,
            strangeness: typing.Optional[str] = None,
            symbols: typing.Optional[str] = None,
            # PBG
            populationMultiplier: typing.Optional[str] = None,
            planetoidBelts: typing.Optional[str] = None,
            gasGiants: typing.Optional[str] = None,
            zone: typing.Optional[str] = None,
            # System worlds can be None if the number is not not known (e.g. if uwp is ???????-?)
            # It can also be none due to it just not being specified in sector data
            # TODO: If I'm keeping gas giants etc as ehex strings, should system worlds be
            # the same? I'm not sure if it's stored as ehex in the file. If it's
            # not, should I convert it to ehex for consistency (what range does it need?)
            systemWorlds: typing.Optional[int] = None,
            allegiance: typing.Optional[DbAllegiance] = None,
            nobilities: typing.Optional[typing.Collection[DbNobility]] = None,
            tradeCodes: typing.Optional[typing.Collection[DbTradeCode]] = None,
            sophontPopulations: typing.Optional[typing.Collection[DbSophontPopulation]] = None,
            rulingAllegiances: typing.Optional[typing.Collection[DbRulingAllegiance]] = None,
            owningSystems: typing.Optional[typing.Collection[DbOwningSystem]] = None,
            colonySystems: typing.Optional[typing.Collection[DbColonySystem]] = None,
            researchStations: typing.Optional[typing.Collection[DbResearchStation]] = None,
            customRemarks: typing.Optional[typing.Collection[DbCustomRemark]] = None,
            bases: typing.Optional[typing.Collection[DbBase]] = None,
            stars: typing.Optional[typing.Collection[DbStar]] = None,
            notes: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        common.validateMandatoryInt(name='hexX', value=hexX)
        common.validateMandatoryInt(name='hexY', value=hexY)
        # TODO: Ideally the name probably shouldn't allow empty but it currently blows up if you enable it
        common.validateOptionalStr(name='name', value=name)
        # TODO: Should this validate the UWP/PBG/etc codes are valid codes?
        common.validateOptionalStr(name='starport', value=starport)
        common.validateOptionalStr(name='worldSize', value=worldSize)
        common.validateOptionalStr(name='atmosphere', value=atmosphere)
        common.validateOptionalStr(name='hydrographics', value=hydrographics)
        common.validateOptionalStr(name='population', value=population)
        common.validateOptionalStr(name='government', value=government)
        common.validateOptionalStr(name='lawLevel', value=lawLevel)
        common.validateOptionalStr(name='techLevel', value=techLevel)
        common.validateOptionalStr(name='resources', value=resources)
        common.validateOptionalStr(name='labour', value=labour)
        common.validateOptionalStr(name='infrastructure', value=infrastructure)
        common.validateOptionalStr(name='efficiency', value=efficiency)
        common.validateOptionalStr(name='heterogeneity', value=heterogeneity)
        common.validateOptionalStr(name='acceptance', value=acceptance)
        common.validateOptionalStr(name='strangeness', value=strangeness)
        common.validateOptionalStr(name='symbols', value=symbols)
        common.validateOptionalStr(name='populationMultiplier', value=populationMultiplier)
        common.validateOptionalStr(name='planetoidBelts', value=planetoidBelts)
        common.validateOptionalStr(name='gasGiants', value=gasGiants)
        common.validateOptionalStr(name='zone', value=zone)
        common.validateOptionalInt(name='systemWorlds', value=systemWorlds, min=0)
        common.validateOptionalObject(name='allegiance', value=allegiance, type=DbAllegiance)
        common.validateOptionalCollection(name='nobilities', value=nobilities, type=DbNobility)
        common.validateOptionalCollection(name='tradeCodes', value=tradeCodes, type=DbTradeCode)
        common.validateOptionalCollection(name='sophontPopulations', value=sophontPopulations, type=DbSophontPopulation)
        common.validateOptionalCollection(name='rulingAllegiances', value=rulingAllegiances, type=DbRulingAllegiance)
        common.validateOptionalCollection(name='owningSystems', value=owningSystems, type=DbOwningSystem)
        common.validateOptionalCollection(name='colonySystems', value=colonySystems, type=DbColonySystem)
        common.validateOptionalCollection(name='researchStations', value=researchStations, type=DbResearchStation)
        common.validateOptionalCollection(name='customRemarks', value=customRemarks, type=DbCustomRemark)
        common.validateOptionalCollection(name='bases', value=bases, type=DbBase)
        common.validateOptionalCollection(name='stars', value=stars, type=DbStar)
        common.validateOptionalStr(name='notes', value=notes)

        super().__init__(id=id, sectorId=sectorId)

        self._hexX = hexX
        self._hexY = hexY
        self._name = name
        self._starport = starport
        self._worldSize = worldSize
        self._atmosphere = atmosphere
        self._hydrographics = hydrographics
        self._population = population
        self._government = government
        self._lawLevel = lawLevel
        self._techLevel = techLevel
        self._resources = resources
        self._labour = labour
        self._infrastructure = infrastructure
        self._efficiency = efficiency
        self._heterogeneity = heterogeneity
        self._acceptance = acceptance
        self._strangeness = strangeness
        self._symbols = symbols
        self._populationMultiplier = populationMultiplier
        self._planetoidBelts = planetoidBelts
        self._gasGiants = gasGiants
        self._zone = zone
        self._systemWorlds = systemWorlds
        self._allegiance = allegiance
        self._notes = notes

        self._nobilities = list(nobilities) if nobilities else None
        self._attachObjects(self._nobilities)
        self._tradeCodes = list(tradeCodes) if tradeCodes else None
        self._attachObjects(self._tradeCodes)
        self._sophontPopulations = list(sophontPopulations) if sophontPopulations else None
        self._attachObjects(self._sophontPopulations)
        self._rulingAllegiances = list(rulingAllegiances) if rulingAllegiances else None
        self._attachObjects(self._rulingAllegiances)
        self._owningSystems = list(owningSystems) if owningSystems else None
        self._attachObjects(self._owningSystems)
        self._colonySystems = list(colonySystems) if colonySystems else None
        self._attachObjects(self._colonySystems)
        self._researchStations = list(researchStations) if researchStations else None
        self._attachObjects(self._researchStations)
        self._customRemarks = list(customRemarks) if customRemarks else None
        self._attachObjects(self._customRemarks)
        self._bases = list(bases) if bases else None
        self._attachObjects(self._bases)
        self._stars = list(stars) if stars else None
        self._attachObjects(self._stars)

    def hexX(self) -> int:
        return self._hexX

    def hexY(self) -> int:
        return self._hexY

    def name(self) -> typing.Optional[str]:
        return self._name

    def starport(self) -> typing.Optional[str]:
        return self._starport

    def worldSize(self) -> typing.Optional[str]:
        return self._worldSize

    def atmosphere(self) -> typing.Optional[str]:
        return self._atmosphere

    def hydrographics(self) -> typing.Optional[str]:
        return self._hydrographics

    def population(self) -> typing.Optional[str]:
        return self._population

    def government(self) -> typing.Optional[str]:
        return self._government

    def lawLevel(self) -> typing.Optional[str]:
        return self._lawLevel

    def techLevel(self) -> typing.Optional[str]:
        return self._techLevel

    def resources(self ) -> typing.Optional[str]:
        return self._resources

    def labour(self ) -> typing.Optional[str]:
        return self._labour

    def infrastructure(self ) -> typing.Optional[str]:
        return self._infrastructure

    def efficiency(self ) -> typing.Optional[str]:
        return self._efficiency

    def heterogeneity(self) -> typing.Optional[str]:
        return self._heterogeneity

    def acceptance(self) -> typing.Optional[str]:
        return self._acceptance

    def strangeness(self) -> typing.Optional[str]:
        return self._strangeness

    def symbols(self) -> typing.Optional[str]:
        return self._symbols

    def populationMultiplier(self) -> typing.Optional[str]:
        return self._populationMultiplier

    def planetoidBelts(self) -> typing.Optional[str]:
        return self._planetoidBelts

    def gasGiants(self) -> typing.Optional[str]:
        return self._gasGiants

    def zone(self) -> typing.Optional[str]:
        return self._zone

    def systemWorlds(self) -> typing.Optional[int]:
        return self._systemWorlds

    def allegiance(self) -> typing.Optional[DbAllegiance]:
        return self._allegiance

    def nobilities(self) -> typing.Optional[typing.Collection[DbNobility]]:
        return self._nobilities

    def tradeCodes(self) -> typing.Optional[typing.Collection[DbTradeCode]]:
        return self._tradeCodes

    def sophontPopulations(self) -> typing.Optional[typing.Collection[DbSophontPopulation]]:
        return self._sophontPopulations

    def rulingAllegiances(self) -> typing.Optional[typing.Collection[DbRulingAllegiance]]:
        return self._rulingAllegiances

    def owningSystems(self) -> typing.Optional[typing.Collection[DbOwningSystem]]:
        return self._owningSystems

    def colonySystems(self) -> typing.Optional[typing.Collection[DbColonySystem]]:
        return self._colonySystems

    def researchStations(self) -> typing.Optional[typing.Collection[DbResearchStation]]:
        return self._researchStations

    def customRemarks(self) -> typing.Optional[typing.Collection[DbCustomRemark]]:
        return self._customRemarks

    def bases(self) -> typing.Optional[typing.Collection[DbBase]]:
        return self._bases

    def stars(self) -> typing.Optional[typing.Collection[DbStar]]:
        return self._stars

    def notes(self) -> typing.Optional[str]:
        return self._notes

    def _attachObjects(
            self,
            objects: typing.Optional[typing.Iterable[DbSystemObject]]
            ) -> None:
        if not objects:
            return
        for obj in objects:
            obj.setSystemId(systemId=self._id)

class DbAlternateName(DbSectorObject):
    def __init__(
            self,
            name: str,
            language: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        common.validateMandatoryStr(name='name', value=name, allowEmpty=False)
        common.validateOptionalStr(name='language', value=language, allowEmpty=False)

        super().__init__(id=id, sectorId=sectorId)

        self._name = name
        self._language = language

    def name(self) -> str:
        return self._name

    def language(self) -> typing.Optional[str]:
        return self._language

class DbSubsectorName(DbSectorObject):
    def __init__(
            self,
            code: str,
            name: str,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        # TODO: Should this check its a valid code?
        common.validateMandatoryStr(name='code', value=code, allowEmpty=False)
        common.validateMandatoryStr(name='name', value=name, allowEmpty=False)

        super().__init__(id=id, sectorId=sectorId)

        self._code = code
        self._name = name

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

class DbRoute(DbSectorObject):
    def __init__(
            self,
            startHexX: int,
            startHexY: int,
            endHexX: int,
            endHexY: int,
            # These offsets are sector offsets for the start/end. If all
            # the x/y offsets are both 0 for the start and/or end it means
            # they are in the current sector
            startOffsetX: int = 0,
            startOffsetY: int = 0,
            endOffsetX: int = 0,
            endOffsetY: int = 0,
            type: typing.Optional[str] = None,
            style: typing.Optional[str] = None,
            colour: typing.Optional[str] = None,
            width: typing.Optional[float] = None,
            allegiance: typing.Optional[DbAllegiance] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        common.validateMandatoryInt(name='startHexX', value=startHexX)
        common.validateMandatoryInt(name='startHexY', value=startHexY)
        common.validateMandatoryInt(name='endHexX', value=endHexX)
        common.validateMandatoryInt(name='endHexY', value=endHexY)
        common.validateOptionalInt(name='startOffsetX', value=startOffsetX)
        common.validateOptionalInt(name='startOffsetY', value=startOffsetY)
        common.validateOptionalInt(name='endOffsetX', value=endOffsetX)
        common.validateOptionalInt(name='endOffsetY', value=endOffsetY)
        common.validateOptionalStr(name='type', value=type)
        common.validateOptionalStr(name='style', value=style, allowed=_ValidLineStyles)
        common.validateOptionalHtmlColour(name='colour', value=colour)
        common.validateOptionalFloat(name='width', value=width, min=0)
        common.validateOptionalObject(name='allegiance', value=allegiance, type=DbAllegiance)

        super().__init__(id=id, sectorId=sectorId)

        self._startHexX = startHexX
        self._startHexY = startHexY
        self._endHexX = endHexX
        self._endHexY = endHexY
        self._startOffsetX = startOffsetX
        self._startOffsetY = startOffsetY
        self._endOffsetX = endOffsetX
        self._endOffsetY = endOffsetY
        self._type = type
        self._style = style
        self._colour = colour
        self._width = width
        self._allegiance = allegiance

    def startHexX(self) -> int:
        return self._startHexX

    def startHexY(self) -> int:
        return self._startHexY

    def endHexX(self) -> int:
        return self._endHexX

    def endHexY(self) -> int:
        return self._endHexY

    def startOffsetX(self) -> int:
        return self._startOffsetX

    def startOffsetY(self) -> int:
        return self._startOffsetY

    def endOffsetX(self) -> int:
        return self._endOffsetX

    def endOffsetY(self) -> int:
        return self._endOffsetY

    def type(self) -> typing.Optional[str]:
        return self._type

    def style(self) -> typing.Optional[str]:
        return self._style

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def width(self) -> typing.Optional[float]:
        return self._width

    def allegiance(self) -> typing.Optional[DbAllegiance]:
        return self._allegiance

class DbBorder(DbSectorObject):
    def __init__(
            self,
            hexes: typing.Sequence[typing.Tuple[int, int]],
            allegiance: typing.Optional[DbAllegiance] = None,
            style: typing.Optional[str] = None,
            colour: typing.Optional[str] = None,
            label: typing.Optional[str] = None,
            labelWorldX: typing.Optional[float] = None,
            labelWorldY: typing.Optional[float] = None,
            showLabel: bool = True,
            wrapLabel: bool = False,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        common.validateMandatoryCollection(name='hexes', value=hexes, validationFn=DbBorder._hexTupleValidator)
        common.validateOptionalObject(name='allegiance', value=allegiance, type=DbAllegiance)
        common.validateOptionalStr(name='style', value=style, allowed=_ValidLineStyles)
        common.validateOptionalHtmlColour(name='colour', value=colour)
        common.validateOptionalStr(name='label', value=label)
        common.validateOptionalFloat(name='labelWorldX', value=labelWorldX)
        common.validateOptionalFloat(name='labelWorldY', value=labelWorldY)
        common.validateMandatoryBool(name='showLabel', value=showLabel)
        common.validateMandatoryBool(name='wrapLabel', value=wrapLabel)

        super().__init__(id=id, sectorId=sectorId)

        self._hexes = list(hexes)
        self._allegiance = allegiance
        self._style = style
        self._colour = colour
        self._label = label
        self._labelWorldX = labelWorldX
        self._labelWorldY = labelWorldY
        self._showLabel = showLabel
        self._wrapLabel = wrapLabel

    def hexes(self) -> typing.Sequence[typing.Tuple[int, int]]:
        return self._hexes

    def allegiance(self) -> typing.Optional[DbAllegiance]:
        return self._allegiance

    def style(self) -> typing.Optional[str]:
        return self._style

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def label(self) -> typing.Optional[str]:
        return self._label

    def labelWorldX(self) -> typing.Optional[float]:
        return self._labelWorldX

    def labelWorldY(self) -> typing.Optional[int]:
        return self._labelWorldY

    def showLabel(self) -> bool:
        return self._showLabel

    def wrapLabel(self) -> bool:
        return self._wrapLabel

    @staticmethod
    def _hexTupleValidator(
            name: str,
            value: typing.Tuple[int, int],
            ) -> None:
        if len(value) != 2 or not isinstance(value[0], int) or not isinstance(value[1], int):
            raise ValueError(f'{name} should contain tuples each with 2 integers')

class DbRegion(DbSectorObject):
    def __init__(
            self,
            hexes: typing.Sequence[typing.Tuple[int, int]],
            colour: typing.Optional[str] = None,
            label: typing.Optional[str] = None,
            labelWorldX: typing.Optional[float] = None,
            labelWorldY: typing.Optional[float] = None,
            showLabel: bool = True,
            wrapLabel: bool = False,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        common.validateMandatoryCollection(name='hexes', value=hexes, validationFn=DbBorder._hexTupleValidator)
        common.validateOptionalHtmlColour(name='colour', value=colour)
        common.validateOptionalStr(name='label', value=label)
        common.validateOptionalFloat(name='labelWorldX', value=labelWorldX)
        common.validateOptionalFloat(name='labelWorldY', value=labelWorldY)
        common.validateMandatoryBool(name='showLabel', value=showLabel)
        common.validateMandatoryBool(name='wrapLabel', value=wrapLabel)

        super().__init__(id=id, sectorId=sectorId)

        self._hexes = list(hexes)
        self._colour = colour
        self._label = label
        self._labelWorldX = labelWorldX
        self._labelWorldY = labelWorldY
        self._showLabel = showLabel
        self._wrapLabel = wrapLabel

    def hexes(self) -> typing.Sequence[typing.Tuple[int, int]]:
        return self._hexes

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def label(self) -> typing.Optional[str]:
        return self._label

    def labelWorldX(self) -> typing.Optional[float]:
        return self._labelWorldX

    def labelWorldY(self) -> typing.Optional[float]:
        return self._labelWorldY

    def showLabel(self) -> bool:
        return self._showLabel

    def wrapLabel(self) -> bool:
        return self._wrapLabel

    def _hexTupleValidator(
            name: str,
            value: typing.Tuple[int, int],
            ) -> None:
        if len(value) != 2 or not isinstance(value[0], int) or not isinstance(value[1], int):
            raise ValueError(f'{name} should contain tuples each with 2 integers')

class DbLabel(DbSectorObject):
    def __init__(
            self,
            text: str,
            worldX: float,
            worldY: float,
            colour: typing.Optional[str] = None,
            size: typing.Optional[str] = None,
            wrap: bool = False,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        common.validateMandatoryStr(name='text', value=text)
        common.validateMandatoryFloat(name='worldX', value=worldX)
        common.validateMandatoryFloat(name='worldY', value=worldY)
        common.validateOptionalHtmlColour(name='colour', value=colour)
        common.validateOptionalStr(name='size', value=size, allowed=_ValidLabelSizes)
        common.validateMandatoryBool(name='wrap', value=wrap)

        super().__init__(id=id, sectorId=sectorId)

        self._text = text
        self._worldX = worldX
        self._worldY = worldY
        self._colour = colour
        self._size = size
        self._wrap = wrap

    def text(self) -> str:
        return self._text

    def worldX(self) -> float:
        return self._worldX

    def worldY(self) -> float:
        return self._worldY

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def size(self) -> typing.Optional[str]:
        return self._size

    def wrap(self) -> bool:
        return self._wrap

class DbProduct(DbSectorObject):
    def __init__(
            self,
            publication: typing.Optional[str] = None,
            author: typing.Optional[str] = None,
            publisher: typing.Optional[str] = None,
            reference: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        common.validateOptionalStr(name='publication', value=publication, allowEmpty=False)
        common.validateOptionalStr(name='author', value=author, allowEmpty=False)
        common.validateOptionalStr(name='publisher', value=publisher, allowEmpty=False)
        common.validateOptionalStr(name='reference', value=reference, allowEmpty=False)

        super().__init__(id=id, sectorId=sectorId)

        self._publication = publication
        self._author = author
        self._publisher = publisher
        self._reference = reference

    def publication(self) -> typing.Optional[str]:
        return self._publication

    def author(self) -> typing.Optional[str]:
        return self._author

    def publisher(self) -> typing.Optional[str]:
        return self._publisher

    def reference(self) -> typing.Optional[str]:
        return self._reference

class DbTag(DbSectorObject):
    def __init__(
            self,
            tag: str,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        common.validateMandatoryStr(name='tag', value=tag, allowEmpty=False)

        super().__init__(id=id, sectorId=sectorId)
        self._string = tag

    def tag(self) -> str:
        return self._string

class DbSector(DbUniverseObject):
    def __init__(
            self,
            isCustom: bool,
            milieu: str,
            sectorX: int,
            sectorY: int,
            primaryName: str,
            primaryLanguage: typing.Optional[str] = None,
            abbreviation: typing.Optional[str] = None,
            sectorLabel: typing.Optional[str] = None,
            selected: bool = False,
            alternateNames: typing.Optional[typing.Collection[DbAlternateName]] = None,
            subsectorNames: typing.Optional[typing.Collection[DbSubsectorName]] = None,
            allegiances: typing.Optional[typing.Collection[DbAllegiance]] = None,
            sophonts: typing.Optional[typing.Collection[DbSophont]] = None,
            systems: typing.Optional[typing.Collection[DbSystem]] = None,
            routes: typing.Optional[typing.Collection[DbRoute]] = None,
            borders: typing.Optional[typing.Collection[DbBorder]] = None,
            regions: typing.Optional[typing.Collection[DbRegion]] = None,
            labels: typing.Optional[typing.Collection[DbLabel]] = None,
            tags: typing.Optional[typing.Collection[DbTag]] = None,
            credits: typing.Optional[str] = None,
            publication: typing.Optional[str] = None,
            author: typing.Optional[str] = None,
            publisher: typing.Optional[str] = None,
            reference: typing.Optional[str] = None,
            products: typing.Optional[typing.Collection[DbProduct]] = None,
            notes: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            universeId: typing.Optional[str] = None
            ) -> None:
        # TODO: Verify that there aren't 2 worlds with the same location
        common.validateMandatoryBool(name='isCustom', value=isCustom)
        common.validateMandatoryStr(name='milieu', value=milieu) # TODO: Validate that this is an expected value
        common.validateMandatoryInt(name='sectorX', value=sectorX)
        common.validateMandatoryInt(name='sectorY', value=sectorY)
        common.validateMandatoryStr(name='primaryName', value=primaryName, allowEmpty=False)
        common.validateOptionalStr(name='primaryLanguage', value=primaryLanguage, allowEmpty=False)
        common.validateOptionalStr(name='abbreviation', value=abbreviation, allowEmpty=False)
        common.validateOptionalStr(name='sectorLabel', value=sectorLabel, allowEmpty=False)
        common.validateMandatoryBool(name='selected', value=selected)
        common.validateOptionalCollection(name='alternateNames', value=alternateNames, type=DbAlternateName)
        common.validateOptionalCollection(name='subsectorNames', value=subsectorNames, type=DbSubsectorName)
        common.validateOptionalCollection(name='allegiances', value=allegiances, type=DbAllegiance)
        common.validateOptionalCollection(name='sophonts', value=sophonts, type=DbSophont)
        common.validateOptionalCollection(name='systems', value=systems, type=DbSystem)
        common.validateOptionalCollection(name='routes', value=routes, type=DbRoute)
        common.validateOptionalCollection(name='borders', value=borders, type=DbBorder)
        common.validateOptionalCollection(name='regions', value=regions, type=DbRegion)
        common.validateOptionalCollection(name='labels', value=labels, type=DbLabel)
        common.validateOptionalCollection(name='tags', value=tags, type=DbTag)
        common.validateOptionalStr(name='credits', value=credits, allowEmpty=False)
        common.validateOptionalStr(name='publication', value=publication, allowEmpty=False)
        common.validateOptionalStr(name='author', value=author, allowEmpty=False)
        common.validateOptionalStr(name='publisher', value=publisher, allowEmpty=False)
        common.validateOptionalStr(name='reference', value=reference, allowEmpty=False)
        common.validateOptionalCollection(name='products', value=products, type=DbProduct)
        common.validateOptionalStr(name='notes', value=notes)

        super().__init__(id=id, universeId=universeId)

        self._isCustom = isCustom
        self._milieu = milieu
        self._sectorX = sectorX
        self._sectorY = sectorY
        self._primaryName = primaryName
        self._primaryLanguage = primaryLanguage
        self._abbreviation = abbreviation
        self._sectorLabel = sectorLabel
        self._selected = selected
        self._credits = credits
        self._publication = publication
        self._author = author
        self._publisher = publisher
        self._reference = reference
        self._notes = notes

        self._alternateNames = list(alternateNames) if alternateNames else None
        self._attachObjects(self._alternateNames)
        self._subsectorNames = list(subsectorNames) if subsectorNames else None
        self._attachObjects(self._subsectorNames)
        self._allegiances = list(allegiances) if allegiances else None
        self._attachObjects(self._allegiances)
        self._sophonts = list(sophonts) if sophonts else None
        self._attachObjects(self._sophonts)
        self._systems = list(systems) if systems else None
        self._attachObjects(self._systems)
        self._routes = list(routes) if routes else None
        self._attachObjects(self._routes)
        self._borders = list(borders) if borders else None
        self._attachObjects(self._borders)
        self._regions = list(regions) if regions else None
        self._attachObjects(self._regions)
        self._labels = list(labels) if labels else None
        self._attachObjects(self._labels)
        self._tags = list(tags) if tags else None
        self._attachObjects(self._tags)
        self._products = list(products) if products else None
        self._attachObjects(self._products)

    def isCustom(self) -> bool:
        return self._isCustom

    def milieu(self) -> str:
        return self._milieu

    def sectorX(self) -> int:
        return self._sectorX

    def sectorY(self) -> int:
        return self._sectorY

    def primaryName(self) -> str:
        return self._primaryName

    def primaryLanguage(self) -> typing.Optional[str]:
        return self._primaryLanguage

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

    def sectorLabel(self) -> typing.Optional[str]:
        return self._sectorLabel

    def selected(self) -> bool:
        return self._selected

    def alternateNames(self) -> typing.Optional[typing.Collection[DbAlternateName]]:
        return self._alternateNames

    def subsectorNames(self) -> typing.Optional[typing.Collection[DbSubsectorName]]:
        return self._subsectorNames

    def allegiances(self) -> typing.Optional[typing.Collection[DbAllegiance]]:
        return self._allegiances

    def sophonts(self) -> typing.Optional[typing.Collection[DbSophont]]:
        return self._sophonts

    def systems(self) -> typing.Optional[typing.Collection[DbSystem]]:
        return self._systems

    def routes(self) -> typing.Optional[typing.Collection[DbRoute]]:
        return self._routes

    def borders(self) -> typing.Optional[typing.Collection[DbBorder]]:
        return self._borders

    def regions(self) -> typing.Optional[typing.Collection[DbRegion]]:
        return self._regions

    def labels(self) -> typing.Optional[typing.Collection[DbLabel]]:
        return self._labels

    def tags(self) -> typing.Optional[typing.Collection[DbTag]]:
        return self._tags

    def credits(self) -> typing.Optional[str]:
        return self._credits

    def publication(self) -> typing.Optional[str]:
        return self._publication

    def author(self) -> typing.Optional[str]:
        return self._author

    def publisher(self) -> typing.Optional[str]:
        return self._publisher

    def reference(self) -> typing.Optional[str]:
        return self._reference

    def products(self) -> typing.Optional[typing.Collection[DbProduct]]:
        return self._products

    def notes(self) -> typing.Optional[str]:
        return self._notes

    def _attachObjects(
            self,
            objects: typing.Optional[typing.Iterable[DbSectorObject]]
            ) -> None:
        if not objects:
            return
        for obj in objects:
            obj.setSectorId(sectorId=self._id)

# TODO: This needs updated to be immutable like the other db objects
class DbUniverse(DbObject):
    def __init__(
            self,
            name: str,
            description: typing.Optional[str] = None,
            sectors: typing.Optional[typing.Collection[DbSector]] = None,
            notes: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            ) -> None:
        # TODO: Verify that there aren't 2 sectors at the same location
        common.validateMandatoryStr(name='name', value=name)
        common.validateOptionalStr(name='description', value=description)
        common.validateOptionalCollection(name='sectors', value=sectors, type=DbSector)
        common.validateOptionalStr(name='notes', value=notes)

        super().__init__(id=id)

        self._sectorByMilieuPosition: typing.Dict[typing.Tuple[str, int, int], DbSector] = {}

        self.setName(name)
        self.setDescription(description)
        self.setNotes(notes)
        self.setSectors(sectors)

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> None:
        self._name = name

    def description(self) -> typing.Optional[str]:
        return self._description

    def setDescription(self, description: typing.Optional[str]) -> None:
        self._description = description

    def notes(self) -> typing.Optional[str]:
        return self._notes

    def setNotes(self, notes: typing.Optional[str]) -> None:
        self._notes = notes

    def sectors(self) -> typing.Optional[typing.Collection[DbSector]]:
        return self._sectors

    def sector(
            self,
            milieu: str,
            sectorX: int,
            sectorY: int
            ) -> typing.Optional[DbSector]:
        key = (milieu, sectorX, sectorY)
        return self._sectorByMilieuPosition.get(key)

    def setSectors(self, sectors: typing.Optional[typing.Collection[DbSector]]) -> None:
        if sectors is not None:
            self._sectors = []
            for sector in sectors:
                self.addSector(sector=sector)
        else:
            self._sectors = None

    def addSector(self, sector: DbSector) -> None:
        if self._sectors is None:
            self._sectors: typing.List[DbSector] = []

        key = (sector.milieu(), sector.sectorX(), sector.sectorY())

        oldSector = self._sectorByMilieuPosition.get(key)
        if oldSector:
            self._sectors.remove(oldSector)

        self._sectors.append(sector)
        self._sectorByMilieuPosition[key] = sector

        sector.setUniverseId(self._id)

    def removeSector(self, sectorId: str) -> None:
        if self._sectors is None:
            return
        for i in range(self._sectors):
            sector = self._sectors[i]
            if sector.id() == sectorId:
                del self._sectorByMilieuPosition[(sector.milieu(), sector.sectorX(), sector.sectorY())]
                del self._sectors[i]
                return
