import aiosqlite
from lib.config import SQLITE_DB_FILE


class SQLiteConnectionManager:
    _instance = None

    def __new__(cls) -> "SQLiteConnectionManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._db_file = "db_file_to_be_set"
            cls._instance._conn = None
        return cls._instance

    def __init__(self) -> "SQLiteConnectionManager":
        self._db_file = SQLITE_DB_FILE

    async def connect(self):
        if self._conn is None:
            self._conn = await aiosqlite.connect(self._db_file)
        return self._conn

    async def close(self):
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def __aenter__(self):
        return await self.connect()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
