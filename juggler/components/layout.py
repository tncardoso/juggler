from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import (
    Container,
    ScrollableContainer,
)

class Body(ScrollableContainer):
    pass

class ChatTitle(Static):
    pass

class Title(Static):
    pass

class Sidebar(Container):
    def compose(self) -> ComposeResult:
        yield Title("Chat History")
        yield Static("coming soon...")