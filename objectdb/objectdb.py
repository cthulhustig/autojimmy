import common
import enum
import logging
import operator
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
        self._lastParent = None

    def __eq__(self, other: object) -> bool:
        # NOTE: Last parent is intentionally not compared, it's not really
        # part of the objects state
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

        if self._parent != None and parent == None:
            # The entity is being detached from it's current parent
            self._lastParent = self._parent
        elif parent != None and self._lastParent != None  and parent != self._lastParent:
            # This object is being attached to a parent that is different
            # from the one it was last attached to. It's assigned a new
            # id to effectively make it a new object.
            # NOTE: This is done to avoid the problematic case of an entity
            # instance being detached from one parent and attached to
            # another and then that parent entity saved, resulting in both
            # parents referencing the same child entity. I could have the
            # db manager check for this happening at the point an object is
            # being updated, I think it would just be a case of checking the
            # entity table to see if there was an entry for the entity being
            # updated and if so, was it's parent id different to the one it
            # will be updated to (check the todo that was removed from
            # DiceRollerWindow when this comment was added for SQL that
            # __might__ do the check and update if it's ok in a single query).
            # The problem with doing it in the db manager is it prevents the
            # db getting into a bad state but it doesn't prevent code from
            # creating objects in this bad state then trying and failing to
            # update them. It would be the kind of thing that could result in
            # objects getting into a bad state in obscure corner cases that I
            # don't catch and the user getting a write error. By changing the
            # id like this it __should__ mean objects never get into a bad
            # state in the first place.
            # NOTE: It's important that the id is updated at the point it's
            # attached to a new parent rather than at the point it's detached
            # from the previous parent in order to allow code to detach an
            # entity from a parent then retrieve the id from it to explicitly
            # delete the entity from the db.
            self._id = str(uuid.uuid4())

        self._parent = parent

class DatabaseObject(DatabaseEntity):
    def __init__(
            self,
            id: typing.Optional[str] = None,
            parent: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, parent=parent)

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
    class ParamType(enum.Enum):
        Text = 0
        Integer = 1
        Float = 2
        Boolean = 3
        Enum = 4
        Object = 5
        List = 6

    def __init__(
            self,
            paramName: str,
            paramType: ParamType,
            isOptional: bool = False,
            columnName: typing.Optional[str] = None,
            enumType: typing.Optional[typing.Type[enum.Enum]] = None
            ) -> None:
        if paramType == ParamDef.ParamType.Enum:
            if not enumType:
                raise ValueError(f'No enum type specified for enum parameter {paramName}')
            if not issubclass(enumType, enum.Enum):
                raise ValueError(f'Invalid enum type {enumType} specified for enum parameter {paramName}')
        else:
            if enumType:
                raise ValueError(f'Unexpected enum type specified for non-enum parameter {paramName}')

        self._paramName = paramName
        self._paramType = paramType
        self._isOptional = isOptional
        self._columnName = columnName if columnName != None else paramName
        self._enumType = enumType

    def paramName(self) -> str:
        return self._paramName

    def paramType(self) -> ParamType:
        return self._paramType

    def isOptional(self) -> bool:
        return self._isOptional

    def columnName(self) -> str:
        return self._columnName

    def enumType(self) -> typing.Optional[typing.Type[enum.Enum]]:
        return self._enumType

