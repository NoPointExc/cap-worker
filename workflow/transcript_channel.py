import asyncio
import logging

from typing import Optional
from task.transcript_task import (
    TranscriptTask,
    TranscriptRequest,
)
from task.download_task import (
    DownloadRequest,
    DownloadTask
)
from task.get_video_task import (
    GetVideoRequest,
    GetVideoTask
)
from lib.log import get_logger


logger = get_logger(__file__)


MAX_VIDEO = 2
TIMEOUT_S = 10 * 60
# trunk-ignore(bandit/B108)
VIDEO_DOWNLOAD_PATH = "/tmp/workflow/video"
DEFAULT_TRANSCRIPT_EXT = "srt"


class TranscriptChannelWorkflow:

    def __init__(self, channel_title: str, user_name: Optional[str]) -> None:
        self.channel_title = channel_title
        self.max_video = MAX_VIDEO
        self.user_name = user_name
        self.videos = []

    async def start(self) -> None:
        logger.info(f"Get videos for channel {self.channel_title}...")
        get_video_task = GetVideoTask().init()
        get_video_rsp = await get_video_task.start(GetVideoRequest(
            channel_title=self.channel_title,
            max_video=self.max_video
        ))

        all_videos = get_video_rsp.videos

        logger.info(f"Download videos : {all_videos}")
        for video in all_videos:
            # TODO call signle video workflow.


# python3 -m workflow.transcript_channel workflow/transcript_channel.py
# if __name__ == "__main__":
#     # TODO get args from cli??
#     workflow = TranscriptChannelWorkflow(
#         channel_title="索菲亚一斤半Sophia1.5"
#     )
#     asyncio.run(workflow.start())