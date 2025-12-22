import logging
import itertools
import multiverse
import re
import typing

# TODO: The conversion process needs to give better error/warning/info
# feedback to the user when converting custom sectors (converting the
# default universe should just log)
# TODO: Need code to allow export from db to file. I deleted the old
# code that did it as it had bit rotted

# These unofficial allegiances are taken from Traveller Map. It has a
# comment saying they're for M1120 but as far as I can tell it uses
# them no mater which milieu you have selected. In my implementation
# they are only used for M1120 & M1121
_T5UnofficialM112xAllegiances = [
    # -----------------------
    # Unofficial/Unreviewed
    # -----------------------
    multiverse.RawStockAllegiance(code='FdAr', legacy='Fa', base=None, name='Federation of Arden' ),
    multiverse.RawStockAllegiance(code='BoWo', legacy='Bw', base=None, name='Border Worlds' ),
    multiverse.RawStockAllegiance(code='LuIm', legacy='Li', base='Im', name='Lucan\'s Imperium' ),
    multiverse.RawStockAllegiance(code='MaSt', legacy='Ma', base='Im', name='Maragaret\'s Domain' ),
    multiverse.RawStockAllegiance(code='BaCl', legacy='Bc', base=None, name='Backman Cluster' ),
    multiverse.RawStockAllegiance(code='FdDa', legacy='Fd', base='Im', name='Federation of Daibei' ),
    multiverse.RawStockAllegiance(code='FdIl', legacy='Fi', base='Im', name='Federation of Ilelish' ),
    multiverse.RawStockAllegiance(code='AvCn', legacy='Ac', base=None, name='Avalar Consulate' ),
    multiverse.RawStockAllegiance(code='CoAl', legacy='Ca', base=None, name='Corsair Alliance' ),
    multiverse.RawStockAllegiance(code='StIm', legacy='St', base='Im', name='Strephon\'s Worlds' ),
    multiverse.RawStockAllegiance(code='ZiSi', legacy='Rv', base='Im', name='Restored Vilani Imperium' ), # Ziru Sirka
    multiverse.RawStockAllegiance(code='VA16', legacy='V6', base=None, name='Assemblage of 1116' ),
    multiverse.RawStockAllegiance(code='CRVi', legacy='CV', base=None, name='Vilani Cultural Region' ),
    multiverse.RawStockAllegiance(code='CRGe', legacy='CG', base=None, name='Geonee Cultural Region' ),
    multiverse.RawStockAllegiance(code='CRSu', legacy='CS', base=None, name='Suerrat Cultural Region' ),
    multiverse.RawStockAllegiance(code='CRAk', legacy='CA', base=None, name='Anakudnu Cultural Region' )
    ]
_T5UnofficialAllegiancesMap = {
    'M1120': _T5UnofficialM112xAllegiances,
    'M1121': _T5UnofficialM112xAllegiances,
    }

# These allegiances are take from Traveller Map (SecondSurvey.cs)
# Cases where T5SS codes don't apply: e.g. the Hierate or Imperium, or where no codes exist yet
_LegacyAllegiances = [
    multiverse.RawStockAllegiance(code='As', legacy='As', base='As', name='Aslan Hierate' ), # T5SS: Clan, client state, or unknown; no generic code
    multiverse.RawStockAllegiance(code='Dr', legacy='Dr', base='Dr', name='Droyne' ), # T5SS: Polity name or unaligned w/ Droyne population
    multiverse.RawStockAllegiance(code='Im', legacy='Im', base='Im', name='Third Imperium' ), # T5SS: Domain or cultural region; no generic code
    multiverse.RawStockAllegiance(code='Kk', legacy='Kk', base='Kk', name='The Two Thousand Worlds' ), # T5SS: (Not yet assigned)
]

# These mappings are taken from Traveller Map (SecondSurvey.cs)
# Overrides or additions where Legacy -> T5SS code mapping is ambiguous.
_LegacyAllegianceToT5Overrides = {
    'J-': 'JuPr',
    'Jp': 'JuPr',
    'Ju': 'JuPr',
    'Na': 'NaHu',
    'So': 'SoCf',
    'Va': 'NaVa',
    'Zh': 'ZhCo',
    '??': 'XXXX',
    '--': 'XXXX'
}

_MilitaryRuleRemarkPattern = re.compile(r'(?:(?<=^)|(?<=[\s,]))Mr\((\S{4})\)(?=$|[\s,])')

# This pattern matches major sophont home worlds using the official [Name]#
# format where # is an optional population percentage in 10s of precent
# _and_ the unofficial [Name]###% format where # is the population in percent.
# NOTE: This should be kept up to date with parseSystemRemarksString
# NOTE: The second survey spec only has the population percentage for minor home
# worlds but it seems odd to assume the home world is always 100%
# NOTE: The docs only have 'W' as meaning 100% for but I've allowed 'w' in order
# to be more accepting
# NOTE: The percentage can be set to '?' to mean unknown population. It's not
# mentioned documentation but they are used in the Traveller Map sectors
_MajorSophontHomeWorldRemarkPattern = re.compile(r'(?:(?<=^)|(?<=[\s,]))\[\s*(?=\S)([^]]+?)\s*\](?:[0-9Ww?]?|(?:0|[1-9][0-9]?|100)%)(?=$|[\s,])')

# This pattern matches minor sophont home worlds using the official (Name)#
# format where # is an optional population percentage in 10s of precent
# _and_ the unofficial (Name)###% format where # is the population in percent.
# NOTE: The docs only have 'W' as meaning 100% for but I've allowed 'w' in order
# to be more accepting
# NOTE: The percentage can be set to '?' to mean unknown population. It's not
# mentioned documentation but they are used in the Traveller Map sectors
_MinorSophontHomeWorldRemarkPattern = re.compile(r'(?:(?<=^)|(?<=[\s,]))\(\s*(?=\S)([^)]+?)\s*\)(?:[0-9Ww?]?|(?:0|[1-9][0-9]?|100)%)(?=$|[\s,])')


# This pattern matches sophont using the official XXXX# where XXXX is a T5
# sophont code and # is the population in 10s of percentage or W to indicate
# 100% _and_ the unofficial XXXX###% format where # is the population in
# percent.
# NOTE: I support an optional ':' separator between the code and population.
# It's not part of the of the second survey spec but some sector files do use
# it.
# NOTE: I've used \S (anything that's not a space) for the code (rather than \w)
# as there are some uses of none alphabetic characters (notably Za'tW in M1105
# Wrenton)
# NOTE: The docs only have 'W' as meaning 100% for but I've allowed 'w' in order
# to be more accepting
# NOTE: The percentage can be set to '?' to mean unknown population. It's not
# mentioned documentation but they are used in the Traveller Map sectors
_T5SophontPopulationRemarkPattern = re.compile(r'(?:(?<=^)|(?<=[\s,]))(\S{4}):?(?:[0-9Ww?]|(?:0|[1-9][0-9]?|100)%)(?=$|[\s,])')

