import common
import enum
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

    def data(self) -> typing.Mapping[str, typing.Any]:
        raise RuntimeError(f'{type(self)} is derived from DatabaseObject so must implement data')

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DatabaseObject):
            return super().__eq__(other)
        return False

class DatabaseList(DatabaseEntity):
    def __init__(
            self,
            objects: typing.Optional[typing.Iterable[DatabaseObject]] = None,
            id: typing.Optional[str] = None,
            parent: typing.Optional[str] = None,
            ) -> None:
        super().__init__(id=id, parent=parent)
        self._objects: typing.List[DatabaseObject] = []
        if objects:
            self.init(objects=objects)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DatabaseList):
            return super().__eq__(other) and \
                self._objects == other._objects
        return False

    def __iter__(self) -> typing.Iterator[DatabaseObject]:
        return self._objects.__iter__()

    def __next__(self) -> typing.Any:
        return self._objects.__next__()

    def __len__(self) -> int:
        return self._objects.__len__()

    def __getitem__(self, index: int) -> DatabaseObject:
        return self._objects.__getitem__(index)

    def init(self, objects: typing.Iterable[DatabaseObject]) -> None:
        seen = set(obj.id() for obj in objects)
        if len(seen) != len(objects):
            raise ValueError(f'Init object list can\'t contain objects with duplicate ids')

        self.clear()
        for object in objects:
            object.setParent(self.id())
            self._objects.append(object)

    def add(self, object: DatabaseObject) -> None:
        for current in self._objects:
            if current.id() == object.id():
                raise ValueError(f'Object {object.id()} is already in list {self.id()}')

        object.setParent(self.id())
        self._objects.append(object)

    def insert(self, index: int, object: DatabaseObject) -> None:
        for current in self._objects:
            if current.id() == object.id():
                raise ValueError(f'Object {object.id()} is already in list {self.id()}')

        object.setParent(self.id())
        self._objects.insert(index, object)

    def remove(self, id: str) -> DatabaseObject:
        for obj in self._objects:
            if id == obj.id():
                self._objects.remove(obj)
                obj.setParent(None)
                return obj
        raise ValueError(f'{id} not found in list {self.id()}')

    def find(self, id: str) -> typing.Optional[DatabaseObject]:
        for obj in self._objects:
            if id == obj.id():
                return obj
        return None

    def contains(self, id: str) -> bool:
        return self.find(id) != None

    def clear(self) -> None:
        for object in self._objects:
            object.setParent(None)
        self._objects.clear()

class ParamDef(object):
    class ColumnType(enum.Enum):
        Text = 0
        Integer = 1
        Float = 2
        Boolean = 3
        Enum = 4
        Object = 5
        List = 6

    def __init__(
            self,
            columnName: str,
            columnType: ColumnType,
            isOptional: bool = False,
            enumType: typing.Optional[typing.Type[enum.Enum]] = None
            ) -> None:
        if columnType == ParamDef.ColumnType.Enum:
            if not enumType:
                raise ValueError(f'No enum type specified for enum parameter {columnName}')
            if not issubclass(enumType, enum.Enum):
                raise ValueError(f'Invalid enum type {enumType} specified for enum parameter {columnName}')
        else:
            if enumType:
                raise ValueError(f'Unexpected enum type specified for non-enum parameter {columnName}')

        self._columnName = columnName
        self._columnType = columnType
        self._isOptional = isOptional
        self._enumType = enumType

    def columnName(self) -> str:
        return self._columnName

    def columnType(self) -> ColumnType:
        return self._columnType

    def isOptional(self) -> bool:
        return self._isOptional

    def enumType(self) -> typing.Optional[typing.Type[enum.Enum]]:
        return self._enumType

