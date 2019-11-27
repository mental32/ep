from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Union, List, Deque, Dict, TypeVar, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ep.tui import Window


K = TypeVar("K")
V = TypeVar("V")

__all__ = ("AbstractWidget", "Console")


def intersects(sub: Dict[str, Any], dom: [str, Any]) -> bool:
    """Recursively assert sub intersects dom."""
    if not isinstance(sub, dict):
        return sub == dom

    return all(
        (key in dom and intersects(value, dom[key])) for key, value in sub.items()
    )


@dataclass
class AbstractWidget(ABC):
    """
    """

    root: Union["Window", "AbstractWidget"]
    _dirty: bool = True

    @property
    def dirty(self) -> bool:
        return self._dirty

    @property
    def terminal(self):
        base = self.root

        while isinstance(base, AbstractWidget):
            base = base.root

        return base.terminal

    @abstractmethod
    def update(self, payload: Any, config: Dict) -> None:
        """
        """

    @abstractmethod
    def render(self) -> None:
        """
        """

    @abstractmethod
    def stdinp(self, key: bytes) -> None:
        """
        """


@dataclass
class Console(AbstractWidget):
    """A widget representing a view and an input."""

    msg_buf: Deque[str] = field(repr=False, init=False)
    inp_buf: Deque[str] = field(repr=False, init=False)

    formatters = {
        "MESSAGE_CREATE": (
            "({int(data_['channel_id'])!s} :: Channel)"
            ", ({data_['author']['username']}#{data_['author']['discriminator']} :: Author)"
            " => {data_['content']!r}"),
    }

    def __post_init__(self):
        self.inp_buf = deque(maxlen=512)
        self.msg_buf = deque(maxlen=512)

    def _eval_inp(self, source: str) -> None:
        pass

    def stdinp(self, char):
        if char in (b"\r", b"\n"):
            self._eval_inp("".join(self.inp_buf))
            self.inp_buf.clear()
        elif char in (b"\x7f", b"\b") and self.inp_buf:
            self.inp_buf.pop()
        else:
            self.inp_buf.append(char.decode())

        self._dirty = True

    def update(self, payload: Any, config: Dict) -> None:
        data: Optional[str] = None

        if (
            isinstance(payload, dict)
            and set(payload) == {"d", "t", "s", "op"}
            and payload["op"] == 0
        ):
            data_, type_ = payload["d"], payload["t"]

            filters = config.get("filters", {})
            filters_t = filters.get(type_, {})

            exclude = filters_t.get("exclude", [])
            include = filters_t.get("include", [])

            intersection_of = intersects

            if type_ in self.formatters and all(
                intersection_of(form, data_) is as_expected
                for as_expected, group in ((False, exclude), (True, include))
                for form in group
            ):
                data = eval(f"f{self.formatters[type_]!r}", {}, {"data_": data_, "self": self})

        elif isinstance(payload, str):
            data = payload

        if data is not None:
            if isinstance(data, list):
                self.msg_buf.extend(data)
            else:
                self.msg_buf.append(data)

            self._dirty = True

    def render(self) -> None:
        term = self.terminal
        width = term.width
        height = term.height

        clobber = " " * (width - 2)
        edge = (lambda rhs: min((width - 2, rhs)))

        for index, part in enumerate(reversed(self.msg_buf)):
            if index >= (height - 4):
                break

            with term.location(1, height - (index + 4)):
                if not isinstance(part, str):
                    part = repr(part)

                limit = edge(len(part))
                print("".join(part[: limit]) + clobber[limit:], end="", flush=True)

        with term.location(0, term.height - 3):
            print("╠" + ("═" * (term.width - 2)) + "╣", end="", flush=True)

        with term.location(1, term.height - 2):
            print(clobber)

            with term.location(1, term.height - 2):
                limit = edge(len(self.inp_buf))
                print("".join(self.inp_buf)[: limit], end="", flush=True)

        self._dirty = True
