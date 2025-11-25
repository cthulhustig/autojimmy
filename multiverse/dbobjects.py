import typing
import uuid

# TODO: These classes should probably do some level of validation on that
# data they are passed

class DbSystem(object):
    def __init__(
            self,
            hexX: int,
            hexY: int,
            name: str, # TODO: Do worlds in sector files always have a name????
            uwp: str, # TODO: Do worlds in sector files always have a UWP
            remarks: typing.Optional[str] = None,
            importance: typing.Optional[str] = None,
            economics: typing.Optional[str] = None,
            culture: typing.Optional[str] = None,
            nobility: typing.Optional[str] = None,
            bases: typing.Optional[str] = None,
            zone: typing.Optional[str] = None,
            pbg: typing.Optional[str] = None,
            # System worlds can be None if the number is not not known (e.g. if uwp is ???????-?)
            # It can also be none due to it just not being specified in sector data
            systemWorlds: typing.Optional[int] = None,
            allegiance: typing.Optional[str] = None,
            stellar: typing.Optional[str] = None,
            notes: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        self._id = id if id is not None else str(uuid.uuid4())

        self.setSectorId(sectorId)
        self.setHexX(hexX)
        self.setHexY(hexY)
        self.setName(name)
        self.setUWP(uwp)
        self.setRemarks(remarks)
        self.setImportance(importance)
        self.setEconomics(economics)
        self.setCulture(culture)
        self.setNobility(nobility)
        self.setBases(bases)
        self.setZone(zone)
        self.setPBG(pbg)
        self.setSystemWorlds(systemWorlds)
        self.setAllegiance(allegiance)
        self.setStellar(stellar)
        self.setNotes(notes)

    def id(self) -> str:
        return self._id

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

    def remarks(self) -> typing.Optional[str]:
        return self._remarks

    def setRemarks(self, remarks: typing.Optional[str]) -> None:
        self._remarks = remarks

    def importance(self) -> typing.Optional[str]:
        return self._importance

    def setImportance(self, importance: typing.Optional[str]) -> None:
        self._importance = importance

    def economics(self) -> typing.Optional[str]:
        return self._economics

    def setEconomics(self, economics: typing.Optional[str]) -> None:
        self._economics = economics

    def culture(self) -> typing.Optional[str]:
        return self._culture

    def setCulture(self, culture: typing.Optional[str]) -> None:
        self._culture = culture

    def nobility(self) -> typing.Optional[str]:
        return self._nobility

    def setNobility(self, nobility: typing.Optional[str]) -> None:
        self._nobility = nobility

    def bases(self) -> typing.Optional[str]:
        return self._bases

    def setBases(self, bases: typing.Optional[str]) -> None:
        self._bases = bases

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

    def allegiance(self) -> typing.Optional[str]:
        return self._allegiance

    def setAllegiance(self, allegiance: typing.Optional[str]) -> None:
        self._allegiance = allegiance

    def stellar(self) -> typing.Optional[str]:
        return self._stellar

    def setStellar(self, stellar: typing.Optional[str]) -> None:
        self._stellar = stellar

    def notes(self) -> typing.Optional[str]:
        return self._notes

    def setNotes(self, notes: typing.Optional[str]) -> None:
        self._notes = notes

class DbRoute(object):
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
            allegiance: typing.Optional[str] = None,
            type: typing.Optional[str] = None,
            style: typing.Optional[str] = None,
            colour: typing.Optional[str] = None,
            width: typing.Optional[float] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        self._id = id if id is not None else str(uuid.uuid4())

        self.setSectorId(sectorId)
        self.setStartHexX(startHexX)
        self.setStartHexY(startHexY)
        self.setEndHexX(endHexX)
        self.setEndHexY(endHexY)
        self.setStartOffsetX(startOffsetX)
        self.setStartOffsetY(startOffsetY)
        self.setEndOffsetX(endOffsetX)
        self.setEndOffsetY(endOffsetY)
        self.setAllegiance(allegiance)
        self.setType(type)
        self.setStyle(style)
        self.setColour(colour)
        self.setWidth(width)

    # TODO: As long as I only allow saving at the sector level, I don't think
    # having the id as part of the structure makes sense as we always know
    # what sector it's part of. The same goes for the other objects that also
    # have the sector id
    def id(self) -> str:
        return self._id

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

    def allegiance(self) -> typing.Optional[str]:
        return self._allegiance

    def setAllegiance(self, allegiance: typing.Optional[str]) -> None:
        self._allegiance = allegiance

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

class DbBorder(object):
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
            allegiance: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        self._id = id if id is not None else str(uuid.uuid4())

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

    def id(self) -> str:
        return self._id

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

    def allegiance(self) -> typing.Optional[str]:
        return self._allegiance

    def setAllegiance(self, allegiance: typing.Optional[str]) -> None:
        self._allegiance = allegiance

class DbRegion(object):
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
        self._id = id if id is not None else str(uuid.uuid4())

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

    def id(self) -> str:
        return self._id

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

class DbLabel(object):
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
        self._id = id if id is not None else str(uuid.uuid4())

        self.setSectorId(sectorId)
        self.setText(text)
        self.setHexX(hexX)
        self.setHexY(hexY)
        self.setWrap(wrap)
        self.setColour(colour)
        self.setSize(size)
        self.setOffsetX(offsetX)
        self.setOffsetY(offsetY)

    def id(self) -> str:
        return self._id

    # NOTE: Changing the id of an object isn't something that should
    # ever happen. If for whatever reason I do enable it, I'll need
    # to update the sector id of all child objects
    #def setId(self, id: str) -> None:
    #    self._id = id

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

class DbAllegiance(object):
    def __init__(
            self,
            code: str,
            name: str,
            legacy: typing.Optional[str] = None,
            base: typing.Optional[str] = None
            ) -> None:
        self.setCode(code)
        self.setName(name)
        self.setLegacy(legacy)
        self.setBase(base)

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

class DbSector(object):
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
            systems: typing.Optional[typing.Collection[DbSystem]] = None,
            routes: typing.Optional[typing.Collection[DbRoute]] = None,
            borders: typing.Optional[typing.Collection[DbBorder]] = None,
            regions: typing.Optional[typing.Collection[DbRegion]] = None,
            labels: typing.Optional[typing.Collection[DbLabel]] = None,
            notes: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            universeId: typing.Optional[str] = None
            ) -> None:
        self._id = id if id is not None else str(uuid.uuid4())

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
        self.setSystems(systems)
        self.setRoutes(routes)
        self.setBorders(borders)
        self.setLabels(labels)
        self.setRegions(regions)
        self.setNotes(notes)

    def id(self) -> str:
        return self._id

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

class DbUniverse(object):
    def __init__(
            self,
            name: str,
            description: typing.Optional[str] = None,
            notes: typing.Optional[str] = None,
            sectors: typing.Optional[typing.Collection[DbSector]] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            ) -> None:
        self._id = id if id is not None else str(uuid.uuid4())

        self._sectorByMilieuPosition: typing.Dict[typing.Tuple[str, int, int], DbSector] = {}

        self.setName(name)
        self.setDescription(description)
        self.setNotes(notes)
        self.setSectors(sectors)

    def id(self) -> str:
        return self._id

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