# This pattern matches sophont using the official X# where X is a legacy sophont
# code and # is the population in 10s of percentage or W to indicate 100% _and_
# the unofficial X###% format where # is the population in percent.
# NOTE: I've made the ':' separator optional as a separator isn't required due
# to the fields being a fixed length
# NOTE: The docs only have 'w' as meaning 100% for but I've allowed 'W' in order
# to be more accepting
# NOTE: The percentage can be set to '?' to mean unknown population. It's not
# mentioned documentation but they are used in the Traveller Map sectors
_LegacySophontPopulationRemarkPattern = re.compile(r'(?:(?<=^)|(?<=[\s,]))([ACDHIMVXZ]):?(?:[0-9wW?]|(?:0|[1-9][0-9]?|100)%)(?=$|[\s,])')


# This pattern matches sophonts using the Di(Name) format to indicate a
# die back sophont
_DieBackSophontRemarkPattern = re.compile(r'(?:(?<=^)|(?<=[\s,]))Di\(\s*(?=\S)([^)]+?)\s*\)(?=$|[\s,])')

_StockMajorSophonts = set([
    'Human',
    'Aslan',
    'Droyne',
    'Hiver',
    'K\'kree',
    'Vargr',
])

# This maps legacy single letter sophont codes to T5 sophont codes. There is no
# mapping for 'F' as I've no idea what T5 sophont it maps to
_LegacySophontMap = {
    'A': 'Asla',
    'C': 'Chir',
    'D': 'Droy',
    #'F': 'Non-Hiver Federation Member',
    'H': 'Hive',
    'I': 'Ithk',
    'M': 'Huma',
    'V': 'Varg',
    'X': 'Adda',
    'Z': 'Zhod'
}

def _findUsedAllegianceCodes(
        rawMetadata: multiverse.RawMetadata,
        rawSystems: typing.Collection[multiverse.RawWorld]
        ) -> typing.Set[str]:
    usedCodes: typing.Set[str] = set()
    if rawSystems:
        for rawWorld in rawSystems:
            rawAllegianceCode = rawWorld.attribute(multiverse.WorldAttribute.Allegiance)
            if rawAllegianceCode:
                usedCodes.add(rawAllegianceCode)

            rawRemarks = rawWorld.attribute(multiverse.WorldAttribute.Remarks)
            if rawRemarks:
                matches = _MilitaryRuleRemarkPattern.findall(rawRemarks)
                for match in matches:
                    usedCodes.add(match)
    if rawMetadata.routes():
        for rawRoute in rawMetadata.routes():
            rawAllegianceCode = rawRoute.allegiance()
            if rawAllegianceCode:
                usedCodes.add(rawAllegianceCode)
    if rawMetadata.borders():
        for rawBorder in rawMetadata.borders():
            rawAllegianceCode = rawBorder.allegiance()
            if rawAllegianceCode:
                usedCodes.add(rawAllegianceCode)
    return usedCodes

def _filterStockAllegiances(
        milieu: str,
        rawMetadata: multiverse.RawMetadata,
        rawUsedAllegianceCodes: typing.Collection[str],
        rawStockAllegiances: typing.Collection[multiverse.RawStockAllegiance] = None,
        ) -> typing.List[multiverse.RawStockAllegiance]:
    rawLocalAllegiances: typing.Collection[multiverse.RawStockAllegiance] = []
    rawGlobalAllegiances: typing.Collection[multiverse.RawStockAllegiance]  = []
    rawSeenAllegianceCodes = set()

    if rawStockAllegiances:
        rawAbbreviation = rawMetadata.abbreviation()
        for rawStockAllegiance in rawStockAllegiances:
            if rawStockAllegiance.code() in rawSeenAllegianceCodes:
                raise RuntimeError(f'Stock allegiances contain multiple allegiances with the code {rawStockAllegiance.code()}')
            rawSeenAllegianceCodes.add(rawStockAllegiance.code())

            rawLocations = rawStockAllegiance.location()
            if rawLocations is not None:
                rawLocations = rawLocations.split('/')

            if rawLocations:
                # The database allegiance if for specific locations so only use it if
                # it specifies this sectors abbreviation or 'various'. I can't find
                # an explicit definition for various but all that can really be done with
                # it is to treat it as global and use it for any sector (the same as if
                # no locations had been specified)
                for rawLocation in rawLocations:
                    if rawAbbreviation and rawLocation == rawAbbreviation:
                        rawLocalAllegiances.append(rawStockAllegiance)
                        break

                    if rawLocation.lower() == 'various':
                        rawGlobalAllegiances.append(rawStockAllegiance)
                        break
            else:
                # The database allegiance is global so it can be used for this sector
                rawGlobalAllegiances.append(rawStockAllegiance)

    rawMilieuAllegiances = _T5UnofficialAllegiancesMap.get(milieu)
    if rawMilieuAllegiances:
        for rawStockAllegiance in rawMilieuAllegiances:
            if rawStockAllegiance.code() in rawSeenAllegianceCodes:
                continue # Skip already defined allegiance
            rawSeenAllegianceCodes.add(rawStockAllegiance.code())

            rawGlobalAllegiances.append(rawStockAllegiance)

    for rawStockAllegiance in _LegacyAllegiances:
        if rawStockAllegiance.code() in rawSeenAllegianceCodes:
            continue # Skip already defined allegiance
        rawSeenAllegianceCodes.add(rawStockAllegiance.code())

        rawGlobalAllegiances.append(rawStockAllegiance)

    # Always include local allegiances
    rawFilteredAllegiances = list(rawLocalAllegiances)

    # Only include global allegiances if they're actually required
    for rawAllegiance in rawGlobalAllegiances:
        if rawAllegiance.code() in rawUsedAllegianceCodes:
            rawFilteredAllegiances.append(rawAllegiance)
        elif rawAllegiance.legacy() in rawUsedAllegianceCodes:
            rawFilteredAllegiances.append(rawAllegiance)

    return rawFilteredAllegiances

