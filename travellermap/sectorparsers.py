import common
import enum
import itertools
import json
import logging
import re
import typing
import xml.etree.ElementTree

_XmlFloatDecimalPlaces = 2

class SectorFormat(enum.Enum):
    T5Column = 0, # aka Second Survey format
    T5Tab = 1

class MetadataFormat(enum.Enum):
    JSON = 0
    XML = 1

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
        return self._attributes[attribute]

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
            hexList: typing.Iterable[str],
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

    def hexList(self) -> typing.Iterable[str]:
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
            hexList: typing.Iterable[str],
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

    def hexList(self) -> typing.Iterable[str]:
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

class RawMetadata(object):
    def __init__(
            self,
            canonicalName: typing.Iterable[str],
            alternateNames: typing.Optional[typing.Iterable[str]],
            nameLanguages: typing.Optional[typing.Mapping[str, str]],
            abbreviation: typing.Optional[str],
            subsectorNames: typing.Optional[typing.Mapping[str, str]], # Maps subsector code (A-P) to the name of that sector
            x: int,
            y: int,
            tags: typing.Optional[str],
            allegiances: typing.Optional[typing.Iterable[RawAllegiance]],
            routes: typing.Optional[typing.Iterable[RawRoute]],
            borders: typing.Optional[typing.Iterable[RawBorder]],
            labels: typing.Optional[typing.Iterable[RawLabel]],
            regions: typing.Optional[typing.Iterable[RawRegion]],
            styleSheet: typing.Optional[str]
            ) -> None:
        self._canonicalName = canonicalName
        self._alternateNames = alternateNames
        self._nameLanguages = nameLanguages
        self._abbreviation = abbreviation
        self._subsectorNames = subsectorNames
        self._x = x
        self._y = y
        self._tags = tags
        self._allegiances = allegiances
        self._routes = routes
        self._borders = borders
        self._labels = labels
        self._regions = regions
        self._styleSheet = styleSheet

    def canonicalName(self) -> str:
        return self._canonicalName

    def alternateNames(self) -> typing.Optional[typing.Iterable[str]]:
        return self._alternateNames

    def names(self) -> typing.Iterable[str]:
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

    def subsectorNames(self) -> typing.Optional[typing.Mapping[str, str]]:
        return self._subsectorNames

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def tags(self) -> typing.Optional[str]:
        return self._tags

    def allegiances(self) -> typing.Optional[typing.Iterable[RawAllegiance]]:
        return self._allegiances

    def routes(self) -> typing.Optional[typing.Iterable[RawRoute]]:
        return self._routes

    def borders(self) -> typing.Optional[typing.Iterable[RawBorder]]:
        return self._borders

    def labels(self) -> typing.Optional[typing.Iterable[RawLabel]]:
        return self._labels

    def regions(self) -> typing.Optional[typing.Iterable[RawRegion]]:
        return self._regions

    def styleSheet(self) -> typing.Optional[str]:
        return self._styleSheet


_HeaderPattern = re.compile(r'(?:([\w{}()\[\]]+)\s*)')
_SeparatorPattern = re.compile(r'(?:([-]+)\s?)')
_T5Column_ColumnNameToAttributeMap = {
    'Hex': WorldAttribute.Hex,
    'Name': WorldAttribute.Name,
    'UWP': WorldAttribute.UWP,
    'Remarks': WorldAttribute.Remarks,
    '{Ix}': WorldAttribute.Importance,
    '(Ex)': WorldAttribute.Economics,
    '[Cx]': WorldAttribute.Culture,
    'N': WorldAttribute.Nobility,
    'B': WorldAttribute.Bases,
    'Z': WorldAttribute.Zone,
    'PBG': WorldAttribute.PBG,
    'W': WorldAttribute.SystemWorlds,
    'A': WorldAttribute.Allegiance,
    'Stellar': WorldAttribute.Stellar
}
_T5Row_ColumnNameToAttributeMap = {
    'Hex': WorldAttribute.Hex,
    'Name': WorldAttribute.Name,
    'UWP': WorldAttribute.UWP,
    'Remarks': WorldAttribute.Remarks,
    '{Ix}': WorldAttribute.Importance,
    '(Ex)': WorldAttribute.Economics,
    '[Cx]': WorldAttribute.Culture,
    'Nobility': WorldAttribute.Nobility,
    'Bases': WorldAttribute.Bases,
    'Zone': WorldAttribute.Zone,
    'PBG': WorldAttribute.PBG,
    'W': WorldAttribute.SystemWorlds,
    'Allegiance': WorldAttribute.Allegiance,
    'Stars': WorldAttribute.Stellar
}

def _isAllDashes(string: str) -> bool:
    if not string:
        return False # Empty string isn't all dashes
    for c in string:
        if c != '-':
            return False
    return True

def _optionalConvertToBool(
        value: typing.Optional[typing.Any],
        attributeName: str,
        elementName: str,
        identifier: str
        ) -> typing.Optional[int]:
    if value == None:
        return None

    try:
        return str(value).lower() == 'true'
    except Exception as ex:
        raise RuntimeError(f'Failed to convert {attributeName} attribute "{value}" to bool for {elementName} in {identifier} ({str(ex)})')

