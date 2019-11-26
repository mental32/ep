import asyncio
import os
import sys
import json
import time
import pathlib
import inspect
import importlib
from functools import partial
from typing import Union, Any, Optional

import discord
from discord import TextChannel
from discord.ext.commands import Paginator

# from episcript import EpiScriptRuntime

from .cog import Cog
from .base import ClientBase
from ..config import Config
from ..utils import codeblock, infer_token


class Client(ClientBase):
    r"""A hard client implementation used as default.

    Parameters
    ----------
    \*args : Any
        foo
    config : :class:`ep.Config`
        The config to use.
    disable : :class:`bool`
        disable the run method of the client instance, usefully for testing.
    \*\*kwargs : Any
        bar

    Attributes
    ----------
    _timestamp : :class:`int`
        The timestamp of when the client started
        or the timestamp of when the class was created.
    """

    _timestamp: int = int(time.time())

    def __init__(
        self, *args, config: Config, disable: bool = False, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)

        self.__socket_noloop = set()

        self._config = config
        if "cogpath" in self._config["ep"]:
            self.load_cogs(config.fp.parent.joinpath(self._config["ep"]["cogpath"]))

        if disable or "EP_DISABLED" in os.environ:
            self.run = lambda *_, **__: None
            return

        def cleanup():
            self.loop.run_until_complete(self.http.close())

        self.run = partial(self.run, infer_token(cleanup=cleanup))

        # self.runtime_exector = episcript.RuntimeExector()

    def __enter__(self):
        self._timestamp = int(time.time())
        return self

    def __exit__(self, *_, **__):
        self.logger.info(
            "Ran for %s seconds, Exiting...", int(time.time()) - self._timestamp
        )

    # Properties

    @property
    def config(self):
        return self._config

    @property
    def whitelist(self):
        """List[:class:`int`] - A list of whitelisted channel ids"""
        if "whitelist" in self.config["ep"]:
            return self.config["ep"]["whitelist"]
        return []

    # Internals

    def get_socket_channel(self) -> Optional[TextChannel]:
        try:
            channel_id = self._config["ep"]["socket_channel"]
        except KeyError:
            self.logger.warn("`socket_channel` option not present in configuration!")
            return None

        channel = self.get_channel(channel_id)

        if channel is None:
            self.logger.error("`socket_channel` could not be found! %s", repr(channel_id))
            return None

        return channel

    # Public

    def load_cogs(self, path: pathlib.Path) -> None:
        """Load cogs from a given :class:`pathlib.Path`.

        Parameters
        ----------
        path : :class:`pathlib.Path`
            The path to load the cogs from.
        """
        if not isinstance(path, pathlib.Path):
            raise TypeError()

        cogs = path.resolve().absolute()

        if not cogs.exists():
            raise FileNotFoundError("Ru'roh the cogs directory doesn't seem to exist!")

        disabled_cogs = self._config["ep"].get("disabled-cogs", [])

        try:
            sys.path.append(str(cogs))

            for path in cogs.iterdir():

                if path.resolve().is_file():
                    if not path.name.endswith(".py"):
                        continue
                    else:
                        name = path.name[:-3]
                else:
                    name = path.name

                if path.name not in disabled_cogs:
                    module = importlib.import_module(name)

                    for _, obj in inspect.getmembers(module):
                        if (
                            isinstance(obj, type)
                            and issubclass(obj, Cog)
                            and getattr(obj, "__export__", False)
                        ):
                            self.add_cog(obj(self))
        finally:
            sys.path.remove(str(cogs))

    async def process_message(self, message: discord.Message) -> None:
        """Given a :class:`discord.Message` attempt to invoke a command

        Parameters
        ----------
        message : :class:`discord.Message`
            The discord message to process.
        """
        _locals = _globals = None
        content = message.content

        async with self.runtime_exector.exec(content, _locals, _globals) as rv:
            pass

    # Event handlers

    async def on_message(self, message: discord.Message) -> None:
        if message.channel in self.whitelist:
            await self.process_message(message)

    async def on_ready(self) -> None:
        await super().on_ready()

        channel = self.get_socket_channel()

        if channel is None:
            return

        await channel.edit(topic="alive")

    async def on_socket_response(self, message: Union[Any, bytes]) -> None:
        if isinstance(message, bytes) or not self._config["ep"]["socket_emit"] or not self.is_ready():
            return

        await super().on_socket_response(message)

        channel = self.get_socket_channel()

        if channel is None:
            return

        await asyncio.sleep(1)

        if message['t'] == 'MESSAGE_CREATE' and int(message['d']['id']) in self.__socket_noloop:
            return self.__socket_noloop.remove(int(message['d']['id']))

        data = json.dumps(message)

        if len(data) >= 1900:
            return  # TODO: Impl paging objects

        try:
            resp = await channel.send(codeblock(data, style="json"))
        except Exception as err:
            self.logger.error(err)
            raise
        else:
            self.__socket_noloop.add(resp.id)
