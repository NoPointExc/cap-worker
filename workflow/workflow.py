from enum import Enum
from pydantic import BaseModel
from typing import TypeVar, Generic, Optional, Tuple, Type

from lib.aio_sqlite_connection_manager import SQLiteConnectionManager
from lib.user import User
from lib.log import get_logger

logger = get_logger(__file__)


class BaseArgs(BaseModel):
    def __str__(self) -> str:
        return self.model_dump_json()

    def __repr__(self) -> str:
        return self.__str__()

    @classmethod
    def from_json(cls, json_str: str) -> "BaseArgs":
        return cls.model_validate_json(json_str)


class WorkflowType(Enum):
    VIDEO = 1


class Status(Enum):
    TODO = 1
    LOCKED = 2
    CLAIMED = 3
    WORKING = 4
    ERROR = 5
    FAILED = 6
    DONE = 7


Args = TypeVar("Args", bound=BaseArgs)


class Workflow(Generic[Args]):
    def __init__(self, worflow_type: WorkflowType, args: Type[BaseArgs]):
        self.args_type = args
        self.workflow_type = worflow_type

    async def done(self, id: int) -> None:
        UPDATE_SQL = """
            UPDATE workflow
            SET status = ?
            WHERE id = ?
        """
        async with SQLiteConnectionManager() as conn:
            logger.info(f"Mark workflow: {id} as 'DONE'")
            await conn.execute(
                UPDATE_SQL,
                (Status.DONE.value, id),
            )
            await conn.commit()

    async def claim(self) -> Optional[Tuple[int, int, Args]]:
        SELECT_SQL = """
            SELECT
                id,
                user_id,
                args,
                type
            FROM
                workflow
            WHERE
                status = ? AND type = ?
            ORDER BY
                create_at
            LIMIT 1
            """
        UPDATE_SQL = """
            UPDATE workflow
            SET status = ?
            WHERE id = ?
        """
        try:
            conn = await SQLiteConnectionManager().connect()
            conn.isolation_level = "EXCLUSIVE"
            # Select
            cursor = await conn.execute(
                SELECT_SQL, (Status.TODO.value, self.workflow_type.value)
            )
            row = await cursor.fetchone()
            if row:
                id, user_id, args, type = row
                # Lock
                logger.info(f"Locking workflow: {id}")
                await conn.execute(
                    UPDATE_SQL,
                    (Status.LOCKED.value, id),
                )
                logger.info(f"Locked workflow: {id}")
                arg_obj = self.args_type.from_json(json_str=args)

                # Claim
                logger.info(f"Claiming workflow: {id}")
                await conn.execute(UPDATE_SQL, (Status.CLAIMED.value, id))
            else:
                logger.info(
                    "No pending work left for "
                    f"workflow type: {self.workflow_type.name}"
                )
        except Exception as e:
            logger.exception(e)
            # Mark as error.
            await conn.execute(UPDATE_SQL, (Status.ERROR.value, id))
        finally:
            await conn.commit()
            await SQLiteConnectionManager().close()

        if not row:
            return None
        return id, user_id, arg_obj

    async def start(self) -> Optional[int]:
        out = await self.claim()
        if out is None:
            logger.info("No workflow in TOOD status found, skipping...")
            return None
        id, user_id, args = out
        logger.info(f"Starting workflow id: {id} with args: {args}")
        # get user
        user = await User.get_by_id(user_id)
        await self._start(id, user, args)
        await self.done(id)
        return id
