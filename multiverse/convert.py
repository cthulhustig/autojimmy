import common
import logging
import itertools
import math
import multiverse
import re
import survey
import typing

# TODO: The conversion process needs to give better error/warning/info
# feedback to the user when converting custom sectors (converting the
# default universe should just log)
# TODO: Need code to allow export from db to file. I deleted the old
# code that did it as it had bit rotted
# TODO: A lot of places where I'm constructing DB objects, I should
# wrap them in a try/except and log and continue if they throw.
# TODO: I need away to export sectors to metadata/tab formats (i.e. convert
# DbObjects back to RawObjects then save)
# TODO: The data from the label files (mega_labels.tab, minor_labels.tab, Worlds.xml)
# should be integrated into the data written to the database. These changes will need
# an update to the rendering code as it will need to pull the data from the universe
# rather than static files
# - mega_labels.tab & minor_labels.tab probably need to be separate label tables. Either
# a table for each type or a single table with a column to indicate the type. I could
# include the min/max scale values that determine when they're shown so the user can
# customise it when I add a UI
# - Worlds.xml data needs to be added to the world table. Adding it to the remarks seems
# the obvious choice. It might even be there already as it seems to all relate to the
# major sophont home worlds & major allegiance capitals
# TODO: Need to move the vectors in data\map\vectors into the database as well so the
# user can edit them for their universe. This will also need an update to the rendering
# code
# TODO: It would probably be a good idea to store the zoomed out galaxy bitmap in the
# database as well. Remember there are two, one for light and one for dark maps. Again
# this will need an update to the rendering code but it should be trivial. I think it
# makes sense to leave the candy images as static files as they're more part of the
# rendering system than the universe

# Useful Test Locations:
# - Sector: Tsebntsiatldlants
#   - There is a route that runs the length of it (e.g. through Oiansh) that
#     should be dashed purple. The colour and style come from it using the
#     "Core Route" type which is the only type defined in the otu css file
#     that has a space in the name.
# - Sector: Glimmerdrift Reaches (Judges Guild)
#   - A lot of the borders in this sector use a dashed salmon pink colour. They get
#     this from the default border colour in the metadata style sheet info (i.e.
#     not the otu css file)
#   - Some of the routes are extra chunky because they use the Special type which
#     has a custom width defined in the metadata style sheet info (e.g ones
#     going into Rasma)
# - Sector: Far Frontiers
#   - The routes for the worlds around Bestus should be grey, not green. They can
#     get go wrong if the order the style sheet groups are looked up are messed up.
#     The reason it gets messed up is it relies on the colour not being taken from
#     the "Im" allegiance style because the route has a type specified (even though
#     that type doesn't have a style defined)
# -  Vanguard Reaches (Don McKinney 2015)
#   - There is a red route running vertically (e.g. through Cloister) that gets
#     its colour from the allegiance of Im on the route and the custom colour
#     specified for Im in the metadata style sheet info
#   - This is also a very colourful sector with lots of different borders and
#     regions
# - Sector: Far Home
#   - Routes in this sector have a custom default colour specified in the metadata
#     stylesheet info (such as those going through Iridina)
# - Sector: The Beyond
#   - When using Atlas style, the route between Djend and Morphy should be
#     solid rather than dashed. The special case for grayscale rendering in
#     my _drawMicroRoutes shouldn't kick in
# - System: Inast (Gateway)
#   - Has a ruling allegiance
# - System: Yeasea (Dark Nebula)
#   - Has an owner in another sector
# - System: Uyar (Datsatl)
#   - Has a colony
# - System: 551-458 (Storr)
#   - Has 6 stars of different types
# - System: Aestera (Storr)
#   - Has 3 bases
# - System: Ziruushda (Dagudashaag)
#   - Has 4 sophonts
# - System: Garden (Reft)
#   - Has a named die back sophont
# - System: Beta Station (Joyce's Void)
#   - Has research station
# - System: Canoga (Ilelish)
#   - Has 5 nobilities

# These unofficial allegiances are taken from Traveller Map. It has a
# comment saying they're for M1120 but as far as I can tell it uses
# them no mater which milieu you have selected. In my implementation
# they are only used for M1120 & M1121
_T5UnofficialM112xAllegiances = [
    # -----------------------
    # Unofficial/Unreviewed
    # -----------------------
    survey.RawStockAllegiance(code='FdAr', legacy='Fa', base=None, name='Federation of Arden' ),
    survey.RawStockAllegiance(code='BoWo', legacy='Bw', base=None, name='Border Worlds' ),
    survey.RawStockAllegiance(code='LuIm', legacy='Li', base='Im', name='Lucan\'s Imperium' ),
    survey.RawStockAllegiance(code='MaSt', legacy='Ma', base='Im', name='Maragaret\'s Domain' ),
    survey.RawStockAllegiance(code='BaCl', legacy='Bc', base=None, name='Backman Cluster' ),
    survey.RawStockAllegiance(code='FdDa', legacy='Fd', base='Im', name='Federation of Daibei' ),
    survey.RawStockAllegiance(code='FdIl', legacy='Fi', base='Im', name='Federation of Ilelish' ),
    survey.RawStockAllegiance(code='AvCn', legacy='Ac', base=None, name='Avalar Consulate' ),
    survey.RawStockAllegiance(code='CoAl', legacy='Ca', base=None, name='Corsair Alliance' ),
    survey.RawStockAllegiance(code='StIm', legacy='St', base='Im', name='Strephon\'s Worlds' ),
    survey.RawStockAllegiance(code='ZiSi', legacy='Rv', base='Im', name='Restored Vilani Imperium' ), # Ziru Sirka
    survey.RawStockAllegiance(code='VA16', legacy='V6', base=None, name='Assemblage of 1116' ),
    survey.RawStockAllegiance(code='CRVi', legacy='CV', base=None, name='Vilani Cultural Region' ),
    survey.RawStockAllegiance(code='CRGe', legacy='CG', base=None, name='Geonee Cultural Region' ),
    survey.RawStockAllegiance(code='CRSu', legacy='CS', base=None, name='Suerrat Cultural Region' ),
    survey.RawStockAllegiance(code='CRAk', legacy='CA', base=None, name='Anakudnu Cultural Region' )
    ]
_T5UnofficialAllegiancesMap = {
    'M1120': _T5UnofficialM112xAllegiances,
    'M1121': _T5UnofficialM112xAllegiances,
    }

# These allegiances are take from Traveller Map (SecondSurvey.cs)
# Cases where T5SS codes don't apply: e.g. the Hierate or Imperium, or where no codes exist yet
_LegacyAllegiances = [
    survey.RawStockAllegiance(code='As', legacy='As', base='As', name='Aslan Hierate' ), # T5SS: Clan, client state, or unknown; no generic code
    survey.RawStockAllegiance(code='Dr', legacy='Dr', base='Dr', name='Droyne' ), # T5SS: Polity name or unaligned w/ Droyne population
    survey.RawStockAllegiance(code='Im', legacy='Im', base='Im', name='Third Imperium' ), # T5SS: Domain or cultural region; no generic code
    survey.RawStockAllegiance(code='Kk', legacy='Kk', base='Kk', name='The Two Thousand Worlds' ), # T5SS: (Not yet assigned)
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
    # NOTE: The mappings for ?? and -- will have no effect due to the
    # _IgnoreAllegianceCodes list below. I've left them here for
    # completeness
    '??': 'XXXX',
    '--': 'XXXX'
}

# These allegiance codes are used as they're used in sector data to
# indicate no allegiance.
_IgnoreAllegianceCodes = set(['--', '??'])

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

_DieBackTradeCode = 'Di'
_MilitaryRuleTradeCode = 'Mr'
_ResearchStationTradeCode = 'Rs'

_ValidLineStyles = set(['solid', 'dashed', 'dotted'])
_ValidLabelSizes = set(['small', 'large'])

def _formatHexString(hexX: int, hexY: int) -> str:
    return f'{hexX:02d}{hexY:02d}'

def _parseHexString(string: str) -> typing.Tuple[int, int]:
    return (int(string[:2]), int(string[-2:]))

# This is based on the sector world bounds and hex world center code in
# astrometrics. It uses a coordinate space that has the same scale as
# world space coordinates but is relative to the upper left corner of
# the sector.
_ParsecScaleX = math.cos(math.pi / 6) # = cosine 30° = 0.8660254037844387
_HexWidthOffset = math.tan(math.pi / 6) / 4 / _ParsecScaleX # = 0.16666666666666666
def _hexToSectorWorldOffset(
        hexX: int,
        hexY: int,
        worldOffsetX: typing.Optional[float],
        worldOffsetY: typing.Optional[float]
        ) -> typing.Tuple[float, float]:
        worldX = (hexX - 0.5)
        worldX += _HexWidthOffset # Offset of sector origin
        if worldOffsetX is not None:
            worldX += worldOffsetX

        worldY = (hexY - (0.0 if ((hexX % 2) != 0) else -0.5))
        worldY -= 0.5 # Offset of sector origin
        if worldOffsetY is not None:
            worldY += worldOffsetY

        return (worldX, worldY)

def _sectorWorldOffsetToHex(
        worldX: float,
        worldY: float
        ) -> typing.Tuple[int, int, typing.Optional[float], typing.Optional[float]]:
    localX = worldX - _HexWidthOffset
    localY = worldY + 0.5

    hexX = int(localX + 0.5)
    worldOffsetX = localX - (hexX - 0.5)

    yBase = localY - (0.0 if ((hexX % 2) != 0) else -0.5)

    hexY = int(yBase)
    worldOffsetY = yBase - hexY

    return (hexX, hexY, worldOffsetX if worldOffsetX else None, worldOffsetY if worldOffsetY else None)

_SubsectorWidth = 8 # parsecs
_SubsectorHeight = 10 # parsecs
def _hexToSubsectorCode(
        hexX: int,
        hexY: int
        ) -> str:
    indexX = (hexX - 1) // _SubsectorWidth
    indexY = (hexY - 1) // _SubsectorHeight
    return chr(ord('A') + (indexY * 4) + indexX)

def _parseSystemWorldCount(
        rawSystemWorldCount: typing.Optional[str]
        ) -> typing.Optional[int]:
    if rawSystemWorldCount is None:
        return None

    try:
        return int(rawSystemWorldCount)
    except:
        # The number of system worlds should be an integer but wasn't
        # so try parsing it as ehex
        return survey.ehexToInteger(value=rawSystemWorldCount, default=None)

def _findUsedAllegianceCodes(
        rawMetadata: survey.RawMetadata,
        rawSystems: typing.Collection[survey.RawWorld]
        ) -> typing.Set[str]:
    usedCodes: typing.Set[str] = set()
    if rawSystems:
        for rawWorld in rawSystems:
            rawAllegianceCode = rawWorld.allegiance()
            if rawAllegianceCode and rawAllegianceCode not in _IgnoreAllegianceCodes:
                usedCodes.add(rawAllegianceCode)

            rawRemarks = rawWorld.remarks()
            if rawRemarks:
                matches = _MilitaryRuleRemarkPattern.findall(rawRemarks)
                for match in matches:
                    if match not in _IgnoreAllegianceCodes:
                        usedCodes.add(match)
    if rawMetadata.routes():
        for rawRoute in rawMetadata.routes():
            rawAllegianceCode = rawRoute.allegiance()
            if rawAllegianceCode and rawAllegianceCode not in _IgnoreAllegianceCodes:
                usedCodes.add(rawAllegianceCode)
    if rawMetadata.borders():
        for rawBorder in rawMetadata.borders():
            rawAllegianceCode = rawBorder.allegiance()
            if rawAllegianceCode and rawAllegianceCode not in _IgnoreAllegianceCodes:
                usedCodes.add(rawAllegianceCode)
    return usedCodes