def _optionalConvertToInt(
        value: typing.Optional[typing.Any],
        attributeName: str,
        elementName: str,
        identifier: str
        ) -> typing.Optional[int]:
    if value == None:
        return None

    try:
        return int(value)
    except Exception as ex:
        raise RuntimeError(f'Failed to convert {attributeName} attribute "{value}" to int for {elementName} in {identifier} ({str(ex)})')

def _optionalConvertToFloat(
        value: typing.Optional[typing.Any],
        attributeName: str,
        elementName: str,
        identifier: str
        ) -> typing.Optional[int]:
    if value == None:
        return None

    try:
        return float(value)
    except Exception as ex:
        raise RuntimeError(f'Failed to convert {attributeName} attribute "{value}" to float for {elementName} in {identifier} ({str(ex)})')

def sectorFileFormatDetect(content: str) -> typing.Optional[SectorFormat]:
    hasComment = False
    hasSeparator = False
    foundNames = None
    for line in content.splitlines():
        if not line:
            continue # Ignore blank lines
        if line[0] == '#':
            hasComment = True
            continue

        if not foundNames:
            columnNames = _HeaderPattern.findall(line)
            if len(columnNames) < 14:
                # Technically this is off spec for both file types but some second
                # survey files have off spec comments so just skip it
                continue

            # Check if this line contains all the mandatory columns
            for column in _T5Column_ColumnNameToAttributeMap.keys():
                if column not in columnNames:
                    continue

            foundNames = columnNames
            continue

        # The header has been found so check if this is a valid separator line for T5 column
        # format
        separators = _SeparatorPattern.findall(line)
        if len(separators) == len(foundNames):
            hasSeparator = True

        # Stop reading after processing the first line after the column names were found
        break

    if not foundNames:
        # Didn't find any column names
        return None

    if (not hasComment) and (not hasSeparator):
        return SectorFormat.T5Tab

    if hasSeparator:
        return SectorFormat.T5Column

    return None

def readSector(
        content: str,
        format: SectorFormat,
        identifier: str, # File name or some other identifier, used for logging and error generation
        ) -> typing.Iterable[RawWorld]:
    if format == SectorFormat.T5Column:
        return readT5ColumnSector(
            content=content,
            identifier=identifier)
    elif format == SectorFormat.T5Tab:
        return readT5RowSector(
            content=content,
            identifier=identifier)
    else:
        raise RuntimeError(f'Unknown sector format {format} for {identifier}')

def readT5ColumnSector(
        content: str,
        identifier: str
        ) -> typing.Iterable[RawWorld]:
    worlds = []
    columnNames = None
    columnAttributes = None
    columnWidths = None
    for lineNumber, line in enumerate(content.splitlines()):
        if not line:
            # Ignore empty lines
            continue
        if line[:1] == '#':
            # Ignore comments
            continue

        if not columnNames:
            columnNames = _HeaderPattern.findall(line)
            if len(columnNames) < len(_T5Column_ColumnNameToAttributeMap):
                # This is needed as some sectors (notably Shadow Rift) are off format and have
                # broken comments that don't start with #. This gets logged at a low level so
                # we don't spam the logs every time we start
                logging.debug(
                    f'Skipping bogus header on line {lineNumber} for {identifier}')
                columnNames = None
                continue

            # Check that mandatory columns are present
            for columnName in _T5Column_ColumnNameToAttributeMap.keys():
                if columnName not in columnNames:
                    raise RuntimeError(
                        f'Unable to load data for {identifier} (Header is missing {columnName} column)')

            # Convert column names to list of column attributes with None for unknown columns
            columnAttributes = []
            for columnName in columnNames:
                attribute = _T5Column_ColumnNameToAttributeMap.get(columnName)
                columnAttributes.append(attribute)
            continue
        elif not columnWidths:
            separators = _SeparatorPattern.findall(line)
            if len(separators) != len(columnNames):
                raise RuntimeError(
                    f'Unable to load data for {identifier} (Header column count doesn\'t match separator column count)')

            columnWidths = []
            for columnSeparator in separators:
                columnWidths.append(len(columnSeparator))
            continue

        # Parse the line as a world definition
        try:
            worlds.append(_readT5ColumnWorld(
                line=line,
                lineNumber=lineNumber,
                columnAttributes=columnAttributes,
                columnWidths=columnWidths))
        except Exception as ex:
            logging.warning(
                f'Failed parse world on line {lineNumber} in data for {identifier} ({str(ex)})')
            continue
    return worlds

def _readT5ColumnWorld(
        line: str,
        lineNumber: int,
        columnAttributes: typing.Iterable[WorldAttribute],
        columnWidths: typing.Iterable[int]
        ) -> RawWorld:
    worldData = RawWorld(lineNumber=lineNumber)
    lineLength = len(line)
    startIndex = 0
    finishIndex = 0
    for attribute, width in itertools.zip_longest(columnAttributes, columnWidths):
        if startIndex >= lineLength:
            raise RuntimeError('Line is to short')

        finishIndex = startIndex + width
        if attribute != None:
            data = line[startIndex:finishIndex].strip()
            if data and _isAllDashes(data):
                data = '' # Replace no data marker with empty string

            worldData.setAttribute(
                attribute=attribute,
                value=data)
        startIndex = finishIndex + 1
    return worldData

