import traceback
import functools
from enum import IntEnum
from inspect import getmembers as _getmembers
from typing import Optional, Type, Dict, Callable

from discord import Role as _Role
from discord.utils import maybe_coroutine as _run_possible_coroutine
from discord.ext import commands

from . import get_logger, event

__all__ = ('GuildCogFactory', 'GuildCog')


class MethTypes(IntEnum):
    Setup = 0
    CogCheck = 1


class GuildCogFactory:
    """Factory class for GuildCogs.

    Attributes
    ----------
    MethTypes : :class:`enum.IntEnum`
        An enumeration of method types.
    GuildCog : :class:`GuildCogFactory.GuildCog`
        The base class of a GuildCog instance.
    products : Dict[:class:`str`, :class:`GuildCogFactory.GuildCog`]
        A memoizing cache for the factory.
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

        __enabled: bool = False

        def __init__(self, bot: commands.Bot):
            self.logger = get_logger(f'cog.{type(self).__name__}')
            self.bot = bot

            self.__rich_methods = [
                getattr(self, name)
                for name, _ in _getmembers(
                    type(self),
                    (lambda obj: callable(obj) and hasattr(obj, '__guild_cog_tp__')),
                )
            ]

            def _cog_check_factory(func, *args, **kwargs):
                @functools.wraps(func)
                async def _cog_check(ctx):
                    return await _run_possible_coroutine(func, ctx)

                return _cog_check

            self.__cog_check_chain = [
                self._cog_check_factory(obj)
                for obj in self.__rich_methods
                if MethTypes.CogCheck in obj.__guild_cog_tp__
            ]


            if bot.is_ready():
                bot.loop.create_task(self.__cog_init())

        def __repr__(self):
            return f'<Cog name={type(self).__name__!r}>'

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

            for _, obj in _getmembers(
                self, (lambda obj: callable(obj) and hasattr(obj, '__guild_cog_tp__'))
            ):
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
        """Decorate a function by marking it as a setup method of a GuildCog."""
        if not hasattr(func, '__guild_cog_tp__'):
            func.__guild_cog_tp__ = [MethTypes.Setup]
        else:
            func.__guild_cog_tp__.append(MethTypes.Setup)

        return func

    @staticmethod
    def check(func: Callable) -> Callable:
        """Decorate a function by marking it as a local cog check of a GuildCog."""
        if not hasattr(func, '__guild_cog_tp__'):
            func.__guild_cog_tp__ = [MethTypes.CogCheck]
        else:
            func.__guild_cog_tp__.append(MethTypes.CogCheck)

        return func

    @staticmethod
    def passive_command(*, predicate=None, prefix=None):
        """Registers a passive command"""
        if predicate is not None and prefix is not None:
            raise TypeError('Only predicate or prefix must be supplied not both.')

        if prefix is not None:
            if isinstance(prefix, tuple):
                predicate = lambda message: any(
                    message.content.startswith(substr) for substr in prefix
                )

            elif isinstance(prefix, str):
                predicate = lambda message: message.content[: len(prefix)] == prefix

            else:
                raise TypeError
        else:
            predicate = predicate or (lambda _: True)

        def _passive_command_wrapper(func):
            @commands.Cog.listener('on_message')
            @functools.wraps(func)
            async def wrapper(self, message):
                try:
                    if not message.author.bot and predicate(message):
                        return await func(self, message)
                except Exception:
                    traceback.print_exc()

            return wrapper

        return _passive_command_wrapper


@GuildCogFactory.wrap_staticmethods
def GuildCog(snowflake: Optional[int]) -> Type[GuildCogFactory.GuildCogBase]:
    """Factory for GuildCogBase class instances, needed for guild specific GuildCogs.

    Parameters
    ----------
    snowflake : Optional[:class:`int`]
        The snowflake id of the guild the Cog should be registered under.
        `None` is accepted when the Cog isn't registered to any one guild.
    """
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