def _filterStockAllegiances(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        rawUsedAllegianceCodes: typing.Collection[str],
        rawStockAllegiances: typing.Collection[survey.RawStockAllegiance] = None,
        ) -> typing.List[survey.RawStockAllegiance]:
    rawLocalAllegiances: typing.Collection[survey.RawStockAllegiance] = []
    rawGlobalAllegiances: typing.Collection[survey.RawStockAllegiance]  = []
    rawSeenAllegianceCodes = set()

    if rawStockAllegiances:
        rawAbbreviation = rawMetadata.abbreviation()
        for rawStockAllegiance in rawStockAllegiances:
            if not rawStockAllegiance.code():
                logging.debug('Converter ignoring stock allegiance with empty code')
                continue

            if not rawStockAllegiance.name():
                logging.debug('Converter ignoring stock allegiance with empty name')
                continue

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

def _mergeRouteStyles(
        rawStockStyleSheet: typing.Optional[survey.RawStyleSheet] = None,
        rawSectorStyleSheet: typing.Optional[survey.RawStyleSheet] = None,
        ) -> typing.Dict[
            str, # Style tag
            typing.Tuple[
                str, # Colour
                str, # Style
                float]]: # Width
    routeStyleMap: typing.Dict[str, typing.Tuple[str, str, float]] = {}

    if rawSectorStyleSheet:
        for rawStyle in rawSectorStyleSheet.routeStyles():
            tag = rawStyle.tag()
            colour = rawStyle.colour()
            style = rawStyle.style()
            width = rawStyle.width()

            if colour is not None and not common.isValidHtmlColour(colour):
                # TODO: This log message should say which sector it is
                logging.warning(f'Converter ignoring invalid colour "{colour}" for route style {tag} from sector style sheet')
                colour = None
            if style is not None:
                if style.lower() in _ValidLineStyles:
                    style = style.lower()
                else:
                    logging.warning(f'Converter ignoring invalid line style "{style}" for route style {tag} from sector style sheet')
                    style = None

            routeStyleMap[tag] = (colour, style, width)

    if rawStockStyleSheet:
        for rawStyle in rawStockStyleSheet.routeStyles():
            tag = rawStyle.tag()
            colour, style, width = routeStyleMap.get(tag, (None, None, None))
            if colour is None:
                colour = rawStyle.colour()
            if style is None:
                style = rawStyle.style()
            if width is None:
                width = rawStyle.width()

            if colour is not None and not common.isValidHtmlColour(colour):
                # TODO: This log message should say which sector it is
                logging.warning(f'Converter ignoring invalid colour "{colour}" for route style {tag} from stock style sheet')
                colour = None
            if style is not None:
                if style.lower() in _ValidLineStyles:
                    style = style.lower()
                else:
                    logging.warning(f'Converter ignoring invalid line style "{style}" for route style {tag} from stock style sheet')
                    style = None

            routeStyleMap[tag] = (colour, style, width)

    # Update all tag mappings with default values
    if None in routeStyleMap:
        defaultColour, defaultStyle, defaultWith = routeStyleMap.get(None)
        for tag in list(routeStyleMap.keys()):
            colour, style, width = routeStyleMap[tag]
            if colour is None:
                colour = defaultColour
            if style is None:
                style = defaultStyle
            if width is None:
                width = defaultWith
            routeStyleMap[tag] = (colour, style, width)

    return routeStyleMap

def _mergeBorderStyles(
        rawStockStyleSheet: typing.Optional[survey.RawStyleSheet] = None,
        rawSectorStyleSheet: typing.Optional[survey.RawStyleSheet] = None,
        ) -> typing.Dict[
            str, # Style tag
            typing.Tuple[
                str, # Colour
                str]]: # Style
    borderStyleMap: typing.Dict[str, typing.Tuple[str, str]] = {}

    if rawSectorStyleSheet:
        for rawStyle in rawSectorStyleSheet.borderStyles():
            tag = rawStyle.tag()
            colour = rawStyle.colour()
            style = rawStyle.style()

            if colour is not None and not common.isValidHtmlColour(colour):
                # TODO: This log message should say which sector it is
                logging.warning(f'Converter ignoring invalid colour "{colour}" for border style {tag} from sector style sheet')
                colour = None
            if style is not None:
                if style.lower() in _ValidLineStyles:
                    style = style.lower()
                else:
                    logging.warning(f'Converter ignoring invalid line style "{style}" for border style {tag} from sector style sheet')
                    style = None

            borderStyleMap[tag] = (colour, style)

    if rawStockStyleSheet:
        for rawStyle in rawStockStyleSheet.borderStyles():
            tag = rawStyle.tag()
            colour, style = borderStyleMap.get(tag, (None, None))
            if colour is None:
                colour = rawStyle.colour()
            if style is None:
                style = rawStyle.style()

            if colour is not None and not common.isValidHtmlColour(colour):
                # TODO: This log message should say which sector it is
                logging.warning(f'Converter ignoring invalid colour "{colour}" for border style {tag} from sector style sheet')
                colour = None
            if style is not None:
                if style.lower() in _ValidLineStyles:
                    style = style.lower()
                else:
                    logging.warning(f'Converter ignoring invalid line style "{style}" for border style {tag} from sector style sheet')
                    style = None

            borderStyleMap[tag] = (colour, style)

    # Update all tag mappings with default values
    if None in borderStyleMap:
        defaultColour, defaultStyle = borderStyleMap.get(None)
        for tag in list(borderStyleMap.keys()):
            colour, style = borderStyleMap[tag]
            if colour is None:
                colour = defaultColour
            if style is None:
                style = defaultStyle
            borderStyleMap[tag] = (colour, style)

    return borderStyleMap

def _createDbAlternateNames(
        milieu: str,
        rawMetadata: survey.RawMetadata
        ) -> typing.List[multiverse.DbAlternateName]:
    dbAlternateNames = []

    if rawMetadata.alternateNames():
        for name in rawMetadata.alternateNames():
            if not name:
                logging.warning(f'Converter ignoring alternate sector name with empty name in {rawMetadata.canonicalName()} at {milieu}')
                continue
            language = rawMetadata.nameLanguage(name)
            dbAlternateNames.append(multiverse.DbAlternateName(
                name=name,
                language=language if language else None))

    return dbAlternateNames

def _createDbSubsectorNames(
        milieu: str,
        rawMetadata: survey.RawMetadata
        ) -> typing.List[multiverse.DbSubsectorName]:
    dbSubsectorNames = []

    if rawMetadata.subsectorNames():
        for code, name in rawMetadata.subsectorNames().items():
            if not code:
                logging.warning(f'Converter ignoring subsector name with empty code in {rawMetadata.canonicalName()} at {milieu}')
                continue

            if not name:
                # This doesn't get logged as it happens quite a bit in the stock
                # data and just seems to be used when subsectors aren't named
                #logging.debug(f'Converter ignoring subsector name with empty name in {rawMetadata.canonicalName()} at {milieu}')
                continue

            # Silently fix instances where code is lower case
            code = code.upper()

            dbSubsectorNames.append(multiverse.DbSubsectorName(
                code=code,
                name=name))

    return dbSubsectorNames

