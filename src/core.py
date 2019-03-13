import os
import sys
import json
import pathlib
import asyncio

from discord.ext import commands

import src

_LIB_PATH = pathlib.Path(src.__file__).parents[0]
_LIB_EXTS = _LIB_PATH.joinpath('cogs')

def py_style(key):
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

        self.__socket_noloop = []

        if 'DISCORD_TOKEN' not in os.environ:
            raise RuntimeError('Could not find `DISCORD_TOKEN` in the environment!')

        token = os.environ['DISCORD_TOKEN']

        for file in os.listdir(f'{_LIB_EXTS}'):
            if '__pycache__' in file:
                continue

            _cut_off = -3

            if os.path.isdir(f'{_LIB_EXTS.joinpath(file)}'):
                _cut_off = len(file) + 1

            elif file[-3:] != '.py':
                continue

            self.load_extension(f'src.cogs.{file[:_cut_off]}')

        self.run(token)

    def load_extension(self, *args, **kwargs):
        super().load_extension(*args, **kwargs)
        self.dispatch('ext_load', self.extensions[args[0]])

    def add_cog(self, klass, *args, **kwargs):
        super().add_cog(klass, *args, **kwargs)
        getattr(klass, f'_{type(klass).__name__}__cog_add', (lambda: None))()

    def _do_cleanup(self, *args, **kwargs):
        super()._do_cleanup(*args, **kwargs)
        os.kill(os.getpid(), 3)

    async def get_context(self, *args, **kwargs):
        ctx = await super().get_context(*args, **kwargs)

        style = ((lambda key: key) if ctx.prefix != 'Py' else py_style)

        for cmd, coro in self.all_commands.items():
            if style(cmd) == ctx.invoked_with:
                ctx.command = coro
                break

        return ctx

    async def on_connect(self):
        print('Connect...', end='')

    async def on_ready(self):
        print('ready!')
        self._guild = self.get_guild(455072636075245588)

    async def on_ext_load(self, ext):
        print(f'Loaded: {repr(ext)}')

    async def on_cog_init(self, cog):
        print(f'Initalized: {repr(cog)}')

    async def on_socket_response(self, msg):
        if type(msg) is bytes:
            return

        await asyncio.sleep(1)

        if msg['t'] == 'MESSAGE_CREATE' and int(msg['d']['id']) in self.__socket_noloop:
            return self.__socket_noloop.remove(int(msg['d']['id']))

        j_msg = json.dumps(msg)

        if len(j_msg) >= 2000:
            return

        try:
            body = j_msg.replace("`", "\\`")
            msg = await self.get_channel(455073632859848724).send(f'```json\n{body}```')
            self.__socket_noloop.append(msg.id)
        except Exception as error:
            print(error)
