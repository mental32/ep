import asyncio


def GuildCog(snowflake: int):
    class GuildCog:
        def __init__(self, bot):
            self._enabled = False
            self.bot = bot

            if self.bot.is_ready():
                self.bot.loop.create_task(self.__cog_init())

        def __repr__(self):
            return f'<Cog => {{ {type(self).__name__} }}>'

        async def on_ready(self):
            await self.__cog_init()

        @property
        def _guild_roles(self):
            return {role.name: role for role in self._guild.roles}

        @property
        def _enabled(self):
            return self.__enabled

        @_enabled.setter
        def _enabled(self, value):
            self.__enabled = bool(value)

        async def __cog_init(self):
            while not hasattr(self.bot, '_guild'):
                await asyncio.sleep(0)

            self.__enabled = True

            self._guild = _guild = self.bot.get_guild(snowflake)
            self._general = _guild.get_channel(455072636075245590)

            _roles = self._guild_roles
            self._member_role = _roles['Member']
            self._bot_role = _roles['Bot']

            self.bot.dispatch('cog_init', self)

    return GuildCog
