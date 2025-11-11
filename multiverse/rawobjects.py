
import enum
import typing

class SectorFormat(enum.Enum):
    T5Column = 0, # aka Second Survey format
    T5Tab = 1

class MetadataFormat(enum.Enum):
    JSON = 0
    XML = 1

# TODO: Need to change this method of accessing the world attributes to something
# more standard
class WorldAttribute(enum.Enum):
    Hex = 0
    Name = 1
    UWP = 2
    Remarks = 3
    Importance = 4
    Economics = 5
    Culture = 6
    Nobility = 7
    Bases = 8
    Zone = 9
    PBG = 10
    SystemWorlds = 11
    Allegiance = 12
    Stellar = 13

# TODO: I don't like the naming of all these RawObjects. It probably
# makes sense for them to be Fs* (for filesystem) rather than Raw*

class RawWorld(object):
    def __init__(
            self,
            lineNumber: int
            ) -> None:
        self._lineNumber = lineNumber
        self._attributes: typing.Dict[WorldAttribute, str] = {}

    def lineNumber(self) -> int:
        return self._lineNumber

    def attribute(
            self,
            attribute: WorldAttribute
            ) -> str:
        return self._attributes.get(attribute, '')

    def setAttribute(
            self,
            attribute: WorldAttribute,
            value: str
            ) -> None:
        self._attributes[attribute] = value

class RawAllegiance(object):
    def __init__(
            self,
            code: str,
            name: str,
            base: typing.Optional[str],
            fileIndex: int
            ) -> None:
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
        self._sectorInfos = sectorInfos

    def sectorInfos(self) -> typing.Collection[RawSectorInfo]:
        return self._sectorInfos
