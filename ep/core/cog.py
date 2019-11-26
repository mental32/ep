import asyncio
import ast
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
    def wait_until_ready(corofunc: Callable[..., Awaitable]) -> Callable[..., Awaitable]:
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

        if tp:
            return partial(_event, event_type=tp)

        return _event

    @staticmethod
    def regex(pattern: str, **attrs: Any):
        """Regex based message content parsing.

        Parameters
        ----------
        pattern : :class:`str`
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
        wrapped = self.event(tp="on_message", **attrs)

        def decorator(corofunc: CoroutineFunction):
            async def decoratorated(*args, **kwargs):
                bound = signature(corofunc).bind(*args, **kwargs)

                try:
                    content = bound["message"].content
                except KeyError:
                    for arg in bound.args:
                        if isinstance(arg, Message):
                            content = arg.content
                            break
                    else:
                        raise ValueError("could not infer message object for a regex match.")

                loop = asyncio.get_event_loop()
                match = loop.run_in_executor(None, partial(fullmatch, pattern, content))

                if match is None:
                    return  # XXX: Should we raise here?

                group_dict = match.groupdict()
                annotations = corofunc.__annotations__

                if group_dict and annotations:
                    group_kwargs = group_dict.copy()

                    for group_name, group_value in group_dict.items():
                        if group_name in annotations:
                            value_annotation = annotations[group_name]

                            # TODO: Unions, Tuples, ...

                            if value_annotation in (int, float, list, tuple, dict, set, frozenset):
                                try:
                                    value = ast.literal_eval(group_value)
                                except ValueError:
                                    value = group_value
                                    # value = eval(f"{value_annotation.__name__}({group_value})", {}, {})

                                group_kwargs[group_name] = value

                kwargs.update(group_kwargs)

                return await corofunc(*args, **kwargs)
            return wrapped(decorated)
        return decorator

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
