from discord import Embed
from discord.ext.commands import MemberConverter, BadArgument

from ..utils import GuildCog

DESCRIPTION = '''```ini
[Member/{member}]
ID = {member.id}

{roles}```
'''

class SlimContext:
    def __init__(self, bot, message):
        self.bot = bot
        self.guild = bot._guild
        self.message = message


class Whois(GuildCog):
    converter = MemberConverter()

    async def on_message(self, message):
        if message.author.bot:
            return

        elif message.content[:5] == 'whois':
            target, *_ = message.content[5:].strip().split(' ', maxsplit=1)

            try:
                member = await self.converter.convert(SlimContext(self, message), target)
            except BadArgument as error:
                return await message.channel.send(f'```\n{error!r}```')

            description = DESCRIPTION.format(member=member, roles='\n'.join(f'role-{i} = {role!r}' for i, role in enumerate(member.roles)))

            embed = Embed(description=description)
            embed.set_thumbnail(url=member.avatar_url)
            embed.set_author(name=member.name, icon_url=member.avatar_url)

            await message.channel.send(embed=embed)

def setup(bot):
    bot.add_cog(Whois(bot))