def readT5RowSector(
        content: str,
        identifier: str
        ) -> typing.Iterable[RawWorld]:
    worlds = []
    columnNames = None
    columnAttributes = None
    for lineNumber, line in enumerate(content.splitlines()):
        if not line:
            # Ignore blank lines
            continue
        if line[:1] == '#':
            # Technically comments aren't allowed in T5 tab format but ignore them anyway
            continue

        if not columnNames:
            columnNames = _HeaderPattern.findall(line)
            if len(columnNames) < len(_T5Row_ColumnNameToAttributeMap):
                # This is needed as some sectors (notably Shadow Rift) are off format and have
                # broken comments that don't start with #. This gets logged at a low level so
                # we don't spam the logs every time we start
                logging.debug(
                    f'Skipping bogus header on line {lineNumber} for {identifier}')
                columnNames = None
                continue

            # Check that mandatory columns are present
            for columnName in _T5Row_ColumnNameToAttributeMap.keys():
                if columnName not in columnNames:
                    raise RuntimeError(
                        f'Unable to load data for {identifier} (Header is missing {columnName} column)')

            # Convert column names to list of column attributes with None for unknown columns
            columnAttributes = []
            for columnName in columnNames:
                attribute = _T5Row_ColumnNameToAttributeMap.get(columnName)
                columnAttributes.append(attribute)
            continue

        # Parse the line as a world definition
        try:
            worlds.append(_readT5RowWorld(
                line=line,
                lineNumber=lineNumber,
                columnAttributes=columnAttributes))
        except Exception as ex:
            logging.warning(
                f'Failed parse world on line {lineNumber} in data for {identifier} ({str(ex)})')
            continue
    return worlds

def _readT5RowWorld(
        line: str,
        lineNumber: int,
        columnAttributes: typing.Iterable[WorldAttribute],
        ) -> RawWorld:
    columnData = line.split('\t')
    if len(columnData) != len(columnAttributes):
        raise RuntimeError('Line has incorrect number of columns')

    worldData = RawWorld(lineNumber=lineNumber)
    for attribute, data in itertools.zip_longest(columnAttributes, columnData):
        if data and _isAllDashes(data):
            data = '' # Replace no data marker with empty string

        worldData.setAttribute(
            attribute=attribute,
            value=data)
    return worldData

def metadataFileFormatDetect(content: str) -> typing.Optional[MetadataFormat]:
    try:
        xml.etree.ElementTree.fromstring(content)
        return MetadataFormat.XML
    except:
        pass

    try:
        json.loads(content)
        return MetadataFormat.JSON
    except:
        pass

    return None

def readMetadata(
        content: str,
        format: MetadataFormat,
        identifier: str
        ) -> RawMetadata:
    if format == MetadataFormat.XML:
        return readXMLMetadata(
            content=content,
            identifier=identifier)
    elif format == MetadataFormat.JSON:
        return readJSONMetadata(
            content=content,
            identifier=identifier)
    else:
        raise RuntimeError(f'Unknown metadata format {format} for {identifier}')

