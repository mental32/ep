from typing import Coroutine

import websockets


class WebsocketServer:
    host: str = "localhost"
    port: int = 9876

    def __init__(self, client):
        self._client = client
        self._coro = None

    async def handler(self, socket, _):
        await socket.close()

    def serve(self) -> Coroutine:
        if self._coro is not None:
            raise RuntimeError

        self._coro = coro = websockets.serve(self.handler, self.host, self.port)
        return coro
