import enum
import itertools
import json
import logging
import re
import typing
import xml.etree.ElementTree

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

class WorldData(object):
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

# TODO: When I switch to loading subsector names and allegiances from the metadata files I
# can remove the SectorData class and have the parsers just return a list of WorldData
class SectorData(object):
    def __init__(self) -> None:
        self._subsectorNames: typing.Dict[str, str] = {}
        self._allegiances: typing.Dict[str, str] = {}
        self._worlds: typing.List[WorldData] = []

    def subsectorNames(self) -> typing.Mapping[str, str]:
        return self._subsectorNames

    def addSubsectorName(
            self,
            code: str,
            name: str
            ) -> None:
        self._subsectorNames[code] = name

    def allegiances(self) -> typing.Mapping[str, str]:
        return self._allegiances

    def addAllegiance(
            self,
            code: str,
            name: str
            ) -> None:
        self._allegiances[code] = name

    def worlds(self) -> typing.Iterable[WorldData]:
        return self._worlds

    def addWorld(self, world: WorldData) -> None:
        self._worlds.append(world)

_HeaderPattern = re.compile('(?:([\w{}()\[\]]+)\s*)')
_SeparatorPattern = re.compile('(?:([-]+)\s?)')
_SubsectorPattern = re.compile('#\s*Subsector ([a-pA-P]{1}): (.+)')
_AllegiancePattern = re.compile('#\s*Alleg: (\S+): ["?](.+)["?]')
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

def parseSector(
        content: str,
        fileFormat: SectorFormat,
        identifier: str, # File name or some other identifier, used for logging and error generation
        ) -> SectorData:
    if fileFormat == SectorFormat.T5Column:
        return parseT5ColumnSector(
            content=content,
            identifier=identifier)
    elif fileFormat == SectorFormat.T5Tab:
        return parseT5RowSector(
            content=content,
            identifier=identifier)
    else:
        raise RuntimeError(f'Unknown sector format {fileFormat} for {identifier}')
    
def parseT5ColumnSector(
        content: str,
        identifier: str
        ) -> SectorData:
    sectorData = SectorData()
    columnNames = None
    columnAttributes = None
    columnWidths = None
    for lineNumber, line in enumerate(content.splitlines()):
        if not line:
            # Ignore empty lines
            continue
        if line[:1] == '#':
            match = _SubsectorPattern.match(line)
            if match:
                code = match[1]
                name = match[2]
                sectorData.addSubsectorName(
                    code=code,
                    name=name)
                continue

            match = _AllegiancePattern.match(line)
            if match:
                code = match[1]
                name = match[2]
                # Ignore allegiances made up completely of '-' as we strip those out of the
                # world data when reading it
                if not all(ch == '-' for ch in code):
                    sectorData.addAllegiance(
                        code=code,
                        name=name)
                continue

            # Ignore other comments
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
            sectorData.addWorld(
                world=_parseT5ColumnWorld(
                    line=line,
                    lineNumber=lineNumber,
                    columnAttributes=columnAttributes,
                    columnWidths=columnWidths))
        except Exception as ex:
            logging.debug(
                f'Failed parse world on line {lineNumber} in data for {identifier} ({str(ex)})')            
            continue
    return sectorData

def _parseT5ColumnWorld(
        line: str,
        lineNumber: int,
        columnAttributes: typing.Iterable[WorldAttribute],
        columnWidths: typing.Iterable[int]
        ) -> WorldData:
    worldData = WorldData(lineNumber=lineNumber)
    lineLength = len(line)
    startIndex = 0
    finishIndex = 0
    for attribute, width in itertools.zip_longest(columnAttributes, columnWidths):
        if startIndex >= lineLength:
            raise RuntimeError('Line is to short')

        finishIndex = startIndex + width
        if attribute != None:
            data = line[startIndex:finishIndex].strip()
            if data and all(ch == '-' for ch in data):
                # Replace no data marker with empty string
                data = ''
            worldData.setAttribute(
                attribute=attribute,
                value=data)
        startIndex = finishIndex + 1
    return worldData

def parseT5RowSector(
        content: str,
        identifier: str
        ) -> SectorData:
    sectorData = SectorData()
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
            sectorData.addWorld(
                world=_parseT5RowWorld(
                    line=line,
                    lineNumber=lineNumber,
                    columnAttributes=columnAttributes))
        except Exception as ex:
            logging.debug(
                f'Failed parse world on line {lineNumber} in data for {identifier} ({str(ex)})')            
            continue
    return sectorData

def _parseT5RowWorld(
        line: str,
        lineNumber: int,
        columnAttributes: typing.Iterable[WorldAttribute],
        ) -> typing.Optional[SectorData]:
    columnData = line.split('\t')
    if len(columnData) != len(columnAttributes):
        raise RuntimeError('Line has incorrect number of columns')
    
    worldData = WorldData(lineNumber=lineNumber)
    for attribute, data in itertools.zip_longest(columnAttributes, columnData):
        worldData.setAttribute(
            attribute=attribute,
            value=data)
    return worldData