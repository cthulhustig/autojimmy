import common
import survey
import typing
import uuid

_ValidSubsectorCodes = set(map(chr, range(ord('A'), ord('P') + 1)))

_ValidLabelLayer = set(['mega', 'minor', 'world', 'border', 'rift', 'route'])

_ValidVectorLayer = set(['border', 'rift', 'route'])

_ValidTextAlignments = set([
    'baseline',
    'center',
    'top_left',
    'top_center',
    'top_right',
    'center_left',
    'center_right',
    'bottom_left',
    'bottom_center',
    'bottom_right'])

def _validateStrNoCase(
        name: str,
        value: str,
        allowed: typing.Collection[str]
        ) -> None:
    if value is not None and value.lower() not in allowed:
        raise ValueError(f'{name} must be one of [{",".join(allowed)}]')

def _validateWorldSpacePointElement(
        name: str,
        index: int,
        value: typing.Tuple[float, float]
        ) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f'{name} element at index {index} must be a tuple')
    if len(value) != 2:
        raise TypeError(f'{name} element at index {index} must have 2 elements')
    if not isinstance(value[0], (float, int)):
        raise TypeError(f'{name} element at index {index} x value must be a float')
    if not isinstance(value[1], (float, int)):
        raise TypeError(f'{name} element at index {index} y value must be a float')

class DbObject(object):
    def __init__(
            self,
            id: typing.Optional[str] = None, # None means allocate an id
            ) -> None:
        super().__init__()

        common.validateStr(name='id', value=id, allowNone=True, allowEmpty=False)

        # TODO: Some testing showed that switching to uuid7 is 10% faster when
        # importing the custom universe (2 seconds less). Unfortunately it's
        # only part of the standard library in Python 3.14+.
        # - Add some code that checks Python version and uses uuid7 if available.
        #   It should be something that gets run once when the py file is loaded
        #   rather than something is checked every time an object is constructed.
        #   Store the function as a global variable or something like that.
        # - I should upgrade my install to Python 3.14+ before I do any serious
        #   testing of the db/editor changes
        # - I should also update the build machine to Python 3.14+
        # https://andersmurphy.com/2026/06/05/the-perils-of-uuid-primary-keys-in-sqlite.html
        self._id = id if id is not None else str(uuid.uuid4())

    def id(self) -> str:
        return self._id

class DbUniverseObject(DbObject):
    pass

