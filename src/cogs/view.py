import discord
from discord.ext import commands

_remaining_todo = {
    'Complete': [],
    'In progress': [
        'Website'
    ],
    'Not implemented': [
        'PyDoc',
        'PyProfile',
        'Python code sandbox',
        'CPython bug/branch tracker',
        'Forward PSF tweets?',
    ],
}


class General:
    @commands.command(name='todo')
    async def test_todo(self, ctx):
        await ctx.send('\n\n'.join(f'**{key}:**\n' + '\n'.join(f'• {_}' for _ in value) for key, value in _remaining_todo.items() if value))

    @commands.command(name='source')
    async def test_source(self, ctx):
        return await ctx.send('https://github.com/mental32/ep_bot')

    @commands.command(name='PEP')
    async def test_pep(self, ctx, pep_number: int):
        return await ctx.send(f'https://www.python.org/dev/peps/pep-{str(pep_number).zfill(4)}/')

    @commands.command(name='profile')
    async def test_profile(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        em = discord.Embed(title=f'{member}\'s profile')
        em.set_thumbnail(url=member.avatar_url)
        await ctx.send(embed=em)

def setup(bot):
    bot.add_cog(General())
