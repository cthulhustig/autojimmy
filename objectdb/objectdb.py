import common
import logging
import sqlite3
import threading
import typing
import uuid

class DatabaseEntity(object):
    def __init__(
            self,
            id: typing.Optional[str] = None,
            parent: typing.Optional[str] = None
            ) -> None:
        super().__init__()
        self._id = id if id != None else str(uuid.uuid4())
        self._parent = parent

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DatabaseEntity):
            return self._id == other._id and \
                self._parent == other._parent
        return False

    def id(self) -> str:
        return self._id

    def setId(self, id: str) -> None:
        self._id = id

    def parent(self) -> typing.Optional[str]:
        return self._parent

    def setParent(self, parent: typing.Optional[str]) -> None:
        if parent and self._parent:
            raise RuntimeError(f'Object {self._id} already has a parent')
        self._parent = parent

class DatabaseObject(DatabaseEntity):
    def __init__(
            self,
            id: typing.Optional[str] = None,
            parent: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, parent=parent)

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
            parent: typing.Optional[str],
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
            id: typing.Optional[str] = None,
            parent: typing.Optional[str] = None,
            ) -> None:
        super().__init__(id=id, parent=parent)
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
        seen = set()
        for item in content:
            if isinstance(item, DatabaseEntity):
                if item.id() in seen:
                    raise ValueError(f'Init content for list {self._id} can\'t contain objects with duplicate ids')
                seen.add(item.id())

        self.clear()
        for item in content:
            if isinstance(item, DatabaseEntity):
                item.setParent(self.id())
            self._content.append(item)

    def add(
            self,
            item: typing.Union[bool, int, float, str, DatabaseEntity]
            ) -> None:
        if isinstance(item, DatabaseEntity):
            for other in self._content:
                if isinstance(other, DatabaseEntity) and other.id() == item.id():
                    raise ValueError(f'Duplicate entity {item.id()} can\'t be added to list {self.id()}')
            item.setParent(self.id())

        self._content.append(item)

    def insert(
            self,
            index: int,
            item: typing.Union[bool, int, float, str, DatabaseEntity]
            ) -> None:
        if isinstance(item, DatabaseEntity):
            for other in self._content:
                if isinstance(other, DatabaseEntity) and other.id() == item.id():
                    raise ValueError(f'Duplicate entity {item.id()} can\'t be inserted into to list {self.id()}')
            item.setParent(self.id())

        self._content.insert(index, item)

    def remove(
            self,
            index: int
            ) -> typing.Union[bool, int, float, str, DatabaseEntity]:
        item = self._content[index]
        del self._content[index]

        if isinstance(item, DatabaseEntity):
            item.setParent(None)

        return item

    def removeById(self, id: str) -> DatabaseEntity:
        for item in self._content:
            if isinstance(item, DatabaseEntity) and id == item.id():
                self._content.remove(item)
                item.setParent(None)
                return item
        raise ValueError(f'Entity {id} not found in list {self.id()}')

    def clear(self) -> None:
        for item in self._content:
            if isinstance(item, DatabaseEntity):
                item.setParent(None)
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
            cursor: sqlite3.Cursor
            ) -> None:
        self._cursor = cursor

    def cursor(self) -> sqlite3.Cursor:
        return self._cursor

    def begin(self) -> 'Transaction':
        self._cursor.execute('BEGIN;')
        return self

    def end(self) -> None:
        self._cursor.execute('END;')

    def rollback(self) -> None:
        self._cursor.execute('ROLLBACK;')

    def __enter__(self) -> 'Transaction':
        return self.begin()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.end()
        else:
            self.rollback()

