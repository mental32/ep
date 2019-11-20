import asyncio
import pickle
from contextlib import suppress
from functools import partial
from typing import Any, Coroutine

import websockets


class WebsocketServer:
    host: str = "localhost"
    port: int = 9876

    def __init__(self, client):
        self._client = client
        self._coro = None
        self._sockets = set()

    @property
    def sockets(self):
        return self._sockets

    async def broadcast(self, data: Any) -> None:
        if not self.sockets:
            return

        try:
            payload = await self._client.loop.run_in_executor(None, partial(pickle.dumps, data, protocol=5))
        except Exception as err:
            return self._client.logger.error("%s => %s", repr(data), err)

        for socket in self.sockets:
            await socket.send(payload)

    async def handler(self, socket, _):
        self._client.logger.info("WSS CONNECT: %s", repr(socket))
        self._sockets.add(socket)

        try:
            async for message in socket:
                self._client.logger.info("WSS: %s => %s", repr(message), repr(socket))
        finally:
            self._client.logger.info("WSS DISCONNECT: %s", repr(socket))
            self._sockets.remove(socket)

            with suppress(Exception):
                socket.close()

            del socket

    async def serve(self):
        if self._coro is not None:
            raise RuntimeError

        self._coro = coro = websockets.serve(self.handler, self.host, self.port)
        await coro
