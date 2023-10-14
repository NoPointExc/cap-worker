from pydantic import BaseModel


class Request(BaseModel):
    pass


class Response(BaseModel):
    pass


class Task:

    def init(self) -> "Task":
        return self

    async def start(self, req: Request) -> Response:
        return Response()