# This is intended to mimic the logic of GetStockAllegianceFromCode from the
# Traveller Map source code (SecondSurvey.cs). That code handles the precedence
# of the various legacy allegiances by checking different maps in a specific
# order each time it's called. My implementation creates a single map with all
# the allegiances for the given sector. The way the map is populated is key to
# maintaining the same precedence as Traveller Map
def _createDbAllegiances(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        rawSystems: typing.Collection[survey.RawWorld],
        rawStockAllegiances: typing.Optional[typing.Collection[
            survey.RawStockAllegiance
            ]] = None,
        routeStyleMap: typing.Optional[typing.Mapping[
            str, # Style tag
            typing.Tuple[
                str, # Colour
                str, # Style
                float # Width
                ]]] = None,
        borderStyleMap: typing.Optional[typing.Mapping[
            str, # Style tag
            typing.Tuple[
                str, # Colour
                str # Style
                ]]] = None,
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

        # NOTE: It's important that the full list of stock allegiances are used
        # when generating this map (rather than the just the ones used in the
        # sector) as the metadata may contain definitions that aren't actually
        # used but we still want to include them in the list of allegiances added
        # to the database and we still want to use stock allegiances to fill in
        # any missing information for them where possible.
        rawStockAllegiancesCodeMap = {a.code(): a for a in  rawStockAllegiances}

        for rawMetadataAllegiance in rawMetadata.allegiances():
            code = rawMetadataAllegiance.code()
            if not code:
                logging.warning(f'Converter ignoring sector allegiance with empty code in {rawMetadata.canonicalName()} at {milieu}')
                continue

            name = rawMetadataAllegiance.name()
            if not name:
                logging.warning(f'Converter ignoring sector allegiance with empty name in {rawMetadata.canonicalName()} at {milieu}')
                continue

            baseCode = rawMetadataAllegiance.base()
            legacyCode = None

            rawStockAllegiance = rawStockAllegiancesCodeMap.get(code)
            if rawStockAllegiance:
                useStockInfo = (rawStockAllegiance.name() == name) and \
                    ((not baseCode) or (rawStockAllegiance.base() == baseCode))
                if useStockInfo:
                    if not baseCode:
                        baseCode = rawStockAllegiance.base()
                    legacyCode = rawStockAllegiance.legacy()

            routeColour, routeStyle, routeWidth = routeStyleMap.get(
                code,
                (None, None, None))
            borderColour, borderStyle = borderStyleMap.get(
                code,
                (None, None))

            dbAllegianceCodeMap[code] = multiverse.DbAllegiance(
                code=code,
                name=name,
                base=baseCode if baseCode else None,
                legacy=legacyCode if legacyCode else None,
                routeColour=routeColour,
                routeStyle=routeStyle,
                routeWidth=routeWidth,
                borderColour=borderColour,
                borderStyle=borderStyle)

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
        code = rawStockAllegiance.code()
        name = rawStockAllegiance.name()
        legacyCode = rawStockAllegiance.legacy()
        baseCode = rawStockAllegiance.base()

        dbAllegiance = dbAllegianceCodeMap.get(code)
        if dbAllegiance:
            # The metadata has overridden this allegiance code
            continue

        routeColour, routeStyle, routeWidth = routeStyleMap.get(
            code,
            (None, None, None))
        borderColour, borderStyle = borderStyleMap.get(
            code,
            (None, None))

        dbAllegianceCodeMap[code] = multiverse.DbAllegiance(
            code=code,
            name=name,
            legacy=legacyCode if legacyCode else None,
            base=baseCode if baseCode else None,
            routeColour=routeColour,
            routeStyle=routeStyle,
            routeWidth=routeWidth,
            borderColour=borderColour,
            borderStyle=borderStyle)

    # Find any codes that haven't had database allegiance defined. These might be
    # legacy codes or they might be codes that aren't defined anywhere
    rawMissingAllegianceCodes = []
    for code in rawUsedAllegianceCodes:
        if code not in dbAllegianceCodeMap:
            rawMissingAllegianceCodes.append(code)

    # Create database allegiances for any missing allegiance codes
    if rawMissingAllegianceCodes:
        # Create mapping to use for legacy codes. Only stock allegiances are used here as
        # allegiances defined in the metadata don't support legacy codes.
        rawStockAllegianceLegacyMap: typing.Dict[str, survey.RawStockAllegiance] = {}
        for rawStockAllegiance in rawStockAllegiances:
            if rawStockAllegiance.legacy() and rawStockAllegiance.legacy() not in rawStockAllegianceLegacyMap:
                rawStockAllegianceLegacyMap[rawStockAllegiance.legacy()] = rawStockAllegiance

        for code in rawMissingAllegianceCodes:
            if code in dbAllegianceCodeMap:
                continue

            overrideCode = _LegacyAllegianceToT5Overrides.get(code)
            rawStockAllegiance = rawStockAllegianceLegacyMap.get(overrideCode if overrideCode else code)

            if rawStockAllegiance:
                name = rawStockAllegiance.name()
                legacyCode = rawStockAllegiance.legacy()
                baseCode = rawStockAllegiance.base()

                # There is a stock allegiance with a legacy code that matches the missing code.
                # If there is an existing database allegiance that is an exact match _or_ a match
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
                        dbAllegiance.name() == name and \
                        dbAllegiance.legacy == legacyCode and \
                        dbAllegiance.base() == baseCode
                    if not useExisting:
                        # There is an existing database allegiance for this code but it's not using
                        # the same details as the stock allegiance so it's not appropriate to use
                        # for this code. Create a new database allegiance, as the stock allegiance
                        # code is already in use, use the raw code with the rest of the stock details
                        routeColour, routeStyle, routeWidth = routeStyleMap.get(
                            code,
                            (None, None, None))
                        borderColour, borderStyle = borderStyleMap.get(
                            code,
                            (None, None))

                        dbAllegiance = multiverse.DbAllegiance(
                            code=code,
                            name=name,
                            legacy=legacyCode if legacyCode else None,
                            base=baseCode if baseCode else None,
                            routeColour=routeColour,
                            routeStyle=routeStyle,
                            routeWidth=routeWidth,
                            borderColour=borderColour,
                            borderStyle=borderStyle)
                else:
                    # There is no existing database allegiance for this code so create one
                    routeColour, routeStyle, routeWidth = routeStyleMap.get(
                        rawStockAllegiance.code(),
                        (None, None, None))
                    borderColour, borderStyle = borderStyleMap.get(
                        rawStockAllegiance.code(),
                        (None, None))

                    dbAllegiance = multiverse.DbAllegiance(
                        code=rawStockAllegiance.code(),
                        name=name,
                        legacy=legacyCode if legacyCode else None,
                        base=baseCode if baseCode else None,
                        routeColour=routeColour,
                        routeStyle=routeStyle,
                        routeWidth=routeWidth,
                        borderColour=borderColour,
                        borderStyle=borderStyle)
            else:
                # There is no stock allegiance that has a legacy code matching this missing code.
                # All we can do is create a database allegiance with information we do have
                routeColour, routeStyle, routeWidth = routeStyleMap.get(
                    code,
                    (None, None, None))
                borderColour, borderStyle = borderStyleMap.get(
                    code,
                    (None, None))

                dbAllegiance = multiverse.DbAllegiance(
                    code=code,
                    name=code,
                    legacy=None, # No legacy code known
                    base=None, # No base code know
                    routeColour=routeColour,
                    routeStyle=routeStyle,
                    routeWidth=routeWidth,
                    borderColour=borderColour,
                    borderStyle=borderStyle)

            # NOTE: Use the code from the list of missing allegiances as the code as
            # that's what the rest of the data will be referring to it as. This may
            # be different from the allegiance code actually used by the allegiance.
            # If they differ it has the effect of mapping the old raw code to the
            # new code used in the database.
            dbAllegianceCodeMap[code] = dbAllegiance

            # If the allegiance code was overridden, add a mapping for the real code if it's
            # used and there isn't already a mapping for it
            if code != dbAllegiance.code() and \
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
        legacyCode = dbAllegiance.legacy()
        if not legacyCode:
            continue
        if legacyCode in dbAllegianceCodeMap:
            continue
        if legacyCode not in rawUsedAllegianceCodes:
            continue
        dbAllegianceCodeMap[legacyCode] = dbAllegiance

    # Add mappings for base codes
    for dbAllegiance in dbAllegiances:
        baseCode = dbAllegiance.base()
        if not baseCode:
            continue
        if baseCode in dbAllegianceCodeMap:
            continue
        if baseCode not in rawUsedAllegianceCodes:
            continue
        dbAllegianceCodeMap[baseCode] = dbAllegiance

    return dbAllegianceCodeMap

# This code generates a code for a sophont name following the rules defined on
# the Traveller Wiki (at least as best as I can understand them)
# https://wiki.travellerrpg.com/Sophont_Code
def _generateSophontCode(
        name: str,
        existingCodes: typing.Collection[str]
        ) -> str:
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

def _generateSophontName(
        code: str,
        existingNames: typing.Collection[str]
        ) -> str:
    name = code
    while name in existingNames:
        name += 'X'
    return name

def _createDbSophonts(
        rawSystems: typing.Collection[survey.RawWorld],
        rawStockSophonts: typing.Optional[typing.Collection[
            survey.RawStockSophont
            ]] = None,
        ) -> typing.Tuple[
            typing.Dict[str, multiverse.DbSophont], # Code to DbSophont map
            typing.Dict[str, multiverse.DbSophont]]: # Name to DbSophont map
    rawStockSophontCodeMap: typing.Dict[str, survey.RawStockSophont] = {}
    rawStockSophontNameMap: typing.Dict[str, survey.RawStockSophont] = {}
    if rawStockSophonts:
        for rawStockSophont in rawStockSophonts:
            if not rawStockSophont.code():
                logging.debug('Converter ignoring stock sophont with empty code')
                continue

            if not rawStockSophont.name():
                logging.debug('Converter ignoring stock sophont with empty name')
                continue

            if rawStockSophont.code() in rawStockSophontCodeMap:
                raise RuntimeError(f'Stock sophonts contain multiple sophonts with the code {rawStockSophont.code()}')
            rawStockSophontCodeMap[rawStockSophont.code()] = rawStockSophont

            if rawStockSophont.name() in rawStockSophontNameMap:
                raise RuntimeError(f'Stock sophonts contain multiple sophonts with the name {rawStockSophont.name()}')
            rawStockSophontNameMap[rawStockSophont.name()] = rawStockSophont

    rawUsedSophontCodes: typing.Set[str] = set()
    rawUsedSophontNames: typing.Set[str] = set()
    rawMajorSophontNames: typing.Set[str] = set(_StockMajorSophonts)
    if rawSystems:
        for rawWorld in rawSystems:
            rawRemarks = rawWorld.remarks()
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

    if rawUsedSophontNames or rawUsedSophontCodes:
        uniqueCodes = set(rawStockSophontCodeMap.keys())
        uniqueNames = set(rawStockSophontNameMap.keys())

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
                    existingCodes=uniqueCodes)
                uniqueCodes.add(dbSophontCode)

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
                # DbSophont for that code then one needs to be created.
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

                dbSophontName = _generateSophontName(
                    code=rawSophontCode,
                    existingNames=uniqueNames)
                uniqueNames.add(dbSophontName)

                dbSophont = multiverse.DbSophont(
                    code=rawSophontCode,
                    name=dbSophontName,
                    isMajor=False)

            # NOTE: It's important that the rawSophontCode is used as the key here as,
            # in the case that the code was overridden, we still need a mapping for
            # the raw code as that's what other raw data will be using
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

def _createDbStars(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld
        ) -> typing.Optional[typing.List[multiverse.DbStar]]:
    rawStellar = rawWorld.stellar()
    if not rawStellar:
        return None

    dbStars = []
    for luminosityClass, spectralClass, spectralScale in survey.parseSystemStellarString(string=rawStellar):
        try:
            dbStars.append(multiverse.DbStar(
                luminosityClass=luminosityClass,
                spectralClass=spectralClass,
                spectralScale=spectralScale))
        except Exception as ex:
            logging.error('Converter failed to construct star on world {world} in {sector} at {milieu}'.format(
                    world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                    sector=rawMetadata.canonicalName(),
                    milieu=milieu),
                exc_info=ex)

    return dbStars

def _createDbBodies(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld,
        dbAllegianceCodeMap: typing.Dict[str, multiverse.DbAllegiance],
        dbSophontCodeMap: typing.Dict[str, multiverse.DbSophont],
        dbSophontNameMap: typing.Dict[str, multiverse.DbSophont]
        ) -> typing.Optional[typing.List[multiverse.DbBody]]:
    rawSystemName = rawWorld.name()
    dbSystemName = rawSystemName if rawSystemName else None

    rawUWP = rawWorld.uwp()
    dbStarport = dbWorldSize = dbAtmosphere = dbHydrographics = \
        dbPopulation = dbGovernment = dbLawLevel = dbTechLevel = None
    if rawUWP:
        dbStarport, dbWorldSize, dbAtmosphere, dbHydrographics, \
            dbPopulation, dbGovernment, dbLawLevel, dbTechLevel = \
            survey.parseSystemUWPString(uwp=rawUWP.upper())

    rawEconomics = rawWorld.economics()
    dbResources = dbLabour = dbInfrastructure = dbEfficiency = None
    if rawEconomics:
        dbResources, dbLabour, dbInfrastructure, dbEfficiency = \
            survey.parseSystemEconomicsString(economics=rawEconomics.upper())

    rawCulture = rawWorld.culture()
    dbHeterogeneity = dbAcceptance = dbStrangeness = dbSymbols = None
    if rawCulture:
        dbHeterogeneity, dbAcceptance, dbStrangeness, dbSymbols = \
            survey.parseSystemCultureString(culture=rawCulture.upper())

    rawPBG = rawWorld.pbg()
    dbPopulationMultiplier = None
    if rawPBG:
        dbPopulationMultiplier, _, _ = \
            survey.parseSystemPBGString(pbg=rawPBG.upper())

    dbNobilities = _createDbNobilities(
        milieu=milieu,
        rawMetadata=rawMetadata,
        rawWorld=rawWorld)

    dbBases = _createDbBases(
        milieu=milieu,
        rawMetadata=rawMetadata,
        rawWorld=rawWorld)

    rawRemarks = rawWorld.remarks()
    dbTradeCodes = dbSophontPopulations = dbRulingAllegiances = dbOwningSystems = dbColonySystems = \
        dbResearchStations = dbCustomRemarks = None
    if rawRemarks:
        rawTradeCodes, rawMajorHomeWorlds, rawMinorHomeWorlds, rawSophontPopulations, \
            rawDieBackSophonts, rawOwningSystems, rawColonySystems, rawRulingAllegiances, \
            rawResearchStations, rawUnrecognisedRemarks = survey.parseSystemRemarksString(rawRemarks)

        dbSophontPopulations = _createDbSophontPopulations(
            milieu=milieu,
            rawMetadata=rawMetadata,
            rawWorld=rawWorld,
            rawMajorHomeWorlds=rawMajorHomeWorlds,
            rawMinorHomeWorlds=rawMinorHomeWorlds,
            rawSophontPopulations=rawSophontPopulations,
            rawDieBackSophonts=rawDieBackSophonts,
            dbSophontCodeMap=dbSophontCodeMap,
            dbSophontNameMap=dbSophontNameMap)

        dbOwningSystems = _createDbOwningSystems(
            milieu=milieu,
            rawMetadata=rawMetadata,
            rawWorld=rawWorld,
            rawOwningSystems=rawOwningSystems)

        dbColonySystems = _createDbColonySystems(
            milieu=milieu,
            rawMetadata=rawMetadata,
            rawWorld=rawWorld,
            rawColonySystems=rawColonySystems)

        dbRulingAllegiances = _createDbRulingAllegiances(
            milieu=milieu,
            rawMetadata=rawMetadata,
            rawWorld=rawWorld,
            rawRulingAllegiances=rawRulingAllegiances,
            dbAllegianceCodeMap=dbAllegianceCodeMap)

        dbResearchStations = _createDbResearchStations(
            milieu=milieu,
            rawMetadata=rawMetadata,
            rawWorld=rawWorld,
            rawResearchStations=rawResearchStations)

        dbTradeCodes = _createDbTradeCodes(
            milieu=milieu,
            rawMetadata=rawMetadata,
            rawWorld=rawWorld,
            rawTradeCodes=rawTradeCodes,
            dbSophontPopulations=dbSophontPopulations,
            dbRulingAllegiances=dbRulingAllegiances,
            dbResearchStations=dbResearchStations)

        dbCustomRemarks = _createDbCustomRemarks(
            milieu=milieu,
            rawMetadata=rawMetadata,
            rawWorld=rawWorld,
            rawUnrecognisedRemarks=rawUnrecognisedRemarks)

    # Only create the main world if there is some data or there is known
    # to be at least one system world
    hasData = dbStarport or dbWorldSize or dbAtmosphere or dbHydrographics or \
        dbPopulation or dbGovernment or dbLawLevel or dbTechLevel or \
        dbResources or dbLabour or dbInfrastructure or dbEfficiency or \
        dbHeterogeneity or dbAcceptance or dbStrangeness or dbSymbols or \
        dbPopulationMultiplier or dbTradeCodes or dbSophontPopulations or \
        dbRulingAllegiances or dbOwningSystems or dbColonySystems or \
        dbResearchStations or dbCustomRemarks
    numSystemWorlds = _parseSystemWorldCount(rawWorld.systemWorlds())
    if not hasData and not numSystemWorlds:
        return None

    return [multiverse.DbWorld(
        orbitIndex=1,
        isMainWorld=True,
        name=dbSystemName,
        starport=dbStarport,
        worldSize=dbWorldSize,
        atmosphere=dbAtmosphere,
        hydrographics=dbHydrographics,
        population=dbPopulation,
        government=dbGovernment,
        lawLevel=dbLawLevel,
        techLevel=dbTechLevel,
        resources=dbResources,
        labour=dbLabour,
        infrastructure=dbInfrastructure,
        efficiency=dbEfficiency,
        heterogeneity=dbHeterogeneity,
        acceptance=dbAcceptance,
        strangeness=dbStrangeness,
        symbols=dbSymbols,
        populationMultiplier=dbPopulationMultiplier,
        nobilities=dbNobilities,
        bases=dbBases,
        tradeCodes=dbTradeCodes,
        sophontPopulations=dbSophontPopulations,
        rulingAllegiances=dbRulingAllegiances,
        owningSystems=dbOwningSystems,
        colonySystems=dbColonySystems,
        researchStations=dbResearchStations,
        customRemarks=dbCustomRemarks)]

