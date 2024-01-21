import json

from cryptography.fernet import Fernet
from google.oauth2.credentials import Credentials
from pydantic import BaseModel

from typing import Optional

from lib.aio_sqlite_connection_manager import SQLiteConnectionManager
from lib.log import get_logger
from lib.config import FERNET_KEY

UTF_8 = "utf-8"

logger = get_logger(__file__)


class User(BaseModel):
    id: int
    name: str
    create_at: int
    credentials_encrypted: Optional[str]
    credit: int

    @property
    def credentials(self) -> Optional[Credentials]:
        # decrypt
        if not self.credentials_encrypted:
            return None
        fernet = Fernet(FERNET_KEY)
        credentials_raw = fernet.decrypt(
            self.credentials_encrypted
        ).decode(UTF_8)
        credentials_json = json.loads(credentials_raw)
        logger.info(f"credentials_json\n {credentials_json}")
        return Credentials.from_authorized_user_info(info=credentials_json)

    @credentials.setter
    def credentials(self, credentials: Optional[Credentials]) -> None:
        # encrypt
        if not credentials:
            return None
        fernet = Fernet(FERNET_KEY)
        self.credentials_encrypted = fernet.encrypt(
            credentials.to_json().encode(UTF_8)
        )

    @classmethod
    async def get_by_id(cls, id: int) -> "User":
        sql = """
            SELECT
                id, name, create_at, credentials, credit
            FROM users
            WHERE id = ?
        """
        user = None
        try:
            async with SQLiteConnectionManager() as conn:
                cursor = await conn.execute(sql, (id,))
                row = await cursor.fetchone()
                if row:
                    id, name, create_at, credentials_encrypted, credit = row
                    user = User(
                        id=id,
                        name=name,
                        create_at=create_at,
                        credentials_encrypted=credentials_encrypted,
                        credit=credit,
                    )
        except Exception as e:
            logger.exception(f"User not found due to exception: {e}")

        return user
