import enum
import common
import itertools
import json
import logging
import multiverse
import re
import typing
import xml.etree.ElementTree

class SectorFormat(enum.Enum):
    T5Column = 0, # aka Second Survey format
    T5Tab = 1

class MetadataFormat(enum.Enum):
    JSON = 0
    XML = 1

class LegacyAllegiancesFormat(enum.Enum):
    T5TAB = 0
    JSON  = 1

_XmlFloatDecimalPlaces = 2

_HeaderPattern = re.compile(r'(?:([\w{}()\[\]]+)\s*)')
_SeparatorPattern = re.compile(r'(?:([-]+)\s?)')
_T5Column_ColumnNameToAttributeMap = {
    'Name': multiverse.WorldAttribute.Name,
    'Hex': multiverse.WorldAttribute.Hex,
    'UWP': multiverse.WorldAttribute.UWP,
    'B': multiverse.WorldAttribute.Bases,
    'Remarks': multiverse.WorldAttribute.Remarks,
    'Z': multiverse.WorldAttribute.Zone,
    'PBG': multiverse.WorldAttribute.PBG,
    'A': multiverse.WorldAttribute.Allegiance,
    '{Ix}': multiverse.WorldAttribute.Importance,
    '(Ex)': multiverse.WorldAttribute.Economics,
    '[Cx]': multiverse.WorldAttribute.Culture,
    'N': multiverse.WorldAttribute.Nobility,
    'W': multiverse.WorldAttribute.SystemWorlds,
    'Stellar': multiverse.WorldAttribute.Stellar
}
_T5Row_ColumnNameToAttributeMap = {
    'Hex': multiverse.WorldAttribute.Hex,
    'Name': multiverse.WorldAttribute.Name,
    'UWP': multiverse.WorldAttribute.UWP,
    'Remarks': multiverse.WorldAttribute.Remarks,
    '{Ix}': multiverse.WorldAttribute.Importance,
    '(Ex)': multiverse.WorldAttribute.Economics,
    '[Cx]': multiverse.WorldAttribute.Culture,
    'Nobility': multiverse.WorldAttribute.Nobility,
    'Bases': multiverse.WorldAttribute.Bases,
    'Zone': multiverse.WorldAttribute.Zone,
    'PBG': multiverse.WorldAttribute.PBG,
    'W': multiverse.WorldAttribute.SystemWorlds,
    'Allegiance': multiverse.WorldAttribute.Allegiance,
    'Stars': multiverse.WorldAttribute.Stellar
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
        ) -> typing.Collection[multiverse.RawWorld]:
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
        ) -> typing.Collection[multiverse.RawWorld]:
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
        columnAttributes: typing.Collection[multiverse.WorldAttribute],
        columnWidths: typing.Collection[int]
        ) -> multiverse.RawWorld:
    worldData = multiverse.RawWorld(lineNumber=lineNumber)
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
        ) -> typing.Collection[multiverse.RawWorld]:
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
        columnAttributes: typing.Collection[multiverse.WorldAttribute],
        ) -> multiverse.RawWorld:
    columnData = line.split('\t')
    if len(columnData) != len(columnAttributes):
        raise RuntimeError('Line has incorrect number of columns')

    worldData = multiverse.RawWorld(lineNumber=lineNumber)
    for attribute, data in itertools.zip_longest(columnAttributes, columnData):
        if data and _isAllDashes(data):
            data = '' # Replace no data marker with empty string

        worldData.setAttribute(
            attribute=attribute,
            value=data)
    return worldData

def writeSector(
        worlds: typing.Collection[multiverse.RawWorld],
        format: SectorFormat,
        identifier: str
        ) -> str:
    if format is SectorFormat.T5Column:
        return writeT5ColumnSector(worlds, identifier)
    elif format is SectorFormat.T5Tab:
        return writeT5RowSector(worlds, identifier)
    else:
        raise RuntimeError(f'Unknown sector format {format} for {identifier}')

