import common
import logging
import multiverse
import survey
import typing

# TODO: This code needs tidying up
#   - The main work function has a lot of duplicated code
#   - The merged sector style maps should be generated once per sector
# TODO: The main algorithm is generating to many disambiguated allegiance names (i.e. ones structured "<ORIGINAL_NAME> (<CODE>)")

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
# TODO: This isn't being used
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

_ValidLineStyles = set(['solid', 'dashed', 'dotted'])

class AllegianceMapper(object):
    class _CodeTracker(object):
        def __init__(self):
            self._metadataToCodes: typing.Dict[
                typing.Optional[survey.RawMetadata],
                typing.Set[str]
            ] = {}

        def addCode(self, rawMetadata: typing.Optional[survey.RawMetadata], code: str) -> None:
            codes = self._metadataToCodes.get(rawMetadata)
            if codes is None:
                codes = set()
                self._metadataToCodes[rawMetadata] = codes
            codes.add(code)

        def hasCode(self, rawMetadata: survey.RawMetadata, code: str) -> bool:
            codes = self._metadataToCodes.get(rawMetadata)
            if codes is not None and code in codes:
                return True
            codes = self._metadataToCodes.get(None)
            return codes is not None and code in codes

    def __init__(
            self,
            milieu: str,
            rawSectors: typing.List[typing.Tuple[survey.RawMetadata, typing.List[survey.RawWorld]]],
            rawStockAllegiances: typing.List[survey.RawStockAllegiance],
            rawStockStyleSheet: survey.RawStyleSheet,
            ) -> None:
        self._nameToDbAllegiance: typing.Dict[
            str, # Allegiance Name
            multiverse.DbAllegiance] = {}
        self._globalCodeToDbAllegiance: typing.Dict[
            str, # Allegiance Code
            multiverse.DbAllegiance] = {}
        self._metadataToCodeMap: typing.Dict[
            survey.RawMetadata,
            typing.Dict[
                str, # Allegiance Code
                multiverse.DbAllegiance
            ]] = {}

        self._usedAllegiances: typing.Set[multiverse.DbAllegiance] = set()

        self._populate(
            milieu=milieu,
            rawSectors=rawSectors,
            rawStockAllegiances=rawStockAllegiances,
            rawStockStyleSheet=rawStockStyleSheet)

    def hasMapping(
            self,
            rawMetadata: survey.RawMetadata,
            code: str
            ) -> bool:
        codeMap = self._metadataToCodeMap.get(rawMetadata)
        if codeMap is not None and code in codeMap:
            return True
        return code in self._globalCodeToDbAllegiance

    def lookupAllegiance(
            self,
            rawMetadata: survey.RawMetadata,
            code: str
            ) -> typing.Optional[multiverse.DbAllegiance]:
        codeMap = self._metadataToCodeMap.get(rawMetadata)
        if codeMap is not None:
            dbAllegiance = codeMap.get(code)
            if dbAllegiance is not None:
                self._usedAllegiances.add(dbAllegiance)
                return dbAllegiance

        dbAllegiance = self._globalCodeToDbAllegiance.get(code)
        if dbAllegiance is not None:
            self._usedAllegiances.add(dbAllegiance)
        return dbAllegiance

    def listAllegiances(self, usedOnly: bool = True) -> typing.List[multiverse.DbAllegiance]:
        if usedOnly:
            return list(self._usedAllegiances)
        return list(self._nameToDbAllegiance.values())

    def clearUsed(self) -> None:
        self._usedAllegiances.clear()

    def _populate(
            self,
            milieu: str,
            rawSectors: typing.List[typing.Tuple[survey.RawMetadata, typing.List[survey.RawWorld]]],
            rawStockAllegiances: typing.List[survey.RawStockAllegiance],
            rawStockStyleSheet: survey.RawStyleSheet
            ) -> None:
        sectorAbbreviationToMetadata = {m.abbreviation(): m for m, _ in rawSectors if m.abbreviation() is not None}
        stockAllegianceCodeToRouteStyle = self._createRouteStyleMap(
            rawStyleSheet=rawStockStyleSheet,
            loggingName='Stock Styles')
        stockAllegianceCodeToBorderStyle = self._createBorderStyleMap(
            rawStyleSheet=rawStockStyleSheet,
            loggingName='Stock Styles')

        rawStockAllegiances = self._selectStockAllegiances(
            milieu=milieu,
            rawStockAllegiances=rawStockAllegiances)

        globalDbAllegiances: typing.List[multiverse.DbAllegiance] = []
        metadataToDbAllegiances: typing.Dict[
            survey.RawMetadata,
            typing.List[multiverse.DbAllegiance]] = {}
        seenCodes = AllegianceMapper._CodeTracker()

        for rawAllegiance in rawStockAllegiances:
            code = rawAllegiance.code()
            location = rawAllegiance.location()

            if location is None or location == 'various':
                routeColour, routeStyle, routeWidth = stockAllegianceCodeToRouteStyle.get(
                    code,
                    (None, None, None))
                borderColour, borderStyle = stockAllegianceCodeToBorderStyle.get(
                    code,
                    (None, None))
                dbAllegiance = multiverse.DbAllegiance(
                    name=rawAllegiance.name(),
                    code=code,
                    legacy=rawAllegiance.legacy(),
                    base=rawAllegiance.base(),
                    routeColour=routeColour,
                    routeStyle=routeStyle,
                    routeWidth=routeWidth,
                    borderColour=borderColour,
                    borderStyle=borderStyle)
                globalDbAllegiances.append(dbAllegiance)
                seenCodes.addCode(rawMetadata=None, code=dbAllegiance.code())
            else:
                for sectorAbbreviation in location.split('/'):
                    rawMetadata = sectorAbbreviationToMetadata.get(sectorAbbreviation)
                    if rawMetadata is None:
                        # TODO: Log and continue
                        print(f'Missing Sector {sectorAbbreviation}')
                        continue

                    sectorAllegianceCodeToRouteStyle = stockAllegianceCodeToRouteStyle
                    sectorAllegianceCodeToBorderStyle = stockAllegianceCodeToBorderStyle
                    rawStyleSheet = rawMetadata.styleSheet()
                    if rawStyleSheet:
                        sectorAllegianceCodeToRouteStyle = self._mergeRouteStyles(
                            sectorStyles=self._createRouteStyleMap(
                                rawStyleSheet=rawStyleSheet,
                                loggingName=rawMetadata.canonicalName()),
                            stockStyles=stockAllegianceCodeToRouteStyle)
                        sectorAllegianceCodeToBorderStyle = self._mergeBorderStyles(
                            sectorStyles=self._createBorderStyleMap(
                                rawStyleSheet=rawStyleSheet,
                                loggingName=rawMetadata.canonicalName()),
                            stockStyles=stockAllegianceCodeToBorderStyle)
                    routeColour, routeStyle, routeWidth = sectorAllegianceCodeToRouteStyle.get(
                        code,
                        (None, None, None))
                    borderColour, borderStyle = sectorAllegianceCodeToBorderStyle.get(
                        code,
                        (None, None))

                    sectorDbAllegiances = metadataToDbAllegiances.get(rawMetadata)
                    if sectorDbAllegiances is None:
                        sectorDbAllegiances = []
                        metadataToDbAllegiances[rawMetadata] = sectorDbAllegiances
                    dbAllegiance = multiverse.DbAllegiance(
                        name=rawAllegiance.name(),
                        code=code,
                        legacy=rawAllegiance.legacy(),
                        base=rawAllegiance.base(),
                        routeColour=routeColour,
                        routeStyle=routeStyle,
                        routeWidth=routeWidth,
                        borderColour=borderColour,
                        borderStyle=borderStyle)
                    sectorDbAllegiances.append(dbAllegiance)
                    seenCodes.addCode(rawMetadata=rawMetadata, code=dbAllegiance.code())

        for rawMetadata, _ in rawSectors:
            rawAllegiances = rawMetadata.allegiances()
            if rawAllegiances is None:
                continue

            sectorAllegianceCodeToRouteStyle = stockAllegianceCodeToRouteStyle
            sectorAllegianceCodeToBorderStyle = stockAllegianceCodeToBorderStyle
            rawStyleSheet = rawMetadata.styleSheet()
            if rawStyleSheet:
                sectorAllegianceCodeToRouteStyle = self._mergeRouteStyles(
                    sectorStyles=self._createRouteStyleMap(
                        rawStyleSheet=rawStyleSheet,
                        loggingName=rawMetadata.canonicalName()),
                    stockStyles=stockAllegianceCodeToRouteStyle)
                sectorAllegianceCodeToBorderStyle = self._mergeBorderStyles(
                    sectorStyles=self._createBorderStyleMap(
                        rawStyleSheet=rawStyleSheet,
                        loggingName=rawMetadata.canonicalName()),
                    stockStyles=stockAllegianceCodeToBorderStyle)

            for rawAllegiance in rawAllegiances:
                code = rawAllegiance.code()
                routeColour, routeStyle, routeWidth = sectorAllegianceCodeToRouteStyle.get(
                    code,
                    (None, None, None))
                borderColour, borderStyle = sectorAllegianceCodeToBorderStyle.get(
                    code,
                    (None, None))

                sectorDbAllegiances = metadataToDbAllegiances.get(rawMetadata)
                if sectorDbAllegiances is None:
                    sectorDbAllegiances = []
                    metadataToDbAllegiances[rawMetadata] = sectorDbAllegiances
                dbAllegiance = multiverse.DbAllegiance(
                    name=rawAllegiance.name(),
                    code=code,
                    base=rawAllegiance.base(),
                    routeColour=routeColour,
                    routeStyle=routeStyle,
                    routeWidth=routeWidth,
                    borderColour=borderColour,
                    borderStyle=borderStyle)
                sectorDbAllegiances.append(dbAllegiance)
                seenCodes.addCode(rawMetadata=rawMetadata, code=dbAllegiance.code())

        for rawMetadata, rawWorlds in rawSectors:
            usedCodes = self._collectUsedCodes(rawMetadata=rawMetadata, rawWorlds=rawWorlds)

            sectorAllegianceCodeToRouteStyle = stockAllegianceCodeToRouteStyle
            sectorAllegianceCodeToBorderStyle = stockAllegianceCodeToBorderStyle
            rawStyleSheet = rawMetadata.styleSheet()
            if rawStyleSheet:
                sectorAllegianceCodeToRouteStyle = self._mergeRouteStyles(
                    sectorStyles=self._createRouteStyleMap(
                        rawStyleSheet=rawStyleSheet,
                        loggingName=rawMetadata.canonicalName()),
                    stockStyles=stockAllegianceCodeToRouteStyle)
                sectorAllegianceCodeToBorderStyle = self._mergeBorderStyles(
                    sectorStyles=self._createBorderStyleMap(
                        rawStyleSheet=rawStyleSheet,
                        loggingName=rawMetadata.canonicalName()),
                    stockStyles=stockAllegianceCodeToBorderStyle)

            for code in usedCodes:
                if seenCodes.hasCode(code=code, rawMetadata=rawMetadata):
                    continue # Not missing

                routeColour, routeStyle, routeWidth = sectorAllegianceCodeToRouteStyle.get(
                    code,
                    (None, None, None))
                borderColour, borderStyle = sectorAllegianceCodeToBorderStyle.get(
                    code,
                    (None, None))

                # There is no mapping for this code so create one with the code as
                # the name
                sectorDbAllegiances = metadataToDbAllegiances.get(rawMetadata)
                if sectorDbAllegiances is None:
                    sectorDbAllegiances = []
                    metadataToDbAllegiances[rawMetadata] = sectorDbAllegiances
                sectorDbAllegiances.append(multiverse.DbAllegiance(
                    name=code,
                    code=code,
                    routeColour=routeColour,
                    routeStyle=routeStyle,
                    routeWidth=routeWidth,
                    borderColour=borderColour,
                    borderStyle=borderStyle))

        for dbAllegiance in globalDbAllegiances:
            self._nameToDbAllegiance[dbAllegiance.name()] = dbAllegiance
            self._globalCodeToDbAllegiance[dbAllegiance.code()] = dbAllegiance

        localNameToAllegianceData: typing.Dict[
            str, # Allegiance Name
            typing.List[typing.Tuple[
                multiverse.DbAllegiance,
                survey.RawMetadata]]] = {}
        for rawMetadata, dbAllegiances in metadataToDbAllegiances.items():
            for dbAllegiance in dbAllegiances:
                name = dbAllegiance.name()
                allegianceData = localNameToAllegianceData.get(name)
                if allegianceData is None:
                    allegianceData = []
                    localNameToAllegianceData[name] = allegianceData
                allegianceData.append((dbAllegiance, rawMetadata))

        for name, allegianceData in localNameToAllegianceData.items():
            consistentCode = None
            for dbAllegiance, _ in allegianceData:
                if consistentCode is not None and dbAllegiance.code() != consistentCode:
                    consistentCode = None
                    break
                consistentCode = dbAllegiance.code()

            dbAllegianceForName = self._nameToDbAllegiance.get(name)
            if dbAllegianceForName is not None:
                # There is a stock allegiance with this name
                if consistentCode is not None and dbAllegianceForName.code() != consistentCode:
                    consistentCode = None

                if not consistentCode:
                    for dbAllegiance, rawMetadata in allegianceData:
                        codeMap = self._metadataToCodeMap.get(rawMetadata)
                        if codeMap is None:
                            codeMap = {}
                            self._metadataToCodeMap[rawMetadata] = codeMap
                        codeMap[dbAllegiance.code()] = dbAllegianceForName
            else:
                consistentRouteColour = None
                for dbAllegiance, _ in allegianceData:
                    if consistentRouteColour is not None and dbAllegiance.routeColour() != consistentRouteColour:
                        consistentRouteColour = None
                        break
                    consistentRouteColour = dbAllegiance.routeColour()

                consistentRouteStyle = None
                for dbAllegiance, _ in allegianceData:
                    if consistentRouteStyle is not None and dbAllegiance.routeStyle() != consistentRouteStyle:
                        consistentRouteStyle = None
                        break
                    consistentRouteStyle = dbAllegiance.routeStyle()

                consistentRouteWidth = None
                for dbAllegiance, _ in allegianceData:
                    if consistentRouteWidth is not None and dbAllegiance.routeWidth() != consistentRouteWidth:
                        consistentRouteWidth = None
                        break
                    consistentRouteWidth = dbAllegiance.routeWidth()

                consistentBorderColour = None
                for dbAllegiance, _ in allegianceData:
                    if consistentBorderColour is not None and dbAllegiance.borderColour() != consistentBorderColour:
                        consistentBorderColour = None
                        break
                    consistentBorderColour = dbAllegiance.borderColour()

                consistentBorderStyle = None
                for dbAllegiance, _ in allegianceData:
                    if consistentBorderStyle is not None and dbAllegiance.borderStyle() != consistentBorderStyle:
                        consistentBorderStyle = None
                        break
                    consistentBorderStyle = dbAllegiance.borderStyle()

                if consistentCode:
                    legacy = base = None
                    for dbAllegiance, _ in allegianceData:
                        if legacy is None:
                            legacy = dbAllegiance.legacy()
                        if base is None:
                            base = dbAllegiance.base()

                    dbAllegianceForName = multiverse.DbAllegiance(
                        name=name,
                        code=consistentCode,
                        legacy=legacy,
                        base=base,
                        routeColour=consistentRouteColour,
                        routeStyle=consistentRouteStyle,
                        routeWidth=consistentRouteWidth,
                        borderColour=consistentBorderColour,
                        borderStyle=consistentBorderStyle)
                    self._nameToDbAllegiance[name] = dbAllegianceForName

                    for _, rawMetadata in allegianceData:
                        codeMap = self._metadataToCodeMap.get(rawMetadata)
                        if codeMap is None:
                            codeMap = {}
                            self._metadataToCodeMap[rawMetadata] = codeMap
                        codeMap[dbAllegianceForName.code()] = dbAllegianceForName
                else:
                    for dbAllegiance, rawMetadata in allegianceData:
                        name = f'{dbAllegiance.name()} ({dbAllegiance.code()})'
                        dbAllegianceForName = self._nameToDbAllegiance.get(name)
                        if dbAllegianceForName is None:
                            dbAllegianceForName = multiverse.DbAllegiance(
                                name=name,
                                code=dbAllegiance.code(),
                                legacy=dbAllegiance.legacy(),
                                base=dbAllegiance.base(),
                                routeColour=consistentRouteColour,
                                routeStyle=consistentRouteStyle,
                                routeWidth=consistentRouteWidth,
                                borderColour=consistentBorderColour,
                                borderStyle=consistentBorderStyle)
                            self._nameToDbAllegiance[name] = dbAllegianceForName

                        codeMap = self._metadataToCodeMap.get(rawMetadata)
                        if codeMap is None:
                            codeMap = {}
                            self._metadataToCodeMap[rawMetadata] = codeMap
                        codeMap[dbAllegianceForName.code()] = dbAllegianceForName

    def _selectStockAllegiances(
            self,
            milieu: str,
            rawStockAllegiances: typing.List[survey.RawStockAllegiance]
            ) -> typing.List[survey.RawStockAllegiance]:
        rawAllegiances = list(rawStockAllegiances)
        rawAllegiances.extend(_LegacyAllegiances)

        rawMilieuAllegiances = _T5UnofficialAllegiancesMap.get(milieu)
        if rawMilieuAllegiances:
            rawAllegiances.extend(rawMilieuAllegiances)

        return rawAllegiances

    def _collectUsedCodes(
            self,
            rawMetadata: survey.RawMetadata,
            rawWorlds: typing.List[survey.RawWorld]
            ) -> typing.Set[str]:
        usedCodes: typing.Set[str] = set()
        if rawWorlds:
            for rawWorld in rawWorlds:
                rawAllegianceCode = rawWorld.allegianceCode()
                if rawAllegianceCode and rawAllegianceCode not in _IgnoreAllegianceCodes:
                    usedCodes.add(rawAllegianceCode)

                rawRemarks = rawWorld.remarks()
                if rawRemarks and rawRemarks.rulingAllegiances():
                    for rawAllegianceCode in rawRemarks.rulingAllegiances():
                        if rawAllegianceCode not in _IgnoreAllegianceCodes:
                            usedCodes.add(rawAllegianceCode)
        if rawMetadata.routes():
            for rawRoute in rawMetadata.routes():
                rawAllegianceCode = rawRoute.allegianceCode()
                if rawAllegianceCode and rawAllegianceCode not in _IgnoreAllegianceCodes:
                    usedCodes.add(rawAllegianceCode)
        if rawMetadata.borders():
            for rawBorder in rawMetadata.borders():
                rawAllegianceCode = rawBorder.allegianceCode()
                if rawAllegianceCode and rawAllegianceCode not in _IgnoreAllegianceCodes:
                    usedCodes.add(rawAllegianceCode)
        return usedCodes

    def _createRouteStyleMap(
            self,
            rawStyleSheet: survey.RawStyleSheet,
            loggingName: str
            ) -> typing.Dict[
                str, # Style tag
                typing.Tuple[
                    typing.Optional[str], # Colour
                    typing.Optional[str], # Style
                    typing.Optional[float]]]: # Width
        defaultColour = defaultStyle = defaultWidth = None
        for rawStyle in rawStyleSheet.routeStyles():
            tag = rawStyle.tag()
            if tag is not None:
                continue

            colour = rawStyle.colour()
            style = rawStyle.style()
            width = rawStyle.width()

            if colour is not None and not common.isValidHtmlColour(colour):
                logging.warning(f'Converter ignoring invalid colour {colour} for default route style from sector style sheet for {loggingName}')
                colour = None
            if style is not None:
                if style.lower() in _ValidLineStyles:
                    style = style.lower()
                else:
                    logging.warning(f'Converter ignoring invalid line style {style} for default route style from sector style sheet for {loggingName}')
                    style = None

            if colour is not None:
                defaultColour = colour
            if style is not None:
                defaultStyle = style
            if width is not None:
                defaultWidth = width

        styleMap = {}
        for rawStyle in rawStyleSheet.routeStyles():
            tag = rawStyle.tag()
            if tag is None:
                continue
            colour = rawStyle.colour()
            style = rawStyle.style()
            width = rawStyle.width()

            if colour is not None and not common.isValidHtmlColour(colour):
                logging.warning(f'Converter ignoring invalid colour {colour} for route style {tag} from sector style sheet for {loggingName}')
                colour = None
            if style is not None:
                if style.lower() in _ValidLineStyles:
                    style = style.lower()
                else:
                    logging.warning(f'Converter ignoring invalid line style {style} for route style {tag} from sector style sheet for {loggingName}')
                    style = None

            styleMap[tag] = (
                colour if colour is not None else defaultColour,
                style if style is not None else defaultStyle,
                width if width is not None else defaultWidth)

        return styleMap

    def _mergeRouteStyles(
            self,
            sectorStyles: typing.Optional[typing.Dict[
                str, # Style tag
                typing.Tuple[
                    str, # Colour
                    str, # Style
                    float]]], # Width
            stockStyles: typing.Optional[typing.Dict[
                str, # Style tag
                typing.Tuple[
                    str, # Colour
                    str, # Style
                    float]]] # Width
            ) -> typing.Dict[
                str, # Style tag
                typing.Tuple[
                    str, # Colour
                    str, # Style
                    float]]: # Width
        mergedStyleMap: typing.Dict[str, typing.Tuple[str, str, float]] = {}

        if sectorStyles:
            for tag, (sectorColour, sectorStyle, sectorWidth) in sectorStyles.items():
                mergedStyleMap[tag] = (sectorColour, sectorStyle, sectorWidth)

        if stockStyles:
            for tag, (stockColour, stockStyle, stockWidth) in stockStyles.items():
                colour, style, width = mergedStyleMap.get(tag, (None, None, None))
                if colour is None:
                    colour = stockColour
                if style is None:
                    style = stockStyle
                if width is None:
                    width = stockWidth

                mergedStyleMap[tag] = (colour, style, width)

        # Update all tag mappings with default values
        if None in mergedStyleMap:
            defaultColour, defaultStyle, defaultWidth = mergedStyleMap.get(None)
            for tag in mergedStyleMap.keys():
                colour, style, width = mergedStyleMap[tag]
                if colour is None:
                    colour = defaultColour
                if style is None:
                    style = defaultStyle
                if width is None:
                    width = defaultWidth
                mergedStyleMap[tag] = (colour, style, width)

        return mergedStyleMap

    def _createBorderStyleMap(
            self,
            rawStyleSheet: survey.RawStyleSheet,
            loggingName: str
            ) -> typing.Dict[
                str, # Style tag
                typing.Tuple[
                    typing.Optional[str], # Colour
                    typing.Optional[str]]]: # Style
        defaultColour = defaultStyle = None
        for rawStyle in rawStyleSheet.borderStyles():
            tag = rawStyle.tag()
            if tag is not None:
                continue

            colour = rawStyle.colour()
            style = rawStyle.style()

            if colour is not None and not common.isValidHtmlColour(colour):
                logging.warning(f'Converter ignoring invalid colour {colour} for default border style from sector style sheet for {loggingName}')
                colour = None
            if style is not None:
                if style.lower() in _ValidLineStyles:
                    style = style.lower()
                else:
                    logging.warning(f'Converter ignoring invalid line style {style} for default border style from sector style sheet for {loggingName}')
                    style = None

            if colour is not None:
                defaultColour = colour
            if style is not None:
                defaultStyle = style

        styleMap = {}
        for rawStyle in rawStyleSheet.borderStyles():
            tag = rawStyle.tag()
            if tag is None:
                continue
            colour = rawStyle.colour()
            style = rawStyle.style()

            if colour is not None and not common.isValidHtmlColour(colour):
                logging.warning(f'Converter ignoring invalid colour {colour} for route style {tag} from sector style sheet for {loggingName}')
                colour = None
            if style is not None:
                if style.lower() in _ValidLineStyles:
                    style = style.lower()
                else:
                    logging.warning(f'Converter ignoring invalid line style {style} for route style {tag} from sector style sheet for {loggingName}')
                    style = None

            styleMap[tag] = (
                colour if colour is not None else defaultColour,
                style if style is not None else defaultStyle)

        return styleMap

    def _mergeBorderStyles(
            self,
            sectorStyles: typing.Optional[typing.Dict[
                str, # Style tag
                typing.Tuple[
                    str, # Colour
                    str]]], # Style
            stockStyles: typing.Optional[typing.Dict[
                str, # Style tag
                typing.Tuple[
                    str, # Colour
                    str ]]] # Style
            ) -> typing.Dict[
                str, # Style tag
                typing.Tuple[
                    str, # Colour
                    str]]: # Style
        mergedStyleMap: typing.Dict[str, typing.Tuple[str, str]] = {}

        if sectorStyles:
            for tag, (sectorColour, sectorStyle) in sectorStyles.items():
                mergedStyleMap[tag] = (sectorColour, sectorStyle)

        if stockStyles:
            for tag, (stockColour, stockStyle) in stockStyles.items():
                colour, style = mergedStyleMap.get(tag, (None, None))
                if colour is None:
                    colour = stockColour
                if style is None:
                    style = stockStyle

                mergedStyleMap[tag] = (colour, style)

        # Update all tag mappings with default values
        if None in mergedStyleMap:
            defaultColour, defaultStyle = mergedStyleMap.get(None)
            for tag in mergedStyleMap.keys():
                colour, style = mergedStyleMap[tag]
                if colour is None:
                    colour = defaultColour
                if style is None:
                    style = defaultStyle
                mergedStyleMap[tag] = (colour, style)

        return mergedStyleMap