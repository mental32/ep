import os
import sys
import pathlib
from functools import partial

from discord.ext import commands

_LIB_PATH = pathlib.Path(__file__).parents[0]
_LIB_EXTS = _LIB_PATH.joinpath('cogs')

_GUILD_SNOWFLAKE = 455072636075245588


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        kwargs['command_prefix'] = '?'

        super().__init__(*args, **kwargs)

        try:
            self.run = partial(self.run, os.environ['DISCORD_TOKEN'])
        except KeyError:
            self.loop.run_until_complete(self.http.close())  # Close the underlying http session.
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
            except Exception as err:
                print(f'Failed to load "{path.name}" ({err})', file=sys.stderr)

    def add_cog(self, klass, *args, **kwargs):
        super().add_cog(klass, *args, **kwargs)
        getattr(klass, f'_{type(klass).__name__}__cog_add', (lambda: None))()

    async def on_connect(self):
        print('Connect...', end='')

    async def on_ready(self):
        self._guild = self.get_guild(_GUILD_SNOWFLAKE)
        print('ready!')
