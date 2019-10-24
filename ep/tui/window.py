import asyncio
import sys
import termios
import tty
from contextlib import contextmanager

import aioconsole
from blessings import Terminal

from .websocket import WebsocketClient


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

    refresh_delay: float = 0.25

    def __init__(self, connector: WebsocketClient) -> None:
        self._connector = connector
        self._widgets = []
        self._terminal = Terminal()

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
        terminal = self.terminal

        stdin, _ = await aioconsole.get_standard_streams()

        refresh_counter = 1

        while True:
            try:
                char = await asyncio.wait_for(stdin.read(1), timeout=0.1)
            except asyncio.TimeoutError:
                char = None

            if refresh_counter >= 1:
                refresh_counter = 0

                print(terminal.clear)

                self.render_frame()

                for widget in self.widgets:
                    widget.render()

            await asyncio.sleep(self.refresh_delay)
            refresh_counter += self.refresh_delay
