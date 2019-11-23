from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop, Task
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
    loop: AbstractEventLoop

    _task: Optional[Task] = field(init=False, default=None)

    def start(self, **kwargs) -> None:
        if self._task is not None:
            self._task.cancel()

        self._task = self.loop.create_task(self.exhaust(**kwargs))

    def update_widgets(self, data) -> None:
        for widget in self.window.widgets:
            widget.update(data)

    @abstractmethod
    async def send(self, data: Any) -> None:
        """
        """

    @abstractmethod
    async def exhaust(self):
        """
        """


class WebsocketConnector(BaseConnector):
    """
    """

    __socket = None

    async def send(self, data: bytes) -> None:
        assert isinstance(data, bytes)
        await self.__socket.send(data)

    async def exhaust(self, uri: str, config: "ep.Config"):
        async with websockets.connect(uri) as websocket:
            self.__socket = websocket

            async for message in websocket:
                data = await self.loop.run_in_executor(None, partial(pickle_loads, message))
                self.update_widgets(data)


class DiscordClientConnector(BaseConnector):
    """
    """

    __client = None

    async def send(self, data: bytes) -> None:
        pass

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
