import common
import survey
import typing
import uuid

_ValidMilieu = set(['IW', 'M0', 'M990', 'M1105', 'M1120', 'M1201', 'M1248', 'M1900'])
_ValidSubsectorCodes = set(map(chr, range(ord('A'), ord('P') + 1)))
_ValidLineStyles = set(['solid', 'dashed', 'dotted'])
_ValidLabelSizes = set(['small', 'large'])

class DbObject(object):
    def __init__(
            self,
            id: typing.Optional[str] = None, # None means allocate an id
            ) -> None:
        super().__init__()

        common.validateOptionalStr(name='id', value=id, allowEmpty=False)

        self._id = id if id is not None else str(uuid.uuid4())

    def id(self) -> str:
        return self._id

class DbUniverseObject(DbObject):
    def __init__(
            self,
            id: typing.Optional[str] = None, # None means allocate an id
            universeId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        common.validateOptionalStr(name='universeId', value=universeId, allowEmpty=False)

        self._universeId = universeId

    def universeId(self) -> None:
        return self._universeId

    # NOTE: Setting the id back to None is intentionally disallowed as the only
    # reason to do so would be to remove an object from its parent and it's not
    # safe to do that as the object may hold references to other objects owned
    # by the parent. If the object was removed from the parent and attached to
    # another object, it would still refer to objects owned by its old parent.
    # An example of this would be sophont populations. They're attached to a
    # system but hold references to the sophont which is owned by the sector. If
    # the system was removed from one sector and added to another, it would still
    # reference the sophont from its old sector which would result in horrible
    # bugs and the mangled data being written back to the database.
    def setUniverseId(self, universeId: str) -> None:
        common.validateMandatoryStr(name='universeId', value=universeId, allowEmpty=False)

        if universeId == self._universeId:
            return # Nothing to do

        if self._universeId is not None:
            raise RuntimeError(f'Object {self._id} of type {type(self)} is already attached to a universe')

        self._universeId = universeId

class DbSectorObject(DbObject):
    def __init__(
            self,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        common.validateOptionalStr(name='sectorId', value=sectorId, allowEmpty=False)

        self._sectorId = sectorId

    def sectorId(self) -> None:
        return self._sectorId

    # NOTE: Setting the id back to None is intentionally disallowed as the only
    # reason to do so would be to remove an object from its parent and it's not
    # safe to do that as the object may hold references to other objects owned
    # by the parent. If the object was removed from the parent and attached to
    # another object, it would still refer to objects owned by its old parent.
    # An example of this would be sophont populations. They're attached to a
    # system but hold references to the sophont which is owned by the sector. If
    # the system was removed from one sector and added to another, it would still
    # reference the sophont from its old sector which would result in horrible
    # bugs and the mangled data being written back to the database.
    def setSectorId(self, sectorId: str) -> None:
        common.validateMandatoryStr(name='sectorId', value=sectorId, allowEmpty=False)

        if sectorId == self._sectorId:
            return # Nothing to do

        if self._sectorId is not None:
            raise RuntimeError(f'Object {self._id} of type {type(self)} is already attached to a sector')

        self._sectorId = sectorId

class DbSystemObject(DbObject):
    def __init__(
            self,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        common.validateOptionalStr(name='systemId', value=systemId, allowEmpty=False)

        self._systemId = systemId

    def systemId(self) -> None:
        return self._systemId

    # NOTE: Setting the id back to None is intentionally disallowed as the only
    # reason to do so would be to remove an object from its parent and it's not
    # safe to do that as the object may hold references to other objects owned
    # by the parent. If the object was removed from the parent and attached to
    # another object, it would still refer to objects owned by its old parent.
    # An example of this would be sophont populations. They're attached to a
    # system but hold references to the sophont which is owned by the sector. If
    # the system was removed from one sector and added to another, it would still
    # reference the sophont from its old sector which would result in horrible
    # bugs and the mangled data being written back to the database.
    def setSystemId(self, systemId: str) -> None:
        common.validateMandatoryStr(name='systemId', value=systemId, allowEmpty=False)

        if systemId == self._systemId:
            return # Nothing to do

        if self._systemId is not None:
            raise RuntimeError(f'Object {self._id} of type {type(self)} is already attached to a system')

        self._systemId = systemId

class DbNobility(DbSystemObject):
    def __init__(
            self,
            code: str,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, systemId=systemId)

        survey.validateMandatoryNobility(name='code', value=code)

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
        super().__init__(id=id, systemId=systemId)

        survey.validateMandatoryTradeCode(name='code', value=code)

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
        super().__init__(id=id, sectorId=sectorId)

        common.validateMandatoryStr(name='code', value=code, allowEmpty=False)
        common.validateMandatoryStr(name='name', value=name, allowEmpty=False)
        common.validateOptionalStr(name='legacy', value=legacy, allowEmpty=False)
        common.validateOptionalStr(name='base', value=base, allowEmpty=False)
        common.validateOptionalHtmlColour(name='routeColour', value=routeColour)
        common.validateOptionalStr(name='routeStyle', value=routeStyle, allowed=_ValidLineStyles)
        common.validateOptionalFloat(name='routeWidth', value=routeWidth, min=0)
        common.validateOptionalHtmlColour(name='borderColour', value=borderColour)
        common.validateOptionalStr(name='borderStyle', value=borderStyle, allowed=_ValidLineStyles)

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
        super().__init__(id=id, systemId=systemId)

        common.validateMandatoryObject(name='allegiance', value=allegiance, type=DbAllegiance)

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
        super().__init__(id=id, sectorId=sectorId)

        common.validateMandatoryStr(name='code', value=code, allowEmpty=False)
        common.validateMandatoryStr(name='name', value=name, allowEmpty=False)
        common.validateMandatoryBool(name='isMajor', value=isMajor)

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
        super().__init__(id=id, systemId=systemId)

        common.validateMandatoryObject(name='sophont', value=sophont, type=DbSophont)
        common.validateOptionalInt(name='percentage', value=percentage, min=0, max=100)
        common.validateMandatoryBool(name='isHomeWorld', value=isHomeWorld)
        common.validateMandatoryBool(name='isDieBack', value=isDieBack)

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
        super().__init__(id=id, systemId=systemId)

        common.validateMandatoryInt(name='hexX', value=hexX)
        common.validateMandatoryInt(name='hexY', value=hexY)
        common.validateOptionalStr(name='sectorAbbreviation', value=sectorAbbreviation, allowEmpty=False)

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
        super().__init__(id=id, systemId=systemId)

        common.validateMandatoryInt(name='hexX', value=hexX)
        common.validateMandatoryInt(name='hexY', value=hexY)
        common.validateOptionalStr(name='sectorAbbreviation', value=sectorAbbreviation, allowEmpty=False)

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
        super().__init__(id=id, systemId=systemId)

        common.validateMandatoryStr(name='remark', value=remark, allowEmpty=False)

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
        super().__init__(id=id, systemId=systemId)

        survey.validateMandatoryBase(name='code', value=code)

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
        super().__init__(id=id, systemId=systemId)

        survey.validateMandatoryResearchStation(name='code', value=code)

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
        super().__init__(id=id, systemId=systemId)

        survey.validateMandatoryLuminosityClass(name='luminosityClass', value=luminosityClass)
        survey.validateOptionalSpectralClass(name='spectralClass', value=spectralClass)
        survey.validateOptionalSpectralScale(name='spectralScale', value=spectralScale)

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
        super().__init__(id=id, sectorId=sectorId)

        common.validateMandatoryInt(name='hexX', value=hexX)
        common.validateMandatoryInt(name='hexY', value=hexY)
        common.validateOptionalStr(name='name', value=name, allowEmpty=False)
        survey.validateOptionalStarport(name='starport', value=starport)
        survey.validateOptionalWorldSize(name='worldSize', value=worldSize)
        survey.validateOptionalAtmosphere(name='atmosphere', value=atmosphere)
        survey.validateOptionalHydrographics(name='hydrographics', value=hydrographics)
        survey.validateOptionalPopulation(name='population', value=population)
        survey.validateOptionalGovernment(name='government', value=government)
        survey.validateOptionalLawLevel(name='lawLevel', value=lawLevel)
        survey.validateOptionalTechLevel(name='techLevel', value=techLevel)
        survey.validateOptionalEconomicsResources(name='resources', value=resources)
        survey.validateOptionalEconomicsLabour(name='labour', value=labour)
        survey.validateOptionalEconomicsInfrastructure(name='infrastructure', value=infrastructure)
        survey.validateOptionalEconomicsEfficiency(name='efficiency', value=efficiency)
        survey.validateOptionalHeterogeneity(name='heterogeneity', value=heterogeneity)
        survey.validateOptionalAcceptance(name='acceptance', value=acceptance)
        survey.validateOptionalStrangeness(name='strangeness', value=strangeness)
        survey.validateOptionalSymbols(name='symbols', value=symbols)
        survey.validateOptionalPopulationMultiplier(name='populationMultiplier', value=populationMultiplier)
        survey.validateOptionalPlanetoidBelts(name='planetoidBelts', value=planetoidBelts)
        survey.validateOptionalGasGiants(name='gasGiants', value=gasGiants)
        survey.validateOptionalZone(name='zone', value=zone)
        common.validateOptionalInt(name='systemWorlds', value=systemWorlds, min=0)
        DbSystem._validateAllegiance(name='allegiance', value=allegiance, sectorId=sectorId)
        DbSystem._validateNobilities(name='nobilities', value=nobilities, systemId=id)
        DbSystem._validateTradeCodes(name='tradeCodes', value=tradeCodes, systemId=id)
        DbSystem._validateSophontPopulations(name='sophontPopulations', value=sophontPopulations, systemId=id, sectorId=sectorId)
        DbSystem._validateRulingAllegiances(name='rulingAllegiances', value=rulingAllegiances, systemId=id, sectorId=sectorId)
        DbSystem._validateOwningSystems(name='owningSystems', value=owningSystems, systemId=id)
        DbSystem._validateColonySystems(name='colonySystems', value=colonySystems, systemId=id)
        DbSystem._validateResearchStations(name='researchStations', value=researchStations, systemId=id)
        DbSystem._validateBases(name='bases', value=bases, systemId=id)
        DbSystem._validateStars(name='stars', value=stars, systemId=id)
        DbSystem._validateCustomRemarks(name='customRemarks', value=customRemarks, systemId=id)
        common.validateOptionalStr(name='notes', value=notes)

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

    @staticmethod
    def _validateAllegiance(
            name: str,
            value: typing.Optional[DbAllegiance],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalObject(name=name, value=value, type=DbAllegiance)
        if not value:
            return

        if sectorId is not None and sectorId != value.sectorId():
            raise ValueError('{name} references an allegiance from another sector')

    @staticmethod
    def _validateNobilities(
            name: str,
            value: typing.Optional[typing.Collection[DbNobility]],
            systemId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbNobility)
        if not value:
            return

        seen = set()
        for nobility in value:
            currentSystemId = nobility.systemId()
            if currentSystemId is not None and currentSystemId != systemId:
                raise ValueError('{name} contains nobilities that are already attached to a system')

            code = nobility.code()
            if code in seen:
                raise ValueError('{name} contains multiple instances of the same nobility')
            seen.add(code)

    @staticmethod
    def _validateTradeCodes(
            name: str,
            value: typing.Optional[typing.Collection[DbTradeCode]],
            systemId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbTradeCode)
        if not value:
            return

        seen = set()
        for tradeCode in value:
            currentSystemId = tradeCode.systemId()
            if currentSystemId is not None and currentSystemId != systemId:
                raise ValueError('{name} contains trade codes that are already attached to a system')

            code = tradeCode.code()
            if code in seen:
                raise ValueError('{name} contains multiple instances of the same trade code')
            seen.add(code)

    @staticmethod
    def _validateSophontPopulations(
            name: str,
            value: typing.Optional[typing.Collection[DbSophontPopulation]],
            systemId: typing.Optional[str],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbSophontPopulation)
        if not value:
            return

        seen = set()
        for population in value:
            currentSystemId = population.systemId()
            if currentSystemId is not None and currentSystemId != systemId:
                raise ValueError('{name} contains populations that are already attached to a system')

            sophont = population.sophont()
            if sectorId is not None and sectorId != sophont.sectorId():
                raise ValueError('{name} contains populations that references a sophont from another sector')

            if sophont in seen:
                raise ValueError('{name} contains multiple populations for the same sophont')
            seen.add(sophont)

    @staticmethod
    def _validateRulingAllegiances(
            name: str,
            value: typing.Optional[typing.Collection[DbRulingAllegiance]],
            systemId: typing.Optional[str],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbRulingAllegiance)
        if not value:
            return

        seen = set()
        for ruler in value:
            currentSystemId = ruler.systemId()
            if currentSystemId is not None and currentSystemId != systemId:
                raise ValueError('{name} contains ruling allegiances that are already attached to a system')

            allegiance = ruler.allegiance()
            if sectorId is not None and sectorId != allegiance.sectorId():
                raise ValueError('{name} contains ruling allegiances that references an allegiance from another sector')

            if allegiance in seen:
                raise ValueError('{name} contains multiple ruling allegiances for the same allegiance')
            seen.add(allegiance)

    @staticmethod
    def _validateOwningSystems(
            name: str,
            value: typing.Optional[typing.Collection[DbOwningSystem]],
            systemId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbOwningSystem)
        if not value:
            return

        seen = set()
        for owner in value:
            currentSystemId = owner.systemId()
            if currentSystemId is not None and currentSystemId != systemId:
                raise ValueError('{name} contains owning systems that are already attached to a system')

            key = (owner.hexX(), owner.hexY(), owner.sectorAbbreviation())
            if key in seen:
                raise ValueError('{name} contains multiple instances of the same owning system')
            seen.add(key)

    @staticmethod
    def _validateColonySystems(
            name: str,
            value: typing.Optional[typing.Collection[DbColonySystem]],
            systemId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbColonySystem)
        if not value:
            return

        seen = set()
        for colony in value:
            currentSystemId = colony.systemId()
            if currentSystemId is not None and currentSystemId != systemId:
                raise ValueError('{name} contains colony systems that are already attached to a system')

            key = (colony.hexX(), colony.hexY(), colony.sectorAbbreviation())
            if key in seen:
                raise ValueError('{name} contains multiple instances of the same colony system')
            seen.add(key)

    @staticmethod
    def _validateResearchStations(
            name: str,
            value: typing.Optional[typing.Collection[DbResearchStation]],
            systemId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbResearchStation)
        if not value:
            return

        seen = set()
        for station in value:
            currentSystemId = station.systemId()
            if currentSystemId is not None and currentSystemId != systemId:
                raise ValueError('{name} contains research stations that are already attached to a system')

            code = station.code()
            if code in seen:
                raise ValueError('{name} contains multiple instances of the same research station')
            seen.add(code)

    @staticmethod
    def _validateBases(
            name: str,
            value: typing.Optional[typing.Collection[DbBase]],
            systemId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbBase)
        if not value:
            return

        seen = set()
        for base in value:
            currentSystemId = base.systemId()
            if currentSystemId is not None and currentSystemId != systemId:
                raise ValueError('{name} contains bases that are already attached to a system')

            code = base.code()
            if code in seen:
                raise ValueError('{name} contains multiple instances of the same base code')
            seen.add(code)

    @staticmethod
    def _validateStars(
            name: str,
            value: typing.Optional[typing.Collection[DbStar]],
            systemId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbStar)
        if not value:
            return

        for base in value:
            currentSystemId = base.systemId()
            if currentSystemId is not None and currentSystemId != systemId:
                raise ValueError('{name} contains stars that are already attached to a system')

    @staticmethod
    def _validateCustomRemarks(
            name: str,
            value: typing.Optional[typing.Collection[DbCustomRemark]],
            systemId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbCustomRemark)
        if not value:
            return

        for base in value:
            currentSystemId = base.systemId()
            if currentSystemId is not None and currentSystemId != systemId:
                raise ValueError('{name} contains custom remarks that are already attached to a system')

class DbAlternateName(DbSectorObject):
    def __init__(
            self,
            name: str,
            language: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, sectorId=sectorId)

        common.validateMandatoryStr(name='name', value=name, allowEmpty=False)
        common.validateOptionalStr(name='language', value=language, allowEmpty=False)

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
        super().__init__(id=id, sectorId=sectorId)

        common.validateMandatoryStr(name='code', value=code, allowed=_ValidSubsectorCodes)
        common.validateMandatoryStr(name='name', value=name, allowEmpty=False)

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
        super().__init__(id=id, sectorId=sectorId)

        common.validateMandatoryInt(name='startHexX', value=startHexX)
        common.validateMandatoryInt(name='startHexY', value=startHexY)
        common.validateMandatoryInt(name='endHexX', value=endHexX)
        common.validateMandatoryInt(name='endHexY', value=endHexY)
        common.validateOptionalInt(name='startOffsetX', value=startOffsetX)
        common.validateOptionalInt(name='startOffsetY', value=startOffsetY)
        common.validateOptionalInt(name='endOffsetX', value=endOffsetX)
        common.validateOptionalInt(name='endOffsetY', value=endOffsetY)
        common.validateOptionalStr(name='type', value=type, allowEmpty=False)
        common.validateOptionalStr(name='style', value=style, allowed=_ValidLineStyles)
        common.validateOptionalHtmlColour(name='colour', value=colour)
        common.validateOptionalFloat(name='width', value=width, min=0)
        common.validateOptionalObject(name='allegiance', value=allegiance, type=DbAllegiance)

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
        super().__init__(id=id, sectorId=sectorId)

        common.validateMandatoryCollection(name='hexes', value=hexes, allowEmpty=False, validationFn=DbBorder._hexTupleValidator)
        common.validateOptionalObject(name='allegiance', value=allegiance, type=DbAllegiance)
        common.validateOptionalStr(name='style', value=style, allowed=_ValidLineStyles)
        common.validateOptionalHtmlColour(name='colour', value=colour)
        common.validateOptionalStr(name='label', value=label, allowEmpty=False)
        common.validateOptionalFloat(name='labelWorldX', value=labelWorldX)
        common.validateOptionalFloat(name='labelWorldY', value=labelWorldY)
        common.validateMandatoryBool(name='showLabel', value=showLabel)
        common.validateMandatoryBool(name='wrapLabel', value=wrapLabel)

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
        super().__init__(id=id, sectorId=sectorId)

        common.validateMandatoryCollection(name='hexes', value=hexes, allowEmpty=False, validationFn=DbBorder._hexTupleValidator)
        common.validateOptionalHtmlColour(name='colour', value=colour)
        common.validateOptionalStr(name='label', value=label, allowEmpty=False)
        common.validateOptionalFloat(name='labelWorldX', value=labelWorldX)
        common.validateOptionalFloat(name='labelWorldY', value=labelWorldY)
        common.validateMandatoryBool(name='showLabel', value=showLabel)
        common.validateMandatoryBool(name='wrapLabel', value=wrapLabel)

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
        super().__init__(id=id, sectorId=sectorId)

        common.validateMandatoryStr(name='text', value=text)
        common.validateMandatoryFloat(name='worldX', value=worldX)
        common.validateMandatoryFloat(name='worldY', value=worldY)
        common.validateOptionalHtmlColour(name='colour', value=colour)
        common.validateOptionalStr(name='size', value=size, allowed=_ValidLabelSizes)
        common.validateMandatoryBool(name='wrap', value=wrap)

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
        super().__init__(id=id, sectorId=sectorId)

        common.validateOptionalStr(name='publication', value=publication, allowEmpty=False)
        common.validateOptionalStr(name='author', value=author, allowEmpty=False)
        common.validateOptionalStr(name='publisher', value=publisher, allowEmpty=False)
        common.validateOptionalStr(name='reference', value=reference, allowEmpty=False)

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
        super().__init__(id=id, sectorId=sectorId)

        common.validateMandatoryStr(name='tag', value=tag, allowEmpty=False)

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
        super().__init__(id=id, universeId=universeId)

        common.validateMandatoryBool(name='isCustom', value=isCustom)
        common.validateMandatoryStr(name='milieu', value=milieu, allowed=_ValidMilieu)
        common.validateMandatoryInt(name='sectorX', value=sectorX)
        common.validateMandatoryInt(name='sectorY', value=sectorY)
        common.validateMandatoryStr(name='primaryName', value=primaryName, allowEmpty=False)
        common.validateOptionalStr(name='primaryLanguage', value=primaryLanguage, allowEmpty=False)
        common.validateOptionalStr(name='abbreviation', value=abbreviation, allowEmpty=False)
        common.validateOptionalStr(name='sectorLabel', value=sectorLabel, allowEmpty=False)
        common.validateMandatoryBool(name='selected', value=selected)
        DbSector._validateAlternateNames(name='alternateNames', value=alternateNames, sectorId=id)
        DbSector._validateSubsectorNames(name='subsectorNames', value=subsectorNames, sectorId=id)
        DbSector._validateAllegiances(name='allegiances', value=allegiances, sectorId=id)
        DbSector._validateSophonts(name='sophonts', value=sophonts, sectorId=id)
        DbSector._validateSystems(name='systems', value=systems, sectorId=id)
        DbSector._validateRoutes(name='routes', value=routes, sectorId=id)
        DbSector._validateBorders(name='borders', value=borders, sectorId=id)
        DbSector._validateRegions(name='regions', value=regions, sectorId=id)
        DbSector._validateLabels(name='labels', value=labels, sectorId=id)
        DbSector._validateTags(name='tags', value=tags, sectorId=id)
        common.validateOptionalStr(name='credits', value=credits, allowEmpty=False)
        common.validateOptionalStr(name='publication', value=publication, allowEmpty=False)
        common.validateOptionalStr(name='author', value=author, allowEmpty=False)
        common.validateOptionalStr(name='publisher', value=publisher, allowEmpty=False)
        common.validateOptionalStr(name='reference', value=reference, allowEmpty=False)
        DbSector._validateProducts(name='products', value=products, sectorId=id)
        common.validateOptionalStr(name='notes', value=notes)

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

    @staticmethod
    def _validateAlternateNames(
            name: str,
            value: typing.Optional[typing.Collection[DbAlternateName]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbAlternateName)

        for alternateName in value:
            currentSectorId = alternateName.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError('{name} contains alternate names that are already attached to a sector')

    @staticmethod
    def _validateSubsectorNames(
            name: str,
            value: typing.Optional[typing.Collection[DbSubsectorName]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbSubsectorName)

        seen = set()
        for subsectorName in value:
            currentSectorId = subsectorName.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError('{name} contains subsector names that are already attached to a sector')

            code = subsectorName.code()
            if code in seen:
                raise ValueError('{name} contains multiple names for the same subsector')
            seen.add(code)

    @staticmethod
    def _validateAllegiances(
            name: str,
            value: typing.Optional[typing.Collection[DbAllegiance]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbAllegiance)

        seen = set()
        for allegiance in value:
            currentSectorId = allegiance.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError('{name} contains allegiances that are already attached to a sector')

            code = allegiance.code()
            if code in seen:
                raise ValueError('{name} contains multiple allegiances with the same code')
            seen.add(code)

    @staticmethod
    def _validateSophonts(
            name: str,
            value: typing.Optional[typing.Collection[DbSophont]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbSophont)

        seenCodes = set()
        seenNames = set()
        for sophont in value:
            currentSectorId = sophont.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError('{name} contains sophonts that are already attached to a sector')

            code = sophont.code()
            if code in seenCodes:
                raise ValueError('{name} contains multiple sophonts with the same code')
            seenCodes.add(code)

            name = sophont.code()
            if name in seenNames:
                raise ValueError('{name} contains multiple sophonts with the same name')
            seenNames.add(name)

    @staticmethod
    def _validateSystems(
            name: str,
            value: typing.Optional[typing.Collection[DbSystem]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbSystem)

        seen = set()
        for system in value:
            currentSectorId = system.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError('{name} contains systems that are already attached to a sector')

            key = (system.hexX(), system.hexY())
            if key in seen:
                raise ValueError('{name} contains multiple systems with the same location')
            seen.add(key)

    @staticmethod
    def _validateRoutes(
            name: str,
            value: typing.Optional[typing.Collection[DbRoute]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbRoute)

        for route in value:
            currentSectorId = route.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError('{name} contains routes that are already attached to a sector')

    @staticmethod
    def _validateBorders(
            name: str,
            value: typing.Optional[typing.Collection[DbBorder]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbBorder)

        for border in value:
            currentSectorId = border.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError('{name} contains borders that are already attached to a sector')

    @staticmethod
    def _validateRegions(
            name: str,
            value: typing.Optional[typing.Collection[DbRegion]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbRegion)

        for region in value:
            currentSectorId = region.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError('{name} contains regions that are already attached to a sector')

    @staticmethod
    def _validateLabels(
            name: str,
            value: typing.Optional[typing.Collection[DbLabel]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbLabel)

        for label in value:
            currentSectorId = label.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError('{name} contains labels that are already attached to a sector')

    @staticmethod
    def _validateTags(
            name: str,
            value: typing.Optional[typing.Collection[DbTag]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbTag)

        for tag in value:
            currentSectorId = tag.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError('{name} contains tags that are already attached to a sector')

    @staticmethod
    def _validateProducts(
            name: str,
            value: typing.Optional[typing.Collection[DbProduct]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbProduct)

        for tag in value:
            currentSectorId = tag.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError('{name} contains products that are already attached to a sector')

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
        super().__init__(id=id)

        common.validateMandatoryStr(name='name', value=name)
        common.validateOptionalStr(name='description', value=description)
        DbUniverse._validateSectors(name='sectors', value=sectors, universeId=id)
        common.validateOptionalStr(name='notes', value=notes)

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

    @staticmethod
    def _validateSectors(
            name: str,
            value: typing.Optional[typing.Collection[DbSector]],
            universeId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateOptionalCollection(name=name, value=value, type=DbSector)

        seen = set()
        for sector in value:
            currentSectorId = sector.universeId()
            if currentSectorId is not None and currentSectorId != universeId:
                raise ValueError('{name} contains sectors that are already attached to a universe')

            key = (sector.sectorX(), sector.sectorY(), sector.milieu())
            if key in seen:
                raise ValueError('{name} contains multiple systems with the same location and milieu')
            seen.add(key)