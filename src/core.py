import os
import pathlib
import traceback
from functools import partial

from discord.ext import commands

from . import utils
from .utils import (
    PRIORITISED_EXTENSIONS,
    GUILD_SNOWFLAKE as _GUILD_SNOWFLAKE,
    LIB_EXTS as _LIB_EXTS,
)

logger = utils.get_logger(__name__)


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        kwargs['command_prefix'] = ('py_', 'py', 'py?', '?', '>>')

        super().__init__(*args, **kwargs)

        try:
            self.run = partial(self.run, os.environ['DISCORD_TOKEN'])
        except KeyError:
            self.loop.run_until_complete(
                self.http.close()
            )  # Close the underlying http session.
            raise RuntimeError('Could not find `DISCORD_TOKEN` in the environment!')

        self.load_extension('jishaku')

        for path in _LIB_EXTS.iterdir():
            if path.is_dir():
                name = path.name

            elif path.name.count('.') > 1:
                print(f'Skipping: {path.name}')
                continue

            else:
                name, *_ = path.name.rpartition('.')

            try:
                self.load_extension(f'src.cogs.{name}')
            except Exception:
                traceback.print_exc()

    def add_cog(self, klass, *args, **kwargs):
        super().add_cog(klass, *args, **kwargs)
        getattr(klass, f'_{type(klass).__name__}__cog_add', (lambda: None))()

    async def on_connect(self):
        print('Connect...', end='')

    async def on_ready(self):
        self._guild = self.get_guild(_GUILD_SNOWFLAKE)
        print('ready!')
