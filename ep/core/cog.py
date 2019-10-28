import hashlib
import asyncio
import inspect
import functools
from typing import Type, Callable, Awaitable, Optional, Any

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
    def task(corofunc: Callable[..., Awaitable]) -> Callable[..., Awaitable]:
        """Mark coroutine function to be scheduled as a :class:`asyncio.Task`.

        Parameters
        ----------
        corofunc : Callable[..., Coroutine]
            The coroutine function to mark.
        """
        if not asyncio.iscoroutinefunction(corofunc):
            raise TypeError("target function must be a coroutine function.")

        corofunc.__schedule_task__ = True
        return corofunc

    @staticmethod
    def wait_for_envvar(envvar: str) -> Callable[[Callable[..., Any]], Callable]:
        """Produce a decorator that will block execution of a coroutine until an envvar is seen.

        Parameters
        ----------
        envvar : :class:`str`
            The envvar to look out for.
        """
        def decorator(corofunc: Callable[..., Any]) -> Callable[..., Any]:
            if not asyncio.iscoroutinefunction(corofunc):
                raise TypeError("target function must be a coroutine function.")

            @functools.wraps(corofunc)
            async def decorated(*args, **kwargs) -> Any:
                while True:
                    try:
                        value = os.environ[envvar]
                    except KeyError:
                        await asyncio.sleep(1)
                    else:
                        break

                args = (*args, value)
                return await corofunc(*args, **kwargs)
            return decorated
        return decorator

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