class ObjectDef(object):
    def __init__(
            self,
            classType: typing.Type['DatabaseObject'],
            paramDefs: typing.Iterable[ParamDef],
            tableName: str,
            ) -> None:
        self._classType = classType
        self._paramDefs = paramDefs
        self._tableName = tableName

        self._paramNameMap = {p.paramName(): p for p in self._paramDefs}
        self._columnNameMap = {p.columnName(): p for p in self._paramDefs}
        # Sanity check for duplicates
        assert(len(self._paramDefs) == len(self._paramNameMap) == len(self._columnNameMap))

    def classType(self) -> typing.Type['DatabaseObject']:
        return self._classType

    def paramDefs(self) -> typing.Iterable[ParamDef]:
        return self._paramDefs

    def paramDefByName(self, name) -> typing.Optional[ParamDef]:
        return self._paramNameMap.get(name)

    def paramDefByColumn(self, column) -> typing.Optional[ParamDef]:
        return self._columnNameMap.get(column)

    def tableName(self) -> str:
        return self._tableName

    def columnNames(self) -> typing.Iterable[str]:
        names = []
        for paramDef in self._paramDefs:
            names.append(paramDef.columnName())
        return names

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

                # All DatabaseObject classes should have a static defineObject function
                # that the ObjectDbManager can use to retrieve its ObjectDef
                if not common.hasMethod(obj=classType, method='defineObject', includeSubclasses=False):
                    raise RuntimeError(f'{classType} is derived from DatabaseObject so must have a static defineObject function')

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
                        paramType = paramDef.paramType()
                        column = paramDef.columnName()

                        if paramType == ParamDef.ParamType.Text:
                            column += ' TEXT'
                        elif paramType == ParamDef.ParamType.Integer:
                            column += ' INTEGER'
                        elif paramType == ParamDef.ParamType.Float:
                            column += ' REAL'
                        elif paramType == ParamDef.ParamType.Boolean:
                            column += ' INTEGER'
                        elif paramType == ParamDef.ParamType.Enum:
                            column += ' TEXT'
                        elif paramType == ParamDef.ParamType.Object:
                            column += ' TEXT'
                        elif paramType == ParamDef.ParamType.List:
                            column += ' TEXT'
                        else:
                            raise RuntimeError(
                                f'Parameter definition {classType}.{paramDef.paramName()} has unknown type {paramType}')

                        if not paramDef.isOptional():
                            column += ' NOT NULL'

                        columnStrings.append(column)

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

    def createObject(
            self,
            object: DatabaseObject,
            ) -> str:
            logging.debug(f'ObjectDbManager creating object {object.id()} of type {type(object)}')
            with ObjectDbManager._lock:
                with self._connection:
                    self._internalCreateEntity(
                        entity=object,
                        cursor=self._connection.cursor())

    def readObject(
            self,
            id: str
            ) -> DatabaseObject:
        logging.debug(f'ObjectDbManager reading object {id}')
        with ObjectDbManager._lock:
            # Use a transaction for the read to ensure a consistent
            # view of the database across multiple selects
            with self._connection:
                return self._internalReadEntity(
                    id=id,
                    cursor=self._connection.cursor())

    def readObjects(
            self,
            classType: typing.Type[DatabaseObject]
            ) -> typing.Iterable[DatabaseObject]:
        logging.debug(f'ObjectDbManager reading object of type {classType}')
        with ObjectDbManager._lock:
            # Use a transaction for the read to ensure a consistent
            # view of the database across multiple selects
            with self._connection:
                return self._internalReadEntities(
                    classType=classType,
                    cursor=self._connection.cursor())

    def updateObject(
            self,
            object: DatabaseObject
            ) -> None:
        logging.debug(f'ObjectDbManager updating object {object.id()} of type {type(object)}')
        with ObjectDbManager._lock:
            with self._connection:
                self._internalUpdateEntity(
                    entity=object,
                    cursor=self._connection.cursor())

    def deleteObject(
            self,
            id: str
            ) -> None:
        logging.debug(f'ObjectDbManager deleting object {id}')
        with ObjectDbManager._lock:
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
            paramDefs = objectDef.paramDefs()

            sql = 'INSERT INTO {table} VALUES (:id, :parent, :table_name)'.format(
                table=ObjectDbManager._EntitiesTableName)
            values = {
                'id': entity.id(),
                'parent': entity.parent(),
                'table_name': objectDef.tableName()
            }
            cursor.execute(sql, values)

            sql = 'INSERT INTO {table} VALUES (:id'.format(
                table=objectDef.tableName())
            values = {'id': entity.id()}
            for paramDef in paramDefs:
                paramType = paramDef.paramType()
                sql += ', :' + paramDef.columnName()

                value = operator.methodcaller(paramDef.paramName())(entity)
                if value == None and not paramDef.isOptional():
                    raise RuntimeError(f'Mandatory parameter accessor {objectDef.classType()}.{paramDef.paramName()} returned none for object {entity.id()}')

                childEntity = None
                if value != None:
                    if paramType == ParamDef.ParamType.Text:
                        value = str(value)
                    elif paramType == ParamDef.ParamType.Integer:
                        value = int(value)
                    elif paramType == ParamDef.ParamType.Float:
                        value = float(value)
                    elif paramType == ParamDef.ParamType.Boolean:
                        value = 1 if value else 0
                    elif paramType == ParamDef.ParamType.Enum:
                        if not isinstance(value, enum.Enum):
                            raise RuntimeError(
                                f'Value returned by parameter accessor {objectDef.classType()}.{paramDef.paramName()} for object {entity.id()} is not an enum')
                        value = value.name
                    elif paramType == ParamDef.ParamType.Object:
                        if not isinstance(value, DatabaseObject):
                            raise RuntimeError(
                                f'Value returned by parameter accessor {objectDef.classType()}.{paramDef.paramName()} for object {entity.id()} is not a DatabaseObject')
                        childEntity = value
                        value = value.id()
                    elif paramType == ParamDef.ParamType.List:
                        if not isinstance(value, DatabaseList):
                            raise RuntimeError(
                                f'Value returned by parameter accessor {objectDef.classType()}.{paramDef.paramName()} for object {entity.id()} is not a DatabaseList')
                        childEntity = value
                        value = value.id()
                    else:
                        raise RuntimeError(
                            f'Parameter definition {objectDef.classType()}.{paramDef.paramName()} has unknown type {paramType}')

                values[paramDef.columnName()] = value

                if childEntity != None:
                    self._internalCreateEntity(
                        entity=childEntity,
                        cursor=cursor)
            sql += ');'

            cursor.execute(sql, values)
        elif isinstance(entity, DatabaseList):
            # Always insert list into entity table, even if doesn't
            # have any entries in the list table because it's empty
            sql = 'INSERT INTO {table} VALUES (:id, :parent, :table_name)'.format(
                table=ObjectDbManager._EntitiesTableName)
            values = {
                'id': entity.id(),
                'parent': entity.parent(),
                'table_name': 'lists'
            }
            cursor.execute(sql, values)

            values = []
            for child in entity:
                self._internalCreateEntity(entity=child, cursor=cursor)
                values.append((entity.id(), child.id()))
            if values:
                sql = 'INSERT INTO {table} (id, object) VALUES (?, ?)'.format(
                    table=ObjectDbManager._ListsTableName)
                cursor.executemany(sql, values)
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
                SELECT id, table_name
                FROM {table}
                WHERE parent = :id;
                """.format(
                    table=ObjectDbManager._EntitiesTableName)
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
            columns = [
                '{table}.parent'.format(table=ObjectDbManager._EntitiesTableName)
                ]
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

            values = {
                'id': id,
                'parent': row[0] if setParent else None}
            index = 1
            for paramDef in objectDef.paramDefs():
                value = row[index]
                if value == None and not paramDef.isOptional():
                    raise RuntimeError(f'Database value for mandatory parameter {objectDef.classType()}.{paramDef.paramName()} is null')
                index += 1

                paramType = paramDef.paramType()
                if value != None:
                    if paramType == ParamDef.ParamType.Text:
                        pass # Nothing to do
                    elif paramType == ParamDef.ParamType.Integer:
                        pass # Nothing to do
                    elif paramType == ParamDef.ParamType.Float:
                        pass # Nothing to do
                    elif paramType == ParamDef.ParamType.Boolean:
                        value = value != 0
                    elif paramType == ParamDef.ParamType.Enum:
                        enumType = paramDef.enumType()
                        if value not in enumType.__members__:
                            raise RuntimeError(
                                f'Database value {value} not found in enum type for {objectDef.classType()}.{paramDef.paramName()}')
                        value = enumType.__members__[value]
                    elif paramType == ParamDef.ParamType.Object:
                        value = self._internalReadEntity(
                            id=value,
                            setParent=False,
                            cursor=cursor)
                    elif paramType == ParamDef.ParamType.List:
                        value = self._internalReadEntity(
                            id=value,
                            table=ObjectDbManager._ListsTableName,
                            setParent=False,
                            cursor=cursor)
                    else:
                        raise RuntimeError(
                            f'Parameter definition {objectDef.classType()}.{paramDef.paramName()} has unknown type {paramType}')

                values[paramDef.paramName()] = value

            classType = objectDef.classType()
            return classType(**values)

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
            values = {
                'id': row[0],
                'parent': row[1]}
            index = 2
            for paramDef in objectDef.paramDefs():
                value = row[index]
                if value == None and not paramDef.isOptional():
                    raise RuntimeError(f'Database value for mandatory parameter {objectDef.classType()}.{paramDef.paramName()} is null')
                index += 1

                paramType = paramDef.paramType()
                if value != None:
                    if paramType == ParamDef.ParamType.Text:
                        pass # Nothing to do
                    elif paramType == ParamDef.ParamType.Integer:
                        pass # Nothing to do
                    elif paramType == ParamDef.ParamType.Float:
                        pass # Nothing to do
                    elif paramType == ParamDef.ParamType.Boolean:
                        value = value != 0
                    elif paramType == ParamDef.ParamType.Enum:
                        enumType = paramDef.enumType()
                        if value not in enumType.__members__:
                            raise RuntimeError(
                                f'Database value {value} not found in enum type for {objectDef.classType()}.{paramDef.paramName()}')
                        value = enumType.__members__[value]
                    elif paramType == ParamDef.ParamType.Object:
                        value = self._internalReadEntity(
                            id=value,
                            setParent=False,
                            cursor=cursor)
                    elif paramType == ParamDef.ParamType.List:
                        value = self._internalReadEntity(
                            id=value,
                            table=ObjectDbManager._ListsTableName,
                            setParent=False,
                            cursor=cursor)
                    else:
                        raise RuntimeError(
                            f'Parameter definition {objectDef.classType()}.{paramDef.paramName()} has unknown type {paramType}')

                values[paramDef.paramName()] = value

            classType = objectDef.classType()
            objects.append(classType(**values))
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
            columns = objectDef.columnNames()

            # Update the entities table metadata
            sql = """
                INSERT INTO {table} (id, parent, table_name)
                VALUES (:id, :parent, :table)
                ON CONFLICT(id) DO UPDATE SET
                    parent = excluded.parent,
                    table_name = excluded.table_name;
                """.format(table=ObjectDbManager._EntitiesTableName)
            values = {
                'id': entity.id(),
                'parent': entity.parent(),
                'table': objectDef.tableName()}
            cursor.execute(sql, values)

            # Query existing values if any of the objects parameters refer to
            # another entity as they're used to delete the old object if the
            # parameter is being updated to refer to a different object
            hasReference = any(
                paramDef.paramType() in {ParamDef.ParamType.Object, ParamDef.ParamType.List}
                for paramDef in paramDefs)
            exitingValues = None
            if hasReference:
                sql = """
                    SELECT {columns}
                    FROM {dataTable}
                    WHERE id = :id
                    LIMIT 1;
                    """.format(
                        columns=','.join(columns),
                        dataTable=objectDef.tableName(),
                        entitiesTable=ObjectDbManager._EntitiesTableName)
                cursor.execute(sql, {'id': entity.id()})
                exitingValues = cursor.fetchone()

            values = {'id': entity.id()}
            for index, paramDef in enumerate(paramDefs):
                paramType = paramDef.paramType()
                column = paramDef.columnName()

                value = operator.methodcaller(paramDef.paramName())(entity)
                if value == None and not paramDef.isOptional():
                    raise RuntimeError(f'Mandatory parameter accessor {objectDef.classType()}.{paramDef.paramName()} returned none for object {entity.id()}')

                isReference = False
                childEntity = None
                if value != None:
                    if paramType == ParamDef.ParamType.Text:
                        value = str(value)
                    elif paramType == ParamDef.ParamType.Integer:
                        value = int(value)
                    elif paramType == ParamDef.ParamType.Float:
                        value = float(value)
                    elif paramType == ParamDef.ParamType.Boolean:
                        value = 1 if value else 0
                    elif paramType == ParamDef.ParamType.Enum:
                        if not isinstance(value, enum.Enum):
                            raise RuntimeError(
                                f'Value returned by parameter accessor {objectDef.classType()}.{paramDef.paramName()} for object {entity.id()} is not an enum')
                        value = value.name
                    elif paramType == ParamDef.ParamType.Object:
                        if not isinstance(value, DatabaseObject):
                            raise RuntimeError(
                                f'Value returned by parameter accessor {objectDef.classType()}.{paramDef.paramName()} for object {entity.id()} is not a DatabaseObject')
                        isReference = True
                        childEntity = value
                        value = value.id()
                    elif paramType == ParamDef.ParamType.List:
                        if not isinstance(value, DatabaseList):
                            raise RuntimeError(
                                f'Value returned by parameter accessor {objectDef.classType()}.{paramDef.paramName()} for object {entity.id()} is not a DatabaseList')
                        isReference = True
                        childEntity = value
                        value = value.id()
                    else:
                        raise RuntimeError(
                            f'Parameter definition {objectDef.classType()}.{paramDef.paramName()} has unknown type {paramType}')

                values[column] = value

                if isReference and (exitingValues != None):
                    oldId = exitingValues[index]
                    if oldId != None and oldId != value:
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
                    columns=', '.join(columns),
                    placeholders=', '.join([f':{col}' for col in columns]),
                    conflict=', '.join([f'{col} = excluded.{col}' for col in columns]))
            cursor.execute(sql, values)
        elif isinstance(entity, DatabaseList):
            # Update the entities table for the list
            sql = """
                INSERT INTO {table} (id, parent, table_name)
                VALUES (:id, :parent, :table)
                ON CONFLICT(id) DO UPDATE SET
                    parent = excluded.parent,
                    table_name = excluded.table_name;
                """.format(table=ObjectDbManager._EntitiesTableName)
            values = {
                'id': entity.id(),
                'parent': entity.parent(),
                'table': ObjectDbManager._ListsTableName}
            cursor.execute(sql, values)

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
            values = [entity.id()] + contentIds
            cursor.execute(sql, values)

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

            values = [(entity.id(), child.id()) for child in entity]
            if values:
                sql = 'INSERT INTO {table} (id, object) VALUES (?, ?)'.format(
                    table=ObjectDbManager._ListsTableName)
                cursor.executemany(sql, values)
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
                if (paramDef.paramType() == ParamDef.ParamType.Object) and paramDef.isOptional():
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
