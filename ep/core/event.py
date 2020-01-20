from asyncio import iscoroutinefunction
from functools import reduce, partial
from inspect import signature, Signature


class Event:
    __slots__ = ("event_type", "attrs", "group", "klass")

    def __init__(
        self,
        event_type: str,
        *,
        group: Group,
        cls: EventHandler = EventHandler,
        attrs: Dict[str, Any],
    ):
        self.klass = cls
        self.event_type = event_type
        self.group = group
        self.raw_attrs = attrs

        self.attrs = {}
        for target, expected in attrs.items():
            encoded = target.encode("ascii")

            # Support underscore separated names by replacing the underscore
            # With an illegal character for names (here we use a null terminator)
            # Then split and collect while reverting terminators into underscores.
            parts = tuple(
                [
                    part.replace(b"\x00", b"_").decode("ascii")
                    for part in encoded.replace(b"__", b"\x00").split(b"_")
                ]
            )

            self.attrs[parts] = expected

    def __call__(self, callback: CoroutineFunction, *args, **kwargs) -> EventHandler:
        return self.klass(self, callback, *args, **kwargs)

    def __hash__(self) -> int:
        return hash((self.event_type, self.group))

    def __repr__(self) -> str:
        return f"<Event: {self.event_type=!r}, {self.group=!r}>"


class EventHandler:
    __slots__ = ("callback",)

    def __init__(
        self,
        event: Event,
        callback: CoroutineFunction,
        signature: Optional[Signature] = None,
    ):
        self.event = event

        if isinstance(callback, partial):
            if not iscoroutinefunction(callback.func):
                raise TypeError(
                    "function of partial object must be a coroutine function."
                )

            func = callback.func

        elif not iscoroutinefunction(callback):
            raise TypeError("``callback`` must be a coroutine function.")

        else:
            func = callback

        self.callback = callback

        if signature is not None:
            if not isinstance(signature, Signature):
                raise TypeError(
                    "``signature`` keyword argument must be an instance of ``inspect.Signature``"
                )

            self.signature = signature
            return

        self.signature = signature(func)

    def __repr__(self) -> str:
        return repr(self.callback)

    async def __call__(self, *args, **kwargs) -> Any:
        if not self.event.attrs:
            return await self.callback(*args, **kwargs)

        can_run = await self.should_run(args, kwargs)

        if can_run:
            try:
                return await self.callback(*args, **kwargs)
            except Exception as exc:
                if (group := self.event.group) is not None:
                    await group.raise_exception(exc, self, bound)

                raise

    async def should_run(self, args, kwargs) -> bool:
        # Bind the signature over the current arguments
        bound = self.signature.bind(*args, **kwargs)

        assert "self" in bound.arguments, "no 'self' in callback"

        # Pre-invokation predicates
        for parts, expected in self.event.attrs.items():
            if isinstance(expected, ConfigValue):
                expected = expected.resolve(bound.arguments["self"].config)

            head, *tail = parts

            try:
                base = bound.arguments[head]
            except KeyError:
                raise NameError(f"name {head!r} is not defined.")

            # Further resolve nested attributes
            # ``foo_bar_baz=obj` becomes ``assert foo.bar.baz == obj``
            try:
                base = reduce(partial(getattr, base), tail)
            except AttributeError:
                return False

            # Compare the resolved value with the excepted argument.
            if base != expected:
                # Failed to satisfy comparison, return eagerly.
                return False

        return True
