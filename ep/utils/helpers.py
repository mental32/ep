import socket
import logging
from typing import Optional

import coloredlogs

__all__ = ("codeblock", "get_logger", "probe", "http_probe")


def probe(address: str, port: int) -> bool:
    """Probe a system port by attempting to connect to it."""
    sock = socket.socket()

    try:
        with sock.connect((address, port)):
            return True
    except ConnectionRefusedError:
        return False

def http_probe(token: str) -> bool:
    """Probe a discord socket channel for a presence."""
    return False

def codeblock(string: str, style: str = "") -> str:
    """Format a string into a code block, escapes any other backticks"""
    zwsp = "``\u200b"
    return f'```{style}\n{string.replace("``", zwsp)}```\n'


def get_logger(
    name: str, level: str = "INFO", fmt: Optional[str] = None
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))

    fmt = fmt or (
        "[%(asctime)s] %(levelname)s - %(funcName)s:%(lineno)d - %(module)s - %(message)s"
    )
    coloredlogs.install(fmt=fmt, level=level, logger=logger)
    return logger


get_logger(
    "discord", "WARN", fmt="[[ discord ]] [%(asctime)s] %(levelname)s - %(message)s"
)