# This is intended to mimic the logic of GetStockAllegianceFromCode from the
# Traveller Map source code (SecondSurvey.cs). That code handles the precedence
# of the various legacy allegiances by checking different maps in a specific
# order each time it's called. My implementation creates a single map with all
# the allegiances for the given sector. The way the map is populated is key to
# maintaining the same precedence as Traveller Map
def _createDbAllegiances(
        milieu: str,
        rawMetadata: multiverse.RawMetadata,
        rawSystems: typing.Collection[multiverse.RawWorld],
        rawStockAllegiances: typing.Optional[typing.Collection[
            multiverse.RawStockAllegiance
            ]] = None,
        ) -> typing.Dict[str, multiverse.DbAllegiance]: # Returns code to DbAllegiance map
    dbAllegianceCodeMap: typing.Dict[str, multiverse.DbAllegiance] = {}

    # Create database allegiances for the raw allegiances defined in the metadata.
    # These take presence over any stock allegiances. This is done even if the
    # allegiance isn't used in the sector. The reasoning being, if they were worth
    # defining in the the metadata, they're worth having pre-defined in the db for
    # when I add editing.
    if rawMetadata.allegiances():
        # The allegiances defined in the metadata are sometimes redefinitions of
        # stock metadata but without all the information (e.g. missing legacy or
        # base code). In order to keep as much information as possible, if there
        # is a stock allegiance with the same code, name (and base/legacy if
        # supplied in the metadata) then the stock allegiance should be used to
        # fill in any missing data in the metadata definition.

        # NOTE: It's important that the fill list of stock allegiances are used
        # when generating this map (rather than the just the ones used in the
        # sector) as the metadata may contain definitions that aren't actually
        # used but we still want to include them in the list of allegiances added
        # to the database and we still want to use stock allegiances to fill in
        # any missing information for them where possible.
        rawStockAllegiancesCodeMap = {a.code(): a for a in  rawStockAllegiances}

        for rawMetadataAllegiance in rawMetadata.allegiances():
            baseCode = rawMetadataAllegiance.base()
            legacyCode = None

            rawStockAllegiance = rawStockAllegiancesCodeMap.get(rawMetadataAllegiance.code())
            if rawStockAllegiance:
                useStockInfo = \
                    rawStockAllegiance.name() == rawMetadataAllegiance.name() and \
                    ((not baseCode) or (rawStockAllegiance.base() == baseCode))
                if useStockInfo:
                    if not baseCode:
                        baseCode = rawStockAllegiance.base()
                    legacyCode = rawStockAllegiance.legacy()

            dbAllegianceCodeMap[rawMetadataAllegiance.code()] = multiverse.DbAllegiance(
                code=rawMetadataAllegiance.code(),
                name=rawMetadataAllegiance.name(),
                base=baseCode,
                legacy=legacyCode)

    # Get the allegiance codes used in the sector
    rawUsedAllegianceCodes = _findUsedAllegianceCodes(
        rawMetadata=rawMetadata,
        rawSystems=rawSystems)

    # Get stock allegiances for this sector. This is any stock allegiances referenced in
    # the sector data along with any unused allegiances that are seen as worth having
    # pre-defined for the user when I add editing. The expectation is, there should be
    # a database entry created for each of these sophonts, unless they're overridden in
    # the sector specific metadata
    rawStockAllegiances = _filterStockAllegiances(
        milieu=milieu,
        rawMetadata=rawMetadata,
        rawUsedAllegianceCodes=rawUsedAllegianceCodes,
        rawStockAllegiances=rawStockAllegiances)

    # Create database allegiances for stock allegiances used by the sector
    for rawStockAllegiance in rawStockAllegiances:
        dbAllegiance = dbAllegianceCodeMap.get(rawStockAllegiance.code())
        if dbAllegiance:
            # The metadata has overridden this allegiance code
            continue

        dbAllegianceCodeMap[rawStockAllegiance.code()] = multiverse.DbAllegiance(
            code=rawStockAllegiance.code(),
            name=rawStockAllegiance.name(),
            legacy=rawStockAllegiance.legacy(),
            base=rawStockAllegiance.base())

    # Find any codes that haven't had database allegiance defined. These might be
    # legacy codes or they might be codes that aren't defined anywhere
    rawMissingAllegianceCodes = []
    for rawCode in rawUsedAllegianceCodes:
        if rawCode not in dbAllegianceCodeMap:
            rawMissingAllegianceCodes.append(rawCode)

    # Create database allegiances for any missing allegiance codes
    if rawMissingAllegianceCodes:
        # Create mapping to use for legacy codes. Only stock allegiances are used here as
        # allegiances defined in the metadata don't support legacy codes.
        rawStockAllegianceLegacyMap: typing.Dict[str, multiverse.RawStockAllegiance] = {}
        for rawStockAllegiance in rawStockAllegiances:
            if rawStockAllegiance.legacy() and rawStockAllegiance.legacy() not in rawStockAllegianceLegacyMap:
                rawStockAllegianceLegacyMap[rawStockAllegiance.legacy()] = rawStockAllegiance

        for rawCode in rawMissingAllegianceCodes:
            if rawCode in dbAllegianceCodeMap:
                continue

            overrideCode = _LegacyAllegianceToT5Overrides.get(rawCode)
            rawStockAllegiance = rawStockAllegianceLegacyMap.get(overrideCode if overrideCode else rawCode)

            if rawStockAllegiance:
                # There is a stock allegiance with a legacy code that matches the missing code.
                # If there is an existing database allegiance that is an exact match or a match
                # where the existing database allegiance is just missing a legacy and/or base code
                # (e.g. because it was defined in the metadata which doesn't support legacy codes),
                # then that existing database allegiance can be used with the legacy/base codes
                # updated if missing. This tries to minimise duplicate database allegiances that
                # just vary by code when sectors use a mix of legacy and T5 allegiance codes.
                # If there is no such existing database allegiance then we need to create a database
                # allegiance that uses the missing code but takes the other information from the
                # raw allegiance. This is done to maintain as much information as possible while
                # still avoiding ending up with multiple database allegiances with the same code.
                dbAllegiance = dbAllegianceCodeMap.get(rawStockAllegiance.code())
                if dbAllegiance:
                    useExisting = \
                        dbAllegiance.name() == rawStockAllegiance.name() and \
                        dbAllegiance.legacy == rawStockAllegiance.legacy() and \
                        dbAllegiance.base() == rawStockAllegiance.base()
                    if not useExisting:
                        # There is an existing database allegiance for this code but it's not using
                        # the same details as the stock allegiance so it's not appropriate to use
                        # for this code. Create a new database allegiance, as the stock allegiance
                        # code is already in use, use the raw code with the rest of the stock details
                        dbAllegiance = multiverse.DbAllegiance(
                            code=rawCode,
                            name=rawStockAllegiance.name(),
                            legacy=rawStockAllegiance.legacy(),
                            base=rawStockAllegiance.base())
                else:
                    # There is no existing database allegiance fro this code so create one
                    dbAllegiance = multiverse.DbAllegiance(
                        code=rawStockAllegiance.code(),
                        name=rawStockAllegiance.name(),
                        legacy=rawStockAllegiance.legacy(),
                        base=rawStockAllegiance.base())
            else:
                # There is no stock allegiance that has a legacy code matching this missing code.
                # All we can do is create a database allegiance with information we do have
                dbAllegiance = multiverse.DbAllegiance(
                    code=rawCode,
                    name=rawCode,
                    legacy=None, # No legacy code known
                    base=None) # No base code know

            dbAllegianceCodeMap[rawCode] = dbAllegiance

            # If the allegiance code was overridden, add a mapping for the real code if it's
            # used and there isn't already a mapping for it
            if rawCode != dbAllegiance.code() and \
                    dbAllegiance.code() not in dbAllegianceCodeMap and \
                    dbAllegiance.code() in rawUsedAllegianceCodes:
                dbAllegianceCodeMap[dbAllegiance.code()] = dbAllegiance

    # When adding a the legacy/base code mappings, it's important to
    # use a copy of the list of values currently in the map rather
    # than iterating over values directly as adding a view entry will
    # invalidate the iterator
    dbAllegiances = list(dbAllegianceCodeMap.values())

    # Add mappings for legacy codes
    for dbAllegiance in dbAllegiances:
        if not dbAllegiance.legacy():
            continue
        if dbAllegiance.legacy() in dbAllegianceCodeMap:
            continue
        if dbAllegiance.legacy() not in rawUsedAllegianceCodes:
            continue
        dbAllegianceCodeMap[dbAllegiance.legacy()] = dbAllegiance

    # Add mappings for base codes
    for dbAllegiance in dbAllegiances:
        if not dbAllegiance.base():
            continue
        if dbAllegiance.base() in dbAllegianceCodeMap:
            continue
        if dbAllegiance.base() not in rawUsedAllegianceCodes:
            continue
        dbAllegianceCodeMap[dbAllegiance.base()] = dbAllegiance

    return dbAllegianceCodeMap

