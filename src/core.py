import os
import sys
import json
import pathlib

from discord.ext import commands

import src
from .utils import SocketLogger

SOCKET_INBOUND = 0
SOCKET_OUTOUND = 1

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

        self.__sock = SocketLogger(self)

        if not os.path.exists('.data.json'):
            raise RuntimeError('fatal: ".data.json" is a file that must exist. (try using the --init argument)')

        with open('.data.json') as inf:
            self._config = json.load(inf)

        for file in os.listdir(f'{_LIB_EXTS}'):
            if '__pycache__' in file:
                continue

            _cut_off = -3

            if os.path.isdir(f'{_LIB_EXTS.joinpath(file)}'):
                _cut_off = len(file) + 1

            elif file[-3:] != '.py':
                continue

            self.load_extension(f'src.cogs.{file[:_cut_off]}')

        self.run()

    def load_extension(self, *args, **kwargs):
        super().load_extension(*args, **kwargs)
        self.dispatch('ext_load', self.extensions[args[0]])

    def add_cog(self, klass, *args, **kwargs):
        super().add_cog(klass, *args, **kwargs)
        getattr(klass, f'_{type(klass).__name__}__cog_init', (lambda: None))()

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

    def run(self, *args, **kwargs):
        return super().run(self._config['token'])

    async def on_connect(self):
        print('Connect...', end='')

    async def on_ready(self):
        print('ready!')
        self._guild = self.get_guild(455072636075245588)

    async def on_ext_load(self, ext):
        print(f'Loaded: {repr(ext)}')

    async def on_cog_init(self, cog):
        print(f'Initalized: {repr(cog)}')

    async def on_socket_raw_receive(self, msg):
        self.__sock.write((SOCKET_INBOUND, msg))

    async def on_socket_raw_send(self, payload):
        self.__sock.write((SOCKET_OUTBOUND, payload))
