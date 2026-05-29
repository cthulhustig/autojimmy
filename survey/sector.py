import common
import enum
import itertools
import logging
import re
import survey
import typing

class SectorFormat(enum.Enum):
    T5Column = 0, # aka Second Survey format
    T5Tab = 1

# https://travellermap.com/doc/fileformats
class _WorldAttribute(enum.Enum):
    Hex = 0
    Name = 1
    UWP = 2
    Remarks = 3
    Importance = 4
    Economics = 5
    Culture = 6
    Nobilities = 7
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
    'N': _WorldAttribute.Nobilities,
    'W': _WorldAttribute.SystemWorlds,
    'Stellar': _WorldAttribute.Stellar
}

_T5Tab_ColumnNameToAttributeMap = {
    'Hex': _WorldAttribute.Hex,
    'Name': _WorldAttribute.Name,
    'UWP': _WorldAttribute.UWP,
    'Remarks': _WorldAttribute.Remarks,
    '{Ix}': _WorldAttribute.Importance,
    '(Ex)': _WorldAttribute.Economics,
    '[Cx]': _WorldAttribute.Culture,
    'Nobility': _WorldAttribute.Nobilities,
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

# NOTE: This is intended to sort the worlds so they will be written out
# in the same order Traveller Map seems to. Worlds are grouped by rows
# of subsectors, inside the each grouping, worlds are written out by x
# value then by y value. If you take the standard subsector labeling
# below, all worlds for subsector A will be written out, then all
# worlds for subsector B and so on
# ABCD
# EFGH
# IJKL
# MNOP
_SubsectorWidth = 8
_SubsectorHeight = 10
_SubsectorsPerRow = 4
_HexesPerParsecRow = _SubsectorWidth * _SubsectorsPerRow
_HexesPerSubsectorRow = _HexesPerParsecRow * _SubsectorHeight
def _sortWorldsByHex(
        worlds: typing.Iterable[survey.RawWorld]
        ) -> typing.Iterable[survey.RawWorld]:
    def calcKey(world: survey.RawWorld) -> int:
        x = world.x()
        y = world.y()
        if x is None or y is None:
            return 0
        subSectorRow = (y - 1) // _SubsectorHeight
        return (y - (subSectorRow * _SubsectorHeight)) + (x * _SubsectorHeight) + (subSectorRow * _HexesPerSubsectorRow)

    return sorted(worlds, key=calcKey)

def _createWorld(
        attributes: typing.Mapping[_WorldAttribute, typing.Optional[str]],
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[survey.RawWorld]:
    hex = attributes.get(_WorldAttribute.Hex)
    hexX = hexY = None
    if hex is not None:
        hexX, hexY = survey.parseHexString(string=hex, reporter=reporter)
    if hexX is None or hexY is None:
        if reporter:
            reporter.addMessage('Ignoring system with no hex')
        return None

    zone = attributes.get(_WorldAttribute.Zone)
    if zone is not None:
        zone = survey.parseSystemZoneString(zone=zone, reporter=reporter)

    uwp = attributes.get(_WorldAttribute.UWP)
    if uwp is not None:
        starport, worldSize, atmosphere, hydrographics, population, government, lawLevel, techLevel = \
            survey.parseSystemUWPString(uwp=uwp, reporter=reporter)
        uwp = survey.RawUWP(
            starport=starport,
            worldSize=worldSize,
            atmosphere=atmosphere,
            hydrographics=hydrographics,
            population=population,
            government=government,
            lawLevel=lawLevel,
            techLevel=techLevel)

    economics = attributes.get(_WorldAttribute.Economics)
    if economics is not None:
        resources, labour, infrastructure, efficiency = \
            survey.parseSystemEconomicsString(economics=economics, reporter=reporter)
        economics = survey.RawEconomics(
            resources=resources,
            labour=labour,
            infrastructure=infrastructure,
            efficiency=efficiency)

    culture = attributes.get(_WorldAttribute.Culture)
    if culture is not None:
        heterogeneity, acceptance, strangeness, symbols = \
            survey.parseSystemCultureString(culture=culture, reporter=reporter)
        culture = survey.RawCulture(
            heterogeneity=heterogeneity,
            acceptance=acceptance,
            strangeness=strangeness,
            symbols=symbols)

    nobilities = attributes.get(_WorldAttribute.Nobilities)
    if nobilities is not None:
        nobilities = survey.parseSystemNobilityString(nobilities, reporter=reporter)

    bases = attributes.get(_WorldAttribute.Bases)
    if bases is not None:
        bases = survey.parseSystemBasesString(bases, reporter=reporter)

    remarks = attributes.get(_WorldAttribute.Remarks)
    if remarks is not None:
        tradeCodes, majorHomeWorlds, minorHomeWorlds, sophontPopulations, dieBackSophonts, \
            owningSystems, colonySystems, rulingAllegiances, researchStations, unrecognisedRemarks = \
            survey.parseSystemRemarksString(string=remarks, reporter=reporter)

        if majorHomeWorlds is not None:
            majorHomeWorlds = [survey.RawSophontPopulation(sophont=sophont, percentage=percentage)
                            for sophont, percentage in majorHomeWorlds]

        if minorHomeWorlds is not None:
            minorHomeWorlds = [survey.RawSophontPopulation(sophont=sophont, percentage=percentage)
                            for sophont, percentage in minorHomeWorlds]

        if sophontPopulations is not None:
            sophontPopulations = [survey.RawSophontPopulation(sophont=sophont, percentage=percentage)
                                for sophont, percentage in sophontPopulations]

        if owningSystems is not None:
            owningSystems = [survey.RawHexRef(x=x, y=y, sector=sector)
                            for x, y, sector in owningSystems]

        if colonySystems is not None:
            colonySystems = [survey.RawHexRef(x=x, y=y, sector=sector)
                            for x, y, sector in colonySystems]

        remarks = survey.RawRemarks(
            tradeCodes=tradeCodes,
            majorRaceHomeWorlds=majorHomeWorlds,
            minorRaceHomeWorlds=minorHomeWorlds,
            sophontPopulations=sophontPopulations,
            dieBackSophonts=dieBackSophonts,
            owningSystems=owningSystems,
            colonySystems=colonySystems,
            rulingAllegiances=rulingAllegiances,
            researchStations=researchStations,
            customRemarks=unrecognisedRemarks)

    pbg = attributes.get(_WorldAttribute.PBG)
    if pbg is not None:
        populationMultiplier, planetoidBeltCount, gasGiantCount = \
            survey.parseSystemPBGString(pbg=pbg, reporter=reporter)
        pbg = survey.RawPBG(
            populationMultiplier=populationMultiplier,
            planetoidBeltCount=planetoidBeltCount,
            gasGiantCount=gasGiantCount)

    systemWorlds = attributes.get(_WorldAttribute.SystemWorlds)
    if systemWorlds is not None:
        systemWorlds = survey.parseSystemWorldCountString(string=systemWorlds, reporter=reporter)

    stars = attributes.get(_WorldAttribute.Stellar)
    if stars is not None:
        stars = survey.parseSystemStellarString(string=stars, reporter=reporter)
        stars = [survey.RawStar(luminosityClass=luminosityClass, spectralClass=spectralClass, spectralScale=spectralScale)
                for luminosityClass, spectralClass, spectralScale in stars]

    importance = attributes.get(_WorldAttribute.Importance)
    if importance is not None:
        importance = survey.parseSystemImportanceString(string=importance, reporter=reporter)

    return survey.RawWorld(
        x=hexX,
        y=hexY,
        name=attributes.get(_WorldAttribute.Name),
        # TODO: Allegiance should probably have some kind of validation. I expect
        # there should be at least a valid character set. I probably want to avoid
        # things like brackets as they'd break some of the remarks formatting where
        # it wraps names in brackets.
        allegiance=attributes.get(_WorldAttribute.Allegiance),
        zone=zone,
        uwp=uwp,
        economics=economics,
        culture=culture,
        nobilities=nobilities,
        bases=bases,
        remarks=remarks,
        importance=importance,
        pbg=pbg,
        systemWorlds=systemWorlds,
        stars=stars)

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
        format: typing.Optional[SectorFormat] = None,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Collection[survey.RawWorld]:
    if format is None:
        format = detectSectorFormat(content=content)
        if format is None:
            raise ValueError('Unable to detect sector format')

    if format == SectorFormat.T5Column:
        return parseT5ColumnSector(content=content, reporter=reporter)
    elif format == SectorFormat.T5Tab:
        return parseT5TabSector(content=content, reporter=reporter)

    raise RuntimeError(f'Unknown sector format {format}')

def parseT5ColumnSector(
        content: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Collection[survey.RawWorld]:
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

        if reporter:
            reporter.pushPrefix(f'Line {lineNumber + 1}: ')

        # Parse the line as a world definition
        try:
            world = _parseT5ColumnWorld(
                line=line,
                columnAttributes=columnAttributes,
                columnWidths=columnWidths,
                reporter=reporter)
        finally:
            if reporter:
                reporter.popPrefix()

        if world:
            worlds.append(world)

    return worlds

def _parseT5ColumnWorld(
        line: str,
        columnAttributes: typing.Collection[_WorldAttribute],
        columnWidths: typing.Collection[int],
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[survey.RawWorld]:
    lineLength = len(line)
    startIndex = 0
    finishIndex = 0
    attributes: typing.Dict[_WorldAttribute, typing.Optional[str]] = {}
    for attribute, width in itertools.zip_longest(columnAttributes, columnWidths):
        if startIndex >= lineLength:
            break

        finishIndex = startIndex + width
        if attribute != None:
            data = line[startIndex:finishIndex].strip()
            if data and not _isAllDashes(data): # Ignore "empty" columns
                attributes[attribute] = data
        startIndex = finishIndex + 1

    return _createWorld(attributes=attributes, reporter=reporter)

def parseT5TabSector(
        content: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Collection[survey.RawWorld]:
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
            if len(columnNames) < len(_T5Tab_ColumnNameToAttributeMap):
                # This is needed as some sectors (notably Shadow Rift) are off format and have
                # broken comments that don't start with #. This gets logged at a low level so
                # we don't spam the logs every time we start
                logging.debug(
                    f'Skipping bogus header on sector file line {lineNumber}')
                columnNames = None
                continue

            # Check that mandatory columns are present
            for columnName in _T5Tab_ColumnNameToAttributeMap.keys():
                if columnName not in columnNames:
                    raise RuntimeError(
                        f'Unable to load data from sector file (Header is missing {columnName} column)')

            # Convert column names to list of column attributes with None for unknown columns
            columnAttributes = []
            for columnName in columnNames:
                attribute = _T5Tab_ColumnNameToAttributeMap.get(columnName)
                columnAttributes.append(attribute)
            continue

        if reporter:
            reporter.pushPrefix(f'Line {lineNumber + 1}:')

        # Parse the line as a world definition
        try:
            world = _parseT5TabWorld(
                line=line,
                columnAttributes=columnAttributes,
                reporter=reporter)
        finally:
            if reporter:
                reporter.popPrefix()

        if world:
            worlds.append(world)
    return worlds

def _parseT5TabWorld(
        line: str,
        columnAttributes: typing.Collection[_WorldAttribute],
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[survey.RawWorld]:
    columnValues = line.split('\t')
    attributes: typing.Dict[_WorldAttribute, typing.Optional[str]] = {}
    for index, attribute in enumerate(columnAttributes):
        if attribute is None:
            continue
        if index >= len(columnValues):
            # There are less columns for this world than defined in the header.
            # I think this is technically invalid but we can handle by just
            # treating that data as unspecified (as it would if the column
            # wasn't defined in the header). Having to fill in blank tabs is a
            # pain in the ass and error prone so I can see it being wrong in a
            # lot of files that are otherwise valid.
            break
        data = columnValues[index]
        if data and not _isAllDashes(data): # Ignore "empty" columns
            attributes[attribute] = data

    return _createWorld(attributes=attributes, reporter=reporter)

_worldAttributeCharMap = str.maketrans({'\t': ' ', '\n': ' '})
def _worldAttribute(
        world: survey.RawWorld,
        attribute: _WorldAttribute,
        default: typing.Any,
        reporter: typing.Optional[common.Reporter] = None
        ) -> str:
    value = None
    if attribute is _WorldAttribute.Hex:
        hexX = world.x()
        hexY = world.y()
        if hexX is not None and hexY is not None:
            value = survey.formatHexString(
                x=hexX,
                y=hexY,
                reporter=reporter)
    elif attribute is _WorldAttribute.Name:
        value = world.name()
    elif attribute is _WorldAttribute.Zone:
        zone = world.zone()
        if zone is not None:
            value = survey.formatSystemZoneString(
                zone=zone,
                reporter=reporter)
    elif attribute is _WorldAttribute.UWP:
        uwp = world.uwp()
        if uwp is not None:
            value = survey.formatSystemUWPString(
                starport=uwp.starport(),
                worldSize=uwp.worldSize(),
                atmosphere=uwp.atmosphere(),
                hydrographics=uwp.hydrographics(),
                population=uwp.population(),
                government=uwp.government(),
                lawLevel=uwp.lawLevel(),
                techLevel=uwp.techLevel(),
                reporter=reporter)
    elif attribute is _WorldAttribute.Remarks:
        remarks = world.remarks()
        if remarks is not None:
            value = survey.formatSystemRemarksString(
                tradeCodes=remarks.tradeCodes(),
                majorRaceHomeWorlds=[(p.sophont(), p.percentage()) for p in remarks.majorRaceHomeWorlds()] if remarks.majorRaceHomeWorlds() else None,
                minorRaceHomeWorlds=[(p.sophont(), p.percentage()) for p in remarks.minorRaceHomeWorlds()] if remarks.minorRaceHomeWorlds() else None,
                sophontPopulations=[(p.sophont(), p.percentage()) for p in remarks.sophontPopulations()] if remarks.sophontPopulations() else None,
                dieBackSophonts=remarks.dieBackSophonts(),
                owningSystems=[(r.x(), r.y(), r.sector()) for r in remarks.owningSystems()] if remarks.owningSystems() else None,
                colonySystems=[(r.x(), r.y(), r.sector()) for r in remarks.colonySystems()] if remarks.colonySystems() else None,
                rulingAllegiances=remarks.rulingAllegiances(),
                researchStations=remarks.researchStations(),
                customRemarks=remarks.customRemarks(),
                reporter=reporter)
    elif attribute is _WorldAttribute.Importance:
        importance = world.importance()
        if importance is not None:
            value = survey.formatSystemImportanceString(
                importance=importance,
                reporter=reporter)
    elif attribute is _WorldAttribute.Economics:
        economics = world.economics()
        if economics is not None:
            value = survey.formatSystemEconomicsString(
                resources=economics.resources(),
                labour=economics.labour(),
                infrastructure=economics.infrastructure(),
                efficiency=economics.efficiency(),
                reporter=reporter)
    elif attribute is _WorldAttribute.Culture:
        culture = world.culture()
        if culture is not None:
            value = survey.formatSystemCultureString(
                heterogeneity=culture.heterogeneity(),
                acceptance=culture.acceptance(),
                strangeness=culture.strangeness(),
                symbols=culture.symbols(),
                reporter=reporter)
    elif attribute is _WorldAttribute.Nobilities:
        nobilities = world.nobilities()
        if nobilities is not None:
            value = survey.formatSystemNobilityString(
                nobilities=nobilities,
                reporter=reporter)
    elif attribute is _WorldAttribute.Bases:
        bases = world.bases()
        if bases is not None:
            value = survey.formatSystemBasesString(
                bases=bases,
                reporter=reporter)
    elif attribute is _WorldAttribute.PBG:
        pbg = world.pbg()
        if pbg is not None:
            value = survey.formatSystemPBGString(
                populationMultiplier=pbg.populationMultiplier(),
                planetoidBelts=pbg.planetoidBeltCount(),
                gasGiants=pbg.gasGiantCount(),
                reporter=reporter)
    elif attribute is _WorldAttribute.SystemWorlds:
        systemWorlds = world.systemWorlds()
        if systemWorlds is not None:
            value = survey.formatSystemWorldCountString(
                count=systemWorlds,
                reporter=reporter)
    elif attribute is _WorldAttribute.Allegiance:
        value = world.allegiance()
    elif attribute is _WorldAttribute.Stellar:
        stars = world.stars()
        if stars is not None:
            value = survey.formatSystemStellarString(
                stars=[(s.luminosityClass(), s.spectralClass(), s.spectralScale()) for s in stars],
                reporter=reporter)
        value = world.stars()

    if value is None:
        return default

    if isinstance(value, str):
        return value.translate(_worldAttributeCharMap)
    else:
        return str(value)

def formatSector(
        worlds: typing.Collection[survey.RawWorld],
        format: SectorFormat,
        reporter: typing.Optional[common.Reporter] = None
        ) -> str:
    if format is SectorFormat.T5Column:
        return formatT5ColumnSector(worlds=worlds, reporter=reporter)
    elif format is SectorFormat.T5Tab:
        return formatT5TabSector(worlds=worlds, reporter=reporter)

    raise RuntimeError(f'Unknown sector format {format}')

def formatT5ColumnSector(
        worlds: typing.Collection[survey.RawWorld],
        reporter: typing.Optional[common.Reporter] = None
        ) -> str:
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

    for world in _sortWorldsByHex(worlds):
        if reporter:
            identifier = _worldAttribute(
                world=world,
                attribute=_WorldAttribute.Name,
                default=None)
            if not identifier:
                hex = _worldAttribute(
                    world=world,
                    attribute=_WorldAttribute.Hex,
                    default=None)
                if hex:
                    identifier = f'Hex {hex}'
                else:
                    identifier = 'Unknown World'
            reporter.pushPrefix(f'{identifier}: ')

        try:
            values = []
            for columnName, columnAttribute in _T5Column_ColumnNameToAttributeMap.items():
                value = _worldAttribute(world=world, attribute=columnAttribute, default='', reporter=reporter)
                maxLength = maxColumnLengths[columnName]
                value += ' ' * (maxLength - len(value))
                values.append(value)
            content += ' '.join(values) + '\n'
        finally:
            if reporter:
                reporter.popPrefix()

    return content

def formatT5TabSector(
        worlds: typing.Collection[survey.RawWorld],
        reporter: typing.Optional[common.Reporter] = None
        ) -> str:
    outputColumns = dict(_T5Tab_ColumnNameToAttributeMap)
    content = '\t'.join(outputColumns.keys())

    for world in _sortWorldsByHex(worlds):
        if reporter:
            identifier = _worldAttribute(
                world=world,
                attribute=_WorldAttribute.Name,
                default=None)
            if not identifier:
                hex = _worldAttribute(
                    world=world,
                    attribute=_WorldAttribute.Hex,
                    default=None)
                if hex:
                    identifier = f'Hex {hex}'
                else:
                    identifier = 'Unknown World'
            reporter.pushPrefix(f'{identifier}: ')

        try:
            values = []
            for columnAttribute in outputColumns.values():
                value = _worldAttribute(
                    world=world,
                    attribute=columnAttribute,
                    default='',
                    reporter=reporter)
                values.append(value)
            content += '\t'.join(values) + '\n'
        finally:
            if reporter:
                reporter.popPrefix()

    return content
