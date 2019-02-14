import dis
import io
from contextlib import redirect_stdout

import discord
from discord.ext import commands


class General:
    @commands.command(name='source')
    async def test_source(self, ctx):
        return await ctx.send('https://github.com/mental32/ep_bot')

    @commands.command(name='PEP')
    async def test_pep(self, ctx, pep_number: int):
        return await ctx.send(f'https://www.python.org/dev/peps/pep-{str(pep_number).zfill(4)}/')

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
