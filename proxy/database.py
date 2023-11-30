import aiosqlite
import datetime
import logging
import proxy
import typing

# This is the best page size based on the average size of tile blobs
# https://www.sqlite.org/intern-v-extern-blob.html
_SqlitePageSizeBytes = 8192

_MetadataTableName = 'metadata'

_CheckIfTableExistsQuery = 'SELECT name FROM sqlite_master WHERE type = "table" AND name = :table;'

# NOTE: Setting the page_size needs to be done before setting the journal_mode as
# it can't be changed after entering WAL mode
_SetPersistentPragmaScript = \
f"""
PRAGMA page_size = {_SqlitePageSizeBytes};
PRAGMA journal_mode = WAL;
"""

_CreateMetadataTableQuery = \
f"""
CREATE TABLE IF NOT EXISTS {_MetadataTableName} (
    key TEXT NOT NULL PRIMARY KEY,
    value TEXT NOT NULL);
"""

_ReadMetadataValueQuery = \
    f'SELECT value FROM {_MetadataTableName} WHERE key = :key;'

_WriteMetadataValueQuery = \
    f'INSERT OR REPLACE INTO {_MetadataTableName} VALUES (:key, :value);'

_DeleteMetadataValueQuery = \
    f'DELETE FROM {_MetadataTableName} WHERE key = :key;'

_DropTableQuery = f'DROP TABLE :table;'

_DatabaseTimestampFormat = '%Y-%m-%d %H:%M:%S.%f'

def stringToDbTimestamp(string: str) -> datetime.datetime:
    timestamp = datetime.datetime.strptime(
        string,
        _DatabaseTimestampFormat)
    return datetime.datetime.fromtimestamp(
        timestamp.timestamp(),
        tz=datetime.timezone.utc)

def dbTimestampToString(timestamp: datetime.datetime) -> str:
    return timestamp.strftime(_DatabaseTimestampFormat)

async def checkIfTableExistsAsync(
        connection: aiosqlite.Connection,
        tableName: str
        ) -> bool:
    async with connection.execute(_CheckIfTableExistsQuery, {'table': tableName}) as cursor:
        row = await cursor.fetchone()
        return row != None

async def readDbMetadataAsync(
        connection: aiosqlite.Connection,
        key: str,
        type: typing.Type[typing.Any],
        default: typing.Any = None
        ) -> None:
    queryArgs = {'key': key}
    async with connection.execute(_ReadMetadataValueQuery, queryArgs) as cursor:
        row = await cursor.fetchone()
        if row == None:
            return default

        if type == datetime.datetime:
            return stringToDbTimestamp(row[0])
        elif type == bool:
            return str(row[0]).lower() == 'true'
        return type(row[0])

async def writeDbMetadataAsync(
        connection: aiosqlite.Connection,
        key: str,
        value: typing.Any,
        commit = False
        ) -> None:
    if isinstance(value, datetime.datetime):
        value = dbTimestampToString(timestamp=value)

    queryArgs = {'key': key, 'value': str(value)}
    async with connection.execute(_WriteMetadataValueQuery, queryArgs):
        pass

    if commit:
        await connection.commit()

async def deleteDbMetadataAsync(
        connection: aiosqlite.Connection,
        key: str,
        commit: bool = False
        ) -> None:
    queryArgs = {'key': key}
    async with connection.execute(_DeleteMetadataValueQuery, queryArgs):
        pass
    
    if commit:
        await connection.commit()

async def createSchemaTableAsync(
        connection: aiosqlite.Connection,
        tableName: str,
        requiredSchema: int,
        createTableQuery: str,
        commit: bool = False
        ) -> None:
    schemaKey = tableName + '_schema'
    tableSchema = await proxy.readDbMetadataAsync(
        connection=connection,
        key=schemaKey,
        type=int,
        default=None)    
    tableExists = await proxy.checkIfTableExistsAsync(
        connection=connection,
        tableName=tableName)
    if tableSchema != requiredSchema:
        if tableExists:                    
            logging.info(
                'Deleting {table} due to schema version change from {old} to {new}'.format(
                    table=tableName,
                    old=tableSchema,
                    new=requiredSchema))
            # The database schema doesn't match the expected schema. Drop the tiles table
            # so it will be recreated with the correct structure.
            # NOTE: This query is generated differently to others as you can't parameters
            # for a DROP TABLE query
            async with connection.execute(f'DROP TABLE {tableName};'):
                pass
            tableExists = False

        # Write the new schema version to the database
        await proxy.writeDbMetadataAsync(
            connection=connection,
            key=schemaKey,
            value=requiredSchema)

    if not tableExists:
        logging.debug(f'Creating {tableName} table')
        async with connection.execute(createTableQuery):
            pass

    if commit:
        await connection.commit()        

class Database(object):
    def __init__(
            self,
            filePath: str
            ) -> None:
        self._filePath = filePath

    def filePath(self) -> str:
        return self._filePath

    async def initAsync(self) -> None:
        async with aiosqlite.connect(self._filePath) as connection:
            configTableExists = await proxy.checkIfTableExistsAsync(
                tableName=_MetadataTableName,
                connection=connection)
            if configTableExists:
                return
            
            logging.debug('Creating tile cache config table')

            async with connection.executescript(_SetPersistentPragmaScript):
                pass

            async with connection.execute(_CreateMetadataTableQuery):
                pass

            await connection.commit()

    async def connectAsync(
            self,
            pragmaQuery: typing.Optional[str] = None
            ) -> aiosqlite.Connection:
        connection = await aiosqlite.connect(self._filePath)
        if pragmaQuery is not None:
            try:
                async with connection.executescript(pragmaQuery):
                    pass
            except:
                await connection.close()
                raise

        return connection