# This code generates a code for a sophont name following the rules defined on
# the Traveller Wiki (at least as best as I can understand them)
# https://wiki.travellerrpg.com/Sophont_Code
def _generateSophontCode(name: str, existingCodes: typing.Collection[str]) -> str:
    length = len(name)
    code = ''
    for i in range(4):
        char = name[i] if i < length else 'X'
        code += char if char.isalpha() else 'X'

    if code not in existingCodes:
        return code

    original = code
    for i in range(len(code) - 1, -1, -1):
        code = original
        prefix = code[:i]
        suffix = code[i + 1:]
        for j in range(25):
            old = ord(code[i])
            new = old + j + 1
            if old <= 90 and new > 90:
                new -= 26
            elif old <= 122 and new > 122:
                new -= 26

            code = prefix + chr(new) + suffix
            if code not in existingCodes:
                return code

    raise RuntimeError(f'Unable to generate unused code for sophont {name}')

def _createDbSophonts(
        rawSystems: typing.Collection[multiverse.RawWorld],
        rawStockSophonts: typing.Optional[typing.Collection[
            multiverse.RawStockSophont
            ]] = None,
        ) -> typing.Tuple[
            typing.Dict[str, multiverse.DbSophont], # Code to DbSophont map
            typing.Dict[str, multiverse.DbSophont]]: # Name to DbSophont map
    rawStockSophontCodeMap: typing.Dict[str, multiverse.RawStockSophont] = {}
    rawStockSophontNameMap: typing.Dict[str, multiverse.RawStockSophont] = {}
    if rawStockSophonts:
        for rawStockSophont in rawStockSophonts:
            if rawStockSophont.code() in rawStockSophontCodeMap:
                raise RuntimeError(f'Stock sophonts contain multiple sophonts with the code {rawStockSophont.code()}')
            rawStockSophontCodeMap[rawStockSophont.code()] = rawStockSophont

            if rawStockSophont.name() in rawStockSophontNameMap:
                raise RuntimeError(f'Stock sophonts contain multiple sophonts with the code {rawStockSophont.name()}')
            rawStockSophontNameMap[rawStockSophont.name()] = rawStockSophont

    rawUsedSophontCodes: typing.Set[str] = set()
    rawUsedSophontNames: typing.Set[str] = set()
    rawMajorSophontNames: typing.Set[str] = set(_StockMajorSophonts)
    if rawSystems:
        for rawWorld in rawSystems:
            rawRemarks = rawWorld.attribute(multiverse.WorldAttribute.Remarks)
            if not rawRemarks:
                continue
            matches = _T5SophontPopulationRemarkPattern.findall(rawRemarks)
            for match in matches:
                rawUsedSophontCodes.add(match)

            matches = _LegacySophontPopulationRemarkPattern.findall(rawRemarks)
            for match in matches:
                rawUsedSophontCodes.add(match)

            matches = _MajorSophontHomeWorldRemarkPattern.findall(rawRemarks)
            for match in matches:
                rawUsedSophontNames.add(match)
                rawMajorSophontNames.add(match)

            matches = _MinorSophontHomeWorldRemarkPattern.findall(rawRemarks)
            for match in matches:
                rawUsedSophontNames.add(match)

            matches = _DieBackSophontRemarkPattern.findall(rawRemarks)
            for match in matches:
                rawUsedSophontNames.add(match)

    dbSophontCodeMap: typing.Dict[str, multiverse.DbSophont] = {}
    dbSophontNameMap: typing.Dict[str, multiverse.DbSophont] = {}
    if rawUsedSophontCodes or rawUsedSophontNames:
        # IMPORTANT: Names MUST be processed before codes as we need codes for
        # names that don't match a stock sophont to have been generated first
        # so the DbSophont for that code is used when processing the used codes.
        for rawSophontName in rawUsedSophontNames:
            if rawSophontName in dbSophontNameMap:
                continue

            rawStockSophont = rawStockSophontNameMap.get(rawSophontName)

            if rawStockSophont:
                dbSophont = multiverse.DbSophont(
                    code=rawStockSophont.code(),
                    name=rawStockSophont.name(),
                    isMajor=rawSophontName in rawMajorSophontNames)
            else:
                # TODO: Log something if there is no stock sophont. If this is a custom
                # sector the user should also be informed. I'm not sure if there is anything
                # the user could actually do though. I think I really need to extend the
                # metadata file format so sophonts can be specified with the idea being you
                # should to define any sophonts that are used in the sector that aren't
                # covered by the stock sophonts

                # There is no stock sophont and therefore no predefined code, so generate
                # one instead
                dbSophontCode = _generateSophontCode(
                    name=rawSophontName,
                    existingCodes=dbSophontCodeMap.keys())
                dbSophont = multiverse.DbSophont(
                    code=dbSophontCode,
                    name=rawSophontName,
                    isMajor=rawSophontName in rawMajorSophontNames)

            dbSophontNameMap[rawSophontName] = dbSophont

            # Add a mapping for the sophont code if it's used but there isn't
            # already a mapping
            if dbSophont.code() not in dbSophontCodeMap and \
                    dbSophont.code() in rawUsedSophontCodes:
                dbSophontCodeMap[dbSophont.code()] = dbSophont

        for rawSophontCode in rawUsedSophontCodes:
            if rawSophontCode in dbSophontCodeMap:
                continue

            overrideCode = _LegacySophontMap.get(rawSophontCode)
            rawStockSophont = rawStockSophontCodeMap.get(overrideCode if overrideCode else rawSophontCode)

            if rawStockSophont:
                # There is a stock sophont that matches the code. If there is no
                # DbSophont for that code then one needs to be created. If there
                # is an existing entry then it is used, it still needs to have a
                # mapping added to the code map for the original raw sophont code
                # as that is the code it's referenced by in the sector data.
                dbSophont = dbSophontCodeMap.get(rawStockSophont.code())
                if not dbSophont:
                    dbSophont = multiverse.DbSophont(
                        code=rawStockSophont.code(),
                        name=rawStockSophont.name(),
                        isMajor=rawStockSophont.name() in rawMajorSophontNames)
            else:
                # There is no stock sophont that matches the code. Create a new
                # DbSophont using the information we do have.

                # TODO: Log something if there is no stock sophont. If this is a custom
                # sector the user should also be informed. I'm not sure if there is anything
                # the user could actually do though. I think I really need to extend the
                # metadata file format so sophonts can be specified with the idea being you
                # should to define any sophonts that are used in the sector that aren't
                # covered by the stock sophonts

                # TODO: This should generate a name to make sure it is unique
                dbSophont = multiverse.DbSophont(
                    code=rawSophontCode,
                    name=rawSophontCode,
                    isMajor=False)

            dbSophontCodeMap[rawSophontCode] = dbSophont

            # If the sophont code was overridden, add an mapping for the real code if it's
            # used and there isn't a mapping for it already
            if rawSophontCode != dbSophont.code() and \
                    dbSophont.code() not in dbSophontCodeMap and \
                    dbSophont.code() in rawUsedSophontCodes:
                dbSophontCodeMap[dbSophont.code()] = dbSophont

            # Add a mapping for the sophont name if it's used but there isn't
            # already a mapping
            if dbSophont.name() not in dbSophontNameMap and \
                    dbSophont.name() in rawUsedSophontNames:
                dbSophontNameMap[dbSophont.name()] = dbSophont

    return (dbSophontCodeMap, dbSophontNameMap)

