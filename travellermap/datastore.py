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
import xmlschema
import xml.etree.ElementTree
import zipfile

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
    class UpdateStage(enum.Enum):
        DownloadStage = 0,
        ExtractStage = 1

    _MilieuBaseDir = 'milieu'
    _UniverseFileName = 'universe.json'
    _SophontsFileName = 'sophonts.json'
    _AllegiancesFileName = 'allegiances.json'
    _MainsFileName = 'mains.json'
    _DataFormatFileName = 'dataformat.txt'
    _TimestampFileName = 'timestamp.txt'
    _SectorMetadataXsdFileName = 'sectors.xsd'
    _TimestampFormat = '%Y-%m-%d %H:%M:%S.%f'
    _DataArchiveUrl = 'https://github.com/cthulhustig/autojimmy-data/archive/refs/heads/main.zip'
    _DataArchiveMapPath = 'autojimmy-data-main/map/'
    _TimestampUrl = 'https://raw.githubusercontent.com/cthulhustig/autojimmy-data/main/map/timestamp.txt'
    _TimestampCheckTimeout = 3 # Seconds
    _DefaultSectorsMilieu = travellermap.Milieu.M1105

    # TODO: This should be 3.1 for the next version
    _MinDataFormatVersion = 3

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
                    cls._instance._checkOverlayVersion()
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
        self._loadSectors()
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
        self._loadSectors()
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
        self._loadSectors()
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
        self._loadSectors()
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
        self._loadSectors()

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
        self._loadSectors()

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
        self._loadSectors()

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
        return self._bytesToString(bytes=self._readFile(
            relativeFilePath=self._SophontsFileName))

    def allegiancesData(self) -> str:
        return self._bytesToString(bytes=self._readFile(
            relativeFilePath=self._AllegiancesFileName))
    
    def mainsData(
            self,
            milieu: travellermap.Milieu,
            stockOnly: bool = False
            ) -> str:
        if (not stockOnly) and self.hasCustomSectors(milieu=milieu):
            try:
                return self._bytesToString(bytes=self._readMilieuFile(
                    fileName=DataStore._MainsFileName,
                    milieu=milieu,
                    useCustomMapDir=True))
            except Exception as ex:
                logging.error(f'Data store failed to read custom mains data for {milieu.value}', exc_info=ex)
                # Continue to load default file

        return self._bytesToString(bytes=self._readFile(
            relativeFilePath=self._MainsFileName))    

    def snapshotTimestamp(self) -> typing.Optional[datetime.datetime]:
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
                if not os.path.exists(directoryHierarchy):
                    os.makedirs(directoryHierarchy, exist_ok=True)
                with open(targetPath, 'wb') as outputFile:
                    outputFile.write(zipData.read(fileInfo.filename))

            logging.info('Replacing old universe snapshot')
            self._replaceDir(
                workingDirPath=workingDirPath,
                currentDirPath=self._overlayDir)
            
            # Force reload of all sector data
            self._loadSectors(reload=True)
            
            # Regenerate the custom mains for _ALL_ milieu
            # TODO: Progress should probably take this into account somehow (if I can't get the time down)
            self._regenerateCustomMains()
            
    def hasCustomSectors(
            self,
            milieu: typing.Optional[travellermap.Milieu] = None,
            ) -> bool:
        self._loadSectors()

        milieuList = [milieu] if milieu else travellermap.Milieu
        with self._lock:        
            for milieu in milieuList:
                universe = self._universeMap[milieu]
                if not universe:
                    continue
                if universe.hasCustomSectors():
                    return True
        return False
    
    def createCustomSector(
            self,
            milieu: travellermap.Milieu,
            sectorContent: str,
            metadataContent: str,
            customMapStyle: typing.Optional[travellermap.Style],
            customMapOptions: typing.Optional[typing.Iterable[travellermap.Option]],
            customMapImages: typing.Mapping[int, travellermap.MapImage]
            ) -> SectorInfo:
        self._loadSectors()

        # Load metadata, currently only XML format is supported. The Poster API also supports
        # MSEC metadata but that format doesn't include the sector position. Strangely the docs
        # don't say it supports JSON format
        metadata = travellermap.parseXMLMetadata(
            content=metadataContent,
            identifier='Custom Metadata')

        sectorFormat = travellermap.sectorFileFormatDetect(content=sectorContent)
        if not sectorFormat:
            raise RuntimeError('Sector file content has an unknown format')

        # Do a full parse of the custom sector data based on the detected file format. If it fails
        # an exception will be raised an allowed to pass back to the called. Doing this check is
        # important as it prevents bad data causing the app to barf when loading
        travellermap.parseSector(
            content=sectorContent,
            fileFormat=sectorFormat,
            identifier=f'Custom Sector {metadata.canonicalName()}')

        milieuDirPath = os.path.join(
            self._customDir,
            DataStore._MilieuBaseDir,
            milieu.value)
        os.makedirs(milieuDirPath, exist_ok=True)

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
            with open(sectorFilePath, 'w', encoding='utf-8') as file:
                file.write(sectorContent)

            metadataFilePath = os.path.join(milieuDirPath, f'{escapedSectorName}.xml')
            with open(metadataFilePath, 'w', encoding='utf-8') as file:
                file.write(metadataContent)

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

                with open(mapLevelFilePath, 'wb') as file:
                    file.write(mapImage.bytes())

            sector = SectorInfo(
                canonicalName=metadata.canonicalName(),
                abbreviation=metadata.abbreviation(),
                x=metadata.x(),
                y=metadata.y(),
                sectorFormat=sectorFormat,
                metadataFormat=travellermap.MetadataFormat.XML, # Only XML metadata is supported for custom sectors
                isCustomSector=True,
                customMapStyle=customMapStyle,
                customMapOptions=customMapOptions,
                customMapLevels=mapLevels)
            universe.addSector(sector)
            
            self._saveCustomSectors(milieu=milieu)

            # Regenerate the mains for the affected milieu
            self._regenerateCustomMains(milieu=milieu)            

            return sector

    def deleteCustomSector(
            self,
            sectorName: str,
            milieu: travellermap.Milieu
            ) -> None:
        self._loadSectors()

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
                    os.remove(filePath)
                except Exception as ex:
                    logging.warning(
                        'Failed to delete custom sector file {file} from {milieu}'.format(
                            file=filePath,
                            milieu=milieu.value),
                        exc_info=ex)
                    
            # Force reload of sectors for this milieu in order to load details of any
            # sector that had been replaced by the custom sector that was deleted
            self._loadSectors(milieu=milieu, reload=True)
                    
            # Regenerate the mains for the affected milieu
            self._regenerateCustomMains(milieu=milieu)

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

    def _loadSectors(
            self,
            milieu: typing.Optional[travellermap.Milieu] = None,
            reload: bool = False
            ) -> None:
        with self._lock:
            if (not reload) and self._universeMap and ((not milieu) or self._universeMap.get(milieu)):
                return # Already loaded
            
            logging.info('{operation} sector info'.format(operation='Reloading' if reload else 'Loading'))

            if not self._universeMap:
                self._universeMap: typing.Dict[travellermap.Milieu, UniverseInfo] = {}

            milieuList = [milieu] if milieu else travellermap.Milieu
            for milieu in milieuList:
                logging.debug(f'Loading sector info for {milieu.value}')

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

    def _checkOverlayVersion(self) -> None:
        if not os.path.exists(self._overlayDir):
            # If the overlay directory doesn't exist there is nothing to check
            return
        overlayDataFormatPath = os.path.join(self._overlayDir, self._DataFormatFileName)

        # The data format file might not exist if the overlay was created by an older version.
        # In that situation the current overlay should be deleted
        if os.path.exists(overlayDataFormatPath):
            try:
                with open(overlayDataFormatPath, 'rb') as file:
                    # TODO: This is NOT finished, it's just a hack to get things working. It needs
                    # updated to do proper major/minor version numbers rather than just forcing a
                    # float to an int
                    overlayDataFormat = int(float(file.read()))

                if overlayDataFormat >= self._MinDataFormatVersion:
                    # The current overlay meets the required data format
                    return
            except Exception as ex:
                logging.warning(
                    f'Failed to load overlay data format from "{overlayDataFormatPath}"',
                    exc_info=ex)

        self._deleteOverlayDir()

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

        self._deleteOverlayDir()

    def _deleteOverlayDir(self) -> None:
        logging.info(f'Deleting overlay directory "{self._overlayDir}"')
        try:
            shutil.rmtree(self._overlayDir)
        except Exception as ex:
            logging.error(
                f'Failed to delete overlay directory "{self._overlayDir}"',
                exc_info=ex)

    def _readFile(
            self,
            relativeFilePath: str
            ) -> bytes:
        # If the overlay directory exists load files from there, if not load from the
        # install directory
        filePath = os.path.join(
            self._overlayDir if os.path.isdir(self._overlayDir) else self._installDir,
            relativeFilePath)
        with open(filePath, 'rb') as file:
            return file.read()
        
    def _readMilieuFile(
            self,
            fileName: str,
            milieu: travellermap.Milieu,
            useCustomMapDir: bool
            ) -> bytes:
        relativePath = os.path.join(self._MilieuBaseDir, milieu.value, fileName)
        if useCustomMapDir:
            absolutePath = os.path.join(self._customDir, relativePath)
            with open(absolutePath, 'rb') as file:
                return file.read()

        return self._readFile(relativeFilePath=relativePath)
    
    # NOTE: This assumes the lock is already held to give consistent results
    def _regenerateCustomMains(
            self,
            milieu: typing.Optional[travellermap.Milieu] = None
            ) -> None:
        defaultSectors = self._loadSectorWorlds(
            milieu=DataStore._DefaultSectorsMilieu,
            stockOnly=True) # Custom sectors shouldn't be used for default sector data

        milieuList = [milieu] if milieu else travellermap.Milieu
        for milieu in milieuList:
            logging.info(f'Regenerating mains for {milieu.value}')

            customMainsFilePath = os.path.join(
                self._customDir,
                DataStore._MilieuBaseDir,
                milieu.value,
                DataStore._MainsFileName)

            if not self.hasCustomSectors(milieu=milieu):
                # This milieu has no custom sectors so delete any mains file for that custom sector
                # if it exists to cause the default file from Traveller Map
                try:
                    if os.path.isfile(customMainsFilePath):
                        os.remove(customMainsFilePath)
                except Exception as ex:
                    logging.error(f'Failed to delete custom mains file for {milieu.value}', exc_info=ex)
                continue # Keep going and try to update the next milieu

            try:
                mainsGenerator = travellermap.MainGenerator()
                sectorWorlds = self._loadSectorWorlds(
                    milieu=milieu,
                    stockOnly=False) # Load custom sectors
                    
                # If the milieu being updated isn't the base milieu then use worlds from the base milieu
                # for any locations where the base milieu has a sector but the current milieu doesn't.
                # This mimics the behaviour of Traveller Map but with support for custom sectors
                if milieu != DataStore._DefaultSectorsMilieu:
                    seenSectors = set()
                    for sectorInfo in sectorWorlds.keys():
                        seenSectors.add((sectorInfo.x(), sectorInfo.y()))
                    for sectorInfo in defaultSectors.keys():
                        if (sectorInfo.x(), sectorInfo.y()) not in seenSectors:
                            sectorWorlds[sectorInfo] = defaultSectors[sectorInfo]

                for sectorInfo, worldList in sectorWorlds.items():
                    for world in worldList:
                        worldHex = world.attribute(travellermap.WorldAttribute.Hex)
                        if len(worldHex) != 4:
                            pass # TODO: Do something

                        mainsGenerator.addWorld(
                            sectorX=sectorInfo.x(),
                            sectorY=sectorInfo.y(),
                            hexX=int(worldHex[:2]),
                            hexY=int(worldHex[2:]))
                        
                mains = mainsGenerator.generate()
                outputData = []
                for main in mains:
                    outputMain = []
                    for sectorX, sectorY, hexX, hexY in main:
                        outputMain.append(f'{sectorX}/{sectorY}/{hexX:02d}{hexY:02d}')
                    outputData.append(outputMain)
            except Exception as ex:
                logging.error(f'Failed to generate custom mains file for {milieu.value}', exc_info=ex)
                continue # Keep going and try to update the next milieu

            try:
                with open(customMainsFilePath, 'w', encoding='utf-8') as file:
                    json.dump(outputData, file)
            except Exception as ex:
                logging.error(f'Failed to write custom mains file for {milieu.value}', exc_info=ex)
                continue # Keep going and try to update the next milieu

    def _loadSectorWorlds(
            self,
            milieu: travellermap.Milieu,
            stockOnly: bool
            ) -> typing.Mapping[SectorInfo, typing.Iterable[travellermap.RawWorld]]:
        sectorWorldMap = {}
        for sectorInfo in self.sectors(milieu=milieu, stockOnly=stockOnly):
            sectorData = self.sectorFileData(
                sectorName=sectorInfo.canonicalName(),
                milieu=milieu,
                stockOnly=stockOnly)
            if not sectorData:
                continue
            sectorWorldMap[sectorInfo] = travellermap.parseSector(
                content=sectorData,
                fileFormat=sectorInfo.sectorFormat(),
                identifier=sectorInfo.canonicalName())
        return sectorWorldMap


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
        return bytes.decode('utf-8-sig') # Use utf-8-sig to strip BOM from unicode files

    @staticmethod
    def _parseSnapshotTimestamp(data: bytes) -> datetime.datetime:
        return datetime.datetime.strptime(
            DataStore._bytesToString(data),
            DataStore._TimestampFormat)

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
                # universe file which means the corresponding metadata files all use JSON format
                metadataFormatTag = sectorElement.get('MetadataFormat')
                metadataFormat = travellermap.MetadataFormat.JSON
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

            with open(universeFilePath, 'w', encoding='utf-8') as file:
                json.dump(universeData, file, indent=4)
