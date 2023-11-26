import asyncio

from typing import Optional
from task.transcript_task import (
    TranscriptTask,
    TranscriptRequest,
)
from task.download_task import (
    DownloadRequest,
    DownloadTask
)
from lib.log import get_logger
from lib.video import Video


logger = get_logger(__file__)


TIMEOUT_S = 10 * 60
# trunk-ignore(bandit/B108)
VIDEO_DOWNLOAD_PATH = "/tmp/workflow/video"
DEFAULT_TRANSCRIPT_EXT = "srt"


class SingleVideoWorkflow:

    def __init__(self, video_id: str, user_name: Optional[str]) -> None:
        self.video_id = video_id
        self.user_name = user_name

    async def start(self) -> None:
        logger.info(f"Get videos for {self.video_id} for user: {self.user_name}...")
        video = Video(id=self.video_id)

        logger.info(f"Download videos : {video}")
        download_task = DownloadTask().init()
        try:
            download_rsp = await download_task.start(DownloadRequest(
                    id=video.id,
                    path=VIDEO_DOWNLOAD_PATH,
                    timeout=TIMEOUT_S,
                )
            )
            video.path = f"{VIDEO_DOWNLOAD_PATH}/{video.id}.{download_rsp.ext}"
            logger.info(f"Download success for video: {video}")
        except Exception as e:
            logger.error(f"Failed to download video: {video} with error:\n {e}")
            raise e

        transcript_task = TranscriptTask().init()
        try:
            _ = await transcript_task.start(
                TranscriptRequest(
                    videos=[video],
                    language="zh",
                )
            )
        except Exception as e:
            logger.error(
                f"Failed to transcript video: {video} "
                f"due to error:\n {e}"
            )
            raise e

        logger.info(f"videos {self.video_id} transcript successed.")

        # video.save_as_json()
        tran_pathes = video.save_transcript()
        logger.info(f"Transcript has been writen into : {tran_pathes}")
        transcript_path = tran_pathes.get(DEFAULT_TRANSCRIPT_EXT, None)
        if transcript_path:
            logger.info(
                f"Uploading transcript in {transcript_path} "
                "to the Youtube"
            )
            await video.upload_transcript(transcript_path, self.user_name)
            logger.info("uploaded")
        else:
            logger.info("upload skipped")
        logger.info("All done")


# python3 -m workflow.single_video workflow/single_video.py
if __name__ == "__main__":
    # TODO get args from cli??
    workflow = SingleVideoWorkflow(
        video_id="3g5KGYyneGw",
        user_name="sjyhehe@gmail.com",
    )
    logger.info("starting signle youtube video workflow")
    asyncio.run(workflow.start())
    logger.info("Single video has been done for video_id: 3g5KGYyneGw")
