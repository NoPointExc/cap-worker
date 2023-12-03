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
    video_uuid: str  # TODO validation for this to return invliad uuid fast.
    auto_upload: bool
    # TODO validation for language and transcript formats
    language: Optional[str] = None
    transcript_fmts: Set[str] = {"srt"}
    # TODO validation on promotes size.
    # TODO should be "prompts". Typo, but this has been copy past everywhere.
    promotes: Optional[str] = None

    @property
    def transcript_fmt(self) -> str:
        transcript_fmt = "srt"
        if len(self.transcript_fmts) > 0:
            transcript_fmt = list(self.transcript_fmts)[0]
        if len(self.transcript_fmts) > 1:
            logger.warning(
                "More than one transcript_fmts "
                f"requests: {self.transcript_fmts} "
                f"which is not supported now. "
                f"Taking {transcript_fmt} only now."
            )
        return transcript_fmt


class SingleVideoWorkflow(Workflow[Args]):
    def __init__(self):
        super().__init__(WorkflowType.VIDEO, Args)

    async def _start(self, workflow_id: int, user_id: int, args: Args) -> int:
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
            logger.info(f"language={args.language}")
            _ = await transcript_task.start(
                TranscriptRequest(
                    videos=[video],
                    language=args.language,
                    promot=args.promotes,
                    transcript_fmt=args.transcript_fmt,
                )
            )
        except Exception as e:
            logger.error(
                f"Failed to transcript video: {video} "
                f"due to error:\n {e}"
            )
            raise e

        logger.info(f"videos {video.id} transcript successed.")

        tran_pathes = video.save_transcript()
        logger.info(f"Transcript has been writen into : {tran_pathes}")
        transcript_path = tran_pathes.get(DEFAULT_TRANSCRIPT_EXT, None)
        if transcript_path and args.auto_upload:
            logger.info(
                f"Uploading transcript in {transcript_path} "
                "to the Youtube"
            )
            # TODO handle error when no access to upload
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
