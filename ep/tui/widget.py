from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Union, List, Deque

from . import Window

__all__ = ("Widget", "Console")


@dataclass
class Widget(ABC):
    """
    """
    root: Union[Window, "Widget"]
    _dirty: bool = True

    @property
    def dirty(self) -> bool:
        return self._dirty

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

    msg_buf: Deque[str] = field(repr=False, init=False)
    inp_buf: Deque[str] = field(repr=False, init=False)

    def __post_init__(self):
        self.inp_buf = deque(maxlen=512)
        self.msg_buf = deque(maxlen=512)

    def _eval_inp(self, source: str) -> None:
        pass

    def stdinp(self, char):
        if char in (b'\r', b'\n'):
            self._eval_inp("".join(self.inp_buf))
            self.inp_buf.clear()
        elif char in (b'\x7f', b'\b') and self.inp_buf:
            self.inp_buf.pop()
        else:
            self.inp_buf.append(char.decode())

        self._dirty = True

    def update(self, payload: Any) -> None:
        data: Optional[str] = None

        if isinstance(payload, dict) and set(payload) == {"d", "t", "s", "op"} and payload["op"] == 0:
            d, t = payload["d"], payload["t"]

            if t == "MESSAGE_CREATE":
                data = f"{d['channel_id']!r} >> {d['author']['username']}#{d['author']['discriminator']} >> {d['content']!r}"

        elif isinstance(payload, str):
            data = payload

        if data is not None:
            self.msg_buf.append(data)
            self._dirty = True

    def render(self) -> None:
        term = self.terminal
        width = term.width
        height = term.height

        for index, part in enumerate(reversed(self.msg_buf)):
            if index >= (height - 4):
                break

            with term.location(1, height - (index + 4)):
                if not isinstance(part, str):
                    part = repr(part)

                fmt = part[:width - 3]
                print(fmt, end='', flush=True)

        with term.location(0, term.height - 3):
            print('╠' + ('═' * (term.width - 2)) + '╣', end="", flush=True)

        with term.location(1, term.height - 2):
            print("".join(self.inp_buf)[:width], end="", flush=True)

        self._dirty = True
