import typing
import uuid

# TODO: These classes should probably do some level of validation on that
# data they are passed

class DbObject(object):
    def __init__(
            self,
            id: typing.Optional[str] = None, # None means allocate an id
            ) -> None:
        super().__init__()
        self._id = id if id is not None else str(uuid.uuid4())

    def id(self) -> str:
        return self._id

class DbNobility(DbObject):
    def __init__(
            self,
            code: str,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        self.setSystemId(systemId)
        self.setCode(code)

    def systemId(self) -> typing.Optional[str]:
        return self._systemId

    def setSystemId(self, systemId: str) -> None:
        self._systemId = systemId

    def code(self) -> typing.Optional[str]:
        return self._code

    def setCode(self, code: typing.Optional[str]) -> None:
        self._code = code

class DbTradeCode(DbObject):
    def __init__(
            self,
            code: str,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        self.setSystemId(systemId)
        self.setCode(code)

    def systemId(self) -> typing.Optional[str]:
        return self._systemId

    def setSystemId(self, systemId: str) -> None:
        self._systemId = systemId

    def code(self) -> typing.Optional[str]:
        return self._code

    def setCode(self, code: typing.Optional[str]) -> None:
        self._code = code

class DbAllegiance(DbObject):
    def __init__(
            self,
            code: str,
            name: str,
            legacy: typing.Optional[str] = None,
            base: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        self.setSectorId(sectorId)
        self.setCode(code)
        self.setName(name)
        self.setLegacy(legacy)
        self.setBase(base)

    def sectorId(self) -> typing.Optional[str]:
        return self._sectorId

    def setSectorId(self, sectorId: str) -> None:
        self._sectorId = sectorId

    def code(self) -> str:
        return self._code

    def setCode(self, code: str) -> None:
        self._code = code

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> None:
        self._name = name

    def legacy(self) -> typing.Optional[str]:
        return self._legacy

    def setLegacy(self, legacy: typing.Optional[str]) -> None:
        self._legacy = legacy

    def base(self) -> typing.Optional[str]:
        return self._base

    def setBase(self, base: typing.Optional[str]) -> None:
        self._base = base

class DbRulingAllegiance(DbObject):
    def __init__(
            self,
            allegiance: DbAllegiance,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        self.setSystemId(systemId)
        self.setAllegiance(allegiance)

    def systemId(self) -> typing.Optional[str]:
        return self._systemId

    def setSystemId(self, systemId: str) -> None:
        self._systemId = systemId

    def allegiance(self) -> DbAllegiance:
        return self._allegiance

    def setAllegiance(self, allegiance: DbAllegiance) -> None:
        self._allegiance = allegiance

class DbSophont(DbObject):
    def __init__(
            self,
            code: str,
            name: str,
            isMajor: bool,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        self.setSectorId(sectorId)
        self.setCode(code)
        self.setName(name)
        self.setIsMajor(isMajor)

    def sectorId(self) -> typing.Optional[str]:
        return self._sectorId

    def setSectorId(self, sectorId: str) -> None:
        self._sectorId = sectorId

    def code(self) -> str:
        return self._code

    def setCode(self, code: str) -> None:
        self._code = code

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> None:
        self._name = name

    def isMajor(self) -> bool:
        return self._isMajor

    def setIsMajor(self, isMajor: bool) -> None:
        self._isMajor = isMajor

class DbSophontPopulation(DbObject):
    def __init__(
            self,
            sophont: DbSophont,
            percentage: typing.Optional[int], # None means it's a die back sophont
            isHomeWorld: bool,
            isDieBack: bool,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        self.setSystemId(systemId)
        self.setSophont(sophont)
        self.setPercentage(percentage)
        self.setIsHomeWorld(isHomeWorld)
        self.setIsDieBack(isDieBack)

    def systemId(self) -> typing.Optional[str]:
        return self._systemId

    def setSystemId(self, systemId: str) -> None:
        self._systemId = systemId

    def sophont(self) -> DbSophont:
        return self._sophont

    def setSophont(self, sophont: DbSophont) -> None:
        self._sophont = sophont

    def percentage(self) -> typing.Optional[int]:
        return self._percentage

    def setPercentage(self, percentage: typing.Optional[int]) -> None:
        self._percentage = percentage

    def isHomeWorld(self) -> bool:
        return self._isHomeWorld

    def setIsHomeWorld(self, isHomeWorld: bool) -> None:
        self._isHomeWorld = isHomeWorld

    def isDieBack(self) -> bool:
        return self._isDieBack

    def setIsDieBack(self, isDieback: bool) -> None:
        self._isDieBack = isDieback

class DbOwningSystem(DbObject):
    def __init__(
            self,
            hexX: int,
            hexY: int,
            sectorCode: typing.Optional[str], # None means current sector
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ):
        super().__init__(id)

        self.setSystemId(systemId)
        self.setHexX(hexX)
        self.setHexY(hexY)
        self.setSectorCode(sectorCode)

    def systemId(self) -> typing.Optional[str]:
        return self._systemId

    def setSystemId(self, systemId: str) -> None:
        self._systemId = systemId

    def hexX(self) -> int:
        return self._hexX

    def setHexX(self, hexX: int) -> None:
        self._hexX = hexX

    def hexY(self) -> int:
        return self._hexY

    def setHexY(self, hexY: int) -> None:
        self._hexY = hexY

    def sectorCode(self) -> typing.Optional[str]:
        return self._sectorCode

    def setSectorCode(self, sectorCode: typing.Optional[str]) -> None:
        self._sectorCode = sectorCode

class DbColonySystem(DbObject):
    def __init__(
            self,
            hexX: int,
            hexY: int,
            sectorCode: typing.Optional[str], # None means current sector
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ):
        super().__init__(id)

        self.setSystemId(systemId)
        self.setHexX(hexX)
        self.setHexY(hexY)
        self.setSectorCode(sectorCode)

    def systemId(self) -> typing.Optional[str]:
        return self._systemId

    def setSystemId(self, systemId: str) -> None:
        self._systemId = systemId

    def hexX(self) -> int:
        return self._hexX

    def setHexX(self, hexX: int) -> None:
        self._hexX = hexX

    def hexY(self) -> int:
        return self._hexY

    def setHexY(self, hexY: int) -> None:
        self._hexY = hexY

    def sectorCode(self) -> typing.Optional[str]:
        return self._sectorCode

    def setSectorCode(self, sectorCode: typing.Optional[str]) -> None:
        self._sectorCode = sectorCode

class DbCustomRemark(DbObject):
    def __init__(
            self,
            remark: str,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ):
        super().__init__(id)

        self.setSystemId(systemId)
        self.setRemark(remark)

    def systemId(self) -> typing.Optional[str]:
        return self._systemId

    def setSystemId(self, systemId: str) -> None:
        self._systemId = systemId

    def remark(self) -> str:
        return self._remark

    def setRemark(self, remark: str) -> None:
        self._remark = remark

class DbBase(DbObject):
    def __init__(
            self,
            code: str,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        self.setSystemId(systemId)
        self.setCode(code)

    def systemId(self) -> typing.Optional[str]:
        return self._systemId

    def setSystemId(self, systemId: str) -> None:
        self._systemId = systemId

    def code(self) -> str:
        return self._code

    def setCode(self, code: str) -> None:
        self._code = code

# TODO: Should I consolidate bases and research stations at the db level
# (and probably therefore at the astronomer level). They're basically the
# same structure and would just need mapped to/from bases/remarks when
# importing/exporting
class DbResearchStation(DbObject):
    def __init__(
            self,
            code: str,
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        self.setSystemId(systemId)
        self.setCode(code)

    def systemId(self) -> typing.Optional[str]:
        return self._systemId

    def setSystemId(self, systemId: str) -> None:
        self._systemId = systemId

    def code(self) -> str:
        return self._code

    def setCode(self, code: str) -> None:
        self._code = code

class DbStar(DbObject):
    def __init__(
            self,
            luminosityClass: str,
            spectralClass: typing.Optional[str],
            spectralScale: typing.Optional[str],
            id: typing.Optional[str] = None, # None means allocate an id
            systemId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        self.setSystemId(systemId)
        self.setLuminosityClass(luminosityClass)
        self.setSpectralClass(spectralClass)
        self.setSpectralScale(spectralScale)

    def systemId(self) -> typing.Optional[str]:
        return self._systemId

    def setSystemId(self, systemId: str) -> None:
        self._systemId = systemId

    def luminosityClass(self) -> str:
        return self._luminosityClass

    def setLuminosityClass(self, luminosityClass: str) -> None:
        self._luminosityClass = luminosityClass

    def spectralClass(self) -> typing.Optional[str]:
        return self._spectralClass

    def setSpectralClass(self, spectralClass: typing.Optional[str]) -> None:
        self._spectralClass = spectralClass

    def spectralScale(self) -> typing.Optional[str]:
        return self._spectralScale

    def setSpectralScale(self, spectralScale: typing.Optional[str]) -> None:
        self._spectralScale = spectralScale

class DbSystem(DbObject):
    def __init__(
            self,
            hexX: int,
            hexY: int,
            name: str, # TODO: Do worlds in sector files always have a name????
            uwp: str, # TODO: Do worlds in sector files always have a UWP
            economics: typing.Optional[str] = None,
            culture: typing.Optional[str] = None,
            zone: typing.Optional[str] = None,
            pbg: typing.Optional[str] = None,
            # System worlds can be None if the number is not not known (e.g. if uwp is ???????-?)
            # It can also be none due to it just not being specified in sector data
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
        super().__init__(id=id)

        self.setSectorId(sectorId)
        self.setHexX(hexX)
        self.setHexY(hexY)
        self.setName(name)
        self.setUWP(uwp)
        self.setEconomics(economics)
        self.setCulture(culture)
        self.setZone(zone)
        self.setPBG(pbg)
        self.setSystemWorlds(systemWorlds)
        self.setAllegiance(allegiance)
        self.setNobilities(nobilities)
        self.setTradeCodes(tradeCodes)
        self.setSophontPopulations(sophontPopulations)
        self.setRulingAllegiances(rulingAllegiances)
        self.setOwningSystems(owningSystems)
        self.setColonySystems(colonySystems)
        self.setResearchStations(researchStations)
        self.setCustomRemarks(customRemarks)
        self.setBases(bases)
        self.setStars(stars)
        self.setNotes(notes)

    def sectorId(self) -> typing.Optional[str]:
        return self._sectorId

    def setSectorId(self, sectorId: str) -> None:
        self._sectorId = sectorId

    def hexX(self) -> int:
        return self._hexX

    def setHexX(self, hexX: int) -> None:
        self._hexX = hexX

    def hexY(self) -> int:
        return self._hexY

    def setHexY(self, hexY: int) -> None:
        self._hexY = hexY

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> None:
        self._name = name

    def uwp(self) -> str:
        return self._uwp

    def setUWP(self, uwp: str) -> None:
        self._uwp = uwp

    def economics(self) -> typing.Optional[str]:
        return self._economics

    def setEconomics(self, economics: typing.Optional[str]) -> None:
        self._economics = economics

    def culture(self) -> typing.Optional[str]:
        return self._culture

    def setCulture(self, culture: typing.Optional[str]) -> None:
        self._culture = culture

    def zone(self) -> typing.Optional[str]:
        return self._zone

    def setZone(self, zone: typing.Optional[str]) -> None:
        self._zone = zone

    def pbg(self) -> typing.Optional[str]:
        return self._pbg

    def setPBG(self, pbg: typing.Optional[str]) -> None:
        self._pbg = pbg

    def systemWorlds(self) -> typing.Optional[int]:
        return self._systemWorlds

    def setSystemWorlds(self, systemWorlds: typing.Optional[int]) -> None:
        self._systemWorlds = systemWorlds

    def allegiance(self) -> typing.Optional[DbAllegiance]:
        return self._allegiance

    def setAllegiance(self, allegiance: typing.Optional[DbAllegiance]) -> None:
        self._allegiance = allegiance

    def nobilities(self) -> typing.Optional[typing.Collection[DbNobility]]:
        return self._nobilities

    def setNobilities(self, nobilities: typing.Optional[typing.Collection[DbNobility]]) -> None:
        self._nobilities = list(nobilities) if nobilities else None
        if self._nobilities:
            for code in self._nobilities:
                code.setSystemId(self._id)

    def addNobility(self, nobility: DbNobility) -> None:
        if self._nobilities is None:
            self._nobilities = []
        self._nobilities.append(nobility)
        nobility.setSystemId(self._id)

    def tradeCodes(self) -> typing.Optional[typing.Collection[DbTradeCode]]:
        return self._tradeCodes

    def setTradeCodes(self, tradeCodes: typing.Optional[typing.Collection[DbTradeCode]]) -> None:
        self._tradeCodes = list(tradeCodes) if tradeCodes else None
        if self._tradeCodes:
            for code in self._tradeCodes:
                code.setSystemId(self._id)

    def addTradeCode(self, tradeCode: DbTradeCode) -> None:
        if self._tradeCodes is None:
            self._tradeCodes = []
        self._tradeCodes.append(tradeCode)
        tradeCode.setSystemId(self._id)

    def sophontPopulations(self) -> typing.Optional[typing.Collection[DbSophontPopulation]]:
        return self._sophontPopulations

    # TODO: Something needs to check that the sophont ids used by the
    # supplied populations match a known sophont for the sector this
    # world is part of
    def setSophontPopulations(self, populations: typing.Collection[DbSophontPopulation]) -> None:
        self._sophontPopulations = list(populations) if populations else None
        if self._sophontPopulations:
            for sophont in self._sophontPopulations:
                sophont.setSystemId(self._id)

    def addSophontPopulation(self, population: DbSophontPopulation) -> None:
        if self._sophontPopulations is None:
            self._sophontPopulations = []
        self._sophontPopulations.append(population)
        population.setSystemId(self._id)

    def rulingAllegiances(self) -> typing.Optional[typing.Collection[DbRulingAllegiance]]:
        return self._rulingAllegiances

    def setRulingAllegiances(self, allegiances: typing.Optional[typing.Collection[DbRulingAllegiance]]) -> None:
        self._rulingAllegiances = list(allegiances) if allegiances else None
        if self._rulingAllegiances:
            for allegiance in self._rulingAllegiances:
                allegiance.setSystemId(self._id)

    def addRulingAllegiance(self, allegiance: DbRulingAllegiance) -> None:
        if self._rulingAllegiances is None:
            self._rulingAllegiances = []
        self._rulingAllegiances.append(allegiance)
        allegiance.setSystemId(self._id)

    def owningSystems(self) -> typing.Optional[typing.Collection[DbOwningSystem]]:
        return self._owningSystems

    def setOwningSystems(self, systems: typing.Optional[typing.Collection[DbOwningSystem]]) -> None:
        self._owningSystems = list(systems) if systems else None
        if self._owningSystems:
            for system in self._owningSystems:
                system.setSystemId(self._id)

    def addOwningSystem(self, system: DbOwningSystem) -> None:
        if self._owningSystems is None:
            self._owningSystems = []
        self._owningSystems.append(system)
        system.setSystemId(self._id)

    def colonySystems(self) -> typing.Optional[typing.Collection[DbColonySystem]]:
        return self._colonySystems

    def setColonySystems(self, systems: typing.Optional[typing.Collection[DbColonySystem]]) -> None:
        self._colonySystems = list(systems) if systems else None
        if self._colonySystems:
            for system in self._colonySystems:
                system.setSystemId(self._id)

    def addColonySystem(self, system: DbColonySystem) -> None:
        if self._colonySystems is None:
            self._colonySystems = []
        self._colonySystems.append(system)
        system.setSystemId(self._id)

    def researchStations(self) -> typing.Optional[typing.Collection[DbResearchStation]]:
        return self._researchStations

    def setResearchStations(self, stations: typing.Optional[typing.Collection[DbResearchStation]]) -> None:
        self._researchStations = list(stations) if stations else None
        if self._researchStations:
            for station in self._researchStations:
                station.setSystemId(self._id)

    def addResearchStation(self, station: DbResearchStation) -> None:
        if self._researchStations is None:
            self._researchStations = []
        self._researchStations.append(station)
        station.setSystemId(self._id)

    def customRemarks(self) -> typing.Optional[typing.Collection[DbCustomRemark]]:
        return self._customRemarks

    def setCustomRemarks(self, remarks: typing.Optional[typing.Collection[DbCustomRemark]]) -> None:
        self._customRemarks = list(remarks) if remarks else None
        if self._customRemarks:
            for remark in self._customRemarks:
                remark.setSystemId(self._id)

    def addCustomRemark(self, remark: DbCustomRemark) -> None:
        if self._customRemarks is None:
            self._customRemarks = []
        self._customRemarks.append(remark)
        remark.setSystemId(self._id)

    def bases(self) -> typing.Optional[typing.Collection[DbBase]]:
        return self._bases

    def setBases(self, bases: typing.Optional[typing.Collection[DbBase]]) -> None:
        self._bases = list(bases) if bases else None
        if self._bases:
            for base in self._bases:
                base.setSystemId(self._id)

    def addBase(self, base: DbBase) -> None:
        if self._bases is None:
            self._bases = []
        self._bases.append(base)
        base.setSystemId(self._id)

    def stars(self) -> typing.Optional[typing.Collection[DbStar]]:
        return self._stars

    def setStars(self, stars: typing.Optional[typing.Collection[DbStar]]) -> None:
        self._stars = list(stars) if stars else None
        if self._stars:
            for star in self._stars:
                star.setSystemId(self._id)

    def addStar(self, star: DbStar) -> None:
        if self._stars is None:
            self._stars = []
        self._stars.append(star)
        star.setSystemId(self._id)

    def notes(self) -> typing.Optional[str]:
        return self._notes

    def setNotes(self, notes: typing.Optional[str]) -> None:
        self._notes = notes

class DbRoute(DbObject):
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
        super().__init__(id=id)

        self.setSectorId(sectorId)
        self.setStartHexX(startHexX)
        self.setStartHexY(startHexY)
        self.setEndHexX(endHexX)
        self.setEndHexY(endHexY)
        self.setStartOffsetX(startOffsetX)
        self.setStartOffsetY(startOffsetY)
        self.setEndOffsetX(endOffsetX)
        self.setEndOffsetY(endOffsetY)
        self.setType(type)
        self.setStyle(style)
        self.setColour(colour)
        self.setWidth(width)
        self.setAllegiance(allegiance)

    def sectorId(self) -> typing.Optional[str]:
        return self._sectorId

    def setSectorId(self, sectorId: str) -> None:
        self._sectorId = sectorId

    def startHexX(self) -> int:
        return self._startHexX

    def setStartHexX(self, startHexX: int) -> None:
        self._startHexX = startHexX

    def startHexY(self) -> int:
        return self._startHexY

    def setStartHexY(self, startHexY: int) -> None:
        self._startHexY = startHexY

    def endHexX(self) -> int:
        return self._endHexX

    def setEndHexX(self, endHexX: int) -> None:
        self._endHexX = endHexX

    def endHexY(self) -> int:
        return self._endHexY

    def setEndHexY(self, endHexY: int) -> None:
        self._endHexY = endHexY

    def startOffsetX(self) -> int:
        return self._startOffsetX

    def setStartOffsetX(self, startOffsetX: int) -> None:
        self._startOffsetX = startOffsetX

    def startOffsetY(self) -> int:
        return self._startOffsetY

    def setStartOffsetY(self, startOffsetY: int) -> None:
        self._startOffsetY = startOffsetY

    def endOffsetX(self) -> int:
        return self._endOffsetX

    def setEndOffsetX(self, endOffsetX: int) -> None:
        self._endOffsetX = endOffsetX

    def endOffsetY(self) -> int:
        return self._endOffsetY

    def setEndOffsetY(self, endOffsetY: int) -> None:
        self._endOffsetY = endOffsetY

    def type(self) -> typing.Optional[str]:
        return self._type

    def setType(self, type: typing.Optional[str]) -> None:
        self._type = type

    def style(self) -> typing.Optional[str]:
        return self._style

    def setStyle(self, style: typing.Optional[str]) -> None:
        self._style = style

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def setColour(self, colour: typing.Optional[str]) -> None:
        self._colour = colour

    def width(self) -> typing.Optional[float]:
        return self._width

    def setWidth(self, width: typing.Optional[str]) -> None:
        self._width = width

    def allegiance(self) -> typing.Optional[DbAllegiance]:
        return self._allegiance

    def setAllegiance(self, allegiance: typing.Optional[DbAllegiance]) -> None:
        self._allegiance = allegiance

class DbBorder(DbObject):
    def __init__(
            self,
            hexes: typing.Iterable[typing.Tuple[int, int]],
            showLabel: bool, # TODO: This and wrap should be optional
            wrapLabel: bool,
            label: typing.Optional[str] = None,
            labelHexX: typing.Optional[int] = None,
            labelHexY: typing.Optional[int] = None,
            labelOffsetX: typing.Optional[float] = None,
            labelOffsetY: typing.Optional[float] = None,
            colour: typing.Optional[str] = None,
            style: typing.Optional[str] = None,
            allegiance: typing.Optional[DbAllegiance] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        self.setSectorId(sectorId)
        self.setHexes(hexes)
        self.setLabel(label)
        self.setShowLabel(showLabel)
        self.setWrapLabel(wrapLabel)
        self.setLabelHexX(labelHexX)
        self.setLabelHexY(labelHexY)
        self.setLabelOffsetX(labelOffsetX)
        self.setLabelOffsetY(labelOffsetY)
        self.setColour(colour)
        self.setStyle(style)
        self.setAllegiance(allegiance)

    def sectorId(self) -> typing.Optional[str]:
        return self._sectorId

    def setSectorId(self, sectorId: str) -> None:
        self._sectorId = sectorId

    def hexes(self) -> typing.Iterable[typing.Tuple[int, int]]:
        return self._hexes

    def setHexes(self, hexes: typing.Iterable[typing.Tuple[int, int]]) -> None:
        self._hexes = list(hexes)

    def showLabel(self) -> bool:
        return self._showLabel

    def setShowLabel(self, showLabel: bool) -> None:
        self._showLabel = showLabel

    def wrapLabel(self) -> bool:
        return self._wrapLabel

    def setWrapLabel(self, wrapLabel: bool) -> None:
        self._wrapLabel = wrapLabel

    def label(self) -> typing.Optional[str]:
        return self._label

    def setLabel(self, label: typing.Optional[str]) -> None:
        self._label = label

    def labelHexX(self) -> typing.Optional[int]:
        return self._labelHexX

    def setLabelHexX(self, labelHexX: typing.Optional[int]) -> None:
        self._labelHexX = labelHexX

    def labelHexY(self) -> typing.Optional[int]:
        return self._labelHexY

    def setLabelHexY(self, labelHexY: typing.Optional[int]) -> None:
        self._labelHexY = labelHexY

    def labelOffsetX(self) -> typing.Optional[float]:
        return self._labelOffsetX

    def setLabelOffsetX(self, labelOffsetX: typing.Optional[float]) -> None:
        self._labelOffsetX = labelOffsetX

    def labelOffsetY(self) -> typing.Optional[float]:
        return self._labelOffsetY

    def setLabelOffsetY(self, labelOffsetY: typing.Optional[float]) -> None:
        self._labelOffsetY = labelOffsetY

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def setColour(self, colour: typing.Optional[str]) -> None:
        self._colour = colour

    def style(self) -> typing.Optional[str]:
        return self._style

    def setStyle(self, style: typing.Optional[str]) -> None:
        self._style = style

    def allegiance(self) -> typing.Optional[DbAllegiance]:
        return self._allegiance

    def setAllegiance(self, allegiance: typing.Optional[DbAllegiance]) -> None:
        self._allegiance = allegiance

class DbRegion(DbObject):
    def __init__(
            self,
            hexes: typing.Iterable[typing.Tuple[int, int]],
            showLabel: bool, # TODO: This and wrap should be optional (and after the label string)
            wrapLabel: bool,
            label: typing.Optional[str] = None,
            labelHexX: typing.Optional[int] = None,
            labelHexY: typing.Optional[int] = None,
            labelOffsetX: typing.Optional[float] = None,
            labelOffsetY: typing.Optional[float] = None,
            colour: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        self.setSectorId(sectorId)
        self.setHexes(hexes)
        self.setLabel(label)
        self.setShowLabel(showLabel)
        self.setWrapLabel(wrapLabel)
        self.setLabelHexX(labelHexX)
        self.setLabelHexY(labelHexY)
        self.setLabelOffsetX(labelOffsetX)
        self.setLabelOffsetY(labelOffsetY)
        self.setColour(colour)

    def sectorId(self) -> typing.Optional[str]:
        return self._sectorId

    def setSectorId(self, sectorId: str) -> None:
        self._sectorId = sectorId

    def hexes(self) -> typing.Iterable[typing.Tuple[int, int]]:
        return self._hexes

    def setHexes(self, hexes: typing.Iterable[typing.Tuple[int, int]]) -> None:
        self._hexes = list(hexes)

    def showLabel(self) -> bool:
        return self._showLabel

    def setShowLabel(self, showLabel: bool) -> None:
        self._showLabel = showLabel

    def label(self) -> typing.Optional[str]:
        return self._label

    def setLabel(self, label: typing.Optional[str]) -> None:
        self._label = label

    def wrapLabel(self) -> bool:
        return self._wrapLabel

    def setWrapLabel(self, wrapLabel: bool) -> None:
        self._wrapLabel = wrapLabel

    def labelHexX(self) -> typing.Optional[int]:
        return self._labelHexX

    def setLabelHexX(self, labelHexX: typing.Optional[int]) -> None:
        self._labelHexX = labelHexX

    def labelHexY(self) -> typing.Optional[int]:
        return self._labelHexY

    def setLabelHexY(self, labelHexY: typing.Optional[int]) -> None:
        self._labelHexY = labelHexY

    def labelOffsetX(self) -> typing.Optional[float]:
        return self._labelOffsetX

    def setLabelOffsetX(self, labelOffsetX: typing.Optional[float]) -> None:
        self._labelOffsetX = labelOffsetX

    def labelOffsetY(self) -> typing.Optional[float]:
        return self._labelOffsetY

    def setLabelOffsetY(self, labelOffsetY: typing.Optional[float]) -> None:
        self._labelOffsetY = labelOffsetY

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def setColour(self, colour: typing.Optional[str]) -> None:
        self._colour = colour

class DbLabel(DbObject):
    def __init__(
            self,
            text: str,
            hexX: int,
            hexY: int,
            wrap: bool,
            colour: typing.Optional[str] = None,
            size: typing.Optional[str] = None,
            offsetX: typing.Optional[float] = None,
            offsetY: typing.Optional[float] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        self.setSectorId(sectorId)
        self.setText(text)
        self.setHexX(hexX)
        self.setHexY(hexY)
        self.setWrap(wrap)
        self.setColour(colour)
        self.setSize(size)
        self.setOffsetX(offsetX)
        self.setOffsetY(offsetY)

    def sectorId(self) -> typing.Optional[str]:
        return self._sectorId

    def setSectorId(self, sectorId: str) -> None:
        self._sectorId = sectorId

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = text

    def hexX(self) -> int:
        return self._hexX

    def setHexX(self, hexX: int) -> None:
        self._hexX = hexX

    def hexY(self) -> int:
        return self._hexY

    def setHexY(self, hexY: int) -> None:
        self._hexY = hexY

    def wrap(self) -> bool:
        return self._wrap

    def setWrap(self, wrap: int) -> None:
        self._wrap = wrap

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def setColour(self, colour: typing.Optional[str]) -> None:
        self._colour = colour

    def size(self) -> typing.Optional[str]:
        return self._size

    def setSize(self, size: typing.Optional[str]) -> None:
        self._size = size

    def offsetX(self) -> typing.Optional[float]:
        return self._offsetX

    def setOffsetX(self, offsetX: typing.Optional[float]) -> None:
        self._offsetX = offsetX

    def offsetY(self) -> typing.Optional[float]:
        return self._offsetY

    def setOffsetY(self, offsetY: typing.Optional[float]) -> None:
        self._offsetY = offsetY

# TODO: This should be a DbObject but it doesn't have an id in the table
class DbProduct(object):
    def __init__(
            self,
            publication: typing.Optional[str] = None,
            author: typing.Optional[str] = None,
            publisher: typing.Optional[str] = None,
            reference: typing.Optional[str] = None
            ) -> None:
        self.setPublication(publication)
        self.setPublisher(publisher)
        self.setAuthor(author)
        self.setReference(reference)

    def publication(self) -> typing.Optional[str]:
        return self._publication

    def setPublication(self, publication: typing.Optional[str]) -> None:
        self._publication = publication

    def author(self) -> typing.Optional[str]:
        return self._author

    def setAuthor(self, author: typing.Optional[str]) -> None:
        self._author = author

    def publisher(self) -> typing.Optional[str]:
        return self._publisher

    def setPublisher(self, publisher: typing.Optional[str]) -> None:
        self._publisher = publisher

    def reference(self) -> typing.Optional[str]:
        return self._reference

    def setReference(self, reference: typing.Optional[str]) -> None:
        self._reference = reference

class DbSector(DbObject):
    def __init__(
            self,
            isCustom: bool,
            milieu: str,
            sectorX: int,
            sectorY: int,
            primaryName: str,
            primaryLanguage: typing.Optional[str] = None,
            alternateNames: typing.Optional[typing.Collection[typing.Tuple[str, typing.Optional[str]]]] = None, # (Name, Language)
            abbreviation: typing.Optional[str] = None,
            sectorLabel: typing.Optional[str] = None,
            subsectorNames: typing.Optional[typing.Collection[typing.Tuple[int, str]]] = None, # Maps subsector index (0-15) to the name of that sector
            selected: bool = False,
            tags: typing.Optional[str] = None,
            styleSheet: typing.Optional[str] = None,
            credits: typing.Optional[str] = None,
            publication: typing.Optional[str] = None,
            author: typing.Optional[str] = None,
            publisher: typing.Optional[str] = None,
            reference: typing.Optional[str] = None,
            products: typing.Optional[typing.Collection[DbProduct]] = None,
            allegiances: typing.Optional[typing.Collection[DbAllegiance]] = None,
            sophonts: typing.Optional[typing.Collection[DbSophont]] = None,
            systems: typing.Optional[typing.Collection[DbSystem]] = None,
            routes: typing.Optional[typing.Collection[DbRoute]] = None,
            borders: typing.Optional[typing.Collection[DbBorder]] = None,
            regions: typing.Optional[typing.Collection[DbRegion]] = None,
            labels: typing.Optional[typing.Collection[DbLabel]] = None,
            notes: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            universeId: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

        self.setUniverseId(universeId)
        self.setIsCustom(isCustom)
        self.setMilieu(milieu)
        self.setSectorX(sectorX)
        self.setSectorY(sectorY)
        self.setPrimaryName(primaryName)
        self.setPrimaryLanguage(primaryLanguage)
        self.setAlternateNames(alternateNames)
        self.setAbbreviation(abbreviation)
        self.setSectorLabel(sectorLabel)
        self.setSubsectorNames(subsectorNames)
        self.setSelected(selected)
        self.setTags(tags)
        self.setStyleSheet(styleSheet)
        self.setCredits(credits)
        self.setPublication(publication)
        self.setAuthor(author)
        self.setPublisher(publisher)
        self.setReference(reference)
        self.setProducts(products)
        self.setAllegiances(allegiances)
        self.setSophonts(sophonts)
        self.setSystems(systems)
        self.setRoutes(routes)
        self.setBorders(borders)
        self.setLabels(labels)
        self.setRegions(regions)
        self.setNotes(notes)

    def universeId(self) -> typing.Optional[str]:
        return self._universeId

    def setUniverseId(self, universeId: str) -> None:
        self._universeId = universeId

    def isCustom(self) -> bool:
        return self._isCustom

    def setIsCustom(self, isCustom: bool) -> None:
        self._isCustom = isCustom

    def milieu(self) -> str:
        return self._milieu

    def setMilieu(self, milieu: str) -> None:
        self._milieu = milieu

    def sectorX(self) -> int:
        return self._sectorX

    def setSectorX(self, sectorX: int) -> None:
        self._sectorX = sectorX

    def sectorY(self) -> int:
        return self._sectorY

    def setSectorY(self, sectorY: int) -> None:
        self._sectorY = sectorY

    def primaryName(self) -> str:
        return self._primaryName

    def setPrimaryName(self, primaryName: str) -> None:
        self._primaryName = primaryName

    def primaryLanguage(self) -> typing.Optional[str]:
        return self._primaryLanguage

    def setPrimaryLanguage(self, primaryLanguage: typing.Optional[str]) -> None:
        self._primaryLanguage = primaryLanguage

    # Maps name to optional language
    def alternateNames(self) -> typing.Optional[typing.Collection[typing.Tuple[str, typing.Optional[str]]]]:
        return self._alternateNames

    def setAlternateNames(self, alternateNames: typing.Optional[typing.Collection[typing.Tuple[str, typing.Optional[str]]]]) -> None:
        self._alternateNames = list(alternateNames) if alternateNames else None

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

    def setAbbreviation(self, abbreviation: typing.Optional[str]) -> None:
        self._abbreviation = abbreviation

    def sectorLabel(self) -> typing.Optional[str]:
        return self._sectorLabel

    def setSectorLabel(self, sectorLabel: typing.Optional[str]) -> None:
        self._sectorLabel = sectorLabel

    # Maps subsector int index (0-15) to the name for that subsector
    def subsectorNames(self) -> typing.Optional[typing.Collection[typing.Tuple[int, str]]]:
        return self._subsectorNames

    def setSubsectorNames(self, subsectorNames: typing.Optional[typing.Collection[typing.Tuple[int, str]]]) -> None:
        self._subsectorNames = list(subsectorNames) if subsectorNames else None

    def selected(self) -> bool:
        return self._selected

    def setSelected(self, selected: bool) -> None:
        self._selected = selected

    def tags(self) -> typing.Optional[str]:
        return self._tags

    def setTags(self, tags: typing.Optional[str]) -> None:
        self._tags = tags

    def styleSheet(self) -> typing.Optional[str]:
        return self._styleSheet

    def setStyleSheet(self, styleSheet: typing.Optional[str]) -> None:
        self._styleSheet = styleSheet

    def credits(self) -> typing.Optional[str]:
        return self._credits

    def setCredits(self, credits: typing.Optional[str]) -> None:
        self._credits = credits

    def publication(self) -> typing.Optional[str]:
        return self._publication

    def setPublication(self, publication: typing.Optional[str]) -> None:
        self._publication = publication

    def author(self) -> typing.Optional[str]:
        return self._author

    def setAuthor(self, author: typing.Optional[str]) -> None:
        self._author = author

    def publisher(self) -> typing.Optional[str]:
        return self._publisher

    def setPublisher(self, publisher: typing.Optional[str]) -> None:
        self._publisher = publisher

    def reference(self) -> typing.Optional[str]:
        return self._reference

    def setReference(self, reference: typing.Optional[str]) -> None:
        self._reference = reference

    def products(self) -> typing.Optional[typing.Collection[DbProduct]]:
        return self._products

    def setProducts(self, products: typing.Optional[typing.Collection[DbProduct]]) -> None:
        self._products = list(products) if products else None

    def allegiances(self) -> typing.Optional[typing.Collection[DbAllegiance]]:
        return self._allegiances

    def setAllegiances(self, allegiances: typing.Optional[typing.Collection[DbAllegiance]]) -> None:
        self._allegiances = list(allegiances) if allegiances else None
        if self._allegiances:
            for allegiance in self._allegiances:
                allegiance.setSectorId(self._id)

    def sophonts(self) -> typing.Optional[typing.Collection[DbSophont]]:
        return self._sophonts

    def setSophonts(self, sophonts: typing.Optional[typing.Collection[DbSophont]]) -> None:
        self._sophonts = list(sophonts) if sophonts else None
        if self._sophonts:
            for sophont in self._sophonts:
                sophont.setSectorId(self._id)

    def systems(self) -> typing.Optional[typing.Collection[DbSystem]]:
        return self._systems

    def setSystems(self, systems: typing.Optional[typing.Collection[DbSystem]]) -> None:
        self._systems = list(systems) if systems else None
        if self._systems:
            for system in self._systems:
                system.setSectorId(self._id)

    def addSystem(self, system: DbSystem) -> None:
        if self._systems is None:
            self._systems = []
        self._systems.append(system)
        system.setSectorId(self._id)

    def removeSystem(self, systemId: str) -> None:
        if self._systems is None:
            return
        for i in range(self._systems):
            system = self._systems[i]
            if system.id() == systemId:
                del self._systems[i]
                return

    def routes(self) -> typing.Optional[typing.Collection[DbRoute]]:
        return self._routes

    def setRoutes(self, routes: typing.Optional[typing.Collection[DbRoute]]) -> None:
        self._routes = list(routes) if routes else None
        if self._routes:
            for route in self._routes:
                route.setSectorId(self._id)

    def addRoute(self, route: DbRoute) -> None:
        if self._routes is None:
            self._routes = []
        self._routes.append(route)
        route.setSectorId(self._id)

    def removeRoute(self, routeId: str) -> None:
        if self._routes is None:
            return
        for i in range(self._routes):
            route = self._routes[i]
            if route.id() == routeId:
                del self._routes[i]
                return

    def borders(self) -> typing.Optional[typing.Collection[DbBorder]]:
        return self._borders

    def setBorders(self, borders: typing.Optional[typing.Collection[DbBorder]]) -> None:
        self._borders = list(borders) if borders else None
        if self._borders:
            for border in self._borders:
                border.setSectorId(self._id)

    def addBorder(self, border: DbBorder) -> None:
        if self._borders is None:
            self._borders = []
        self._borders.append(border)
        border.setSectorId(self._id)

    def removeBorder(self, borderId: str) -> None:
        if self._borders is None:
            return
        for i in range(self._borders):
            border = self._borders[i]
            if border.id() == borderId:
                del self._borders[i]
                return

    def regions(self) -> typing.Optional[typing.Collection[DbRegion]]:
        return self._regions

    def setRegions(self, regions: typing.Optional[typing.Collection[DbRegion]]) -> None:
        self._regions = list(regions) if regions else None
        if self._regions:
            for region in self._regions:
                region.setSectorId(self._id)

    def addRegion(self, region: DbRegion) -> None:
        if self._regions is None:
            self._regions = []
        self._regions.append(region)
        region.setSectorId(self._id)

    def removeRegion(self, regionId: str) -> None:
        if self._regions is None:
            return
        for i in range(self._regions):
            region = self._regions[i]
            if region.id() == regionId:
                del self._regions[i]
                return

    def labels(self) -> typing.Optional[typing.Collection[DbLabel]]:
        return self._labels

    def setLabels(self, labels: typing.Optional[typing.Collection[DbLabel]]) -> None:
        self._labels = list(labels) if labels else None
        if self._labels:
            for label in self._labels:
                label.setSectorId(self._id)

    def addLabel(self, label: DbLabel) -> None:
        if self._labels is None:
            self._labels = []
        self._labels.append(label)
        label.setSectorId(self._id)

    def removeLabel(self, labelId: str) -> None:
        if self._labels is None:
            return
        for i in range(self._labels):
            label = self._labels[i]
            if label.id() == labelId:
                del self._labels[i]
                return

    def notes(self) -> typing.Optional[str]:
        return self._notes

    def setNotes(self, notes: typing.Optional[str]) -> None:
        self._notes = notes

class DbUniverse(DbObject):
    def __init__(
            self,
            name: str,
            description: typing.Optional[str] = None,
            notes: typing.Optional[str] = None,
            sectors: typing.Optional[typing.Collection[DbSector]] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            ) -> None:
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