def writeT5ColumnSector(
        worlds: typing.Collection[multiverse.RawWorld],
        identifier: str
        ) -> str:
    content = ''

    maxColumnLengths = {}
    for columnName, columnAttribute in _T5Column_ColumnNameToAttributeMap.items():
        maxLength = 0
        if worlds:
            maxLength = max([len(w.attribute(attribute=columnAttribute)) for w in worlds])
            if columnAttribute is multiverse.WorldAttribute.Name or \
                columnAttribute is multiverse.WorldAttribute.Remarks:
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
def writeT5RowSector(
        worlds: typing.Collection[multiverse.RawWorld],
        identifier: str
        ) -> str:
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
        ) -> multiverse.RawMetadata:
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
        ) -> multiverse.RawMetadata:
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

    sectorLabelElement = sectorElement.find('./Label')
    sectorLabel = sectorLabelElement.text if sectorLabelElement != None else None

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
                allegiances.append(multiverse.RawAllegiance(
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

            routes.append(multiverse.RawRoute(
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

            borders.append(multiverse.RawBorder(
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

            labels.append(multiverse.RawLabel(
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

            regions.append(multiverse.RawRegion(
                hexList=path,
                showLabel=showLabel,
                wrapLabel=wrapLabel,
                labelHex=element.get('LabelPosition'),
                labelOffsetX=labelOffsetX,
                labelOffsetY=labelOffsetY,
                label=element.get('Label'),
                colour=element.get('Color'),
                fileIndex=index))

    creditsElements = sectorElement.find('./Credits')
    primaryElements = sectorElement.find('./DataFile')
    productsElements = sectorElement.findall('./Product')
    sources = None
    if creditsElements != None or primaryElements != None or productsElements != None:
        primary = None
        if primaryElements != None:
            publication = primaryElements.get('Source')
            author = primaryElements.get('Author')
            publisher = primaryElements.get('Publisher')
            reference = primaryElements.get('Ref')

            if publication or author or publisher or reference:
                primary = multiverse.RawSource(
                    publication=publication,
                    author=author,
                    publisher=publisher,
                    reference=reference)

        products = None
        if productsElements != None:
            products = []
            for element in productsElements:
                products.append(multiverse.RawSource(
                    publication=element.get('Title'),
                    author=element.get('Author'),
                    publisher=element.get('Publisher'),
                    reference=element.get('Ref')))

        sources = multiverse.RawSources(
            credits=creditsElements.text if creditsElements != None else None,
            primary=primary,
            products=products)

    styleSheetElement = sectorElement.find('./Stylesheet')
    styleSheet = styleSheetElement.text if styleSheetElement != None else None

    return multiverse.RawMetadata(
        canonicalName=names[0],
        alternateNames=names[1:],
        nameLanguages=nameLanguages,
        abbreviation=sectorElement.get('Abbreviation'),
        sectorLabel=sectorLabel,
        subsectorNames=subsectorNames,
        x=x,
        y=y,
        selected=_optionalConvertToBool(sectorElement.get('Selected'), 'Selected', 'Sector', identifier),
        tags=sectorElement.get('Tags'),
        allegiances=allegiances,
        routes=routes,
        borders=borders,
        labels=labels,
        regions=regions,
        sources=sources,
        styleSheet=styleSheet)

def readJSONMetadata(
        content: str,
        identifier: str
        ) -> multiverse.RawMetadata:
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
                    allegiances.append(multiverse.RawAllegiance(
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

            routes.append(multiverse.RawRoute(
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

            borders.append(multiverse.RawBorder(
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

            labels.append(multiverse.RawLabel(
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

            regions.append(multiverse.RawRegion(
                hexList=path,
                showLabel=showLabel,
                wrapLabel=wrapLabel,
                labelHex=element.get('LabelPosition'),
                labelOffsetX=labelOffsetX,
                labelOffsetY=labelOffsetY,
                label=element.get('Label'),
                colour=element.get('Color'),
                fileIndex=index))

    creditsElements = sectorElement.get('Credits')
    primaryElements = sectorElement.get('DataFile')
    productsElements = sectorElement.get('Products')
    sources = None
    if creditsElements != None or primaryElements != None or productsElements != None:
        primary = None
        if primaryElements != None:
            publication = primaryElements.get('Source')
            author = primaryElements.get('Author')
            publisher = primaryElements.get('Publisher')
            reference = primaryElements.get('Ref')

            if publication or author or publisher or reference:
                primary = multiverse.RawSource(
                    publication=publication,
                    author=author,
                    publisher=publisher,
                    reference=reference)

        products = None
        if productsElements != None:
            products = []
            for element in productsElements:
                products.append(multiverse.RawSource(
                    publication=element.get('Title'),
                    author=element.get('Author'),
                    publisher=element.get('Publisher'),
                    reference=element.get('Ref')))

        # NOTE: Credits aren't currently supported for JSON format as I don't
        # know what structure they use. The Traveller Map metadata API always
        # returns an empty list
        if primary or products:
            sources = multiverse.RawSources(
                credits=None,
                primary=primary,
                products=products)

    return multiverse.RawMetadata(
        canonicalName=names[0],
        alternateNames=names[1:],
        nameLanguages=nameLanguages,
        abbreviation=sectorElement.get('Abbreviation'),
        sectorLabel=sectorElement.get('Label'),
        subsectorNames=subsectorNames,
        x=x,
        y=y,
        selected=_optionalConvertToBool(sectorElement.get('Selected'), 'Selected', 'Sector', identifier),
        tags=sectorElement.get('Tags'),
        allegiances=allegiances,
        routes=routes,
        borders=borders,
        labels=labels,
        regions=regions,
        sources=sources,
        styleSheet=sectorElement.get('StyleSheet'))

def writeMetadata(
        metadata: multiverse.RawMetadata,
        format: MetadataFormat,
        identifier: str
        ) -> str:
    if format == MetadataFormat.XML:
        return writeXMLMetadata(
            metadata=metadata,
            identifier=identifier)
    elif format == MetadataFormat.JSON:
        return writeJSONMetadata(
            metadata=metadata,
            identifier=identifier)
    else:
        raise RuntimeError(f'Unknown metadata format {format} for {identifier}')

def writeXMLMetadata(
        metadata: multiverse.RawMetadata,
        identifier: str
        ) -> str:
    sectorAttributes = {}

    if metadata.selected() != None:
        sectorAttributes['Selected'] = str(metadata.selected())

    # NOTE: The Traveller Map documentation doesn't mention Tags or Abbreviation for the XML
    # format but the XSD does have them
    # https://travellermap.com/doc/metadata
    if metadata.tags() != None:
        sectorAttributes['Tags'] = metadata.tags()

    if metadata.abbreviation() != None:
        sectorAttributes['Abbreviation'] = metadata.abbreviation()

    sectorElement = xml.etree.ElementTree.Element('Sector', sectorAttributes)

    names = [metadata.canonicalName()]
    if metadata.alternateNames():
        names.extend(metadata.alternateNames())
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
            if route.startOffsetX():
                attributes['StartOffsetX'] = str(route.startOffsetX())
            if route.startOffsetY():
                attributes['StartOffsetY'] = str(route.startOffsetY())
            if route.endOffsetX():
                attributes['EndOffsetX'] = str(route.endOffsetX())
            if route.endOffsetY():
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

    sources = metadata.sources()
    if sources:
        if sources.credits():
            creditsElement = xml.etree.ElementTree.SubElement(sectorElement, 'Credits')
            creditsElement.text = sources.credits()

        if sources.primary():
            primary = sources.primary()
            attributes = {}
            if primary.publication():
                attributes['Source'] = primary.publication()
            if primary.author():
                attributes['Author'] = primary.author()
            if primary.publisher():
                attributes['Publisher'] = primary.publisher()
            if primary.reference():
                attributes['Ref'] = primary.reference()

            if attributes:
                xml.etree.ElementTree.SubElement(sectorElement, 'DataFile', attributes)

        if sources.products():
            for product in sources.products():
                attributes = {}
                if product.publication():
                    attributes['Title'] = product.publication()
                if product.author():
                    attributes['Author'] = product.author()
                if product.publisher():
                    attributes['Publisher'] = product.publisher()
                if product.reference():
                    attributes['Ref'] = product.reference()

                if attributes:
                    xml.etree.ElementTree.SubElement(sectorElement, 'Product', attributes)

    if metadata.styleSheet() != None:
        styleSheetElement = xml.etree.ElementTree.SubElement(sectorElement, 'StyleSheet')
        styleSheetElement.text = metadata.styleSheet()

    xml.etree.ElementTree.indent(sectorElement, space="\t", level=0)
    resultBytes: bytes = xml.etree.ElementTree.tostring(
        element=sectorElement,
        encoding='utf-8',
        xml_declaration=True)
    return resultBytes.decode('utf-8')

def writeJSONMetadata(
        metadata: multiverse.RawMetadata,
        identifier: str
        ) -> str:
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

    sources = metadata.sources()
    if sources:
        # NOTE: The Credits string isn't written out as I don't know what
        # format it's mean to be in for JSON. The Traveller Map metadata
        # API returns an empty array for sectors with credits when JSON
        # is requested

        if sources.primary():
            primary = sources.primary()
            primaryElement = {}
            if primary.publication():
                primaryElement['Source'] = primary.publication()
            if primary.author():
                primaryElement['Author'] = primary.author()
            if primary.publisher():
                primaryElement['Publisher'] = primary.publisher()
            if primary.reference():
                primaryElement['Ref'] = primary.reference()

            if primaryElement:
                sectorElement['DataFile'] = primaryElement

        if sources.products():
            productsElement = []
            for product in sources.products():
                productElement = {}
                if product.publication():
                    productElement['Title'] = product.publication()
                if product.author():
                    productElement['Author'] = product.author()
                if product.publisher():
                    productElement['Publisher'] = product.publisher()
                if product.reference():
                    productElement['Ref'] = product.reference()

                if productElement:
                    productsElement.append(productElement)

            if productsElement:
                sectorElement['Products'] = productsElement

    # NOTE: The JSON metadata returned by Traveller Map doesn't include
    # style sheet information
    """
    if metadata.styleSheet() != None:
        sectorElement['StyleSheet'] = metadata.styleSheet()
    """

    return json.dumps(sectorElement, indent=4)

def readUniverseInfo(
        content: str
        ) -> multiverse.RawUniverseInfo:
    universeElement = json.loads(content)

    sectorsElement = universeElement.get('Sectors')
    sectorInfos = []
    if not sectorsElement:
        raise RuntimeError('No Sectors element found')

    for sectorElement in sectorsElement:
        sectorX = sectorElement.get('X')
        if sectorX is None:
            raise RuntimeError('Sector has no X Position')
        sectorX = int(sectorX)

        sectorY = sectorElement.get('Y')
        if sectorY is None:
            raise RuntimeError('Sector has no Y Position')
        sectorY = int(sectorY)

        milieu = sectorElement.get('Milieu')
        if not milieu:
            raise RuntimeError('Sector has no Milieu')

        abbreviation = sectorElement.get('Abbreviation')
        if abbreviation is not None:
            abbreviation = str(abbreviation)

        tags = sectorElement.get('Tags')
        if tags is not None:
            tags = str(tags)

        namesElements = sectorElement.get('Names')
        nameInfos = None
        if namesElements and len(namesElements) > 0:
            nameInfos = []
            for nameElement in namesElements:
                name = nameElement.get('Text')
                if not name:
                    raise RuntimeError('Sector Name element has no Text')
                name = str(name)

                language = nameElement.get('Lang')
                if language is not None:
                    language = str(language)

                source = nameElement.get('Source')
                if source is not None:
                    source = str(source)

                nameInfos.append(multiverse.RawNameInfo(
                    name=name,
                    language=language,
                    source=source))

        sectorInfos.append(multiverse.RawSectorInfo(
            x=sectorX,
            y=sectorY,
            milieu=milieu,
            abbreviation=abbreviation,
            tags=tags,
            nameInfos=nameInfos))

    return multiverse.RawUniverseInfo(
        sectorInfos=sectorInfos)

def writeUniverseInfo(
        universeInfo: multiverse.RawUniverseInfo
        ) -> str:
    universeElement = {}

    sectorsElement = []
    for sectorInfo in universeInfo.sectorInfos():
        sectorElement = {
            'X': sectorInfo.x(),
            'Y': sectorInfo.y(),
            'Milieu': sectorInfo.milieu()}

        if sectorInfo.abbreviation():
            sectorElement['Abbreviation'] = sectorInfo.abbreviation()

        if sectorInfo.tags():
            sectorElement['Tags'] = sectorInfo.tags()

        if sectorInfo.names():
            namesElement = []
            for nameInfo in sectorInfo.names():
                nameElement = {'Text': nameInfo.name()}

                if nameInfo.language():
                    nameElement['Lang'] = nameInfo.language()

                if nameInfo.source():
                    nameElement['Source'] = nameInfo.source()

                namesElement.append(nameElement)

            sectorElement['Names'] = namesElement

        sectorsElement.append(sectorElement)

    universeElement['Sectors'] = sectorsElement

    return json.dumps(universeElement, indent=4).encode()

def _detectLegacyAllegiancesFormat(
        content: str
        ) -> LegacyAllegiancesFormat:
    try:
        result = json.loads(content)
        if result:
            return LegacyAllegiancesFormat.JSON
    except:
        pass

    return LegacyAllegiancesFormat.T5TAB

def readT5LegacyAllegiances(
        content: str
        ) -> typing.List[multiverse.RawLegacyAllegiance]:
    _, results = common.parseTabTableContent(content=content)

    allegiances: typing.List[multiverse.RawLegacyAllegiance] = []
    for index, allegiance in enumerate(results):
        code = allegiance.get('Code')
        if not code:
            raise RuntimeError(f'No code specified for legacy allegiance {index + 1}')
        name = allegiance.get('Name')
        if not name:
            raise RuntimeError(f'No name specified for legacy allegiance {index + 1}')
        legacy = allegiance.get('Legacy')
        if not legacy:
            raise RuntimeError(f'No legacy code specified for legacy allegiance {index + 1}')
        base = allegiance.get('BaseCode')
        locations = allegiance.get('Location')
        if locations is not None:
            locations = locations.split('/')

        allegiances.append(multiverse.RawLegacyAllegiance(
            code=code,
            name=name,
            legacy=legacy,
            base=base,
            locations=locations))

    return allegiances

def readJsonLegacyAllegiances(
        content: str
        ) -> typing.List[multiverse.RawLegacyAllegiance]:
    jsonList = json.loads(content)
    if not isinstance(jsonList, list):
        raise RuntimeError(f'Content is not a json list')

    allegiances: typing.List[multiverse.RawLegacyAllegiance] = []
    for index, allegiance in enumerate(jsonList):
        if not isinstance(allegiance, dict):
            raise RuntimeError(f'Item {index + 1} is not a json object')

        code = allegiance.get('Code')
        if not code:
            raise RuntimeError(f'No code specified for legacy allegiance {index + 1}')
        if not isinstance(code, str):
            raise RuntimeError(f'Code specified for legacy allegiance {index + 1} is not a string')

        name = allegiance.get('Name')
        if not name:
            raise RuntimeError(f'No name specified for legacy allegiance {index + 1}')
        if not isinstance(name, str):
            raise RuntimeError(f'Name specified for legacy allegiance {index + 1} is not a string')

        legacy = allegiance.get('Legacy')
        if not legacy:
            raise RuntimeError(f'No legacy code specified for legacy allegiance {index + 1}')
        if not isinstance(legacy, str):
            raise RuntimeError(f'Legacy code specified for legacy allegiance {index + 1} is not a string')

        base = allegiance.get('BaseCode')
        if base is not None and not isinstance(base, str):
            raise RuntimeError(f'Base code specified for legacy allegiance {index + 1} is not a string')

        locations = allegiance.get('Location')
        if locations is not None:
            if not isinstance(locations, str):
                raise RuntimeError(f'Locations specified for legacy allegiance {index + 1} is not a string')
            locations = locations.split('/')

        allegiances.append(multiverse.RawLegacyAllegiance(
            code=code,
            name=name,
            legacy=legacy,
            base=base,
            locations=locations))

    return allegiances

def readLegacyAllegiances(
        content: str
        ) -> typing.List[multiverse.RawLegacyAllegiance]:
    format = _detectLegacyAllegiancesFormat(content=content)
    if format is LegacyAllegiancesFormat.T5TAB:
        return readT5LegacyAllegiances(content=content)
    elif format is LegacyAllegiancesFormat.JSON:
        return readJsonLegacyAllegiances(content=content)

    raise ValueError('Unrecognised legacy allegiances content format')
