import common
import database
import datetime
import logging
import multiverse
import os
import sqlite3
import typing


# TODO: I need to move allegiances & sophonts from sectors to the universe before
# I can move worlds from the sector to the universe
# - When creating a universe from Traveller Map data, I need to merge the allegiances
#   and sophonts into a single list of each
#   - This might be as simple as creating a map of tuples where the keys are the elements of the
#     object, then iterating over all the instances of the object being imported in all sectors
#     and creating new DB objects if the name isn't in the map
# - When importing a sector, I need to use existing universe entries for objects if
#   there is one that matches what is in the imported data or create a new sophont if
#   none exist
# - This will affect everything that uses allegiances and sophonts
#   - Sophont Population
#   - World Allegiance (System at the DB level)
#   - Route Allegiance
#   - Border Allegiance
#
# IMPORTANT: There is some kind of bug in the allegiance code that means it's generating
# multiple copies of very similar allegiances. For example Zii has Zh and ZhCo but ZhCo isn't
# actually used.
#
# IMPORTANT: I think it might make sense to drop Faraway as they're probably a big source
# of inconsistent allegiances & sophonts
#
# Generating the universe list of allegiances
# - Handling sectors where routes/borders don't use standard allegiance colours
#   - I could drop styles from allegiances and set the allegiance styles on the routes/borders on import
#       - DOWNSIDE: It means the user needs to manually set the colour on allegiance routes/borders rather than just assign the allegiance
#   - I could add something to sectors that allow them to override the styles of an allegiance
#       - DOWNSIDE: More complicated to implement
#   - I could set styles on routes/borders in sectors that don't use the stock styles for an allegiance
#       - The style info on allegiances would just come from the stock style sheet (otu.css)
#       - If the sector styles match the stock style for an allegiance, ignore the styles from the sector and just use the allegiance style
#       - If the sector styles don't match the stock style for an allegiance, set the style on the routes/borders from that sector that use the allegiance in question
# - Rather than storing route/border style info in the allegiance
#   - This is needed so I can have routes/regions for a given allegiance use different styles in different sectors
#   - Ideally I'd resolve it all at import and store the correct colours with the routes/regions but render time logic may prevent that
#   - An alternative would be add allegiance border/style info to the sector
# - When generating the list I probably want to do it by allegiance name




# TODO: Do I want to separate sectors from things like systems/routes/borders etc and treat
# everything more as a single universe rather than a group of sectors.
# - Things like systems/routes/borders would need to be stored as absolute hexes rather than sector relative hexes
# - Need to flatten sophonts/allegiances to make a single set of each for the entire universe
# - I think it would make sense to join border polygons from individual sectors into complete borders
#
# - PRO: I think it more closely models what I'm trying to achieve (a single coherent universe) so will
# make things easier in the future
# - PRO: Having sophonts/allegiances for the whole universe makes it easier for the user to edit things that span multiple sectors
# - CON: Will make it harder to pull updated traveller map data into new sectors
#   - Not sure if I need this functionality
# - CON: If I join borders it could make it harder to export individual sectors (would need to split them again)
#
# At a minimum I think I want to make the sophonts/allegiances per universe
# TODO: When I add support for notes I think I need to have it so you can add notes to the
# stock universe. This probably means keeping notes in a separate table and having it so
# the primary key is the object the notes are for. The editor/database would then need to
# allow writing the notes independently of writing the object. I suspect I'll need to have
# a table per object type _or_ have all objects with notes "inherit" from a base table so
# the the notes table can key off the id in that table. It might be worth doing this as
# the number of object types that will support notes will grow when I add support for gas
# giants etc

class SectorInfo(object):
    def __init__(
            self,
            id: str,
            name: str,
            sectorX: int,
            sectorY: int,
            abbreviation: typing.Optional[str]
            ) -> None:
        common.validateStr(name='id', value=id, allowEmpty=False)
        common.validateStr(name='name', value=name, allowEmpty=False)
        common.validateInt(name='sectorX', value=sectorX)
        common.validateInt(name='sectorY', value=sectorY)
        common.validateStr(name='abbreviation', value=abbreviation, allowNone=True, allowEmpty=False)

        self._id = id
        self._name = name
        self._sectorX = sectorX
        self._sectorY = sectorY
        self._abbreviation = abbreviation

    def id(self) -> str:
        return self._id

    def name(self) -> str:
        return self._name

    def sectorX(self) -> int:
        return self._sectorX

    def sectorY(self) -> int:
        return self._sectorY

    def abbreviation(self) -> typing.Optional[str]:
        return self._abbreviation

class StockSourceInfo(object):
    def __init__(
            self,
            sectorX: int,
            sectorY: int,
            dataHash: typing.Optional[str]
            ) -> None:
        common.validateInt(name='sectorX', value=sectorX)
        common.validateInt(name='sectorY', value=sectorY)
        common.validateStr(name='dataHash', value=dataHash, allowNone=True, allowEmpty=False)

        self._sectorX = sectorX
        self._sectorY = sectorY
        self._dataHash = dataHash

    def sectorX(self) -> int:
        return self._sectorX

    def sectorY(self) -> int:
        return self._sectorY

    def dataHash(self) -> typing.Optional[str]:
        return self._dataHash