class ObjectDbManager(object):
    class UnsupportedDatabaseVersion(RuntimeError):
        pass

    _DatabasePath = 'test.db'
    _PragmaScript = """
        PRAGMA foreign_keys = ON;
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;
        """
    _SchemasTableName = 'objectdb_table_schemas'
    _EntitiesTableName = 'objectdb_entities'
    _EntitiesTableSchema = 1
    _ListsTableName = 'objectdb_lists'
    _ListsTableSchema = 1

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _connection = None
    _tableObjectDefMap: typing.Dict[str, ObjectDef] = {}
    _classObjectDefMap: typing.Dict[typing.Type[DatabaseObject], ObjectDef] = {}

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

    def initialise(
            self,
            databasePath: str
            ) -> None:
        logging.info(f'ObjectDbManager connecting to {databasePath}')

        with ObjectDbManager._lock:
            if self._connection:
                raise RuntimeError('ObjectDbManager singleton has already been initialised')

            self._connection = sqlite3.connect(databasePath)
            self._connection.executescript(ObjectDbManager._PragmaScript)
            # Uncomment this to have sqlite print the SQL that it executes
            #self._connection.set_trace_callback(print)

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

            with self.createTransaction() as transaction:
                cursor = transaction.cursor()

                # Create schema table
                if not self._checkIfTableExists(
                    tableName=ObjectDbManager._SchemasTableName,
                    cursor=cursor):
                    sql = """
                        CREATE TABLE IF NOT EXISTS {table} (
                            table_name TEXT PRIMARY KEY NOT NULL,
                            schema INTEGER
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
                            parent TEXT,
                            table_name TEXT NOT NULL,
                            FOREIGN KEY(parent) REFERENCES {table}(id) ON DELETE CASCADE
                        ) WITHOUT ROWID;
                        """.format(table=ObjectDbManager._EntitiesTableName)
                    logging.info(f'ObjectDbManager creating \'{ObjectDbManager._EntitiesTableName}\' table')
                    cursor.execute(sql)

                    self._writeSchema(
                        table=ObjectDbManager._EntitiesTableName,
                        schema=ObjectDbManager._EntitiesTableSchema,
                        cursor=cursor)

                    # Create schema table indexes for id and parent columns. The id
                    # index is needed as, even though it's the primary key, it's of
                    # type TEXT so doesn't automatically get indexes
                    self._createColumnIndex(
                        table=ObjectDbManager._EntitiesTableName,
                        column='id',
                        unique=True,
                        cursor=cursor)
                    self._createColumnIndex(
                        table=ObjectDbManager._EntitiesTableName,
                        column='parent',
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

                    self._writeSchema(
                        table=ObjectDbManager._ListsTableName,
                        schema=ObjectDbManager._ListsTableSchema,
                        cursor=cursor)

                    # Create schema table indexes for id columns
                    self._createColumnIndex(
                        table=ObjectDbManager._ListsTableName,
                        column='id',
                        unique=False,
                        cursor=cursor)

                # Check there are no tables with schemas newer than this version supports
                tableSchemas = self._readSchemas(cursor=cursor)
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

            self._tableObjectDefMap.update(tableObjectDefs)
            self._classObjectDefMap.update(classObjectDefs)

    def createTransaction(self) -> Transaction:
        return Transaction(cursor=self._connection.cursor())

    def createObject(
            self,
            object: DatabaseObject,
            transaction: typing.Optional[Transaction] = None
            ) -> str:
        if object.parent() != None:
            # The parent should be created/updated rather than creating the child.
            # The prevents the database become corrupt because there is a parent
            # set for the object but the parent doesn't refer to it (or possibly
            # doesn't exit at all)
            raise ValueError('Object to be created can\'t have a parent')

        logging.debug(f'ObjectDbManager creating object {object.id()} of type {type(object)}')
        with ObjectDbManager._lock:
            if transaction != None:
                self._createEntity(
                    entity=object,
                    cursor=transaction.cursor())
            else:
                with self.createTransaction() as transaction:
                    self._createEntity(
                        entity=object,
                        cursor=transaction.cursor())

    def readObject(
            self,
            id: str,
            transaction: typing.Optional[Transaction] = None
            ) -> DatabaseObject:
        logging.debug(f'ObjectDbManager reading object {id}')
        with ObjectDbManager._lock:
            if transaction != None:
                return self._readEntity(
                    id=id,
                    cursor=transaction.cursor())
            else:
                # Use a transaction for the read to ensure a consistent
                # view of the database across multiple selects
                with self.createTransaction() as transaction:
                    return self._readEntity(
                        id=id,
                        cursor=transaction.cursor())

    def readObjects(
            self,
            classType: typing.Type[DatabaseObject],
            transaction: typing.Optional[Transaction] = None
            ) -> typing.Iterable[DatabaseObject]:
        logging.debug(f'ObjectDbManager reading objects of type {classType}')
        with ObjectDbManager._lock:
            if transaction != None:
                return self._readEntities(
                    classType=classType,
                    cursor=transaction.cursor())
            else:
                # Use a transaction for the read to ensure a consistent
                # view of the database across multiple selects
                with self.createTransaction() as transaction:
                    return self._readEntities(
                        classType=classType,
                        cursor=transaction.cursor())

    def updateObject(
            self,
            object: DatabaseObject,
            transaction: typing.Optional[Transaction] = None
            ) -> None:
        logging.debug(f'ObjectDbManager updating object {object.id()} of type {type(object)}')
        with ObjectDbManager._lock:
            if transaction != None:
                self._updateEntity(
                    entity=object,
                    cursor=transaction.cursor())
            else:
                with self.createTransaction() as transaction:
                    self._updateEntity(
                        entity=object,
                        cursor=transaction.cursor())

    def deleteObject(
            self,
            id: str,
            transaction: typing.Optional[Transaction] = None
            ) -> None:
        logging.debug(f'ObjectDbManager deleting object {id}')
        with ObjectDbManager._lock:
            if transaction != None:
                self._deleteEntity(
                    id=id,
                    cursor=transaction.cursor())
            else:
                with self.createTransaction() as transaction:
                    self._deleteEntity(
                        id=id,
                        cursor=transaction.cursor())

    def _checkIfTableExists(
            self,
            tableName: str,
            cursor: sqlite3.Cursor
            ) -> bool:
        sql = 'SELECT name FROM sqlite_master WHERE type = "table" AND name = :table;'
        cursor.execute(sql, {'table': tableName})
        return cursor.fetchone() != None

    def _readSchemas(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.Mapping[str, int]:
        sql = """
            SELECT table_name, schema
            FROM {table};
            """.format(
            table=ObjectDbManager._SchemasTableName)
        cursor.execute(sql)
        schemas = {}
        for row in cursor.fetchall():
            tableName = row[0]
            schema = int(row[1])
            schemas[tableName] = schema

        return schemas

    def _writeSchema(
            self,
            table: str,
            schema: int,
            cursor: sqlite3.Cursor
            ) -> None:
        sql = """
            INSERT INTO {table} (table_name, schema)
            VALUES (:table_name, :schema)
            ON CONFLICT(table_name) DO UPDATE SET
                schema = excluded.schema;
            """.format(table=ObjectDbManager._SchemasTableName)
        logging.info(f'ObjectDbManager setting table schema for \'{table}\' to {schema}')
        rowData = {
            'table_name': table,
            'schema': str(schema)}
        cursor.execute(sql, rowData)

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
            CREATE TABLE IF NOT EXISTS {table} ({columns}) WITHOUT ROWID;
            """.format(
            table=objectDef.tableName(),
            columns=', '.join(columnStrings))
        logging.info(f'ObjectDbManager creating \'{objectDef.tableName()}\' table')
        cursor.execute(sql)

        self._writeSchema(
            table=objectDef.tableName(),
            schema=objectDef.tableSchema(),
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
        if isinstance(entity, DatabaseObject):
            objectDef = self._classObjectDefMap.get(type(entity))
            if objectDef == None:
                raise ValueError(f'Failed to create {type(entity)} (Unknown object type)')

            sql = 'INSERT INTO {table} VALUES (:id, :parent, :table_name)'.format(
                table=ObjectDbManager._EntitiesTableName)
            rowData = {
                'id': entity.id(),
                'parent': entity.parent(),
                'table_name': objectDef.tableName()
            }
            cursor.execute(sql, rowData)

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

                childEntity = None
                columnType = paramDef.columnType()
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
                    self._createEntity(
                        entity=childEntity,
                        cursor=cursor)
            sql += ');'

            cursor.execute(sql, rowData)
        elif isinstance(entity, DatabaseList):
            # Always insert list into entity table, even if doesn't
            # have any entries in the list table because it's empty
            sql = 'INSERT INTO {table} VALUES (:id, :parent, :table_name)'.format(
                table=ObjectDbManager._EntitiesTableName)
            rowData = {
                'id': entity.id(),
                'parent': entity.parent(),
                'table_name': ObjectDbManager._ListsTableName
            }
            cursor.execute(sql, rowData)

            rowData = []
            for child in entity:
                if isinstance(child, DatabaseEntity):
                    self._createEntity(entity=child, cursor=cursor)

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

    def _readEntity(
            self,
            id: str,
            cursor: sqlite3.Cursor,
            table: typing.Optional[str] = None,
            setParent: bool = True
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
            parent = None
            if setParent:
                sql = """
                    SELECT parent
                    FROM {table}
                    WHERE id = :id
                    LIMIT 1;
                    """.format(
                    table=ObjectDbManager._EntitiesTableName)
                cursor.execute(sql, {'id': id})
                row = cursor.fetchone()
                if not row:
                    raise RuntimeError(f'Parent for {id} not found in entity table')
                parent = row[0]

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
                        setParent=False,
                        cursor=cursor))

            return DatabaseList(
                id=id,
                parent=parent,
                content=content)
        else:
            objectDef = self._tableObjectDefMap.get(table)
            if objectDef == None:
                raise ValueError(f'Object {id} uses unknown table {table}')
            columns = ['{table}.parent'.format(table=ObjectDbManager._EntitiesTableName)]
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

            parent = row[0] if setParent else None
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
                            setParent=False,
                            cursor=cursor)
                else:
                    raise RuntimeError(
                        f'Parameter {columnName} for object {id} of type {objectDef.classType()} has unknown type {columnType}')

                objectData[columnName] = columnValue

            classType = objectDef.classType()
            return classType.createObject(
                id=id,
                parent=parent,
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
            '{table}.id'.format(table=objectDef.tableName()),
            '{table}.parent'.format(table=ObjectDbManager._EntitiesTableName)
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
            parent = row[1]
            objectData = {}
            columnIndex = 2
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
                            setParent=False,
                            cursor=cursor)
                else:
                    raise RuntimeError(
                        f'Parameter definition {objectDef.classType()}.{columnName} has unknown type {columnType}')

                objectData[columnName] = columnValue

            classType = objectDef.classType()
            objects.append(classType.createObject(
                id=id,
                parent=parent,
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
        if isinstance(entity, DatabaseObject):
            objectDef = self._classObjectDefMap.get(type(entity))
            if objectDef == None:
                raise ValueError(f'Object {entity.id()} uses unknown type {type(entity)}')

            paramDefs = objectDef.paramDefs()
            columnNames = [paramDef.columnName() for paramDef in paramDefs]

            # Update the entities table metadata
            sql = """
                INSERT INTO {table} (id, parent, table_name)
                VALUES (:id, :parent, :table)
                ON CONFLICT(id) DO UPDATE SET
                    parent = excluded.parent,
                    table_name = excluded.table_name;
                """.format(table=ObjectDbManager._EntitiesTableName)
            rowData = {
                'id': entity.id(),
                'parent': entity.parent(),
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

                isReference = False
                childEntity = None
                columnType = paramDef.columnType()
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
                        columnValue = columnValue.id()
                else:
                    raise RuntimeError(
                        f'Parameter {columnName} for object {entity.id()} of type {objectDef.classType()} has unknown type {columnType}')

                rowData[columnName] = columnValue

                if isReference and (exitingValues != None):
                    oldId = exitingValues[index]
                    if oldId != None and oldId != columnValue:
                        sql = """
                            DELETE FROM {table}
                            WHERE id = :id;
                            """.format(table=ObjectDbManager._EntitiesTableName)
                        cursor.execute(sql, {'id': oldId})

                if childEntity != None:
                    # Recursively update the child entity
                    self._updateEntity(entity=childEntity, cursor=cursor)

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
                INSERT INTO {table} (id, parent, table_name)
                VALUES (:id, :parent, :table)
                ON CONFLICT(id) DO UPDATE SET
                    parent = excluded.parent,
                    table_name = excluded.table_name;
                """.format(table=ObjectDbManager._EntitiesTableName)
            rowData = {
                'id': entity.id(),
                'parent': entity.parent(),
                'table': ObjectDbManager._ListsTableName}
            cursor.execute(sql, rowData)

            # Delete any children that were in the list but aren't any more
            contentIds = [child.id() for child in entity if isinstance(child, DatabaseEntity)]
            sql = """
                DELETE FROM {entitiesTable}
                WHERE id IN (
                    SELECT entity
                    FROM {listsTable}
                    WHERE id = ?
                    AND entity NOT IN ({placeholders})
                );
            """.format(
                entitiesTable=ObjectDbManager._EntitiesTableName,
                listsTable=ObjectDbManager._ListsTableName,
                placeholders=', '.join('?' for _ in contentIds))
            rowData = [entity.id()] + contentIds
            cursor.execute(sql, rowData)

            # Recursively update list children. This must be done before
            # the inserting items into the list for them in order to
            # avoid failing foreign key checks
            for child in entity:
                self._updateEntity(entity=child, cursor=cursor)

            # Remove all existing items for the list and add the new ones.
            # This is a bit inefficient if the majority of the same objects
            # are still in the list, however it has the advantage that it
            # keeps the order of the items in the db the same as the order
            # the list object has them
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

    def _deleteEntity(
            self,
            id: str,
            cursor: sqlite3.Cursor
            ) -> None:
        # This beast of a query was generated by chat-gpt as an optimisation
        # on my implementation that did the recursion in code with multiple
        # queries
        fetchHierarchySql = """
            WITH RECURSIVE ParentHierarchy(id, parent, table_name) AS (
                SELECT id, parent, table_name
                FROM {table}
                WHERE id = :id
                UNION ALL
                SELECT e.id, e.parent, e.table_name
                FROM {table} e
                JOIN ParentHierarchy ph ON e.id = ph.parent
            )
            SELECT id, parent, table_name
            FROM ParentHierarchy;
            """.format(table=ObjectDbManager._EntitiesTableName)
        cursor.execute(fetchHierarchySql, {'id': id})
        hierarchy = cursor.fetchall()

        if not hierarchy:
            raise RuntimeError(f'Object {id} not found in entity table')

        idToParentMap = {row[0]: (row[1], row[2]) for row in hierarchy}
        deleteId = id
        parentId, parentTable = idToParentMap.get(id)
        columnToNull = None

        # If this object is a mandatory part of its parent then deleting
        # the object must also delete the parent
        while parentId != None:
            nextParentId, parentTable = idToParentMap.get(parentId, (None, None))

            if parentTable == ObjectDbManager._ListsTableName:
                # The parent is a list so the current deleteId can be deleted,
                # resulting in it being removed from the list
                break

            # Get the object definition for this parent table
            objectDef = self._tableObjectDefMap.get(parentTable)
            if objectDef == None:
                raise RuntimeError(
                    f'Parent object {parentId} uses table {parentTable} but has no object description')

            columns = []
            for paramDef in objectDef.paramDefs():
                if issubclass(paramDef.columnType(), DatabaseObject) and paramDef.isOptional():
                    columns.append(paramDef.columnName())
            if columns:
                fetchDataSql = """
                    SELECT {columns}
                    FROM {table}
                    WHERE id = :id
                    LIMIT 1;
                    """.format(
                    columns=','.join(columns),
                    table=parentTable)
                cursor.execute(fetchDataSql, {'id': parentId})
                row = cursor.fetchone()
                if not row:
                    raise RuntimeError(f'Parent object {parentId} not found in {parentTable}')

                for index, value in enumerate(row):
                    if value == deleteId:
                        columnToNull = columns[index]
                        break

                if columnToNull:
                    # The parentId parameter that refers to the current deleteId is
                    # an optional object reference so the column can be nulled and
                    # deleteId deleted
                    break

            # The deleteId entity is a mandatory part of the of the parentId
            # entity so deleting it also deletes the parent
            deleteId = parentId
            parentId = nextParentId

        if deleteId != id:
            logging.debug(f'ObjectDbManager deleting object {id} requires deleting object {deleteId}')

        if parentTable and columnToNull:
            # Null the column that refers to the object being deleted
            updateColumnSql = """
                UPDATE {table}
                SET {column} = NULL
                WHERE id = :id;
                """.format(
                table=parentTable,
                column=columnToNull)
            cursor.execute(updateColumnSql, {'id': parentId})

        # Delete the object. This deletes the entity table entry and assumes it
        # will trigger a delete cascade in the relevant entity tables that will
        # delete the object and its child entity hierarchy
        deleteEntitySql = """
            DELETE FROM {table}
            WHERE id = :id;
            """.format(table=ObjectDbManager._EntitiesTableName)
        cursor.execute(deleteEntitySql, {'id': deleteId})
