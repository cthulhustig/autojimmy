import common
import database
import datetime
import logging
import multiverse
import os
import sqlite3
import threading
import typing

# TODO: Need to handle updating db after snapshot update
# TODO: When updating snapshot I'll need to do something to make sure notes
# are preserved on systems/sectors. I could split notes in a separate table
# but it's probably easiest to just read the existing notes and set the
# notes on the new object before writing it to the db.
# TODO: Do I need to add any kind of thread locking to public methods? I'm
# not sure I do with the current implementation as I believe the sqlite
# db is thread saf and I'm not maintaining an internal state. If I add
# connection pooling I suspect I'll need something to protect the pool

class DbUniverseInfo(object):
    def __init__(
            self,
            universeId: str,
            name: str
            ) -> None:
        self._universeId = universeId
        self._name = name

        self._hash = None

    def id(self) -> str:
        return self._universeId

    def name(self) -> str:
        return self._name

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, DbUniverseInfo):
            return NotImplemented
        return self._universeId == other._universeId and self._name == other._name

    def __hash__(self) -> int:
        if self._hash is None:
            self._hash = hash((self._universeId, self._name))
        return self._hash

class DbSectorInfo(object):
    def __init__(
            self,
            id: str,
            name: str,
            sectorX: int,
            sectorY: int,
            isCustom: bool,
            abbreviation: typing.Optional[str]
            ) -> None:
        self._id = id
        self._name = name
        self._sectorX = sectorX
        self._sectorY = sectorY
        self._isCustom = isCustom
        self._abbreviation = abbreviation

        self._hash = None

    def id(self) -> str:
        return self._id

    def name(self) -> str:
        return self._name

    def sectorX(self) -> int:
        return self._sectorX

    def sectorY(self) -> int:
        return self._sectorY

    def isCustom(self) -> bool:
        return self._isCustom

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, DbSectorInfo):
            return NotImplemented
        return self._id == other._id and self._name == other._name and \
            self._sectorX == other._sectorX and self._sectorY == other._sectorY and \
            self._isCustom == self._isCustom and self._abbreviation == other._abbreviation

    def __hash__(self) -> int:
        if self._hash is None:
            self._hash = hash((self._id, self._name, self._sectorX, self._sectorY,
                               self._isCustom, self._abbreviation))
        return self._hash