def readXMLMetadata(
        content: str,
        identifier: str
        ) -> RawMetadata:
    sectorElement = xml.etree.ElementTree.fromstring(content)

    nameElements = sectorElement.findall('./Name')
    if not nameElements:
        raise RuntimeError(f'Failed to find Name element in {identifier} metadata')

    names = []
    nameLanguages = {}
    for element in nameElements:
        name = element.text
        names.append(name)

        lang = element.attrib.get('Lang')
        if lang != None:
            nameLanguages[name] = lang

    xElement = sectorElement.find('./X')
    if xElement == None:
        raise RuntimeError(f'Failed to find X element in {identifier} metadata')
    try:
        x = int(xElement.text)
    except Exception as ex:
        raise RuntimeError(f'Failed to convert X value "{xElement.text}" to int in {identifier} metadata ({str(ex)})')

    yElement = sectorElement.find('./Y')
    if yElement == None:
        raise RuntimeError(f'Failed to find Y element in {identifier} metadata')
    try:
        y = int(yElement.text)
    except Exception as ex:
        raise RuntimeError(f'Failed to convert Y value "{yElement.text}" to int in {identifier} metadata ({str(ex)})')

    subsectorElements = sectorElement.findall('./Subsectors/Subsector')
    subsectorNames = None
    if subsectorElements:
        subsectorNames = {}
        for element in subsectorElements:
            code = element.get('Index')
            if code == None:
                raise RuntimeError(f'Failed to find Index attribute for Subsector in {identifier} metadata')

            upperCode = code.upper()
            if len(code) != 1 or (ord(upperCode) < ord('A') or ord(upperCode) > ord('P')):
                raise RuntimeError(f'Invalid Index attribute "{code}" for Subsector in {identifier} metadata')

            subsectorNames[code] = element.text

    allegianceElements = sectorElement.findall('./Allegiances/Allegiance')
    allegiances = None
    if allegianceElements:
        allegiances = []
        for index, element in enumerate(allegianceElements):
            code = element.get('Code')
            if code == None:
                raise RuntimeError(f'Failed to find Code attribute for Allegiance in {identifier} metadata')

            # Ignore allegiances that are just a sequence of '-'
            if code and not _isAllDashes(code):
                allegiances.append(RawAllegiance(
                    code=code,
                    name=element.text,
                    base=element.get('Base'),
                    fileIndex=index))

    routeElements = sectorElement.findall('./Routes/Route')
    routes = None
    if routeElements:
        routes = []
        for index, element in enumerate(routeElements):
            startHex = element.get('Start')
            if not startHex:
                raise RuntimeError(f'Failed to find Start attribute for Route in {identifier} metadata')

            endHex = element.get('End')
            if not endHex:
                raise RuntimeError(f'Failed to find End attribute for Route in {identifier} metadata')

            startOffsetX = _optionalConvertToInt(element.get('StartOffsetX'), 'StartOffsetX', 'Route', identifier)
            startOffsetY = _optionalConvertToInt(element.get('StartOffsetY'), 'StartOffsetY', 'Route', identifier)
            endOffsetX = _optionalConvertToInt(element.get('EndOffsetX'), 'EndOffsetX', 'Route', identifier)
            endOffsetY = _optionalConvertToInt(element.get('EndOffsetY'), 'EndOffsetY', 'Route', identifier)
            width = _optionalConvertToFloat(element.get('Width'), 'Width', 'Route', identifier)

            routes.append(RawRoute(
                startHex=startHex,
                endHex=endHex,
                startOffsetX=startOffsetX,
                startOffsetY=startOffsetY,
                endOffsetX=endOffsetX,
                endOffsetY=endOffsetY,
                allegiance=element.get('Allegiance'),
                type=element.get('Type'),
                style=element.get('Style'),
                colour=element.get('Color'),
                width=width,
                fileIndex=index))

    borderElements = sectorElement.findall('./Borders/Border')
    borders = None
    if borderElements:
        borders = []
        for index, element in enumerate(borderElements):
            path = element.text.split(' ')
            showLabel = _optionalConvertToBool(element.get('ShowLabel'), 'ShowLabel', 'Border', identifier)
            wrapLabel = _optionalConvertToBool(element.get('WrapLabel'), 'WrapLabel', 'Border', identifier)
            labelOffsetX = _optionalConvertToFloat(element.get('LabelOffsetX'), 'LabelOffsetX', 'Border', identifier)
            labelOffsetY = _optionalConvertToFloat(element.get('LabelOffsetY'), 'LabelOffsetY', 'Border', identifier)

            borders.append(RawBorder(
                hexList=path,
                allegiance=element.get('Allegiance'),
                showLabel=showLabel,
                wrapLabel=wrapLabel,
                labelHex=element.get('LabelPosition'),
                labelOffsetX=labelOffsetX,
                labelOffsetY=labelOffsetY,
                label=element.get('Label'),
                style=element.get('Style'),
                colour=element.get('Color'),
                fileIndex=index))

    labelElements = sectorElement.findall('./Labels/Label')
    labels = None
    if labelElements:
        labels = []
        for index, element in enumerate(labelElements):
            hex = element.get('Hex')
            if hex == None:
                raise RuntimeError(f'Failed to find Hex element for Label in {identifier} metadata')

            colour = element.get('Color')
            if colour == None:
                raise RuntimeError(f'Failed to find Color element for Label in {identifier} metadata')

            wrap = _optionalConvertToBool(element.get('Wrap'), 'Wrap', 'Label', identifier)
            offsetX = _optionalConvertToFloat(element.get('OffsetX'), 'OffsetX', 'Label', identifier)
            offsetY = _optionalConvertToFloat(element.get('OffsetY'), 'OffsetY', 'Label', identifier)

            labels.append(RawLabel(
                text=element.text,
                hex=hex,
                colour=colour,
                size=element.get('Size'),
                wrap=wrap,
                offsetX=offsetX,
                offsetY=offsetY,
                fileIndex=index))

    regionElements = sectorElement.findall('./Regions/Region')
    regions = None
    if regionElements:
        regions = []
        for index, element in enumerate(regionElements):
            path = element.text.split(' ')
            showLabel = _optionalConvertToBool(element.get('ShowLabel'), 'ShowLabel', 'Region', identifier)
            wrapLabel = _optionalConvertToBool(element.get('WrapLabel'), 'WrapLabel', 'Region', identifier)
            labelOffsetX = _optionalConvertToFloat(element.get('LabelOffsetX'), 'LabelOffsetX', 'Region', identifier)
            labelOffsetY = _optionalConvertToFloat(element.get('LabelOffsetY'), 'LabelOffsetY', 'Region', identifier)

            regions.append(RawRegion(
                hexList=path,
                showLabel=showLabel,
                wrapLabel=wrapLabel,
                labelHex=element.get('LabelPosition'),
                labelOffsetX=labelOffsetX,
                labelOffsetY=labelOffsetY,
                label=element.get('Label'),
                colour=element.get('Color'),
                fileIndex=index))

    styleSheetElement = sectorElement.find('./Stylesheet')
    styleSheet = styleSheetElement.text if styleSheetElement != None else None

    return RawMetadata(
        canonicalName=names[0],
        alternateNames=names[1:],
        nameLanguages=nameLanguages,
        abbreviation=sectorElement.get('Abbreviation'),
        subsectorNames=subsectorNames,
        x=x,
        y=y,
        tags=sectorElement.get('Tags'),
        allegiances=allegiances,
        routes=routes,
        borders=borders,
        labels=labels,
        regions=regions,
        styleSheet=styleSheet)