def _createDbNobilities(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld
        ) -> typing.Optional[typing.List[multiverse.DbNobility]]:
    rawNobilities = rawWorld.nobility()
    if not rawNobilities:
        return None

    dbNobilities = []
    seenNobilities = set()
    for nobilityCode in survey.parseSystemNobilityString(string=rawNobilities):
        if nobilityCode in seenNobilities:
            logging.debug('Converter ignoring duplicate nobility code "{code}" on world {world} in {sector} at {milieu}'.format(
                code=nobilityCode,
                world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                sector=rawMetadata.canonicalName(),
                milieu=milieu))
            continue
        seenNobilities.add(nobilityCode)

        try:
            dbNobilities.append(multiverse.DbNobility(code=nobilityCode))
        except Exception as ex:
            logging.error('Converter failed to construct nobility on world {world} in {sector} at {milieu}'.format(
                    world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                    sector=rawMetadata.canonicalName(),
                    milieu=milieu),
                exc_info=ex)

    return dbNobilities

def _createDbBases(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld
        ) -> typing.Optional[typing.List[multiverse.DbBase]]:
    rawBases = rawWorld.bases()
    if not rawBases:
        return None

    dbBases = []
    seenBases = set()
    for baseCode in survey.parseSystemBasesString(string=rawBases):
        if baseCode in seenBases:
            logging.debug('Converter ignoring duplicate base code "{code}" on world {world} in {sector} at {milieu}'.format(
                code=baseCode,
                world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                sector=rawMetadata.canonicalName(),
                milieu=milieu))
            continue
        seenBases.add(baseCode)

        try:
            dbBases.append(multiverse.DbBase(code=baseCode))
        except Exception as ex:
            logging.error('Converter failed to construct base on world {world} in {sector} at {milieu}'.format(
                    world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                    sector=rawMetadata.canonicalName(),
                    milieu=milieu),
                exc_info=ex)

    return dbBases

def _createDbSophontPopulations(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld,
        rawMajorHomeWorlds: typing.List[typing.Tuple[
            str, # Sophont Name
            typing.Optional[int]]], # Population Percentage
        rawMinorHomeWorlds: typing.List[typing.Tuple[
            str, # Sophont Name
            typing.Optional[int]]], # Population Percentage
        rawSophontPopulations: typing.List[typing.Tuple[
            str, # Sophont Code
            typing.Optional[int]]], # Population Percentage
        rawDieBackSophonts: typing.List[str], # Sophont Names
        dbSophontCodeMap: typing.Mapping[str, multiverse.DbSophont],
        dbSophontNameMap: typing.Mapping[str, multiverse.DbSophont]
        ) -> typing.Optional[typing.List[multiverse.DbStar]]:
    if not rawMajorHomeWorlds and not rawMinorHomeWorlds and not rawSophontPopulations and not rawDieBackSophonts:
        return None

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

        try:
            dbSophontPopulations.append(multiverse.DbSophontPopulation(
                sophontId=dbSophont.id(),
                percentage=rawPopulation,
                isHomeWorld=True,
                isDieBack=False))
        except Exception as ex:
            logging.error('Converter failed to construct major home world sophont population on world {world} in {sector} at {milieu}'.format(
                    world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                    sector=rawMetadata.canonicalName(),
                    milieu=milieu),
                exc_info=ex)

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

        try:
            dbSophontPopulations.append(multiverse.DbSophontPopulation(
                sophontId=dbSophont.id(),
                percentage=rawPopulation,
                isHomeWorld=True,
                isDieBack=False))
        except Exception as ex:
            logging.error('Converter failed to construct minor home world sophont population on world {world} in {sector} at {milieu}'.format(
                    world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                    sector=rawMetadata.canonicalName(),
                    milieu=milieu),
                exc_info=ex)

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

        try:
            dbSophontPopulations.append(multiverse.DbSophontPopulation(
                sophontId=dbSophont.id(),
                percentage=rawPopulation,
                isHomeWorld=False,
                isDieBack=False))
        except Exception as ex:
            logging.error('Converter failed to construct sophont population on world {world} in {sector} at {milieu}'.format(
                    world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                    sector=rawMetadata.canonicalName(),
                    milieu=milieu),
                exc_info=ex)

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

        try:
            dbSophontPopulations.append(multiverse.DbSophontPopulation(
                sophontId=dbSophont.id(),
                percentage=None,
                isHomeWorld=False,
                isDieBack=True))
        except Exception as ex:
            logging.error('Converter failed to construct die back sophont population on world {world} in {sector} at {milieu}'.format(
                    world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                    sector=rawMetadata.canonicalName(),
                    milieu=milieu),
                exc_info=ex)

    return dbSophontPopulations

def _createDbOwningSystems(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld,
        rawOwningSystems: typing.List[typing.Tuple[
            int, # Hex X in sector coordinates
            int, # Hex Y in sector coordinates
            typing.Optional[str]]], # Sector Abbreviation or None if Current Sector
        ) -> typing.Optional[typing.List[multiverse.DbOwningSystem]]:
    if not rawOwningSystems:
        return None

    dbOwningSystems = []
    seenOwners = set()
    for hexX, hexY, sectorAbbreviation in rawOwningSystems:
        if not sectorAbbreviation:
            sectorAbbreviation = None
        elif sectorAbbreviation == rawMetadata.abbreviation():
            # If the sector abbreviation is the same as the current sector
            # abbreviation then it can be omitted
            sectorAbbreviation = None

        key = (hexX, hexY, sectorAbbreviation)
        if key in seenOwners:
            logging.debug('Converter ignoring duplicate owner world on world {world} in {sector} at {milieu}'.format(
                world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                sector=rawMetadata.canonicalName(),
                milieu=milieu))
            continue
        seenOwners.add(key)

        try:
            dbOwningSystems.append(multiverse.DbOwningSystem(
                hexX=hexX,
                hexY=hexY,
                sectorAbbreviation=sectorAbbreviation))
        except Exception as ex:
            logging.error('Converter failed to construct owner world on world {world} in {sector} at {milieu}'.format(
                    world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                    sector=rawMetadata.canonicalName(),
                    milieu=milieu),
                exc_info=ex)

    return dbOwningSystems

def _createDbColonySystems(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld,
        rawColonySystems: typing.List[typing.Tuple[
            int, # Hex X in sector coordinates
            int, # Hex Y in sector coordinates
            typing.Optional[str]]], # Sector Abbreviation or None if Current Sector
        ) -> typing.Optional[typing.List[multiverse.DbColonySystem]]:
    if not rawColonySystems:
        return None

    dbColonySystems = []
    seenColonies = set()
    for hexX, hexY, sectorAbbreviation in rawColonySystems:
        if not sectorAbbreviation:
            sectorAbbreviation = None
        elif sectorAbbreviation == rawMetadata.abbreviation():
            # If the sector abbreviation is the same as the current sector
            # abbreviation then it can be omitted
            sectorAbbreviation = None

        key = (hexX, hexY, sectorAbbreviation)
        if key in seenColonies:
            logging.debug('Converter ignoring duplicate colony world on world {world} in {sector} at {milieu}'.format(
                world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                sector=rawMetadata.canonicalName(),
                milieu=milieu))
            continue
        seenColonies.add(key)

        try:
            dbColonySystems.append(multiverse.DbColonySystem(
                hexX=hexX,
                hexY=hexY,
                sectorAbbreviation=sectorAbbreviation))
        except Exception as ex:
            logging.error('Converter failed to construct colony world on world {world} in {sector} at {milieu}'.format(
                    world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                    sector=rawMetadata.canonicalName(),
                    milieu=milieu),
                exc_info=ex)

    return dbColonySystems

def _createDbRulingAllegiances(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld,
        rawRulingAllegiances: typing.List[str], # Allegiance codes
        dbAllegianceCodeMap: typing.Mapping[str, multiverse.DbAllegiance]
        ) -> typing.Optional[typing.List[multiverse.DbRulingAllegiance]]:
    if not rawRulingAllegiances:
        return None

    dbRulingAllegiances = []
    seenRulingAllegiances = set()
    for rawAllegianceCode in rawRulingAllegiances:
        if rawAllegianceCode in seenRulingAllegiances:
            logging.debug('Converter ignoring duplicate ruling allegiance on world {world} in {sector} at {milieu}'.format(
                world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                sector=rawMetadata.canonicalName(),
                milieu=milieu))
            continue
        seenRulingAllegiances.add(rawAllegianceCode)

        dbAllegiance = dbAllegianceCodeMap.get(rawAllegianceCode)
        if not dbAllegiance:
            # TODO: This should probably log and continue with no allegiance,
            # if it's a custom sector it should also warn the user
            raise RuntimeError(f'Military rule trade code (Mr) in {rawMetadata.canonicalName()} at {milieu} uses undefined allegiance code {rawAllegianceCode}')

        try:
            dbRulingAllegiances.append(multiverse.DbRulingAllegiance(allegianceId=dbAllegiance.id()))
        except Exception as ex:
            logging.error('Converter failed to construct ruling allegiance on world {world} in {sector} at {milieu}'.format(
                    world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                    sector=rawMetadata.canonicalName(),
                    milieu=milieu),
                exc_info=ex)

    return dbRulingAllegiances

def _createDbResearchStations(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld,
        rawResearchStations: typing.List[str]
        ) -> typing.Optional[typing.List[multiverse.DbResearchStation]]:
    if not rawResearchStations:
        return None

    dbResearchStations = []
    seenResearchStations = set()
    for rawResearchStation in rawResearchStations:
        if rawResearchStation in seenResearchStations:
            logging.debug('Converter ignoring duplicate research station on world {world} in {sector} at {milieu}'.format(
                world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                sector=rawMetadata.canonicalName(),
                milieu=milieu))
            continue # Skip duplicates
        seenResearchStations.add(rawResearchStation)

        try:
            dbResearchStations.append(multiverse.DbResearchStation(code=rawResearchStation))
        except Exception as ex:
            logging.error('Converter failed to construct research station on world {world} in {sector} at {milieu}'.format(
                    world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                    sector=rawMetadata.canonicalName(),
                    milieu=milieu),
                exc_info=ex)

    return dbResearchStations

