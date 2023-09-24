import common
import datetime
import enum
import io
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
import zipfile

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
    class UpdateStage(enum.Enum):
        DownloadStage = 0,
        ExtractStage = 1

    _MilieuBaseDir = 'milieu'
    _UniverseFileName = 'universe.json'
    _SophontsFileName = 'sophonts.json'
    _AllegiancesFileName = 'allegiances.json'
    _TimestampFileName = 'timestamp.txt'
    _TimestampFormat = '%Y-%m-%d %H:%M:%S.%f'
    _DataArchiveUrl = 'https://github.com/cthulhustig/autojimmy-data/archive/refs/heads/main.zip'
    _DataArchiveMapPath = 'autojimmy-data-main/map/'
    _TimestampUrl = 'https://raw.githubusercontent.com/cthulhustig/autojimmy-data/main/map/timestamp.txt'
    _TimestampCheckTimeout = 3 # Seconds

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _installDir = None
    _overlayDir = None
    _userDir = None
    _milieuMap = None
    _downloader = common.Downloader()

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
            relativeFilePath=self._SophontsFileName))

    def allegiancesData(self) -> str:
        return self._bytesToString(bytes=self._readFile(
            relativeFilePath=self._AllegiancesFileName))

    def snapshotTimestamp(self) -> datetime.datetime:
        try:
            return DataStore._parseSnapshotTimestamp(
                data=self._readFile(relativeFilePath=self._TimestampFileName))
        except Exception:
            return None
    
    def checkForNewSnapshot(self) -> bool:
        currentTimestamp = self.snapshotTimestamp()
        try:
            response = urllib.request.urlopen(
                DataStore._TimestampUrl,
                timeout=DataStore._TimestampCheckTimeout)
            repoTimestamp = DataStore._parseSnapshotTimestamp(data=response.read())
        except Exception as ex:
            return False
        
        return (not currentTimestamp) or (repoTimestamp > currentTimestamp)
        
    def downloadSnapshot(
            self,
            progressCallback: typing.Optional[typing.Callable[[UpdateStage, int], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> None:
        with self._lock:
            logging.debug('Downloading universe data archive')
            if progressCallback:
                progressCallback(DataStore.UpdateStage.DownloadStage, 0)

            dataBuffer = io.BytesIO()
            with urllib.request.urlopen(DataStore._DataArchiveUrl) as response:
                length = response.getheader('content-length')
                blockSize = 1000000  # default value

                if length:
                    length = int(length)
                    blockSize = max(4096, length // 20)

                downloaded = 0
                while True:
                    if isCancelledCallback and isCancelledCallback():
                        return # Operation cancelled
                    chunk = response.read(blockSize)
                    if not chunk:
                        break
                    dataBuffer.write(chunk)
                    downloaded += len(chunk)
                    if length:
                        progressCallback(
                            DataStore.UpdateStage.DownloadStage,
                            int((downloaded / length) * 100))

            logging.debug('Extracting universe data archive')
            if progressCallback:
                progressCallback(DataStore.UpdateStage.ExtractStage, 0) 

            workingDirPath = self._makeWorkingDir(overlayDirPath=self._overlayDir)
            zipData = zipfile.ZipFile(dataBuffer)
            fileInfoList = zipData.infolist()
            extractIndex = 0
            for fileInfo in fileInfoList:
                if isCancelledCallback and isCancelledCallback():
                    return # Operation cancelled
                
                extractIndex += 1
                if progressCallback:
                    progressCallback(
                        DataStore.UpdateStage.ExtractStage,
                        int((extractIndex / len(fileInfoList)) * 100))
                                    
                if fileInfo.is_dir():
                    continue # Skip directories
                if not fileInfo.filename.startswith(DataStore._DataArchiveMapPath):
                    continue # Skip files not in the map directory

                subPath = fileInfo.filename[len(DataStore._DataArchiveMapPath):]
                targetPath = os.path.join(workingDirPath, subPath)

                logging.debug(f'Extracting {subPath}')
                directoryHierarchy = os.path.dirname(targetPath)
                if not os.path.exists(directoryHierarchy):
                    os.makedirs(directoryHierarchy, exist_ok=True)
                with open(targetPath, 'wb') as outputFile:
                    outputFile.write(zipData.read(fileInfo.filename))

            logging.debug('Replacing old universe data')
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
                        fileName=self._UniverseFileName,
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
        overlayTimestampPath = os.path.join(self._overlayDir, self._TimestampFileName)
        if not os.path.exists(overlayTimestampPath):
            # Overlay timestamp file doesn't exist, err on th side of caution and don't do anything
            logging.warning(f'Overlay timestamp file "{overlayTimestampPath}" not found')
            return

        installTimestampPath = os.path.join(self._installDir, self._TimestampFileName)
        if not os.path.exists(installTimestampPath):
            # Install timestamp file doesn't exist, err on th side of caution and don't do anything
            logging.warning(f'Install timestamp file "{installTimestampPath}" not found')
            return

        try:
            with open(overlayTimestampPath, 'rb') as file:
                overlayTimestamp = DataStore._parseSnapshotTimestamp(data=file.read())
        except Exception as ex:
            logging.error(
                f'Failed to load overlay timestamp from "{overlayTimestampPath}"',
                exc_info=ex)
            return

        try:
            with open(installTimestampPath, 'rb') as file:
                installTimestamp = DataStore._parseSnapshotTimestamp(data=file.read())
        except Exception as ex:
            logging.error(
                f'Failed to load install timestamp from "{installTimestampPath}"',
                exc_info=ex)
            return

        if installTimestamp <= overlayTimestamp:
            # The install copy of the sectors is older than the overlay copy so there is nothing to do
            return

        logging.debug(f'Deleting out of date overlay directory "{self._overlayDir}"')
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
        # If a FILE exists in the user dir use it over anything else. If it doesn't, read it
        # from the overlay if that DIRECTORY exists, if not read it from the install directory
        filePath = os.path.join(self._userDir, relativeFilePath)
        if not os.path.exists(filePath):
            filePath = os.path.join(
                self._overlayDir if os.path.isdir(self._overlayDir) else self._installDir,
                relativeFilePath)

        with open(filePath, 'rb') as file:
            return file.read()

    def _readMilieuFile(
            self,
            fileName: str,
            milieu: travellermap.Milieu
            ) -> bytes:
        return self._readFile(
            relativeFilePath=os.path.join(os.path.join(self._MilieuBaseDir, milieu.value), fileName))

    @staticmethod
    def _makeWorkingDir(overlayDirPath: str) -> str:
        workingDir = overlayDirPath + '_working'
        if os.path.exists(workingDir):
            # Delete any previous working directory that may have been left kicking about
            shutil.rmtree(workingDir)
        os.makedirs(workingDir)
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
    def _parseSnapshotTimestamp(data: bytes) -> datetime.datetime:
        return datetime.datetime.strptime(
            DataStore._bytesToString(data),
            DataStore._TimestampFormat)    

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
