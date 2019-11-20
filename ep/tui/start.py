import asyncio
import pickle
from functools import partial
from sys import stderr

import websockets

from .window import Window, tty_raw


async def start(*, address: str = None, port: int = None) -> None:
    # loop = asyncio.get_event_loop()

    # while True:
    #     try:
    #         print("Connecting...", file=stderr)
    #         async with websockets.connect(f'ws://{address}:{port}') as ws:
    #             print("Connected!", file=stderr)
    #             while True:
    #                 data = await loop.run_in_executor(None, partial(pickle.loads, await ws.recv()))
    #                 print("DEBUG: ", repr(data))
    #     except OSError:
    #         timeout = 60
    #     except websockets.ConnectionClosed:
    #         timeout = 10

    #     print(f"Connection closed, retrying in {timeout} seconds", file=stderr)
    #     await asyncio.sleep(timeout)

    uri = f"ws://{address}:{port}"
    async with websockets.connect(uri) as ws:
        with tty_raw(), Window(socket=ws) as win:
            await win.run_forever()
