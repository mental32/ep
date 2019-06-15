import traceback
import functools
from enum import IntEnum
from inspect import getmembers as _getmembers
from typing import Optional, Type, Dict, Callable

from discord import Role as _Role
from discord.abc import GuildChannel as _GuildChannel
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
        __can_be_enabled: bool = True

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
                _cog_check_factory(obj)
                for obj in self.__rich_methods
                if MethTypes.CogCheck in obj.__guild_cog_tp__
            ]

            self._database = bot.datastore

            if bot.is_ready():
                bot.loop.create_task(self.__cog_init())

        def __repr__(self):
            return f'<Cog name={type(self).__name__!r}>'

        async def __cog_init(self):
            await self.bot.wait_until_ready()

            if self._database is not None:
                await self._database.wait_until_ready()

            for obj in self.__rich_methods:
                if MethTypes.Setup in obj.__guild_cog_tp__:
                    try:
                        await _run_possible_coroutine(obj)
                    except Exception:
                        traceback.print_exc()

            if self.__can_be_enabled:
                self._enabled = True

            self.bot.dispatch('cog_init', self)

        # Properties

        @property
        def _enabled(self) -> bool:
            return self.__enabled

        @_enabled.setter
        def _enabled(self, value: bool):
            state = bool(value)

            if self.__enabled and not state:
                self.logger.warn(f'Disabling cog: {self!r}')

            self.__enabled = state

        @property
        def _guild(self):
            return self.bot.get_guild(self.__cog_guild__)

        @property
        def _general(self):
            return self._guild.get_channel(455072636075245590)

        @property
        def guild_roles(self) -> Dict[str, _Role]:
            return {role.name: role for role in self._guild.roles}

        @property
        def guild_channels(self) -> Dict[int, _GuildChannel]:
            return {channel.id: channel for channel in self._guild.channels}

        @property
        def cog_can_be_enabled(self) -> bool:
            return self.__can_be_enabled

        @cog_can_be_enabled.setter
        def cog_can_be_enabled(self, value: bool):
            boolean = bool(value)

            if boolean is False:
                self._enabled = False
                self.__can_be_enabled = False
            else:
                self.__can_be_enabled = True

        @property
        def instances(self):
            collection = self._database.default_collection
            return [] if collection is None else collection.instances

        @property
        def cog_tasks(self):
            return self.bot.task_manager

        cog_guild = _guild

        # Checks

        async def cog_check(self, ctx):
            if not self._enabled or ctx.guild.id != self.__cog_guild__:
                return False

            for check in self.__cog_check_chain:
                if not await check(ctx):
                    return False
            return True

        # Event handlers

        @event
        async def on_ready(self):
            await self.__cog_init()

    # Staticmethods
    # Wraps another object with the staticmethods of this factory.

    @staticmethod
    def wrap_staticmethods(obj):
        for name, attr in filter(
            (lambda obj: isinstance(obj[-1], staticmethod)), __class__.__dict__.items()
        ):
            setattr(obj, name, getattr(__class__, name))
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
