import asyncio
import time
import logging
import json

from task.task import Task, Request, Response
from lib.exception import (
    TimeoutException,
    UnknownException,
    DependencyException,
    BadRequestException,
)


logger = logging.getLogger(__name__)

# https://developers.google.com/youtube/v3/docs/search/list
# https://github.com/ytdl-org/youtube-dl


class DownloadRequest(Request):
    # Youtube video id, e.g '5FpCdgZ-Jtk&t=20s'
    id: str
    # path to download audio/video, e.g /tmp/yt_download
    path: str
    timeout: int


class DownloadResponse(Response):
    title: str
    description: str
    duration_s: int
    # audio file extenstion. E.g webm for '5FpCdgZ-Jtk&t=20s.webm'
    ext: str


class DownloadTask(Task):

    def init(self) -> None:
        pass

    async def start(self, req: DownloadRequest) -> DownloadResponse:
        _start_time = time.time()
        """
        Example:
        $youtube-dl -f 'worstaudio/worst/bestaudio' -o '%(id)s.%(ext)s'  --print-json JUVlHzfncjw
        {"id"" "JUVlHzfncjw","title": "【恋爱记】创始人 付小龙，5000万用户app的9年坎坷发展史",..."description":"...","duration": 663,"ext": "webm",...}
        """
        if len(req.path) == 0:
            raise BadRequestException("path can't be none or empty string")

        path = req.path
        if path[-1] == "/":
            path = path[:-1]

        output = f"{path}/%(id)s.%(ext)s"
        cmd = [
            "youtube-dl",
            # for lowest cost, download audio only
            # see also: https://github.com/ytdl-org/youtube-dl#format-selection
            "--format worstaudio/worst/bestaudio",
            # E.g '5FpCdgZ-Jtk&t=20s.webm'
            f"--output '{output}'",
            "--print-json",
            req.id,
        ]

        subprocess = await asyncio.create_subprocess_shell(
            " ".join(cmd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                subprocess.communicate(),
                timeout=req.timeout,
            )
        except TimeoutError as e:
            msg = (
                f"Download timeout-ed after: {time.time() - _start_time}s"
                f" while timeout is: {req.timeout}. Error detail: {e}"
            )
            logger.error(msg)
            raise TimeoutException(msg)
        except Exception as e:
            raise UnknownException(str(e))

        if subprocess.returncode == 0 and (stderr is None or len(stderr) == 0):
            try:
                video_info = json.loads(stdout)
            except Exception as e:
                msg = (
                    f"Parse video info from json:\nstdout\n"
                    f"failed with error: {e}"
                )
                logger.error(msg)
                raise DependencyException(msg)

            title = video_info.get("title", None)
            duration_s = video_info.get("duration", None)
            ext = video_info.get("ext", None)
            description = video_info.get("description", None)

            if any(v is None for v in [
                    title,
                    duration_s,
                    ext,
                    description,
                    ]):
                logger.warning(
                    "None of following video info expect to be empty but got: "
                    f"title: {title}, duration: {duration_s}, ext: {ext}, "
                    f"description: {description}"
                )
            return DownloadResponse(
                title=title,
                duration_s=duration_s,
                ext=ext,
                description=description,
            )
        else:
            msg = (
                f"subprocess:\n ${' '.join(cmd)}\n"
                f"Failed with return code: {subprocess.returncode}\n"
                f"stdout: {stdout}\n"
                f"stderror: {stderr}\n"
            )
            logger.error(msg)
            raise DependencyException(msg)


# ------------- TEST -------------
# $cd ~/Documents/github/cap/worker
# $python3 -m task.download_task task/download_task.py
async def test_download_success() -> None:
    req = DownloadRequest(
        id="JUVlHzfncjw",
        path="/tmp/yt_download",
        timeout=2*60,
    )
    rsp = await DownloadTask().start(req)
    print(f"success and got response: {rsp}")


async def test_download_fail_with_invalid_video_id() -> None:
    req = DownloadRequest(
        id="chestnut_video",
        path="/tmp/yt_download",
        timeout=2*60,
    )
    rsp = await DownloadTask().start(req)
    print(f"success and got response: {rsp}")


def main() -> None:
    print("============================")
    print("running test 'test_download_success'.......")
    asyncio.run(test_download_success())

    print("============================")
    print("running test 'test_download_fail_with_invalid_video_id'.......")
    try:
        asyncio.run(test_download_fail_with_invalid_video_id())
    except DependencyException as e:
        print(f"Got expected dependency error: {e}")


if __name__ == "__main__":
    print("running main.......")
    main()
