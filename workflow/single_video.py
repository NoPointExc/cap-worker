#!/usr/bin/env python3 -m workflow.single_video

import asyncio
import math
import time

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
SLEEP_SECONDS = 6


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
        duration_m = None
        video = await self.dowload_video(video)
        if "duration" in video.snippet:
            duration_m = math.ceil(video.snippet["duration"] / 60.0)
            if duration_m > user.credit:
                logger.warning(
                    f"No enough credit. Video {video.uuid} "
                    f"cost {duration_m} mins of credit "
                    f"but user {user.id} only has {user.credit} mins."
                )
                await self.no_credit(workflow_id)
                return False

        logger.info(
            f"Video {video.uuid} duration is {duration_m} minutes."
        )

        await self.transcript_video(
            video,
            args.language,
            args.promotes,
            args.transcript_fmts,
        )

        await video.save()
        # Charge
        if duration_m is None:
            logger.error(
                f"Can not get duration for video {video.uuid} "
                f"from workflow {workflow_id} for user: {user.id}"
            )
        elif duration_m > 0:
            await user.charge(duration_m)
        elif duration_m <= 0:
            logger.error(
                f"Duration {duration_m}mins is not expected for "
                f"video {video.uuid} from workflow {workflow_id} "
                f"for user: {user.id}"
            )

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
        await self.done(workflow_id)
        return True

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

    async def dowload_video(self, video: Video) -> Video:
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
            video.set_snippet({
                "title": download_rsp.title,
                "description": download_rsp.description,
                "duration": download_rsp.duration_s,
            })
            logger.info(f"Download success for video: {video}")
        except Exception as e:
            logger.error(
                f"Failed to download video: {video.uuid} with error:\n {e}")
            raise e

        return video

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


def test() -> None:
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
        45, user, args
    ))
    logger.info(f"Single video has been done for workflow id: {workflow_id}")


def main() -> None:
    video_workflow = SingleVideoWorkflow()
    while True:
        workflow_id = asyncio.run(video_workflow.start())
        logger.info(
            f"Single video has been done for workflow id: {workflow_id}. "
            f"Going to sleep for {SLEEP_SECONDS}s"
        )
        time.sleep(SLEEP_SECONDS)


# python3 -m workflow.single_video workflow/single_video.py
if __name__ == "__main__":
    main()
