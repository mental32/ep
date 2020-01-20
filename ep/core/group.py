from dataclasses import dataclass, field


@dataclass
class Group:
    """A semantically bound grouping of various events."""

    __exc_handlers: List[Callable[[BaseException], Any]] = field(
        init=False, default_factory=list
    )

    def add_exception_handler(self, handler: Callable[[BaseException], Any]):
        """Adds `handler` to the list of exception handlers."""
        self.__exc_handlers.append(handler)

    def del_exception_handler(self, handler: Callable[[BaseException], Any]):
        self.__exc_handlers.remove(handler)

    async def raise_exception(self, exc: BaseException, corofunc, args):
        """Trigger the exception handlers with ``exc``."""
        for handler in self.__exc_handlers:
            with suppress(Exception):
                if iscoroutine((coro := handler(exc, corofunc, args))):
                    await coro
