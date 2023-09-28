import logging
import asyncio
import openai


from task.task import Task, Request, Response
from lib.video import Video
from lib.config import OPENAI_API_KEY
from typing import List

logger = logging.getLogger(__name__)

OPENAI_DOMAIN = "https://api.openai.com/v1/"


class TranscriptRequest(Request):
    videos: List[Video]
    language: str


class TranscriptResponse(Response):
    # TODO only return videos with transcript
    videos: List[Video]


class TranscriptTask(Task):

    async def transcribe(self, video: Video) -> Video:
        openai.api_key = OPENAI_API_KEY

        prompts = []
        snippet = video.snippet

        if "channelTitle" in snippet.keys():
            prompts.append(snippet["channelTitle"])
        if "title" in snippet.keys():
            prompts.append(snippet["title"])
        if "description" in snippet.keys():
            prompts.append(snippet["description"])

        with open(video.path, "rb") as file:
            transcript = await openai.Audio.atranscribe(
                model="whisper-1",
                file=file,
                prompt=";".join(prompts),
                response_format="srt",
                language="zh",
            )
            video.transcript = {"srt": transcript}
        return video

    async def start(self, req: TranscriptRequest) -> TranscriptResponse:

        processed_videos = []
        for video in req.videos:
            processed = await self.transcribe2(video)
            processed_videos.append(processed)

        return TranscriptResponse(videos=processed_videos)


# ------------- TEST -------------
# $cd ~/Documents/github/cap/worker
# $python3 -m task.transcript_task task/transcript_task.py
async def test_transcript_a_video() -> None:
    task = TranscriptTask()
    task.init()
    video = Video(
        id="random_id",
        path="/Users/jiayangsun/Documents/github/cap/media/talkshow.mp3",
        snippet={"channelTitle": "智胜", "description": "女同学"},
        transcript={}
    )
    rsp = await task.start(TranscriptRequest(videos=[video], language="zh"))
    assert len(rsp.videos) == 1, "The transcript task expect to get 1 response"
    print(rsp.videos[0].transcript)


def main() -> None:
    asyncio.run(test_transcript_a_video())


if __name__ == "__main__":
    print("running as main...")
    main()
