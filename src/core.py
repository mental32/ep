import os
import pathlib
import traceback
from functools import partial
from typing import List, Tuple

import discord
from discord.ext import commands

from . import utils
from .utils import (
    PRIORITISED_EXTENSIONS,
    GUILD_SNOWFLAKE as _GUILD_SNOWFLAKE,
    LIB_EXTS as _LIB_EXTS,
)

logger = utils.get_logger(__name__)


class Bot(commands.Bot):
    _guild: discord.Guild = None
    _cog_counter: int = 0

    def __init__(self, *args, **kwargs):
        kwargs['command_prefix'] = ('py_', 'py?', 'ep.', '?')

        super().__init__(*args, **kwargs)

        try:
            self.run = partial(self.run, os.environ['DISCORD_TOKEN'])
        except KeyError:
            self.loop.run_until_complete(
                self.http.close()
            )  # Close the underlying http session.
            raise RuntimeError('Could not find `DISCORD_TOKEN` in the environment!')

        self._guild_command_channels = []
        self.reloaded_cogs = set()
        self.datastore = None
        self.load_extension('jishaku')

        failed = succeeded = 0

        for name in self._peek_extensions():
            try:
                self.load_extension(f'src.cogs.{name}')
            except commands.ExtensionFailed as error:
                logger.critical(error)
                self.dispatch('error', error)
                failed += 1
            else:
                succeeded += 1

        logger.info(
            f'Loaded {succeeded + failed} cogs ({succeeded} succeeded and {failed} failed)'
        )

    def _peek_extensions(self) -> Tuple[str]:
        """Collect the extensions to load and shuffle the list for priority"""
        raw = [
            (path.name if path.is_dir() else path.name.rsplit('.').pop(0))
            for path in _LIB_EXTS.iterdir()
            if path.is_dir() or (len(path.name) >= 4 and path.name.count('.') == 1)
        ]

        missing = tuple(
            extension
            for extension in PRIORITISED_EXTENSIONS
            if extension.name not in raw and extension.critical
        )

        if missing:
            raise RuntimeError(f'Critical extensions were not present! {missing!r}')
        else:
            extensions = [
                (
                    extension.name
                    if extension.name in raw
                    else logger.warn(f'Extension was not found! {extension!r}')
                )
                for extension in PRIORITISED_EXTENSIONS
            ]
            raw = [name for name in raw if name not in extensions]
            extensions += raw

            # Drain the extensions list from the NoneType's
            # present after any `logger.warn` calls.
            while None in extensions:
                extensions.remove(None)

        return tuple(extensions)

    def add_cog(self, cog):
        self._cog_counter += 1
        super().add_cog(cog)
        getattr(cog, f'_{type(cog).__name__}__cog_add', (lambda: None))()

    def load_extension(self, name):
        super().load_extension(name)
        logger.info(f'Loaded extension: {name!r}')

    async def on_message(self, message):
        await self.wait_until_ready()

        channel = message.channel
        guild = message.guild
        author = message.author

        if (
            guild is None
            or author.guild_permissions.administrator
            or channel.id in self._guild_command_channels
        ):
            await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        if not ctx.cog._enabled:
            if isinstance(error, commands.CheckFailure):
                await ctx.send('This command cannot be ran because the cog it belongs to is currently disabled.')
            else:
                logger.warn(f'Exception raised in disabled cog: cog={ctx.cog!r} error={error!r}')
                await ctx.send('An command belonging to a disabled cog raised an exception.')
        else:
            await ctx.send(error)

    async def on_connect(self):
        logger.info('Connected!')

    async def on_ready(self):
        self._guild = self.get_guild(_GUILD_SNOWFLAKE)
        logger.info('Ready!')
