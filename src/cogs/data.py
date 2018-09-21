import asyncio
import base64
import json

import discord
from discord.ext import commands

from src.utils import GuildCog


class Datapoint:
    def __init__(self, message):
        self.message = message

    @property
    def content(self):
        return json.loads(base64.b64decode(self.message.content.encode()).decode())

    def _encode_json(self, data):
        return base64.b64encode(json.dumps(data).encode()).decode()

    async def update(self, key, value):
        body = self.content
        body[key] = value
        await self.message.edit(content=self._encode_json(body))
        return self

    async def edit(self, obj):
        await self.message.edit(content=self._encode_json(obj))
        return self


class Handler:
    __slots__ = ('channel', 'root')

    def __init__(self, channel):
        self.channel = channel
        self.root = None

    async def _purge_db(self):
        await self.channel.purge(limit=10_000_000, check=lambda m: m.author == self.channel.guild.me)

    async def _init_db(self, *, clear=False):
        if clear:
            await self._purge_db()

        self.root = root = await self.write({})
        return root

    async def write(self, obj, message_id=None):
        body = base64.b64encode(json.dumps(obj).encode()).decode()

        if message_id is None:
            message = await self.channel.send(body)
        else:
            message = await self.channel.get_message(message_id)
            await message.edit(content=body)

        return Datapoint(message)

    async def get(self, key):
        root = self.root or await self._get_root()

        if key not in root.content:
            raise KeyError

        message = await self.channel.get_message(root.content[key])
        return Datapoint(message)

    async def set(self, key, value):
        root = self.root or await self._get_root()
        data = root.content
        data[key] = value
        return await root.edit(data)

    async def _get_root(self):
        async for message in self.channel.history(limit=10, reverse=True):
            if message.author == self.channel.guild.me:
                self.root = root = Datapoint(message)
                return root

    async def _data_body(self, pred=None):
        pred = pred or (lambda *args: True)

        def check(message):
            return message.author == self.channel.guild.me and pred(message)

        async for message in channel.history(limit=10_000_000):
            if check(message):
                yield message.content


class Database(GuildCog):
    def __call__(self):
        return Handler(self._database)

    def __set_database(self):
        if self.bot.is_ready():
            self.bot.db = self.handler = self()

    def __cog_init(self):
        self.__set_database()

    async def on_ready(self):
        await super().on_ready()
        self.__set_database()

    @commands.command(name='db_init')
    @commands.is_owner()
    async def test_dbinit(self, ctx, clear: bool = False):
        root = await self.handler._init_db(clear=clear)
        await ctx.send(f'```fix\n{repr(root)}```')

def setup(bot):
    bot.add_cog(Database(bot))
