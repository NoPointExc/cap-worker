from pydantic import BaseModel
from task.task import Task, Request, Response

class Channel(BaseModel):
    
    def get_tasks(self) -> List[Task]:
        pass
