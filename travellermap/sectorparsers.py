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
            tags: typing.Optional[typing.Iterable[str]],
            allegiances: typing.Optional[typing.Mapping[str, str]], # Maps allegiance code to the name of the allegiance
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

    def tags(self) -> typing.Optional[typing.Iterable[str]]:
        return list(self._tags) if self._tags else None

    def allegiances(self) -> typing.Optional[typing.Mapping[str, str]]:
        return self._allegiances

_HeaderPattern = re.compile('(?:([\w{}()\[\]]+)\s*)')
_SeparatorPattern = re.compile('(?:([-]+)\s?)')
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
        ) -> typing.Iterable[RawWorld]:
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
            worlds.append(_parseT5ColumnWorld(
                line=line,
                lineNumber=lineNumber,
                columnAttributes=columnAttributes,
                columnWidths=columnWidths))
        except Exception as ex:
            logging.debug(
                f'Failed parse world on line {lineNumber} in data for {identifier} ({str(ex)})')            
            continue
    return worlds

def _parseT5ColumnWorld(
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
            # TODO: If I'm trying to keep this code as a faithful representation of the contents
            # of the file then this code should be moved into somewhere higher level such as
            # WorldManager            
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
            worlds.append(_parseT5RowWorld(
                line=line,
                lineNumber=lineNumber,
                columnAttributes=columnAttributes))
        except Exception as ex:
            logging.debug(
                f'Failed parse world on line {lineNumber} in data for {identifier} ({str(ex)})')            
            continue
    return worlds

def _parseT5RowWorld(
        line: str,
        lineNumber: int,
        columnAttributes: typing.Iterable[WorldAttribute],
        ) -> RawWorld:
    columnData = line.split('\t')
    if len(columnData) != len(columnAttributes):
        raise RuntimeError('Line has incorrect number of columns')
    
    worldData = RawWorld(lineNumber=lineNumber)
    for attribute, data in itertools.zip_longest(columnAttributes, columnData):
        worldData.setAttribute(
            attribute=attribute,
            value=data)
    return worldData

def parseMetadata(
        content: str,
        metadataFormat: MetadataFormat,
        identifier: str
        ) -> RawMetadata:
    if metadataFormat == MetadataFormat.XML:
        return parseXMLMetadata(
            content=content,
            identifier=identifier)
    elif metadataFormat == MetadataFormat.JSON:
        return parseJSONMetadata(
            content=content,
            identifier=identifier)
    else:
        raise RuntimeError(f'Unknown metadata format {metadataFormat} for {identifier}')

def parseXMLMetadata(
        content: str,
        identifier: str
        ) -> RawMetadata:
    root = xml.etree.ElementTree.fromstring(content)

    nameElements = root.findall('./Name')
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

    xElement = root.find('./X')
    if xElement == None:
        raise RuntimeError(f'Failed to find X element in {identifier} metadata')
    x = int(xElement.text)
    
    yElement = root.find('./Y')
    if yElement == None:
        raise RuntimeError(f'Failed to find Y element in {identifier} metadata')
    y = int(yElement.text)

    subsectorNames = {}
    for element in root.findall('./Subsectors/Subsector'):
        code = element.get('Index')
        if not code:
            # TODO: Log something???
            continue
        # TODO: Should probably validate that code is in range A-P
        subsectorNames[code] = element.text

    # TODO: Allegiances have an additional 'Base' attribute that I'm not doing anything
    # with at the moment, not sure what it's used for
    allegiances = {}
    for element in root.findall('./Allegiances/Allegiance'):
        code = element.get('Code')
        if not code:
            # TODO: Log something???
            continue
        allegiances[code] = element.text

    return RawMetadata(
        canonicalName=names[0],
        alternateNames=names[1:],
        nameLanguages=nameLanguages,
        abbreviation=root.get('Abbreviation'),
        subsectorNames=subsectorNames,
        x=x,
        y=y,
        tags=root.get('Tags'),
        allegiances=allegiances)

def parseJSONMetadata(
        content: str,
        identifier: str
        ) -> RawMetadata:
    root = json.loads(content)
    
    nameElements = root.get('Names')
    if not nameElements:
        raise RuntimeError(f'Failed to find Names element in {identifier} metadata')

    names = []
    nameLanguages = {}
    for element in nameElements:
        name = element.get('Text')
        if not name:
            # TODO: Log something????
            continue
        names.append(name)

        lang = element.get('Lang')
        if lang:
            nameLanguages[name] = lang
    
    x = root.get('X')
    if x == None:
        raise RuntimeError(f'Failed to find X element in {identifier} metadata')
    x = int(x)

    y = root.get('Y')
    if y == None:
        raise RuntimeError(f'Failed to find Y element in {identifier} metadata')
    y = int(y)

    subsectorElements = root.get('Subsectors')
    subsectorNames = {}
    if subsectorElements:
        for element in subsectorElements:
            name = element.get('Name')
            if not name:
                # TODO: Log something?????
                continue
            code = element.get('Index')
            if not code:
                # TODO: Log something?????
                continue
            # TODO: Should probably validate that code is in range A-P
            subsectorNames[code] = name

    # TODO: Allegiances have an additional 'Base' attribute that I'm not doing anything
    # with at the moment, not sure what it's used for
    allegianceElements = root.get('Allegiances')
    allegiances = {}
    if allegianceElements:
        for element in allegianceElements:
            name = element.get('Name')
            if not name:
                # TODO: Log something?????
                continue
            code = element.get('Code')
            if not code:
                # TODO: Log something?????
                continue
            # TODO: Should probably validate that code is in range A-P
            allegiances[code] = name
    
    return RawMetadata(
        canonicalName=names[0],
        alternateNames=names[1:],
        nameLanguages=nameLanguages,
        abbreviation=root.get('Abbreviation'),
        subsectorNames=subsectorNames,
        x=x,
        y=y,
        tags=root.get('Tags'),
        allegiances=allegiances)