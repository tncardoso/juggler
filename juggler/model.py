from pydantic import BaseModel


class ContextFile(BaseModel):
    filename: str
    content: str