# TODO: Not sure where this should live
_T5OfficialAllegiancesPath = "t5ss/allegiance_codes.tab"
def readSnapshotStockAllegiances() -> typing.List[multiverse.RawStockAllegiance]:
    return multiverse.readTabStockAllegiances(
        content=multiverse.SnapshotManager.instance().loadTextResource(
            filePath=_T5OfficialAllegiancesPath))

_T5OfficialSophontsPath = "t5ss/sophont_codes.tab"
def readSnapshotStockSophonts() -> typing.List[multiverse.RawStockSophont]:
    return multiverse.readTabStockSophonts(
        content=multiverse.SnapshotManager.instance().loadTextResource(
            filePath=_T5OfficialSophontsPath))

def convertRawUniverseToDbUniverse(
        universeName: str,
        isCustom: bool,
        rawSectors: typing.Collection[typing.Tuple[
            str, # Milieu
            multiverse.RawMetadata,
            typing.Collection[multiverse.RawWorld]
            ]],
        rawStockAllegiances: typing.Optional[typing.Collection[
            multiverse.RawStockAllegiance
            ]] = None,
        rawStockSophonts: typing.Optional[typing.Collection[
            multiverse.RawStockSophont
            ]] = None,
        universeId: typing.Optional[str] = None,
        progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
        ) -> multiverse.DbUniverse:
    dbUniverse = multiverse.DbUniverse(
        id=universeId,
        name=universeName)
    totalSectorCount = len(rawSectors)
    for progressCount, (milieu, rawMetadata, rawSystems) in enumerate(rawSectors):
        if progressCallback:
            progressCallback(
                f'Converting: {milieu} - {rawMetadata.canonicalName()}',
                progressCount,
                totalSectorCount)

        dbUniverse.addSector(convertRawSectorToDbSector(
            milieu=milieu,
            rawMetadata=rawMetadata,
            rawSystems=rawSystems,
            rawStockAllegiances=rawStockAllegiances,
            rawStockSophonts=rawStockSophonts,
            isCustom=isCustom))

    if progressCallback:
        progressCallback(
            f'Converting: Complete!',
            totalSectorCount,
            totalSectorCount)

    return dbUniverse

