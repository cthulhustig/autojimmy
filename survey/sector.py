import enum
import itertools
import logging
import re
import survey
import typing

class SectorFormat(enum.Enum):
    T5Column = 0, # aka Second Survey format
    T5Tab = 1

class _WorldAttribute(enum.Enum):
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
    # NOTE: The Traveller Map file format documentation says the following
    # columns are optional
    # https://travellermap.com/doc/fileformats
    SectorAbbreviation = 14
    SubSectorCode = 15
    ResourceUnits = 16

_HeaderPattern = re.compile(r'(?:([\w{}()\[\]]+)\s*)')
_SeparatorPattern = re.compile(r'(?:([-]+)\s?)')

_T5Column_ColumnNameToAttributeMap = {
    'Name': _WorldAttribute.Name,
    'Hex': _WorldAttribute.Hex,
    'UWP': _WorldAttribute.UWP,
    'B': _WorldAttribute.Bases,
    'Remarks': _WorldAttribute.Remarks,
    'Z': _WorldAttribute.Zone,
    'PBG': _WorldAttribute.PBG,
    'A': _WorldAttribute.Allegiance,
    '{Ix}': _WorldAttribute.Importance,
    '(Ex)': _WorldAttribute.Economics,
    '[Cx]': _WorldAttribute.Culture,
    'N': _WorldAttribute.Nobility,
    'W': _WorldAttribute.SystemWorlds,
    'Stellar': _WorldAttribute.Stellar
}

_T5Tab_MandatoryColumnNameToAttributeMap = {
    'Hex': _WorldAttribute.Hex,
    'Name': _WorldAttribute.Name,
    'UWP': _WorldAttribute.UWP,
    'Remarks': _WorldAttribute.Remarks,
    '{Ix}': _WorldAttribute.Importance,
    '(Ex)': _WorldAttribute.Economics,
    '[Cx]': _WorldAttribute.Culture,
    'Nobility': _WorldAttribute.Nobility,
    'Bases': _WorldAttribute.Bases,
    'Zone': _WorldAttribute.Zone,
    'PBG': _WorldAttribute.PBG,
    'W': _WorldAttribute.SystemWorlds,
    'Allegiance': _WorldAttribute.Allegiance,
    'Stars': _WorldAttribute.Stellar
}
_T5Tab_OptionalColumnNameToAttributeMap = {
    'Sector': _WorldAttribute.SectorAbbreviation,
    'SS': _WorldAttribute.SubSectorCode,
    'RU': _WorldAttribute.ResourceUnits
}
_T5Tab_ColumnNameToAttributeMap = _T5Tab_MandatoryColumnNameToAttributeMap | _T5Tab_OptionalColumnNameToAttributeMap

_WorldAttributeAccessMap: typing.Dict[_WorldAttribute, typing.Callable[[survey.RawWorld], typing.Optional[str]]] = {
    _WorldAttribute.Hex: lambda world: world.hex(),
    _WorldAttribute.Name: lambda world: world.name(),
    _WorldAttribute.UWP: lambda world: world.uwp(),
    _WorldAttribute.Remarks: lambda world: world.remarks(),
    _WorldAttribute.Importance: lambda world: world.importance(),
    _WorldAttribute.Economics: lambda world: world.economics(),
    _WorldAttribute.Culture: lambda world: world.culture(),
    _WorldAttribute.Nobility: lambda world: world.nobility(),
    _WorldAttribute.Bases: lambda world: world.bases(),
    _WorldAttribute.Zone: lambda world: world.zone(),
    _WorldAttribute.PBG: lambda world: world.pbg(),
    _WorldAttribute.SystemWorlds: lambda world: world.systemWorlds(),
    _WorldAttribute.Allegiance: lambda world: world.allegiance(),
    _WorldAttribute.Stellar: lambda world: world.stellar(),
    _WorldAttribute.SectorAbbreviation: lambda world: world.sectorAbbreviation(),
    _WorldAttribute.SubSectorCode: lambda world: world.subSectorCode(),
    _WorldAttribute.ResourceUnits: lambda world: world.resourceUnits(),
}

def _isAllDashes(string: str) -> bool:
    if not string:
        return False # Empty string isn't all dashes
    for c in string:
        if c != '-':
            return False
    return True

def detectSectorFormat(content: str) -> typing.Optional[SectorFormat]:
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
        format: typing.Optional[SectorFormat] = None
        ) -> typing.Collection[survey.RawWorld]:
    if format is None:
        format = detectSectorFormat(content=content)
        if format is None:
            raise ValueError('Unable to detect sector format')

    if format == SectorFormat.T5Column:
        return parseT5ColumnSector(content=content)
    elif format == SectorFormat.T5Tab:
        return parseT5TabSector(content=content)

    raise RuntimeError(f'Unknown sector format {format}')

