import common
import enum
import logging
import sqlite3
import threading
import typing
import uuid

class ObjectDbOperation(enum.Enum):
    Insert = 'insert'
    Update = 'update'
    Delete = 'delete'

class ObjectDbTriggerType(enum.Enum):
    Before = 'before'
    After = 'after'

class DatabaseEntity(object):
    def __init__(
            self,
            id: typing.Optional[str] = None
            ) -> None:
        super().__init__()
        self._id = id if id != None else str(uuid.uuid4())

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DatabaseEntity):
            return self._id == other._id
        return False

    def id(self) -> str:
        return self._id

    def setId(self, id: str) -> None:
        self._id = id

class DatabaseObject(DatabaseEntity):
    def __init__(
            self,
            id: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)

    def data(self) -> typing.Mapping[
            str,
            typing.Optional[typing.Union[bool, int, float, str, DatabaseEntity]]]:
        raise RuntimeError(f'{type(self)} is derived from DatabaseObject so must implement data')

    @staticmethod
    def defineObject() -> 'ObjectDef':
        raise RuntimeError(f'{__class__} is derived from DatabaseObject so must implement data')

    @staticmethod
    def createObject(
            id: str,
            data: typing.Mapping[
                str,
                typing.Optional[typing.Union[bool, int, float, str, DatabaseEntity]]]
            ) -> 'DatabaseObject':
        raise RuntimeError(f'{__class__} is derived from DatabaseObject so must implement data')

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DatabaseObject):
            return super().__eq__(other)
        return False

class DatabaseList(DatabaseEntity):
    def __init__(
            self,
            content: typing.Optional[typing.Iterable[typing.Union[bool, int, float, str, DatabaseEntity]]] = None,
            id: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id)
        self._content: typing.List[typing.Union[bool, int, float, str, DatabaseEntity]] = []
        if content:
            self.init(content=content)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DatabaseList):
            return super().__eq__(other) and \
                self._content == other._content
        return False

    def __iter__(self) -> typing.Iterator[typing.Union[bool, int, float, str, DatabaseEntity]]:
        return self._content.__iter__()

    def __next__(self) -> typing.Union[bool, int, float, str, DatabaseEntity]:
        return self._content.__next__()

    def __len__(self) -> int:
        return self._content.__len__()

    def __getitem__(self, index: int) -> typing.Union[bool, int, float, str, DatabaseEntity]:
        return self._content.__getitem__(index)

    def init(
            self,
            content: typing.Iterable[typing.Union[bool, int, float, str, DatabaseEntity]]
            ) -> None:
        self.clear()
        self._content.extend(content)

    def add(
            self,
            item: typing.Union[bool, int, float, str, DatabaseEntity]
            ) -> None:
        self._content.append(item)

    def insert(
            self,
            index: int,
            item: typing.Union[bool, int, float, str, DatabaseEntity]
            ) -> None:
        self._content.insert(index, item)

    def remove(
            self,
            index: int
            ) -> typing.Union[bool, int, float, str, DatabaseEntity]:
        item = self._content[index]
        del self._content[index]
        return item

    def removeById(self, id: str) -> None:
        for item in list(self._content):
            if isinstance(item, DatabaseEntity) and id == item.id():
                self._content.remove(item)

    def clear(self) -> None:
        self._content.clear()

class ParamDef(object):
    def __init__(
            self,
            columnName: str,
            columnType: typing.Type[typing.Any],
            isOptional: bool = False
            ) -> None:
        self._columnName = columnName
        self._columnType = columnType
        self._isOptional = isOptional

    def columnName(self) -> str:
        return self._columnName

    def columnType(self) -> typing.Type[typing.Any]:
        return self._columnType

    def isOptional(self) -> bool:
        return self._isOptional

class ObjectDef(object):
    def __init__(
            self,
            tableName: str,
            tableSchema: int,
            classType: typing.Type['DatabaseObject'],
            paramDefs: typing.Iterable[ParamDef],
            ) -> None:
        self._tableName = tableName
        self._tableSchema = tableSchema
        self._classType = classType
        self._paramDefs = paramDefs

    def tableName(self) -> str:
        return self._tableName

    def tableSchema(self) -> int:
        return self._tableSchema

    def classType(self) -> typing.Type['DatabaseObject']:
        return self._classType

    def paramDefs(self) -> typing.Iterable[ParamDef]:
        return self._paramDefs

class Transaction(object):
    def __init__(
            self,
            connection: sqlite3.Connection,
            beginCallback: typing.Callable[[sqlite3.Cursor], None],
            endCallback: typing.Callable[[sqlite3.Cursor], None],
            rollbackCallback: typing.Callable[[sqlite3.Cursor], None]
            ) -> None:
        self._connection = connection
        self._beginCallback = beginCallback
        self._endCallback = endCallback
        self._rollbackCallback = rollbackCallback

    def connection(self) -> sqlite3.Connection:
        return self._connection

    def begin(self) -> 'Transaction':
        if not self._beginCallback:
            raise RuntimeError('Invalid state to begin transaction')

        try:
            self._beginCallback(self._connection)
            # Clear begin callback to indicate transaction has begun. This catches
            # logic errors and is used as an indicator of if the destructor should
            # teardown a transaction that is in progress
            self._beginCallback = None
        except:
            self._teardown()
            raise

        return self

    def end(self) -> None:
        if not self._endCallback:
            raise RuntimeError('Invalid state to end transaction')

        try:
            self._endCallback(self._connection)
        finally:
            self._teardown()

    def rollback(self) -> None:
        if not self._rollbackCallback:
            raise RuntimeError('Invalid state to roll back transaction')

        try:
            self._rollbackCallback(self._connection)
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
        if not self._beginCallback and self._endCallback:
            # A transaction is in progress so roll it back
            self.rollback()

    def _teardown(self) -> None:
        self._endCallback = None
        self._beginCallback = None
        self._rollbackCallback = None
        self._connection = None

class ChangeCallbackToken():
    def __init__(
            self,
            handle: typing.Any,
            detachCallback: typing.Callable[[typing.Any], None]
            ):
        self._handle = handle
        self._detachCallback = detachCallback

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.detach()

    def __del__(self) -> None:
        self.detach()

    def detach(self) -> None:
        try:
            if self._detachCallback:
                self._detachCallback(self._handle)
        finally:
            self._handle = None
            self._detachCallback = None

