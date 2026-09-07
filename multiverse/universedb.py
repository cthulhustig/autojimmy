import collections
import common
import database
import enum
import inspect
import logging
import itertools
import math
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

# TODO: Add progress to save & delete

# TODO: Chunk large loads/saves/deletes for more granular progress
# - I think this needs a way to generalise the load/save/delete code so I don't need to add
# chunking to multiple places
# - Needs structures to describe conversion similar to what I've done for columns/tables
#   - Need to handle mapping between column and DbObject constructor parameters/getter functions
#       - Need to have constructor parameters and getter functions in the mapping so saves can be handled as well as loads
#   - This mapping is likely to be fragile if I rename/restructure things
#       - It might be possible to assert check things at the point the definitions are being made (I think I did something similar in ObjectDb)
#       - I think checking that the target object type has the specified setter should be possible, might even be possible to check the typing annotation for the return type
#       - I __think__ the inspect library lets you list the input parameters for a function so it could be possible to verify the constructor arguments
#   - Most mappings will be simple map this column to this parameter
#       - This mapping would need to allow you to specify
#           - The column name
#           - The column type (so bool can be converted to int when saving)
#           - The DbObject constructor parameter
#           - The DbObject getter function
#           - The DbObject type (so int can be converted to bool when loading)
#       - Would need to specify the type of the DbObject parameter so it can map int to bool
#   - There would be more complex mappings where one of the DbObject properties comes from another table
#       - This would be things like subsector names or border hexes
#       - These currently look like they all look in a similar manor
#           - The entire sub-table is loaded into a list of sub-objects
#           - The list of sub-objects is converted to a dict that maps the id of the primary table to a list of objects from the su-table for that primary object
#           - The dict is used to retrieve the sub-objects when constructing the primary object
#       - This mapping definition would need to allow you to specify the following
#           - The sub-table name
#           - The primary DbObject constructor parameter
#           - The primary DbObject getter function
#           - The column from the sub-table that contains the id of the primary object
#               - NOTE: Specifying the column name (rather than the sub-object getter function) would mean the mapping
#                 of primary id to list of sub-objects would need to be created while the sub-objects were being created
#                 rather than creating them all in a list the creating the dict afterwards

class ParameterMapping(object):
    def __init__(
            self,
            paramName: str
            ) -> None:
        self._paramName = paramName

    def paramName(self) -> str:
        return self._paramName

class ColumnParameterMapping(ParameterMapping):
    class ParamType(enum.Enum):
        String = 0
        Integer = 1
        Float = 2
        Boolean = 3

    def __init__(
            self,
            columnName: str,
            paramType: ParamType,
            paramName: str
            ) -> None:
        super().__init__(paramName=paramName)
        self._columnName = columnName
        self._paramType = paramType

    def columnName(self) -> str:
        return self._columnName

    def paramType(self) -> ParamType:
        return self._paramType

class SubTableParameterMapping(ParameterMapping):
    def __init__(
            self,
            table: 'TableMapping',
            parentColumnName: str,
            initParam: str
            ) -> None:
        super().__init__(paramName=initParam)
        self._table = table
        self._parentColumnName = parentColumnName

    def table(self) -> 'TableMapping':
        return self._table

    def parentColumnName(self) -> str:
        return self._parentColumnName

class TableMapping(object):
    def __init__(
            self,
            tableName: str
            ) -> None:
        self._tableName = tableName

    def tableName(self) -> str:
        return self._tableName

class RawTableMapping(TableMapping):
    def __init__(
            self,
            tableName: str,
            columnNames: typing.Sequence[str],
            ) -> None:
        super().__init__(tableName=tableName)
        self._columnNames = list(columnNames)

    def columnNames(self) -> typing.Sequence[str]:
        return common.ConstSequenceRef(self._columnNames)

class ObjectTableMapping(TableMapping):
    def __init__(
            self,
            tableName: str,
            objectType: typing.Type[multiverse.DbObject],
            parameters: typing.Collection[ParameterMapping],
            deriveObjects: typing.Optional[typing.Collection['DerivedObjectMapping']] = None
            ) -> None:
        super().__init__(tableName=tableName)
        self._objectType = objectType
        self._parameters = list(parameters)
        self._deriveObjects = list(deriveObjects) if deriveObjects is not None else None

        initSignature = inspect.signature(objectType.__init__)
        seenInitParams = set()
        for paramMapping in self._parameters:
            paramName = paramMapping.paramName()
            if paramMapping.paramName() not in initSignature.parameters:
                raise ValueError(f'{objectType}.__init__ doesn\'t have a {paramName!r} parameter')
            seenInitParams.add(paramName)

            if not callable(getattr(objectType, paramName, None)):
                raise ValueError(f'{objectType} doesn\'t have getter function named {paramName!r}')

    def objectType(self) -> typing.Type[multiverse.DbObject]:
        return self._objectType

    def parameters(self) -> typing.Collection[ParameterMapping]:
        return common.ConstCollectionRef(self._parameters)

    def deriveObjects(self) -> typing.Optional[typing.Collection['DerivedObjectMapping']]:
        return common.ConstCollectionRef(self._deriveObjects) if self._deriveObjects is not None else None

class DerivedObjectMapping(ObjectTableMapping):
    def __init__(
            self,
            tableName: str,
            objectType: typing.Type[multiverse.DbObject],
            parameters: typing.Collection[ParameterMapping],
            baseColumnName: str,
            ) -> None:
        super().__init__(tableName=tableName, objectType=objectType, parameters=parameters)
        self._baseColumnName = baseColumnName

    def baseColumnName(self) -> str:
        return self._baseColumnName

