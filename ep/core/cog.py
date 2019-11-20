import asyncio
import functools
import inspect
import os
import hashlib
import traceback
from contextlib import suppress
from functools import partial
from inspect import iscoroutinefunction, getmembers, signature
from typing import Type, Callable, Awaitable, Optional, Any, Coroutine

__all__ = ("Cog",)

CoroutineFunction = Callable[..., Coroutine]

def _event(corofunc: CoroutineFunction, event_type: str = "", inject: Optional[Callable[[CoroutineFunction], CoroutineFunction]] = None) -> CoroutineFunction:
    if not event_type:
        event_type = corofunc.__name__

    if callable(inject):
        _corofunc = inject(corofunc)
    else:
        _corofunc = corofunc

    if _corofunc is not corofunc:
        _corofunc = functools.wraps(corofunc)(_corofunc)

    _corofunc.__event_listener__ = event_type

    return _corofunc


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

        self.__cog_listeners__ = [
            (getattr(obj, "__event_listener__"), name)
            for name, obj in getmembers(self)
            if hasattr(obj, "__event_listener__")
        ]

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

    @staticmethod
    def event(_corofunc: Optional[CoroutineFunction] = None, *, tp: str = "", **attrs: Any):
        """Mark a coroutine function as an event listener.

        >>> @Cog.event
        ... async def on_message(message: Message) -> None:
        ...     pass

        >>> @Cog.event(event="message")
        ... async def parse(self, source):
        ...     pass

        >>> @Cog.event(event="message", message_channel=0xDEADBEEF)
        ... async def on_special_message(message):
        ...     pass

        Parameters
        ----------
        _corofunc : Optional[:class:`CoroutineFunction`]
            When used directly as a decorator this is the function that is
            being marked.
        event : :class:`str`
            The type of event to listen out for.
        **attrs : Any
            Implemented for presence based rich predicates.
        """
        if _corofunc is not None:
            return _event(_corofunc, event_type=tp)

        if attrs:

            def decorate(corofunc: CoroutineFunction):
                sig = signature(corofunc)

                async def dyn(*args, **kwargs):
                    nonlocal sig, attrs

                    # Bind the signature over the current arguments
                    bound_sig = sig.bind(*args, **kwargs)

                    # Pre-invokation predicates
                    for target, expected in attrs.items():
                        head, *tail = target.split('_')

                        try:
                            base = bound_sig.arguments[head]
                        except KeyError:
                            raise NameError(f"name {head!r} is not defined.")

                        # Further resolve nested attributes
                        # foo_bar_baz -> foo.bar.baz
                        for part in tail:
                            base = getattr(base, part)

                        # Compare the resolved value with the excepted argument.
                        if base != expected:
                            # Failed to satisfy comparison, return eagerly.
                            return

                    return await corofunc(*args, **kwargs)
                return _event(corofunc, event_type=tp, inject=(lambda _: dyn))
            return decorate

        if event:
            return partial(_event, event_type=tp)

        return _event

    # Properties

    @property
    def cog_tasks(self):
        return []

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
