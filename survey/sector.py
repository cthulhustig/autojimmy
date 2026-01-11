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
_T5Row_ColumnNameToAttributeMap = {
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
        return parseT5RowSector(content=content)

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
                lineNumber=lineNumber,
                columnAttributes=columnAttributes,
                columnWidths=columnWidths))
        except Exception as ex:
            logging.warning(
                f'Failed parse world on sector file {lineNumber} ({str(ex)})')
            continue
    return worlds

def _parseT5ColumnWorld(
        line: str,
        lineNumber: int,
        columnAttributes: typing.Collection[_WorldAttribute],
        columnWidths: typing.Collection[int]
        ) -> survey.RawWorld:
    attributes: typing.Dict[_WorldAttribute, typing.Optional[str]] = {}
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
            attributes[attribute] = data
        startIndex = finishIndex + 1

    return survey.RawWorld(
        hex=attributes.get(_WorldAttribute.Hex),
        name=attributes.get(_WorldAttribute.Name),
        allegiance=attributes.get(_WorldAttribute.Allegiance),
        zone=attributes.get(_WorldAttribute.Zone),
        uwp=attributes.get(_WorldAttribute.UWP),
        economics=attributes.get(_WorldAttribute.Economics),
        culture=attributes.get(_WorldAttribute.Culture),
        nobility=attributes.get(_WorldAttribute.Nobility),
        bases=attributes.get(_WorldAttribute.Bases),
        remarks=attributes.get(_WorldAttribute.Remarks),
        importance=attributes.get(_WorldAttribute.Importance),
        pbg=attributes.get(_WorldAttribute.PBG),
        systemWorlds=attributes.get(_WorldAttribute.SystemWorlds),
        stellar=attributes.get(_WorldAttribute.Stellar),
        lineNumber=lineNumber)

def parseT5RowSector(content: str) -> typing.Collection[survey.RawWorld]:
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
                    f'Skipping bogus header on sector file line {lineNumber}')
                columnNames = None
                continue

            # Check that mandatory columns are present
            for columnName in _T5Row_ColumnNameToAttributeMap.keys():
                if columnName not in columnNames:
                    raise RuntimeError(
                        f'Unable to load data from sector file (Header is missing {columnName} column)')

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
            logging.warning(
                f'Failed parse world on sector file line {lineNumber} ({str(ex)})')
            continue
    return worlds

def _parseT5RowWorld(
        line: str,
        lineNumber: int,
        columnAttributes: typing.Collection[_WorldAttribute],
        ) -> survey.RawWorld:
    columnData = line.split('\t')
    if len(columnData) != len(columnAttributes):
        raise RuntimeError('Line has incorrect number of columns')

    attributes: typing.Dict[_WorldAttribute, typing.Optional[str]] = {}
    for attribute, data in itertools.zip_longest(columnAttributes, columnData):
        if data and _isAllDashes(data):
            data = '' # Replace no data marker with empty string
        attributes[attribute] = data

    return survey.RawWorld(
        hex=attributes.get(_WorldAttribute.Hex),
        name=attributes.get(_WorldAttribute.Name),
        allegiance=attributes.get(_WorldAttribute.Allegiance),
        zone=attributes.get(_WorldAttribute.Zone),
        uwp=attributes.get(_WorldAttribute.UWP),
        economics=attributes.get(_WorldAttribute.Economics),
        culture=attributes.get(_WorldAttribute.Culture),
        nobility=attributes.get(_WorldAttribute.Nobility),
        bases=attributes.get(_WorldAttribute.Bases),
        remarks=attributes.get(_WorldAttribute.Remarks),
        importance=attributes.get(_WorldAttribute.Importance),
        pbg=attributes.get(_WorldAttribute.PBG),
        systemWorlds=attributes.get(_WorldAttribute.SystemWorlds),
        stellar=attributes.get(_WorldAttribute.Stellar),
        lineNumber=lineNumber)

def _worldAttribute(
        world: survey.RawWorld,
        attribute: _WorldAttribute
        ) -> typing.Optional[str]:
    if attribute is _WorldAttribute.Hex:
        return world.hex()
    elif attribute is _WorldAttribute.Name:
        return world.name()
    elif attribute is _WorldAttribute.UWP:
        return world.uwp()
    elif attribute is _WorldAttribute.Remarks:
        return world.remarks()
    elif attribute is _WorldAttribute.Importance:
        return world.importance()
    elif attribute is _WorldAttribute.Economics:
        return world.economics()
    elif attribute is _WorldAttribute.Culture:
        return world.culture()
    elif attribute is _WorldAttribute.Nobility:
        return world.nobility()
    elif attribute is _WorldAttribute.Bases:
        return world.bases()
    elif attribute is _WorldAttribute.Zone:
        return world.zone()
    elif attribute is _WorldAttribute.PBG:
        return world.pbg()
    elif attribute is _WorldAttribute.SystemWorlds:
        return world.systemWorlds()
    elif attribute is _WorldAttribute.Allegiance:
        return world.allegiance()
    elif attribute is _WorldAttribute.Stellar:
        return world.stellar()

    raise ValueError(f'Unknown world attribute {attribute}')

def formatSector(
        worlds: typing.Collection[survey.RawWorld],
        format: SectorFormat
        ) -> str:
    if format is SectorFormat.T5Column:
        return formatT5ColumnSector(worlds)
    elif format is SectorFormat.T5Tab:
        return formatT5RowSector(worlds)

    raise RuntimeError(f'Unknown sector format {format}')

def formatT5ColumnSector(worlds: typing.Collection[survey.RawWorld]) -> str:
    content = ''

    maxColumnLengths = {}
    for columnName, columnAttribute in _T5Column_ColumnNameToAttributeMap.items():
        maxLength = 0
        if worlds:
            maxLength = max([len(
                _worldAttribute(world=w, attribute=columnAttribute)) for w in worlds])
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

    if worlds:
        for world in worlds:
            values = []
            for columnName, columnAttribute in _T5Column_ColumnNameToAttributeMap.items():
                value = _worldAttribute(world=world, attribute=columnAttribute)
                maxLength = maxColumnLengths[columnName]
                value += ' ' * (maxLength - len(value))
                values.append(value)
            content += ' '.join(values) + '\n'

    return content

# TODO: What this is generating isn't valid as T5 Row has extra columns
# (e.g. Sector or SS for Subsector) which my raw format doesn't have as
# I don't need it
def formatT5RowSector(worlds: typing.Collection[survey.RawWorld]) -> str:
    content = ''

    content += '\t'.join(_T5Row_ColumnNameToAttributeMap.keys())

    if worlds:
        for world in worlds:
            values = []
            for columnAttribute in _T5Row_ColumnNameToAttributeMap.values():
                value = _worldAttribute(world=world, attribute=columnAttribute)
                values.append(value.replace('\t', '\\t'))
            content += '\t'.join(values) + '\n'

    return content
