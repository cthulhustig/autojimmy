import json
import logging
import threading
import traveller
import travellermap
import typing

class AllegianceCodeInfo(object):
    def __init__(
            self,
            code: str,
            globalName: typing.Optional[str]
            ) -> None:
        self._code = code
        self._globalName = globalName
        self._localNames = {}
        self._consistentName = True

    def code(self) -> str:
        return self._code

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
                # This name is different to other local names so this allegiance is no longer
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

class AllegianceManager(object):
    _instance = None # Singleton instance
    _allegianceMap: typing.Dict[str, AllegianceCodeInfo] = {}
    _lock = threading.Lock()
    _milieu = travellermap.Milieu.M1105 # Same default as Traveller Map

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
                    cls._instance._loadGlobalAllegiances()
        return cls._instance

    @staticmethod
    def setMilieu(milieu: travellermap.Milieu) -> None:
        if AllegianceManager._instance:
            raise RuntimeError('You can\'t set the milieu after the singleton has been initialised')
        AllegianceManager._milieu = milieu

    def allegiances(self) -> typing.Iterable[AllegianceCodeInfo]:
        return self._allegianceMap.values()

    def allegianceName(self, world: traveller.World) -> typing.Optional[str]:
        code = world.allegiance()
        if not code:
            return None

        codeInfo = self._allegianceMap.get(code)
        if not codeInfo:
            return None

        return codeInfo.name(world.sectorName())

    def uniqueAllegianceCode(self, world: traveller.World) -> typing.Optional[str]:
        code = world.allegiance()
        if not code:
            return None

        codeInfo = self._allegianceMap.get(code)
        if not codeInfo:
            return None

        return codeInfo.uniqueCode(world.sectorName())

    def formatAllegianceString(self, world: traveller.World) -> str:
        allegianceCode = world.allegiance()
        if allegianceCode:
            allegianceName = traveller.AllegianceManager.instance().allegianceName(world)
            if allegianceName:
                allegianceString = f'{allegianceCode} - {allegianceName}'
            else:
                allegianceString = f'{allegianceCode} - Unknown'
        else:
            allegianceString = 'Unknown'
        return allegianceString

    def addSectorAllegiances(
            self,
            sectorName: str,
            allegiances: typing.Mapping[str, str]
            ) -> None:
        with self._lock:
            for code, name in allegiances.items():
                codeInfo = self._allegianceMap.get(code)
                if not codeInfo:
                    codeInfo = self._addAllegianceCode(
                        code=code,
                        globalName=None) # Codes added from sectors don't have global names
                codeInfo.addLocalName(sectorName=sectorName, allegianceName=name)

    # This function assumes it's only called once when the singleton is created and that
    # the mutex is locked
    def _loadGlobalAllegiances(self) -> None:
        # Pre-load mapping with legacy allegiances. This is done so to control which
        # name ends up being used as the data retrieved from Traveller Map has multiple
        # allegiances (with different names) mapped to the same legacy code
        self._addAllegianceCode(code='Im', globalName='Third Imperium')
        self._addAllegianceCode(code='Dr', globalName='Droyne')
        self._addAllegianceCode(code='Na', globalName='Non-Aligned, Human-dominated')
        self._addAllegianceCode(code='Zh', globalName='Zhodani Consulate')
        self._addAllegianceCode(code='Va', globalName='Non-Aligned, Vargr-dominated')
        self._addAllegianceCode(code='So', globalName='Solomani Confederation')
        self._addAllegianceCode(code='Zc', globalName='Zhodani Client')
        self._addAllegianceCode(code='As', globalName='Aslan Hierate')
        self._addAllegianceCode(code='Kk', globalName='The Two Thousand Worlds')

        # Load the T5 second survey allegiances pulled from Traveller Map
        results = json.loads(travellermap.DataStore.instance().allegiancesData())

        # Split results into global and local allegiances
        globalAllegiances = []
        localAllegiances = []
        for allegiance in results:
            location = allegiance.get('Location')
            if not location or location.lower() == 'various':
                globalAllegiances.append(allegiance)
            else:
                localAllegiances.append(allegiance)

        # Generate a mapping of sector abbreviations to sector names
        abbreviationMap = {}
        for sectorInfo in travellermap.DataStore.instance().sectors(milieu=self._milieu):
            abbreviation = sectorInfo.abbreviation()
            if not abbreviation:
                continue
            abbreviationMap[abbreviation] = sectorInfo.canonicalName()

        # First the entries with no location or location of 'various' are added as global names
        for allegiance in globalAllegiances:
            code = allegiance['Code']
            legacyCode = allegiance['LegacyCode']
            name = allegiance['Name']

            self._addAllegianceCode(code=code, globalName=name)
            self._addAllegianceCode(code=legacyCode, globalName=name)

        # Now entries where the locations specify sectors are added as names for those
        # sectors
        for allegiance in localAllegiances:
            code = allegiance['Code']
            legacyCode = allegiance['LegacyCode']
            name = allegiance['Name']
            location = allegiance['Location']

            codeInfo = self._addAllegianceCode(
                code=code,
                globalName=None)
            legacyCodeInfo = self._addAllegianceCode(
                code=legacyCode,
                globalName=None)

            abbreviations = location.split('/')
            for abbreviation in abbreviations:
                sectorName = abbreviationMap.get(abbreviation)
                if not sectorName:
                    # Log this at debug as it occurs with the standard data
                    logging.debug(f'Unable to resolve Allegiance location abbreviation {abbreviation} to a sector')
                    continue

                codeInfo.addLocalName(
                    sectorName=sectorName,
                    allegianceName=name)
                legacyCodeInfo.addLocalName(
                    sectorName=sectorName,
                    allegianceName=name)

    def _addAllegianceCode(
            self,
            code: str,
            globalName: typing.Optional[str],
            ) -> AllegianceCodeInfo:
        codeInfo = self._allegianceMap.get(code)
        if not codeInfo:
            codeInfo = AllegianceCodeInfo(code=code, globalName=globalName)
            self._allegianceMap[code] = codeInfo
        return codeInfo
