import logging
import threading
import travellermap
import typing

class AllegianceCodeInfo(object):
    def __init__(
            self,
            code: str,
            legacyCode: typing.Optional[str],
            basesCode: typing.Optional[str],
            globalName: typing.Optional[str]
            ) -> None:
        self._code = code
        self._legacyCode = legacyCode
        self._basesCode = basesCode
        self._globalName = globalName
        self._localNames: typing.Dict[str, str] = {}
        self._consistentName = True

    def code(self) -> str:
        return self._code

    def legacyCode(self) -> typing.Optional[str]:
        return self._legacyCode

    def basesCode(self) -> typing.Optional[str]:
        return self._basesCode

    def name(self, sectorName) -> typing.Optional[str]:
        localName = self._localNames.get(sectorName)
        if localName:
            return localName
        return self._globalName

    def uniqueCode(self, sectorName) -> str:
        if not self._consistentName and sectorName in self._localNames:
            return self._formatUniqueCode(sectorName)
        return self._code

    def globalName(self) -> typing.Optional[str]:
        return self._globalName

    def localNames(self) -> typing.Mapping[str, str]:
        return self._localNames

    def addLocalName(
            self,
            sectorName: str,
            allegianceName: str
            ) -> None:
        if self._globalName:
            if allegianceName.lower() == self._globalName.lower():
                # The local name is the same as the global name so just use the global name
                return

            # The local name differs from the global name so the allegiance doesn't have a
            # consistent name
            self._consistentName = False

        if self._consistentName and len(self._localNames) > 0:
            if allegianceName.lower() not in (name.lower() for name in self._localNames.values()):
                # This name is different to other local names so this allegiance no longer
                # has a consistent local name
                self._consistentName = False

        self._localNames[sectorName] = allegianceName

    def uniqueNameMap(self) -> typing.Mapping[str, str]:
        nameMap = {}
        if self._globalName:
            nameMap[self._code] = self._globalName

            if self._consistentName:
                # The allegiance has a consistent name so there is only one mapping, no need to
                # look at local mappings
                return nameMap

        for sectorName, allegianceName in self._localNames.items():
            if self._consistentName:
                # The allegiance has a local name so just create a single mapping using the base
                # code and this instance of the local name
                nameMap[self._code] = allegianceName
                break

            # This allegiance doesn't have a consistent name so map the sectors unique code to the
            # allegiance name
            nameMap[self._formatUniqueCode(sectorName)] = allegianceName

        return nameMap

    def _formatUniqueCode(
            self,
            sectorName: str
            ) -> str:
        return f'{self._code} ({sectorName})'

