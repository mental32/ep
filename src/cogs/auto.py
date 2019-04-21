import asyncio
import json

from ..utils import GuildCog

_PEP = lambda n: f'https://www.python.org/dev/peps/pep-{str(n).zfill(4)}/'


class Automation(GuildCog(455072636075245588)):
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
