import asyncio

import websockets


class WebsocketClient:
    def __init__(self, channel: asyncio.Queue, websocket) -> None:
        self.channel = channel
        self.socket = websocket

    @classmethod
    async def connect(cls, channel: asyncio.Queue, uri: str) -> "WebsocketClient":
        socket = await websockets.connect(uri)
        return cls(channel, socket)