def readJSONMetadata(
        content: str,
        identifier: str
        ) -> RawMetadata:
    sectorElement = json.loads(content)

    nameElements = sectorElement.get('Names')
    if not nameElements:
        raise RuntimeError(f'Failed to find Names element in {identifier} metadata')

    names = []
    nameLanguages = {}
    for element in nameElements:
        name = element.get('Text')
        if name == None:
            logging.warning(f'Skipping name with no Text element in {identifier} metadata')
            continue
        names.append(str(name))

        lang = element.get('Lang')
        if lang != None:
            nameLanguages[name] = str(lang)

    x = sectorElement.get('X')
    if x == None:
        raise RuntimeError(f'Failed to find X element in {identifier} metadata')
    try:
        x = int(x)
    except Exception as ex:
        raise RuntimeError(f'Failed to convert X value "{x}" to int in {identifier} metadata ({str(ex)})')

    y = sectorElement.get('Y')
    if y == None:
        raise RuntimeError(f'Failed to find Y element in {identifier} metadata')
    try:
        y = int(y)
    except Exception as ex:
        raise RuntimeError(f'Failed to convert Y value "{y}" to int in {identifier} metadata ({str(ex)})')

    subsectorElements = sectorElement.get('Subsectors')
    subsectorNames = None
    if subsectorElements:
        subsectorNames = {}
        if subsectorElements:
            for element in subsectorElements:
                name = element.get('Name')
                if name == None:
                    raise RuntimeError(f'Failed to find Name element for Subsector in {identifier} metadata')

                code = element.get('Index')
                if code == None:
                    raise RuntimeError(f'Failed to find Index element for Subsector in {identifier} metadata')

                upperCode = code.upper()
                if len(code) != 1 or (ord(upperCode) < ord('A') or ord(upperCode) > ord('P')):
                    raise RuntimeError(f'Invalid Index attribute "{code}" for Subsector in {identifier} metadata')

                subsectorNames[code] = name

    allegianceElements = sectorElement.get('Allegiances')
    allegiances = None
    if allegianceElements:
        allegiances = []
        if allegianceElements:
            for index, element in enumerate(allegianceElements):
                name = element.get('Name')
                if name == None:
                    raise RuntimeError(f'Failed to find Name element for Allegiance in {identifier} metadata')

                code = element.get('Code')
                if code == None:
                    raise RuntimeError(f'Failed to find Code element for Allegiance in {identifier} metadata')

                # Ignore allegiances that are just a sequence of '-'
                if code and not _isAllDashes(code):
                    allegiances.append(RawAllegiance(
                        code=code,
                        name=name,
                        base=element.get('Base'),
                        fileIndex=index))

    routeElements = sectorElement.get('Routes')
    routes = None
    if routeElements:
        routes = []
        for index, element in enumerate(routeElements):
            startHex = element.get('Start')
            if startHex == None:
                raise RuntimeError(f'Failed to find Start element for Route in {identifier} metadata')

            endHex = element.get('End')
            if endHex == None:
                raise RuntimeError(f'Failed to find End element for Route in {identifier} metadata')

            startOffsetX = _optionalConvertToInt(element.get('StartOffsetX'), 'StartOffsetX', 'Route', identifier)
            startOffsetY = _optionalConvertToInt(element.get('StartOffsetY'), 'StartOffsetY', 'Route', identifier)
            endOffsetX = _optionalConvertToInt(element.get('EndOffsetX'), 'EndOffsetX', 'Route', identifier)
            endOffsetY = _optionalConvertToInt(element.get('EndOffsetY'), 'EndOffsetY', 'Route', identifier)
            width = _optionalConvertToFloat(element.get('Width'), 'Width', 'Route', identifier)

            routes.append(RawRoute(
                startHex=startHex,
                endHex=endHex,
                startOffsetX=startOffsetX,
                startOffsetY=startOffsetY,
                endOffsetX=endOffsetX,
                endOffsetY=endOffsetY,
                allegiance=element.get('Allegiance'),
                type=element.get('Type'),
                style=element.get('Style'),
                colour=element.get('Color'),
                width=width,
                fileIndex=index))

    borderElements = sectorElement.get('Borders')
    borders = None
    if borderElements:
        borders = []
        for index, element in enumerate(borderElements):
            path = element.get('Path')
            if path == None:
                raise RuntimeError(f'Failed to find Path element for Border in {identifier} metadata')
            path = path.split(' ')

            showLabel = _optionalConvertToBool(element.get('ShowLabel'), 'ShowLabel', 'Border', identifier)
            wrapLabel = _optionalConvertToBool(element.get('WrapLabel'), 'WrapLabel', 'Border', identifier)
            labelOffsetX = _optionalConvertToFloat(element.get('LabelOffsetX'), 'LabelOffsetX', 'Border', identifier)
            labelOffsetY = _optionalConvertToFloat(element.get('LabelOffsetY'), 'LabelOffsetY', 'Border', identifier)

            borders.append(RawBorder(
                hexList=path,
                allegiance=element.get('Allegiance'),
                showLabel=showLabel,
                wrapLabel=wrapLabel,
                labelHex=element.get('LabelPosition'),
                labelOffsetX=labelOffsetX,
                labelOffsetY=labelOffsetY,
                label=element.get('Label'),
                style=element.get('Style'),
                colour=element.get('Color'),
                fileIndex=index))

    labelElements = sectorElement.get('Labels')
    labels = None
    if labelElements:
        labels = []
        for index, element in enumerate(labelElements):
            text = element.get('Text')
            if text == None:
                raise RuntimeError(f'Failed to find Text element for Label in {identifier} metadata')

            hex = element.get('Hex')
            if hex == None:
                raise RuntimeError(f'Failed to find Hex element for Label in {identifier} metadata')

            colour = element.get('Color')
            if colour == None:
                raise RuntimeError(f'Failed to find Color element for Label in {identifier} metadata')

            wrap = _optionalConvertToBool(element.get('Wrap'), 'Wrap', 'Label', identifier)
            offsetX = _optionalConvertToFloat(element.get('OffsetX'), 'OffsetX', 'Label', identifier)
            offsetY = _optionalConvertToFloat(element.get('OffsetY'), 'OffsetY', 'Label', identifier)

            labels.append(RawLabel(
                text=text,
                hex=hex,
                colour=colour,
                size=element.get('Size'),
                wrap=wrap,
                offsetX=offsetX,
                offsetY=offsetY,
                fileIndex=index))

    regionElements = sectorElement.get('Regions')
    regions = None
    if regionElements:
        regions = []
        for index, element in enumerate(regionElements):
            path = element.get('Path')
            if path == None:
                raise RuntimeError(f'Failed to find Path element for Region in {identifier} metadata')
            path = path.split(' ')

            showLabel = _optionalConvertToBool(element.get('ShowLabel'), 'ShowLabel', 'Region', identifier)
            wrapLabel = _optionalConvertToBool(element.get('WrapLabel'), 'WrapLabel', 'Region', identifier)
            labelOffsetX = _optionalConvertToFloat(element.get('LabelOffsetX'), 'LabelOffsetX', 'Region', identifier)
            labelOffsetY = _optionalConvertToFloat(element.get('LabelOffsetY'), 'LabelOffsetY', 'Region', identifier)

            regions.append(RawRegion(
                hexList=path,
                showLabel=showLabel,
                wrapLabel=wrapLabel,
                labelHex=element.get('LabelPosition'),
                labelOffsetX=labelOffsetX,
                labelOffsetY=labelOffsetY,
                label=element.get('Label'),
                colour=element.get('Color'),
                fileIndex=index))

    return RawMetadata(
        canonicalName=names[0],
        alternateNames=names[1:],
        nameLanguages=nameLanguages,
        abbreviation=sectorElement.get('Abbreviation'),
        subsectorNames=subsectorNames,
        x=x,
        y=y,
        tags=sectorElement.get('Tags'),
        allegiances=allegiances,
        routes=routes,
        borders=borders,
        labels=labels,
        regions=regions,
        styleSheet=sectorElement.get('StyleSheet'))