def _createDbTradeCodes(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld,
        rawTradeCodes: typing.Optional[typing.Collection[str]],
        dbSophontPopulations: typing.Optional[typing.Collection[multiverse.DbSophontPopulation]],
        dbRulingAllegiances: typing.Optional[typing.Collection[multiverse.DbRulingAllegiance]],
        dbResearchStations: typing.Optional[typing.Collection[multiverse.DbResearchStation]]
        ) -> typing.Optional[typing.List[multiverse.DbTradeCode]]:
    if not rawTradeCodes:
        return None

    dbTradeCodes = []
    seenTradeCodes = set()
    for rawTradeCode in rawTradeCodes:
        if rawTradeCode in seenTradeCodes:
            logging.debug('Converter ignoring duplicate trade code "{code}" on world at {world} in {sector} at {milieu}'.format(
                code=rawTradeCode,
                world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                sector=rawMetadata.canonicalName(),
                milieu=milieu))
            continue
        seenTradeCodes.add(rawTradeCode)

        try:
            dbTradeCodes.append(multiverse.DbTradeCode(code=rawTradeCode))
        except Exception as ex:
            logging.error('Converter failed to construct trade code on world at {world} in {sector} at {milieu}'.format(
                world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                sector=rawMetadata.canonicalName(),
                milieu=milieu),
                exc_info=ex)

    if dbSophontPopulations:
        for population in dbSophontPopulations:
            if not population.isDieBack():
                continue

            if _DieBackTradeCode in seenTradeCodes:
                break
            seenTradeCodes.add(_DieBackTradeCode)

            try:
                dbTradeCodes.append(multiverse.DbTradeCode(code=_DieBackTradeCode))
            except Exception as ex:
                logging.error('Converter failed to construct trade code on world at {world} in {sector} at {milieu}'.format(
                    world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                    sector=rawMetadata.canonicalName(),
                    milieu=milieu),
                    exc_info=ex)
            break

    if dbRulingAllegiances and _MilitaryRuleTradeCode not in seenTradeCodes:
        seenTradeCodes.add(_MilitaryRuleTradeCode)
        try:
            dbTradeCodes.append(multiverse.DbTradeCode(code=_MilitaryRuleTradeCode))
        except Exception as ex:
            logging.error('Converter failed to construct trade code on world at {world} in {sector} at {milieu}'.format(
                world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                sector=rawMetadata.canonicalName(),
                milieu=milieu),
                exc_info=ex)

    if dbResearchStations and _ResearchStationTradeCode not in seenTradeCodes:
        seenTradeCodes.add(_ResearchStationTradeCode)
        try:
            dbTradeCodes.append(multiverse.DbTradeCode(code=_ResearchStationTradeCode))
        except Exception as ex:
            logging.error('Converter failed to construct trade code on world at {world} in {sector} at {milieu}'.format(
                world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                sector=rawMetadata.canonicalName(),
                milieu=milieu),
                exc_info=ex)

    return dbTradeCodes

def _createDbCustomRemarks(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld,
        rawUnrecognisedRemarks: typing.Optional[typing.Collection[str]]
        ) -> typing.Optional[typing.List[multiverse.DbCustomRemark]]:
    if not rawUnrecognisedRemarks:
        return None


    dbCustomRemarks = []
    for remark in rawUnrecognisedRemarks:
        if not remark:
            continue

        try:
            dbCustomRemarks.append(multiverse.DbCustomRemark(remark=remark))
        except Exception as ex:
            logging.error('Converter failed to construct custom remark on world at {world} in {sector} at {milieu}'.format(
                world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                sector=rawMetadata.canonicalName(),
                milieu=milieu),
                exc_info=ex)

    return dbCustomRemarks

def _createDbSystems(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        rawSystems: typing.Collection[survey.RawWorld],
        dbAllegianceCodeMap: typing.Dict[str, multiverse.DbAllegiance],
        dbSophontCodeMap: typing.Dict[str, multiverse.DbSophont],
        dbSophontNameMap: typing.Dict[str, multiverse.DbSophont],
        ) -> typing.List[multiverse.DbSystem]:
    dbSystems = []

    # TODO: Should all the survey.parse* calls here be wrapped in try/except so just
    # the invalid data is ignored?
    for systemIndex, rawWorld in enumerate(rawSystems):
        try:
            rawHex = rawWorld.hex()
            if not rawHex:
                assert(False) # TODO: Better error handling
            dbHexX, dbHexY = _parseHexString(rawHex)

            rawSystemName = rawWorld.name()
            dbSystemName = rawSystemName if rawSystemName else None

            rawPBG = rawWorld.pbg()
            dbPlanetoidBeltCount = dbGasGiantCount = None
            if rawPBG:
                _, dbPlanetoidBeltCount, dbGasGiantCount = \
                    survey.parseSystemPBGString(pbg=rawPBG.upper())
                if dbPlanetoidBeltCount is not None:
                    dbPlanetoidBeltCount = survey.ehexToInteger(dbPlanetoidBeltCount, None)
                if dbGasGiantCount is not None:
                    dbGasGiantCount = survey.ehexToInteger(dbGasGiantCount, None)

            rawZone = rawWorld.zone()
            dbZone = None
            if rawZone:
                dbZone = survey.parseSystemZoneString(zone=rawZone.upper())
                if dbZone == 'G':
                    # In the database a green zone is represented by null
                    dbZone = None

            rawAllegianceCode = rawWorld.allegiance()
            dbAllegiance = dbAllegianceCodeMap.get(rawAllegianceCode) if rawAllegianceCode else None
            if rawAllegianceCode and not dbAllegiance:
                # TODO: This should probably log and continue with no allegiance,
                # if it's a custom sector it should also warn the user
                raise RuntimeError(f'World at {rawHex} in {rawMetadata.canonicalName()} at {milieu} uses undefined allegiance code {rawAllegianceCode}')

            # From the Traveller Map Second Survey documentation the system world count is
            # Main World + Gas Giant Count + Planetoid Belt Count + Other Planetoid Count.
            # With the minimum being 1 for the Main World. Gas Giant satellites (I assume
            # this means moons or rings) aren't included in the Other Planetoid Count unless
            # they are the Main World. If the Main World is a gas giant satellite, the world
            # should have the "Sa" remark which I don't believe any of the current worlds
            # have (but user data could).
            # https://travellermap.com/doc/secondsurvey#worlds
            # The section covering the Planetoid Belt Count in the PBG also says that a
            # Main World of size 0 is not included in that count. I assume this is because
            # it should be included in the other world count.
            # https://travellermap.com/doc/secondsurvey#pbg
            rawSystemWorlds = rawWorld.systemWorlds()
            dbWorldCount = None
            if rawSystemWorlds:
                numBelts = dbPlanetoidBeltCount if dbPlanetoidBeltCount else 0
                numGiants = dbGasGiantCount if dbGasGiantCount else 0
                numBeltsPlusGiants = numBelts + numGiants
                numSystemWorlds = _parseSystemWorldCount(rawSystemWorlds)
                if numSystemWorlds is not None:
                    if numSystemWorlds >= numBeltsPlusGiants:
                        dbWorldCount = numSystemWorlds - numBeltsPlusGiants
                    else:
                        logging.warning('Other world count for world {world} in {sector} at {milieu} is unknown as the world count {total} is lower than the number of known worlds (Main World + {belts} Planetoid Belts + {giants} Gas Giants)'.format(
                                total=numSystemWorlds,
                                belts=numBelts,
                                giants=numGiants,
                                world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                                sector=rawMetadata.canonicalName(),
                                milieu=milieu))
                else:
                    logging.warning('Other world count for world {world} in {sector} at {milieu} is unknown as the system world count "{count}" is invalid'.format(
                            count=rawSystemWorlds,
                            world=rawWorld.name() if rawWorld.name() else rawWorld.hex(),
                            sector=rawMetadata.canonicalName(),
                            milieu=milieu))

            dbBodies = _createDbBodies(
                milieu=milieu,
                rawMetadata=rawMetadata,
                rawWorld=rawWorld,
                dbSophontCodeMap=dbSophontCodeMap,
                dbAllegianceCodeMap=dbAllegianceCodeMap,
                dbSophontNameMap=dbSophontNameMap)

            if dbBodies is not None:
                numCreatedWorlds = 0
                for dbBody in dbBodies:
                    if isinstance(dbBody, multiverse.DbWorld):
                        numCreatedWorlds += 1
                if dbWorldCount is None or dbWorldCount < numCreatedWorlds:
                    dbWorldCount = numCreatedWorlds

            dbStars = _createDbStars(
                milieu=milieu,
                rawMetadata=rawMetadata,
                rawWorld=rawWorld)

            dbSystems.append(multiverse.DbSystem(
                hexX=dbHexX,
                hexY=dbHexY,
                name=dbSystemName,
                planetoidBeltCount=dbPlanetoidBeltCount,
                gasGiantCount=dbGasGiantCount,
                worldCount=dbWorldCount,
                zone=dbZone,
                allegianceId=dbAllegiance.id() if dbAllegiance else None,
                stars=dbStars,
                bodies=dbBodies))
        except Exception as ex:
            logging.warning(f'Failed to convert system {systemIndex} in {rawMetadata.canonicalName()} at {milieu}', exc_info=ex)

    return dbSystems

def _createDbRoutes(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        dbAllegianceCodeMap: typing.Dict[str, multiverse.DbAllegiance],
        styleMap: typing.Optional[typing.Mapping[
            str, # Style tag
            typing.Tuple[
                str, # Colour
                str, # Style
                float # Width
                ]]] = None
        ) -> typing.List[multiverse.DbRoute]:
    dbRoutes = []

    if rawMetadata.routes():
        for rawRoute in rawMetadata.routes():
            rawStartX, rawStartY = _parseHexString(rawRoute.startHex())
            rawEndX, rawEndY = _parseHexString(rawRoute.endHex())
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

            rawType = rawRoute.type()
            dbType = rawType if rawType else None

            dbWidth = rawRoute.width()

            dbColour = rawRoute.colour()
            if dbColour is not None and not common.isValidHtmlColour(dbColour):
                logging.warning(f'Converter ignoring invalid route colour {dbColour} in {rawMetadata.canonicalName()} at {milieu}')
                dbColour = None

            dbStyle = rawRoute.style()
            if dbStyle is not None:
                if dbStyle.lower() in _ValidLineStyles:
                    dbStyle = dbStyle.lower()
                else:
                    logging.warning(f'Converter ignoring invalid route style {dbStyle} in {rawMetadata.canonicalName()} at {milieu}')
                    dbStyle = None

            # This is replicating code from Traveller Map DrawMicroBorders. The
            # logic is quite fragile in order to mimic the the behaviour from
            # that code while allowing routes to inherit their style from their
            # allegiance.
            if styleMap and (dbAllegiance is None or dbAllegiance.code() not in styleMap):
                precedence = []
                if dbType is not None:
                    precedence.append(dbType)
                else:
                    precedence.append('Im')
                precedence.append(None)

                for tag in precedence:
                    if tag not in styleMap:
                        continue
                    defaultColour, defaultStyle, defaultWidth = styleMap.get(tag)
                    if dbColour is None:
                        dbColour = defaultColour
                    if dbStyle is None:
                        dbStyle = defaultStyle
                    if dbWidth is None:
                        dbWidth = defaultWidth
                    break

            dbRoutes.append(multiverse.DbRoute(
                startHexX=rawStartX,
                startHexY=rawStartY,
                endHexX=rawEndX,
                endHexY=rawEndY,
                startOffsetX=rawStartOffsetX if rawStartOffsetX is not None else 0,
                startOffsetY=rawStartOffsetY if rawStartOffsetY is not None else 0,
                endOffsetX=rawEndOffsetX if rawEndOffsetX is not None else 0,
                endOffsetY=rawEndOffsetY if rawEndOffsetY is not None else 0,
                type=dbType,
                style=dbStyle,
                colour=dbColour,
                width=dbWidth,
                allegianceId=dbAllegiance.id() if dbAllegiance else None))

    return dbRoutes

