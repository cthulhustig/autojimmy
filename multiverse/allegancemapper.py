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

        self._stockBorderStyleData: typing.Dict[
            str, # Style tag
            typing.Tuple[
                typing.Optional[str], # Colour
                typing.Optional[str]] # Style
            ] = {}
        self._metadataToBorderStyleData: typing.Dict[
            survey.RawMetadata,
            typing.Dict[
                str, # Style tag
                typing.Tuple[
                    typing.Optional[str], # Colour
                    typing.Optional[str]] # Style
            ]] = {}

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
            rawMetadata: survey.RawMetadata,
            code: str
            ) -> typing.Optional[multiverse.DbAllegiance]:
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
            location = rawAllegiance.location()

            if location is None or location == 'various':
                # Create a global allegiance
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

                dbAllegiances = metadataToDbAllegiances.get(None)
                if dbAllegiances is None:
                    dbAllegiances = []
                    metadataToDbAllegiances[None] = dbAllegiances
                dbAllegiances.append(dbAllegiance)
                seenCodes.add(rawMetadata=None, code=dbAllegiance.code())
            else:
                # Create a sector allegiance for each location
                for sectorAbbreviation in location.split('/'):
                    rawMetadata = sectorAbbreviationToMetadata.get(sectorAbbreviation)
                    if rawMetadata is None:
                        logging.info(f'Ignoring unknown sector abbreviation {sectorAbbreviation!r} for stock abbreviation {rawAllegiance.name()!r}')
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

        globalDbAllegiances = metadataToDbAllegiances.get(None)
        if globalDbAllegiances:
            codeMap = self._metadataToCodeMap.get(None)
            if codeMap is None:
                codeMap = {}
                self._metadataToCodeMap[None] = codeMap

            for dbAllegiance in globalDbAllegiances:
                self._nameToDbAllegiance[dbAllegiance.name()] = dbAllegiance
                codeMap[dbAllegiance.code()] = dbAllegiance

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
                code = dbAllegiance.code()
                code = _LegacyAllegianceToT5Overrides.get(code, code)

                if consistentCode is not None and code != consistentCode:
                    consistentCode = None
                    break
                consistentCode = code

            if consistentCode is None:
                # The sectors aren't using a completely consistent code for the allegiance
                # but check for the case where the only other code they're using is the
                # legacy code of the allegiance.
                legacyCodes = set()
                for dbAllegiance, _ in allegianceData:
                    legacy = dbAllegiance.legacy()
                    if legacy is not None:
                        legacyCodes.add(legacy)
                if legacyCodes:
                    for dbAllegiance, _ in allegianceData:
                        code = dbAllegiance.code()
                        if code in legacyCodes:
                            continue

                        if consistentCode is not None and code != consistentCode:
                            consistentCode = None
                            break
                        consistentCode = code

            dbAllegianceForName = self._nameToDbAllegiance.get(name)
            if dbAllegianceForName is not None:
                # There is a global allegiance with this name so use it as the final allegiance.
                # This will use style information for the global allegiance, any sector specific
                # styling for this name will need to be handled as a per-sector override

                # Create mappings for this sector that map the code used by the sector for the
                # allegiance and (if there is one) the "consistent" code to the DbAllegiance for
                # this allegiance name. Even if the code is "consistent", the sector may use a
                # different one as the sector may use the legacy code or have had its code
                # overridden
                for dbAllegiance, rawMetadata in allegianceData:
                    codeMap = self._metadataToCodeMap.get(rawMetadata)
                    if codeMap is None:
                        codeMap = {}
                        self._metadataToCodeMap[rawMetadata] = codeMap
                    codeMap[dbAllegiance.code()] = dbAllegianceForName
                    if consistentCode is not None:
                        codeMap[consistentCode] = dbAllegianceForName
            else:
                # There is no global allegiance with this name so create as many as are
                # required for the sectors that reference the same name. The sector style
                # data will be used if it's consistent across all sectors that use this
                # allegiance. If they're not consistent then styling for this allegiance
                # will need to be handled as a per-sector override

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
                    # The sectors all use a consistent code for this name so create a single
                    # allegiance to be used by them all. For the legacy/base codes we just
                    # find the first non-null for each and use it
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

                    # Create mappings for this sector that map the code used by the sector for the
                    # allegiance and the "consistent" code to the DbAllegiance for this allegiance
                    # name. Even though code is "consistent", the sector may use a different one as
                    # the sector may use the legacy code or have had its code overridden
                    for dbAllegiance, rawMetadata in allegianceData:
                        codeMap = self._metadataToCodeMap.get(rawMetadata)
                        if codeMap is None:
                            codeMap = {}
                            self._metadataToCodeMap[rawMetadata] = codeMap
                        codeMap[dbAllegiance.code()] = dbAllegianceForName
                        codeMap[consistentCode] = dbAllegianceForName
                else:
                    # The sectors are not consistent in the codes they use for this allegiance
                    # name so we can't really be sure that they are the same allegiance (e.g.
                    # VOpA and  VOpp in allegiance_codes.tab). Disambiguate them by creating
                    # allegiances with the code appended on the name
                    for dbAllegiance, rawMetadata in allegianceData:
                        code = dbAllegiance.code()
                        code = _LegacyAllegianceToT5Overrides.get(code, code)

                        name = f'{dbAllegiance.name()} ({code})'
                        dbAllegianceForName = self._nameToDbAllegiance.get(name)
                        if dbAllegianceForName is None:
                            dbAllegianceForName = multiverse.DbAllegiance(
                                name=name,
                                code=code,
                                legacy=dbAllegiance.legacy(),
                                base=dbAllegiance.base(),
                                routeColour=consistentRouteColour,
                                routeStyle=consistentRouteStyle,
                                routeWidth=consistentRouteWidth,
                                borderColour=consistentBorderColour,
                                borderStyle=consistentBorderStyle)
                            self._nameToDbAllegiance[name] = dbAllegianceForName

                        # Create mappings for this sector that map the code used by the sector
                        # for the allegiance and its actual code to the DbAllegiance for this
                        # allegiance name. These codes may be different as the sector may have
                        # had its code overridden
                        codeMap = self._metadataToCodeMap.get(rawMetadata)
                        if codeMap is None:
                            codeMap = {}
                            self._metadataToCodeMap[rawMetadata] = codeMap
                        codeMap[dbAllegiance.code()] = dbAllegianceForName
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
