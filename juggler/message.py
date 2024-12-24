import enum
from pydantic import BaseModel
from typing import List, Optional

class MessageType(str, enum.Enum):
    SYSTEM = "📢"
    USER = "👤"
    AI = "🤖"

    def to_role(self) -> Optional[str]:
        conv = {
            MessageType.SYSTEM: "system",
            MessageType.USER: "user",
            MessageType.AI: "assistant",
        }
        return conv.get(self)


    @staticmethod
    def from_role(role: str) -> "MessageType":
        if role == "system":
            return MessageType.SYSTEM
        elif role == "user":
            return MessageType.USER
        elif role == "assistant":
            return MessageType.AI
        else:
            raise ValueError("Invalid message type", role)

class Message(BaseModel):
    msg_type: MessageType
    content: str

    def to_dict(self):
        return {"role": self.msg_type.to_role(), "content": self.content}

class Chat(BaseModel):
    title: str = ""
    messages: List[Message] = []

    def to_dict(self) -> List[dict[str, str]]:
        return [m.to_dict() for m in self.messages]

    def add_message(self, msg: Message) -> None:
        self.messages.append(msg)
