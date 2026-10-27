import common
import logging
import multiverse
import survey
import typing

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

class AllegianceMapper(object):
    class _CodeTracker(object):
        def __init__(self):
            self._metadataToCodes: typing.Dict[
                typing.Optional[survey.RawMetadata],
                typing.Set[str]
            ] = {}

        def add(self, rawMetadata: typing.Optional[survey.RawMetadata], code: str) -> None:
            codes = self._metadataToCodes.get(rawMetadata)
            if codes is None:
                codes = set()
                self._metadataToCodes[rawMetadata] = codes
            codes.add(code)

        def contains(self, rawMetadata: survey.RawMetadata, code: str) -> bool:
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
            styleMapper: multiverse.StyleMapper
            ) -> None:
        self._styleMapper = styleMapper

        self._idToDbAllegiance: typing.Dict[
            str, # Allegiance Id
            multiverse.DbAllegiance
            ] = {}
        self._nameToDbAllegiance: typing.Dict[
            str, # Allegiance Name
            multiverse.DbAllegiance
            ] = {}
        self._metadataToCodeMap: typing.Dict[
            typing.Optional[survey.RawMetadata], # None = global
            typing.Dict[
                str, # Allegiance Code
                multiverse.DbAllegiance
            ]] = {}

        self._populate(
            milieu=milieu,
            rawSectors=rawSectors,
            rawStockAllegiances=rawStockAllegiances)

    def lookupAllegiance(
            self,
            code: str,
            rawMetadata: typing.Optional[survey.RawMetadata] = None
            ) -> typing.Optional[multiverse.DbAllegiance]:
        code = _LegacyAllegianceToT5Overrides.get(code, code)

        if rawMetadata is not None:
            # First check if there is a sector specific allegiance for this code
            codeMap = self._metadataToCodeMap.get(rawMetadata)
            if codeMap is not None:
                dbAllegiance = codeMap.get(code)
                if dbAllegiance is not None:
                    return dbAllegiance

        # No sector specific allegiance so check if there is a global one
        codeMap = self._metadataToCodeMap.get(None)
        if codeMap is not None:
            dbAllegiance = codeMap.get(code)
            if dbAllegiance is not None:
                return dbAllegiance

        return None # No allegiance for this code

    def allegianceById(self, id: str) -> typing.Optional[multiverse.DbAllegiance]:
        return self._idToDbAllegiance.get(id)

    def listAllegiances(self) -> typing.List[multiverse.DbAllegiance]:
        return list(self._nameToDbAllegiance.values())

    def _populate(
            self,
            milieu: str,
            rawSectors: typing.List[typing.Tuple[survey.RawMetadata, typing.List[survey.RawWorld]]],
            rawStockAllegiances: typing.List[survey.RawStockAllegiance]
            ) -> None:
        metadataToDbAllegiances = self._createDbAllegiances(
            milieu=milieu,
            rawSectors=rawSectors,
            rawStockAllegiances=rawStockAllegiances)

        self._processDbAllegiances(
            metadataToDbAllegiances=metadataToDbAllegiances)

    def _selectRawStockAllegiances(
            self,
            milieu: str,
            rawStockAllegiances: typing.Collection[survey.RawStockAllegiance]
            ) -> typing.List[survey.RawStockAllegiance]:
        rawAllegiances = list(rawStockAllegiances)
        rawAllegiances.extend(_LegacyAllegiances)

        rawMilieuAllegiances = _T5UnofficialAllegiancesMap.get(milieu)
        if rawMilieuAllegiances:
            rawAllegiances.extend(rawMilieuAllegiances)

        return rawAllegiances

    def _createDbAllegiances(
            self,
            milieu: str,
            rawSectors: typing.List[typing.Tuple[survey.RawMetadata, typing.List[survey.RawWorld]]],
            rawStockAllegiances: typing.List[survey.RawStockAllegiance]
            ) -> typing.Dict[
                typing.Optional[survey.RawMetadata], # None = global
                typing.List[multiverse.DbAllegiance]]:
        rawStockAllegiances = self._selectRawStockAllegiances(
            milieu=milieu,
            rawStockAllegiances=rawStockAllegiances)

        sectorAbbreviationToMetadata = {m.abbreviation(): m for m, _ in rawSectors if m.abbreviation() is not None}

        metadataToDbAllegiances: typing.Dict[
            typing.Optional[survey.RawMetadata],
            typing.List[multiverse.DbAllegiance]
            ] = {}
        seenCodes = self._CodeTracker()

        for rawAllegiance in rawStockAllegiances:
            code = rawAllegiance.code()

            # Always create a global allegiance, even if a location is specified. This
            # is consistent with Traveller Map which also ignores them. This is
            # important as the sectors specified in location strings isn't always an
            # exhaustive list, for example Julian Protectorate is used in way more than
            # the 3 sectors listed in the location. I think what _might_ be going on is
            # the location only specifies official sectors (i.e. the ones not shaded when
            # the overlay is selected)
            routeColour, routeStyle, routeWidth = self._styleMapper.lookupRouteStyle(
                rawMetadata=None,
                tag=code)
            borderColour, borderStyle = self._styleMapper.lookupBorderStyle(
                rawMetadata=None,
                tag=code)
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

            dbAllegiances = metadataToDbAllegiances.get(None)
            if dbAllegiances is None:
                dbAllegiances = []
                metadataToDbAllegiances[None] = dbAllegiances
            dbAllegiances.append(dbAllegiance)
            seenCodes.add(rawMetadata=None, code=dbAllegiance.code())

            # Create an allegiance for each location. This needs done as the
            # style may be different from the global one.
            location = rawAllegiance.location()
            if location and location != 'various':
                for sectorAbbreviation in location.split('/'):
                    rawMetadata = sectorAbbreviationToMetadata.get(sectorAbbreviation)
                    if rawMetadata is None:
                        # NOTE: Only write this at debug as the file uses M1105 sector abbreviations so this
                        # will happen a lot for non-M1105 milieu
                        logging.debug(f'Ignoring unknown sector abbreviation {sectorAbbreviation!r} for stock abbreviation {rawAllegiance.name()!r}')
                        continue

                    routeColour, routeStyle, routeWidth = self._styleMapper.lookupRouteStyle(
                        rawMetadata=rawMetadata,
                        tag=code)
                    borderColour, borderStyle = self._styleMapper.lookupBorderStyle(
                        rawMetadata=rawMetadata,
                        tag=code)

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

                    dbAllegiances = metadataToDbAllegiances.get(rawMetadata)
                    if dbAllegiances is None:
                        dbAllegiances = []
                        metadataToDbAllegiances[rawMetadata] = dbAllegiances
                    dbAllegiances.append(dbAllegiance)
                    seenCodes.add(rawMetadata=rawMetadata, code=dbAllegiance.code())

        # Create allegiances defined in sector metadata
        for rawMetadata, _ in rawSectors:
            rawAllegiances = rawMetadata.allegiances()
            if rawAllegiances is None:
                continue

            for rawAllegiance in rawAllegiances:
                code = rawAllegiance.code()
                routeColour, routeStyle, routeWidth = self._styleMapper.lookupRouteStyle(
                    rawMetadata=rawMetadata,
                    tag=code)
                borderColour, borderStyle = self._styleMapper.lookupBorderStyle(
                    rawMetadata=rawMetadata,
                    tag=code)

                dbAllegiance = multiverse.DbAllegiance(
                    name=rawAllegiance.name(),
                    code=code,
                    base=rawAllegiance.base(),
                    routeColour=routeColour,
                    routeStyle=routeStyle,
                    routeWidth=routeWidth,
                    borderColour=borderColour,
                    borderStyle=borderStyle)

                dbAllegiances = metadataToDbAllegiances.get(rawMetadata)
                if dbAllegiances is None:
                    dbAllegiances = []
                    metadataToDbAllegiances[rawMetadata] = dbAllegiances
                dbAllegiances.append(dbAllegiance)
                seenCodes.add(rawMetadata=rawMetadata, code=dbAllegiance.code())

        # Crete allegiances that are referenced but not defined
        for rawMetadata, rawWorlds in rawSectors:
            usedCodes = self._collectUsedCodes(rawMetadata=rawMetadata, rawWorlds=rawWorlds)

            for code in usedCodes:
                if seenCodes.contains(code=code, rawMetadata=rawMetadata):
                    continue # Not missing

                routeColour, routeStyle, routeWidth = self._styleMapper.lookupRouteStyle(
                    rawMetadata=rawMetadata,
                    tag=code)
                borderColour, borderStyle = self._styleMapper.lookupBorderStyle(
                    rawMetadata=rawMetadata,
                    tag=code)

                # There is no mapping for this code so create one with the code as the name
                dbAllegiance = multiverse.DbAllegiance(
                    name=code,
                    code=code,
                    routeColour=routeColour,
                    routeStyle=routeStyle,
                    routeWidth=routeWidth,
                    borderColour=borderColour,
                    borderStyle=borderStyle)

                dbAllegiances = metadataToDbAllegiances.get(rawMetadata)
                if dbAllegiances is None:
                    dbAllegiances = []
                    metadataToDbAllegiances[rawMetadata] = dbAllegiances
                dbAllegiances.append(dbAllegiance)

        return metadataToDbAllegiances

    def _processDbAllegiances(
            self,
            metadataToDbAllegiances: typing.Mapping[
                typing.Optional[survey.RawMetadata], # None = global
                typing.List[multiverse.DbAllegiance]]
            ) -> None:
        nameToAllegianceData: typing.Dict[
            str, # Allegiance Name
            typing.List[typing.Tuple[
                multiverse.DbAllegiance,
                survey.RawMetadata]]] = {}
        for rawMetadata, dbAllegiances in metadataToDbAllegiances.items():
            for dbAllegiance in dbAllegiances:
                name = dbAllegiance.name()
                allegianceData = nameToAllegianceData.get(name)
                if allegianceData is None:
                    allegianceData = []
                    nameToAllegianceData[name] = allegianceData
                allegianceData.append((dbAllegiance, rawMetadata))

        nameToStyleData: typing.Dict[
            str,
            typing.Tuple[
                typing.Optional[str], # Route colour
                typing.Optional[str], # Route style
                typing.Optional[float], # Route width
                typing.Optional[str], # Border colour
                typing.Optional[str]] # Border style
            ] = {}
        for name, allegianceData in nameToAllegianceData.items():
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

            nameToStyleData[name] = (consistentRouteColour, consistentRouteStyle, consistentRouteWidth,
                                     consistentBorderColour, consistentBorderStyle)

        # Add global allegiances to the name map first so the legacy/base codes
        # for them will be used in preference to any defined in sectors
        globalDbAllegiances = metadataToDbAllegiances.get(None)
        if globalDbAllegiances:
            codeMap = self._metadataToCodeMap.get(None)
            if codeMap is None:
                codeMap = {}
                self._metadataToCodeMap[None] = codeMap

            for dbAllegiance in globalDbAllegiances:
                code = dbAllegiance.code()
                code = _LegacyAllegianceToT5Overrides.get(code, code)

                routeColour, routeStyle, routeWidth, borderColour, borderStyle = \
                    nameToStyleData.get(dbAllegiance.name(), (None, None, None, None, None))

                dbAllegiance = multiverse.DbAllegiance(
                    code=code,
                    name=dbAllegiance.name(),
                    legacy=dbAllegiance.legacy(),
                    base=dbAllegiance.base(),
                    routeColour=routeColour,
                    routeStyle=routeStyle,
                    routeWidth=routeWidth,
                    borderColour=borderColour,
                    borderStyle=borderStyle)

                self._idToDbAllegiance[dbAllegiance.id()] = dbAllegiance
                self._nameToDbAllegiance[dbAllegiance.name()] = dbAllegiance
                codeMap[dbAllegiance.code()] = dbAllegiance

        for name, allegianceData in nameToAllegianceData.items():
            dbAllegianceForName = self._nameToDbAllegiance.get(name)
            if dbAllegianceForName is None:
                routeColour, routeStyle, routeWidth, borderColour, borderStyle = \
                    nameToStyleData.get(dbAllegiance.name(), (None, None, None, None, None))

                # Determine which code to use for the allegiance
                # 1. If there is just one code then use that
                # 2. If there is one consistent 4 character second survey code and the other
                #    codes are legacy 2 character codes (or something else), use the second
                #    survey code
                # 3. Use the most commonly used code
                # 4. In the case of a tie, just use the first one with the highest usage count
                usageCounts = common.InstanceCounter()
                for dbAllegiance, _ in allegianceData:
                    code = dbAllegiance.code()
                    code = _LegacyAllegianceToT5Overrides.get(code, code)
                    usageCounts.add(code)

                code = next(iter(usageCounts))
                if len(usageCounts) > 1:
                    secondSurveyCode = None
                    for usedCode in usageCounts:
                        if len(usedCode) != 4:
                            continue

                        if secondSurveyCode is not None and usedCode != secondSurveyCode:
                            secondSurveyCode = None
                            break
                        secondSurveyCode = usedCode

                    if secondSurveyCode is not None:
                        code = secondSurveyCode
                    else:
                        mostUsedCode = None
                        for usedCode in usageCounts:
                            if mostUsedCode is None or usageCounts[usedCode] > usageCounts[mostUsedCode]:
                                mostUsedCode = usedCode
                        if mostUsedCode is not None:
                            code = mostUsedCode

                # For the legacy and base codes, just use the first one
                legacy = base = None
                for dbAllegiance, _ in allegianceData:
                    if legacy is None:
                        legacy = dbAllegiance.legacy()
                    if base is None:
                        base = dbAllegiance.base()

                dbAllegianceForName = multiverse.DbAllegiance(
                    name=name,
                    code=code,
                    legacy=legacy,
                    base=base,
                    routeColour=routeColour,
                    routeStyle=routeStyle,
                    routeWidth=routeWidth,
                    borderColour=borderColour,
                    borderStyle=borderStyle)
                self._idToDbAllegiance[dbAllegianceForName.id()] = dbAllegianceForName
                self._nameToDbAllegiance[dbAllegianceForName.name()] = dbAllegianceForName

            for dbAllegiance, rawMetadata in allegianceData:
                # Create mappings for this sector that map the code used by the sector
                # for the allegiance and its actual code to the DbAllegiance for this
                # allegiance name. These codes may be different as the sector may have
                # had its code overridden though a local allegiance definition
                code = dbAllegiance.code()
                code = _LegacyAllegianceToT5Overrides.get(code, code)

                codeMap = self._metadataToCodeMap.get(rawMetadata)
                if codeMap is None:
                    codeMap = {}
                    self._metadataToCodeMap[rawMetadata] = codeMap
                codeMap[code] = dbAllegianceForName

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
