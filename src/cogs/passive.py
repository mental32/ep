import shlex

from discord import Embed
from discord.ext.commands import MemberConverter, BadArgument

from ..utils import codeblock, GuildCog
from ..utils.constants import EFFICIENT_PYTHON, WHOIS_TEMPLATE as DESCRIPTION


class SlimContext:
    __slots__ = ('bot', 'guild', 'message')

    def __init__(self, bot, message):
        self.bot = bot
        self.guild = bot._guild
        self.message = message


class PassiveCommands(GuildCog(EFFICIENT_PYTHON)):
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

        roles = 'roles = [\n{0}\n]'.format(
            '\n'.join(f'    "{role.id}:{role.name}",' for role in member.roles)
        )
        description = DESCRIPTION.format(member=member, roles=roles)

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

    @GuildCog.passive_command(prefix=('dis '))
    async def _dis_command(self, message):
        await self.bot.get_command('dis').callback(
            None, message.channel, source=message.content[4:].strip()
        )


def setup(bot):
    bot.add_cog(PassiveCommands(bot))
