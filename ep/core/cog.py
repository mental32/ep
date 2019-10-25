import hashlib
import asyncio
import inspect
from typing import Type, Callable, Awaitable

from ..utils import get_logger as _utils_get_logger

__all__ = ("Cog",)


class Cog:
    """Base class for a GuildCog.

    Attributes
    ----------
    client : :class:`BaseClient`
        The bot instance the cog belongs too.
    """

    def __init__(self, client: "BaseClient"):
        self.logger = client.logger
        self.config = client.config
        self.loop = client.loop

        self.client = client

        self.__cog_listeners__ = []
        self.__cog_name__ = type(self).__name__

        self.cog_hash = (
            hashlib.md5(
                self.__module__.encode("ascii")
                + self.__class__.__name__.encode("ascii")
            )
            .digest()
            .hex()
        )

        self.__post_init__()

    def __post_init__(self):
        pass

    def __repr__(self):
        return f"<Cog name={type(self).__name__!r}>"

    # staticmethods

    @staticmethod
    def export(klass: Optional[Type["Cog"]] = None, **flags):
        if klass is None:

            def decorator(klass: Type["Cog"]):
                klass.__export__ = True
                klass.__export_flags__ = flags

            return decorator

        if not isinstance(klass, type) and issubclass(klass, Cog):
            raise TypeError()

        klass.__export__ = True
        klass.__export_flags__ = ()
        return klass

    @staticmethod
    def task(func: Callable[..., Awaitable]) -> Callable[..., Awaitable]:
        if not asyncio.iscoroutinefunction(func):
            raise TypeError()

        func.__schedule_task__ = True
        return func

    # Special methods

    def cog_unload(self):
        pass

    # Creation hooks

    def cog_inject(self, client):
        for name, method_name in self.__cog_listeners__:
            client.add_listener(getattr(self, method_name), name)

        for _, obj in inspect.getmembers(self):
            if getattr(obj, "__schedule_task__", False):
                client.logger.info("Scheduling task: %s", repr(obj))
                client.schedule_task(obj())

        return self

    def cog_eject(self, client):
        try:
            for _, method_name in self.__cog_listeners__:
                client.remove_listener(getattr(self, method_name))
        finally:
            self.cog_unload()

    # Properties

    @property
    def cog_guild(self):
        return self.client.get_guild(self.__cog_guild__)

    @property
    def cog_tasks(self):
        pass