class UniverseDb(object):
    _MetadataTableName = 'metadata'
    _MetadataTableSchema = 1
    _MetadataFormatKey = 'format'
    _MetadataMilieuKey = 'milieu'
    _MetadataDescriptionKey = 'description'

    # TODO: Once I've finished moving stuff to the universe I should probably
    # rename all the tables (and variables) where the table has a delete foreign
    # key so they start with the parent table (e.g custom_remarks -> world_custom_remarks,
    # alternate_names -> sector_alternate_names)

    _SectorsTableName = 'sectors'
    _SectorsTableSchema = 1

    _MapLabelsTableName = 'map_labels'
    _MapLabelsTableSchema = 1

    _MapVectorsTableName = 'map_vectors'
    _MapVectorsTableSchema = 1

    _MapVectorPointsTableName = 'map_vector_points'
    _MapVectorPointsTableSchema = 1

    # TODO: The stock sources stuff needs rewritten since I moved stuff from the
    # sector to the universe
    _StockSourcesTableName = 'stock_sources'
    _StockSourcesTableSchema = 1

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

    _SectorLabelsTableName = 'sector_labels'
    _SectorLabelsTableSchema = 1

    _SectorTagsTableName = 'sector_tags'
    _SectorTagsTableSchema = 1

    _ProductsTableName = 'products'
    _ProductsTableSchema = 1

    # TODO: This should just be 1.0 rather than the full string
    # as I'll need to parse it at some point
    _FormatString = 'Auto-Jimmy Universe v1.0'

    _database = None

    def __init__(self, universePath: str) -> None:
        self._universePath = universePath
        if os.path.exists(self._universePath):
            # The path exists so check if it's a valid database
            if not UniverseDb.isUniverseDb(self._universePath):
                raise ValueError(f'File {universePath!r} is not a universe database')

        self._database = database.SchemaDb(path=universePath)
        self._initTables()

    @staticmethod
    def isUniverseDb(universePath: str) -> bool:
        connection = None
        try:
            # NOTE: This intentionally uses a raw sqlite connection to the database
            # (rather than SchemaDb etc) as they automatically create tables in the
            # database and we don't want to do that if it's not a universe database
            connection = sqlite3.connect(universePath)
            cursor = connection.cursor()
            sql = """
                SELECT value
                FROM {metadataTable}
                WHERE key = :key
                LIMIT 1;
                """.format(metadataTable=UniverseDb._MetadataTableName)
            cursor.execute(sql, {'key': UniverseDb._MetadataFormatKey})
            row = cursor.fetchone()
            if not row:
                return False
            return row[0] == UniverseDb._FormatString
        except:
            return False
        finally:
            if connection:
                connection.close()

    def createConnection(self) -> None:
        return self._database.createConnection()

    def createTransaction(
            self,
            onCommitCallback: typing.Optional[typing.Callable[[], None]] = None,
            onRollbackCallback: typing.Optional[typing.Callable[[], None]] = None
            ) -> database.Transaction:
        return self._database.createTransaction(
            onCommitCallback=onCommitCallback,
            onRollbackCallback=onRollbackCallback)

    def milieu(
            self,
            transaction: typing.Optional[database.Transaction] = None
            ) -> str:
        logging.debug(f'UniverseDb reading milieu for universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            milieu = self._readMetadata(
                cursor=connection.cursor(),
                key=UniverseDb._MetadataMilieuKey)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                milieu = self._readMetadata(
                    cursor=connection.cursor(),
                    key=UniverseDb._MetadataMilieuKey)

        if milieu is None:
            raise ValueError('UniverseDb {self._universePath!r} has no milieu metadata')
        return milieu

    def setMilieu(
            self,
            milieu: str,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseDb setting milieu for universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            return self._writeMetadata(
                cursor=connection.cursor(),
                key=UniverseDb._MetadataMilieuKey,
                value=milieu)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._writeMetadata(
                    cursor=connection.cursor(),
                    key=UniverseDb._MetadataMilieuKey,
                    value=milieu)

    def description(
            self,
            transaction: typing.Optional[database.Transaction] = None
            ) -> str:
        logging.debug(f'UniverseDb reading description for universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            description = self._readMetadata(
                cursor=connection.cursor(),
                key=UniverseDb._MetadataDescriptionKey)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                description = self._readMetadata(
                    cursor=connection.cursor(),
                    key=UniverseDb._MetadataDescriptionKey)

        return description if description is not None else ''

    def setDescription(
            self,
            description: str,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseDb setting description for universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            return self._writeMetadata(
                cursor=connection.cursor(),
                key=UniverseDb._MetadataDescriptionKey,
                value=description)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._writeMetadata(
                    cursor=connection.cursor(),
                    key=UniverseDb._MetadataDescriptionKey,
                    value=description)

    def loadAllegiances(
            self,
            transaction: typing.Optional[database.Transaction] = None,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbAllegiance]:
        if transaction != None:
            connection = transaction.connection()
            return self._loadAllegiances(
                cursor=connection.cursor(),
                progress=progress)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._loadAllegiances(
                    cursor=connection.cursor())

    def saveAllegiances(
            self,
            allegiances: typing.Collection[multiverse.DbAllegiance],
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            return self._saveAllegiances(
                allegiances=allegiances,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._saveAllegiances(
                    allegiances=allegiances,
                    cursor=connection.cursor())

    def loadSophonts(
            self,
            transaction: typing.Optional[database.Transaction] = None,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbSophont]:
        if transaction != None:
            connection = transaction.connection()
            return self._loadSophonts(
                cursor=connection.cursor(),
                progress=progress)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._loadSophonts(
                    cursor=connection.cursor(),
                    progress=progress)

    def saveSophonts(
            self,
            sophonts: multiverse.DbSophont,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            return self._saveSophonts(
                sophonts=sophonts,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._saveSophonts(
                    sophonts=sophonts,
                    cursor=connection.cursor())

    def listSectors(
            self,
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.List[SectorInfo]:
        if transaction != None:
            connection = transaction.connection()
            return self._listSectors(
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._listSectors(
                    cursor=connection.cursor())

    def saveSectors(
            self,
            sectors: typing.Collection[multiverse.DbSector],
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            cursor = connection.cursor()
            self._saveSectors(cursor=cursor, sectors=sectors)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                cursor = connection.cursor()
                self._saveSectors(cursor=cursor, sectors=sectors)

    def loadSectors(
            self,
            transaction: typing.Optional[database.Transaction] = None,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbSector]:
        if transaction != None:
            connection = transaction.connection()
            return self._loadSectors(
                cursor=connection.cursor(),
                progress=progress)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._loadSectors(
                    cursor=connection.cursor(),
                    progress=progress)

    def deleteSectors(
            self,
            sectorIds: typing.Collection[str],
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            self._deleteSectors(
                sectorIds=sectorIds,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._deleteSectors(
                    sectorIds=sectorIds,
                    cursor=connection.cursor())

    def loadSystems(
            self,
            transaction: typing.Optional[database.Transaction] = None,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbSystem]:
        if transaction != None:
            connection = transaction.connection()
            return self._loadSystems(
                cursor=connection.cursor(),
                progress=progress)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._loadSystems(
                    cursor=connection.cursor(),
                    progress=progress)

    def saveSystems(
            self,
            systems: typing.Collection[multiverse.DbSystem],
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            self._saveSystems(
                systems=systems,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._saveSystems(
                    systems=systems,
                    cursor=connection.cursor())

    def deleteSystems(
            self,
            systemIds: typing.Collection[str],
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            self._deleteSystems(
                systemIds=systemIds,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._deleteSystems(
                    systemIds=systemIds,
                    cursor=connection.cursor())

    def saveMapLabels(
            self,
            labels: typing.Collection[multiverse.DbMapLabel],
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            return self._saveMapLabels(
                labels=labels,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._saveMapLabels(
                    labels=labels,
                    cursor=connection.cursor())

    def loadMapLabels(
            self,
            transaction: typing.Optional[database.Transaction] = None,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbMapLabel]:
        if transaction != None:
            connection = transaction.connection()
            return self._loadMapLabels(
                cursor=connection.cursor(),
                progress=progress)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._loadMapLabels(
                    cursor=connection.cursor(),
                    progress=progress)

    def saveMapVectors(
            self,
            vectors: typing.Collection[multiverse.DbMapVector],
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            return self._saveMapVectors(
                vectors=vectors,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._saveMapVectors(
                    vectors=vectors,
                    cursor=connection.cursor())

    def loadMapVectors(
            self,
            transaction: typing.Optional[database.Transaction] = None,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbMapLabel]:
        if transaction != None:
            connection = transaction.connection()
            return self._loadMapVectors(
                cursor=connection.cursor(),
                progress=progress)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._loadMapVectors(
                    cursor=connection.cursor(),
                    progress=progress)

    def copyTo(self, targetPath: str) -> None:
        self._database.copyTo(targetPath=targetPath)

    def _initTables(self) -> None:
        with self.createTransaction() as transaction:
            connection = transaction.connection()
            cursor = connection.cursor()

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._MetadataTableName,
                requiredSchemaVersion=UniverseDb._MetadataTableSchema,
                columns=[
                    database.ColumnDef(columnName='key', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='value', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)])
            self._writeMetadata(
                cursor=cursor,
                key=UniverseDb._MetadataFormatKey,
                value=UniverseDb._FormatString)

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._SectorsTableName,
                requiredSchemaVersion=UniverseDb._SectorsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='sector_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='language', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='abbreviation', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='sector_label', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='selected', columnType=database.ColumnDef.ColumnType.Integer, allowedValues=(0, 1), isNullable=False),
                    database.ColumnDef(columnName='credits', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='publication', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='author', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='publisher', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='reference', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='notes', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['sector_x', 'sector_y'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._MapLabelsTableName,
                requiredSchemaVersion=UniverseDb._MapLabelsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='text', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='x', columnType=database.ColumnDef.ColumnType.Real, isNullable=False),
                    database.ColumnDef(columnName='y', columnType=database.ColumnDef.ColumnType.Real, isNullable=False),
                    database.ColumnDef(columnName='layer', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='alignment', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='colour', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='size', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='rotation', columnType=database.ColumnDef.ColumnType.Real, isNullable=True)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._MapVectorsTableName,
                requiredSchemaVersion=UniverseDb._MapVectorsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='layer', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    # TODO: Can I get rid of the closed flag? Can't I just make sure the first point is also
                    # the last point for closed polygons?
                    database.ColumnDef(columnName='closed', columnType=database.ColumnDef.ColumnType.Integer, allowedValues=(0, 1), isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._MapVectorPointsTableName,
                requiredSchemaVersion=UniverseDb._MapVectorPointsTableSchema,
                columns=[
                    database.ColumnDef(columnName='vector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._MapVectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='x', columnType=database.ColumnDef.ColumnType.Real, isNullable=False),
                    database.ColumnDef(columnName='y', columnType=database.ColumnDef.ColumnType.Real, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._StockSourcesTableName,
                requiredSchemaVersion=UniverseDb._StockSourcesTableSchema,
                columns=[
                    # NOTE: It's very important that if I ever add anything to this table I also
                    # update _saveSector so, it's maintained when the old sector data is deleted
                    # and the new sector data is added.
                    database.ColumnDef(columnName='sector_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='sector_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='data_hash', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)],
                primaryKeyDef=database.PrimaryKeyDef(columnNames=['sector_x', 'sector_y']))

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._AlternateNamesTableName,
                requiredSchemaVersion=UniverseDb._AlternateNamesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='language', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._SubsectorNamesTableName,
                requiredSchemaVersion=UniverseDb._SubsectorNamesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='code', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              minValue='A', maxValue='P'),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['sector_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._AllegiancesTableName,
                requiredSchemaVersion=UniverseDb._AllegiancesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='code', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='legacy', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='base', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='route_colour', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='route_style', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='route_width', columnType=database.ColumnDef.ColumnType.Real, isNullable=True, minValue=0),
                    database.ColumnDef(columnName='border_colour', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='border_style', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._SophontsTableName,
                requiredSchemaVersion=UniverseDb._SophontsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='code', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='is_major', columnType=database.ColumnDef.ColumnType.Integer, allowedValues=(0, 1), isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._SystemsTableName,
                requiredSchemaVersion=UniverseDb._SystemsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='hex_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='hex_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='planetoid_belt_count', columnType=database.ColumnDef.ColumnType.Integer, isNullable=True, minValue=0),
                    database.ColumnDef(columnName='gas_giant_count', columnType=database.ColumnDef.ColumnType.Integer, isNullable=True, minValue=0),
                    # NOTE: The world count is NOT the same as the system world count from
                    # second survey sector format. The system would count includes belts
                    # and gas giants where as this world count does not (but it does include
                    # the main world)
                    database.ColumnDef(columnName='world_count', columnType=database.ColumnDef.ColumnType.Integer, isNullable=True, minValue=0),
                    database.ColumnDef(columnName='zone', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='allegiance_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=True,
                              foreignTableName=UniverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.SetNull),
                    database.ColumnDef(columnName='notes', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['hex_x', 'hex_y'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._BodiesTableName,
                requiredSchemaVersion=UniverseDb._BodiesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='system_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SystemsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='orbit_index', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='notes', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._StarsTableName,
                requiredSchemaVersion=UniverseDb._StarsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='system_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SystemsTableName, foreignColumnName='id',
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
                tableName=UniverseDb._WorldsTableName,
                requiredSchemaVersion=UniverseDb._WorldsTableSchema,
                columns=[
                    database.ColumnDef(columnName='body_id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True,
                                foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                                foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='is_main_world', columnType=database.ColumnDef.ColumnType.Integer, allowedValues=(0, 1), isNullable=False),
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
                tableName=UniverseDb._NobilitiesTableName,
                requiredSchemaVersion=UniverseDb._NobilitiesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='code', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['world_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._TradeCodesTableName,
                requiredSchemaVersion=UniverseDb._TradeCodesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='code', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['world_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._SophontPopulationsTableName,
                requiredSchemaVersion=UniverseDb._SophontPopulationsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='sophont_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SophontsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='percentage', columnType=database.ColumnDef.ColumnType.Integer, isNullable=True, minValue=0, maxValue=100),
                    database.ColumnDef(columnName='is_home_world', columnType=database.ColumnDef.ColumnType.Integer, allowedValues=(0, 1), isNullable=False),
                    database.ColumnDef(columnName='is_die_back', columnType=database.ColumnDef.ColumnType.Integer, allowedValues=(0, 1), isNullable=False)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['world_id', 'sophont_id'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._RulingAllegiancesTableName,
                requiredSchemaVersion=UniverseDb._RulingAllegiancesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='allegiance_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['world_id', 'allegiance_id'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._OwningSystemsTableName,
                requiredSchemaVersion=UniverseDb._OwningSystemsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    # TODO: This should be converted to absolute space hex As part of the changes to move things to the universe label
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
                tableName=UniverseDb._ColonySystemsTableName,
                requiredSchemaVersion=UniverseDb._ColonySystemsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    # TODO: This should be converted to absolute space hex As part of the changes to move things to the universe label
                    database.ColumnDef(columnName='hex_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='hex_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    # NOTE: See comment on owning systems as to why this is the
                    # abbreviation rather than the sector id
                    database.ColumnDef(columnName='sector_abbreviation', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['world_id', 'hex_x', 'hex_y', 'sector_abbreviation'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._ResearchStationTableName,
                requiredSchemaVersion=UniverseDb._ResearchStationTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='code', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['world_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._CustomRemarksTableName,
                requiredSchemaVersion=UniverseDb._CustomRemarksTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='remark', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._BasesTableName,
                requiredSchemaVersion=UniverseDb._BasesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='code', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['world_id', 'code'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._RoutesTableName,
                requiredSchemaVersion=UniverseDb._RoutesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    # TODO: These hexes should be converted to absolute space hex As part of the changes to move things to the universe label
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
                              foreignTableName=UniverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.SetNull)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._BordersTableName,
                requiredSchemaVersion=UniverseDb._BordersTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='allegiance_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=True,
                              foreignTableName=UniverseDb._AllegiancesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.SetNull),
                    database.ColumnDef(columnName='style', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='colour', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='label', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    # NOTE: The label position is stored as an offset in world space from the
                    # origin of the sector (top, left). An offset is used rather than storing
                    # world space coordinates to keep sector data relative to the sector. It
                    # will make it easier if we ever want to move a sector
                    # TODO: This should be converted to world space as part of the changes to move things to the universe label
                    database.ColumnDef(columnName='label_x', columnType=database.ColumnDef.ColumnType.Real, isNullable=True),
                    database.ColumnDef(columnName='label_y', columnType=database.ColumnDef.ColumnType.Real, isNullable=True),
                    database.ColumnDef(columnName='show_label', columnType=database.ColumnDef.ColumnType.Integer, allowedValues=(0, 1), isNullable=False),
                    database.ColumnDef(columnName='wrap_label', columnType=database.ColumnDef.ColumnType.Integer, allowedValues=(0, 1), isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._BorderHexesTableName,
                requiredSchemaVersion=UniverseDb._BorderHexesTableSchema,
                columns=[
                    database.ColumnDef(columnName='border_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BordersTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    # TODO: These hexes should be converted to absolute space hex as part of the changes to move things to the universe label
                    database.ColumnDef(columnName='hex_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='hex_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._RegionsTableName,
                requiredSchemaVersion=UniverseDb._RegionsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='colour', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='label', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    # NOTE: See note on borders about coordinate space used for world x/y
                    # TODO: This should be converted to world space as part of the changes to move things to the universe label
                    database.ColumnDef(columnName='label_x', columnType=database.ColumnDef.ColumnType.Real, isNullable=True),
                    database.ColumnDef(columnName='label_y', columnType=database.ColumnDef.ColumnType.Real, isNullable=True),
                    database.ColumnDef(columnName='show_label', columnType=database.ColumnDef.ColumnType.Integer, allowedValues=(0, 1), isNullable=False),
                    database.ColumnDef(columnName='wrap_label', columnType=database.ColumnDef.ColumnType.Integer, allowedValues=(0, 1), isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._RegionHexesTableName,
                requiredSchemaVersion=UniverseDb._RegionHexesTableSchema,
                columns=[
                    database.ColumnDef(columnName='region_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._RegionsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    # TODO: These hexes should be converted to absolute space hex as part of the changes to move things to the universe label
                    database.ColumnDef(columnName='hex_x', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False),
                    database.ColumnDef(columnName='hex_y', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._SectorLabelsTableName,
                requiredSchemaVersion=UniverseDb._SectorLabelsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='text', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    # TODO: This should be converted to world space as part of the changes to move things to the universe label
                    database.ColumnDef(columnName='x', columnType=database.ColumnDef.ColumnType.Real, isNullable=False),
                    database.ColumnDef(columnName='y', columnType=database.ColumnDef.ColumnType.Real, isNullable=False),
                    database.ColumnDef(columnName='colour', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='size', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='wrap', columnType=database.ColumnDef.ColumnType.Integer, allowedValues=(0, 1), isNullable=False)])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._SectorTagsTableName,
                requiredSchemaVersion=UniverseDb._SectorTagsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='tag', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)],
                uniqueConstraints=[
                    database.UniqueConstraintDef(columnNames=['sector_id', 'tag'])])

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._ProductsTableName,
                requiredSchemaVersion=UniverseDb._ProductsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='sector_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._SectorsTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='publication', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='author', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='publisher', columnType=database.ColumnDef.ColumnType.Text, isNullable=True),
                    database.ColumnDef(columnName='reference', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)])

    def _readMetadata(
            self,
            cursor: sqlite3.Cursor,
            key: str
            ) -> typing.Optional[str]:
        rows = self._database.select(
            cursor=cursor,
            tableName=UniverseDb._MetadataTableName,
            columns=('value',),
            where='key = :key',
            parameters={'key': key},
            limit=1)
        if not rows:
            return None
        return rows[0]['value']

    def _writeMetadata(
            self,
            cursor: sqlite3.Cursor,
            key: str,
            value: str
            ) -> None:
        self._database.insert(
            cursor=cursor,
            tableName=UniverseDb._MetadataTableName,
            values={'key': key, 'value': value},
            replaceIfExists=True)

    #      █████████   ████  ████                     ███
    #     ███░░░░░███ ░░███ ░░███                    ░░░
    #    ░███    ░███  ░███  ░███   ██████   ███████ ████   ██████   ████████    ██████   ██████   █████
    #    ░███████████  ░███  ░███  ███░░███ ███░░███░░███  ░░░░░███ ░░███░░███  ███░░███ ███░░███ ███░░
    #    ░███░░░░░███  ░███  ░███ ░███████ ░███ ░███ ░███   ███████  ░███ ░███ ░███ ░░░ ░███████ ░░█████
    #    ░███    ░███  ░███  ░███ ░███░░░  ░███ ░███ ░███  ███░░███  ░███ ░███ ░███  ███░███░░░   ░░░░███
    #    █████   █████ █████ █████░░██████ ░░███████ █████░░████████ ████ █████░░██████ ░░██████  ██████
    #   ░░░░░   ░░░░░ ░░░░░ ░░░░░  ░░░░░░   ░░░░░███░░░░░  ░░░░░░░░ ░░░░ ░░░░░  ░░░░░░   ░░░░░░  ░░░░░░
    #                                       ███ ░███
    #                                      ░░██████
    #                                       ░░░░░░

    def _saveAllegiances(
            self,
            cursor: sqlite3.Cursor,
            allegiances: typing.Collection[multiverse.DbAllegiance]
            ) -> None:
        if not allegiances:
            return

        rows = []
        for allegiance in allegiances:
            logging.debug(f'UniverseDb saving allegiances {allegiance.id()!r} to universe {self._universePath!r}')

            rows.append({
                'id': allegiance.id(),
                'name': allegiance.name(),
                'code': allegiance.code(),
                'legacy': allegiance.legacy(),
                'base': allegiance.base(),
                'route_colour': allegiance.routeColour(),
                'route_style': allegiance.routeStyle(),
                'route_width': allegiance.routeWidth(),
                'border_colour': allegiance.borderColour(),
                'border_style': allegiance.borderStyle()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._AllegiancesTableName,
            rows=rows,
            # NOTE: It's important that allegiances are replaced if the exist (rather
            # than deleting and reinserting) as there are other tables that use allegiance
            # id as a foreign key so data will be lost if it's deleted
            replaceIfExists=True)

    def _loadAllegiances(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbAllegiance]:
        logging.debug(f'UniverseDb loading allegiances from universe {self._universePath!r}')

        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._AllegiancesTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        allegiances = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._AllegiancesTableName):
            allegianceId = row['id']
            try:
                allegiances.append(multiverse.DbAllegiance(
                    id=allegianceId,
                    name=row['name'],
                    code=row['code'],
                    legacy=row['legacy'],
                    base=row['base'],
                    routeColour=row['route_colour'],
                    routeStyle=row['route_style'],
                    routeWidth=row['route_width'],
                    borderColour=row['border_colour'],
                    borderStyle=row['border_style']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load allegiance {allegianceId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return allegiances

    def _deleteAllegiances(
            self,
            cursor: sqlite3.Cursor,
            allegianceIds: typing.Collection[str]
            ) -> None:
        parameters = []
        for allegianceId in allegianceIds:
            logging.debug(f'UniverseDb deleting allegiance {allegianceId!r} from universe {self._universePath!r}')
            parameters.append((allegianceId,))

        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._AllegiancesTableName,
            where='id = ?',
            parameters=parameters)

    #     █████████                     █████                           █████
    #    ███░░░░░███                   ░░███                           ░░███
    #   ░███    ░░░   ██████  ████████  ░███████    ██████  ████████   ███████    █████
    #   ░░█████████  ███░░███░░███░░███ ░███░░███  ███░░███░░███░░███ ░░░███░    ███░░
    #    ░░░░░░░░███░███ ░███ ░███ ░███ ░███ ░███ ░███ ░███ ░███ ░███   ░███    ░░█████
    #    ███    ░███░███ ░███ ░███ ░███ ░███ ░███ ░███ ░███ ░███ ░███   ░███ ███ ░░░░███
    #   ░░█████████ ░░██████  ░███████  ████ █████░░██████  ████ █████  ░░█████  ██████
    #    ░░░░░░░░░   ░░░░░░   ░███░░░  ░░░░ ░░░░░  ░░░░░░  ░░░░ ░░░░░    ░░░░░  ░░░░░░
    #                         ░███
    #                         █████
    #                        ░░░░░

    def _saveSophonts(
            self,
            cursor: sqlite3.Cursor,
            sophonts: typing.Collection[multiverse.DbSophont]
            ) -> None:
        if not sophonts:
            return

        rows = []
        for sophont in sophonts:
            logging.debug(f'UniverseDb saving sophont {sophont.id()!r} to universe {self._universePath!r}')

            rows.append({
                'id': sophont.id(),
                'name': sophont.name(),
                'code': sophont.code(),
                'is_major': int(sophont.isMajor())})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._SophontsTableName,
            rows=rows,
            # NOTE: It's important that sophonts are replaced if the exist (rather than
            # deleting and reinserting) as there are other tables that use sophont id
            # as a foreign key so data will be lost if it's deleted
            replaceIfExists=True)

    def _loadSophonts(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbSophont]:
        logging.debug(f'UniverseDb loading sophonts from universe {self._universePath!r}')

        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._SophontsTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        sophonts = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._SophontsTableName):
            sophontId = row['id']
            try:
                sophonts.append(multiverse.DbSophont(
                    id=sophontId,
                    name=row['name'],
                    code=row['code'],
                    isMajor=bool(row['is_major'])))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load sophont {sophontId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return sophonts

    def _deleteSophonts(
            self,
            cursor: sqlite3.Cursor,
            sophontIds: typing.Collection[str]
            ) -> None:
        parameters = []
        for sophontId in sophontIds:
            logging.debug(f'UniverseDb deleting sophont {sophontId!r} from universe {self._universePath!r}')
            parameters.append((sophontId,))

        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._SophontsTableName,
            where='id = ?',
            parameters=parameters)

    #     █████████                     █████
    #    ███░░░░░███                   ░░███
    #   ░███    ░░░   ██████   ██████  ███████    ██████  ████████   █████
    #   ░░█████████  ███░░███ ███░░███░░░███░    ███░░███░░███░░███ ███░░
    #    ░░░░░░░░███░███████ ░███ ░░░   ░███    ░███ ░███ ░███ ░░░ ░░█████
    #    ███    ░███░███░░░  ░███  ███  ░███ ███░███ ░███ ░███      ░░░░███
    #   ░░█████████ ░░██████ ░░██████   ░░█████ ░░██████  █████     ██████
    #    ░░░░░░░░░   ░░░░░░   ░░░░░░     ░░░░░   ░░░░░░  ░░░░░     ░░░░░░

    def _listSectors(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[SectorInfo]:
        logging.debug(f'UniverseDb listing sectors in universe {self._universePath!r}')

        rows = self._database.select(
            cursor=cursor,
            tableName=UniverseDb._SectorsTableName,
            columns=('id', 'name', 'sector_x', 'sector_y', 'abbreviation'))
        sectorList = []
        for row in rows:
            sectorList.append(SectorInfo(
                id=row['id'],
                name=row['name'],
                sectorX=row['sector_x'],
                sectorY=row['sector_y'],
                abbreviation=row['abbreviation']))
        return sectorList

    def _saveSectors(
            self,
            cursor: sqlite3.Cursor,
            sectors: typing.Collection[multiverse.DbSector]
            ) -> None:
        if not sectors:
            return

        # Any existing sectors with the same id or sector position as a sector
        # being saved should be deleted before the new sectors are inserted.
        # This handles two cases:
        # - Existing sectors that have been updated
        # - Sectors that have been moved to a location that already has a
        #   sector in it
        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._SectorsTableName,
            where='id == ? OR (sector_x == ? AND sector_y == ?)',
            parameters=((s.id(), s.sectorX(), s.sectorY()) for s in sectors))

        rows = []
        for sector in sectors:
            logging.debug(f'UniverseDb saving sector {sector.id()!r} to universe {self._universePath!r}')

            rows.append({
                'id': sector.id(),
                'sector_x': sector.sectorX(),
                'sector_y': sector.sectorY(),
                'name': sector.name(),
                'language': sector.language(),
                'abbreviation': sector.abbreviation(),
                'sector_label': sector.sectorLabel(),
                'selected': int(sector.selected()),
                'credits': sector.credits(),
                'publication': sector.publication(),
                'author': sector.author(),
                'publisher': sector.publisher(),
                'reference': sector.reference(),
                'notes': sector.notes()})

        names = []
        subsectors = []
        routes = []
        borders = []
        regions = []
        labels = []
        tags = []
        products = []
        for sector in sectors:
            if sector.alternateNames():
                names.extend(sector.alternateNames())
            if sector.subsectorNames():
                subsectors.extend(sector.subsectorNames())
            if sector.routes():
                routes.extend(sector.routes())
            if sector.borders():
                borders.extend(sector.borders())
            if sector.regions():
                regions.extend(sector.regions())
            if sector.labels():
                labels.extend(sector.labels())
            if sector.tags():
                tags.extend(sector.tags())
            if sector.products():
                products.extend(sector.products())
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._SectorsTableName,
            rows=rows)

        if names:
            self._insertAlternateNames(cursor=cursor, names=names)
        if subsectors:
            self._insertSubsectorNames(cursor=cursor, names=subsectors)
        if routes:
            self._insertRoutes(cursor=cursor, routes=routes)
        if borders:
            self._insertBorders(cursor=cursor, borders=borders)
        if regions:
            self._insertRegions(cursor=cursor, regions=regions)
        if labels:
            self._insertSectorLabels(cursor=cursor, labels=labels)
        if tags:
            self._insertTags(cursor=cursor, tags=tags)
        if products:
            self._insertProducts(cursor=cursor, products=products)

    def _loadSectors(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbSector]:
        logging.debug(f'UniverseDb loading sectors from universe {self._universePath!r}')

        taskCount = 9
        taskWeight = 1 / taskCount

        alternateNamesProgress = None
        if progress:
            alternateNamesProgress = progress.createChild(weight=taskWeight)
        alternateNamesMap = {}
        for name in self._loadAlternateNames(cursor=cursor, progress=alternateNamesProgress):
            names = alternateNamesMap.get(name.sectorId())
            if names is None:
                names = []
                alternateNamesMap[name.sectorId()] = names
            names.append(name)

        subsectorNamesProgress = None
        if progress:
            subsectorNamesProgress = progress.createChild(weight=taskWeight)
        subsectorNamesMap = {}
        for name in self._loadSubsectorNames(cursor=cursor, progress=subsectorNamesProgress):
            names = subsectorNamesMap.get(name.sectorId())
            if names is None:
                names = []
                subsectorNamesMap[name.sectorId()] = names
            names.append(name)

        routesProgress = None
        if progress:
            routesProgress = progress.createChild(weight=taskWeight)
        routesMap = {}
        for route in self._loadRoutes(cursor=cursor, progress=routesProgress):
            routes = routesMap.get(route.sectorId())
            if routes is None:
                routes = []
                routesMap[route.sectorId()] = routes
            routes.append(route)

        bordersProgress = None
        if progress:
            bordersProgress = progress.createChild(weight=taskWeight)
        bordersMap = {}
        for border in self._loadBorders(cursor=cursor, progress=bordersProgress):
            borders = bordersMap.get(border.sectorId())
            if borders is None:
                borders = []
                bordersMap[border.sectorId()] = borders
            borders.append(border)

        regionsProgress = None
        if progress:
            regionsProgress = progress.createChild(weight=taskWeight)
        regionsMap = {}
        for region in self._loadRegions(cursor=cursor, progress=regionsProgress):
            regions = regionsMap.get(region.sectorId())
            if regions is None:
                regions = []
                regionsMap[region.sectorId()] = regions
            regions.append(region)

        labelsProgress = None
        if progress:
            labelsProgress = progress.createChild(weight=taskWeight)
        labelsMap = {}
        for label in self._loadSectorLabels(cursor=cursor, progress=labelsProgress):
            labels = labelsMap.get(label.sectorId())
            if labels is None:
                labels = []
                labelsMap[label.sectorId()] = labels
            labels.append(label)

        tagsProgress = None
        if progress:
            tagsProgress = progress.createChild(weight=taskWeight)
        tagsMap = {}
        for tag in self._loadTags(cursor=cursor, progress=tagsProgress):
            tags = tagsMap.get(tag.sectorId())
            if tags is None:
                tags = []
                tagsMap[tag.sectorId()] = tags
            tags.append(tag)

        productsProgress = None
        if progress:
            productsProgress = progress.createChild(weight=taskWeight)
        productsMap = {}
        for product in self._loadProducts(cursor=cursor, progress=productsProgress):
            products = productsMap.get(product.sectorId())
            if products is None:
                products = []
                productsMap[product.sectorId()] = products
            products.append(product)

        sectorCount = self._database.rowCount(cursor=cursor, tableName=UniverseDb._SectorsTableName)
        sectorsProgress = None
        if progress:
            sectorsProgress = progress.createChild(weight=taskWeight, steps=sectorCount)
        sectors = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._SectorsTableName):
            sectorId = row['id']

            try:
                sectors.append(multiverse.DbSector(
                    id=sectorId,
                    sectorX=row['sector_x'],
                    sectorY=row['sector_y'],
                    name=row['name'],
                    language=row['language'],
                    abbreviation=row['abbreviation'],
                    sectorLabel=row['sector_label'],
                    selected=bool(row['selected']),
                    credits=row['credits'],
                    publication=row['publication'],
                    author=row['author'],
                    publisher=row['publisher'],
                    reference=row['reference'],
                    notes=row['notes'],
                    alternateNames=alternateNamesMap.get(sectorId),
                    subsectorNames=subsectorNamesMap.get(sectorId),
                    routes=routesMap.get(sectorId),
                    borders=bordersMap.get(sectorId),
                    regions=regionsMap.get(sectorId),
                    labels=labelsMap.get(sectorId),
                    tags=tagsMap.get(sectorId),
                    products=productsMap.get(sectorId)))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load sector {sectorId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if sectorsProgress:
            sectorsProgress.advance(increment=sectorCount)

        return sectors

    def _deleteSectors(
            self,
            cursor: sqlite3.Cursor,
            sectorIds: str
            ) -> None:
        parameters = []
        for sectorId in sectorIds:
            logging.debug(f'UniverseDb deleting sector {sectorId!r} from universe {self._universePath!r}')
            parameters.append((sectorId,))

        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._SectorsTableName,
            where='id = ?',
            parameters=parameters)

    def _insertAlternateNames(
            self,
            cursor: sqlite3.Cursor,
            names: typing.Collection[multiverse.DbAlternateName]
            ) -> None:
        if not names:
            return

        rows = []
        for alternateName in names:
            rows.append({
                'id': alternateName.id(),
                'sector_id': alternateName.sectorId(),
                'name': alternateName.name(),
                'language': alternateName.language()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._AlternateNamesTableName,
            rows=rows)

    def _loadAlternateNames(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbAlternateName]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._AlternateNamesTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        names = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._AlternateNamesTableName):
            nameId = row['id']

            try:
                names.append(multiverse.DbAlternateName(
                    id=nameId,
                    sectorId=row['sector_id'],
                    name=row['name'],
                    language=row['language']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load alternate name {nameId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return names

    def _insertSubsectorNames(
            self,
            cursor: sqlite3.Cursor,
            names: typing.Collection[multiverse.DbSubsectorName]
            ) -> None:
        if not names:
            return

        rows = []
        for subsectorName in names:
            rows.append({
                'id': subsectorName.id(),
                'sector_id': subsectorName.sectorId(),
                'code': subsectorName.code(),
                'name': subsectorName.name()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._SubsectorNamesTableName,
            rows=rows)

    def _loadSubsectorNames(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbSubsectorName]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._SubsectorNamesTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        names = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._SubsectorNamesTableName):
            nameId = row['id']

            try:
                names.append(multiverse.DbSubsectorName(
                    id=nameId,
                    sectorId=row['sector_id'],
                    code=row['code'],
                    name=row['name']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load subsector name {nameId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return names

    def _insertSectorLabels(
            self,
            cursor: sqlite3.Cursor,
            labels: typing.Collection[multiverse.DbSectorLabel]
            ) -> None:
        if not labels:
            return

        rows = []
        for label in labels:
            rows.append({
                'id': label.id(),
                'sector_id': label.sectorId(),
                'text': label.text(),
                'x': label.worldX(),
                'y': label.worldY(),
                'colour': label.colour(),
                'size': label.size(),
                'wrap': int(label.wrap())})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._SectorLabelsTableName,
            rows=rows)

    def _loadSectorLabels(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbSectorLabel]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._SectorLabelsTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        labels = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._SectorLabelsTableName):
            labelId = row['id']

            try:
                labels.append(multiverse.DbSectorLabel(
                    id=labelId,
                    sectorId=row['sector_id'],
                    text=row['text'],
                    worldX=row['x'],
                    worldY=row['y'],
                    colour=row['colour'],
                    size=row['size'],
                    wrap=bool(row['wrap'])))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load label {labelId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return labels

    def _insertTags(
            self,
            cursor: sqlite3.Cursor,
            tags: typing.Collection[multiverse.DbTag]
            ) -> None:
        if not tags:
            return

        rows = []
        for tag in tags:
            rows.append({
                'id': tag.id(),
                'sector_id': tag.sectorId(),
                'tag': tag.tag()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._SectorTagsTableName,
            rows=rows)

    def _loadTags(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbTag]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._SectorTagsTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        tags = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._SectorTagsTableName):
            tagId = row['id']

            try:
                tags.append(multiverse.DbTag(
                    id=tagId,
                    sectorId=row['sector_id'],
                    tag=row['tag']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load tag {tagId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return tags

    def _insertProducts(
            self,
            cursor: sqlite3.Cursor,
            products: typing.Collection[multiverse.DbProduct]
            ) -> None:
        if not products:
            return

        rows = []
        for product in products:
            rows.append({
                'id': product.id(),
                'sector_id': product.sectorId(),
                'publication': product.publication(),
                'author': product.author(),
                'publisher': product.publisher(),
                'reference': product.reference()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._ProductsTableName,
            rows=rows)

    def _loadProducts(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbTag]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._ProductsTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        products = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._ProductsTableName):
            productId = row['id']

            try:
                products.append(multiverse.DbProduct(
                    id=productId,
                    sectorId=row['sector_id'],
                    publication=row['publication'],
                    author=row['author'],
                    publisher=row['publisher'],
                    reference=row['reference']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load product {productId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return products

    #     █████████                      █████
    #    ███░░░░░███                    ░░███
    #   ░███    ░░░  █████ ████  █████  ███████    ██████  █████████████    █████
    #   ░░█████████ ░░███ ░███  ███░░  ░░░███░    ███░░███░░███░░███░░███  ███░░
    #    ░░░░░░░░███ ░███ ░███ ░░█████   ░███    ░███████  ░███ ░███ ░███ ░░█████
    #    ███    ░███ ░███ ░███  ░░░░███  ░███ ███░███░░░   ░███ ░███ ░███  ░░░░███
    #   ░░█████████  ░░███████  ██████   ░░█████ ░░██████  █████░███ █████ ██████
    #    ░░░░░░░░░    ░░░░░███ ░░░░░░     ░░░░░   ░░░░░░  ░░░░░ ░░░ ░░░░░ ░░░░░░
    #                 ███ ░███
    #                ░░██████
    #                 ░░░░░░

    def _saveSystems(
            self,
            cursor: sqlite3.Cursor,
            systems: typing.Collection[multiverse.DbSystem]
            ) -> None:
        if not systems:
            return

        # Any existing systems with the same id or hex position as a system
        # being saved should be deleted before the new systems are inserted.
        # This handles two cases:
        # - Existing systems that have been updated
        # - Systems that have been moved to a location that already has a
        #   system in it
        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._SystemsTableName,
            where='id == ? OR (hex_x == ? AND hex_y == ?)',
            parameters=((s.id(), s.hexX(), s.hexY()) for s in systems))

        rows = []
        for system in systems:
            logging.debug(f'UniverseDb saving system {system.id()!r} to universe {self._universePath!r}')
            rows.append({
                'id': system.id(),
                'hex_x': system.hexX(),
                'hex_y': system.hexY(),
                'name': system.name(),
                'planetoid_belt_count': system.planetoidBeltCount(),
                'gas_giant_count': system.gasGiantCount(),
                'world_count': system.worldCount(),
                'zone': system.zone(),
                'allegiance_id': system.allegianceId(),
                'notes': system.notes()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._SystemsTableName,
            rows=rows)

        stars = []
        bodies = []
        for system in systems:
            if system.stars():
                stars.extend(system.stars())
            if system.bodies():
                bodies.extend(system.bodies())
        if stars:
            self._insertStars(cursor=cursor, stars=stars)
        if bodies:
            self._insertBodies(cursor=cursor, bodies=bodies)

    def _loadSystems(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbSystem]:
        logging.debug(f'UniverseDb loading systems from universe {self._universePath!r}')

        taskCount = 3
        taskWeight = 1 / taskCount

        stars = self._loadStars(
            cursor=cursor,
            progress=progress.createChild(weight=taskWeight) if progress is not None else None)
        systemStarsMap = {}
        for star in stars:
            systemStars = systemStarsMap.get(star.systemId())
            if systemStars is None:
                systemStars = []
                systemStarsMap[star.systemId()] = systemStars
            systemStars.append(star)

        bodies = self._loadBodies(
            cursor=cursor,
            progress=progress.createChild(weight=taskWeight) if progress is not None else None)
        systemBodiesMap = {}
        for body in bodies:
            systemBodies = systemBodiesMap.get(body.systemId())
            if systemBodies is None:
                systemBodies = []
                systemBodiesMap[body.systemId()] = systemBodies
            systemBodies.append(body)

        systems = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._SystemsTableName):
            systemId = row['id']

            try:
                systems.append(multiverse.DbSystem(
                    id=systemId,
                    hexX=row['hex_x'],
                    hexY=row['hex_y'],
                    name=row['name'],
                    planetoidBeltCount=row['planetoid_belt_count'],
                    gasGiantCount=row['gas_giant_count'],
                    worldCount=row['world_count'],
                    zone=row['zone'],
                    allegianceId=row['allegiance_id'],
                    notes=row['notes'],
                    stars=systemStarsMap.get(systemId),
                    bodies=systemBodiesMap.get(systemId)))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load system {systemId!r} from {self._universePath!r}',
                    exc_info=ex)

        return systems

    def _deleteSystems(
            self,
            cursor: sqlite3.Cursor,
            systemIds: str
            ) -> None:
        parameters = []
        for systemId in systemIds:
            logging.debug(f'UniverseDb deleting system {systemId!r} from universe {self._universePath!r}')
            parameters.append((systemId,))

        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._SystemsTableName,
            where='id = ?',
            parameters=parameters)

    def _insertStars(
            self,
            cursor: sqlite3.Cursor,
            stars: typing.Collection[multiverse.DbStar]
            ) -> None:
        if not stars:
            return

        rows = []
        for star in stars:
            rows.append({
                'id': star.id(),
                'system_id': star.systemId(),
                'luminosity_class': star.luminosityClass(),
                'spectral_class': star.spectralClass(),
                'spectral_scale': star.spectralScale()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._StarsTableName,
            rows=rows)

    def _loadStars(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbStar]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._StarsTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        stars = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._StarsTableName):
            starId = row['id']

            try:
                stars.append(multiverse.DbStar(
                    id=starId,
                    systemId=row['system_id'],
                    luminosityClass=row['luminosity_class'],
                    spectralClass=row['spectral_class'],
                    spectralScale=row['spectral_scale']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load star {starId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return stars

    def _insertBodies(
            self,
            cursor: sqlite3.Cursor,
            bodies: typing.Collection[multiverse.DbBody]
            ) -> None:
        if not bodies:
            return

        rows = []
        for body in bodies:
            rows.append({
                'id': body.id(),
                'system_id': body.systemId(),
                'orbit_index': body.orbitIndex(),
                'name': body.name(),
                'notes': body.notes()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._BodiesTableName,
            rows=rows)

        rows = []
        for body in bodies:
            if not isinstance(body, multiverse.DbWorld):
                continue

            rows.append({
                'body_id': body.id(),
                'is_main_world': int(body.isMainWorld()),
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
        if rows:
            self._database.insertMany(
                cursor=cursor,
                tableName=UniverseDb._WorldsTableName,
                rows=rows)

        nobilities = []
        bases = []
        tradeCodes = []
        populations = []
        rulers = []
        owners = []
        colonies = []
        stations = []
        remarks = []
        for body in bodies:
            if not isinstance(body, multiverse.DbWorld):
                continue

            if body.nobilities():
                nobilities.extend(body.nobilities())
            if body.bases():
                bases.extend(body.bases())
            if body.tradeCodes():
                tradeCodes.extend(body.tradeCodes())
            if body.sophontPopulations():
                populations.extend(body.sophontPopulations())
            if body.rulingAllegiances():
                rulers.extend(body.rulingAllegiances())
            if body.owningSystems():
                owners.extend(body.owningSystems())
            if body.colonySystems():
                colonies.extend(body.colonySystems())
            if body.researchStations():
                stations.extend(body.researchStations())
            if body.customRemarks():
                remarks.extend(body.customRemarks())

        if nobilities:
            self._insertNobilities(cursor=cursor, nobilities=nobilities)
        if bases:
            self._insertBases(cursor=cursor, bases=bases)
        if tradeCodes:
            self._insertTradeCodes(cursor=cursor, codes=tradeCodes)
        if populations:
            self._insertSophontPopulations(cursor=cursor, populations=populations)
        if rulers:
            self._insertRulingAllegiances(cursor=cursor, rulers=rulers)
        if owners:
            self._insertOwningSystems(cursor=cursor, owners=owners)
        if colonies:
            self._insertColonySystems(cursor=cursor, colonies=colonies)
        if stations:
            self._insertResearchStations(cursor=cursor, stations=stations)
        if remarks:
            self._insertCustomRemarks(cursor=cursor, remarks=remarks)

    def _loadBodies(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbBody]:
        taskCount = 11
        taskWeight = 1 / taskCount

        nobilitiesProgress = None
        if progress:
            nobilitiesProgress = progress.createChild(weight=taskWeight)
        worldNobilitiesMap = {}
        for nobility in self._loadNobilities(cursor=cursor, progress=nobilitiesProgress):
            nobilities = worldNobilitiesMap.get(nobility.worldId())
            if nobilities is None:
                nobilities = []
                worldNobilitiesMap[nobility.worldId()] = nobilities
            nobilities.append(nobility)

        basesProgress = None
        if progress:
            basesProgress = progress.createChild(weight=taskWeight)
        basesMap = {}
        for base in self._loadBases(cursor=cursor, progress=basesProgress):
            bases = basesMap.get(base.worldId())
            if bases is None:
                bases = []
                basesMap[base.worldId()] = bases
            bases.append(base)

        tradeCodesProgress = None
        if progress:
            tradeCodesProgress = progress.createChild(weight=taskWeight)
        tradeCodesMap = {}
        for tradeCode in self._loadTradeCodes(cursor=cursor, progress=tradeCodesProgress):
            tradeCodes = tradeCodesMap.get(tradeCode.worldId())
            if tradeCodes is None:
                tradeCodes = []
                tradeCodesMap[tradeCode.worldId()] = tradeCodes
            tradeCodes.append(tradeCode)

        populationsProgress = None
        if progress:
            populationsProgress = progress.createChild(weight=taskWeight)
        populationsMap = {}
        for population in self._loadSophontPopulations(cursor=cursor, progress=populationsProgress):
            populations = populationsMap.get(population.worldId())
            if populations is None:
                populations = []
                populationsMap[population.worldId()] = populations
            populations.append(population)

        rulersProgress = None
        if progress:
            rulersProgress = progress.createChild(weight=taskWeight)
        rulersMap = {}
        for ruler in self._loadRulingAllegiances(cursor=cursor, progress=rulersProgress):
            rulers = rulersMap.get(ruler.worldId())
            if rulers is None:
                rulers = []
                rulersMap[ruler.worldId()] = rulers
            rulers.append(ruler)

        ownersProgress = None
        if progress:
            ownersProgress = progress.createChild(weight=taskWeight)
        ownersMap = {}
        for owner in self._loadOwningSystems(cursor=cursor, progress=ownersProgress):
            owners = ownersMap.get(owner.worldId())
            if owners is None:
                owners = []
                ownersMap[owner.worldId()] = owners
            owners.append(owner)

        coloniesProgress = None
        if progress:
            coloniesProgress = progress.createChild(weight=taskWeight)
        coloniesMap = {}
        for colony in self._loadColonySystems(cursor=cursor, progress=coloniesProgress):
            colonies = coloniesMap.get(colony.worldId())
            if colonies is None:
                colonies = []
                coloniesMap[colony.worldId()] = colonies
            colonies.append(colony)

        stationsProgress = None
        if progress:
            stationsProgress = progress.createChild(weight=taskWeight)
        stationsMap = {}
        for station in self._loadResearchStations(cursor=cursor, progress=stationsProgress):
            stations = stationsMap.get(station.worldId())
            if stations is None:
                stations = []
                stationsMap[station.worldId()] = stations
            stations.append(station)

        remarksProgress = None
        if progress:
            remarksProgress = progress.createChild(weight=taskWeight)
        remarksMap = {}
        for remark in self._loadCustomRemarks(cursor=cursor, progress=remarksProgress):
            remarks = remarksMap.get(remark.worldId())
            if remarks is None:
                remarks = []
                remarksMap[remark.worldId()] = remarks
            remarks.append(remark)

        bodyCount = self._database.rowCount(cursor=cursor, tableName=UniverseDb._BodiesTableName)
        bodiesProgress = None
        if progress:
            bodiesProgress = progress.createChild(weight=taskWeight, steps=bodyCount)
        bodyIdToRow = {}
        for worldRow in self._database.select(cursor=cursor, tableName=UniverseDb._BodiesTableName):
            bodyIdToRow[worldRow['id']] = worldRow

        # TODO: Should chunk the inserts and do more granular advancing
        if bodiesProgress:
            bodiesProgress.advance(increment=bodyCount)

        worldCount = self._database.rowCount(cursor=cursor, tableName=UniverseDb._WorldsTableName)
        worldsProgress = None
        if progress:
            worldsProgress = progress.createChild(weight=taskWeight, steps=worldCount)
        bodies = []
        for worldRow in self._database.select(cursor=cursor, tableName=UniverseDb._WorldsTableName):
            bodyId = worldRow['body_id']
            bodyRow = bodyIdToRow[bodyId]

            try:
                bodies.append(multiverse.DbWorld(
                    id=bodyId,
                    systemId=bodyRow['system_id'],
                    orbitIndex=bodyRow['orbit_index'],
                    name=bodyRow['name'],
                    isMainWorld=bool(worldRow['is_main_world']),
                    starport=worldRow['starport'],
                    worldSize=worldRow['world_size'],
                    atmosphere=worldRow['atmosphere'],
                    hydrographics=worldRow['hydrographics'],
                    population=worldRow['population'],
                    government=worldRow['government'],
                    lawLevel=worldRow['law_level'],
                    techLevel=worldRow['tech_level'],
                    resources=worldRow['resources'],
                    labour=worldRow['labour'],
                    infrastructure=worldRow['infrastructure'],
                    efficiency=worldRow['efficiency'],
                    heterogeneity=worldRow['heterogeneity'],
                    acceptance=worldRow['acceptance'],
                    strangeness=worldRow['strangeness'],
                    symbols=worldRow['symbols'],
                    populationMultiplier=worldRow['population_multiplier'],
                    notes=bodyRow['notes'],
                    nobilities=worldNobilitiesMap.get(bodyId),
                    bases=basesMap.get(bodyId),
                    tradeCodes=tradeCodesMap.get(bodyId),
                    sophontPopulations=populationsMap.get(bodyId),
                    rulingAllegiances=rulersMap.get(bodyId),
                    owningSystems=ownersMap.get(bodyId),
                    colonySystems=coloniesMap.get(bodyId),
                    researchStations=stationsMap.get(bodyId),
                    customRemarks=remarksMap.get(bodyId)))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load body {bodyId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if worldsProgress:
            worldsProgress.advance(increment=worldCount)

        return bodies

    def _insertNobilities(
            self,
            cursor: sqlite3.Cursor,
            nobilities: typing.Collection[multiverse.DbNobility]
            ) -> None:
        if not nobilities:
            return

        rows = []
        for nobility in nobilities:
            rows.append({
                'id': nobility.id(),
                'world_id': nobility.worldId(),
                'code': nobility.code()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._NobilitiesTableName,
            rows=rows)

    def _loadNobilities(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbNobility]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._NobilitiesTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        nobilities = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._NobilitiesTableName):
            nobilityId = row['id']

            try:
                nobilities.append(multiverse.DbNobility(
                    id=nobilityId,
                    worldId=row['world_id'],
                    code=row['code']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load nobility {nobilityId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return nobilities

    def _insertBases(
            self,
            cursor: sqlite3.Cursor,
            bases: typing.Collection[multiverse.DbBase]
            ) -> None:
        if not bases:
            return

        rows = []
        for base in bases:
            rows.append({
                'id': base.id(),
                'world_id': base.worldId(),
                'code': base.code()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._BasesTableName,
            rows=rows)

    def _loadBases(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbBase]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._BasesTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        bases = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._BasesTableName):
            baseId = row['id']

            try:
                bases.append(multiverse.DbBase(
                    id=baseId,
                    worldId=row['world_id'],
                    code=row['code']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load base {baseId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return bases

    def _insertTradeCodes(
            self,
            cursor: sqlite3.Cursor,
            codes: typing.Collection[multiverse.DbTradeCode]
            ) -> None:
        if not codes:
            return

        rows = []
        for code in codes:
            rows.append({
                'id': code.id(),
                'world_id': code.worldId(),
                'code': code.code()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._TradeCodesTableName,
            rows=rows)

    def _loadTradeCodes(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbTradeCode]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._TradeCodesTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        tradeCodes = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._TradeCodesTableName):
            tradeCodeId = row['id']

            try:
                tradeCodes.append(multiverse.DbTradeCode(
                    id=tradeCodeId,
                    worldId=row['world_id'],
                    code=row['code']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load trade code {tradeCodeId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return tradeCodes

    def _insertSophontPopulations(
            self,
            cursor: sqlite3.Cursor,
            populations: typing.Collection[multiverse.DbSophontPopulation]
            ) -> None:
        if not populations:
            return

        rows = []
        for sophont in populations:
            rows.append({
                'id': sophont.id(),
                'world_id': sophont.worldId(),
                'sophont_id': sophont.sophontId(),
                'percentage': sophont.percentage(),
                'is_home_world': int(sophont.isHomeWorld()),
                'is_die_back': int(sophont.isDieBack())})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._SophontPopulationsTableName,
            rows=rows)

    def _loadSophontPopulations(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbSophontPopulation]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._SophontPopulationsTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        populations = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._SophontPopulationsTableName):
            populationId = row['id']

            try:
                populations.append(multiverse.DbSophontPopulation(
                    id=populationId,
                    worldId=row['world_id'],
                    sophontId=row['sophont_id'],
                    percentage=row['percentage'],
                    isHomeWorld=bool(row['is_home_world']),
                    isDieBack=bool(row['is_die_back'])))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load sophont population {populationId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return populations

    def _insertRulingAllegiances(
            self,
            cursor: sqlite3.Cursor,
            rulers: typing.Collection[multiverse.DbRulingAllegiance]
            ) -> None:
        if not rulers:
            return

        rows = []
        for rulingAllegiance in rulers:
            rows.append({
                'id': rulingAllegiance.id(),
                'world_id': rulingAllegiance.worldId(),
                'allegiance_id': rulingAllegiance.allegianceId()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._RulingAllegiancesTableName,
            rows=rows)

    def _loadRulingAllegiances(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbRulingAllegiance]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._SophontPopulationsTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        rulers = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._RulingAllegiancesTableName):
            rulerId = row['id']

            try:
                rulers.append(multiverse.DbRulingAllegiance(
                    id=rulerId,
                    worldId=row['world_id'],
                    allegianceId=row['allegiance_id']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load ruling allegiance {rulerId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return rulers

    def _insertOwningSystems(
            self,
            cursor: sqlite3.Cursor,
            owners: typing.Collection[multiverse.DbOwningSystem]
            ) -> None:
        if not owners:
            return

        rows = []
        for owner in owners:
            rows.append({
                'id': owner.id(),
                'world_id': owner.worldId(),
                'hex_x': owner.hexX(),
                'hex_y': owner.hexY(),
                'sector_abbreviation': owner.sectorAbbreviation()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._OwningSystemsTableName,
            rows=rows)

    def _loadOwningSystems(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbOwningSystem]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._OwningSystemsTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        owners = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._OwningSystemsTableName):
            ownerId = row['id']

            try:
                owners.append(multiverse.DbOwningSystem(
                    id=ownerId,
                    worldId=row['world_id'],
                    hexX=row['hex_x'],
                    hexY=row['hex_y'],
                    sectorAbbreviation=row['sector_abbreviation']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load owning system {ownerId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return owners

    def _insertColonySystems(
            self,
            cursor: sqlite3.Cursor,
            colonies: typing.Collection[multiverse.DbColonySystem]
            ) -> None:
        if not colonies:
            return

        rows = []
        for colony in colonies:
            rows.append({
                'id': colony.id(),
                'world_id': colony.worldId(),
                'hex_x': colony.hexX(),
                'hex_y': colony.hexY(),
                'sector_abbreviation': colony.sectorAbbreviation()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._ColonySystemsTableName,
            rows=rows)

    def _loadColonySystems(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbColonySystem]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._ColonySystemsTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        colonies = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._ColonySystemsTableName):
            colonyId = row['id']

            try:
                colonies.append(multiverse.DbColonySystem(
                    id=colonyId,
                    worldId=row['world_id'],
                    hexX=row['hex_x'],
                    hexY=row['hex_y'],
                    sectorAbbreviation=row['sector_abbreviation']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load colony system {colonyId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return colonies

    def _insertResearchStations(
            self,
            cursor: sqlite3.Cursor,
            stations: typing.Collection[multiverse.DbResearchStation]
            ) -> None:
        if not stations:
            return

        rows = []
        for station in stations:
            rows.append({
                'id': station.id(),
                'world_id': station.worldId(),
                'code': station.code()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._ResearchStationTableName,
            rows=rows)

    def _loadResearchStations(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbResearchStation]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._ResearchStationTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        stations = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._ResearchStationTableName):
            stationId = row['id']

            try:
                stations.append(multiverse.DbResearchStation(
                    id=stationId,
                    worldId=row['world_id'],
                    code=row['code']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load research station {stationId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return stations

    def _insertCustomRemarks(
            self,
            cursor: sqlite3.Cursor,
            remarks: typing.Collection[multiverse.DbCustomRemark]
            ) -> None:
        if not remarks:
            return

        rows = []
        for remark in remarks:
            rows.append({
                'id': remark.id(),
                'world_id': remark.worldId(),
                'remark': remark.remark()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._CustomRemarksTableName,
            rows=rows)

    def _loadCustomRemarks(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbCustomRemark]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._CustomRemarksTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        remarks = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._CustomRemarksTableName):
            remarkId = row['id']

            try:
                remarks.append(multiverse.DbCustomRemark(
                    id=remarkId,
                    worldId=row['world_id'],
                    remark=row['remark']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load custom remark {remarkId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return remarks


    #    ███████████                        █████
    #   ░░███░░░░░███                      ░░███
    #    ░███    ░███   ██████  █████ ████ ███████    ██████   █████
    #    ░██████████   ███░░███░░███ ░███ ░░░███░    ███░░███ ███░░
    #    ░███░░░░░███ ░███ ░███ ░███ ░███   ░███    ░███████ ░░█████
    #    ░███    ░███ ░███ ░███ ░███ ░███   ░███ ███░███░░░   ░░░░███
    #    █████   █████░░██████  ░░████████  ░░█████ ░░██████  ██████
    #   ░░░░░   ░░░░░  ░░░░░░    ░░░░░░░░    ░░░░░   ░░░░░░  ░░░░░░

    def _insertRoutes(
            self,
            cursor: sqlite3.Cursor,
            routes: typing.Collection[multiverse.DbRoute]
            ) -> None:
        if not routes:
            return

        rows = []
        for route in routes:
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
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._RoutesTableName,
            rows=rows)

    def _loadRoutes(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbRoute]:
        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._RoutesTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        routes = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._RoutesTableName):
            routeId = row['id']

            try:
                routes.append(multiverse.DbRoute(
                    id=routeId,
                    sectorId=row['sector_id'],
                    startHexX=row['start_hex_x'],
                    startHexY=row['start_hex_y'],
                    endHexX=row['end_hex_x'],
                    endHexY=row['end_hex_y'],
                    startOffsetX=row['start_offset_x'],
                    startOffsetY=row['start_offset_y'],
                    endOffsetX=row['end_offset_x'],
                    endOffsetY=row['end_offset_y'],
                    type=row['type'],
                    style=row['style'],
                    colour=row['colour'],
                    width=row['width'],
                    allegianceId=row['allegiance_id']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load route {routeId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return routes

    #    ███████████                         █████
    #   ░░███░░░░░███                       ░░███
    #    ░███    ░███  ██████  ████████   ███████   ██████  ████████   █████
    #    ░██████████  ███░░███░░███░░███ ███░░███  ███░░███░░███░░███ ███░░
    #    ░███░░░░░███░███ ░███ ░███ ░░░ ░███ ░███ ░███████  ░███ ░░░ ░░█████
    #    ░███    ░███░███ ░███ ░███     ░███ ░███ ░███░░░   ░███      ░░░░███
    #    ███████████ ░░██████  █████    ░░████████░░██████  █████     ██████
    #   ░░░░░░░░░░░   ░░░░░░  ░░░░░      ░░░░░░░░  ░░░░░░  ░░░░░     ░░░░░░

    def _insertBorders(
            self,
            cursor: sqlite3.Cursor,
            borders: typing.Collection[multiverse.DbBorder]
            ) -> None:
        if not borders:
            return

        borderRows = []
        hexRows = []
        for border in borders:
            borderRows.append({
                'id': border.id(),
                'sector_id': border.sectorId(),
                'allegiance_id': border.allegianceId(),
                'style': border.style(),
                'colour': border.colour(),
                'label': border.label(),
                'label_x': border.labelWorldX(),
                'label_y': border.labelWorldY(),
                'show_label': int(border.showLabel()),
                'wrap_label': int(border.wrapLabel())})
            for hexX, hexY in border.hexes():
                hexRows.append({
                    'border_id': border.id(),
                    'hex_x': hexX,
                    'hex_y': hexY})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._BordersTableName,
            rows=borderRows)
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._BorderHexesTableName,
            rows=hexRows)

    def _loadBorders(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbBorder]:
        taskCount = 2
        taskWeight = 1 / taskCount

        hexCount = self._database.rowCount(cursor=cursor, tableName=UniverseDb._BorderHexesTableName)
        hexProgress = None
        if progress:
            hexProgress = progress.createChild(weight=taskWeight, steps=hexCount)
        borderHexMap = {}
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._BorderHexesTableName):
            borderId = row['border_id']
            hexes = borderHexMap.get(borderId)
            if hexes is None:
                hexes = []
                borderHexMap[borderId] = hexes
            hexes.append((row['hex_x'], row['hex_y']))

        # TODO: Should chunk the inserts and do more granular advancing
        if hexProgress:
            hexProgress.advance(increment=hexCount)

        borderCount = self._database.rowCount(cursor=cursor, tableName=UniverseDb._BordersTableName)
        bordersProgress = None
        if progress:
            bordersProgress = progress.createChild(weight=taskWeight, steps=borderCount)
        borders = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._BordersTableName):
            borderId = row['id']

            try:
                borders.append(multiverse.DbBorder(
                    id=borderId,
                    sectorId=row['sector_id'],
                    allegianceId=row['allegiance_id'],
                    style=row['style'],
                    colour=row['colour'],
                    label=row['label'],
                    labelWorldX=row['label_x'],
                    labelWorldY=row['label_y'],
                    showLabel=bool(row['show_label']),
                    wrapLabel=bool(row['wrap_label']),
                    hexes=borderHexMap.get(borderId)))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load border {borderId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if bordersProgress:
            bordersProgress.advance(increment=borderCount)

        return borders

    #    ███████████                      ███
    #   ░░███░░░░░███                    ░░░
    #    ░███    ░███   ██████   ███████ ████   ██████  ████████    █████
    #    ░██████████   ███░░███ ███░░███░░███  ███░░███░░███░░███  ███░░
    #    ░███░░░░░███ ░███████ ░███ ░███ ░███ ░███ ░███ ░███ ░███ ░░█████
    #    ░███    ░███ ░███░░░  ░███ ░███ ░███ ░███ ░███ ░███ ░███  ░░░░███
    #    █████   █████░░██████ ░░███████ █████░░██████  ████ █████ ██████
    #   ░░░░░   ░░░░░  ░░░░░░   ░░░░░███░░░░░  ░░░░░░  ░░░░ ░░░░░ ░░░░░░
    #                           ███ ░███
    #                          ░░██████
    #                           ░░░░░░

    def _insertRegions(
            self,
            cursor: sqlite3.Cursor,
            regions: typing.Collection[multiverse.DbRegion]
            ) -> None:
        if not regions:
            return

        regionsRows = []
        hexRows = []
        for region in regions:
            regionsRows.append({
                'id': region.id(),
                'sector_id': region.sectorId(),
                'colour': region.colour(),
                'label': region.label(),
                'label_x': region.labelWorldX(),
                'label_y': region.labelWorldY(),
                'show_label': int(region.showLabel()),
                'wrap_label': int(region.wrapLabel())})
            for hexX, hexY in region.hexes():
                hexRows.append({
                    'region_id': region.id(),
                    'hex_x': hexX,
                    'hex_y': hexY})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._RegionsTableName,
            rows=regionsRows)
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._RegionHexesTableName,
            rows=hexRows)

    def _loadRegions(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbRegion]:
        taskCount = 2
        taskWeight = 1 / taskCount

        hexCount = self._database.rowCount(cursor=cursor, tableName=UniverseDb._RegionHexesTableName)
        hexProgress = None
        if progress:
            hexProgress = progress.createChild(weight=taskWeight, steps=hexCount)
        regionHexMap = {}
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._RegionHexesTableName):
            regionId = row['region_id']
            hexes = regionHexMap.get(regionId)
            if hexes is None:
                hexes = []
                regionHexMap[regionId] = hexes
            hexes.append((row['hex_x'], row['hex_y']))

        # TODO: Should chunk the inserts and do more granular advancing
        if hexProgress:
            hexProgress.advance(increment=hexCount)

        regionsCount = self._database.rowCount(cursor=cursor, tableName=UniverseDb._RegionsTableName)
        regionsProgress = None
        if progress:
            regionsProgress = progress.createChild(weight=taskWeight, steps=regionsCount)
        regions = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._RegionsTableName):
            regionId = row['id']

            try:
                regions.append(multiverse.DbRegion(
                    id=regionId,
                    sectorId=row['sector_id'],
                    colour=row['colour'],
                    label=row['label'],
                    labelWorldX=row['label_x'],
                    labelWorldY=row['label_y'],
                    showLabel=bool(row['show_label']),
                    wrapLabel=bool(row['wrap_label']),
                    hexes=regionHexMap.get(regionId)))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load region {regionId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if regionsProgress:
            regionsProgress.advance(increment=regionsCount)

        return regions

    #    ██████   ██████                        █████                 █████              ████
    #   ░░██████ ██████                        ░░███                 ░░███              ░░███
    #    ░███░█████░███   ██████   ████████     ░███         ██████   ░███████   ██████  ░███   █████
    #    ░███░░███ ░███  ░░░░░███ ░░███░░███    ░███        ░░░░░███  ░███░░███ ███░░███ ░███  ███░░
    #    ░███ ░░░  ░███   ███████  ░███ ░███    ░███         ███████  ░███ ░███░███████  ░███ ░░█████
    #    ░███      ░███  ███░░███  ░███ ░███    ░███      █ ███░░███  ░███ ░███░███░░░   ░███  ░░░░███
    #    █████     █████░░████████ ░███████     ███████████░░████████ ████████ ░░██████  █████ ██████
    #   ░░░░░     ░░░░░  ░░░░░░░░  ░███░░░     ░░░░░░░░░░░  ░░░░░░░░ ░░░░░░░░   ░░░░░░  ░░░░░ ░░░░░░
    #                              ░███
    #                              █████
    #                             ░░░░░

    def _saveMapLabels(
            self,
            cursor: sqlite3.Cursor,
            labels: typing.Collection[multiverse.DbMapLabel]
            ) -> None:
        if not labels:
            return

        rows = []
        for label in labels:
            logging.debug(f'UniverseDb saving map label {label.id()!r} to universe {self._universePath!r}')
            rows.append({
                'id': label.id(),
                'text': label.text(),
                'x': label.worldX(),
                'y': label.worldY(),
                'layer': label.layer(),
                'alignment': label.alignment(),
                'colour': label.colour(),
                'size': label.size(),
                'rotation': label.rotation()})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._MapLabelsTableName,
            rows=rows,
            replaceIfExists=True)

    def _loadMapLabels(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbMapLabel]:
        logging.debug(f'UniverseDb loading map labels from universe {self._universePath!r}')

        count = self._database.rowCount(cursor=cursor, tableName=UniverseDb._MapLabelsTableName)
        taskProgress = None
        if progress:
            taskProgress = progress.createChild(weight=1.0, steps=count)

        labels: typing.List[multiverse.DbMapLabel] = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._MapLabelsTableName):
            labelId = row['id']

            try:
                labels.append(multiverse.DbMapLabel(
                    id=labelId,
                    text=row['text'],
                    worldX=row['x'],
                    worldY=row['y'],
                    layer=row['layer'],
                    alignment=row['alignment'],
                    colour=row['colour'],
                    size=row['size'],
                    rotation=row['rotation']))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load map label {labelId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if taskProgress:
            taskProgress.advance(increment=count)

        return labels

    def _deleteMapLabels(
            self,
            cursor: sqlite3.Cursor,
            labelIds: str
            ) -> None:
        parameters = []
        for labelId in labelIds:
            logging.debug(f'UniverseDb deleting map label {labelId!r} from universe {self._universePath!r}')
            parameters.append((labelId,))

        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._MapLabelsTableName,
            where='id = ?',
            parameters=parameters)

    #    ██████   ██████                        █████   █████                    █████
    #   ░░██████ ██████                        ░░███   ░░███                    ░░███
    #    ░███░█████░███   ██████   ████████     ░███    ░███   ██████   ██████  ███████    ██████  ████████   █████
    #    ░███░░███ ░███  ░░░░░███ ░░███░░███    ░███    ░███  ███░░███ ███░░███░░░███░    ███░░███░░███░░███ ███░░
    #    ░███ ░░░  ░███   ███████  ░███ ░███    ░░███   ███  ░███████ ░███ ░░░   ░███    ░███ ░███ ░███ ░░░ ░░█████
    #    ░███      ░███  ███░░███  ░███ ░███     ░░░█████░   ░███░░░  ░███  ███  ░███ ███░███ ░███ ░███      ░░░░███
    #    █████     █████░░████████ ░███████        ░░███     ░░██████ ░░██████   ░░█████ ░░██████  █████     ██████
    #   ░░░░░     ░░░░░  ░░░░░░░░  ░███░░░          ░░░       ░░░░░░   ░░░░░░     ░░░░░   ░░░░░░  ░░░░░     ░░░░░░
    #                              ░███
    #                              █████
    #                             ░░░░░

    def _saveMapVectors(
            self,
            cursor: sqlite3.Cursor,
            vectors: typing.Collection[multiverse.DbMapVector]
            ) -> None:
        if not vectors:
            return

        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._MapVectorPointsTableName,
            where='vector_id = ?',
            parameters=((v.id(),) for v in vectors))

        rows = []
        for vector in vectors:
            logging.debug(f'UniverseDb saving map vector {vector.id()!r} to universe {self._universePath!r}')
            rows.append({
                'id': vector.id(),
                'layer': vector.layer(),
                'closed': int(vector.closed())})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._MapVectorsTableName,
            rows=rows)

        rows = []
        for vector in vectors:
            for x, y in vector.points():
                rows.append({
                    'vector_id': vector.id(),
                    'x': x,
                    'y': y})
        self._database.insertMany(
            cursor=cursor,
            tableName=UniverseDb._MapVectorPointsTableName,
            rows=rows)

    def _loadMapVectors(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbMapVector]:
        logging.debug(f'UniverseDb loading map vectors from universe {self._universePath!r}')

        taskCount = 2
        taskWeight = 1 / taskCount

        pointCount = self._database.rowCount(cursor=cursor, tableName=UniverseDb._MapVectorPointsTableName)
        pointsProgress = None
        if progress:
            pointsProgress = progress.createChild(weight=taskWeight, steps=pointCount)
        vectorPointsMap: typing.Dict[str, typing.List[typing.Tuple[float, float]]] = {}
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._MapVectorPointsTableName):
            vectorId = row['vector_id']
            points = vectorPointsMap.get(vectorId)
            if points is None:
                points = []
                vectorPointsMap[vectorId] = points
            points.append((row['x'], row['y']))

        # TODO: Should chunk the inserts and do more granular advancing
        if pointsProgress:
            pointsProgress.advance(increment=pointCount)

        vectorCount = self._database.rowCount(cursor=cursor, tableName=UniverseDb._MapVectorsTableName)
        vectorsProgress = None
        if progress:
            vectorsProgress = progress.createChild(weight=taskWeight, steps=vectorCount)
        vectors: typing.List[multiverse.DbMapVector] = []
        for row in self._database.select(cursor=cursor, tableName=UniverseDb._MapVectorsTableName):
            vectorId = row['id']

            try:
                vectors.append(multiverse.DbMapVector(
                    id=vectorId,
                    points=vectorPointsMap.get(vectorId),
                    layer=row['layer'],
                    closed=bool(row['closed'])))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load map vector {vectorId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        # TODO: Should chunk the inserts and do more granular advancing
        if vectorsProgress:
            vectorsProgress.advance(increment=vectorCount)

        return vectors

    def _deleteMapLabels(
            self,
            cursor: sqlite3.Cursor,
            vectorIds: str
            ) -> None:
        parameters = []
        for vectorId in vectorIds:
            logging.debug(f'UniverseDb deleting map vector {vectorId!r} from universe {self._universePath!r}')
            parameters.append((vectorId,))

        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._MapVectorsTableName,
            where='id = ?',
            parameters=parameters)

    @staticmethod
    def _parseTimestampString(content: typing.Optional[str]) -> typing.Optional[datetime.datetime]:
        if content is None:
            return None

        return datetime.datetime.fromisoformat(content)

    @staticmethod
    def _formatTimestampString(timestamp: typing.Optional[datetime.datetime]) -> typing.Optional[str]:
        if timestamp is None:
            return None

        if timestamp.tzinfo is None:
            # Assume timestamps without a timezone are in UTC
            timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
        return timestamp.astimezone(datetime.timezone.utc).isoformat()