def parseT5ColumnSector(content: str) -> typing.Collection[survey.RawWorld]:
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
                    f'Skipping bogus header on sector file line {lineNumber}')
                columnNames = None
                continue

            # Check that mandatory columns are present
            for columnName in _T5Column_ColumnNameToAttributeMap.keys():
                if columnName not in columnNames:
                    raise RuntimeError(
                        f'Unable to load data from sector file (Header is missing {columnName} column)')

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
                    f'Unable to load data from sector file (Header column count doesn\'t match separator column count)')

            columnWidths = []
            for columnSeparator in separators:
                columnWidths.append(len(columnSeparator))
            continue

        # Parse the line as a world definition
        try:
            worlds.append(_parseT5ColumnWorld(
                line=line,
                columnAttributes=columnAttributes,
                columnWidths=columnWidths))
        except Exception as ex:
            logging.warning(
                f'Failed parse world on sector file {lineNumber} ({str(ex)})')
            continue
    return worlds

def _parseT5ColumnWorld(
        line: str,
        columnAttributes: typing.Collection[_WorldAttribute],
        columnWidths: typing.Collection[int]
        ) -> survey.RawWorld:
    lineLength = len(line)
    startIndex = 0
    finishIndex = 0
    valueMap: typing.Dict[_WorldAttribute, typing.Optional[str]] = {}
    for attribute, width in itertools.zip_longest(columnAttributes, columnWidths):
        if startIndex >= lineLength:
            raise RuntimeError('Line is to short')

        finishIndex = startIndex + width
        if attribute != None:
            data = line[startIndex:finishIndex].strip()
            if data and _isAllDashes(data):
                data = '' # Replace no data marker with empty string
            valueMap[attribute] = data
        startIndex = finishIndex + 1

    return survey.RawWorld(
        hex=valueMap.get(_WorldAttribute.Hex),
        name=valueMap.get(_WorldAttribute.Name),
        allegiance=valueMap.get(_WorldAttribute.Allegiance),
        zone=valueMap.get(_WorldAttribute.Zone),
        uwp=valueMap.get(_WorldAttribute.UWP),
        economics=valueMap.get(_WorldAttribute.Economics),
        culture=valueMap.get(_WorldAttribute.Culture),
        nobility=valueMap.get(_WorldAttribute.Nobility),
        bases=valueMap.get(_WorldAttribute.Bases),
        remarks=valueMap.get(_WorldAttribute.Remarks),
        importance=valueMap.get(_WorldAttribute.Importance),
        pbg=valueMap.get(_WorldAttribute.PBG),
        systemWorlds=valueMap.get(_WorldAttribute.SystemWorlds),
        stellar=valueMap.get(_WorldAttribute.Stellar),
        # Optional attributes not supported by T5 column format
        sectorAbbreviation=None,
        subSectorCode=None,
        resourceUnits=None)

def parseT5TabSector(content: str) -> typing.Collection[survey.RawWorld]:
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
            if len(columnNames) < len(_T5Tab_MandatoryColumnNameToAttributeMap):
                # This is needed as some sectors (notably Shadow Rift) are off format and have
                # broken comments that don't start with #. This gets logged at a low level so
                # we don't spam the logs every time we start
                logging.debug(
                    f'Skipping bogus header on sector file line {lineNumber}')
                columnNames = None
                continue

            # Check that mandatory columns are present
            for columnName in _T5Tab_MandatoryColumnNameToAttributeMap.keys():
                if columnName not in columnNames:
                    raise RuntimeError(
                        f'Unable to load data from sector file (Header is missing {columnName} column)')

            # Convert column names to list of column attributes with None for unknown columns
            columnAttributes = []
            for columnName in columnNames:
                attribute = _T5Tab_ColumnNameToAttributeMap.get(columnName)
                columnAttributes.append(attribute)
            continue

        # Parse the line as a world definition
        try:
            worlds.append(_parseT5TabWorld(
                line=line,
                columnAttributes=columnAttributes))
        except Exception as ex:
            logging.warning(
                f'Failed parse world on sector file line {lineNumber} ({str(ex)})')
            continue
    return worlds

