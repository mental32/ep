import asyncio

from src.utils import GuildCog

class Automation(GuildCog):
    async def on_member_join(self, member):
        if member.bot:
            return await member.add_roles(self._bot_role)

        await member.add_roles(self._member_role)
        await self._general.send(f'Welcome {member.mention}', delete_after=600.0)

def setup(bot):
    bot.add_cog(Automation(bot))
