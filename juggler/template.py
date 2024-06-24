import sys
from jinja2 import Environment, select_autoescape, meta
from litellm import completion
from juggler.message import Chat, MessageType, Message

class Template:
    def __init__(self, prompt: str):
        self.prompt = prompt
        self.role: MessageType = MessageType.SYSTEM
        self.chat: Chat = Chat()

    def system(self):
        self.role = MessageType.SYSTEM
        print(f"\n--- {self.role} ---\n")
        return ""

    def user(self):
        self.role = MessageType.USER
        print(f"\n--- {self.role} ---\n")
        return ""

    def assistant(self):
        self.role = MessageType.AI
        print(f"\n--- {self.role} ---\n")
        result = ""
        resp = completion(
            model="gpt-3.5-turbo",
            messages=self.chat.to_dict(),
            stream=True)
        for part in resp:
            if part.choices[0].delta.content is not None:
                result += part.choices[0].delta.content
                sys.stdout.write(part.choices[0].delta.content)
        return result

    def add_message(self, msg: Message):
        self.chat.add_message(msg)
        if msg.msg_type != MessageType.AI:
            print(msg.content)

    def run(self):
        env = Environment(
            autoescape=select_autoescape(),
        )

        env.globals.update(system=lambda: self.system())
        env.globals.update(assistant=lambda: self.assistant())
        env.globals.update(user=lambda: self.user())
        env.globals.update(gen=lambda: self.gen())

        chat = self.prompt.split("---")

        for msg in chat:
            parsed_content = env.parse(msg)
            vars = {}
            for var in meta.find_undeclared_variables(parsed_content):
                vars[var] = input(f"{var}: ").strip()

            t = env.from_string(msg)
            content = t.render(**vars).strip()
            self.add_message(Message(msg_type=self.role, content=content))



if __name__ == "__main__":
    t = Template()
    t.run()
