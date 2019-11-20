from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Union, List, Deque

from . import Window


@dataclass
class Widget(ABC):
    """
    """
    root: Union[Window, "Widget"]

    @property
    def terminal(self):
        base = self.root

        while isinstance(base, Widget):
            base = base.root

        return base.terminal

    @abstractmethod
    def update(self, payload: Any) -> None:
        """
        """

    @abstractmethod
    async def render(self) -> None:
        """
        """

    @abstractmethod
    async def stdinp(self, key: bytes) -> None:
        """
        """


@dataclass
class Console(Widget):
    """
    """

    msg_buf: Deque[Any] = field(repr=False, init=False)
    inp_buf: str = field(repr=False, init=False)

    def __post_init__(self):
        self.inp_buf = ""
        self.msg_buf = deque()

    def stdinp(self, char):
        if char != b'\n':
            self.inp_buf += char.decode()
        else:
            self.inp_buf = ""

    def update(self, payload: Any) -> None:
        self.msg_buf.append(payload)

        term = self.terminal

        while len(self.msg_buf) > (term.height - 5):
            self.msg_buf.popleft()

    def render(self) -> None:
        term = self.terminal
        width = term.width

        for index, part in enumerate(self.msg_buf):
            with term.location(1, index + 1):
                fmt = repr(part)[:width - 3]
                print(fmt, end='', flush=True)

        with term.location(1, term.height - 2):
            print(self.inp_buf[:width], end="", flush=True)
