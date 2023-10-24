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

logger = logging.getLogger(__file__)


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
        download_success = []
        download_failed = []
        download_task = DownloadTask().init()
        for video in all_videos:
            try:
                download_rsp = await download_task.start(DownloadRequest(
                        id=video.id,
                        path=VIDEO_DOWNLOAD_PATH,
                        timeout=TIMEOUT_S,
                    )
                )
                video.path = f"{VIDEO_DOWNLOAD_PATH}/{video.id}.{download_rsp.ext}"
                logger.info(f"Download success for video: {video}")
                download_success.append(video)
            except Exception as e:
                logger.error(f"Failed to download video: {video} with error:\n {e}")
                download_failed.append(video)

        logger.info(
            f"{len(download_success)}/{len(all_videos)} videos"
            " download successed."
        )

        logger.info(f"Transcript videos : {download_success}...")
        transcript_success = []
        transcript_failed = []
        transcript_task = TranscriptTask().init()
        for video in download_success:
            try:
                tran_rsp = await transcript_task.start(
                    TranscriptRequest(
                        videos=[video],
                        language="zh",
                    )
                )
                transcript_success.extend(tran_rsp.videos)
            except Exception as e:
                logger.error(
                    f"Failed to transcript video: {video} "
                    f"due to error:\n {e}"
                )
                transcript_failed.append(video)

        logger.info(
            f"{len(transcript_success)}/{len(all_videos)} videos"
            " transcript successed."
        )

        logger.info("Saving result as json file into ")
        for video in transcript_success:
            video.save_as_json()
            tran_pathes = video.save_transcript()
            transcript_path = tran_pathes.get(DEFAULT_TRANSCRIPT_EXT, None)
            if transcript_path:
                video.upload_transcript(transcript_path)


# python3 -m workflow.transcript_channel workflow/transcript_channel.py
if __name__ == "__main__":
    # TODO get args from cli??
    workflow = TranscriptChannelWorkflow(
        channel_title="索菲亚一斤半Sophia1.5"
    )
    asyncio.run(workflow.start())