def _createDbBorders(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        dbAllegianceCodeMap: typing.Dict[str, multiverse.DbAllegiance],
        styleMap: typing.Optional[typing.Mapping[
            str, # Style tag
            typing.Tuple[
                str, # Colour
                str # Style
                ]]] = None,
        ) -> typing.List[multiverse.DbBorder]:
    dbBorders = []

    if rawMetadata.borders():
        for rawBorder in rawMetadata.borders():
            dbHexes = []
            for rawHex in rawBorder.hexes():
                dbHexes.append(_parseHexString(rawHex))

            if not dbHexes:
                logging.warning(f'Converter ignoring border with empty hex list in {rawMetadata.canonicalName()} at {milieu}')
                continue

            rawAllegianceCode = rawBorder.allegiance()
            dbAllegiance = dbAllegianceCodeMap.get(rawAllegianceCode) if rawAllegianceCode else None
            if rawAllegianceCode and not dbAllegiance:
                # TODO: This should probably log and continue with no allegiance,
                # if it's a custom sector it should also warn the user
                raise RuntimeError(f'Border in {rawMetadata.canonicalName()} at {milieu} uses undefined allegiance code {rawAllegianceCode}')

            dbColour = rawBorder.colour()
            if dbColour is not None and not common.isValidHtmlColour(dbColour):
                logging.warning(f'Converter ignoring invalid border colour {dbColour} in {rawMetadata.canonicalName()} at {milieu}')
                dbColour = None

            dbStyle = rawBorder.style()
            if dbStyle is not None:
                if dbStyle.lower() in _ValidLineStyles:
                    dbStyle = dbStyle.lower()
                else:
                    logging.warning(f'Converter ignoring invalid border style {dbStyle} in {rawMetadata.canonicalName()} at {milieu}')
                    dbStyle = None

            # This is replicating code from Traveller Map DrawMicroBorders. The
            # logic is quite fragile in order to mimic the the behaviour from
            # that code while allowing borders to inherit their style from their
            # allegiance.
            if styleMap and (dbAllegiance is None or dbAllegiance.code() not in styleMap):
                defaultColour, defaultStyle = styleMap.get(None, (None, None))
                if dbColour is None:
                    dbColour = defaultColour
                if dbStyle is None:
                    dbStyle = defaultStyle

            rawLabel = rawBorder.label()
            dbLabel = rawLabel if rawLabel else None

            rawLabelHex = rawBorder.labelHex()
            rawLabelOffsetX = rawBorder.labelOffsetX()
            rawLabelOffsetY = rawBorder.labelOffsetY()
            dbLabelX = None
            dbLabelY = None
            if rawLabelHex:
                rawLabelHexX, rawLabelHexY = _parseHexString(rawLabelHex)
                dbLabelX, dbLabelY = _hexToSectorWorldOffset(
                    hexX=rawLabelHexX,
                    hexY=rawLabelHexY,
                    # NOTE: The 0.7 multiplier is to mimic how Traveller Map
                    # scales the offset in DrawMicroLabels
                    worldOffsetX=(rawLabelOffsetX * 0.7) if rawLabelOffsetX is not None else None,
                    # NOTE: The coordinate space used for the offsets seems to
                    # have an inverted Y direction compared to world space
                    worldOffsetY=(-rawLabelOffsetY * 0.7) if rawLabelOffsetY is not None else None)

            # Show label use the same defaults as the traveller map Border class
            rawShowLabel = rawBorder.showLabel()
            dbShowLabel = rawShowLabel if rawShowLabel is not None else True

            rawWrapLabel = rawBorder.wrapLabel()
            dbWrapLabel = rawWrapLabel if rawWrapLabel is not None else False

            dbBorders.append(multiverse.DbBorder(
                hexes=dbHexes,
                allegianceId=dbAllegiance.id() if dbAllegiance else None,
                style=dbStyle,
                colour=dbColour,
                label=dbLabel,
                labelWorldX=dbLabelX,
                labelWorldY=dbLabelY,
                showLabel=dbShowLabel,
                wrapLabel=dbWrapLabel))

    return dbBorders

def _createDbRegions(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        ) -> typing.List[multiverse.DbBorder]:
    dbRegions = []

    if rawMetadata.regions():
        for rawRegion in rawMetadata.regions():
            dbHexes = []
            for rawHex in rawRegion.hexes():
                dbHexes.append(_parseHexString(rawHex))

            if not dbHexes:
                logging.warning(f'Converter ignoring region with empty hex list in {rawMetadata.canonicalName()} at {milieu}')
                continue

            rawLabel = rawRegion.label()
            dbLabel = rawLabel if rawLabel else None

            rawLabelHex = rawRegion.labelHex()
            rawLabelOffsetX = rawRegion.labelOffsetX()
            rawLabelOffsetY = rawRegion.labelOffsetY()
            dbLabelX = None
            dbLabelY = None
            if rawLabelHex:
                rawLabelHexX, rawLabelHexY = _parseHexString(rawLabelHex)
                dbLabelX, dbLabelY = _hexToSectorWorldOffset(
                    hexX=rawLabelHexX,
                    hexY=rawLabelHexY,
                    # NOTE: The 0.7 multiplier is to mimic how Traveller Map
                    # scales the offset in DrawMicroLabels
                    worldOffsetX=(rawLabelOffsetX * 0.7) if rawLabelOffsetX is not None else None,
                    # NOTE: The coordinate space used for the offsets seems to
                    # have an inverted Y direction compared to world space
                    worldOffsetY=(-rawLabelOffsetY * 0.7) if rawLabelOffsetY is not None else None)

            dbColour = rawRegion.colour()
            if dbColour is not None and not common.isValidHtmlColour(dbColour):
                logging.warning(f'Converter ignoring invalid region colour {dbColour} in {rawMetadata.canonicalName()} at {milieu}')
                dbColour = None

            # Show label use the same defaults as the Traveller Map Border class
            rawShowLabel = rawRegion.showLabel()
            dbShowLabel = rawShowLabel if rawShowLabel is not None else True

            rawWrapLabel = rawRegion.wrapLabel()
            dbWrapLabel = rawWrapLabel if rawWrapLabel is not None else False

            dbRegions.append(multiverse.DbRegion(
                hexes=dbHexes,
                colour=dbColour,
                label=dbLabel,
                labelWorldX=dbLabelX,
                labelWorldY=dbLabelY,
                showLabel=dbShowLabel,
                wrapLabel=dbWrapLabel))

    return dbRegions

def _createDbLabels(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        ) -> typing.List[multiverse.DbLabel]:
    dbLabels = []

    if rawMetadata.labels():
        for rawLabel in rawMetadata.labels():
            dbLabel = rawLabel.text()
            if not dbLabel:
                logging.warning(f'Converter ignoring empty label in {rawMetadata.canonicalName()} at {milieu}')
                continue

            rawHexX, rawHexY = _parseHexString(rawLabel.hex())
            rawOffsetX = rawLabel.offsetX()
            rawOffsetY = rawLabel.offsetY()
            dbX, dbY = _hexToSectorWorldOffset(
                hexX=rawHexX,
                hexY=rawHexY,
                # NOTE: The 0.7 multiplier is to mimic how Traveller Map
                # scales the offset in DrawMicroLabels
                worldOffsetX=(rawOffsetX * 0.7) if rawOffsetX is not None else None,
                # NOTE: The coordinate space used for the offsets seems to
                # have an inverted Y direction compared to world space
                worldOffsetY=(-rawOffsetY * 0.7) if rawOffsetY is not None else None)

            dbColour = rawLabel.colour()
            if dbColour is not None and not common.isValidHtmlColour(dbColour):
                logging.warning(f'Converter ignoring invalid label colour {dbColour} in {rawMetadata.canonicalName()} at {milieu}')
                dbColour = None

            dbSize = rawLabel.size()
            if dbSize is not None:
                if dbSize.lower() in _ValidLabelSizes:
                    dbSize = dbSize.lower()
                else:
                    logging.warning(f'Converter ignoring invalid label size {dbSize} in {rawMetadata.canonicalName()} at {milieu}')
                    dbSize = None

            rawWrap = rawLabel.wrap()
            dbWrap = rawWrap if rawWrap is not None else False

            dbLabels.append(multiverse.DbLabel(
                text=dbLabel,
                worldX=dbX,
                worldY=dbY,
                colour=dbColour,
                size=dbSize,
                wrap=dbWrap))

    return dbLabels

def _createDbTags(
        rawMetadata: survey.RawMetadata
        ) -> typing.List[multiverse.DbTag]:
    dbTags = []

    rawTags = rawMetadata.tags()
    if rawTags:
        for tag in rawTags.split():
            if tag:
                dbTags.append(multiverse.DbTag(tag=tag))

    return dbTags

def _createDbProducts(
        rawMetadata: survey.RawMetadata
        ) -> typing.List[multiverse.DbProduct]:
    rawSources = rawMetadata.sources()
    dbProducts = []

    if rawSources and rawSources.products():
        for product in rawSources.products():
            rawPublication = product.publication()
            rawAuthor = product.author()
            rawPublisher =product.publisher()
            rawReference = product.reference()

            dbProducts.append(multiverse.DbProduct(
                publication=rawPublication if rawPublication else None,
                author=rawAuthor if rawAuthor else None,
                publisher=rawPublisher if rawPublisher else None,
                reference=rawReference if rawReference else None))

    return dbProducts

# TODO: Not sure where this should live (probably SnapshotManager)
# The fact they live here means things like CustomUniverseWindow need
# to pull in multiverse when they shouldn't be dealing with this layer
_T5OfficialAllegiancesPath = 't5ss/allegiance_codes.tab'
def readSnapshotStockAllegiances() -> typing.List[survey.RawStockAllegiance]:
    return survey.parseTabStockAllegiances(
        content=multiverse.SnapshotManager.instance().readTextResource(
            filePath=_T5OfficialAllegiancesPath))

_T5OfficialSophontsPath = 't5ss/sophont_codes.tab'
def readSnapshotStockSophonts() -> typing.List[survey.RawStockSophont]:
    return survey.parseTabStockSophonts(
        content=multiverse.SnapshotManager.instance().readTextResource(
            filePath=_T5OfficialSophontsPath))

_OTUStyleSheet = 'styles/otu.css'
def readSnapshotStyleSheet() -> survey.RawStyleSheet:
    return survey.parseStyleSheet(
        content=multiverse.SnapshotManager.instance().readTextResource(
            filePath=_OTUStyleSheet))

