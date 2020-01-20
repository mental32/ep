"""Cog implementation."""
import ast
import asyncio
import functools
import hashlib
import inspect
import os
from asyncio import Task, iscoroutinefunction
from contextlib import suppress
from dataclasses import dataclass, field
from functools import partial, wraps
from inspect import iscoroutine, iscoroutinefunction, getmembers, signature
from itertools import cycle
from re import compile as re_compile, Pattern, Match
from string import Template
from sys import stderr
from typing import (
    Type,
    List,
    Callable,
    Awaitable,
    Optional,
    Any,
    Coroutine,
    Dict,
    Tuple,
    Union,
)

from discord import Message
from ep import ConfigValue

from ..event import Event, EventHandler
from ..regex import RegexHandler, FormattedRegexHandler, RegexPattern

__all__ = ("Cog",)

CoroutineFunction = Callable[..., Coroutine]


class Cog:
    """Base class for a GuildCog.

    Attributes
    ----------
    client : :class:`ep.core.BaseClient`
        The client instance the cog belongs too.
    config : :class:`ep.Config`
        The current configuration.
    loop : :class:`asyncio.AbstractEventLoop`
        The current event loop.

    Special attributes
    ------------------
    __cog_listeners__ : List[:class:`types.MethodTypes`]
        The currently regsitered listeners.
    __cog_name__ : :class:`str`
        The name of the cog.
    """

    group = Group

    def __init__(self, client: "BaseClient"):
        self.logger = client.logger
        self.config = config = client.config
        self.loop = client.loop

        self.client = client

        self.__cog_name__ = type(self).__name__
        self.__cog_destructors__ = []
        self.__cog_listeners__ = []
        self.__cog_tasks__ = []

        for name, obj in getmembers(self):
            if hasattr(obj, "__cog_unload_cb__"):
                self.__cog_destructors__.append(obj)

            elif hasattr(obj, "__event_listener__"):
                self.__cog_listeners__.append(
                    (getattr(obj, "__event_listener__"), name)
                )

            elif hasattr(obj, "__schedule_task__"):
                self.__cog_tasks__.append(obj)

            elif not isinstance(
                getattr(type(self), name, None), property
            ) and isinstance(obj, ConfigValue):
                setattr(self, name, obj.resolve(config))

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
        """Overloadable method that deals with processing after the standard ``__init__`` is called."""

    def __repr__(self):
        return f"<Cog name={type(self).__name__!r}>"

    ## Creation hooks

    def cog_inject(self, client):
        """An initializer that is called when the client is loading the cog."""
        disabled = self.config.get("disabled", False)

        for name, method_name in self.__cog_listeners__:
            client.add_listener(getattr(self, method_name), name)

        if not disabled:
            for func in self.__cog_tasks__:
                client.logger.info("Scheduling task: %s", repr(func))
                client.schedule_task(func())

        return self

    def cog_eject(self, client):
        """A destructor that is called when the client is unloading the cog."""
        try:
            for _, method_name in self.__cog_listeners__:
                client.remove_listener(getattr(self, method_name))
        finally:
            for cb in self.__cog_destructors__:
                with suppress(Exception):
                    cb()

    # Properties

    @property
    def cog_tasks(self) -> List[Task]:
        """List[:class:`asyncio.Task`] - The tasks associated with this cog."""
        return []

    # staticmethods

    # Markers

    @staticmethod
    def export(klass: Optional[Type["Cog"]]):
        """Mark a Cog class to be automatically exported when the module is loaded."""
        if not isinstance(klass, type) and issubclass(klass, Cog):
            raise TypeError("``klass`` must be a type that subclasses ``Cog``.")

        klass.__export__ = True
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
    def destructor(func: Callable) -> Callable:
        """Mark a function to be run as a cog destructor, when the cog is unloaded.

        Parameters
        ----------
        func : Callable
            The function the mark.
        """
        if iscoroutinefunction(func):
            raise TypeError("target functions must not be a coroutine function.")

        func.__cog_unload_cb__ = True
        return func

    # Decorators

    @staticmethod
    def wait_until_ready(
        corofunc: Callable[..., Awaitable]
    ) -> Callable[..., Awaitable]:
        """Block until the bot is ready.

        This is the same as sticking a ``await bot.wait_until_ready()`` at the
        head of the coroutine.

        Parameters
        ----------
        corofunc : Callable[..., Coroutine]
            The coroutine function to mark.
        """

        @functools.wraps(corofunc)
        async def decorated(self, *args, **kwargs):
            assert hasattr(self, "client")
            await self.client.wait_until_ready()
            return await corofunc(*(self, *args), **kwargs)

        return decorated

    @staticmethod
    def wait_for_envvar(
        envvar: str, delay: Union[int, float] = 1
    ) -> Callable[[Callable[..., Any]], Callable]:
        """Produce a decorator that will stall the invokation of a coroutine function until an envvar is seen.

        Parameters
        ----------
        envvar : :class:`str`
            The envvar to look out for.
        """

        def decorator(corofunc: Callable[..., Any]) -> Callable[..., Any]:
            if not asyncio.iscoroutinefunction(corofunc):
                raise TypeError("target function must be a coroutine function.")

            @wraps(corofunc)
            async def decorated(*args, **kwargs) -> Any:
                while True:
                    try:
                        value = os.environ[envvar]
                    except KeyError:
                        await asyncio.sleep(delay)
                    else:
                        kwargs[envvar] = value
                        break

                return await corofunc(*args, **kwargs)

            return decorated

        return decorator

    @staticmethod
    def event(
        _corofunc: Optional[CoroutineFunction] = None,
        *,
        tp: str = "",  # pylint: disable=invalid-name
        group: Optional[Group] = None,
        **attrs: Any,
    ) -> Union[Event, EventHandler]:
        """Mark a coroutine function as an event listener.

        >>> @Cog.event
        ... async def on_message(message: Message) -> None:
        ...     pass

        >>> @Cog.event(tp="message")
        ... async def parse(self, source):
        ...     pass

        >>> @Cog.event(tp="message", message_channel=0xDEADBEEF)
        ... async def on_special_message(message):
        ...     pass

        >>> marked = Cog.event(tp="on_message")
        >>> @marked
        ... async def some_event(self, message):
        ...     pass
        ...
        >>> @marked
        ... async def some_other_event(self, message):
        ...     pass
        ...

        Parameters
        ----------
        tp : :class:`str`
            The type of event to listen out for.
        group : :class:`ep.Group`
            The group this event is associated with, None otherwise.
        **attrs : Any
            Implemented for presence based rich predicates.
        """
        if not tp or _corofunc is None:
            raise ValueError("Must specify a ``tp`` argument or a coroutine function.")

        event = Event(tp, attrs=attrs, group=group)

        if _corofunc is not None:
            return event(_corofunc)

        return event

    @staticmethod
    def regex(
        pattern: RegexPattern,
        *,
        filter_: Union[bool, None, Callable[[Match], bool]] = None,
        **attrs: Any,
    ):
        """Regex based message content parsing.

        >>> @Cog.regex(r"!ping")
        ... async def pong(self, message: discord.Message) -> None:
        ...     await message.channel.send("Pong!")

        Is semantically equivelant to:

        >>> @Cog.event(tp="on_message")
        ... async def pong(self, message: discord.Message) -> None:
        ...     if re.fullmatch(r"!ping", message.content) is not None:
        ...         await ctx.message.send("Pong!")

        Parameters
        ----------
        pattern : :class:`RegexPattern`
            The regex pattern to match against
        **attrs : Any
            Further attrs to pass into :func:`event`

        Returns
        -------
        decorator : Callable[[CoroutineFunction], CoroutineFunction]
            The decorator that wraps a coroutine function into an event
            with regex parsing baked in.

        Raises
        ------
        ValueError
            This is raised if the message object could not be found.
        """
        assert "_corofunc" not in attrs

        kwargs = {
            "filter_": filter_,
            "pattern": re_compile(pattern)
            if not isinstance(pattern, Pattern)
            else pattern,
        }

        wrapped = Event("on_message", cls=RegexHandler, attrs=attrs)
        return partial(wrapped, **kwargs)


    @staticmethod
    def formatted_regex(
        formatter: Callable[["ep.Client"], Dict[str, Any]],
        pattern: RegexPattern,
        filter_: Union[bool, None, Callable[[Match], bool]] = None,
        **attrs,
    ) -> Callable:
        """Like :meth:`Cog.regex` but lazilly formats the pattern using the provided formatter.

        Conceptually its the same as :meth:`Cog.regex` but where it differs is
        the pattern used is ``pattern.format(**formatter(client))``

        Patterns
        --------
        formatter : Callable[[:class:`ep.Client`], Dict[str, Any]]
            The formatter to use.
        pattern : :class:`str`
            The pattern to format.
        attrs : Any
            Any subsequent attrs to filter against, see :meth:`Cog.event`
        """
        assert "_corofunc" not in attrs

        if not isinstance(pattern, str):
            raise TypeError("Bad pattern.")

        wrapped = Event("on_message", cls=FormattedRegexHandler, attrs=attrs)
        return partial(wrapped, filter_=filter_, pattern=pattern)
