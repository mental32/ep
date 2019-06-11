import logging
from typing import Optional

import coloredlogs

from discord import Embed as _Embed
from discord.ext.commands import Cog as _Cog

__all__ = ('listener', 'event', 'codeblock', 'embed', 'get_logger')

listener = _Cog.listener
event = listener()


def codeblock(string: str, style: str = '') -> str:
    """Format a string into a code block, escapes any other backticks"""
    zwsp = "``\u200b"
    return f'```{style}\n{string.replace("``", zwsp)}```\n'


def embed() -> _Embed:
    pass


def get_logger(
    name: str, level: str = 'INFO', fmt: Optional[str] = None
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))

    fmt = fmt or (
        '[%(asctime)s] %(levelname)s - %(funcName)s:%(lineno)d - %(module)s - %(message)s'
    )
    coloredlogs.install(fmt=fmt, level=level, logger=logger)
    return logger


get_logger(
    'discord', 'WARN', fmt='[[ discord ]] [%(asctime)s] %(levelname)s - %(message)s'
)
