import asyncio
import json
import datetime

from discord.ext import commands

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
        self.bot.loop.create_task(self.statistics())

    async def statistics(self):
        member_statistic = self.bot.get_channel(567812974270742538)
        local_time = self.bot.get_channel(567816759675977758)

        member_count = 0

        while True:
            if member_count != self._guild.member_count:
                member_count = self._guild.member_count
                await member_statistic.edit(name=f'Total members: {member_count}')

            t = datetime.datetime.now().strftime('%H:%M')
            await local_time.edit(name=f'Server Time: {t}')
            await asyncio.sleep(60)

    async def bump_unlock(self, target, *, timeout):
        """Unlock the bump channel by giving Members send_messages permission after a timeout."""
        await asyncio.sleep(timeout)
        await channel.set_permissions(member_role, send_messages=True)

    @commands.Cog.listener()
    async def on_cog_init(self, cog):
        print(f'Initalized: {repr(cog)}')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.channel.id == BUMP_CHANNEL_ID:
            content = message.content

            if any(content.startswith(prefix) for prefix in DISBOARD_BOT_PREFIX):

                try:
                    response = await self.bot.wait_for('message', check=_disboard_bot_check)
                except Exception as err:
                    await response.delete()

                if response.embeds and 'bump done' in response.embeds[0].description.lower():
                    member_role = self._guild_roles['Member']

                    await channel.set_permissions(member_role, send_messages=False)

                    return self.bot.loop.create_task(self.bump_unlock(member_role, timeout=_TWO_HOURS))

            await message.delete()

        elif message.content[:3] in ('PEP', 'pep'):
            for pep in message.content[3:].split():
                if not pep.isdigit():
                    break
                else:
                    await self.bot.get_command('PEP').callback(None, message.channel, pep)

        elif message.content[:4] in ('DIS ', 'dis '):
            return await self.bot.get_command('dis').callback(None, message.channel, source=message.content[4:].strip())

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
