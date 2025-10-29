import database
import logging
import sqlite3
import typing
import uuid

# TODO: Need something that updates the stock sectors from disk
# - Will need to leave custom sectors so can't just delete the universe
# - Should VACUUM the DB after an import to free space
# TODO: Need something that does one time import of custom sectors from
# filesystem to database
# TODO: All the constructors and setters on DB objects should validate the
# input

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
            systemWorlds: int = 1,
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

    def systemWorlds(self) -> int:
        return self._systemWorlds

    def setSystemWorlds(self, systemWorlds: int) -> None:
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
        self.setAllegiance(allegiance)
        self.setType(type)
        self.setStyle(style)
        self.setColour(colour)
        self.setWidth(width)

    def id(self) -> str:
        return self._id

    # TODO: As long as I only allow saving at the sector level, I don't think
    # having the id as part of the structure makes sense as we always know
    # what sector it's part of. The same goes for the other objects that also
    # have the sector id
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
            showLabel: bool,
            wrapLabel: bool,
            labelHexX: typing.Optional[int] = None,
            labelHexY: typing.Optional[int] = None,
            labelOffsetX: typing.Optional[float] = None,
            labelOffsetY: typing.Optional[float] = None,
            label: typing.Optional[str] = None,
            colour: typing.Optional[str] = None,
            style: typing.Optional[str] = None,
            allegiance: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        self._id = id if id is not None else str(uuid.uuid4())

        self.setSectorId(sectorId)
        self.setHexes(hexes)
        self.setShowLabel(showLabel)
        self.setWrapLabel(wrapLabel)
        self.setLabelHexX(labelHexX)
        self.setLabelHexY(labelHexY)
        self.setLabelOffsetX(labelOffsetX)
        self.setLabelOffsetY(labelOffsetY)
        self.setLabel(label)
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

    # TODO: I can maybe get rid of this here and in DbRegion if I uses the
    # presence of label text to indicate if the label should be shown. I'd
    # need to check the cartographer to see how it's actually used.
    def showLabel(self) -> bool:
        return self._showLabel

    def setShowLabel(self, showLabel: bool) -> None:
        self._showLabel = showLabel

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

    def label(self) -> typing.Optional[str]:
        return self._label

    def setLabel(self, label: typing.Optional[str]) -> None:
        self._label = label

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
            showLabel: bool,
            wrapLabel: bool,
            labelHexX: typing.Optional[int] = None,
            labelHexY: typing.Optional[int] = None,
            labelOffsetX: typing.Optional[float] = None,
            labelOffsetY: typing.Optional[float] = None,
            label: typing.Optional[str] = None,
            colour: typing.Optional[str] = None,
            id: typing.Optional[str] = None, # None means allocate an id
            sectorId: typing.Optional[str] = None
            ) -> None:
        self._id = id if id is not None else str(uuid.uuid4())

        self.setSectorId(sectorId)
        self.setHexes(hexes)
        self.setShowLabel(showLabel)
        self.setWrapLabel(wrapLabel)
        self.setLabelHexX(labelHexX)
        self.setLabelHexY(labelHexY)
        self.setLabelOffsetX(labelOffsetX)
        self.setLabelOffsetY(labelOffsetY)
        self.setLabel(label)
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

    def label(self) -> typing.Optional[str]:
        return self._label

    def setLabel(self, label: typing.Optional[str]) -> None:
        self._label = label

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
            base: typing.Optional[str] = None
            ) -> None:
        self.setCode(code)
        self.setName(name)
        self.setBase(base)

    def code(self) -> str:
        return self._code

    def setCode(self, code: str) -> None:
        self._code = code

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> None:
        self._name = name

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

    def setSectors(self, sectors: typing.Optional[typing.Collection[DbSector]]) -> None:
        self._sectors = list(sectors) if sectors else None
        if self._sectors:
            for sector in self._sectors:
                sector.setUniverseId(self._id)

    def addSector(self, sector: DbSector) -> None:
        if self._sectors is None:
            self._sectors = []
        self._sectors.append(sector)
        sector.setUniverseId(self._id)

    def removeSector(self, sectorId: str) -> None:
        if self._sectors is None:
            return
        for i in range(self._sectors):
            sector = self._sectors[i]
            if sector.id() == sectorId:
                del self._sectors[i]
                return

