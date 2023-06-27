import enum
import openai
import yaml
import asyncio

from typing import List

from textual import work
from textual.app import App, ComposeResult
from textual.reactive import Reactive
from textual.message import Message
from textual.worker import Worker, get_current_worker
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.reactive import reactive
from textual.css.query import NoMatches
from textual.widget import Widget
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Static,
    Switch,
    TextLog,
    Markdown,
    LoadingIndicator,
)

from juggler.message import MessageType, LLMMessage
from juggler.components.baloon import (
    Baloon,
    BaloonContainer,
    BaloonMarkdown,
)
from juggler.components.layout import (
    Sidebar,
    ChatTitle,
    Body,
)
from juggler.llm.library import GuidanceLibrary

class Juggler(App[None]):
    CSS_PATH = "juggler.css"
    TITLE = "Juggler"
    BINDINGS = [
        ("ctrl+b", "toggle_sidebar", "History"),
    ]

    show_sidebar = reactive(False)
    messages: list[LLMMessage] = []
    first_message: bool = True
    library: GuidanceLibrary = None

    class ContentUpdate(Message):
        class Type(enum.Enum):
            UPDATE = enum.auto()
            FINISHED = enum.auto()

        def __init__(self, typ: Type, content: List[LLMMessage] = None) -> None:
            self.type = typ
            self.content = content
            super().__init__()

    def __init__(self, library: GuidanceLibrary):
        super().__init__()
        self.library = library      

    def compose(self) -> ComposeResult:
        yield Container(
            Sidebar(classes="-hidden"),
            Header(show_clock=True),
            Body(
                ChatTitle("untitled"),
            ),
            Input(),
        )
        yield Footer()

    def add_message(self, role: MessageType, content: str) -> None:
        self.messages.append(LLMMessage(role, content))
            
    @work(exit_on_error=True)
    def call_llm_title(self, content: str) -> None:
        title = self.query_one(ChatTitle)
        title.update("updating...")

        prompt = [
            {
                "role": "system",
                "content": """
Summarize the following text in 5 words. Do not end sentence with dot
and do not add any information other than the summary:

```%s```
"""%(content),
            }
        ]

        response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=prompt,
            temperature=0,
        )

        summary = response["choices"][0]["message"]["content"]
        summary = summary.strip().strip(".")
        title.update(summary)
        

    @work(exit_on_error=True)
    def call_llm(self) -> None:
        print('running thread')

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            print("creating new event loop")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)  
        
        for msgs in self.library.run_messages(self.messages):
            self.post_message(self.ContentUpdate(
                self.ContentUpdate.Type.UPDATE,
                msgs,
            ))

        self.post_message(self.ContentUpdate(self.ContentUpdate.Type.FINISHED, msgs))

    def on_juggler_content_update(self, message: ContentUpdate) -> None:
        if message.type == self.ContentUpdate.Type.FINISHED:
            self.add_message(message.content[-1].type, message.content[-1].content)

        body = self.query_one(Body)
        baloons = body.query(Baloon)

        idx_base = len(baloons)
        for i in range(len(message.content) - len(baloons)):
            idx = idx_base + i
            baloon = Baloon(message.content[idx].type,
                            message.content[idx].content,
                            True)
            body.mount(baloon)
            
        baloons = body.query(Baloon)
        for i in range(len(message.content)):
            msg = message.content[i]
            baloons[i].update(msg.content)

        # scroll body
        body.scroll_page_down()


    def on_input_submitted(self, message: Input.Submitted) -> None:
        # save message
        msg = message.value
        self.add_message(MessageType.USER, msg)

        # clear input field
        message.input.value = ""

        self.call_llm()
        if self.first_message:
            self.first_message = False
            self.call_llm_title(msg)

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one(Sidebar)
        self.set_focus(None)
        if sidebar.has_class("-hidden"):
            sidebar.remove_class("-hidden")
        else:
            if sidebar.query("*:focus"):
                self.screen.set_focus(None)
            sidebar.add_class("-hidden")

