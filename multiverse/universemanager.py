import datetime
import logging
import multiverse
import os
import threading
import typing
import uuid

# TODO: When updating snapshot I'll need to do something to make sure notes
# are preserved on systems/sectors. I could split notes in a separate table
# but it's probably easiest to just read the existing notes and set the
# notes on the new object before writing it to the db.
# TODO: When I switch to making a copy of the entire universe for custom
# universes, I need to add an option to regenerate the trade codes for
# the entire universe based on a specified rule set. It should default to
# the current selected rules but also have the option to use the trade
# codes as they appear on Traveller Map (explain the difference in a tooltip).
# The default universe will always use the Traveller Map trade codes.
# This will replace the ability to switch between modes dynamically which
# I removed as it complicated the code for generating remarks.
# Part of this work will probably need to be converting calculateMongooseTradeCodes
# to use string trade codes rather than traveller.TradeCode as the converter
# code doesn't have access to that logic.
# Alternatively it might be the time to convert DbObjects to use enums for things.
# It would make sense if it was the same ones as the traveller/astronomer code, so
# maybe I need some kind of low level basic type namespace.
# I've left the _RegenerateTradeCodesToolTip text as it could be a basis for the
# option when I add it to the custom universe creation dialog
# TODO: For the problem of how to notify the user of non-critical errors at the
# point they import a custom sector. If I have a list of the issues, I could
# display them to the user after I've converted to DbObjects but before I write
# it to the DB


# TODO: Need to handle creation of creating a custom universe if the user had
# custom sectors in the previous version
# TODO: Top level functions should log that they were called

