from litellm import acompletion
from textual import log
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import (
    Static,
    Header,
    Footer,
    Button,
    Input,
    Markdown,
    LoadingIndicator,
    TextArea,
)
from juggler.message import Message, MessageType, Chat
from typing import Optional

class Body(ScrollableContainer):
    pass

class ChatTitle(Static):
    pass

class Title(Static):
    pass

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
    content = reactive("")
    container: BaloonContainer
    markdown: BaloonMarkdown
    message_type: MessageType = MessageType.SYSTEM
    add_loaded: bool = False
    isloading: bool = True

    def __init__(self, message_type: MessageType, content: str, add_loaded: bool=False):
        super().__init__()
        self.message_type = message_type
        self.add_loaded = add_loaded
        self.content = content
        self.markdown = BaloonMarkdown(content)
        self.container = BaloonContainer(LoadingIndicator())

    def compose(self) -> ComposeResult:
        yield Avatar(self.message_type)
        yield self.container

    def loaded(self) -> None:
        if self.isloading:
            for widget in self.container.children:
                widget.remove()
            self.container.mount(self.markdown)
            self.isloading = False

    def on_mount(self) -> None:
        if self.add_loaded:
            self.loaded()

    def update(self, content: str):
        self.content = content

    def update_delta(self, delta: str):
        self.content += delta

    async def watch_content(self, content: str) -> None:
        try:
            await self.markdown.update(content)
        except NoMatches:
            pass

class Sidebar(ScrollableContainer):
    def compose(self) -> ComposeResult:
        yield Title("Templates")
        yield Title("Sessions")

class Juggler(App[None]):
    TITLE = "Juggler"
    CSS_PATH = "juggler.tcss"
    BINDINGS = [
        Binding("f1", "toggle_sidebar", "Sidebar"),
        Binding("f2", "new_chat", "New"),
        Binding("ctrl+q", "app.quit", "Quit", show=True),
    ]

    current_baloon: Optional[Baloon] = None
    current_chat: Chat = Chat()
    current_title: ChatTitle = ChatTitle("New chat")
    body: Body

    def __init__(self, model: str):
        super(Juggler, self).__init__()
        self.model = model

    def compose(self) -> ComposeResult:
        yield Container(
            Sidebar(classes="-hidden"),
            Header(show_clock=False),
            Body(
                self.current_title,
            ),
            Input(),
            Footer(),
        )

    def on_mount(self) -> None:
        input = self.query_one(Input)
        input.focus()
        self.body = self.query_one(Body)
        self.set_sidebar(False)

    def set_sidebar(self, open: bool) -> None:
        sidebar = self.query_one(Sidebar)
        if open:
            sidebar.remove_class("-hidden")
        else:
            sidebar.add_class("-hidden")
            if sidebar.query("*:focus"):
                self.screen.set_focus(None)
                input = self.query_one(Input)
                input.focus()

    async def update_chat_name(self) -> None:
        prompt = f"Summarize in one short sentence the following message:\n\n{self.current_chat.messages[0].content}"
        messages = [
            {"role": "user", "content": prompt},
        ]

        resp = await acompletion(model=self.model, messages=messages, stream=True)
        async for part in resp: # pyright: ignore
            if part.choices[0].delta.content is not None:
                self.current_chat.title += part.choices[0].delta.content
                self.current_title.update(self.current_chat.title)

    async def update_chat(self) -> None:
        # add current assistant baloon
        body = self.query_one(Body)
        self.current_baloon = Baloon(MessageType.AI, "")
        body.mount(self.current_baloon)

        messages = self.current_chat.to_dict()
        resp = await acompletion(model=self.model, messages=messages, stream=True)
        self.current_baloon.loaded()
        async for part in resp: # pyright: ignore
            if part.choices[0].delta.content is not None:
                self.current_baloon.update_delta(part.choices[0].delta.content)
                self.body.scroll_end()

        self.current_chat.add_message(Message(msg_type=MessageType.AI, content=self.current_baloon.content))
        self.body.scroll_end()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value == "":
            # ignore if no text was input
            return

        # add user baloon and fill with content
        self.current_chat.add_message(Message(msg_type=MessageType.USER, content=event.value))
        body = self.query_one(Body)
        user_baloon = Baloon(MessageType.USER, event.value, True)
        await body.mount(user_baloon)
        event.input.value = ""

        # if this is the first message, update chat title
        if len(self.current_chat.messages) == 1:
            self.run_worker(self.update_chat_name())

        # call completion
        self.run_worker(self.update_chat())

    def action_new_chat(self) -> None:
        self.current_baloon = None
        self.current_chat = Chat()
        self.current_title.update("New chat")
        self.query(Baloon).remove()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one(Sidebar)
        if sidebar.has_class("-hidden"):
            self.set_sidebar(True)
        else:
            self.set_sidebar(False)
