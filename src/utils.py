import asyncio
import random
import traceback
import functools
from enum import IntEnum
from inspect import getmembers as _getmembers
from typing import Optional, Union, Type, Dict, Callable

from discord import Role as _Role
from discord.utils import maybe_coroutine as _run_possible_coroutine
from discord.ext import commands

__all__ = ('codeblock', 'GuildCogFactory', 'GuildCog')


def codeblock(string: str, style: str = '') -> str:
    """Format a string into a code block, escapes any other backticks"""
    zwsp = "``\u200b"
    return f'```{style}\n{string.replace("``", zwsp)}```\n'


class MethTypes(IntEnum):
    Setup = 0


class GuildCogFactory:
    """Factory class for GuildCogs.

    Attributes
    ----------
    MethTypes : IntEnum
        An enumeration of method types.
    GuildCog : GuildCogFactory.GuildCog
        The base class of a GuildCog instance.
    products : Dict[str, GuildCogFactory.GuildCog]
        The products produced by this factory.
    """
    class GuildCogBase(commands.Cog):
        """Base class for a GuildCog.

        Attributes
        ----------
        bot : discord.ext.commands.Bot
            The bot instance the cog belongs too.
        _enabled : bool
            A flag whether the current cog should be considered "enabled" or "present".
        """
        def __init__(self, bot: commands.Bot):
            self.__enabled = False
            self.bot = bot

            if self.bot.is_ready():
                self.bot.loop.create_task(self.__cog_init())

        def __repr__(self):
            return f'<Cog => {{ {type(self).__name__} }}>'

        @commands.Cog.listener()
        async def on_ready(self):
            await self.__cog_init()

        @property
        def _guild_roles(self) -> Dict[str, _Role]:
            return {role.name: role for role in self._guild.roles}

        @property
        def _enabled(self) -> bool:
            return self.__enabled

        @_enabled.setter
        def _enabled(self, value):
            self.__enabled = bool(value)

        @property
        def _guild(self):
            return self.bot.get_guild(self.__cog_guild__)

        @property
        def _general(self):
            return self._guild.get_channel(455072636075245590)

        async def __cog_init(self):
            await self.bot.wait_until_ready()

            for _, obj in _getmembers(self, (lambda obj: callable(obj) and hasattr(obj, '__guild_cog_tp__'))):
                if MethTypes.Setup in obj.__guild_cog_tp__:
                    await _run_possible_coroutine(obj)

            self._enabled = True

            if self._guild is not None:
                self.__factory__.products[self._guild.name] = self

            self.bot.dispatch('cog_init', self)

    products: Dict[str, GuildCogBase] = {}

    # Staticmethods
    # Wraps another object with the staticmethods of this factory.

    @staticmethod
    def wrap_staticmethods(obj):
        for attr in ('setup', 'check', 'passive_command'):
            setattr(obj, attr, getattr(GuildCogFactory, attr))
        return obj

    # Used as decorators to methods on Cogs

    @staticmethod
    def setup(func: Callable) -> Callable:
        """Dirty a function by marking it as a setup method of a GuildCog."""
        if not hasattr(func, '__guild_cog_tp__'):
            func.__guild_cog_tp__ = [MethTypes.Setup]
        else:
            func.__guild_cog_tp__.append(MethTypes.Setup)

        return func

    @staticmethod
    def check(pred: Callable) -> Callable:
        def decorator(func):
            @functools.wraps(func)
            def decorated(*args, **kwargs):
                if _run_possible_coroutine(pred(*args, **kwargs)):
                    return _run_possible_coroutine(func)
            return decorated
        return inner

    @staticmethod
    def passive_command(*, predicate=None, prefix=None):
        if predicate is not None and prefix is not None:
            raise TypeError('Only predicate or prefix must be supplied not both.')

        if prefix is not None:
            if isinstance(prefix, tuple):
                predicate = lambda message: any(message.content.startswith(substr) for substr in prefix)

            elif isinstance(prefix, str):
                predicate = lambda message: message.content[:len(prefix)] == prefix                

            else:
                raise TypeError
        else:
            predicate = predicate or (lambda _: True)

        def _passive_command_wrapper(func):

            @commands.Cog.listener('on_message')
            @functools.wraps(func)
            async def wrapper(message):
                try:
                    if not message.bot and predicate(message):
                        return await func(*args, **kwargs)
                except Exception as err:
                    traceback.print_exc()

        return _passive_command_wrapper



@GuildCogFactory.wrap_staticmethods
def GuildCog(snowflake: Optional[int]) -> Type[GuildCogFactory.GuildCogBase]:
    """Factory for GuildCogBase class instances, needed for guild specific GuildCogs."""
    if snowflake is not None and not isinstance(snowflake, int):
        raise TypeError(f'`snowflake` must be an int, got {type(snowflake)!r}')

    elif snowflake in GuildCogFactory.products:
        return GuildCogFactory.products[snowflake]

    else:
        GuildCogBase = GuildCogFactory.GuildCogBase

    class GuildCog(GuildCogBase):
        __cog_guild__ = snowflake
        __factory__ = GuildCogFactory
        __qualname__ = GuildCogBase.__qualname__
        __doc__ = GuildCogBase.__doc__

    return GuildCog
