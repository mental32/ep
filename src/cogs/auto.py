import asyncio

from src.utils import GuildCog

_PEP = lambda n: f'https://www.python.org/dev/peps/pep-{str(n).zfill(4)}/'


class Automation(GuildCog):
    async def on_message(self, message):
        if message.author.bot:
            return

        elif message.content[:3] == 'PEP':
            def _links():
                for pep in message.content[3:].split():
                    if not pep.isdigit():
                        break
                    yield _PEP(int(pep))

            return await message.channel.send('\n'.join(_links()))

    async def on_member_join(self, member):
        if member.guild != self._guild:
            return

        elif member.bot:
            return await member.add_roles(self._bot_role)

        await member.add_roles(self._member_role)
        await self._general.send(f'Welcome {member.mention}', delete_after=600.0)

def setup(bot):
    bot.add_cog(Automation(bot))
