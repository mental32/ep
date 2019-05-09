import shlex

from discord import Embed
from discord.ext import commands
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


class PassiveCommands(GuildCog(455072636075245588)):
    converter = MemberConverter()

    @GuildCog.passive_command(prefix='whois ')
    async def _whois_command(self, message):
        target, *_ = message.content[5:].strip().split(' ', maxsplit=1)

        if not target:
            return

        try:
            member = await self.converter.convert(SlimContext(self, message), target)
        except BadArgument as error:
            return await message.channel.send(codeblock(repr(error)))

        fmt = lambda role: f'{role.id} > {role.name!r}'
        description = DESCRIPTION.format(member=member, roles='\n'.join(f'role-{i} = {fmt(role)}' for i, role in enumerate(member.roles)))

        embed = Embed(description=description)
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_author(name=member.name, icon_url=member.avatar_url)

        await message.channel.send(embed=embed)

    @GuildCog.passive_command(prefix=('PEP', 'pep'))
    async def _pep_command(self, message):
        for pep in shlex.split(message.content[3:]):
            if pep.isdigit():
                await self.bot.get_command('PEP').callback(None, message.channel, pep)
            else:
                break

    @GuildCog.passive_command(prefix=('DIS', 'dis'))
    async def _dis_command(self, message):
        await self.bot.get_command('dis').callback(None, message.channel, source=message.content[4:].strip())

def setup(bot):
    bot.add_cog(Whois(bot))
