from discord import Embed as _Embed
from discord.ext.commands import Cog as _Cog

__all__ = ('listener', 'event', 'codeblock', 'embed')

listener = _Cog.listener
event = listener()

def codeblock(string: str, style: str = '') -> str:
    """Format a string into a code block, escapes any other backticks"""
    zwsp = "``\u200b"
    return f'```{style}\n{string.replace("``", zwsp)}```\n'


def embed() -> _Embed:
	pass