def convertRawSectorToDbSector(
        milieu: str,
        rawMetadata: survey.RawMetadata,
        rawSystems: typing.Collection[survey.RawWorld],
        rawStockAllegiances: typing.Optional[typing.Collection[
            survey.RawStockAllegiance
            ]] = None,
        rawStockSophonts: typing.Optional[typing.Collection[
            survey.RawStockSophont
            ]] = None,
        rawStockStyleSheet: typing.Optional[survey.RawStyleSheet] = None,
        sectorId: typing.Optional[str] = None
        ) -> multiverse.DbSector:
    dbSectorX = rawMetadata.x()
    dbSectorY = rawMetadata.y()
    dbSectorName = rawMetadata.canonicalName()

    rawSectorLanguage = rawMetadata.nameLanguage(rawMetadata.canonicalName())
    dbSectorLanguage = rawSectorLanguage if rawSectorLanguage else None

    rawAbbreviation = rawMetadata.abbreviation()
    dbAbbreviation = rawAbbreviation if rawAbbreviation else None

    rawSectorLabel = rawMetadata.sectorLabel()
    dbSectorLabel = rawSectorLabel if rawSectorLabel else None

    rawSelected = rawMetadata.selected()
    dbSelected = rawSelected if rawSelected is not None else False

    rawSectorStyleSheet = None
    if rawMetadata.styleSheet():
        rawSectorStyleSheet = survey.parseStyleSheet(
            content=rawMetadata.styleSheet())

    routeStyleMap = _mergeRouteStyles(
        rawStockStyleSheet=rawStockStyleSheet,
        rawSectorStyleSheet=rawSectorStyleSheet)
    borderStyleMap = _mergeBorderStyles(
        rawStockStyleSheet=rawStockStyleSheet,
        rawSectorStyleSheet=rawSectorStyleSheet)

    dbAlternateNames = _createDbAlternateNames(
        milieu=milieu,
        rawMetadata=rawMetadata)

    dbSubsectorNames = _createDbSubsectorNames(
        milieu=milieu,
        rawMetadata=rawMetadata)

    dbAllegianceCodeMap = _createDbAllegiances(
        milieu=milieu,
        rawMetadata=rawMetadata,
        rawSystems=rawSystems,
        rawStockAllegiances=rawStockAllegiances,
        routeStyleMap=routeStyleMap,
        borderStyleMap=borderStyleMap)
    dbAllegiances = set(dbAllegianceCodeMap.values()) # Use unique allegiances

    dbSophontCodeMap, dbSophontNameMap = _createDbSophonts(
        rawSystems=rawSystems,
        rawStockSophonts=rawStockSophonts)
    dbSophonts = set(itertools.chain(dbSophontCodeMap.values(), dbSophontNameMap.values())) # Use unique sophonts

    dbSystems = _createDbSystems(
        milieu=milieu,
        rawMetadata=rawMetadata,
        rawSystems=rawSystems,
        dbAllegianceCodeMap=dbAllegianceCodeMap,
        dbSophontCodeMap=dbSophontCodeMap,
        dbSophontNameMap=dbSophontNameMap)

    dbRoutes = _createDbRoutes(
        milieu=milieu,
        rawMetadata=rawMetadata,
        dbAllegianceCodeMap=dbAllegianceCodeMap,
        styleMap=routeStyleMap)

    dbBorders = _createDbBorders(
        milieu=milieu,
        rawMetadata=rawMetadata,
        dbAllegianceCodeMap=dbAllegianceCodeMap,
        styleMap=borderStyleMap)

    dbRegions = _createDbRegions(
        milieu=milieu,
        rawMetadata=rawMetadata)

    dbLabels = _createDbLabels(
        milieu=milieu,
        rawMetadata=rawMetadata)

    dbTags = _createDbTags(rawMetadata=rawMetadata)

    dbProducts = _createDbProducts(rawMetadata=rawMetadata)

    rawSources = rawMetadata.sources()
    rawPrimarySource = rawSources.primary() if rawSources else None

    rawCredits = rawSources.credits() if rawSources else None
    dbCredits = rawCredits if rawCredits else None

    rawPublication = rawPrimarySource.publication() if rawPrimarySource else None
    dbPublication = rawPublication if rawPublication else None

    rawAuthor = rawPrimarySource.author() if rawPrimarySource else None
    dbAuthor = rawAuthor if rawAuthor else None

    rawPublisher = rawPrimarySource.publisher() if rawPrimarySource else None
    dbPublisher = rawPublisher if rawPublisher else None

    rawReference = rawPrimarySource.reference() if rawPrimarySource else None
    dbReference = rawReference if rawReference else None

    return multiverse.DbSector(
        id=sectorId,
        milieu=milieu,
        sectorX=dbSectorX,
        sectorY=dbSectorY,
        name=dbSectorName,
        language=dbSectorLanguage,
        abbreviation=dbAbbreviation,
        sectorLabel=dbSectorLabel,
        selected=dbSelected,
        alternateNames=dbAlternateNames,
        subsectorNames=dbSubsectorNames,
        allegiances=dbAllegiances,
        sophonts=dbSophonts,
        systems=dbSystems,
        routes=dbRoutes,
        borders=dbBorders,
        regions=dbRegions,
        labels=dbLabels,
        tags=dbTags,
        credits=dbCredits,
        publication=dbPublication,
        author=dbAuthor,
        publisher=dbPublisher,
        reference=dbReference,
        products=dbProducts)

def _createRawAlternateNames(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.List[str]]:
    rawAlternateNames = None
    if dbSector.alternateNames():
        rawAlternateNames = []
        for dbName in dbSector.alternateNames():
            rawAlternateNames.append(dbName.name())
    return rawAlternateNames

def _createRawNameLanguages(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.Dict[str, str]]:
    rawNameLanguages = {} if dbSector.language() or dbSector.alternateNames() else None

    if dbSector.language():
        rawNameLanguages[dbSector.name()] = dbSector.language()

    if dbSector.alternateNames():
        for dbName in dbSector.alternateNames():
            if dbName.language():
                rawNameLanguages[dbName.name()] = dbName.language()

    return rawNameLanguages

def _createRawSubsectorNames(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.Dict[str, str]]:
    rawSubsectorNames = None
    if dbSector.subsectorNames():
        rawSubsectorNames = {}
        for dbName in dbSector.subsectorNames():
            rawSubsectorNames[dbName.code()] = dbName.name()
    return rawSubsectorNames

