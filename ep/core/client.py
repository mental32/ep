import os
import sys
import time
import pathlib
import inspect
import importlib
from functools import partial

from episcript import EpiScriptRuntime

from .. import utils
from .base import ClientBase


class Client(ClientBase):
    """A hard client implementation used as default.
    
    Attributes
    ----------
    _timestamp : :class:`int`
        The timestamp of when the client started
        or the timestamp of when the class was created.
    """

    _timestamp: int = int(time.time())

    def __init__(
        self, *args, config: pathlib.Path, disable: bool = False, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)

        self._config = utils.read_cfg(config)

        if disable or "EP_DISABLED" in os.environ:
            self.run = lambda *_, **__: None
        else:
            try:
                self.run = partial(self.run, os.environ["DISCORD_TOKEN"])
            except KeyError:
                # Tidy up lose connections.
                self.loop.run_until_complete(self.http.close())
                raise RuntimeError("Could not find `DISCORD_TOKEN` in the environment!")

        if "cogpath" in self._config["ep"]:
            self._load_cogs(pathlib.Path(self._config["ep"]["cogpath"]))

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
                        if isinstance(obj, type) and getattr(obj, "__export__", False):
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
        locals_ = globals_ = {}  # TODO: namespace serialization/resolution

        runtime = EpiScriptRuntime(locals_, globals_)
        code = await runtime.compile(message.content)
        await runtime.exec(code)

    # Event handlers

    async def on_message(self, message: discord.Message) -> None:
        if message.channel in self.whitelist:
            await self.process_message(message)