# NOTE: Mapping allegiance codes to names needs to be case sensitive as some sectors have
# allegiances that differ only by case (e.g. Knaeleng, Kharrthon, Phlange, Kruse)
class AllegianceManager(object):
    _T5OfficialAllegiancesPath = "t5ss/allegiance_codes.tab"

    # These unofficial allegiances are taken from Traveller Map. It has a
    # comment saying they're for M1120 but as far as I can tell it uses
    # them no mater which milieu you have selected. In my implementation
    # they are only used for M1120
    _T5UnofficialAllegiancesMap = {
        travellermap.Milieu.M1120: [
            # -----------------------
            # Unofficial/Unreviewed
            # -----------------------

            # M1120
            ( 'FdAr', 'Fa', None, 'Federation of Arden' ),
            ( 'BoWo', 'Bw', None, 'Border Worlds' ),
            ( 'LuIm', 'Li', 'Im', 'Lucan\'s Imperium' ),
            ( 'MaSt', 'Ma', 'Im', 'Maragaret\'s Domain' ),
            ( 'BaCl', 'Bc', None, 'Backman Cluster' ),
            ( 'FdDa', 'Fd', 'Im', 'Federation of Daibei' ),
            ( 'FdIl', 'Fi', 'Im', 'Federation of Ilelish' ),
            ( 'AvCn', 'Ac', None, 'Avalar Consulate' ),
            ( 'CoAl', 'Ca', None, 'Corsair Alliance' ),
            ( 'StIm', 'St', 'Im', 'Strephon\'s Worlds' ),
            ( 'ZiSi', 'Rv', 'Im', 'Restored Vilani Imperium' ), # Ziru Sirka
            ( 'VA16', 'V6', None, 'Assemblage of 1116' ),
            ( 'CRVi', 'CV', None, 'Vilani Cultural Region' ),
            ( 'CRGe', 'CG', None, 'Geonee Cultural Region' ),
            ( 'CRSu', 'CS', None, 'Suerrat Cultural Region' ),
            ( 'CRAk', 'CA', None, 'Anakudnu Cultural Region' )]}

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _milieuDataMap: typing.Dict[
        travellermap.Milieu,
        typing.Dict[
            str,
            AllegianceCodeInfo]]

    def __init__(self) -> None:
        raise RuntimeError('Call instance() instead')

    @classmethod
    def instance(cls):
        if not cls._instance:
            with cls._lock:
                # Recheck instance as another thread could have created it between the
                # first check adn the lock
                if not cls._instance:
                    cls._instance = cls.__new__(cls)
                    cls._instance._loadAllegiances()
        return cls._instance

    def allegiances(
            self,
            milieu: travellermap.Milieu
            ) -> typing.Iterable[AllegianceCodeInfo]:
        milieuData = self._milieuDataMap.get(milieu)
        if not milieuData:
            return []
        return milieuData.values()

    def allegianceName(
            self,
            milieu: travellermap.Milieu,
            code: str,
            sectorName: str
            ) -> typing.Optional[str]:
        if not code:
            return None

        milieuData = self._milieuDataMap.get(milieu)
        if not milieuData:
            return None

        codeInfo = milieuData.get(code)
        if not codeInfo:
            return None

        return codeInfo.name(sectorName)

    def legacyCode(
            self,
            milieu: travellermap.Milieu,
            code: str
            ) -> typing.Optional[str]:
        if not code:
            return None

        milieuData = self._milieuDataMap.get(milieu)
        if not milieuData:
            return None

        codeInfo = milieuData.get(code)
        if not codeInfo:
            return None

        return codeInfo.legacyCode()

    def basesCode(
            self,
            milieu: travellermap.Milieu,
            code: str
            ) -> typing.Optional[str]:
        if not code:
            return None

        milieuData = self._milieuDataMap.get(milieu)
        if not milieuData:
            return None

        codeInfo = milieuData.get(code)
        if not codeInfo:
            return None

        return codeInfo.basesCode()

    def uniqueAllegianceCode(
            self,
            milieu: travellermap.Milieu,
            code: str,
            sectorName: str
            ) -> typing.Optional[str]:
        if not code:
            return None

        milieuData = self._milieuDataMap.get(milieu)
        if not milieuData:
            return None

        codeInfo = milieuData.get(code)
        if not codeInfo:
            return None

        return codeInfo.uniqueCode(sectorName)

    def formatAllegianceString(
            self,
            milieu: travellermap.Milieu,
            code: str,
            sectorName: str
            ) -> str:
        if code:
            allegianceName = self.allegianceName(
                milieu=milieu,
                code=code,
                sectorName=sectorName)
            if allegianceName:
                allegianceString = f'{code} - {allegianceName}'
            else:
                allegianceString = f'{code} - Unknown'
        else:
            allegianceString = 'Unknown'
        return allegianceString

    def addSectorAllegiances(
            self,
            milieu: travellermap.Milieu,
            sectorName: str,
            allegiances: typing.Mapping[str, str]
            ) -> None:
        with self._lock:
            for code, name in allegiances.items():
                codeInfo = self._addAllegianceCode(milieu=milieu, code=code)
                codeInfo.addLocalName(sectorName=sectorName, allegianceName=name)

    # This function assumes it's only called once when the singleton is created and that
    # the mutex is locked
    def _loadAllegiances(self) -> None:
        self._milieuDataMap = {}
        for milieu in travellermap.Milieu:
            self._milieuDataMap[milieu] = {}

        # Load the T5 second survey allegiances pulled from Traveller Map
        _, results = travellermap.parseTabContent(
            content=travellermap.DataStore.instance().loadTextResource(
                filePath=AllegianceManager._T5OfficialAllegiancesPath))

        # Split results into global and local allegiances
        globalAllegiances = []
        localAllegiances = []
        for allegiance in results:
            location = allegiance.get('Location')
            if not location or location.lower() == 'various':
                globalAllegiances.append(allegiance)
            else:
                localAllegiances.append(allegiance)

        # First the entries with no location or location of 'various' are added as global names
        for allegiance in globalAllegiances:
            code = allegiance['Code']
            legacyCode = allegiance['Legacy']
            baseCode = allegiance['BaseCode']
            globalName = allegiance['Name']

            for milieu in travellermap.Milieu:
                self._addAllegianceCode(
                    milieu=milieu,
                    code=code,
                    legacyCode=legacyCode if legacyCode else None,
                    basesCode=baseCode if baseCode else None,
                    globalName=globalName if globalName else None)

        # Now entries where the locations specify sectors are added as names for those
        # sectors. The locations are specified using abbreviations so a per-milieu map
        # is generated for all abbreviations.
        abbreviationMap: typing.Dict[
            typing.Tuple[travellermap.Milieu, str], # Milieu & abbreviation
            str # Canonical name
            ] = {}
        for milieu in travellermap.Milieu:
            for sectorInfo in travellermap.DataStore.instance().sectors(milieu=milieu):
                abbreviation = sectorInfo.abbreviation()
                if not abbreviation:
                    continue
                abbreviationMap[(milieu, abbreviation)] = sectorInfo.canonicalName()

        for allegiance in localAllegiances:
            code = allegiance['Code']
            legacyCode = allegiance['Legacy']
            baseCode = allegiance['BaseCode']
            localName = allegiance['Name']
            location = allegiance['Location']

            abbreviations = location.split('/')

            for milieu in travellermap.Milieu:
                codeInfo = self._addAllegianceCode(
                    milieu=milieu,
                    code=code,
                    legacyCode=legacyCode if legacyCode else None,
                    basesCode=baseCode if baseCode else None)

                for abbreviation in abbreviations:
                    sectorName = abbreviationMap.get((milieu, abbreviation))
                    if not sectorName:
                        # Log this at debug as it occurs with the standard data
                        logging.debug(f'Unable to resolve Allegiance location abbreviation {abbreviation} to a sector')
                        continue

                    codeInfo.addLocalName(
                        sectorName=sectorName,
                        allegianceName=localName)

        # Now unofficial global entries
        for milieu in travellermap.Milieu:
            unofficialAllegiance = self._T5UnofficialAllegiancesMap.get(milieu)
            if unofficialAllegiance:
                for code, legacyCode, basesCode, globalName in unofficialAllegiance:
                    self._addAllegianceCode(
                        milieu=milieu,
                        code=code,
                        legacyCode=legacyCode if legacyCode else None,
                        basesCode=basesCode if baseCode else None,
                        globalName=globalName if globalName else None)

    def _addAllegianceCode(
            self,
            milieu: travellermap.Milieu,
            code: str,
            legacyCode: typing.Optional[str] = None,
            basesCode: typing.Optional[str] = None,
            globalName: typing.Optional[str] = None,
            ) -> AllegianceCodeInfo:
        milieuData = self._milieuDataMap.get(milieu)
        codeInfo = None
        if milieuData:
            codeInfo = milieuData.get(code)
        if not codeInfo:
            codeInfo = AllegianceCodeInfo(
                code=code,
                legacyCode=legacyCode,
                basesCode=basesCode,
                globalName=globalName)
            milieuData[code] = codeInfo
        return codeInfo
