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
from typing import Optional, List
import uuid
from datetime import datetime

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

class SessionButton(Button):
    def __init__(self, session_id: str, title: str):
        super().__init__(title)
        self.session_id = session_id
    
    def key_enter(self) -> None:
        # Use post_message to ensure proper event handling
        self.post_message(Button.Pressed(self))
    
    def key_space(self) -> None:
        # Use post_message to ensure proper event handling
        self.post_message(Button.Pressed(self))

class Sidebar(ScrollableContainer):
    sessions: List[Chat] = []
    
    def compose(self) -> ComposeResult:
        yield Title("Sessions")
        
    async def add_session(self, chat: Chat) -> None:
        self.sessions.append(chat)
        session_button = SessionButton(chat.session_id, chat.title or "New chat")
        await self.mount(session_button)
        
    def remove_all_sessions(self) -> None:
        for button in self.query(SessionButton):
            button.remove()
            
    async def refresh_sessions(self) -> None:
        self.remove_all_sessions()
        for chat in self.sessions:
            session_button = SessionButton(chat.session_id, chat.title or "New chat")
            await self.mount(session_button)
    
    def key_down(self) -> None:
        buttons = self.query(SessionButton)
        if not buttons:
            return
            
        focused = self.screen.focused
        if isinstance(focused, SessionButton):
            try:
                current_index = list(buttons).index(focused)
                next_index = min(current_index + 1, len(buttons) - 1)
                buttons[next_index].focus()
            except ValueError:
                buttons[0].focus()
        else:
            buttons[0].focus()
    
    def key_up(self) -> None:
        buttons = self.query(SessionButton)
        if not buttons:
            return
            
        focused = self.screen.focused
        if isinstance(focused, SessionButton):
            try:
                current_index = list(buttons).index(focused)
                prev_index = max(current_index - 1, 0)
                buttons[prev_index].focus()
            except ValueError:
                buttons[-1].focus()
        else:
            buttons[-1].focus()
    
    def key_enter(self) -> None:
        focused = self.screen.focused
        if isinstance(focused, SessionButton):
            # Use post_message to ensure proper event handling
            focused.post_message(Button.Pressed(focused))
    
    def key_escape(self) -> None:
        # Close sidebar when escape is pressed
        self.app.set_sidebar(False)

class Juggler(App[None]):
    TITLE = "Juggler"
    CSS_PATH = "juggler.tcss"
    BINDINGS = [
        Binding("f2", "toggle_sidebar", "Sidebar"),
        Binding("ctrl+n", "new_chat", "New"),
        Binding("ctrl+q", "app.quit", "Quit", show=True),
    ]

    current_baloon: Optional[Baloon] = None
    current_chat: Chat = Chat()
    current_title: ChatTitle = ChatTitle("New chat")
    body: Body
    sidebar: Sidebar
    sessions: List[Chat] = []

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
        self.sidebar = self.query_one(Sidebar)
        self.set_sidebar(False)
        self.create_new_session()

    def set_sidebar(self, open: bool) -> None:
        sidebar = self.query_one(Sidebar)
        if open:
            sidebar.remove_class("-hidden")
            # Focus first session if available, otherwise focus sidebar itself
            session_buttons = sidebar.query(SessionButton)
            if session_buttons:
                session_buttons[0].focus()
            else:
                sidebar.focus()
        else:
            # Remove focus from sidebar elements first to prevent CSS :focus-within override
            focused = self.screen.focused
            if focused and (focused == sidebar or sidebar in focused.ancestors_with_self):
                self.screen.set_focus(None)
            
            sidebar.add_class("-hidden")
            
            # Focus input after sidebar is hidden
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
        
        self.save_current_session()
        self.run_worker(self.sidebar.refresh_sessions())

    async def update_chat(self) -> None:
        # add current assistant baloon
        body = self.query_one(Body)
        self.current_baloon = Baloon(MessageType.AI, "")
        await body.mount(self.current_baloon)

        messages = self.current_chat.to_dict()
        resp = await acompletion(model=self.model, messages=messages, stream=True)
        self.current_baloon.loaded()
        async for part in resp: # pyright: ignore
            if part.choices[0].delta.content is not None:
                self.current_baloon.update_delta(part.choices[0].delta.content)
                self.body.scroll_end()

        self.current_chat.add_message(Message(msg_type=MessageType.AI, content=self.current_baloon.content))
        self.body.scroll_end()
        self.save_current_session()

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
        self.save_current_session()

    def create_new_session(self) -> None:
        session_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        self.current_chat = Chat(session_id=session_id, created_at=created_at)
        
    def save_current_session(self) -> None:
        if self.current_chat.session_id:
            existing_session = next((s for s in self.sessions if s.session_id == self.current_chat.session_id), None)
            if existing_session:
                existing_session.title = self.current_chat.title
                existing_session.messages = self.current_chat.messages
            else:
                self.sessions.append(self.current_chat)
                self.run_worker(self.sidebar.add_session(self.current_chat))
    
    async def switch_to_session(self, session_id: str) -> None:
        try:
            self.save_current_session()
            
            session = next((s for s in self.sessions if s.session_id == session_id), None)
            if session:
                self.current_chat = session
                self.current_title.update(session.title or "New chat")
                
                # Remove existing balloons
                for baloon in self.query(Baloon):
                    baloon.remove()
                
                # Add messages from the session one by one with small delays
                for i, message in enumerate(session.messages):
                    baloon = Baloon(message.msg_type, message.content, True)
                    await self.body.mount(baloon)
                    # Small delay to prevent blocking
                    if i % 5 == 0:  # Every 5 messages, yield control
                        await self.sleep(0.01)
                
                self.body.scroll_end()
        except Exception as e:
            log(f"Error switching session: {e}")

    def action_new_chat(self) -> None:
        self.save_current_session()
        self.current_baloon = None
        self.create_new_session()
        self.current_title.update("New chat")
        self.query(Baloon).remove()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one(Sidebar)
        if sidebar.has_class("-hidden"):
            self.set_sidebar(True)
        else:
            self.set_sidebar(False)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if isinstance(event.button, SessionButton):
            # Close sidebar immediately for better UX
            self.set_sidebar(False)
            
            # If clicking the already active session, just close sidebar
            if event.button.session_id == self.current_chat.session_id:
                return
                
            # Switch session in background
            self.run_worker(self.switch_to_session(event.button.session_id), exclusive=True)
