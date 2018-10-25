import dis
import io
from contextlib import redirect_stdout

import discord
from discord.ext import commands


_remaining_todo = {
    'Complete': [
        'PyDis'
    ],
    'In progress': [
        'Python code sandbox'
    ],
    'Not implemented': [
        'PyDoc',
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

    @commands.command(name='dis')
    async def test_dis(self, ctx, *, source):
        if source.startswith('```py\n'):
            source = source[6:]

        source = source.strip('`')
        out = io.StringIO()

        with redirect_stdout(out):
            dis.dis(source)

        await ctx.send(f'```py\n{out.getvalue()}```')


def setup(bot):
    bot.add_cog(General())
