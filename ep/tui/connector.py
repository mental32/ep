from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop, Task
from dataclasses import dataclass, field
from functools import partial
from json import loads as json_loads
from pickle import loads as pickle_loads
from traceback import format_exc
from typing import TYPE_CHECKING, Optional

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
    loop: AbstractEventLoop

    _task: Optional[Task] = field(init=False, default=None)

    def start(self, **kwargs) -> None:
        if self._task is not None:
            self._task.cancel()

        self._task = self.loop.create_task(self.exhaust(**kwargs))

    def emit(self, data) -> None:
        for widget in self.window.widgets:
            widget.update(data)

    @abstractmethod
    async def exhaust(self):
        """
        """


class WebsocketConnector(BaseConnector):
    """
    """
    async def exhaust(self, uri: str):
        async with websockets.connect(uri) as websocket:
            async for message in websocket:
                data = await self.loop.run_in_executor(None, partial(pickle_loads, message))
                self.emit(data)


class DiscordClientConnector(BaseConnector):
    """
    """
    async def exhaust(self, token: str, config: "ep.Config"):

        superusers = config["ep"]["superusers"]

        channel_id: int = config["ep"]["socket_channel"]
        client = Client()

        @client.event
        async def on_connect() -> None:
            self.emit("Connected")

        @client.event
        async def on_ready() -> None:
            self.emit("Ready")

        @client.event
        async def on_error(event, *args, **kwargs) -> None:
            self.emit((event, format_exc()))

        @client.event
        async def on_message(message: Message) -> None:
            try:
                if message.channel.id == channel_id:
                    content = message.content[8:-3]
                    data = json_loads(content)
                    self.emit(data)
            except Exception as err:
                self.emit(repr(err))

        try:
            await client.start(token, bot=False)
        finally:
            await client.logout()
