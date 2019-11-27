from .connector import *
from .window import Window, tty_raw
from . import widget

async def start(klass, *, config: "ep.Config", **klass_kwargs) -> None:
    with tty_raw(), Window(connector_klass=klass, config=config, connector_kwargs=klass_kwargs) as win:
        await win.run_forever()