class UniverseManager(object):
    _RegistryFileName = 'registry.db'
    _UniversesDir = 'universes'

    _StockUniverseName = 'Traveller Map'
    _StockUniverseDescription = 'Sector data taken from Traveller Map'

    _lock = threading.RLock() # Recursive lock
    _instance = None # Singleton instance
    _initialised = False
    _multiversePath = None
    _registry = None

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
    def initialise(
            multiversePath: str
            ) -> None:
        if UniverseManager._initialised:
            raise RuntimeError('The MultiverseDb singleton has already been initialised')

        UniverseManager._multiversePath = multiversePath

        universePath = UniverseManager._universeDirPath()
        os.makedirs(universePath, exist_ok=True)

        registryPath = UniverseManager._registryDbFilePath()
        UniverseManager._registry = multiverse.UniverseRegistry(registryPath=registryPath)

        UniverseManager._initialised = True

    def universeInfos(self) -> typing.List[multiverse.UniverseInfo]:
        return UniverseManager._registry.listUniverses()

    def universeInfo(self, universeId: str) -> typing.Optional[multiverse.UniverseInfo]:
        return UniverseManager._registry.universeById(id=universeId)

    def hasStockUniverse(self) -> bool:
        return UniverseManager._registry.stockUniverse() is not None

    def stockUniverseInfo(self) -> typing.Optional[multiverse.UniverseInfo]:
        return UniverseManager._registry.stockUniverse()

    def checkStockUniverseTimestamp(
            self,
            snapshotTimestamp: datetime.datetime
            ) -> bool:
        info = UniverseManager._registry.stockUniverse()
        if not info:
            # There is no stock universe yet so the snapshot is always newer
            return True
        currentTimestamp = info.snapshotTimestamp()
        if not currentTimestamp:
            # The current stock universe has no timestamp. This shouldn't
            # happen but assume the snapshot is newer
            return True
        return snapshotTimestamp > currentTimestamp

    def updateStockUniverse(
            self,
            sectors: typing.Collection[multiverse.DbSector],
            snapshotTimestamp: datetime.datetime,
            sourceDataHashes: typing.Mapping[multiverse.DbSector, str],
            progressCallback: typing.Optional[typing.Callable[[typing.Optional[str], int, int], typing.Any]] = None
            ) -> None:
        existingInfo = UniverseManager._registry.stockUniverse()

        universeId = existingInfo.id() if existingInfo else str(uuid.uuid4())
        dbPath = UniverseManager._universeDbFilePath(id=universeId)
        database = multiverse.UniverseDb(universePath=dbPath)
        onCommit = onRollback = None
        if progressCallback:
            onCommit = lambda: progressCallback('Committing', 0, 0)
            onRollback = lambda: progressCallback('Reverting', 0, 0)

        with database.createTransaction(onCommitCallback=onCommit, onRollbackCallback=onRollback) as transaction:
            # Remove old sectors
            if existingInfo:
                database.clearSectors(transaction=transaction)

            # Add new sectors
            sectorCount = len(sectors)
            for progressCount, sector in enumerate(sectors):
                if progressCallback:
                    try:
                        progressCallback(
                            f'Writing: {sector.milieu()} - {sector.primaryName()}',
                            progressCount,
                            sectorCount)
                    except Exception as ex:
                        logging.warning('UniverseManager stock universe update progress callback threw an exception', exc_info=ex)

                database.saveSector(
                    sector=sector,
                    stockDataHash=sourceDataHashes.get(sector),
                    transaction=transaction)

            if progressCallback:
                try:
                    progressCallback(
                        'Writing: Complete!',
                        sectorCount,
                        sectorCount)
                except Exception as ex:
                    logging.warning('UniverseManager stock universe update progress callback threw an exception', exc_info=ex)

        if existingInfo:
            # The stock universe is already in the registry so just update
            # the snapshot timestamp
            UniverseManager._registry.setSnapshotTimestamp(
                timestamp=snapshotTimestamp)
        else:
            # The registry didn't contain an entry for the stock universe so
            # create one
            try:
                UniverseManager._registry.addUniverse(
                    id=universeId,
                    name=UniverseManager._StockUniverseName,
                    description=UniverseManager._StockUniverseDescription,
                    stock=True,
                    snapshotTimestamp=snapshotTimestamp)
            except Exception:
                # Tidy up by deleting the newly created universe database
                try:
                    os.remove(dbPath)
                except Exception as ex:
                    logging.error(f'UniverseManager failed to clean up stock universe file "{dbPath}"', exc_info=ex)
                raise

    # NOTE: When copyStock is true the stock database is copied as-is. This is
    # done for speed (3 seconds vs > 30 seconds when loaded then saved). The
    # downside of this is the id's of objects in the copy will be the same so
    # the app needs to handle that.
    def createCustomUniverse(
            self,
            name: str,
            description: str,
            copyStock: bool,
            sectors: typing.Optional[typing.Collection[multiverse.DbSector]] = None,
            progressCallback: typing.Optional[typing.Callable[[typing.Optional[str], int, int], typing.Any]] = None,
            universeId: typing.Optional[str] = None
            ) -> str: # Universe Id
        if UniverseManager._registry.universeByName(name=name):
            raise ValueError(f'Universe named "{name}" already exists')

        if universeId and UniverseManager._registry.universeById(id=universeId):
            raise ValueError(f'Universe with id "{id}" already exists')

        if not universeId:
            universeId = str(uuid.uuid4())
        universePath = UniverseManager._universeDbFilePath(id=universeId)
        if os.path.exists(universePath):
            raise RuntimeError(f'Universe database "{universePath}" already exists')

        if progressCallback:
            try:
                progressCallback('Creating', 0, 0)
            except Exception as ex:
                logging.warning('UniverseManager custom universe creation progress callback threw an exception', exc_info=ex)

        if copyStock:
            stockInfo = self.stockUniverseInfo()
            if not stockInfo:
                raise RuntimeError('No stock universe defined')
            stockPath = UniverseManager._universeDbFilePath(id=stockInfo.id())
            stockDatabase = multiverse.UniverseDb(universePath=stockPath)
            stockDatabase.copyTo(targetPath=universePath)

        # Always create database, even when there are no sectors, as we want it
        # to be created on disk
        universeDb = multiverse.UniverseDb(universePath=universePath)

        if sectors:
            with universeDb.createTransaction() as transaction:
                sectorCount = len(sectors)
                for progressCount, sector in enumerate(sectors):
                    if progressCallback:
                        try:
                            progressCallback(
                                f'Creating: {sector.milieu()} - {sector.primaryName()}',
                                progressCount,
                                sectorCount)
                        except Exception as ex:
                            logging.warning('UniverseManager custom universe creation progress callback threw an exception', exc_info=ex)

                    universeDb.saveSector(sector=sector, transaction=transaction)

        # Only add the universe to the registry after the database has been
        # created to avoid dangling entries if creating the database fails
        try:
            UniverseManager._registry.addUniverse(
                id=universeId,
                name=name,
                description=description,
                stock=False)
        except Exception:
            # Attempt to tidy up by deleting the universe database
            try:
                os.remove(universePath)
            except Exception as ex:
                logging.error(f'UniverseManager failed to clean up universe file "{universePath}"', exc_info=ex)
            raise

        if progressCallback:
            try:
                progressCallback('Creation: Complete!', 1, 1)
            except Exception as ex:
                logging.warning('UniverseManager custom universe creation progress callback threw an exception', exc_info=ex)

        return universeId

    def deleteCustomUniverse(self, universeId: str) -> None:
        info = UniverseManager._registry.universeById(id=universeId)
        if info is None:
            raise ValueError(f'Universe "{universeId}" doesn\'t exist')

        if info.isStock():
            raise ValueError(f'Stock universe can\'t be deleted')

        UniverseManager._registry.removeUniverse(id=universeId)

        dbPath = UniverseManager._universeDbFilePath(id=universeId)
        if os.path.isfile(dbPath):
            os.remove(dbPath)

    def setUniverseName(
            self,
            universeId: str,
            name: str) -> None:
        info = UniverseManager._registry.universeByName(name=name)
        if info:
            if info.id() == universeId:
                # There is no change in name so nothing to do
                return

            # There is already a universe with the same name
            raise ValueError(f'Universe named "{name}" already exists')

        UniverseManager._registry.setUniverseName(id=universeId, name=name)

    def setUniverseDescription(
            self,
            id: str,
            description: str
            ) -> None:
        UniverseManager._registry.setUniverseDescription(id=id, description=description)

    def sectorInfos(
            self,
            universeId: str
            ) -> typing.List[multiverse.SectorInfo]:
        universeInfo = UniverseManager._registry.universeById(id=universeId)
        if not universeInfo:
            raise ValueError(f'Unknown universe {universeId}')

        dbPath = UniverseManager._universeDbFilePath(id=universeId)
        universeDb = multiverse.UniverseDb(universePath=dbPath)

        return universeDb.listSectors()

    def stockUniverseSectorInfos(self) -> typing.List[multiverse.SectorInfo]:
        info = UniverseManager._registry.stockUniverse()
        if not info:
            raise RuntimeError('No stock universe defined')
        return self.sectorInfos(universeId=info.id())

    def sectors(
            self,
            universeId: str,
            progressCallback: typing.Optional[typing.Callable[[typing.Optional[str], int, int], typing.Any]] = None
            ) -> typing.List[multiverse.DbSector]:
        return list(self.yieldSectors(universeId=universeId, progressCallback=progressCallback))

    def yieldSectors(
            self,
            universeId: str,
            progressCallback: typing.Optional[typing.Callable[[typing.Optional[str], int, int], typing.Any]] = None
            ) -> typing.Generator[multiverse.DbSector, None, None]:
        universeInfo = UniverseManager._registry.universeById(id=universeId)
        if not universeInfo:
            raise ValueError(f'Unknown universe {universeId}')

        dbPath = UniverseManager._universeDbFilePath(id=universeId)
        universeDb = multiverse.UniverseDb(universePath=dbPath)

        with universeDb.createTransaction() as transaction:
            sectorInfos = universeDb.listSectors(transaction=transaction)
            sectorCount = len(sectorInfos)
            for progressCount, sectorInfo in enumerate(sectorInfos):
                if progressCallback:
                    try:
                        progressCallback(
                            f'Loading: {sectorInfo.milieu()} - {sectorInfo.name()}',
                            progressCount,
                            sectorCount)
                    except Exception as ex:
                        logging.warning('UniverseManager universe read progress callback threw an exception', exc_info=ex)

                try:
                    sector = universeDb.loadSector(
                        sectorId=sectorInfo.id(),
                        transaction=transaction)
                    yield sector
                except Exception as ex:
                    # Log error but continue loading
                    logging.error('UniverseManager failed to read sector {sectorId}', exc_info=ex)

            if progressCallback:
                try:
                    progressCallback(
                        f'Loading: Complete!',
                        sectorCount,
                        sectorCount)
                except Exception as ex:
                    logging.warning('UniverseManager universe read progress callback threw an exception', exc_info=ex)

    def stockUniverseSectors(
            self,
            progressCallback: typing.Optional[typing.Callable[[typing.Optional[str], int, int], typing.Any]] = None
            ) -> typing.List[multiverse.DbSector]:
        return list(self.yieldStockUniverseSectors(progressCallback=progressCallback))

    def yieldStockUniverseSectors(
            self,
            progressCallback: typing.Optional[typing.Callable[[typing.Optional[str], int, int], typing.Any]] = None
            ) -> typing.Generator[multiverse.DbSector, None, None]:
        info = UniverseManager._registry.stockUniverse()
        if not info:
            raise RuntimeError('No stock universe defined')
        return self.yieldSectors(universeId=info.id(), progressCallback=progressCallback)

    # NOTE: When copyStock is true the stock database is copied as-is. This is
    # done for speed (3 seconds vs > 30 seconds when loaded then saved). The
    # downside of this is the id's of objects in the copy will be the same so
    # the app needs to handle that.
    def _createUniverse(
            self,
            name: str,
            description: str,
            isStock: bool,
            copyStock: bool = False,
            sectors: typing.Optional[typing.Collection[multiverse.DbSector]] = None,
            snapshotTimestamp: typing.Optional[datetime.datetime] = None
            ) -> str:
        if UniverseManager._registry.universeByName(name=name):
            raise ValueError(f'Universe named "{name}" already exists')

        universeId = str(uuid.uuid4())
        universePath = UniverseManager._universeDbFilePath(id=universeId)
        if os.path.exists(universePath):
            raise RuntimeError(f'Universe database "{universePath}" already exists')

        if copyStock:
            if isStock:
                raise ValueError('Can\'t copy stock database to stock database')
            stockInfo = self.stockUniverseInfo()
            if not stockInfo:
                raise RuntimeError('No stock universe defined')
            stockPath = UniverseManager._universeDbFilePath(id=stockInfo.id())
            stockDatabase = multiverse.UniverseDb(universePath=stockPath)
            stockDatabase.copyTo(targetPath=universePath)

        # Always create database, even when there are no sectors, as we want it
        # to be created on disk
        universeDb = multiverse.UniverseDb(universePath=universePath)

        if sectors:
            with universeDb.createTransaction() as transaction:
                for sector in sectors:
                    universeDb.saveSector(sector=sector, transaction=transaction)

        # Only add the universe to the registry after the database has been
        # created to avoid dangling entries if creating the database fails
        try:
            UniverseManager._registry.addUniverse(
                id=universeId,
                name=name,
                description=description,
                stock=isStock,
                snapshotTimestamp=snapshotTimestamp)
        except Exception:
            try:
                os.remove(universePath)
            except Exception as ex:
                logging.error(f'UniverseManager failed to clean up universe file "{universePath}"', exc_info=ex)

            raise

        return universeId

    @staticmethod
    def _registryDbFilePath() -> str:
        return os.path.join(
            UniverseManager._multiversePath,
            UniverseManager._RegistryFileName)

    @staticmethod
    def _universeDirPath() -> str:
        return os.path.join(
            UniverseManager._multiversePath,
            UniverseManager._UniversesDir)

    @staticmethod
    def _universeDbFilePath(id: str) -> str:
        return os.path.join(
            UniverseManager._universeDirPath(),
            f'{id}.db')