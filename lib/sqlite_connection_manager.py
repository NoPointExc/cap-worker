import sqlite3
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

    def connect(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_file)
        return self._conn

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        self.connection = sqlite3.connect(self.db_name)
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()