class ObjectDef(object):
    def __init__(
            self,
            tableName: str,
            classType: typing.Type['DatabaseObject'],
            paramDefs: typing.Iterable[ParamDef],
            ) -> None:
        self._tableName = tableName
        self._classType = classType
        self._paramDefs = paramDefs

    def tableName(self) -> str:
        return self._tableName

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
    _DatabasePath = 'test.db'
    _PragmaScript = """
        PRAGMA foreign_keys = ON;
        """
    _EntitiesTableName = 'entities'
    _ListsTableName = 'lists'

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

            classTypes = common.getSubclasses(
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

            with self._connection:
                cursor = self._connection.cursor()

                sql = """
                    CREATE TABLE IF NOT EXISTS {table} (
                        id TEXT PRIMARY KEY NOT NULL,
                        parent TEXT,
                        table_name TEXT NOT NULL,
                        FOREIGN KEY(parent) REFERENCES {table}(id) ON DELETE CASCADE
                    );
                    """.format(table=ObjectDbManager._EntitiesTableName)
                logging.info(f'ObjectDbManager initialising table \'{ObjectDbManager._EntitiesTableName}\'')
                cursor.execute(sql)

                sql = """
                    CREATE TABLE IF NOT EXISTS {table} (
                        id TEXT NOT NULL,
                        object TEXT NOT NULL,
                        FOREIGN KEY(id) REFERENCES {entitiesTable}(id) ON DELETE CASCADE
                        FOREIGN KEY(object) REFERENCES {entitiesTable}(id) ON DELETE CASCADE
                    );
                    """.format(
                    table=ObjectDbManager._ListsTableName,
                    entitiesTable=ObjectDbManager._EntitiesTableName)
                logging.info(f'ObjectDbManager initialising table \'{ObjectDbManager._ListsTableName}\'')
                cursor.execute(sql)

                for classType, objectDef in classObjectDefs.items():
                    columnStrings = ['id TEXT PRIMARY KEY NOT NULL']
                    for paramDef in objectDef.paramDefs():
                        columnString = paramDef.columnName()
                        columnType = paramDef.columnType()

                        if columnType == ParamDef.ColumnType.Text:
                            columnString += ' TEXT'
                        elif columnType == ParamDef.ColumnType.Integer:
                            columnString += ' INTEGER'
                        elif columnType == ParamDef.ColumnType.Float:
                            columnString += ' REAL'
                        elif columnType == ParamDef.ColumnType.Boolean:
                            columnString += ' INTEGER'
                        elif columnType == ParamDef.ColumnType.Enum:
                            columnString += ' TEXT'
                        elif columnType == ParamDef.ColumnType.Object:
                            columnString += ' TEXT'
                        elif columnType == ParamDef.ColumnType.List:
                            columnString += ' TEXT'
                        else:
                            raise RuntimeError(
                                f'Parameter definition {classType}.{paramDef.columnName()} has unknown type {columnType}')

                        if not paramDef.isOptional():
                            columnString += ' NOT NULL'

                        columnStrings.append(columnString)

                    columnStrings.append(
                        'FOREIGN KEY(id) REFERENCES {entitiesTable}(id) ON DELETE CASCADE'.format(
                            entitiesTable=ObjectDbManager._EntitiesTableName))

                    # NOTE: This breaks the cardinal rule of not manually formatting
                    # SQL statements, however, it's acceptable here as what it's
                    # formatting comes from code (rather than user input) so there is
                    # no real risk of sql injection
                    sql = 'CREATE TABLE IF NOT EXISTS {table} ({columns});'.format(
                        table=objectDef.tableName(),
                        columns=', '.join(columnStrings))
                    logging.info(f'ObjectDbManager initialising table \'{objectDef.tableName()}\'')
                    cursor.execute(sql)

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
                self._internalCreateEntity(
                    entity=object,
                    cursor=transaction.cursor())
            else:
                with self._connection:
                    self._internalCreateEntity(
                        entity=object,
                        cursor=self._connection.cursor())

    def readObject(
            self,
            id: str,
            transaction: typing.Optional[Transaction] = None
            ) -> DatabaseObject:
        logging.debug(f'ObjectDbManager reading object {id}')
        with ObjectDbManager._lock:
            if transaction != None:
                return self._internalReadEntity(
                    id=id,
                    cursor=transaction.cursor())
            else:
                # Use a transaction for the read to ensure a consistent
                # view of the database across multiple selects
                with self._connection:
                    return self._internalReadEntity(
                        id=id,
                        cursor=self._connection.cursor())

    def readObjects(
            self,
            classType: typing.Type[DatabaseObject],
            transaction: typing.Optional[Transaction] = None
            ) -> typing.Iterable[DatabaseObject]:
        logging.debug(f'ObjectDbManager reading object of type {classType}')
        with ObjectDbManager._lock:
            if transaction != None:
                return self._internalReadEntities(
                    classType=classType,
                    cursor=transaction.cursor())
            else:
                # Use a transaction for the read to ensure a consistent
                # view of the database across multiple selects
                with self._connection:
                    return self._internalReadEntities(
                        classType=classType,
                        cursor=self._connection.cursor())

    def updateObject(
            self,
            object: DatabaseObject,
            transaction: typing.Optional[Transaction] = None
            ) -> None:
        logging.debug(f'ObjectDbManager updating object {object.id()} of type {type(object)}')
        with ObjectDbManager._lock:
            if transaction != None:
                self._internalUpdateEntity(
                    entity=object,
                    cursor=transaction.cursor())
            else:
                with self._connection:
                    self._internalUpdateEntity(
                        entity=object,
                        cursor=self._connection.cursor())

    def deleteObject(
            self,
            id: str,
            transaction: typing.Optional[Transaction] = None
            ) -> None:
        logging.debug(f'ObjectDbManager deleting object {id}')
        with ObjectDbManager._lock:
            if transaction != None:
                self._internalDeleteEntity(
                    id=id,
                    cursor=transaction.cursor())
            else:
                with self._connection:
                    self._internalDeleteEntity(
                        id=id,
                        cursor=self._connection.cursor())

    def _internalCreateEntity(
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
            columnData = {
                'id': entity.id(),
                'parent': entity.parent(),
                'table_name': objectDef.tableName()
            }
            cursor.execute(sql, columnData)

            sql = 'INSERT INTO {table} VALUES (:id'.format(
                table=objectDef.tableName())
            columnData = {'id': entity.id()}
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
                if columnValue != None:
                    columnType = paramDef.columnType()
                    if columnType == ParamDef.ColumnType.Text:
                        columnValue = str(columnValue)
                    elif columnType == ParamDef.ColumnType.Integer:
                        columnValue = int(columnValue)
                    elif columnType == ParamDef.ColumnType.Float:
                        columnValue = float(columnValue)
                    elif columnType == ParamDef.ColumnType.Boolean:
                        columnValue = 1 if columnValue else 0
                    elif columnType == ParamDef.ColumnType.Enum:
                        if not isinstance(columnValue, enum.Enum) and \
                            not isinstance(columnValue, paramDef.enumType()):
                            raise RuntimeError(
                                f'Parameter {columnName} for object {entity.id()} of type {objectDef.classType()} is not an enum of type {paramDef.enumType()}')
                        columnValue = columnValue.name
                    elif columnType == ParamDef.ColumnType.Object:
                        if not isinstance(columnValue, DatabaseObject):
                            raise RuntimeError(
                                f'Parameter {columnName} for object {entity.id()} of type {objectDef.classType()} is not of type DatabaseObject')
                        childEntity = columnValue
                        columnValue = columnValue.id()
                    elif columnType == ParamDef.ColumnType.List:
                        if not isinstance(columnValue, DatabaseList):
                            raise RuntimeError(
                                f'Parameter {columnName} for object {entity.id()} of type {objectDef.classType()} is not of type DatabaseList')
                        childEntity = columnValue
                        columnValue = columnValue.id()
                    else:
                        raise RuntimeError(
                            f'Parameter {columnName} for object {entity.id()} of type {objectDef.classType()} has unknown type {columnType}')

                columnData[columnName] = columnValue

                if childEntity != None:
                    self._internalCreateEntity(
                        entity=childEntity,
                        cursor=cursor)
            sql += ');'

            cursor.execute(sql, columnData)
        elif isinstance(entity, DatabaseList):
            # Always insert list into entity table, even if doesn't
            # have any entries in the list table because it's empty
            sql = 'INSERT INTO {table} VALUES (:id, :parent, :table_name)'.format(
                table=ObjectDbManager._EntitiesTableName)
            columnData = {
                'id': entity.id(),
                'parent': entity.parent(),
                'table_name': 'lists'
            }
            cursor.execute(sql, columnData)

            columnData = []
            for child in entity:
                self._internalCreateEntity(entity=child, cursor=cursor)
                columnData.append((entity.id(), child.id()))
            if columnData:
                sql = 'INSERT INTO {table} (id, object) VALUES (?, ?)'.format(
                    table=ObjectDbManager._ListsTableName)
                cursor.executemany(sql, columnData)
        else:
            raise RuntimeError(f'Unexpected entity type {type(entity)}')

    def _internalReadEntity(
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
                SELECT object, table_name
                FROM {listsTable}
                JOIN {entitiesTable} ON {listsTable}.object = {entitiesTable}.id
                WHERE {listsTable}.id = :id;
                """.format(
                listsTable=ObjectDbManager._ListsTableName,
                entitiesTable=ObjectDbManager._EntitiesTableName)
            cursor.execute(sql, {'id': id})
            objects = []
            for row in cursor.fetchall():
                objects.append(self._internalReadEntity(
                    id=row[0],
                    table=row[1],
                    setParent=False,
                    cursor=cursor))

            return DatabaseList(
                id=id,
                parent=parent,
                objects=objects)
        else:
            objectDef = self._tableObjectDefMap.get(table)
            if objectDef == None:
                raise ValueError(f'Object {id} uses unknown table {table}')
            columns = ['{table}.parent'.format(table=ObjectDbManager._EntitiesTableName)]
            for paramDef in objectDef.paramDefs():
                columns.append('{table}.{column}'.format(
                    table=table,
                    column=paramDef.columnName()))

            sql = """
                SELECT {columns}
                FROM {dataTable}
                JOIN {entitiesTable} ON {dataTable}.id = {entitiesTable}.id
                WHERE {dataTable}.id = :id
                LIMIT 1;
                """.format(
                columns=','.join(columns),
                dataTable=table,
                entitiesTable=ObjectDbManager._EntitiesTableName)
            cursor.execute(sql, {'id': id})
            row = cursor.fetchone()
            if not row:
                raise RuntimeError(f'Object {id} not found in table {table}')

            parent = row[0] if setParent else None
            objectData = {}
            index = 1
            for paramDef in objectDef.paramDefs():
                columnName = paramDef.columnName()
                columnValue = row[index]
                if columnValue == None and not paramDef.isOptional():
                    raise RuntimeError(
                        f'Database column {columnName} for object {id} of type {objectDef.classType()} has null value for mandatory parameter')
                index += 1

                if columnValue != None:
                    columnType = paramDef.columnType()
                    if columnType == ParamDef.ColumnType.Text:
                        pass # Nothing to do
                    elif columnType == ParamDef.ColumnType.Integer:
                        pass # Nothing to do
                    elif columnType == ParamDef.ColumnType.Float:
                        pass # Nothing to do
                    elif columnType == ParamDef.ColumnType.Boolean:
                        columnValue = columnValue != 0
                    elif columnType == ParamDef.ColumnType.Enum:
                        enumType = paramDef.enumType()
                        if columnValue not in enumType.__members__:
                            raise RuntimeError(
                                f'Database column {columnName} for object {id} of type {objectDef.classType()} has unexpected value {columnValue}')
                        columnValue = enumType.__members__[columnValue]
                    elif columnType == ParamDef.ColumnType.Object:
                        columnValue = self._internalReadEntity(
                            id=columnValue,
                            setParent=False,
                            cursor=cursor)
                    elif columnType == ParamDef.ColumnType.List:
                        columnValue = self._internalReadEntity(
                            id=columnValue,
                            table=ObjectDbManager._ListsTableName,
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

    def _internalReadEntities(
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
        for paramDef in objectDef.paramDefs():
            columns.append('{table}.{column}'.format(
                table=objectDef.tableName(),
                column=paramDef.columnName()))

        sql = """
            SELECT {columns}
            FROM {dataTable}
            JOIN {entitiesTable} ON {dataTable}.id = {entitiesTable}.id;
            """.format(
            columns=','.join(columns),
            dataTable=objectDef.tableName(),
            entitiesTable=ObjectDbManager._EntitiesTableName)
        cursor.execute(sql)
        objects = []
        for row in cursor.fetchall():
            id = row[0]
            parent = row[1]
            objectData = {}
            index = 2
            for paramDef in objectDef.paramDefs():
                columnName = paramDef.columnName()
                columnValue = row[index]
                if columnValue == None and not paramDef.isOptional():
                    raise RuntimeError(
                        f'Database column {columnName} for object {id} of type {objectDef.classType()} has null value for mandatory parameter')
                index += 1

                if columnValue != None:
                    columnType = paramDef.columnType()
                    if columnType == ParamDef.ColumnType.Text:
                        pass # Nothing to do
                    elif columnType == ParamDef.ColumnType.Integer:
                        pass # Nothing to do
                    elif columnType == ParamDef.ColumnType.Float:
                        pass # Nothing to do
                    elif columnType == ParamDef.ColumnType.Boolean:
                        columnValue = columnValue != 0
                    elif columnType == ParamDef.ColumnType.Enum:
                        enumType = paramDef.enumType()
                        if columnValue not in enumType.__members__:
                            raise RuntimeError(
                                f'Database column {columnName} for object {id} of type {objectDef.classType()} has unexpected value {columnValue}')
                        columnValue = enumType.__members__[columnValue]
                    elif columnType == ParamDef.ColumnType.Object:
                        columnValue = self._internalReadEntity(
                            id=columnValue,
                            setParent=False,
                            cursor=cursor)
                    elif columnType == ParamDef.ColumnType.List:
                        columnValue = self._internalReadEntity(
                            id=columnValue,
                            table=ObjectDbManager._ListsTableName,
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
    def _internalUpdateEntity(
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
            columnData = {
                'id': entity.id(),
                'parent': entity.parent(),
                'table': objectDef.tableName()}
            cursor.execute(sql, columnData)

            # Query existing values if any of the objects parameters refer to
            # another entity as they're used to delete the old object if the
            # parameter is being updated to refer to a different object
            hasReference = any(
                paramDef.columnType() in {ParamDef.ColumnType.Object, ParamDef.ColumnType.List}
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
            columnData = {'id': entity.id()}
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
                if columnValue != None:
                    columnType = paramDef.columnType()
                    if columnType == ParamDef.ColumnType.Text:
                        columnValue = str(columnValue)
                    elif columnType == ParamDef.ColumnType.Integer:
                        columnValue = int(columnValue)
                    elif columnType == ParamDef.ColumnType.Float:
                        columnValue = float(columnValue)
                    elif columnType == ParamDef.ColumnType.Boolean:
                        columnValue = 1 if columnValue else 0
                    elif columnType == ParamDef.ColumnType.Enum:
                        if not isinstance(columnValue, enum.Enum) and \
                            not isinstance(columnValue, paramDef.enumType()):
                            raise RuntimeError(
                                f'Parameter {columnName} for object {entity.id()} of type {objectDef.classType()} is not an enum of type {paramDef.enumType()}')
                        columnValue = columnValue.name
                    elif columnType == ParamDef.ColumnType.Object:
                        if not isinstance(columnValue, DatabaseObject):
                            raise RuntimeError(
                                f'Parameter {columnName} for object {entity.id()} of type {objectDef.classType()} is not of type DatabaseObject')
                        isReference = True
                        childEntity = columnValue
                        columnValue = columnValue.id()
                    elif columnType == ParamDef.ColumnType.List:
                        if not isinstance(columnValue, DatabaseList):
                            raise RuntimeError(
                                f'Parameter {columnName} for object {entity.id()} of type {objectDef.classType()} is not of type DatabaseList')
                        isReference = True
                        childEntity = columnValue
                        columnValue = columnValue.id()
                    else:
                        raise RuntimeError(
                            f'Parameter {columnName} for object {entity.id()} of type {objectDef.classType()} has unknown type {columnType}')

                columnData[columnName] = columnValue

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
                    self._internalUpdateEntity(entity=childEntity, cursor=cursor)

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
            cursor.execute(sql, columnData)
        elif isinstance(entity, DatabaseList):
            # Update the entities table for the list
            sql = """
                INSERT INTO {table} (id, parent, table_name)
                VALUES (:id, :parent, :table)
                ON CONFLICT(id) DO UPDATE SET
                    parent = excluded.parent,
                    table_name = excluded.table_name;
                """.format(table=ObjectDbManager._EntitiesTableName)
            columnData = {
                'id': entity.id(),
                'parent': entity.parent(),
                'table': ObjectDbManager._ListsTableName}
            cursor.execute(sql, columnData)

            # Delete any children that were in the list but aren't any more
            contentIds = [child.id() for child in entity]
            sql = """
                DELETE FROM {entitiesTable}
                WHERE id IN (
                    SELECT object
                    FROM {listsTable}
                    WHERE id = ?
                    AND object NOT IN ({placeholders})
                );
            """.format(
                entitiesTable=ObjectDbManager._EntitiesTableName,
                listsTable=ObjectDbManager._ListsTableName,
                placeholders=', '.join('?' for _ in contentIds))
            columnData = [entity.id()] + contentIds
            cursor.execute(sql, columnData)

            # Recursively update list children. This must be done before
            # the inserting items into the list for them in order to
            # avoid failing foreign key checks
            for child in entity:
                self._internalUpdateEntity(entity=child, cursor=cursor)

            # Remove all existing items for the list and add the new ones.
            # This is a bit inefficient if the majority of the same objects
            # are still in the list, however it has the advantage that it
            # keeps the order of the items in the db the same as the order
            # the list object has them
            sql = 'DELETE FROM {table} WHERE id = :id'.format(
                table=ObjectDbManager._ListsTableName)
            cursor.execute(sql, {'id': entity.id()})

            columnData = [(entity.id(), child.id()) for child in entity]
            if columnData:
                sql = 'INSERT INTO {table} (id, object) VALUES (?, ?)'.format(
                    table=ObjectDbManager._ListsTableName)
                cursor.executemany(sql, columnData)
        else:
            raise RuntimeError(f'Unexpected entity type {type(entity)}')

    def _internalDeleteEntity(
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
                if (paramDef.columnType() == ParamDef.ColumnType.Object) and paramDef.isOptional():
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
