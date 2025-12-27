import enum
import itertools
import logging
import re
import survey
import typing

class SectorFormat(enum.Enum):
    T5Column = 0, # aka Second Survey format
    T5Tab = 1

_HeaderPattern = re.compile(r'(?:([\w{}()\[\]]+)\s*)')
_SeparatorPattern = re.compile(r'(?:([-]+)\s?)')
_T5Column_ColumnNameToAttributeMap = {
    'Name': survey.WorldAttribute.Name,
    'Hex': survey.WorldAttribute.Hex,
    'UWP': survey.WorldAttribute.UWP,
    'B': survey.WorldAttribute.Bases,
    'Remarks': survey.WorldAttribute.Remarks,
    'Z': survey.WorldAttribute.Zone,
    'PBG': survey.WorldAttribute.PBG,
    'A': survey.WorldAttribute.Allegiance,
    '{Ix}': survey.WorldAttribute.Importance,
    '(Ex)': survey.WorldAttribute.Economics,
    '[Cx]': survey.WorldAttribute.Culture,
    'N': survey.WorldAttribute.Nobility,
    'W': survey.WorldAttribute.SystemWorlds,
    'Stellar': survey.WorldAttribute.Stellar
}
_T5Row_ColumnNameToAttributeMap = {
    'Hex': survey.WorldAttribute.Hex,
    'Name': survey.WorldAttribute.Name,
    'UWP': survey.WorldAttribute.UWP,
    'Remarks': survey.WorldAttribute.Remarks,
    '{Ix}': survey.WorldAttribute.Importance,
    '(Ex)': survey.WorldAttribute.Economics,
    '[Cx]': survey.WorldAttribute.Culture,
    'Nobility': survey.WorldAttribute.Nobility,
    'Bases': survey.WorldAttribute.Bases,
    'Zone': survey.WorldAttribute.Zone,
    'PBG': survey.WorldAttribute.PBG,
    'W': survey.WorldAttribute.SystemWorlds,
    'Allegiance': survey.WorldAttribute.Allegiance,
    'Stars': survey.WorldAttribute.Stellar
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
        columnAttributes: typing.Collection[survey.WorldAttribute],
        columnWidths: typing.Collection[int]
        ) -> survey.RawWorld:
    worldData = survey.RawWorld(lineNumber=lineNumber)
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
        columnAttributes: typing.Collection[survey.WorldAttribute],
        ) -> survey.RawWorld:
    columnData = line.split('\t')
    if len(columnData) != len(columnAttributes):
        raise RuntimeError('Line has incorrect number of columns')

    worldData = survey.RawWorld(lineNumber=lineNumber)
    for attribute, data in itertools.zip_longest(columnAttributes, columnData):
        if data and _isAllDashes(data):
            data = '' # Replace no data marker with empty string

        worldData.setAttribute(
            attribute=attribute,
            value=data)
    return worldData

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
            maxLength = max([len(w.attribute(attribute=columnAttribute)) for w in worlds])
            if columnAttribute is survey.WorldAttribute.Name or \
                columnAttribute is survey.WorldAttribute.Remarks:
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
                value = world.attribute(attribute=columnAttribute)
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
                value = world.attribute(attribute=columnAttribute)
                # TODO: This should probably remove any \t characters from the value
                values.append(value)
            content += '\t'.join(values) + '\n'

    return content
