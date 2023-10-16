import logging
import json
import os

from googleapiclient.discovery import build
from lib.config import YOUTUBE_API_KEY, API_VERSION
from pydantic import BaseModel
from typing import Mapping, Any, Optional

# trunk-ignore(bandit/B108)
VIDEO_TRANSCRIPT_PATH = "/tmp/workflow/transcript"
logger = logging.getLogger(__file__)


class Video(BaseModel):
    # video id
    id: str
    # /path/to/the/video.mp3
    path: Optional[str] = None
    # {
    #     "publishedAt": "2023-09-10T10:00:45Z",
    #     "channelId": "UCR2LHLiQmL_zEJnlCiyyxAA",
    #     "title": "花99去中国最大威士忌酒展，居然喝到将近100000？",
    #     "description": "时隔三年的Whisky L ！这次真的喝回票价！ 猜猜在全国最大的威士忌酒展能喝到多少钱？",
    #     "thumbnails": {
    #       "default": {
    #         "url": "https://i.ytimg.com/vi/y2eajIQeQZs/default.jpg",
    #         "width": 120,
    #         "height": 90
    #       },
    #       "medium": {
    #         "url": "https://i.ytimg.com/vi/y2eajIQeQZs/mqdefault.jpg",
    #         "width": 320,
    #         "height": 180
    #       },
    #       "high": {
    #         "url": "https://i.ytimg.com/vi/y2eajIQeQZs/hqdefault.jpg",
    #         "width": 480,
    #         "height": 360
    #       }
    #     },
    #     "channelTitle": "索菲亚一斤半Sophia1.5",
    #     "liveBroadcastContent": "none",
    #     "publishTime": "2023-09-10T10:00:45Z"
    #   }
    # }
    snippet: Mapping[str, Any] = {}
    # Transcript format to content, 
    # format could be json, text, srt, verbose_json, or vtt
    transcript: Mapping[str, Any] = {}

    def __str__(self) -> str:
        return str(self.id)

    def __repr__(self) -> str:
        return self.__str__()

    def _path(self) -> str:
        if not os.path.exists(VIDEO_TRANSCRIPT_PATH):
            os.makedirs(VIDEO_TRANSCRIPT_PATH)
        return VIDEO_TRANSCRIPT_PATH

    def save_as_json(self) -> str:
        path = f"{self._path()}/{self.id}.json"
        with open(path, "w", encoding="utf-8") as json_file:
            json.dump(
                self.model_dump(mode="json"),
                json_file,
                ensure_ascii=False,
            )
        return path

    def save_transcript(self) -> Mapping[str, str]:
        """
        Return map from transcript extendtion to transcript file path.
        """
        pathes = dict()
        for ext, tran in self.transcript.items():
            path = f"{self._path()}/{self.id}.{ext}"
            with open(path, "w", encoding="utf-8") as file:
                file.write(tran)

            pathes[ext] = path
        return pathes

    # TODO auth required for upload.
    # TODO send user a link and click & auth before uplaod??
    # example https://github.com/youtube/api-samples/blob/master/python/captions.py#L53
    # googleapiclient.errors.HttpError: <HttpError 401 when requesting https://youtube.googleapis.com/upload/youtube/v3/captions?part=snippet&key=AIzaSyBIBYZ0LAYyfV6ZNtyRw0PzSMIhzOTubLk&alt=json&uploadType=multipart returned "API keys are not supported by this API. Expected OAuth2 access token or other authentication credentials that assert a principal. See https://cloud.google.com/docs/authentication". Details: "[{'message': 'Login Required.', 'domain': 'global', 'reason': 'required', 'location': 'Authorization', 'locationType': 'header'}]">
    def upload_transcript(self, transcript_path: str) -> Any:
        youtube = build(
            "youtube",
            API_VERSION,
            developerKey=YOUTUBE_API_KEY,
        )
        result = youtube.captions().insert(
            part="snippet",
            body=dict(
                snippet=dict(
                    videoId=self.id,
                    # TODO, set language
                    language="zh",
                    # name=name,
                    isDraft=True
                )
            ),
            media_body=transcript_path,
        ).execute()

        logger.info(result)

        return result
