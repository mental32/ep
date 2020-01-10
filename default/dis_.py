"""Implementation of the dissasembler Cog."""
from contextlib import redirect_stdout
from dis import dis
from io import StringIO

from discord import Message
from ep import Cog, codeblock

__all__ = ("Disassembler",)


@Cog.export
class Disassembler(Cog):
    """Interactively disassemble Python code."""

    @Cog.regex(r"^(?:dis(?:assemble)?) ((```)|(`))(?(2)(?:py(?:thon)?)\n|)(?P<source>[\w\W]{1,2000})\1$")
    async def disassemble(self, message: Message, *, source: str) -> None:
        """Disassemble some Python source."""
        output = StringIO()

        with redirect_stdout(output):
            dis(source.strip("`"))

        await message.channel.send(codeblock(output.getvalue(), style="py"))
