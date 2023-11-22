import common
import datetime
import enum
import io
import json
import logging
import os
import re
import shutil
import threading
import travellermap
import typing
import urllib.error
import urllib.parse
import urllib.request
import xmlschema
import xml.etree.ElementTree
import zipfile

class UniverseDataFormat(object):
    def __init__(self, major: int, minor: int) -> None:
        self._major = major
        self._minor = minor

    def major(self) -> int:
        return self._major

    def minor(self) -> int:
        return self._minor

    def __str__(self) -> str:
        return f'{self._major}.{self._minor}'

    def __eq__(self, other: 'UniverseDataFormat') -> bool:
        if self.__class__ is other.__class__:
            return (self._major == other._major) and (self._minor == other._minor)
        return False

    def __lt__(self, other: 'UniverseDataFormat') -> bool:
        if self.__class__ is other.__class__:
            if self._major < other._major:
                return True
            if self._major > other._major:
                return False
            return self._minor < other._minor
        return NotImplemented

    def __le__(self, other: 'UniverseDataFormat') -> bool:
        if self.__class__ is other.__class__:
            if self._major < other._major:
                return True
            if self._major > other._major:
                return False
            return self._minor <= other._minor
        return NotImplemented

    def __gt__(self, other: 'UniverseDataFormat') -> bool:
        if self.__class__ is other.__class__:
            if self._major > other._major:
                return True
            if self._major < other._major:
                return False
            return self._minor > other._minor
        return NotImplemented

    def __ge__(self, other: 'UniverseDataFormat') -> bool:
        if self.__class__ is other.__class__:
            if self._major > other._major:
                return True
            if self._major < other._major:
                return False
            return self._minor >= other._minor
        return NotImplemented


class CustomMapLevel(object):
    def __init__(
            self,
            scale: int,
            fileName: str,
            format: travellermap.MapFormat
            ) -> None:
        self._scale = scale
        self._fileName = fileName
        self._format = format

    def scale(self) -> int:
        return self._scale

    def fileName(self) -> str:
        return self._fileName

    def format(self) -> travellermap.MapFormat:
        return self._format

class SectorInfo(object):
    def __init__(
            self,
            canonicalName: typing.Iterable[str],
            abbreviation: typing.Optional[str],
            x: int,
            y: int,
            sectorFormat: travellermap.SectorFormat,
            metadataFormat: travellermap.MetadataFormat,
            isCustomSector: bool,
            customMapStyle: typing.Optional[travellermap.Style],
            customMapOptions: typing.Optional[typing.Iterable[travellermap.Option]],
            customMapLevels: typing.Optional[typing.Mapping[int, CustomMapLevel]],
            ) -> None:
        self._canonicalName = canonicalName
        self._abbreviation = abbreviation
        self._x = x
        self._y = y
        self._sectorFormat = sectorFormat
        self._metadataFormat = metadataFormat
        self._isCustomSector = isCustomSector
        self._customMapStyle = customMapStyle
        self._customMapOptions = list(customMapOptions) if customMapOptions else None
        self._customMapLevels = dict(customMapLevels) if customMapLevels else None

    def canonicalName(self) -> str:
        return self._canonicalName

    def abbreviation(self) -> str:
        return self._abbreviation

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def sectorFormat(self) -> travellermap.SectorFormat:
        return self._sectorFormat

    def metadataFormat(self) -> travellermap.MetadataFormat:
        return self._metadataFormat

    def isCustomSector(self) -> bool:
        return self._isCustomSector

    def customMapLevels(self) -> typing.Optional[typing.Dict[int, CustomMapLevel]]:
        return self._customMapLevels.copy() if self._customMapLevels else None

    def customMapLevel(self, scale: int) -> typing.Optional[CustomMapLevel]:
        return self._customMapLevels.get(scale) if self._customMapLevels else None

    def customMapStyle(self) -> typing.Optional[travellermap.Style]:
        return self._customMapStyle

    def customMapOptions(self) -> typing.Optional[typing.List[travellermap.Option]]:
        return self._customMapOptions.copy() if self._customMapOptions else None

class SectorLookupMaps(object):
    def __init__(self) -> None:
        self._sectors = set()
        self._positionMap = {}
        self._nameMap = {} # NOTE: Names are lower case as search is case insensitive

    def sectors(self) -> typing.Iterable[SectorInfo]:
        return self._sectors

    def count(self) -> int:
        return len(self._sectors)

    def addSector(
            self,
            sector: SectorInfo
            ) -> None:
        self._sectors.add(sector)
        self._positionMap[(sector.x(), sector.y())] = sector
        self._nameMap[sector.canonicalName().lower()] = sector

    def removeSector(
            self,
            sector: SectorInfo
            ) -> None:
        if sector not in self._sectors:
            return

        self._sectors.remove(sector)

        # Only remove position & name maps if it was found in the main list of sectors. This
        # is a safety net to avoid removing the world form only a single map if a sector with
        # the same name or position is passed in. Still play it safe and don't assume that
        # there is an entry in either of the maps.
        position = (sector.x(), sector.y())
        if position in self._positionMap:
            del self._positionMap[position]

        name = sector.canonicalName().lower()
        if name in self._nameMap:
            del self._nameMap[name]

    def clear(self) -> None:
        self._sectors.clear()
        self._positionMap.clear()
        self._nameMap.clear()

    def containsSector(
            self,
            sector: SectorInfo
            ) -> bool:
        return sector in self._sectors

    def lookupPosition(
            self,
            pos: typing.Tuple[int, int]
            ) -> typing.Optional[SectorInfo]:
        return self._positionMap.get(pos)

    def lookupName(
            self,
            name: str
            ) -> typing.Optional[SectorInfo]:
        return self._nameMap.get(name.lower())

class SectorConflictException(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)

