import dis
import io
from contextlib import redirect_stdout

import aiohttp
from discord.ext import commands

from ..utils import GuildCog, codeblock
from ..utils.constants import PEP_URL_ERR as _PEP_URL_ERR


class General(GuildCog(None)):
    @commands.command(name='source')
    async def _source_command(self, ctx, target: str = None):
        """Link the source of a target."""
        if target is None:
            return await ctx.send('<https://github.com/mental32/ep_bot>')

    @commands.command(name='PEP')
    async def _pep_command(self, ctx, pep_number: int = 0):
        pep = str(pep_number).zfill(4)
        url = f'https://www.python.org/dev/peps/pep-{pep}/'

        async with aiohttp.ClientSession as cs:
            async with cs.get(url) as resp:
                await ctx.send(
                    f'{url}' if resp.status == 200 else _PEP_URL_ERR % pep_number
                )

    @commands.command(name='dis')
    async def _dis_command(self, ctx, *, source):
        if source.startswith('```py\n'):
            source = source[6:]

        source = source.strip('`')
        out = io.StringIO()

        try:
            with redirect_stdout(out):
                dis.dis(source)
        except Exception as err:
            out.write(f'{err!r}')

        await ctx.send(codeblock(out.getvalue(), style='py'))


def setup(bot):
    bot.add_cog(General(bot))
