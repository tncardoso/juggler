import enum
import openai

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


class MessageType(str, enum.Enum):
    SYSTEM = "📢"
    USER = "👤"
    AI = "🤖"

class Body(ScrollableContainer):
    pass

class Title(Static):
    DEFAULT_CSS = """
    Title {
        margin: 1 4;
        padding: 1 2;
        background: cornflowerblue;
        color: black;
        text-align: center;
        text-style: bold;
    }
    """
    pass

class Avatar(Container):
    DEFAULT_CSS = """
    Avatar {
        width: 5;
        height: 3;
        content-align: center middle;
        padding: 1;
    }
    """

    avatar: MessageType = MessageType.SYSTEM

    def __init__(self, avatar):
        super().__init__()
        self.avatar = avatar

    def compose(self) -> ComposeResult:
        yield Static(self.avatar)

class BaloonContainer(Container):
    DEFAULT_CSS = """
    BaloonContainer {
        height: auto;
        min-height: 3;
        padding-bottom: 0;
    }
    """

class BaloonMarkdown(Markdown):
    DEFAULT_CSS = """
    BaloonMarkdown {
        padding: 0;
        margin: 0;
    }
    """

class Baloon(Container):
    DEFAULT_CSS = """
    Baloon {
        height: auto;
        width: 100%;
        margin: 1 3;
        border: tall $background;
        background: $boost;
        layout: horizontal;
        padding: 0;
    }
    """

    content: str = reactive("")
    message_type: MessageType = MessageType.SYSTEM
    loading = reactive(True)
    add_loaded: bool = False

    def __init__(self, message_type, content, add_loaded=False):
        super().__init__()
        self.message_type = message_type
        self.content = content
        self.add_loaded = add_loaded

    def compose(self) -> ComposeResult:
        yield Avatar(self.message_type)
        yield BaloonContainer()

    def on_mount(self) -> None:
        if self.add_loaded:
            self.loading = False

    def watch_loading(self, loading: bool) -> None:
        container = self.query_one(BaloonContainer)
        for widget in container.children:
            widget.remove()

        if loading:
            container.mount(LoadingIndicator())
        else:
            container.mount(BaloonMarkdown(self.content))

    def watch_content(self, content: str) -> None:
        try:
            mark = self.query_one(BaloonMarkdown)
            mark.update(content)
        except NoMatches:
            pass


class Sidebar(Container):
    def compose(self) -> ComposeResult:
        yield Title("Chat History")
        yield Static("hello hello")

class Juggler(App[None]):
    CSS_PATH = "juggler.css"
    TITLE = "Juggler"
    BINDINGS = [
        ("ctrl+b", "toggle_sidebar", "History"),
    ]

    show_sidebar = reactive(False)
    messages: list[dict[str, str]] = []

    class ContentUpdate(Message):
        class Type(enum.Enum):
            UPDATE = enum.auto()
            FINISHED = enum.auto()

        def __init__(self, typ: Type, content: str = None) -> None:
            super().__init__()
            self.type = typ
            self.content = content

    def compose(self) -> ComposeResult:
        yield Container(
            Sidebar(classes="-hidden"),
            Header(show_clock=True),
            Body(
                Title("untitled"),
            ),
            Input(),
        )
        yield Footer()

    def add_message(self, role: MessageType, content: str) -> None:
        typ = "system"
        if role == MessageType.AI:
            typ = "assistant"
        elif role == MessageType.USER:
            typ = "user"

        self.messages.append({
            "role": typ,
            "content": content,
        })

    @work(exclusive=True)
    def call_llm(self) -> None:
        print('running thread')
        response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=self.messages,
            temperature=0,
            stream=True,
        )

        for chunk in response:
            if "content" in chunk["choices"][0]["delta"]:
                self.post_message(self.ContentUpdate(
                    self.ContentUpdate.Type.UPDATE,
                    chunk["choices"][0]["delta"]["content"],
                ))
            self.post_message(self.ContentUpdate(self.ContentUpdate.Type.FINISHED))

    def on_gen_juggler_content_update(self, message: ContentUpdate) -> None:
        print(message)
        baloon = self.query(Baloon).last()

        if baloon.loading:
            baloon.loading = False

        if message.type == self.ContentUpdate.Type.FINISHED:
            self.add_message(MessageType.AI, baloon.content)
        else:
            baloon.content += message.content

        # scroll container
        body = self.query_one(Body)
        body.scroll_page_down()

    def on_input_submitted(self, message: Input.Submitted) -> None:
        # save message
        msg = message.value
        self.add_message(MessageType.USER, msg)
        user_baloon = Baloon(MessageType.USER, msg, True)
        ai_baloon = Baloon(MessageType.AI, "")

        # mount baloons
        body = self.query_one(Body)
        body.mount(user_baloon, ai_baloon)

        # clear input field
        message.input.value = ""

        self.call_llm()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one(Sidebar)
        self.set_focus(None)
        if sidebar.has_class("-hidden"):
            sidebar.remove_class("-hidden")
        else:
            if sidebar.query("*:focus"):
                self.screen.set_focus(None)
            sidebar.add_class("-hidden")


if __name__ == "__main__":
    app = Juggler()
    app.run()
