from pydantic import BaseModel
from typing import Mapping, Any


class Video(BaseModel):
    id: str
    # /path/to/the/video.mp3
    path: str
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
    snippet: Mapping[str, Any]
    # Transcript format to content, 
    # format could be json, text, srt, verbose_json, or vtt
    transcript: Mapping[str, Any]


    def __str__(self) -> str:
        return id

    def __repr__(self) -> str:
        return self.__str__()