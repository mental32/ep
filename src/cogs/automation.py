import asyncio
import json
import datetime

from discord.ext import commands, tasks

from ..utils import GuildCog, codeblock

_PEP = lambda n: f'https://www.python.org/dev/peps/pep-{str(n).zfill(4)}/'

DISBOARD_BOT_PREFIX = ('!d', '!disboard')

DISBOARD_BOT_ID = 302050872383242240
BUMP_CHANNEL_ID = 575696848405397544

_TWO_HOURS = 3600 * 2

def _disboard_bot_check(message):
    return message.channel.id == BUMP_CHANNEL_ID and message.author.id == DISBOARD_BOT_ID


class Automation(GuildCog(455072636075245588)):
    __socket_ignore = []

    @GuildCog.setup
    async def setup(self):
        self.__socket = self._guild.get_channel(455073632859848724)

        self.__cached_member_count = self._guild.member_count

        self.__bump_channel = bump = self.bot.get_channel(BUMP_CHANNEL_ID)
        self.__member_stat_channel = self.bot.get_channel(567812974270742538)
        self.__time_stat_channel = self.bot.get_channel(567816759675977758)

        self.statistic_task.start()

        member_role = self._guild_roles['Member']

        async for message in bump.history(limit=1):
            delta = (datetime.datetime.now() - message.created_at).total_seconds()
            locked = delta < _TWO_HOURS

            if locked:
                self.bot.loop.create_task(self.bump_unlock(member_role, timeout=_TWO_HOURS - delta))

        await self.__bump_channel.set_permissions(member_role, send_messages=locked, read_messages=True)

    @tasks.loop(seconds=60, reconnect=True)
    async def statistic_task(self):
        if self._guild.member_count != self.__cached_member_count:
            self.__cached_member_count = self._guild.member_count
            await self.__member_stat_channel.edit(name=f'Total members: {member_count}')

        t = datetime.datetime.now().strftime('%H:%M')
        await self.__time_stat_channel.edit(name=f'Server Time: {t}')

    async def bump_unlock(self, target, *, timeout):
        """Unlock the bump channel by giving Members send_messages permission after a timeout."""
        await asyncio.sleep(timeout)
        await self.__bump_channel.set_permissions(target, send_messages=True, read_messages=True)

    @commands.Cog.listener()
    async def on_cog_init(self, cog):
        print(f'Initalized: {repr(cog)}')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        elif message.channel.id == BUMP_CHANNEL_ID:
            content = message.content

            if ' ' in content and content.endswith('bump') and any(content.startswith(prefix) for prefix in DISBOARD_BOT_PREFIX):

                try:
                    response = await self.bot.wait_for('message', check=_disboard_bot_check)
                except Exception as err:
                    await response.delete()

                if response.embeds and 'bump done' in response.embeds[0].description.lower():
                    member_role = self._guild_roles['Member']

                    await self.__bump_channel.set_permissions(member_role, send_messages=False, read_messages=True)

                    return self.bot.loop.create_task(self.bump_unlock(member_role, timeout=_TWO_HOURS))
                else:
                    await response.delete()

            await message.delete()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild != self._guild:
            return

        elif member.bot:
            return await member.add_roles(self._guild_roles['Bot'])

        await member.add_roles(self._guild_roles['Member'])
        await self._general.send(f'[{self._guild.member_count}] Welcome {member.mention}!', delete_after=1200.0)

    @commands.Cog.listener()
    async def on_socket_response(self, msg):
        if type(msg) is bytes:
            return

        elif not self.bot.is_ready():
            return

        await asyncio.sleep(1)

        if msg['t'] == 'MESSAGE_CREATE' and int(msg['d']['id']) in self.__socket_ignore:
            return self.__socket_ignore.remove(int(msg['d']['id']))

        body = json.dumps(msg)

        if len(body) >= 2000:
            return

        try:
            msg = await self.__socket.send(codeblock(body, style='json'))
        except Exception:
            pass
        else:
            self.__socket_ignore.append(msg.id)

def setup(bot):
    bot.add_cog(Automation(bot))
