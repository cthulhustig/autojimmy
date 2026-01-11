
import typing

# TODO: I don't like the naming of all these RawObjects. It probably
# makes sense for them to be Fs* (for filesystem) rather than Raw*
# TODO: Get rid of the file index, there must be a way to a decent
# error message without them. The don't really mean much for most
# of the items as they're read from xml/json. It only really makes
# any sense for worlds as it's the line number in the source file

class RawWorld(object):
    def __init__(
            self,
            hex: typing.Optional[str],
            name: typing.Optional[str],
            allegiance: typing.Optional[str],
            zone: typing.Optional[str],
            uwp: typing.Optional[str],
            economics: typing.Optional[str],
            culture: typing.Optional[str],
            nobility: typing.Optional[str],
            bases: typing.Optional[str],
            remarks: typing.Optional[str],
            importance: typing.Optional[str],
            pbg: typing.Optional[str],
            systemWorlds: typing.Optional[str],
            stellar: typing.Optional[str],
            lineNumber: int
            ) -> None:
        super().__init__()
        self._hex = hex
        self._name = name
        self._allegiance = allegiance
        self._zone = zone
        self._uwp = uwp
        self._economics = economics
        self._culture = culture
        self._nobility = nobility
        self._bases = bases
        self._remarks = remarks
        self._importance = importance
        self._pbg = pbg
        self._systemWorlds = systemWorlds
        self._stellar = stellar
        self._lineNumber = lineNumber

    def lineNumber(self) -> int:
        return self._lineNumber

    # TODO: This should probably be mandatory
    def hex(self) -> typing.Optional[str]:
        return self._hex

    def name(self) -> typing.Optional[str]:
        return self._name

    def allegiance(self) -> typing.Optional[str]:
        return self._allegiance

    def zone(self) -> typing.Optional[str]:
        return self._zone

    def uwp(self) -> typing.Optional[str]:
        return self._uwp

    def economics(self) -> typing.Optional[str]:
        return self._economics

    def culture(self) -> typing.Optional[str]:
        return self._culture

    def nobility(self) -> typing.Optional[str]:
        return self._nobility

    def bases(self) -> typing.Optional[str]:
        return self._bases

    def remarks(self) -> typing.Optional[str]:
        return self._remarks

    def importance(self) -> typing.Optional[str]:
        return self._importance

    def pbg(self) -> typing.Optional[str]:
        return self._pbg

    # TODO: This should probably be an int
    def systemWorlds(self) -> typing.Optional[str]:
        return self._systemWorlds

    def stellar(self) -> typing.Optional[str]:
        return self._stellar

class RawAllegiance(object):
    def __init__(
            self,
            code: str,
            name: str,
            base: typing.Optional[str],
            fileIndex: int
            ) -> None:
        super().__init__()
        self._code = code
        self._name = name
        self._base = base
        self._fileIndex = fileIndex

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

    def base(self) -> typing.Optional[str]:
        return self._base

    def fileIndex(self) -> int:
        return self._fileIndex

class RawRoute(object):
    def __init__(
            self,
            startHex: str,
            endHex: str,
            startOffsetX: typing.Optional[int],
            startOffsetY: typing.Optional[int],
            endOffsetX: typing.Optional[int],
            endOffsetY: typing.Optional[int],
            allegiance: typing.Optional[str],
            type: typing.Optional[str],
            style: typing.Optional[str],
            colour: typing.Optional[str],
            width: typing.Optional[float],
            fileIndex: int
            ) -> None:
        super().__init__()
        self._startHex = startHex
        self._endHex = endHex
        self._startOffsetX = startOffsetX
        self._startOffsetY = startOffsetY
        self._endOffsetX = endOffsetX
        self._endOffsetY = endOffsetY
        self._allegiance = allegiance
        self._type = type
        self._style = style
        self._colour = colour
        self._width = width
        self._fileIndex = fileIndex

    def startHex(self) -> str:
        return self._startHex

    def endHex(self) -> str:
        return self._endHex

    def startOffsetX(self) -> typing.Optional[int]:
        return self._startOffsetX

    def startOffsetY(self) -> typing.Optional[int]:
        return self._startOffsetY

    def endOffsetX(self) -> typing.Optional[int]:
        return self._endOffsetX

    def endOffsetY(self) -> typing.Optional[int]:
        return self._endOffsetY

    def allegiance(self) -> typing.Optional[str]:
        return self._allegiance

    def type(self) -> typing.Optional[str]:
        return self._type

    def style(self) -> typing.Optional[str]:
        return self._style

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def width(self) -> typing.Optional[float]:
        return self._width

    def fileIndex(self) -> int:
        return self._fileIndex