# TODO: I'm not sure this existing will make logical sense once I've
# finished moving stuff to the universe
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
        self._objectTypeToTableMapping: typing.Dict[
            typing.Type[multiverse.DbObject]
            ] = {}

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
                    cursor=connection.cursor(),
                    progress=progress)

    def saveAllegiances(
            self,
            allegiances: typing.Collection[multiverse.DbAllegiance],
            transaction: typing.Optional[database.Transaction] = None,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            return self._saveAllegiances(
                cursor=connection.cursor(),
                allegiances=allegiances,
                progress=progress)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._saveAllegiances(
                    cursor=connection.cursor(),
                    allegiances=allegiances,
                    progress=progress)

    def deleteAllegiances(
            self,
            allegianceIds: typing.Collection[str],
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            self._deleteAllegiances(
                cursor=connection.cursor(),
                allegianceIds=allegianceIds)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._deleteAllegiances(
                    cursor=connection.cursor(),
                    allegianceIds=allegianceIds)

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
            transaction: typing.Optional[database.Transaction] = None,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            return self._saveSophonts(
                cursor=connection.cursor(),
                sophonts=sophonts,
                progress=progress)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._saveSophonts(
                    cursor=connection.cursor(),
                    sophonts=sophonts,
                    progress=progress)

    def deleteSophonts(
            self,
            sophontIds: typing.Collection[str],
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            self._deleteSophonts(
                cursor=connection.cursor(),
                sophontIds=sophontIds)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._deleteSophonts(
                    cursor=connection.cursor(),
                    sophontIds=sophontIds)

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

    def saveSectors(
            self,
            sectors: typing.Collection[multiverse.DbSector],
            transaction: typing.Optional[database.Transaction] = None,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            self._saveSectors(
                cursor=connection.cursor(),
                sectors=sectors,
                progress=progress)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._saveSectors(
                    cursor=connection.cursor(),
                    sectors=sectors,
                    progress=progress)

    def deleteSectors(
            self,
            sectorIds: typing.Collection[str],
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            self._deleteSectors(
                cursor=connection.cursor(),
                sectorIds=sectorIds)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._deleteSectors(
                    cursor=connection.cursor(),
                    sectorIds=sectorIds)

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
            transaction: typing.Optional[database.Transaction] = None,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            self._saveSystems(
                cursor=connection.cursor(),
                systems=systems,
                progress=progress)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._saveSystems(
                    cursor=connection.cursor(),
                    systems=systems,
                    progress=progress)

    def deleteSystems(
            self,
            systemIds: typing.Collection[str],
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            self._deleteSystems(
                cursor=connection.cursor(),
                systemIds=systemIds)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._deleteSystems(
                    cursor=connection.cursor(),
                    systemIds=systemIds)

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

    def saveMapLabels(
            self,
            labels: typing.Collection[multiverse.DbMapLabel],
            transaction: typing.Optional[database.Transaction] = None,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            return self._saveMapLabels(
                cursor=connection.cursor(),
                labels=labels,
                progress=progress)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._saveMapLabels(
                    cursor=connection.cursor(),
                    labels=labels,
                    progress=progress)

    def deleteMapLabels(
            self,
            labelIds: typing.Collection[str],
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            self._deleteMapLabels(
                cursor=connection.cursor(),
                labelIds=labelIds)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._deleteMapLabels(
                    cursor=connection.cursor(),
                    labelIds=labelIds)

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

    def saveMapVectors(
            self,
            vectors: typing.Collection[multiverse.DbMapVector],
            transaction: typing.Optional[database.Transaction] = None,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            return self._saveMapVectors(
                cursor=connection.cursor(),
                vectors=vectors,
                progress=progress)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._saveMapVectors(
                    cursor=connection.cursor(),
                    vectors=vectors,
                    progress=progress)

    def deleteMapVectors(
            self,
            vectorIds: typing.Collection[str],
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        if transaction != None:
            connection = transaction.connection()
            self._deleteMapVectors(
                cursor=connection.cursor(),
                vectorIds=vectorIds)
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._deleteMapVectors(
                    cursor=connection.cursor(),
                    vectorIds=vectorIds)

    def copyTo(self, targetPath: str) -> None:
        self._database.copyTo(targetPath=targetPath)

    def _initTables(self) -> None:
        with self.createTransaction() as transaction:
            connection = transaction.connection()
            cursor = connection.cursor()

            self._createMetadataTable(cursor=cursor)
            self._createAllegianceTables(cursor=cursor)
            self._createSophontTables(cursor=cursor)
            self._createSectorTables(cursor=cursor)
            self._createSystemTables(cursor=cursor)
            # TODO: These should be called from here rather than _createSystemTables as I move them to the universe
            #self._createRouteTables(cursor=cursor)
            #self._createBorderTables(cursor=cursor)
            #self._createRegionTables(cursor=cursor)
            self._createMapLabelTables(cursor=cursor)
            self._createMapVectorTables(cursor=cursor)

    def _createMetadataTable(self, cursor: sqlite3.Cursor) -> None:
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

    def _createAllegianceTables(self, cursor: sqlite3.Cursor) -> None:
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

            self._objectTypeToTableMapping[multiverse.DbAllegiance] = ObjectTableMapping(
                tableName=UniverseDb._AllegiancesTableName,
                objectType=multiverse.DbAllegiance,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='name', paramType=ColumnParameterMapping.ParamType.String, paramName='name'),
                    ColumnParameterMapping(columnName='code', paramType=ColumnParameterMapping.ParamType.String, paramName='code'),
                    ColumnParameterMapping(columnName='legacy', paramType=ColumnParameterMapping.ParamType.String, paramName='legacy'),
                    ColumnParameterMapping(columnName='base', paramType=ColumnParameterMapping.ParamType.String, paramName='base'),
                    ColumnParameterMapping(columnName='route_colour', paramType=ColumnParameterMapping.ParamType.String, paramName='routeColour'),
                    ColumnParameterMapping(columnName='route_style', paramType=ColumnParameterMapping.ParamType.String, paramName='routeStyle'),
                    ColumnParameterMapping(columnName='route_width', paramType=ColumnParameterMapping.ParamType.Float, paramName='routeWidth'),
                    ColumnParameterMapping(columnName='border_colour', paramType=ColumnParameterMapping.ParamType.String, paramName='borderColour'),
                    ColumnParameterMapping(columnName='border_style', paramType=ColumnParameterMapping.ParamType.String, paramName='borderStyle')])

    def _createSophontTables(self, cursor: sqlite3.Cursor) -> None:
            self._database.createTable(
                cursor=cursor,
                tableName=UniverseDb._SophontsTableName,
                requiredSchemaVersion=UniverseDb._SophontsTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='code', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    database.ColumnDef(columnName='is_major', columnType=database.ColumnDef.ColumnType.Integer, allowedValues=(0, 1), isNullable=False)])

            self._objectTypeToTableMapping[multiverse.DbSophont] = ObjectTableMapping(
                tableName=UniverseDb._SophontsTableName,
                objectType=multiverse.DbSophont,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='name', paramType=ColumnParameterMapping.ParamType.String, paramName='name'),
                    ColumnParameterMapping(columnName='code', paramType=ColumnParameterMapping.ParamType.String, paramName='code'),
                    ColumnParameterMapping(columnName='is_major', paramType=ColumnParameterMapping.ParamType.Boolean, paramName='isMajor')])

    def _createSectorTables(self, cursor: sqlite3.Cursor) -> None:
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

            # TODO: These should be called from _initTables as I move them to the universe
            self._createRouteTables(cursor=cursor)
            self._createBorderTables(cursor=cursor)
            self._createRegionTables(cursor=cursor)

            self._objectTypeToTableMapping[multiverse.DbAlternateName] = ObjectTableMapping(
                tableName=UniverseDb._AlternateNamesTableName,
                objectType=multiverse.DbAlternateName,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='sector_id', paramType=ColumnParameterMapping.ParamType.String, paramName='sectorId'),
                    ColumnParameterMapping(columnName='name', paramType=ColumnParameterMapping.ParamType.String, paramName='name'),
                    ColumnParameterMapping(columnName='language', paramType=ColumnParameterMapping.ParamType.String, paramName='language')])

            self._objectTypeToTableMapping[multiverse.DbSubsectorName] = ObjectTableMapping(
                tableName=UniverseDb._SubsectorNamesTableName,
                objectType=multiverse.DbSubsectorName,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='sector_id', paramType=ColumnParameterMapping.ParamType.String, paramName='sectorId'),
                    ColumnParameterMapping(columnName='code', paramType=ColumnParameterMapping.ParamType.String, paramName='code'),
                    ColumnParameterMapping(columnName='name', paramType=ColumnParameterMapping.ParamType.String, paramName='name')])

            self._objectTypeToTableMapping[multiverse.DbSectorLabel] = ObjectTableMapping(
                tableName=UniverseDb._SectorLabelsTableName,
                objectType=multiverse.DbSectorLabel,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='sector_id', paramType=ColumnParameterMapping.ParamType.String, paramName='sectorId'),
                    ColumnParameterMapping(columnName='text', paramType=ColumnParameterMapping.ParamType.String, paramName='text'),
                    ColumnParameterMapping(columnName='x', paramType=ColumnParameterMapping.ParamType.Float, paramName='worldX'),
                    ColumnParameterMapping(columnName='y', paramType=ColumnParameterMapping.ParamType.Float, paramName='worldY'),
                    ColumnParameterMapping(columnName='colour', paramType=ColumnParameterMapping.ParamType.String, paramName='colour'),
                    ColumnParameterMapping(columnName='size', paramType=ColumnParameterMapping.ParamType.String, paramName='size'),
                    ColumnParameterMapping(columnName='wrap', paramType=ColumnParameterMapping.ParamType.Boolean, paramName='wrap')])

            self._objectTypeToTableMapping[multiverse.DbTag] = ObjectTableMapping(
                tableName=UniverseDb._SectorTagsTableName,
                objectType=multiverse.DbTag,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='sector_id', paramType=ColumnParameterMapping.ParamType.String, paramName='sectorId'),
                    ColumnParameterMapping(columnName='tag', paramType=ColumnParameterMapping.ParamType.String, paramName='tag')])

            self._objectTypeToTableMapping[multiverse.DbProduct] = ObjectTableMapping(
                tableName=UniverseDb._ProductsTableName,
                objectType=multiverse.DbProduct,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='sector_id', paramType=ColumnParameterMapping.ParamType.String, paramName='sectorId'),
                    ColumnParameterMapping(columnName='publication', paramType=ColumnParameterMapping.ParamType.String, paramName='publication'),
                    ColumnParameterMapping(columnName='author', paramType=ColumnParameterMapping.ParamType.String, paramName='author'),
                    ColumnParameterMapping(columnName='publisher', paramType=ColumnParameterMapping.ParamType.String, paramName='publisher'),
                    ColumnParameterMapping(columnName='reference', paramType=ColumnParameterMapping.ParamType.String, paramName='reference')])

            self._objectTypeToTableMapping[multiverse.DbSector] = ObjectTableMapping(
                tableName=UniverseDb._SectorsTableName,
                objectType=multiverse.DbSector,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='sector_x', paramType=ColumnParameterMapping.ParamType.Integer, paramName='sectorX'),
                    ColumnParameterMapping(columnName='sector_y', paramType=ColumnParameterMapping.ParamType.Integer, paramName='sectorY'),
                    ColumnParameterMapping(columnName='name', paramType=ColumnParameterMapping.ParamType.String, paramName='name'),
                    ColumnParameterMapping(columnName='language', paramType=ColumnParameterMapping.ParamType.String, paramName='language'),
                    ColumnParameterMapping(columnName='abbreviation', paramType=ColumnParameterMapping.ParamType.String, paramName='abbreviation'),
                    ColumnParameterMapping(columnName='sector_label', paramType=ColumnParameterMapping.ParamType.String, paramName='sectorLabel'),
                    ColumnParameterMapping(columnName='selected', paramType=ColumnParameterMapping.ParamType.Boolean, paramName='selected'),
                    ColumnParameterMapping(columnName='credits', paramType=ColumnParameterMapping.ParamType.String, paramName='credits'),
                    ColumnParameterMapping(columnName='publication', paramType=ColumnParameterMapping.ParamType.String, paramName='publication'),
                    ColumnParameterMapping(columnName='author', paramType=ColumnParameterMapping.ParamType.String, paramName='author'),
                    ColumnParameterMapping(columnName='publisher', paramType=ColumnParameterMapping.ParamType.String, paramName='publisher'),
                    ColumnParameterMapping(columnName='reference', paramType=ColumnParameterMapping.ParamType.String, paramName='reference'),
                    ColumnParameterMapping(columnName='notes', paramType=ColumnParameterMapping.ParamType.String, paramName='notes'),
                    SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbAlternateName], parentColumnName='sector_id', initParam='alternateNames'),
                    SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbSubsectorName], parentColumnName='sector_id', initParam='subsectorNames'),
                    SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbSectorLabel], parentColumnName='sector_id', initParam='labels'),
                    SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbTag], parentColumnName='sector_id', initParam='tags'),
                    SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbProduct], parentColumnName='sector_id', initParam='products'),
                    SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbRoute], parentColumnName='sector_id', initParam='routes'),
                    SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbBorder], parentColumnName='sector_id', initParam='borders'),
                    SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbRegion], parentColumnName='sector_id', initParam='regions')])

    def _createSystemTables(self, cursor: sqlite3.Cursor) -> None:
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
                tableName=UniverseDb._CustomRemarksTableName,
                requiredSchemaVersion=UniverseDb._CustomRemarksTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='world_id', columnType=database.ColumnDef.ColumnType.Text, isNullable=False,
                              foreignTableName=UniverseDb._BodiesTableName, foreignColumnName='id',
                              foreignDeleteOp=database.ColumnDef.ForeignKeyDeleteOp.Cascade),
                    database.ColumnDef(columnName='remark', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)])

            self._objectTypeToTableMapping[multiverse.DbStar] = ObjectTableMapping(
                tableName=UniverseDb._StarsTableName,
                objectType=multiverse.DbStar,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='system_id', paramType=ColumnParameterMapping.ParamType.String, paramName='systemId'),
                    ColumnParameterMapping(columnName='luminosity_class', paramType=ColumnParameterMapping.ParamType.String, paramName='luminosityClass'),
                    ColumnParameterMapping(columnName='spectral_class', paramType=ColumnParameterMapping.ParamType.String, paramName='spectralClass'),
                    ColumnParameterMapping(columnName='spectral_scale', paramType=ColumnParameterMapping.ParamType.String, paramName='spectralScale')])

            self._objectTypeToTableMapping[multiverse.DbNobility] = ObjectTableMapping(
                tableName=UniverseDb._NobilitiesTableName,
                objectType=multiverse.DbNobility,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='world_id', paramType=ColumnParameterMapping.ParamType.String, paramName='worldId'),
                    ColumnParameterMapping(columnName='code', paramType=ColumnParameterMapping.ParamType.String, paramName='code')])

            self._objectTypeToTableMapping[multiverse.DbTradeCode] = ObjectTableMapping(
                tableName=UniverseDb._TradeCodesTableName,
                objectType=multiverse.DbTradeCode,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='world_id', paramType=ColumnParameterMapping.ParamType.String, paramName='worldId'),
                    ColumnParameterMapping(columnName='code', paramType=ColumnParameterMapping.ParamType.String, paramName='code')])

            self._objectTypeToTableMapping[multiverse.DbSophontPopulation] = ObjectTableMapping(
                tableName=UniverseDb._SophontPopulationsTableName,
                objectType=multiverse.DbSophontPopulation,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='world_id', paramType=ColumnParameterMapping.ParamType.String, paramName='worldId'),
                    ColumnParameterMapping(columnName='sophont_id', paramType=ColumnParameterMapping.ParamType.String, paramName='sophontId'),
                    ColumnParameterMapping(columnName='percentage', paramType=ColumnParameterMapping.ParamType.Integer, paramName='percentage'),
                    ColumnParameterMapping(columnName='is_home_world', paramType=ColumnParameterMapping.ParamType.Boolean, paramName='isHomeWorld'),
                    ColumnParameterMapping(columnName='is_die_back', paramType=ColumnParameterMapping.ParamType.Boolean, paramName='isDieBack')])

            self._objectTypeToTableMapping[multiverse.DbRulingAllegiance] = ObjectTableMapping(
                tableName=UniverseDb._RulingAllegiancesTableName,
                objectType=multiverse.DbRulingAllegiance,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='world_id', paramType=ColumnParameterMapping.ParamType.String, paramName='worldId'),
                    ColumnParameterMapping(columnName='allegiance_id', paramType=ColumnParameterMapping.ParamType.String, paramName='allegianceId')])

            self._objectTypeToTableMapping[multiverse.DbOwningSystem] = ObjectTableMapping(
                tableName=UniverseDb._OwningSystemsTableName,
                objectType=multiverse.DbOwningSystem,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='world_id', paramType=ColumnParameterMapping.ParamType.String, paramName='worldId'),
                    ColumnParameterMapping(columnName='hex_x', paramType=ColumnParameterMapping.ParamType.Integer, paramName='hexX'),
                    ColumnParameterMapping(columnName='hex_y', paramType=ColumnParameterMapping.ParamType.Integer, paramName='hexY'),
                    ColumnParameterMapping(columnName='sector_abbreviation', paramType=ColumnParameterMapping.ParamType.String, paramName='sectorAbbreviation')])

            self._objectTypeToTableMapping[multiverse.DbColonySystem] = ObjectTableMapping(
                tableName=UniverseDb._ColonySystemsTableName,
                objectType=multiverse.DbColonySystem,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='world_id', paramType=ColumnParameterMapping.ParamType.String, paramName='worldId'),
                    ColumnParameterMapping(columnName='hex_x', paramType=ColumnParameterMapping.ParamType.Integer, paramName='hexX'),
                    ColumnParameterMapping(columnName='hex_y', paramType=ColumnParameterMapping.ParamType.Integer, paramName='hexY'),
                    ColumnParameterMapping(columnName='sector_abbreviation', paramType=ColumnParameterMapping.ParamType.String, paramName='sectorAbbreviation')])

            self._objectTypeToTableMapping[multiverse.DbBase] = ObjectTableMapping(
                tableName=UniverseDb._BasesTableName,
                objectType=multiverse.DbBase,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='world_id', paramType=ColumnParameterMapping.ParamType.String, paramName='worldId'),
                    ColumnParameterMapping(columnName='code', paramType=ColumnParameterMapping.ParamType.String, paramName='code')])

            self._objectTypeToTableMapping[multiverse.DbResearchStation] = ObjectTableMapping(
                tableName=UniverseDb._ResearchStationTableName,
                objectType=multiverse.DbResearchStation,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='world_id', paramType=ColumnParameterMapping.ParamType.String, paramName='worldId'),
                    ColumnParameterMapping(columnName='code', paramType=ColumnParameterMapping.ParamType.String, paramName='code')])

            self._objectTypeToTableMapping[multiverse.DbCustomRemark] = ObjectTableMapping(
                tableName=UniverseDb._CustomRemarksTableName,
                objectType=multiverse.DbCustomRemark,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='world_id', paramType=ColumnParameterMapping.ParamType.String, paramName='worldId'),
                    ColumnParameterMapping(columnName='remark', paramType=ColumnParameterMapping.ParamType.String, paramName='remark')])

            self._objectTypeToTableMapping[multiverse.DbBody] = ObjectTableMapping(
                tableName=UniverseDb._BodiesTableName,
                objectType=multiverse.DbBody,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='system_id', paramType=ColumnParameterMapping.ParamType.String, paramName='systemId'),
                    ColumnParameterMapping(columnName='orbit_index', paramType=ColumnParameterMapping.ParamType.Integer, paramName='orbitIndex'),
                    ColumnParameterMapping(columnName='name', paramType=ColumnParameterMapping.ParamType.String, paramName='name'),
                    ColumnParameterMapping(columnName='notes', paramType=ColumnParameterMapping.ParamType.String, paramName='notes')],
                deriveObjects=[
                    DerivedObjectMapping(
                        tableName=self._WorldsTableName,
                        baseColumnName='body_id',
                        objectType=multiverse.DbWorld,
                        parameters=[
                            ColumnParameterMapping(columnName='is_main_world', paramType=ColumnParameterMapping.ParamType.Boolean, paramName='isMainWorld'),
                            ColumnParameterMapping(columnName='starport', paramType=ColumnParameterMapping.ParamType.String, paramName='starport'),
                            ColumnParameterMapping(columnName='world_size', paramType=ColumnParameterMapping.ParamType.String, paramName='worldSize'),
                            ColumnParameterMapping(columnName='atmosphere', paramType=ColumnParameterMapping.ParamType.String, paramName='atmosphere'),
                            ColumnParameterMapping(columnName='hydrographics', paramType=ColumnParameterMapping.ParamType.String, paramName='hydrographics'),
                            ColumnParameterMapping(columnName='population', paramType=ColumnParameterMapping.ParamType.String, paramName='population'),
                            ColumnParameterMapping(columnName='government', paramType=ColumnParameterMapping.ParamType.String, paramName='government'),
                            ColumnParameterMapping(columnName='law_level', paramType=ColumnParameterMapping.ParamType.String, paramName='lawLevel'),
                            ColumnParameterMapping(columnName='tech_level', paramType=ColumnParameterMapping.ParamType.String, paramName='techLevel'),
                            ColumnParameterMapping(columnName='resources', paramType=ColumnParameterMapping.ParamType.String, paramName='resources'),
                            ColumnParameterMapping(columnName='labour', paramType=ColumnParameterMapping.ParamType.String, paramName='labour'),
                            ColumnParameterMapping(columnName='infrastructure', paramType=ColumnParameterMapping.ParamType.String, paramName='infrastructure'),
                            ColumnParameterMapping(columnName='efficiency', paramType=ColumnParameterMapping.ParamType.String, paramName='efficiency'),
                            ColumnParameterMapping(columnName='heterogeneity', paramType=ColumnParameterMapping.ParamType.String, paramName='heterogeneity'),
                            ColumnParameterMapping(columnName='acceptance', paramType=ColumnParameterMapping.ParamType.String, paramName='acceptance'),
                            ColumnParameterMapping(columnName='strangeness', paramType=ColumnParameterMapping.ParamType.String, paramName='strangeness'),
                            ColumnParameterMapping(columnName='symbols', paramType=ColumnParameterMapping.ParamType.String, paramName='symbols'),
                            ColumnParameterMapping(columnName='population_multiplier', paramType=ColumnParameterMapping.ParamType.String, paramName='populationMultiplier'),
                            SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbNobility], parentColumnName='world_id', initParam='nobilities'),
                            SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbBase], parentColumnName='world_id', initParam='bases'),
                            SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbTradeCode], parentColumnName='world_id', initParam='tradeCodes'),
                            SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbSophontPopulation], parentColumnName='world_id', initParam='sophontPopulations'),
                            SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbRulingAllegiance], parentColumnName='world_id', initParam='rulingAllegiances'),
                            SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbOwningSystem], parentColumnName='world_id', initParam='owningSystems'),
                            SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbColonySystem], parentColumnName='world_id', initParam='colonySystems'),
                            SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbResearchStation], parentColumnName='world_id', initParam='researchStations'),
                            SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbCustomRemark], parentColumnName='world_id', initParam='customRemarks')])])

            self._objectTypeToTableMapping[multiverse.DbSystem] = ObjectTableMapping(
                tableName=UniverseDb._SystemsTableName,
                objectType=multiverse.DbSystem,
                parameters=[
                    ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                    ColumnParameterMapping(columnName='hex_x', paramType=ColumnParameterMapping.ParamType.Integer, paramName='hexX'),
                    ColumnParameterMapping(columnName='hex_y', paramType=ColumnParameterMapping.ParamType.Integer, paramName='hexY'),
                    ColumnParameterMapping(columnName='name', paramType=ColumnParameterMapping.ParamType.String, paramName='name'),
                    ColumnParameterMapping(columnName='planetoid_belt_count', paramType=ColumnParameterMapping.ParamType.Integer, paramName='planetoidBeltCount'),
                    ColumnParameterMapping(columnName='gas_giant_count', paramType=ColumnParameterMapping.ParamType.Integer, paramName='gasGiantCount'),
                    ColumnParameterMapping(columnName='world_count', paramType=ColumnParameterMapping.ParamType.Integer, paramName='worldCount'),
                    ColumnParameterMapping(columnName='zone', paramType=ColumnParameterMapping.ParamType.String, paramName='zone'),
                    ColumnParameterMapping(columnName='allegiance_id', paramType=ColumnParameterMapping.ParamType.String, paramName='allegianceId'),
                    ColumnParameterMapping(columnName='notes', paramType=ColumnParameterMapping.ParamType.String, paramName='notes'),
                    SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbStar], parentColumnName='system_id', initParam='stars'),
                    SubTableParameterMapping(table=self._objectTypeToTableMapping[multiverse.DbBody], parentColumnName='system_id', initParam='bodies')])

    def _createRouteTables(self, cursor: sqlite3.Cursor) -> None:
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

        self._objectTypeToTableMapping[multiverse.DbRoute] = ObjectTableMapping(
            tableName=UniverseDb._RoutesTableName,
            objectType=multiverse.DbRoute,
            parameters=[
                ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                ColumnParameterMapping(columnName='sector_id', paramType=ColumnParameterMapping.ParamType.String, paramName='sectorId'),
                ColumnParameterMapping(columnName='start_hex_x', paramType=ColumnParameterMapping.ParamType.Integer, paramName='startHexX'),
                ColumnParameterMapping(columnName='start_hex_y', paramType=ColumnParameterMapping.ParamType.Integer, paramName='startHexY'),
                ColumnParameterMapping(columnName='end_hex_x', paramType=ColumnParameterMapping.ParamType.Integer, paramName='endHexX'),
                ColumnParameterMapping(columnName='end_hex_y', paramType=ColumnParameterMapping.ParamType.Integer, paramName='endHexY'),
                ColumnParameterMapping(columnName='start_offset_x', paramType=ColumnParameterMapping.ParamType.Integer, paramName='startOffsetX'),
                ColumnParameterMapping(columnName='start_offset_y', paramType=ColumnParameterMapping.ParamType.Integer, paramName='startOffsetY'),
                ColumnParameterMapping(columnName='end_offset_x', paramType=ColumnParameterMapping.ParamType.Integer, paramName='endOffsetX'),
                ColumnParameterMapping(columnName='end_offset_y', paramType=ColumnParameterMapping.ParamType.Integer, paramName='endOffsetY'),
                ColumnParameterMapping(columnName='type', paramType=ColumnParameterMapping.ParamType.String, paramName='type'),
                ColumnParameterMapping(columnName='style', paramType=ColumnParameterMapping.ParamType.String, paramName='style'),
                ColumnParameterMapping(columnName='colour', paramType=ColumnParameterMapping.ParamType.String, paramName='colour'),
                ColumnParameterMapping(columnName='width', paramType=ColumnParameterMapping.ParamType.Float, paramName='width'),
                ColumnParameterMapping(columnName='allegiance_id', paramType=ColumnParameterMapping.ParamType.String, paramName='allegianceId')])

    def _createBorderTables(self, cursor: sqlite3.Cursor) -> None:
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

        hexesMapping = RawTableMapping(
            tableName=UniverseDb._BorderHexesTableName,
            columnNames=['hex_x', 'hex_y'])
        self._objectTypeToTableMapping[multiverse.DbBorder] = ObjectTableMapping(
            tableName=UniverseDb._BordersTableName,
            objectType=multiverse.DbBorder,
            parameters=[
                ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                ColumnParameterMapping(columnName='sector_id', paramType=ColumnParameterMapping.ParamType.String, paramName='sectorId'),
                SubTableParameterMapping(table=hexesMapping, parentColumnName='border_id', initParam='hexes'),
                ColumnParameterMapping(columnName='allegiance_id', paramType=ColumnParameterMapping.ParamType.String, paramName='allegianceId'),
                ColumnParameterMapping(columnName='style', paramType=ColumnParameterMapping.ParamType.String, paramName='style'),
                ColumnParameterMapping(columnName='colour', paramType=ColumnParameterMapping.ParamType.String, paramName='colour'),
                ColumnParameterMapping(columnName='label', paramType=ColumnParameterMapping.ParamType.String, paramName='label'),
                ColumnParameterMapping(columnName='label_x', paramType=ColumnParameterMapping.ParamType.Float, paramName='labelWorldX'),
                ColumnParameterMapping(columnName='label_y', paramType=ColumnParameterMapping.ParamType.Float, paramName='labelWorldY'),
                ColumnParameterMapping(columnName='show_label', paramType=ColumnParameterMapping.ParamType.Boolean, paramName='showLabel'),
                ColumnParameterMapping(columnName='wrap_label', paramType=ColumnParameterMapping.ParamType.Boolean, paramName='wrapLabel')])

    def _createRegionTables(self, cursor: sqlite3.Cursor) -> None:
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

        hexesMapping = RawTableMapping(
            tableName=UniverseDb._RegionHexesTableName,
            columnNames=['hex_x', 'hex_y'])
        self._objectTypeToTableMapping[multiverse.DbRegion] = ObjectTableMapping(
            tableName=UniverseDb._RegionsTableName,
            objectType=multiverse.DbRegion,
            parameters=[
                ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                ColumnParameterMapping(columnName='sector_id', paramType=ColumnParameterMapping.ParamType.String, paramName='sectorId'),
                SubTableParameterMapping(table=hexesMapping, parentColumnName='region_id', initParam='hexes'),
                ColumnParameterMapping(columnName='colour', paramType=ColumnParameterMapping.ParamType.String, paramName='colour'),
                ColumnParameterMapping(columnName='label', paramType=ColumnParameterMapping.ParamType.String, paramName='label'),
                ColumnParameterMapping(columnName='label_x', paramType=ColumnParameterMapping.ParamType.Float, paramName='labelWorldX'),
                ColumnParameterMapping(columnName='label_y', paramType=ColumnParameterMapping.ParamType.Float, paramName='labelWorldY'),
                ColumnParameterMapping(columnName='show_label', paramType=ColumnParameterMapping.ParamType.Boolean, paramName='showLabel'),
                ColumnParameterMapping(columnName='wrap_label', paramType=ColumnParameterMapping.ParamType.Boolean, paramName='wrapLabel')])

    def _createMapLabelTables(self, cursor: sqlite3.Cursor) -> None:
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

        self._objectTypeToTableMapping[multiverse.DbMapLabel] = ObjectTableMapping(
            tableName=UniverseDb._MapLabelsTableName,
            objectType=multiverse.DbMapLabel,
            parameters=[
                ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                ColumnParameterMapping(columnName='text', paramType=ColumnParameterMapping.ParamType.String, paramName='text'),
                ColumnParameterMapping(columnName='x', paramType=ColumnParameterMapping.ParamType.Float, paramName='worldX'),
                ColumnParameterMapping(columnName='y', paramType=ColumnParameterMapping.ParamType.Float, paramName='worldY'),
                ColumnParameterMapping(columnName='layer', paramType=ColumnParameterMapping.ParamType.String, paramName='layer'),
                ColumnParameterMapping(columnName='alignment', paramType=ColumnParameterMapping.ParamType.String, paramName='alignment'),
                ColumnParameterMapping(columnName='colour', paramType=ColumnParameterMapping.ParamType.String, paramName='colour'),
                ColumnParameterMapping(columnName='size', paramType=ColumnParameterMapping.ParamType.String, paramName='size'),
                ColumnParameterMapping(columnName='rotation', paramType=ColumnParameterMapping.ParamType.Float, paramName='rotation')])

    def _createMapVectorTables(self, cursor: sqlite3.Cursor) -> None:
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

        pointsMapping = RawTableMapping(
            tableName=UniverseDb._MapVectorPointsTableName,
            columnNames=['x', 'y'])
        self._objectTypeToTableMapping[multiverse.DbMapVector] = ObjectTableMapping(
            tableName=UniverseDb._MapVectorsTableName,
            objectType=multiverse.DbMapVector,
            parameters=[
                ColumnParameterMapping(columnName='id', paramType=ColumnParameterMapping.ParamType.String, paramName='id'),
                SubTableParameterMapping(table=pointsMapping, parentColumnName='vector_id', initParam='points'),
                ColumnParameterMapping(columnName='layer', paramType=ColumnParameterMapping.ParamType.String, paramName='layer'),
                ColumnParameterMapping(columnName='closed', paramType=ColumnParameterMapping.ParamType.Boolean, paramName='isClosed')])

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

    def _findUsedTables(
            self,
            tableMapping: TableMapping
            ) -> typing.Set[str]:
        usedTables: typing.Set[str] = set()
        usedTables.add(tableMapping.tableName())
        if isinstance(tableMapping, ObjectTableMapping):
            for paramMapping in tableMapping.parameters():
                if isinstance(paramMapping, SubTableParameterMapping):
                    usedTables.update(self._findUsedTables(tableMapping=paramMapping.table()))

            if tableMapping.deriveObjects():
                for derivedMapping in tableMapping.deriveObjects():
                    usedTables.add(derivedMapping.tableName())

                    for paramMapping in derivedMapping.parameters():
                        if isinstance(paramMapping, SubTableParameterMapping):
                            usedTables.update(self._findUsedTables(tableMapping=paramMapping.table()))

        return usedTables

    def _loadTableRows(
            self,
            cursor: sqlite3.Cursor,
            tableName: str,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[typing.Dict[
                str, # Column Name
                typing.Any
                ]]:
        if progress is None:
            # IF there is no progress reporting just return all rows as a single operation
            return self._database.select(
                cursor=cursor,
                tableName=tableName)

        rowCount = self._database.rowCount(
            cursor=cursor,
            tableName=tableName)
        if not rowCount:
            if progress is not None:
                progress.complete()
            return

        chunkSize = 50000
        chunkCount = math.ceil(rowCount / chunkSize)

        localProgress = progress.createChild(weight=1, steps=chunkCount)

        rows = []
        for chunkIndex in range(chunkCount):
            rows.extend(self._database.select(
                cursor=cursor,
                tableName=tableName,
                limit=chunkSize,
                offset=chunkIndex * chunkSize))

            localProgress.advance()

        return rows

    @typing.overload
    def _mapTableToObjects(
            self,
            tableMapping: ObjectTableMapping,
            tableNameToRows: typing.Dict[
                str, # Table Name
                typing.List[typing.Dict[
                    str, # Column Name
                    typing.Any]]],
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbObject]: ...
    @typing.overload
    def _mapTableToObjects(
            self,
            tableMapping: ObjectTableMapping,
            tableNameToRows: typing.Dict[
                str, # Table Name
                typing.List[typing.Dict[
                    str, # Column Name
                    typing.Any]]],
            parentColumnName: typing.Literal[None],
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbObject]: ...
    @typing.overload
    def _mapTableToObjects(
            self,
            tableMapping: ObjectTableMapping,
            tableNameToRows: typing.Dict[
                str, # Table Name
                typing.List[typing.Dict[
                    str, # Column Name
                    typing.Any]]],
            parentColumnName: str,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.Dict[
                    str, # Parent column value
                    typing.List[multiverse.DbObject]]: ...

    def _mapTableToObjects(
            self,
            tableMapping: ObjectTableMapping,
            # If parentColumnName not None a dict is returned mapping this value to lists of the object type
            tableNameToRows: typing.Optional[typing.Dict[
                str, # Table Name
                typing.List[typing.Dict[
                    str, # Column Name
                    typing.Any]]]],
            parentColumnName: typing.Optional[str] = None,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.Union[
                typing.List[multiverse.DbObject],
                typing.Dict[
                    str, # Parent id
                    typing.List[multiverse.DbObject]]]:
        tableRows = tableNameToRows[tableMapping.tableName()]
        rowCount = len(tableRows)
        if not rowCount:
            if progress is not None:
                progress.complete()
            return

        taskCount = 1
        for paramMapping in tableMapping.parameters():
            if isinstance(paramMapping, SubTableParameterMapping):
                taskCount += 1

        if tableMapping.deriveObjects():
            for derivedMapping in tableMapping.deriveObjects():
                for paramMapping in derivedMapping.parameters():
                    if isinstance(paramMapping, SubTableParameterMapping):
                        taskCount += 1
        taskWeight = 1 / taskCount

        initParamNameToParentRows: typing.Dict[
            str, # __init__ param name
            typing.Union[
                typing.Dict[
                    str, # Parent id
                    typing.List[typing.List[multiverse.DbObject]]],
                typing.Dict[
                    str, # Parent id
                    typing.List[typing.Tuple[typing.Any, ...]]]
            ]]= {}
        for paramMapping in tableMapping.parameters():
            if not isinstance(paramMapping, SubTableParameterMapping):
                continue

            if isinstance(paramMapping.table(), ObjectTableMapping):
                initParamNameToParentRows[paramMapping.paramName()] = self._mapTableToObjects(
                    tableMapping=paramMapping.table(),
                    parentColumnName=paramMapping.parentColumnName(),
                    tableNameToRows=tableNameToRows,
                    progress=progress.createChild(weight=taskWeight) if progress is not None else None)
            elif isinstance(paramMapping.table(), RawTableMapping):
                initParamNameToParentRows[paramMapping.paramName()] = self._mapTableToRaw(
                    tableMapping=paramMapping.table(),
                    parentColumnName=paramMapping.parentColumnName(),
                    tableNameToRows=tableNameToRows,
                    progress=progress.createChild(weight=taskWeight) if progress is not None else None)
            else:
                # TODO: Do something
                pass

        baseIdToDerivedObjectRows: typing.Optional[typing.Dict[
            str, # Base Id
            typing.Tuple[
                DerivedObjectMapping,
                typing.Dict[
                    str, # Column Name
                    typing.Any]]]] = None
        derivedObjectToInitParams: typing.Optional[typing.Dict[
            typing.Type[multiverse.DbObject],
            typing.Dict[
                str, # __init__ param name
                typing.Union[
                    typing.Dict[
                        str, # Parent id
                        typing.List[typing.List[multiverse.DbObject]]],
                    typing.Dict[
                        str, # Parent id
                        typing.List[typing.Tuple[typing.Any, ...]]]
                ]]]] = None
        if tableMapping.deriveObjects():
            baseIdToDerivedObjectRows = {}
            derivedObjectToInitParams = {}
            for derivedMapping in tableMapping.deriveObjects():
                derivedRows = tableNameToRows[derivedMapping.tableName()]
                for row in derivedRows:
                    baseId = row[derivedMapping.baseColumnName()]
                    baseIdToDerivedObjectRows[baseId] = (derivedMapping, row)

                derivedInitParams: typing.Dict[
                    str, # __init__ param name
                    typing.Union[
                        typing.Dict[
                            str, # Parent id
                            typing.List[typing.List[multiverse.DbObject]]],
                        typing.Dict[
                            str, # Parent id
                            typing.List[typing.Tuple[typing.Any, ...]]]
                    ]] = {}
                derivedObjectToInitParams[derivedMapping.objectType()] = derivedInitParams
                for paramMapping in derivedMapping.parameters():
                    if not isinstance(paramMapping, SubTableParameterMapping):
                        continue

                    if isinstance(paramMapping.table(), ObjectTableMapping):
                        derivedInitParams[paramMapping.paramName()] = self._mapTableToObjects(
                            tableMapping=paramMapping.table(),
                            parentColumnName=paramMapping.parentColumnName(),
                            tableNameToRows=tableNameToRows,
                            progress=progress.createChild(weight=taskWeight) if progress is not None else None)
                    elif isinstance(paramMapping.table(), RawTableMapping):
                        derivedInitParams[paramMapping.paramName()] = self._mapTableToRaw(
                            tableMapping=paramMapping.table(),
                            parentColumnName=paramMapping.parentColumnName(),
                            tableNameToRows=tableNameToRows,
                            progress=progress.createChild(weight=taskWeight) if progress is not None else None)
                    else:
                        # TODO: Do something
                        pass

        chunkSize = 1000
        chunkCount = math.ceil(rowCount / chunkSize)
        localProgress = progress.createChild(weight=taskWeight, steps=chunkCount) if progress is not None else None

        objects: typing.Union[
            typing.List[multiverse.DbObject],
            typing.Dict[
                str, # Parent id
                typing.List[multiverse.DbObject]]] = [] if parentColumnName is None else {}
        for chunk in range(chunkCount):
            index = chunk * chunkSize
            limit = min(index + chunkSize, rowCount)
            while index < limit:
                row = tableRows[index]
                index += 1

                objectId = row['id']
                objectType = tableMapping.objectType()
                initParams: typing.Mapping[
                    str, # __init__ parameter name
                    typing.Any # __init__ parameter value
                    ] = {}
                for paramMapping in tableMapping.parameters():
                    if isinstance(paramMapping, ColumnParameterMapping):
                        value = row[paramMapping.columnName()]
                        if value is not None and paramMapping.paramType() is ColumnParameterMapping.ParamType.Boolean:
                            value = bool(value)
                        initParams[paramMapping.paramName()] = value
                    elif isinstance(paramMapping, SubTableParameterMapping):
                        if paramMapping.parentColumnName() is None:
                            initParams[paramMapping.paramName()] = initParamNameToParentRows[paramMapping.paramName()]
                        else:
                            initParams[paramMapping.paramName()] = initParamNameToParentRows[paramMapping.paramName()].get(objectId)

                if tableMapping.deriveObjects():
                    derivedMapping, derivedRow = baseIdToDerivedObjectRows[objectId]
                    objectType = derivedMapping.objectType()

                    derivedInitParamNameToParentRows = derivedObjectToInitParams[objectType]
                    for paramMapping in derivedMapping.parameters():
                        if isinstance(paramMapping, ColumnParameterMapping):
                            value = derivedRow[paramMapping.columnName()]
                            if value is not None and paramMapping.paramType() is ColumnParameterMapping.ParamType.Boolean:
                                value = bool(value)
                            initParams[paramMapping.paramName()] = value
                        elif isinstance(paramMapping, SubTableParameterMapping):
                            if paramMapping.parentColumnName() is None:
                                initParams[paramMapping.paramName()] = derivedInitParamNameToParentRows[paramMapping.paramName()]
                            else:
                                initParams[paramMapping.paramName()] = derivedInitParamNameToParentRows[paramMapping.paramName()].get(objectId)

                obj = objectType(**initParams)
                if parentColumnName is None:
                    objects.append(obj)
                else:
                    parentId = row[parentColumnName]
                    objectList = objects.get(parentId)
                    if objectList is None:
                        objectList = []
                        objects[parentId] = objectList
                    objectList.append(obj)

            if localProgress is not None:
                localProgress.advance()

        return objects

    @typing.overload
    def _mapTableToRaw(
            self,
            tableMapping: RawTableMapping,
            tableNameToRows: typing.Dict[
                str, # Table Name
                typing.List[typing.Dict[
                    str, # Column Name
                    typing.Any]]],
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[typing.Tuple[typing.Any, ...]]: ...
    @typing.overload
    def _mapTableToRaw(
            self,
            tableMapping: RawTableMapping,
            tableNameToRows: typing.Dict[
                str, # Table Name
                typing.List[typing.Dict[
                    str, # Column Name
                    typing.Any]]],
            parentColumnName: typing.Literal[None],
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[typing.Tuple[typing.Any, ...]]: ...
    @typing.overload
    def _mapTableToRaw(
            self,
            tableMapping: RawTableMapping,
            tableNameToRows: typing.Dict[
                str, # Table Name
                typing.List[typing.Dict[
                    str, # Column Name
                    typing.Any]]],
            parentColumnName: str,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.Dict[
                    str, # Parent column value
                    typing.List[typing.Tuple[typing.Any, ...]]]: ...

    def _mapTableToRaw(
            self,
            tableMapping: RawTableMapping,
            # If parentColumnName not None a dict is returned mapping this value to lists of the object type
            tableNameToRows: typing.Dict[
                str, # Table Name
                typing.List[typing.Dict[
                    str, # Column Name
                    typing.Any]]],
            parentColumnName: typing.Optional[str] = None,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.Union[
                typing.List[typing.Tuple[typing.Any, ...]],
                typing.Dict[
                    str, # Parent id
                    typing.List[typing.Tuple[typing.Any, ...]]]]:
        tableRows = tableNameToRows[tableMapping.tableName()]
        rowCount = len(tableRows)
        if not rowCount:
            if progress is not None:
                progress.complete()
            return

        chunkSize = 1000
        chunkCount = math.ceil(rowCount / chunkSize)
        localProgress = progress.createChild(weight=1, steps=chunkCount) if progress is not None else None

        tuples: typing.Union[
            typing.List[typing.Tuple[typing.Any, ...]],
            typing.Dict[
                str, # Parent Id
                typing.List[typing.Tuple[typing.Any, ...]]]] = [] if parentColumnName is None else {}

        for chunk in range(chunkCount):
            index = chunk * chunkSize
            limit = min(index + chunkSize, rowCount)
            while index < limit:
                row = tableRows[index]
                index += 1

                if parentColumnName is None:
                    tuples.append(tuple(row[n] for n in tableMapping.columnNames()))
                else:
                    parentId = row[parentColumnName]
                    tupleList = tuples.get(parentId)
                    if tupleList is None:
                        tupleList = []
                        tuples[parentId] = tupleList
                    tupleList.append(tuple(row[n] for n in tableMapping.columnNames()))

            if localProgress is not None:
                localProgress.advance()

        return tuples

    @typing.overload
    def _loadTableObjects(
            self,
            cursor: sqlite3.Cursor,
            tableMapping: ObjectTableMapping,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbObject]: ...
    @typing.overload
    def _loadTableObjects(
            self,
            cursor: sqlite3.Cursor,
            tableMapping: RawTableMapping,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[typing.Tuple[typing.Any, ...]]: ...

    def _loadTableObjects(
            self,
            cursor: sqlite3.Cursor,
            tableMapping: TableMapping,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.Union[
                typing.List[multiverse.DbObject],
                typing.List[typing.Tuple[typing.Any, ...]]]:
        tablesToLoad = self._findUsedTables(tableMapping=tableMapping)

        taskCount = 1
        if tablesToLoad:
            taskCount += len(tablesToLoad)
        taskWeight = 1 / taskCount if taskCount else 1

        if tablesToLoad:
            tableNameToRows = {}
            for tableName in tablesToLoad:
                tableNameToRows[tableName] = self._loadTableRows(
                    cursor=cursor,
                    tableName=tableName,
                    progress=progress.createChild(weight=taskWeight) if progress is not None else None)

        if isinstance(tableMapping, ObjectTableMapping):
            return self._mapTableToObjects(
                tableMapping=tableMapping,
                tableNameToRows=tableNameToRows,
                progress=progress.createChild(weight=taskWeight) if progress is not None else None)
        elif isinstance(tableMapping, RawTableMapping):
            return self._mapTableToRaw(
                tableMapping=tableMapping,
                tableNameToRows=tableNameToRows,
                progress=progress.createChild(weight=taskWeight) if progress is not None else None)
        else:
            # TODO: Log something
            pass

    def _mapObjectsToTable(
            self,
            tableMapping: ObjectTableMapping,
            objects: typing.Collection[multiverse.DbObject],
            tableNameToRows: typing.OrderedDict[
                str,
                typing.List[typing.Dict[
                    str, # Column Name
                    typing.Any]]], # Column value
            parentColumnName: typing.Optional[str] = None,
            parentColumnValue: typing.Optional[str] = None
            ) -> None:
        if not objects:
            return

        # NOTE: Add the rows to the table mapping before mapping any sub tables
        # as we want the the tables to be added to tableNameToRows so parents
        # are before children.
        objectRows = tableNameToRows.get(tableMapping.tableName())
        if objectRows is None:
            objectRows = []
            tableNameToRows[tableMapping.tableName()] = objectRows

        derivedObjectMappings = tableMapping.deriveObjects()
        derivedObjectTypeToObjects: typing.Dict[
            typing.Type[multiverse.DbObject],
            typing.List[multiverse.DbObject]
            ] = {}
        for obj in objects:
            if derivedObjectMappings:
                objectType = type(obj)
                derivedObjects = derivedObjectTypeToObjects.get(objectType)
                if derivedObjects is None:
                    derivedObjects = []
                    derivedObjectTypeToObjects[objectType] = derivedObjects
                derivedObjects.append(obj)

        isDerivedObject = isinstance(tableMapping, DerivedObjectMapping)
        for obj in objects:
            row = {}
            if isDerivedObject:
                row[tableMapping.baseColumnName()] = obj.id()
            if parentColumnName is not None:
                row[parentColumnName] = parentColumnValue
            for paramMapping in tableMapping.parameters():
                function = getattr(obj, paramMapping.paramName())
                value = function()

                if isinstance(paramMapping, ColumnParameterMapping):
                    if value is not None and paramMapping.paramType() is ColumnParameterMapping.ParamType.Boolean:
                        value = 1 if value else 0
                    row[paramMapping.columnName()] = value
                elif isinstance(paramMapping, SubTableParameterMapping):
                    subTableMapping = paramMapping.table()
                    if isinstance(subTableMapping, ObjectTableMapping):
                        self._mapObjectsToTable(
                            tableMapping=subTableMapping,
                            objects=value,
                            tableNameToRows=tableNameToRows,
                            parentColumnName=paramMapping.parentColumnName(),
                            parentColumnValue=obj.id())
                    elif isinstance(subTableMapping, RawTableMapping):
                        self._mapRawToTable(
                            tableMapping=subTableMapping,
                            objects=value,
                            tableNameToRows=tableNameToRows,
                            parentColumnName=paramMapping.parentColumnName(),
                            parentColumnValue=obj.id())
                    else:
                        # TODO: Better exception message
                        raise RuntimeError('Unknown sub table mapping type')

            objectRows.append(row)

        if derivedObjectTypeToObjects:
            objectTypeToDerivedMapping = {m.objectType(): m for m in derivedObjectMappings}
            for objectType, derivedObjects in derivedObjectTypeToObjects.items():
                derivedMapping = objectTypeToDerivedMapping[objectType]
                self._mapObjectsToTable(
                    tableMapping=derivedMapping,
                    objects=derivedObjects,
                    tableNameToRows=tableNameToRows)

    def _mapRawToTable(
            self,
            tableMapping: RawTableMapping,
            objects: typing.Collection[multiverse.DbObject],
            tableNameToRows: typing.OrderedDict[
                str,
                typing.List[typing.Dict[
                    str, # Column Name
                    typing.Any]]], # Column value
            parentColumnName: typing.Optional[str] = None,
            parentColumnValue: typing.Optional[str] = None
            ) -> None:
        if not objects:
            return

        # NOTE: Add the rows to the table mapping before mapping any sub tables
        # as we want the the tables to be added to tableNameToRows so parents
        # are before children.
        tableRows = tableNameToRows.get(tableMapping.tableName())
        if tableRows is None:
            tableRows = []
            tableNameToRows[tableMapping.tableName()] = tableRows

        for obj in objects:
            row = {}
            if parentColumnName is not None:
                row[parentColumnName] = parentColumnValue
            for index, columnName in enumerate(tableMapping.columnNames()):
                row[columnName] = obj[index]
            tableRows.append(row)

    def _saveTableRows(
            self,
            cursor: sqlite3.Cursor,
            tableName: str,
            rows: typing.Collection[typing.Mapping[
                str, # Column Name
                typing.Any]], # Column Value
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if not rows:
            if progress is not None:
                progress.complete()
            return

        if progress is None:
            # If progress reporting is not required, just write all rows as single operation
            self._database.insertMany(
                cursor=cursor,
                tableName=tableName,
                rows=rows,
                replaceIfExists=True)
            return

        rowCount = len(rows)
        chunkSize = rowCount
        if progress is not None:
            chunkSize = 50000
            localProgress = progress.createChild(
                weight=1,
                steps=math.ceil(rowCount / chunkSize))

        for chunkStart in range(0, rowCount, chunkSize):
            chunkRows = itertools.islice(rows, chunkStart, chunkStart + chunkSize)
            self._database.insertMany(
                cursor=cursor,
                tableName=tableName,
                rows=chunkRows,
                replaceIfExists=True)
            localProgress.advance()

    def _saveTableObjects(
            self,
            cursor: sqlite3.Cursor,
            tableMapping: TableMapping,
            objects: typing.Union[
                typing.Collection[multiverse.DbObject],
                typing.Collection[typing.Tuple[typing.Any, ...]]],
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if not objects:
            progress.complete()
            return

        usedTables = self._findUsedTables(tableMapping=tableMapping)

        taskCount = 1 + len(usedTables)
        taskWeight = 1 / taskCount

        objectCount = len(objects)
        chunkSize = objectCount
        localProgress = None
        if progress is not None:
            chunkSize = 10000
            chunkCount = math.ceil(objectCount / chunkSize)
            localProgress = progress.createChild(weight=taskWeight, steps=chunkCount)

        # NOTE: It's important tableNameToRows is an ordered dict as the code adds
        # the tables in dependency order (parents before children) so rows can be
        # added to parent tables before rows that may depend on them are added to child
        # tables
        tableNameToRows: typing.OrderedDict[
            TableMapping,
            typing.List[typing.Dict[
                str, # Column Name
                typing.Any]]] = collections.OrderedDict()

        for chunkStart in range(0, objectCount, chunkSize):
            chunkObjects = objects[chunkStart:chunkStart + chunkSize]
            if isinstance(tableMapping, ObjectTableMapping):
                self._mapObjectsToTable(
                    tableMapping=tableMapping,
                    objects=chunkObjects,
                    tableNameToRows=tableNameToRows)
            elif isinstance(tableMapping, RawTableMapping):
                self._mapRawToTable(
                    tableMapping=tableMapping,
                    objects=chunkObjects,
                    tableNameToRows=tableNameToRows)
            else:
                # TODO: Log something
                pass

            if localProgress is not None:
                localProgress.advance()

        for tableName, rows in tableNameToRows.items():
            self._saveTableRows(
                cursor=cursor,
                tableName=tableName,
                rows=rows,
                progress=progress.createChild(weight=taskWeight) if progress is not None else None)

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

    def _loadAllegiances(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbAllegiance]:
        logging.debug(f'UniverseDb loading allegiances from universe {self._universePath!r}')

        return self._loadTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbAllegiance],
            progress=progress)

    def _saveAllegiances(
            self,
            cursor: sqlite3.Cursor,
            allegiances: typing.Collection[multiverse.DbAllegiance],
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if not allegiances:
            return

        for allegiance in allegiances:
            logging.debug(f'UniverseDb saving allegiance {allegiance.id()!r} to universe {self._universePath!r}')

        self._saveTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbAllegiance],
            objects=allegiances,
            progress=progress)

    def _deleteAllegiances(
            self,
            cursor: sqlite3.Cursor,
            allegianceIds: typing.Collection[str]
            ) -> None:
        if not allegianceIds:
            return

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

    def _loadSophonts(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbSophont]:
        logging.debug(f'UniverseDb loading sophonts from universe {self._universePath!r}')

        return self._loadTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbSophont],
            progress=progress)

    def _saveSophonts(
            self,
            cursor: sqlite3.Cursor,
            sophonts: typing.Collection[multiverse.DbSophont],
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if not sophonts:
            return

        for sophont in sophonts:
            logging.debug(f'UniverseDb saving sophont {sophont.id()!r} to universe {self._universePath!r}')

        self._saveTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbSophont],
            objects=sophonts,
            progress=progress)

    def _deleteSophonts(
            self,
            cursor: sqlite3.Cursor,
            sophontIds: typing.Collection[str]
            ) -> None:
        if not sophontIds:
            return

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

    def _loadSectors(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbSector]:
        logging.debug(f'UniverseDb loading sectors from universe {self._universePath!r}')

        return self._loadTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbSector],
            progress=progress)

    def _saveSectors(
            self,
            cursor: sqlite3.Cursor,
            sectors: typing.Collection[multiverse.DbSector],
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if not sectors:
            return

        for sector in sectors:
            logging.debug(f'UniverseDb saving sophont {sector.id()!r} to universe {self._universePath!r}')

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

        self._saveTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbSector],
            objects=sectors,
            progress=progress)

    def _deleteSectors(
            self,
            cursor: sqlite3.Cursor,
            sectorIds: typing.Collection[str]
            ) -> None:
        if not sectorIds:
            return

        parameters = []
        for sectorId in sectorIds:
            logging.debug(f'UniverseDb deleting sector {sectorId!r} from universe {self._universePath!r}')
            parameters.append((sectorId,))

        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._SectorsTableName,
            where='id = ?',
            parameters=parameters)

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

    def _loadSystems(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbSystem]:
        logging.debug(f'UniverseDb loading systems from universe {self._universePath!r}')

        return self._loadTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbSystem],
            progress=progress)

    def _saveSystems(
            self,
            cursor: sqlite3.Cursor,
            systems: typing.Collection[multiverse.DbSystem],
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if not systems:
            return

        for system in systems:
            logging.debug(f'UniverseDb saving system {system.id()!r} to universe {self._universePath!r}')

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

        self._saveTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbSystem],
            objects=systems,
            progress=progress)

    def _deleteSystems(
            self,
            cursor: sqlite3.Cursor,
            systemIds: typing.Collection[str]
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

    #    ███████████                        █████
    #   ░░███░░░░░███                      ░░███
    #    ░███    ░███   ██████  █████ ████ ███████    ██████   █████
    #    ░██████████   ███░░███░░███ ░███ ░░░███░    ███░░███ ███░░
    #    ░███░░░░░███ ░███ ░███ ░███ ░███   ░███    ░███████ ░░█████
    #    ░███    ░███ ░███ ░███ ░███ ░███   ░███ ███░███░░░   ░░░░███
    #    █████   █████░░██████  ░░████████  ░░█████ ░░██████  ██████
    #   ░░░░░   ░░░░░  ░░░░░░    ░░░░░░░░    ░░░░░   ░░░░░░  ░░░░░░

    def _loadRoutes(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbRoute]:
        logging.debug(f'UniverseDb loading routes from universe {self._universePath!r}')

        return self._loadTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbRoute],
            progress=progress)

    def _saveRoutes(
            self,
            cursor: sqlite3.Cursor,
            routes: typing.Collection[multiverse.DbRoute],
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if not routes:
            return

        for route in routes:
            logging.debug(f'UniverseDb saving route {route.id()!r} to universe {self._universePath!r}')

        self._saveTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbRoute],
            objects=routes,
            progress=progress)

    def _deleteRoutes(
            self,
            cursor: sqlite3.Cursor,
            routeIds: typing.Collection[str]
            ) -> None:
        parameters = []
        for routeId in routeIds:
            logging.debug(f'UniverseDb deleting route {routeId!r} from universe {self._universePath!r}')
            parameters.append((routeId,))

        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._RoutesTableName,
            where='id = ?',
            parameters=parameters)

    #    ███████████                         █████
    #   ░░███░░░░░███                       ░░███
    #    ░███    ░███  ██████  ████████   ███████   ██████  ████████   █████
    #    ░██████████  ███░░███░░███░░███ ███░░███  ███░░███░░███░░███ ███░░
    #    ░███░░░░░███░███ ░███ ░███ ░░░ ░███ ░███ ░███████  ░███ ░░░ ░░█████
    #    ░███    ░███░███ ░███ ░███     ░███ ░███ ░███░░░   ░███      ░░░░███
    #    ███████████ ░░██████  █████    ░░████████░░██████  █████     ██████
    #   ░░░░░░░░░░░   ░░░░░░  ░░░░░      ░░░░░░░░  ░░░░░░  ░░░░░     ░░░░░░

    def _loadBorders(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbBorder]:
        logging.debug(f'UniverseDb loading borders from universe {self._universePath!r}')

        return self._loadTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbBorder],
            progress=progress)

    def _insertBorders(
            self,
            cursor: sqlite3.Cursor,
            borders: typing.Collection[multiverse.DbBorder],
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if not borders:
            return

        for border in borders:
            logging.debug(f'UniverseDb saving border {border.id()!r} to universe {self._universePath!r}')

        # Any existing border with the same id as a border being saved should
        # be deleted before the new borders are inserted. This is needed so any
        # points associated with the existing border will be deleted before adding
        # the points for the new border
        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._BordersTableName,
            where='id == ?',
            parameters=((b.id(),) for b in borders))

        self._saveTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbBorder],
            objects=borders,
            progress=progress)

    def _deleteBorders(
            self,
            cursor: sqlite3.Cursor,
            borderIds: typing.Collection[str]
            ) -> None:
        if not borderIds:
            return

        parameters = []
        for borderId in borderIds:
            logging.debug(f'UniverseDb deleting border {borderId!r} from universe {self._universePath!r}')
            parameters.append((borderId,))

        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._BordersTableName,
            where='id = ?',
            parameters=parameters)

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

    def _loadRegions(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbRegion]:
        logging.debug(f'UniverseDb loading regions from universe {self._universePath!r}')

        return self._loadTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbRegion],
            progress=progress)

    def _insertRegions(
            self,
            cursor: sqlite3.Cursor,
            regions: typing.Collection[multiverse.DbRegion],
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if not regions:
            return

        for region in regions:
            logging.debug(f'UniverseDb saving region {region.id()!r} to universe {self._universePath!r}')

        # Any existing region with the same id as a region being saved should
        # be deleted before the new regions are inserted. This is needed so any
        # points associated with the existing region will be deleted before adding
        # the points for the new region
        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._RegionsTableName,
            where='id == ?',
            parameters=((r.id(),) for r in region))

        self._saveTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbRegion],
            objects=region,
            progress=progress)

    def _deleteRegions(
            self,
            cursor: sqlite3.Cursor,
            regionIds: typing.Collection[str]
            ) -> None:
        if not regionIds:
            return

        parameters = []
        for regionId in regionIds:
            logging.debug(f'UniverseDb deleting region {regionId!r} from universe {self._universePath!r}')
            parameters.append((regionId,))

        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._RegionsTableName,
            where='id = ?',
            parameters=parameters)

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

    def _loadMapLabels(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbMapLabel]:
        logging.debug(f'UniverseDb loading map labels from universe {self._universePath!r}')

        return self._loadTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbMapLabel],
            progress=progress)

    def _saveMapLabels(
            self,
            cursor: sqlite3.Cursor,
            labels: typing.Collection[multiverse.DbMapLabel],
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if not labels:
            return

        for label in labels:
            logging.debug(f'UniverseDb saving map label {label.id()!r} to universe {self._universePath!r}')

        self._saveTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbMapLabel],
            objects=labels,
            progress=progress)

    def _deleteMapLabels(
            self,
            cursor: sqlite3.Cursor,
            labelIds: typing.Collection[str]
            ) -> None:
        if not labelIds:
            return

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

    def _loadMapVectors(
            self,
            cursor: sqlite3.Cursor,
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> typing.List[multiverse.DbMapVector]:
        logging.debug(f'UniverseDb loading map vectors from universe {self._universePath!r}')

        return self._loadTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbMapVector],
            progress=progress)

    def _saveMapVectors(
            self,
            cursor: sqlite3.Cursor,
            vectors: typing.Collection[multiverse.DbMapVector],
            progress: typing.Optional[common.ProgressTracker] = None
            ) -> None:
        if not vectors:
            return

        # Any existing vector with the same id as a vector being saved should
        # be deleted before the new vectors are inserted. This is needed so any
        # points associated with the existing vector will be deleted before adding
        # the points for the new vector
        self._database.deleteMany(
            cursor=cursor,
            tableName=UniverseDb._MapVectorsTableName,
            where='id == ?',
            parameters=((v.id(),) for v in vectors))

        self._saveTableObjects(
            cursor=cursor,
            tableMapping=self._objectTypeToTableMapping[multiverse.DbMapVector],
            objects=vectors,
            progress=progress)

    def _deleteMapVectors(
            self,
            cursor: sqlite3.Cursor,
            vectorIds: typing.Collection[str]
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
