import common
import database
import datetime
import logging
import sqlite3
import typing

class UniverseInfo(object):
    def __init__(
            self,
            id: str,
            name: str,
            ) -> None:
        common.validateStr(name='id', value=id, allowEmpty=False)
        common.validateStr(name='name', value=name, allowEmpty=False)

        self._id = id
        self._name = name

    def id(self) -> str:
        return self._id

    def name(self) -> str:
        return self._name

class UniverseRegistry(object):
    _UniversesTableName = 'universes'
    _UniversesTableSchema = 1

    def __init__(self, registryPath: str) -> None:
        self._database = database.SchemaDb(path=registryPath)
        self._initDatabase()

    def createTransaction(self) -> database.Transaction:
        return self._database.createTransaction()

    def addUniverse(
            self,
            id: str,
            name: str,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseRegister adding universe {id!r} ({name!r})')

        if transaction != None:
            connection = transaction.connection()
            self._addUniverse(
                id=id,
                name=name,
                cursor=connection.cursor())
        else:
            with self._database.createTransaction() as transaction:
                connection = transaction.connection()
                self._addUniverse(
                    id=id,
                    name=name,
                    cursor=connection.cursor())

    def removeUniverse(
            self,
            id: str,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseRegister removing universe {id!r}')

        if transaction != None:
            connection = transaction.connection()
            self._removeUniverse(
                id=id,
                cursor=connection.cursor())
        else:
            with self._database.createTransaction() as transaction:
                connection = transaction.connection()
                self._removeUniverse(
                    id=id,
                    cursor=connection.cursor())

    def listUniverses(
            self,
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.List[UniverseInfo]:
        logging.debug(f'UniverseRegister listing universes')

        if transaction != None:
            connection = transaction.connection()
            return self._listUniverses(
                cursor=connection.cursor())
        else:
            with self._database.createTransaction() as transaction:
                connection = transaction.connection()
                return self._listUniverses(
                    cursor=connection.cursor())

    def universeById(
            self,
            id: str,
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.Optional[UniverseInfo]:
        logging.debug(
            f'UniverseRegister retrieving info for universe with id {id!r}')

        if transaction != None:
            connection = transaction.connection()
            return self._universeById(
                id=id,
                cursor=connection.cursor())
        else:
            with self._database.createTransaction() as transaction:
                connection = transaction.connection()
                return self._universeById(
                    id=id,
                    cursor=connection.cursor())

    def setUniverseName(
            self,
            id: str,
            name: str,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseRegister setting name of universe {id!r} to {name!r}')

        if transaction != None:
            connection = transaction.connection()
            return self._setUniverseName(
                id=id,
                name=name,
                cursor=connection.cursor())
        else:
            with self._database.createTransaction() as transaction:
                connection = transaction.connection()
                return self._setUniverseName(
                    id=id,
                    name=name,
                    cursor=connection.cursor())

    def _initDatabase(self) -> None:
        with self._database.createTransaction() as transaction:
            connection = transaction.connection()
            cursor = connection.cursor()

            self._database.createTable(
                cursor=cursor,
                tableName=UniverseRegistry._UniversesTableName,
                requiredSchemaVersion=UniverseRegistry._UniversesTableSchema,
                columns=[
                    database.ColumnDef(columnName='id', columnType=database.ColumnDef.ColumnType.Text, isPrimaryKey=True),
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=False)])

    def _addUniverse(
            self,
            cursor: sqlite3.Cursor,
            id: str,
            name: str
            ) -> None:
        sql = """
            INSERT INTO {table} (id, name)
            VALUES (:id, :name);
            """.format(table=UniverseRegistry._UniversesTableName)
        rowData = {
            'id': id,
            'name': name}
        cursor.execute(sql, rowData)

    def _removeUniverse(
            self,
            cursor: sqlite3.Cursor,
            id: str
            ) -> None:
        sql = """
            DELETE FROM {table}
            WHERE id = :id
            """.format(table=UniverseRegistry._UniversesTableName)
        cursor.execute(sql, {'id': id})

    def _listUniverses(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[UniverseInfo]:
        sql = """
            SELECT id, name
            FROM {table};
            """.format(table=UniverseRegistry._UniversesTableName)
        cursor.execute(sql)

        universeList = []
        for row in cursor.fetchall():
            universeList.append(UniverseInfo(
                id=row[0],
                name=row[1]))
        return universeList

    def _universeById(
            self,
            cursor: sqlite3.Cursor,
            id: str
            ) -> typing.Optional[UniverseInfo]:
        sql = """
            SELECT name
            FROM {table}
            WHERE id = :id
            LIMIT 1;
            """.format(table=UniverseRegistry._UniversesTableName)
        cursor.execute(sql, {'id': id})

        row = cursor.fetchone()
        if not row:
            return None

        return UniverseInfo(
            id=id,
            name=row[0])

    def _setUniverseName(
            self,
            cursor: sqlite3.Cursor,
            id: str,
            name: str
            ) -> None:
        sql = """
            UPDATE {table}
            SET name = :name
            WHERE id = :id;
            """.format(table=UniverseRegistry._UniversesTableName)
        # TODO: Does this throw if the entry doesn't exist or do I need to check a return value?
        cursor.execute(sql, {'id': id, 'name': name})
