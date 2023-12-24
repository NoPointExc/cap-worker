import asyncio

from typing import Optional, Set
from google.oauth2.credentials import Credentials

from lib.exception import IOException, UnknownException, DependencyException
from lib.log import get_logger
from lib.user import User
from lib.video import Video
from task.transcript_task import (
    TranscriptTask,
    TranscriptRequest,
)
from task.download_task import (
    DownloadRequest,
    DownloadTask
)
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


def get_video_path(uuid: str, ext: str) -> str:
    return f"{VIDEO_DOWNLOAD_PATH}/{uuid}.{ext}"


class SingleVideoWorkflow(Workflow[Args]):
    def __init__(self):
        super().__init__(WorkflowType.VIDEO, Args)

    async def _start(self, workflow_id: int, user: User, args: Args):
        logger.info(
            f"Get videos for {args.video_uuid} for user: {user.name}...")
        video = Video(
            workflow_id=workflow_id,
            user_id=user.id,
            uuid=args.video_uuid,
        )

        await self.dowload_video(video)

        await self.transcript_video(
            video,
            args.language,
            args.promotes,
            args.transcript_fmts,
        )

        await video.save()

        if args.auto_upload:
            logger.info(f"Going to upload video {video.id}")
            await self.upload_to_youtube(
                self,
                video,
                args.language,
                user.credentials,
            )
            logger.info(f"Video {video.id} uploaded.")

        logger.info(f"videos {video.uuid} transcript successed.")

    async def transcript_video(
        self,
        video: Video,
        language: Optional[str],
        promotes: Optional[str],
        transcript_fmts: Set[str],
    ) -> None:
        transcript_task = TranscriptTask().init()
        try:
            logger.info(f"language={language}")
            _ = await transcript_task.start(
                TranscriptRequest(
                    video=video,
                    language=language,
                    transcript_fmt=list(transcript_fmts)[0],
                    promot=promotes,
                )
            )
        except Exception as e:
            logger.error(
                f"Failed to transcript video: {video.uuid} "
                f"due to error:\n {e}"
            )
            raise e

    async def dowload_video(self, video: Video) -> None:
        logger.info(f"Download videos : {video}")
        download_task = DownloadTask().init()
        try:
            download_rsp = await download_task.start(
                DownloadRequest(
                    uuid=video.uuid,
                    path=VIDEO_DOWNLOAD_PATH,
                    timeout=TIMEOUT_S,
                )
            )
            video.path = get_video_path(video.uuid, download_rsp.ext)
            logger.info(f"Download success for video: {video}")
        except Exception as e:
            logger.error(
                f"Failed to download video: {video.uuid} with error:\n {e}")
            raise e

    async def upload_to_youtube(
        self,
        video: Video,
        language: Optional[str],
        credentials: Credentials,
    ):
        transcript = video.transcript.get(DEFAULT_TRANSCRIPT_EXT, None)
        if not transcript:
            raise UnknownException(
                f"Required default transcript type: {DEFAULT_TRANSCRIPT_EXT} "
                f"not found for video: {video}"
            )

        transcript_path = f"{self._path()}/{self.id}.{DEFAULT_TRANSCRIPT_EXT}"
        try:
            with open(transcript_path, "w", encoding="utf-8") as file:
                file.write(transcript)
        except Exception as e:
            raise IOException from e

        try:
            await video.upload_transcript(
                language,
                transcript_path,
                credentials,
            )
        except Exception as e:
            raise DependencyException from e


# python3 -m workflow.single_video workflow/single_video.py
if __name__ == "__main__":
    video_workflow = SingleVideoWorkflow()
    logger.info("starting signle youtube video workflow")

    args = Args.model_validate({
        "video_uuid": "3g5KGYyneGw",
        "auto_upload": "false",
        "language": "zh",
        "transcript_fmts": ["srt"],
        "promotes": "元青花"
    })
    user = asyncio.run(User.get_by_id(3))
    workflow_id = asyncio.run(video_workflow._start(
        0, user, args
    ))
    logger.info(f"Single video has been done for workflow id: {workflow_id}")
