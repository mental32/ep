import json
import asyncio


class GuildCog:
    def __init__(self, bot):
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

    async def __cog_init(self):
        while not hasattr(self.bot, '_guild'):
            await asyncio.sleep(0)

        self._guild = _guild = self.bot._guild
        self._general = _guild.get_channel(455072636075245590)

        _roles = self._guild_roles
        self._member_role = _roles['Member']
        self._bot_role = _roles['Bot']

        self.bot.dispatch('cog_init', self)


class SocketLogger:
    def __init__(self, client):
        self._buffer = []
        self._client = client

        client.loop.create_task(self._write_task())

    def write(self, data):
        self._buffer.append(data)

    async def _write_task(self):
        while True:
            await asyncio.sleep(60)

            if not self._buffer:
                continue

            with open('.socket.json', 'r') as inf:
                body = json.loads(inf.read())

            body += self._buffer
            self._buffer = []

            with open('.socket.json', 'w') as inf:
                inf.write(json.dumps(body))
