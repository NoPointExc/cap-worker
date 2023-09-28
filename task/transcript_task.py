import logging
import aiohttp
import json
import asyncio
import os
import base64

from task.task import Task, Request, Response
from lib.video import Video
from lib.config import OPENAI_API_KEY
from typing import List

logger = logging.getLogger(__name__)

OPENAI_DOMAIN = "https://api.openai.com/v1/"


class TranscriptRequest(Request):
    videos: List[Video]


class TranscriptResponse(Response):
    videos: List[Video]


class TranscriptTask(Task):
    def init(self) -> None:
        self.headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

    # TODO check out how to async this with openai lib
    async def transcribe(self, video: Video) -> Video:
        prompts = []
        snippet = video.snippet

        if "channelTitle" in snippet.keys():
            prompts.append(snippet["channelTitle"])
        if "title" in snippet.keys():
            prompts.append(snippet["title"])
        if "description" in snippet.keys():
            prompts.append(snippet["description"])

        """
        - file: The audio file to transcribe, in one of these formats: mp3, mp4, mpeg, mpga, m4a, wav, or webm.
        example: '@/path/to/file/audio.mp3'
        - model: ID of the model to use. Only whisper-1 is currently available. E.g 'whisper-1'
        - prompt: An optional text to guide the model's style or continue a previous audio segment.
        The prompt should match the audio language.
        - response_format: The format of the transcript output, in one of these options: json, text,
        srt, verbose_json, or vtt.
        - temperature: The sampling temperature, between 0 and 1. Higher values like 0.8 will make the
        output more random, while lower values like 0.2 will make it more focused and deterministic. If
        set to 0, the model will use log probability to automatically increase the temperature until certain
        thresholds are hit.
        - language: The language of the input audio. Supplying the input language in ISO-639-1 format will
        improve accuracy and latency.
        """
       
        with open(video.path, "rb") as file:
            file_content = file.read()
        request = {
            'file': base64.b64encode(file_content).decode('utf-8'),
            'model': 'whisper-1',
            'prompt': ';'.join(prompts),
            'response_format': 'srt',
        }
        # TODO debug return code 400 and 502 when internet came back
        async with aiohttp.ClientSession(headers=self.headers) as session:
            # TODO handle aiohttp.client_exceptions.ClientConnectorError
            async with session.post(
                f"{OPENAI_DOMAIN}/audio/transcriptions",
                data=request,
            ) as rsp:
                print(rsp.status)
                if rsp.status == 200:
                    video.transcript = await rsp.json()
                    logger.debug(f"Got response:\n {str( video.transcript)[:600]}")
                else:
                    # TODO handle non-200 return code.
                    print(f"Got error {rsp.status}, {rsp}")
        return video

    async def start(self, req: TranscriptRequest) -> TranscriptResponse:

        processed_videos = []
        for video in req.videos:
            processed = await self.transcribe(video)
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
    rsp = await task.start(TranscriptRequest(videos=[video]))
    assert len(rsp.videos) == 1, "The transcript task expect to get 1 response"
    print(rsp.videos[0].transcript)


def main() -> None:
    asyncio.run(test_transcript_a_video())


if __name__ == "__main__":
    print("running as main...")
    main()
