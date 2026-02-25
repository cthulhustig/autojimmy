import sqlite3
import typing

def checkIfTableExists(
        tableName: str,
        cursor: sqlite3.Cursor
        ) -> bool:
    sql = 'SELECT name FROM sqlite_master WHERE type = "table" AND name = :table;'
    cursor.execute(sql, {'table': tableName})
    return cursor.fetchone() != None

def checkIfTriggerExists(
        triggerName: str,
        cursor: sqlite3.Cursor
        ) -> bool:
    sql = 'SELECT name  FROM sqlite_master  WHERE type = "trigger" AND name = :trigger;'
    cursor.execute(sql, {'trigger': triggerName})
    return cursor.fetchone() != None

def createColumnIndex(
        table: str,
        column: str,
        unique: bool,
        cursor: sqlite3.Cursor
        ) -> None:
    if unique:
        sql = f'CREATE UNIQUE INDEX IF NOT EXISTS {table}_{column}_index ON {table}({column});'
    else:
        sql = f'CREATE INDEX IF NOT EXISTS {table}_{column}_index ON {table}({column});'
    cursor.execute(sql)

def createMultiColumnIndex(
        table: str,
        columns: typing.Collection[str],
        unique: bool,
        cursor: sqlite3.Cursor
        ) -> None:
    indexName = table
    for column in columns:
        indexName += '_' + column
    indexName += '_index'
    columns = ', '.join(columns)

    if unique:
        sql = f'CREATE UNIQUE INDEX IF NOT EXISTS {indexName} ON {table}({columns});'
    else:
        sql = f'CREATE INDEX IF NOT EXISTS {indexName} ON {table}({columns});'
    cursor.execute(sql)