# TODO: This should do some basic sanity tests on the passed on data (e.g. doesn't have multiple worlds with the same hex)
def convertRawSectorToDbSector(
        milieu: str,
        rawMetadata: multiverse.RawMetadata,
        rawSystems: typing.Collection[multiverse.RawWorld],
        isCustom: bool,
        rawStockAllegiances: typing.Optional[typing.Collection[
            multiverse.RawStockAllegiance
            ]] = None,
        rawStockSophonts: typing.Optional[typing.Collection[
            multiverse.RawStockSophont
            ]] = None,
        sectorId: typing.Optional[str] = None,
        universeId: typing.Optional[str] = None,
        ) -> multiverse.DbUniverse:
        dbAlternateNames = None
        if rawMetadata.alternateNames():
            dbAlternateNames = [(name, rawMetadata.nameLanguage(name)) for name in rawMetadata.alternateNames()]

        dbSubsectorNames = None
        if rawMetadata.subsectorNames():
            dbSubsectorNames = []
            for code, name in rawMetadata.subsectorNames().items():
                if not name:
                    continue
                dbSubsectorNames.append((ord(code) - ord('A'), name))

        dbProducts = None
        rawSources = rawMetadata.sources()
        rawPrimarySource = rawSources.primary() if rawSources else None
        if rawSources and rawSources.products():
            dbProducts = []
            for product in rawSources.products():
                dbProducts.append(multiverse.DbProduct(
                    publication=product.publication(),
                    author=product.author(),
                    publisher=product.publisher(),
                    reference=product.reference()))

        dbAllegianceCodeMap = _createDbAllegiances(
            milieu=milieu,
            rawMetadata=rawMetadata,
            rawSystems=rawSystems,
            rawStockAllegiances=rawStockAllegiances)

        dbSophontCodeMap, dbSophontNameMap = _createDbSophonts(
            rawSystems=rawSystems,
            rawStockSophonts=rawStockSophonts)

        dbSystems = None
        if rawSystems:
            dbSystems = []
            for rawWorld in rawSystems:
                rawHex = rawWorld.attribute(multiverse.WorldAttribute.Hex)
                if not rawHex:
                    assert(False) # TODO: Better error handling

                rawUWP = rawWorld.attribute(multiverse.WorldAttribute.UWP)
                dbStarport = None
                dbWorldSize = None
                dbAtmosphere = None
                dbHydrographics = None
                dbPopulation = None
                dbGovernment = None
                dbLawLevel = None
                dbTechLevel = None
                if rawUWP:
                    dbStarport, dbWorldSize, dbAtmosphere, dbHydrographics, dbPopulation, \
                        dbGovernment, dbLawLevel, dbTechLevel = multiverse.parseSystemUWPString(uwp=rawUWP)

                rawSystemWorlds = rawWorld.attribute(multiverse.WorldAttribute.SystemWorlds)

                rawAllegianceCode = rawWorld.attribute(multiverse.WorldAttribute.Allegiance)
                dbAllegiance = dbAllegianceCodeMap.get(rawAllegianceCode) if rawAllegianceCode else None
                if rawAllegianceCode and not dbAllegiance:
                    # TODO: This should probably log and continue with no allegiance,
                    # if it's a custom sector it should also warn the user
                    raise RuntimeError(f'World at {rawHex} in {rawMetadata.canonicalName()} at {milieu} uses undefined allegiance code {rawAllegianceCode}')

                rawNobilities = rawWorld.attribute(multiverse.WorldAttribute.Nobility)
                dbNobilities = None
                if rawNobilities:
                    dbNobilities = []
                    seenNobilities = set()
                    for nobilityCode in multiverse.parseSystemNobilityString(string=rawNobilities):
                        if nobilityCode in seenNobilities:
                            continue # Ignore duplicates
                        seenNobilities.add(nobilityCode)

                        dbNobilities.append(multiverse.DbNobility(code=nobilityCode))

                rawBases = rawWorld.attribute(multiverse.WorldAttribute.Bases)
                dbBases = None
                if rawBases:
                    dbBases = []
                    seenBases = set()
                    for baseCode in multiverse.parseSystemBasesString(string=rawBases):
                        if baseCode in seenBases:
                            continue # Ignore duplicates
                        seenBases.add(baseCode)

                        dbBases.append(multiverse.DbBase(code=baseCode))

                rawStellar = rawWorld.attribute(multiverse.WorldAttribute.Stellar)
                dbStars = None
                if rawStellar:
                    dbStars = []
                    for luminosityClass, spectralClass, spectralScale in multiverse.parseSystemStellarString(string=rawStellar):
                        dbStars.append(multiverse.DbStar(
                            luminosityClass=luminosityClass,
                            spectralClass=spectralClass,
                            spectralScale=spectralScale))

                rawRemarks = rawWorld.attribute(multiverse.WorldAttribute.Remarks)
                dbTradeCodes: typing.Optional[typing.List[multiverse.DbTradeCode]] = None
                dbSophontPopulations: typing.Optional[typing.List[multiverse.DbSophontPopulation]]  = None
                dbRulingAllegiances: typing.Optional[typing.List[multiverse.RawAllegiance]]  = None
                dbOwningSystems: typing.Optional[typing.List[multiverse.DbOwningSystem]]  = None
                dbColonySystems: typing.Optional[typing.List[multiverse.DbColonySystem]]  = None
                dbResearchStations: typing.Optional[typing.List[multiverse.DbResearchStation]]  = None
                dbCustomRemarks: typing.Optional[typing.List[multiverse.DbCustomRemark]]  = None
                if rawRemarks:
                    rawTradeCodes, rawMajorHomeWorlds, rawMinorHomeWorlds, rawSophontPopulations, \
                        rawDieBackSophonts, rawOwningSystems, rawColonySystems, rawRulingAllegiances, \
                        rawResearchStations, rawUnrecognisedRemarks = multiverse.parseSystemRemarksString(rawRemarks)

                    if rawTradeCodes:
                        # It's important to process the explicit trade codes first as
                        # trade codes may be added by later steps (e.g. for die back
                        # worlds)
                        dbTradeCodes = []
                        seenTradeCodes = set()
                        for rawTradeCode in rawTradeCodes:
                            if rawTradeCode in seenTradeCodes:
                                continue # Skip duplicates
                            seenTradeCodes.add(rawTradeCode)

                            dbTradeCodes.append(multiverse.DbTradeCode(code=rawTradeCode))

                    if rawMajorHomeWorlds or rawMinorHomeWorlds or rawSophontPopulations or rawDieBackSophonts:
                        dbSophontPopulations = []
                        seenDbSophonts = set()

                        for rawSophontName, rawPopulation in rawMajorHomeWorlds:
                            dbSophont = dbSophontNameMap.get(rawSophontName)
                            if not dbSophont:
                                # This should never happen, the remarks should already have been
                                # processed to extract all the used sophont names & codes and
                                # DbSophont instances should have been created for all of them
                                # TODO: Better exception string
                                raise RuntimeError('This shouldn\'t happen')
                            if dbSophont in seenDbSophonts:
                                # There is already a population entry for this sophont so
                                # ignore this one
                                # TODO: This should log and probably inform the user if it's
                                # a custom sector that's being converted
                                # TODO: I think I need to write my own linting code that
                                # will check for things like repeated sophonts or multiple
                                # owning worlds in remarks
                                continue
                            seenDbSophonts.add(dbSophont)

                            dbSophontPopulations.append(multiverse.DbSophontPopulation(
                                sophont=dbSophont,
                                percentage=rawPopulation,
                                isHomeWorld=True,
                                isDieBack=False))

                        for rawSophontName, rawPopulation in rawMinorHomeWorlds:
                            dbSophont = dbSophontNameMap.get(rawSophontName)
                            if not dbSophont:
                                # This should never happen, the remarks should already have been
                                # processed to extract all the used sophont names & codes and
                                # DbSophont instances should have been created for all of them
                                # TODO: Better exception string
                                raise RuntimeError('This shouldn\'t happen')
                            if dbSophont in seenDbSophonts:
                                # There is already a population entry for this sophont so
                                # ignore this one
                                # TODO: This should log and probably inform the user if it's
                                # a custom sector that's being converted
                                continue
                            seenDbSophonts.add(dbSophont)

                            dbSophontPopulations.append(multiverse.DbSophontPopulation(
                                sophont=dbSophont,
                                percentage=rawPopulation,
                                isHomeWorld=True,
                                isDieBack=False))

                        for rawSophontCode, rawPopulation in rawSophontPopulations:
                            dbSophont = dbSophontCodeMap.get(rawSophontCode)
                            if not dbSophont:
                                # This should never happen, the remarks should already have been
                                # processed to extract all the used sophont names & codes and
                                # DbSophont instances should have been created for all of them
                                # TODO: Better exception string
                                raise RuntimeError('This shouldn\'t happen')
                            if dbSophont in seenDbSophonts:
                                # There is already a population entry for this sophont so
                                # ignore this one
                                # TODO: This should log and probably inform the user if it's
                                # a custom sector that's being converted
                                continue
                            seenDbSophonts.add(dbSophont)

                            dbSophontPopulations.append(multiverse.DbSophontPopulation(
                                sophont=dbSophont,
                                percentage=rawPopulation,
                                isHomeWorld=False,
                                isDieBack=False))

                        for rawSophontName in rawDieBackSophonts:
                            dbSophont = dbSophontNameMap.get(rawSophontName)
                            if not dbSophont:
                                # This should never happen, the remarks should already have been
                                # processed to extract all the used sophont names & codes and
                                # DbSophont instances should have been created for all of them
                                # TODO: Better exception string
                                raise RuntimeError('This shouldn\'t happen')
                            if dbSophont in seenDbSophonts:
                                # There is already a population entry for this sophont so
                                # ignore this one
                                # TODO: This should log and probably inform the user if it's
                                # a custom sector that's being converted
                                continue
                            seenDbSophonts.add(dbSophont)

                            dbSophontPopulations.append(multiverse.DbSophontPopulation(
                                sophont=dbSophont,
                                percentage=None,
                                isHomeWorld=False,
                                isDieBack=True))

                            # Add the Die Back trade code if the system doesn't already have it
                            if not dbTradeCodes:
                                dbTradeCodes = [multiverse.DbTradeCode(code='Di')]
                            elif not any(dbCode.code() == 'Di' for dbCode in dbTradeCodes):
                                dbTradeCodes.append(multiverse.DbTradeCode(code='Di'))

                    if rawOwningSystems:
                        dbOwningSystems = []
                        for hexX, hexY, sectorCode in rawOwningSystems:
                            dbOwningSystems.append(multiverse.DbOwningSystem(
                                hexX=hexX,
                                hexY=hexY,
                                # If the sector code is the same as the current sector code
                                # (aka abbreviation) then set a value of None to indicate the
                                # current sector
                                sectorCode=sectorCode if sectorCode != rawMetadata.abbreviation() else None))

                    if rawColonySystems:
                        dbColonySystems = []
                        for hexX, hexY, sectorCode in rawColonySystems:
                            dbColonySystems.append(multiverse.DbColonySystem(
                                hexX=hexX,
                                hexY=hexY,
                                # If the sector code is the same as the current sector code
                                # (aka abbreviation) then set a value of None to indicate the
                                # current sector
                                sectorCode=sectorCode if sectorCode != rawMetadata.abbreviation() else None))

                    if rawRulingAllegiances:
                        dbRulingAllegiances = []
                        seenRulingAllegiances = set()
                        for rawAllegianceCode in rawRulingAllegiances:
                            if rawAllegianceCode in seenRulingAllegiances:
                                continue # Skip duplicates
                            seenRulingAllegiances.add(rawAllegianceCode)

                            dbAllegiance = dbAllegianceCodeMap.get(rawAllegianceCode)
                            if not dbAllegiance:
                                # TODO: This should probably log and continue with no allegiance,
                                # if it's a custom sector it should also warn the user
                                raise RuntimeError(f'Military rule trade code (Mr) in {rawMetadata.canonicalName()} at {milieu} uses undefined allegiance code {rawAllegianceCode}')
                            dbRulingAllegiances.append(multiverse.DbRulingAllegiance(allegiance=dbAllegiance))

                    if rawResearchStations:
                        dbResearchStations = []
                        seenResearchStations = set()
                        for rawResearchStation in rawResearchStations:
                            if rawResearchStation in seenResearchStations:
                                continue # Skip duplicates
                            seenResearchStations.add(rawResearchStation)

                            dbResearchStations.append(multiverse.DbResearchStation(code=rawResearchStation))

                    if rawUnrecognisedRemarks:
                        dbCustomRemarks = []
                        for remark in rawUnrecognisedRemarks:
                            dbCustomRemarks.append(multiverse.DbCustomRemark(remark=remark))

                dbSystems.append(multiverse.DbSystem(
                    hexX=int(rawHex[:2]),
                    hexY=int(rawHex[-2:]),
                    # TODO: Should I make name optional? Some sectors don't have names
                    # (e.g. some of the ones that have a UWP of ???????-?).
                    name=rawWorld.attribute(multiverse.WorldAttribute.Name),
                    starport=dbStarport,
                    worldSize=dbWorldSize,
                    atmosphere=dbAtmosphere,
                    hydrographics=dbHydrographics,
                    population=dbPopulation,
                    government=dbGovernment,
                    lawLevel=dbLawLevel,
                    techLevel=dbTechLevel,
                    economics=rawWorld.attribute(multiverse.WorldAttribute.Economics),
                    culture=rawWorld.attribute(multiverse.WorldAttribute.Culture),
                    zone=rawWorld.attribute(multiverse.WorldAttribute.Zone),
                    pbg=rawWorld.attribute(multiverse.WorldAttribute.PBG),
                    # TODO: I think the Traveller Map second survey page clarifies that
                    # system worlds is the number of worlds excluding the main world
                    systemWorlds=int(rawSystemWorlds) if rawSystemWorlds else None,
                    allegiance=dbAllegiance,
                    nobilities=dbNobilities,
                    tradeCodes=dbTradeCodes,
                    sophontPopulations=dbSophontPopulations,
                    rulingAllegiances=dbRulingAllegiances,
                    owningSystems=dbOwningSystems,
                    colonySystems=dbColonySystems,
                    researchStations=dbResearchStations,
                    customRemarks=dbCustomRemarks,
                    bases=dbBases,
                    stars=dbStars))

        dbRoutes = None
        if rawMetadata.routes():
            dbRoutes = []
            for rawRoute in rawMetadata.routes():
                rawStartHex = rawRoute.startHex()
                rawEndHex = rawRoute.endHex()
                rawStartOffsetX = rawRoute.startOffsetX()
                rawStartOffsetY = rawRoute.startOffsetY()
                rawEndOffsetX = rawRoute.endOffsetX()
                rawEndOffsetY = rawRoute.endOffsetY()

                rawAllegianceCode = rawRoute.allegiance()
                dbAllegiance = dbAllegianceCodeMap.get(rawAllegianceCode) if rawAllegianceCode else None
                if rawAllegianceCode and not dbAllegiance:
                    # TODO: This should probably log and continue with no allegiance,
                    # if it's a custom sector it should also warn the user
                    raise RuntimeError(f'Route in {rawMetadata.canonicalName()} at {milieu} uses undefined allegiance code {rawAllegianceCode}')

                dbRoutes.append(multiverse.DbRoute(
                    startHexX=int(rawStartHex[:2]),
                    startHexY=int(rawStartHex[-2:]),
                    endHexX=int(rawEndHex[:2]),
                    endHexY=int(rawEndHex[-2:]),
                    startOffsetX=rawStartOffsetX if rawStartOffsetX is not None else 0,
                    startOffsetY=rawStartOffsetY if rawStartOffsetY is not None else 0,
                    endOffsetX=rawEndOffsetX if rawEndOffsetX is not None else 0,
                    endOffsetY=rawEndOffsetY if rawEndOffsetY is not None else 0,
                    type=rawRoute.type(),
                    style=rawRoute.style(),
                    colour=rawRoute.colour(),
                    width=rawRoute.width(),
                    allegiance=dbAllegiance))

        dbBorders = None
        if rawMetadata.borders():
            dbBorders = []
            for rawBorder in rawMetadata.borders():
                dbHexes = []
                for rawHex in rawBorder.hexList():
                    dbHexes.append((int(rawHex[:2]), int(rawHex[-2:])))

                rawLabel = rawBorder.label()
                rawShowLabel = rawBorder.showLabel()
                rawWrapLabel = rawBorder.wrapLabel()
                rawLabelHex = rawBorder.labelHex()

                rawAllegianceCode = rawBorder.allegiance()
                dbAllegiance = dbAllegianceCodeMap.get(rawAllegianceCode) if rawAllegianceCode else None
                if rawAllegianceCode and not dbAllegiance:
                    # TODO: This should probably log and continue with no allegiance,
                    # if it's a custom sector it should also warn the user
                    raise RuntimeError(f'Border in {rawMetadata.canonicalName()} at {milieu} uses undefined allegiance code {rawAllegianceCode}')

                dbBorders.append(multiverse.DbBorder(
                    hexes=dbHexes,
                    showLabel=rawShowLabel if rawShowLabel is not None else True,
                    wrapLabel=rawWrapLabel if rawWrapLabel is not None else False,
                    label=rawLabel,
                    labelHexX=int(rawLabelHex[:2]) if rawLabelHex is not None else None,
                    labelHexY=int(rawLabelHex[-2:]) if rawLabelHex is not None else None,
                    labelOffsetX=rawBorder.labelOffsetX(),
                    labelOffsetY=rawBorder.labelOffsetY(),
                    colour=rawBorder.colour(),
                    style=rawBorder.style(),
                    allegiance=dbAllegiance))

        dbRegions = None
        if rawMetadata.regions():
            dbRegions = []
            for rawRegion in rawMetadata.regions():
                dbHexes = []
                for rawHex in rawRegion.hexList():
                    dbHexes.append((int(rawHex[:2]), int(rawHex[-2:])))

                rawLabel = rawRegion.label()
                rawShowLabel = rawRegion.showLabel()
                rawWrapLabel = rawRegion.wrapLabel()
                rawLabelHex = rawRegion.labelHex()

                dbRegions.append(multiverse.DbRegion(
                    hexes=dbHexes,
                    showLabel=rawShowLabel if rawShowLabel is not None else True,
                    wrapLabel=rawWrapLabel if rawWrapLabel is not None else False,
                    label=rawRegion.label(),
                    labelHexX=int(rawLabelHex[:2]) if rawLabelHex is not None else None,
                    labelHexY=int(rawLabelHex[-2:]) if rawLabelHex is not None else None,
                    labelOffsetX=rawRegion.labelOffsetX(),
                    labelOffsetY=rawRegion.labelOffsetY(),
                    colour=rawRegion.colour()))

        dbLabels = None
        if rawMetadata.labels():
            dbLabels = []
            for rawLabel in rawMetadata.labels():
                rawHex = rawLabel.hex()
                rawWrap = rawLabel.wrap()

                dbLabels.append(multiverse.DbLabel(
                    text=rawLabel.text(),
                    hexX=int(rawHex[:2]),
                    hexY=int(rawHex[-2:]),
                    wrap=rawWrap if rawWrap is not None else False,
                    colour=rawLabel.colour(),
                    size=rawLabel.size(),
                    offsetX=rawLabel.offsetX(),
                    offsetY=rawLabel.offsetY()))

        return multiverse.DbSector(
            id=sectorId,
            universeId=universeId,
            isCustom=isCustom,
            milieu=milieu,
            sectorX=rawMetadata.x(),
            sectorY=rawMetadata.y(),
            primaryName=rawMetadata.canonicalName(),
            primaryLanguage=rawMetadata.nameLanguage(rawMetadata.canonicalName()),
            alternateNames=dbAlternateNames,
            abbreviation=rawMetadata.abbreviation(),
            sectorLabel=rawMetadata.sectorLabel(),
            subsectorNames=dbSubsectorNames,
            selected=rawMetadata.selected() if rawMetadata.selected() is not None else False,
            tags=rawMetadata.tags(),
            styleSheet=rawMetadata.styleSheet(),
            credits=rawSources.credits() if rawSources else None,
            publication=rawPrimarySource.publication() if rawPrimarySource else None,
            author=rawPrimarySource.author() if rawPrimarySource else None,
            publisher=rawPrimarySource.publisher() if rawPrimarySource else None,
            reference=rawPrimarySource.reference() if rawPrimarySource else None,
            products=dbProducts,
            allegiances=set(dbAllegianceCodeMap.values()), # Use unique allegiances
            sophonts=set(itertools.chain(dbSophontCodeMap.values(), dbSophontNameMap.values())), # Use unique sophonts
            systems=dbSystems,
            routes=dbRoutes,
            borders=dbBorders,
            regions=dbRegions,
            labels=dbLabels)
