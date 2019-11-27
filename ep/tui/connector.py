from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop, Task, get_event_loop
from dataclasses import dataclass, field
from functools import partial
from json import loads as json_loads
from pickle import loads as pickle_loads
from traceback import format_exc
from typing import TYPE_CHECKING, Any, Optional

import websockets
from discord import Client, Message

if TYPE_CHECKING:
    import ep

__all__ = ("BaseConnector", "DiscordClientConnector", "WebsocketConnector")

@dataclass
class BaseConnector(ABC):
    """
    """
    window: "ep.tui.Window"
    config: "ep.Config"
    loop: AbstractEventLoop = field(default_factory=get_event_loop)

    __task: Optional[Task] = field(init=False, default=None)

    def start(self, **kwargs) -> None:
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


class DiscordClientConnector(BaseConnector):
    """
    """A :class:`discord.Client` based connector."""

    __client = None

    async def exhaust(self, token: str, config: "ep.Config"):
        superusers = config["ep"]["superusers"]

        channel_id: int = config["ep"]["socket_channel"]
        self.__client = client = Client()

        @client.event
        async def on_connect() -> None:
            self.update_widgets("Connected")

        @client.event
        async def on_ready() -> None:
            self.update_widgets("Ready")

        @client.event
        async def on_error(event, *args, **kwargs) -> None:
            self.update_widgets((event, format_exc()))

        @client.event
        async def on_message(message: Message) -> None:
            try:
                if message.channel.id == channel_id:
                    content = message.content[8:-3]
                    data = json_loads(content)
                    self.update_widgets(data)
            except Exception as err:
                self.update_widgets(repr(err))

        try:
            await client.start(token, bot=False)
        finally:
            await client.logout()