# TODO: When updating snapshot I'll need to do something to make sure notes
# are preserved on systems/sectors. I could split notes in a separate table
# but it's probably easiest to just read the existing notes and set the
# notes on the new object before writing it to the db.
class MapDb(object):
    class Transaction(object):
        def __init__(
                self,
                connection: sqlite3.Connection
                ) -> None:
            self._connection = connection
            self._hasBegun = False

        def connection(self) -> sqlite3.Connection:
            return self._connection

        def begin(self) -> 'MapDb.Transaction':
            if self._hasBegun:
                raise RuntimeError('Invalid state to begin transaction')

            cursor = self._connection.cursor()
            try:
                cursor.execute('BEGIN;')
                self._hasBegun = True
            except:
                self._teardown()
                raise

            return self

        def end(self) -> None:
            if not self._hasBegun:
                raise RuntimeError('Invalid state to end transaction')

            cursor = self._connection.cursor()
            try:
                cursor.execute('END;')
            finally:
                self._teardown()

        def rollback(self) -> None:
            if not self._hasBegun:
                raise RuntimeError('Invalid state to roll back transaction')

            cursor = self._connection.cursor()
            try:
                cursor.execute('ROLLBACK;')
            finally:
                self._teardown()

        def __enter__(self) -> 'MapDb.Transaction':
            return self.begin()

        def __exit__(self, exc_type, exc_val, exc_tb) -> None:
            if exc_type is None:
                self.end()
            else:
                self.rollback()

        def __del__(self) -> None:
            if self._hasBegun:
                # A transaction is in progress so roll it back
                self.rollback()

        def _teardown(self) -> None:
            if self._connection:
                self._connection.close()
            self._connection = None
            self._hasBegun = False

    _PragmaScript = """
        PRAGMA foreign_keys = ON;
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;
        """

    _TableSchemaTableName = 'table_schemas'

    _UniversesTableName = 'universes'
    _UniversesTableSchema = 1

    _SectorsTableName = 'sectors'
    _SectorsTableSchema = 1

    _AlternateNamesTableName = 'alternate_names'
    _AlternateNamesTableSchema = 1

    _SubsectorNamesTableName = 'subsector_names'
    _SubsectorNamesTableSchema = 1

    _AllegiancesTableName = 'allegiances'
    _AllegiancesTableSchema = 1

    _ProductsTableName = 'products'
    _ProductsTableSchema = 1

    _RoutesTableName = 'routes'
    _RoutesTableSchema = 1

    _BordersTableName = 'borders'
    _BordersTableSchema = 1

    _BorderHexesTableName = 'border_hexes'
    _BorderHexesTableSchema = 1

    _RegionsTableName = 'regions'
    _RegionsTableSchema = 1

    _RegionHexesTableName = 'region_hexes'
    _RegionHexesTableSchema = 1

    _LabelsTableName = 'labels'
    _LabelsTableSchema = 1

    _SystemsTableName = 'systems'
    _SystemsTableSchema = 1

    def __init__(self, path: str):
        self._path = path
        self._initTables()

    def createTransaction(self) -> Transaction:
        connection = self._createConnection()
        return MapDb.Transaction(connection=connection)

    def writeUniverse(
            self,
            universe: DbUniverse,
            transaction: typing.Optional['MapDb.Transaction'] = None
            ) -> None:
        logging.debug(f'MapDb writing universe {universe.id()}')
        if transaction != None:
            connection = transaction.connection()
            self._internalDeleteUniverse(
                universeId=universe.id(),
                cursor=connection.cursor())
            self._internalInsertUniverse(
                universe=universe,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._internalDeleteUniverse(
                    universeId=universe.id(),
                    cursor=connection.cursor())
                self._internalInsertUniverse(
                    universe=universe,
                    cursor=connection.cursor())

    def readUniverse(
            self,
            universeId: str,
            transaction: typing.Optional['MapDb.Transaction'] = None
            ) -> typing.Optional[DbUniverse]:
        logging.debug(f'MapDb reading universe {universeId}')
        if transaction != None:
            connection = transaction.connection()
            return self._internalReadUniverse(
                universeId=universeId,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._internalReadUniverse(
                    universeId=universeId,
                    cursor=connection.cursor())

    def deleteUniverse(
            self,
            universeId: str,
            transaction: typing.Optional['MapDb.Transaction'] = None
            ) -> None:
        logging.debug(f'MapDb deleting universe {universeId}')
        if transaction != None:
            connection = transaction.connection()
            self._internalDeleteUniverse(
                universeId=universeId,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._internalDeleteUniverse(
                    universeId=universeId,
                    cursor=connection.cursor())

    def writeSector(
            self,
            sector: DbSector,
            transaction: typing.Optional['MapDb.Transaction'] = None
            ) -> None:
        logging.debug(f'MapDb writing sector {sector.id()}')
        if transaction != None:
            connection = transaction.connection()
            self._internalDeleteSector(
                sectorId=sector.id(),
                cursor=connection.cursor())
            self._internalInsertSector(
                sector=sector,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._internalDeleteSector(
                    sectorId=sector.id(),
                    cursor=connection.cursor())
                self._internalInsertSector(
                    sector=sector,
                    cursor=connection.cursor())

    def readSector(
            self,
            sectorId: str,
            transaction: typing.Optional['MapDb.Transaction'] = None
            ) -> typing.Optional[DbSector]:
        logging.debug(f'MapDb reading sector {sectorId}')
        if transaction != None:
            connection = transaction.connection()
            self._internalReadSector(
                sectorId=sectorId,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._internalReadSector(
                    sectorId=sectorId,
                    cursor=connection.cursor())

    def deleteSector(
            self,
            sectorId: str,
            transaction: typing.Optional['MapDb.Transaction'] = None
            ) -> None:
        logging.debug(f'MapDb deleting sector {sectorId}')
        if transaction != None:
            connection = transaction.connection()
            self._internalDeleteSector(
                sectorId=sectorId,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._internalDeleteSector(
                    sectorId=sectorId,
                    cursor=connection.cursor())

    def listUniverseNames(
            self,
            transaction: typing.Optional['MapDb.Transaction'] = None
            ) -> typing.Mapping[str, str]:
        logging.debug(f'MapDb listing universe names')
        if transaction != None:
            connection = transaction.connection()
            return self._internalListUniverseNames(
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._internalListUniverseNames(
                    cursor=connection.cursor())

    def listSectorNames(
            self,
            universeId: typing.Optional[str] = None,
            transaction: typing.Optional['MapDb.Transaction'] = None
            ) -> typing.Mapping[str, str]:
        logging.debug(
            f'MapDb listing sector names' + ('' if universeId is None else f' for universe {universeId}'))
        if transaction != None:
            connection = transaction.connection()
            return self._internalListSectorNames(
                universeId=universeId,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._internalListSectorNames(
                    universeId=universeId,
                    cursor=connection.cursor())

    def _createConnection(self) -> sqlite3.Connection:
        # TODO: Connection pool like ObjectDb????

        connection = sqlite3.connect(self._path)
        logging.debug(f'ObjectDbManager created new connection {connection} to \'{self._path}\'')
        connection.executescript(MapDb._PragmaScript)
        # Uncomment this to have sqlite print the SQL that it executes
        #connection.set_trace_callback(print)
        return connection

    def _initTables(self) -> None:
        connection = None
        cursor = None
        try:
            connection = self._createConnection()
            cursor = connection.cursor()
            cursor.execute('BEGIN;')

            if not database.checkIfTableExists(
                    tableName=MapDb._TableSchemaTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {table} (
                        name TEXT PRIMARY KEY NOT NULL,
                        version INTEGER NOT NULL
                    );
                    """.format(table=MapDb._TableSchemaTableName)
                logging.info(f'MapDb creating \'{MapDb._TableSchemaTableName}\' table')
                cursor.execute(sql)

            # Create universe table
            if not database.checkIfTableExists(
                    tableName=MapDb._UniversesTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {table} (
                        id TEXT PRIMARY KEY NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        notes TEXT
                    );
                    """.format(table=MapDb._UniversesTableName)
                logging.info(f'MapDb creating \'{MapDb._UniversesTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MapDb._UniversesTableName,
                    version=MapDb._UniversesTableSchema,
                    cursor=cursor)

                # Create schema table indexes for id column. The id index is
                # needed as, even though it's the primary key, it's of type
                # TEXT so doesn't automatically get indexes
                self._createColumnIndex(
                    table=MapDb._UniversesTableName,
                    column='id',
                    unique=True,
                    cursor=cursor)

            # Create sectors table
            if not database.checkIfTableExists(
                    tableName=MapDb._SectorsTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {sectorsTable} (
                        id TEXT PRIMARY KEY NOT NULL,
                        universe_id TEXT NOT NULL,
                        is_custom INTEGER NOT NULL,
                        milieu TEXT NOT NULL,
                        sector_x INTEGER NOT NULL,
                        sector_y INTEGER NOT NULL,
                        primary_name TEXT NOT NULL,
                        primary_language TEXT,
                        abbreviation TEXT,
                        sector_label TEXT,
                        selected INTEGER NOT NULL,
                        tags TEXT,
                        style_sheet TEXT,
                        credits TEXT,
                        publication TEXT,
                        author TEXT,
                        publisher TEXT,
                        reference TEXT,
                        notes TEXT,
                        FOREIGN KEY(universe_id) REFERENCES {universesTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        sectorsTable=MapDb._SectorsTableName,
                        universesTable=MapDb._UniversesTableName)
                logging.info(f'MapDb creating \'{MapDb._SectorsTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MapDb._SectorsTableName,
                    version=MapDb._SectorsTableSchema,
                    cursor=cursor)

                # Create indexes for id column. The id index is needed as, even
                # though it's the primary key, it's of type TEXT so doesn't
                # automatically get indexes
                self._createColumnIndex(
                    table=MapDb._SectorsTableName,
                    column='id',
                    unique=True,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MapDb._SectorsTableName,
                    column='universe_id',
                    unique=False,
                    cursor=cursor)

            # Create sector alternate names table
            if not database.checkIfTableExists(
                    tableName=MapDb._AlternateNamesTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {namesTable} (
                        sector_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        language TEXT,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        namesTable=MapDb._AlternateNamesTableName,
                        sectorsTable=MapDb._SectorsTableName)
                logging.info(f'MapDb creating \'{MapDb._AlternateNamesTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MapDb._AlternateNamesTableName,
                    version=MapDb._AlternateNamesTableSchema,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MapDb._AlternateNamesTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create subsector names table
            if not database.checkIfTableExists(
                    tableName=MapDb._SubsectorNamesTableName,
                    cursor=cursor):
                # TODO: Can I enforce a valid range for the code (0-15)
                sql = """
                    CREATE TABLE IF NOT EXISTS {namesTable} (
                        sector_id TEXT NOT NULL,
                        code INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        namesTable=MapDb._SubsectorNamesTableName,
                        sectorsTable=MapDb._SectorsTableName)
                logging.info(f'MapDb creating \'{MapDb._SubsectorNamesTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MapDb._SubsectorNamesTableName,
                    version=MapDb._SubsectorNamesTableSchema,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MapDb._SubsectorNamesTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create allegiance names table
            if not database.checkIfTableExists(
                    tableName=MapDb._AllegiancesTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {allegiancesTable} (
                        sector_id TEXT NOT NULL,
                        code TEXT NOT NULL,
                        name TEXT NOT NULL,
                        base TEXT,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        allegiancesTable=MapDb._AllegiancesTableName,
                        sectorsTable=MapDb._SectorsTableName)
                logging.info(f'MapDb creating \'{MapDb._AllegiancesTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MapDb._AllegiancesTableName,
                    version=MapDb._AllegiancesTableSchema,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MapDb._AllegiancesTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create products table
            if not database.checkIfTableExists(
                    tableName=MapDb._ProductsTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {productsTable} (
                        sector_id TEXT NOT NULL,
                        publication TEXT,
                        author TEXT,
                        publisher TEXT,
                        reference TEXT,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        productsTable=MapDb._ProductsTableName,
                        sectorsTable=MapDb._SectorsTableName)
                logging.info(f'MapDb creating \'{MapDb._ProductsTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MapDb._ProductsTableName,
                    version=MapDb._ProductsTableSchema,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MapDb._ProductsTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create systems table
            if not database.checkIfTableExists(
                    tableName=MapDb._SystemsTableName,
                    cursor=cursor):

                # TODO: I'm not sure what to do about importance. I don't think I use
                # it anywhere. I think this might be the same as the importance value
                # I calculate in the cartographer
                sql = """
                    CREATE TABLE IF NOT EXISTS {systemsTable} (
                        id TEXT PRIMARY KEY NOT NULL,
                        sector_id TEXT NOT NULL,
                        hex_x INTEGER NOT NULL,
                        hex_y INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        uwp TEXT NOT NULL,
                        remarks TEXT,
                        importance TEXT,
                        economics TEXT,
                        culture TEXT,
                        nobility TEXT,
                        bases TEXT,
                        zone TEXT,
                        pbg TEXT,
                        system_worlds INTEGER NOT NULL,
                        allegiance TEXT,
                        stellar TEXT,
                        notes TEXT,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        systemsTable=MapDb._SystemsTableName,
                        sectorsTable=MapDb._SectorsTableName)
                logging.info(f'MapDb creating \'{MapDb._SystemsTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MapDb._SystemsTableName,
                    version=MapDb._SystemsTableSchema,
                    cursor=cursor)

                # Create indexes for id column. The id index is needed as, even
                # though it's the primary key, it's of type TEXT so doesn't
                # automatically get indexes
                self._createColumnIndex(
                    table=MapDb._SystemsTableName,
                    column='id',
                    unique=True,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MapDb._SystemsTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create routes table
            if not database.checkIfTableExists(
                    tableName=MapDb._RoutesTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {routesTable} (
                        id TEXT PRIMARY KEY NOT NULL,
                        sector_id TEXT NOT NULL,
                        start_hex_x INTEGER NOT NULL,
                        start_hex_y INTEGER NOT NULL,
                        end_hex_x INTEGER NOT NULL,
                        end_hex_y INTEGER NOT NULL,
                        allegiance TEXT,
                        type TEXT,
                        style TEXT,
                        colour TEXT,
                        width REAL,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        routesTable=MapDb._RoutesTableName,
                        sectorsTable=MapDb._SectorsTableName)
                logging.info(f'MapDb creating \'{MapDb._RoutesTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MapDb._RoutesTableName,
                    version=MapDb._RoutesTableSchema,
                    cursor=cursor)

                # Create indexes for id column. The id index is needed as, even
                # though it's the primary key, it's of type TEXT so doesn't
                # automatically get indexes
                self._createColumnIndex(
                    table=MapDb._RoutesTableName,
                    column='id',
                    unique=True,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MapDb._RoutesTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create borders table
            if not database.checkIfTableExists(
                    tableName=MapDb._BordersTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {bordersTable} (
                        id TEXT PRIMARY KEY NOT NULL,
                        sector_id TEXT NOT NULL,
                        show_label INTEGER NOT NULL,
                        wrap_label INTEGER NOT NULL,
                        label_hex_x INTEGER,
                        label_hex_y INTEGER,
                        label_offset_x REAL,
                        label_offset_y REAL,
                        label TEXT,
                        colour TEXT,
                        style TEXT,
                        allegiance TEXT,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        bordersTable=MapDb._BordersTableName,
                        sectorsTable=MapDb._SectorsTableName)
                logging.info(f'MapDb creating \'{MapDb._BordersTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MapDb._BordersTableName,
                    version=MapDb._BordersTableSchema,
                    cursor=cursor)

                # Create indexes for id column. The id index is needed as, even
                # though it's the primary key, it's of type TEXT so doesn't
                # automatically get indexes
                self._createColumnIndex(
                    table=MapDb._BordersTableName,
                    column='id',
                    unique=True,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MapDb._BordersTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create border hexes table
            if not database.checkIfTableExists(
                    tableName=MapDb._BorderHexesTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {hexesTable} (
                        border_id TEXT NOT NULL,
                        hex_x INTEGER NOT NULL,
                        hex_y INTEGER NOT NULL,
                        FOREIGN KEY(border_id) REFERENCES {bordersTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        hexesTable=MapDb._BorderHexesTableName,
                        bordersTable=MapDb._BordersTableName)
                logging.info(f'MapDb creating \'{MapDb._BorderHexesTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MapDb._BorderHexesTableName,
                    version=MapDb._BorderHexesTableSchema,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MapDb._BorderHexesTableName,
                    column='border_id',
                    unique=False,
                    cursor=cursor)

            # Create regions table
            # TODO: The only difference between regions and borders seems to be
            # that borders have a style but regions don't. It feels like there
            # must be a way to do this that doesn't involve having two tables
            # and object definitions
            if not database.checkIfTableExists(
                    tableName=MapDb._RegionsTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {regionsTable} (
                        id TEXT PRIMARY KEY NOT NULL,
                        sector_id TEXT NOT NULL,
                        show_label INTEGER NOT NULL,
                        wrap_label INTEGER NOT NULL,
                        label_hex_x INTEGER,
                        label_hex_y INTEGER,
                        label_offset_x REAL,
                        label_offset_y REAL,
                        label TEXT,
                        colour TEXT,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        regionsTable=MapDb._RegionsTableName,
                        sectorsTable=MapDb._SectorsTableName)
                logging.info(f'MapDb creating \'{MapDb._RegionsTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MapDb._RegionsTableName,
                    version=MapDb._RegionsTableSchema,
                    cursor=cursor)

                # Create indexes for id column. The id index is needed as, even
                # though it's the primary key, it's of type TEXT so doesn't
                # automatically get indexes
                self._createColumnIndex(
                    table=MapDb._RegionsTableName,
                    column='id',
                    unique=True,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MapDb._RegionsTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create region hexes table
            if not database.checkIfTableExists(
                    tableName=MapDb._RegionHexesTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {hexesTable} (
                        region_id TEXT NOT NULL,
                        hex_x INTEGER NOT NULL,
                        hex_y INTEGER NOT NULL,
                        FOREIGN KEY(region_id) REFERENCES {regionsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        hexesTable=MapDb._RegionHexesTableName,
                        regionsTable=MapDb._RegionsTableName)
                logging.info(f'MapDb creating \'{MapDb._RegionHexesTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MapDb._RegionHexesTableName,
                    version=MapDb._RegionHexesTableSchema,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MapDb._RegionHexesTableName,
                    column='region_id',
                    unique=False,
                    cursor=cursor)

            # Create labels table
            if not database.checkIfTableExists(
                    tableName=MapDb._LabelsTableName,
                    cursor=cursor):
                # TODO: Should offset be optional?
                sql = """
                    CREATE TABLE IF NOT EXISTS {labelsTable} (
                        id TEXT PRIMARY KEY NOT NULL,
                        sector_id TEXT NOT NULL,
                        text TEXT NOT NULL,
                        hex_x INTEGER NOT NULL,
                        hex_y INTEGER NOT NULL,
                        wrap INTEGER NOT NULL,
                        colour TEXT,
                        size TEXT,
                        offset_x REAL,
                        offset_y REAL,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        labelsTable=MapDb._LabelsTableName,
                        sectorsTable=MapDb._SectorsTableName)
                logging.info(f'MapDb creating \'{MapDb._LabelsTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MapDb._LabelsTableName,
                    version=MapDb._LabelsTableSchema,
                    cursor=cursor)

                # Create indexes for id column. The id index is needed as, even
                # though it's the primary key, it's of type TEXT so doesn't
                # automatically get indexes
                self._createColumnIndex(
                    table=MapDb._LabelsTableName,
                    column='id',
                    unique=True,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MapDb._LabelsTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            cursor.execute('END;')
        except:
            if cursor:
                try:
                    cursor.execute('ROLLBACK;')
                except:
                    pass
            if connection:
                connection.close()
            raise

    def _writeSchemaVersion(
            self,
            table: str,
            version: int,
            cursor: sqlite3.Cursor
            ) -> None:
        sql = """
            INSERT INTO {table} (name, version)
            VALUES (:name, :version)
            ON CONFLICT(name) DO UPDATE SET
                version = excluded.version;
            """.format(table=MapDb._TableSchemaTableName)
        logging.info(f'MapDb setting schema for \'{table}\' table to {version}')
        rowData = {
            'name': table,
            'version': version}
        cursor.execute(sql, rowData)

    def _createColumnIndex(
            self,
            table: str,
            column: str,
            unique: bool,
            cursor: sqlite3.Cursor
            ) -> None:
        logging.info(f'MapDb creating \'{table}\' \'{column}\' index')
        database.createColumnIndex(table=table, column=column, unique=unique, cursor=cursor)

    def _internalInsertUniverse(
            self,
            universe: DbUniverse,
            cursor: sqlite3.Cursor
            ) -> None:
        sql = """
            INSERT INTO {table} (id, name, description, notes)
            VALUES (:id, :name, :description, :notes);
            """.format(table=MapDb._UniversesTableName)
        rowData = {
            'id': universe.id(),
            'name': universe.name(),
            'description': universe.description(),
            'notes': universe.notes()}
        cursor.execute(sql, rowData)

        if universe.sectors():
            for sector in universe.sectors():
                self._internalInsertSector(
                    sector=sector,
                    cursor=cursor)

    def _internalReadUniverse(
            self,
            universeId: str,
            cursor: sqlite3.Cursor
            ) -> typing.Optional[DbUniverse]:
        sql = """
            SELECT name, description, notes
            FROM {table}
            WHERE id = :id;
            """.format(table=MapDb._UniversesTableName)
        cursor.execute(sql, {'id': universeId})
        row = cursor.fetchone()
        if not row:
            return None
        name = row[0]
        description = row[1]
        notes = row[2]

        # TODO: This could be made more efficient by loading all the sector
        # information in a single select then just loading the sector child
        # data with individual selects.
        sql = """
            SELECT id FROM {table} WHERE universe_id = :id;
            """.format(table=MapDb._SectorsTableName)
        cursor.execute(sql, {'id': universeId})
        sectors = []
        for row in cursor.fetchall():
            sectorId = row[0]
            sector = self._internalReadSector(
                sectorId=sectorId,
                cursor=cursor)
            if not sector:
                # TODO: Some kind of logging or error handling?
                continue
            sectors.append(sector)

        return DbUniverse(
            id=universeId,
            name=name,
            description=description,
            notes=notes,
            sectors=sectors)

    def _internalDeleteUniverse(
            self,
            universeId: str,
            cursor: sqlite3.Cursor
            ) -> typing.Optional[DbUniverse]:
        sql = """
            DELETE FROM {table}
            WHERE id = :id
            """.format(
            table=MapDb._UniversesTableName)
        cursor.execute(sql, {'id': universeId})

    def _internalInsertSector(
            self,
            sector: DbSector,
            cursor: sqlite3.Cursor
            ) -> None:
        sql = """
            INSERT INTO {table} (id, universe_id, is_custom, milieu,
                sector_x, sector_y, primary_name, primary_language,
                abbreviation, sector_label, selected, tags, style_sheet,
                credits, publication, author, publisher, reference, notes)
            VALUES (:id, :universe_id, :is_custom, :milieu,
                :sector_x, :sector_y, :primary_name, :primary_language,
                :abbreviation, :sector_label, :selected, :tags, :style_sheet,
                :credits, :publication, :author, :publisher, :reference, :notes);
            """.format(table=MapDb._SectorsTableName)
        rowData = {
            'id': sector.id(),
            'universe_id': sector.universeId(),
            'is_custom': 1 if sector.isCustom() else 0,
            'milieu': sector.milieu(),
            'sector_x': sector.sectorX(),
            'sector_y': sector.sectorY(),
            'primary_name': sector.primaryName(),
            'primary_language': sector.primaryLanguage(),
            'abbreviation': sector.abbreviation(),
            'sector_label': sector.sectorLabel(),
            'selected': 1 if sector.selected() else 0,
            'tags': sector.tags(),
            'style_sheet': sector.styleSheet(),
            'credits': sector.credits(),
            'publication': sector.publication(),
            'author': sector.author(),
            'publisher': sector.publisher(),
            'reference': sector.reference(),
            'notes': sector.notes()}
        cursor.execute(sql, rowData)

        if sector.alternateNames():
            sql = """
                INSERT INTO {table} (sector_id, name, language)
                VALUES (:sector_id, :name, :language);
                """.format(table=MapDb._AlternateNamesTableName)
            rowData = []
            for name, language in sector.alternateNames():
                rowData.append({
                    'sector_id': sector.id(),
                    'name': name,
                    'language': language})
            cursor.executemany(sql, rowData)

        if sector.subsectorNames():
            sql = """
                INSERT INTO {table} (sector_id, code, name)
                VALUES (:sector_id, :code, :name);
                """.format(table=MapDb._SubsectorNamesTableName)
            rowData = []
            for code, name in sector.subsectorNames():
                rowData.append({
                    'sector_id': sector.id(),
                    'code': code,
                    'name': name})
            cursor.executemany(sql, rowData)

        if sector.products():
            sql = """
                INSERT INTO {table} (sector_id, publication, author,
                    publisher, reference)
                VALUES (:sector_id, :publication, :author,
                    :publisher, :reference);
                """.format(table=MapDb._ProductsTableName)
            rowData = []
            for product in sector.products():
                rowData.append({
                    'sector_id': sector.id(),
                    'publication': product.publication(),
                    'author': product.author(),
                    'publisher': product.publisher(),
                    'reference': product.reference()})
            cursor.executemany(sql, rowData)

        if sector.allegiances():
            sql = """
                INSERT INTO {table} (sector_id, code, name, base)
                VALUES (:sector_id, :code, :name, :base);
                """.format(table=MapDb._AllegiancesTableName)
            rowData = []
            for allegiance in sector.allegiances():
                rowData.append({
                    'sector_id': sector.id(),
                    'code': allegiance.code(),
                    'name': allegiance.name(),
                    'base': allegiance.base()})
            cursor.executemany(sql, rowData)

        if sector.systems():
            sql = """
                INSERT INTO {table} (id, sector_id, hex_x, hex_y, name, uwp, remarks,
                    importance, economics, culture, nobility, bases, zone, pbg,
                    system_worlds, allegiance, stellar, notes)
                VALUES (:id, :sector_id, :hex_x, :hex_y, :name, :uwp, :remarks,
                    :importance, :economics, :culture, :nobility, :bases, :zone, :pbg,
                    :system_worlds, :allegiance, :stellar, :notes);
                """.format(table=MapDb._SystemsTableName)
            rowData = []
            for system in sector.systems():
                rowData.append({
                    'id': system.id(),
                    'sector_id': system.sectorId(),
                    'hex_x': system.hexX(),
                    'hex_y': system.hexY(),
                    'name': system.name(),
                    'uwp': system.uwp(),
                    'remarks': system.remarks(),
                    'importance': system.importance(),
                    'economics': system.economics(),
                    'culture': system.culture(),
                    'nobility': system.nobility(),
                    'bases': system.bases(),
                    'zone': system.zone(),
                    'pbg': system.pbg(),
                    'system_worlds': 1 if system.systemWorlds() is None else system.systemWorlds(),
                    'allegiance': system.allegiance(),
                    'stellar': system.stellar(),
                    'notes': system.notes()})
            cursor.executemany(sql, rowData)

        if sector.routes():
            sql = """
                INSERT INTO {table} (id, sector_id, start_hex_x, start_hex_y,
                    end_hex_x, end_hex_y, allegiance, type, style, colour, width)
                VALUES (:id, :sector_id, :start_hex_x, :start_hex_y,
                    :end_hex_x, :end_hex_y, :allegiance, :type, :style, :colour, :width);
                """.format(table=MapDb._RoutesTableName)
            rowData = []
            for route in sector.routes():
                rowData.append({
                    'id': route.id(),
                    'sector_id': route.sectorId(),
                    'start_hex_x': route.startHexX(),
                    'start_hex_y': route.startHexY(),
                    'end_hex_x': route.endHexX(),
                    'end_hex_y': route.endHexY(),
                    'allegiance': route.allegiance(),
                    'type': route.type(),
                    'style': route.style(),
                    'colour': route.colour(),
                    'width': route.width()})
            cursor.executemany(sql, rowData)

        if sector.borders():
            bordersSql = """
                INSERT INTO {table} (id, sector_id, show_label, wrap_label,
                    label_hex_x, label_hex_y, label_offset_x, label_offset_y,
                    label, colour, style, allegiance)
                VALUES (:id, :sector_id, :show_label, :wrap_label,
                    :label_hex_x, :label_hex_y, :label_offset_x, :label_offset_y,
                    :label, :colour, :style, :allegiance );
                """.format(table=MapDb._BordersTableName)
            hexesSql =  """
                INSERT INTO {table} (border_id, hex_x, hex_y)
                VALUES (:border_id, :hex_x, :hex_y);
                """.format(table=MapDb._BorderHexesTableName)
            bordersData = []
            hexesData = []
            for border in sector.borders():
                bordersData.append({
                    'id': border.id(),
                    'sector_id': border.sectorId(),
                    'show_label': 1 if border.showLabel() else 0,
                    'wrap_label': 1 if border.wrapLabel() else 0,
                    'label_hex_x': border.labelHexX(),
                    'label_hex_y': border.labelHexY(),
                    'label_offset_x': border.labelOffsetX(),
                    'label_offset_y': border.labelOffsetY(),
                    'label': border.label(),
                    'colour': border.colour(),
                    'style': border.style(),
                    'allegiance': border.allegiance()})
                for hexX, hexY in border.hexes():
                    hexesData.append({
                        'border_id': border.id(),
                        'hex_x': hexX,
                        'hex_y': hexY})
            cursor.executemany(bordersSql, bordersData)
            cursor.executemany(hexesSql, hexesData)

        if sector.regions():
            regionsSql = """
                INSERT INTO {table} (id, sector_id, show_label, wrap_label,
                    label_hex_x, label_hex_y, label_offset_x, label_offset_y,
                    label, colour)
                VALUES (:id, :sector_id, :show_label, :wrap_label,
                    :label_hex_x, :label_hex_y, :label_offset_x, :label_offset_y,
                    :label, :colour);
                """.format(table=MapDb._RegionsTableName)
            hexesSql =  """
                INSERT INTO {table} (region_id, hex_x, hex_y)
                VALUES (:region_id, :hex_x, :hex_y);
                """.format(table=MapDb._RegionHexesTableName)
            regionsData = []
            hexesData = []
            for region in sector.regions():
                regionsData.append({
                    'id': region.id(),
                    'sector_id': region.sectorId(),
                    'show_label': 1 if region.showLabel() else 0,
                    'wrap_label': 1 if region.wrapLabel() else 0,
                    'label_hex_x': region.labelHexX(),
                    'label_hex_y': region.labelHexY(),
                    'label_offset_x': region.labelOffsetX(),
                    'label_offset_y': region.labelOffsetY(),
                    'label': region.label(),
                    'colour': region.colour()})
                for hexX, hexY in region.hexes():
                    hexesData.append({
                        'region_id': region.id(),
                        'hex_x': hexX,
                        'hex_y': hexY})
            cursor.executemany(regionsSql, regionsData)
            cursor.executemany(hexesSql, hexesData)

        if sector.labels():
            sql = """
                INSERT INTO {table} (id, sector_id, text, hex_x, hex_y,
                    wrap, colour, size, offset_x, offset_y)
                VALUES (:id, :sector_id, :text, :hex_x, :hex_y,
                    :wrap, :colour, :size, :offset_x, :offset_y);
                """.format(table=MapDb._LabelsTableName)
            rowData = []
            for label in sector.labels():
                rowData.append({
                    'id': label.id(),
                    'sector_id': label.sectorId(),
                    'text': label.text(),
                    'hex_x': label.hexX(),
                    'hex_y': label.hexY(),
                    'wrap': 1 if label.wrap() else 0,
                    'colour': label.colour(),
                    'size': label.size(),
                    'offset_x': label.offsetX(),
                    'offset_y': label.offsetY()})
            cursor.executemany(sql, rowData)

    def _internalReadSector(
            self,
            sectorId: str,
            cursor: sqlite3.Cursor
            ) -> typing.Optional[DbSector]:
        sql = """
            SELECT universe_id, is_custom, milieu, sector_x, sector_y,
                primary_name, primary_language, abbreviation, sector_label,
                selected, tags, style_sheet, credits, publication, author,
                publisher, reference, notes
            FROM {table}
            WHERE id = :id;
            """.format(table=MapDb._SectorsTableName)
        cursor.execute(sql, {'id': sectorId})
        row = cursor.fetchone()
        if not row:
            return None

        sector = DbSector(
            id=sectorId,
            universeId=row[0],
            isCustom=True if row[1] else False,
            milieu=row[2],
            sectorX=row[3],
            sectorY=row[4],
            primaryName=row[5],
            primaryLanguage=row[6],
            abbreviation=row[7],
            sectorLabel=row[8],
            selected=True if row[9] else False,
            tags=row[10],
            styleSheet=row[11],
            credits=row[12],
            publication=row[13],
            author=row[14],
            publisher=row[15],
            reference=row[16],
            notes=row[17])

        sql = """
            SELECT name, language
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MapDb._AlternateNamesTableName)
        cursor.execute(sql, {'id': sectorId})
        sector.setAlternateNames(
            [(row[0], row[1]) for row in cursor.fetchall()])

        sql = """
            SELECT code, name
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MapDb._SubsectorNamesTableName)
        cursor.execute(sql, {'id': sectorId})
        sector.setSubsectorNames(
            [(row[0], row[1]) for row in cursor.fetchall()])

        sql = """
            SELECT publication, author, publisher, reference
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MapDb._ProductsTableName)
        cursor.execute(sql, {'id': sectorId})
        products = []
        for row in cursor.fetchall():
            products.append(DbProduct(
                publication=row[0],
                author=row[1],
                publisher=row[2],
                reference=row[3]))
        sector.setProducts(products)

        sql = """
            SELECT code, name, base
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MapDb._AllegiancesTableName)
        cursor.execute(sql, {'id': sectorId})
        allegiances = []
        for row in cursor.fetchall():
            allegiances.append(DbAllegiance(
                code=row[0],
                name=row[1],
                base=row[2]))
        sector.setAllegiances(allegiances)

        sql = """
            SELECT id, hex_x, hex_y, name, uwp, remarks, importance,
                economics, culture, nobility, bases, zone, pbg,
                system_worlds, allegiance, stellar, notes
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MapDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        systems = []
        for row in cursor.fetchall():
            systems.append(DbSystem(
                id=row[0],
                hexX=row[1],
                hexY=row[2],
                name=row[3],
                uwp=row[4],
                remarks=row[5],
                importance=row[6],
                economics=row[7],
                culture=row[8],
                nobility=row[9],
                bases=row[10],
                zone=row[11],
                pbg=row[12],
                systemWorlds=row[13],
                allegiance=row[14],
                stellar=row[15],
                notes=row[16]))
        sector.setSystems(systems)

        sql = """
            SELECT id, start_hex_x, start_hex_y, end_hex_x, end_hex_y,
                allegiance, type, style, colour, width
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MapDb._RoutesTableName)
        cursor.execute(sql, {'id': sectorId})
        routes = []
        for row in cursor.fetchall():
            routes.append(DbRoute(
                id=row[0],
                startHexX=row[1],
                startHexY=row[2],
                endHexX=row[3],
                endHexY=row[4],
                allegiance=row[5],
                type=row[6],
                style=row[7],
                colour=row[8],
                width=row[9]))
        sector.setRoutes(routes)

        sql = """
            SELECT id, show_label, wrap_label,
                label_hex_x, label_hex_y, label_offset_x, label_offset_y,
                label, colour, style, allegiance
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MapDb._BordersTableName)
        cursor.execute(sql, {'id': sectorId})
        borders = []
        for row in cursor.fetchall():
            borderId = row[0]

            hexesSql = """
                SELECT hex_x, hex_y
                FROM {table}
                WHERE border_id = :id;
                """.format(table=MapDb._BorderHexesTableName)
            cursor.execute(hexesSql, {'id': borderId})
            hexes = []
            for hexRow in cursor.fetchall():
                hexes.append((hexRow[0], hexRow[1]))

            borders.append(DbBorder(
                id=borderId,
                hexes=hexes,
                showLabel=True if row[1] else False,
                wrapLabel=True if row[2] else False,
                labelHexX=row[3],
                labelHexY=row[4],
                labelOffsetX=row[5],
                labelOffsetY=row[6],
                label=row[7],
                colour=row[8],
                style=row[9],
                allegiance=row[10]))
        sector.setBorders(borders)

        sql = """
            SELECT id, show_label, wrap_label,
                label_hex_x, label_hex_y, label_offset_x, label_offset_y,
                label, colour
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MapDb._RegionsTableName)
        cursor.execute(sql, {'id': sectorId})
        regions = []
        for row in cursor.fetchall():
            regionId = row[0]

            hexesSql = """
                SELECT hex_x, hex_y
                FROM {table}
                WHERE region_id = :id;
                """.format(table=MapDb._RegionHexesTableName)
            cursor.execute(hexesSql, {'id': regionId})
            hexes = []
            for hexRow in cursor.fetchall():
                hexes.append((hexRow[0], hexRow[1]))

            regions.append(DbRegion(
                id=regionId,
                hexes=hexes,
                showLabel=True if row[1] else False,
                wrapLabel=True if row[2] else False,
                labelHexX=row[3],
                labelHexY=row[4],
                labelOffsetX=row[5],
                labelOffsetY=row[6],
                label=row[7],
                colour=row[8]))
        sector.setRegions(regions)

        sql = """
            SELECT id, text, hex_x, hex_y, wrap, colour, size,
                offset_x, offset_y
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MapDb._LabelsTableName)
        cursor.execute(sql, {'id': sectorId})
        labels = []
        for row in cursor.fetchall():
            labels.append(DbLabel(
                id=row[0],
                text=row[1],
                hexX=row[2],
                hexY=row[3],
                wrap=True if row[4] else False,
                colour=row[5],
                size=row[6],
                offsetX=row[7],
                offsetY=row[8]))
        sector.setLabels(labels)

        return sector

    def _internalDeleteSector(
            self,
            sectorId: str,
            cursor: sqlite3.Cursor
            ) -> typing.Optional[DbUniverse]:
        sql = """
            DELETE FROM {table}
            WHERE id = :id
            """.format(
            table=MapDb._SectorsTableName)
        cursor.execute(sql, {'id': sectorId})

    def _internalListUniverseNames(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.Mapping[str, str]:
        sql = """
            SELECT id, name FROM {table}
            """.format(
            table=MapDb._UniversesTableName)
        cursor.execute(sql)
        idToNameMap = {}
        for row in cursor.fetchall():
            universeId = row[0]
            name = row[1]
            idToNameMap[universeId] = name

        return idToNameMap

    def _internalListSectorNames(
            self,
            universeId: typing.Optional[str],
            milieu: typing.Optional[str],
            cursor: sqlite3.Cursor
            ) -> typing.Mapping[str, str]:
        sql = 'SELECT id, name FROM {table}'.format(
            table=MapDb._UniversesTableName)
        selectData = {}
        if universeId and milieu:
            sql += """
                WHERE universe_id = :universe_id
                AND milieu = :milieu
                """
            selectData['universe_id'] = universeId
            selectData['milieu'] = milieu
        elif universeId:
            sql += "WHERE universe_id = :universe_id"""
            selectData['universe_id'] = universeId
        elif milieu:
            sql += "WHERE milieu = :milieu"""
            selectData['milieu'] = milieu
        sql += ';'
        cursor.execute(sql, selectData)

        idToNameMap = {}
        for row in cursor.fetchall():
            sectorId = row[0]
            name = row[1]
            idToNameMap[sectorId] = name

        return idToNameMap