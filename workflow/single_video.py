import asyncio

from lib.log import get_logger
from lib.video import Video
from task.transcript_task import (
    TranscriptTask,
    TranscriptRequest,
)
from task.download_task import (
    DownloadRequest,
    DownloadTask
)
from typing import Optional, Set
from workflow.workflow import Workflow, BaseArgs, WorkflowType


logger = get_logger(__file__)


TIMEOUT_S = 10 * 60
# trunk-ignore(bandit/B108)
VIDEO_DOWNLOAD_PATH = "/tmp/workflow/video"
DEFAULT_TRANSCRIPT_EXT = "srt"


class Args(BaseArgs):
    """
    One Example:
    {
        "video_uuid": "vO_yw27CCi4",
        "auto_upload": "false",
        "language": "CN",
        "transcript_fmts": ["srt"],
        "promotes": "元青花"
    }
    """
    video_uuid: str  # TODO validation for this.
    auto_upload: bool
    language: Optional[str] = None
    transcript_fmts: Set[str] = {"srt"}
    promotes: Optional[str] = None


class SingleVideoWorkflow(Workflow[Args]):
    def __init__(self):
        super().__init__(WorkflowType.VIDEO, Args)

    async def _start(self, id: int, user_id: int, args: Args) -> int:
        # TODO get user name with user id
        self.user_name = "sjyhehe@gmail.com"

        logger.info(
            f"Get videos for {args.video_uuid} for user: {self.user_name}...")
        video = Video(id=args.video_uuid)

        logger.info(f"Download videos : {video}")
        download_task = DownloadTask().init()
        try:
            download_rsp = await download_task.start(
                DownloadRequest(
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

        logger.info(f"videos {video.id} transcript successed.")

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
    video_workflow = SingleVideoWorkflow()
    logger.info("starting signle youtube video workflow")
    workflow_id = asyncio.run(video_workflow.start())
    logger.info(f"Single video has been done for workflow id: {workflow_id}")
