import enum
from pydantic import BaseModel

class MessageType(str, enum.Enum):
    SYSTEM = "📢"
    USER = "👤"
    AI = "🤖"

    @staticmethod
    def from_openai_role(role: str):
        if role == "system":
            return MessageType.SYSTEM
        elif role == "user":
            return MessageType.USER
        elif role == "assistant":
            return MessageType.AI
        else:
            raise 'illegalfixme'


#class Message(BaseModel):
class LLMMessage:
    type: MessageType
    content: str

    def __init__(self, typ, content):
        self.type = typ
        self.content = content
        super().__init__()