def _parseT5TabWorld(
        line: str,
        columnAttributes: typing.Collection[_WorldAttribute],
        ) -> survey.RawWorld:
    columnData = line.split('\t')
    valueMap: typing.Dict[_WorldAttribute, typing.Optional[str]] = {}
    for index, attribute in enumerate(columnAttributes):
        if attribute is None:
            continue
        if index >= len(columnData):
            # There are less columns for this world than defined in the header.
            # I think this is technically invalid but we can handle by just
            # treating that data as unspecified (as it would if the column
            # wasn't defined in the header). Having to fill in blank tabs is a
            # pain in the ass and error prone so I can see it being wrong in a
            # lot of files that are otherwise valid.
            break
        if data and _isAllDashes(data):
            data = '' # Replace no data marker with empty string
        valueMap[attribute] = data

    return survey.RawWorld(
        hex=valueMap.get(_WorldAttribute.Hex),
        name=valueMap.get(_WorldAttribute.Name),
        allegiance=valueMap.get(_WorldAttribute.Allegiance),
        zone=valueMap.get(_WorldAttribute.Zone),
        uwp=valueMap.get(_WorldAttribute.UWP),
        economics=valueMap.get(_WorldAttribute.Economics),
        culture=valueMap.get(_WorldAttribute.Culture),
        nobility=valueMap.get(_WorldAttribute.Nobility),
        bases=valueMap.get(_WorldAttribute.Bases),
        remarks=valueMap.get(_WorldAttribute.Remarks),
        importance=valueMap.get(_WorldAttribute.Importance),
        pbg=valueMap.get(_WorldAttribute.PBG),
        systemWorlds=valueMap.get(_WorldAttribute.SystemWorlds),
        stellar=valueMap.get(_WorldAttribute.Stellar),
        sectorAbbreviation=valueMap.get(_WorldAttribute.SectorAbbreviation),
        subSectorCode=valueMap.get(_WorldAttribute.SubSectorCode),
        resourceUnits=valueMap.get(_WorldAttribute.ResourceUnits))

_worldAttributeCharMap = str.maketrans({'\t': ' ', '\n': ' '})
def _worldAttribute(
        world: survey.RawWorld,
        attribute: _WorldAttribute,
        default: typing.Any
        ) -> str:
    accessFn = _WorldAttributeAccessMap.get(attribute)
    if not accessFn:
        raise ValueError(f'Unknown world attribute {attribute}')

    value = accessFn(world)
    if value is None:
        return default
    return value.translate(_worldAttributeCharMap)

def formatSector(
        worlds: typing.Collection[survey.RawWorld],
        format: SectorFormat
        ) -> str:
    if format is SectorFormat.T5Column:
        return formatT5ColumnSector(worlds)
    elif format is SectorFormat.T5Tab:
        return formatT5TabSector(worlds)

    raise RuntimeError(f'Unknown sector format {format}')

def formatT5ColumnSector(worlds: typing.Collection[survey.RawWorld]) -> str:
    content = ''

    maxColumnLengths = {}
    for columnName, columnAttribute in _T5Column_ColumnNameToAttributeMap.items():
        maxLength = 0
        if worlds:
            maxLength = max([len(
                _worldAttribute(world=w, attribute=columnAttribute, default='')) for w in worlds])
            if columnAttribute is _WorldAttribute.Name or \
                columnAttribute is _WorldAttribute.Remarks:
                # For some reason Traveller Map adds an extra space separation for sector
                # name and remarks. I've replicated this to make diffing files easier
                maxLength += 1
        if len(columnName) > maxLength:
            maxLength = len(columnName)
        maxColumnLengths[columnName] = maxLength

    columns = []
    separators = []
    for columnName in _T5Column_ColumnNameToAttributeMap.keys():
        maxLength = maxColumnLengths[columnName]
        padding = maxLength - len(columnName)
        columns.append(columnName + (' ' * padding))
        separators.append('-' * maxLength)

    content += ' '.join(columns) + '\n'
    content += ' '.join(separators) + '\n'

    for world in worlds:
        values = []
        for columnName, columnAttribute in _T5Column_ColumnNameToAttributeMap.items():
            value = _worldAttribute(world=world, attribute=columnAttribute, default='')
            maxLength = maxColumnLengths[columnName]
            value += ' ' * (maxLength - len(value))
            values.append(value)
        content += ' '.join(values) + '\n'

    return content

def formatT5TabSector(worlds: typing.Collection[survey.RawWorld]) -> str:
    outputColumns = dict(_T5Tab_MandatoryColumnNameToAttributeMap)
    for columnName, columnAttribute in _T5Tab_OptionalColumnNameToAttributeMap:
        for world in worlds:
            value = _worldAttribute(world=world, attribute=columnAttribute, default=None)
            if value is not None:
                outputColumns[columnName] = columnAttribute
                break

    content = '\t'.join(outputColumns.keys())

    for world in worlds:
        values = []
        for columnAttribute in outputColumns.values():
            value = _worldAttribute(world=world, attribute=columnAttribute, default='')
            values.append(value)
        content += '\t'.join(values) + '\n'

    return content
