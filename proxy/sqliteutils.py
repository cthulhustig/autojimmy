import aiosqlite

_CheckIfTableExistsQuery = 'SELECT name FROM sqlite_master WHERE type = "table" AND name = :table;'

async def checkIfTableExistsAsync(
        table: str,
        connection: aiosqlite.Connection
        ) -> bool:
    async with connection.execute(_CheckIfTableExistsQuery, {'table': table}) as cursor:
        row = await cursor.fetchone()
        return row != None
