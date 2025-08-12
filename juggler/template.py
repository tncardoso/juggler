import sys
from jinja2 import Environment, select_autoescape, meta
from litellm import completion
from juggler.message import Chat, MessageType, Message
from juggler.model import ContextFile
from typing import Any, List, Optional
from pathlib import Path
import re


class Template:
    def __init__(self, model: str, prompt: str):
        self.model = model
        self.prompt = prompt
        self.role: MessageType = MessageType.SYSTEM
        self.chat: Chat = Chat()

    def system(self) -> str:
        self.role = MessageType.SYSTEM
        print(f"\n--- {self.role} ---\n")
        return ""

    def user(self) -> str:
        self.role = MessageType.USER
        print(f"\n--- {self.role} ---\n")
        return ""

    def assistant(self) -> str:
        self.role = MessageType.AI
        print(f"\n--- {self.role} ---\n")
        result: str = ""
        resp = completion(model=self.model, messages=self.chat.to_dict(), stream=True)
        for part in resp:
            content = part.choices[0].delta.content  # pyright: ignore
            if content is not None:
                result += content
                sys.stdout.write(content)
        return result

    def add_message(self, msg: Message):
        self.chat.add_message(msg)
        if msg.msg_type != MessageType.AI:
            print(msg.content)

    def run(self, context: List[ContextFile], inputs: List[str] = []) -> None:
        env = Environment(
            autoescape=select_autoescape(),
        )

        env.globals.update(system=lambda: self.system())
        env.globals.update(assistant=lambda: self.assistant())
        env.globals.update(user=lambda: self.user())

        chat = self.prompt.split("---")

        for msg in chat:
            parsed_content = env.parse(msg)
            vars: dict[str, Any] = {"context": context, "inputs": inputs}

            for var in meta.find_undeclared_variables(parsed_content):
                if var != "inputs" and var != "context":
                    vars[var] = input(f"{var}: ").strip()

            t = env.from_string(msg)
            content = t.render(**vars).strip()
            self.add_message(Message(msg_type=self.role, content=content))


class TemplateLoader:
    """
    Load templates following a path hierarchy. The first
    template with provided name is returned.
    """

    def __init__(self, dirs: List[Path]):
        self.dirs = dirs

    def get_by_name(self, model: str, name: str) -> Optional[Template]:
        """
        Iterate directories looking for file with given name. The
        first one found is returned.
        """

        for d in self.dirs:
            path = d.joinpath(name)
            if path.exists():
                with open(path, "r") as f:
                    content = f.read()
                    t = Template(model, content)
                    return t
        return None

    def list(self):
        # regex to find all entries with format {# summary: text #} and extract text
        pattern = r"{#[\s]+summary:[\s]+(.*)[\s]*#}"

        for d in self.dirs:
            for f in d.glob("*.j2"):
                path = d.joinpath(f.name)
                content = path.read_text()

                summary = ""
                matches = re.findall(pattern, content)
                for m in matches:
                    summary += m.strip()

                if summary == "":
                    print(f"{f.name.rstrip('.j2')}")
                else:
                    print(f"{f.name.rstrip('.j2')}: {summary}")


if __name__ == "__main__":
    t = Template("gpt-4o-mini", "hello")
    t.run([])
