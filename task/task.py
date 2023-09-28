from pydantic import BaseModel


class Request(BaseModel):
    pass


class Response(BaseModel):
    pass


class Task:

    def init(self) -> None:
        pass

    async def start(self, req: Request) -> Response:
        return Response()