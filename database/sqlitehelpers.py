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
