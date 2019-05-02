import dis
import io
from contextlib import redirect_stdout

import aiohttp
import discord
from discord.ext import commands

from ..utils import GuildCog

_PEP_URL_ERR = 'Invalid PEP (%s)'


class General(GuildCog(None)):
    @commands.command(name='source')
    async def _source(self, ctx):
        return await ctx.send('<https://github.com/mental32/ep_bot>')

    @commands.command(name='PEP')
    async def _pep(self, ctx, pep_number: int):
        pep = str(pep_number).zfill(4)
        url = f'https://www.python.org/dev/peps/pep-{pep}/'

        async with aiohttp.ClientSession() as cs:
            async with cs.get(url) as resp:
                await ctx.send(f'{url}' if resp.status == 200 else _PEP_URL_ERR % pep)

    @commands.command(name='dis')
    async def _dis(self, ctx, *, source):
        if source.startswith('```py\n'):
            source = source[6:]

        source = source.strip('`')
        out = io.StringIO()

        with redirect_stdout(out):
            dis.dis(source)

        await ctx.send(f'```py\n{out.getvalue()}```')

def setup(bot):
    bot.add_cog(General(bot))
