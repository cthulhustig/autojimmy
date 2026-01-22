import common
import database
import datetime
import enum
import logging
import multiverse
import os
import sqlite3
import survey
import threading
import typing

# TODO: When updating snapshot I'll need to do something to make sure notes
# are preserved on systems/sectors. I could split notes in a separate table
# but it's probably easiest to just read the existing notes and set the
# notes on the new object before writing it to the db.
# TODO: Long term I suspect I'm going to want to be able to have multiple
# worlds in a system with different details (UWP, trade codes etc) for each.
# It will probably be easier to make the split now.
# - When importing I would create a system for each line in the sector file.
#   Generally there would also be a single world created for the system that
#   has the same name as the system. If the world data has ? for everything
#   other than the name then I could create a system that has no worlds
# - Would need a way to mark a world as the main world for the system. For
#   now the main world would be used for everything
# - Stars would need to be for the system rather than for the world
# TODO: All the objects that take universe/sector/system id, should take the
# object rather than the id (similar to what happens for system Allegiance)

class ColumnDef(object):
    class ColumnType(enum.Enum):
        Text = 0
        Integer = 1
        Real = 2
        Boolean = 3

    class ForeignKeyDeleteOp(enum.Enum):
        Cascade = 0
        SetNull = 1

    def __init__(
            self,
            columnName: str,
            columnType: ColumnType,
            isPrimaryKey: bool = False,
            isNullable: bool = True, # Match Sqlite default (ignored for primary key)
            isUnique: bool = False, # Match sqlite default (ignored for primary key)
            isIndexed: bool = False, # Primary and foreign key columns are always indexed
            foreignTableName: typing.Optional[str] = None,
            foreignColumnName: typing.Optional[str] = None,
            foreignDeleteOp: typing.Optional[ForeignKeyDeleteOp] = None,
            validRange: typing.Optional[typing.Tuple[
                typing.Union[str, int, float], # Range min
                typing.Union[str, int, float] # Range max
                ]] = None
            ):
        if not columnName:
            raise ValueError('Column name can\'t be empty')

        if isPrimaryKey and (columnType is not ColumnDef.ColumnType.Text and columnType is not ColumnDef.ColumnType.Integer):
            raise ValueError('Primary key column type must be Text or Integer')

        if foreignTableName and (not foreignColumnName or not foreignDeleteOp):
            raise ValueError('Foreign key column name and delete operation must be specified if foreign key table name is specified')
        if foreignColumnName and (not foreignTableName or not foreignDeleteOp):
            raise ValueError('Foreign key table name and delete operation must be specified if foreign key column name is specified')
        if foreignDeleteOp and (not foreignTableName or not foreignColumnName):
            raise ValueError('Foreign key table and column names must be specified if foreign key delete operation is specified')

        if validRange:
            if columnType is ColumnDef.ColumnType.Text:
                if not isinstance(validRange[0], str) and not isinstance(validRange[1], str):
                    raise ValueError('Valid range for Text column must be of type str')
            elif columnType is ColumnDef.ColumnType.Integer:
                if not isinstance(validRange[0], int) and not isinstance(validRange[1], int):
                    raise ValueError('Valid range for Integer column must be of type int')
            elif columnType is ColumnDef.ColumnType.Real:
                if not isinstance(validRange[0], [float, int]) and not isinstance(validRange[1], [float, int]):
                    raise ValueError('Valid range for Float column must be of type float or int')
            elif columnType is ColumnDef.ColumnType.Boolean:
                raise ValueError('Valid range for is not allowed for Boolean columns')

        hasForeignKey = foreignTableName and foreignColumnName and foreignDeleteOp

        self._columnName = columnName
        self._columnType = columnType
        self._isPrimaryKey = isPrimaryKey
        self._isNullable = isNullable if not self._isPrimaryKey else False
        self._isUnique = isUnique if not self._isPrimaryKey  else True
        self._isIndexed = isIndexed if (not self._isPrimaryKey and not hasForeignKey) else True
        self._foreignTableName = foreignTableName
        self._foreignColumnName = foreignColumnName
        self._foreignDeleteOp = foreignDeleteOp
        self._validRange = validRange

    def columnName(self) -> str:
        return self._columnName

    def columnType(self) -> typing.Union[typing.Type[str], typing.Type[int], typing.Type[float], typing.Type[bool]]:
        return self._columnType

    def isPrimaryKey(self) -> bool:
        return self._isPrimaryKey

    def isNullable(self) -> bool:
        return self._isNullable

    def isUnique(self) -> bool:
        return self._isUnique

    def isIndexed(self) -> bool:
        return self._isIndexed

    def hasForeignKey(self) -> bool:
        return self._foreignTableName and self._foreignColumnName and self._foreignDeleteOp

    def foreignTableName(self) -> typing.Optional[str]:
        return self._foreignTableName

    def foreignColumnName(self) -> typing.Optional[str]:
        return self._foreignColumnName

    def foreignDeleteOp(self) -> typing.Optional[ForeignKeyDeleteOp]:
        return self._foreignDeleteOp

    def validRange(self) -> typing.Optional[typing.Tuple[
            typing.Union[str, int, float], # Range min
            typing.Union[str, int, float] # Range max
            ]]:
        return self._validRange

class UniqueConstraintDef(object):
    def __init__(
            self,
            columnNames: typing.Collection[str]
            ):
        if not columnNames:
            raise ValueError('Unique constraint column names can\'t be empty')
        for index, name in enumerate(columnNames):
            if not name:
                raise ValueError(f'Unique constraint column name {index} can\'t be empty')

        self._columnNames = list(columnNames)

    def columnNames(self) -> typing.Collection[str]:
        return self._columnNames

