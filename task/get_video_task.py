import asyncio

from googleapiclient.discovery import build
from lib.config import YOUTUBE_API_KEY, API_VERSION
from lib.video import Video
from task.task import Task, Request, Response
from typing import List, Optional
from lib.log import get_logger


logger = get_logger(__file__)


API_SERVICE_NAME = "youtube"


class GetVideoRequest(Request):
    # Example:
    # url:https://www.youtube.com/@sophia1.549
    # channel name: sophia1.549
    # channel title: 索菲亚一斤半Sophia1.5
    # channel id: UCR2LHLiQmL_zEJnlCiyyxAA
    channel_title: str
    # Max number of video returns in each response
    max_video: int
    # "none" video without captions only
    # "closedCaption" Only include videos that have captions.
    # "any"  Do not filter results based on caption availability.
    # video_caption: str="any"


# videoCaption
class GetVideoResponse(Response):
    videos: List[Video]


# TODO install youtube client
class GetVideoTask(Task):
    def init(self) -> "GetVideoTask":
        self.youtube = build(
            API_SERVICE_NAME,
            API_VERSION,
            developerKey=YOUTUBE_API_KEY,
        )
        return self

    # TODO cache it.
    def get_channel_id(self, channel_title: str) -> Optional[str]:
        search_rst = (
            self.youtube.search()
            .list(
                part="id,snippet",
                q=channel_title,
                maxResults=1,
                type="video",
                order="relevance",
            )
            .execute()
        )

        for item in search_rst.get("items", []):
            if "snippet" in item.keys() and "channelId" in item["snippet"]:
                channel_id = item["snippet"]["channelId"]
                logger.info(
                    f"Got Channal id: {channel_id} for"
                    f" channel title: {channel_title}"
                )
                return channel_id
        logger.error(
            f"Failed to get channel id for channel title: {channel_title}")
        return None

    async def start(self, req: GetVideoRequest) -> GetVideoResponse:
        videos = []
        channel_id = self.get_channel_id(req.channel_title)
        if not channel_id:
            return GetVideoResponse(videos)

        search_rst = (
            self.youtube.search()
            .list(
                part="id, snippet",
                channelId=channel_id,
                maxResults=req.max_video,
                type="video",
            )
            .execute()
        )

        for item in search_rst.get("items", []):
            if "id" in item.keys() and "videoId" in item["id"]:
                video = Video(
                    uuid=item["id"]["videoId"],
                )
                if "snippet" in item.keys():
                    video.set_snippet(item["snippet"])
                videos.append(video)

        logger.info(
            f"Found following videos: {[v.id for v in videos]} "
            f"for channel: {req.channel_title}"
        )
        return GetVideoResponse(videos=videos)


# ------------- TEST -------------
# $cd ~/Documents/github/cap/worker
# $python3 -m task.get_video_task task/get_video_task.py


# debug https://developers.google.com/youtube/v3/docs/search/list
"""
{
  "kind": "youtube#searchListResponse",
  "etag": "xZoqLmCFQ_Q8oCP4a0E96QR9kSM",
  "nextPageToken": "CAEQAA",
  "regionCode": "US",
  "pageInfo": {
    "totalResults": 7077,
    "resultsPerPage": 1
  },
  "items": [
    {
      "kind": "youtube#searchResult",
      "etag": "d--nYGR-G5AwckeurbOLTRNNl7g",
      "id": {
        "kind": "youtube#video",
        "videoId": "y2eajIQeQZs"
      },
      "snippet": {
        "publishedAt": "2023-09-10T10:00:45Z",
        "channelId": "UCR2LHLiQmL_zEJnlCiyyxAA",
        "title": "花99去中国最大威士忌酒展，居然喝到将近100000？",
        "description": "时隔三年的Whisky L ！这次真的喝回票价！ 猜猜在全国最大的威士忌酒展能喝到多少钱？",
        "thumbnails": {
          "default": {
            "url": "https://i.ytimg.com/vi/y2eajIQeQZs/default.jpg",
            "width": 120,
            "height": 90
          },
          "medium": {
            "url": "https://i.ytimg.com/vi/y2eajIQeQZs/mqdefault.jpg",
            "width": 320,
            "height": 180
          },
          "high": {
            "url": "https://i.ytimg.com/vi/y2eajIQeQZs/hqdefault.jpg",
            "width": 480,
            "height": 360
          }
        },
        "channelTitle": "索菲亚一斤半Sophia1.5",
        "liveBroadcastContent": "none",
        "publishTime": "2023-09-10T10:00:45Z"
      }
    }
  ]
}
"""


async def test_get_sophia1_549_video():
    task = GetVideoTask().init()
    channel_title = "索菲亚一斤半Sophia1.5"
    rsp = await task.start(
        GetVideoRequest(
            channel_title=channel_title,
            max_video=10,
        )
    )
    print(
        "Got follow top 10 video for channel "
        f"'{channel_title}':\n {','.join([v.id for v in rsp.videos])}"
    )


def main() -> None:
    asyncio.run(test_get_sophia1_549_video())


if __name__ == "__main__":
    print("running as main...")
    main()
