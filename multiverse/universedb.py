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

        self._database = database.SchemaDb(dbPath=universePath)
        self._initTables()

    @staticmethod
    def isUniverseDb(universePath: str) -> bool:
        connection = None
        try:
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
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.List[multiverse.DbAllegiance]:
        logging.debug(f'UniverseDb loading allegiances from universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            return self._loadAllegiances(
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._loadAllegiances(
                    cursor=connection.cursor())

    def saveAllegiance(
            self,
            allegiance: multiverse.DbAllegiance,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseDb saving allegiance {allegiance.id()!r} to universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            return self._saveAllegiance(
                allegiance=allegiance,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._saveAllegiance(
                    allegiance=allegiance,
                    cursor=connection.cursor())

    def loadSophonts(
            self,
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.List[multiverse.DbSophont]:
        logging.debug(f'UniverseDb loading sophonts from universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            return self._loadSophonts(
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._loadSophonts(
                    cursor=connection.cursor())

    def saveSophont(
            self,
            sophont: multiverse.DbSophont,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseDb saving sophont {sophont.id()!r} to universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            return self._saveSophont(
                sophont=sophont,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._saveSophont(
                    sophont=sophont,
                    cursor=connection.cursor())


    def listSectors(
            self,
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.List[SectorInfo]:
        logging.debug(f'UniverseDb listing sectors in universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            return self._listSectors(cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._listSectors(cursor=connection.cursor())

    def saveSector(
            self,
            sector: multiverse.DbSector,
            stockDataHash: typing.Optional[str] = None,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseDb saving sector {sector.id()!r} to universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            cursor = connection.cursor()
            self._saveSector(cursor=cursor, sector=sector, stockDataHash=stockDataHash)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                cursor = connection.cursor()
                self._saveSector(cursor=cursor, sector=sector, stockDataHash=stockDataHash)

    def loadSectors(
            self,
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.List[multiverse.DbSector]:
        logging.debug(f'UniverseDb loading sector from universe {self._universePath!r}')

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
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseDb deleting sector {sectorId!r} from universe {self._universePath!r}')

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

    def loadSystems(
            self,
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.List[multiverse.DbSystem]:
        logging.debug(f'UniverseDb loading systems from universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            return self._loadSystems(
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._loadSystems(
                    cursor=connection.cursor())

    def saveSystems(
            self,
            systems: typing.Collection[multiverse.DbSystem],
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseDb saving systems to universe {self._universePath!r}')

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

    def deleteSystem(
            self,
            systemId: str,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseDb deleting system {systemId!r} to universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            self._deleteSystem(
                systemId=systemId,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._deleteSystem(
                    systemId=systemId,
                    cursor=connection.cursor())

    def saveMapLabel(
            self,
            label: multiverse.DbMapLabel,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseDb saving universe label {label.id()!r} to universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            return self._saveMapLabel(
                label=label,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._saveMapLabel(
                    label=label,
                    cursor=connection.cursor())

    def loadMapLabels(
            self,
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.List[multiverse.DbMapLabel]:
        logging.debug(f'UniverseDb loading map labels from universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            return self._loadMapLabels(
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._loadMapLabels(
                    cursor=connection.cursor())

    def saveMapVector(
            self,
            vector: multiverse.DbMapVector,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseDb saving map vector {vector.id()!r} to universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            return self._saveMapVector(
                vector=vector,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._saveMapVector(
                    vector=vector,
                    cursor=connection.cursor())

    def loadMapVectors(
            self,
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.List[multiverse.DbMapLabel]:
        logging.debug(f'UniverseDb loading map vectors from universe {self._universePath!r}')

        if transaction != None:
            connection = transaction.connection()
            return self._loadMapVectors(
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._loadMapVectors(
                    cursor=connection.cursor())

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
                    database.ColumnDef(columnName='selected', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False),
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
                    database.ColumnDef(columnName='closed', columnType=database.ColumnDef.ColumnType.Integer, isNullable=False)])

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
                    database.ColumnDef(columnName='is_major', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False)])

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
                    database.ColumnDef(columnName='is_home_world', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False),
                    database.ColumnDef(columnName='is_die_back', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False)],
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
                    database.ColumnDef(columnName='show_label', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False),
                    database.ColumnDef(columnName='wrap_label', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False)])

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
                    database.ColumnDef(columnName='show_label', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False),
                    database.ColumnDef(columnName='wrap_label', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False)])

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
                    database.ColumnDef(columnName='wrap', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False)])

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
        sql = """
            SELECT value
            FROM {metadataTable}
            WHERE key = :key
            LIMIT 1;
            """.format(metadataTable=UniverseDb._MetadataTableName)
        cursor.execute(sql, {'key': key})
        row = cursor.fetchone()
        if not row:
            return None
        return row[0]

    def _writeMetadata(
            self,
            cursor: sqlite3.Cursor,
            key: str,
            value: str
            ) -> None:
        sql = """
            INSERT INTO {metadataTable} (key, value)
            VALUES (:key, :value)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value;
            """.format(metadataTable=UniverseDb._MetadataTableName)
        cursor.execute(sql, {'key': key, 'value': value})

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

    def _saveAllegiance(
            self,
            cursor: sqlite3.Cursor,
            allegiance: multiverse.DbAllegiance
            ) -> None:
        sql = """
            INSERT INTO {table} (id, name, code, legacy, base,
                route_colour, route_style, route_width,
                border_colour, border_style)
            VALUES (:id, :name, :code, :legacy, :base,
                :route_colour, :route_style, :route_width,
                :border_colour, :border_style)
            ON CONFLICT(id) DO UPDATE SET
                code = excluded.code,
                name = excluded.name,
                legacy = excluded.legacy,
                base = excluded.base,
                route_colour = excluded.route_colour,
                route_style = excluded.route_style,
                route_width = excluded.route_width,
                border_colour = excluded.border_colour,
                border_style = excluded.border_style;
            """.format(table=UniverseDb._AllegiancesTableName)
        cursor.execute(sql, {
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

    def _loadAllegiances(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbAllegiance]:
        sql = """
            SELECT id, name, code, legacy, base,
                route_colour, route_style, route_width,
                border_colour, border_style
            FROM {table};
            """.format(
                table=UniverseDb._AllegiancesTableName)
        cursor.execute(sql)

        allegiances = []
        for row in cursor.fetchall():
            allegianceId = row[0]
            try:
                allegiances.append(multiverse.DbAllegiance(
                    id=allegianceId,
                    name=row[1],
                    code=row[2],
                    legacy=row[3],
                    base=row[4],
                    routeColour=row[5],
                    routeStyle=row[6],
                    routeWidth=row[7],
                    borderColour=row[8],
                    borderStyle=row[9]))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load allegiance {allegianceId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return allegiances

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

    def _saveSophont(
            self,
            cursor: sqlite3.Cursor,
            sophont: multiverse.DbSophont
            ) -> None:
        sql = """
            INSERT INTO {table} (id, name, code, is_major)
            VALUES (:id, :name, :code, :is_major)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                code = excluded.code,
                is_major = excluded.is_major;
            """.format(table=UniverseDb._SophontsTableName)
        cursor.execute(sql, {
            'id': sophont.id(),
            'name': sophont.name(),
            'code': sophont.code(),
            'is_major': 1 if sophont.isMajor() else 0})

    def _loadSophonts(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbSophont]:
        sql = """
            SELECT id, name, code, is_major
            FROM {table};
            """.format(
                table=UniverseDb._SophontsTableName)
        cursor.execute(sql)

        sophonts = []
        for row in cursor.fetchall():
            sophontId = row[0]
            try:
                sophonts.append(multiverse.DbSophont(
                    id=sophontId,
                    name=row[1],
                    code=row[2],
                    isMajor=True if row[3] else False))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load sophont {sophontId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return sophonts

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
        sql = """
            SELECT id, name, sector_x, sector_y, abbreviation
            FROM {sectorsTable};
            """.format(sectorsTable=UniverseDb._SectorsTableName)
        parameters = {}

        cursor.execute(sql, parameters)

        sectorList = []
        for row in cursor.fetchall():
            sectorList.append(SectorInfo(
                id=row[0],
                name=row[1],
                sectorX=row[2],
                sectorY=row[3],
                abbreviation=row[4]))
        return sectorList

    def _saveSector(
            self,
            cursor: sqlite3.Cursor,
            sector: multiverse.DbSector,
            stockDataHash: typing.Optional[str] = None
            ) -> None:
        # Check there isn't a sector at the same position with a different id.
        # To update a sector at a position, the new sector must have the same id.
        # The only reason this is done is to make deleting the old sector data
        # easier as it means we can just delete the current sector with the same
        # id and that handles it even if the sector has changed position.
        # TODO: I should update this to be consistent with how things like saveSystems
        # works where it just overwrites whatever is there
        sql = """
            SELECT id
            FROM {table}
            WHERE id != :id AND sector_x = :x AND sector_y = :y
            LIMIT 1;
            """.format(table=UniverseDb._SectorsTableName)
        cursor.execute(sql, {
            'id': sector.id(),
            'x': sector.sectorX(),
            'y': sector.sectorY()})
        row = cursor.fetchone()
        if row:
            raise ValueError('Sector {otherId} already exists at ({x}, {y})'.format(
                otherId=row[0],
                x=sector.sectorX(),
                y=sector.sectorY()))

        self._deleteSector(
            sectorId=sector.id(),
            cursor=cursor,
            # If a stock source data has exists for the sector, don't
            # delete it as it will be updated below
            updateSources=False)
        self._insertSectors(
            sectors=[sector],
            cursor=cursor)

        if stockDataHash is not None:
            # A stock data hash was provided so this save is happening
            # because the sector is been filled with stock data. Create a
            # mapping between the position the sector was written to and
            # the data hash for the stock data that is being imported.
            sql = """
                INSERT INTO {table} (sector_x, sector_y, data_hash)
                VALUES (:sector_x, :sector_y, :data_hash)
                ON CONFLICT(sector_x, sector_y) DO UPDATE SET
                    data_hash = excluded.data_hash;
                """.format(table=UniverseDb._StockSourcesTableName)
            cursor.execute(sql, {
                'sector_x': sector.sectorX(),
                'sector_y': sector.sectorY(),
                'data_hash': stockDataHash})
        else:
            # No stock data has was provided so the sector is being
            # updated with user data. If there was a stock data has
            # for the position the sector was written to, keep the
            # entry but set the hash to null. When importing updated
            # stock data, this lets us detect cases where stock data
            # was imported but has since been modified by the user so
            # we need to prompt them to ask if they really want their
            # chances replaced with stock data
            sql = """
                UPDATE {table}
                SET data_hash = NULL
                WHERE sector_x = :sector_x AND sector_y = :sector_y;
                """.format(table=UniverseDb._StockSourcesTableName)
            cursor.execute(sql, {
                'sector_x': sector.sectorX(),
                'sector_y': sector.sectorY()})

    def _deleteSector(
            self,
            cursor: sqlite3.Cursor,
            sectorId: str,
            updateSources: bool = True
            ) -> None:
        if updateSources:
            # If there is a stock data hash for the position the sector
            # to be deleted is located, set it to null but don't delete
            # it. When importing updated stock data, this allows us to
            # detect that case where the data was imported but the user
            # has since deleted the sector so we should prompt the user
            # before re-importing the stock data
            sql = """
                UPDATE {sourcesTable}
                SET data_hash = NULL
                WHERE (sector_x, sector_y) = (
                    SELECT sector_x, sector_y
                    FROM {sectorsTable}
                    WHERE id = :id
                );
                """.format(
                    sourcesTable=UniverseDb._StockSourcesTableName,
                    sectorsTable=UniverseDb._SectorsTableName)
            cursor.execute(sql, {'id': sectorId})

        sql = """
            DELETE FROM {table}
            WHERE id = :id;
            """.format(
            table=UniverseDb._SectorsTableName)
        cursor.execute(sql, {'id': sectorId})

    def _insertSectors(
            self,
            cursor: sqlite3.Cursor,
            sectors: typing.Collection[multiverse.DbSector]
            ) -> None:
        sql = """
            INSERT INTO {table} (id, sector_x, sector_y,
                name, language, abbreviation, sector_label, selected,
                credits, publication, author, publisher, reference, notes)
            VALUES (:id, :sector_x, :sector_y,
                :name, :language, :abbreviation, :sector_label, :selected,
                :credits, :publication, :author, :publisher, :reference, :notes);
            """.format(table=UniverseDb._SectorsTableName)
        rows = []
        names = []
        subsectors = []
        routes = []
        borders = []
        regions = []
        labels = []
        tags = []
        products = []
        for sector in sectors:
            rows.append({
                'id': sector.id(),
                'sector_x': sector.sectorX(),
                'sector_y': sector.sectorY(),
                'name': sector.name(),
                'language': sector.language(),
                'abbreviation': sector.abbreviation(),
                'sector_label': sector.sectorLabel(),
                'selected': 1 if sector.selected() else 0,
                'credits': sector.credits(),
                'publication': sector.publication(),
                'author': sector.author(),
                'publisher': sector.publisher(),
                'reference': sector.reference(),
                'notes': sector.notes()})

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
        cursor.executemany(sql, rows)

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
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbSector]:
        sectorAlternateNamesMap = {}
        for name in self._loadAlternateNames(cursor=cursor):
            names = sectorAlternateNamesMap.get(name.sectorId())
            if names is None:
                names = []
                sectorAlternateNamesMap[name.sectorId()] = names
            names.append(name)

        sectorSubsectorNamesMap = {}
        for name in self._loadSubsectorNames(cursor=cursor):
            names = sectorSubsectorNamesMap.get(name.sectorId())
            if names is None:
                names = []
                sectorSubsectorNamesMap[name.sectorId()] = names
            names.append(name)

        sectorRoutesMap = {}
        for route in self._loadRoutes(cursor=cursor):
            routes = sectorRoutesMap.get(route.sectorId())
            if routes is None:
                routes = []
                sectorRoutesMap[route.sectorId()] = routes
            routes.append(route)

        sectorBordersMap = {}
        for border in self._loadBorders(cursor=cursor):
            borders = sectorBordersMap.get(border.sectorId())
            if borders is None:
                borders = []
                sectorBordersMap[border.sectorId()] = borders
            borders.append(border)

        sectorRegionsMap = {}
        for region in self._loadRegions(cursor=cursor):
            regions = sectorRegionsMap.get(region.sectorId())
            if regions is None:
                regions = []
                sectorRegionsMap[region.sectorId()] = regions
            regions.append(region)

        sectorLabelsMap = {}
        for label in self._loadSectorLabels(cursor=cursor):
            labels = sectorLabelsMap.get(label.sectorId())
            if labels is None:
                labels = []
                sectorLabelsMap[label.sectorId()] = labels
            labels.append(label)

        sectorTagsMap = {}
        for tag in self._loadTags(cursor=cursor):
            tags = sectorTagsMap.get(tag.sectorId())
            if tags is None:
                tags = []
                sectorTagsMap[tag.sectorId()] = tags
            tags.append(tag)

        sectorProductsMap = {}
        for product in self._loadProducts(cursor=cursor):
            products = sectorProductsMap.get(product.sectorId())
            if products is None:
                products = []
                sectorProductsMap[product.sectorId()] = products
            products.append(product)

        sql = """
            SELECT id, sector_x, sector_y,
                name, language, abbreviation, sector_label, selected,
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
                    sectorX=row[1],
                    sectorY=row[2],
                    name=row[3],
                    language=row[4],
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
                    routes=sectorRoutesMap.get(sectorId),
                    borders=sectorBordersMap.get(sectorId),
                    regions=sectorRegionsMap.get(sectorId),
                    labels=sectorLabelsMap.get(sectorId),
                    tags=sectorTagsMap.get(sectorId),
                    products=sectorProductsMap.get(sectorId)))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load sector {sectorId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return sectors

    def _insertAlternateNames(
            self,
            cursor: sqlite3.Cursor,
            names: typing.Collection[multiverse.DbAlternateName]
            ) -> None:
        if not names:
            return

        sql = """
            INSERT INTO {table} (id, sector_id, name, language)
            VALUES (:id, :sector_id, :name, :language);
            """.format(table=UniverseDb._AlternateNamesTableName)
        rows = []
        for alternateName in names:
            rows.append({
                'id': alternateName.id(),
                'sector_id': alternateName.sectorId(),
                'name': alternateName.name(),
                'language': alternateName.language()})
        cursor.executemany(sql, rows)

    def _loadAlternateNames(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbAlternateName]:
        sql = """
            SELECT id, sector_id, name, language
            FROM {table};
            """.format(table=UniverseDb._AlternateNamesTableName)
        cursor.execute(sql)

        names = []
        for row in cursor.fetchall():
            nameId = row[0]
            sectorId = row[1]

            try:
                names.append(multiverse.DbAlternateName(
                    id=nameId,
                    sectorId=sectorId,
                    name=row[2],
                    language=row[3]))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load alternate name {nameId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return names

    def _insertSubsectorNames(
            self,
            cursor: sqlite3.Cursor,
            names: typing.Collection[multiverse.DbSubsectorName]
            ) -> None:
        if not names:
            return

        sql = """
            INSERT INTO {table} (id, sector_id, code, name)
            VALUES (:id, :sector_id, :code, :name);
            """.format(table=UniverseDb._SubsectorNamesTableName)
        rows = []
        for subsectorName in names:
            rows.append({
                'id': subsectorName.id(),
                'sector_id': subsectorName.sectorId(),
                'code': subsectorName.code(),
                'name': subsectorName.name()})
        cursor.executemany(sql, rows)

    def _loadSubsectorNames(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbSubsectorName]:
        sql = """
            SELECT id, sector_id, code, name
            FROM {table};
            """.format(table=UniverseDb._SubsectorNamesTableName)
        cursor.execute(sql)

        names = []
        for row in cursor.fetchall():
            nameId = row[0]
            sectorId = row[1]

            try:
                names.append(multiverse.DbSubsectorName(
                    id=nameId,
                    sectorId=sectorId,
                    code=row[2],
                    name=row[3]))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load subsector name {nameId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return names

    def _insertSectorLabels(
            self,
            cursor: sqlite3.Cursor,
            labels: typing.Collection[multiverse.DbSectorLabel]
            ) -> None:
        if not labels:
            return

        sql = """
            INSERT INTO {table} (id, sector_id, text, x, y,
                colour, size, wrap)
            VALUES (:id, :sector_id, :text, :x, :y,
                :colour, :size, :wrap);
            """.format(table=UniverseDb._SectorLabelsTableName)
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
                'wrap': 1 if label.wrap() else 0})
        cursor.executemany(sql, rows)

    def _loadSectorLabels(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbSectorLabel]:
        sql = """
            SELECT id, sector_id, text, x, y, colour, size, wrap
            FROM {table};
            """.format(table=UniverseDb._SectorLabelsTableName)
        cursor.execute(sql)

        labels = []
        for row in cursor.fetchall():
            labelId = row[0]
            sectorId = row[1]

            try:
                labels.append(multiverse.DbSectorLabel(
                    id=labelId,
                    sectorId=sectorId,
                    text=row[2],
                    worldX=row[3],
                    worldY=row[4],
                    colour=row[5],
                    size=row[6],
                    wrap=True if row[7] else False))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load label {labelId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return labels

    def _insertTags(
            self,
            cursor: sqlite3.Cursor,
            tags: typing.Collection[multiverse.DbTag]
            ) -> None:
        if not tags:
            return

        sql = """
            INSERT INTO {table} (id, sector_id, tag)
            VALUES (:id, :sector_id, :tag);
            """.format(table=UniverseDb._SectorTagsTableName)
        rows = []
        for tag in tags:
            rows.append({
                'id': tag.id(),
                'sector_id': tag.sectorId(),
                'tag': tag.tag()})
        cursor.executemany(sql, rows)

    def _loadTags(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbTag]:
        sql = """
            SELECT id, sector_id, tag
            FROM {table};
            """.format(table=UniverseDb._SectorTagsTableName)
        cursor.execute(sql)

        tags = []
        for row in cursor.fetchall():
            tagId = row[0]
            sectorId = row[1]

            try:
                tags.append(multiverse.DbTag(
                    id=tagId,
                    sectorId=sectorId,
                    tag=row[2]))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load tag {tagId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return tags

    def _insertProducts(
            self,
            cursor: sqlite3.Cursor,
            products: typing.Collection[multiverse.DbProduct]
            ) -> None:
        if not products:
            return

        sql = """
            INSERT INTO {table} (id, sector_id, publication, author,
                publisher, reference)
            VALUES (:id, :sector_id, :publication, :author,
                :publisher, :reference);
            """.format(table=UniverseDb._ProductsTableName)
        rows = []
        for product in products:
            rows.append({
                'id': product.id(),
                'sector_id': product.sectorId(),
                'publication': product.publication(),
                'author': product.author(),
                'publisher': product.publisher(),
                'reference': product.reference()})
        cursor.executemany(sql, rows)

    def _loadProducts(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbTag]:
        sql = """
            SELECT id, sector_id, publication, author, publisher, reference
            FROM {table};
            """.format(table=UniverseDb._ProductsTableName)
        cursor.execute(sql)

        products = []
        for row in cursor.fetchall():
            productId = row[0]
            sectorId = row[1]

            try:
                products.append(multiverse.DbProduct(
                    id=productId,
                    sectorId=sectorId,
                    publication=row[2],
                    author=row[3],
                    publisher=row[4],
                    reference=row[5]))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load product {productId!r} from universe {self._universePath!r}',
                    exc_info=ex)

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
        sql = """
            DELETE FROM {table}
            WHERE id == ? OR (hex_x == ? AND hex_y == ?);
        """.format(
            table=UniverseDb._SystemsTableName)
        cursor.executemany(sql, ((s.id(), s.hexX(), s.hexY()) for s in systems))

        self._insertSystems(
            systems=systems,
            cursor=cursor)

    def _deleteSystem(
            cursor: sqlite3.Cursor,
            systemId: str
            ) -> None:
        sql = """
            DELETE FROM {table}
            WHERE id = :id;
            """.format(
            table=UniverseDb._SystemsTableName)
        cursor.execute(sql, {'id': systemId})

    def _insertSystems(
            self,
            cursor: sqlite3.Cursor,
            systems: typing.Collection[multiverse.DbSystem]
            ) -> None:
        sql = """
            INSERT INTO {table} (id, hex_x, hex_y, name,
                planetoid_belt_count, gas_giant_count, world_count,
                zone, allegiance_id, notes)
            VALUES (:id, :hex_x, :hex_y, :name,
                :planetoid_belt_count, :gas_giant_count, :world_count,
                :zone, :allegiance_id, :notes);
            """.format(table=UniverseDb._SystemsTableName)
        rows = []
        stars = []
        bodies = []
        for system in systems:
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

            if system.stars():
                stars.extend(system.stars())
            if system.bodies():
                bodies.extend(system.bodies())
        cursor.executemany(sql, rows)

        if stars:
            self._insertStars(cursor=cursor, stars=stars)
        if bodies:
            self._insertBodies(cursor=cursor, bodies=bodies)

    def _loadSystems(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbSystem]:
        stars = self._loadStars(cursor=cursor)
        systemStarsMap = {}
        for star in stars:
            systemStars = systemStarsMap.get(star.systemId())
            if systemStars is None:
                systemStars = []
                systemStarsMap[star.systemId()] = systemStars
            systemStars.append(star)

        bodies = self._loadBodies(cursor=cursor)
        systemBodiesMap = {}
        for body in bodies:
            systemBodies = systemBodiesMap.get(body.systemId())
            if systemBodies is None:
                systemBodies = []
                systemBodiesMap[body.systemId()] = systemBodies
            systemBodies.append(body)

        sql = """
            SELECT id, hex_x, hex_y, name,
                planetoid_belt_count, gas_giant_count, world_count,
                zone, allegiance_id, notes
            FROM {table};
            """.format(
                table=UniverseDb._SystemsTableName)
        cursor.execute(sql)

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
                    worldCount=row[6],
                    zone=row[7],
                    allegianceId=row[8],
                    notes=row[9],
                    stars=systemStarsMap.get(systemId),
                    bodies=systemBodiesMap.get(systemId)))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load system {systemId!r} from {self._universePath!r}',
                    exc_info=ex)

        return systems

    def _insertStars(
            self,
            cursor: sqlite3.Cursor,
            stars: typing.Collection[multiverse.DbStar]
            ) -> None:
        if not stars:
            return

        sql = """
            INSERT INTO {table} (id, system_id, luminosity_class, spectral_class, spectral_scale)
            VALUES (:id, :system_id, :luminosity_class, :spectral_class, :spectral_scale);
            """.format(table=UniverseDb._StarsTableName)
        rows = []
        for star in stars:
            rows.append({
                'id': star.id(),
                'system_id': star.systemId(),
                'luminosity_class': star.luminosityClass(),
                'spectral_class': star.spectralClass(),
                'spectral_scale': star.spectralScale()})
        cursor.executemany(sql, rows)

    def _loadStars(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbStar]:
        sql = """
            SELECT id, system_id, luminosity_class, spectral_class, spectral_scale
            FROM {table};
            """.format(table=UniverseDb._StarsTableName)
        cursor.execute(sql)

        stars = []
        for row in cursor.fetchall():
            starId = row[0]

            try:
                stars.append(multiverse.DbStar(
                    id=starId,
                    systemId=row[1],
                    luminosityClass=row[2],
                    spectralClass=row[3],
                    spectralScale=row[4]))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load star {starId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return stars

    def _insertBodies(
            self,
            cursor: sqlite3.Cursor,
            bodies: typing.Collection[multiverse.DbBody]
            ) -> None:
        if not bodies:
            return

        sql = """
            INSERT INTO {table} (id, system_id, orbit_index, name, notes)
            VALUES (:id, :system_id, :orbit_index, :name, :notes)
            """.format(table=UniverseDb._BodiesTableName)
        rows = []
        for body in bodies:
            rows.append({
                'id': body.id(),
                'system_id': body.systemId(),
                'orbit_index': body.orbitIndex(),
                'name': body.name(),
                'notes': body.notes()})
        cursor.executemany(sql, rows)

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
        rows = []
        for body in bodies:
            if not isinstance(body, multiverse.DbWorld):
                continue

            rows.append({
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
        cursor.executemany(sql, rows)

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
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbBody]:
        worldNobilitiesMap = {}
        for nobility in self._loadNobilities(cursor=cursor):
            nobilities = worldNobilitiesMap.get(nobility.worldId())
            if nobilities is None:
                nobilities = []
                worldNobilitiesMap[nobility.worldId()] = nobilities
            nobilities.append(nobility)

        worldBasesMap = {}
        for base in self._loadBases(cursor=cursor):
            bases = worldBasesMap.get(base.worldId())
            if bases is None:
                bases = []
                worldBasesMap[base.worldId()] = bases
            bases.append(base)

        worldTradeCodesMap = {}
        for tradeCode in self._loadTradeCodes(cursor=cursor):
            tradeCodes = worldTradeCodesMap.get(tradeCode.worldId())
            if tradeCodes is None:
                tradeCodes = []
                worldTradeCodesMap[tradeCode.worldId()] = tradeCodes
            tradeCodes.append(tradeCode)

        worldPopulationsMap = {}
        for population in self._loadSophontPopulations(cursor=cursor):
            populations = worldPopulationsMap.get(population.worldId())
            if populations is None:
                populations = []
                worldPopulationsMap[population.worldId()] = populations
            populations.append(population)

        worldRulingAllegianceMap = {}
        for ruler in self._loadRulingAllegiances(cursor=cursor):
            rulers = worldRulingAllegianceMap.get(ruler.worldId())
            if rulers is None:
                rulers = []
                worldRulingAllegianceMap[ruler.worldId()] = rulers
            rulers.append(ruler)

        worldOwnersMap = {}
        for owner in self._loadOwningSystems(cursor=cursor):
            owners = worldOwnersMap.get(owner.worldId())
            if owners is None:
                owners = []
                worldOwnersMap[owner.worldId()] = owners
            owners.append(owner)

        worldColoniesMap = {}
        for colony in self._loadColonySystems(cursor=cursor):
            colonies = worldColoniesMap.get(colony.worldId())
            if colonies is None:
                colonies = []
                worldColoniesMap[colony.worldId()] = colonies
            colonies.append(colony)

        worldResearchStationsMap = {}
        for station in self._loadResearchStations(cursor=cursor):
            stations = worldResearchStationsMap.get(station.worldId())
            if stations is None:
                stations = []
                worldResearchStationsMap[station.worldId()] = stations
            stations.append(station)

        worldRemarksMap = {}
        for remark in self._loadCustomRemarks(cursor=cursor):
            remarks = worldRemarksMap.get(remark.worldId())
            if remarks is None:
                remarks = []
                worldRemarksMap[remark.worldId()] = remarks
            remarks.append(remark)

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
            JOIN {bodiesTable} b ON b.id = w.body_id;
            """.format(
                worldsTable=UniverseDb._WorldsTableName,
                bodiesTable=UniverseDb._BodiesTableName,)
        cursor.execute(sql)

        bodies = []
        for row in cursor.fetchall():
            bodyId = row[0]

            try:
                bodies.append(multiverse.DbWorld(
                    id=bodyId,
                    systemId=row[1],
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
                logging.error(
                    f'UniverseDb failed to load body {bodyId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return bodies

    def _insertNobilities(
            self,
            cursor: sqlite3.Cursor,
            nobilities: typing.Collection[multiverse.DbNobility]
            ) -> None:
        if not nobilities:
            return

        sql = """
            INSERT INTO {table} (id, world_id, code)
            VALUES (:id, :world_id, :code)
            """.format(table=UniverseDb._NobilitiesTableName)
        rows = []
        for nobility in nobilities:
            rows.append({
                'id': nobility.id(),
                'world_id': nobility.worldId(),
                'code': nobility.code()})
        cursor.executemany(sql, rows)

    def _loadNobilities(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbNobility]:
        sql = """
            SELECT id, world_id, code
            FROM {table};
            """.format(table=UniverseDb._NobilitiesTableName)
        cursor.execute(sql)

        nobilities = []
        for row in cursor.fetchall():
            nobilityId = row[0]
            worldId = row[1]

            try:
                nobilities.append(multiverse.DbNobility(
                    id=nobilityId,
                    worldId=worldId,
                    code=row[2]))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load nobility {nobilityId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return nobilities

    def _insertBases(
            self,
            cursor: sqlite3.Cursor,
            bases: typing.Collection[multiverse.DbBase]
            ) -> None:
        if not bases:
            return

        sql = """
            INSERT INTO {table} (id, world_id, code)
            VALUES (:id, :world_id, :code);
            """.format(table=UniverseDb._BasesTableName)
        rows = []
        for base in bases:
            rows.append({
                'id': base.id(),
                'world_id': base.worldId(),
                'code': base.code()})
        cursor.executemany(sql, rows)

    def _loadBases(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbBase]:
        sql = """
            SELECT id, world_id, code
            FROM {table};
            """.format(table=UniverseDb._BasesTableName)
        cursor.execute(sql)

        bases = []
        for row in cursor.fetchall():
            baseId = row[0]
            worldId = row[1]

            try:
                bases.append(multiverse.DbBase(
                    id=baseId,
                    worldId=worldId,
                    code=row[2]))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load base {baseId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return bases

    def _insertTradeCodes(
            self,
            cursor: sqlite3.Cursor,
            codes: typing.Collection[multiverse.DbTradeCode]
            ) -> None:
        if not codes:
            return

        sql = """
            INSERT INTO {table} (id, world_id, code)
            VALUES (:id, :world_id, :code)
            """.format(table=UniverseDb._TradeCodesTableName)
        rows = []
        for code in codes:
            rows.append({
                'id': code.id(),
                'world_id': code.worldId(),
                'code': code.code()})
        cursor.executemany(sql, rows)

    def _loadTradeCodes(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbTradeCode]:
        sql = """
            SELECT id, world_id, code
            FROM {table};
            """.format(table=UniverseDb._TradeCodesTableName)
        cursor.execute(sql)

        tradeCodes = []
        for row in cursor.fetchall():
            tradeCodeId = row[0]
            worldId = row[1]

            try:
                tradeCodes.append(multiverse.DbTradeCode(
                    id=tradeCodeId,
                    worldId=worldId,
                    code=row[2]))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load trade code {tradeCodeId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return tradeCodes

    def _insertSophontPopulations(
            self,
            cursor: sqlite3.Cursor,
            populations: typing.Collection[multiverse.DbSophontPopulation]
            ) -> None:
        if not populations:
            return

        sql = """
            INSERT INTO {table} (id, world_id, sophont_id, percentage, is_home_world, is_die_back)
            VALUES (:id, :world_id, :sophont_id, :percentage, :is_home_world, :is_die_back)
            """.format(table=UniverseDb._SophontPopulationsTableName)
        rows = []
        for sophont in populations:
            rows.append({
                'id': sophont.id(),
                'world_id': sophont.worldId(),
                'sophont_id': sophont.sophontId(),
                'percentage': sophont.percentage(),
                'is_home_world': 1 if sophont.isHomeWorld() else 0,
                'is_die_back': 1 if sophont.isDieBack() else 0})
        cursor.executemany(sql, rows)

    def _loadSophontPopulations(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbSophontPopulation]:
        sql = """
            SELECT id, world_id, sophont_id, percentage, is_home_world, is_die_back
            FROM {table};
            """.format(table=UniverseDb._SophontPopulationsTableName)
        cursor.execute(sql)

        populations = []
        for row in cursor.fetchall():
            populationId = row[0]
            worldId = row[1]

            try:
                populations.append(multiverse.DbSophontPopulation(
                    id=populationId,
                    worldId=worldId,
                    sophontId=row[2],
                    percentage=row[3],
                    isHomeWorld=True if row[4] else False,
                    isDieBack=True if row[5] else False))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load sophont population {populationId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return populations

    def _insertRulingAllegiances(
            self,
            cursor: sqlite3.Cursor,
            rulers: typing.Collection[multiverse.DbRulingAllegiance]
            ) -> None:
        if not rulers:
            return

        sql = """
            INSERT INTO {table} (id, world_id, allegiance_id)
            VALUES (:id, :world_id, :allegiance_id)
            """.format(table=UniverseDb._RulingAllegiancesTableName)
        rows = []
        for rulingAllegiance in rulers:
            rows.append({
                'id': rulingAllegiance.id(),
                'world_id': rulingAllegiance.worldId(),
                'allegiance_id': rulingAllegiance.allegianceId()})
        cursor.executemany(sql, rows)

    def _loadRulingAllegiances(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbRulingAllegiance]:
        sql = """
            SELECT id, world_id, allegiance_id
            FROM {table};
            """.format(table=UniverseDb._RulingAllegiancesTableName)
        cursor.execute(sql)

        rulers = []
        for row in cursor.fetchall():
            rulerId = row[0]
            worldId = row[1]

            try:
                rulers.append(multiverse.DbRulingAllegiance(
                    id=rulerId,
                    worldId=worldId,
                    allegianceId=row[2]))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load ruling allegiance {rulerId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return rulers

    def _insertOwningSystems(
            self,
            cursor: sqlite3.Cursor,
            owners: typing.Collection[multiverse.DbOwningSystem]
            ) -> None:
        if not owners:
            return

        sql = """
            INSERT INTO {table} (id, world_id, hex_x, hex_y, sector_abbreviation)
            VALUES (:id, :world_id, :hex_x, :hex_y, :sector_abbreviation)
            """.format(table=UniverseDb._OwningSystemsTableName)
        rows = []
        for owner in owners:
            rows.append({
                'id': owner.id(),
                'world_id': owner.worldId(),
                'hex_x': owner.hexX(),
                'hex_y': owner.hexY(),
                'sector_abbreviation': owner.sectorAbbreviation()})
        cursor.executemany(sql, rows)

    def _loadOwningSystems(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbOwningSystem]:
        sql = """
            SELECT id, world_id, hex_x, hex_y, sector_abbreviation
            FROM {table};
            """.format(table=UniverseDb._OwningSystemsTableName)
        cursor.execute(sql)

        owners = []
        for row in cursor.fetchall():
            ownerId = row[0]
            worldId = row[1]

            try:
                owners.append(multiverse.DbOwningSystem(
                    id=ownerId,
                    worldId=worldId,
                    hexX=row[2],
                    hexY=row[3],
                    sectorAbbreviation=row[4]))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load owning system {ownerId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return owners

    def _insertColonySystems(
            self,
            cursor: sqlite3.Cursor,
            colonies: typing.Collection[multiverse.DbColonySystem]
            ) -> None:
        if not colonies:
            return

        sql = """
            INSERT INTO {table} (id, world_id, hex_x, hex_y, sector_abbreviation)
            VALUES (:id, :world_id, :hex_x, :hex_y, :sector_abbreviation)
            """.format(table=UniverseDb._ColonySystemsTableName)
        rows = []
        for colony in colonies:
            rows.append({
                'id': colony.id(),
                'world_id': colony.worldId(),
                'hex_x': colony.hexX(),
                'hex_y': colony.hexY(),
                'sector_abbreviation': colony.sectorAbbreviation()})
        cursor.executemany(sql, rows)

    def _loadColonySystems(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbColonySystem]:
        sql = """
            SELECT id, world_id, hex_x, hex_y, sector_abbreviation
            FROM {table};
            """.format(table=UniverseDb._ColonySystemsTableName)
        cursor.execute(sql)

        colonies = []
        for row in cursor.fetchall():
            colonyId = row[0]
            worldId = row[1]

            try:
                colonies.append(multiverse.DbColonySystem(
                    id=colonyId,
                    worldId=worldId,
                    hexX=row[2],
                    hexY=row[3],
                    sectorAbbreviation=row[4]))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load colony system {colonyId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return colonies

    def _insertResearchStations(
            self,
            cursor: sqlite3.Cursor,
            stations: typing.Collection[multiverse.DbResearchStation]
            ) -> None:
        if not stations:
            return

        sql = """
            INSERT INTO {table} (id, world_id, code)
            VALUES (:id, :world_id, :code);
            """.format(table=UniverseDb._ResearchStationTableName)
        rows = []
        for station in stations:
            rows.append({
                'id': station.id(),
                'world_id': station.worldId(),
                'code': station.code()})
        cursor.executemany(sql, rows)

    def _loadResearchStations(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbResearchStation]:
        sql = """
            SELECT id, world_id, code
            FROM {table};
            """.format(table=UniverseDb._ResearchStationTableName)
        cursor.execute(sql)

        stations = []
        for row in cursor.fetchall():
            stationId = row[0]
            worldId = row[1]

            try:
                stations.append(multiverse.DbResearchStation(
                    id=stationId,
                    worldId=worldId,
                    code=row[2]))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load research station {stationId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return stations

    def _insertCustomRemarks(
            self,
            cursor: sqlite3.Cursor,
            remarks: typing.Collection[multiverse.DbCustomRemark]
            ) -> None:
        if not remarks:
            return

        sql = """
            INSERT INTO {table} (id, world_id, remark)
            VALUES (:id, :world_id, :remark)
            """.format(table=UniverseDb._CustomRemarksTableName)
        rows = []
        for remark in remarks:
            rows.append({
                'id': remark.id(),
                'world_id': remark.worldId(),
                'remark': remark.remark()})
        cursor.executemany(sql, rows)

    def _loadCustomRemarks(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbCustomRemark]:
        sql = """
            SELECT id, world_id, remark
            FROM {table};
            """.format(table=UniverseDb._CustomRemarksTableName)
        cursor.execute(sql)

        remarks = []
        for row in cursor.fetchall():
            remarkId = row[0]
            worldId = row[1]

            try:
                remarks.append(multiverse.DbCustomRemark(
                    id=remarkId,
                    worldId=worldId,
                    remark=row[2]))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load custom remark {remarkId!r} from universe {self._universePath!r}',
                    exc_info=ex)

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

        sql = """
            INSERT INTO {table} (id, sector_id, start_hex_x, start_hex_y, end_hex_x, end_hex_y,
                start_offset_x, start_offset_y, end_offset_x, end_offset_y, type, style,
                colour, width, allegiance_id)
            VALUES (:id, :sector_id, :start_hex_x, :start_hex_y, :end_hex_x, :end_hex_y,
                :start_offset_x, :start_offset_y, :end_offset_x, :end_offset_y, :type, :style,
                :colour, :width, :allegiance_id);
            """.format(table=UniverseDb._RoutesTableName)
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
        cursor.executemany(sql, rows)

    def _loadRoutes(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbRoute]:
        sql = """
            SELECT id, sector_id, start_hex_x, start_hex_y, end_hex_x, end_hex_y,
                start_offset_x, start_offset_y, end_offset_x, end_offset_y,
                type, style, colour, width, allegiance_id
            FROM {table};
            """.format(table=UniverseDb._RoutesTableName)
        cursor.execute(sql)

        routes = []
        for row in cursor.fetchall():
            routeId = row[0]
            sectorId = row[1]

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
                logging.error(
                    f'UniverseDb failed to load route {routeId!r} from universe {self._universePath!r}',
                    exc_info=ex)

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
                'show_label': 1 if border.showLabel() else 0,
                'wrap_label': 1 if border.wrapLabel() else 0})
            for hexX, hexY in border.hexes():
                hexRows.append({
                    'border_id': border.id(),
                    'hex_x': hexX,
                    'hex_y': hexY})
        cursor.executemany(bordersSql, borderRows)
        cursor.executemany(hexesSql, hexRows)

    def _loadBorders(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbBorder]:
        sql = """
            SELECT id, sector_id, allegiance_id, style, colour, label,
                label_x, label_y, show_label, wrap_label
            FROM {table};
            """.format(
                table=UniverseDb._BordersTableName)
        cursor.execute(sql)

        # TODO: Should load all points in single request
        sql = """
            SELECT hex_x, hex_y
            FROM {table}
            WHERE border_id = :id;
            """.format(table=UniverseDb._BorderHexesTableName)
        borders = []
        for row in cursor.fetchall():
            borderId = row[0]
            sectorId = row[1]

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
                logging.error(
                    f'UniverseDb failed to load border {borderId!r} from universe {self._universePath!r}',
                    exc_info=ex)

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
        for region in regions:
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

    def _loadRegions(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbRegion]:
        sql = """
            SELECT id, sector_id, colour, label, label_x, label_y, show_label, wrap_label
            FROM {table};
            """.format(table=UniverseDb._RegionsTableName)
        cursor.execute(sql)

        # TODO: Should load all points in a single request
        sql = """
            SELECT hex_x, hex_y
            FROM {table}
            WHERE region_id = :id;
            """.format(table=UniverseDb._RegionHexesTableName)
        regions = []
        for row in cursor.fetchall():
            regionId = row[0]
            sectorId = row[1]

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
                logging.error(
                    f'UniverseDb failed to load region {regionId!r} from universe {self._universePath!r}',
                    exc_info=ex)

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

    def _saveMapLabel(
            self,
            cursor: sqlite3.Cursor,
            label: multiverse.DbMapLabel
            ) -> None:
        sql = """
            INSERT INTO {table} (id, text, x, y, layer,
                alignment, colour, size, rotation)
            VALUES (:id, :text, :x, :y, :layer,
                :alignment, :colour, :size, :rotation)
            ON CONFLICT(id) DO UPDATE SET
                text = excluded.text,
                x = excluded.x,
                y = excluded.y,
                layer = excluded.layer,
                alignment = excluded.alignment,
                colour = excluded.colour,
                size = excluded.size,
                rotation = excluded.rotation;
            """.format(table=UniverseDb._MapLabelsTableName)
        cursor.execute(sql, {
            'id': label.id(),
            'text': label.text(),
            'x': label.worldX(),
            'y': label.worldY(),
            'layer': label.layer(),
            'alignment': label.alignment(),
            'colour': label.colour(),
            'size': label.size(),
            'rotation': label.rotation()})

    def _loadMapLabels(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbMapLabel]:
        sql = """
            SELECT id, text, x, y, layer, alignment, colour, size, rotation
            FROM {table};
            """.format(
                table=UniverseDb._MapLabelsTableName)
        cursor.execute(sql)

        labels: typing.List[multiverse.DbMapLabel] = []
        for row in cursor.fetchall():
            labelId = row[0]

            try:
                labels.append(multiverse.DbMapLabel(
                    id=row[0],
                    text=row[1],
                    worldX=row[2],
                    worldY=row[3],
                    layer=row[4],
                    alignment=row[5],
                    colour=row[6],
                    size=row[7],
                    rotation=row[8]))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load map label {labelId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return labels

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

    def _saveMapVector(
            self,
            cursor: sqlite3.Cursor,
            vector: multiverse.DbMapVector
            ) -> None:
        sql = """
            INSERT INTO {table} (id, layer, closed)
            VALUES (:id, :layer, :closed)
            ON CONFLICT(id) DO UPDATE SET
                layer = excluded.layer;
            """.format(table=UniverseDb._MapVectorsTableName)
        cursor.execute(sql, {
            'id': vector.id(),
            'layer': vector.layer(),
            'closed': 1 if vector.closed() else 0})

        sql = """
            DELETE FROM {table}
            WHERE vector_id = :vector_id;
            """.format(table=UniverseDb._MapVectorPointsTableName)
        cursor.execute(sql, {'vector_id': vector.id()})

        sql = """
            INSERT INTO {table} (vector_id, x, y)
            VALUES (:vector_id, :x, :y);
            """.format(table=UniverseDb._MapVectorPointsTableName)
        cursor.executemany(sql, [(vector.id(), x, y) for x, y in vector.points()])

    def _loadMapVectors(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[multiverse.DbMapVector]:
        sql = """
            SELECT vector_id, x, y
            FROM {table};
            """.format(table=UniverseDb._MapVectorPointsTableName)
        cursor.execute(sql)

        vectorPointsMap: typing.Dict[str, typing.List[typing.Tuple[float, float]]] = {}
        for row in cursor.fetchall():
            vectorId = row[0]
            points = vectorPointsMap.get(vectorId)
            if points is None:
                points = []
                vectorPointsMap[vectorId] = points
            points.append((row[1], row[2]))

        sql = """
            SELECT id, layer, closed
            FROM {table};
            """.format(table=UniverseDb._MapVectorsTableName)
        cursor.execute(sql)

        vectors: typing.List[multiverse.DbMapVector] = []
        for row in cursor.fetchall():
            vectorId = row[0]

            try:
                vectors.append(multiverse.DbMapVector(
                    id=vectorId,
                    points=vectorPointsMap.get(vectorId),
                    layer=row[1],
                    closed=True if row[2] else False))
            except Exception as ex:
                logging.error(
                    f'UniverseDb failed to load map vector {vectorId!r} from universe {self._universePath!r}',
                    exc_info=ex)

        return vectors

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