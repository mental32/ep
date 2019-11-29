"""Cog implementation"""
import asyncio
import ast
import functools
import inspect
import os
import hashlib
from sys import stderr
from asyncio import Task, iscoroutinefunction
from dataclasses import dataclass, field
from functools import partial, wraps
from re import compile as re_compile, Pattern, Match
from itertools import cycle
from string import Template
from inspect import iscoroutinefunction, getmembers, signature
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

__all__ = ("Cog",)

CoroutineFunction = Callable[..., Coroutine]
RegexPattern = Union[str, Pattern]


LITERAL_TYPES = (
    int,
    float,
    list,
    tuple,
    dict,
    set,
    frozenset,
)


def _event(
    corofunc: CoroutineFunction,
    event_type: str = "",
    inject: Optional[Callable[[CoroutineFunction], CoroutineFunction]] = None,
) -> CoroutineFunction:
    if not iscoroutinefunction(corofunc) or (
        isinstance(corofunc, partial) and not iscoroutinefunction(corofunc.func)
    ):
        raise TypeError("`corofunc` must be a coroutine function.")

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


# fmt: off
async def _decorated_regex(
    pattern: Pattern,
    corofunc: Callable,
    filter_: Union[Callable[[Match], bool], bool, None] = (lambda match: match is None),
    *,
    args,
    kwargs,
) -> Any:
    # Named groups in a pattern have the potential to be arguments in the signiture
    kwargs.update(dict(zip(pattern.groupindex, cycle([None]))))

    bound = signature(corofunc).bind(*args, **kwargs)

    try:
        content = bound.arguments["message"].content
    except KeyError:
        if not any(isinstance(arg, Message) and (content := arg.content) for arg in bound.args):
            raise ValueError("could not infer message object (needed for a regex match.)")

    filter_ = {
        None: (lambda match: match is None),
        True: (lambda _: True),
        False: (lambda _: False),
    }.get(filter_, filter_)

    loop = asyncio.get_event_loop()
    match = await loop.run_in_executor(None, partial(pattern.fullmatch, content))
    del loop

    if filter_(match):
        return  # TODO: Should we raise here?

    if match is not None:
        group_dict = match.groupdict()
        annotations = corofunc.__annotations__

        kwargs_ = {}

        if group_dict and annotations:
            kwargs_.update(group_dict.copy())

            for name in {*group_dict}.intersection({*annotations}):
                argument_annotation = annotations[name]
                argument = group_dict[name]

                # TODO: Unions, Tuples, ...

                if argument_annotation in LITERAL_TYPES:
                    try:
                        value = ast.literal_eval(argument)
                    except ValueError:
                        value = argument

                    kwargs_[name] = value

        kwargs.update(kwargs_)

    return await corofunc(*args, **kwargs)
# fmt: on


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
        """Overloadable method that deals with processing after the standard ``__init__`` is called."""

    def __repr__(self):
        return f"<Cog name={type(self).__name__!r}>"

    # Special methods

    def cog_unload(self):
        """A method that is called when a cog is unloaded."""

    ## Creation hooks

    def cog_inject(self, client):
        """An initializer that is called when the client is loading the cog."""
        disabled = self.config.get("disabled", False)

        for name, method_name in self.__cog_listeners__:
            client.add_listener(getattr(self, method_name), name)

        for _, obj in inspect.getmembers(self):
            if not disabled and getattr(obj, "__schedule_task__", False):
                client.logger.info("Scheduling task: %s", repr(obj))
                client.schedule_task(obj())

        return self

    def cog_eject(self, client):
        """A destructor that is called when the client is unloading the cog."""
        try:
            for _, method_name in self.__cog_listeners__:
                client.remove_listener(getattr(self, method_name))
        finally:
            self.cog_unload()

    # Properties

    @property
    def cog_tasks(self) -> List[Task]:
        """List[:class:`asyncio.Task`] - The tasks associated with this cog."""
        return []

    # staticmethods

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
        _corofunc: Optional[CoroutineFunction] = None, *, tp: str = "", **attrs: Any
    ):  # pylint: disable=invalid-name
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
        _corofunc : Optional[:class:`CoroutineFunction`]
            When used directly as a decorator this is the function that is
            being marked.
        tp : :class:`str`
            The type of event to listen out for.
        **attrs : Any
            Implemented for presence based rich predicates.
        """
        if _corofunc is not None:
            return _event(_corofunc, event_type=tp)

        if attrs:

            def decorate(corofunc: CoroutineFunction):
                if isinstance(corofunc, partial):
                    signature_ = signature(corofunc.func)
                else:
                    signature_ = signature(corofunc)

                @wraps(corofunc)
                async def decorated(*args, **kwargs):
                    nonlocal signature_, attrs

                    # Bind the signature over the current arguments
                    bound_sig = signature_.bind(*args, **kwargs)

                    # Pre-invokation predicates
                    for target, expected in attrs.items():
                        head, *tail = target.split("_")

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

                return _event(corofunc, event_type=tp, inject=(lambda _: decorated))

            return decorate

        if tp:
            return partial(_event, event_type=tp)

        raise ValueError(
            "Must supply at least one of: ``tp``, ``attrs``, or a coroutine function."
        )

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
        wrapped = Cog.event(tp="on_message", **attrs)
        kwargs_ = {
            "filter_": filter_,
            "pattern": re_compile(pattern)
            if not isinstance(pattern, Pattern)
            else pattern
        }

        def decorator(corofunc: CoroutineFunction):
            kwargs_["corofunc"] = corofunc

            async def decorated(*args, **kwargs):
                kwargs_["args"] = args
                kwargs_["kwargs"] = kwargs
                return await _decorated_regex(**kwargs_)

            return wrapped(decorated)

        return decorator

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
        wrapped = Cog.event(tp="on_message", **attrs)

        if not isinstance(pattern, str):
            raise TypeError("Bad pattern.")

        kwargs_ = {"filter_": filter_}

        def decorator(corofunc: CoroutineFunction):
            kwargs_["corofunc"] = corofunc

            @wraps(corofunc)
            async def decorated(*args, **kwargs):
                bound = signature(corofunc).bind(*args, **kwargs)
                assert "self" in bound.arguments

                template = Template(pattern)
                fmt = template.substitute(formatter(bound.arguments["self"].client))
                compiled_pattern = re_compile(fmt)

                kwargs_.update(
                    {"pattern": compiled_pattern, "args": args, "kwargs": kwargs}
                )

                return await _decorated_regex(**kwargs_)

            return wrapped(decorated)

        return decorator
