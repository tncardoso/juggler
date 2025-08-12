import sys
import pathlib
import re
import subprocess
from jinja2 import Environment, FileSystemLoader, select_autoescape
from litellm import completion
from juggler.message import Chat, MessageType, Message
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.live import Live


class AgentPrompt(Prompt):
    prompt_suffix = ""


class SHAgent:
    def __init__(self, model: str):
        self._model = model
        self._sh_regex = re.compile(r"```sh([\s\S]+)```")
        self._chat = Chat()
        self._prompt = AgentPrompt()
        dir = pathlib.Path(__file__).parent.resolve().joinpath("prompts")
        self._env = Environment(
            loader=FileSystemLoader(dir),
            autoescape=select_autoescape(),
        )
        self._system()

    def _system(self):
        """
        Append system message
        """

        out, err = self._cmd("uname -a && $SHELL --version")
        t = self._env.get_template("sh_system.j2")
        self._chat.add_message(
            Message(
                msg_type=MessageType.SYSTEM,
                content=t.render(shell=out.decode("utf8")),
            )
        )

    def _cmd(self, cmd: str):
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        return p.communicate()

    def run(self):
        console = Console()
        while True:
            inp = self._prompt.ask("[bold green]>[/bold green] ")
            self._chat.add_message(
                Message(
                    msg_type=MessageType.USER,
                    content=inp,
                )
            )

            resp = completion(
                model=self._model, messages=self._chat.to_dict(), stream=True
            )

            assistant = ""
            with Live(Markdown(""), refresh_per_second=1) as live:
                # sys.stdout.write("\n")
                for part in resp:
                    content = part.choices[0].delta.content  # pyright: ignore
                    if content is not None:
                        assistant += content
                        live.update(Markdown(assistant))
            sys.stdout.write("\n")
            self._chat.add_message(
                Message(
                    msg_type=MessageType.AI,
                    content=assistant.strip(),
                )
            )

            m = self._sh_regex.match(assistant.strip())
            if m:
                run = Confirm.ask("run?", default=True)
                if run:
                    cmd = m.group(1)
                    out, err = self._cmd(cmd)

                    console.print(Markdown(f"```sh\n{out.decode()}\n```"))
                    if err:
                        console.print(Markdown(f"```sh\n{err.decode()}\n```"))

                    self._chat.add_message(
                        Message(
                            msg_type=MessageType.SYSTEM,
                            content=out.decode().strip(),
                        )
                    )
