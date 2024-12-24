import sys
import pathlib
from litellm import completion
from juggler.message import Chat, Message, MessageType

def complete(model: str, fname: pathlib.Path) -> None:
    with open(fname, "r") as f:
        content = f.read()

    with open(fname, "a") as f:
        chat = Chat()
        chat.add_message(
            Message(
                msg_type=MessageType.SYSTEM,
                content="""
You are a specialist in programming, your job is to expand the provided content. No aditional content or markdown should be provided, only respond with the incremental content.

# Instructions

- Do not add markdown or triple quotes
- Only return the content that should be appended to file
""",
            )
        )

        chat.add_message(
            Message(
                msg_type=MessageType.USER,
                content=content,
            )
        )
        print(content)

        resp = completion(model=model, messages=chat.to_dict(), stream=True)
        for part in resp:
            content = part.choices[0].delta.content # pyright: ignore
            if content is not None:
                sys.stdout.write(content)
                f.write(content)
                f.flush()
