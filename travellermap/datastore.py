import common
import datetime
import json
import logging
import os
import shutil
import threading
import travellermap
import typing
import urllib.error
import urllib.parse
import urllib.request

class SectorInfo(object):
    def __init__(
            self,
            canonicalName: typing.Iterable[str],
            alternateNames: typing.Optional[typing.Iterable[str]],
            abbreviation: typing.Optional[str],
            x: int,
            y: int,
            tags: typing.Optional[typing.Iterable[str]]
            ) -> None:
        self._canonicalName = canonicalName
        self._alternateNames = alternateNames
        self._abbreviation = abbreviation
        self._x = x
        self._y = y
        self._tags = tags

    def canonicalName(self) -> str:
        return self._canonicalName

    def alternateNames(self) -> typing.Optional[typing.Iterable[str]]:
        return self._alternateNames

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def tags(self) -> typing.Optional[typing.Iterable[str]]:
        return self._tags


class DataStore(object):
    _instance = None # Singleton instance
    _lock = threading.Lock()
    _installDir = None
    _overlayDir = None
    _userDir = None
    _milieuMap = None
    _downloader = common.Downloader()

    _milieuBaseDir = 'milieu'
    _universeFileName = 'universe.json'
    _sophontsFileName = 'sophonts.json'
    _allegiancesFileName = 'allegiances.json'
    _timestampFileName = 'timestamp.txt'
    _timestampFormat = '%Y-%m-%d %H:%M:%S.%f'

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
                    # Check the overlay age, the overlay directory will be deleted if it's older
                    # than the install directory
                    cls._instance._checkOverlayAge()
        return cls._instance

    @staticmethod
    def setSectorDirs(
            installDir: str,
            overlayDir: str,
            userDir: str
            ) -> None:
        if DataStore._instance:
            raise RuntimeError('You can\'t set the data store directories after the singleton has been initialised')
        DataStore._installDir = installDir
        DataStore._overlayDir = overlayDir
        DataStore._userDir = userDir

    def sectorCount(
            self,
            milieu: travellermap.Milieu
            ) -> int:
        self._loadSectors()
        return len(self._milieuMap[milieu])

    def sectors(
            self,
            milieu: travellermap.Milieu
            ) -> typing.Iterable[SectorInfo]:
        self._loadSectors()
        return self._milieuMap[milieu].values()

    def sectorFileData(
            self,
            name: str,
            milieu: travellermap.Milieu
            ) -> str:
        self._loadSectors()

        sectorMap = self._milieuMap[milieu]
        if name not in sectorMap:
            raise RuntimeError(f'Unknown sector "{name}"')
        sector: SectorInfo = sectorMap[name]
        escapedSectorName = common.encodeFileName(rawFileName=sector.canonicalName())
        return self._bytesToString(bytes=self._readMilieuFile(
            fileName=f'{escapedSectorName}.sec',
            milieu=milieu))

    def sophontsData(self) -> str:
        return self._bytesToString(bytes=self._readFile(
            relativeFilePath=self._sophontsFileName))

    def allegiancesData(self) -> str:
        return self._bytesToString(bytes=self._readFile(
            relativeFilePath=self._allegiancesFileName))

    def lastDownloadTime(self) -> datetime.datetime:
        try:
            timestampContent = self._readFile(relativeFilePath=self._timestampFileName)
        except Exception:
            return None

        return datetime.datetime.strptime(
            DataStore._bytesToString(timestampContent),
            DataStore._timestampFormat)

    def downloadData(
            self,
            travellerMapUrl: str,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> None:
        with self._lock:
            downloadTimestamp = datetime.datetime.utcnow().strftime(self._timestampFormat)

            workingDirPath = self._makeWorkingDir(
                baseDirPath=self._overlayDir,
                timestamp=downloadTimestamp)

            downloadQueue = []

            downloadQueue.append((
                f'{travellerMapUrl}/t5ss/sophonts',
                os.path.join(workingDirPath, self._sophontsFileName),
                None))

            downloadQueue.append((
                f'{travellerMapUrl}/t5ss/allegiances',
                os.path.join(workingDirPath, self._allegiancesFileName),
                None))

            for milieu in travellermap.Milieu:
                downloadQueue.append((
                    f'{travellerMapUrl}/api/universe?milieu={urllib.parse.quote(milieu.value)}&requireData=1',
                    os.path.join(*[workingDirPath, self._milieuBaseDir, milieu.value, self._universeFileName]),
                    milieu))

            downloadCount = 0
            while downloadQueue:
                if isCancelledCallback and isCancelledCallback():
                    return

                downloadInfo = downloadQueue.pop(0)

                url = downloadInfo[0]
                filePath = downloadInfo[1]
                milieu = downloadInfo[2]

                dirPath = os.path.dirname(filePath)
                if not os.path.exists(dirPath):
                    os.makedirs(dirPath)

                if progressCallback:
                    progressCallback(
                        os.path.relpath(filePath, workingDirPath),
                        downloadCount,
                        downloadCount + len(downloadQueue))

                self._downloader.downloadToFile(
                    url=url,
                    filePath=filePath,
                    isCancelledCallback=isCancelledCallback)
                if isCancelledCallback and isCancelledCallback():
                    return
                downloadCount += 1

                if milieu:
                    # If there was a milieu specified it means this is a universe file that was downloaded
                    # so we want to add the sectors
                    with open(filePath, 'rb') as file:
                        fileContent = file.read()
                    sectors = self._parseUniverseData(universeData=fileContent)
                    for sector in sectors:
                        escapedFileName = common.encodeFileName(rawFileName=sector.canonicalName()) + '.sec'
                        downloadQueue.append((
                            f'{travellerMapUrl}/api/sec?sector={urllib.parse.quote(sector.canonicalName())}&milieu={urllib.parse.quote(milieu.value)}&type=SecondSurvey',
                            os.path.join(dirPath, escapedFileName),
                            None))

            self._replaceDir(
                workingDirPath=workingDirPath,
                currentDirPath=self._overlayDir)

    def _loadSectors(self) -> None:
        if self._milieuMap:
            # Already loaded, nothing to do
            return

        with self._lock:
            if self._milieuMap:
                # Another thread loaded the sectors
                return

            self._milieuMap = {}
            for milieu in travellermap.Milieu:
                sectors = self._parseUniverseData(
                    universeData=self._readMilieuFile(
                        fileName=self._universeFileName,
                        milieu=milieu))
                sectorMap = {}
                for sector in sectors:
                    logging.debug(f'Initialising sector {sector.canonicalName()}')
                    sectorMap[sector.canonicalName()] = sector

                self._milieuMap[milieu] = sectorMap

    def _checkOverlayAge(self) -> None:
        if not os.path.exists(self._overlayDir):
            # If the overlay directory doesn't exist there is nothing to check
            return
        overlayTimestampPath = os.path.join(self._overlayDir, self._timestampFileName)
        if not os.path.exists(overlayTimestampPath):
            # Overlay timestamp file doesn't exist, err on th side of caution and don't do anything
            logging.warning(f'Overlay timestamp file "{overlayTimestampPath}" not found')
            return

        installTimestampPath = os.path.join(self._installDir, self._timestampFileName)
        if not os.path.exists(installTimestampPath):
            # Install timestamp file doesn't exist, err on th side of caution and don't do anything
            logging.warning(f'Install timestamp file "{installTimestampPath}" not found')
            return

        try:
            with open(overlayTimestampPath, 'rb') as file:
                overlayTimestamp = datetime.datetime.strptime(
                    DataStore._bytesToString(file.read()),
                    DataStore._timestampFormat)
        except Exception as ex:
            logging.error(
                f'Failed to load overlay timestamp from "{overlayTimestampPath}"',
                exc_info=ex)
            return

        try:
            with open(installTimestampPath, 'rb') as file:
                installTimestamp = datetime.datetime.strptime(
                    DataStore._bytesToString(file.read()),
                    DataStore._timestampFormat)
        except Exception as ex:
            logging.error(
                f'Failed to load install timestamp from "{installTimestampPath}"',
                exc_info=ex)
            return

        if installTimestamp <= overlayTimestamp:
            # The install copy of the sectors is older than the overlay copy so there is nothing to do
            return

        logging.info(f'Deleting out of date overlay directory "{self._overlayDir}"')
        try:
            shutil.rmtree(self._overlayDir)
        except Exception as ex:
            logging.error(
                f'Failed to delete out of date overlay directory "{self._overlayDir}"',
                exc_info=ex)

    def _readFile(
            self,
            relativeFilePath: str
            ) -> bytes:
        filePath = os.path.join(self._userDir, relativeFilePath)
        if not os.path.exists(filePath):
            filePath = os.path.join(self._overlayDir, relativeFilePath)
            if not os.path.exists(filePath):
                filePath = os.path.join(self._installDir, relativeFilePath)
                if not os.path.exists(filePath):
                    raise RuntimeError(f'Couldn\'t find "{relativeFilePath}"')

        with open(filePath, 'rb') as file:
            return file.read()

    def _readMilieuFile(
            self,
            fileName: str,
            milieu: travellermap.Milieu
            ) -> bytes:
        return self._readFile(
            relativeFilePath=os.path.join(os.path.join(self._milieuBaseDir, milieu.value), fileName))

    @staticmethod
    def _makeWorkingDir(
            baseDirPath: str,
            timestamp: datetime.datetime
            ) -> str:
        workingDir = baseDirPath + '_working'
        if os.path.exists(workingDir):
            shutil.rmtree(workingDir)
        os.makedirs(workingDir)

        timestampFilePath = os.path.join(workingDir, DataStore._timestampFileName)
        with open(timestampFilePath, 'wb') as file:
            file.write(str(timestamp).encode('ascii'))

        return workingDir

    @staticmethod
    def _replaceDir(
            workingDirPath,
            currentDirPath
            ) -> None:
        oldDirPath = None
        if os.path.exists(currentDirPath):
            oldDirPath = currentDirPath + '_old'
            if os.path.exists(oldDirPath):
                shutil.rmtree(oldDirPath)
            os.rename(currentDirPath, oldDirPath)

        try:
            os.rename(workingDirPath, currentDirPath)
        except Exception:
            if oldDirPath:
                os.rename(oldDirPath, currentDirPath)
            raise

    @staticmethod
    def _bytesToString(bytes: bytes) -> str:
        return bytes.decode('utf-8')

    @staticmethod
    def _parseUniverseData(
            universeData: bytes
            ) -> typing.List[SectorInfo]:
        universeJson = json.loads(DataStore._bytesToString(universeData))
        if 'Sectors' not in universeJson:
            raise RuntimeError('Invalid sector list')

        sectors = []
        for sectorInfo in universeJson['Sectors']:
            # Sectors can have multiple names. We have a single sector object that uses the first
            # name but multiple entries in the sector name map (but only a single entry in the
            # position map)
            sectorX = int(sectorInfo['X'])
            sectorY = int(sectorInfo['Y'])

            canonicalName = None
            alternateNames = None
            for element in sectorInfo['Names']:
                name = element['Text']
                if not canonicalName:
                    canonicalName = name
                else:
                    if not alternateNames:
                        alternateNames = []
                    alternateNames.append(name)
            assert(canonicalName)

            abbreviation = None
            if 'Abbreviation' in sectorInfo:
                abbreviation = sectorInfo['Abbreviation']

            tags = None
            if 'Tags' in sectorInfo:
                tags = sectorInfo['Tags'].split()

            sectors.append(SectorInfo(
                canonicalName=canonicalName,
                alternateNames=alternateNames,
                abbreviation=abbreviation,
                x=sectorX,
                y=sectorY,
                tags=tags))

        return sectors
