from enum import Enum
from lib.aio_sqlite_connection_manager import SQLiteConnectionManager
from lib.log import get_logger
from pydantic import BaseModel
from typing import TypeVar, Generic, Optional, Tuple, Type


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
                SELECT_SQL,
                (Status.TODO.value, self.workflow_type.value)
            )
            row = await cursor.fetchone()
            if not row:
                logger.info(
                    "No pending work left for "
                    f"workflow type: {self.workflow_type.name}"
                )
                return None
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
            return id, user_id, arg_obj
        except Exception as e:
            logger.exception(e)
            # Mark as error.
            await conn.execute(UPDATE_SQL, (Status.ERROR.value, id))
        finally:
            await conn.commit()
            await conn.close()
        return None

    async def start(self) -> Optional[int]:
        out = await self.claim()
        if out is None:
            logger.info("No workflow in TOOD status found, skipping...")
            return None
        id, user_id, args = out
        logger.info(f"Starting workflow id: {id} with args: {args}")
        await self._start(id, user_id, args)
        return id