# NOTE: If I'm ever generating borders then there are rules about the "winding" of the hex list
# https://travellermap.com/doc/metadata#borders
class RawBorder(object):
    def __init__(
            self,
            hexList: typing.Collection[str],
            allegiance: typing.Optional[str],
            showLabel: typing.Optional[bool],
            wrapLabel: typing.Optional[bool],
            labelHex: typing.Optional[str],
            labelOffsetX: typing.Optional[float],
            labelOffsetY: typing.Optional[float],
            label: typing.Optional[str],
            style: typing.Optional[str],
            colour: typing.Optional[str],
            fileIndex: int
            ) -> None:
        super().__init__()
        self._hexList = hexList
        self._allegiance = allegiance
        self._showLabel = showLabel
        self._wrapLabel = wrapLabel
        self._labelHex = labelHex
        self._labelOffsetX = labelOffsetX
        self._labelOffsetY = labelOffsetY
        self._label = label
        self._style = style
        self._colour = colour
        self._fileIndex = fileIndex

    def hexList(self) -> typing.Collection[str]:
        return self._hexList

    def allegiance(self) -> typing.Optional[str]:
        return self._allegiance

    def showLabel(self) -> typing.Optional[bool]:
        return self._showLabel

    def wrapLabel(self) -> typing.Optional[bool]:
        return self._wrapLabel

    def labelHex(self) -> typing.Optional[str]:
        return self._labelHex

    def labelOffsetX(self) -> typing.Optional[float]:
        return self._labelOffsetX

    def labelOffsetY(self) -> typing.Optional[float]:
        return self._labelOffsetY

    def label(self) -> typing.Optional[str]:
        return self._label

    def style(self) -> typing.Optional[str]:
        return self._style

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def fileIndex(self) -> int:
        return self._fileIndex

class RawLabel(object):
    def __init__(
            self,
            text: str,
            hex: str,
            colour: str,
            size: typing.Optional[str],
            wrap: typing.Optional[bool],
            offsetX: typing.Optional[float],
            offsetY: typing.Optional[float],
            fileIndex: int
            ) -> None:
        super().__init__()
        self._text = text
        self._hex = hex
        self._colour = colour
        self._size = size
        self._wrap = wrap
        self._offsetX = offsetX
        self._offsetY = offsetY
        self._fileIndex = fileIndex

    def text(self) -> str:
        return self._text

    def hex(self) -> str:
        return self._hex

    def colour(self) -> str:
        return self._colour

    def size(self) -> typing.Optional[str]:
        return self._size

    def wrap(self) -> typing.Optional[bool]:
        return self._wrap

    def offsetX(self) -> typing.Optional[float]:
        return self._offsetX

    def offsetY(self) -> typing.Optional[float]:
        return self._offsetY

    def fileIndex(self) -> int:
        return self._fileIndex

# NOTE: If I'm ever generating routes then they follow the same "winding" rules for the hex list as borders
# https://travellermap.com/doc/metadata#borders
class RawRegion(object):
    def __init__(
            self,
            hexList: typing.Collection[str],
            showLabel: typing.Optional[bool],
            wrapLabel: typing.Optional[bool],
            labelHex: typing.Optional[str],
            labelOffsetX: typing.Optional[float],
            labelOffsetY: typing.Optional[float],
            label: typing.Optional[str],
            colour: typing.Optional[str],
            fileIndex: int
            ) -> None:
        super().__init__()
        self._hexList = hexList
        self._showLabel = showLabel
        self._wrapLabel = wrapLabel
        self._labelHex = labelHex
        self._labelOffsetX = labelOffsetX
        self._labelOffsetY = labelOffsetY
        self._label = label
        self._colour = colour
        self._fileIndex = fileIndex

    def hexList(self) -> typing.Collection[str]:
        return self._hexList

    def showLabel(self) -> typing.Optional[bool]:
        return self._showLabel

    def wrapLabel(self) -> typing.Optional[bool]:
        return self._wrapLabel

    def labelHex(self) -> typing.Optional[str]:
        return self._labelHex

    def labelOffsetX(self) -> typing.Optional[float]:
        return self._labelOffsetX

    def labelOffsetY(self) -> typing.Optional[float]:
        return self._labelOffsetY

    def label(self) -> typing.Optional[str]:
        return self._label

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def fileIndex(self) -> int:
        return self._fileIndex

class RawSource(object):
    def __init__(
            self,
            publication: typing.Optional[str],
            author: typing.Optional[str],
            publisher: typing.Optional[str],
            reference: typing.Optional[str]
            ) -> None:
        super().__init__()
        self._publication = publication
        self._publisher = publisher
        self._author = author
        self._reference = reference

    def publication(self) -> typing.Optional[str]:
        return self._publication

    def author(self) -> typing.Optional[str]:
        return self._author

    def publisher(self) -> typing.Optional[str]:
        return self._publisher

    def reference(self) -> typing.Optional[str]:
        return self._reference

class RawSources(object):
    def __init__(
            self,
            credits: typing.Optional[str],
            primary: typing.Optional[RawSource],
            products: typing.Optional[typing.Collection[RawSource]]
            ) -> None:
        super().__init__()
        self._credits = credits
        self._primary = primary
        self._products = products

    def credits(self) -> typing.Optional[str]:
        return self._credits

    def primary(self) -> typing.Optional[RawSource]:
        return self._primary

    def products(self) -> typing.Optional[typing.Collection[RawSource]]:
        return self._products

