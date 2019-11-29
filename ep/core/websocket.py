"""Websocket server implementation."""
from pickle import dumps as pickle_dumps
from contextlib import suppress
from functools import partial
from typing import Any

import websockets


class WebsocketServer:
    """A Websocket server."""
    host: str = "localhost"
    port: int = 9876

    def __init__(self, client):
        self._client = client
        self._coro = None
        self._sockets = set()

    @property
    def sockets(self):
        """Set[socket] - All of the currently connected sockets."""
        return self._sockets

    async def broadcast(self, data: Any) -> None:
        """Pickle and ``.send`` some ``data`` to all connected clients."""
        if not self.sockets:
            return

        try:
            payload = await self._client.loop.run_in_executor(None, partial(pickle_dumps, data, protocol=5))
        except Exception as err:  # pylint: disable=broad-except
            return self._client.logger.error("%s => %s", repr(data), err)

        for socket in self.sockets:
            await socket.send(payload)

    async def handler(self, socket, _):
        """Client handler."""
        self._client.logger.info("ws connect!")
        self._sockets.add(socket)

        try:
            async for message in socket:
                self._client.logger.info("ws: recv => %s", repr(message))
        finally:
            self._client.logger.info("ws disconnect!")
            self._sockets.remove(socket)

            with suppress(Exception):
                socket.close()

            del socket

    async def serve(self):
        """Attempt to serve the websocket server."""
        if self._coro is not None:
            raise RuntimeError

        self._coro = coro = websockets.serve(self.handler, self.host, self.port)
        await coro
