import asyncio

from .window import Window, tty_raw


async def _start(*, address: str = None, port: int = None) -> None:
    # connector = await WebsocketClient.connect(address=address, port=port)
    connector = None

    with tty_raw(), Window(connector=connector) as win:
        await win.run_forever()


def start(*args, **kwargs) -> None:
    return asyncio.run(_start(*args, **kwargs))