class RawMetadata(object):
    def __init__(
            self,
            canonicalName: typing.Collection[str],
            alternateNames: typing.Optional[typing.Collection[str]],
            nameLanguages: typing.Optional[typing.Mapping[str, str]], # Maps names to languages
            abbreviation: typing.Optional[str],
            sectorLabel: typing.Optional[str],
            subsectorNames: typing.Optional[typing.Mapping[str, str]], # Maps subsector code (A-P) to the name of that sector
            x: int,
            y: int,
            selected: typing.Optional[bool],
            tags: typing.Optional[str],
            allegiances: typing.Optional[typing.Collection[RawAllegiance]],
            routes: typing.Optional[typing.Collection[RawRoute]],
            borders: typing.Optional[typing.Collection[RawBorder]],
            labels: typing.Optional[typing.Collection[RawLabel]],
            regions: typing.Optional[typing.Collection[RawRegion]],
            sources: typing.Optional[RawSources],
            styleSheet: typing.Optional[str]
            ) -> None:
        super().__init__()
        self._canonicalName = canonicalName
        self._alternateNames = alternateNames
        self._nameLanguages = nameLanguages
        self._abbreviation = abbreviation
        self._sectorLabel = sectorLabel
        self._subsectorNames = subsectorNames
        self._x = x
        self._y = y
        self._selected = selected
        self._tags = tags
        self._allegiances = allegiances
        self._routes = routes
        self._borders = borders
        self._labels = labels
        self._regions = regions
        self._sources = sources
        self._styleSheet = styleSheet

    def canonicalName(self) -> str:
        return self._canonicalName

    def alternateNames(self) -> typing.Optional[typing.Collection[str]]:
        return self._alternateNames

    def names(self) -> typing.Collection[str]:
        names = [self._canonicalName]
        if self._alternateNames:
            names.extend(self._alternateNames)
        return names

    def nameLanguage(self, name: str) -> typing.Optional[str]:
        if not self._nameLanguages:
            return None
        return self._nameLanguages.get(name, None)

    def nameLanguages(self) -> typing.Mapping[str, str]:
        return self._nameLanguages

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

    def sectorLabel(self) -> typing.Optional[str]:
        return self._sectorLabel

    def subsectorNames(self) -> typing.Optional[typing.Mapping[str, str]]:
        return self._subsectorNames

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def selected(self) -> typing.Optional[bool]:
        return self._selected

    def tags(self) -> typing.Optional[str]:
        return self._tags

    def allegiances(self) -> typing.Optional[typing.Collection[RawAllegiance]]:
        return self._allegiances

    def routes(self) -> typing.Optional[typing.Collection[RawRoute]]:
        return self._routes

    def borders(self) -> typing.Optional[typing.Collection[RawBorder]]:
        return self._borders

    def labels(self) -> typing.Optional[typing.Collection[RawLabel]]:
        return self._labels

    def regions(self) -> typing.Optional[typing.Collection[RawRegion]]:
        return self._regions

    def sources(self) -> typing.Optional[RawSources]:
        return self._sources

    def styleSheet(self) -> typing.Optional[str]:
        return self._styleSheet

class RawNameInfo(object):
    def __init__(
            self,
            name: str,
            language: typing.Optional[str],
            source: typing.Optional[str]
            ):
        super().__init__()
        self._name = name
        self._language = language
        self._source = source

    def name(self) -> str:
        return self._name

    def language(self) -> typing.Optional[str]:
        return self._language

    def source(self) -> typing.Optional[str]:
        return self._source

class RawSectorInfo(object):
    def __init__(
            self,
            x: int,
            y: int,
            milieu: str,
            abbreviation: typing.Optional[str],
            tags: typing.Optional[str],
            nameInfos: typing.Optional[typing.Collection[RawNameInfo]],
            ) -> None:
        super().__init__()
        self._x = x
        self._y = y
        self._milieu = milieu
        self._abbreviation = abbreviation
        self._tags = tags
        self._nameInfos = nameInfos

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def milieu(self) -> str:
        return self._milieu

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

    def tags(self) -> typing.Optional[str]:
        return self._tags

    def nameInfos(self) -> typing.Optional[typing.Collection[RawNameInfo]]:
        return self._nameInfos

class RawUniverseInfo(object):
    def __init__(
            self,
            sectorInfos: typing.Collection[RawSectorInfo]
            ) -> None:
        super().__init__()
        self._sectorInfos = sectorInfos

    def sectorInfos(self) -> typing.Collection[RawSectorInfo]:
        return self._sectorInfos

class RawStockAllegiance(object):
    def __init__(
            self,
            code: str,
            name: str,
            legacy: str,
            base: typing.Optional[str] = None,
            location: typing.Optional[str] = None
            ) -> None:
        super().__init__()
        self._code = code
        self._name = name
        self._legacy = legacy
        self._base = base
        self._location = location

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

    def legacy(self) -> str:
        return self._legacy

    def base(self) -> typing.Optional[str]:
        return self._base

    def location(self) -> typing.Optional[str]:
        return self._location

class RawStockSophont(object):
    def __init__(
            self,
            code: str,
            name: str,
            location: typing.Optional[str] = None
            ) -> None:
        super().__init__()
        self._code = code
        self._name = name
        self._location = location

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

    def location(self) -> str:
        return self._location