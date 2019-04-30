import os
import sys
import json
import pathlib
import asyncio
from functools import partial

from discord.ext import commands
from discord.utils import maybe_coroutine

import src

_LIB_PATH = pathlib.Path(src.__file__).parents[0]
_LIB_EXTS = _LIB_PATH.joinpath('cogs')
_GUILD_SNOWFLAKE = 455072636075245588

def snake_case(key):
    out = list(key.replace('__', '@'))

    while '_' in out:
        pos = out.index('_')
        del out[pos]
        out[pos] = out[pos].upper()

    return ''.join(out).replace('@', '_').title()


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        kwargs['command_prefix'] = ('Py', 'py_')

        super().__init__(*args, **kwargs)

        try:
            self.run = partial(self.run, os.environ['DISCORD_TOKEN'])
        except KeyError:
            self.loop.run_until_complete(self.http.close())  # Close the underlying http session.
            raise RuntimeError('Could not find `DISCORD_TOKEN` in the environment!')

        for file in os.listdir(f'{_LIB_EXTS}'):
            if '__pycache__' in file:
                continue

            _cut_off = -3

            if _LIB_EXTS.joinpath(file).is_dir():
                _cut_off = len(file)

            elif file[-3:] != '.py':
                continue

            try:
                self.load_extension(f'src.cogs.{file[:_cut_off]}')
            except Exception as err:
                print(f'Failed to load "{file}" ({err})', file=sys.stderr)

    def add_cog(self, klass, *args, **kwargs):
        super().add_cog(klass, *args, **kwargs)
        getattr(klass, f'_{type(klass).__name__}__cog_add', (lambda: None))()

    async def get_context(self, *args, **kwargs):
        ctx = await super().get_context(*args, **kwargs)

        style = ((lambda key: key) if ctx.prefix != 'Py' else snake_case)

        for cmd, coro in self.all_commands.items():
            if style(cmd) == ctx.invoked_with:
                ctx.command = coro
                break

        return ctx

    async def on_connect(self):
        print('Connect...', end='')

    async def on_ready(self):
        self._guild = self.get_guild(_GUILD_SNOWFLAKE)
        print('ready!')