class ColumnIndexDef(object):
    def __init__(
            self,
            columnNames: typing.Collection[str],
            isUnique: bool = False # Match Sqlite default
            ):
        if not columnNames:
            raise ValueError('Column index column names can\'t be empty')
        for index, name in enumerate(columnNames):
            if not name:
                raise ValueError(f'Column index column name {index} can\'t be empty')

        self._columnNames = list(columnNames)
        self._isUnique = isUnique

    def columnNames(self) -> typing.Collection[str]:
        return self._columnNames

    def isUnique(self) -> bool:
        return self._isUnique

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
            universeId: str,
            milieu: str,
            name: str,
            sectorX: int,
            sectorY: int,
            isCustom: bool,
            abbreviation: typing.Optional[str]
            ) -> None:
        self._id = id
        self._universeId = universeId
        self._milieu = milieu
        self._name = name
        self._sectorX = sectorX
        self._sectorY = sectorY
        self._isCustom = isCustom
        self._abbreviation = abbreviation

        self._hash = None

    def id(self) -> str:
        return self._id

    def universeId(self) -> str:
        return self._universeId

    def milieu(self) -> str:
        return self._milieu

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
    class TableVersionException(Exception):
        def __init__(
                self,
                table: str,
                required: int,
                current: typing.Optional[int]
                ) -> None:
            super().__init__(f'MultiverseDb "{table}" table has schema version {current} when version {required} is required')
            self._table = table
            self._required = required
            self._current = current

        def table(self) -> str:
            return self._table

        def required(self) -> int:
            return self._required

        def current(self) -> typing.Optional[int]:
            return self._current

    class Transaction(object):
        def __init__(
                self,
                connection: sqlite3.Connection,
                onCommitCallback: typing.Optional[typing.Callable[[], None]] = None,
                onRollbackCallback: typing.Optional[typing.Callable[[], None]] = None
                ) -> None:
            self._connection = connection
            self._hasBegun = False
            self._onCommitCallback = onCommitCallback
            self._onRollbackCallback = onRollbackCallback

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

            if self._onCommitCallback:
                try:
                    self._onCommitCallback()
                except Exception as ex:
                    logging.error('MultiverseDb transaction commit callback threw exception')

            cursor = self._connection.cursor()
            try:
                cursor.execute('END;')
            finally:
                self._teardown()

        def rollback(self) -> None:
            if not self._hasBegun:
                raise RuntimeError('Invalid state to roll back transaction')

            if self._onCommitCallback:
                try:
                    self._onRollbackCallback()
                except Exception as ex:
                    logging.error('MultiverseDb transaction rollback callback threw exception')

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

    _SophontsTableName = 'sophonts'
    _SophontsTableSchema = 1

    _SystemsTableName = 'systems'
    _SystemsTableSchema = 1

    _NobilitiesTableName = 'nobilities'
    _NobilitiesTableSchema = 1

    _TradeCodesTableName = 'trade_codes'
    _TradeCodesTableSchema = 1

    _SophontPopulationsTableName = 'sophont_populations'
    _SophontPopulationsTableSchema = 1

    _RulingAllegiancesTableName = 'ruling_allegiances'
    _RulingAllegiancesTableSchema = 1

    _OwningSystemsTableName = 'owning_systems'
    _OwningSystemsTableSchema = 1

    _ColonySystemsTableName = 'colony_systems'
    _ColonySystemsTableSchema = 1

    _ResearchStationTableName = 'research_stations'
    _ResearchStationTableSchema = 1

    _CustomRemarksTableName = 'custom_remarks'
    _CustomRemarksTableSchema = 1

    _BasesTableName = 'bases'
    _BasesTableSchema = 1

    _StarsTableName = 'stars'
    _StarsTableSchema = 1

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

    _SectorTagsTableName = 'sector_tags'
    _SectorTagsTableSchema = 1

    _ProductsTableName = 'products'
    _ProductsTableSchema = 1

    _DefaultUniverseId = 'default'
    _DefaultUniverseAppVersionKey = 'default_universe_app_version'
    _DefaultUniverseTimestampKey = 'default_universe_timestamp'

    _SnapshotTimestampFormat = '%Y-%m-%d %H:%M:%S.%f'

    _lock = threading.RLock() # Recursive lock
    _instance = None # Singleton instance
    _initialised = False
    _appVersion = None
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
        return cls._instance

    def initialise(
            self,
            appVersion: str,
            databasePath: str
            ) -> None:
        if self._initialised:
            raise RuntimeError('The MultiverseDb singleton has already been initialised')

        MultiverseDb._appVersion = appVersion
        MultiverseDb._databasePath = databasePath

        self._initTables()

        MultiverseDb._initialised = True

    def createTransaction(
            self,
            onCommitCallback: typing.Optional[typing.Callable[[], None]] = None,
            onRollbackCallback: typing.Optional[typing.Callable[[], None]] = None
            ) -> Transaction:
        connection = self._createConnection()
        return MultiverseDb.Transaction(
            connection=connection,
            onCommitCallback=onCommitCallback,
            onRollbackCallback=onRollbackCallback)

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

            importTimestamp = MultiverseDb._readSnapshotTimestamp(
                directoryPath=directoryPath)

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

        onCommit = onRollback = None
        if progressCallback:
            onCommit = lambda: progressCallback('Saving!', 0, 0)
            onRollback = lambda: progressCallback('Rolling Back!', 0, 0)
        with self.createTransaction(onCommitCallback=onCommit, onRollbackCallback=onRollback) as transaction:
            connection = transaction.connection()
            self._internalImportDefaultUniverse(
                directoryPath=directoryPath,
                cursor=connection.cursor(),
                progressCallback=progressCallback)

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
            insertProgressCallback = lambda milieu, name, progress, total: progressCallback(f'Saving: {milieu} - {name}' if progress != total else 'Saving: Complete!', progress, total)

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
            readProgressCallback = lambda milieu, name, progress, total: progressCallback(f'Loading: {milieu} - {name}' if progress != total else 'Loading: Complete!', progress, total)

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

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._UniversesTableName,
                requiredSchemaVersion=MultiverseDb._UniversesTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='name', columnType=ColumnDef.ColumnType.Text, isNullable=False, isUnique=True),
                    ColumnDef(columnName='description', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='notes', columnType=ColumnDef.ColumnType.Text, isNullable=True)])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._SectorsTableName,
                requiredSchemaVersion=MultiverseDb._SectorsTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='universe_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._UniversesTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='milieu', columnType=ColumnDef.ColumnType.Text, isNullable=False),
                    ColumnDef(columnName='sector_x', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='sector_y', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='primary_name', columnType=ColumnDef.ColumnType.Text, isNullable=False),
                    ColumnDef(columnName='primary_language', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='abbreviation', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='sector_label', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='selected', columnType=ColumnDef.ColumnType.Boolean, isNullable=False),
                    ColumnDef(columnName='credits', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='publication', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='author', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='publisher', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='reference', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='notes', columnType=ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    UniqueConstraintDef(columnNames=['universe_id', 'milieu', 'sector_x', 'sector_y'])])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._AlternateNamesTableName,
                requiredSchemaVersion=MultiverseDb._AlternateNamesTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='sector_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='name', columnType=ColumnDef.ColumnType.Text, isNullable=False),
                    ColumnDef(columnName='language', columnType=ColumnDef.ColumnType.Text, isNullable=True)])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._SubsectorNamesTableName,
                requiredSchemaVersion=MultiverseDb._SubsectorNamesTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='sector_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='code', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              validRange=('A', 'P')),
                    ColumnDef(columnName='name', columnType=ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    UniqueConstraintDef(columnNames=['sector_id', 'code'])])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._AllegiancesTableName,
                requiredSchemaVersion=MultiverseDb._AllegiancesTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='sector_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='code', columnType=ColumnDef.ColumnType.Text, isNullable=False),
                    ColumnDef(columnName='name', columnType=ColumnDef.ColumnType.Text, isNullable=False),
                    ColumnDef(columnName='legacy', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='base', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='route_colour', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='route_style', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='route_width', columnType=ColumnDef.ColumnType.Real, isNullable=True),
                    ColumnDef(columnName='border_colour', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='border_style', columnType=ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    UniqueConstraintDef(columnNames=['sector_id', 'code'])])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._SophontsTableName,
                requiredSchemaVersion=MultiverseDb._SophontsTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='sector_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='code', columnType=ColumnDef.ColumnType.Text, isNullable=False),
                    ColumnDef(columnName='name', columnType=ColumnDef.ColumnType.Text, isNullable=False),
                    ColumnDef(columnName='is_major', columnType=ColumnDef.ColumnType.Boolean, isNullable=False)],
                uniqueConstraints=[
                    UniqueConstraintDef(columnNames=['sector_id', 'code']),
                    UniqueConstraintDef(columnNames=['sector_id', 'name'])])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._SystemsTableName,
                requiredSchemaVersion=MultiverseDb._SystemsTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='sector_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='hex_x', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='hex_y', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='name', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='starport', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='world_size', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='atmosphere', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='hydrographics', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='population', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='government', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='law_level', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='tech_level', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='resources', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='labour', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='infrastructure', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='efficiency', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='heterogeneity', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='acceptance', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='strangeness', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='symbols', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='population_multiplier', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='planetoid_belts', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='gas_giants', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='zone', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='system_worlds', columnType=ColumnDef.ColumnType.Integer, isNullable=True),
                    ColumnDef(columnName='allegiance_id', columnType=ColumnDef.ColumnType.Text, isNullable=True,
                              foreignTableName=MultiverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.SetNull),
                    ColumnDef(columnName='notes', columnType=ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    UniqueConstraintDef(columnNames=['sector_id', 'hex_x', 'hex_y'])])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._NobilitiesTableName,
                requiredSchemaVersion=MultiverseDb._NobilitiesTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='system_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SystemsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='code', columnType=ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    UniqueConstraintDef(columnNames=['system_id', 'code'])])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._TradeCodesTableName,
                requiredSchemaVersion=MultiverseDb._TradeCodesTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='system_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SystemsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='code', columnType=ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    UniqueConstraintDef(columnNames=['system_id', 'code'])])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._SophontPopulationsTableName,
                requiredSchemaVersion=MultiverseDb._SophontPopulationsTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='system_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SystemsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='sophont_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SophontsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='percentage', columnType=ColumnDef.ColumnType.Integer, isNullable=True),
                    ColumnDef(columnName='is_home_world', columnType=ColumnDef.ColumnType.Boolean, isNullable=False),
                    ColumnDef(columnName='is_die_back', columnType=ColumnDef.ColumnType.Boolean, isNullable=False)],
                uniqueConstraints=[
                    UniqueConstraintDef(columnNames=['system_id', 'sophont_id'])])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._RulingAllegiancesTableName,
                requiredSchemaVersion=MultiverseDb._RulingAllegiancesTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='system_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SystemsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='allegiance_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade)],
                uniqueConstraints=[
                    UniqueConstraintDef(columnNames=['system_id', 'allegiance_id'])])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._OwningSystemsTableName,
                requiredSchemaVersion=MultiverseDb._OwningSystemsTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='system_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SystemsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='hex_x', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='hex_y', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    # NOTE: This intentionally stores the abbreviation rather
                    # than the sector id so that the referenced sector doesn't
                    # need to exist in the DB at the point this sector was
                    # imported. This avoids the chicken and egg situation where
                    # it wouldn't be possible to import two sectors that
                    # reference each other as which ever was imported first
                    # would need the sector id of a sector that hasn't been
                    # imported yet.
                    ColumnDef(columnName='sector_abbreviation', columnType=ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    UniqueConstraintDef(columnNames=['system_id', 'hex_x', 'hex_y', 'sector_abbreviation'])])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._ColonySystemsTableName,
                requiredSchemaVersion=MultiverseDb._ColonySystemsTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='system_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SystemsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='hex_x', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='hex_y', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    # NOTE: See comment on owning systems as to why this is the
                    # abbreviation rather than the sector id
                    ColumnDef(columnName='sector_abbreviation', columnType=ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    UniqueConstraintDef(columnNames=['system_id', 'hex_x', 'hex_y', 'sector_abbreviation'])])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._ResearchStationTableName,
                requiredSchemaVersion=MultiverseDb._ResearchStationTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='system_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SystemsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='code', columnType=ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    UniqueConstraintDef(columnNames=['system_id', 'code'])])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._CustomRemarksTableName,
                requiredSchemaVersion=MultiverseDb._CustomRemarksTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='system_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SystemsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='remark', columnType=ColumnDef.ColumnType.Text, isNullable=False)])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._BasesTableName,
                requiredSchemaVersion=MultiverseDb._BasesTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='system_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SystemsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='code', columnType=ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    UniqueConstraintDef(columnNames=['system_id', 'code'])])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._StarsTableName,
                requiredSchemaVersion=MultiverseDb._StarsTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='system_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SystemsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='luminosity_class', columnType=ColumnDef.ColumnType.Text, isNullable=False),
                    ColumnDef(columnName='spectral_class', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='spectral_scale', columnType=ColumnDef.ColumnType.Text, isNullable=True)])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._RoutesTableName,
                requiredSchemaVersion=MultiverseDb._RoutesTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='sector_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='start_hex_x', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='start_hex_y', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='end_hex_x', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='end_hex_y', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='start_offset_x', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='start_offset_y', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='end_offset_x', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='end_offset_y', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='type', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='style', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='colour', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='width', columnType=ColumnDef.ColumnType.Real, isNullable=True),
                    ColumnDef(columnName='allegiance_id', columnType=ColumnDef.ColumnType.Text, isNullable=True,
                              foreignTableName=MultiverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.SetNull)])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._BordersTableName,
                requiredSchemaVersion=MultiverseDb._BordersTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='sector_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='allegiance_id', columnType=ColumnDef.ColumnType.Text, isNullable=True,
                              foreignTableName=MultiverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.SetNull),
                    ColumnDef(columnName='style', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='colour', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='label', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    # NOTE: The label position is stored as an offset in world space from the
                    # origin of the sector (top, left). An offset is used rather than storing
                    # world space coordinates to keep sector data relative to the sector. It
                    # will make it easier if we ever want to move a sector
                    ColumnDef(columnName='label_x', columnType=ColumnDef.ColumnType.Real, isNullable=True),
                    ColumnDef(columnName='label_y', columnType=ColumnDef.ColumnType.Real, isNullable=True),
                    ColumnDef(columnName='show_label', columnType=ColumnDef.ColumnType.Boolean, isNullable=False),
                    ColumnDef(columnName='wrap_label', columnType=ColumnDef.ColumnType.Boolean, isNullable=False)])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._BorderHexesTableName,
                requiredSchemaVersion=MultiverseDb._BorderHexesTableSchema,
                columns=[
                    ColumnDef(columnName='border_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._BordersTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='hex_x', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='hex_y', columnType=ColumnDef.ColumnType.Integer, isNullable=False)])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._RegionsTableName,
                requiredSchemaVersion=MultiverseDb._RegionsTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='sector_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='colour', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='label', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    # NOTE: See note on borders about coordinate space used for world x/y
                    ColumnDef(columnName='label_x', columnType=ColumnDef.ColumnType.Real, isNullable=True),
                    ColumnDef(columnName='label_y', columnType=ColumnDef.ColumnType.Real, isNullable=True),
                    ColumnDef(columnName='show_label', columnType=ColumnDef.ColumnType.Boolean, isNullable=False),
                    ColumnDef(columnName='wrap_label', columnType=ColumnDef.ColumnType.Boolean, isNullable=False)])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._RegionHexesTableName,
                requiredSchemaVersion=MultiverseDb._RegionHexesTableSchema,
                columns=[
                    ColumnDef(columnName='region_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._RegionsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='hex_x', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='hex_y', columnType=ColumnDef.ColumnType.Integer, isNullable=False)])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._LabelsTableName,
                requiredSchemaVersion=MultiverseDb._LabelsTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='sector_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='text', columnType=ColumnDef.ColumnType.Text, isNullable=False),
                    ColumnDef(columnName='x', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='y', columnType=ColumnDef.ColumnType.Integer, isNullable=False),
                    ColumnDef(columnName='colour', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='size', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='wrap', columnType=ColumnDef.ColumnType.Boolean, isNullable=False)])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._SectorTagsTableName,
                requiredSchemaVersion=MultiverseDb._SectorTagsTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='sector_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='tag', columnType=ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    UniqueConstraintDef(columnNames=['sector_id', 'tag'])])

            self._internalCreateTable(
                cursor=cursor,
                tableName=MultiverseDb._ProductsTableName,
                requiredSchemaVersion=MultiverseDb._ProductsTableSchema,
                columns=[
                    ColumnDef(columnName='id', columnType=ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    ColumnDef(columnName='sector_id', columnType=ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=ColumnDef.ForeignKeyDeleteOp.Cascade),
                    ColumnDef(columnName='publication', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='author', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='publisher', columnType=ColumnDef.ColumnType.Text, isNullable=True),
                    ColumnDef(columnName='reference', columnType=ColumnDef.ColumnType.Text, isNullable=True)])

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
            cursor: sqlite3.Cursor,
            table: str,
            version: int
            ) -> None:
        logging.debug(f'MultiverseDb setting schema for \'{table}\' table to {version}')
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

    def _readSchemaVersion(
            self,
            cursor: sqlite3.Cursor,
            table: str
            ) -> typing.Optional[int]:
        logging.debug(f'MultiverseDb reading schema for \'{table}\' table')
        sql = """
            SELECT version
            FROM {table}
            WHERE name = :name
            LIMIT 1;
            """.format(table=MultiverseDb._TableSchemaTableName)
        cursor.execute(sql, {'name': table})
        rowData = cursor.fetchone()
        return rowData[0] if rowData else None

    def _createColumnIndex(
            self,
            cursor: sqlite3.Cursor,
            table: str,
            column: str,
            unique: bool
            ) -> None:
        logging.debug(f'MultiverseDb creating index for \'{column}\' in table \'{table}\'')
        database.createColumnIndex(table=table, column=column, unique=unique, cursor=cursor)

    def _createMultiColumnIndex(
            self,
            cursor: sqlite3.Cursor,
            table: str,
            columns: typing.Collection[str],
            unique: bool
            ) -> None:
        logging.debug(f'MultiverseDb creating index for \'{','.join(columns)}\' in table \'{table}\'')
        database.createMultiColumnIndex(table=table, columns=columns, unique=unique, cursor=cursor)

    def _setMetadata(
            self,
            cursor: sqlite3.Cursor,
            key: str,
            value: str
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
            cursor: sqlite3.Cursor,
            key: str
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

    def _internalCreateTable(
            self,
            cursor: sqlite3.Cursor,
            tableName: str,
            columns: typing.Collection[ColumnDef],
            requiredSchemaVersion: int,
            # The unique list is a list containing the lists of column names
            # to create unique constraints for
            uniqueConstraints: typing.Optional[typing.Collection[UniqueConstraintDef]] = None,
            # The indexes list is a list containing the lists of column names
            # to index together (i.e. multi-column indexes)
            columnIndexes: typing.Optional[typing.Collection[ColumnIndexDef]] = None,
            ) -> None:
        tableExists = database.checkIfTableExists(
            tableName=tableName,
            cursor=cursor)
        if tableExists:
            currentSchemaVersion = self._readSchemaVersion(
                table=tableName,
                cursor=cursor)
            if currentSchemaVersion is None or currentSchemaVersion != requiredSchemaVersion:
                raise MultiverseDb.TableVersionException(
                    table=tableName,
                    required=requiredSchemaVersion,
                    current=currentSchemaVersion)

            return # Table exists with correct version

        sql = f'CREATE TABLE {tableName} (\n'

        for column in columns:
            sql += '  '
            sql += column.columnName()

            if column.columnType() == ColumnDef.ColumnType.Text:
                sql += ' TEXT'
            elif column.columnType() == ColumnDef.ColumnType.Integer:
                sql += ' INTEGER'
            elif column.columnType() == ColumnDef.ColumnType.Real:
                sql += ' REAL'
            elif column.columnType() == ColumnDef.ColumnType.Boolean:
                sql += ' INTEGER'
            else:
                raise RuntimeError('Unsupported column type {type} for column \'{column}\' when creating table \'{table}\''.format(
                    type=column.columnType(),
                    column=column.columnName(),
                    table=tableName))

            if column.isPrimaryKey():
                sql += ' PRIMARY KEY'
            else:
                if not column.isNullable():
                    sql += ' NOT NULL'

                if column.isUnique():
                    sql += ' UNIQUE'

            sql += ',\n'

        for column in columns:
            if column.hasForeignKey():
                if column.foreignDeleteOp() is ColumnDef.ForeignKeyDeleteOp.Cascade:
                    deleteOp = 'CASCADE'
                elif column.foreignDeleteOp() is ColumnDef.ForeignKeyDeleteOp.SetNull:
                    deleteOp = 'SET NULL'
                else:
                    raise RuntimeError('Unsupported foreign key operation {op} for column \'{column}\' when creating table \'{table}\''.format(
                        type=column.foreignDeleteOp(),
                        column=column.columnName(),
                        table=tableName))

                sql += '  FOREIGN KEY({column}) REFERENCES {foreignTable}({foreignColumn}) ON DELETE {deleteOp},\n'.format(
                    column=column.columnName(),
                    foreignTable=column.foreignTableName(),
                    foreignColumn=column.foreignColumnName(),
                    deleteOp=deleteOp)

        for column in columns:
            if column.columnType() is ColumnDef.ColumnType.Boolean:
                # Add constraint that boolean columns can only have value 0 or 1
                sql += '  CHECK ({column} IN (0, 1)),\n'.format(
                    column=column.columnName())
            else:
                validRange = column.validRange()
                if validRange:
                    if column.columnType() is ColumnDef.ColumnType.Text:
                        sql += '  CHECK ({column} BETWEEN \'{min}\' AND \'{max}\'),\n'.format(
                            column=column.columnName(),
                            min=validRange[0],
                            max=validRange[1])
                    else:
                        sql += '  CHECK ({column} BETWEEN {min} AND {max}),\n'.format(
                            column=column.columnName(),
                            min=validRange[0],
                            max=validRange[1])

        # Add any unique constraints
        if uniqueConstraints:
            for uniqueConstraint in uniqueConstraints:
                sql += '  UNIQUE ({columns}),\n'.format(columns=', '.join(uniqueConstraint.columnNames()))

        sql = sql.rstrip(',\n')
        sql += '\n);'

        logging.info(f'MultiverseDb creating table \'{tableName}\'')
        cursor.execute(sql)

        # Create index on foreign key columns and columns where an index has explicitly
        # been requested. Foreign key columns are indexes as cascade delete performance
        # sucks without them
        for column in columns:
            if column.isPrimaryKey():
                # Sqlite should automatically create an index for the primary key.
                # If the column type is TEXT then an explicitly index is created.
                # if the column type is INTEGER then the column is an alias for the
                # internal Sqlite row index which is automatically indexes.
                # NOTE: This is different to what I have in other DB code as
                # previously I had thought it didn't automatically create an index
                # for TEXT primary keys.
                continue

            if column.hasForeignKey() or column.isIndexed():
                self._createColumnIndex(
                    table=tableName,
                    column=column.columnName(),
                    unique=column.isUnique(),
                    cursor=cursor)

        # Create table specific column indexes
        if columnIndexes:
            for index in columnIndexes:
                self._createMultiColumnIndex(
                    table=tableName,
                    columns=index.columnNames(),
                    unique=index.isUnique(),
                    cursor=cursor)

        # Write schema version to schema table
        self._writeSchemaVersion(
            table=tableName,
            version=requiredSchemaVersion,
            cursor=cursor)

    # This function returns True if imported or False if nothing was
    # done due to the snapshot being older than the current snapshot.
    # If forceImport is true the snapshot will be imported even if
    # it is older
    # TODO: I'm not sure if this should live here or be separate like
    # the custom sector code. It feels like the two types of operation
    # should be handled consistently
    def _internalImportDefaultUniverse(
            self,
            cursor: sqlite3.Cursor,
            directoryPath: str,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        importTimestamp = MultiverseDb._readSnapshotTimestamp(
            directoryPath=directoryPath)

        rawStockAllegiances = multiverse.readSnapshotStockAllegiances()
        rawStockSophonts = multiverse.readSnapshotStockSophonts()
        rawStockStyleSheet = multiverse.readSnapshotStyleSheet()

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
            universeInfo = survey.parseUniverseInfo(content=universeInfoContent)

            sectorNames = []
            for sectorInfo in universeInfo.sectorInfos():
                nameInfos = sectorInfo.nameInfos()
                canonicalName = nameInfos[0].name() if nameInfos else None
                if not canonicalName:
                    logging.warning(f'Default universe import ignoring sector with no name in {universeInfoPath}')
                    continue
                sectorNames.append(canonicalName)
                totalSectorCount += 1

            milieuSectors.append((milieu, sectorNames))

        rawData: typing.List[typing.Tuple[
            str, # Milieu
            survey.RawMetadata,
            typing.Collection[survey.RawWorld]
            ]] = []
        progressCount = 0
        for milieu, sectorNames in milieuSectors:
            milieuPath = os.path.join(universePath, milieu)
            for sectorName in sectorNames:
                if progressCallback:
                    try:
                        progressCallback(
                            f'Reading: {milieu} - {sectorName}',
                            progressCount,
                            totalSectorCount)
                        progressCount += 1
                    except Exception as ex:
                        logging.warning('Default universe import progress callback threw an exception', exc_info=ex)

                try:
                    escapedName = common.encodeFileName(rawFileName=sectorName)

                    metadataPath = os.path.join(milieuPath, escapedName + '.xml')
                    with open(metadataPath, 'r', encoding='utf-8-sig') as file:
                        rawMetadata = survey.parseXMLMetadata(content=file.read())

                    sectorPath = os.path.join(milieuPath, escapedName + '.sec')
                    with open(sectorPath, 'r', encoding='utf-8-sig') as file:
                        rawSystems = survey.parseT5ColumnSector(content=file.read())
                    rawData.append((milieu, rawMetadata, rawSystems))
                except Exception as ex:
                    logging.error(f'Default universe import failed to load data for sector {sectorName} from {milieu}', exc_info=ex)

        if progressCallback:
            try:
                progressCallback(
                    f'Reading: Complete!',
                    totalSectorCount,
                    totalSectorCount)
            except Exception as ex:
                logging.warning('Default universe import progress callback threw an exception', exc_info=ex)

        dbUniverse = multiverse.convertRawUniverseToDbUniverse(
            universeId=MultiverseDb._DefaultUniverseId,
            universeName='Default Universe',
            isCustom=False,
            rawSectors=rawData,
            rawStockAllegiances=rawStockAllegiances,
            rawStockSophonts=rawStockSophonts,
            rawStockStyleSheet=rawStockStyleSheet,
            progressCallback=progressCallback)

        self._internalDeleteUniverse(
            universeId=MultiverseDb._DefaultUniverseId,
            cursor=cursor)

        insertProgressCallback = None
        if progressCallback:
            insertProgressCallback = \
                lambda milieu, name, progress, total: progressCallback(f'Importing: {milieu} - {name}' if progress != total else 'Importing: Complete!', progress, total)
        self._internalInsertUniverse(
            universe=dbUniverse,
            updateDefault=True,
            cursor=cursor,
            progressCallback=insertProgressCallback)

        # Write the app version fpr the import. This future new versions of the
        # app to check which version the custom universe was imported with and
        # force an re-import if needed (e.g. if I've found a bug with my import
        # process).
        self._setMetadata(
            key=MultiverseDb._DefaultUniverseAppVersionKey,
            value=MultiverseDb._appVersion,
            cursor=cursor)

        self._setMetadata(
            key=MultiverseDb._DefaultUniverseTimestampKey,
            value=importTimestamp.isoformat(),
            cursor=cursor)

    def _internalInsertUniverse(
            self,
            cursor: sqlite3.Cursor,
            universe: multiverse.DbUniverse,
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
                    try:
                        progressCallback(
                            sector.milieu(),
                            sector.primaryName(),
                            progressCount,
                            totalSectorCount)
                    except Exception as ex:
                        logging.warning('MultiverseDb universe insert progress callback threw an exception', exc_info=ex)

                if not updateDefault and not sector.isCustom():
                    continue # Only write custom sectors

                self._internalInsertSector(
                    sector=sector,
                    cursor=cursor)

        if progressCallback:
            try:
                progressCallback(
                    None,
                    None,
                    totalSectorCount,
                    totalSectorCount)
            except Exception as ex:
                logging.warning('MultiverseDb universe insert progress callback threw an exception', exc_info=ex)

    def _internalReadUniverse(
            self,
            cursor: sqlite3.Cursor,
            universeId: str,
            includeDefaultSectors: bool,
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

        sql = """
            SELECT id, primary_name, milieu
            FROM {table}
            WHERE universe_id = :id
            """.format(table=MultiverseDb._SectorsTableName)
        parameters = {'id': universeId}
        if includeDefaultSectors:
            sql += """
                UNION ALL

                SELECT d.id, d.primary_name, d.milieu
                FROM {table} d
                WHERE d.universe_id = :default_id
                AND NOT EXISTS (
                    SELECT 1
                    FROM {table} u
                    WHERE u.universe_id = :id
                        AND u.milieu = d.milieu
                        AND u.sector_x = d.sector_x
                        AND u.sector_y = d.sector_y
                )
                """.format(table=MultiverseDb._SectorsTableName)
            parameters['default_id'] = MultiverseDb._DefaultUniverseId
        sql += ';'

        cursor.execute(sql, parameters)
        resultData = cursor.fetchall()
        totalSectorCount = len(resultData)
        sectors = []
        for progressCount, row in enumerate(resultData):
            sectorId = row[0]
            sectorName = row[1]
            sectorMilieu = row[2]

            if progressCallback:
                try:
                    progressCallback(
                        sectorMilieu,
                        sectorName,
                        progressCount,
                        totalSectorCount)
                except Exception as ex:
                    logging.warning('MultiverseDb universe read progress callback threw an exception', exc_info=ex)

            sector = self._internalReadSector(
                sectorId=sectorId,
                cursor=cursor)
            if not sector:
                # TODO: Some kind of logging or error handling?
                continue
            sectors.append(sector)

        if progressCallback:
            try:
                progressCallback(
                    None,
                    None,
                    totalSectorCount,
                    totalSectorCount)
            except Exception as ex:
                logging.warning('MultiverseDb universe read progress callback threw an exception', exc_info=ex)

        return multiverse.DbUniverse(
            id=universeId,
            name=name,
            description=description,
            notes=notes,
            sectors=sectors)

    def _internalDeleteUniverse(
            self,
            cursor: sqlite3.Cursor,
            universeId: str
            ) -> typing.Optional[multiverse.DbUniverse]:
        sql = """
            DELETE FROM {table}
            WHERE id = :id
            """.format(
            table=MultiverseDb._UniversesTableName)
        cursor.execute(sql, {'id': universeId})

    def _internalInsertSector(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        sql = """
            INSERT INTO {table} (id, universe_id, milieu,
                sector_x, sector_y, primary_name, primary_language,
                abbreviation, sector_label, selected,
                credits, publication, author, publisher, reference, notes)
            VALUES (:id, :universe_id, :milieu,
                :sector_x, :sector_y, :primary_name, :primary_language,
                :abbreviation, :sector_label, :selected,
                :credits, :publication, :author, :publisher, :reference, :notes);
            """.format(table=MultiverseDb._SectorsTableName)
        rows = {
            'id': sector.id(),
            'universe_id': sector.universeId(),
            'milieu': sector.milieu(),
            'sector_x': sector.sectorX(),
            'sector_y': sector.sectorY(),
            'primary_name': sector.primaryName(),
            'primary_language': sector.primaryLanguage(),
            'abbreviation': sector.abbreviation(),
            'sector_label': sector.sectorLabel(),
            'selected': 1 if sector.selected() else 0,
            'credits': sector.credits(),
            'publication': sector.publication(),
            'author': sector.author(),
            'publisher': sector.publisher(),
            'reference': sector.reference(),
            'notes': sector.notes()}
        cursor.execute(sql, rows)

        if sector.alternateNames():
            sql = """
                INSERT INTO {table} (id, sector_id, name, language)
                VALUES (:id, :sector_id, :name, :language);
                """.format(table=MultiverseDb._AlternateNamesTableName)
            rows = []
            for alternateName in sector.alternateNames():
                rows.append({
                    'id': alternateName.id(),
                    'sector_id': alternateName.sectorId(),
                    'name': alternateName.name(),
                    'language': alternateName.language()})
            cursor.executemany(sql, rows)

        if sector.subsectorNames():
            sql = """
                INSERT INTO {table} (id, sector_id, code, name)
                VALUES (:id, :sector_id, :code, :name);
                """.format(table=MultiverseDb._SubsectorNamesTableName)
            rows = []
            for subsectorName in sector.subsectorNames():
                rows.append({
                    'id': subsectorName.id(),
                    'sector_id': subsectorName.sectorId(),
                    'code': subsectorName.code(),
                    'name': subsectorName.name()})
            cursor.executemany(sql, rows)

        if sector.allegiances():
            sql = """
                INSERT INTO {table} (id, sector_id, code, name, legacy, base,
                    route_colour, route_style, route_width,
                    border_colour, border_style)
                VALUES (:id, :sector_id, :code, :name, :legacy, :base,
                    :route_colour, :route_style, :route_width,
                    :border_colour, :border_style);
                """.format(table=MultiverseDb._AllegiancesTableName)
            rows = []
            for allegiance in sector.allegiances():
                rows.append({
                    'id': allegiance.id(),
                    'sector_id': allegiance.sectorId(),
                    'code': allegiance.code(),
                    'name': allegiance.name(),
                    'legacy': allegiance.legacy(),
                    'base': allegiance.base(),
                    'route_colour': allegiance.routeColour(),
                    'route_style': allegiance.routeStyle(),
                    'route_width': allegiance.routeWidth(),
                    'border_colour': allegiance.borderColour(),
                    'border_style': allegiance.borderStyle()})
            cursor.executemany(sql, rows)

        if sector.sophonts():
            sql = """
                INSERT INTO {table} (id, sector_id, code, name, is_major)
                VALUES (:id, :sector_id, :code, :name, :is_major);
                """.format(table=MultiverseDb._SophontsTableName)
            rows = []
            for sophont in sector.sophonts():
                rows.append({
                    'id': sophont.id(),
                    'sector_id': sophont.sectorId(),
                    'code': sophont.code(),
                    'name': sophont.name(),
                    'is_major': 1 if sophont.isMajor() else 0})
            cursor.executemany(sql, rows)

        if sector.systems():
            systemRows = []
            nobilitiesRows = []
            tradeCodeRows = []
            sophontPopulationRows = []
            rulingAllegianceRows = []
            owningSystemRows = []
            colonySystemRows = []
            researchStationRows = []
            customRemarkRows = []
            baseRows = []
            starRows = []
            for system in sector.systems():
                allegiance = system.allegiance()
                systemRows.append({
                    'id': system.id(),
                    'sector_id': system.sectorId(),
                    'hex_x': system.hexX(),
                    'hex_y': system.hexY(),
                    'name': system.name(),
                    'starport': system.starport(),
                    'world_size': system.worldSize(),
                    'atmosphere': system.atmosphere(),
                    'hydrographics': system.hydrographics(),
                    'population': system.population(),
                    'government': system.government(),
                    'law_level': system.lawLevel(),
                    'tech_level': system.techLevel(),
                    'resources': system.resources(),
                    'labour': system.labour(),
                    'infrastructure': system.infrastructure(),
                    'efficiency': system.efficiency(),
                    'heterogeneity': system.heterogeneity(),
                    'acceptance': system.acceptance(),
                    'strangeness': system.strangeness(),
                    'symbols': system.symbols(),
                    'population_multiplier': system.populationMultiplier(),
                    'planetoid_belts': system.planetoidBelts(),
                    'gas_giants': system.gasGiants(),
                    'zone': system.zone(),
                    'system_worlds': system.systemWorlds(),
                    'allegiance_id': allegiance.id() if allegiance else None,
                    'notes': system.notes()})

                if system.nobilities():
                    for nobility in system.nobilities():
                        nobilitiesRows.append({
                            'id': nobility.id(),
                            'system_id': nobility.systemId(),
                            'code': nobility.code()})

                if system.tradeCodes():
                    for code in system.tradeCodes():
                        tradeCodeRows.append({
                            'id': code.id(),
                            'system_id': code.systemId(),
                            'code': code.code()})

                if system.sophontPopulations():
                    for sophont in system.sophontPopulations():
                        sophontPopulationRows.append({
                            'id': sophont.id(),
                            'system_id': sophont.systemId(),
                            'sophont_id': sophont.sophont().id(),
                            'percentage': sophont.percentage(),
                            'is_home_world': 1 if sophont.isHomeWorld() else 0,
                            'is_die_back': 1 if sophont.isDieBack() else 0})

                if system.rulingAllegiances():
                    for rulingAllegiance in system.rulingAllegiances():
                        rulingAllegianceRows.append({
                            'id': rulingAllegiance.id(),
                            'system_id': rulingAllegiance.systemId(),
                            'allegiance_id': rulingAllegiance.allegiance().id()})

                if system.owningSystems():
                    for owningSystem in system.owningSystems():
                        owningSystemRows.append({
                            'id': owningSystem.id(),
                            'system_id': owningSystem.systemId(),
                            'hex_x': owningSystem.hexX(),
                            'hex_y': owningSystem.hexY(),
                            'sector_abbreviation': owningSystem.sectorAbbreviation()})

                if system.colonySystems():
                    for colonySystem in system.colonySystems():
                        colonySystemRows.append({
                            'id': colonySystem.id(),
                            'system_id': colonySystem.systemId(),
                            'hex_x': colonySystem.hexX(),
                            'hex_y': colonySystem.hexY(),
                            'sector_abbreviation': colonySystem.sectorAbbreviation()})

                if system.researchStations():
                    for station in system.researchStations():
                        researchStationRows.append({
                            'id': station.id(),
                            'system_id': station.systemId(),
                            'code': station.code()})

                if system.customRemarks():
                    for remark in system.customRemarks():
                        customRemarkRows.append({
                            'id': remark.id(),
                            'system_id': remark.systemId(),
                            'remark': remark.remark()})

                if system.bases():
                    for base in system.bases():
                        baseRows.append({
                            'id': base.id(),
                            'system_id': base.systemId(),
                            'code': base.code()})

                if system.stars():
                    for star in system.stars():
                        starRows.append({
                            'id': star.id(),
                            'system_id': star.systemId(),
                            'luminosity_class': star.luminosityClass(),
                            'spectral_class': star.spectralClass(),
                            'spectral_scale': star.spectralScale()})

            if systemRows:
                sql = """
                    INSERT INTO {table} (id, sector_id, hex_x, hex_y, name,
                        starport, world_size, atmosphere, hydrographics, population, government, law_level, tech_level,
                        resources, labour, infrastructure, efficiency,
                        heterogeneity, acceptance, strangeness, symbols,
                        population_multiplier, planetoid_belts, gas_giants,
                        zone, system_worlds, allegiance_id, notes)
                    VALUES (:id, :sector_id, :hex_x, :hex_y, :name,
                        :starport, :world_size, :atmosphere, :hydrographics, :population, :government, :law_level, :tech_level,
                        :resources, :labour, :infrastructure, :efficiency,
                        :heterogeneity, :acceptance, :strangeness, :symbols,
                        :population_multiplier, :planetoid_belts, :gas_giants,
                        :zone, :system_worlds, :allegiance_id, :notes);
                    """.format(table=MultiverseDb._SystemsTableName)
                cursor.executemany(sql, systemRows)
            if nobilitiesRows:
                sql = """
                    INSERT INTO {table} (id, system_id, code)
                    VALUES (:id, :system_id, :code)
                    """.format(table=MultiverseDb._NobilitiesTableName)
                cursor.executemany(sql, nobilitiesRows)
            if tradeCodeRows:
                sql = """
                    INSERT INTO {table} (id, system_id, code)
                    VALUES (:id, :system_id, :code)
                    """.format(table=MultiverseDb._TradeCodesTableName)
                cursor.executemany(sql, tradeCodeRows)
            if sophontPopulationRows:
                sql = """
                    INSERT INTO {table} (id, system_id, sophont_id, percentage, is_home_world, is_die_back)
                    VALUES (:id, :system_id, :sophont_id, :percentage, :is_home_world, :is_die_back)
                    """.format(table=MultiverseDb._SophontPopulationsTableName)
                cursor.executemany(sql, sophontPopulationRows)
            if rulingAllegianceRows:
                sql = """
                    INSERT INTO {table} (id, system_id, allegiance_id)
                    VALUES (:id, :system_id, :allegiance_id)
                    """.format(table=MultiverseDb._RulingAllegiancesTableName)
                cursor.executemany(sql, rulingAllegianceRows)
            if owningSystemRows:
                sql = """
                    INSERT INTO {table} (id, system_id, hex_x, hex_y, sector_abbreviation)
                    VALUES (:id, :system_id, :hex_x, :hex_y, :sector_abbreviation)
                    """.format(table=MultiverseDb._OwningSystemsTableName)
                cursor.executemany(sql, owningSystemRows)
            if colonySystemRows:
                sql = """
                    INSERT INTO {table} (id, system_id, hex_x, hex_y, sector_abbreviation)
                    VALUES (:id, :system_id, :hex_x, :hex_y, :sector_abbreviation)
                    """.format(table=MultiverseDb._ColonySystemsTableName)
                cursor.executemany(sql, colonySystemRows)
            if researchStationRows:
                sql = """
                    INSERT INTO {table} (id, system_id, code)
                    VALUES (:id, :system_id, :code);
                    """.format(table=MultiverseDb._ResearchStationTableName)
                cursor.executemany(sql, researchStationRows)
            if customRemarkRows:
                sql = """
                    INSERT INTO {table} (id, system_id, remark)
                    VALUES (:id, :system_id, :remark)
                    """.format(table=MultiverseDb._CustomRemarksTableName)
                cursor.executemany(sql, customRemarkRows)
            if baseRows:
                sql = """
                    INSERT INTO {table} (id, system_id, code)
                    VALUES (:id, :system_id, :code);
                    """.format(table=MultiverseDb._BasesTableName)
                cursor.executemany(sql, baseRows)
            if starRows:
                sql = """
                    INSERT INTO {table} (id, system_id, luminosity_class, spectral_class, spectral_scale)
                    VALUES (:id, :system_id, :luminosity_class, :spectral_class, :spectral_scale);
                    """.format(table=MultiverseDb._StarsTableName)
                cursor.executemany(sql, starRows)

        if sector.routes():
            sql = """
                INSERT INTO {table} (id, sector_id, start_hex_x, start_hex_y, end_hex_x, end_hex_y,
                    start_offset_x, start_offset_y, end_offset_x, end_offset_y, type, style,
                    colour, width, allegiance_id)
                VALUES (:id, :sector_id, :start_hex_x, :start_hex_y, :end_hex_x, :end_hex_y,
                    :start_offset_x, :start_offset_y, :end_offset_x, :end_offset_y, :type, :style,
                    :colour, :width, :allegiance_id);
                """.format(table=MultiverseDb._RoutesTableName)
            rows = []
            for route in sector.routes():
                allegiance = route.allegiance()
                rows.append({
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
                    'type': route.type(),
                    'style': route.style(),
                    'colour': route.colour(),
                    'width': route.width(),
                    'allegiance_id': allegiance.id() if allegiance else None})
            cursor.executemany(sql, rows)

        if sector.borders():
            bordersSql = """
                INSERT INTO {table} (id, sector_id, allegiance_id, style, colour,
                    label, label_x, label_y, show_label, wrap_label)
                VALUES (:id, :sector_id, :allegiance_id, :style, :colour,
                    :label, :label_x, :label_y, :show_label, :wrap_label);
                """.format(table=MultiverseDb._BordersTableName)
            hexesSql =  """
                INSERT INTO {table} (border_id, hex_x, hex_y)
                VALUES (:border_id, :hex_x, :hex_y);
                """.format(table=MultiverseDb._BorderHexesTableName)
            borderRows = []
            hexRows = []
            for border in sector.borders():
                allegiance = border.allegiance()
                borderRows.append({
                    'id': border.id(),
                    'sector_id': border.sectorId(),
                    'allegiance_id': allegiance.id() if allegiance else None,
                    'style': border.style(),
                    'colour': border.colour(),
                    'label': border.label(),
                    'label_x': border.labelX(),
                    'label_y': border.labelY(),
                    'show_label': 1 if border.showLabel() else 0,
                    'wrap_label': 1 if border.wrapLabel() else 0})
                for hexX, hexY in border.hexes():
                    hexRows.append({
                        'border_id': border.id(),
                        'hex_x': hexX,
                        'hex_y': hexY})
            cursor.executemany(bordersSql, borderRows)
            cursor.executemany(hexesSql, hexRows)

        if sector.regions():
            regionsSql = """
                INSERT INTO {table} (id, sector_id, colour, label,
                    label_x, label_y, show_label, wrap_label)
                VALUES (:id, :sector_id, :colour, :label,
                    :label_x, :label_y, :show_label, :wrap_label);
                """.format(table=MultiverseDb._RegionsTableName)
            hexesSql =  """
                INSERT INTO {table} (region_id, hex_x, hex_y)
                VALUES (:region_id, :hex_x, :hex_y);
                """.format(table=MultiverseDb._RegionHexesTableName)
            regionsRows = []
            hexRows = []
            for region in sector.regions():
                regionsRows.append({
                    'id': region.id(),
                    'sector_id': region.sectorId(),
                    'colour': region.colour(),
                    'label': region.label(),
                    'label_x': region.labelX(),
                    'label_y': region.labelY(),
                    'show_label': 1 if region.showLabel() else 0,
                    'wrap_label': 1 if region.wrapLabel() else 0})
                for hexX, hexY in region.hexes():
                    hexRows.append({
                        'region_id': region.id(),
                        'hex_x': hexX,
                        'hex_y': hexY})
            cursor.executemany(regionsSql, regionsRows)
            cursor.executemany(hexesSql, hexRows)

        if sector.labels():
            sql = """
                INSERT INTO {table} (id, sector_id, text, x, y,
                    colour, size, wrap)
                VALUES (:id, :sector_id, :text, :x, :y,
                    :colour, :size, :wrap);
                """.format(table=MultiverseDb._LabelsTableName)
            rows = []
            for label in sector.labels():
                rows.append({
                    'id': label.id(),
                    'sector_id': label.sectorId(),
                    'text': label.text(),
                    'x': label.x(),
                    'y': label.y(),
                    'colour': label.colour(),
                    'size': label.size(),
                    'wrap': 1 if label.wrap() else 0})
            cursor.executemany(sql, rows)

        if sector.tags():
            sql = """
                INSERT INTO {table} (id, sector_id, tag)
                VALUES (:id, :sector_id, :tag);
                """.format(table=MultiverseDb._SectorTagsTableName)
            rows = []
            for tag in sector.tags():
                rows.append({
                    'id': tag.id(),
                    'sector_id': tag.sectorId(),
                    'tag': tag.tag()})
            cursor.executemany(sql, rows)

        if sector.products():
            sql = """
                INSERT INTO {table} (id, sector_id, publication, author,
                    publisher, reference)
                VALUES (:id, :sector_id, :publication, :author,
                    :publisher, :reference);
                """.format(table=MultiverseDb._ProductsTableName)
            rows = []
            for product in sector.products():
                rows.append({
                    'id': product.id(),
                    'sector_id': product.sectorId(),
                    'publication': product.publication(),
                    'author': product.author(),
                    'publisher': product.publisher(),
                    'reference': product.reference()})
            cursor.executemany(sql, rows)

    def _internalReadSector(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.Optional[multiverse.DbSector]:
        sql = """
            SELECT universe_id, milieu, sector_x, sector_y,
                primary_name, primary_language, abbreviation, sector_label, selected,
                credits, publication, author, publisher, reference, notes
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
            isCustom=row[0] != MultiverseDb._DefaultUniverseId,
            milieu=row[1],
            sectorX=row[2],
            sectorY=row[3],
            primaryName=row[4],
            primaryLanguage=row[5],
            abbreviation=row[6],
            sectorLabel=row[7],
            selected=True if row[8] else False,
            credits=row[9],
            publication=row[10],
            author=row[11],
            publisher=row[12],
            reference=row[13],
            notes=row[14])

        sql = """
            SELECT id, name, language
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._AlternateNamesTableName)
        cursor.execute(sql, {'id': sectorId})
        idToAlternateNameMap: typing.Dict[str, multiverse.DbAlternateName] = {}
        for row in cursor.fetchall():
            alternateName = multiverse.DbAlternateName(
                id=row[0],
                name=row[1],
                language=row[2])
            idToAlternateNameMap[alternateName.id()] = alternateName
        sector.setAlternateNames(idToAlternateNameMap.values())

        sql = """
            SELECT id, code, name
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._SubsectorNamesTableName)
        cursor.execute(sql, {'id': sectorId})
        idToSubsectorNameMap: typing.Dict[str, multiverse.DbSubsectorName] = {}
        for row in cursor.fetchall():
            subsectorName = multiverse.DbSubsectorName(
                id=row[0],
                code=row[1],
                name=row[2])
            idToSubsectorNameMap[subsectorName.id()] = subsectorName
        sector.setSubsectorNames(idToSubsectorNameMap.values())

        sql = """
            SELECT id, code, name, legacy, base,
                route_colour, route_style, route_width,
                border_colour, border_style
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._AllegiancesTableName)
        cursor.execute(sql, {'id': sectorId})
        idToAllegianceMap: typing.Dict[str, multiverse.DbAllegiance] = {}
        for row in cursor.fetchall():
            allegiance = multiverse.DbAllegiance(
                id=row[0],
                sectorId=sectorId,
                code=row[1],
                name=row[2],
                legacy=row[3],
                base=row[4],
                routeColour=row[5],
                routeStyle=row[6],
                routeWidth=row[7],
                borderColour=row[8],
                borderStyle=row[9])
            idToAllegianceMap[allegiance.id()] = allegiance
        sector.setAllegiances(idToAllegianceMap.values())

        sql = """
            SELECT id, code, name, is_major
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._SophontsTableName)
        cursor.execute(sql, {'id': sectorId})
        idToSophontMap: typing.Dict[str, multiverse.DbSophont] = {}
        for row in cursor.fetchall():
            sophont = multiverse.DbSophont(
                id=row[0],
                sectorId=sectorId,
                code=row[1],
                name=row[2],
                isMajor=True if row[3] else False)
            idToSophontMap[sophont.id()] = sophont
        sector.setSophonts(idToSophontMap.values())

        sql = """
            SELECT id, hex_x, hex_y, name,
                starport, world_size, atmosphere, hydrographics, population, government, law_level, tech_level,
                resources, labour, infrastructure, efficiency,
                heterogeneity, acceptance, strangeness, symbols,
                population_multiplier, planetoid_belts, gas_giants,
                zone, system_worlds, allegiance_id, notes
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        systems = []
        idToSystemMap: typing.Dict[str, multiverse.DbSystem] = {}
        for row in cursor.fetchall():
            system = multiverse.DbSystem(
                id=row[0],
                hexX=row[1],
                hexY=row[2],
                name=row[3],
                starport=row[4],
                worldSize=row[5],
                atmosphere=row[6],
                hydrographics=row[7],
                population=row[8],
                government=row[9],
                lawLevel=row[10],
                techLevel=row[11],
                resources=row[12],
                labour=row[13],
                infrastructure=row[14],
                efficiency=row[15],
                heterogeneity=row[16],
                acceptance=row[17],
                strangeness=row[18],
                symbols=row[19],
                populationMultiplier=row[20],
                planetoidBelts=row[21],
                gasGiants=row[22],
                zone=row[23],
                systemWorlds=row[24],
                allegiance=idToAllegianceMap.get(row[25]),
                notes=row[26])
            systems.append(system)
            idToSystemMap[system.id()] = system
        sector.setSystems(systems)

        sql = """
            SELECT t.id, t.system_id, t.code
            FROM {nobilitiesTable} AS t
            JOIN {systemsTable} AS s
            ON s.id = t.system_id
            WHERE s.sector_id = :id;
            """.format(
                nobilitiesTable=MultiverseDb._NobilitiesTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        for row in cursor.fetchall():
            system = idToSystemMap[row[1]]
            system.addNobility(multiverse.DbNobility(
                id=row[0],
                systemId=system.id(),
                code=row[2]))

        sql = """
            SELECT t.id, t.system_id, t.code
            FROM {tradeTable} AS t
            JOIN {systemsTable} AS s
            ON s.id = t.system_id
            WHERE s.sector_id = :id;
            """.format(
                tradeTable=MultiverseDb._TradeCodesTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        for row in cursor.fetchall():
            system = idToSystemMap[row[1]]
            system.addTradeCode(multiverse.DbTradeCode(
                id=row[0],
                systemId=system.id(),
                code=row[2]))

        sql = """
            SELECT t.id, t.system_id, t.sophont_id, t.percentage, t.is_home_world, t.is_die_back
            FROM {populationsTable} AS t
            JOIN {systemsTable} AS s
            ON s.id = t.system_id
            WHERE s.sector_id = :id;
            """.format(
                populationsTable=MultiverseDb._SophontPopulationsTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        for row in cursor.fetchall():
            system = idToSystemMap[row[1]]
            sophont = idToSophontMap[row[2]]
            system.addSophontPopulation(multiverse.DbSophontPopulation(
                id=row[0],
                systemId=system.id(),
                sophont=sophont,
                percentage=row[3],
                isHomeWorld=True if row[4] else False,
                isDieBack=True if row[5] else False))

        sql = """
            SELECT t.id, t.system_id, t.allegiance_id
            FROM {rulingTable} AS t
            JOIN {systemsTable} AS s
            ON s.id = t.system_id
            WHERE s.sector_id = :id;
            """.format(
                rulingTable=MultiverseDb._RulingAllegiancesTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        for row in cursor.fetchall():
            system = idToSystemMap[row[1]]
            allegiance = idToAllegianceMap[row[2]]
            system.addRulingAllegiance(multiverse.DbRulingAllegiance(
                id=row[0],
                systemId=system.id(),
                allegiance=allegiance))

        sql = """
            SELECT t.id, t.system_id, t.hex_x, t.hex_y, t.sector_abbreviation
            FROM {ownersTable} AS t
            JOIN {systemsTable} AS s
            ON s.id = t.system_id
            WHERE s.sector_id = :id;
            """.format(
                ownersTable=MultiverseDb._OwningSystemsTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        for row in cursor.fetchall():
            system = idToSystemMap[row[1]]
            system.addOwningSystem(multiverse.DbOwningSystem(
                id=row[0],
                systemId=system.id(),
                hexX=row[2],
                hexY=row[3],
                sectorAbbreviation=row[4]))

        sql = """
            SELECT t.id, t.system_id, t.hex_x, t.hex_y, t.sector_abbreviation
            FROM {coloniesTable} AS t
            JOIN {systemsTable} AS s
            ON s.id = t.system_id
            WHERE s.sector_id = :id;
            """.format(
                coloniesTable=MultiverseDb._ColonySystemsTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        for row in cursor.fetchall():
            system = idToSystemMap[row[1]]
            system.addColonySystem(multiverse.DbColonySystem(
                id=row[0],
                systemId=system.id(),
                hexX=row[2],
                hexY=row[3],
                sectorAbbreviation=row[4]))

        sql = """
            SELECT t.id, t.system_id, t.code
            FROM {stationsTable} AS t
            JOIN {systemsTable} AS s
            ON s.id = t.system_id
            WHERE s.sector_id = :id;
            """.format(
                stationsTable=MultiverseDb._ResearchStationTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        for row in cursor.fetchall():
            system = idToSystemMap[row[1]]
            system.addResearchStation(multiverse.DbResearchStation(
                id=row[0],
                systemId=system.id(),
                code=row[2]))

        sql = """
            SELECT t.id, t.system_id, t.remark
            FROM {remarksTable} AS t
            JOIN {systemsTable} AS s
            ON s.id = t.system_id
            WHERE s.sector_id = :id;
            """.format(
                remarksTable=MultiverseDb._CustomRemarksTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        for row in cursor.fetchall():
            system = idToSystemMap[row[1]]
            system.addCustomRemark(multiverse.DbCustomRemark(
                id=row[0],
                systemId=system.id(),
                remark=row[2]))

        sql = """
            SELECT t.id, t.system_id, t.code
            FROM {basesTable} AS t
            JOIN {systemsTable} AS s
            ON s.id = t.system_id
            WHERE s.sector_id = :id;
            """.format(
                basesTable=MultiverseDb._BasesTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        for row in cursor.fetchall():
            system = idToSystemMap[row[1]]
            system.addBase(multiverse.DbBase(
                id=row[0],
                systemId=system.id(),
                code=row[2]))

        sql = """
            SELECT t.id, t.system_id, t.luminosity_class, t.spectral_class, t.spectral_scale
            FROM {starsTable} AS t
            JOIN {systemsTable} AS s
            ON s.id = t.system_id
            WHERE s.sector_id = :id;
            """.format(
                starsTable=MultiverseDb._StarsTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        for row in cursor.fetchall():
            system = idToSystemMap[row[1]]
            system.addStar(multiverse.DbStar(
                id=row[0],
                systemId=system.id(),
                luminosityClass=row[2],
                spectralClass=row[3],
                spectralScale=row[4]))

        sql = """
            SELECT id, start_hex_x, start_hex_y, end_hex_x, end_hex_y,
                start_offset_x, start_offset_y, end_offset_x, end_offset_y,
                type, style, colour, width, allegiance_id
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
                type=row[9],
                style=row[10],
                colour=row[11],
                width=row[12],
                allegiance=idToAllegianceMap.get(row[13])))
        sector.setRoutes(routes)

        sql = """
            SELECT id, allegiance_id, style, colour, label,
                label_x, label_y, show_label, wrap_label
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
                allegiance=idToAllegianceMap.get(row[1]),
                style=row[2],
                colour=row[3],
                label=row[4],
                labelWorldX=row[5],
                labelWorldY=row[6],
                showLabel=True if row[7] else False,
                wrapLabel=True if row[8] else False))
        sector.setBorders(borders)

        sql = """
            SELECT id, colour, label, label_x, label_y, show_label, wrap_label
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
                colour=row[1],
                label=row[2],
                labelX=row[3],
                labelY=row[4],
                showLabel=True if row[5] else False,
                wrapLabel=True if row[6] else False))
        sector.setRegions(regions)

        sql = """
            SELECT id, text, x, y, colour, size, wrap
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._LabelsTableName)
        cursor.execute(sql, {'id': sectorId})
        labels = []
        for row in cursor.fetchall():
            labels.append(multiverse.DbLabel(
                id=row[0],
                text=row[1],
                x=row[2],
                y=row[3],
                colour=row[4],
                size=row[5],
                wrap=True if row[6] else False))
        sector.setLabels(labels)

        sql = """
            SELECT id, tag
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._SectorTagsTableName)
        cursor.execute(sql, {'id': sectorId})
        tags = []
        for row in cursor.fetchall():
            tags.append(multiverse.DbTag(
                id=row[0],
                tag=row[1]))
        sector.setTags(tags)

        sql = """
            SELECT id, publication, author, publisher, reference
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._ProductsTableName)
        cursor.execute(sql, {'id': sectorId})
        products = []
        for row in cursor.fetchall():
            products.append(multiverse.DbProduct(
                id=row[0],
                publication=row[1],
                author=row[2],
                publisher=row[3],
                reference=row[4]))
        sector.setProducts(products)

        return sector

    def _internalDeleteSector(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str,
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
            cursor: sqlite3.Cursor,
            universeId: str
            ) -> typing.List[DbUniverseInfo]:
        sql = """
            SELECT name
            FROM {table}
            WHERE id = :id
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
            cursor: sqlite3.Cursor,
            name: str
            ) -> typing.List[DbUniverseInfo]:
        sql = """
            SELECT id
            FROM {table}
            WHERE name = :name
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
            cursor: sqlite3.Cursor,
            universeId: str,
            milieu: typing.Optional[str],
            includeDefaultSectors: bool
            ) -> typing.List[DbSectorInfo]:
        sql = """
            SELECT id, universe_id, milieu, primary_name, sector_x, sector_y, abbreviation
            FROM {table}
            WHERE universe_id = :id
            """.format(table=MultiverseDb._SectorsTableName)
        parameters = {'id': universeId}

        if milieu:
            sql += 'AND milieu = :milieu'
            parameters['milieu'] = milieu

        if includeDefaultSectors:
            sql += """
                UNION ALL
                SELECT d.id, d.universe_id, d.milieu, d.primary_name, d.sector_x, d.sector_y, abbreviation
                FROM {table} d
                WHERE d.universe_id = :default_id
                """.format(table=MultiverseDb._SectorsTableName)
            parameters['default_id'] = MultiverseDb._DefaultUniverseId

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

        cursor.execute(sql, parameters)

        sectorList = []
        for row in cursor.fetchall():
            sectorList.append(DbSectorInfo(
                id=row[0],
                universeId=row[1],
                isCustom=row[1] != MultiverseDb._DefaultUniverseId,
                milieu=row[2],
                name=row[3],
                sectorX=row[4],
                sectorY=row[5],
                abbreviation=row[6]))
        return sectorList

    def _internalSectorInfoById(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.Optional[DbSectorInfo]:
        sql = """
            SELECT universe_id, milieu, primary_name, sector_x, sector_y, abbreviation
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
            universeId=row[0],
            isCustom=row[0] != MultiverseDb._DefaultUniverseId,
            milieu=row[1],
            name=row[2],
            sectorX=row[3],
            sectorY=row[4],
            abbreviation=row[5])

    def _internalSectorInfoByPosition(
            self,
            cursor: sqlite3.Cursor,
            universeId: str,
            milieu: str,
            sectorX: int,
            sectorY: int
            # NOTE: Returned sector may be from default universe rather than the
            # one specified by universeId
            ) -> typing.Optional[DbSectorInfo]:
        sql = """
            SELECT id, universe_id, primary_name, abbreviation
            FROM {table}
            WHERE (universe_id = :id OR universe_id = :default_id)
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
            'sector_y': sectorY,
            'default_id': MultiverseDb._DefaultUniverseId}

        cursor.execute(sql, selectData)
        row = cursor.fetchone()
        if not row:
            return None

        return DbSectorInfo(
            id=row[0],
            # NOTE: Use returned row as it may be the default universe rather than universeId
            universeId=row[1],
            isCustom=row[1] != MultiverseDb._DefaultUniverseId,
            milieu=milieu,
            name=row[2],
            sectorX=sectorX,
            sectorY=sectorY,
            abbreviation=row[3])

    @staticmethod
    def _readSnapshotTimestamp(directoryPath: str) -> datetime.datetime:
        timestampPath = os.path.join(directoryPath, 'timestamp.txt')
        with open(timestampPath, 'r', encoding='utf-8-sig') as file:
            return MultiverseDb._parseSnapshotTimestamp(content=file.read())

    @staticmethod
    def _parseSnapshotTimestamp(content: str) -> datetime.datetime:
        timestamp = datetime.datetime.strptime(
            content,
            MultiverseDb._SnapshotTimestampFormat)
        return timestamp.replace(tzinfo=datetime.timezone.utc)