class ObjectDbManager(object):
    class SchemaType(enum.Enum):
        Table = 'table'
        Trigger = 'trigger'

    class UnsupportedDatabaseVersion(RuntimeError):
        pass

    _DatabasePath = 'test.db'
    _PragmaScript = """
        PRAGMA foreign_keys = ON;
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;
        """
    _SchemasTableName = 'objectdb_schemas'

    _EntitiesTableName = 'objectdb_entities'
    _EntitiesTableSchema = 1
    _EntityTriggerSchemaVersion = 1

    _HierarchyTableName = 'objectdb_hierarchy'
    _HierarchyTableSchema = 1

    _ListsTableName = 'objectdb_lists'
    _ListsTableSchema = 1

    _ChangeLogTableName = 'objectdb_change_log'
    _ChangeLogTableSchema = 1

    _instance = None # Singleton instance
    _lock = threading.RLock() # Reentrant lock
    _databasePath = None
    _tableObjectDefMap: typing.Dict[str, ObjectDef] = {}
    _classObjectDefMap: typing.Dict[typing.Type[DatabaseObject], ObjectDef] = {}
    _changeTypeCallbackMap: typing.Dict[
        typing.Tuple[
            typing.Optional[ObjectDbOperation],
            typing.Optional[typing.Union[
                str, # Entity id
                typing.Type[DatabaseEntity] # Entity type
                ]]
        ],
        typing.Dict[
            str, # Callback handle
            typing.Callable[ # Notification callback
                [
                    ObjectDbOperation,
                    str, # Entity id
                    typing.Type[DatabaseEntity] # Entity type
                ],
                None]]
        ] = {}
    _handleChangeTypeMap: typing.Dict[
        str, # Callback handle
        typing.Tuple[
            typing.Optional[ObjectDbOperation],
            typing.Optional[typing.Union[
                str, # Entity id
                typing.Type[DatabaseEntity]] # Entity type
        ]]] = {}
    _connectionPool: typing.List[sqlite3.Connection] = []
    _maxConnectionPoolSize = 10

    def __init__(self) -> None:
        raise RuntimeError('Call instance() instead')

    @classmethod
    def instance(cls):
        if not cls._instance:
            with cls._lock:
                # Recheck instance as another thread could have created it between the
                # first check and the lock
                if not cls._instance:
                    cls._instance = cls.__new__(cls)
        return cls._instance

    def __del__(self) -> None:
        self._clearConnectionPool()

    def initialise(
            self,
            databasePath: str
            ) -> None:
        logging.info(f'ObjectDbManager connecting to {databasePath}')

        with ObjectDbManager._lock:
            classTypes: typing.Iterable[typing.Type[DatabaseObject]] = common.getSubclasses(
                classType=DatabaseObject,
                topLevelOnly=True)
            tableObjectDefs: typing.Dict[str, ObjectDef] = {}
            classObjectDefs: typing.Dict[typing.Type[DatabaseObject], ObjectDef] = {}
            for classType in classTypes:
                # DatabaseObject implements __eq__ make it easier for derived classes
                # that need to do so. They aren't actually needed by the ObjectDbManager
                # implementation. However, the fact that DatabaseObject does have them
                # means it's best for all derived classes to implement them to avoid
                # bugs that could be caused by accidentally using the base implementation
                # when dealing with derived objects
                if not common.hasMethod(obj=classType, method='__eq__', includeSubclasses=False):
                    raise RuntimeError(f'{classType} is derived from DatabaseObject so must implement __eq__')

                # All DatabaseObject classes should have a static defineObject and createObject
                # functions that will be used by objectdb
                if not common.hasMethod(obj=classType, method='defineObject', includeSubclasses=False):
                    raise RuntimeError(f'{classType} is derived from DatabaseObject so must have a static defineObject function')
                if not common.hasMethod(obj=classType, method='createObject', includeSubclasses=False):
                    raise RuntimeError(f'{classType} is derived from DatabaseObject so must have a static createObject function')

                objectDef = classType.defineObject()
                if not isinstance(objectDef, ObjectDef):
                    raise RuntimeError(f'Object definition for {classType} is not derived from ObjectDef')
                if objectDef.tableName() in tableObjectDefs:
                    raise RuntimeError(f'Object definition for {classType} uses duplicate table name {objectDef.tableName()}')
                if objectDef.classType() is not classType:
                    raise RuntimeError(f'Object definition for {classType} returns incorrect class type {objectDef.classType()}')

                tableObjectDefs[objectDef.tableName()] = objectDef
                classObjectDefs[classType] = objectDef

            # Clear the connection pool as any cached connections may be for a different db
            self._clearConnectionPool()

            connection = None
            cursor = None
            try:
                connection = self._createConnection(databasePath)

                cursor = connection.cursor()
                cursor.execute('BEGIN;')

                # Create schema table
                if not self._checkIfTableExists(
                    tableName=ObjectDbManager._SchemasTableName,
                    cursor=cursor):
                    sql = """
                        CREATE TABLE IF NOT EXISTS {table} (
                            name TEXT NOT NULL,
                            type TEXT NOT NULL,
                            version INTEGER,
                            PRIMARY KEY (name, type)
                        );
                        """.format(table=ObjectDbManager._SchemasTableName)
                    logging.info(f'ObjectDbManager creating \'{ObjectDbManager._SchemasTableName}\' table')
                    cursor.execute(sql)

                # Create entities table
                if not self._checkIfTableExists(
                    tableName=ObjectDbManager._EntitiesTableName,
                    cursor=cursor):
                    sql = """
                        CREATE TABLE IF NOT EXISTS {table} (
                            id TEXT PRIMARY KEY NOT NULL,
                            table_name TEXT NOT NULL
                        );
                        """.format(table=ObjectDbManager._EntitiesTableName)
                    logging.info(f'ObjectDbManager creating \'{ObjectDbManager._EntitiesTableName}\' table')
                    cursor.execute(sql)

                    self._writeSchemaVersion(
                        name=ObjectDbManager._EntitiesTableName,
                        type=ObjectDbManager.SchemaType.Table,
                        version=ObjectDbManager._EntitiesTableSchema,
                        cursor=cursor)

                    # Create schema table indexes for id column. The id index is
                    # needed as, even though it's the primary key, it's of type
                    # TEXT so doesn't automatically get indexes
                    self._createColumnIndex(
                        table=ObjectDbManager._EntitiesTableName,
                        column='id',
                        unique=True,
                        cursor=cursor)

                # Create hierarchy table
                if not self._checkIfTableExists(
                    tableName=ObjectDbManager._HierarchyTableName,
                    cursor=cursor):
                    # TODO: Should rename id column to parent
                    sql = """
                        CREATE TABLE IF NOT EXISTS {hierarchyTable} (
                            id TEXT NOT NULL,
                            child TEXT,
                            FOREIGN KEY(id) REFERENCES {entityTable}(id) ON DELETE CASCADE
                            FOREIGN KEY(child) REFERENCES {entityTable}(id) ON DELETE CASCADE
                        );
                        """.format(
                            hierarchyTable=ObjectDbManager._HierarchyTableName,
                            entityTable=ObjectDbManager._EntitiesTableName
                            )
                    logging.info(f'ObjectDbManager creating \'{ObjectDbManager._HierarchyTableName}\' table')
                    cursor.execute(sql)

                    self._writeSchemaVersion(
                        name=ObjectDbManager._HierarchyTableName,
                        type=ObjectDbManager.SchemaType.Table,
                        version=ObjectDbManager._HierarchyTableSchema,
                        cursor=cursor)

                    # Create schema table indexes for id and child columns.
                    self._createColumnIndex(
                        table=ObjectDbManager._HierarchyTableName,
                        column='id',
                        unique=False,
                        cursor=cursor)
                    self._createColumnIndex(
                        table=ObjectDbManager._HierarchyTableName,
                        column='child',
                        unique=False,
                        cursor=cursor)

                # Create list table
                if not self._checkIfTableExists(
                    tableName=ObjectDbManager._ListsTableName,
                    cursor=cursor):
                    sql = """
                        CREATE TABLE IF NOT EXISTS {table} (
                            id TEXT NOT NULL,
                            bool INTEGER,
                            integer INTEGER,
                            float REAL,
                            string TEXT,
                            entity TEXT,
                            FOREIGN KEY(id) REFERENCES {entitiesTable}(id) ON DELETE CASCADE
                            FOREIGN KEY(entity) REFERENCES {entitiesTable}(id) ON DELETE CASCADE
                        );
                        """.format(
                        table=ObjectDbManager._ListsTableName,
                        entitiesTable=ObjectDbManager._EntitiesTableName)
                    logging.info(f'ObjectDbManager creating \'{ObjectDbManager._ListsTableName}\' table')
                    cursor.execute(sql)

                    self._writeSchemaVersion(
                        name=ObjectDbManager._ListsTableName,
                        type=ObjectDbManager.SchemaType.Table,
                        version=ObjectDbManager._ListsTableSchema,
                        cursor=cursor)

                    # Create schema table indexes for id columns
                    self._createColumnIndex(
                        table=ObjectDbManager._ListsTableName,
                        column='id',
                        unique=False,
                        cursor=cursor)

                # Create change log table
                if not self._checkIfTableExists(
                    tableName=ObjectDbManager._ChangeLogTableName,
                    cursor=cursor):
                    sql = """
                        CREATE TABLE IF NOT EXISTS {table} (
                            operation TEXT NOT NULL,
                            entity TEXT NOT NULL,
                            table_name TEXT NOT NULL
                        );
                        """.format(
                        table=ObjectDbManager._ChangeLogTableName)
                    logging.info(f'ObjectDbManager creating \'{ObjectDbManager._ChangeLogTableName}\' table')
                    cursor.execute(sql)

                    self._writeSchemaVersion(
                        name=ObjectDbManager._ChangeLogTableName,
                        type=ObjectDbManager.SchemaType.Table,
                        version=ObjectDbManager._ChangeLogTableSchema,
                        cursor=cursor)

                # Check there are no tables with schemas newer than this version supports
                tableSchemas = self._readTableSchemaVersions(cursor=cursor)
                supportedSchemas = {
                    ObjectDbManager._EntitiesTableName: ObjectDbManager._EntitiesTableSchema,
                    ObjectDbManager._ListsTableName: ObjectDbManager._ListsTableSchema}
                for objectDef in classObjectDefs.values():
                    supportedSchemas[objectDef.tableName()] = objectDef.tableSchema()
                for tableName, tableSchema in tableSchemas.items():
                    supportedSchema = supportedSchemas.get(tableName)
                    if supportedSchema != None and supportedSchema < tableSchema:
                        raise ObjectDbManager.UnsupportedDatabaseVersion(
                            f'ObjectDbManager table {tableName} uses schema {tableSchema} but only {supportedSchema} is supported')

                # Create any object tables that don't exist
                for objectDef in classObjectDefs.values():
                    if not self._checkIfTableExists(tableName=objectDef.tableName(), cursor=cursor):
                        self._createObjectTable(
                            objectDef=objectDef,
                            cursor=cursor)

                # Create entity table triggers
                self._createEntityTableTrigger(
                    type=ObjectDbTriggerType.After,
                    operation=ObjectDbOperation.Insert,
                    sqlFragment="""
                        -- Log entity creation
                        INSERT INTO {logTable} (operation, entity, table_name)
                        VALUES ("{operation}", NEW.id, NEW.table_name);
                        """.format(
                            logTable=ObjectDbManager._ChangeLogTableName,
                            operation=ObjectDbOperation.Insert.value),
                    cursor=cursor)
                self._createEntityTableTrigger(
                    type=ObjectDbTriggerType.After,
                    operation=ObjectDbOperation.Update,
                    sqlFragment="""
                        -- Log entity update
                        INSERT INTO {logTable} (operation, entity, table_name)
                        VALUES ("{operation}", NEW.id, NEW.table_name);
                        """.format(
                            logTable=ObjectDbManager._ChangeLogTableName,
                            operation=ObjectDbOperation.Update.value),
                    cursor=cursor)
                self._createEntityTableTrigger(
                    type=ObjectDbTriggerType.After,
                    operation=ObjectDbOperation.Delete,
                    sqlFragment="""
                        -- Log entity deletion
                        INSERT INTO {logTable} (operation, entity, table_name)
                        VALUES ("{operation}", OLD.id, OLD.table_name);
                        """.format(
                            logTable=ObjectDbManager._ChangeLogTableName,
                            operation=ObjectDbOperation.Delete.value),
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

            self._poolReusableConnection(connection=connection)

            self._databasePath = databasePath
            self._tableObjectDefMap.update(tableObjectDefs)
            self._classObjectDefMap.update(classObjectDefs)

    def createTransaction(self) -> Transaction:
        connection = self._createConnection(
            databasePath=self._databasePath)
        return Transaction(
            connection=connection,
            beginCallback=self._handleBeginTransaction,
            endCallback=self._handleEndTransaction,
            rollbackCallback=self._handleRollbackTransaction)

    def createObject(
            self,
            object: DatabaseObject,
            transaction: typing.Optional[Transaction] = None
            ) -> str:
        logging.debug(f'ObjectDbManager creating object {object.id()} of type {type(object)}')
        if transaction != None:
            connection = transaction.connection()
            self._createEntity(
                entity=object,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._createEntity(
                    entity=object,
                    cursor=connection.cursor())

    def readObject(
            self,
            id: str,
            transaction: typing.Optional[Transaction] = None
            ) -> DatabaseObject:
        logging.debug(f'ObjectDbManager reading object {id}')
        if transaction != None:
            connection = transaction.connection()
            return self._readEntity(
                id=id,
                cursor=connection.cursor())
        else:
            # Use a transaction for the read to ensure a consistent
            # view of the database across multiple selects
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._readEntity(
                    id=id,
                    cursor=connection.cursor())

    def readObjects(
            self,
            classType: typing.Type[DatabaseObject],
            transaction: typing.Optional[Transaction] = None
            ) -> typing.Iterable[DatabaseObject]:
        logging.debug(f'ObjectDbManager reading objects of type {classType}')
        if transaction != None:
            connection = transaction.connection()
            return self._readEntities(
                classType=classType,
                cursor=connection.cursor())
        else:
            # Use a transaction for the read to ensure a consistent
            # view of the database across multiple selects
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                return self._readEntities(
                    classType=classType,
                    cursor=connection.cursor())

    def updateObject(
            self,
            object: DatabaseObject,
            transaction: typing.Optional[Transaction] = None
            ) -> None:
        logging.debug(f'ObjectDbManager updating object {object.id()} of type {type(object)}')
        if transaction != None:
            connection = transaction.connection()
            self._updateEntity(
                entity=object,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._updateEntity(
                    entity=object,
                    cursor=connection.cursor())

    def deleteObject(
            self,
            id: str,
            transaction: typing.Optional[Transaction] = None
            ) -> None:
        logging.debug(f'ObjectDbManager deleting object {id}')
        if transaction != None:
            connection = transaction.connection()
            self._deleteEntity(
                id=id,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._deleteEntity(
                    id=id,
                    cursor=connection.cursor())

    def deleteObjects(
            self,
            type: typing.Type[DatabaseObject],
            transaction: typing.Optional[Transaction] = None
            ) -> None:
        logging.debug(f'ObjectDbManager deleting objects of type {type}')
        if transaction != None:
            connection = transaction.connection()
            self._deleteEntities(
                type=type,
                cursor=connection.cursor())
        else:
            with self.createTransaction() as transaction:
                connection = transaction.connection()
                self._deleteEntities(
                    type=type,
                    cursor=connection.cursor())

    def connectChangeCallback(
            self,
            callback: typing.Callable[
                [
                    ObjectDbOperation,
                    str, # Entity id
                    typing.Type[DatabaseEntity] # Entity type
                ],
                None],
            operation: typing.Optional[ObjectDbOperation] = None,
            key: typing.Optional[typing.Union[
                    str, # Entity id
                    typing.Type[DatabaseEntity] # Type of entity
                ]] = None,
            ) -> ChangeCallbackToken:
        handle = str(uuid.uuid4())
        changeType = (operation, key)

        with ObjectDbManager._lock:
            callbackMap = self._changeTypeCallbackMap.get(changeType)
            if not callbackMap:
                callbackMap = {}
                self._changeTypeCallbackMap[changeType] = callbackMap
            callbackMap[handle] = callback

            self._handleChangeTypeMap[handle] = changeType

        return ChangeCallbackToken(
            handle=handle,
            detachCallback=self._handleDisconnectChangeCallback)

    def _createConnection(
            self,
            databasePath: str
            ) -> sqlite3.Connection:
        with ObjectDbManager._lock:
            if self._connectionPool:
                connection = self._connectionPool.pop()
                logging.debug(f'ObjectDbManager reusing cached connection {connection}')
                return connection

        connection = sqlite3.connect(databasePath)
        logging.debug(f'ObjectDbManager created new connection {connection} to \'{databasePath}\'')
        connection.executescript(ObjectDbManager._PragmaScript)
        # Uncomment this to have sqlite print the SQL that it executes
        #connection.set_trace_callback(print)
        return connection

    def _poolReusableConnection(
            self,
            connection: sqlite3.Connection
            ) -> None:
        with ObjectDbManager._lock:
            if len(self._connectionPool) < self._maxConnectionPoolSize:
                self._connectionPool.append(connection)
                logging.debug(f'ObjectDbManager added connection {connection} to pool')
                return

        connection.close()

    def _clearConnectionPool(self) -> None:
        with ObjectDbManager._lock:
            for connection in self._connectionPool:
                try:
                    connection.close()
                except Exception as ex:
                    logging.error(
                        'ObjectDbManager failed to close connection when clearing pool', exc_info=ex)
                    continue
            self._connectionPool.clear()

    def _checkIfTableExists(
            self,
            tableName: str,
            cursor: sqlite3.Cursor
            ) -> bool:
        sql = 'SELECT name FROM sqlite_master WHERE type = "table" AND name = :table;'
        cursor.execute(sql, {'table': tableName})
        return cursor.fetchone() != None

    def _checkIfTriggerExists(
            self,
            triggerName: str,
            cursor: sqlite3.Cursor
            ) -> bool:
        sql = 'SELECT name  FROM sqlite_master  WHERE type = "trigger" AND name = :trigger;'
        cursor.execute(sql, {'trigger': triggerName})
        return cursor.fetchone() != None

    def _readSchemaVersion(
            self,
            name: str,
            type: 'ObjectDbManager.SchemaType',
            cursor: sqlite3.Cursor
            ) -> typing.Optional[int]:
        sql = """
            SELECT version
            FROM {table}
            WHERE name = :name AND type = :type
            LIMIT 1;
            """.format(
            table=ObjectDbManager._SchemasTableName)
        cursor.execute(sql, {'name': name, 'type': type.value})
        row = cursor.fetchone()
        return int(row[0]) if row != None else None

    def _writeSchemaVersion(
            self,
            name: str,
            type: 'ObjectDbManager.SchemaType',
            version: int,
            cursor: sqlite3.Cursor
            ) -> None:
        sql = """
            INSERT INTO {table} (name, type, version)
            VALUES (:name, :type, :version)
            ON CONFLICT(name, type) DO UPDATE SET
                version = excluded.version;
            """.format(table=ObjectDbManager._SchemasTableName)
        logging.info(f'ObjectDbManager setting schema for {type.value} \'{name}\' to {version}')
        rowData = {
            'name': name,
            'type': type.value,
            'version': version}
        cursor.execute(sql, rowData)

    def _readTableSchemaVersions(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.Mapping[str, int]:
        sql = """
            SELECT name, version
            FROM {table}
            WHERE type = "{type}";
            """.format(
            table=ObjectDbManager._SchemasTableName,
            type=ObjectDbManager.SchemaType.Table.value)
        cursor.execute(sql)

        schemaVersions = {}
        for row in cursor.fetchall():
            tableName = row[0]
            schemaVersion = int(row[1])
            schemaVersions[tableName] = schemaVersion

        return schemaVersions

    def _createColumnIndex(
            self,
            table: str,
            column: str,
            unique: bool,
            cursor: sqlite3.Cursor
            ) -> None:
            if unique:
                sql = f'CREATE UNIQUE INDEX IF NOT EXISTS {table}_{column}_index ON {table}({column});'
            else:
                sql = f'CREATE INDEX IF NOT EXISTS {table}_{column}_index ON {table}({column});'
            logging.info(f'ObjectDbManager creating \'{table}\' {column} index')
            cursor.execute(sql)

    def _createEntityTableTrigger(
            self,
            type: ObjectDbTriggerType,
            operation: ObjectDbOperation,
            sqlFragment: str,
            cursor: sqlite3.Cursor
            ) -> None:
        triggerName = '{type}_{operation}_entity_trigger'.format(
            type=type.value.lower(),
            operation=operation.value.lower())

        if self._checkIfTriggerExists(triggerName=triggerName, cursor=cursor):
            schemaVersion = self._readSchemaVersion(
                name=triggerName,
                type=ObjectDbManager.SchemaType.Trigger,
                cursor=cursor)
            if schemaVersion == ObjectDbManager._EntityTriggerSchemaVersion:
                return # Correct version trigger already exists so nothing to do

            # Delete the old trigger and create the new one
            self._dropTrigger(
                triggerName=triggerName,
                schemaVersion=schemaVersion,
                cursor=cursor)

        sql = """
            CREATE TRIGGER {triggerName}
            {type} {operation} ON {entitiesTable}
            FOR EACH ROW
            BEGIN
            {sql}
            END;
            """.format(
                triggerName=triggerName,
                type=type.value.upper(),
                operation=operation.value.upper(),
                entitiesTable=ObjectDbManager._EntitiesTableName,
                sql=sqlFragment)

        logging.info(f'ObjectDbManager creating \'{triggerName}\' trigger')
        cursor.execute(sql)

        self._writeSchemaVersion(
            name=triggerName,
            type=ObjectDbManager.SchemaType.Trigger,
            version=ObjectDbManager._EntityTriggerSchemaVersion,
            cursor=cursor)

    def _dropTrigger(
            self,
            triggerName: str,
            schemaVersion: typing.Optional[str],
            cursor: sqlite3.Cursor
            ) -> None:
        sql = 'DROP TRIGGER {triggerName};'.format(triggerName=triggerName)
        if schemaVersion == None:
            logging.info(f'ObjectDbManager deleting \'{triggerName}\' trigger with unknown version')
        else:
            logging.info(f'ObjectDbManager deleting version {schemaVersion} \'{triggerName}\' trigger')
        cursor.execute(sql)

    def _createObjectTable(
            self,
            objectDef: ObjectDef,
            cursor: sqlite3.Cursor
            ) -> None:
        columnStrings = ['id TEXT PRIMARY KEY NOT NULL']
        for paramDef in objectDef.paramDefs():
            columnString = paramDef.columnName()
            columnType = paramDef.columnType()

            if columnType == str:
                columnString += ' TEXT'
            elif columnType == int:
                columnString += ' INTEGER'
            elif columnType == float:
                columnString += ' REAL'
            elif columnType == bool:
                columnString += ' INTEGER'
            elif issubclass(columnType, DatabaseEntity):
                columnString += ' TEXT'
            else:
                raise RuntimeError(
                    f'Parameter definition {paramDef.columnName()} for {objectDef.classType()} has unknown type {columnType}')

            if not paramDef.isOptional():
                columnString += ' NOT NULL'

            columnStrings.append(columnString)

        columnStrings.append(
            'FOREIGN KEY(id) REFERENCES {entitiesTable}(id) ON DELETE CASCADE'.format(
                entitiesTable=ObjectDbManager._EntitiesTableName))

        # NOTE: This breaks the cardinal rule of not manually formatting SQL
        # statements, however, it's acceptable here as what it's formatting
        # comes from code (rather than user input) so there is no real risk of
        # an injection attack
        sql = """
            CREATE TABLE IF NOT EXISTS {table} ({columns});
            """.format(
            table=objectDef.tableName(),
            columns=', '.join(columnStrings))
        logging.info(f'ObjectDbManager creating \'{objectDef.tableName()}\' table')
        cursor.execute(sql)

        self._writeSchemaVersion(
            name=objectDef.tableName(),
            type=ObjectDbManager.SchemaType.Table,
            version=objectDef.tableSchema(),
            cursor=cursor)

        # Create schema table indexes for id columns. This is needed as.
        # even though it's  the primary key, it's of type TEXT so doesn't
        # automatically get indexes
        self._createColumnIndex(
            table=objectDef.tableName(),
            column='id',
            unique=True,
            cursor=cursor)

    def _createEntity(
            self,
            entity: DatabaseEntity,
            cursor: sqlite3.Cursor
            ) -> None:
        children: typing.List[DatabaseEntity] = []
        if isinstance(entity, DatabaseObject):
            objectDef = self._classObjectDefMap.get(type(entity))
            if objectDef == None:
                raise ValueError(f'Failed to create {type(entity)} (Unknown object type)')

            # Add object to entity table
            sql = 'INSERT INTO {table} VALUES (:id, :table_name);'.format(
                table=ObjectDbManager._EntitiesTableName)
            rowData = {
                'id': entity.id(),
                'table_name': objectDef.tableName()
            }
            cursor.execute(sql, rowData)

            # Add object to its object table
            sql = 'INSERT INTO {table} VALUES (:id'.format(
                table=objectDef.tableName())
            rowData = {'id': entity.id()}
            objectData = entity.data()
            for paramDef in objectDef.paramDefs():
                columnName = paramDef.columnName()
                if columnName not in objectData:
                    raise RuntimeError(
                        f'Parameter {columnName} not present in data for object {entity.id()} of type {objectDef.classType()}')
                columnValue = objectData[columnName]
                if columnValue == None and not paramDef.isOptional():
                    raise RuntimeError(
                        f'Parameter {columnName} for object {entity.id()} of type {objectDef.classType()} has null value for mandatory parameter')
                sql += ', :' + columnName

                columnType = paramDef.columnType()
                childEntity = None
                if columnType == str:
                    if columnValue != None:
                        columnValue = str(columnValue)
                elif columnType == int:
                    if columnValue != None:
                        columnValue = int(columnValue)
                elif columnType == float:
                    if columnValue != None:
                        columnValue = float(columnValue)
                elif columnType == bool:
                    if columnValue != None:
                        columnValue = 1 if columnValue else 0
                elif issubclass(columnType, DatabaseEntity):
                    if columnValue != None:
                        if not isinstance(columnValue, DatabaseEntity) or \
                            not isinstance(columnValue, columnType):
                            raise RuntimeError(
                                f'Parameter {columnName} for object {entity.id()} of type {objectDef.classType()} is not a database object of type {columnType}')
                        childEntity = columnValue
                        columnValue = columnValue.id()
                else:
                    raise RuntimeError(
                        f'Parameter {columnName} for object {entity.id()} of type {objectDef.classType()} has unknown type {columnType}')

                rowData[columnName] = columnValue

                if childEntity != None:
                    # NOTE: Use of _updateEntity rather than recursively calling
                    # _createEntity is intentional as children entities may
                    # already be in the database
                    self._updateEntity(
                        entity=childEntity,
                        cursor=cursor)
                    children.append(childEntity)

            sql += ');'
            cursor.execute(sql, rowData)
        elif isinstance(entity, DatabaseList):
            # Add list to entity table. This is always done, even if the list is
            # empty
            sql = 'INSERT INTO {table} VALUES (:id, :table_name);'.format(
                table=ObjectDbManager._EntitiesTableName)
            rowData = {
                'id': entity.id(),
                'table_name': ObjectDbManager._ListsTableName
            }
            cursor.execute(sql, rowData)

            # Add list entries to list table. This is only done if the list has
            # content
            rowData = []
            for childEntity in entity:
                if isinstance(childEntity, DatabaseEntity):
                    # Add child entities to database. This must be done before
                    # adding the list to the list table to avoid foreign key
                    # issues
                    # NOTE: Use of _updateEntity rather than recursively calling
                    # _createEntity is intentional as children entities may
                    # already be in the database
                    self._updateEntity(
                        entity=childEntity,
                        cursor=cursor)
                    children.append(childEntity)

                rowData.append((
                    entity.id(),
                    (1 if childEntity else 0) if isinstance(childEntity, bool) else None,
                    childEntity if isinstance(childEntity, int) else None,
                    childEntity if isinstance(childEntity, float) else None,
                    childEntity if isinstance(childEntity, str) else None,
                    childEntity.id() if isinstance(childEntity, DatabaseEntity) else None))
            if rowData:
                sql = """
                    INSERT INTO {table} (id, bool, integer, float, string, entity)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """.format(table=ObjectDbManager._ListsTableName)
                cursor.executemany(sql, rowData)
        else:
            raise RuntimeError(f'Unexpected entity type {type(entity)}')

        if children:
            # Add child entries to hierarchy table
            sql = """
                INSERT INTO {table} (id, child)
                VALUES (?, ?);
                """.format(table=ObjectDbManager._HierarchyTableName)
            cursor.executemany(
                sql,
                [(entity.id(), childEntity.id()) for childEntity in children])

    def _readEntity(
            self,
            id: str,
            cursor: sqlite3.Cursor,
            table: typing.Optional[str] = None
            ) -> DatabaseEntity:
        if not table:
            sql = """
                SELECT table_name
                FROM {table}
                WHERE id = :id
                LIMIT 1;
                """.format(table=ObjectDbManager._EntitiesTableName)
            cursor.execute(sql, {'id': id})
            row = cursor.fetchone()
            if not row:
                raise RuntimeError(f'Table for {id} not found in entity table')
            table = row[0]

        if table == ObjectDbManager._ListsTableName:
            sql = """
                SELECT
                    {listTable}.bool,
                    {listTable}.integer,
                    {listTable}.float,
                    {listTable}.string,
                    {listTable}.entity,
                    {entitiesTable}.table_name AS entity_table
                FROM {listTable}
                LEFT JOIN {entitiesTable}
                    ON {listTable}.entity = {entitiesTable}.id
                WHERE {listTable}.id = :id;
                """.format(
                listTable=ObjectDbManager._ListsTableName,
                entitiesTable=ObjectDbManager._EntitiesTableName)
            cursor.execute(sql, {'id': id})
            content = []
            for row in cursor.fetchall():
                if row[0] != None:
                    content.append(bool(row[0])) # It's a bool (stored as an int)
                elif row[1] != None:
                    content.append(row[1]) # It's an integer
                elif row[2] != None:
                    content.append(row[2]) # It's a float
                elif row[3] != None:
                    content.append(row[3]) # It's a string
                elif row[4] != None:
                    content.append(self._readEntity( # It's an entity
                        id=row[4],
                        table=row[5],
                        cursor=cursor))

            return DatabaseList(
                id=id,
                content=content)
        else:
            objectDef = self._tableObjectDefMap.get(table)
            if objectDef == None:
                raise ValueError(f'Object {id} uses unknown table {table}')
            columns = []
            entityJoins = ''
            for paramDef in objectDef.paramDefs():
                columns.append('{table}.{column}'.format(
                    table=table,
                    column=paramDef.columnName()))
                if issubclass(paramDef.columnType(), DatabaseEntity):
                    # If the parameter type is a database entity then add an additional
                    # column and setup a join so the column will be filled with the table
                    # for the entity
                    columns.append('{column}_entity_table.table_name AS {column}_entity_table'.format(
                        column=paramDef.columnName()))
                    entityJoins += \
                        """
                        LEFT JOIN {entitiesTable} AS {column}_entity_table
                            ON {objectTable}.{column} = {column}_entity_table.id
                        """.format(
                            entitiesTable=ObjectDbManager._EntitiesTableName,
                            objectTable=table,
                            column=paramDef.columnName())

            sql = """
                SELECT {columns}
                FROM {dataTable}
                JOIN {entitiesTable} ON {dataTable}.id = {entitiesTable}.id
                {entityJoins}
                WHERE {dataTable}.id = :id
                LIMIT 1;
                """.format(
                columns=','.join(columns),
                dataTable=table,
                entitiesTable=ObjectDbManager._EntitiesTableName,
                entityJoins=entityJoins)
            cursor.execute(sql, {'id': id})
            row = cursor.fetchone()
            if not row:
                raise RuntimeError(f'Object {id} not found in table {table}')

            objectData = {}
            columnIndex = 0
            for paramDef in objectDef.paramDefs():
                columnName = paramDef.columnName()
                columnValue = row[columnIndex]
                if columnValue == None and not paramDef.isOptional():
                    raise RuntimeError(
                        f'Database column {columnName} for object {id} of type {objectDef.classType()} has null value for mandatory parameter')
                columnIndex += 1

                columnType = paramDef.columnType()
                if columnType == str:
                    if columnValue != None:
                        columnValue = str(columnValue) # Should be redundant if table defined correctly
                elif columnType == int:
                    if columnValue != None:
                        columnValue = int(columnValue) # Should be redundant if table defined correctly
                elif columnType == float:
                    if columnValue != None:
                        columnValue = float(columnValue) # Should be redundant if table defined correctly
                elif columnType == bool:
                    if columnValue != None:
                        columnValue = columnValue != 0
                elif issubclass(columnType, DatabaseEntity):
                    entityTable = row[columnIndex]
                    columnIndex += 1 # Entity table was read from row

                    if columnValue != None:
                        if entityTable == None:
                            raise RuntimeError(
                                f'Database column {columnName} for object {id} of type {objectDef.classType()} has null entity table')
                        columnValue = self._readEntity(
                            id=columnValue,
                            table=entityTable,
                            cursor=cursor)
                else:
                    raise RuntimeError(
                        f'Parameter {columnName} for object {id} of type {objectDef.classType()} has unknown type {columnType}')

                objectData[columnName] = columnValue

            classType = objectDef.classType()
            return classType.createObject(
                id=id,
                data=objectData)

    def _readEntities(
            self,
            classType: typing.Type[DatabaseObject],
            cursor: sqlite3.Cursor,
            ) -> typing.Iterable[DatabaseObject]:
        objectDef = self._classObjectDefMap.get(classType)
        if objectDef == None:
            raise ValueError(f'{classType} has no object definition')

        columns = [
            '{table}.id'.format(table=objectDef.tableName())
            ]
        entityJoins = ''
        for paramDef in objectDef.paramDefs():
            columns.append('{table}.{column}'.format(
                table=objectDef.tableName(),
                column=paramDef.columnName()))
            if issubclass(paramDef.columnType(), DatabaseEntity):
                # If the parameter type is a database entity then add an additional
                # column and setup a join so the column will be filled with the table
                # for the entity
                columns.append('{column}_entity_table.table_name AS {column}_entity_table'.format(
                    column=paramDef.columnName()))
                entityJoins += \
                    """
                    LEFT JOIN {entitiesTable} AS {column}_entity_table
                        ON {objectTable}.{column} = {column}_entity_table.id
                    """.format(
                        entitiesTable=ObjectDbManager._EntitiesTableName,
                        objectTable=objectDef.tableName(),
                        column=paramDef.columnName())

        sql = """
            SELECT {columns}
            FROM {dataTable}
            JOIN {entitiesTable} ON {dataTable}.id = {entitiesTable}.id
            {entityJoins};
            """.format(
            columns=','.join(columns),
            dataTable=objectDef.tableName(),
            entitiesTable=ObjectDbManager._EntitiesTableName,
            entityJoins=entityJoins)
        cursor.execute(sql)
        objects = []
        for row in cursor.fetchall():
            id = row[0]
            objectData = {}
            columnIndex = 1
            for paramDef in objectDef.paramDefs():
                columnName = paramDef.columnName()
                columnValue = row[columnIndex]
                if columnValue == None and not paramDef.isOptional():
                    raise RuntimeError(
                        f'Database column {columnName} for object {id} of type {objectDef.classType()} has null value for mandatory parameter')
                columnIndex += 1

                columnType = paramDef.columnType()
                if columnType == str:
                    if columnValue != None:
                        columnValue = str(columnValue) # Should be redundant if table defined correctly
                elif columnType == int:
                    if columnValue != None:
                        columnValue = int(columnValue) # Should be redundant if table defined correctly
                elif columnType == float:
                    if columnValue != None:
                        columnValue = float(columnValue) # Should be redundant if table defined correctly
                elif columnType == bool:
                    if columnValue != None:
                        columnValue = columnValue != 0
                elif issubclass(columnType, DatabaseEntity):
                    entityTable = row[columnIndex]
                    columnIndex += 1 # Entity table was read from row

                    if columnValue != None:
                        if entityTable == None:
                            raise RuntimeError(
                                f'Database column {columnName} for object {id} of type {objectDef.classType()} has null entity table')
                        columnValue = self._readEntity(
                            id=columnValue,
                            table=entityTable,
                            cursor=cursor)
                else:
                    raise RuntimeError(
                        f'Parameter definition {objectDef.classType()}.{columnName} has unknown type {columnType}')

                objectData[columnName] = columnValue

            classType = objectDef.classType()
            objects.append(classType.createObject(
                id=id,
                data=objectData))
        return objects

    # Generated by chat-gpt after I implemented the rest of CRUD. I'm
    # impressed with how good it was, the only thing it got wrong was
    # not handling the error case where an optional object param where
    # the accessor function returns an object that isn't derived from
    # DatabaseObject
    def _updateEntity(
            self,
            entity: DatabaseEntity,
            cursor: sqlite3.Cursor
            ) -> None:
        children: typing.List[DatabaseEntity] = []
        if isinstance(entity, DatabaseObject):
            objectDef = self._classObjectDefMap.get(type(entity))
            if objectDef == None:
                raise ValueError(f'Object {entity.id()} uses unknown type {type(entity)}')

            paramDefs = objectDef.paramDefs()
            columnNames = [paramDef.columnName() for paramDef in paramDefs]

            # Update the entities table metadata
            sql = """
                INSERT INTO {table} (id, table_name)
                VALUES (:id, :table)
                ON CONFLICT(id) DO UPDATE SET
                    table_name = excluded.table_name;
                """.format(table=ObjectDbManager._EntitiesTableName)
            rowData = {
                'id': entity.id(),
                'table': objectDef.tableName()}
            cursor.execute(sql, rowData)

            # Query existing values if any of the objects parameters refer to
            # another entity as they're used to delete the old object if the
            # parameter is being updated to refer to a different object
            hasReference = any(
                issubclass(paramDef.columnType(), DatabaseEntity)
                for paramDef in paramDefs)
            exitingValues = None
            if hasReference:
                sql = """
                    SELECT {columns}
                    FROM {dataTable}
                    WHERE id = :id
                    LIMIT 1;
                    """.format(
                    columns=','.join(columnNames),
                    dataTable=objectDef.tableName(),
                    entitiesTable=ObjectDbManager._EntitiesTableName)
                cursor.execute(sql, {'id': entity.id()})
                exitingValues = cursor.fetchone()

            objectData = entity.data()
            rowData = {'id': entity.id()}
            for index, paramDef in enumerate(paramDefs):
                columnName = paramDef.columnName()
                if columnName not in objectData:
                    raise RuntimeError(
                        f'Parameter {columnName} not present in data for object {entity.id()} of type {objectDef.classType()}')
                columnValue = objectData[columnName]
                if columnValue == None and not paramDef.isOptional():
                    raise RuntimeError(
                        f'Parameter {columnName} for object {entity.id()} of type {objectDef.classType()} has null value for mandatory parameter')

                columnType = paramDef.columnType()
                isReference = False
                childEntity = None
                if columnType == str:
                    if columnValue != None:
                        columnValue = str(columnValue)
                elif columnType == int:
                    if columnValue != None:
                        columnValue = int(columnValue)
                elif columnType == float:
                    if columnValue != None:
                        columnValue = float(columnValue)
                elif columnType == bool:
                    if columnValue != None:
                        columnValue = 1 if columnValue else 0
                elif issubclass(columnType, DatabaseEntity):
                    if columnValue != None:
                        if not isinstance(columnValue, DatabaseEntity) or \
                            not isinstance(columnValue, columnType):
                            raise RuntimeError(
                                f'Parameter {columnName} for object {entity.id()} of type {objectDef.classType()} is not a database object of type {columnType}')
                        isReference = True
                        childEntity = columnValue
                        columnValue = str(columnValue.id())
                else:
                    raise RuntimeError(
                        f'Parameter {columnName} for object {entity.id()} of type {objectDef.classType()} has unknown type {columnType}')

                rowData[columnName] = columnValue

                if isReference and (exitingValues != None):
                    oldId = exitingValues[index]
                    if oldId != None and oldId != columnValue:
                        self._deleteIfOnlyReference(
                            entityId=oldId,
                            parentId=entity.id(),
                            cursor=cursor)

                if childEntity != None:
                    # Recursively update the child entity
                    self._updateEntity(entity=childEntity, cursor=cursor)
                    children.append(childEntity)

            # Update the object's specific table fields
            sql = """
                INSERT INTO {table} (id, {columns})
                VALUES (:id, {placeholders})
                ON CONFLICT(id) DO UPDATE SET {conflict};
                """.format(
                    table=objectDef.tableName(),
                    columns=', '.join(columnNames),
                    placeholders=', '.join([f':{col}' for col in columnNames]),
                    conflict=', '.join([f'{col} = excluded.{col}' for col in columnNames]))
            cursor.execute(sql, rowData)
        elif isinstance(entity, DatabaseList):
            # Update the entities table for the list
            sql = """
                INSERT INTO {table} (id, table_name)
                VALUES (:id, :table)
                ON CONFLICT(id) DO UPDATE SET
                    table_name = excluded.table_name;
                """.format(table=ObjectDbManager._EntitiesTableName)
            rowData = {
                'id': entity.id(),
                'table': ObjectDbManager._ListsTableName}
            cursor.execute(sql, rowData)

            # Delete any children that were in the list but aren't any more
            # NOTE: The SQL query only gets unique entities from the list table
            # (i.e. if the list contains multiple references to the the same
            # child, the query will only return it's id once). This is done to
            # prevent the same entity being deleted twice.
            contentIds = [child.id() for child in entity if isinstance(child, DatabaseEntity)]
            sql = """
                SELECT DISTINCT entity
                FROM {listsTable}
                WHERE id = ?
                AND entity NOT IN ({placeholders})
                """.format(
                    listsTable=ObjectDbManager._ListsTableName,
                    placeholders=', '.join('?' for _ in contentIds))
            rowData = [entity.id()] + contentIds
            cursor.execute(sql, rowData)
            for row in cursor.fetchall():
                childId = row[0]
                self._deleteIfOnlyReference(
                    entityId=childId,
                    parentId=entity.id(),
                    cursor=cursor)

            # Recursively update list children. This must be done before
            # inserting the parent to avoid foreign key issues
            for child in entity:
                if isinstance(child, DatabaseEntity):
                    self._updateEntity(entity=child, cursor=cursor)
                    children.append(child)

            # Remove all existing entries in the list table for this list and
            # add the new ones. This is a bit inefficient if the majority of the
            # same objects are still in the list, however it has the advantage
            # that it keeps the order of the items in the db the same as the
            # order the list object has them
            sql = 'DELETE FROM {table} WHERE id = :id'.format(
                table=ObjectDbManager._ListsTableName)
            cursor.execute(sql, {'id': entity.id()})

            rowData = []
            for child in entity:
                rowData.append((
                    entity.id(),
                    (1 if child else 0) if isinstance(child, bool) else None,
                    child if isinstance(child, int) else None,
                    child if isinstance(child, float) else None,
                    child if isinstance(child, str) else None,
                    child.id() if isinstance(child, DatabaseEntity) else None))
            if rowData:
                sql = """
                    INSERT INTO {table} (id, bool, integer, float, string, entity)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """.format(table=ObjectDbManager._ListsTableName)
                cursor.executemany(sql, rowData)
        else:
            raise RuntimeError(f'Unexpected entity type {type(entity)}')

        # Delete all child entries from the hierarchy table then add the new
        # entries. The delete is always done as, even if an entity doesn't have
        # any children now, it doesn't mean it didn't before it was updated
        # Removing and readding is inefficient but it avoids problems if the
        # parent has multiple references to a given child.
        sql = """
            DELETE FROM {table} WHERE id = :id;
            """.format(table=ObjectDbManager._HierarchyTableName)
        cursor.execute(sql, {'id': entity.id()})

        if children:
            sql = """
                INSERT INTO {table} (id, child)
                VALUES (?, ?);
                """.format(table=ObjectDbManager._HierarchyTableName)
            cursor.executemany(
                sql,
                [(entity.id(), childEntity.id()) for childEntity in children])

    def _deleteEntity(
            self,
            id: str,
            cursor: sqlite3.Cursor
            ) -> None:
        # This beast of a query was generated by chat-gpt as an optimisation
        # on my implementation that did the recursion in code with multiple
        # queries. It retrieves entity entity data for the parent hierarchy
        # of the objected with the specified id
        sql = """
            WITH RECURSIVE parent_hierarchy(id, child, table_name) AS (
                -- Anchor: Start with the given child ID
                SELECT h.id, h.child, e.table_name
                FROM {hierarchyTable} h
                JOIN {entitiesTable} e ON h.id = e.id
                WHERE h.child = :id

                UNION ALL

                -- Recursive step: Find all parents and their table_name
                SELECT h.id, h.child, e.table_name
                FROM {hierarchyTable} h
                JOIN {entitiesTable} e ON h.id = e.id
                INNER JOIN parent_hierarchy cte
                ON h.child = cte.id
            )
            SELECT id, child, table_name FROM parent_hierarchy;
            """.format(
                hierarchyTable=ObjectDbManager._HierarchyTableName,
                entitiesTable=ObjectDbManager._EntitiesTableName)
        cursor.execute(sql, {'id': id})
        results = cursor.fetchall()

        idToTableMap = {}
        childToParentsMap = {}
        for row in results:
            parent = row[0]
            child = row[1]
            table = row[2]

            idToTableMap[parent] = table

            parentList = childToParentsMap.get(child)
            if not parentList:
                parentList = []
                childToParentsMap[child] = parentList
            parentList.append(parent)

        hierarchies = self._constructParentHierarchies(
            entityId=id,
            childToParentsMap=childToParentsMap)

        toDelete = set()
        for hierarchy in hierarchies:
            deleteId = id
            parentTable = None
            columnsToNull = []

            # If this object is a mandatory part of its parent then deleting
            # the object must also delete the parent
            for parentId in hierarchy:
                parentTable = idToTableMap.get(parentId)

                if parentTable == ObjectDbManager._ListsTableName:
                    # The parent is a list so the current deleteId can be deleted,
                    # resulting in it being removed from the list
                    break

                # Get the object definition for this parent table
                objectDef = self._tableObjectDefMap.get(parentTable)
                if objectDef == None:
                    raise RuntimeError(
                        f'Parent object {parentId} uses table {parentTable} but has no object description')

                referenceColumns: typing.Dict[
                    str, # Column name
                    bool # Is optional
                    ] = {}
                for paramDef in objectDef.paramDefs():
                    if issubclass(paramDef.columnType(), DatabaseObject):
                        referenceColumns[paramDef.columnName()] = paramDef.isOptional()
                if referenceColumns:
                    sql = """
                        SELECT {columns}
                        FROM {table}
                        WHERE id = :id
                        LIMIT 1;
                        """.format(
                        columns=','.join(referenceColumns.keys()),
                        table=parentTable)
                    cursor.execute(sql, {'id': parentId})
                    row = cursor.fetchone()
                    if not row:
                        raise RuntimeError(f'Parent object {parentId} not found in {parentTable}')

                    columnsToNull = []
                    for index, (column, isOptional) in enumerate(referenceColumns.items()):
                        value = row[index]
                        if value == deleteId:
                            if not isOptional:
                                # This parameter is not optional so deleting the child means
                                # the parent must also be deleted. As it's going to be deleted
                                # there is no point nulling any parameters on the parent
                                columnsToNull.clear()
                                break
                            columnsToNull.append(column)

                    if columnsToNull:
                        # The parentId parameter that refers to the current deleteId is
                        # an optional object reference so the column can be nulled and
                        # deleteId deleted
                        break

                # The deleteId entity is a mandatory part of the of the parentId
                # entity so deleting it also deletes the parent
                deleteId = parentId

            if deleteId != id:
                logging.debug(f'ObjectDbManager deleting object {id} requires deleting object {deleteId}')

            if parentTable and columnsToNull:
                # Null the column that refers to the object being deleted
                setStrings = [f'{column} = NULL' for column in columnsToNull]
                sql = """
                    UPDATE {table}
                    SET {sets}
                    WHERE id = :id;
                    """.format(
                        table=parentTable,
                        sets=', '.join(setStrings))
                cursor.execute(sql, {'id': parentId})

            toDelete.add(deleteId)

        if not toDelete:
            # Specified object has no parent hierarchies so just delete the object
            assert(not hierarchies)
            toDelete.add(id)

        for entityId in toDelete:
            self._unsafeDeleteHierarchy(
                entityId=entityId,
                cursor=cursor)

    def _deleteEntities(
            self,
            type: typing.Type[DatabaseEntity],
            cursor: sqlite3.Cursor
            ) -> None:
        if type == DatabaseList:
            # I can't think why you'd ever want to do this
            raise ValueError('Deleting all DatabaseList entities is not allowed')

        objectDef = self._classObjectDefMap.get(type)
        if not objectDef:
            raise ValueError(f'Unable to delete entities of unknown type {type}')

        # Delete all objects that have no parent. This may or may not
        # get all of them. Deleting objects with a parent is more
        # complex as it requires the parent to be updated (or possibly
        # deleted). This will trigger a cascade delete that will delete
        # remove the deleted objects and their children from all tables
        sql = """
            WITH has_parent AS (
                SELECT DISTINCT h1.id
                FROM {hierarchyTable} h1
                LEFT JOIN {hierarchyTable} h2 ON h1.id = h2.child
                WHERE h2.child IS NULL
            )
            SELECT id FROM {entityTable}
            WHERE table_name = "{objectTable}"
            AND id IN (
                SELECT id
                FROM has_parent
            );
            """.format(
                entityTable=ObjectDbManager._EntitiesTableName,
                hierarchyTable=ObjectDbManager._HierarchyTableName,
                objectTable=objectDef.tableName())
        cursor.execute(sql)
        for row in cursor.fetchall():
            entityId = row[0]
            self._unsafeDeleteHierarchy(
                entityId=entityId,
                cursor=cursor)

        # Check to see if there are any entries with parents left.
        # If there are call _deleteEntity on them
        sql = """
            SELECT id
            FROM {entityTable}
            WHERE table_name = "{objectTable}";
            """.format(
                entityTable=ObjectDbManager._EntitiesTableName,
                objectTable=objectDef.tableName())
        cursor.execute(sql)
        for rowData in cursor.fetchall():
            self._deleteEntity(id=rowData[0], cursor=cursor)

    def _deleteIfOnlyReference(
            self,
            entityId: str,
            parentId: str,
            cursor: sqlite3.Cursor
            ) -> bool:
        refCount = self._calculateReferenceCount(
            entityId=entityId,
            ignoreId=parentId,
            cursor=cursor)
        if refCount != 0:
            return False

        self._unsafeDeleteHierarchy(
            entityId=entityId,
            cursor=cursor)
        return True

    # This function is classed as unsafe as it deletes the specified entity
    # without checking if it's referenced by any other objects (child reference
    # counting is performed). It's assumed that the caller has already checked
    # that the entity is safe to delete. This means the specified entity will
    # always be deleted (if it exists) and any parts of the child hierarchy that
    # aren't referenced by other entities will also be deleted. The entities
    # parent hierarchy isn't modified. If the entity has a parent hierarchy it
    # is assumed the caller will take appropriate action to prevent dangling
    # references
    def _unsafeDeleteHierarchy(
            self,
            entityId: str,
            cursor: sqlite3.Cursor
            ) -> None:
        sql = """
            -- Determine the entities that make up the hierarchy under a
            -- specified entity. There will be an entry for each time a given
            -- entity appears in the hierarchy.
            WITH RECURSIVE entity_hierarchy AS (
                -- Anchor member: Start with the given ID and its exclusive
                -- children.
                SELECT id
                FROM {entitiesTable}
                WHERE id = :id

                UNION ALL

                -- Recursive member: Find exclusive children of the current
                -- level
                SELECT h.child AS id
                FROM {hierarchyTable} h
                INNER JOIN entity_hierarchy cte ON h.id = cte.id
            ),
            -- Calculate the reference count of each entity in the hierarchy
            ref_counts AS (
                SELECT
                    DISTINCT(id),
                    (
                        SELECT COUNT(*)
                        FROM {hierarchyTable}
                        WHERE child = h.id
                    ) AS ref_count
                FROM entity_hierarchy h
            )
            -- Select the entries from the hierarchy table for the entities in
            -- the hierarchy. This captures the child data for the hierarchy.
            -- The reference count for the entity (not child) is included on
            -- each row. If there are multiple entries in the hierarchy table
            -- for a given entity then this will result in the reference count
            -- being duplicated for each row but that's not a problem
            SELECT
                h.id,
                h.child,
                r.ref_count
            FROM {hierarchyTable} h
            LEFT JOIN ref_counts r ON r.id = h.id
            WHERE h.id IN (
                SELECT id
                FROM ref_counts
            )

            UNION ALL

            -- Add entries for each leaf entities in the hierarchy. This will
            -- add a single row per entity with just the reference count. As
            -- it's a leaf entity there is no child data.
            SELECT
                r.id,
                NULL AS child,
                r.ref_count
            FROM ref_counts r
            WHERE r.id NOT IN (
                SELECT id
                FROM {hierarchyTable}
            )
            """.format(
                entitiesTable=ObjectDbManager._EntitiesTableName,
                hierarchyTable=ObjectDbManager._HierarchyTableName)
        cursor.execute(sql, {"id": entityId})
        childMap: typing.Dict[str, typing.List[str]] = {}
        refCountMap: typing.Dict[str, int] = {}
        for row in cursor.fetchall():
            parent = row[0]
            child = row[1]
            parentRefCount = row[2]

            if child:
                childList = childMap.get(parent)
                if not childList:
                    childList = []
                    childMap[parent] = childList
                childList.append(child)

            refCountMap[parent] = parentRefCount

        toDelete: typing.Set[str] = set()
        toDelete.add(entityId)
        self._recursiveDeleteCheck(
            entityId=entityId,
            childMap=childMap,
            refCountMap=refCountMap,
            toDelete=toDelete)

        sql = """
            DELETE FROM {entityTable}
            WHERE id IN ({placeholders})
            """.format(
                entityTable=ObjectDbManager._EntitiesTableName,
                placeholders=', '.join('?' for _ in toDelete))
        cursor.execute(sql, list(toDelete))

    def _recursiveDeleteCheck(
            self,
            entityId: str,
            childMap: typing.Mapping[str, typing.Iterable[str]],
            refCountMap: typing.Mapping[str, int],
            toDelete: typing.Set[str],
            canDelete: typing.Optional[typing.List[str]] = True,
            deleteCountMap: typing.Optional[typing.Dict[
                str, # Entity id
                int # Number of instances deleted
                ]] = None,
            processedLinks: typing.Optional[typing.Set[typing.Tuple[
                str, # Parent id
                str # Child id
                ]]] = None,
            ) -> None:
        if deleteCountMap == None:
            deleteCountMap = {}
        if processedLinks == None:
            processedLinks = set()

        childList = childMap.get(entityId)
        if not childList:
            return

        for childId in childList:
            if (entityId, childId) not in processedLinks:
                # Only update the delete count for the child if the parent/child
                # pair hasn't already been processed in another part of the
                # hierarchy. This avoids the delete being counted multiple times
                # if there are multiple entities holding references to the
                # _parent_ entity.
                if childId not in deleteCountMap:
                    deleteCountMap[childId] = 1
                else:
                    deleteCountMap[childId] += 1

            childCanDelete = canDelete
            if canDelete:
                refCount = refCountMap[childId]
                if deleteCountMap[childId] >= refCount:
                    # We know that its safe to delete the child and possibly its
                    # some/all of its children (if it has any)
                    toDelete.add(childId)
                else:
                    # We don't know if the child can be deleted yet so it's not
                    # safe to delete any of its children
                    childCanDelete = False

            self._recursiveDeleteCheck(
                entityId=childId,
                childMap=childMap,
                refCountMap=refCountMap,
                toDelete=toDelete,
                canDelete=childCanDelete,
                deleteCountMap=deleteCountMap,
                processedLinks=processedLinks)

        # Add parent/child links to the processed list. This is done after
        # recursing over all the children as an entity can have multiple
        # references to the same child (e.g. a list could contain the same
        # child multiple times). In that situation we need each instance
        # of the child to be processed as each one is it's own independent
        # reference. If the processed links list was updated during the
        # initial iteration then all but the first instance of the child
        # would be skipped.
        for childId in childList:
            processedLinks.add((entityId, childId))

    def _constructParentHierarchies(
            self,
            entityId: str,
            childToParentsMap: typing.Mapping[str, str],
            currentHierarchy: typing.Optional[typing.List[str]] = None
            ) -> typing.Iterable[typing.Iterable[str]]:
        parentList = childToParentsMap.get(entityId)
        if not parentList:
            return [currentHierarchy] if currentHierarchy else []

        results = []
        for parentId in parentList:
            if currentHierarchy != None and parentId in currentHierarchy:
                raise RuntimeError(f'Entity {parentId} is part of its own hierarchy')

            newHierarchy = list(currentHierarchy) if currentHierarchy else list()
            newHierarchy.append(parentId)

            results.extend(self._constructParentHierarchies(
                entityId=parentId,
                childToParentsMap=childToParentsMap,
                currentHierarchy=newHierarchy))
        return results

    def _calculateReferenceCount(
            self,
            entityId: str,
            cursor: sqlite3.Cursor,
            ignoreId: typing.Optional[str] = None
            ) -> int:
        if ignoreId != None:
            sql = """
                SELECT COUNT(*)
                FROM {table}
                WHERE child = :id
                AND id != :ignoreId;
                """.format(table=ObjectDbManager._HierarchyTableName)
            cursor.execute(sql, {'id': entityId, 'ignoreId': ignoreId})
        else:
            sql = """
                SELECT COUNT(*)
                FROM {table}
                WHERE child = :id;
                """.format(table=ObjectDbManager._HierarchyTableName)
            cursor.execute(sql, {'id': entityId})
        result = cursor.fetchone()
        return result[0]

    def _handleBeginTransaction(
            self,
            connection: sqlite3.Connection
            ) -> None:
        cursor = connection.cursor()
        try:
            cursor.execute('BEGIN;')

            # Clear out change table so it can capture changes made during the
            # transaction. This needs to be done, even though it gets cleared
            # out at the end of the transacting, in case an operation external
            # to the system has left entries lying around (e.g. from a manual
            # edit with the db browser)
            sql = """
                DELETE FROM {table};
                """.format(
                    table=self._ChangeLogTableName)
            cursor.execute(sql)
        except:
            connection.close()
            raise

    def _handleEndTransaction(
            self,
            connection: sqlite3.Connection
            ) -> None:
        cursor = connection.cursor()
        try:
            # Read changes
            sql = """
                SELECT operation, entity, table_name FROM {table};
                """.format(
                    table=self._ChangeLogTableName)
            cursor.execute(sql)
            changes: typing.List[typing.Tuple[ObjectDbOperation, str, typing.Type[DatabaseEntity]]] = []
            results = cursor.fetchall()

            for changeData in results:
                operation, entity, tableName = changeData
                operation = common.enumFromValue(
                    enumType=ObjectDbOperation,
                    value=operation)
                if not operation:
                    logging.warning(
                        f'ObjectDbManager ignoring change {changeData} as operation type is unknown')
                    continue

                if tableName == ObjectDbManager._ListsTableName:
                    entityType = DatabaseList
                elif tableName in self._tableObjectDefMap:
                    objectDef = self._tableObjectDefMap[tableName]
                    entityType = objectDef.classType()
                else:
                    logging.warning(
                        f'ObjectDbManager ignoring change {changeData} as table is unknown')
                    continue

                logging.debug(f'ObjectDbManager transaction {operation.name} {entity} in {tableName}')
                changes.append((operation, entity, entityType))

            # Clear changes
            sql = """
                DELETE FROM {table};
                """.format(
                    table=self._ChangeLogTableName)
            cursor.execute(sql)

            # End the transaction
            cursor.execute('END;')
        except:
            try:
                # Not sure if an explicit rollback is actually needed
                # when an uncommitted transaction has failed but but
                # give it a shot just in case
                cursor.execute('ROLLBACK;')
            except Exception as ex:
                logging.debug(
                    f'ObjectDbManager failed to roll back failed transaction', exc_info=ex)
            connection.close()
            raise

        # Only reuse the connection if the transaction completed
        # successfully
        self._poolReusableConnection(connection=connection)

        # Determine which notification callbacks need to be made. The
        # calls aren't actually made here as we want to release the
        # lock while making them but determining which calls to make
        # must be done with the lock held
        callsToMake = []
        with ObjectDbManager._lock:
            for changeData in changes:
                operation, entity, entityType = changeData
                callbackList = None

                for callbackType in self._changeTypeCallbackMap.keys():
                    registeredOperation, registeredKey = callbackType
                    matched = True
                    if registeredOperation != None and registeredKey != None:
                        matched = (operation == registeredOperation) and \
                            ((entity == registeredKey) or (entityType == registeredKey))
                    elif registeredOperation != None:
                        matched = operation == registeredOperation
                    elif registeredKey != None:
                        matched = (entity == registeredKey) or (entityType == registeredKey)

                    if matched:
                        callbackMap = self._changeTypeCallbackMap[callbackType]

                        if not callbackList:
                            callbackList = []
                        callbackList.extend(callbackMap.values())

                if callbackList:
                    callsToMake.append((changeData, callbackList))

        # Call change callbacks. This MUST be done after END has been executed
        # as observers may make new transactions when notified
        if callsToMake:
            for changeData, callbackList in callsToMake:
                operation, entity, entityType = changeData
                for callback in callbackList:
                    try:
                        callback(operation, entity, entityType)
                    except Exception as ex:
                        logging.error(
                            'ObjectDbManager caught exception thrown by change callback', exc_info=ex)
                        continue

    def _handleRollbackTransaction(
            self,
            connection: sqlite3.Connection
            ) -> None:
        cursor = connection.cursor()
        try:
            cursor.execute('ROLLBACK;')
        finally:
            # Never add connections back to the pool if they've been
            # rolled back as we can't be sure what state they're in.
            # I suspect it's ok if the rollback completes successful
            # but it's better to be safe than have some horrible bug
            connection.close()

    def _handleDisconnectChangeCallback(
            self,
            handle: str
            ) -> None:
        with ObjectDbManager._lock:
            changeType = self._handleChangeTypeMap.get(handle)
            if not changeType:
                raise ValueError(f'Unknown change handle {handle}')
            del self._handleChangeTypeMap[handle]

            callbackMap = self._changeTypeCallbackMap.get(changeType)
            if handle not in callbackMap:
                raise RuntimeError(f'Change handle {handle} was not in the callback map')
            del callbackMap[handle]

            if not callbackMap:
                del self._changeTypeCallbackMap[changeType]
