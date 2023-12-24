import json
import os
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from typing import Mapping, Any, Optional
from lib.config import (
    YOUTUBE_API_KEY,
    API_VERSION,
)
from lib.aio_sqlite_connection_manager import SQLiteConnectionManager
from lib.log import get_logger
from pydantic import BaseModel

# trunk-ignore(bandit/B108)
VIDEO_TRANSCRIPT_PATH = "/tmp/workflow/transcript"
UTF_8 = "utf-8"


logger = get_logger(__file__)


def now() -> int:
    return int(time.time())


class Video(BaseModel):
    # id: int
    workflow_id: int
    user_id: int
    uuid: str = None
    snippet: Mapping[str, Any] = {}
    # format -> raw transcript
    transcript: Mapping[str, Any] = {}
    # path to he downloaded video.
    path: Optional[str] = None

    def __str__(self) -> str:
        return (
            "Video("
            # f"id={self.id}, "
            f"workflow_id={self.workflow_id}, "
            f"user_id={self.user_id}, "
            f"uuid={self.uuid}, "
            f"snippet={'not empty' if self.snippet else 'empty'}, "
            f"transcript={self.transcript.keys()}"
            ")"
        )

    def __repr__(self) -> str:
        return self.__str__()

    def _path(self) -> str:
        if not os.path.exists(VIDEO_TRANSCRIPT_PATH):
            os.makedirs(VIDEO_TRANSCRIPT_PATH)
        return VIDEO_TRANSCRIPT_PATH

    def set_snippet(self, snippet: Mapping[str, Any]) -> None:
        self.snippet = snippet

    def set_srt(self, transcript: str) -> None:
        self.transcript["srt"] = transcript

    async def save(self) -> None:
        """
        Save video to database
        """
        sql = """
            INSERT INTO
                video (workflow_id, user_id, uuid, snippt, transcript)
            VALUES (?, ?, ?, ?, ?)
        """
        async with SQLiteConnectionManager() as conn:
            await conn.execute(
                sql,
                (
                    self.workflow_id,
                    self.user_id,
                    self.uuid,
                    json.dumps(self.snippet),
                    json.dumps(self.transcript),
                )
            )
            await conn.commit()

    def save_as_json(self) -> str:
        path = f"{self._path()}/{self.uuid}.json"
        with open(path, "w", encoding="utf-8") as json_file:
            json.dump(
                self.model_dump(mode="json"),
                json_file,
                ensure_ascii=False,
            )
        return path

    # Test video: https://www.youtube.com/watch?v=zB6CmLBNSGs
    # TODO send user a link and click & auth before uplaod??
    async def upload_transcript(
            self,
            language: str,
            transcript_path: str,
            credentials: Credentials
    ) -> Any:
        youtube = build(
            "youtube",
            API_VERSION,
            developerKey=YOUTUBE_API_KEY,
            credentials=credentials,
        )
        # This require at last one of them:
        # https://www.googleapis.com/auth/youtube.force-ssl
        # https://www.googleapis.com/auth/youtubepartner
        result = youtube.captions().insert(
            part="snippet",
            body=dict(
                snippet=dict(
                    videoId=self.uuid,
                    language=language,
                    name=f"autocap_{language if language else ''}_{now}",
                    isDraft=False
                )
            ),
            media_body=transcript_path,
        ).execute()

        logger.info(result)

        return result
