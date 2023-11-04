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

class DataStore(object):
    class UpdateStage(enum.Enum):
        DownloadStage = 0,
        ExtractStage = 1

    _MilieuBaseDir = 'milieu'
    _UniverseFileName = 'universe.json'
    _SophontsFileName = 'sophonts.json'
    _AllegiancesFileName = 'allegiances.json'
    _DataFormatFileName = 'dataformat.txt'
    _TimestampFileName = 'timestamp.txt'
    _SectorMetadataXsdFileName = 'sectors.xsd'
    _TimestampFormat = '%Y-%m-%d %H:%M:%S.%f'
    _DataArchiveUrl = 'https://github.com/cthulhustig/autojimmy-data/archive/refs/heads/main.zip'
    _DataArchiveMapPath = 'autojimmy-data-main/map/'
    _TimestampUrl = 'https://raw.githubusercontent.com/cthulhustig/autojimmy-data/main/map/timestamp.txt'
    _TimestampCheckTimeout = 3 # Seconds

    _MinDataFormatVersion = 2

    _SectorFormatExtensions = {
        # NOTE: The sec format is short for second survey, not the legacy sec format
        travellermap.SectorFormat.T5Column: 'sec',
        travellermap.SectorFormat.T5Tab: 'tab'}
    _MetadataFormatExtensions = {
        travellermap.MetadataFormat.JSON: 'json',
        travellermap.MetadataFormat.XML: 'xml'}

    _instance = None # Singleton instance
    _lock = threading.RLock()
    _installDir = None
    _overlayDir = None
    _customDir = None
    _milieuMap = None

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
            milieu: travellermap.Milieu
            ) -> int:
        self._loadAllSectors()
        with self._lock:
            return len(self._milieuMap[milieu])

    def sectors(
            self,
            milieu: travellermap.Milieu
            ) -> typing.Iterable[SectorInfo]:
        self._loadAllSectors()
        with self._lock:
            return list(self._milieuMap[milieu].values())

    def sector(
            self,
            sectorName: str,
            milieu: travellermap.Milieu
            ) -> typing.Optional[SectorInfo]:
        self._loadAllSectors()
        with self._lock:
            sectors = self._milieuMap[milieu]
            return sectors.get(sectorName)

    def sectorAt(
            self,
            sectorX: int,
            sectorY: int,
            milieu: travellermap.Milieu
            ) -> typing.Optional[SectorInfo]:
        self._loadAllSectors()
        with self._lock:
            # TODO: Iterating over all sectors is inefficient
            for sector in self._milieuMap[milieu].values():
                assert(isinstance(sector, SectorInfo))
                if (sectorX == sector.x()) and (sectorY == sector.y()):
                    return sector
        return None

    def sectorFileData(
            self,
            sectorName: str,
            milieu: travellermap.Milieu
            ) -> str:
        self._loadAllSectors()

        sectorMap = self._milieuMap[milieu]
        if sectorName not in sectorMap:
            raise RuntimeError(f'Unable to retrieve sector file data for unknown sector {sectorName}')
        sector: SectorInfo = sectorMap[sectorName]
        escapedSectorName = common.encodeFileName(rawFileName=sector.canonicalName())
        extension = DataStore._SectorFormatExtensions[sector.sectorFormat()]
        return self._bytesToString(bytes=self._readMilieuFile(
            fileName=f'{escapedSectorName}.{extension}',
            milieu=milieu,
            useCustomMapDir=sector.isCustomSector()))

    def sectorMetaData(
            self,
            sectorName: str,
            milieu: travellermap.Milieu
            ) -> str:
        self._loadAllSectors()

        sectorMap = self._milieuMap[milieu]
        if sectorName not in sectorMap:
            raise RuntimeError(f'Unable to retrieve sector meta data for unknown sector {sectorName}')
        sector: SectorInfo = sectorMap[sectorName]
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
        self._loadAllSectors()

        sectorMap = self._milieuMap[milieu]
        if sectorName not in sectorMap:
            raise RuntimeError(f'Unable to retrieve sector map data for unknown sector {sectorName}')
        sector: SectorInfo = sectorMap[sectorName]
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
            logging.info('Downloading universe data archive')
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

            logging.info('Extracting universe data archive')
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

            logging.info('Replacing old universe data')
            self._replaceDir(
                workingDirPath=workingDirPath,
                currentDirPath=self._overlayDir)

    def createCustomSector(
            self,
            milieu: travellermap.Milieu,
            sectorContent: str,
            metadataContent: str,
            customMapStyle: typing.Optional[travellermap.Style],
            customMapOptions: typing.Optional[typing.Iterable[travellermap.Option]],
            customMapImages: typing.Mapping[int, travellermap.MapImage]
            ) -> SectorInfo:
        self._loadAllSectors()

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
            sectors: typing.Optional[typing.Mapping[str, SectorInfo]] = self._milieuMap.get(milieu)
            if sectors:
                # Check for custom sectors at the same location
                for existingSector in sectors.values():
                    assert(isinstance(existingSector, SectorInfo))
                    if not existingSector.isCustomSector():
                        continue

                    if (metadata.x() == existingSector.x()) and (metadata.y() == existingSector.y()):
                        raise RuntimeError(
                            'Unable to create custom sector {newName} in {milieu} as custom sector {existingName} is already located at ({x}, {y})'.format(
                                newName=metadata.canonicalName(),
                                milieu=milieu.value,
                                existingName=existingSector.canonicalName(),
                                x=metadata.x(),
                                y=metadata.y()))

                # Check for sectors with the same name but different locations
                existingSector = sectors.get(metadata.canonicalName())
                if existingSector:
                    assert(isinstance(existingSector, SectorInfo))
                    if (metadata.x() != existingSector.x()) or (metadata.y() != existingSector.y()):
                        raise RuntimeError(
                            'Unable to create custom sector {newName} in {milieu} as there is a already a sector with that name'.format(
                                newName=metadata.canonicalName(),
                                milieu=milieu.value))

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
            sectors[sector.canonicalName()] = sector

            self._saveCustomSectors(milieu=milieu)

            return sector

    def deleteCustomSector(
            self,
            sectorName: str,
            milieu: travellermap.Milieu
            ) -> None:
        self._loadAllSectors()

        milieuDirPath = os.path.join(
            self._customDir,
            DataStore._MilieuBaseDir,
            milieu.value)

        with self._lock:
            sectors: typing.Optional[typing.Mapping[str, SectorInfo]] = self._milieuMap.get(milieu, None)
            sector = sectors.get(sectorName) if sectors else None
            if not sector:
                raise RuntimeError(
                    'Failed to delete custom sector {name} from {milieu} as it doesn\'t exist'.format(
                        name=sectorName,
                        milieu=milieu.value))

            # Remove the sector from the custom universe file first. That way we don't leave a partially
            # populated sector if deleting a file fails
            del sectors[sectorName]
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

    def _loadAllSectors(self) -> None:
        if self._milieuMap:
            # Already loaded, nothing to do
            return

        with self._lock:
            if self._milieuMap:
                # Another thread loaded the sectors while this one was waiting on the lock
                return

            self._milieuMap = {}
            for milieu in travellermap.Milieu:
                customSectorPosMap: typing.Dict[typing.Tuple[int, int], SectorInfo] = {}
                customSectorNameMap: typing.Dict[str, SectorInfo] = {}
                loadedSectorNameMap: typing.Dict[str, SectorInfo] = {}

                loadedSectors = self._loadMilieuSectors(
                    milieu=milieu,
                    customSectors=True)
                for sector in loadedSectors:
                    logging.debug(
                        f'Loaded custom sector info for {sector.canonicalName()} at {sector.x()},{sector.y()} in {milieu.value}')
                    customSectorPosMap[(sector.x(), sector.y())] = sector
                    customSectorNameMap[sector.canonicalName()] = sector
                    loadedSectorNameMap[sector.canonicalName()] = sector

                loadedSectors = self._loadMilieuSectors(
                    milieu=milieu,
                    customSectors=False)

                for sector in loadedSectors:
                    conflictSector = customSectorPosMap.get((sector.x(), sector.y()))
                    if conflictSector:
                        logging.warning(
                            f'Ignoring sector info for {sector.canonicalName()} at {sector.x()},{sector.y()} in {milieu.value} as it has the same position as custom sector {conflictSector.canonicalName()}')
                        continue

                    conflictSector = customSectorNameMap.get(sector.canonicalName())
                    if conflictSector:
                        logging.warning(
                            f'Ignoring sector info for {sector.canonicalName()} at {sector.x()},{sector.y()} in {milieu.value} as it has the same name as a custom sector at ({conflictSector.x()}, {conflictSector.y()})')
                        continue

                    logging.debug(
                        f'Loaded sector info for {sector.canonicalName()} at {sector.x()},{sector.y()} in {milieu.value}')
                    loadedSectorNameMap[sector.canonicalName()] = sector

                self._milieuMap[milieu] = loadedSectorNameMap

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
                    overlayDataFormat = int(file.read())

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
            sectors: typing.Mapping[str, SectorInfo] = self._milieuMap.get(milieu, {})
            sectorListData = []
            for sectorInfo in sectors.values():
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