class UniverseInfo(object):
    def __init__(
            self,
            milieu: travellermap.Milieu
            ) -> None:
        self._milieu = milieu
        self._stockSectorMap = SectorLookupMaps()
        self._customSectorMap = SectorLookupMaps()
        self._mergedSectorMap = SectorLookupMaps()

    def milieu(self) -> travellermap.Milieu:
        return self._milieu

    def conflictCheck(
            self,
            sectorName: str,
            sectorX: int,
            sectorY: int,
            isCustomSector: bool
            ) -> None:
        if isCustomSector:
            # Prevent adding the custom sector if it has the same name as another custom sector
            conflictSector = self._customSectorMap.lookupName(sectorName)
            if conflictSector:
                raise SectorConflictException(
                    'Sector has same name as custom sector {conflictName} at {conflictX},{conflictY}'.format(
                        conflictName=conflictSector.canonicalName(),
                        conflictX=conflictSector.x(),
                        conflictY=conflictSector.y()))

            # Prevent adding the custom sector if it has the same name as a stock sector at a different location
            conflictSector = self._stockSectorMap.lookupName(sectorName)
            if conflictSector and ((sectorX != conflictSector.x()) or (sectorY != conflictSector.y())):
                raise SectorConflictException(
                    'Sector has same name as stock sector {conflictName} at {conflictX},{conflictY}'.format(
                        conflictName=conflictSector.canonicalName(),
                        conflictX=conflictSector.x(),
                        conflictY=conflictSector.y()))

            # Prevent adding the custom sector if it has the same position as another custom sector
            conflictSector = self._customSectorMap.lookupPosition((sectorX, sectorY))
            if conflictSector:
                raise SectorConflictException(
                    'Sector has same position as custom sector {conflictName} at {conflictX},{conflictY}'.format(
                        conflictName=conflictSector.canonicalName(),
                        conflictX=conflictSector.x(),
                        conflictY=conflictSector.y()))
        else:
            # Prevent adding the stock sector if it has the same name as a custom sector at a different location
            conflictSector = self._customSectorMap.lookupName(sectorName)
            if conflictSector and ((sectorX != conflictSector.x()) or (sectorY != conflictSector.y())):
                raise SectorConflictException(
                    'Sector has same name as custom sector {conflictName} at {conflictX},{conflictY}'.format(
                        conflictName=conflictSector.canonicalName(),
                        conflictX=conflictSector.x(),
                        conflictY=conflictSector.y()))

            # Prevent adding the stock sector if it has the same name as another stock sector
            conflictSector = self._stockSectorMap.lookupName(sectorName)
            if conflictSector:
                raise SectorConflictException(
                    'Sector has same name as stock sector {conflictName} at {conflictX},{conflictY}'.format(
                        conflictName=conflictSector.canonicalName(),
                        conflictX=conflictSector.x(),
                        conflictY=conflictSector.y()))

            # Prevent adding the stock sector if it has the same position as another stock sector
            conflictSector = self._stockSectorMap.lookupPosition((sectorX, sectorY))
            if conflictSector:
                raise SectorConflictException(
                    'Sector has same position as stock sector {conflictName} at {conflictX},{conflictY}'.format(
                        conflictName=conflictSector.canonicalName(),
                        conflictX=conflictSector.x(),
                        conflictY=conflictSector.y()))

    def addSector(
            self,
            sector: SectorInfo
            ) -> None:
        # This will throw if the sector can't be added due to a conflict
        self.conflictCheck(
            sectorName=sector.canonicalName(),
            sectorX=sector.x(),
            sectorY=sector.y(),
            isCustomSector=sector.isCustomSector())

        if sector.isCustomSector():
            self._customSectorMap.addSector(sector)
        else:
            self._stockSectorMap.addSector(sector)
        self._updateMergedSectors(sector)

    def removeSector(
            self,
            sector: SectorInfo
            ) -> None:
        if sector.isCustomSector():
            self._customSectorMap.removeSector(sector)
        else:
            self._stockSectorMap.removeSector(sector)
        self._updateMergedSectors(sector)

    def clear(self):
        self._stockSectorMap.clear()
        self._customSectorMap.clear()
        self._mergedSectorMap.clear()

    def hasCustomSectors(self) -> bool:
        return self._customSectorMap.count() != 0

    def sectorCount(
            self,
            stockOnly: bool
            ) -> int:
        return self._stockSectorMap.count() if stockOnly else self._mergedSectorMap.count()

    def sectors(
            self,
            stockOnly: bool
            ) -> typing.Iterable[SectorInfo]:
        return list(self._stockSectorMap.sectors() if stockOnly else self._mergedSectorMap.sectors())

    def lookupPosition(
            self,
            position: typing.Tuple[int, int],
            stockOnly: bool
            ) -> typing.Optional[SectorInfo]:
        if stockOnly:
            return self._stockSectorMap.lookupPosition(position)
        return self._mergedSectorMap.lookupPosition(position)

    def lookupName(
            self,
            name: str,
            stockOnly: bool
            ) -> typing.Optional[SectorInfo]:
        if stockOnly:
            return self._stockSectorMap.lookupName(name)
        return self._mergedSectorMap.lookupName(name)

    def _updateMergedSectors(
            self,
            sector: SectorInfo
            ) -> None:
        position = (sector.x(), sector.y())
        if sector.isCustomSector():
            if self._customSectorMap.containsSector(sector):
                # The custom sector has been added so remove any sector at the same location
                # and add the custom sector to the merged map
                existingSector = self._mergedSectorMap.lookupPosition(position)
                if existingSector:
                    logging.info('Replacing sector {existingName} at {sectorX},{sectorY} in {milieu} with custom sector {customName}'.format(
                        existingName=existingSector.canonicalName(),
                        sectorX=sector.x(),
                        sectorY=sector.y(),
                        milieu=self._milieu.value,
                        customName=sector.canonicalName()))
                    self._mergedSectorMap.removeSector(existingSector)
                else:
                    logging.info('Adding custom sector {customName} at {sectorX},{sectorY} to {milieu}'.format(
                        customName=sector.canonicalName(),
                        sectorX=sector.x(),
                        sectorY=sector.y(),
                        milieu=self._milieu.value))
                self._mergedSectorMap.addSector(sector)
            else:
                # The custom sector has been removed so remove it from the merged map and
                # reinstate any stock sector at the same location
                logging.info('Removing custom sector {customName} at {sectorX},{sectorY} from {milieu}'.format(
                    customName=sector.canonicalName(),
                    sectorX=sector.x(),
                    sectorY=sector.y(),
                    milieu=self._milieu.value))
                self._mergedSectorMap.removeSector(sector)

                stockSector = self._stockSectorMap.lookupPosition(position)
                if stockSector:
                    logging.info('Reinstating stock sector {stockName} at {sectorX},{sectorY} in {milieu}'.format(
                        stockName=stockSector.canonicalName(),
                        sectorX=stockSector.x(),
                        sectorY=stockSector.y(),
                        milieu=self._milieu.value))
                    self._mergedSectorMap.addSector(stockSector)
        else:
            if self._stockSectorMap.containsSector(sector):
                # The stock sector is being added, only add it to the merge map if there isn't
                # a sector at the same location
                conflictSector = self._mergedSectorMap.lookupPosition(position)
                if conflictSector:
                    logging.info('Ignoring stock sector {stockName} at {sectorX},{sectorY} in {milieu} as it has been replaced by custom sector {conflictName}'.format(
                        stockName=sector.canonicalName(),
                        sectorX=sector.x(),
                        sectorY=sector.y(),
                        milieu=self._milieu.value,
                        conflictName=conflictSector.canonicalName()))
                else:
                    logging.debug('Adding stock sector {stockName} at {sectorX},{sectorY} to {milieu}'.format(
                        stockName=sector.canonicalName(),
                        sectorX=sector.x(),
                        sectorY=sector.y(),
                        milieu=self._milieu.value))
                    self._mergedSectorMap.addSector(sector)
            else:
                # The stock sector is being removed, only remove it from the merge map if it's
                # actually the sector at that location
                currentSector = self._mergedSectorMap.lookupPosition(position)
                if sector is currentSector:
                    logging.debug('Removing stock sector {stockName} at {sectorX},{sectorY} from {milieu}'.format(
                        stockName=sector.canonicalName(),
                        sectorX=sector.x(),
                        sectorY=sector.y(),
                        milieu=self._milieu.value))
                    self._mergedSectorMap.removeSector(sector)