def _createRawTags(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[str]:
    rawTags = None
    if dbSector.tags():
        rawTags = ' '.join(dbTag.tag() for dbTag in dbSector.tags())
    return rawTags

def _createRawAllegiances(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.List[survey.RawAllegiance]]:
    rawAllegiances = None
    if dbSector.allegiances():
        rawAllegiances = []
        for dbAllegiance in dbSector.allegiances():
            rawAllegiances.append(survey.RawAllegiance(
                code=dbAllegiance.code(),
                name=dbAllegiance.name(),
                base=dbAllegiance.base()))
    return rawAllegiances

def _createRawRoutes(
        dbSector: multiverse.DbSector,
        dbIdToAllegianceMap: typing.Mapping[str, multiverse.DbAllegiance]
        ) -> typing.Optional[typing.List[survey.RawRoute]]:
    rawRoutes = None
    if dbSector.routes():
        rawRoutes = []
        for dbRoute in dbSector.routes():
            dbAllegiance = None
            if dbRoute.allegianceId():
                dbAllegiance = dbIdToAllegianceMap.get(dbRoute.allegianceId())
                if not dbAllegiance:
                    pass # TODO: Log something

            rawRoutes.append(survey.RawRoute(
                startHex=_formatHexString(dbRoute.startHexX(), dbRoute.startHexY()),
                endHex=_formatHexString(dbRoute.endHexX(), dbRoute.endHexY()),
                startOffsetX=dbRoute.startOffsetX() if dbRoute.startOffsetX() else None,
                startOffsetY=dbRoute.startOffsetY() if dbRoute.startOffsetY() else None,
                endOffsetX=dbRoute.endOffsetX() if dbRoute.endOffsetX() else None,
                endOffsetY=dbRoute.endOffsetY() if dbRoute.endOffsetY() else None,
                allegiance=dbAllegiance.code() if dbAllegiance else None, # TODO: Should this be the code or the name
                type=dbRoute.type(),
                style=dbRoute.style(),
                colour=dbRoute.colour(),
                width=dbRoute.width()))

    return rawRoutes

def _createRawBorders(
        dbSector: multiverse.DbSector,
        dbIdToAllegianceMap: typing.Mapping[str, multiverse.DbAllegiance]
        ) -> typing.Optional[typing.List[survey.RawBorder]]:
    rawBorders = None
    if dbSector.borders():
        rawBorders = []
        for dbBorder in dbSector.borders():
            hexes = []
            for x, y in dbBorder.hexes():
                hexes.append(_formatHexString(x, y))

            dbAllegiance = None
            if dbBorder.allegianceId():
                dbAllegiance = dbIdToAllegianceMap.get(dbBorder.allegianceId())
                if not dbAllegiance:
                    pass # TODO: Log something

            labelHex = labelOffsetX = labelOffsetY = None
            if dbBorder.labelWorldX() is not None and dbBorder.labelWorldY() is not None:
                hexX, hexY, labelOffsetX, labelOffsetY = _sectorWorldOffsetToHex(
                    worldX=dbBorder.labelWorldX(),
                    worldY=dbBorder.labelWorldY())

                labelHex = _formatHexString(hexX, hexY)

                # NOTE: The 0.7 divisor is to mimic how Traveller Map scales the offset
                # in DrawMicroLabels
                if labelOffsetX is not None:
                    labelOffsetX = labelOffsetX / 0.7
                if labelOffsetY is not None:
                    labelOffsetY = -labelOffsetY / 0.7

            rawBorders.append(survey.RawBorder(
                hexes=hexes,
                allegiance=dbAllegiance.code() if dbAllegiance else None, # TODO: Should this be the code or the name
                showLabel=dbBorder.showLabel(),
                wrapLabel=dbBorder.wrapLabel(),
                labelHex=labelHex,
                labelOffsetX=labelOffsetX,
                labelOffsetY=labelOffsetY,
                label=dbBorder.label(),
                style=dbBorder.style(),
                colour=dbBorder.colour()))

    return rawBorders

def _createRawRegions(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.List[survey.RawRegion]]:
    rawRegions = None
    if dbSector.regions():
        rawRegions = []
        for dbRegion in dbSector.regions():
            hexes = []
            for x, y in dbRegion.hexes():
                hexes.append(_formatHexString(x, y))

            labelHex = labelOffsetX = labelOffsetY = None
            if dbRegion.labelWorldX() is not None and dbRegion.labelWorldY() is not None:
                hexX, hexY, labelOffsetX, labelOffsetY = _sectorWorldOffsetToHex(
                    worldX=dbRegion.labelWorldX(),
                    worldY=dbRegion.labelWorldY())

                labelHex = _formatHexString(hexX, hexY)

                # NOTE: The 0.7 divisor is to mimic how Traveller Map scales the offset
                # in DrawMicroLabels
                if labelOffsetX is not None:
                    labelOffsetX = labelOffsetX / 0.7
                if labelOffsetY is not None:
                    labelOffsetY = -labelOffsetY / 0.7

            rawRegions.append(survey.RawRegion(
                hexes=hexes,
                showLabel=dbRegion.showLabel(),
                wrapLabel=dbRegion.wrapLabel(),
                labelHex=labelHex,
                labelOffsetX=labelOffsetX,
                labelOffsetY=labelOffsetY,
                label=dbRegion.label(),
                colour=dbRegion.colour()))

    return rawRegions

def _createRawLabels(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.List[survey.RawLabel]]:
    rawLabels = None
    if dbSector.labels():
        rawLabels = []
        for dbLabel in dbSector.labels():
            labelHex = labelOffsetX = labelOffsetY = None
            if dbLabel.worldX() is not None and dbLabel.worldY() is not None:
                hexX, hexY, labelOffsetX, labelOffsetY = _sectorWorldOffsetToHex(
                    worldX=dbLabel.worldX(),
                    worldY=dbLabel.worldY())

                labelHex = _formatHexString(hexX, hexY)

                # NOTE: The 0.7 divisor is to mimic how Traveller Map scales the offset
                # in DrawMicroLabels
                if labelOffsetX is not None:
                    labelOffsetX = labelOffsetX / 0.7
                if labelOffsetY is not None:
                    labelOffsetY = -labelOffsetY / 0.7

            rawLabels.append(survey.RawLabel(
                text=dbLabel.text(),
                hex=labelHex,
                offsetX=labelOffsetX,
                offsetY=labelOffsetY,
                colour=dbLabel.colour(),
                size=dbLabel.size(),
                wrap=dbLabel.wrap()))

    return rawLabels

def _createRawSources(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[survey.RawSources]:
    rawPrimarySource = None
    if dbSector.publication() or dbSector.author() or dbSector.publisher() or dbSector.reference():
        rawPrimarySource = survey.RawSource(
            publication=dbSector.publication(),
            author=dbSector.author(),
            publisher=dbSector.publisher(),
            reference=dbSector.reference())

    rawProducts = None
    if dbSector.products():
        rawProducts = []
        for dbProduct in dbSector.products():
            rawProducts.append(survey.RawSource(
                publication=dbProduct.publication(),
                author=dbProduct.author(),
                publisher=dbProduct.publisher(),
                reference=dbProduct.reference()))

    rawSources = None
    if dbSector.credits() or rawPrimarySource or rawProducts:
        rawSources = survey.RawSources(
            credits=dbSector.credits(),
            primary=rawPrimarySource,
            products=rawProducts)

    return rawSources

def _createRawMetadata(
        dbSector: multiverse.DbSector
        ) -> survey.RawMetadata:
    if dbSector.allegiances():
        dbIdToAllegianceMap = {dbAllegiance.id(): dbAllegiance for dbAllegiance in dbSector.allegiances()}
    else:
        dbIdToAllegianceMap = {}

    return survey.RawMetadata(
        canonicalName=dbSector.name(),
        alternateNames=_createRawAlternateNames(dbSector=dbSector),
        nameLanguages=_createRawNameLanguages(dbSector=dbSector),
        abbreviation=dbSector.abbreviation(),
        sectorLabel=dbSector.sectorLabel(),
        subsectorNames=_createRawSubsectorNames(dbSector=dbSector),
        x=dbSector.sectorX(),
        y=dbSector.sectorY(),
        selected=dbSector.selected(),
        tags=_createRawTags(dbSector=dbSector),
        allegiances=_createRawAllegiances(dbSector=dbSector),
        routes=_createRawRoutes(dbSector=dbSector, dbIdToAllegianceMap=dbIdToAllegianceMap),
        borders=_createRawBorders(dbSector=dbSector, dbIdToAllegianceMap=dbIdToAllegianceMap),
        regions=_createRawRegions(dbSector=dbSector),
        labels=_createRawLabels(dbSector=dbSector),
        sources=_createRawSources(dbSector=dbSector),
        styleSheet=None)

def _createRawWorlds(
        dbSector: multiverse.DbSector
        ) -> typing.List[survey.RawWorld]:
    if dbSector.allegiances():
        dbIdToAllegianceMap = {dbAllegiance.id(): dbAllegiance for dbAllegiance in dbSector.allegiances()}
    else:
        dbIdToAllegianceMap = {}

    if dbSector.sophonts():
        dbIdToSophontMap = {dbSophont.id(): dbSophont for dbSophont in dbSector.sophonts()}
    else:
        dbIdToSophontMap = {}

    rawWorlds = []
    if dbSector.systems():
        for dbSystem in dbSector.systems():
            dbMainWorld = None
            for dbBody in dbSystem.bodies():
                if isinstance(dbBody, multiverse.DbWorld) and dbBody.isMainWorld():
                    dbMainWorld = dbBody
                    break

            dbSystemAllegiance = None
            if dbSystem.allegianceId():
                dbSystemAllegiance = dbIdToAllegianceMap.get(dbSystem.allegianceId())
                if not dbSystemAllegiance:
                    pass # TODO: Log something

            rawUWP = survey.formatSystemUWPString(
                starport=dbMainWorld.starport() if dbMainWorld else None,
                worldSize=dbMainWorld.worldSize() if dbMainWorld else None,
                atmosphere=dbMainWorld.atmosphere() if dbMainWorld else None,
                hydrographics=dbMainWorld.hydrographics() if dbMainWorld else None,
                population=dbMainWorld.population() if dbMainWorld else None,
                government=dbMainWorld.government() if dbMainWorld else None,
                lawLevel=dbMainWorld.lawLevel() if dbMainWorld else None,
                techLevel=dbMainWorld.techLevel() if dbMainWorld else None)

            rawEconomics = survey.formatSystemEconomicsString(
                resources=dbMainWorld.resources() if dbMainWorld else None,
                labour=dbMainWorld.labour() if dbMainWorld else None,
                infrastructure=dbMainWorld.infrastructure() if dbMainWorld else None,
                # TODO: Check that generated tab & column files are valid
                # when the efficiency is unknown. I think the fact it's
                # 2 character string (with +/-) but it's only putting
                # in a single ? might break things
                efficiency=dbMainWorld.efficiency() if dbMainWorld else None)

            rawCulture = survey.formatSystemCultureString(
                heterogeneity=dbMainWorld.heterogeneity() if dbMainWorld else None,
                acceptance=dbMainWorld.acceptance() if dbMainWorld else None,
                strangeness=dbMainWorld.strangeness() if dbMainWorld else None,
                symbols=dbMainWorld.symbols() if dbMainWorld else None)

            rawPBG = survey.formatSystemPBGString(
                populationMultiplier=dbMainWorld.populationMultiplier() if dbMainWorld else None,
                planetoidBelts=survey.ehexFromInteger(value=dbSystem.planetoidBeltCount(), default=None),
                gasGiants=survey.ehexFromInteger(value=dbSystem.gasGiantCount(), default=None))

            numPlanetoidBelt = dbSystem.planetoidBeltCount()
            numGasGiants = dbSystem.gasGiantCount()
            numWorlds = dbSystem.worldCount()
            rawSystemWorldCount = None
            if numPlanetoidBelt is not None or numGasGiants is not None or numWorlds is not None:
                rawSystemWorldCount = 0
                if numPlanetoidBelt:
                    rawSystemWorldCount += numPlanetoidBelt
                if numGasGiants:
                    rawSystemWorldCount += numGasGiants
                if numWorlds:
                    rawSystemWorldCount += numWorlds

            rawNobilities = None
            rawBases = None
            rawTradeCodes = None
            rawRemarks = None
            if dbMainWorld:
                if dbMainWorld.nobilities():
                    rawNobilities = survey.formatSystemNobilityString(
                        nobilities=[dbNobility.code() for dbNobility in dbMainWorld.nobilities()])

                if dbMainWorld.bases():
                    rawBases = survey.formatSystemBasesString(
                        bases=[dbBase.code() for dbBase in dbMainWorld.bases()])

                if dbMainWorld.tradeCodes():
                    rawTradeCodes = [dbTradeCode.code() for dbTradeCode in dbMainWorld.tradeCodes()]

                rawMajorRaceHomeWorlds = None
                rawMinorRaceHomeWorlds = None
                rawSophontPopulations = None
                rawDiebackSophonts = None
                if dbMainWorld.sophontPopulations():
                    for dbSophontPopulation in dbMainWorld.sophontPopulations():
                        dbSophont = dbIdToSophontMap.get(dbSophontPopulation.sophontId())
                        if not dbSophont:
                            # TODO: Log something
                            continue

                        if dbSophontPopulation.isHomeWorld():
                            if dbSophont.isMajor():
                                if rawMajorRaceHomeWorlds is None:
                                    rawMajorRaceHomeWorlds = []
                                rawMajorRaceHomeWorlds.append((
                                    dbSophont.name(),
                                    int(dbSophontPopulation.percentage())))
                            else:
                                if rawMinorRaceHomeWorlds is None:
                                    rawMinorRaceHomeWorlds = []
                                rawMinorRaceHomeWorlds.append((
                                    dbSophont.name(),
                                    dbSophontPopulation.percentage()))

                        if dbSophontPopulation.isDieBack():
                            if rawDiebackSophonts is None:
                                rawDiebackSophonts = []
                            rawDiebackSophonts.append(dbSophont.name()) # TODO: Should this be the name or code
                        elif not dbSophontPopulation.isHomeWorld():
                            if rawSophontPopulations is None:
                                rawSophontPopulations = []
                            rawSophontPopulations.append((
                                dbSophont.code(),
                                dbSophontPopulation.percentage()))

                rawOwningSystems = None
                if dbMainWorld.owningSystems():
                    rawOwningSystems = []
                    for dbOwner in dbMainWorld.owningSystems():
                        rawOwningSystems.append((dbOwner.hexX(), dbOwner.hexY(), dbOwner.sectorAbbreviation()))

                rawColonySystems = None
                if dbMainWorld.colonySystems():
                    rawColonySystems = []
                    for dbColony in dbMainWorld.colonySystems():
                        rawColonySystems.append((dbColony.hexX(), dbColony.hexY(), dbColony.sectorAbbreviation()))

                rawRulingAllegiances = None
                if dbMainWorld.rulingAllegiances():
                    rawRulingAllegiances = []
                    for dbRuler in dbMainWorld.rulingAllegiances():
                        dbRulingAllegiance = dbIdToAllegianceMap.get(dbRuler.allegianceId())
                        if dbRulingAllegiance is None:
                            # TODO: Log something
                            continue
                        rawRulingAllegiances.append(dbRulingAllegiance.name()) # TODO: Should this be name or code?

                rawResearchStations = None
                if dbMainWorld.researchStations():
                    rawResearchStations = [dbStation.code() for dbStation in dbMainWorld.researchStations()]

                rawCustomRemarks = None
                if dbMainWorld.customRemarks():
                    rawCustomRemarks = [dbRemark.remark() for dbRemark in dbMainWorld.customRemarks()]

                hasRemarks = rawTradeCodes or rawMajorRaceHomeWorlds or rawMinorRaceHomeWorlds or \
                    rawSophontPopulations or rawDiebackSophonts or rawOwningSystems or rawColonySystems or \
                    rawRulingAllegiances or rawResearchStations or rawCustomRemarks
                if hasRemarks:
                    rawRemarks = survey.formatSystemRemarksString(
                        tradeCodes=rawTradeCodes,
                        majorRaceHomeWorlds=rawMajorRaceHomeWorlds,
                        minorRaceHomeWorlds=rawMinorRaceHomeWorlds,
                        sophontPopulations=rawSophontPopulations,
                        dieBackSophonts=rawDiebackSophonts,
                        owningSystems=rawOwningSystems,
                        colonySystems=rawColonySystems,
                        rulingAllegiances=rawRulingAllegiances,
                        researchStations=rawResearchStations,
                        customRemarks=rawCustomRemarks)

            rawStellar = None
            if dbSystem.stars():
                rawStars = [(dbStar.luminosityClass(), dbStar.spectralClass(), dbStar.spectralScale()) for dbStar in dbSystem.stars()]
                rawStellar = survey.formatSystemStellarString(stars=rawStars)

            rawWorlds.append(survey.RawWorld(
                hex=_formatHexString(dbSystem.hexX(), dbSystem.hexY()),
                name=dbSystem.name(),
                allegiance=dbSystemAllegiance.code() if dbSystemAllegiance else None,
                zone=dbSystem.zone(),
                uwp=rawUWP,
                economics=rawEconomics,
                culture=rawCulture,
                nobility=rawNobilities,
                bases=rawBases,
                remarks=rawRemarks,
                pbg=rawPBG,
                systemWorlds=rawSystemWorldCount,
                stellar=rawStellar,
                sectorAbbreviation=dbSector.abbreviation(),
                subSectorCode=_hexToSubsectorCode(hexX=dbSystem.hexX(), hexY=dbSystem.hexY()),
                # TODO: I'm not sure if I need to bother supporting these
                importance=None,
                resourceUnits=None))

    return rawWorlds

def convertDbSectorToRawSector(
        dbSector: multiverse.DbSector
        ) -> typing.Tuple[
            survey.RawMetadata,
            typing.List[survey.RawWorld]]:
    rawMetadata = _createRawMetadata(
        dbSector=dbSector)

    rawWorlds = _createRawWorlds(
        dbSector=dbSector)

    return (rawMetadata, rawWorlds)
