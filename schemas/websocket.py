from pydantic import BaseModel
from typing import Any

class PublishData(BaseModel):
    topic: str
    message: Any