class DataStore(object):
    class SnapshotAvailability(enum.Enum):
        NewSnapshotAvailable = 0
        NoNewSnapshot = 1
        AppToOld = 2
        AppToNew = 3

    class UpdateStage(enum.Enum):
        DownloadStage = 0
        ExtractStage = 1

    _MilieuBaseDir = 'milieu'
    _UniverseFileName = 'universe.json'
    _SophontsFileName = 'sophonts.json'
    _AllegiancesFileName = 'allegiances.json'
    _TimestampFileName = 'timestamp.txt'
    _DataFormatFileName = 'dataformat.txt'
    _SectorMetadataXsdFileName = 'sectors.xsd'
    _TimestampFormat = '%Y-%m-%d %H:%M:%S.%f'
    _DataArchiveUrl = 'https://github.com/cthulhustig/autojimmy-data/archive/refs/heads/main.zip'
    _DataArchiveMapPath = 'autojimmy-data-main/map/' # Trailing slash is important
    _TimestampUrl = 'https://raw.githubusercontent.com/cthulhustig/autojimmy-data/main/map/timestamp.txt'
    _DataFormatUrl = 'https://raw.githubusercontent.com/cthulhustig/autojimmy-data/main/map/dataformat.txt'
    _SnapshotCheckTimeout = 3 # Seconds
    # NOTE: Pattern for matching data version treats the second digit as optional, if not specified it's
    # assumed to be 0. It also allows white space at the end to stop an easy typo in the snapshot breaking
    # all instances of the app everywhere
    _DataVersionPattern = re.compile(r'^(\d+)(?:\.(\d+))?\s*$')
    _MinDataFormatVersion = UniverseDataFormat(4, 0)
    _FileSystemCacheSize = 256 * 1024 * 1024 # 256MiB

    _SectorFormatExtensions = {
        # NOTE: The sec format is short for second survey, not the legacy sec format
        travellermap.SectorFormat.T5Column: 'sec',
        travellermap.SectorFormat.T5Tab: 'tab'}
    _MetadataFormatExtensions = {
        travellermap.MetadataFormat.JSON: 'json',
        travellermap.MetadataFormat.XML: 'xml'}

    _instance = None # Singleton instance
    _lock = threading.RLock() # Recursive lock
    _installDir = None
    _overlayDir = None
    _customDir = None
    _universeMap = None
    _filesystemCache = common.FileSystemCache(maxCacheSize=_FileSystemCacheSize)

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
                    # Check the overlay version and age, the overlay directory will be deleted if
                    # it's no longer valid
                    cls._instance._checkOverlayDataFormat()
                    cls._instance._checkOverlayAge()
        return cls._instance

    @staticmethod
    def setSectorDirs(
            installDir: str,
            overlayDir: str,
            customDir: str
            ) -> None:
        if DataStore._instance:
            raise RuntimeError('You can\'t set the data store directories after the singleton has been initialised')
        DataStore._installDir = installDir
        DataStore._overlayDir = overlayDir
        DataStore._customDir = customDir

    def sectorCount(
            self,
            milieu: travellermap.Milieu,
            stockOnly: bool = False
            ) -> int:
        self._loadSectors(milieu=milieu)
        with self._lock:
            universe = self._universeMap[milieu]
            if not universe:
                return 0
            return universe.sectorCount(stockOnly=stockOnly)

    def sectors(
            self,
            milieu: travellermap.Milieu,
            stockOnly: bool = False
            ) -> typing.Iterable[SectorInfo]:
        self._loadSectors(milieu=milieu)
        with self._lock:
            universe = self._universeMap[milieu]
            if not universe:
                return []
            return universe.sectors(stockOnly=stockOnly)

    def sector(
            self,
            sectorName: str,
            milieu: travellermap.Milieu,
            stockOnly: bool = False
            ) -> typing.Optional[SectorInfo]:
        self._loadSectors(milieu=milieu)
        with self._lock:
            universe = self._universeMap[milieu]
            if not universe:
                return None
            return universe.lookupName(
                name=sectorName,
                stockOnly=stockOnly)

    def sectorAt(
            self,
            sectorX: int,
            sectorY: int,
            milieu: travellermap.Milieu,
            stockOnly: bool = False
            ) -> typing.Optional[SectorInfo]:
        self._loadSectors(milieu=milieu)
        with self._lock:
            universe = self._universeMap[milieu]
            if not universe:
                return None
            return universe.lookupPosition(
                position=(sectorX, sectorY),
                stockOnly=stockOnly)

    def sectorFileData(
            self,
            sectorName: str,
            milieu: travellermap.Milieu,
            stockOnly: bool = False
            ) -> str:
        self._loadSectors(milieu=milieu)

        with self._lock:
            universe = self._universeMap[milieu]
            sector = universe.lookupName(name=sectorName, stockOnly=stockOnly)
        if not sector:
            raise RuntimeError(f'Unable to retrieve sector file data for unknown sector {sectorName}')
        escapedSectorName = common.encodeFileName(rawFileName=sector.canonicalName())
        extension = DataStore._SectorFormatExtensions[sector.sectorFormat()]
        return self._bytesToString(bytes=self._readMilieuFile(
            fileName=f'{escapedSectorName}.{extension}',
            milieu=milieu,
            useCustomMapDir=sector.isCustomSector()))

    def sectorMetaData(
            self,
            sectorName: str,
            milieu: travellermap.Milieu,
            stockOnly: bool = False
            ) -> str:
        self._loadSectors(milieu=milieu)

        sector = self.sector(
            sectorName=sectorName,
            milieu=milieu,
            stockOnly=stockOnly)
        if not sector:
            raise RuntimeError(f'Unable to retrieve sector meta data for unknown sector {sectorName}')
        escapedSectorName = common.encodeFileName(rawFileName=sector.canonicalName())
        extension = DataStore._MetadataFormatExtensions[sector.metadataFormat()]
        return self._bytesToString(bytes=self._readMilieuFile(
            fileName=f'{escapedSectorName}.{extension}',
            milieu=milieu,
            useCustomMapDir=sector.isCustomSector()))

    def sectorMapImage(
            self,
            sectorName: str,
            milieu: travellermap.Milieu,
            scale: int
            ) -> travellermap.MapImage:
        self._loadSectors(milieu=milieu)

        sector = self.sector(
            sectorName=sectorName,
            milieu=milieu,
            stockOnly=False) # Stock only doesn't make sense for map images
        if not sector:
            raise RuntimeError(f'Unable to retrieve sector map data for unknown sector {sectorName}')
        mapLevel = sector.customMapLevel(scale=scale)
        if not mapLevel:
            raise RuntimeError(f'Unable to retrieve {scale} scale sector map data for {sectorName}')
        mapData = self._readMilieuFile(
            fileName=mapLevel.fileName(),
            milieu=milieu,
            useCustomMapDir=sector.isCustomSector())

        return travellermap.MapImage(
            bytes=mapData,
            format=mapLevel.format())

    def sophontsData(self) -> str:
        return self._bytesToString(bytes=self._readStockFile(
            relativeFilePath=self._SophontsFileName))

    def allegiancesData(self) -> str:
        return self._bytesToString(bytes=self._readStockFile(
            relativeFilePath=self._AllegiancesFileName))

    def universeTimestamp(self) -> typing.Optional[datetime.datetime]:
        try:
            return DataStore._parseTimestamp(
                data=self._readStockFile(relativeFilePath=self._TimestampFileName))
        except Exception as ex:
            logging.error(f'Failed to read universe timestamp', exc_info=ex)
            return None

    def universeDataFormat(self) -> typing.Optional[UniverseDataFormat]:
        try:
            return DataStore._parseUniverseDataFormat(
                data=self._readStockFile(relativeFilePath=self._DataFormatFileName))
        except Exception as ex:
            logging.error(f'Failed to read universe data format', exc_info=ex)
            return None

    def customSectorsTimestamp(self) -> typing.Optional[datetime.datetime]:
        try:
            timestampPath = os.path.join(self._customDir, self._TimestampFileName)
            return DataStore._parseTimestamp(
                data=self._filesystemCache.read(timestampPath))
        except Exception as ex:
            logging.error(f'Failed to read custom sectors timestamp', exc_info=ex)
            return None

    # NOTE: This will block while it downloads the latest snapshot timestamp from the github repo
    def checkForNewSnapshot(self) -> SnapshotAvailability:
        currentTimestamp = self.universeTimestamp()
        try:
            response = urllib.request.urlopen(
                DataStore._TimestampUrl,
                timeout=DataStore._SnapshotCheckTimeout)
            repoTimestamp = DataStore._parseTimestamp(data=response.read())
        except Exception as ex:
            raise RuntimeError(f'Failed to retrieve snapshot timestamp ({str(ex)})')

        if currentTimestamp and (repoTimestamp <= currentTimestamp):
            # No new snapshot available
            return DataStore.SnapshotAvailability.NoNewSnapshot

        try:
            response = urllib.request.urlopen(
                DataStore._DataFormatUrl,
                timeout=DataStore._SnapshotCheckTimeout)
            repoDataFormat = DataStore._parseUniverseDataFormat(data=response.read())
        except Exception as ex:
            raise RuntimeError(f'Failed to retrieve snapshot data format ({str(ex)})')

        if repoDataFormat < DataStore._MinDataFormatVersion:
            # The repo contains data in an older format than the app is expecting. This should
            # only happen when running a dev branch
            return DataStore.SnapshotAvailability.AppToNew

        # The data format is versioned such that the minor version increments should be backwards
        # compatible. If the major version is higher then the app is to old to use the data
        nextMajorVersion = UniverseDataFormat(
            major=DataStore._MinDataFormatVersion.major() + 1,
            minor=0)
        if repoDataFormat >= nextMajorVersion:
            return DataStore.SnapshotAvailability.AppToOld

        return DataStore.SnapshotAvailability.NewSnapshotAvailable

    def downloadSnapshot(
            self,
            progressCallback: typing.Optional[typing.Callable[[UpdateStage, int], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> None:
        with self._lock:
            logging.info('Downloading universe snapshot')
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

            logging.info('Extracting universe snapshot')
            if progressCallback:
                progressCallback(DataStore.UpdateStage.ExtractStage, 0)

            workingDirPath = self._makeWorkingDir(overlayDirPath=self._overlayDir)
            zipData = zipfile.ZipFile(dataBuffer)
            fileInfoList = zipData.infolist()

            # Find the data format file to sanity check that the snapshot is compatible
            dataFormatPath = DataStore._DataArchiveMapPath + DataStore._DataFormatFileName
            dataFormatInfo = None
            for fileInfo in fileInfoList:
                if fileInfo.is_dir():
                    continue # Skip directories
                if fileInfo.filename == dataFormatPath:
                    dataFormatInfo = fileInfo
                    break

            if not dataFormatInfo:
                raise RuntimeError('Universe snapshot has no data format file')
            try:
                dataFormat = self._parseUniverseDataFormat(
                    data=zipData.read(dataFormatInfo.filename))
            except Exception as ex:
                raise RuntimeError(f'Unable to read universe snapshot data format file ({str(ex)})')
            if not self._isDataFormatCompatible(dataFormat):
                raise RuntimeError(f'Universe snapshot is incompatible')

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

                logging.info(f'Extracting {subPath}')
                directoryHierarchy = os.path.dirname(targetPath)
                if not self._filesystemCache.exists(directoryHierarchy):
                    self._filesystemCache.makedirs(directoryHierarchy, canExist=True)
                self._filesystemCache.write(
                    path=targetPath,
                    data=zipData.read(fileInfo.filename))

            logging.info('Replacing old universe snapshot')
            self._replaceDir(
                workingDirPath=workingDirPath,
                currentDirPath=self._overlayDir)

            # Force reload of all sector data
            self._loadSectors(reload=True)

    def hasCustomSectors(
            self,
            milieu: typing.Optional[travellermap.Milieu] = None,
            ) -> bool:
        self._loadSectors(milieu=milieu)

        milieuList = [milieu] if milieu else travellermap.Milieu
        with self._lock:
            for milieu in milieuList:
                universe = self._universeMap[milieu]
                if not universe:
                    continue
                if universe.hasCustomSectors():
                    return True
        return False

    # This will throw a SectorConflictException if there is a conflict
    def customSectorConflictCheck(
            self,
            sectorName: str,
            sectorX: int,
            sectorY: int,
            milieu: travellermap.Milieu
            ) -> None:
        self._loadSectors(milieu=milieu)

        with self._lock:
            universe = self._universeMap[milieu]
            return universe.conflictCheck(
                sectorName=sectorName,
                sectorX=sectorX,
                sectorY=sectorY,
                isCustomSector=True)

    def createCustomSector(
            self,
            milieu: travellermap.Milieu,
            sectorContent: str,
            metadataContent: str,
            customMapStyle: typing.Optional[travellermap.Style],
            customMapOptions: typing.Optional[typing.Iterable[travellermap.Option]],
            customMapImages: typing.Mapping[int, travellermap.MapImage]
            ) -> SectorInfo:
        self._loadSectors(milieu=milieu)

        sectorFormat = travellermap.sectorFileFormatDetect(content=sectorContent)
        if not sectorFormat:
            raise RuntimeError('Sector file content has an unknown format')

        metadataFormat = travellermap.metadataFileFormatDetect(content=metadataContent)
        if not metadataFormat:
            raise RuntimeError('Sector metadata content has an unknown format')

        metadata = travellermap.readMetadata(
            content=metadataContent,
            format=metadataFormat,
            identifier='Custom Metadata')

        # Do a full parse of the custom sector data based on the detected file format. If it fails
        # an exception will be raised an allowed to pass back to the called. Doing this check is
        # important as it prevents bad data causing the app to barf when loading
        travellermap.readSector(
            content=sectorContent,
            format=sectorFormat,
            identifier=f'Custom Sector {metadata.canonicalName()}')

        milieuDirPath = os.path.join(
            self._customDir,
            DataStore._MilieuBaseDir,
            milieu.value)
        self._filesystemCache.makedirs(milieuDirPath, canExist=True)

        with self._lock:
            universe = self._universeMap[milieu]

            # This will throw if the custom sector has a name/position conflicts with an existing sector.
            # It's done now to prevent files being updated if the sector isn't going to be addable
            universe.conflictCheck(
                sectorName=metadata.canonicalName(),
                sectorX=metadata.x(),
                sectorY=metadata.y(),
                isCustomSector=True)

            escapedSectorName = common.encodeFileName(rawFileName=metadata.canonicalName())

            sectorExtension = DataStore._SectorFormatExtensions[sectorFormat]
            sectorFilePath = os.path.join(milieuDirPath, f'{escapedSectorName}.{sectorExtension}')
            self._filesystemCache.write(
                path=sectorFilePath,
                data=sectorContent)

            metadataExtension = DataStore._MetadataFormatExtensions[metadataFormat]
            metadataFilePath = os.path.join(milieuDirPath, f'{escapedSectorName}.{metadataExtension}')
            self._filesystemCache.write(
                path=metadataFilePath,
                data=metadataContent)

            mapLevels = {}
            for scale, mapImage in customMapImages.items():
                mapFormat = mapImage.format()
                mapLevelFileName = f'{escapedSectorName}_{scale}.{mapFormat.value}'
                mapLevelFilePath = os.path.join(milieuDirPath, mapLevelFileName)

                mapLevel = CustomMapLevel(
                    scale=scale,
                    fileName=mapLevelFileName,
                    format=mapFormat)
                mapLevels[mapLevel.scale()] = mapLevel

                # TODO: Need to check if this going into the cache is resulting in multiple
                # copies being help in memory of if they all work out to be the same byte array.
                # If there are multiple copies I need to add a non-cache option as this could eat
                # a lot of memory (may not be needed if I add cache eviction with a max memory
                # limit).
                # TODO: The cache should probably also have some kind of hard limit on the max
                # file size it caches (10MiB maybe)
                self._filesystemCache.write(
                    path=mapLevelFilePath,
                    data=mapImage.bytes())

            sector = SectorInfo(
                canonicalName=metadata.canonicalName(),
                abbreviation=metadata.abbreviation(),
                x=metadata.x(),
                y=metadata.y(),
                sectorFormat=sectorFormat,
                metadataFormat=metadataFormat,
                isCustomSector=True,
                customMapStyle=customMapStyle,
                customMapOptions=customMapOptions,
                customMapLevels=mapLevels)
            universe.addSector(sector)

            self._saveCustomSectors(milieu=milieu)

            return sector

    def deleteCustomSector(
            self,
            sectorName: str,
            milieu: travellermap.Milieu
            ) -> None:
        self._loadSectors(milieu=milieu)

        milieuDirPath = os.path.join(
            self._customDir,
            DataStore._MilieuBaseDir,
            milieu.value)

        with self._lock:
            universe = self._universeMap[milieu]
            sector = universe.lookupName(name=sectorName, stockOnly=False)
            if not sector:
                raise RuntimeError(
                    'Failed to delete custom sector {name} from {milieu} as it doesn\'t exist'.format(
                        name=sectorName,
                        milieu=milieu.value))

            # Remove the sector from the custom universe file first. That way we don't leave a partially
            # populated sector if deleting a file fails
            universe.removeSector(sector)
            self._saveCustomSectors(milieu=milieu)

            escapedSectorName = common.encodeFileName(rawFileName=sector.canonicalName())
            sectorExtension = DataStore._SectorFormatExtensions[sector.sectorFormat()]
            metadataExtension = DataStore._MetadataFormatExtensions[sector.metadataFormat()]
            files = [
                f'{escapedSectorName}.{sectorExtension}',
                f'{escapedSectorName}.{metadataExtension}']
            mapLevels = sector.customMapLevels()
            if mapLevels:
                for mapLevel in mapLevels.values():
                    files.append(mapLevel.fileName())

            # Perform best effort attempt to delete files. If it fails log and continue,
            # any undeleted files will have no effect since the sector has been deleted
            # from the universe. If the user re-creates the a sector with the same name
            # the files will hopefully be overwritten, if not an error will be generated
            for file in files:
                try:
                    filePath = os.path.join(milieuDirPath, file)
                    self._filesystemCache.remove(filePath)
                except Exception as ex:
                    logging.warning(
                        'Failed to delete custom sector file {file} from {milieu}'.format(
                            file=filePath,
                            milieu=milieu.value),
                        exc_info=ex)

            # Force reload of sectors for this milieu in order to load details of any
            # sector that had been replaced by the custom sector that was deleted
            self._loadSectors(milieu=milieu, reload=True)

    class SectorMetadataValidationError(Exception):
        def __init__(self, reason) -> None:
            super().__init__(f'Sector metadata is invalid:\nReason: {reason}')

    def validateSectorMetadataXML(self, content: str) -> None:
        xsdPath = os.path.join(self._installDir, DataStore._SectorMetadataXsdFileName)

        try:
            root = xml.etree.ElementTree.fromstring(content)
        except xml.etree.ElementTree.ParseError as ex:
            raise DataStore.SectorMetadataValidationError(str(ex))

        try:
            xmlschema.validate(root, xsdPath)
        except xmlschema.validators.exceptions.XMLSchemaValidationError as ex:
            # The default string representation for an XML validation exception is stupidly long (dozens of lines) so
            # wrap it in something more concise
            logging.debug('XSD validation of sector metadata failed', exc_info=ex)
            raise DataStore.SectorMetadataValidationError(ex.reason)

        # The base XSD has these as optional but they are required for custom sectors
        if root.find('./Name') == None:
            raise DataStore.SectorMetadataValidationError('Metadata must contain Name element')

        if root.find('./X') == None:
            raise DataStore.SectorMetadataValidationError('Metadata must contain X element')

        if root.find('./Y') == None:
            raise DataStore.SectorMetadataValidationError('Metadata must contain Y element')

    def clearCachedData(self):
        # No need to lock as cache is thread safe
        self._filesystemCache.clearCache()

    def _loadSectors(
            self,
            milieu: typing.Optional[travellermap.Milieu] = None,
            reload: bool = False
            ) -> None:
        with self._lock:
            if (not reload) and self._universeMap and ((not milieu) or self._universeMap.get(milieu)):
                return # Already loaded

            if not self._universeMap:
                self._universeMap: typing.Dict[travellermap.Milieu, UniverseInfo] = {}

            milieuList = [milieu] if milieu else travellermap.Milieu
            for milieu in milieuList:
                logging.debug('{operation} sector info for {milieu}'.format(
                    operation='Reloading' if reload else 'Loading',
                    milieu=milieu.value))

                universe = self._universeMap.get(milieu)
                if universe:
                    universe.clear()
                else:
                    universe = UniverseInfo(milieu=milieu)
                    self._universeMap[milieu] = universe

                loadedSectors = self._loadMilieuSectors(
                    milieu=milieu,
                    customSectors=True)
                for sector in loadedSectors:
                    logging.debug(
                        f'Loaded custom sector info for {sector.canonicalName()} at {sector.x()},{sector.y()} in {milieu.value}')
                    try:
                        universe.addSector(sector)
                    except SectorConflictException as ex:
                        logging.error(
                            f'Failed to add custom sector {sector.canonicalName()} at {sector.x()},{sector.y()} to universe for {milieu.value} ({ex})')
                    except Exception as ex:
                        logging.error(
                            f'Failed to add custom sector {sector.canonicalName()} at {sector.x()},{sector.y()} to universe for {milieu.value}', exc_info=ex)

                loadedSectors = self._loadMilieuSectors(
                    milieu=milieu,
                    customSectors=False)
                for sector in loadedSectors:
                    logging.debug(
                        f'Loaded stock sector info for {sector.canonicalName()} at {sector.x()},{sector.y()} in {milieu.value}')
                    try:
                        universe.addSector(sector)
                    except SectorConflictException as ex:
                        logging.error(
                            f'Failed to add stock sector {sector.canonicalName()} at {sector.x()},{sector.y()} to universe for {milieu.value} ({ex})')
                    except Exception as ex:
                        logging.error(
                            f'Failed to add stock sector {sector.canonicalName()} at {sector.x()},{sector.y()} to universe for {milieu.value}', exc_info=ex)

    def _checkOverlayDataFormat(self) -> None:
        if not self._filesystemCache.exists(self._overlayDir):
            # If the overlay directory doesn't exist there is nothing to check
            return
        overlayDataFormat = self.universeDataFormat()
        if self._isDataFormatCompatible(checkFormat=overlayDataFormat):
            # The overlay data format meets the min requirements for this version of the app and
            # it's still within the same major version so it should be compatible
            return

        # The overlay is using an incompatible data format (either to old or to new), delete the
        # directory to fall back to the install data (which should always be valid)
        self._deleteOverlayDir()

    def _isDataFormatCompatible(
            self,
            checkFormat: UniverseDataFormat
            ) -> bool:
        nextMajorVersion = UniverseDataFormat(
            major=DataStore._MinDataFormatVersion.major() + 1,
            minor=0)

        return (checkFormat >= DataStore._MinDataFormatVersion) and \
            (checkFormat < nextMajorVersion)

    def _checkOverlayAge(self) -> None:
        if not self._filesystemCache.exists(self._overlayDir):
            # If the overlay directory doesn't exist there is nothing to check
            return
        overlayTimestampPath = os.path.join(self._overlayDir, self._TimestampFileName)
        if not self._filesystemCache.exists(overlayTimestampPath):
            # Overlay timestamp file doesn't exist, err on th side of caution and don't do anything
            logging.warning(f'Overlay timestamp file "{overlayTimestampPath}" not found')
            return

        installTimestampPath = os.path.join(self._installDir, self._TimestampFileName)
        if not self._filesystemCache.exists(installTimestampPath):
            # Install timestamp file doesn't exist, err on th side of caution and don't do anything
            logging.warning(f'Install timestamp file "{installTimestampPath}" not found')
            return

        try:
            overlayTimestamp = DataStore._parseTimestamp(
                data=self._filesystemCache.read(overlayTimestampPath))
        except Exception as ex:
            logging.error(
                f'Failed to load overlay timestamp from "{overlayTimestampPath}"',
                exc_info=ex)
            return

        try:
            installTimestamp = DataStore._parseTimestamp(
                data=self._filesystemCache.read(installTimestampPath))
        except Exception as ex:
            logging.error(
                f'Failed to load install timestamp from "{installTimestampPath}"',
                exc_info=ex)
            return

        if overlayTimestamp >= installTimestamp:
            # The overlay data is newer (or equal) to the install timestamp so keep the overlay
            return

        # The overlay data is older than the install data so delete the overlay to fall back to
        # the install
        self._deleteOverlayDir()

    def _deleteOverlayDir(self) -> None:
        logging.info(f'Deleting overlay directory "{self._overlayDir}"')
        try:
            self._filesystemCache.rmtree(path=self._overlayDir)
        except Exception as ex:
            logging.error(
                f'Failed to delete overlay directory "{self._overlayDir}"',
                exc_info=ex)

    def _readStockFile(
            self,
            relativeFilePath: str
            ) -> bytes:
        # If the overlay directory exists load files from there, if not load from the
        # install directory
        filePath = os.path.join(
            self._overlayDir if os.path.isdir(self._overlayDir) else self._installDir,
            relativeFilePath)
        return self._filesystemCache.read(filePath)

    def _readMilieuFile(
            self,
            fileName: str,
            milieu: travellermap.Milieu,
            useCustomMapDir: bool
            ) -> bytes:
        relativePath = os.path.join(self._MilieuBaseDir, milieu.value, fileName)
        if useCustomMapDir:
            absolutePath = os.path.join(self._customDir, relativePath)
            return self._filesystemCache.read(absolutePath)

        return self._readStockFile(relativeFilePath=relativePath)

    def _makeWorkingDir(
            self,
            overlayDirPath: str
            ) -> str:
        workingDir = overlayDirPath + '_working'
        if self._filesystemCache.exists(workingDir):
            # Delete any previous working directory that may have been left kicking about
            self._filesystemCache.rmtree(workingDir)
        self._filesystemCache.makedirs(workingDir)
        return workingDir

    def _replaceDir(
            self,
            workingDirPath: str,
            currentDirPath: str
            ) -> None:
        oldDirPath = None
        if self._filesystemCache.exists(currentDirPath):
            oldDirPath = currentDirPath + '_old'
            if self._filesystemCache.exists(oldDirPath):
                self._filesystemCache.rmtree(oldDirPath)
            self._filesystemCache.rename(currentDirPath, oldDirPath)

        try:
            self._filesystemCache.rename(workingDirPath, currentDirPath)
        except Exception:
            if oldDirPath:
                self._filesystemCache.rename(oldDirPath, currentDirPath)
            raise

    def _loadMilieuSectors(
            self,
            milieu: travellermap.Milieu,
            customSectors: bool
            ) -> typing.List[SectorInfo]:
        sectorType = 'custom' if customSectors else 'base'

        try:
            universeContent = self._readMilieuFile(
                fileName=self._UniverseFileName,
                milieu=milieu,
                useCustomMapDir=customSectors)

            universeJson = json.loads(DataStore._bytesToString(universeContent))

            sectorsElement = universeJson.get('Sectors')
            if sectorsElement == None:
                raise RuntimeError('No Sectors element found')
        except Exception as ex:
            message = f'Failed to load {sectorType} universe ({str(ex)})'
            if customSectors:
                # Custom map data is optional so if the universe file doesn't exist or fails to
                # parse just log and continue as if there are no custom sectors
                if isinstance(ex, FileNotFoundError):
                    logging.debug(message)
                else:
                    logging.warning(message)
                return []

            raise RuntimeError(message)

        sectors = []
        for sectorElement in sectorsElement:
            sectorX = None
            sectorY = None
            canonicalName = None
            try:
                sectorX = sectorElement.get('X')
                if sectorX == None:
                    raise RuntimeError('Sector has no x position')
                sectorX = int(sectorX)

                sectorY = sectorElement.get('Y')
                if sectorY == None:
                    raise RuntimeError('Sector has no y position')
                sectorY = int(sectorY)

                namesElements = sectorElement.get('Names')
                canonicalName = None
                if namesElements != None:
                    for nameElement in namesElements:
                        name = nameElement.get('Text')
                        if name == None:
                            continue
                        canonicalName = str(name)
                        break
                if not canonicalName:
                    raise RuntimeError('Sector has no name')

                abbreviation = sectorElement.get('Abbreviation')
                if abbreviation != None:
                    abbreviation = str(abbreviation)

                #
                # The following elements are extensions and not part of the standard universe file format
                #

                # If the universe doesn't specify the sector format it must be a standard traveller map
                # universe file which means the corresponding sectors files all use T5 column format
                sectorFormatTag = sectorElement.get('SectorFormat')
                sectorFormat = travellermap.SectorFormat.T5Column
                if sectorFormatTag != None:
                    sectorFormat = travellermap.SectorFormat.__members__.get(
                        str(sectorFormatTag),
                        sectorFormat)

                # If the universe doesn't specify the metadata format it must be a standard traveller map
                # universe file which means the corresponding metadata files all use XML format
                metadataFormatTag = sectorElement.get('MetadataFormat')
                metadataFormat = travellermap.MetadataFormat.XML
                if metadataFormatTag != None:
                    metadataFormat = travellermap.MetadataFormat.__members__.get(
                        str(metadataFormatTag),
                        metadataFormat)

                customMapLevels = None
                customMapStyle = None
                customMapOptions = None
                if customSectors:
                    customMapStyleTag = sectorElement.get('CustomMapStyle')
                    if customMapStyleTag:
                        customMapStyle = travellermap.Style.__members__.get(str(customMapStyleTag))
                        if customMapStyle == None:
                            raise RuntimeError('Sector has no custom map style')

                    customMapOptionsElement = sectorElement.get('CustomMapOptions')
                    if customMapOptionsElement:
                        customMapOptions = []
                        for optionTag in customMapOptionsElement:
                            optionTag = str(optionTag)
                            option = travellermap.Option.__members__.get(optionTag)
                            if option == None:
                                raise RuntimeError(f'Sector has unknown custom map option {optionTag}')
                            customMapOptions.append(option)

                    customMapLevelsElement = sectorElement.get('CustomMapLevels')
                    if customMapLevelsElement == None:
                        raise RuntimeError('Sector has no custom map levels')

                    customMapLevels = {}
                    for mapLevel in customMapLevelsElement:
                        mimeType = mapLevel.get('MimeType')
                        if mimeType == None:
                            raise RuntimeError('Custom map level has no mime type')
                        mimeType = str(mimeType)

                        mapFormat = travellermap.mimeTypeToMapFormat(mimeType=mimeType)
                        if mapFormat == None:
                            raise RuntimeError(f'Custom map level has unsupported mime type {mimeType}')

                        scale = mapLevel.get('Scale')
                        if scale == None:
                            raise RuntimeError(f'Custom map level has no scale')
                        scale = int(scale)

                        fileName = mapLevel.get('FileName')
                        if fileName == None:
                            raise RuntimeError(f'Custom map level has no file name')
                        fileName = str(fileName)

                        mapLevel = CustomMapLevel(
                            scale=scale,
                            fileName=fileName,
                            format=mapFormat)
                        customMapLevels[mapLevel.scale()] = mapLevel

                sectors.append(SectorInfo(
                    canonicalName=canonicalName,
                    abbreviation=abbreviation,
                    x=sectorX,
                    y=sectorY,
                    sectorFormat=sectorFormat,
                    metadataFormat=metadataFormat,
                    isCustomSector=customSectors,
                    customMapStyle=customMapStyle,
                    customMapOptions=customMapOptions,
                    customMapLevels=customMapLevels))
            except Exception as ex:
                if canonicalName != None:
                    logging.warning(f'Skipping {sectorType} sector at {canonicalName} in {milieu.value} ({str(ex)})')
                elif sectorX != None and sectorY != None:
                    logging.warning(f'Skipping {sectorType} sector at {sectorX},{sectorY} in {milieu.value} ({str(ex)})')
                else:
                    logging.warning(f'Skipping unidentified {sectorType} sector in {milieu.value} ({str(ex)})')

        return sectors

    def _saveCustomSectors(
            self,
            milieu: travellermap.Milieu
            ) -> None:
        universeFilePath = os.path.join(
            self._customDir,
            DataStore._MilieuBaseDir,
            milieu.value,
            DataStore._UniverseFileName)
        timestampPath = os.path.join(
            self._customDir,
            self._TimestampFileName)

        with self._lock:
            universe = self._universeMap[milieu]
            sectorListData = []
            for sectorInfo in universe.sectors(stockOnly=False):
                if not sectorInfo.isCustomSector():
                    continue

                sectorData = {
                    'Names': [{'Text': sectorInfo.canonicalName()}],
                    'X': sectorInfo.x(),
                    'Y': sectorInfo.y()
                    }

                #
                # The following elements are extensions and not part of the standard universe file format
                #

                sectorData['SectorFormat'] = sectorInfo.sectorFormat().name
                sectorData['MetadataFormat'] = sectorInfo.metadataFormat().name

                mapLevels = sectorInfo.customMapLevels()
                mapLevelListData = []
                if mapLevels:
                    for mapLevel in mapLevels.values():
                        mapLevelListData.append({
                            'Scale': mapLevel.scale(),
                            'FileName': mapLevel.fileName(),
                            'MimeType': travellermap.mapFormatToMimeType(format=mapLevel.format())
                        })
                if mapLevelListData:
                    sectorData['CustomMapLevels'] = mapLevelListData

                mapStyle = sectorInfo.customMapStyle()
                if mapStyle:
                    sectorData['CustomMapStyle'] = mapStyle.name

                mapOptions = sectorInfo.customMapOptions()
                if mapOptions:
                    sectorData['CustomMapOptions'] = [option.name for option in mapOptions]

                sectorListData.append(sectorData)

            universeData = {'Sectors': sectorListData}

            self._filesystemCache.write(
                path=universeFilePath,
                data=json.dumps(universeData, indent=4))

            utcTime = common.utcnow()
            self._filesystemCache.write(
                path=timestampPath,
                data=DataStore._formatTimestamp(timestamp=utcTime))

    @staticmethod
    def _bytesToString(bytes: bytes) -> str:
        return bytes.decode('utf-8-sig') # Use utf-8-sig to strip BOM from unicode files

    @staticmethod
    def _parseTimestamp(data: bytes) -> datetime.datetime:
        timestamp = datetime.datetime.strptime(
            DataStore._bytesToString(data),
            DataStore._TimestampFormat)
        return datetime.datetime.fromtimestamp(
            timestamp.timestamp(),
            tz=datetime.timezone.utc)

    def _formatTimestamp(timestamp: datetime.datetime) -> bytes:
        timestamp = timestamp.astimezone(datetime.timezone.utc)
        return timestamp.strftime(DataStore._TimestampFormat).encode()

    # NOTE: The data format is a major.minor version number with the minor number
    # being optional (assumed 0 if not present)
    @staticmethod
    def _parseUniverseDataFormat(data: bytes) -> UniverseDataFormat:
        result = DataStore._DataVersionPattern.match(
            DataStore._bytesToString(data))
        if not result:
            raise RuntimeError('Invalid data format')
        major = result.group(1)
        minor = result.group(2)
        return UniverseDataFormat(
            major=int(major),
            minor=int(minor) if minor else 0)
