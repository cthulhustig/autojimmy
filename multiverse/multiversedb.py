import common
import database
import datetime
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
# TODO: I think I want to drop the overlay system and have custom universes
# create a complete copy of the stock universe. The stock universe would
# update with new snapshots but the custom universes would remain as they
# were when you created them (barring any edits). This avoids a lot of
# problems with having to create custom versions of sectors when you want
# to edit them in your custom universe.
# IMPORTANT: If I do this it probably also makes sense to move to a seperate
# database file for each universe. This would make it easier for people to
# share just one universe.
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

    _StarsTableName = 'stars'
    _StarsTableSchema = 1

    _BodiesTableName = 'bodies'
    _BodiesTableSchema = 1

    _WorldsTableName = 'worlds'
    _WorldsTableSchema = 1

    _GasGiantsTableName = 'gas_giants'
    _GasGiantsTableSchema = 1

    _PlanetoidBeltsTableName = 'planetoid_belts'
    _PlanetoidBeltsTableSchema = 1

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
    _DefaultUniverseTimestampKey = 'default_universe_timestamp'

    _SnapshotTimestampFormat = '%Y-%m-%d %H:%M:%S.%f'

    _lock = threading.RLock() # Recursive lock
    _instance = None # Singleton instance
    _initialised = False
    _database = None
    _appVersion = None

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

        MultiverseDb._database = database.SchemaDb(
            dbPath=databasePath)
        MultiverseDb._appVersion = appVersion

        self._initTables()

        MultiverseDb._initialised = True

    def createTransaction(
            self,
            onCommitCallback: typing.Optional[typing.Callable[[], None]] = None,
            onRollbackCallback: typing.Optional[typing.Callable[[], None]] = None
            ) -> database.Transaction:
        return self._database.createTransaction(
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
            self._importDefaultUniverse(
                directoryPath=directoryPath,
                cursor=connection.cursor(),
                progressCallback=progressCallback)

    def saveUniverse(
            self,
            universe: multiverse.DbUniverse,
            transaction: typing.Optional[database.Transaction] = None,
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

            self._deleteUniverse(
                universeId=universe.id(),
                cursor=connection.cursor())

            self._insertUniverse(
                universe=universe,
                cursor=connection.cursor(),
                progressCallback=insertProgressCallback)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()

                self._deleteUniverse(
                    universeId=universe.id(),
                    cursor=connection.cursor())

                self._insertUniverse(
                    universe=universe,
                    cursor=connection.cursor(),
                    progressCallback=insertProgressCallback)

    def loadUniverse(
            self,
            universeId: str,
            includeDefaultSectors: bool = True,
            transaction: typing.Optional[database.Transaction] = None,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> typing.Optional[multiverse.DbUniverse]:
        logging.debug(f'MultiverseDb loading universe {universeId}')

        readProgressCallback = None
        if progressCallback:
            readProgressCallback = lambda milieu, name, progress, total: progressCallback(f'Loading: {milieu} - {name}' if progress != total else 'Loading: Complete!', progress, total)

        if transaction != None:
            connection = transaction.connection()
            return self._readUniverse(
                universeId=universeId,
                includeDefaultSectors=includeDefaultSectors,
                cursor=connection.cursor(),
                progressCallback=readProgressCallback)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._readUniverse(
                    universeId=universeId,
                    includeDefaultSectors=includeDefaultSectors,
                    cursor=connection.cursor(),
                    progressCallback=readProgressCallback)

    def saveSector(
            self,
            sector: multiverse.DbSector,
            transaction: typing.Optional[database.Transaction] = None
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
            self._deleteSector(
                sectorId=sector.id(),
                milieu=sector.milieu(),
                sectorX=sector.sectorX(),
                sectorY=sector.sectorY(),
                cursor=connection.cursor())
            self._insertSector(
                sector=sector,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                # Delete any old version of the sector and any sector that has at the
                # same time and place as the new sector
                self._deleteSector(
                    sectorId=sector.id(),
                    milieu=sector.milieu(),
                    sectorX=sector.sectorX(),
                    sectorY=sector.sectorY(),
                    cursor=connection.cursor())
                self._insertSector(
                    sector=sector,
                    cursor=connection.cursor())

    def loadSector(
            self,
            sectorId: str,
            transaction: typing.Optional[database.Transaction] = None
            ) -> multiverse.DbSector:
        logging.debug(f'MultiverseDb reading sector {sectorId}')
        if transaction != None:
            connection = transaction.connection()
            return self._readSector(
                sectorId=sectorId,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._readSector(
                    sectorId=sectorId,
                    cursor=connection.cursor())

    def deleteSector(
            self,
            sectorId: str,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'MultiverseDb deleting sector {sectorId}')

        if transaction != None:
            connection = transaction.connection()

            sectorInfo = self._sectorInfoById(
                sectorId=sectorId,
                cursor=connection.cursor())
            if not sectorInfo:
                return # Nothing to delete
            if not sectorInfo.isCustom():
                raise RuntimeError('Deleting default sectors is not allowed')

            self._deleteSector(
                sectorId=sectorId,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()

                sectorInfo = self._sectorInfoById(
                    sectorId=sectorId,
                    cursor=connection.cursor())
                if not sectorInfo:
                    return # Nothing to delete
                if not sectorInfo.isCustom():
                    raise RuntimeError('Deleting default sectors is not allowed')

                self._deleteSector(
                    sectorId=sectorId,
                    cursor=connection.cursor())

    def universeInfoById(
            self,
            universeId: str,
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.Optional[DbUniverseInfo]:
        logging.debug(
            f'MultiverseDb retrieving info for sector with id "{universeId}"')
        if transaction != None:
            connection = transaction.connection()
            return self._universeInfoById(
                universeId=universeId,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._universeInfoById(
                    universeId=universeId,
                    cursor=connection.cursor())

    def listSectorInfo(
            self,
            universeId: str,
            milieu: typing.Optional[str] = None,
            includeDefaultSectors: bool = True,
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.List[DbSectorInfo]:
        logging.debug(
            'MultiverseDb listing sector info' + ('' if universeId is None else f' for universe {universeId}'))
        if transaction != None:
            connection = transaction.connection()
            return self._listSectorInfo(
                universeId=universeId,
                milieu=milieu,
                includeDefaultSectors=includeDefaultSectors,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._listSectorInfo(
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
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.Optional[DbSectorInfo]:
        logging.debug(
            f'MultiverseDb retrieving info for sector at ({sectorX}, {sectorY}) for universe {universeId} from {milieu}')
        if transaction != None:
            connection = transaction.connection()
            return self._sectorInfoByPosition(
                universeId=universeId,
                milieu=milieu,
                sectorX=sectorX,
                sectorY=sectorY,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._sectorInfoByPosition(
                    universeId=universeId,
                    milieu=milieu,
                    sectorX=sectorX,
                    sectorY=sectorY,
                    cursor=connection.cursor())

    def _initTables(self) -> None:
        with self.createTransaction() as transaction:
            connection = transaction.connection()
            cursor = connection.cursor()

            # Create metadata table
            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._MetadataTableName,
                requiredSchemaVersion=MultiverseDb._MetadataTableSchema,
                columns=[
                    database.ColumnDef(columnName='key', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='value', columnType=database.ColumnDef.ColumnType.Text)])

            # TODO: This table shouldn't be needed when I've finished moving to a per-file universe
            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._UniversesTableName,
                requiredSchemaVersion=MultiverseDb._UniversesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=False, isUnique=True),
                    database.ColumnDef(columnName='description', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='notes', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._SectorsTableName,
                requiredSchemaVersion=MultiverseDb._SectorsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    # TODO: This column shouldn't be needed when I've finished moving to a per-file universe
                    database.ColumnDef(columnName='universe_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._UniversesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='milieu', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='sector_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='sector_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='primary_name', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='primary_language', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='abbreviation', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='sector_label', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='selected', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False),
                    database.ColumnDef(columnName='credits', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='publication', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='author', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='publisher', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='reference', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='notes', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['universe_id', 'milieu', 'sector_x', 'sector_y'])])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._AlternateNamesTableName,
                requiredSchemaVersion=MultiverseDb._AlternateNamesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='language', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._SubsectorNamesTableName,
                requiredSchemaVersion=MultiverseDb._SubsectorNamesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='code', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              minValue='A', maxValue='P'),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['sector_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._AllegiancesTableName,
                requiredSchemaVersion=MultiverseDb._AllegiancesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='code', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='legacy', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='base', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='route_colour', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='route_style', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='route_width', columnType=database.ColumnDef.ColumnType.Real, isNullable=True, minValue=0),
                    database.ColumnDef(columnName='border_colour', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='border_style', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['sector_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._SophontsTableName,
                requiredSchemaVersion=MultiverseDb._SophontsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='code', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='is_major', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['sector_id', 'code']),
                    # NOTE: Unlike most entities (e.g. allegiances) the sophont name must be unique
                    # for a given sector. This is because remarks such as major/minor race and dieback
                    # refer to the sophont by name rather than code so it needs to be unique to prevent
                    # ambiguity
                    database.UniqueConstraintDef(columnNames=['sector_id', 'name'])])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._SystemsTableName,
                requiredSchemaVersion=MultiverseDb._SystemsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='hex_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='hex_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='planetoid_belt_count', columnType=database.ColumnDef.ColumnType.Integer, isNullable=True, minValue=0),
                    database.ColumnDef(columnName='gas_giant_count', columnType=database.ColumnDef.ColumnType.Integer, isNullable=True, minValue=0),
                    # TODO: I wonder if this needs to be world_count and include the main world so I
                    # can allow for systems where there is no main world (e.g. just a star)
                    database.ColumnDef(columnName='other_world_count', columnType=database.ColumnDef.ColumnType.Integer, isNullable=True, minValue=0),
                    database.ColumnDef(columnName='zone', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='allegiance_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=True,
                              foreignTableName=MultiverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.SetNull),
                    database.ColumnDef(columnName='notes', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['sector_id', 'hex_x', 'hex_y'])])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._BodiesTableName,
                requiredSchemaVersion=MultiverseDb._BodiesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='system_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SystemsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='orbit_index', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='notes', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._StarsTableName,
                requiredSchemaVersion=MultiverseDb._StarsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='system_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SystemsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='luminosity_class', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='spectral_class', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='spectral_scale', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)])

            # TODO: Also create giants and belts tables. Even if they don't have any extra data I need
            # to store the body_id so in the future when the user can create them, the code knows which
            # type of object they are. Currently there is no way to tell if a body is a gas giant or
            # a belt. I need code that is similar to how worlds are loaded and that relies on worlds
            # table to identify which bodies are worlds
            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._WorldsTableName,
                requiredSchemaVersion=MultiverseDb._WorldsTableSchema,
                columns=[
                    database.ColumnDef(columnName='body_id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True,
                                foreignTableName=MultiverseDb._BodiesTableName, foreignColumnName='id',
                                foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='is_main_world', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False),
                    database.ColumnDef(columnName='starport', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='world_size', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='atmosphere', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='hydrographics', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='population', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='government', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='law_level', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='tech_level', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='resources', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='labour', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='infrastructure', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='efficiency', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='heterogeneity', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='acceptance', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='strangeness', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='symbols', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='population_multiplier', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._NobilitiesTableName,
                requiredSchemaVersion=MultiverseDb._NobilitiesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='code', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['world_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._TradeCodesTableName,
                requiredSchemaVersion=MultiverseDb._TradeCodesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='code', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['world_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._SophontPopulationsTableName,
                requiredSchemaVersion=MultiverseDb._SophontPopulationsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='sophont_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SophontsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='percentage', columnType=database.ColumnDef.ColumnType.Integer, isNullable=True, minValue=0, maxValue=100),
                    database.ColumnDef(columnName='is_home_world', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False),
                    database.ColumnDef(columnName='is_die_back', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['world_id', 'sophont_id'])])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._RulingAllegiancesTableName,
                requiredSchemaVersion=MultiverseDb._RulingAllegiancesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='allegiance_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['world_id', 'allegiance_id'])])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._OwningSystemsTableName,
                requiredSchemaVersion=MultiverseDb._OwningSystemsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='hex_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='hex_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    # NOTE: This intentionally stores the abbreviation rather
                    # than the sector id so that the referenced sector doesn't
                    # need to exist in the DB at the point this sector was
                    # imported. This avoids the chicken and egg situation where
                    # it wouldn't be possible to import two sectors that
                    # reference each other as which ever was imported first
                    # would need the sector id of a sector that hasn't been
                    # imported yet.
                    database.ColumnDef(columnName='sector_abbreviation', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['world_id', 'hex_x', 'hex_y', 'sector_abbreviation'])])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._ColonySystemsTableName,
                requiredSchemaVersion=MultiverseDb._ColonySystemsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='hex_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='hex_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    # NOTE: See comment on owning systems as to why this is the
                    # abbreviation rather than the sector id
                    database.ColumnDef(columnName='sector_abbreviation', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['world_id', 'hex_x', 'hex_y', 'sector_abbreviation'])])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._ResearchStationTableName,
                requiredSchemaVersion=MultiverseDb._ResearchStationTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='code', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['world_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._CustomRemarksTableName,
                requiredSchemaVersion=MultiverseDb._CustomRemarksTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='remark', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._BasesTableName,
                requiredSchemaVersion=MultiverseDb._BasesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='code', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['world_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._RoutesTableName,
                requiredSchemaVersion=MultiverseDb._RoutesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='start_hex_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='start_hex_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='end_hex_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='end_hex_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='start_offset_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='start_offset_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='end_offset_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='end_offset_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='type', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='style', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='colour', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='width', columnType=database.ColumnDef.ColumnType.Real, isNullable=True, minValue=0),
                    database.ColumnDef(columnName='allegiance_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=True,
                              foreignTableName=MultiverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.SetNull)])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._BordersTableName,
                requiredSchemaVersion=MultiverseDb._BordersTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='allegiance_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=True,
                              foreignTableName=MultiverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.SetNull),
                    database.ColumnDef(columnName='style', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='colour', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='label', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    # NOTE: The label position is stored as an offset in world space from the
                    # origin of the sector (top, left). An offset is used rather than storing
                    # world space coordinates to keep sector data relative to the sector. It
                    # will make it easier if we ever want to move a sector
                    database.ColumnDef(columnName='label_x', columnType=database.ColumnDef.ColumnType.Real, isNullable=True),
                    database.ColumnDef(columnName='label_y', columnType=database.ColumnDef.ColumnType.Real, isNullable=True),
                    database.ColumnDef(columnName='show_label', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False),
                    database.ColumnDef(columnName='wrap_label', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._BorderHexesTableName,
                requiredSchemaVersion=MultiverseDb._BorderHexesTableSchema,
                columns=[
                    database.ColumnDef(columnName='border_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._BordersTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='hex_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='hex_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._RegionsTableName,
                requiredSchemaVersion=MultiverseDb._RegionsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='colour', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='label', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    # NOTE: See note on borders about coordinate space used for world x/y
                    database.ColumnDef(columnName='label_x', columnType=database.ColumnDef.ColumnType.Real, isNullable=True),
                    database.ColumnDef(columnName='label_y', columnType=database.ColumnDef.ColumnType.Real, isNullable=True),
                    database.ColumnDef(columnName='show_label', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False),
                    database.ColumnDef(columnName='wrap_label', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._RegionHexesTableName,
                requiredSchemaVersion=MultiverseDb._RegionHexesTableSchema,
                columns=[
                    database.ColumnDef(columnName='region_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._RegionsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='hex_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='hex_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._LabelsTableName,
                requiredSchemaVersion=MultiverseDb._LabelsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='text', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='colour', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='size', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='wrap', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._SectorTagsTableName,
                requiredSchemaVersion=MultiverseDb._SectorTagsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='tag', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['sector_id', 'tag'])])

            self._database.createTable(
                cursor=cursor,
                tableName=MultiverseDb._ProductsTableName,
                requiredSchemaVersion=MultiverseDb._ProductsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=MultiverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='publication', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='author', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='publisher', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='reference', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)])

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

    # This function returns True if imported or False if nothing was
    # done due to the snapshot being older than the current snapshot.
    # If forceImport is true the snapshot will be imported even if
    # it is older
    # TODO: I'm not sure if this should live here or be separate like
    # the custom sector code. It feels like the two types of operation
    # should be handled consistently
    def _importDefaultUniverse(
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

        self._deleteUniverse(
            universeId=MultiverseDb._DefaultUniverseId,
            cursor=cursor)

        insertProgressCallback = None
        if progressCallback:
            insertProgressCallback = \
                lambda milieu, name, progress, total: progressCallback(f'Importing: {milieu} - {name}' if progress != total else 'Importing: Complete!', progress, total)
        self._insertUniverse(
            universe=dbUniverse,
            updateDefault=True,
            cursor=cursor,
            progressCallback=insertProgressCallback)

        self._setMetadata(
            key=MultiverseDb._DefaultUniverseTimestampKey,
            value=importTimestamp.isoformat(),
            cursor=cursor)

    def _insertUniverse(
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

                self._insertSector(
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

    def _readUniverse(
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

            try:
                sector = self._readSector(
                    sectorId=sectorId,
                    cursor=cursor)
                sectors.append(sector)
            except Exception as ex:
                # Log error but continue loading
                logging.error('MultiverseDb failed to read sector {sectorId}', exc_info=ex)

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
            sectors=sectors,
            notes=notes)

    def _deleteUniverse(
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

    def _insertSector(
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

        self._insertSectorAlternateNames(
            cursor=cursor,
            sector=sector)
        self._insertSectorSubsectorNames(
            cursor=cursor,
            sector=sector)
        self._insertSectorAllegiances(
            cursor=cursor,
            sector=sector)
        self._insertSectorSophonts(
            cursor=cursor,
            sector=sector)
        self._insertSectorSystems(
            cursor=cursor,
            sector=sector)
        self._insertSectorRoutes(
            cursor=cursor,
            sector=sector)
        self._insertSectorBorders(
            cursor=cursor,
            sector=sector)
        self._insertSectorRegions(
            cursor=cursor,
            sector=sector)
        self._insertSectorLabels(
            cursor=cursor,
            sector=sector)
        self._insertSectorTags(
            cursor=cursor,
            sector=sector)
        self._insertSectorProducts(
            cursor=cursor,
            sector=sector)

    def _readSector(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> multiverse.DbSector:
        alternateNames = self._readSectorAlternateNames(
            cursor=cursor,
            sectorId=sectorId)
        subsectorNames = self._readSectorSubsectorNames(
            cursor=cursor,
            sectorId=sectorId)
        allegiances = self._readSectorAllegiances(
            cursor=cursor,
            sectorId=sectorId)
        sophonts = self._readSectorSophonts(
            cursor=cursor,
            sectorId=sectorId)
        systems = self._readSectorSystems(
            cursor=cursor,
            sectorId=sectorId)
        routes = self._readSectorRoutes(
            cursor=cursor,
            sectorId=sectorId)
        borders = self._readSectorBorders(
            cursor=cursor,
            sectorId=sectorId)
        regions = self._readSectorRegions(
            cursor=cursor,
            sectorId=sectorId)
        labels = self._readSectorLabels(
            cursor=cursor,
            sectorId=sectorId)
        tags = self._readSectorTags(
            cursor=cursor,
            sectorId=sectorId)
        products = self._readSectorProducts(
            cursor=cursor,
            sectorId=sectorId)

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
            raise ValueError(f'Unknown sector {sectorId}')

        return multiverse.DbSector(
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
            notes=row[14],
            alternateNames=alternateNames,
            subsectorNames=subsectorNames,
            allegiances=allegiances,
            sophonts=sophonts,
            systems=systems,
            routes=routes,
            borders=borders,
            regions=regions,
            labels=labels,
            tags=tags,
            products=products)

    def _insertSectorAlternateNames(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.alternateNames():
            return

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

    def _readSectorAlternateNames(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.List[multiverse.DbAlternateName]:
        sql = """
            SELECT id, name, language
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._AlternateNamesTableName)
        cursor.execute(sql, {'id': sectorId})
        names = []
        for row in cursor.fetchall():
            nameId = row[0]
            try:
                names.append(multiverse.DbAlternateName(
                    id=nameId,
                    name=row[1],
                    language=row[2]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct alternate name {nameId}', exc_info=ex)

        return names

    def _insertSectorSubsectorNames(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.subsectorNames():
            return

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

    def _readSectorSubsectorNames(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.List[multiverse.DbSubsectorName]:
        sql = """
            SELECT id, code, name
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._SubsectorNamesTableName)
        cursor.execute(sql, {'id': sectorId})
        names = []
        for row in cursor.fetchall():
            nameId = row[0]
            try:
                names.append(multiverse.DbSubsectorName(
                    id=nameId,
                    code=row[1],
                    name=row[2]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct subsector name {nameId}', exc_info=ex)

        return names

    def _insertSectorAllegiances(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.allegiances():
            return

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

    def _readSectorAllegiances(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.List[multiverse.DbAllegiance]:
        sql = """
            SELECT id, code, name, legacy, base,
                route_colour, route_style, route_width,
                border_colour, border_style
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._AllegiancesTableName)
        cursor.execute(sql, {'id': sectorId})
        allegiances = []
        for row in cursor.fetchall():
            allegianceId = row[0]
            try:
                allegiances.append(multiverse.DbAllegiance(
                    id=allegianceId,
                    sectorId=sectorId,
                    code=row[1],
                    name=row[2],
                    legacy=row[3],
                    base=row[4],
                    routeColour=row[5],
                    routeStyle=row[6],
                    routeWidth=row[7],
                    borderColour=row[8],
                    borderStyle=row[9]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct allegiance {allegianceId}', exc_info=ex)

        return allegiances

    def _insertSectorSophonts(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.sophonts():
            return

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

    def _readSectorSophonts(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.List[multiverse.DbSophont]:
        sql = """
            SELECT id, code, name, is_major
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._SophontsTableName)
        cursor.execute(sql, {'id': sectorId})
        sophonts = []
        for row in cursor.fetchall():
            sophontId = row[0]
            try:
                sophonts.append(multiverse.DbSophont(
                    id=sophontId,
                    sectorId=sectorId,
                    code=row[1],
                    name=row[2],
                    isMajor=True if row[3] else False))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct sophont {sophontId}', exc_info=ex)

        return sophonts

    def _insertSectorSystems(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.systems():
            return

        sql = """
            INSERT INTO {table} (id, sector_id, hex_x, hex_y, name,
                planetoid_belt_count, gas_giant_count, other_world_count,
                zone, allegiance_id, notes)
            VALUES (:id, :sector_id, :hex_x, :hex_y, :name,
                :planetoid_belt_count, :gas_giant_count, :other_world_count,
                :zone, :allegiance_id, :notes);
            """.format(table=MultiverseDb._SystemsTableName)
        rows = []
        for system in sector.systems():
            rows.append({
                'id': system.id(),
                'sector_id': system.sectorId(),
                'hex_x': system.hexX(),
                'hex_y': system.hexY(),
                'name': system.name(),
                'planetoid_belt_count': system.planetoidBeltCount(),
                'gas_giant_count': system.gasGiantCount(),
                'other_world_count': system.otherWorldCount(),
                'zone': system.zone(),
                'allegiance_id': system.allegianceId(),
                'notes': system.notes()})
        cursor.executemany(sql, rows)

        self._insertSectorStars(
            cursor=cursor,
            sector=sector)
        self._insertSectorBodies(
            cursor=cursor,
            sector=sector)

    def _readSectorSystems(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.List[multiverse.DbSystem]:
        systemStarsMap = self._readSectorStars(
            cursor=cursor,
            sectorId=sectorId)
        systemBodiesMap = self._readSectorBodies(
            cursor=cursor,
            sectorId=sectorId)

        sql = """
            SELECT id, hex_x, hex_y, name,
                planetoid_belt_count, gas_giant_count, other_world_count,
                zone, allegiance_id, notes
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        systems = []
        for row in cursor.fetchall():
            systemId = row[0]
            try:
                systems.append(multiverse.DbSystem(
                    id=systemId,
                    hexX=row[1],
                    hexY=row[2],
                    name=row[3],
                    planetoidBeltCount=row[4],
                    gasGiantCount=row[5],
                    otherWorldCount=row[6],
                    zone=row[7],
                    allegianceId=row[8],
                    notes=row[9],
                    stars=systemStarsMap.get(systemId),
                    bodies=systemBodiesMap.get(systemId)))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct system {systemId}', exc_info=ex)

        return systems

    def _insertSectorRoutes(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.routes():
            return

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
                'allegiance_id': route.allegianceId()})
        cursor.executemany(sql, rows)

    def _readSectorRoutes(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str,
            ) -> typing.List[multiverse.DbRoute]:
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
            routeId = row[0]
            try:
                routes.append(multiverse.DbRoute(
                    id=routeId,
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
                    allegianceId=row[13]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct route {routeId}', exc_info=ex)

        return routes

    def _insertSectorBorders(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.borders():
            return

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
            borderRows.append({
                'id': border.id(),
                'sector_id': border.sectorId(),
                'allegiance_id': border.allegianceId(),
                'style': border.style(),
                'colour': border.colour(),
                'label': border.label(),
                'label_x': border.labelWorldX(),
                'label_y': border.labelWorldY(),
                'show_label': 1 if border.showLabel() else 0,
                'wrap_label': 1 if border.wrapLabel() else 0})
            for hexX, hexY in border.hexes():
                hexRows.append({
                    'border_id': border.id(),
                    'hex_x': hexX,
                    'hex_y': hexY})
        cursor.executemany(bordersSql, borderRows)
        cursor.executemany(hexesSql, hexRows)

    def _readSectorBorders(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.List[multiverse.DbBorder]:
        bordersSql = """
            SELECT id, allegiance_id, style, colour, label,
                label_x, label_y, show_label, wrap_label
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._BordersTableName)
        hexesSql = """
            SELECT hex_x, hex_y
            FROM {table}
            WHERE border_id = :id;
            """.format(table=MultiverseDb._BorderHexesTableName)
        cursor.execute(bordersSql, {'id': sectorId})
        borders = []
        for row in cursor.fetchall():
            borderId = row[0]
            cursor.execute(hexesSql, {'id': borderId})
            hexes = []
            for hexRow in cursor.fetchall():
                hexes.append((hexRow[0], hexRow[1]))

            try:
                borders.append(multiverse.DbBorder(
                    id=borderId,
                    hexes=hexes,
                    allegianceId=row[1],
                    style=row[2],
                    colour=row[3],
                    label=row[4],
                    labelWorldX=row[5],
                    labelWorldY=row[6],
                    showLabel=True if row[7] else False,
                    wrapLabel=True if row[8] else False))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct border {borderId}', exc_info=ex)

        return borders

    def _insertSectorRegions(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.regions():
            return

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
                'label_x': region.labelWorldX(),
                'label_y': region.labelWorldY(),
                'show_label': 1 if region.showLabel() else 0,
                'wrap_label': 1 if region.wrapLabel() else 0})
            for hexX, hexY in region.hexes():
                hexRows.append({
                    'region_id': region.id(),
                    'hex_x': hexX,
                    'hex_y': hexY})
        cursor.executemany(regionsSql, regionsRows)
        cursor.executemany(hexesSql, hexRows)

    def _readSectorRegions(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.List[multiverse.DbRegion]:
        regionsSql = """
            SELECT id, colour, label, label_x, label_y, show_label, wrap_label
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._RegionsTableName)
        hexesSql = """
            SELECT hex_x, hex_y
            FROM {table}
            WHERE region_id = :id;
            """.format(table=MultiverseDb._RegionHexesTableName)
        cursor.execute(regionsSql, {'id': sectorId})
        regions = []
        for row in cursor.fetchall():
            regionId = row[0]
            cursor.execute(hexesSql, {'id': regionId})
            hexes = []
            for hexRow in cursor.fetchall():
                hexes.append((hexRow[0], hexRow[1]))

            try:
                regions.append(multiverse.DbRegion(
                    id=regionId,
                    hexes=hexes,
                    colour=row[1],
                    label=row[2],
                    labelWorldX=row[3],
                    labelWorldY=row[4],
                    showLabel=True if row[5] else False,
                    wrapLabel=True if row[6] else False))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct region {regionId}', exc_info=ex)

        return regions

    def _insertSectorLabels(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.labels():
            return

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
                'x': label.worldX(),
                'y': label.worldY(),
                'colour': label.colour(),
                'size': label.size(),
                'wrap': 1 if label.wrap() else 0})
        cursor.executemany(sql, rows)

    def _readSectorLabels(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.List[multiverse.DbLabel]:
        sql = """
            SELECT id, text, x, y, colour, size, wrap
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._LabelsTableName)
        cursor.execute(sql, {'id': sectorId})
        labels = []
        for row in cursor.fetchall():
            labelId = row[0]
            try:
                labels.append(multiverse.DbLabel(
                    id=labelId,
                    text=row[1],
                    worldX=row[2],
                    worldY=row[3],
                    colour=row[4],
                    size=row[5],
                    wrap=True if row[6] else False))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct label {labelId}', exc_info=ex)

        return labels

    def _insertSectorTags(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.tags():
            return

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

    def _readSectorTags(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.List[multiverse.DbTag]:
        sql = """
            SELECT id, tag
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._SectorTagsTableName)
        cursor.execute(sql, {'id': sectorId})
        tags = []
        for row in cursor.fetchall():
            tagId = row[0]
            try:
                tags.append(multiverse.DbTag(
                    id=tagId,
                    tag=row[1]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct tag {tagId}', exc_info=ex)

        return tags

    def _insertSectorProducts(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.products():
            return

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

    def _readSectorProducts(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.List[multiverse.DbTag]:
        sql = """
            SELECT id, publication, author, publisher, reference
            FROM {table}
            WHERE sector_id = :id;
            """.format(table=MultiverseDb._ProductsTableName)
        cursor.execute(sql, {'id': sectorId})
        products = []
        for row in cursor.fetchall():
            productId = row[0]
            try:
                products.append(multiverse.DbProduct(
                    id=productId,
                    publication=row[1],
                    author=row[2],
                    publisher=row[3],
                    reference=row[4]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct product {productId}', exc_info=ex)

        return products

    def _insertSectorStars(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.systems():
            return

        rows = []
        for system in sector.systems():
            if not system.stars():
                continue

            for star in system.stars():
                rows.append({
                    'id': star.id(),
                    'system_id': star.systemId(),
                    'luminosity_class': star.luminosityClass(),
                    'spectral_class': star.spectralClass(),
                    'spectral_scale': star.spectralScale()})

        if rows:
            sql = """
                INSERT INTO {table} (id, system_id, luminosity_class, spectral_class, spectral_scale)
                VALUES (:id, :system_id, :luminosity_class, :spectral_class, :spectral_scale);
                """.format(table=MultiverseDb._StarsTableName)
            cursor.executemany(sql, rows)

    def _readSectorStars(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.Dict[
                str, # System Id
                typing.List[multiverse.DbStar]]:
        sql = """
            SELECT t.id, t.system_id, t.luminosity_class, t.spectral_class, t.spectral_scale
            FROM {starsTable} AS t
            JOIN {systemsTable} AS s ON s.id = t.system_id
            WHERE s.sector_id = :id;
            """.format(
                starsTable=MultiverseDb._StarsTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        systemStarsMap: typing.Dict[str, typing.List[multiverse.DbStar]] = {}
        for row in cursor.fetchall():
            starId = row[0]
            systemId = row[1]
            stars = systemStarsMap.get(systemId)
            if not stars:
                stars = []
                systemStarsMap[systemId] = stars

            try:
                stars.append(multiverse.DbStar(
                    id=starId,
                    luminosityClass=row[2],
                    spectralClass=row[3],
                    spectralScale=row[4]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct star {starId}', exc_info=ex)

        return systemStarsMap

    def _insertSectorBodies(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.systems():
            return

        bodiesRows = []
        worldsRows = []
        for system in sector.systems():
            if not system.bodies():
                continue

            for body in system.bodies():
                bodiesRows.append({
                    'id': body.id(),
                    'system_id': body.systemId(),
                    'orbit_index': body.orbitIndex(),
                    'name': body.name(),
                    'notes': body.notes()})

                if isinstance(body, multiverse.DbWorld):
                    worldsRows.append({
                        'body_id': body.id(),
                        'is_main_world': body.isMainWorld(),
                        'starport': body.starport(),
                        'world_size': body.worldSize(),
                        'atmosphere': body.atmosphere(),
                        'hydrographics': body.hydrographics(),
                        'population': body.population(),
                        'government': body.government(),
                        'law_level': body.lawLevel(),
                        'tech_level': body.techLevel(),
                        'resources': body.resources(),
                        'labour': body.labour(),
                        'infrastructure': body.infrastructure(),
                        'efficiency': body.efficiency(),
                        'heterogeneity': body.heterogeneity(),
                        'acceptance': body.acceptance(),
                        'strangeness': body.strangeness(),
                        'symbols': body.symbols(),
                        'population_multiplier': body.populationMultiplier()})

        if bodiesRows:
            sql = """
                INSERT INTO {table} (id, system_id, orbit_index, name, notes)
                VALUES (:id, :system_id, :orbit_index, :name, :notes)
                """.format(table=MultiverseDb._BodiesTableName)
            cursor.executemany(sql, bodiesRows)
        if worldsRows:
            sql = """
                INSERT INTO {table} (body_id, is_main_world,
                    starport, world_size, atmosphere, hydrographics, population, government, law_level, tech_level,
                    resources, labour, infrastructure, efficiency,
                    heterogeneity, acceptance, strangeness, symbols,
                    population_multiplier)
                VALUES (:body_id, :is_main_world,
                    :starport, :world_size, :atmosphere, :hydrographics, :population, :government, :law_level, :tech_level,
                    :resources, :labour, :infrastructure, :efficiency,
                    :heterogeneity, :acceptance, :strangeness, :symbols,
                    :population_multiplier);
                """.format(table=MultiverseDb._WorldsTableName)
            cursor.executemany(sql, worldsRows)

        self._insertSectorNobilities(
            cursor=cursor,
            sector=sector)
        self._insertSectorBases(
            cursor=cursor,
            sector=sector)
        self._insertSectorTradeCodes(
            cursor=cursor,
            sector=sector)
        self._insertSectorSophontPopulations(
            cursor=cursor,
            sector=sector)
        self._insertSectorRulingAllegiances(
            cursor=cursor,
            sector=sector)
        self._insertSectorOwningSystems(
            cursor=cursor,
            sector=sector)
        self._insertSectorColonySystems(
            cursor=cursor,
            sector=sector)
        self._insertSectorResearchStations(
            cursor=cursor,
            sector=sector)
        self._insertSectorCustomRemarks(
            cursor=cursor,
            sector=sector)

    def _readSectorBodies(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.Dict[
                str, # System Id
                typing.List[multiverse.DbBody]]:
        worldNobilitiesMap = self._readSectorNobilities(
            cursor=cursor,
            sectorId=sectorId)
        worldBasesMap = self._readSectorBases(
            cursor=cursor,
            sectorId=sectorId)
        worldTradeCodesMap = self._readSectorTradeCodes(
            cursor=cursor,
            sectorId=sectorId)
        worldPopulationsMap = self._readSectorSophontPopulations(
            cursor=cursor,
            sectorId=sectorId)
        worldRulingAllegianceMap = self._readSectorRulingAllegiances(
            cursor=cursor,
            sectorId=sectorId)
        worldOwnersMap = self._readSectorOwningSystems(
            cursor=cursor,
            sectorId=sectorId)
        worldColoniesMap = self._readSectorColonySystems(
            cursor=cursor,
            sectorId=sectorId)
        worldResearchStationsMap = self._readSectorResearchStations(
            cursor=cursor,
            sectorId=sectorId)
        worldRemarksMap = self._readSectorCustomRemarks(
            cursor=cursor,
            sectorId=sectorId)

        systemBodiesMap: typing.Dict[str, typing.List[multiverse.DbBody]] = {}
        sql = """
            SELECT
                b.id, b.system_id, b.orbit_index, b.name,
                w.is_main_world,
                w.starport, w.world_size, w.atmosphere, w.hydrographics, w.population, w.government, w.law_level, w.tech_level,
                w.resources, w.labour, w.infrastructure, w.efficiency,
                w.heterogeneity, w.acceptance, w.strangeness, w.symbols,
                w.population_multiplier,
                b.notes
            FROM {worldsTable} w
            JOIN {bodiesTable} b ON b.id = w.body_id
            JOIN {systemsTable} s ON s.id = b.system_id
            WHERE s.sector_id = :id;
            """.format(
                worldsTable=MultiverseDb._WorldsTableName,
                bodiesTable=MultiverseDb._BodiesTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        for row in cursor.fetchall():
            bodyId = row[0]
            systemId = row[1]
            bodies = systemBodiesMap.get(systemId)
            if not bodies:
                bodies = []
                systemBodiesMap[systemId] = bodies

            try:
                bodies.append(multiverse.DbWorld(
                    id=bodyId,
                    orbitIndex=row[2],
                    name=row[3],
                    isMainWorld=True if row[4] else False,
                    starport=row[5],
                    worldSize=row[6],
                    atmosphere=row[7],
                    hydrographics=row[8],
                    population=row[9],
                    government=row[10],
                    lawLevel=row[11],
                    techLevel=row[12],
                    resources=row[13],
                    labour=row[14],
                    infrastructure=row[15],
                    efficiency=row[16],
                    heterogeneity=row[17],
                    acceptance=row[18],
                    strangeness=row[19],
                    symbols=row[20],
                    populationMultiplier=row[21],
                    notes=row[22],
                    nobilities=worldNobilitiesMap.get(bodyId),
                    bases=worldBasesMap.get(bodyId),
                    tradeCodes=worldTradeCodesMap.get(bodyId),
                    sophontPopulations=worldPopulationsMap.get(bodyId),
                    rulingAllegiances=worldRulingAllegianceMap.get(bodyId),
                    owningSystems=worldOwnersMap.get(bodyId),
                    colonySystems=worldColoniesMap.get(bodyId),
                    researchStations=worldResearchStationsMap.get(bodyId),
                    customRemarks=worldRemarksMap.get(bodyId)))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct body {bodyId}', exc_info=ex)

        return systemBodiesMap

    def _insertSectorNobilities(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.systems():
            return

        rows = []
        for system in sector.systems():
            if not system.bodies():
                continue

            for body in system.bodies():
                if not isinstance(body, multiverse.DbWorld):
                    continue

                if not body.nobilities():
                    continue

                for nobility in body.nobilities():
                    rows.append({
                        'id': nobility.id(),
                        'world_id': nobility.worldId(),
                        'code': nobility.code()})

        if rows:
            sql = """
                INSERT INTO {table} (id, world_id, code)
                VALUES (:id, :world_id, :code)
                """.format(table=MultiverseDb._NobilitiesTableName)
            cursor.executemany(sql, rows)

    def _readSectorNobilities(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbNobility]]:
        sql = """
            SELECT t.id, t.world_id, t.code
            FROM {nobilitiesTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            WHERE s.sector_id = :id;
            """.format(
                nobilitiesTable=MultiverseDb._NobilitiesTableName,
                worldsTable=MultiverseDb._WorldsTableName,
                bodiesTable=MultiverseDb._BodiesTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        systemNobilitiesMap: typing.Dict[str, typing.List[multiverse.DbNobility]] = {}
        for row in cursor.fetchall():
            nobilityId = row[0]
            worldId = row[1]
            nobilities = systemNobilitiesMap.get(worldId)
            if not nobilities:
                nobilities = []
                systemNobilitiesMap[worldId] = nobilities

            try:
                nobilities.append(multiverse.DbNobility(
                    id=nobilityId,
                    code=row[2]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct nobility {nobilityId}', exc_info=ex)

        return systemNobilitiesMap

    def _insertSectorBases(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.systems():
            return

        rows = []
        for system in sector.systems():
            if not system.bodies():
                continue

            for body in system.bodies():
                if not isinstance(body, multiverse.DbWorld):
                    continue

                if not body.bases():
                    continue

                for base in body.bases():
                    rows.append({
                        'id': base.id(),
                        'world_id': base.worldId(),
                        'code': base.code()})

        if rows:
            sql = """
                INSERT INTO {table} (id, world_id, code)
                VALUES (:id, :world_id, :code);
                """.format(table=MultiverseDb._BasesTableName)
            cursor.executemany(sql, rows)

    def _readSectorBases(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbBase]]:
        sql = """
            SELECT t.id, t.world_id, t.code
            FROM {basesTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            WHERE s.sector_id = :id;
            """.format(
                basesTable=MultiverseDb._BasesTableName,
                worldsTable=MultiverseDb._WorldsTableName,
                bodiesTable=MultiverseDb._BodiesTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        systemBasesMap: typing.Dict[str, typing.List[multiverse.DbBase]] = {}
        for row in cursor.fetchall():
            baseId = row[0]
            worldId = row[1]
            bases = systemBasesMap.get(worldId)
            if not bases:
                bases = []
                systemBasesMap[worldId] = bases

            try:
                bases.append(multiverse.DbBase(
                    id=baseId,
                    code=row[2]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct base {baseId}', exc_info=ex)

        return systemBasesMap

    def _insertSectorTradeCodes(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.systems():
            return

        rows = []
        for system in sector.systems():
            if not system.bodies():
                continue

            for body in system.bodies():
                if not isinstance(body, multiverse.DbWorld):
                    continue

                if not body.tradeCodes():
                    continue

                for code in body.tradeCodes():
                    rows.append({
                        'id': code.id(),
                        'world_id': code.worldId(),
                        'code': code.code()})

        if rows:
            sql = """
                INSERT INTO {table} (id, world_id, code)
                VALUES (:id, :world_id, :code)
                """.format(table=MultiverseDb._TradeCodesTableName)
            cursor.executemany(sql, rows)

    def _readSectorTradeCodes(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbTradeCode]]:
        sql = """
            SELECT t.id, t.world_id, t.code
            FROM {tradeTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            WHERE s.sector_id = :id;
            """.format(
                tradeTable=MultiverseDb._TradeCodesTableName,
                worldsTable=MultiverseDb._WorldsTableName,
                bodiesTable=MultiverseDb._BodiesTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        systemTradeCodesMap: typing.Dict[str, typing.List[multiverse.DbTradeCode]] = {}
        for row in cursor.fetchall():
            tradeCodeId = row[0]
            worldId = row[1]
            tradeCodes = systemTradeCodesMap.get(worldId)
            if not tradeCodes:
                tradeCodes = []
                systemTradeCodesMap[worldId] = tradeCodes

            try:
                tradeCodes.append(multiverse.DbTradeCode(
                    id=tradeCodeId,
                    code=row[2]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct trade code {tradeCodeId}', exc_info=ex)

        return systemTradeCodesMap

    def _insertSectorSophontPopulations(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.systems():
            return

        rows = []
        for system in sector.systems():
            if not system.bodies():
                continue

            for body in system.bodies():
                if not isinstance(body, multiverse.DbWorld):
                    continue

                if not body.sophontPopulations():
                    continue

                for sophont in body.sophontPopulations():
                    rows.append({
                        'id': sophont.id(),
                        'world_id': sophont.worldId(),
                        'sophont_id': sophont.sophontId(),
                        'percentage': sophont.percentage(),
                        'is_home_world': 1 if sophont.isHomeWorld() else 0,
                        'is_die_back': 1 if sophont.isDieBack() else 0})

        if rows:
            sql = """
                INSERT INTO {table} (id, world_id, sophont_id, percentage, is_home_world, is_die_back)
                VALUES (:id, :world_id, :sophont_id, :percentage, :is_home_world, :is_die_back)
                """.format(table=MultiverseDb._SophontPopulationsTableName)
            cursor.executemany(sql, rows)

    def _readSectorSophontPopulations(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbSophontPopulation]]:
        sql = """
            SELECT t.id, t.world_id, t.sophont_id, t.percentage, t.is_home_world, t.is_die_back
            FROM {populationsTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            WHERE s.sector_id = :id;
            """.format(
                populationsTable=MultiverseDb._SophontPopulationsTableName,
                worldsTable=MultiverseDb._WorldsTableName,
                bodiesTable=MultiverseDb._BodiesTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        systemPopulationsMap: typing.Dict[str, typing.List[multiverse.DbSophontPopulation]] = {}
        for row in cursor.fetchall():
            populationId = row[0]
            worldId = row[1]
            populations = systemPopulationsMap.get(worldId)
            if not populations:
                populations = []
                systemPopulationsMap[worldId] = populations

            try:
                populations.append(multiverse.DbSophontPopulation(
                    id=populationId,
                    sophontId=row[2],
                    percentage=row[3],
                    isHomeWorld=True if row[4] else False,
                    isDieBack=True if row[5] else False))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct sophont population {populationId}', exc_info=ex)

        return systemPopulationsMap

    def _insertSectorRulingAllegiances(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.systems():
            return

        rows = []
        for system in sector.systems():
            if not system.bodies():
                continue

            for body in system.bodies():
                if not isinstance(body, multiverse.DbWorld):
                    continue

                if not body.rulingAllegiances():
                    continue

                for rulingAllegiance in body.rulingAllegiances():
                    rows.append({
                        'id': rulingAllegiance.id(),
                        'world_id': rulingAllegiance.worldId(),
                        'allegiance_id': rulingAllegiance.allegianceId()})

        if rows:
            sql = """
                INSERT INTO {table} (id, world_id, allegiance_id)
                VALUES (:id, :world_id, :allegiance_id)
                """.format(table=MultiverseDb._RulingAllegiancesTableName)
            cursor.executemany(sql, rows)

    def _readSectorRulingAllegiances(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbRulingAllegiance]]:
        sql = """
            SELECT t.id, t.world_id, t.allegiance_id
            FROM {rulingTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            WHERE s.sector_id = :id;
            """.format(
                rulingTable=MultiverseDb._RulingAllegiancesTableName,
                worldsTable=MultiverseDb._WorldsTableName,
                bodiesTable=MultiverseDb._BodiesTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        systemRulingAllegianceMap: typing.Dict[str, typing.List[multiverse.DbRulingAllegiance]] = {}
        for row in cursor.fetchall():
            rulerId = row[0]
            worldId = row[1]
            rulers = systemRulingAllegianceMap.get(worldId)
            if not rulers:
                rulers = []
                systemRulingAllegianceMap[worldId] = rulers

            try:
                rulers.append(multiverse.DbRulingAllegiance(
                    id=rulerId,
                    allegianceId=row[2]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct ruling allegiance {rulerId}', exc_info=ex)

        return systemRulingAllegianceMap

    def _insertSectorOwningSystems(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.systems():
            return

        rows = []
        for system in sector.systems():
            if not system.bodies():
                continue

            for body in system.bodies():
                if not isinstance(body, multiverse.DbWorld):
                    continue

                if not body.owningSystems():
                    continue

                for owningSystem in body.owningSystems():
                    rows.append({
                        'id': owningSystem.id(),
                        'world_id': owningSystem.worldId(),
                        'hex_x': owningSystem.hexX(),
                        'hex_y': owningSystem.hexY(),
                        'sector_abbreviation': owningSystem.sectorAbbreviation()})

        if rows:
            sql = """
                INSERT INTO {table} (id, world_id, hex_x, hex_y, sector_abbreviation)
                VALUES (:id, :world_id, :hex_x, :hex_y, :sector_abbreviation)
                """.format(table=MultiverseDb._OwningSystemsTableName)
            cursor.executemany(sql, rows)

    def _readSectorOwningSystems(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbOwningSystem]]:
        sql = """
            SELECT t.id, t.world_id, t.hex_x, t.hex_y, t.sector_abbreviation
            FROM {ownersTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            WHERE s.sector_id = :id;
            """.format(
                ownersTable=MultiverseDb._OwningSystemsTableName,
                worldsTable=MultiverseDb._WorldsTableName,
                bodiesTable=MultiverseDb._BodiesTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        systemOwnersMap: typing.Dict[str, typing.List[multiverse.DbOwningSystem]] = {}
        for row in cursor.fetchall():
            ownerId = row[0]
            worldId = row[1]
            owners = systemOwnersMap.get(worldId)
            if not owners:
                owners = []
                systemOwnersMap[worldId] = owners

            try:
                owners.append(multiverse.DbOwningSystem(
                    id=ownerId,
                    hexX=row[2],
                    hexY=row[3],
                    sectorAbbreviation=row[4]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct owning system {ownerId}', exc_info=ex)

        return systemOwnersMap

    def _insertSectorColonySystems(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.systems():
            return

        rows = []
        for system in sector.systems():
            if not system.bodies():
                continue

            for body in system.bodies():
                if not isinstance(body, multiverse.DbWorld):
                    continue

                if not body.colonySystems():
                    continue

                for colonySystem in body.colonySystems():
                    rows.append({
                        'id': colonySystem.id(),
                        'world_id': colonySystem.worldId(),
                        'hex_x': colonySystem.hexX(),
                        'hex_y': colonySystem.hexY(),
                        'sector_abbreviation': colonySystem.sectorAbbreviation()})

        if rows:
            sql = """
                INSERT INTO {table} (id, world_id, hex_x, hex_y, sector_abbreviation)
                VALUES (:id, :world_id, :hex_x, :hex_y, :sector_abbreviation)
                """.format(table=MultiverseDb._ColonySystemsTableName)
            cursor.executemany(sql, rows)

    def _readSectorColonySystems(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbColonySystem]]:
        sql = """
            SELECT t.id, t.world_id, t.hex_x, t.hex_y, t.sector_abbreviation
            FROM {coloniesTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            WHERE s.sector_id = :id;
            """.format(
                coloniesTable=MultiverseDb._ColonySystemsTableName,
                worldsTable=MultiverseDb._WorldsTableName,
                bodiesTable=MultiverseDb._BodiesTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        systemColoniesMap: typing.Dict[str, typing.List[multiverse.DbColonySystem]] = {}
        for row in cursor.fetchall():
            colonyId = row[0]
            worldId = row[1]
            colonies = systemColoniesMap.get(worldId)
            if not colonies:
                colonies = []
                systemColoniesMap[worldId] = colonies

            try:
                colonies.append(multiverse.DbColonySystem(
                    id=colonyId,
                    hexX=row[2],
                    hexY=row[3],
                    sectorAbbreviation=row[4]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct colony system {colonyId}', exc_info=ex)

        return systemColoniesMap

    def _insertSectorResearchStations(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.systems():
            return

        rows = []
        for system in sector.systems():
            if not system.bodies():
                continue

            for body in system.bodies():
                if not isinstance(body, multiverse.DbWorld):
                    continue

                if not body.researchStations():
                    continue

                for station in body.researchStations():
                    rows.append({
                        'id': station.id(),
                        'world_id': station.worldId(),
                        'code': station.code()})

        if rows:
            sql = """
                INSERT INTO {table} (id, world_id, code)
                VALUES (:id, :world_id, :code);
                """.format(table=MultiverseDb._ResearchStationTableName)
            cursor.executemany(sql, rows)

    def _readSectorResearchStations(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbResearchStation]]:
        sql = """
            SELECT t.id, t.world_id, t.code
            FROM {stationsTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            WHERE s.sector_id = :id;
            """.format(
                stationsTable=MultiverseDb._ResearchStationTableName,
                worldsTable=MultiverseDb._WorldsTableName,
                bodiesTable=MultiverseDb._BodiesTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        systemResearchStationsMap: typing.Dict[str, typing.List[multiverse.DbResearchStation]] = {}
        for row in cursor.fetchall():
            stationId = row[0]
            worldId = row[1]
            stations = systemResearchStationsMap.get(worldId)
            if not stations:
                stations = []
                systemResearchStationsMap[worldId] = stations

            try:
                stations.append(multiverse.DbResearchStation(
                    id=stationId,
                    code=row[2]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct research station {stationId}', exc_info=ex)

        return systemResearchStationsMap

    def _insertSectorCustomRemarks(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        if not sector.systems():
            return

        rows = []
        for system in sector.systems():
            if not system.bodies():
                continue

            for body in system.bodies():
                if not isinstance(body, multiverse.DbWorld):
                    continue

                if not body.customRemarks():
                    continue

                for remark in body.customRemarks():
                    rows.append({
                        'id': remark.id(),
                        'world_id': remark.worldId(),
                        'remark': remark.remark()})

        if rows:
            sql = """
                INSERT INTO {table} (id, world_id, remark)
                VALUES (:id, :world_id, :remark)
                """.format(table=MultiverseDb._CustomRemarksTableName)
            cursor.executemany(sql, rows)

    def _readSectorCustomRemarks(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbCustomRemark]]:
        sql = """
            SELECT t.id, t.world_id, t.remark
            FROM {remarksTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            WHERE s.sector_id = :id;
            """.format(
                remarksTable=MultiverseDb._CustomRemarksTableName,
                worldsTable=MultiverseDb._WorldsTableName,
                bodiesTable=MultiverseDb._BodiesTableName,
                systemsTable=MultiverseDb._SystemsTableName)
        cursor.execute(sql, {'id': sectorId})
        systemRemarksMap: typing.Dict[str, typing.List[multiverse.DbCustomRemark]] = {}
        for row in cursor.fetchall():
            remarkId = row[0]
            worldId = row[1]
            remarks = systemRemarksMap.get(worldId)
            if not remarks:
                remarks = []
                systemRemarksMap[worldId] = remarks

            try:
                remarks.append(multiverse.DbCustomRemark(
                    id=remarkId,
                    remark=row[2]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct custom remark {remarkId}', exc_info=ex)

        return systemRemarksMap

    def _deleteSector(
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

    def _listUniverseInfo(
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

    def _universeInfoById(
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

    def _universeInfoByName(
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

    def _listSectorInfo(
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

    def _sectorInfoById(
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

    def _sectorInfoByPosition(
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