def writeMetadata(
        metadata: RawMetadata,
        metadataFormat: MetadataFormat,
        identifier: str
        ) -> bytes:
    if metadataFormat == MetadataFormat.XML:
        return writeXMLMetadata(
            metadata=metadata,
            identifier=identifier)
    elif metadataFormat == MetadataFormat.JSON:
        return writeJSONMetadata(
            metadata=metadata,
            identifier=identifier)
    else:
        raise RuntimeError(f'Unknown metadata format {metadataFormat} for {identifier}')

def writeXMLMetadata(
        metadata: RawMetadata,
        identifier: str
        ) -> bytes:
    sectorAttributes = {}

    # NOTE: The Traveller Map documentation doesn't mention Tags or Abbreviation for the XML
    # format but the XSD does have them
    # https://travellermap.com/doc/metadata
    if metadata.tags() != None:
        sectorAttributes['Tags'] = metadata.tags()

    if metadata.abbreviation() != None:
        sectorAttributes['Abbreviation'] = metadata.abbreviation()

    sectorElement = xml.etree.ElementTree.Element('Sector', sectorAttributes)

    names = [metadata.canonicalName()] + metadata.alternateNames()
    for name in names:
        attributes = {}
        language = metadata.nameLanguage(name)
        if language:
            attributes['Lang'] = language

        nameElement = xml.etree.ElementTree.SubElement(sectorElement, 'Name', attributes)
        nameElement.text = name

    xElement = xml.etree.ElementTree.SubElement(sectorElement, 'X')
    xElement.text = str(metadata.x())

    yElement = xml.etree.ElementTree.SubElement(sectorElement, 'Y')
    yElement.text = str(metadata.y())

    subsectorNames = metadata.subsectorNames()
    if subsectorNames:
        subsectorsElement = xml.etree.ElementTree.SubElement(sectorElement, 'Subsectors')
        for code, name in subsectorNames.items():
            attributes = {'Index': code}
            subsectorElement = xml.etree.ElementTree.SubElement(subsectorsElement, 'Subsector', attributes)
            subsectorElement.text = name

    allegiances = metadata.allegiances()
    if allegiances:
        allegiancesElement = xml.etree.ElementTree.SubElement(sectorElement, 'Allegiances')
        for allegiance in allegiances:
            attributes = {'Code': allegiance.code()}
            if allegiance.base():
                attributes['Base'] = allegiance.base()
            allegianceElement = xml.etree.ElementTree.SubElement(allegiancesElement, 'Allegiance', attributes)
            allegianceElement.text = allegiance.name()

    routes = metadata.routes()
    if routes:
        routesElement = xml.etree.ElementTree.SubElement(sectorElement, 'Routes')
        for route in routes:
            attributes = {
                'Start': route.startHex(),
                'End': route.endHex()}
            if route.startOffsetX() != None:
                attributes['StartOffsetX'] = str(route.startOffsetX())
            if route.startOffsetY() != None:
                attributes['StartOffsetY'] = str(route.startOffsetY())
            if route.endOffsetX() != None:
                attributes['EndOffsetX'] = str(route.endOffsetX())
            if route.endOffsetY() != None:
                attributes['EndOffsetY'] = str(route.endOffsetY())
            if route.allegiance() != None:
                attributes['Allegiance'] = route.allegiance()
            if route.type() != None:
                attributes['Type'] = route.type()
            if route.style() != None:
                attributes['Style'] = route.style()
            if route.colour() != None:
                attributes['Color'] = route.colour()
            if route.width() != None:
                attributes['Width'] = str(route.width())

            xml.etree.ElementTree.SubElement(routesElement, 'Route', attributes)

    borders = metadata.borders()
    if borders:
        bordersElement = xml.etree.ElementTree.SubElement(sectorElement, 'Borders')
        for border in borders:
            attributes = {}
            if border.allegiance() != None:
                attributes['Allegiance'] = border.allegiance()
            if border.showLabel() != None:
                attributes['ShowLabel'] = str(border.showLabel()).lower()
            if border.wrapLabel() != None:
                attributes['WrapLabel'] = str(border.wrapLabel()).lower()
            if border.labelHex() != None:
                attributes['LabelPosition'] = border.labelHex()
            if border.labelOffsetX() != None:
                attributes['LabelOffsetX'] = common.formatNumber(
                    number=border.labelOffsetX(),
                    decimalPlaces=_XmlFloatDecimalPlaces)
            if border.labelOffsetY() != None:
                attributes['LabelOffsetY'] = common.formatNumber(
                    number=border.labelOffsetY(),
                    decimalPlaces=_XmlFloatDecimalPlaces)
            if border.label() != None:
                attributes['Label'] = border.label()
            if border.style() != None:
                attributes['Style'] = border.style()
            if border.colour() != None:
                attributes['Color'] = border.colour()

            borderElement = xml.etree.ElementTree.SubElement(bordersElement, 'Border', attributes)
            borderElement.text = ' '.join(border.hexList())

    labels = metadata.labels()
    if labels:
        labelsElement = xml.etree.ElementTree.SubElement(sectorElement, 'Labels')
        for label in labels:
            attributes = {
                'Hex': label.hex(),
                'Color': label.colour()}
            if label.size() != None:
                attributes['Size'] = label.size()
            if label.wrap() != None:
                attributes['Wrap'] = str(label.wrap()).lower()
            if label.offsetX() != None:
                attributes['OffsetX'] = common.formatNumber(
                    number=label.offsetX(),
                    decimalPlaces=_XmlFloatDecimalPlaces)
            if label.offsetY() != None:
                attributes['OffsetY'] = common.formatNumber(
                    number=label.offsetY(),
                    decimalPlaces=_XmlFloatDecimalPlaces)

            labelElement = xml.etree.ElementTree.SubElement(labelsElement, 'Label', attributes)
            labelElement.text = label.text()

    regions = metadata.regions()
    if regions:
        regionsElement = xml.etree.ElementTree.SubElement(sectorElement, 'Regions')
        for region in regions:
            attributes = {}
            if region.showLabel() != None:
                attributes['ShowLabel'] = str(region.showLabel()).lower()
            if region.wrapLabel() != None:
                attributes['WrapLabel'] = str(region.wrapLabel()).lower()
            if region.labelHex() != None:
                attributes['LabelPosition'] = region.labelHex()
            if region.labelOffsetX() != None:
                attributes['LabelOffsetX'] = common.formatNumber(
                    number=region.labelOffsetX(),
                    decimalPlaces=_XmlFloatDecimalPlaces)
            if region.labelOffsetY() != None:
                attributes['LabelOffsetY'] = common.formatNumber(
                    number=region.labelOffsetY(),
                    decimalPlaces=_XmlFloatDecimalPlaces)
            if region.label() != None:
                attributes['Label'] = region.label()
            if region.colour() != None:
                attributes['Color'] = region.colour()

            regionElement = xml.etree.ElementTree.SubElement(regionsElement, 'Region', attributes)
            regionElement.text = ' '.join(region.hexList())

    if metadata.styleSheet() != None:
        styleSheetElement = xml.etree.ElementTree.SubElement(labelsElement, 'StyleSheet')
        styleSheetElement.text = metadata.styleSheet()

    xml.etree.ElementTree.indent(sectorElement, space="\t", level=0)
    return xml.etree.ElementTree.tostring(
        element=sectorElement,
        encoding='utf-8',
        xml_declaration=True)