class MultiverseDb(object):
    class Transaction(object):
        def __init__(
                self,
                connection: sqlite3.Connection
                ) -> None:
            self._connection = connection
            self._hasBegun = False

        def connection(self) -> sqlite3.Connection:
            return self._connection

        def begin(self) -> 'MultiverseDb.Transaction':
            if self._hasBegun:
                raise RuntimeError('Invalid state to begin transaction')

            cursor = self._connection.cursor()
            try:
                cursor.execute('BEGIN;')
                self._hasBegun = True
            except:
                self._teardown()
                raise

            return self

        def end(self) -> None:
            if not self._hasBegun:
                raise RuntimeError('Invalid state to end transaction')

            cursor = self._connection.cursor()
            try:
                cursor.execute('END;')
            finally:
                self._teardown()

        def rollback(self) -> None:
            if not self._hasBegun:
                raise RuntimeError('Invalid state to roll back transaction')

            cursor = self._connection.cursor()
            try:
                cursor.execute('ROLLBACK;')
            finally:
                self._teardown()

        def __enter__(self) -> 'MultiverseDb.Transaction':
            return self.begin()

        def __exit__(self, exc_type, exc_val, exc_tb) -> None:
            if exc_type is None:
                self.end()
            else:
                self.rollback()

        def __del__(self) -> None:
            if self._hasBegun:
                # A transaction is in progress so roll it back
                self.rollback()

        def _teardown(self) -> None:
            if self._connection:
                self._connection.close()
            self._connection = None
            self._hasBegun = False

    _PragmaScript = """
        PRAGMA foreign_keys = ON;
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;
        PRAGMA cache_size = -200000;
        """

    _TableSchemaTableName = 'table_schemas'

    _MetadataTableName = 'metadata'
    _MetadataTableSchema = 1

    _UniversesTableName = 'universes'
    _UniversesTableSchema = 1

    _SectorsTableName = 'sectors'
    _SectorsTableSchema = 1

    _AlternateNamesTableName = 'alternate_names'
    _AlternateNamesTableSchema = 1

    _SubsectorNamesTableName = 'subsector_names'
    _SubsectorNamesTableSchema = 1

    _AllegiancesTableName = 'allegiances'
    _AllegiancesTableSchema = 1

    _ProductsTableName = 'products'
    _ProductsTableSchema = 1

    _RoutesTableName = 'routes'
    _RoutesTableSchema = 1

    _BordersTableName = 'borders'
    _BordersTableSchema = 1

    _BorderHexesTableName = 'border_hexes'
    _BorderHexesTableSchema = 1

    _RegionsTableName = 'regions'
    _RegionsTableSchema = 1

    _RegionHexesTableName = 'region_hexes'
    _RegionHexesTableSchema = 1

    _LabelsTableName = 'labels'
    _LabelsTableSchema = 1

    _SystemsTableName = 'systems'
    _SystemsTableSchema = 1

    _DefaultUniverseId = 'default'
    _DefaultUniverseTimestampKey = 'default_universe_timestamp'

    _TimestampFormat = '%Y-%m-%d %H:%M:%S.%f'

    _lock = threading.RLock() # Recursive lock
    _instance = None # Singleton instance
    _databasePath = None

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
                    cls._instance._initTables()
        return cls._instance

    @staticmethod
    def setDbPath(databasePath: str) -> None:
        if MultiverseDb._instance:
            raise RuntimeError('You can\'t set the database path after the singleton has been initialised')
        MultiverseDb._databasePath = databasePath

    def createTransaction(self) -> Transaction:
        connection = self._createConnection()
        return MultiverseDb.Transaction(connection=connection)

    def hasDefaultUniverse(self) -> bool:
        try:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._getMetadata(
                    key=MultiverseDb._DefaultUniverseTimestampKey,
                    cursor=connection.cursor()) is not None
        except Exception as ex:
            logging.debug('MultiverseDb failed to query default universe timestamp', exc_info=ex)
            return False

    # This returns true if the universe snapshot in the specified directory is
    # newer than the default universe currently in the database (or if there is
    # no default universe in the database)
    def isDefaultUniverseSnapshotNewer(
            self,
            directoryPath: str
            ) -> bool:
        with self.createTransaction() as transaction:
            connection = transaction.connection()

            timestampPath = os.path.join(directoryPath, 'timestamp.txt')
            with open(timestampPath, 'r', encoding='utf-8-sig') as file:
                timestampContent = file.read()
            importTimestamp = MultiverseDb._parseTimestamp(content=timestampContent)

            currentTimestamp = self._getMetadata(
                key=MultiverseDb._DefaultUniverseTimestampKey,
                cursor=connection.cursor())
            if not currentTimestamp:
                # No timestamp means there is no default universe so the supplied
                # universe is "newer"
                return True

            try:
                currentTimestamp = datetime.datetime.fromisoformat(currentTimestamp)
            except Exception as ex:
                logging.warning(
                    f'MultiverseDb failed to parse default universe timestamp "{currentTimestamp}"',
                    exc_info=ex)
                return True

            return importTimestamp > currentTimestamp

    def importDefaultUniverse(
            self,
            directoryPath: str,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        logging.info(f'MultiverseDb importing default universe from "{directoryPath}"')
        with self.createTransaction() as transaction:
            connection = transaction.connection()
            self._internalImportDefaultUniverse(
                directoryPath=directoryPath,
                cursor=connection.cursor(),
                progressCallback=progressCallback)

        # Vacuum the database to stop it getting out of control. This MUST be
        # done outside the transaction
        # TODO: Do I really want to do this here?
        self.vacuumDatabase()

    def saveUniverse(
            self,
            universe: multiverse.DbUniverse,
            transaction: typing.Optional['MultiverseDb.Transaction'] = None,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        logging.debug(f'MultiverseDb saving universe {universe.id()}')

        if universe.id() == MultiverseDb._DefaultUniverseId:
            raise RuntimeError('Saving the default universe is not allowed')

        insertProgressCallback = None
        if progressCallback:
            insertProgressCallback = lambda name, milieu, progress, total: progressCallback(f'Saving: {milieu} - {name}' if progress != total else 'Saving: Complete!', progress, total)

        if transaction != None:
            connection = transaction.connection()

            self._internalDeleteUniverse(
                universeId=universe.id(),
                cursor=connection.cursor())

            self._internalInsertUniverse(
                universe=universe,
                cursor=connection.cursor(),
                progressCallback=insertProgressCallback)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()

                self._internalDeleteUniverse(
                    universeId=universe.id(),
                    cursor=connection.cursor())

                self._internalInsertUniverse(
                    universe=universe,
                    cursor=connection.cursor(),
                    progressCallback=insertProgressCallback)

    def loadUniverse(
            self,
            universeId: str,
            includeDefaultSectors: bool = True,
            transaction: typing.Optional['MultiverseDb.Transaction'] = None,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> typing.Optional[multiverse.DbUniverse]:
        logging.debug(f'MultiverseDb loading universe {universeId}')

        readProgressCallback = None
        if progressCallback:
            readProgressCallback = lambda name, milieu, progress, total: progressCallback(f'Loading: {milieu} - {name}' if progress != total else 'Loading: Complete!', progress, total)

        if transaction != None:
            connection = transaction.connection()
            return self._internalReadUniverse(
                universeId=universeId,
                includeDefaultSectors=includeDefaultSectors,
                cursor=connection.cursor(),
                progressCallback=readProgressCallback)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._internalReadUniverse(
                    universeId=universeId,
                    includeDefaultSectors=includeDefaultSectors,
                    cursor=connection.cursor(),
                    progressCallback=readProgressCallback)

    def deleteUniverse(
            self,
            universeId: str,
            transaction: typing.Optional['MultiverseDb.Transaction'] = None
            ) -> None:
        logging.debug(f'MultiverseDb deleting universe {universeId}')

        if universeId == MultiverseDb._DefaultUniverseId:
            raise RuntimeError('Deleting the default universe is not allowed')

        if transaction != None:
            connection = transaction.connection()
            self._internalDeleteUniverse(
                universeId=universeId,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._internalDeleteUniverse(
                    universeId=universeId,
                    cursor=connection.cursor())

    def saveSector(
            self,
            sector: multiverse.DbSector,
            transaction: typing.Optional['MultiverseDb.Transaction'] = None
            ) -> None:
        logging.debug(f'MultiverseDb saving sector {sector.id()}')

        if not sector.id():
            raise RuntimeError('Sector cannot be saved as has no id')

        if not sector.universeId():
            raise RuntimeError('Sector cannot be saved as has no universe id')

        if sector.universeId() == MultiverseDb._DefaultUniverseId:
            raise RuntimeError('Saving default sectors is not allowed')

        if not sector.isCustom():
            raise RuntimeError('Saving non-custom sectors is not allowed')

        if transaction != None:
            connection = transaction.connection()
            # Delete any old version of the sector and any sector that has at the
            # same time and place as the new sector
            self._internalDeleteSector(
                sectorId=sector.id(),
                milieu=sector.milieu(),
                sectorX=sector.sectorX(),
                sectorY=sector.sectorY(),
                cursor=connection.cursor())
            self._internalInsertSector(
                sector=sector,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                # Delete any old version of the sector and any sector that has at the
                # same time and place as the new sector
                self._internalDeleteSector(
                    sectorId=sector.id(),
                    milieu=sector.milieu(),
                    sectorX=sector.sectorX(),
                    sectorY=sector.sectorY(),
                    cursor=connection.cursor())
                self._internalInsertSector(
                    sector=sector,
                    cursor=connection.cursor())

    def loadSector(
            self,
            sectorId: str,
            transaction: typing.Optional['MultiverseDb.Transaction'] = None
            ) -> typing.Optional[multiverse.DbSector]:
        logging.debug(f'MultiverseDb reading sector {sectorId}')
        if transaction != None:
            connection = transaction.connection()
            return self._internalReadSector(
                sectorId=sectorId,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._internalReadSector(
                    sectorId=sectorId,
                    cursor=connection.cursor())

    def deleteSector(
            self,
            sectorId: str,
            transaction: typing.Optional['MultiverseDb.Transaction'] = None
            ) -> None:
        logging.debug(f'MultiverseDb deleting sector {sectorId}')

        if transaction != None:
            connection = transaction.connection()

            sectorInfo = self._internalSectorInfoById(
                sectorId=sectorId,
                cursor=connection.cursor())
            if not sectorInfo:
                return # Nothing to delete
            if not sectorInfo.isCustom():
                raise RuntimeError('Deleting default sectors is not allowed')

            self._internalDeleteSector(
                sectorId=sectorId,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()

                sectorInfo = self._internalSectorInfoById(
                    sectorId=sectorId,
                    cursor=connection.cursor())
                if not sectorInfo:
                    return # Nothing to delete
                if not sectorInfo.isCustom():
                    raise RuntimeError('Deleting default sectors is not allowed')

                self._internalDeleteSector(
                    sectorId=sectorId,
                    cursor=connection.cursor())

    def listUniverseInfo(
            self,
            transaction: typing.Optional['MultiverseDb.Transaction'] = None
            ) -> typing.List[DbUniverseInfo]:
        logging.debug(f'MultiverseDb listing universe info')
        if transaction != None:
            connection = transaction.connection()
            return self._internalListUniverseInfo(
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._internalListUniverseInfo(
                    cursor=connection.cursor())

    def universeInfoById(
            self,
            universeId: str,
            transaction: typing.Optional['MultiverseDb.Transaction'] = None
            ) -> typing.Optional[DbUniverseInfo]:
        logging.debug(
            f'MultiverseDb retrieving info for sector with id "{universeId}"')
        if transaction != None:
            connection = transaction.connection()
            return self._internalUniverseInfoById(
                universeId=universeId,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._internalUniverseInfoById(
                    universeId=universeId,
                    cursor=connection.cursor())

    def universeInfoByName(
            self,
            name: str,
            transaction: typing.Optional['MultiverseDb.Transaction'] = None
            ) -> typing.Optional[DbUniverseInfo]:
        logging.debug(
            f'MultiverseDb retrieving info for sector with name "{name}"')
        if transaction != None:
            connection = transaction.connection()
            return self._internalUniverseInfoByName(
                name=name,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._internalUniverseInfoByName(
                    name=name,
                    cursor=connection.cursor())

    def listSectorInfo(
            self,
            universeId: str,
            milieu: typing.Optional[str] = None,
            includeDefaultSectors: bool = True,
            transaction: typing.Optional['MultiverseDb.Transaction'] = None
            ) -> typing.List[DbSectorInfo]:
        logging.debug(
            'MultiverseDb listing sector info' + ('' if universeId is None else f' for universe {universeId}'))
        if transaction != None:
            connection = transaction.connection()
            return self._internalListSectorInfo(
                universeId=universeId,
                milieu=milieu,
                includeDefaultSectors=includeDefaultSectors,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._internalListSectorInfo(
                    universeId=universeId,
                    milieu=milieu,
                    includeDefaultSectors=includeDefaultSectors,
                    cursor=connection.cursor())

    def sectorInfoByPosition(
            self,
            universeId: str,
            milieu: str,
            sectorX: int,
            sectorY: int,
            transaction: typing.Optional['MultiverseDb.Transaction'] = None
            ) -> typing.Optional[DbSectorInfo]:
        logging.debug(
            f'MultiverseDb retrieving info for sector at ({sectorX}, {sectorY}) for universe {universeId} from {milieu}')
        if transaction != None:
            connection = transaction.connection()
            return self._internalSectorInfoByPosition(
                universeId=universeId,
                milieu=milieu,
                sectorX=sectorX,
                sectorY=sectorY,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._internalSectorInfoByPosition(
                    universeId=universeId,
                    milieu=milieu,
                    sectorX=sectorX,
                    sectorY=sectorY,
                    cursor=connection.cursor())

    def vacuumDatabase(self) -> None:
        logging.debug('MultiverseDb vacuuming database')

        # NOTE: VACUUM can't be performed inside a transaction
        connection = self._createConnection()
        try:
            cursor = connection.cursor()
            cursor.execute('VACUUM;')
        finally:
            connection.close()

    def _createConnection(self) -> sqlite3.Connection:
        # TODO: Connection pool like ObjectDb????

        connection = sqlite3.connect(self._databasePath)
        logging.debug(f'ObjectDbManager created new connection {connection} to \'{self._databasePath}\'')
        connection.executescript(MultiverseDb._PragmaScript)
        # Uncomment this to have sqlite print the SQL that it executes
        #connection.set_trace_callback(print)
        return connection

    def _initTables(self) -> None:
        connection = None
        cursor = None
        try:
            connection = self._createConnection()
            cursor = connection.cursor()
            cursor.execute('BEGIN;')

            # Create table schema table
            if not database.checkIfTableExists(
                    tableName=MultiverseDb._TableSchemaTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {table} (
                        name TEXT PRIMARY KEY NOT NULL,
                        version INTEGER NOT NULL
                    );
                    """.format(table=MultiverseDb._TableSchemaTableName)
                logging.info(f'MultiverseDb creating \'{MultiverseDb._TableSchemaTableName}\' table')
                cursor.execute(sql)

            # Create metadata table
            if not database.checkIfTableExists(
                    tableName=MultiverseDb._MetadataTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {table} (
                        key TEXT PRIMARY KEY NOT NULL,
                        value TEXT
                    );
                    """.format(table=MultiverseDb._MetadataTableName)
                logging.info(f'MultiverseDb creating \'{MultiverseDb._MetadataTableName}\' table')
                cursor.execute(sql)

            # Create universe table
            if not database.checkIfTableExists(
                    tableName=MultiverseDb._UniversesTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {table} (
                        id TEXT PRIMARY KEY NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        notes TEXT,
                        UNIQUE (name)
                    );
                    """.format(table=MultiverseDb._UniversesTableName)
                logging.info(f'MultiverseDb creating \'{MultiverseDb._UniversesTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MultiverseDb._UniversesTableName,
                    version=MultiverseDb._UniversesTableSchema,
                    cursor=cursor)

                # Create schema table indexes for id column. The id index is
                # needed as, even though it's the primary key, it's of type
                # TEXT so doesn't automatically get indexes
                self._createColumnIndex(
                    table=MultiverseDb._UniversesTableName,
                    column='id',
                    unique=True,
                    cursor=cursor)

            # Create sectors table
            if not database.checkIfTableExists(
                    tableName=MultiverseDb._SectorsTableName,
                    cursor=cursor):
                # TODO: I probably want to store the milieu as the integer year but I'll need
                # something to support named milieu (e.g. IW for Interstellar War). It probably
                # means a separate milieu description table that stores per universe year to
                # name mapping
                # TODO: The is_custom column is technically redundant as the information can
                # be implied by the universe id. I should probably remove it but it's currently
                # making some queries a little easier
                sql = """
                    CREATE TABLE IF NOT EXISTS {sectorsTable} (
                        id TEXT PRIMARY KEY NOT NULL,
                        universe_id TEXT,
                        is_custom INTEGER NOT NULL,
                        milieu TEXT NOT NULL,
                        sector_x INTEGER NOT NULL,
                        sector_y INTEGER NOT NULL,
                        primary_name TEXT NOT NULL,
                        primary_language TEXT,
                        abbreviation TEXT,
                        sector_label TEXT,
                        selected INTEGER NOT NULL,
                        tags TEXT,
                        style_sheet TEXT,
                        credits TEXT,
                        publication TEXT,
                        author TEXT,
                        publisher TEXT,
                        reference TEXT,
                        notes TEXT,
                        FOREIGN KEY(universe_id) REFERENCES {universesTable}(id) ON DELETE CASCADE,
                        UNIQUE (universe_id, milieu, sector_x, sector_y)
                    );
                    """.format(
                        sectorsTable=MultiverseDb._SectorsTableName,
                        universesTable=MultiverseDb._UniversesTableName)
                logging.info(f'MultiverseDb creating \'{MultiverseDb._SectorsTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MultiverseDb._SectorsTableName,
                    version=MultiverseDb._SectorsTableSchema,
                    cursor=cursor)

                # Create indexes for id column. The id index is needed as, even
                # though it's the primary key, it's of type TEXT so doesn't
                # automatically get indexes
                self._createColumnIndex(
                    table=MultiverseDb._SectorsTableName,
                    column='id',
                    unique=True,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MultiverseDb._SectorsTableName,
                    column='universe_id',
                    unique=False,
                    cursor=cursor)

                # Create index on universe id and sector position. This is used
                # to speed up the queries when determining which default sectors
                # should be used. The index is unique as each universe should
                # only ever have one sector at a location for a given milieu
                self._createMultiColumnIndex(
                    table=MultiverseDb._SectorsTableName,
                    columns=['universe_id', 'milieu', 'sector_x', 'sector_y'],
                    unique=True,
                    cursor=cursor)

            # Create sector alternate names table
            if not database.checkIfTableExists(
                    tableName=MultiverseDb._AlternateNamesTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {namesTable} (
                        sector_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        language TEXT,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        namesTable=MultiverseDb._AlternateNamesTableName,
                        sectorsTable=MultiverseDb._SectorsTableName)
                logging.info(f'MultiverseDb creating \'{MultiverseDb._AlternateNamesTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MultiverseDb._AlternateNamesTableName,
                    version=MultiverseDb._AlternateNamesTableSchema,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MultiverseDb._AlternateNamesTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create subsector names table
            if not database.checkIfTableExists(
                    tableName=MultiverseDb._SubsectorNamesTableName,
                    cursor=cursor):
                # TODO: Can I enforce a valid range for the code (0-15)
                sql = """
                    CREATE TABLE IF NOT EXISTS {namesTable} (
                        sector_id TEXT NOT NULL,
                        code INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE,
                        UNIQUE (sector_id, code)
                    );
                    """.format(
                        namesTable=MultiverseDb._SubsectorNamesTableName,
                        sectorsTable=MultiverseDb._SectorsTableName)
                logging.info(f'MultiverseDb creating \'{MultiverseDb._SubsectorNamesTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MultiverseDb._SubsectorNamesTableName,
                    version=MultiverseDb._SubsectorNamesTableSchema,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MultiverseDb._SubsectorNamesTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create allegiance names table
            if not database.checkIfTableExists(
                    tableName=MultiverseDb._AllegiancesTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {allegiancesTable} (
                        sector_id TEXT NOT NULL,
                        code TEXT NOT NULL,
                        name TEXT NOT NULL,
                        legacy TEXT,
                        base TEXT,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        allegiancesTable=MultiverseDb._AllegiancesTableName,
                        sectorsTable=MultiverseDb._SectorsTableName)
                logging.info(f'MultiverseDb creating \'{MultiverseDb._AllegiancesTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MultiverseDb._AllegiancesTableName,
                    version=MultiverseDb._AllegiancesTableSchema,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MultiverseDb._AllegiancesTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create products table
            if not database.checkIfTableExists(
                    tableName=MultiverseDb._ProductsTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {productsTable} (
                        sector_id TEXT NOT NULL,
                        publication TEXT,
                        author TEXT,
                        publisher TEXT,
                        reference TEXT,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        productsTable=MultiverseDb._ProductsTableName,
                        sectorsTable=MultiverseDb._SectorsTableName)
                logging.info(f'MultiverseDb creating \'{MultiverseDb._ProductsTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MultiverseDb._ProductsTableName,
                    version=MultiverseDb._ProductsTableSchema,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MultiverseDb._ProductsTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create systems table
            if not database.checkIfTableExists(
                    tableName=MultiverseDb._SystemsTableName,
                    cursor=cursor):

                # TODO: I'm not sure what to do about importance. I don't think I use
                # it anywhere. I think this might be the same as the importance value
                # I calculate in the cartographer
                sql = """
                    CREATE TABLE IF NOT EXISTS {systemsTable} (
                        id TEXT PRIMARY KEY NOT NULL,
                        sector_id TEXT NOT NULL,
                        hex_x INTEGER NOT NULL,
                        hex_y INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        uwp TEXT NOT NULL,
                        remarks TEXT,
                        importance TEXT,
                        economics TEXT,
                        culture TEXT,
                        nobility TEXT,
                        bases TEXT,
                        zone TEXT,
                        pbg TEXT,
                        system_worlds INTEGER,
                        allegiance TEXT,
                        stellar TEXT,
                        notes TEXT,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE,
                        UNIQUE (sector_id, hex_x, hex_y)
                    );
                    """.format(
                        systemsTable=MultiverseDb._SystemsTableName,
                        sectorsTable=MultiverseDb._SectorsTableName)
                logging.info(f'MultiverseDb creating \'{MultiverseDb._SystemsTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MultiverseDb._SystemsTableName,
                    version=MultiverseDb._SystemsTableSchema,
                    cursor=cursor)

                # Create indexes for id column. The id index is needed as, even
                # though it's the primary key, it's of type TEXT so doesn't
                # automatically get indexes
                self._createColumnIndex(
                    table=MultiverseDb._SystemsTableName,
                    column='id',
                    unique=True,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MultiverseDb._SystemsTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create routes table
            if not database.checkIfTableExists(
                    tableName=MultiverseDb._RoutesTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {routesTable} (
                        id TEXT PRIMARY KEY NOT NULL,
                        sector_id TEXT NOT NULL,
                        start_hex_x INTEGER NOT NULL,
                        start_hex_y INTEGER NOT NULL,
                        end_hex_x INTEGER NOT NULL,
                        end_hex_y INTEGER NOT NULL,
                        start_offset_x INTEGER NOT NULL,
                        start_offset_y INTEGER NOT NULL,
                        end_offset_x INTEGER NOT NULL,
                        end_offset_y INTEGER NOT NULL,
                        allegiance TEXT,
                        type TEXT,
                        style TEXT,
                        colour TEXT,
                        width REAL,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        routesTable=MultiverseDb._RoutesTableName,
                        sectorsTable=MultiverseDb._SectorsTableName)
                logging.info(f'MultiverseDb creating \'{MultiverseDb._RoutesTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MultiverseDb._RoutesTableName,
                    version=MultiverseDb._RoutesTableSchema,
                    cursor=cursor)

                # Create indexes for id column. The id index is needed as, even
                # though it's the primary key, it's of type TEXT so doesn't
                # automatically get indexes
                self._createColumnIndex(
                    table=MultiverseDb._RoutesTableName,
                    column='id',
                    unique=True,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MultiverseDb._RoutesTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create borders table
            if not database.checkIfTableExists(
                    tableName=MultiverseDb._BordersTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {bordersTable} (
                        id TEXT PRIMARY KEY NOT NULL,
                        sector_id TEXT NOT NULL,
                        label TEXT,
                        show_label INTEGER NOT NULL,
                        wrap_label INTEGER NOT NULL,
                        label_hex_x INTEGER,
                        label_hex_y INTEGER,
                        label_offset_x REAL,
                        label_offset_y REAL,
                        colour TEXT,
                        style TEXT,
                        allegiance TEXT,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        bordersTable=MultiverseDb._BordersTableName,
                        sectorsTable=MultiverseDb._SectorsTableName)
                logging.info(f'MultiverseDb creating \'{MultiverseDb._BordersTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MultiverseDb._BordersTableName,
                    version=MultiverseDb._BordersTableSchema,
                    cursor=cursor)

                # Create indexes for id column. The id index is needed as, even
                # though it's the primary key, it's of type TEXT so doesn't
                # automatically get indexes
                self._createColumnIndex(
                    table=MultiverseDb._BordersTableName,
                    column='id',
                    unique=True,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MultiverseDb._BordersTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create border hexes table
            if not database.checkIfTableExists(
                    tableName=MultiverseDb._BorderHexesTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {hexesTable} (
                        border_id TEXT NOT NULL,
                        hex_x INTEGER NOT NULL,
                        hex_y INTEGER NOT NULL,
                        FOREIGN KEY(border_id) REFERENCES {bordersTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        hexesTable=MultiverseDb._BorderHexesTableName,
                        bordersTable=MultiverseDb._BordersTableName)
                logging.info(f'MultiverseDb creating \'{MultiverseDb._BorderHexesTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MultiverseDb._BorderHexesTableName,
                    version=MultiverseDb._BorderHexesTableSchema,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MultiverseDb._BorderHexesTableName,
                    column='border_id',
                    unique=False,
                    cursor=cursor)

            # Create regions table
            # TODO: The only difference between regions and borders seems to be
            # that borders have a style but regions don't. It feels like there
            # must be a way to do this that doesn't involve having two tables
            # and object definitions
            if not database.checkIfTableExists(
                    tableName=MultiverseDb._RegionsTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {regionsTable} (
                        id TEXT PRIMARY KEY NOT NULL,
                        sector_id TEXT NOT NULL,
                        label TEXT,
                        show_label INTEGER NOT NULL,
                        wrap_label INTEGER NOT NULL,
                        label_hex_x INTEGER,
                        label_hex_y INTEGER,
                        label_offset_x REAL,
                        label_offset_y REAL,
                        colour TEXT,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        regionsTable=MultiverseDb._RegionsTableName,
                        sectorsTable=MultiverseDb._SectorsTableName)
                logging.info(f'MultiverseDb creating \'{MultiverseDb._RegionsTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MultiverseDb._RegionsTableName,
                    version=MultiverseDb._RegionsTableSchema,
                    cursor=cursor)

                # Create indexes for id column. The id index is needed as, even
                # though it's the primary key, it's of type TEXT so doesn't
                # automatically get indexes
                self._createColumnIndex(
                    table=MultiverseDb._RegionsTableName,
                    column='id',
                    unique=True,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MultiverseDb._RegionsTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            # Create region hexes table
            if not database.checkIfTableExists(
                    tableName=MultiverseDb._RegionHexesTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {hexesTable} (
                        region_id TEXT NOT NULL,
                        hex_x INTEGER NOT NULL,
                        hex_y INTEGER NOT NULL,
                        FOREIGN KEY(region_id) REFERENCES {regionsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        hexesTable=MultiverseDb._RegionHexesTableName,
                        regionsTable=MultiverseDb._RegionsTableName)
                logging.info(f'MultiverseDb creating \'{MultiverseDb._RegionHexesTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MultiverseDb._RegionHexesTableName,
                    version=MultiverseDb._RegionHexesTableSchema,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MultiverseDb._RegionHexesTableName,
                    column='region_id',
                    unique=False,
                    cursor=cursor)

            # Create labels table
            if not database.checkIfTableExists(
                    tableName=MultiverseDb._LabelsTableName,
                    cursor=cursor):
                # TODO: Should offset be optional?
                sql = """
                    CREATE TABLE IF NOT EXISTS {labelsTable} (
                        id TEXT PRIMARY KEY NOT NULL,
                        sector_id TEXT NOT NULL,
                        text TEXT NOT NULL,
                        hex_x INTEGER NOT NULL,
                        hex_y INTEGER NOT NULL,
                        wrap INTEGER NOT NULL,
                        colour TEXT,
                        size TEXT,
                        offset_x REAL,
                        offset_y REAL,
                        FOREIGN KEY(sector_id) REFERENCES {sectorsTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                        labelsTable=MultiverseDb._LabelsTableName,
                        sectorsTable=MultiverseDb._SectorsTableName)
                logging.info(f'MultiverseDb creating \'{MultiverseDb._LabelsTableName}\' table')
                cursor.execute(sql)

                self._writeSchemaVersion(
                    table=MultiverseDb._LabelsTableName,
                    version=MultiverseDb._LabelsTableSchema,
                    cursor=cursor)

                # Create indexes for id column. The id index is needed as, even
                # though it's the primary key, it's of type TEXT so doesn't
                # automatically get indexes
                self._createColumnIndex(
                    table=MultiverseDb._LabelsTableName,
                    column='id',
                    unique=True,
                    cursor=cursor)

                # Create index on parent id column as it's used a lot by reads
                # and cascade deletes
                self._createColumnIndex(
                    table=MultiverseDb._LabelsTableName,
                    column='sector_id',
                    unique=False,
                    cursor=cursor)

            cursor.execute('END;')
        except:
            if cursor:
                try:
                    cursor.execute('ROLLBACK;')
                except:
                    pass
            if connection:
                connection.close()
            raise

    def _writeSchemaVersion(
            self,
            table: str,
            version: int,
            cursor: sqlite3.Cursor
            ) -> None:
        logging.info(f'MultiverseDb setting schema for \'{table}\' table to {version}')
        sql = """
            INSERT INTO {table} (name, version)
            VALUES (:name, :version)
            ON CONFLICT(name) DO UPDATE SET
                version = excluded.version;
            """.format(table=MultiverseDb._TableSchemaTableName)
        rowData = {
            'name': table,
            'version': version}
        cursor.execute(sql, rowData)

    def _createColumnIndex(
            self,
            table: str,
            column: str,
            unique: bool,
            cursor: sqlite3.Cursor
            ) -> None:
        logging.info(f'MultiverseDb creating index for \'{column}\' in table \'{table}\'')
        database.createColumnIndex(table=table, column=column, unique=unique, cursor=cursor)

    def _createMultiColumnIndex(
            self,
            table: str,
            columns: typing.Collection[str],
            unique: bool,
            cursor: sqlite3.Cursor
            ) -> None:
        logging.info(f'MultiverseDb creating index for \'{','.join(columns)}\' in table \'{table}\'')
        database.createMultiColumnIndex(table=table, columns=columns, unique=unique, cursor=cursor)

    def _setMetadata(
            self,
            key: str,
            value: str,
            cursor: sqlite3.Cursor
            ) -> None:
        logging.debug(f'MultiverseDb setting metadata \'{key}\' to {value}')
        sql = """
            INSERT INTO {table} (key, value)
            VALUES (:key, :value)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value;
            """.format(table=MultiverseDb._MetadataTableName)
        rowData = {
            'key': key,
            'value': value}
        cursor.execute(sql, rowData)

    def _getMetadata(
            self,
            key: str,
            cursor: sqlite3.Cursor
            ) -> typing.Optional[str]:
        sql = """
            SELECT value
            FROM {table}
            WHERE key = :key
            LIMIT 1;
            """.format(table=MultiverseDb._MetadataTableName)
        cursor.execute(sql, {'key': key})
        rowData = cursor.fetchone()
        return rowData[0] if rowData else None

    # This function returns True if imported or False if nothing was
    # done due to the snapshot being older than the current snapshot.
    # If forceImport is true the snapshot will be imported even if
    # it is older
    # TODO: I'm not sure if this should live here or be separate like
    # the custom sector code. It feels like the two types of operation
    # should be handled consistently
    def _internalImportDefaultUniverse(
            self,
            directoryPath: str,
            cursor: sqlite3.Cursor,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        timestampPath = os.path.join(directoryPath, 'timestamp.txt')
        with open(timestampPath, 'r', encoding='utf-8-sig') as file:
            timestampContent = file.read()
        importTimestamp = MultiverseDb._parseTimestamp(content=timestampContent)

        rawStockAllegiances = multiverse.readSnapshotStockAllegiances()

        universePath = os.path.join(directoryPath, 'milieu')
        milieuSectors: typing.List[typing.Tuple[
            str, # Milieu
            typing.List[str] # List of sector names in the milieu
        ]] = []
        totalSectorCount = 0
        for milieu in [d for d in os.listdir(universePath) if os.path.isdir(os.path.join(universePath, d))]:
            milieuPath = os.path.join(universePath, milieu)
            universeInfoPath = os.path.join(milieuPath, 'universe.json')
            with open(universeInfoPath, 'r', encoding='utf-8-sig') as file:
                universeInfoContent = file.read()
            universeInfo = multiverse.readUniverseInfo(content=universeInfoContent)

            sectorNames = []
            for sectorInfo in universeInfo.sectorInfos():
                try:
                    nameInfos = sectorInfo.nameInfos()
                    canonicalName = nameInfos[0].name() if nameInfos else None
                    if not canonicalName:
                        raise RuntimeError('Sector has no name')
                    sectorNames.append(canonicalName)
                    totalSectorCount += 1
                except Exception as ex:
                    # TODO: Log something but continue
                    continue

            milieuSectors.append((milieu, sectorNames))

        rawData: typing.List[typing.Tuple[
            str, # Milieu
            multiverse.RawMetadata,
            typing.Collection[multiverse.RawWorld]
            ]] = []
        progressCount = 0
        for milieu, sectorNames in milieuSectors:
            milieuPath = os.path.join(universePath, milieu)
            for sectorName in sectorNames:
                try:
                    if progressCallback:
                        progressCallback(
                            f'Reading: {milieu} - {sectorName}',
                            progressCount,
                            totalSectorCount)
                        progressCount += 1

                    escapedName = common.encodeFileName(rawFileName=sectorName)

                    metadataPath = os.path.join(milieuPath, escapedName + '.xml')
                    with open(metadataPath, 'r', encoding='utf-8-sig') as file:
                        rawMetadata = multiverse.readXMLMetadata(
                            content=file.read(),
                            identifier=sectorName)

                    sectorPath = os.path.join(milieuPath, escapedName + '.sec')
                    with open(sectorPath, 'r', encoding='utf-8-sig') as file:
                        rawSystems = multiverse.readT5ColumnSector(
                            content=file.read(),
                            identifier=sectorName)
                    rawData.append((milieu, rawMetadata, rawSystems))
                except Exception as ex:
                    # TODO: Log something but continue
                    continue

        if progressCallback:
            progressCallback(
                f'Reading: Complete!',
                totalSectorCount,
                totalSectorCount)

        dbUniverse = multiverse.convertRawUniverseToDbUniverse(
            universeId=MultiverseDb._DefaultUniverseId,
            universeName='Default Universe',
            isCustom=False,
            rawSectors=rawData,
            rawStockAllegiances=rawStockAllegiances,
            progressCallback=progressCallback)

        self._internalDeleteUniverse(
            universeId=MultiverseDb._DefaultUniverseId,
            cursor=cursor)

        insertProgressCallback = None
        if progressCallback:
            insertProgressCallback = \
                lambda name, milieu, progress, total: progressCallback(f'Importing: {milieu} - {name}' if progress != total else 'Importing: Complete!', progress, total)
        self._internalInsertUniverse(
            universe=dbUniverse,
            updateDefault=True,
            cursor=cursor,
            progressCallback=insertProgressCallback)

        self._setMetadata(
            key=MultiverseDb._DefaultUniverseTimestampKey,
            value=importTimestamp.isoformat(),
            cursor=cursor)

    def _internalInsertUniverse(
            self,
            universe: multiverse.DbUniverse,
            cursor: sqlite3.Cursor,
            updateDefault: bool = False,
            progressCallback: typing.Optional[typing.Callable[[typing.Optional[str], typing.Optional[str], int, int], typing.Any]] = None
            ) -> None:
        sql = """
            INSERT INTO {table} (id, name, description, notes)
            VALUES (:id, :name, :description, :notes);
            """.format(table=MultiverseDb._UniversesTableName)
        rowData = {
            'id': universe.id(),
            'name': universe.name(),
            'description': universe.description(),
            'notes': universe.notes()}
        cursor.execute(sql, rowData)

        sectors = universe.sectors()
        totalSectorCount = len(sectors) if sectors else 0
        if sectors:
            for progressCount, sector in enumerate(sectors):
                if progressCallback:
                    progressCallback(
                        sector.milieu(),
                        sector.primaryName(),
                        progressCount,
                        totalSectorCount)

                if not updateDefault and not sector.isCustom():
                    continue # Only write custom sectors

                self._internalInsertSector(
                    sector=sector,
                    cursor=cursor)

        if progressCallback:
            progressCallback(
                None,
                None,
                totalSectorCount,
                totalSectorCount)

    def _internalReadUniverse(
            self,
            universeId: str,
            includeDefaultSectors: bool,
            cursor: sqlite3.Cursor,
            progressCallback: typing.Optional[typing.Callable[[typing.Optional[str], typing.Optional[str], int, int], typing.Any]] = None
            ) -> typing.Optional[multiverse.DbUniverse]:
        sql = """
            SELECT name, description, notes
            FROM {table}
            WHERE id = :id
            LIMIT 1;
            """.format(table=MultiverseDb._UniversesTableName)
        cursor.execute(sql, {'id': universeId})
        row = cursor.fetchone()
        if not row:
            return None
        name = row[0]
        description = row[1]
        notes = row[2]

        # TODO: This could be made more efficient by loading all the sector
        # information in a single select then just loading the sector child
        # data with individual selects.
        sql = """
            SELECT id, primary_name, milieu
            FROM {table}
            WHERE universe_id = :id
            """.format(table=MultiverseDb._SectorsTableName)
        if includeDefaultSectors:
            sql += """
                UNION ALL

                SELECT d.id, d.primary_name, d.milieu
                FROM {table} d
                WHERE d.universe_id IS "default"
                AND NOT EXISTS (
                    SELECT 1
                    FROM {table} u
                    WHERE u.universe_id = :id
                        AND u.milieu = d.milieu
                        AND u.sector_x = d.sector_x
                        AND u.sector_y = d.sector_y
                )
                """.format(table=MultiverseDb._SectorsTableName)
        sql += ';'

        cursor.execute(sql, {'id': universeId})
        resultData = cursor.fetchall()
        totalSectorCount = len(resultData)
        sectors = []
        for progressCount, row in enumerate(resultData):
            sectorId = row[0]
            sectorName = row[1]
            sectorMilieu = row[2]

            if progressCallback:
                progressCallback(
                    sectorMilieu,
                    sectorName,
                    progressCount,
                    totalSectorCount)

            sector = self._internalReadSector(
                sectorId=sectorId,
                cursor=cursor)
            if not sector:
                # TODO: Some kind of logging or error handling?
                continue
            sectors.append(sector)

        if progressCallback:
            progressCallback(
                None,
                None,
                totalSectorCount,
                totalSectorCount)

        return multiverse.DbUniverse(
            id=universeId,
            name=name,
            description=description,
            notes=notes,
            sectors=sectors)

    def _internalDeleteUniverse(
            self,
            universeId: str,
            cursor: sqlite3.Cursor
            ) -> typing.Optional[multiverse.DbUniverse]:
        sql = """
            DELETE FROM {table}
            WHERE id = :id
            """.format(
            table=MultiverseDb._UniversesTableName)
        cursor.execute(sql, {'id': universeId})

    def _internalInsertSector(
            self,
            sector: multiverse.DbSector,
            cursor: sqlite3.Cursor
            ) -> None:
        sql = """
            INSERT INTO {table} (id, universe_id, is_custom, milieu,
                sector_x, sector_y, primary_name, primary_language,
                abbreviation, sector_label, selected, tags, style_sheet,
                credits, publication, author, publisher, reference, notes)
            VALUES (:id, :universe_id, :is_custom, :milieu,
                :sector_x, :sector_y, :primary_name, :primary_language,
                :abbreviation, :sector_label, :selected, :tags, :style_sheet,
                :credits, :publication, :author, :publisher, :reference, :notes);
            """.format(table=MultiverseDb._SectorsTableName)
        rowData = {
            'id': sector.id(),
            'universe_id': sector.universeId(),
            'is_custom': 1 if sector.isCustom() else 0,
            'milieu': sector.milieu(),
            'sector_x': sector.sectorX(),
            'sector_y': sector.sectorY(),
            'primary_name': sector.primaryName(),
            'primary_language': sector.primaryLanguage(),
            'abbreviation': sector.abbreviation(),
            'sector_label': sector.sectorLabel(),
            'selected': 1 if sector.selected() else 0,
            'tags': sector.tags(),
            'style_sheet': sector.styleSheet(),
            'credits': sector.credits(),
            'publication': sector.publication(),
            'author': sector.author(),
            'publisher': sector.publisher(),
            'reference': sector.reference(),
            'notes': sector.notes()}
        cursor.execute(sql, rowData)

        if sector.alternateNames():
            sql = """
                INSERT INTO {table} (sector_id, name, language)
                VALUES (:sector_id, :name, :language);
                """.format(table=MultiverseDb._AlternateNamesTableName)
            rowData = []
            for name, language in sector.alternateNames():
                rowData.append({
                    'sector_id': sector.id(),
                    'name': name,
                    'language': language})
            cursor.executemany(sql, rowData)

        if sector.subsectorNames():
            sql = """
                INSERT INTO {table} (sector_id, code, name)
                VALUES (:sector_id, :code, :name);
                """.format(table=MultiverseDb._SubsectorNamesTableName)
            rowData = []
            for code, name in sector.subsectorNames():
                rowData.append({
                    'sector_id': sector.id(),
                    'code': code,
                    'name': name})
            cursor.executemany(sql, rowData)

        if sector.products():
            sql = """
                INSERT INTO {table} (sector_id, publication, author,
                    publisher, reference)
                VALUES (:sector_id, :publication, :author,
                    :publisher, :reference);
                """.format(table=MultiverseDb._ProductsTableName)
            rowData = []
            for product in sector.products():
                rowData.append({
                    'sector_id': sector.id(),
                    'publication': product.publication(),
                    'author': product.author(),
                    'publisher': product.publisher(),
                    'reference': product.reference()})
            cursor.executemany(sql, rowData)

        if sector.allegiances():
            sql = """
                INSERT INTO {table} (sector_id, code, name, legacy, base)
                VALUES (:sector_id, :code, :name, :legacy, :base);
                """.format(table=MultiverseDb._AllegiancesTableName)
            rowData = []
            for allegiance in sector.allegiances():
                rowData.append({
                    'sector_id': sector.id(),
                    'code': allegiance.code(),
                    'name': allegiance.name(),
                    'legacy': allegiance.legacy(),
                    'base': allegiance.base()})
            cursor.executemany(sql, rowData)

        if sector.systems():
            sql = """
                INSERT INTO {table} (id, sector_id, hex_x, hex_y, name, uwp, remarks,
                    importance, economics, culture, nobility, bases, zone, pbg,
                    system_worlds, allegiance, stellar, notes)
                VALUES (:id, :sector_id, :hex_x, :hex_y, :name, :uwp, :remarks,
                    :importance, :economics, :culture, :nobility, :bases, :zone, :pbg,
                    :system_worlds, :allegiance, :stellar, :notes);
                """.format(table=MultiverseDb._SystemsTableName)
            rowData = []
            for system in sector.systems():
                rowData.append({
                    'id': system.id(),
                    'sector_id': system.sectorId(),
                    'hex_x': system.hexX(),
                    'hex_y': system.hexY(),
                    'name': system.name(),
                    'uwp': system.uwp(),
                    'remarks': system.remarks(),
                    'importance': system.importance(),
                    'economics': system.economics(),
                    'culture': system.culture(),
                    'nobility': system.nobility(),
                    'bases': system.bases(),
                    'zone': system.zone(),
                    'pbg': system.pbg(),
                    'system_worlds': system.systemWorlds(),
                    'allegiance': system.allegiance(),
                    'stellar': system.stellar(),
                    'notes': system.notes()})
            cursor.executemany(sql, rowData)

        if sector.routes():
            sql = """
                INSERT INTO {table} (id, sector_id, start_hex_x, start_hex_y, end_hex_x, end_hex_y,
                    start_offset_x, start_offset_y, end_offset_x, end_offset_y, allegiance, type,
                    style, colour, width)
                VALUES (:id, :sector_id, :start_hex_x, :start_hex_y, :end_hex_x, :end_hex_y,
                    :start_offset_x, :start_offset_y, :end_offset_x, :end_offset_y, :allegiance, :type,
                    :style, :colour, :width);
                """.format(table=MultiverseDb._RoutesTableName)
            rowData = []
            for route in sector.routes():
                rowData.append({
                    'id': route.id(),
                    'sector_id': route.sectorId(),
                    'start_hex_x': route.startHexX(),
                    'start_hex_y': route.startHexY(),
                    'end_hex_x': route.endHexX(),
                    'end_hex_y': route.endHexY(),
                    'start_offset_x': route.startOffsetX(),
                    'start_offset_y': route.startOffsetY(),
                    'end_offset_x': route.endOffsetX(),
                    'end_offset_y': route.endOffsetY(),
                    'allegiance': route.allegiance(),
                    'type': route.type(),
                    'style': route.style(),
                    'colour': route.colour(),
                    'width': route.width()})
            cursor.executemany(sql, rowData)

        if sector.borders():
            bordersSql = """
                INSERT INTO {table} (id, sector_id, show_label, wrap_label,
                    label_hex_x, label_hex_y, label_offset_x, label_offset_y,
                    label, colour, style, allegiance)
                VALUES (:id, :sector_id, :show_label, :wrap_label,
                    :label_hex_x, :label_hex_y, :label_offset_x, :label_offset_y,
                    :label, :colour, :style, :allegiance );
                """.format(table=MultiverseDb._BordersTableName)
            hexesSql =  """
                INSERT INTO {table} (border_id, hex_x, hex_y)
                VALUES (:border_id, :hex_x, :hex_y);
                """.format(table=MultiverseDb._BorderHexesTableName)
            bordersData = []
            hexesData = []
            for border in sector.borders():
                bordersData.append({
                    'id': border.id(),
                    'sector_id': border.sectorId(),
                    'show_label': 1 if border.showLabel() else 0,
                    'wrap_label': 1 if border.wrapLabel() else 0,
                    'label_hex_x': border.labelHexX(),
                    'label_hex_y': border.labelHexY(),
                    'label_offset_x': border.labelOffsetX(),
                    'label_offset_y': border.labelOffsetY(),
                    'label': border.label(),
                    'colour': border.colour(),
                    'style': border.style(),
                    'allegiance': border.allegiance()})
                for hexX, hexY in border.hexes():
                    hexesData.append({
                        'border_id': border.id(),
                        'hex_x': hexX,
                        'hex_y': hexY})
            cursor.executemany(bordersSql, bordersData)
            cursor.executemany(hexesSql, hexesData)

        if sector.regions():
            regionsSql = """
                INSERT INTO {table} (id, sector_id, show_label, wrap_label,
                    label_hex_x, label_hex_y, label_offset_x, label_offset_y,
                    label, colour)
                VALUES (:id, :sector_id, :show_label, :wrap_label,
                    :label_hex_x, :label_hex_y, :label_offset_x, :label_offset_y,
                    :label, :colour);
                """.format(table=MultiverseDb._RegionsTableName)
            hexesSql =  """
                INSERT INTO {table} (region_id, hex_x, hex_y)
                VALUES (:region_id, :hex_x, :hex_y);
                """.format(table=MultiverseDb._RegionHexesTableName)
            regionsData = []
            hexesData = []
            for region in sector.regions():
                regionsData.append({
                    'id': region.id(),
                    'sector_id': region.sectorId(),
                    'show_label': 1 if region.showLabel() else 0,
                    'wrap_label': 1 if region.wrapLabel() else 0,
                    'label_hex_x': region.labelHexX(),
                    'label_hex_y': region.labelHexY(),
                    'label_offset_x': region.labelOffsetX(),
                    'label_offset_y': region.labelOffsetY(),
                    'label': region.label(),
                    'colour': region.colour()})
                for hexX, hexY in region.hexes():
                    hexesData.append({
                        'region_id': region.id(),
                        'hex_x': hexX,
                        'hex_y': hexY})
            cursor.executemany(regionsSql, regionsData)
            cursor.executemany(hexesSql, hexesData)

        if sector.labels():
            sql = """
                INSERT INTO {table} (id, sector_id, text, hex_x, hex_y,
                    wrap, colour, size, offset_x, offset_y)
                VALUES (:id, :sector_id, :text, :hex_x, :hex_y,
                    :wrap, :colour, :size, :offset_x, :offset_y);
                """.format(table=MultiverseDb._LabelsTableName)
            rowData = []
            for label in sector.labels():
                rowData.append({
                    'id': label.id(),
                    'sector_id': label.sectorId(),
                    'text': label.text(),
                    'hex_x': label.hexX(),
                    'hex_y': label.hexY(),
                    'wrap': 1 if label.wrap() else 0,
                    'colour': label.colour(),
                    'size': label.size(),
                    'offset_x': label.offsetX(),
                    'offset_y': label.offsetY()})
            cursor.executemany(sql, rowData)

    def _internalReadSector(
            self,
            sectorId: str,
            cursor: sqlite3.Cursor
            ) -> typing.Optional[multiverse.DbSector]:
        sql = """
            SELECT universe_id, is_custom, milieu, sector_x, sector_y,
                primary_name, primary_language, abbreviation, sector_label,
                selected, tags, style_sheet, credits, publication, author,
                publisher, reference, notes
            FROM {table}
            WHERE id = :id
            LIMIT 1;
            """.format(table=MultiverseDb._SectorsTableName)
        cursor.execute(sql, {'id': sectorId})
        row = cursor.fetchone()
        if not row:
            return None

        sector = multiverse.DbSector(
            id=sectorId,
            universeId=row[0],
            isCustom=True if row[1] else False,
            milieu=row[2],
            sectorX=row[3],
            sectorY=row[4],
            primaryName=row[5],
            primaryLanguage=row[6],
            abbreviation=row[7],
            sectorLabel=row[8],
            selected=True if row[9] else False,
            tags=row[10],
            styleSheet=row[11],
            credits=row[12],
            publication=row[13],
            author=row[14],
            publisher=row[15],
            reference=row[16],
            notes=row[17])

        sql = """
            SELECT name, language
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._AlternateNamesTableName)
        cursor.execute(sql, {'id': sectorId})
        sector.setAlternateNames(
            [(row[0], row[1]) for row in cursor.fetchall()])

        sql = """
            SELECT code, name
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._SubsectorNamesTableName)
        cursor.execute(sql, {'id': sectorId})
        sector.setSubsectorNames(
            [(row[0], row[1]) for row in cursor.fetchall()])

        sql = """
            SELECT publication, author, publisher, reference
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._ProductsTableName)
        cursor.execute(sql, {'id': sectorId})
        products = []
        for row in cursor.fetchall():
            products.append(multiverse.DbProduct(
                publication=row[0],
                author=row[1],
                publisher=row[2],
                reference=row[3]))
        sector.setProducts(products)

        sql = """
            SELECT code, name, legacy, base
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._AllegiancesTableName)
        cursor.execute(sql, {'id': sectorId})
        allegiances = []
        for row in cursor.fetchall():
            allegiances.append(multiverse.DbAllegiance(
                code=row[0],
                name=row[1],
                legacy=row[2],
                base=row[3]))
        sector.setAllegiances(allegiances)

        sql = """
            SELECT id, hex_x, hex_y, name, uwp, remarks, importance,
                economics, culture, nobility, bases, zone, pbg,
                system_worlds, allegiance, stellar, notes
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        systems = []
        for row in cursor.fetchall():
            systems.append(multiverse.DbSystem(
                id=row[0],
                hexX=row[1],
                hexY=row[2],
                name=row[3],
                uwp=row[4],
                remarks=row[5],
                importance=row[6],
                economics=row[7],
                culture=row[8],
                nobility=row[9],
                bases=row[10],
                zone=row[11],
                pbg=row[12],
                systemWorlds=row[13],
                allegiance=row[14],
                stellar=row[15],
                notes=row[16]))
        sector.setSystems(systems)

        sql = """
            SELECT id, start_hex_x, start_hex_y, end_hex_x, end_hex_y,
                start_offset_x, start_offset_y, end_offset_x, end_offset_y,
                allegiance, type, style, colour, width
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._RoutesTableName)
        cursor.execute(sql, {'id': sectorId})
        routes = []
        for row in cursor.fetchall():
            routes.append(multiverse.DbRoute(
                id=row[0],
                startHexX=row[1],
                startHexY=row[2],
                endHexX=row[3],
                endHexY=row[4],
                startOffsetX=row[5],
                startOffsetY=row[6],
                endOffsetX=row[7],
                endOffsetY=row[8],
                allegiance=row[9],
                type=row[10],
                style=row[11],
                colour=row[12],
                width=row[13]))
        sector.setRoutes(routes)

        sql = """
            SELECT id, show_label, wrap_label,
                label_hex_x, label_hex_y, label_offset_x, label_offset_y,
                label, colour, style, allegiance
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._BordersTableName)
        cursor.execute(sql, {'id': sectorId})
        borders = []
        for row in cursor.fetchall():
            borderId = row[0]

            hexesSql = """
                SELECT hex_x, hex_y
                FROM {table}
                WHERE border_id = :id;
                """.format(table=MultiverseDb._BorderHexesTableName)
            cursor.execute(hexesSql, {'id': borderId})
            hexes = []
            for hexRow in cursor.fetchall():
                hexes.append((hexRow[0], hexRow[1]))

            borders.append(multiverse.DbBorder(
                id=borderId,
                hexes=hexes,
                showLabel=True if row[1] else False,
                wrapLabel=True if row[2] else False,
                labelHexX=row[3],
                labelHexY=row[4],
                labelOffsetX=row[5],
                labelOffsetY=row[6],
                label=row[7],
                colour=row[8],
                style=row[9],
                allegiance=row[10]))
        sector.setBorders(borders)

        sql = """
            SELECT id, show_label, wrap_label,
                label_hex_x, label_hex_y, label_offset_x, label_offset_y,
                label, colour
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._RegionsTableName)
        cursor.execute(sql, {'id': sectorId})
        regions = []
        for row in cursor.fetchall():
            regionId = row[0]

            hexesSql = """
                SELECT hex_x, hex_y
                FROM {table}
                WHERE region_id = :id;
                """.format(table=MultiverseDb._RegionHexesTableName)
            cursor.execute(hexesSql, {'id': regionId})
            hexes = []
            for hexRow in cursor.fetchall():
                hexes.append((hexRow[0], hexRow[1]))

            regions.append(multiverse.DbRegion(
                id=regionId,
                hexes=hexes,
                showLabel=True if row[1] else False,
                wrapLabel=True if row[2] else False,
                labelHexX=row[3],
                labelHexY=row[4],
                labelOffsetX=row[5],
                labelOffsetY=row[6],
                label=row[7],
                colour=row[8]))
        sector.setRegions(regions)

        sql = """
            SELECT id, text, hex_x, hex_y, wrap, colour, size,
                offset_x, offset_y
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._LabelsTableName)
        cursor.execute(sql, {'id': sectorId})
        labels = []
        for row in cursor.fetchall():
            labels.append(multiverse.DbLabel(
                id=row[0],
                text=row[1],
                hexX=row[2],
                hexY=row[3],
                wrap=True if row[4] else False,
                colour=row[5],
                size=row[6],
                offsetX=row[7],
                offsetY=row[8]))
        sector.setLabels(labels)

        return sector

    def _internalDeleteSector(
            self,
            sectorId: str,
            cursor: sqlite3.Cursor,
            milieu: typing.Optional[str] = None,
            sectorX: typing.Optional[int] = None,
            sectorY: typing.Optional[int] = None,
            ) -> typing.Optional[multiverse.DbUniverse]:
        sql = """
            DELETE FROM {table}
            WHERE id = :id
            """.format(
            table=MultiverseDb._SectorsTableName)
        queryData = {'id': sectorId}

        if milieu is not None and sectorX is not None and sectorY is not None:
            sql += 'OR (milieu = :milieu AND sector_x = :sector_x AND sector_y = :sector_y)'
            queryData['milieu'] = milieu
            queryData['sector_x'] = sectorX
            queryData['sector_y'] = sectorY

        sql += ';'
        cursor.execute(sql, queryData)

    def _internalListUniverseInfo(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[DbUniverseInfo]:
        sql = """
            SELECT id, name
            FROM {table}
            WHERE id != :defaultId;
            """.format(
            table=MultiverseDb._UniversesTableName)
        cursor.execute(sql, {'defaultId': MultiverseDb._DefaultUniverseId})

        universeList = []
        for row in cursor.fetchall():
            universeList.append(DbUniverseInfo(
                universeId=row[0],
                name=row[1]))
        return universeList

    def _internalUniverseInfoById(
            self,
            universeId: str,
            cursor: sqlite3.Cursor
            ) -> typing.List[DbUniverseInfo]:
        sql = """
            SELECT name
            FROM {table}
            WHERE id != :id
            LIMIT 1;
            """.format(
            table=MultiverseDb._UniversesTableName)
        cursor.execute(sql, {'id': universeId})

        row = cursor.fetchone()
        if not row:
            return None

        return DbUniverseInfo(
            universeId=universeId,
            name=row[0])

    def _internalUniverseInfoByName(
            self,
            name: str,
            cursor: sqlite3.Cursor
            ) -> typing.List[DbUniverseInfo]:
        sql = """
            SELECT id
            FROM {table}
            WHERE name != :name
            LIMIT 1;
            """.format(
            table=MultiverseDb._UniversesTableName)
        cursor.execute(sql, {'name': name})

        row = cursor.fetchone()
        if not row:
            return None

        return DbUniverseInfo(
            universeId=row[0],
            name=name)

    def _internalListSectorInfo(
            self,
            universeId: str,
            milieu: typing.Optional[str],
            includeDefaultSectors: bool,
            cursor: sqlite3.Cursor
            ) -> typing.List[DbSectorInfo]:
        sql = """
            SELECT id, primary_name, sector_x, sector_y, is_custom, abbreviation
            FROM {table}
            WHERE universe_id = :id
            """.format(table=MultiverseDb._SectorsTableName)
        selectData = {'id': universeId}

        if milieu:
            sql += 'AND milieu = :milieu'
            selectData['milieu'] = milieu

        if includeDefaultSectors:
            sql += """
                UNION ALL
                SELECT d.id, d.primary_name, d.sector_x, d.sector_y, is_custom, abbreviation
                FROM {table} d
                WHERE d.universe_id IS "default"
                """.format(table=MultiverseDb._SectorsTableName)

            if milieu:
                sql += 'AND milieu = :milieu'

            sql += """
                AND NOT EXISTS (
                    SELECT 1
                    FROM {table} u
                    WHERE u.universe_id = :id
                        AND u.milieu = d.milieu
                        AND u.sector_x = d.sector_x
                        AND u.sector_y = d.sector_y
                )
                """.format(table=MultiverseDb._SectorsTableName)

        sql += ';'

        cursor.execute(sql, selectData)

        sectorList = []
        for row in cursor.fetchall():
            sectorList.append(DbSectorInfo(
                id=row[0],
                name=row[1],
                sectorX=row[2],
                sectorY=row[3],
                isCustom=True if row[4] else False,
                abbreviation=row[5]))
        return sectorList

    def _internalSectorInfoById(
            self,
            sectorId: str,
            cursor: sqlite3.Cursor
            ) -> typing.Optional[DbSectorInfo]:
        sql = """
            SELECT primary_name, sector_x, sector_y, is_custom, abbreviation
            FROM {table}
            WHERE id = :id
            LIMIT 1;
            """.format(table=MultiverseDb._SectorsTableName)
        selectData = {'id': sectorId}

        cursor.execute(sql, selectData)
        row = cursor.fetchone()
        if not row:
            return None

        return DbSectorInfo(
            id=sectorId,
            name=row[0],
            sectorX=row[1],
            sectorY=row[2],
            isCustom=True if row[3] else False,
            abbreviation=row[4])

    def _internalSectorInfoByPosition(
            self,
            universeId: str,
            milieu: str,
            sectorX: int,
            sectorY: int,
            cursor: sqlite3.Cursor
            ) -> typing.Optional[DbSectorInfo]:
        sql = """
            SELECT id, primary_name, is_custom, abbreviation
            FROM {table}
            WHERE (universe_id = :id OR universe_id = 'default')
                AND milieu = :milieu
                AND sector_x = :sector_x
                AND sector_y = :sector_y
            ORDER BY
                CASE WHEN universe_id = :id THEN 0 ELSE 1 END
            LIMIT 1;
            """.format(table=MultiverseDb._SectorsTableName)
        selectData = {
            'id': universeId,
            'milieu': milieu,
            'sector_x': sectorX,
            'sector_y': sectorY}

        cursor.execute(sql, selectData)
        row = cursor.fetchone()
        if not row:
            return None

        return DbSectorInfo(
            id=row[0],
            name=row[1],
            sectorX=sectorX,
            sectorY=sectorY,
            isCustom=True if row[2] else False,
            abbreviation=row[3])

    @staticmethod
    def _parseTimestamp(
            content: str,
            ) -> datetime.datetime:
        timestamp = datetime.datetime.strptime(
            content,
            MultiverseDb._TimestampFormat)
        return timestamp.replace(tzinfo=datetime.timezone.utc)