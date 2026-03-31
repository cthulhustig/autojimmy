import logging
import multiverse
import sqlite3
import typing

# TODO: All log messages need updated to say UniverseDb and include the file name

class SectorInfo(object):
    def __init__(
            self,
            id: str,
            milieu: str,
            name: str,
            sectorX: int,
            sectorY: int,
            abbreviation: typing.Optional[str]
            ) -> None:
        self._id = id
        self._milieu = milieu
        self._name = name
        self._sectorX = sectorX
        self._sectorY = sectorY
        self._abbreviation = abbreviation

        self._hash = None

    def id(self) -> str:
        return self._id

    def milieu(self) -> str:
        return self._milieu

    def name(self) -> str:
        return self._name

    def sectorX(self) -> int:
        return self._sectorX

    def sectorY(self) -> int:
        return self._sectorY

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

class UniverseDb(object):
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

    _database = None

    def __init__(self, universePath: str) -> None:
        self._universePath = universePath
        self._database = multiverse.SchemaDb(dbPath=universePath)
        self._initTables()

    def createConnection(self) -> None:
        return self._database.createConnection()

    def createTransaction(
            self,
            onCommitCallback: typing.Optional[typing.Callable[[], None]] = None,
            onRollbackCallback: typing.Optional[typing.Callable[[], None]] = None
            ) -> multiverse.Transaction:
        return self._database.createTransaction(
            onCommitCallback=onCommitCallback,
            onRollbackCallback=onRollbackCallback)

    def listSectors(
            self,
            milieu: typing.Optional[str] = None,
            transaction: typing.Optional[multiverse.Transaction] = None
            ) -> typing.List[SectorInfo]:
        logging.debug(f'UniverseDb listing {milieu if milieu else "all"} sectors in universe {self._universePath}')

        if transaction != None:
            connection = transaction.connection()
            return self._listSectors(
                milieu=milieu,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._listSectors(
                    milieu=milieu,
                    cursor=connection.cursor())

    def saveSector(
            self,
            sector: multiverse.DbSector,
            transaction: typing.Optional[multiverse.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseDb saving sector {sector.id()} to universe {self._universePath}')

        if transaction != None:
            connection = transaction.connection()
            cursor = connection.cursor()
            # Delete any old version of the sector and any sector that has at the
            # same time and place as the new sector
            self._deleteSector(
                sectorId=sector.id(),
                milieu=sector.milieu(),
                sectorX=sector.sectorX(),
                sectorY=sector.sectorY(),
                cursor=cursor)
            self._insertSector(
                sector=sector,
                cursor=cursor)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                cursor = connection.cursor()
                # Delete any old version of the sector and any sector that has at the
                # same time and place as the new sector
                self._deleteSector(
                    sectorId=sector.id(),
                    milieu=sector.milieu(),
                    sectorX=sector.sectorX(),
                    sectorY=sector.sectorY(),
                    cursor=cursor)
                self._insertSector(
                    sector=sector,
                    cursor=cursor)

    def loadSector(
            self,
            sectorId: str,
            transaction: typing.Optional[multiverse.Transaction] = None
            ) -> multiverse.DbSector:
        logging.debug(f'UniverseDb loading sector {sectorId} from universe {self._universePath}')

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

    def loadSectors(
            self,
            transaction: typing.Optional[multiverse.Transaction] = None
            ) -> typing.List[multiverse.DbSector]:
        logging.debug(f'UniverseDb loading sector from universe {self._universePath}')

        if transaction != None:
            connection = transaction.connection()
            return self._loadSectors(
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._loadSectors(
                    cursor=connection.cursor())

    def deleteSector(
            self,
            sectorId: str,
            transaction: typing.Optional[multiverse.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseDb deleting sector {sectorId} from universe {self._universePath}')

        if transaction != None:
            connection = transaction.connection()
            self._deleteSector(
                sectorId=sectorId,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._deleteSector(
                    sectorId=sectorId,
                    cursor=connection.cursor())

    def clearSectors(
            self,
            transaction: typing.Optional[multiverse.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseDb clearing sectors in universe {self._universePath}')

        if transaction != None:
            connection = transaction.connection()
            # Delete any old version of the sector and any sector that has at the
            # same time and place as the new sector
            self._clearSectors(
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                # Delete any old version of the sector and any sector that has at the
                # same time and place as the new sector
                self._clearSectors(
                    cursor=connection.cursor())

    def copyTo(self, targetPath: str) -> None:
        self._database.copyTo(targetPath=targetPath)

    def _initTables(self) -> None:
        with self.createTransaction() as transaction:
            connection = transaction.connection()
            cursor = connection.cursor()

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._SectorsTableName,
                requiredSchemaVersion=UniverseDb._SectorsTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='milieu', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False),
                    multiverse.ColumnDef(columnName='sector_x', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='sector_y', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='primary_name', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False),
                    multiverse.ColumnDef(columnName='primary_language', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='abbreviation', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='sector_label', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='selected', columnType=multiverse.ColumnDef.ColumnType.Boolean, isNullable=False),
                    multiverse.ColumnDef(columnName='credits', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='publication', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='author', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='publisher', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='reference', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='notes', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    multiverse.UniqueConstraintDef(columnNames=['milieu', 'sector_x', 'sector_y'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._AlternateNamesTableName,
                requiredSchemaVersion=UniverseDb._AlternateNamesTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='sector_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='name', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False),
                    multiverse.ColumnDef(columnName='language', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._SubsectorNamesTableName,
                requiredSchemaVersion=UniverseDb._SubsectorNamesTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='sector_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='code', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              minValue='A', maxValue='P'),
                    multiverse.ColumnDef(columnName='name', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    multiverse.UniqueConstraintDef(columnNames=['sector_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._AllegiancesTableName,
                requiredSchemaVersion=UniverseDb._AllegiancesTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='sector_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='code', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False),
                    multiverse.ColumnDef(columnName='name', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False),
                    multiverse.ColumnDef(columnName='legacy', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='base', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='route_colour', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='route_style', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='route_width', columnType=multiverse.ColumnDef.ColumnType.Real, isNullable=True, minValue=0),
                    multiverse.ColumnDef(columnName='border_colour', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='border_style', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    multiverse.UniqueConstraintDef(columnNames=['sector_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._SophontsTableName,
                requiredSchemaVersion=UniverseDb._SophontsTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='sector_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='code', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False),
                    multiverse.ColumnDef(columnName='name', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False),
                    multiverse.ColumnDef(columnName='is_major', columnType=multiverse.ColumnDef.ColumnType.Boolean, isNullable=False)],
                uniqueConstraints=[
                    multiverse.UniqueConstraintDef(columnNames=['sector_id', 'code']),
                    # NOTE: Unlike most entities (e.g. allegiances) the sophont name must be unique
                    # for a given sector. This is because remarks such as major/minor race and dieback
                    # refer to the sophont by name rather than code so it needs to be unique to prevent
                    # ambiguity
                    multiverse.UniqueConstraintDef(columnNames=['sector_id', 'name'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._SystemsTableName,
                requiredSchemaVersion=UniverseDb._SystemsTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='sector_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='hex_x', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='hex_y', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='name', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='planetoid_belt_count', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=True, minValue=0),
                    multiverse.ColumnDef(columnName='gas_giant_count', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=True, minValue=0),
                    # TODO: I wonder if this needs to be world_count and include the main world so I
                    # can allow for systems where there is no main world (e.g. just a star)
                    multiverse.ColumnDef(columnName='other_world_count', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=True, minValue=0),
                    multiverse.ColumnDef(columnName='zone', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='allegiance_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True,
                              foreignTableName=UniverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.SetNull),
                    multiverse.ColumnDef(columnName='notes', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    multiverse.UniqueConstraintDef(columnNames=['sector_id', 'hex_x', 'hex_y'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._BodiesTableName,
                requiredSchemaVersion=UniverseDb._BodiesTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='system_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SystemsTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='orbit_index', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='name', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='notes', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._StarsTableName,
                requiredSchemaVersion=UniverseDb._StarsTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='system_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SystemsTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='luminosity_class', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False),
                    multiverse.ColumnDef(columnName='spectral_class', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='spectral_scale', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True)])

            # TODO: Also create giants and belts tables. Even if they don't have any extra data I need
            # to store the body_id so in the future when the user can create them, the code knows which
            # type of object they are. Currently there is no way to tell if a body is a gas giant or
            # a belt. I need code that is similar to how worlds are loaded and that relies on worlds
            # table to identify which bodies are worlds
            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._WorldsTableName,
                requiredSchemaVersion=UniverseDb._WorldsTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='body_id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True,
                                foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                                foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='is_main_world', columnType=multiverse.ColumnDef.ColumnType.Boolean, isNullable=False),
                    multiverse.ColumnDef(columnName='starport', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='world_size', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='atmosphere', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='hydrographics', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='population', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='government', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='law_level', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='tech_level', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='resources', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='labour', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='infrastructure', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='efficiency', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='heterogeneity', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='acceptance', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='strangeness', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='symbols', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='population_multiplier', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._NobilitiesTableName,
                requiredSchemaVersion=UniverseDb._NobilitiesTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='world_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='code', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    multiverse.UniqueConstraintDef(columnNames=['world_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._TradeCodesTableName,
                requiredSchemaVersion=UniverseDb._TradeCodesTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='world_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='code', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    multiverse.UniqueConstraintDef(columnNames=['world_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._SophontPopulationsTableName,
                requiredSchemaVersion=UniverseDb._SophontPopulationsTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='world_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='sophont_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SophontsTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='percentage', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=True, minValue=0, maxValue=100),
                    multiverse.ColumnDef(columnName='is_home_world', columnType=multiverse.ColumnDef.ColumnType.Boolean, isNullable=False),
                    multiverse.ColumnDef(columnName='is_die_back', columnType=multiverse.ColumnDef.ColumnType.Boolean, isNullable=False)],
                uniqueConstraints=[
                    multiverse.UniqueConstraintDef(columnNames=['world_id', 'sophont_id'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._RulingAllegiancesTableName,
                requiredSchemaVersion=UniverseDb._RulingAllegiancesTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='world_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='allegiance_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade)],
                uniqueConstraints=[
                    multiverse.UniqueConstraintDef(columnNames=['world_id', 'allegiance_id'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._OwningSystemsTableName,
                requiredSchemaVersion=UniverseDb._OwningSystemsTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='world_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='hex_x', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='hex_y', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    # NOTE: This intentionally stores the abbreviation rather
                    # than the sector id so that the referenced sector doesn't
                    # need to exist in the DB at the point this sector was
                    # imported. This avoids the chicken and egg situation where
                    # it wouldn't be possible to import two sectors that
                    # reference each other as which ever was imported first
                    # would need the sector id of a sector that hasn't been
                    # imported yet.
                    multiverse.ColumnDef(columnName='sector_abbreviation', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    multiverse.UniqueConstraintDef(columnNames=['world_id', 'hex_x', 'hex_y', 'sector_abbreviation'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._ColonySystemsTableName,
                requiredSchemaVersion=UniverseDb._ColonySystemsTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='world_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='hex_x', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='hex_y', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    # NOTE: See comment on owning systems as to why this is the
                    # abbreviation rather than the sector id
                    multiverse.ColumnDef(columnName='sector_abbreviation', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    multiverse.UniqueConstraintDef(columnNames=['world_id', 'hex_x', 'hex_y', 'sector_abbreviation'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._ResearchStationTableName,
                requiredSchemaVersion=UniverseDb._ResearchStationTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='world_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='code', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    multiverse.UniqueConstraintDef(columnNames=['world_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._CustomRemarksTableName,
                requiredSchemaVersion=UniverseDb._CustomRemarksTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='world_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='remark', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._BasesTableName,
                requiredSchemaVersion=UniverseDb._BasesTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='world_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='code', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    multiverse.UniqueConstraintDef(columnNames=['world_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._RoutesTableName,
                requiredSchemaVersion=UniverseDb._RoutesTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='sector_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='start_hex_x', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='start_hex_y', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='end_hex_x', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='end_hex_y', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='start_offset_x', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='start_offset_y', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='end_offset_x', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='end_offset_y', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='type', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='style', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='colour', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='width', columnType=multiverse.ColumnDef.ColumnType.Real, isNullable=True, minValue=0),
                    multiverse.ColumnDef(columnName='allegiance_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True,
                              foreignTableName=UniverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.SetNull)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._BordersTableName,
                requiredSchemaVersion=UniverseDb._BordersTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='sector_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='allegiance_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True,
                              foreignTableName=UniverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.SetNull),
                    multiverse.ColumnDef(columnName='style', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='colour', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='label', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    # NOTE: The label position is stored as an offset in world space from the
                    # origin of the sector (top, left). An offset is used rather than storing
                    # world space coordinates to keep sector data relative to the sector. It
                    # will make it easier if we ever want to move a sector
                    multiverse.ColumnDef(columnName='label_x', columnType=multiverse.ColumnDef.ColumnType.Real, isNullable=True),
                    multiverse.ColumnDef(columnName='label_y', columnType=multiverse.ColumnDef.ColumnType.Real, isNullable=True),
                    multiverse.ColumnDef(columnName='show_label', columnType=multiverse.ColumnDef.ColumnType.Boolean, isNullable=False),
                    multiverse.ColumnDef(columnName='wrap_label', columnType=multiverse.ColumnDef.ColumnType.Boolean, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._BorderHexesTableName,
                requiredSchemaVersion=UniverseDb._BorderHexesTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='border_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BordersTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='hex_x', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='hex_y', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._RegionsTableName,
                requiredSchemaVersion=UniverseDb._RegionsTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='sector_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='colour', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='label', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    # NOTE: See note on borders about coordinate space used for world x/y
                    multiverse.ColumnDef(columnName='label_x', columnType=multiverse.ColumnDef.ColumnType.Real, isNullable=True),
                    multiverse.ColumnDef(columnName='label_y', columnType=multiverse.ColumnDef.ColumnType.Real, isNullable=True),
                    multiverse.ColumnDef(columnName='show_label', columnType=multiverse.ColumnDef.ColumnType.Boolean, isNullable=False),
                    multiverse.ColumnDef(columnName='wrap_label', columnType=multiverse.ColumnDef.ColumnType.Boolean, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._RegionHexesTableName,
                requiredSchemaVersion=UniverseDb._RegionHexesTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='region_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._RegionsTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='hex_x', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='hex_y', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._LabelsTableName,
                requiredSchemaVersion=UniverseDb._LabelsTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='sector_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='text', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False),
                    multiverse.ColumnDef(columnName='x', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='y', columnType=multiverse.ColumnDef.ColumnType.Integer, isNullable=False),
                    multiverse.ColumnDef(columnName='colour', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='size', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='wrap', columnType=multiverse.ColumnDef.ColumnType.Boolean, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._SectorTagsTableName,
                requiredSchemaVersion=UniverseDb._SectorTagsTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='sector_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='tag', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    multiverse.UniqueConstraintDef(columnNames=['sector_id', 'tag'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._ProductsTableName,
                requiredSchemaVersion=UniverseDb._ProductsTableSchema,
                columns=[
                    multiverse.ColumnDef(columnName='id', columnType=multiverse.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    multiverse.ColumnDef(columnName='sector_id', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=multiverse.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    multiverse.ColumnDef(columnName='publication', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='author', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='publisher', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True),
                    multiverse.ColumnDef(columnName='reference', columnType=multiverse.ColumnDef.ColumnType.Text, isNullable=True)])

    def _listSectors(
            self,
            cursor: sqlite3.Cursor,
            milieu: typing.Optional[str]
            ) -> typing.List[SectorInfo]:
        sql = """
            SELECT id, milieu, primary_name, sector_x, sector_y, abbreviation
            FROM {table}
            """.format(table=UniverseDb._SectorsTableName)
        parameters = {}

        if milieu:
            sql += 'AND milieu = :milieu'
            parameters['milieu'] = milieu

        sql += ';'

        cursor.execute(sql, parameters)

        sectorList = []
        for row in cursor.fetchall():
            sectorList.append(SectorInfo(
                id=row[0],
                milieu=row[1],
                name=row[2],
                sectorX=row[3],
                sectorY=row[4],
                abbreviation=row[5]))
        return sectorList

    def _loadSectors(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbSector]:
        sectorAlternateNamesMap = self._readAlternateNames(
            cursor=cursor)
        sectorSubsectorNamesMap = self._readSubsectorNames(
            cursor=cursor)
        sectorAllegiancesMap = self._readAllegiances(
            cursor=cursor)
        sectorSophontsMap = self._readSophonts(
            cursor=cursor)
        sectorSystemsMap = self._readSystems(
            cursor=cursor)
        sectorRoutesMap = self._readRoutes(
            cursor=cursor)
        sectorBordersMap = self._readBorders(
            cursor=cursor)
        sectorRegionsMap = self._readRegions(
            cursor=cursor)
        sectorLabelsMap = self._readLabels(
            cursor=cursor)
        sectorTagsMap = self._readTags(
            cursor=cursor)
        sectorProductsMap = self._readProducts(
            cursor=cursor)

        sql = """
            SELECT id, milieu, sector_x, sector_y,
                primary_name, primary_language, abbreviation, sector_label, selected,
                credits, publication, author, publisher, reference, notes
            FROM {table};
            """.format(table=UniverseDb._SectorsTableName)
        cursor.execute(sql)
        sectors = []
        for row in cursor.fetchall():
            sectorId = row[0]

            try:
                sectors.append(multiverse.DbSector(
                    id=sectorId,
                    universeId='BLAH', # TODO: This should be removed from DbSector
                    isCustom=False, # TODO: This should be held at the universe level rather than the sector level
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
                    alternateNames=sectorAlternateNamesMap.get(sectorId),
                    subsectorNames=sectorSubsectorNamesMap.get(sectorId),
                    allegiances=sectorAllegiancesMap.get(sectorId),
                    sophonts=sectorSophontsMap.get(sectorId),
                    systems=sectorSystemsMap.get(sectorId),
                    routes=sectorRoutesMap.get(sectorId),
                    borders=sectorBordersMap.get(sectorId),
                    regions=sectorRegionsMap.get(sectorId),
                    labels=sectorLabelsMap.get(sectorId),
                    tags=sectorTagsMap.get(sectorId),
                    products=sectorProductsMap.get(sectorId)))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct sector {sectorId}', exc_info=ex)

        return sectors

    def _insertSector(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector
            ) -> None:
        sql = """
            INSERT INTO {table} (id, milieu, sector_x, sector_y,
                primary_name, primary_language, abbreviation, sector_label, selected,
                credits, publication, author, publisher, reference, notes)
            VALUES (:id, :milieu, :sector_x, :sector_y,
                :primary_name, :primary_language, :abbreviation, :sector_label, :selected,
                :credits, :publication, :author, :publisher, :reference, :notes);
            """.format(table=UniverseDb._SectorsTableName)
        rows = {
            'id': sector.id(),
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
        sectorAlternateNamesMap = self._readAlternateNames(
            cursor=cursor,
            sectorId=sectorId)
        sectorSubsectorNamesMap = self._readSubsectorNames(
            cursor=cursor,
            sectorId=sectorId)
        sectorAllegiancesMap = self._readAllegiances(
            cursor=cursor,
            sectorId=sectorId)
        sectorSophontsMap = self._readSophonts(
            cursor=cursor,
            sectorId=sectorId)
        sectorSystemsMap = self._readSystems(
            cursor=cursor,
            sectorId=sectorId)
        sectorRoutesMap = self._readRoutes(
            cursor=cursor,
            sectorId=sectorId)
        sectorBordersMap = self._readBorders(
            cursor=cursor,
            sectorId=sectorId)
        sectorRegionsMap = self._readRegions(
            cursor=cursor,
            sectorId=sectorId)
        sectorLabelsMap = self._readLabels(
            cursor=cursor,
            sectorId=sectorId)
        sectorTagsMap = self._readTags(
            cursor=cursor,
            sectorId=sectorId)
        sectorProductsMap = self._readProducts(
            cursor=cursor,
            sectorId=sectorId)

        sql = """
            SELECT milieu, sector_x, sector_y,
                primary_name, primary_language, abbreviation, sector_label, selected,
                credits, publication, author, publisher, reference, notes
            FROM {table}
            WHERE id = :id
            LIMIT 1;
            """.format(table=UniverseDb._SectorsTableName)
        cursor.execute(sql, {'id': sectorId})
        row = cursor.fetchone()
        if not row:
            raise ValueError(f'Unknown sector {sectorId}')

        return multiverse.DbSector(
            id=sectorId,
            universeId='BLAH', # TODO: This should be removed from DbSector
            isCustom=False, # TODO: This should be held at the universe level rather than the sector level
            milieu=row[0],
            sectorX=row[1],
            sectorY=row[2],
            primaryName=row[3],
            primaryLanguage=row[4],
            abbreviation=row[5],
            sectorLabel=row[6],
            selected=True if row[7] else False,
            credits=row[8],
            publication=row[9],
            author=row[10],
            publisher=row[11],
            reference=row[12],
            notes=row[13],
            alternateNames=sectorAlternateNamesMap.get(sectorId),
            subsectorNames=sectorSubsectorNamesMap.get(sectorId),
            allegiances=sectorAllegiancesMap.get(sectorId),
            sophonts=sectorSophontsMap.get(sectorId),
            systems=sectorSystemsMap.get(sectorId),
            routes=sectorRoutesMap.get(sectorId),
            borders=sectorBordersMap.get(sectorId),
            regions=sectorRegionsMap.get(sectorId),
            labels=sectorLabelsMap.get(sectorId),
            tags=sectorTagsMap.get(sectorId),
            products=sectorProductsMap.get(sectorId))

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
            """.format(table=UniverseDb._AlternateNamesTableName)
        rows = []
        for alternateName in sector.alternateNames():
            rows.append({
                'id': alternateName.id(),
                'sector_id': alternateName.sectorId(),
                'name': alternateName.name(),
                'language': alternateName.language()})
        cursor.executemany(sql, rows)

    def _readAlternateNames(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # Sector Id
                typing.List[multiverse.DbAlternateName]]:
        sql = """
            SELECT id, sector_id, name, language
            FROM {table}
            {where};
            """.format(
                table=UniverseDb._AlternateNamesTableName,
                where='WHERE sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

        sectorNamesMap = {}
        for row in cursor.fetchall():
            nameId = row[0]
            sectorId = row[1]
            names = sectorNamesMap.get(sectorId)
            if names is None:
                names = []
                sectorNamesMap[sectorId] = names

            try:
                names.append(multiverse.DbAlternateName(
                    id=nameId,
                    sectorId=sectorId,
                    name=row[2],
                    language=row[3]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct alternate name {nameId}', exc_info=ex)

        return sectorNamesMap

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
            """.format(table=UniverseDb._SubsectorNamesTableName)
        rows = []
        for subsectorName in sector.subsectorNames():
            rows.append({
                'id': subsectorName.id(),
                'sector_id': subsectorName.sectorId(),
                'code': subsectorName.code(),
                'name': subsectorName.name()})
        cursor.executemany(sql, rows)

    def _readSubsectorNames(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # Sector Id
                typing.List[multiverse.DbSubsectorName]]:
        sql = """
            SELECT id, sector_id, code, name
            FROM {table}
            {where};
            """.format(
                table=UniverseDb._SubsectorNamesTableName,
                where='WHERE sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

        sectorNamesMap = {}
        for row in cursor.fetchall():
            nameId = row[0]
            sectorId = row[1]
            names = sectorNamesMap.get(sectorId)
            if names is None:
                names = []
                sectorNamesMap[sectorId] = names

            try:
                names.append(multiverse.DbSubsectorName(
                    id=nameId,
                    sectorId=sectorId,
                    code=row[2],
                    name=row[3]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct subsector name {nameId}', exc_info=ex)

        return sectorNamesMap

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
            """.format(table=UniverseDb._AllegiancesTableName)
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

    def _readAllegiances(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # Sector Id
                typing.List[multiverse.DbAllegiance]]:
        sql = """
            SELECT id, sector_id, code, name, legacy, base,
                route_colour, route_style, route_width,
                border_colour, border_style
            FROM {table}
            {where};
            """.format(
                table=UniverseDb._AllegiancesTableName,
                where='WHERE sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

        sectorAllegiancesMap = {}
        for row in cursor.fetchall():
            allegianceId = row[0]
            sectorId = row[1]
            allegiances = sectorAllegiancesMap.get(sectorId)
            if allegiances is None:
                allegiances = []
                sectorAllegiancesMap[sectorId] = allegiances

            try:
                allegiances.append(multiverse.DbAllegiance(
                    id=allegianceId,
                    sectorId=sectorId,
                    code=row[2],
                    name=row[3],
                    legacy=row[4],
                    base=row[5],
                    routeColour=row[6],
                    routeStyle=row[7],
                    routeWidth=row[8],
                    borderColour=row[9],
                    borderStyle=row[10]))
            except Exception as ex:
                logging.error(f'UniverseDb failed to construct allegiance {allegianceId}', exc_info=ex)

        return sectorAllegiancesMap

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
            """.format(table=UniverseDb._SophontsTableName)
        rows = []
        for sophont in sector.sophonts():
            rows.append({
                'id': sophont.id(),
                'sector_id': sophont.sectorId(),
                'code': sophont.code(),
                'name': sophont.name(),
                'is_major': 1 if sophont.isMajor() else 0})
        cursor.executemany(sql, rows)

    def _readSophonts(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # Sector Id
                typing.List[multiverse.DbSophont]]:
        sql = """
            SELECT id, sector_id, code, name, is_major
            FROM {table}
            {where};
            """.format(
                table=UniverseDb._SophontsTableName,
                where='WHERE sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

        sectorSophontsMap = {}
        for row in cursor.fetchall():
            sophontId = row[0]
            sectorId = row[1]
            sophonts = sectorSophontsMap.get(sectorId)
            if sophonts is None:
                sophonts = []
                sectorSophontsMap[sectorId] = sophonts

            try:
                sophonts.append(multiverse.DbSophont(
                    id=sophontId,
                    sectorId=sectorId,
                    code=row[2],
                    name=row[3],
                    isMajor=True if row[4] else False))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct sophont {sophontId}', exc_info=ex)

        return sectorSophontsMap

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
            """.format(table=UniverseDb._SystemsTableName)
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

    def _readSystems(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # Sector Id
                typing.List[multiverse.DbSystem]]:
        systemStarsMap = self._readStars(
            cursor=cursor,
            sectorId=sectorId)
        systemBodiesMap = self._readBodies(
            cursor=cursor,
            sectorId=sectorId)

        sql = """
            SELECT id, sector_id, hex_x, hex_y, name,
                planetoid_belt_count, gas_giant_count, other_world_count,
                zone, allegiance_id, notes
            FROM {table}
            {where};
            """.format(
                table=UniverseDb._SystemsTableName,
                where='WHERE sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

        sectorSystemsMap = {}
        for row in cursor.fetchall():
            systemId = row[0]
            sectorId = row[1]
            systems = sectorSystemsMap.get(sectorId)
            if systems is None:
                systems = []
                sectorSystemsMap[sectorId] = systems

            try:
                systems.append(multiverse.DbSystem(
                    id=systemId,
                    sectorId=sectorId,
                    hexX=row[2],
                    hexY=row[3],
                    name=row[4],
                    planetoidBeltCount=row[5],
                    gasGiantCount=row[6],
                    otherWorldCount=row[7],
                    zone=row[8],
                    allegianceId=row[9],
                    notes=row[10],
                    stars=systemStarsMap.get(systemId),
                    bodies=systemBodiesMap.get(systemId)))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct system {systemId}', exc_info=ex)

        return sectorSystemsMap

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
            """.format(table=UniverseDb._RoutesTableName)
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

    def _readRoutes(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # Sector Id
                typing.List[multiverse.DbRoute]]:
        sql = """
            SELECT id, sector_id, start_hex_x, start_hex_y, end_hex_x, end_hex_y,
                start_offset_x, start_offset_y, end_offset_x, end_offset_y,
                type, style, colour, width, allegiance_id
            FROM {table}
            {where};
            """.format(
                table=UniverseDb._RoutesTableName,
                where='WHERE sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

        sectorRoutesMap = {}
        for row in cursor.fetchall():
            routeId = row[0]
            sectorId = row[1]
            routes = sectorRoutesMap.get(sectorId)
            if routes is None:
                routes = []
                sectorRoutesMap[sectorId] = routes

            try:
                routes.append(multiverse.DbRoute(
                    id=routeId,
                    sectorId=sectorId,
                    startHexX=row[2],
                    startHexY=row[3],
                    endHexX=row[4],
                    endHexY=row[5],
                    startOffsetX=row[6],
                    startOffsetY=row[7],
                    endOffsetX=row[8],
                    endOffsetY=row[9],
                    type=row[10],
                    style=row[11],
                    colour=row[12],
                    width=row[13],
                    allegianceId=row[14]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct route {routeId}', exc_info=ex)

        return sectorRoutesMap

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
            """.format(table=UniverseDb._BordersTableName)
        hexesSql =  """
            INSERT INTO {table} (border_id, hex_x, hex_y)
            VALUES (:border_id, :hex_x, :hex_y);
            """.format(table=UniverseDb._BorderHexesTableName)
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

    def _readBorders(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # Sector Id
                typing.List[multiverse.DbBorder]]:
        sql = """
            SELECT id, sector_id, allegiance_id, style, colour, label,
                label_x, label_y, show_label, wrap_label
            FROM {table}
            {where};
            """.format(
                table=UniverseDb._BordersTableName,
                where='WHERE sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

        sql = """
            SELECT hex_x, hex_y
            FROM {table}
            WHERE border_id = :id;
            """.format(table=UniverseDb._BorderHexesTableName)
        sectorBordersMap = {}
        for row in cursor.fetchall():
            borderId = row[0]
            sectorId = row[1]
            borders = sectorBordersMap.get(sectorId)
            if borders is None:
                borders = []
                sectorBordersMap[sectorId] = borders

            cursor.execute(sql, {'id': borderId})
            hexes = []
            for hexRow in cursor.fetchall():
                hexes.append((hexRow[0], hexRow[1]))

            try:
                borders.append(multiverse.DbBorder(
                    id=borderId,
                    sectorId=sectorId,
                    allegianceId=row[2],
                    style=row[3],
                    colour=row[4],
                    label=row[5],
                    labelWorldX=row[6],
                    labelWorldY=row[7],
                    showLabel=True if row[8] else False,
                    wrapLabel=True if row[9] else False,
                    hexes=hexes))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct border {borderId}', exc_info=ex)

        return sectorBordersMap

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
            """.format(table=UniverseDb._RegionsTableName)
        hexesSql =  """
            INSERT INTO {table} (region_id, hex_x, hex_y)
            VALUES (:region_id, :hex_x, :hex_y);
            """.format(table=UniverseDb._RegionHexesTableName)
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

    def _readRegions(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # Sector Id
                typing.List[multiverse.DbRegion]]:
        sql = """
            SELECT id, sector_id, colour, label, label_x, label_y, show_label, wrap_label
            FROM {table}
            {where};
            """.format(
                table=UniverseDb._RegionsTableName,
                where='WHERE sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

        sql = """
            SELECT hex_x, hex_y
            FROM {table}
            WHERE region_id = :id;
            """.format(table=UniverseDb._RegionHexesTableName)
        sectorRegionsMap = {}
        for row in cursor.fetchall():
            regionId = row[0]
            sectorId = row[1]
            regions = sectorRegionsMap.get(sectorId)
            if regions is None:
                regions = []
                sectorRegionsMap[sectorId] = regions

            cursor.execute(sql, {'id': regionId})
            hexes = []
            for hexRow in cursor.fetchall():
                hexes.append((hexRow[0], hexRow[1]))

            try:
                regions.append(multiverse.DbRegion(
                    id=regionId,
                    sectorId=sectorId,
                    colour=row[2],
                    label=row[3],
                    labelWorldX=row[4],
                    labelWorldY=row[5],
                    showLabel=True if row[6] else False,
                    wrapLabel=True if row[7] else False,
                    hexes=hexes))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct region {regionId}', exc_info=ex)

        return sectorRegionsMap

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
            """.format(table=UniverseDb._LabelsTableName)
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

    def _readLabels(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # Sector Id
                typing.List[multiverse.DbLabel]]:
        sql = """
            SELECT id, sector_id, text, x, y, colour, size, wrap
            FROM {table}
            {where};
            """.format(
                table=UniverseDb._LabelsTableName,
                where='WHERE sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

        sectorLabelsMap = {}
        for row in cursor.fetchall():
            labelId = row[0]
            sectorId = row[1]
            labels = sectorLabelsMap.get(sectorId)
            if labels is None:
                labels = []
                sectorLabelsMap[sectorId] = labels

            try:
                labels.append(multiverse.DbLabel(
                    id=labelId,
                    sectorId=sectorId,
                    text=row[2],
                    worldX=row[3],
                    worldY=row[4],
                    colour=row[5],
                    size=row[6],
                    wrap=True if row[7] else False))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct label {labelId}', exc_info=ex)

        return sectorLabelsMap

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
            """.format(table=UniverseDb._SectorTagsTableName)
        rows = []
        for tag in sector.tags():
            rows.append({
                'id': tag.id(),
                'sector_id': tag.sectorId(),
                'tag': tag.tag()})
        cursor.executemany(sql, rows)

    def _readTags(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # Sector Id
                typing.List[multiverse.DbTag]]:
        sql = """
            SELECT id, sector_id, tag
            FROM {table}
            {where};
            """.format(
                table=UniverseDb._SectorTagsTableName,
                where='WHERE sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

        sectorTagsMap = {}
        for row in cursor.fetchall():
            tagId = row[0]
            sectorId = row[1]
            tags = sectorTagsMap.get(sectorId)
            if tags is None:
                tags = []
                sectorTagsMap[sectorId] = tags

            try:
                tags.append(multiverse.DbTag(
                    id=tagId,
                    sectorId=sectorId,
                    tag=row[2]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct tag {tagId}', exc_info=ex)

        return sectorTagsMap

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
            """.format(table=UniverseDb._ProductsTableName)
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

    def _readProducts(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # Sector Id
                typing.List[multiverse.DbTag]]:
        sql = """
            SELECT id, sector_id, publication, author, publisher, reference
            FROM {table}
            {where};
            """.format(
                table=UniverseDb._ProductsTableName,
                where='WHERE sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

        sectorProductsMap = {}
        for row in cursor.fetchall():
            productId = row[0]
            sectorId = row[1]
            products = sectorProductsMap.get(sectorId)
            if products is None:
                products = []
                sectorProductsMap[sectorId] = products

            try:
                products.append(multiverse.DbProduct(
                    id=productId,
                    sectorId=sectorId,
                    publication=row[2],
                    author=row[3],
                    publisher=row[4],
                    reference=row[5]))
            except Exception as ex:
                logging.error(f'MultiverseDb failed to construct product {productId}', exc_info=ex)

        return sectorProductsMap

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
                """.format(table=UniverseDb._StarsTableName)
            cursor.executemany(sql, rows)

    def _readStars(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # System Id
                typing.List[multiverse.DbStar]]:
        sql = """
            SELECT t.id, t.system_id, t.luminosity_class, t.spectral_class, t.spectral_scale
            FROM {starsTable} AS t
            JOIN {systemsTable} AS s ON s.id = t.system_id
            {where};
            """.format(
                starsTable=UniverseDb._StarsTableName,
                systemsTable=UniverseDb._SystemsTableName,
                where='WHERE s.sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

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
                    systemId=systemId,
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
                """.format(table=UniverseDb._BodiesTableName)
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
                """.format(table=UniverseDb._WorldsTableName)
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

    def _readBodies(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # System Id
                typing.List[multiverse.DbBody]]:
        worldNobilitiesMap = self._readNobilities(
            cursor=cursor,
            sectorId=sectorId)
        worldBasesMap = self._readBases(
            cursor=cursor,
            sectorId=sectorId)
        worldTradeCodesMap = self._readTradeCodes(
            cursor=cursor,
            sectorId=sectorId)
        worldPopulationsMap = self._readSophontPopulations(
            cursor=cursor,
            sectorId=sectorId)
        worldRulingAllegianceMap = self._readRulingAllegiances(
            cursor=cursor,
            sectorId=sectorId)
        worldOwnersMap = self._readOwningSystems(
            cursor=cursor,
            sectorId=sectorId)
        worldColoniesMap = self._readColonySystems(
            cursor=cursor,
            sectorId=sectorId)
        worldResearchStationsMap = self._readResearchStations(
            cursor=cursor,
            sectorId=sectorId)
        worldRemarksMap = self._readCustomRemarks(
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
            {where};
            """.format(
                worldsTable=UniverseDb._WorldsTableName,
                bodiesTable=UniverseDb._BodiesTableName,
                systemsTable=UniverseDb._SystemsTableName,
                where='WHERE s.sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

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
                    systemId=systemId,
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
                """.format(table=UniverseDb._NobilitiesTableName)
            cursor.executemany(sql, rows)

    def _readNobilities(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbNobility]]:
        sql = """
            SELECT t.id, t.world_id, t.code
            FROM {nobilitiesTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            {where};
            """.format(
                nobilitiesTable=UniverseDb._NobilitiesTableName,
                worldsTable=UniverseDb._WorldsTableName,
                bodiesTable=UniverseDb._BodiesTableName,
                systemsTable=UniverseDb._SystemsTableName,
                where='WHERE s.sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

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
                    worldId=worldId,
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
                """.format(table=UniverseDb._BasesTableName)
            cursor.executemany(sql, rows)

    def _readBases(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbBase]]:
        sql = """
            SELECT t.id, t.world_id, t.code
            FROM {basesTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            {where};
            """.format(
                basesTable=UniverseDb._BasesTableName,
                worldsTable=UniverseDb._WorldsTableName,
                bodiesTable=UniverseDb._BodiesTableName,
                systemsTable=UniverseDb._SystemsTableName,
                where='WHERE s.sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

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
                    worldId=worldId,
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
                """.format(table=UniverseDb._TradeCodesTableName)
            cursor.executemany(sql, rows)

    def _readTradeCodes(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbTradeCode]]:
        sql = """
            SELECT t.id, t.world_id, t.code
            FROM {tradeTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            {where};
            """.format(
                tradeTable=UniverseDb._TradeCodesTableName,
                worldsTable=UniverseDb._WorldsTableName,
                bodiesTable=UniverseDb._BodiesTableName,
                systemsTable=UniverseDb._SystemsTableName,
                where='WHERE s.sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

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
                    worldId=worldId,
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
                """.format(table=UniverseDb._SophontPopulationsTableName)
            cursor.executemany(sql, rows)

    def _readSophontPopulations(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbSophontPopulation]]:
        sql = """
            SELECT t.id, t.world_id, t.sophont_id, t.percentage, t.is_home_world, t.is_die_back
            FROM {populationsTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            {where};
            """.format(
                populationsTable=UniverseDb._SophontPopulationsTableName,
                worldsTable=UniverseDb._WorldsTableName,
                bodiesTable=UniverseDb._BodiesTableName,
                systemsTable=UniverseDb._SystemsTableName,
                where='WHERE s.sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

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
                    worldId=worldId,
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
                """.format(table=UniverseDb._RulingAllegiancesTableName)
            cursor.executemany(sql, rows)

    def _readRulingAllegiances(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbRulingAllegiance]]:
        sql = """
            SELECT t.id, t.world_id, t.allegiance_id
            FROM {rulingTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            {where};
            """.format(
                rulingTable=UniverseDb._RulingAllegiancesTableName,
                worldsTable=UniverseDb._WorldsTableName,
                bodiesTable=UniverseDb._BodiesTableName,
                systemsTable=UniverseDb._SystemsTableName,
                where='WHERE s.sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

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
                    worldId=worldId,
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
                """.format(table=UniverseDb._OwningSystemsTableName)
            cursor.executemany(sql, rows)

    def _readOwningSystems(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbOwningSystem]]:
        sql = """
            SELECT t.id, t.world_id, t.hex_x, t.hex_y, t.sector_abbreviation
            FROM {ownersTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            {where};
            """.format(
                ownersTable=UniverseDb._OwningSystemsTableName,
                worldsTable=UniverseDb._WorldsTableName,
                bodiesTable=UniverseDb._BodiesTableName,
                systemsTable=UniverseDb._SystemsTableName,
                where='WHERE s.sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

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
                    worldId=worldId,
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
                """.format(table=UniverseDb._ColonySystemsTableName)
            cursor.executemany(sql, rows)

    def _readColonySystems(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbColonySystem]]:
        sql = """
            SELECT t.id, t.world_id, t.hex_x, t.hex_y, t.sector_abbreviation
            FROM {coloniesTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            {where};
            """.format(
                coloniesTable=UniverseDb._ColonySystemsTableName,
                worldsTable=UniverseDb._WorldsTableName,
                bodiesTable=UniverseDb._BodiesTableName,
                systemsTable=UniverseDb._SystemsTableName,
                where='WHERE s.sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

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
                    worldId=worldId,
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
                """.format(table=UniverseDb._ResearchStationTableName)
            cursor.executemany(sql, rows)

    def _readResearchStations(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbResearchStation]]:
        sql = """
            SELECT t.id, t.world_id, t.code
            FROM {stationsTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            {where};
            """.format(
                stationsTable=UniverseDb._ResearchStationTableName,
                worldsTable=UniverseDb._WorldsTableName,
                bodiesTable=UniverseDb._BodiesTableName,
                systemsTable=UniverseDb._SystemsTableName,
                where='WHERE s.sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

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
                    worldId=worldId,
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
                """.format(table=UniverseDb._CustomRemarksTableName)
            cursor.executemany(sql, rows)

    def _readCustomRemarks(
            self,
            cursor: sqlite3.Cursor,
            sectorId: typing.Optional[str] = None
            ) -> typing.Dict[
                str, # World Id
                typing.List[multiverse.DbCustomRemark]]:
        sql = """
            SELECT t.id, t.world_id, t.remark
            FROM {remarksTable} AS t
            JOIN {worldsTable} AS w ON w.body_id = t.world_id
            JOIN {bodiesTable} AS b ON b.id = w.body_id
            JOIN {systemsTable} AS s ON s.id = b.system_id
            {where};
            """.format(
                remarksTable=UniverseDb._CustomRemarksTableName,
                worldsTable=UniverseDb._WorldsTableName,
                bodiesTable=UniverseDb._BodiesTableName,
                systemsTable=UniverseDb._SystemsTableName,
                where='WHERE s.sector_id = :id' if sectorId else '')

        parameters = {}
        if sectorId:
            parameters['id'] = sectorId
        cursor.execute(sql, parameters)

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
                    worldId=worldId,
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
            ) -> None:
        sql = """
            DELETE FROM {table}
            WHERE id = :id
            """.format(
            table=UniverseDb._SectorsTableName)
        queryData = {'id': sectorId}

        if milieu is not None and sectorX is not None and sectorY is not None:
            sql += 'OR (milieu = :milieu AND sector_x = :sector_x AND sector_y = :sector_y)'
            queryData['milieu'] = milieu
            queryData['sector_x'] = sectorX
            queryData['sector_y'] = sectorY

        sql += ';'
        cursor.execute(sql, queryData)

    def _clearSectors(self, cursor: sqlite3.Cursor) -> None:
        sql = """
            DELETE FROM {table};
            """.format(
            table=UniverseDb._SectorsTableName)
        cursor.execute(sql)

    def _replaceSectors(
            self,
            cursor: sqlite3.Cursor,
            sectors: typing.Collection[multiverse.DbSector]
            ) -> None:
        self._clearSectors(cursor=cursor)
        for sector in sectors:
            self._insertSector(cursor=cursor, sector=sector)