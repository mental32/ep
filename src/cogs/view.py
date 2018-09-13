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

    @commands.command(name='magic')
    async def test_magic(self, ctx, number: int = None):
        try:
            datapoint = await ctx.bot.db.get(ctx.author.id)
        except KeyError:
            datapoint = await ctx.bot.db.set(ctx.author.id, number)

        if number is None:
            await ctx.send(datapoint.content)
        else:
            await datapoint.update(ctx.author.id, number)
            await ctx.send('\N{OK HAND SIGN}')

def setup(bot):
    bot.add_cog(General())
