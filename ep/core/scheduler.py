import asyncio
import random
import string
import logging
import traceback
from functools import partial
from asyncio import Task, AbstractEventLoop
from typing import Coroutine, Union, Optional


class TaskScheduler:
    def __init__(self, loop: AbstractEventLoop) -> None:
        self.__loop = loop
        self.__task_registry = {}

    def schedule_task(
        self, coro: Coroutine, *, name: Optional[str] = None
    ) -> asyncio.Task:
        if not asyncio.iscoroutine(coro):
            raise TypeError("`coro` argument must be a coroutine.")

        if name is None:
            name = "".join(random.choice(string.ascii_lowercase) for _ in range(8))

        elif not isinstance(name, str):
            raise TypeError("`name` keyword argument must be None or a string.")

        async def handle(coro):
            try:
                return await coro
            except asyncio.CancelledError:
                raise
            except Exception:
                traceback.print_exc()

        task = self.__loop.create_task(handle(coro))

        def _task_registry_cleanup(_) -> None:
            self.__task_registry.pop(name, None)

        task.add_done_callback(_task_registry_cleanup)

        self.__task_registry[name] = task
        return task