class DbSectorObject(DbObject):
    def __init__(
            self,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        common.validateStr(name='sectorId', value=sectorId, allowNone=True, allowEmpty=False)

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
        common.validateStr(name='sectorId', value=sectorId, allowEmpty=False)

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

        common.validateStr(name='systemId', value=systemId, allowNone=True, allowEmpty=False)

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
        common.validateStr(name='systemId', value=systemId, allowEmpty=False)

        if systemId == self._systemId:
            return # Nothing to do

        if self._systemId is not None:
            raise RuntimeError(f'Object {self._id} of type {type(self)} is already attached to a system')

        self._systemId = systemId

class DbWorldObject(DbObject):
    def __init__(
            self,
            id: typing.Optional[str] = None, # None means allocate an id
            worldId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        common.validateStr(name='worldId', value=worldId, allowNone=True, allowEmpty=False)

        self._worldId = worldId

    def worldId(self) -> typing.Optional[str]:
        return self._worldId

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
    def setWorldId(self, worldId: str) -> None:
        common.validateStr(name='worldId', value=worldId, allowEmpty=False)

        if worldId == self._worldId:
            return # Nothing to do

        if self._worldId is not None:
            raise RuntimeError(f'Object {self._id} of type {type(self)} is already attached to a world')

        self._worldId = worldId

class DbNobility(DbWorldObject):
    def __init__(
            self,
            code: str,
            id: typing.Optional[str] = None, # None means allocate an id
            worldId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, worldId=worldId)

        survey.validateNobility(name='code', value=code)

        self._code = code

    def code(self) -> str:
        return self._code

class DbTradeCode(DbWorldObject):
    def __init__(
            self,
            code: str,
            id: typing.Optional[str] = None, # None means allocate an id
            worldId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, worldId=worldId)

        survey.validateTradeCode(name='code', value=code)

        self._code = code

    def code(self) -> str:
        return self._code

class DbSophontPopulation(DbWorldObject):
    def __init__(
            self,
            sophontId: str,
            percentage: typing.Optional[int], # None means it's a die back sophont
            isHomeWorld: bool,
            isDieBack: bool,
            id: typing.Optional[str] = None, # None means allocate an id
            worldId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, worldId=worldId)

        common.validateStr(name='sophontId', value=sophontId, allowEmpty=False)
        survey.validateSophontPercentage(name='percentage', value=percentage, allowNone=True)
        common.validateBool(name='isHomeWorld', value=isHomeWorld)
        common.validateBool(name='isDieBack', value=isDieBack)

        self._sophontId = sophontId
        self._percentage = percentage
        self._isHomeWorld = isHomeWorld
        self._isDieBack = isDieBack

    def sophontId(self) -> str:
        return self._sophontId

    def percentage(self) -> typing.Optional[int]:
        return self._percentage

    def isHomeWorld(self) -> bool:
        return self._isHomeWorld

    def isDieBack(self) -> bool:
        return self._isDieBack

class DbRulingAllegiance(DbWorldObject):
    def __init__(
            self,
            allegianceId: str,
            id: typing.Optional[str] = None, # None means allocate an id
            worldId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, worldId=worldId)

        common.validateStr(name='allegianceId', value=allegianceId, allowEmpty=False)

        self._allegianceId = allegianceId

    def allegianceId(self) -> str:
        return self._allegianceId

class DbOwningSystem(DbWorldObject):
    def __init__(
            self,
            hexX: int,
            hexY: int,
            sectorAbbreviation: typing.Optional[str], # None means current sector
            id: typing.Optional[str] = None, # None means allocate an id
            worldId: typing.Optional[str] = None
            ):
        super().__init__(id=id, worldId=worldId)

        survey.validateHexX(name='hexX', value=hexX)
        survey.validateHexY(name='hexY', value=hexY)
        common.validateStr(name='sectorAbbreviation', value=sectorAbbreviation, allowNone=True, allowEmpty=False)

        self._hexX = hexX
        self._hexY = hexY
        self._sectorAbbreviation = sectorAbbreviation

    def hexX(self) -> int:
        return self._hexX

    def hexY(self) -> int:
        return self._hexY

    def sectorAbbreviation(self) -> typing.Optional[str]:
        return self._sectorAbbreviation

class DbColonySystem(DbWorldObject):
    def __init__(
            self,
            hexX: int,
            hexY: int,
            sectorAbbreviation: typing.Optional[str], # None means current sector
            id: typing.Optional[str] = None, # None means allocate an id
            worldId: typing.Optional[str] = None
            ):
        super().__init__(id=id, worldId=worldId)

        survey.validateHexX(name='hexX', value=hexX)
        survey.validateHexY(name='hexY', value=hexY)
        common.validateStr(name='sectorAbbreviation', value=sectorAbbreviation, allowNone=True, allowEmpty=False)

        self._hexX = hexX
        self._hexY = hexY
        self._sectorAbbreviation = sectorAbbreviation

    def hexX(self) -> int:
        return self._hexX

    def hexY(self) -> int:
        return self._hexY

    def sectorAbbreviation(self) -> typing.Optional[str]:
        return self._sectorAbbreviation

class DbCustomRemark(DbWorldObject):
    def __init__(
            self,
            remark: str,
            id: typing.Optional[str] = None, # None means allocate an id
            worldId: typing.Optional[str] = None
            ):
        super().__init__(id=id, worldId=worldId)

        common.validateStr(name='remark', value=remark, allowEmpty=False)

        self._remark = remark

    def remark(self) -> str:
        return self._remark

class DbBase(DbWorldObject):
    def __init__(
            self,
            code: str,
            id: typing.Optional[str] = None, # None means allocate an id
            worldId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, worldId=worldId)

        survey.validateBase(name='code', value=code)

        self._code = code

    def code(self) -> str:
        return self._code

class DbResearchStation(DbWorldObject):
    def __init__(
            self,
            code: str,
            id: typing.Optional[str] = None, # None means allocate an id
            worldId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, worldId=worldId)

        survey.validateResearchStation(name='code', value=code)

        self._code = code

    def code(self) -> str:
        return self._code

class DbBody(DbSystemObject):
    def __init__(
            self,
            orbitIndex: int,
            name: typing.Optional[str] = None,
            notes: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, systemId=systemId)

        common.validateInt(name='orbitIndex', value=orbitIndex)
        common.validateStr(name='name', value=name, allowNone=True, allowEmpty=False)
        common.validateStr(name='notes', value=notes, allowNone=True)

        self._orbitIndex = orbitIndex
        self._name = name
        self._notes = notes

    def orbitIndex(self) -> int:
        return self._orbitIndex

    def name(self) -> str:
        return self._name

    def notes(self) -> typing.Optional[str]:
        return self._notes

class DbWorld(DbBody):
    def __init__(
            self,
            orbitIndex: int,
            name: typing.Optional[str] = None,
            isMainWorld: bool = False,
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
            # PBG (Belts and Gas Giants are stored at the DbSystem level)
            populationMultiplier: typing.Optional[str] = None,
            nobilities: typing.Optional[typing.Collection[DbNobility]] = None,
            bases: typing.Optional[typing.Collection[DbBase]] = None,
            tradeCodes: typing.Optional[typing.Collection[DbTradeCode]] = None,
            sophontPopulations: typing.Optional[typing.Collection[DbSophontPopulation]] = None,
            rulingAllegiances: typing.Optional[typing.Collection[DbRulingAllegiance]] = None,
            owningSystems: typing.Optional[typing.Collection[DbOwningSystem]] = None,
            colonySystems: typing.Optional[typing.Collection[DbColonySystem]] = None,
            researchStations: typing.Optional[typing.Collection[DbResearchStation]] = None,
            customRemarks: typing.Optional[typing.Collection[DbCustomRemark]] = None,
            notes: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        super().__init__(
            id=id,
            systemId=systemId,
            orbitIndex=orbitIndex,
            name=name,
            notes=notes)

        common.validateBool(name='isMainWorld', value=isMainWorld)
        survey.validateStarport(name='starport', value=starport, allowNone=True)
        survey.validateWorldSize(name='worldSize', value=worldSize, allowNone=True)
        survey.validateAtmosphere(name='atmosphere', value=atmosphere, allowNone=True)
        survey.validateHydrographics(name='hydrographics', value=hydrographics, allowNone=True)
        survey.validatePopulation(name='population', value=population, allowNone=True)
        survey.validateGovernment(name='government', value=government, allowNone=True)
        survey.validateLawLevel(name='lawLevel', value=lawLevel, allowNone=True)
        survey.validateTechLevel(name='techLevel', value=techLevel, allowNone=True)
        survey.validateResources(name='resources', value=resources, allowNone=True)
        survey.validateLabour(name='labour', value=labour, allowNone=True)
        survey.validateInfrastructure(name='infrastructure', value=infrastructure, allowNone=True)
        survey.validateEfficiency(name='efficiency', value=efficiency, allowNone=True)
        survey.validateHeterogeneity(name='heterogeneity', value=heterogeneity, allowNone=True)
        survey.validateAcceptance(name='acceptance', value=acceptance, allowNone=True)
        survey.validateStrangeness(name='strangeness', value=strangeness, allowNone=True)
        survey.validateSymbols(name='symbols', value=symbols, allowNone=True)
        survey.validatePopulationMultiplier(name='populationMultiplier', value=populationMultiplier, allowNone=True)
        DbWorld._validateNobilities(name='nobilities', value=nobilities, worldId=id)
        DbWorld._validateBases(name='bases', value=bases, worldId=id)
        DbWorld._validateTradeCodes(name='tradeCodes', value=tradeCodes, worldId=id)
        DbWorld._validateSophontPopulations(name='sophontPopulations', value=sophontPopulations, worldId=id)
        DbWorld._validateRulingAllegiances(name='rulingAllegiances', value=rulingAllegiances, worldId=id)
        DbWorld._validateOwningSystems(name='owningSystems', value=owningSystems, worldId=id)
        DbWorld._validateColonySystems(name='colonySystems', value=colonySystems, worldId=id)
        DbWorld._validateResearchStations(name='researchStations', value=researchStations, worldId=id)
        DbWorld._validateCustomRemarks(name='customRemarks', value=customRemarks, worldId=id)

        self._isMainWorld = isMainWorld
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

        self._nobilities = list(nobilities) if nobilities else None
        self._attachObjects(self._nobilities)
        self._bases = list(bases) if bases else None
        self._attachObjects(self._bases)
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

    def isMainWorld(self) -> bool:
        return self._isMainWorld

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

    def resources(self) -> typing.Optional[str]:
        return self._resources

    def labour(self) -> typing.Optional[str]:
        return self._labour

    def infrastructure(self) -> typing.Optional[str]:
        return self._infrastructure

    def efficiency(self) -> typing.Optional[str]:
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

    def nobilities(self) -> typing.Optional[typing.Collection[DbNobility]]:
        return self._nobilities

    def bases(self) -> typing.Optional[typing.Collection[DbBase]]:
        return self._bases

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

    def _attachObjects(
            self,
            objects: typing.Optional[typing.Iterable[DbWorldObject]]
            ) -> None:
        if not objects:
            return
        for obj in objects:
            obj.setWorldId(worldId=self._id)

    @staticmethod
    def _validateNobilities(
            name: str,
            value: typing.Optional[typing.Collection[DbNobility]],
            worldId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbNobility, allowNone=True)
        if not value:
            return

        seen = set()
        for nobility in value:
            currentWorldId = nobility.worldId()
            if currentWorldId is not None and currentWorldId != worldId:
                raise ValueError(f'{name} contains nobilities that are already attached to a system')

            code = nobility.code()
            if code in seen:
                raise ValueError(f'{name} contains multiple instances of the same nobility')
            seen.add(code)

    @staticmethod
    def _validateBases(
            name: str,
            value: typing.Optional[typing.Collection[DbBase]],
            worldId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbBase, allowNone=True)
        if not value:
            return

        seen = set()
        for base in value:
            currentWorldId = base.worldId()
            if currentWorldId is not None and currentWorldId != worldId:
                raise ValueError(f'{name} contains bases that are already attached to a world')

            code = base.code()
            if code in seen:
                raise ValueError(f'{name} contains multiple instances of the same base code')
            seen.add(code)

    @staticmethod
    def _validateTradeCodes(
            name: str,
            value: typing.Optional[typing.Collection[DbTradeCode]],
            worldId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbTradeCode, allowNone=True)
        if not value:
            return

        seen = set()
        for tradeCode in value:
            currentWorldId = tradeCode.worldId()
            if currentWorldId is not None and currentWorldId != worldId:
                raise ValueError(f'{name} contains trade codes that are already attached to a world')

            code = tradeCode.code()
            if code in seen:
                raise ValueError(f'{name} contains multiple instances of the same trade code')
            seen.add(code)

    @staticmethod
    def _validateSophontPopulations(
            name: str,
            value: typing.Optional[typing.Collection[DbSophontPopulation]],
            worldId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbSophontPopulation, allowNone=True)
        if not value:
            return

        seen = set()
        for population in value:
            currentWorldId = population.worldId()
            if currentWorldId is not None and currentWorldId != worldId:
                raise ValueError(f'{name} contains populations that are already attached to a world')

            sophont = population.sophontId()
            if sophont in seen:
                raise ValueError(f'{name} contains multiple populations for the same sophont')
            seen.add(sophont)

    @staticmethod
    def _validateRulingAllegiances(
            name: str,
            value: typing.Optional[typing.Collection[DbRulingAllegiance]],
            worldId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbRulingAllegiance, allowNone=True)
        if not value:
            return

        seen = set()
        for ruler in value:
            currentWorldId = ruler.worldId()
            if currentWorldId is not None and currentWorldId != worldId:
                raise ValueError(f'{name} contains ruling allegiances that are already attached to a world')

            allegiance = ruler.allegianceId()
            if allegiance in seen:
                raise ValueError(f'{name} contains multiple ruling allegiances for the same allegiance')
            seen.add(allegiance)

    @staticmethod
    def _validateOwningSystems(
            name: str,
            value: typing.Optional[typing.Collection[DbOwningSystem]],
            worldId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbOwningSystem, allowNone=True)
        if not value:
            return

        seen = set()
        for owner in value:
            currentWorldId = owner.worldId()
            if currentWorldId is not None and currentWorldId != worldId:
                raise ValueError(f'{name} contains owning systems that are already attached to a world')

            key = (owner.hexX(), owner.hexY(), owner.sectorAbbreviation())
            if key in seen:
                raise ValueError(f'{name} contains multiple instances of the same owning system')
            seen.add(key)

    @staticmethod
    def _validateColonySystems(
            name: str,
            value: typing.Optional[typing.Collection[DbColonySystem]],
            worldId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbColonySystem, allowNone=True)
        if not value:
            return

        seen = set()
        for colony in value:
            currentWorldId = colony.worldId()
            if currentWorldId is not None and currentWorldId != worldId:
                raise ValueError(f'{name} contains colony systems that are already attached to a world')

            key = (colony.hexX(), colony.hexY(), colony.sectorAbbreviation())
            if key in seen:
                raise ValueError(f'{name} contains multiple instances of the same colony system')
            seen.add(key)

    @staticmethod
    def _validateResearchStations(
            name: str,
            value: typing.Optional[typing.Collection[DbResearchStation]],
            worldId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbResearchStation, allowNone=True)
        if not value:
            return

        seen = set()
        for station in value:
            currentWorldId = station.worldId()
            if currentWorldId is not None and currentWorldId != worldId:
                raise ValueError(f'{name} contains research stations that are already attached to a world')

            code = station.code()
            if code in seen:
                raise ValueError(f'{name} contains multiple instances of the same research station')
            seen.add(code)

    @staticmethod
    def _validateCustomRemarks(
            name: str,
            value: typing.Optional[typing.Collection[DbCustomRemark]],
            worldId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbCustomRemark, allowNone=True)
        if not value:
            return

        for remark in value:
            currentWorldId = remark.worldId()
            if currentWorldId is not None and currentWorldId != worldId:
                raise ValueError(f'{name} contains custom remarks that are already attached to a world')

class DbAllegiance(DbUniverseObject):
    def __init__(
            self,
            name: str,
            code: str,
            legacy: typing.Optional[str] = None,
            base: typing.Optional[str] = None,
            routeColour: typing.Optional[str] = None,
            routeStyle: typing.Optional[str] = None,
            routeWidth: typing.Optional[float] = None,
            borderColour: typing.Optional[str] = None,
            borderStyle: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            ) -> None:
        super().__init__(id=id)

        survey.validateAllegianceName(name='name', value=name)
        survey.validateAllegianceCode(name='code', value=code)
        survey.validateAllegianceCode(name='legacy', value=legacy, allowNone=True)
        survey.validateAllegianceCode(name='base', value=base, allowNone=True)
        survey.validateHtmlColour(name='routeColour', value=routeColour, allowNone=True)
        survey.validateLineStyle(name='routeStyle', value=routeStyle, allowNone=True)
        survey.validateLineWidth(name='routeWidth', value=routeWidth, allowNone=True)
        survey.validateHtmlColour(name='borderColour', value=borderColour, allowNone=True)
        survey.validateLineStyle(name='borderStyle', value=borderStyle, allowNone=True)

        self._name = name
        self._code = code
        self._legacy = legacy
        self._base = base
        self._routeColour = routeColour
        self._routeStyle = routeStyle
        self._routeWidth = routeWidth
        self._borderColour = borderColour
        self._borderStyle = borderStyle

    def name(self) -> str:
        return self._name

    def code(self) -> str:
        return self._code

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

class DbSophont(DbUniverseObject):
    def __init__(
            self,
            name: str,
            code: str,
            isMajor: bool,
            id: typing.Optional[str] = None # None means allocate an id
            ) -> None:
        super().__init__(id=id)

        survey.validateSophontCode(name='code', value=code)
        survey.validateSophontName(name='name', value=name)
        common.validateBool(name='isMajor', value=isMajor)

        self._name = name
        self._code = code
        self._isMajor = isMajor

    def name(self) -> str:
        return self._name

    def code(self) -> str:
        return self._code

    def isMajor(self) -> bool:
        return self._isMajor

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

        survey.validateLuminosityClass(name='luminosityClass', value=luminosityClass)
        survey.validateSpectralClass(name='spectralClass', value=spectralClass, allowNone=True)
        survey.validateSpectralScale(name='spectralScale', value=spectralScale, allowNone=True)

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
            # PBG (Population Multiplier is stored as the DbWorld level)
            planetoidBeltCount: typing.Optional[int] = None,
            gasGiantCount: typing.Optional[int] = None,
            # World count is my invention, it's calculated using the total system
            # world count that is (optionally) specified in sector files but with
            # logic applied that ignores total system world counts that are lower
            # than the specified number of belts + gas giants (basically ignores
            # negative values). The total system world count can be re-constituted
            # by calculating:
            # planetoid belt count + gas giant count + world count
            worldCount: typing.Optional[int] = None,
            zone: typing.Optional[str] = None,
            allegianceId: typing.Optional[str] = None,
            stars: typing.Optional[typing.Collection[DbStar]] = None,
            bodies: typing.Optional[typing.Collection[DbBody]] = None,
            notes: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, sectorId=sectorId)

        common.validateInt(name='hexX', value=hexX)
        common.validateInt(name='hexY', value=hexY)
        common.validateStr(name='name', value=name, allowNone=True, allowEmpty=False)
        common.validateInt(name='planetoidBeltCount', value=planetoidBeltCount, allowNone=True, min=0)
        common.validateInt(name='gasGiantCount', value=gasGiantCount, allowNone=True, min=0)
        common.validateInt(name='worldCount', value=worldCount, allowNone=True, min=0)
        survey.validateZone(name='zone', value=zone, allowNone=True)
        common.validateStr(name='allegianceId', value=allegianceId, allowNone=True, allowEmpty=False)
        DbSystem._validateStars(name='stars', value=stars, systemId=id)
        DbSystem._validateBodies(name='bodies', value=bodies, systemId=id)
        common.validateStr(name='notes', value=notes, allowNone=True)

        self._hexX = hexX
        self._hexY = hexY
        self._name = name
        self._planetoidBeltCount = planetoidBeltCount
        self._gasGiantCount = gasGiantCount
        self._worldCount = worldCount
        self._zone = zone
        self._allegianceId = allegianceId
        self._notes = notes

        self._stars = list(stars) if stars else None
        self._attachObjects(self._stars)
        self._bodies = list(bodies) if bodies else None
        self._attachObjects(self._bodies)

    def hexX(self) -> int:
        return self._hexX

    def hexY(self) -> int:
        return self._hexY

    def name(self) -> typing.Optional[str]:
        return self._name

    def planetoidBeltCount(self) -> typing.Optional[int]:
        return self._planetoidBeltCount

    def gasGiantCount(self) -> typing.Optional[int]:
        return self._gasGiantCount

    def worldCount(self) -> typing.Optional[int]:
        return self._worldCount

    def zone(self) -> typing.Optional[str]:
        return self._zone

    def allegianceId(self) -> typing.Optional[str]:
        return self._allegianceId

    def stars(self) -> typing.Optional[typing.Collection[DbStar]]:
        return self._stars

    def bodies(self) -> typing.Optional[typing.Collection[DbBody]]:
        return self._bodies

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
    def _validateStars(
            name: str,
            value: typing.Optional[typing.Collection[DbStar]],
            systemId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbStar, allowNone=True)
        if not value:
            return

        for base in value:
            currentSystemId = base.systemId()
            if currentSystemId is not None and currentSystemId != systemId:
                raise ValueError(f'{name} contains stars that are already attached to a system')

    @staticmethod
    def _validateBodies(
            name: str,
            value: typing.Optional[typing.Collection[DbBody]],
            systemId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbBody, allowNone=True)
        if not value:
            return

        hasWorld = False
        hasMainWorld = False
        for body in value:
            currentSystemId = body.systemId()
            if currentSystemId is not None and currentSystemId != systemId:
                raise ValueError(f'{name} contains bodies that are already attached to a system')

            if isinstance(body, DbWorld):
                hasWorld = True

                if body.isMainWorld():
                    if hasMainWorld:
                        raise ValueError(f'{name} contains more than one main world')
                    hasMainWorld = True

        if hasWorld and not hasMainWorld:
            raise ValueError(f'{name} contains worlds but has no main world')

class DbAlternateName(DbSectorObject):
    def __init__(
            self,
            name: str,
            language: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, sectorId=sectorId)

        common.validateStr(name='name', value=name, allowEmpty=False)
        common.validateStr(name='language', value=language, allowNone=True, allowEmpty=False)

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

        common.validateStr(name='code', value=code, allowedValues=_ValidSubsectorCodes)
        common.validateStr(name='name', value=name, allowEmpty=False)

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
            allegianceId: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, sectorId=sectorId)

        # TODO: Ideally I wouldn't allow invalid hexes here but I need to have
        # the conversion process convert invalid hexes to valid hexes with offsets
        survey.validateHexX(name='startHexX', value=startHexX, allowInvalid=True)
        survey.validateHexY(name='startHexY', value=startHexY, allowInvalid=True)
        survey.validateHexX(name='endHexX', value=endHexX, allowInvalid=True)
        survey.validateHexY(name='endHexY', value=endHexY, allowInvalid=True)
        common.validateInt(name='startOffsetX', value=startOffsetX, allowNone=True)
        common.validateInt(name='startOffsetY', value=startOffsetY, allowNone=True)
        common.validateInt(name='endOffsetX', value=endOffsetX, allowNone=True)
        common.validateInt(name='endOffsetY', value=endOffsetY, allowNone=True)
        common.validateStr(name='type', value=type, allowNone=True, allowEmpty=False)
        survey.validateLineStyle(name='style', value=style, allowNone=True)
        survey.validateHtmlColour(name='colour', value=colour, allowNone=True)
        survey.validateLineWidth(name='width', value=width, allowNone=True)
        common.validateStr(name='allegianceId', value=allegianceId, allowNone=True, allowEmpty=False)

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
        self._allegianceId = allegianceId

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

    def allegianceId(self) -> typing.Optional[str]:
        return self._allegianceId

class DbBorder(DbSectorObject):
    def __init__(
            self,
            hexes: typing.Sequence[typing.Tuple[int, int]],
            allegianceId: typing.Optional[str] = None,
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

        survey.validateHexSequence(name='hexes', value=hexes, allowInvalid=True, allowEmpty=False)
        common.validateStr(name='allegianceId', value=allegianceId, allowNone=True, allowEmpty=False)
        survey.validateLineStyle(name='style', value=style, allowNone=True)
        survey.validateHtmlColour(name='colour', value=colour, allowNone=True)
        common.validateStr(name='label', value=label, allowNone=True, allowEmpty=False)
        common.validateFloat(name='labelWorldX', value=labelWorldX, allowNone=True)
        common.validateFloat(name='labelWorldY', value=labelWorldY, allowNone=True)
        common.validateBool(name='showLabel', value=showLabel)
        common.validateBool(name='wrapLabel', value=wrapLabel)

        self._hexes = list(hexes)
        self._allegianceId = allegianceId
        self._style = style
        self._colour = colour
        self._label = label
        self._labelWorldX = labelWorldX
        self._labelWorldY = labelWorldY
        self._showLabel = showLabel
        self._wrapLabel = wrapLabel

    def hexes(self) -> typing.Sequence[typing.Tuple[int, int]]:
        return self._hexes

    def allegianceId(self) -> typing.Optional[str]:
        return self._allegianceId

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

        survey.validateHexSequence(name='hexes', value=hexes, allowInvalid=True, allowEmpty=False)
        survey.validateHtmlColour(name='colour', value=colour, allowNone=True)
        common.validateStr(name='label', value=label, allowNone=True, allowEmpty=False)
        common.validateFloat(name='labelWorldX', value=labelWorldX, allowNone=True)
        common.validateFloat(name='labelWorldY', value=labelWorldY, allowNone=True)
        common.validateBool(name='showLabel', value=showLabel)
        common.validateBool(name='wrapLabel', value=wrapLabel)

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

class DbSectorLabel(DbSectorObject):
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

        common.validateStr(name='text', value=text, allowEmpty=False)
        common.validateFloat(name='worldX', value=worldX)
        common.validateFloat(name='worldY', value=worldY)
        survey.validateHtmlColour(name='colour', value=colour, allowNone=True)
        survey.validateLabelSize(name='size', value=size, allowNone=True)
        common.validateBool(name='wrap', value=wrap)

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

        common.validateStr(name='publication', value=publication, allowNone=True, allowEmpty=False)
        common.validateStr(name='author', value=author, allowNone=True, allowEmpty=False)
        common.validateStr(name='publisher', value=publisher, allowNone=True, allowEmpty=False)
        common.validateStr(name='reference', value=reference, allowNone=True, allowEmpty=False)

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

        common.validateStr(name='tag', value=tag, allowEmpty=False)

        self._string = tag

    def tag(self) -> str:
        return self._string

class DbSector(DbUniverseObject):
    def __init__(
            self,
            sectorX: int,
            sectorY: int,
            name: str,
            language: typing.Optional[str] = None,
            abbreviation: typing.Optional[str] = None,
            sectorLabel: typing.Optional[str] = None,
            selected: bool = False,
            alternateNames: typing.Optional[typing.Collection[DbAlternateName]] = None,
            subsectorNames: typing.Optional[typing.Collection[DbSubsectorName]] = None,
            routes: typing.Optional[typing.Collection[DbRoute]] = None,
            borders: typing.Optional[typing.Collection[DbBorder]] = None,
            regions: typing.Optional[typing.Collection[DbRegion]] = None,
            labels: typing.Optional[typing.Collection[DbSectorLabel]] = None,
            tags: typing.Optional[typing.Collection[DbTag]] = None,
            credits: typing.Optional[str] = None,
            publication: typing.Optional[str] = None,
            author: typing.Optional[str] = None,
            publisher: typing.Optional[str] = None,
            reference: typing.Optional[str] = None,
            products: typing.Optional[typing.Collection[DbProduct]] = None,
            notes: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            ) -> None:
        super().__init__(id=id)

        common.validateInt(name='sectorX', value=sectorX)
        common.validateInt(name='sectorY', value=sectorY)
        common.validateStr(name='name', value=name, allowEmpty=False)
        common.validateStr(name='language', value=language, allowNone=True, allowEmpty=False)
        common.validateStr(name='abbreviation', value=abbreviation, allowNone=True, allowEmpty=False)
        common.validateStr(name='sectorLabel', value=sectorLabel, allowNone=True, allowEmpty=False)
        common.validateBool(name='selected', value=selected)
        DbSector._validateAlternateNames(name='alternateNames', value=alternateNames, sectorId=id)
        DbSector._validateSubsectorNames(name='subsectorNames', value=subsectorNames, sectorId=id)
        DbSector._validateRoutes(name='routes', value=routes, sectorId=id)
        DbSector._validateBorders(name='borders', value=borders, sectorId=id)
        DbSector._validateRegions(name='regions', value=regions, sectorId=id)
        DbSector._validateLabels(name='labels', value=labels, sectorId=id)
        DbSector._validateTags(name='tags', value=tags, sectorId=id)
        common.validateStr(name='credits', value=credits, allowNone=True, allowEmpty=False)
        common.validateStr(name='publication', value=publication, allowNone=True, allowEmpty=False)
        common.validateStr(name='author', value=author, allowNone=True, allowEmpty=False)
        common.validateStr(name='publisher', value=publisher, allowNone=True, allowEmpty=False)
        common.validateStr(name='reference', value=reference, allowNone=True, allowEmpty=False)
        DbSector._validateProducts(name='products', value=products, sectorId=id)
        common.validateStr(name='notes', value=notes, allowNone=True)

        self._sectorX = sectorX
        self._sectorY = sectorY
        self._name = name
        self._language = language
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

    def sectorX(self) -> int:
        return self._sectorX

    def sectorY(self) -> int:
        return self._sectorY

    def name(self) -> str:
        return self._name

    def language(self) -> typing.Optional[str]:
        return self._language

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

    def routes(self) -> typing.Optional[typing.Collection[DbRoute]]:
        return self._routes

    def borders(self) -> typing.Optional[typing.Collection[DbBorder]]:
        return self._borders

    def regions(self) -> typing.Optional[typing.Collection[DbRegion]]:
        return self._regions

    def labels(self) -> typing.Optional[typing.Collection[DbSectorLabel]]:
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

        common.validateCollection(name=name, value=value, elementType=DbAlternateName, allowNone=True)

        for alternateName in value:
            currentSectorId = alternateName.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError(f'{name} contains alternate names that are already attached to a sector')

    @staticmethod
    def _validateSubsectorNames(
            name: str,
            value: typing.Optional[typing.Collection[DbSubsectorName]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbSubsectorName, allowNone=True)

        seen = set()
        for subsectorName in value:
            currentSectorId = subsectorName.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError(f'{name} contains subsector names that are already attached to a sector')

            code = subsectorName.code()
            if code in seen:
                raise ValueError(f'{name} contains multiple names for the same subsector')
            seen.add(code)

    @staticmethod
    def _validateRoutes(
            name: str,
            value: typing.Optional[typing.Collection[DbRoute]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbRoute, allowNone=True)

        for route in value:
            currentSectorId = route.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError(f'{name} contains routes that are already attached to a sector')

    @staticmethod
    def _validateBorders(
            name: str,
            value: typing.Optional[typing.Collection[DbBorder]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbBorder, allowNone=True)

        for border in value:
            currentSectorId = border.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError(f'{name} contains borders that are already attached to a sector')

    @staticmethod
    def _validateRegions(
            name: str,
            value: typing.Optional[typing.Collection[DbRegion]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbRegion, allowNone=True)

        for region in value:
            currentSectorId = region.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError(f'{name} contains regions that are already attached to a sector')

    @staticmethod
    def _validateLabels(
            name: str,
            value: typing.Optional[typing.Collection[DbSectorLabel]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbSectorLabel, allowNone=True)

        for label in value:
            currentSectorId = label.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError(f'{name} contains labels that are already attached to a sector')

    @staticmethod
    def _validateTags(
            name: str,
            value: typing.Optional[typing.Collection[DbTag]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbTag, allowNone=True)

        for tag in value:
            currentSectorId = tag.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError(f'{name} contains tags that are already attached to a sector')

    @staticmethod
    def _validateProducts(
            name: str,
            value: typing.Optional[typing.Collection[DbProduct]],
            sectorId: typing.Optional[str]
            ) -> None:
        if value is None:
            return

        common.validateCollection(name=name, value=value, elementType=DbProduct, allowNone=True)

        for tag in value:
            currentSectorId = tag.sectorId()
            if currentSectorId is not None and currentSectorId != sectorId:
                raise ValueError(f'{name} contains products that are already attached to a sector')

class DbMapLabel(DbUniverseObject):
    def __init__(
            self,
            text: str,
            worldX: float,
            worldY: float,
            layer: str,
            alignment: typing.Optional[str] = None,
            colour: typing.Optional[str] = None,
            size: typing.Optional[str] = None,
            rotation: typing.Optional[float] = None,
            id: typing.Optional[str] = None # None means allocate an id
            ) -> None:
        super().__init__(id=id)

        common.validateStr(name='text', value=text, allowEmpty=False)
        common.validateFloat(name='worldX', value=worldX)
        common.validateFloat(name='worldY', value=worldY)
        common.validateStr(name='layer', value=layer, validationFn=lambda n, v: _validateStrNoCase(n, v, _ValidLabelLayer))
        common.validateStr(name='alignment', value=alignment, allowNone=True, validationFn=lambda n, v: _validateStrNoCase(n, v, _ValidTextAlignments))
        survey.validateHtmlColour(name='colour', value=colour, allowNone=True)
        survey.validateLabelSize(name='size', value=size, allowNone=True)
        common.validateFloat(name='rotation', value=rotation, allowNone=True)

        self._text = text
        self._worldX = worldX
        self._worldY = worldY
        self._layer = layer
        self._alignment = alignment
        self._colour = colour
        self._size = size
        self._rotation = rotation

    def text(self) -> str:
        return self._text

    def worldX(self) -> float:
        return self._worldX

    def worldY(self) -> float:
        return self._worldY

    def layer(self) -> str:
        return self._layer

    def alignment(self) -> typing.Optional[str]:
        return self._alignment

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def size(self) -> typing.Optional[str]:
        return self._size

    def rotation(self) -> typing.Optional[float]:
        return self._rotation

class DbMapVector(DbUniverseObject):
    def __init__(
            self,
            points: typing.Sequence[typing.Tuple[float, float]],
            layer: str,
            isClosed: bool,
            id: typing.Optional[str] = None # None means allocate an id
            ) -> None:
        super().__init__(id=id)

        common.validateSequence(name='points', value=points, allowEmpty=False, validationFn=_validateWorldSpacePointElement)
        common.validateStr(name='layer', value=layer, validationFn=lambda n, v: _validateStrNoCase(n, v, _ValidVectorLayer))
        common.validateBool(name='isClosed', value=isClosed)

        self._points = list(points)
        self._layer = layer
        self._isClosed = isClosed

    def points(self) -> typing.Sequence[typing.Tuple[float, float]]:
        return common.ConstSequenceRef(self._points)

    def layer(self) -> str:
        return self._layer

    def isClosed(self) -> bool:
        return self._isClosed