from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.css.query import NoMatches
from textual.widgets import (
    Static,
    Markdown,
    LoadingIndicator,
)

from juggler.message import MessageType

class Avatar(Container):
    avatar: MessageType = MessageType.SYSTEM

    def __init__(self, avatar):
        super().__init__()
        self.avatar = avatar

    def compose(self) -> ComposeResult:
        yield Static(self.avatar)

class BaloonContainer(Container):
    pass

class BaloonMarkdown(Markdown):
    pass

class Baloon(Container):
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

    def update(self, content: str):
        self.content = content

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

