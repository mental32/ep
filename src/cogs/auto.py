import asyncio
import json
import datetime

from ..utils import GuildCog

_PEP = lambda n: f'https://www.python.org/dev/peps/pep-{str(n).zfill(4)}/'


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

    async def on_message(self, message):
        if message.author.bot:
            return

        if message.content[:3] in ('PEP', 'pep'):
            for pep in message.content[3:].split():
                if not pep.isdigit():
                    break
                else:
                    await self.bot.get_command('PEP').callback(None, message.channel, pep)

        elif message.content[:4] in ('DIS ', 'dis '):
            return await self.bot.get_command('dis').callback(None, message.channel, source=message.content[4:].strip())

    async def on_member_join(self, member):
        if member.guild != self._guild:
            return

        elif member.bot:
            return await member.add_roles(self._guild_roles['Bot'])

        await member.add_roles(self._guild_roles['Member'])
        await self._general.send(f'[{self._guild.member_count}] Welcome {member.mention}!', delete_after=1200.0)

    async def on_socket_response(self, msg):
        if type(msg) is bytes:
            return

        await asyncio.sleep(1)

        if msg['t'] == 'MESSAGE_CREATE' and int(msg['d']['id']) in self.__socket_ignore:
            return self.__socket_ignore.remove(int(msg['d']['id']))

        body = json.dumps(msg)

        if len(body) >= 2000:
            return

        try:
            msg = await self.__socket.send(codeblock(body, style='json'))
        except Exception as error:
            pass
        else:
            self.__socket_ignore.append(msg.id)

def setup(bot):
    bot.add_cog(Automation(bot))
