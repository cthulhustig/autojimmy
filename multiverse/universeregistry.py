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
            description: str = '',
            isStock: bool = False,
            snapshotTimestamp: typing.Optional[datetime.datetime] = None
            ) -> None:
        common.validateMandatoryStr(name='id', value=id, allowEmpty=False)
        common.validateMandatoryStr(name='name', value=name, allowEmpty=False)
        common.validateMandatoryStr(name='description', value=description, allowEmpty=True)
        common.validateMandatoryBool(name='isStock', value=isStock)
        common.validateOptionalObject(name='snapshotTimestamp', value=snapshotTimestamp, type=datetime.datetime)

        self._id = id
        self._name = name
        self._description = description
        self._isStock = isStock
        self._snapshotTimestamp = snapshotTimestamp

    def id(self) -> str:
        return self._id

    def name(self) -> str:
        return self._name

    def description(self) -> str:
        return self._description

    def isStock(self) -> bool:
        return self._isStock

    def snapshotTimestamp(self) -> datetime.datetime:
        return self._snapshotTimestamp

class UniverseRegistry(object):
    _UniversesTableName = 'universes'
    _UniversesTableSchema = 1

    def __init__(self, registryPath: str) -> None:
        self._database = database.SchemaDb(dbPath=registryPath)
        self._initDatabase()

    def createTransaction(self) -> database.Transaction:
        return self._database.createTransaction()

    # TODO: Need to check that this prevents multiple universes with the same
    # id or name, and that the UI does something sensible if it happens
    def addUniverse(
            self,
            id: str,
            name: str,
            description: str = '',
            stock: bool = False,
            snapshotTimestamp: typing.Optional[datetime.datetime] = None,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseRegister adding universe {id} ({name})')

        if transaction != None:
            connection = transaction.connection()
            self._addUniverse(
                id=id,
                name=name,
                description=description,
                stock=stock,
                snapshotTimestamp=snapshotTimestamp,
                cursor=connection.cursor())
        else:
            with self._database.createTransaction() as transaction:
                connection = transaction.connection()
                self._addUniverse(
                    id=id,
                    name=name,
                    description=description,
                    stock=stock,
                    snapshotTimestamp=snapshotTimestamp,
                    cursor=connection.cursor())

    def removeUniverse(
            self,
            id: str,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseRegister removing universe {id}')

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

    def stockUniverse(
            self,
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.Optional[UniverseInfo]:
        logging.debug('UniverseRegister retrieving stock universe')

        if transaction != None:
            connection = transaction.connection()
            return self._stockUniverse(
                cursor=connection.cursor())
        else:
            with self._database.createTransaction() as transaction:
                connection = transaction.connection()
                return self._stockUniverse(
                    cursor=connection.cursor())

    def universeById(
            self,
            id: str,
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.Optional[UniverseInfo]:
        logging.debug(
            f'UniverseRegister retrieving info for universe with id {id}')

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

    def universeByName(
            self,
            name: str,
            transaction: typing.Optional[database.Transaction] = None
            ) -> typing.Optional[UniverseInfo]:
        logging.debug(
            f'UniverseRegister retrieving info for universe with name "{name}"')

        if transaction != None:
            connection = transaction.connection()
            return self._universeByName(
                name=name,
                cursor=connection.cursor())
        else:
            with self._database.createTransaction() as transaction:
                connection = transaction.connection()
                return self._universeByName(
                    name=name,
                    cursor=connection.cursor())

    def setUniverseName(
            self,
            id: str,
            name: str,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseRegister setting name of universe {id} to "{name}"')

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

    def setUniverseDescription(
            self,
            id: str,
            description: str,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseRegister setting description for universe {id} to "{description}"')

        if transaction != None:
            connection = transaction.connection()
            return self._setUniverseDescription(
                id=id,
                description=description,
                cursor=connection.cursor())
        else:
            with self._database.createTransaction() as transaction:
                connection = transaction.connection()
                return self._setUniverseDescription(
                    id=id,
                    description=description,
                    cursor=connection.cursor())

    def setSnapshotTimestamp(
            self,
            timestamp: datetime.datetime,
            transaction: typing.Optional[database.Transaction] = None
            ) -> None:
        logging.debug(f'UniverseRegister setting stock sector snapshot timestamp to {timestamp.isoformat()}')

        if transaction != None:
            connection = transaction.connection()
            self._setSnapshotTimestamp(
                timestamp=timestamp,
                cursor=connection.cursor())
        else:
            with self._database.createTransaction() as transaction:
                connection = transaction.connection()
                self._setSnapshotTimestamp(
                    timestamp=timestamp,
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
                    database.ColumnDef(columnName='name', columnType=database.ColumnDef.ColumnType.Text, isNullable=False, isUnique=True),
                    database.ColumnDef(columnName='description', columnType=database.ColumnDef.ColumnType.Text, isNullable=False),
                    # TODO: Is there a way I can enforce that there is only ever one entry with this set True
                    database.ColumnDef(columnName='is_stock', columnType=database.ColumnDef.ColumnType.Boolean, isNullable=False),
                    # TODO: Is there a way I can enforce that the timestamp must be specified for the stock universes but never specified for custom universes
                    database.ColumnDef(columnName='snapshot_timestamp', columnType=database.ColumnDef.ColumnType.Text, isNullable=True)])

    def _addUniverse(
            self,
            cursor: sqlite3.Cursor,
            id: str,
            name: str,
            description: str,
            stock: bool,
            snapshotTimestamp: typing.Optional[datetime.datetime]
            ) -> None:
        if stock and snapshotTimestamp is None:
            raise ValueError('Stock sector can\'t have a null snapshot timestamp')
        elif not stock and snapshotTimestamp is not None:
            raise ValueError('Custom sector can\'t have a snapshot timestamp')


        sql = """
            INSERT INTO {table} (id, name, description, is_stock, snapshot_timestamp)
            VALUES (:id, :name, :description, :is_stock, :snapshot_timestamp);
            """.format(table=UniverseRegistry._UniversesTableName)
        rowData = {
            'id': id,
            'name': name,
            'description': description,
            'is_stock': stock,
            'snapshot_timestamp': UniverseRegistry._formatTimestampString(snapshotTimestamp)}
        cursor.execute(sql, rowData)

    def _removeUniverse(
            self,
            cursor: sqlite3.Cursor,
            universeId: str
            ) -> None:
        sql = """
            DELETE FROM {table}
            WHERE id = :id
            """.format(
            table=UniverseRegistry._UniversesTableName)
        cursor.execute(sql, {'id': universeId})

    def _listUniverses(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.List[UniverseInfo]:
        sql = """
            SELECT id, name, description, is_stock, snapshot_timestamp
            FROM {table};
            """.format(
            table=UniverseRegistry._UniversesTableName)
        cursor.execute(sql)

        universeList = []
        for row in cursor.fetchall():
            universeList.append(UniverseInfo(
                id=row[0],
                name=row[1],
                description=row[2],
                isStock=True if row[3] else False,
                snapshotTimestamp=UniverseRegistry._parseTimestampString(row[4])))
        return universeList

    def _stockUniverse(
            self,
            cursor: sqlite3.Cursor
            ) -> typing.Optional[UniverseInfo]:
        sql = """
            SELECT id, name, description, snapshot_timestamp
            FROM {table}
            WHERE is_stock = 1
            LIMIT 1;
            """.format(
            table=UniverseRegistry._UniversesTableName)
        cursor.execute(sql)

        row = cursor.fetchone()
        if not row:
            return None

        return UniverseInfo(
            id=row[0],
            name=row[1],
            description=row[2],
            isStock=True,
            snapshotTimestamp=UniverseRegistry._parseTimestampString(row[3]))

    def _universeById(
            self,
            cursor: sqlite3.Cursor,
            id: str
            ) -> typing.Optional[UniverseInfo]:
        sql = """
            SELECT name, description, is_stock, snapshot_timestamp
            FROM {table}
            WHERE id = :id
            LIMIT 1;
            """.format(
            table=UniverseRegistry._UniversesTableName)
        cursor.execute(sql, {'id': id})

        row = cursor.fetchone()
        if not row:
            return None

        return UniverseInfo(
            id=id,
            name=row[0],
            description=row[1],
            isStock=True if row[2] else False,
            snapshotTimestamp=UniverseRegistry._parseTimestampString(row[3]))

    def _universeByName(
            self,
            cursor: sqlite3.Cursor,
            name: str
            ) -> typing.Optional[UniverseInfo]:
        sql = """
            SELECT id, description, is_stock, snapshot_timestamp
            FROM {table}
            WHERE name = :name
            LIMIT 1;
            """.format(
            table=UniverseRegistry._UniversesTableName)
        cursor.execute(sql, {'name': name})

        row = cursor.fetchone()
        if not row:
            return None

        return UniverseInfo(
            id=row[0],
            name=name,
            description=row[1],
            isStock=True if row[2] else False,
            snapshotTimestamp=UniverseRegistry._parseTimestampString(row[3]))

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
            """.format(
            table=UniverseRegistry._UniversesTableName)
        # TODO: Does this throw if the entry doesn't exist or do I need to check a return value?
        cursor.execute(sql, {'id': id, 'name': name})

    def _setUniverseDescription(
            self,
            cursor: sqlite3.Cursor,
            id: str,
            description: str
            ) -> None:
        sql = """
            UPDATE {table}
            SET description = :description
            WHERE id = :id;
            """.format(
            table=UniverseRegistry._UniversesTableName)
        # TODO: Does this throw if the entry doesn't exist or do I need to check a return value?
        cursor.execute(sql, {'id': id, 'description': description})

    def _setSnapshotTimestamp(
            self,
            cursor: sqlite3.Cursor,
            timestamp: datetime.datetime
            ) -> None:
        sql = """
            UPDATE {table}
            SET snapshot_timestamp = :snapshot_timestamp
            WHERE is_stock = 1;
            """.format(
            table=UniverseRegistry._UniversesTableName)
        # TODO: Does this throw if the entry doesn't exist or do I need to check a return value?
        cursor.execute(sql, {'snapshot_timestamp': UniverseRegistry._formatTimestampString(timestamp)})

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