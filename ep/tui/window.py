import asyncio
import sys
import pickle
import termios
import tty
import traceback
from functools import partial
from contextlib import suppress, contextmanager
from typing import Dict, Any, List

import aioconsole
from blessings import Terminal

from .connector import BaseConnector

__all__ = ("tty_raw", "Window")

@contextmanager
def tty_raw():
    before = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin)
    try:
        yield
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, before)


class Window:
    """Root interface window."""

    refresh_delay: float = 0.1
    refresh_watermark: float = 0.2

    def __init__(self, connector_klass: BaseConnector, connector_kwargs: Dict[Any, Any]) -> None:
        self.loop = loop = asyncio.get_event_loop()
        self._connector = connector_klass(self, loop)
        self._connector_kwargs = connector_kwargs
        self._terminal = Terminal()
        self._widgets: List["Widget"] = []

    def __enter__(self):
        self.terminal.stream.write(self.terminal.enter_fullscreen)
        return self

    def __exit__(self, *_, **__):
        self.terminal.stream.write(self.terminal.exit_fullscreen)

    # Properties

    @property
    def terminal(self):
        return self._terminal

    @property
    def widgets(self):
        return iter(self._widgets)

    # Public api

    def render_frame(self) -> None:
        term = self.terminal

        parts = (
            ("╔", 0, 0),
            ("╗", term.width - 1, 0),
            ("╚", 0, term.height - 1),
            ("╝", term.width - 1, term.height - 1),
        )

        for char, x_pos, y_pos in parts:
            with term.location(x_pos, y_pos):
                print(char, end="", flush=True)

        for y_pos in (0, term.height - 1):
            with term.location(1, y_pos):
                print("═" * (term.width - 2), end="", flush=True)

        for x_pos in (0, term.width - 1):
            for y_pos in range(1, term.height - 1):
                with term.location(x_pos, y_pos):
                    print("║", end="", flush=True)

    async def run_forever(self):
        from .widget import Console

        self._connector.start(**self._connector_kwargs)

        if not self._widgets:
            self._widgets.append(Console(root=self))

        terminal = self.terminal
        refresh_debt = self.refresh_watermark

        stdin, _ = await aioconsole.get_standard_streams()

        while True:
            t1 = self.loop.time()

            if refresh_debt >= self.refresh_watermark:
                refresh_debt = 0.0

                if any(widget.dirty for widget in self.widgets):
                    print(terminal.clear)

                    self.render_frame()

                    with terminal.location(terminal.width - 11, terminal.height - 2):
                        print(repr(self.loop.time() - t1)[:10], end="", flush=True)

                    for widget in self.widgets:
                        if widget.dirty:
                            widget.render()

            try:
                char = await asyncio.wait_for(stdin.read(1), timeout=self.refresh_delay)
            except asyncio.TimeoutError:
                char = None
            else:
                for widget in self.widgets:
                    with suppress(Exception):
                        widget.stdinp(char)

            refresh_debt += self.refresh_delay
