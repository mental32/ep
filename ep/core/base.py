"""BaseClient implementation."""
from asyncio import (
    iscoroutinefunction,
    Future,
    Task,
    iscoroutine,
    CancelledError,
)
from collections import defaultdict
from typing import Coroutine, Optional
from types import MappingProxyType
from traceback import print_exc as traceback_print_exc
from random import choice
from string import ascii_lowercase

from discord import Client

from ..utils import get_logger as _utils_get_logger
from .cog import Cog


LOGGER = _utils_get_logger(__name__)


class ClientBase(Client):
    """A base client."""
    logger = LOGGER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra_events = defaultdict(list)
        self.__cogs = {}
        self.__extensions = {}
        self.__task_registry = {}

    # Properties

    @property
    def cogs(self):
        """Mapping[:class:`str`, :class:`Cog`]: A read-only mapping of cog name to cog."""
        return MappingProxyType(self.__cogs)

    @property
    def extensions(self):
        """Mapping[:class:`str`, :class:`py:types.ModuleType`]: A read-only mapping of extension name to extension."""
        return MappingProxyType(self.__extensions)

    # Internal

    def dispatch(self, event, *args, **kwargs):
        # Core dispatching
        super().dispatch(event, *args, **kwargs)

        # Extra event handling
        fmt = f"on_{event}"
        for event_ in self.extra_events.get(fmt, []):
            self._schedule_event(event_, fmt, *args, **kwargs)

    async def close(self):
        await super().close()

        for cog_name in list(self.cogs):
            self.remove_cog(cog_name)

    # Public

    def schedule_task(self, coro: Coroutine, *, name: Optional[str] = None) -> Task:
        """Schedule a coroutine to be wrapped in an :class:`asyncio.Task`."""
        if not iscoroutine(coro):
            raise TypeError("`coro` argument must be a coroutine.")

        if name is None:
            name = "".join(choice(ascii_lowercase) for _ in range(8))

        elif not isinstance(name, str):
            raise TypeError("`name` keyword argument must be None or a string.")

        async def handle(coro):
            try:
                return await coro
            except Exception as exc:  # pylint: disable=broad-except
                if isinstance(exc, CancelledError):
                    raise

                traceback_print_exc()

        task = self.loop.create_task(handle(coro))

        def task_registry_cleanup(_: Future) -> None:
            self.__task_registry.pop(name, None)

        task.add_done_callback(task_registry_cleanup)

        self.__task_registry[name] = task
        return task

    def add_listener(self, corofunc, name=None):
        """The non decorator alternative to :meth:`.listen`.

        Parameters
        -----------
        corofunc: Callable[..., Coroutine]
            The function to call.
        name: Optional[:class:`str`]
            The name of the event to listen for. Defaults to ``corofunc.__name__``.

        Example
        --------

        >>> async def on_ready():
        ...     pass
        >>> client.add_listener(on_ready)
        >>> async def some_event(message):
        ...     pass
        >>> client.add_listener(some_event, "on_message")
        """
        name = name or corofunc.__name__

        if not iscoroutinefunction(corofunc):
            raise TypeError("`corofunc` is not a coroutine function.")

        self.extra_events[name].append(corofunc)

    def remove_listener(self, func, name=None):
        """Removes a listener from the pool of listeners.

        Parameters
        -----------
        func
            The function that was used as a listener to remove.
        name: :class:`str`
            The name of the event we want to remove. Defaults to
            ``func.__name__``.
        """
        name = name or func.__name__
        self.extra_events.get(name, {}).pop(func, None)

    def add_cog(self, cog):
        """Adds a cog to the bot.

        A cog is a class that has its own event listeners and commands.

        Parameters
        -----------
        cog: :class:`ep.Cog`
            The cog to register to the bot.

        Raises
        -------
        TypeError
            The cog does not inherit from :class:`ep.Cog`.
        """
        if not isinstance(cog, Cog):
            raise TypeError("cogs must derive from Cog")

        self.logger.info("Adding cog: %s", repr(cog))

        cog = cog.cog_inject(self)
        self.__cogs[cog.__cog_name__] = cog

    def remove_cog(self, name):
        """Removes a cog from the bot.

        All registered commands and event listeners that the
        cog has registered will be removed as well.
        If no cog is found then this method has no effect.

        Parameters
        -----------
        name: :class:`str`
            The name of the cog to remove.
        """
        if name in self.__cogs:
            self.__cogs.pop(name).cog_eject(self)
