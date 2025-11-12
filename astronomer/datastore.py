import astronomer
import common
import datetime
import enum
import json
import logging
import multiverse
import os
import threading
import typing
import xmlschema
import xml.etree.ElementTree

# TODO: By the end of this I should be able to remove this file as
# everything will have been moved to either the snapshot manager or
# database

class SectorInfo(object):
    def __init__(
            self,
            canonicalName: typing.Iterable[str],
            abbreviation: typing.Optional[str],
            x: int,
            y: int,
            sectorFormat: multiverse.SectorFormat,
            metadataFormat: multiverse.MetadataFormat,
            modifiedTimestamp: datetime.datetime,
            isCustomSector: bool
            ) -> None:
        self._canonicalName = canonicalName
        self._abbreviation = abbreviation
        self._x = x
        self._y = y
        self._sectorFormat = sectorFormat
        self._metadataFormat = metadataFormat
        self._modifiedTimestamp = modifiedTimestamp
        self._isCustomSector = isCustomSector

    def canonicalName(self) -> str:
        return self._canonicalName

    def abbreviation(self) -> str:
        return self._abbreviation

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def sectorFormat(self) -> multiverse.SectorFormat:
        return self._sectorFormat

    def metadataFormat(self) -> multiverse.MetadataFormat:
        return self._metadataFormat

    def modifiedTimestamp(self) -> datetime.datetime:
        return self._modifiedTimestamp

    def isCustomSector(self) -> bool:
        return self._isCustomSector

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
        # is a safety net to avoid leaving the maps in an inconsistent state if something
        # unexpected happens
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
            milieu: astronomer.Milieu
            ) -> None:
        self._milieu = milieu
        self._stockSectorMap = SectorLookupMaps()
        self._customSectorMap = SectorLookupMaps()
        self._mergedSectorMap = SectorLookupMaps()

    def milieu(self) -> astronomer.Milieu:
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
    _TimestampFileName = 'timestamp.txt'
    _SectorMetadataXsdFileName = 'sectors.xsd'
    _TimestampFormat = '%Y-%m-%d %H:%M:%S.%f'

    _SectorFormatExtensions = {
        # NOTE: The sec format is short for second survey, not the legacy sec format
        multiverse.SectorFormat.T5Column: 'sec',
        multiverse.SectorFormat.T5Tab: 'tab'}
    _MetadataFormatExtensions = {
        multiverse.MetadataFormat.JSON: 'json',
        multiverse.MetadataFormat.XML: 'xml'}

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

    def sectors(
            self,
            milieu: astronomer.Milieu,
            stockOnly: bool = False
            ) -> typing.Iterable[SectorInfo]:
        self._loadSectors(milieu=milieu)
        with self._lock:
            universeInfo = self._universeMap[milieu]
            if not universeInfo:
                return []
            return universeInfo.sectors(stockOnly=stockOnly)

    def sector(
            self,
            sectorName: str,
            milieu: astronomer.Milieu,
            stockOnly: bool = False
            ) -> typing.Optional[SectorInfo]:
        self._loadSectors(milieu=milieu)
        with self._lock:
            universeInfo = self._universeMap[milieu]
            if not universeInfo:
                return None
            return universeInfo.lookupName(
                name=sectorName,
                stockOnly=stockOnly)

    # This will throw a SectorConflictException if there is a conflict
    # TODO: I need to check to see if there are any conflict checks from
    # customSectorConflictCheck that I need to replicate in the database.
    # One example might be the current name conflict that prevents multiple
    # sectors with the same name. This isn't a restriction on the database
    # but not enforcing it would mean it would be difficult to implement
    # exporting the database to a snapshot (if I ever wanted to do it) as
    # there could be filesystem name conflicts
    def customSectorConflictCheck(
            self,
            sectorName: str,
            sectorX: int,
            sectorY: int,
            milieu: astronomer.Milieu
            ) -> None:
        self._loadSectors(milieu=milieu)

        with self._lock:
            universeInfo = self._universeMap[milieu]
            return universeInfo.conflictCheck(
                sectorName=sectorName,
                sectorX=sectorX,
                sectorY=sectorY,
                isCustomSector=True)

    def createCustomSector(
            self,
            milieu: astronomer.Milieu,
            sectorContent: str,
            metadataContent: str
            ) -> SectorInfo:
        self._loadSectors(milieu=milieu)

        sectorFormat = multiverse.sectorFileFormatDetect(content=sectorContent)
        if not sectorFormat:
            raise RuntimeError('Sector file content has an unknown format')

        metadataFormat = multiverse.metadataFileFormatDetect(content=metadataContent)
        if not metadataFormat:
            raise RuntimeError('Sector metadata content has an unknown format')

        metadata = multiverse.readMetadata(
            content=metadataContent,
            format=metadataFormat,
            identifier='Custom Metadata')

        # Do a full parse of the custom sector data based on the detected file
        # format. If it fails an exception will be raised and allowed to pass
        # back to the called. Doing this check is important as it prevents bad
        # data causing the app to barf when loading
        multiverse.readSector(
            content=sectorContent,
            format=sectorFormat,
            identifier=f'Custom Sector {metadata.canonicalName()}')

        milieuDirPath = os.path.join(
            self._customDir,
            DataStore._MilieuBaseDir,
            milieu.value)
        os.makedirs(milieuDirPath, exist_ok=True)

        with self._lock:
            universeInfo = self._universeMap[milieu]

            # This will throw if the custom sector has a name/position conflicts with an existing sector.
            # It's done now to prevent files being updated if the sector isn't going to be addable
            universeInfo.conflictCheck(
                sectorName=metadata.canonicalName(),
                sectorX=metadata.x(),
                sectorY=metadata.y(),
                isCustomSector=True)

            escapedSectorName = common.encodeFileName(rawFileName=metadata.canonicalName())

            sectorExtension = DataStore._SectorFormatExtensions[sectorFormat]
            sectorFilePath = os.path.join(milieuDirPath, f'{escapedSectorName}.{sectorExtension}')
            DataStore._writeFile(
                path=sectorFilePath,
                data=sectorContent)

            metadataExtension = DataStore._MetadataFormatExtensions[metadataFormat]
            metadataFilePath = os.path.join(milieuDirPath, f'{escapedSectorName}.{metadataExtension}')
            DataStore._writeFile(
                path=metadataFilePath,
                data=metadataContent)

            sectorInfo = SectorInfo(
                canonicalName=metadata.canonicalName(),
                abbreviation=metadata.abbreviation(),
                x=metadata.x(),
                y=metadata.y(),
                sectorFormat=sectorFormat,
                metadataFormat=metadataFormat,
                modifiedTimestamp=common.utcnow(),
                isCustomSector=True)
            universeInfo.addSector(sectorInfo)

            self._saveCustomSectors(milieu=milieu)

            return sectorInfo

    def deleteCustomSector(
            self,
            sectorName: str,
            milieu: astronomer.Milieu
            ) -> None:
        self._loadSectors(milieu=milieu)

        milieuDirPath = os.path.join(
            self._customDir,
            DataStore._MilieuBaseDir,
            milieu.value)

        with self._lock:
            universeInfo = self._universeMap[milieu]
            sectorInfo = universeInfo.lookupName(name=sectorName, stockOnly=False)
            if not sectorInfo:
                raise RuntimeError(
                    'Failed to delete custom sector {name} from {milieu} as it doesn\'t exist'.format(
                        name=sectorName,
                        milieu=milieu.value))

            # Remove the sector from the custom universe file first. That way we don't leave a partially
            # populated sector if deleting a file fails
            universeInfo.removeSector(sectorInfo)
            self._saveCustomSectors(milieu=milieu)

            escapedSectorName = common.encodeFileName(rawFileName=sectorInfo.canonicalName())
            sectorExtension = DataStore._SectorFormatExtensions[sectorInfo.sectorFormat()]
            metadataExtension = DataStore._MetadataFormatExtensions[sectorInfo.metadataFormat()]
            files = [
                f'{escapedSectorName}.{sectorExtension}',
                f'{escapedSectorName}.{metadataExtension}']

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
            milieu: typing.Optional[astronomer.Milieu] = None,
            reload: bool = False
            ) -> None:
        with self._lock:
            if (not reload) and self._universeMap and ((not milieu) or self._universeMap.get(milieu)):
                return # Already loaded

            if not self._universeMap:
                self._universeMap: typing.Dict[astronomer.Milieu, UniverseInfo] = {}

            milieuList = [milieu] if milieu else astronomer.Milieu
            for milieu in milieuList:
                logging.debug('{operation} sector info for {milieu}'.format(
                    operation='Reloading' if reload else 'Loading',
                    milieu=milieu.value))

                universeInfo = self._universeMap.get(milieu)
                if universeInfo:
                    universeInfo.clear()
                else:
                    universeInfo = UniverseInfo(milieu=milieu)
                    self._universeMap[milieu] = universeInfo

                loadedSectors = self._loadMilieuSectors(
                    milieu=milieu,
                    customSectors=True)
                for sector in loadedSectors:
                    logging.debug(
                        f'Loaded custom sector info for {sector.canonicalName()} at {sector.x()},{sector.y()} in {milieu.value}')
                    try:
                        universeInfo.addSector(sector)
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
                        universeInfo.addSector(sector)
                    except SectorConflictException as ex:
                        logging.error(
                            f'Failed to add stock sector {sector.canonicalName()} at {sector.x()},{sector.y()} to universe for {milieu.value} ({ex})')
                    except Exception as ex:
                        logging.error(
                            f'Failed to add stock sector {sector.canonicalName()} at {sector.x()},{sector.y()} to universe for {milieu.value}', exc_info=ex)

    def _readStockFile(
            self,
            relativeFilePath: str
            ) -> bytes:
        # If the overlay directory exists load files from there, if not load from the
        # install directory. This approach allows for files to be deleted (or renamed
        # in an overlay (compared to checking if the file exists in the overlay
        # directory and loading it from the install dir if it doesn't). This is important
        # as sectors can be renamed/deleted
        filePath = os.path.join(
            self._overlayDir if os.path.isdir(self._overlayDir) else self._installDir,
            relativeFilePath)
        return DataStore._readFile(path=filePath)

    def _readMilieuFile(
            self,
            fileName: str,
            milieu: astronomer.Milieu,
            useCustomMapDir: bool
            ) -> bytes:
        relativePath = os.path.join(self._MilieuBaseDir, milieu.value, fileName)
        if useCustomMapDir:
            absolutePath = os.path.join(self._customDir, relativePath)
            return DataStore._readFile(path=absolutePath)

        return self._readStockFile(relativeFilePath=relativePath)

    # TODO: Some part of this code will need to live on as the code
    # that ends up importing the custom sectors into the database
    # will need to handle the custom elements I added (e.g. SectorFormat)
    # in order to load the custom sectors (unless I can figure out a way
    # round it)
    # - Sector files are the problem as I don't have a way to detect format
    # for parsing. Metadata files should be ok as I have code for detecting
    # the format there.
    def _loadMilieuSectors(
            self,
            milieu: astronomer.Milieu,
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
                sectorFormat = multiverse.SectorFormat.T5Column
                if sectorFormatTag != None:
                    sectorFormat = multiverse.SectorFormat.__members__.get(
                        str(sectorFormatTag),
                        sectorFormat)

                # If the universe doesn't specify the metadata format it must be a standard traveller map
                # universe file which means the corresponding metadata files all use XML format
                metadataFormatTag = sectorElement.get('MetadataFormat')
                metadataFormat = multiverse.MetadataFormat.XML
                if metadataFormatTag != None:
                    metadataFormat = multiverse.MetadataFormat.__members__.get(
                        str(metadataFormatTag),
                        metadataFormat)

                # If the universe doesn't specify the modified timestamp assume the epoch
                # NOTE: For now the modified time is only used for custom sectors. I've added it like this
                # to make it easier if I want to update the github action that creates the snapshots so that
                # it tracks the modified time of each individual sector and adds it to the universe file.
                modifiedTimestampTag = sectorElement.get('ModifiedTimestamp')
                if modifiedTimestampTag != None:
                    modifiedTimestamp = DataStore._parseTimestamp(str(modifiedTimestampTag).encode())
                else:
                    modifiedTimestamp = datetime.datetime.fromtimestamp(0)

                sectors.append(SectorInfo(
                    canonicalName=canonicalName,
                    abbreviation=abbreviation,
                    x=sectorX,
                    y=sectorY,
                    sectorFormat=sectorFormat,
                    metadataFormat=metadataFormat,
                    modifiedTimestamp=modifiedTimestamp,
                    isCustomSector=customSectors))
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
            milieu: astronomer.Milieu
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
            universeInfo = self._universeMap[milieu]
            sectorListData = []
            for sectorInfo in universeInfo.sectors(stockOnly=False):
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
                sectorData['ModifiedTimestamp'] = \
                    DataStore._formatTimestamp(sectorInfo.modifiedTimestamp()).decode()

                sectorListData.append(sectorData)

            universeData = {'Sectors': sectorListData}

            DataStore._writeFile(
                path=universeFilePath,
                data=json.dumps(universeData, indent=4))

            utcTime = common.utcnow()
            DataStore._writeFile(
                path=timestampPath,
                data=DataStore._formatTimestamp(timestamp=utcTime))

    @staticmethod
    def _readFile(path: str) -> bytes:
        with open(path, 'rb') as file:
            return file.read()

    @staticmethod
    def _writeFile(
            path: str,
            data: typing.Union[bytes, str]
            ) -> None:
        if not isinstance(data, bytes):
            data = data.encode()

        with open(path, 'wb') as file:
            file.write(data)

    @staticmethod
    def _bytesToString(bytes: bytes) -> str:
        return bytes.decode('utf-8-sig') # Use utf-8-sig to strip BOM from unicode files

    @staticmethod
    def _parseTimestamp(data: bytes) -> datetime.datetime:
        timestamp = datetime.datetime.strptime(
            DataStore._bytesToString(data),
            DataStore._TimestampFormat)
        return timestamp.replace(tzinfo=datetime.timezone.utc)

    @staticmethod
    def _formatTimestamp(timestamp: datetime.datetime) -> bytes:
        timestamp = timestamp.astimezone(datetime.timezone.utc)
        return timestamp.strftime(DataStore._TimestampFormat).encode()
