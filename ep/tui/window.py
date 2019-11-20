import asyncio
import sys
import pickle
import termios
import tty
import traceback
from functools import partial
from contextlib import suppress, contextmanager
from typing import List

import aioconsole
from blessings import Terminal


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
    watermark: float = 0.2

    def __init__(self, socket: "Websocket") -> None:
        self.loop = loop = asyncio.get_event_loop()

        self._socket = socket
        self._socket_task = loop.create_task(self.socket_read())

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

    @property
    def socket(self):
        return self._socket

    # Public api

    async def socket_read(self):
        async for message in self.socket:
            data = await self.loop.run_in_executor(None, partial(pickle.loads, message))

            for widget in self.widgets:
                with suppress(Exception):
                    widget.update(data)

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

        terminal = self.terminal
        refresh_counter = self.watermark

        if not self._widgets:
            self._widgets.append(Console(root=self))

        stdin, _ = await aioconsole.get_standard_streams()

        while True:
            try:
                char = await asyncio.wait_for(stdin.read(1), timeout=0.1)
            except asyncio.TimeoutError:
                char = None
            else:
                for widget in self.widgets:
                    with suppress(Exception):
                        widget.stdinp(char)

            if refresh_counter >= self.watermark:
                refresh_counter = 0

                print(terminal.clear)

                self.render_frame()

                for widget in self.widgets:
                    with suppress(Exception):
                        widget.render()

            await asyncio.sleep(self.refresh_delay)
            refresh_counter += self.refresh_delay
