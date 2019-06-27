import asyncio
import re
import os
import random
import tempfile
from pathlib import Path
from typing import Set, Optional

import discord
from discord.ext import commands

from ..utils import GuildCog, codeblock
from ..utils.constants import EFFICIENT_PYTHON

_SYMLINK_RE = re.compile(r' -> (.+)\n+')
ROOT_TMP = Path('/tmp')


class FSInterface(GuildCog(EFFICIENT_PYTHON)):
    __root: Set[Path] = set()
    __removed: Set[Path] = set()
    __root_dir: Optional[Path] = None

    @GuildCog.setup
    async def __setup(self):
        if self.cog_was_reloaded:
            for file in ROOT_TMP.iterdir():
                if file.is_dir() and any(self.cog_hash == sub.name for sub in file.iterdir()):
                    self.__root_dir = file
                    return self.logger.info(f'VFS found! ({file!r}')
            else:
                self.logger.info('FSInterface was reloaded but could not retrieve VFS instance.')

        self.logger.info('Creating new VFS...')
        self.__root_dir = root = Path(tempfile.mkdtemp())
        self.logger.info(f'VFS is at: {root!r}')

        with open(f'{root / self.cog_hash}', 'w'):
            # This creates an empty file where the filename is the cog's hash
            # This is then used for identification and relinking.
            pass

        for path in self.__root:
            if not path.exists():
                self.logger.warn(f'Root path does not exist! {path!r}')
                self.unmount(path)
            else:
                self.mount(path)

    @GuildCog.check
    async def __is_owner(self, ctx):
        return await self.bot.is_owner(ctx.author)

    def cog_unload(self):
        self.bot.reloaded_cogs.add(self.cog_hash)

        if self.__removed:
            self.__root.update(self.__removed)
            self.__removed.clear()

    # Methods

    async def __sh_exec(self, command: str) -> str:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True
        )

        stdout, stderr = await process.communicate()

        return stdout.decode()

    def is_subset_path(self, path, directory):
        path = path.absolute().resolve()
        directory = directory.absolute().resolve()
        return os.path.commonprefix([str(path), str(directory)]) == str(directory)

    def resolve(self, path: Path) -> Optional[Path]:
        path = self.__root_dir.joinpath(path).absolute().resolve()
        return path if path.exists() else None

    def mount(self, path: Path):
        self.__root.add(path)
        root = self.__root_dir

        try:
            root.joinpath(path.name).symlink_to(path, target_is_directory=path.is_dir())
        except Exception as err:
            self.logger.warn(f'Failing during symlink: {err!r}')
            raise err
        else:
            self.logger.info(f'VFS : Linked {path!r}')

    def unmount(self, path: Path):
        assert path.is_symlink()
        assert path.resolve() in self.__root

        path.unlink()
        target = path.resolve()
        self.__root.remove(target)
        self.__removed.add(target)

    # Properties

    @property
    def root(self):
        return self.__root

    # Commands

    @commands.group(name='fs', alias=['filesystem'], invoke_without_command=True)
    async def _filesystem(self, ctx):
        await ctx.send('foo')

    @_filesystem.command(name='ls', alias=['list'])
    async def _filesystem_ls(self, ctx, path: Path):
        """List the contents of a directory inside the virtual filesystem."""
        path = self.resolve(path)

        if path is not None:
            ls_stdout = await self.__sh_exec(f'ls -alh {path.absolute()!s}')
            await ctx.send(codeblock(_SYMLINK_RE.sub('\n', ls_stdout)))
        else:
            raise commands.CommandError(f'cannot access "{path!s}": No such file or directory')

    @_filesystem.command(name='fetch')
    async def _filesystem_fetch(self, ctx, file: Path):
        """Fetch a single file from the virtual filesystem."""
        path = self.resolve(file)

        if path is None:
            raise commands.CommandError(f'cannot access "{file!s}": No such file or directory')
        elif path.is_dir():
            raise commands.CommandError(f'cannot fetch directories!')
        else:
            await ctx.send(file=discord.File(fp=str(path), filename=path.name))

    @_filesystem.command(name='rfetch')
    async def _filesystem_rfetch(self, ctx, directory: Path):
        """Fetch a random file from the virtual filesystem."""
        path = self.resolve(directory)

        if path is None:
            raise commands.CommandError(f'cannot access "{directory!s}": No such file or directory')
        elif path.is_file():
            raise commands.CommandError(f'cannot fetch randomly from a file!')
        else:
            target = random.choice(list(path.iterdir()))
            await ctx.send(file=discord.File(fp=str(target), filename=target.name))

    @_filesystem.command(name='mount')
    async def _filesystem_mount(self, ctx, path: Path):
        """Attempt to mount a path to the virtual filesystem root."""
        if not path.exists():
            raise commands.CommandError(f'cannot access "{path!s}": No such file or directory')
        else:
            self.mount(path)

    @_filesystem.command(name='unmount')
    async def _filesystem_unmount(self, ctx, path_name: str):
        """Attempt to unmount a path."""
        for root_entry in self.__root:
            if root_entry.name == path_name:
                try:
                    symlink_entry = next(path for path in self.__root_dir.iterdir() if (path.is_symlink() and path.resolve().samefile(root_entry)))
                except StopIteration:
                    await ctx.send('{path_name}: Was not a symbolic link!')
                else:
                    self.unmount(symlink_entry)
                    await ctx.send(f'Unmounted: {path_name}')
        else:
            raise commands.CommandError(f'{path_name}: No such file or directory')


def setup(bot):
    bot.add_cog(FSInterface(bot))
