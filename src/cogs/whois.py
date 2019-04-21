from discord import Embed
from discord.ext.commands import MemberConverter, BadArgument

from ..utils import codeblock, GuildCog

DESCRIPTION = codeblock('''
[[Member]]
username = "{member}"
ID = {member.id}

{roles}
''', style='toml')

class SlimContext:
    __slots__ = ('bot', 'guild', 'message')

    def __init__(self, bot, message):
        self.bot = bot
        self.guild = bot._guild
        self.message = message


class Whois(GuildCog(455072636075245588)):
    converter = MemberConverter()

    async def on_message(self, message):
        if message.author.bot:
            return

        elif message.content[:5] == 'whois':
            target, *_ = message.content[5:].strip().split(' ', maxsplit=1)

            if not target:
                return

            try:
                member = await self.converter.convert(SlimContext(self, message), target)
            except BadArgument as error:
                return await message.channel.send(f'```\n{error!r}```')

            _ = lambda role: f'{role.id} > {role.name!r}'
            description = DESCRIPTION.format(member=member, roles='\n'.join(f'role-{i} = {_(role)}' for i, role in enumerate(member.roles)))

            embed = Embed(description=description)
            embed.set_thumbnail(url=member.avatar_url)
            embed.set_author(name=member.name, icon_url=member.avatar_url)

            await message.channel.send(embed=embed)

def setup(bot):
    bot.add_cog(Whois(bot))
