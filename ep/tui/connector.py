from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop, Task, get_event_loop
from dataclasses import dataclass, field
from functools import partial, wraps
from json import loads as json_loads
from pickle import loads as pickle_loads
from traceback import format_exc
from typing import TYPE_CHECKING, Any, Optional, Coroutine, Callable, Union

import websockets
from discord import Client, Message

if TYPE_CHECKING:
    import ep

__all__ = ("BaseConnector", "DiscordClientConnector", "WebsocketConnector", "IndependantConnector")

@dataclass
class BaseConnector(ABC):
    """
    """
    window: "ep.tui.Window"
    config: "ep.Config"
    loop: AbstractEventLoop = field(default_factory=get_event_loop)

    __task: Optional[Task] = field(init=False, default=None)

    def refresh(self, **kwargs) -> None:
        if self.__task is not None:
            self.__task.cancel()

        self.__task = self.loop.create_task(self.exhaust(**kwargs))

    def update_widgets(self, data) -> None:
        for widget in self.window.widgets:
            widget.update(data, self.config["ep"]["tui"])

    @abstractmethod
    async def exhaust(self):
        """
        """


class WebsocketConnector(BaseConnector):
    """A websocket based connector."""

    __socket = None

    async def exhaust(self, uri: str):
        async with websockets.connect(uri) as websocket:
            self.__socket = websocket

            async for message in websocket:
                data = await self.loop.run_in_executor(None, partial(pickle_loads, message))
                self.update_widgets(data)


@dataclass
class DiscordClientConnector(BaseConnector, Client):
    """A :class:`discord.Client` based connector."""

    def __post_init__(self):
        Client.__init__(self, loop=self.loop)

    # Event handlers

    async def on_connect(self) -> None:
        self.update_widgets("Connected")

    async def on_ready(self) -> None:
        self.update_widgets("Ready")

    async def on_message(self, message: Message) -> None:
        try:
            if message.channel.id == self.config["ep"]["socket_channel"]:
                content = message.content[8:-3]
                data = json_loads(content)
                self.update_widgets(data)
        except Exception:
            for line in format_exc().split('\n'):
                self.update_widgets(line)

    async def on_error(self, event, *args, **kwargs) -> None:
        self.update_widgets((event, format_exc()))

    # Public api

    async def exhaust(self, token: str):
        try:
            await self.start(token, bot=False)
        finally:
            await self.logout()


class IndependantConnector(DiscordClientConnector):
    """A :class:`discord.Client` based connector that focuses on its own raw socket responses."""

    async def on_message(self, message: Message) -> None:
        return None  # dummy overload

    async def on_socket_response(self, payload: Union[Any, bytes]) -> None:
        if isinstance(payload, bytes) or not self.is_ready():
            return

        self.update_widgets(payload)
