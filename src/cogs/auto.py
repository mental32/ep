import asyncio

from ..utils import GuildCog

_PEP = lambda n: f'https://www.python.org/dev/peps/pep-{str(n).zfill(4)}/'


class Automation(GuildCog(455072636075245588)):
    async def on_message(self, message):
        if message.author.bot:
            return

        elif message.content[:3] in ('PEP', 'pep'):
            def _links():
                for pep in message.content[3:].split():
                    if not pep.isdigit():
                        break
                    yield _PEP(int(pep))

            return await message.channel.send('\n'.join(_links()))

        elif message.content[:4] in ('DIS ', 'dis '):
            return await self.bot.get_command('dis').callback(None, message.channel, source=message.content[4:].strip())

    async def on_member_join(self, member):
        if member.guild != self._guild:
            return

        elif member.bot:
            return await member.add_roles(self._guild_roles['Bot'])

        await member.add_roles(self._guild_roles['Member'])
        await self._general.send(f'[{self._guild.member_count}] Welcome {member.mention}!', delete_after=1200.0)

def setup(bot):
    bot.add_cog(Automation(bot))