def writeJSONMetadata(
        metadata: RawMetadata,
        identifier: str
        ) -> bytes:
    sectorElement = {}

    if metadata.tags() != None:
        sectorElement['Tags'] = metadata.tags()

    if metadata.abbreviation() != None:
        sectorElement['Abbreviation'] = metadata.abbreviation()

    namesElement = []
    sectorElement['Names'] = namesElement

    names = [metadata.canonicalName()] + metadata.alternateNames()
    for name in names:
        nameElement = {'Text': name}
        language = metadata.nameLanguage(name)
        if language:
            nameElement['Lang'] = language
        namesElement.append(nameElement)

    sectorElement['X'] = str(metadata.x())
    sectorElement['Y'] = str(metadata.y())

    subsectorNames = metadata.subsectorNames()
    if subsectorNames:
        subsectorsElement = []
        sectorElement['Subsectors'] = subsectorsElement
        for code, name in subsectorNames.items():
            subsectorElement = {
                'Name': name,
                'Index': code,
                'IndexNumber': ord(code) - ord('A')}
            subsectorsElement.append(subsectorElement)

    allegiances = metadata.allegiances()
    if allegiances:
        allegiancesElement = []
        sectorElement['Allegiances'] = allegiancesElement
        for allegiance in allegiances:
            allegianceElement = {
                'Name': allegiance.name(),
                'Code': allegiance.code()}
            if allegiance.base():
                allegianceElement['Base'] = allegiance.base()
            allegiancesElement.append(allegianceElement)

    routes = metadata.routes()
    if routes:
        routesElement = []
        sectorElement['Routes'] = routesElement
        for route in routes:
            routeElement = {
                'Start': route.startHex(),
                'End': route.endHex()}
            if route.startOffsetX() != None:
                routeElement['StartOffsetX'] = route.startOffsetX()
            if route.startOffsetY() != None:
                routeElement['StartOffsetY'] = route.startOffsetY()
            if route.endOffsetX() != None:
                routeElement['EndOffsetX'] = route.endOffsetX()
            if route.endOffsetY() != None:
                routeElement['EndOffsetY'] = route.endOffsetY()
            if route.allegiance() != None:
                routeElement['Allegiance'] = route.allegiance()
            if route.type() != None:
                routeElement['Type'] = route.type()
            if route.style() != None:
                routeElement['Style'] = route.style()
            if route.colour() != None:
                routeElement['Color'] = route.colour()
            if route.width() != None:
                routeElement['Width'] = route.width()

            routesElement.append(routeElement)

    borders = metadata.borders()
    if borders:
        bordersElement = []
        sectorElement['Borders'] = bordersElement
        for border in borders:
            borderElement = {'Path': ' '.join(border.hexList())}
            if border.allegiance() != None:
                borderElement['Allegiance'] = border.allegiance()
            if border.showLabel() != None:
                borderElement['ShowLabel'] = border.showLabel()
            if border.wrapLabel() != None:
                borderElement['WrapLabel'] = border.wrapLabel()
            if border.labelHex() != None:
                borderElement['LabelPosition'] = border.labelHex()
            if border.labelOffsetX() != None:
                borderElement['LabelOffsetX'] = border.labelOffsetX()
            if border.labelOffsetY() != None:
                borderElement['LabelOffsetY'] = border.labelOffsetY()
            if border.label() != None:
                borderElement['Label'] = border.label()
            if border.style() != None:
                borderElement['Style'] = border.style()
            if border.colour() != None:
                borderElement['Color'] = border.colour()

            bordersElement.append(borderElement)

    labels = metadata.labels()
    if labels:
        labelsElement = []
        sectorElement['Labels'] = labelsElement
        for label in labels:
            labelElement = {
                'Text': label.text(),
                'Hex': label.hex(),
                'Color': label.colour()}
            if label.size() != None:
                labelElement['Size'] = label.size()
            if label.wrap() != None:
                labelElement['Wrap'] = label.wrap()
            if label.offsetX() != None:
                labelElement['OffsetX'] = label.offsetX()
            if label.offsetY() != None:
                labelElement['OffsetY'] = label.offsetY()

            labelsElement.append(labelsElement)

    regions = metadata.regions()
    if regions:
        regionsElement = []
        sectorElement['Regions'] = regionsElement
        for region in regions:
            regionElement = {'Path': ' '.join(region.hexList())}
            if region.showLabel() != None:
                regionElement['ShowLabel'] = region.showLabel()
            if region.wrapLabel() != None:
                regionElement['WrapLabel'] = region.wrapLabel()
            if region.labelHex() != None:
                regionElement['LabelPosition'] = region.labelHex()
            if region.labelOffsetX() != None:
                regionElement['LabelOffsetX'] = region.labelOffsetX()
            if region.labelOffsetY() != None:
                regionElement['LabelOffsetY'] = region.labelOffsetY()
            if region.label() != None:
                regionElement['Label'] = region.label()
            if region.colour() != None:
                regionElement['Color'] = region.colour()

            regionsElement.append(regionElement)

    # NOTE: The JSON metadata returned by Traveller Map doesn't include
    # style sheet information
    """
    if metadata.styleSheet() != None:
        sectorElement['StyleSheet'] = metadata.styleSheet()
    """

    return json.dumps(sectorElement, indent=4)
