import database
import enum
import logging
import sqlite3
import typing

# TODO: Log messages etc need updated to not reference MultiverseDb

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
            minValue: typing.Optional[typing.Union[str, int, float]] = None,
            maxValue: typing.Optional[typing.Union[str, int, float]] = None
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

        if minValue is not None:
            if columnType is ColumnDef.ColumnType.Text:
                if not isinstance(minValue, str):
                    raise ValueError('Min value for Text column must be of type str')
            elif columnType is ColumnDef.ColumnType.Integer:
                if not isinstance(minValue, int):
                    raise ValueError('Min value for Integer column must be of type int')
            elif columnType is ColumnDef.ColumnType.Real:
                if not isinstance(minValue, (float, int)):
                    raise ValueError('Min value for Float column must be of type float or int')
            elif columnType is ColumnDef.ColumnType.Boolean:
                raise ValueError('Min value for is not allowed for Boolean columns')

        if maxValue is not None:
            if columnType is ColumnDef.ColumnType.Text:
                if not isinstance(maxValue, str):
                    raise ValueError('Max value for Text column must be of type str')
            elif columnType is ColumnDef.ColumnType.Integer:
                if not isinstance(maxValue, int):
                    raise ValueError('Max value for Integer column must be of type int')
            elif columnType is ColumnDef.ColumnType.Real:
                if not isinstance(maxValue, (float, int)):
                    raise ValueError('Max value for Float column must be of type float or int')
            elif columnType is ColumnDef.ColumnType.Boolean:
                raise ValueError('Max value for is not allowed for Boolean columns')

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
        self._minValue = minValue
        self._maxValue = maxValue

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

    def minValue(self) -> typing.Optional[typing.Union[str, int, float]]:
        return self._minValue

    def maxValue(self) -> typing.Optional[typing.Union[str, int, float]]:
        return self._maxValue

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

    def begin(self) -> 'SchemaDb.Transaction':
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

    def __enter__(self) -> 'Transaction':
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

class SchemaDb(object):
    _PragmaScript = """
        PRAGMA foreign_keys = ON;
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;
        PRAGMA cache_size = -400000;
        """

    _TableSchemaTableName = 'table_schemas'

    _MetadataTableName = 'metadata'
    _MetadataTableSchema = 1

    def __init__(self, dbPath: str) -> None:
        self._dbPath = dbPath

        self._initDatabase()

    def createTransaction(
            self,
            onCommitCallback: typing.Optional[typing.Callable[[], None]] = None,
            onRollbackCallback: typing.Optional[typing.Callable[[], None]] = None
            ) -> Transaction:
        connection = self._createConnection()
        return Transaction(
            connection=connection,
            onCommitCallback=onCommitCallback,
            onRollbackCallback=onRollbackCallback)

    def createTable(
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
                raise TableVersionException(
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
                minValue = column.minValue()
                maxValue = column.maxValue()
                isText = column.columnType() is ColumnDef.ColumnType.Text
                if minValue is not None and maxValue is not None:
                    sql += '  CHECK ({column} BETWEEN {min} AND {max}),\n'.format(
                        column=column.columnName(),
                        min=f'\'{minValue}\'' if isText else minValue,
                        max=f'\'{maxValue}\'' if isText else maxValue)
                elif minValue is not None:
                    sql += '  CHECK ({column} >= {min}),\n'.format(
                        column=column.columnName(),
                        min=f'\'{minValue}\'' if isText else minValue)
                elif maxValue is not None:
                    sql += '  CHECK ({column} <= {max}),\n'.format(
                        column=column.columnName(),
                        max=f'\'{maxValue}\'' if isText else maxValue)

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

    def vacuumDatabase(self) -> None:
        logging.debug('MultiverseDb vacuuming database')

        # NOTE: VACUUM can't be performed inside a transaction
        connection = self._createConnection()
        try:
            cursor = connection.cursor()
            cursor.execute('VACUUM;')
        finally:
            connection.close()

    def _initDatabase(self) -> None:
        connection = None
        cursor = None
        try:
            connection = self._createConnection()
            cursor = connection.cursor()
            cursor.execute('BEGIN;')

            # Create table schema table
            if not database.checkIfTableExists(
                    tableName=SchemaDb._TableSchemaTableName,
                    cursor=cursor):
                sql = """
                    CREATE TABLE IF NOT EXISTS {table} (
                        name TEXT PRIMARY KEY NOT NULL,
                        version INTEGER NOT NULL
                    );
                    """.format(table=SchemaDb._TableSchemaTableName)
                logging.info(f'MultiverseDb creating \'{SchemaDb._TableSchemaTableName}\' table')
                cursor.execute(sql)

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

    def _createConnection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._dbPath)
        logging.debug(f'MultiverseDb created new connection {connection} to \'{self._dbPath}\'')
        connection.executescript(SchemaDb._PragmaScript)
        # Uncomment this to have sqlite print the SQL that it executes
        #connection.set_trace_callback(print)
        return connection

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
            """.format(table=SchemaDb._TableSchemaTableName)
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
            """.format(table=SchemaDb._TableSchemaTableName)
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
